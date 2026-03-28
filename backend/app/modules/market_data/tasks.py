"""Celery tasks for scheduled market data refresh.

Tasks run on Celery workers (sync context, psycopg2 driver) and write
to Redis. They NEVER handle API requests — they only populate the cache.

Schedule (defined in celery_app.py beat_schedule):
  - refresh_quotes: every 15 min, Mon-Fri, 10h-17h BRT
  - refresh_macro:  every 6 hours

Redis key schema:
  market:quote:{TICKER}    — ex=1200 (20 min)
  market:macro:{indicator} — ex=25200 (7h)
  market:quote:IBOV        — ex=1200

Default ticker list:
  Phase 2 uses a hardcoded seed list. In production (Phase 3+), the task
  should query the DB for all tickers in active portfolios.
  The IBOVESPA index (^BVSP) is always refreshed as it is used for
  benchmark comparisons.

Error handling:
  Tasks use bind=True + max_retries=3. On exception, self.retry() is called.
  This ensures transient failures (network, rate limits) don't cause
  permanent data gaps.
"""
from __future__ import annotations

import json
import logging
import os

import redis as redis_lib
import requests as requests_lib

from app.celery_app import celery_app
from app.modules.market_data.adapters.bcb import fetch_macro_indicators
from app.modules.market_data.adapters.brapi import BrapiClient

logger = logging.getLogger(__name__)

# Default tickers to refresh every 15 minutes during market hours.
# Phase 3+: replace with DB query for all tickers in active portfolios.
DEFAULT_TICKERS = [
    "PETR4",
    "VALE3",
    "ITUB4",
    "BBDC4",
    "WEGE3",
    "MGLU3",
    "ABEV3",
    "BOVA11",
]

# Redis TTLs (in seconds)
_QUOTE_TTL = 1200        # 20 min — slightly longer than 15-min refresh interval
_MACRO_TTL = 25200       # 7h — longer than 6h refresh interval
_FUNDAMENTALS_TTL = 14400  # 4h — fundamentals change rarely


def _get_redis() -> redis_lib.Redis:
    """Create a synchronous Redis client for Celery task use."""
    url = os.environ.get("REDIS_URL", "redis://localhost:6379/0")
    return redis_lib.Redis.from_url(url)


@celery_app.task(bind=True, max_retries=3, default_retry_delay=60)
def refresh_quotes(self) -> None:
    """Fetch B3 quotes from brapi.dev and write to Redis cache.

    Fetches all DEFAULT_TICKERS plus IBOVESPA index.
    Each quote is written with TTL=1200 (20 min).
    On failure, retries up to 3 times with 60s delay.
    """
    r = _get_redis()
    client = BrapiClient()

    try:
        logger.info("refresh_quotes: fetching %d tickers", len(DEFAULT_TICKERS))
        quotes = client.fetch_quotes(DEFAULT_TICKERS)

        for q in quotes:
            ticker = q.get("symbol", "")
            if not ticker:
                continue
            key = f"market:quote:{ticker.upper()}"
            r.set(key, json.dumps(q), ex=_QUOTE_TTL)
            logger.debug("Wrote %s to Redis (TTL=%d)", key, _QUOTE_TTL)

        logger.info("refresh_quotes: wrote %d quotes to Redis", len(quotes))

        # Populate fundamentals cache for each ticker (used by AI analysis tasks)
        for ticker in DEFAULT_TICKERS:
            try:
                fund = client.fetch_fundamentals(ticker)
                key = f"market:fundamentals:{ticker.upper()}"
                r.set(key, json.dumps(fund), ex=_FUNDAMENTALS_TTL)
                logger.debug("Wrote %s to Redis (TTL=%d)", key, _FUNDAMENTALS_TTL)
            except Exception as fund_exc:
                logger.warning("refresh_quotes: fundamentals skipped for %s — %s", ticker, fund_exc)
        logger.info("refresh_quotes: fundamentals refreshed for %d tickers", len(DEFAULT_TICKERS))

        # Also fetch IBOVESPA index — may fail on unauthenticated free tier
        try:
            ibov = client.fetch_ibovespa()
            r.set("market:quote:IBOV", json.dumps(ibov), ex=_QUOTE_TTL)
            logger.info("refresh_quotes: wrote IBOV to Redis")
        except Exception as ibov_exc:
            logger.warning("refresh_quotes: IBOV fetch skipped (%s) — stock quotes still written", ibov_exc)

    except requests_lib.exceptions.HTTPError as exc:
        if exc.response is not None and exc.response.status_code in (401, 403):
            logger.warning("refresh_quotes: auth error %s — BRAPI_TOKEN not set or invalid. Skipping retry.", exc.response.status_code)
            return
        logger.error("refresh_quotes failed: %s", exc)
        raise self.retry(exc=exc)
    except Exception as exc:
        logger.error("refresh_quotes failed: %s", exc)
        raise self.retry(exc=exc)


@celery_app.task(bind=True, max_retries=3, default_retry_delay=300)
def refresh_macro(self) -> None:
    """Fetch macro indicators from BCB and write to Redis cache.

    Writes individual indicators as separate keys with TTL=25200 (7h).
    Keys written: market:macro:selic, :cdi, :ipca, :ptax_usd, :fetched_at
    On failure, retries up to 3 times with 5min delay.
    """
    r = _get_redis()

    try:
        logger.info("refresh_macro: fetching BCB macro indicators")
        macro = fetch_macro_indicators()

        for key_suffix, value in macro.items():
            redis_key = f"market:macro:{key_suffix}"
            r.set(redis_key, str(value), ex=_MACRO_TTL)
            logger.debug("Wrote %s to Redis (TTL=%d)", redis_key, _MACRO_TTL)

        logger.info(
            "refresh_macro: wrote SELIC=%.4f CDI=%.4f IPCA=%.4f PTAX=%.4f",
            float(macro["selic"]),
            float(macro["cdi"]),
            float(macro["ipca"]),
            float(macro["ptax_usd"]),
        )

    except Exception as exc:
        logger.error("refresh_macro failed: %s", exc)
        raise self.retry(exc=exc)
