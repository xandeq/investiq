"""Celery task to refresh crypto prices from CoinGecko into Redis."""
from __future__ import annotations

import json
import logging
import os

import redis as redis_lib
from celery import shared_task

from app.modules.market_data.adapters.coingecko import get_crypto_prices_brl

logger = logging.getLogger(__name__)

# 6 minutes — crypto prices change frequently
_CRYPTO_TTL = 360


def _get_redis() -> redis_lib.Redis:
    """Create a synchronous Redis client for Celery task use."""
    url = os.environ.get("REDIS_URL", "redis://localhost:6379/0")
    return redis_lib.Redis.from_url(url)


@shared_task(name="app.modules.market_data.crypto_tasks.refresh_crypto_quotes")
def refresh_crypto_quotes() -> None:
    """Fetch crypto prices from CoinGecko and write to Redis as market:quote:{TICKER}."""
    prices = get_crypto_prices_brl()
    if not prices:
        logger.warning("refresh_crypto_quotes: no prices returned from CoinGecko")
        return

    r = _get_redis()
    updated = 0
    for ticker, data in prices.items():
        price = data.get("price_brl")
        if price is None:
            continue
        change_24h_pct = data.get("change_24h_pct")
        change_brl = price * (change_24h_pct / 100) if change_24h_pct is not None else 0.0
        cache_entry = {
            "price": price,
            "change": change_brl,
            "regularMarketPrice": price,
            "data_stale": False,
            "ticker": ticker,
        }
        key = f"market:quote:{ticker}"
        r.set(key, json.dumps(cache_entry), ex=_CRYPTO_TTL)
        updated += 1

    logger.info("refresh_crypto_quotes: %d prices updated", updated)
