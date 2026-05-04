"""Briefing Engine API router.

GET  /briefing/daily   — returns the latest cached daily report (or generates)
POST /briefing/generate — force-generate a new report (admin)
"""

import json
import logging
import os
from datetime import datetime, timezone, timedelta

from fastapi import APIRouter, Depends, Request
from fastapi import status as http_status

from app.core.limiter import limiter
from app.core.middleware import get_current_tenant_id

logger = logging.getLogger(__name__)

router = APIRouter()

_CACHE_KEY = "briefing_engine:latest"
_CACHE_TTL = 6 * 3600  # 6 hours


@router.get("/daily")
@limiter.limit("10/minute")
async def get_daily_briefing(
    request: Request,
    tenant_id: str = Depends(get_current_tenant_id),
) -> dict:
    """Return the latest daily briefing report."""
    import redis.asyncio as aioredis

    redis_url = os.environ.get("REDIS_URL", "redis://redis:6379/0")
    r = aioredis.from_url(redis_url, decode_responses=True)
    try:
        cached = await r.get(_CACHE_KEY)
        if cached:
            report = json.loads(cached)
            report["from_cache"] = True
            return report

        # Generate on demand
        from app.modules.briefing_engine.report import build_full_report
        report = await build_full_report(redis_client=r)

        await r.setex(_CACHE_KEY, _CACHE_TTL, json.dumps(report, default=str))
        report["from_cache"] = False
        return report
    finally:
        await r.aclose()


@router.post("/generate")
@limiter.limit("3/minute")
async def force_generate_briefing(
    request: Request,
    tenant_id: str = Depends(get_current_tenant_id),
) -> dict:
    """Force-generate a new briefing report (ignores cache)."""
    import redis.asyncio as aioredis

    redis_url = os.environ.get("REDIS_URL", "redis://redis:6379/0")
    r = aioredis.from_url(redis_url, decode_responses=True)
    try:
        from app.modules.briefing_engine.report import build_full_report
        report = await build_full_report(redis_client=r)
        await r.setex(_CACHE_KEY, _CACHE_TTL, json.dumps(report, default=str))
        return {**report, "from_cache": False}
    finally:
        await r.aclose()
