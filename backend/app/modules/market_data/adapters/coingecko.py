"""CoinGecko free API adapter for crypto prices in BRL."""
from __future__ import annotations

import logging

import requests

logger = logging.getLogger(__name__)

_BASE_URL = "https://api.coingecko.com/api/v3"

CRYPTO_IDS = {
    "BTC": "bitcoin",
    "ETH": "ethereum",
    "SOL": "solana",
    "BNB": "binancecoin",
    "MATIC": "matic-network",
    "XRP": "ripple",
    "ADA": "cardano",
    "DOT": "polkadot",
}

# Reverse map: coingecko_id -> ticker
_ID_TO_TICKER: dict[str, str] = {v: k for k, v in CRYPTO_IDS.items()}


def get_crypto_prices_brl() -> dict[str, dict]:
    """Fetch BRL prices for all mapped crypto tickers from CoinGecko free API.

    Returns dict keyed by ticker (e.g. "BTC") with keys:
      - price_brl (float)
      - change_24h_pct (float | None)
    Returns partial results on per-coin errors.
    """
    ids_csv = ",".join(CRYPTO_IDS.values())
    try:
        resp = requests.get(
            f"{_BASE_URL}/simple/price",
            params={
                "ids": ids_csv,
                "vs_currencies": "brl",
                "include_24hr_change": "true",
            },
            timeout=10,
        )
        resp.raise_for_status()
        raw: dict = resp.json()
    except Exception as exc:
        logger.warning("coingecko: request failed — %s", exc)
        return {}

    result: dict[str, dict] = {}
    for coin_id, ticker in _ID_TO_TICKER.items():
        coin_data = raw.get(coin_id)
        if not coin_data:
            logger.warning("coingecko: no data for %s (%s)", ticker, coin_id)
            continue
        try:
            price_brl = float(coin_data["brl"])
            change_24h_pct: float | None = (
                float(coin_data["brl_24h_change"])
                if coin_data.get("brl_24h_change") is not None
                else None
            )
            result[ticker] = {"price_brl": price_brl, "change_24h_pct": change_24h_pct}
        except (KeyError, TypeError, ValueError) as exc:
            logger.warning("coingecko: parse error for %s — %s", ticker, exc)

    return result
