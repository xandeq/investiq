"""Binance public REST API adapter — no API key required.

Fetches 24h ticker stats for top crypto pairs (BTC, ETH, BNB, SOL).
Uses /api/v3/ticker/24hr endpoint which is public and rate-limit friendly.
"""
from __future__ import annotations

import logging
from typing import Any

import requests

logger = logging.getLogger(__name__)

_BASE = "https://api.binance.com/api/v3"
_TIMEOUT = 8

_SYMBOLS = ["BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT"]


def get_crypto_quotes() -> dict[str, Any]:
    """Return 24h stats for top crypto pairs.

    Returns dict keyed by symbol (e.g. "BTCUSDT") with:
      price, change_pct, volume_usd, high_24h, low_24h
    """
    results: dict[str, Any] = {}
    for symbol in _SYMBOLS:
        try:
            resp = requests.get(
                f"{_BASE}/ticker/24hr",
                params={"symbol": symbol},
                timeout=_TIMEOUT,
            )
            resp.raise_for_status()
            d = resp.json()
            results[symbol] = {
                "price": float(d["lastPrice"]),
                "change_pct": float(d["priceChangePercent"]),
                "volume_usd": float(d["quoteVolume"]),
                "high_24h": float(d["highPrice"]),
                "low_24h": float(d["lowPrice"]),
            }
        except Exception as exc:
            logger.warning("binance: failed to fetch %s: %s", symbol, exc)
            results[symbol] = None
    return results


def get_btc_price() -> float | None:
    """Quick BTC/USDT price fetch."""
    try:
        resp = requests.get(
            f"{_BASE}/ticker/price",
            params={"symbol": "BTCUSDT"},
            timeout=_TIMEOUT,
        )
        resp.raise_for_status()
        return float(resp.json()["price"])
    except Exception as exc:
        logger.warning("binance: BTC price fetch failed: %s", exc)
        return None
