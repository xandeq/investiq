"""MarketDataService — Redis read layer for all user-facing market data.

Architecture:
  - All user API requests read from Redis (never call external APIs directly)
  - Celery tasks (tasks.py) populate Redis on schedule via brapi.dev and BCB
  - Cache-aside pattern: if key is missing, return data with data_stale=True
  - All reads are async (redis.asyncio / aioredis compatible)

Redis key schema:
  market:quote:{TICKER}          — QuoteCache JSON
  market:macro:selic             — Decimal string
  market:macro:cdi               — Decimal string
  market:macro:ipca              — Decimal string
  market:macro:ptax_usd          — Decimal string
  market:macro:fetched_at        — ISO timestamp string
  market:fundamentals:{TICKER}   — FundamentalsCache JSON
  market:historical:{TICKER}     — HistoricalCache JSON

Stale data policy:
  When a Redis key returns None (cache miss), the service returns the
  appropriate Cache schema with data_stale=True and fetched_at=datetime.min.
  The caller (router/frontend) should surface this to the user.
"""
from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from decimal import Decimal

from pydantic import ValidationError

from app.modules.market_data.schemas import (
    FundamentalsCache,
    HistoricalCache,
    MacroCache,
    QuoteCache,
)

logger = logging.getLogger(__name__)

# Sentinel for missing cache data
_EPOCH_MIN = datetime.min


