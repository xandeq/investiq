"""StockTwits adapter — retail sentiment for B3 tickers.

Uses the public StockTwits API (no auth required for basic streams).
B3 tickers are accessed via Yahoo Finance format: {TICKER}.SA
e.g., PETR4 → https://api.stocktwits.com/api/2/streams/symbol/PETR4.SA.json

Rate limit: ~300 req/hour unauthenticated.
"""

import logging
from datetime import datetime, timezone, timedelta
from typing import Any

import requests

logger = logging.getLogger(__name__)

_BASE = "https://api.stocktwits.com/api/2"
_TIMEOUT = 8
_HEADERS = {"User-Agent": "InvestIQ/2.0 (investiq.com.br)"}

# StockTwits sentiment label mapping
_SENTIMENT_MAP = {"Bullish": 1.0, "Bearish": -1.0}


def get_stocktwits_sentiment(ticker: str, hours_back: int = 24) -> dict[str, Any]:
    """Fetch StockTwits stream for a B3 ticker and compute sentiment.

    Uses TICKER.SA format (Yahoo Finance / StockTwits B3 convention).
    Returns:
        {
            "ticker": str,
            "source": "stocktwits",
            "score": float,
            "mention_count": int,
            "sample_posts": list[str],
            "window_hours": int,
        }
    """
    symbol = f"{ticker}.SA"
    cutoff = datetime.now(timezone.utc) - timedelta(hours=hours_back)

    try:
        url = f"{_BASE}/streams/symbol/{symbol}.json"
        resp = requests.get(url, headers=_HEADERS, timeout=_TIMEOUT, params={"limit": 30})
        resp.raise_for_status()
        data = resp.json()
    except Exception as exc:
        logger.debug("stocktwits: %s fetch failed: %s", ticker, exc)
        return {
            "ticker": ticker,
            "source": "stocktwits",
            "score": 0.0,
            "mention_count": 0,
            "sample_posts": [],
            "window_hours": hours_back,
        }

    messages = data.get("messages", [])
    scored: list[float] = []
    sample: list[str] = []
    seen = set()

    for msg in messages:
        msg_id = msg.get("id")
        if msg_id in seen:
            continue
        seen.add(msg_id)

        # Time filter
        created_raw = msg.get("created_at", "")
        if created_raw:
            try:
                created_dt = datetime.fromisoformat(created_raw.replace("Z", "+00:00"))
                if created_dt < cutoff:
                    continue
            except ValueError:
                pass

        # Sentiment from StockTwits label
        sentiment_obj = msg.get("entities", {}).get("sentiment")
        if sentiment_obj:
            label = sentiment_obj.get("basic", "")
            score = _SENTIMENT_MAP.get(label, 0.0)
        else:
            score = 0.0

        scored.append(score)
        body = msg.get("body", "")[:120]
        if body and len(sample) < 3:
            sample.append(body)

    if not scored:
        return {
            "ticker": ticker,
            "source": "stocktwits",
            "score": 0.0,
            "mention_count": 0,
            "sample_posts": sample,
            "window_hours": hours_back,
        }

    avg_score = round(sum(scored) / len(scored), 3)
    return {
        "ticker": ticker,
        "source": "stocktwits",
        "score": avg_score,
        "mention_count": len(scored),
        "sample_posts": sample,
        "window_hours": hours_back,
    }
