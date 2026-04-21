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


def _fetch_yahoo(symbol: str) -> float | None:
    """Fetch latest price from Yahoo Finance (primary source — works from VPS)."""
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}"
    try:
        resp = requests.get(
            url,
            params={"interval": "1d", "range": "5d"},
            timeout=_TIMEOUT,
            headers={"User-Agent": "Mozilla/5.0 (compatible; InvestIQ/1.0)"},
        )
        resp.raise_for_status()
        data = resp.json()
        closes = data["chart"]["result"][0]["indicators"]["quote"][0]["close"]
        # Last non-null close
        valid = [c for c in closes if c is not None]
        return float(valid[-1]) if valid else None
    except Exception as exc:
        logger.warning("yahoo: failed to fetch %s: %s", symbol, exc)
        return None


def _fetch(symbol: str) -> float | None:
    """Fetch the latest close price — tries Yahoo Finance first, then Stooq."""
    # Map Stooq symbols to Yahoo Finance equivalents
    _yahoo_map = {
        "^vix": "%5EVIX",
        "^spx": "%5EGSPC",
        "^ndx": "%5EIXIC",  # Nasdaq composite
        "^bvsp": "%5EBVSP",
        "cl.f": "CL=F",  # WTI crude oil futures
    }
    yahoo_sym = _yahoo_map.get(symbol.lower(), symbol)
    result = _fetch_yahoo(yahoo_sym)
    if result is not None:
        return result

    # Fallback: Stooq
    today = date.today()
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
            return float(last[4])
        return None
    except Exception as exc:
        logger.warning("stooq: failed to fetch %s: %s", symbol, exc)
        return None


def get_global_indices() -> dict[str, Any]:
    """Return latest values for VIX, S&P500, Nasdaq, Ibovespa."""
    return {
        "vix": _fetch("^vix"),
        "sp500": _fetch("^spx"),
        "nasdaq": _fetch("^ndx"),
        "ibovespa": _fetch("^bvsp"),
    }
