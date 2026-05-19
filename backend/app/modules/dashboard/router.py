"""Dashboard API router.

Endpoints:
  GET /dashboard/summary                — consolidated portfolio summary (P&L, allocation, timeseries)
  GET /dashboard/portfolio-history      — EOD portfolio value history for historical chart
  GET /dashboard/monthly-performance    — month-by-month return % heatmap data

Uses get_authed_db (RLS-scoped session) — same pattern as portfolio router.
_get_redis is a separate dependency so tests can override it independently.
"""

from datetime import date, timedelta

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.middleware import get_authed_db, get_current_tenant_id
from app.modules.dashboard.schemas import (
    DashboardSummaryResponse,
    RiskMetricsResponse,
    SectorAllocationResponse,
    DividendCalendarResponse,
    DividendRankingResponse,
)
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
    range: str = Query("3m", pattern="^(1m|3m|6m|1y|all)$"),
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


@router.get("/monthly-performance")
async def get_monthly_performance(
    years: int = Query(3, ge=1, le=5),
    db: AsyncSession = Depends(get_authed_db),
    tenant_id: str = Depends(get_current_tenant_id),
) -> dict:
    """Return month-by-month portfolio return percentages for a heatmap.

    Response:
      {
        "months": [
          {"year": 2026, "month": 1, "return_pct": 3.45, "start_value": "14000.00", "end_value": "14482.00"},
          ...
        ]
      }

    Each month's return is computed from the first and last data point in that
    calendar month. Months with fewer than 2 data points are skipped (insufficient data).
    """
    since = date.today().replace(day=1) - timedelta(days=365 * years)

    result = await db.execute(
        text(
            "SELECT snapshot_date, total_value "
            "FROM portfolio_daily_value "
            "WHERE tenant_id = :tid AND snapshot_date >= :since "
            "ORDER BY snapshot_date ASC"
        ),
        {"tid": tenant_id, "since": since},
    )
    rows = result.fetchall()

    # Group by (year, month)
    from collections import defaultdict
    monthly: dict[tuple[int, int], list[tuple]] = defaultdict(list)
    for snap_date, total_value in rows:
        monthly[(snap_date.year, snap_date.month)].append((snap_date, float(total_value)))

    months_out = []
    for (year, month), points in sorted(monthly.items()):
        if len(points) < 2:
            continue
        start_val = points[0][1]
        end_val = points[-1][1]
        if start_val <= 0:
            continue
        ret_pct = round(((end_val - start_val) / start_val) * 100, 2)
        months_out.append(
            {
                "year": year,
                "month": month,
                "return_pct": ret_pct,
                "start_value": f"{start_val:.2f}",
                "end_value": f"{end_val:.2f}",
            }
        )

    return {"months": months_out}


@router.get("/risk-metrics", response_model=RiskMetricsResponse)
async def get_risk_metrics(
    db: AsyncSession = Depends(get_authed_db),
    tenant_id: str = Depends(get_current_tenant_id),
    service: DashboardService = Depends(_get_service),
    redis=Depends(_get_redis),
) -> RiskMetricsResponse:
    """Return annualised risk metrics + Sharpe ratio from the last 252 trading days.

    Fields:
      - volatility_annual_pct: annualised std dev of daily returns × 100
      - max_drawdown_pct: maximum peak-to-trough decline × 100
      - positive_days_pct: proportion of days with positive return × 100
      - annual_return_pct: annualised portfolio return over the window
      - sharpe_ratio: (annual_return - CDI) / volatility  (null if < 10 days)
      - trading_days: number of data points used
      - data_available: False when fewer than 5 days of history exist
    """
    return await service.get_risk_metrics(db, tenant_id, redis_client=redis)


@router.get("/dividend-ranking", response_model=DividendRankingResponse)
async def get_dividend_ranking(
    db: AsyncSession = Depends(get_authed_db),
    tenant_id: str = Depends(get_current_tenant_id),
    service: DashboardService = Depends(_get_service),
) -> DividendRankingResponse:
    """Return portfolio holdings ranked by trailing dividend yield (DY).

    Uses screener_snapshots.dy (last available snapshot) and current
    position quantities. Returns empty when no holdings have DY data.
    Fields per item: ticker, dy_pct, position_value, estimated_annual, sector.
    """
    return await service.get_dividend_ranking(db, tenant_id)


@router.get("/sector-allocation", response_model=SectorAllocationResponse)
async def get_sector_allocation(
    db: AsyncSession = Depends(get_authed_db),
    tenant_id: str = Depends(get_current_tenant_id),
    service: DashboardService = Depends(_get_service),
) -> SectorAllocationResponse:
    """Return portfolio value broken down by sector/segmento.

    Sector label priority per ticker:
      1. screener_snapshots.sector (latest snapshot)
      2. fii_metadata.segmento
      3. transactions.asset_class (fallback)

    Price used for valuation: screener_snapshots.regular_market_price
    (latest available snapshot date). Tickers absent from screener are
    valued at 0 and excluded from the percentage calculation.

    No Redis dependency — DB-only query.
    """
    return await service.get_sector_allocation(db, tenant_id)


@router.get("/dividend-calendar", response_model=DividendCalendarResponse)
async def get_dividend_calendar(
    db: AsyncSession = Depends(get_authed_db),
    tenant_id: str = Depends(get_current_tenant_id),
    service: DashboardService = Depends(_get_service),
) -> DividendCalendarResponse:
    """Upcoming dividend payments for the user's portfolio (next 90 days).
    Fetches dividend data from brapi.dev and merges with user's holdings.
    Returns empty list gracefully if brapi is unavailable.
    """
    return await service.get_dividend_calendar(db, tenant_id)
