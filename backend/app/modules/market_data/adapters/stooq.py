"""Stooq.com adapter — free global market data (no key required).

Fetches VIX, S&P 500, Nasdaq, and other indices via Stooq CSV API.
Stooq tickers: ^VIX (VIX), ^SPX (S&P500), ^NDX (Nasdaq100), ^BVSP (Ibovespa)
"""
from __future__ import annotations

import logging
from datetime import date, timedelta
from typing import Any

import requests

logger = logging.getLogger(__name__)

_BASE = "https://stooq.com/q/d/l/"
_TIMEOUT = 10


def _fetch(symbol: str) -> float | None:
    """Fetch the latest close price for a Stooq symbol."""
    today = date.today()
    # Request last 5 days to handle weekends/holidays
    start = (today - timedelta(days=5)).strftime("%Y%m%d")
    end = today.strftime("%Y%m%d")
    url = f"{_BASE}?s={symbol}&d1={start}&d2={end}&i=d"
    try:
        resp = requests.get(url, timeout=_TIMEOUT, headers={"User-Agent": "Mozilla/5.0"})
        resp.raise_for_status()
        lines = [ln for ln in resp.text.strip().splitlines() if ln and not ln.startswith("Date")]
        if not lines:
            return None
        last = lines[-1].split(",")
        if len(last) >= 5:
            close = last[4]  # Date,Open,High,Low,Close
            return float(close)
        return None
    except Exception as exc:
        logger.warning("stooq: failed to fetch %s: %s", symbol, exc)
        return None


def get_global_indices() -> dict[str, Any]:
    """Return latest values for VIX, S&P500, Nasdaq100, Ibovespa."""
    return {
        "vix": _fetch("^vix"),
        "sp500": _fetch("^spx"),
        "nasdaq": _fetch("^ndx"),
        "ibovespa": _fetch("^bvsp"),
    }