class MarketDataService:
    """Redis-backed read service for market data.

    Args:
        redis_client: async Redis client (redis.asyncio.Redis or compatible)
    """

    def __init__(self, redis_client) -> None:
        self.redis = redis_client

    async def get_quote(self, ticker: str) -> QuoteCache:
        """Read B3 quote from Redis cache.

        Returns QuoteCache with data_stale=True when cache key is missing.
        """
        key = f"market:quote:{ticker.upper()}"
        raw = await self.redis.get(key)
        if raw is None:
            logger.debug("Cache miss for %s — returning stale placeholder", key)
            return QuoteCache(
                symbol=ticker.upper(),
                price=Decimal("0"),
                change=Decimal("0"),
                change_pct=Decimal("0"),
                fetched_at=_EPOCH_MIN,
                data_stale=True,
            )
        try:
            return QuoteCache.model_validate_json(raw)
        except ValidationError:
            payload = json.loads(raw)
            if not isinstance(payload, dict):
                raise

            fetched_at_raw = payload.get("fetched_at")
            try:
                fetched_at = (
                    datetime.fromisoformat(str(fetched_at_raw))
                    if fetched_at_raw
                    else _EPOCH_MIN
                )
            except ValueError:
                fetched_at = _EPOCH_MIN

            return QuoteCache(
                symbol=ticker.upper(),
                price=Decimal(str(payload.get("price", payload.get("regularMarketPrice", 0)))),
                change=Decimal(str(payload.get("change", payload.get("regularMarketChange", 0)))),
                change_pct=Decimal(str(payload.get("change_pct", payload.get("regularMarketChangePercent", 0)))),
                fetched_at=fetched_at,
                data_stale=bool(payload.get("data_stale", False)),
            )

    async def get_macro(self) -> MacroCache:
        """Read macro indicators from Redis cache.

        Individual indicators are stored as separate keys and assembled
        into a MacroCache response. Returns data_stale=True if any key is missing.
        """
        keys = ["selic", "cdi", "ipca", "ptax_usd", "fetched_at"]
        values: dict[str, bytes | None] = {}

        for k in keys:
            values[k] = await self.redis.get(f"market:macro:{k}")

        # If any core indicator is missing, mark as stale
        core_keys = ["selic", "cdi", "ipca", "ptax_usd"]
        is_stale = any(values[k] is None for k in core_keys)

        if is_stale:
            logger.debug("Cache miss for macro indicators — returning stale placeholder")
            return MacroCache(
                selic=Decimal("0"),
                cdi=Decimal("0"),
                ipca=Decimal("0"),
                ptax_usd=Decimal("0"),
                fetched_at=_EPOCH_MIN,
                data_stale=True,
            )

        def _to_decimal(raw: bytes | str | None) -> Decimal:
            if raw is None:
                return Decimal("0")
            s = raw.decode() if isinstance(raw, bytes) else raw
            return Decimal(s)

        fetched_at_raw = values["fetched_at"]
        fetched_at: datetime
        if fetched_at_raw:
            try:
                s = fetched_at_raw.decode() if isinstance(fetched_at_raw, bytes) else fetched_at_raw
                fetched_at = datetime.fromisoformat(s)
            except ValueError:
                fetched_at = _EPOCH_MIN
        else:
            fetched_at = _EPOCH_MIN

        return MacroCache(
            selic=_to_decimal(values["selic"]),
            cdi=_to_decimal(values["cdi"]),
            ipca=_to_decimal(values["ipca"]),
            ptax_usd=_to_decimal(values["ptax_usd"]),
            fetched_at=fetched_at,
            data_stale=False,
        )

    async def get_fundamentals(self, ticker: str) -> FundamentalsCache:
        """Read fundamental analysis data from Redis cache.

        Returns FundamentalsCache with data_stale=True when cache key is missing.
        """
        key = f"market:fundamentals:{ticker.upper()}"
        raw = await self.redis.get(key)
        if raw is None:
            logger.debug("Cache miss for %s — returning stale placeholder", key)
            return FundamentalsCache(
                ticker=ticker.upper(),
                fetched_at=_EPOCH_MIN,
                data_stale=True,
            )
        return FundamentalsCache.model_validate_json(raw)

    async def get_quotes_batch(self, tickers: list[str]) -> dict[str, QuoteCache]:
        """Batch-read B3 quotes from Redis using a single MGET round-trip.

        Returns a dict {ticker: QuoteCache}. Tickers with cache miss get
        QuoteCache(data_stale=True). O(1) Redis round-trips regardless of N.
        """
        if not tickers:
            return {}
        upper = [t.upper() for t in tickers]
        keys = [f"market:quote:{t}" for t in upper]
        raw_values = await self.redis.mget(keys)

        result: dict[str, QuoteCache] = {}
        for ticker, raw in zip(upper, raw_values):
            if raw is None:
                result[ticker] = QuoteCache(
                    symbol=ticker,
                    price=Decimal("0"),
                    change=Decimal("0"),
                    change_pct=Decimal("0"),
                    fetched_at=_EPOCH_MIN,
                    data_stale=True,
                )
            else:
                try:
                    result[ticker] = QuoteCache.model_validate_json(raw)
                except Exception:
                    try:
                        payload = json.loads(raw)
                        result[ticker] = QuoteCache(
                            symbol=ticker,
                            price=Decimal(str(payload.get("price", payload.get("regularMarketPrice", 0)))),
                            change=Decimal(str(payload.get("change", payload.get("regularMarketChange", 0)))),
                            change_pct=Decimal(str(payload.get("change_pct", payload.get("regularMarketChangePercent", 0)))),
                            fetched_at=_EPOCH_MIN,
                            data_stale=bool(payload.get("data_stale", False)),
                        )
                    except Exception:
                        result[ticker] = QuoteCache(
                            symbol=ticker,
                            price=Decimal("0"),
                            change=Decimal("0"),
                            change_pct=Decimal("0"),
                            fetched_at=_EPOCH_MIN,
                            data_stale=True,
                        )
        return result

    async def get_fundamentals_batch(self, tickers: list[str]) -> dict[str, FundamentalsCache]:
        """Batch-read fundamentals from Redis using a single MGET round-trip.

        Returns a dict {ticker: FundamentalsCache}. O(1) Redis round-trips.
        """
        if not tickers:
            return {}
        upper = [t.upper() for t in tickers]
        keys = [f"market:fundamentals:{t}" for t in upper]
        raw_values = await self.redis.mget(keys)

        result: dict[str, FundamentalsCache] = {}
        for ticker, raw in zip(upper, raw_values):
            if raw is None:
                result[ticker] = FundamentalsCache(ticker=ticker, fetched_at=_EPOCH_MIN, data_stale=True)
            else:
                try:
                    result[ticker] = FundamentalsCache.model_validate_json(raw)
                except Exception:
                    result[ticker] = FundamentalsCache(ticker=ticker, fetched_at=_EPOCH_MIN, data_stale=True)
        return result

    async def get_historical(self, ticker: str) -> HistoricalCache:
        """Read historical OHLCV data from Redis cache.

        Returns HistoricalCache with data_stale=True when cache key is missing.
        """
        key = f"market:historical:{ticker.upper()}"
        raw = await self.redis.get(key)
        if raw is None:
            logger.debug("Cache miss for %s — returning stale placeholder", key)
            return HistoricalCache(
                ticker=ticker.upper(),
                points=[],
                fetched_at=_EPOCH_MIN,
                data_stale=True,
            )
        return HistoricalCache.model_validate_json(raw)
