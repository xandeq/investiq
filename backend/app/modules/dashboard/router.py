"""Dashboard API router.

Endpoints:
  GET /dashboard/summary           — consolidated portfolio summary (P&L, allocation, timeseries)
  GET /dashboard/portfolio-history — EOD portfolio value history for historical chart

Uses get_authed_db (RLS-scoped session) — same pattern as portfolio router.
_get_redis is a separate dependency so tests can override it independently.
"""

from datetime import date, timedelta

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, text
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


_RANGE_DAYS = {"1m": 30, "3m": 90, "6m": 180, "1y": 365, "all": 0}


@router.get("/portfolio-history")
async def get_portfolio_history(
    range: str = Query("3m", regex="^(1m|3m|6m|1y|all)$"),
    db: AsyncSession = Depends(get_authed_db),
    tenant_id: str = Depends(get_current_tenant_id),
) -> dict:
    """Return historical EOD portfolio value for charting.

    Response:
      {
        "range": "3m",
        "points": [{"date": "2026-01-15", "total_value": "15000.00", "total_invested": "12000.00"}, ...]
      }

    Data comes from portfolio_daily_value (populated nightly by Celery at 18h30 BRT).
    Returns empty points array for new users (table builds up over time).
    """
    days = _RANGE_DAYS.get(range, 90)
    since = date.today() - timedelta(days=days) if days > 0 else date(2020, 1, 1)

    result = await db.execute(
        text(
            "SELECT snapshot_date, total_value, total_invested "
            "FROM portfolio_daily_value "
            "WHERE tenant_id = :tid AND snapshot_date >= :since "
            "ORDER BY snapshot_date ASC"
        ),
        {"tid": tenant_id, "since": since},
    )
    rows = result.fetchall()

    points = [
        {
            "date": str(r[0]),
            "total_value": str(r[1]),
            "total_invested": str(r[2]),
        }
        for r in rows
    ]
    return {"range": range, "points": points}
