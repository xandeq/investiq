"""Context assembler — collects real-world context for a ticker before LLM calls.

Used by copilot.py picks and briefing_engine to enrich prompts with:
  - sentiment_score: weighted average from Reddit + StockTwits snapshots
  - news_headlines: recent headlines from news_events (via Redis cache)
  - reddit_mentions: mention count from sentiment_snapshots

All lookups are async; DB access runs in executor to avoid blocking event loop.
Never raises — returns partial/empty context on any failure.
"""

import asyncio
import json
import logging
import os
from typing import Any

logger = logging.getLogger(__name__)


async def get_context_for_ticker(
    ticker: str,
    hours: int = 6,
    redis_client=None,
) -> dict[str, Any]:
    """Assemble market context for a ticker from all available data sources.

    Returns:
        {
            "ticker": str,
            "sentiment_score": float | None,   # [-1.0, 1.0] or None if no data
            "news_headlines": list[str],        # ≤3 recent headlines
            "reddit_mentions": int,             # mention count in last 24h
            "sources_used": list[str],          # which sources had data
        }
    """
    loop = asyncio.get_event_loop()
    ticker = ticker.upper()
    context: dict[str, Any] = {
        "ticker": ticker,
        "sentiment_score": None,
        "news_headlines": [],
        "reddit_mentions": 0,
        "sources_used": [],
    }

    # 1. News headlines from Redis (set by ingest_news_events task, TTL 3h)
    if redis_client is not None:
        try:
            raw = await redis_client.get(f"news:ticker:{ticker}:recent")
            if raw:
                headlines = json.loads(raw) if isinstance(raw, str) else json.loads(raw.decode())
                context["news_headlines"] = headlines[:3]
                if headlines:
                    context["sources_used"].append("news")
        except Exception as exc:
            logger.debug("context_assembler: Redis news lookup failed for %s: %s", ticker, exc)

    # 2. Sentiment from DB (sentiment_snapshots) via executor
    try:
        sentiment_data = await loop.run_in_executor(None, lambda: _fetch_sentiment_sync(ticker, hours))
        if sentiment_data["score"] is not None:
            context["sentiment_score"] = sentiment_data["score"]
            context["reddit_mentions"] = sentiment_data["reddit_mentions"]
            context["sources_used"].extend(sentiment_data["sources"])
    except Exception as exc:
        logger.debug("context_assembler: sentiment lookup failed for %s: %s", ticker, exc)

    return context


def _fetch_sentiment_sync(ticker: str, hours: int) -> dict[str, Any]:
    """Sync helper: query sentiment_snapshots via psycopg2."""
    import psycopg2

    result: dict[str, Any] = {"score": None, "reddit_mentions": 0, "sources": []}

    db_url = os.environ.get("DATABASE_URL", "")
    if not db_url:
        return result
    db_url = db_url.replace("postgresql+asyncpg://", "postgresql://").replace("asyncpg://", "postgresql://")

    try:
        conn = psycopg2.connect(db_url)
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT source, score, mention_count
                FROM sentiment_snapshots
                WHERE ticker = %s
                  AND created_at >= NOW() - make_interval(hours => %s)
                ORDER BY created_at DESC
                LIMIT 6
                """,
                (ticker, hours),
            )
            rows = cur.fetchall()
        conn.close()

        if not rows:
            return result

        total_weight = 0
        weighted_sum = 0.0
        seen_sources: set[str] = set()

        for source, score, mention_count in rows:
            weight = max(mention_count or 1, 1)
            weighted_sum += float(score) * weight
            total_weight += weight
            if source not in seen_sources:
                seen_sources.add(source)
                result["sources"].append(source)
            if source == "reddit":
                result["reddit_mentions"] += mention_count or 0

        result["score"] = round(weighted_sum / total_weight, 3) if total_weight else None

    except Exception as exc:
        logger.debug("_fetch_sentiment_sync %s: %s", ticker, exc)

    return result


async def get_context_batch(
    tickers: list[str],
    hours: int = 6,
    redis_client=None,
) -> dict[str, dict[str, Any]]:
    """Fetch context for multiple tickers concurrently."""
    tasks = [get_context_for_ticker(t, hours=hours, redis_client=redis_client) for t in tickers]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    return {
        ticker: (result if isinstance(result, dict) else {})
        for ticker, result in zip(tickers, results)
    }
