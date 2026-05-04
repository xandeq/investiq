"""FastAPI router for /chart-analyzer endpoints."""

import logging
import os

import redis as redis_lib
from fastapi import APIRouter, Depends, HTTPException, Query, Request, status

from app.core.limiter import limiter
from app.core.security import get_current_user
from app.modules.chart_analyzer.analyzer import analyze

logger = logging.getLogger(__name__)

router = APIRouter()


def _get_sync_redis() -> redis_lib.Redis | None:
    """Return a sync Redis client for internal use, or None if not configured."""
    url = os.environ.get("REDIS_URL", "redis://redis:6379/0")
    try:
        return redis_lib.from_url(url, decode_responses=True)
    except Exception as exc:
        logger.warning("Could not connect to Redis: %s", exc)
        return None


@router.get("/{ticker}")
@limiter.limit("30/minute")
async def get_chart_analysis(
    request: Request,
    ticker: str,
    timeframe: str = Query(default="90d", description="Lookback window (currently only 90d supported)"),
    current_user: dict = Depends(get_current_user),
):
    """Analyze a B3 ticker and return technical setup, indicators, and levels.

    - **ticker**: B3 symbol (e.g. BBSE3, PETR4)
    - **timeframe**: Lookback window (default: 90d)

    Returns full analysis JSON with setup entry/stop/target, indicators, and support/resistance levels.
    """
    if not ticker or len(ticker) > 10:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid ticker")

    brapi_token = os.environ.get("BRAPI_TOKEN", "")

    # Use async redis if available
    redis_client = None
    try:
        import redis.asyncio as aioredis
        redis_url = os.environ.get("REDIS_URL", "redis://redis:6379/0")
        redis_client = aioredis.from_url(redis_url, decode_responses=True)
    except Exception:
        pass

    result = await analyze(ticker.upper(), brapi_token=brapi_token, redis_client=redis_client)

    if redis_client is not None:
        try:
            await redis_client.aclose()
        except Exception:
            pass

    if result.get("error") and not result.get("indicators"):
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Failed to analyze {ticker}: {result['error']}",
        )

    return result
