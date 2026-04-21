"""Finnhub.io adapter — market news and earnings calendar.

Uses Finnhub free tier (no key required for general news, optional key for more).
Free endpoints:
  - GET /news?category=general — general market news
  - GET /calendar/earnings?from=&to= — earnings calendar (requires key)

With FINNHUB_API_KEY env var, enables earnings calendar.
Without key, only general news is fetched.
"""
from __future__ import annotations

import logging
import os
from datetime import date, datetime, timezone, timedelta
from typing import Any

import requests

logger = logging.getLogger(__name__)

_BASE = "https://finnhub.io/api/v1"
_TIMEOUT = 8


def _get_key() -> str:
    return os.environ.get("FINNHUB_API_KEY", "")


def get_market_news(category: str = "general", hours_back: int = 24) -> list[dict[str, Any]]:
    """Fetch market news from Finnhub (requires API key).

    category: 'general', 'forex', 'crypto', 'merger'
    Returns list of dicts: headline, summary, url, source, published_at, tickers
    Falls back to empty list if no key.
    """
    key = _get_key()
    if not key:
        logger.debug("finnhub: FINNHUB_API_KEY not set — skipping news")
        return []

    params: dict = {"category": category, "token": key}

    try:
        resp = requests.get(f"{_BASE}/news", params=params, timeout=_TIMEOUT)
        resp.raise_for_status()
        items = resp.json()

        cutoff = datetime.now(timezone.utc) - timedelta(hours=hours_back)
        results = []
        for item in items[:30]:
            ts = item.get("datetime", 0)
            pub = datetime.fromtimestamp(ts, tz=timezone.utc) if ts else None
            if pub and pub < cutoff:
                continue
            related = item.get("related", "")
            tickers = [t.strip() for t in related.split(",") if t.strip()] if related else []
            results.append({
                "headline": item.get("headline", ""),
                "summary": item.get("summary", ""),
                "url": item.get("url", ""),
                "source": item.get("source", "Finnhub"),
                "published_at": pub.isoformat() if pub else "",
                "tickers": tickers,
                "category": category,
            })
        return results
    except Exception as exc:
        logger.warning("finnhub: news fetch failed (category=%s): %s", category, exc)
        return []


def get_earnings_calendar(days_ahead: int = 7) -> list[dict[str, Any]]:
    """Fetch upcoming earnings calendar (requires FINNHUB_API_KEY).

    Returns list of: ticker, company, date, eps_estimate, revenue_estimate
    """
    key = _get_key()
    if not key:
        logger.debug("finnhub: FINNHUB_API_KEY not set — skipping earnings calendar")
        return []

    today = date.today()
    end = today + timedelta(days=days_ahead)
    params = {
        "from": today.strftime("%Y-%m-%d"),
        "to": end.strftime("%Y-%m-%d"),
        "token": key,
    }
    try:
        resp = requests.get(f"{_BASE}/calendar/earnings", params=params, timeout=_TIMEOUT)
        resp.raise_for_status()
        items = resp.json().get("earningsCalendar", [])
        return [
            {
                "ticker": i.get("symbol", ""),
                "company": i.get("symbol", ""),
                "date": i.get("date", ""),
                "eps_estimate": i.get("epsEstimate"),
                "revenue_estimate": i.get("revenueEstimate"),
            }
            for i in items[:20]
        ]
    except Exception as exc:
        logger.warning("finnhub: earnings calendar fetch failed: %s", exc)
        return []
