"""Dashboard API router.

Single endpoint: GET /dashboard/summary
Uses get_authed_db (RLS-scoped session) — same pattern as portfolio router.
_get_redis is a separate dependency so tests can override it independently.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.middleware import get_authed_db, get_current_tenant_id
from app.modules.dashboard.schemas import DashboardSummaryResponse
from app.modules.dashboard.service import DashboardService

router = APIRouter()


def _get_service() -> DashboardService:
    return DashboardService()


def _get_redis():
    """Dependency: async Redis client. Override in tests via dependency_overrides."""
    import redis.asyncio as aioredis
    from app.core.config import settings
    return aioredis.from_url(settings.REDIS_URL, decode_responses=False)


@router.get("/summary", response_model=DashboardSummaryResponse)
async def get_dashboard_summary(
    db: AsyncSession = Depends(get_authed_db),
    tenant_id: str = Depends(get_current_tenant_id),
    service: DashboardService = Depends(_get_service),
    redis=Depends(_get_redis),
) -> DashboardSummaryResponse:
    """Return consolidated portfolio summary for the authenticated tenant.

    Delegates to DashboardService which calls PortfolioService.get_pnl() once
    and MarketDataService for Redis reads. Never calls external market data APIs.

    Returns data_stale=True (not 500) when Redis cache is empty.
    All monetary values are Decimal serialized as strings by Pydantic v2.
    """
    return await service.get_summary(db, tenant_id, redis)
