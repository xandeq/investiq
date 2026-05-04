"""Briefing Engine API router.

GET  /briefing/daily              — latest cached daily report (or generates on demand)
POST /briefing/generate           — force-generate a new report (admin)
POST /briefing/send-test          — trigger morning briefing to Telegram right now (admin)
GET  /briefing/sentiment?ticker=  — latest sentiment snapshot for a B3 ticker
"""

import json
import logging
import os
from datetime import datetime, timezone, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi import status as http_status

from app.core.config import settings
from app.core.limiter import limiter
from app.core.middleware import get_current_tenant_id
from app.core.security import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter()

_CACHE_KEY = "briefing_engine:latest"
_CACHE_TTL = 6 * 3600  # 6 hours


@router.get("/daily")
@limiter.limit("10/minute")
async def get_daily_briefing(
    request: Request,
    tenant_id: str = Depends(get_current_tenant_id),
) -> dict:
    """Return the latest daily briefing report."""
    import redis.asyncio as aioredis

    redis_url = os.environ.get("REDIS_URL", "redis://redis:6379/0")
    r = aioredis.from_url(redis_url, decode_responses=True)
    try:
        cached = await r.get(_CACHE_KEY)
        if cached:
            report = json.loads(cached)
            report["from_cache"] = True
            return report

        # Generate on demand
        from app.modules.briefing_engine.report import build_full_report
        report = await build_full_report(redis_client=r)

        await r.setex(_CACHE_KEY, _CACHE_TTL, json.dumps(report, default=str))
        report["from_cache"] = False
        return report
    finally:
        await r.aclose()


@router.post("/generate")
@limiter.limit("3/minute")
async def force_generate_briefing(
    request: Request,
    tenant_id: str = Depends(get_current_tenant_id),
) -> dict:
    """Force-generate a new briefing report (ignores cache)."""
    import redis.asyncio as aioredis

    redis_url = os.environ.get("REDIS_URL", "redis://redis:6379/0")
    r = aioredis.from_url(redis_url, decode_responses=True)
    try:
        from app.modules.briefing_engine.report import build_full_report
        report = await build_full_report(redis_client=r)
        await r.setex(_CACHE_KEY, _CACHE_TTL, json.dumps(report, default=str))
        return {**report, "from_cache": False}
    finally:
        await r.aclose()


@router.post("/send-test")
@limiter.limit("2/minute")
async def send_test_briefing(
    request: Request,
    current_user=Depends(get_current_user),
) -> dict:
    """Trigger morning briefing to Telegram immediately (admin only).

    Builds the full report and sends it via Telegram — same as the 08h30 beat task.
    """
    if not current_user or current_user.email not in settings.ADMIN_EMAILS:
        raise HTTPException(status_code=http_status.HTTP_403_FORBIDDEN, detail="Admin only")

    from app.modules.telegram_bot.tasks import send_morning_briefing
    result = send_morning_briefing.delay()
    task_id = result.id
    return {"status": "queued", "task_id": task_id, "message": "Morning briefing queued for Telegram delivery"}


