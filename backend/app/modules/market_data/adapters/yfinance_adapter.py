"""yfinance fallback adapter for historical OHLCV data.

Used when brapi.dev historical data is unavailable or stale.
B3 (Brazilian) tickers require the .SA suffix for Yahoo Finance
(e.g., PETR4 → PETR4.SA, BOVA11 → BOVA11.SA).

Returns the same OHLCV dict format as brapi.py:
  [{"date": int_epoch, "open": float, "high": float,
    "low": float, "close": float, "volume": int}]

Index tickers (e.g., ^BVSP) are passed through without .SA suffix.
"""
from __future__ import annotations

import logging

logger = logging.getLogger(__name__)

_B3_SUFFIX = ".SA"
_INDEX_PREFIXES = ("^",)


def _to_yf_ticker(ticker: str) -> str:
    """Convert B3 ticker to Yahoo Finance format.

    Index tickers (starting with ^) are left unchanged.
    Regular B3 tickers get .SA appended if not already present.
    """
    upper = ticker.upper()
    if any(upper.startswith(p) for p in _INDEX_PREFIXES):
        return upper
    if upper.endswith(_B3_SUFFIX):
        return upper
    return upper + _B3_SUFFIX


def fetch_historical_fallback(ticker: str, period: str = "1y") -> list[dict]:
    """Fetch historical OHLCV data from Yahoo Finance for a B3 ticker.

    Args:
        ticker: B3 ticker symbol (e.g., "PETR4", "BOVA11").
                .SA suffix is added automatically.
        period:  yfinance period string (default "1y").
                 Options: "1d", "5d", "1mo", "3mo", "6mo", "1y", "2y", "5y", "max"

    Returns:
        List of OHLCV dicts compatible with brapi.py output:
          [{"date": int_epoch, "open": float, "high": float,
            "low": float, "close": float, "volume": int}]
        Returns empty list on error.
    """
    # ^BVSP (IBOVESPA) is blocked by Yahoo Finance from Brazilian IPs — use brapi instead.
    if ticker.upper() in ("^BVSP", "BVSP"):
        try:
            from app.modules.market_data.adapters.brapi import BrapiClient
            logger.info("yfinance_adapter: routing ^BVSP to brapi.dev (Yahoo Finance blocks BR IPs)")
            return BrapiClient().fetch_historical("^BVSP", range=period if period in ("1y", "2y", "5y") else "1y")
        except Exception as exc:
            logger.error("brapi ^BVSP fallback failed: %s", exc)
            return []

    import yfinance as yf

    yf_ticker = _to_yf_ticker(ticker)
    logger.info("yfinance fallback: fetching %s (mapped from %s)", yf_ticker, ticker)

    try:
        hist = yf.Ticker(yf_ticker).history(period=period, interval="1d")
    except Exception as exc:  # noqa: BLE001
        logger.error("yfinance fetch failed for %s: %s", yf_ticker, exc)
        return []

    if hist.empty:
        logger.warning("yfinance returned empty history for %s", yf_ticker)
        return []

    points: list[dict] = []
    for ts, row in hist.iterrows():
        # Convert pandas Timestamp to Unix epoch (integer seconds)
        epoch = int(ts.timestamp())
        points.append(
            {
                "date": epoch,
                "open": float(row.get("Open", 0.0)),
                "high": float(row.get("High", 0.0)),
                "low": float(row.get("Low", 0.0)),
                "close": float(row.get("Close", 0.0)),
                "volume": int(row.get("Volume", 0)),
            }
        )

    return points
