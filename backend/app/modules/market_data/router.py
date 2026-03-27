"""FastAPI router for market data endpoints.

All endpoints read from Redis via MarketDataService (never call external APIs).
The cache is populated by Celery tasks (tasks.py) on schedule.

Endpoints:
  GET /market-data/macro                  — current SELIC, CDI, IPCA, PTAX USD
  GET /market-data/fundamentals/{ticker}  — P/L, P/VP, DY, EV/EBITDA
  GET /market-data/historical/{ticker}    — 1-year OHLCV price history

All endpoints require authentication (get_authed_db ensures valid JWT cookie).
Data is tenant-agnostic (same market data for all users) but auth ensures
only registered users can access the data.

Cache miss behavior:
  If Redis is empty (data_stale=True), endpoints still return 200 with
  data_stale=True in the response body. The frontend displays a "data
  delayed" warning rather than an error. This avoids cascading failures
  if the Celery worker is temporarily down.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends

from app.core.middleware import get_authed_db
from app.modules.market_data.schemas import FundamentalsCache, HistoricalCache, MacroCache
from app.modules.market_data.service import MarketDataService

router = APIRouter()


def _get_market_service() -> MarketDataService:
    """Dependency: create MarketDataService with async Redis client.

    Uses redis.asyncio (bundled with the redis package ≥4.2).
    REDIS_URL is read from app settings (falls back to localhost:6379/0).
    """
    import redis.asyncio as aioredis

    from app.core.config import settings

    r = aioredis.from_url(settings.REDIS_URL, decode_responses=False)
    return MarketDataService(r)


@router.get("/macro", response_model=MacroCache)
async def get_macro(
    service: MarketDataService = Depends(_get_market_service),
    _authed_db=Depends(get_authed_db),
) -> MacroCache:
    """Return current Brazilian macro indicators from Redis cache.

    Response includes SELIC, CDI, IPCA and BRL/USD PTAX rate.
    If data_stale=True, the Celery worker has not yet populated the cache.
    """
    return await service.get_macro()


@router.get("/fundamentals/{ticker}", response_model=FundamentalsCache)
async def get_fundamentals(
    ticker: str,
    service: MarketDataService = Depends(_get_market_service),
    _authed_db=Depends(get_authed_db),
) -> FundamentalsCache:
    """Return fundamental analysis data for a B3 ticker from Redis cache.

    Returns P/L, P/VP, Dividend Yield and EV/EBITDA ratios.
    Values may be None if brapi.dev did not return them for this ticker.
    If data_stale=True, the cache has not been populated for this ticker.
    """
    return await service.get_fundamentals(ticker)


@router.get("/historical/{ticker}", response_model=HistoricalCache)
async def get_historical(
    ticker: str,
    service: MarketDataService = Depends(_get_market_service),
    _authed_db=Depends(get_authed_db),
) -> HistoricalCache:
    """Return 1-year OHLCV price history for a B3 ticker from Redis cache.

    Returns daily OHLCV data points as Unix epoch timestamps.
    If data_stale=True, the cache has not been populated for this ticker.
    """
    return await service.get_historical(ticker)