@router.get("/sentiment")
@limiter.limit("30/minute")
async def get_sentiment(
    request: Request,
    ticker: str = Query(..., description="B3 ticker, e.g. PETR4"),
    current_user=Depends(get_current_user),
) -> dict:
    """Return the latest sentiment snapshot for a ticker.

    Aggregates Reddit + StockTwits scores from the last 24h ingestion run.
    Returns score in [-1.0, 1.0] and mention counts per source.
    """
    ticker = ticker.upper().strip()
    if not ticker or len(ticker) > 10:
        raise HTTPException(status_code=http_status.HTTP_400_BAD_REQUEST, detail="Invalid ticker")

    import os
    import psycopg2

    db_url = os.environ.get("DATABASE_URL", "")
    if not db_url:
        raise HTTPException(status_code=http_status.HTTP_503_SERVICE_UNAVAILABLE, detail="DB not configured")

    db_url = db_url.replace("postgresql+asyncpg://", "postgresql://").replace("asyncpg://", "postgresql://")

    try:
        conn = psycopg2.connect(db_url)
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT source, score, mention_count, sample_posts, created_at
                FROM sentiment_snapshots
                WHERE ticker = %s
                  AND created_at >= NOW() - INTERVAL '25 hours'
                ORDER BY created_at DESC
                LIMIT 10
                """,
                (ticker,),
            )
            rows = cur.fetchall()
        conn.close()
    except Exception as exc:
        logger.error("briefing/sentiment DB error: %s", exc)
        raise HTTPException(status_code=http_status.HTTP_503_SERVICE_UNAVAILABLE, detail="DB error")

    if not rows:
        return {
            "ticker": ticker,
            "score": None,
            "mention_count": 0,
            "sources": [],
            "last_updated": None,
            "message": "No sentiment data yet — ingestion runs every 30min during market hours",
        }

    sources = []
    total_mentions = 0
    scores_weighted: list[tuple[float, int]] = []
    latest_ts = None

    for source, score, mention_count, sample_posts, created_at in rows:
        sources.append({
            "source": source,
            "score": float(score),
            "mention_count": mention_count,
            "sample_posts": sample_posts or [],
            "created_at": created_at.isoformat() if created_at else None,
        })
        total_mentions += mention_count or 0
        weight = max(mention_count or 0, 1)
        scores_weighted.append((float(score), weight))
        if latest_ts is None or (created_at and created_at > latest_ts):
            latest_ts = created_at

    # Weighted average score
    total_weight = sum(w for _, w in scores_weighted)
    avg_score = round(sum(s * w for s, w in scores_weighted) / total_weight, 3) if total_weight else 0.0

    return {
        "ticker": ticker,
        "score": avg_score,
        "mention_count": total_mentions,
        "sources": sources,
        "last_updated": latest_ts.isoformat() if latest_ts else None,
    }


@router.get("/news-feed")
@limiter.limit("30/minute")
async def get_news_feed(
    request: Request,
    ticker: str = Query(None, description="Filter by B3 ticker, e.g. PETR4"),
    hours: int = Query(6, ge=1, le=48, description="Look-back window in hours"),
    current_user=Depends(get_current_user),
) -> dict:
    """Return recent market news, optionally filtered by ticker.

    Uses news_events table populated by the ingest-news-events Celery task (every 2h).
    Returns up to 20 most recent headlines.
    """
    import os
    import psycopg2

    db_url = os.environ.get("DATABASE_URL", "")
    if not db_url:
        raise HTTPException(status_code=http_status.HTTP_503_SERVICE_UNAVAILABLE, detail="DB not configured")
    db_url = db_url.replace("postgresql+asyncpg://", "postgresql://").replace("asyncpg://", "postgresql://")

    try:
        conn = psycopg2.connect(db_url)
        with conn.cursor() as cur:
            if ticker:
                ticker = ticker.upper().strip()
                cur.execute(
                    """
                    SELECT headline, url, source, tickers, sentiment, published_at
                    FROM news_events
                    WHERE %s = ANY(tickers)
                      AND published_at >= NOW() - make_interval(hours => %s)
                    ORDER BY published_at DESC
                    LIMIT 20
                    """,
                    (ticker, hours),
                )
            else:
                cur.execute(
                    """
                    SELECT headline, url, source, tickers, sentiment, published_at
                    FROM news_events
                    WHERE published_at >= NOW() - make_interval(hours => %s)
                    ORDER BY published_at DESC
                    LIMIT 20
                    """,
                    (hours,),
                )
            rows = cur.fetchall()
        conn.close()
    except Exception as exc:
        logger.error("briefing/news-feed DB error: %s", exc)
        raise HTTPException(status_code=http_status.HTTP_503_SERVICE_UNAVAILABLE, detail="DB error")

    items = [
        {
            "headline": r[0],
            "url": r[1],
            "source": r[2],
            "tickers": r[3] or [],
            "sentiment": float(r[4]) if r[4] is not None else None,
            "published_at": r[5].isoformat() if r[5] else None,
        }
        for r in rows
    ]

    return {
        "ticker_filter": ticker if ticker else None,
        "hours": hours,
        "count": len(items),
        "items": items,
    }
