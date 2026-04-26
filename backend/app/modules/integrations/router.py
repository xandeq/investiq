"""Integration API — server-to-server endpoints for external systems.

Authentication: static X-Integration-Key header (no user JWT).
Currently supports one tenant per key (configured via INTEGRATION_TENANT_ID).

Endpoint:
  GET /integrations/portfolio-summary — aggregated portfolio snapshot for DIAX CRM
"""
from __future__ import annotations

from datetime import datetime, timezone, timedelta
from decimal import Decimal

from fastapi import APIRouter, Header, HTTPException, status
from pydantic import BaseModel

from app.core.config import settings
from app.core.db import get_tenant_db
from app.modules.portfolio.service import PortfolioService

router = APIRouter()


def _require_integration_key(x_integration_key: str = Header(...)) -> None:
    """Dependency: validate X-Integration-Key header."""
    if not settings.INTEGRATION_KEY:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Integration not configured",
        )
    if x_integration_key != settings.INTEGRATION_KEY:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid integration key",
        )


class AllocationItem(BaseModel):
    asset_class: str
    total_value: float
    percentage: float


class PortfolioSummaryResponse(BaseModel):
    portfolio_value: float
    total_invested: float
    unrealized_pnl: float
    realized_pnl: float
    total_return_pct: float | None
    monthly_dividends: float
    position_count: int
    asset_allocation: list[AllocationItem]
    cached_at: str


@router.get(
    "/portfolio-summary",
    response_model=PortfolioSummaryResponse,
    summary="Portfolio summary for external integrations",
)
async def get_portfolio_summary(
    x_integration_key: str = Header(...),
) -> PortfolioSummaryResponse:
    """Return aggregated portfolio snapshot.

    Requires X-Integration-Key header. No user JWT needed.
    Uses Redis for current prices when available; falls back to CMP.
    """
    _require_integration_key(x_integration_key)

    tenant_id = settings.INTEGRATION_TENANT_ID
    if not tenant_id:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Integration tenant not configured",
        )

    service = PortfolioService()

    # Try to get Redis client for live prices
    redis_client = None
    try:
        import redis.asyncio as aioredis
        redis_client = aioredis.from_url(settings.REDIS_URL, decode_responses=False)
    except Exception:
        pass  # proceed without live prices

    async for db in get_tenant_db(tenant_id):
        pnl = await service.get_pnl(db, tenant_id, redis_client)

        # Monthly dividends: sum dividend transactions from last 30 days
        monthly_dividends = Decimal("0")
        from datetime import date
        cutoff = datetime.now(tz=timezone.utc) - timedelta(days=30)
        dividends = await service.get_dividends(db, tenant_id)
        for div in dividends:
            div_date = div.transaction_date
            if hasattr(div_date, 'tzinfo') and div_date.tzinfo is None:
                from datetime import timezone as _tz
                div_date = div_date.replace(tzinfo=_tz.utc)
            elif not hasattr(div_date, 'tzinfo'):
                pass
            try:
                if div_date >= cutoff:
                    monthly_dividends += Decimal(str(div.total_value))
            except Exception:
                pass

        return PortfolioSummaryResponse(
            portfolio_value=float(pnl.total_portfolio_value),
            total_invested=float(pnl.total_invested),
            unrealized_pnl=float(pnl.unrealized_pnl_total),
            realized_pnl=float(pnl.realized_pnl_total),
            total_return_pct=float(pnl.total_return_pct) if pnl.total_return_pct is not None else None,
            monthly_dividends=float(monthly_dividends),
            position_count=len(pnl.positions),
            asset_allocation=[
                AllocationItem(
                    asset_class=a.asset_class,
                    total_value=float(a.total_value),
                    percentage=float(a.percentage),
                )
                for a in sorted(pnl.allocation, key=lambda x: x.total_value, reverse=True)
            ],
            cached_at=datetime.now(tz=timezone.utc).isoformat(),
        )
