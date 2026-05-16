"""Funds API router — CVM fund search and position endpoints."""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.middleware import get_authed_db, get_current_tenant_id
from app.modules.funds.schemas import FundInfoResponse, FundPosition, FundSearchResult
from app.modules.funds.service import FundsService

router = APIRouter()


def _get_service() -> FundsService:
    return FundsService()


def _get_redis():
    import redis.asyncio as aioredis
    from app.core.config import settings
    return aioredis.from_url(settings.REDIS_URL, decode_responses=False)


@router.get("/search", response_model=list[FundSearchResult])
async def search_funds(
    q: str = Query(..., min_length=2, description="Fund name fragment or CNPJ"),
    db: AsyncSession = Depends(get_authed_db),
    service: FundsService = Depends(_get_service),
) -> list[FundSearchResult]:
    """Search registered CVM funds by name or CNPJ.

    Returns up to 20 matching active funds.
    Requires fund_info table to be populated by the daily sync task.
    """
    return await service.search_funds(db, q)


@router.get("/positions", response_model=list[FundPosition])
async def get_fund_positions(
    db: AsyncSession = Depends(get_authed_db),
    tenant_id: str = Depends(get_current_tenant_id),
    service: FundsService = Depends(_get_service),
    redis=Depends(_get_redis),
) -> list[FundPosition]:
    """Return fund positions for the authenticated user with current NAV.

    NAV is fetched from Redis cache (populated by daily refresh task).
    Returns nav_stale=True when no quote is available.
    """
    return await service.get_fund_positions(db, tenant_id, redis)


@router.get("/info/{cnpj}", response_model=FundInfoResponse)
async def get_fund_info(
    cnpj: str,
    db: AsyncSession = Depends(get_authed_db),
    service: FundsService = Depends(_get_service),
) -> FundInfoResponse:
    """Return fund metadata for a given CNPJ (digits only or formatted)."""
    from fastapi import HTTPException
    fund = await service.get_fund_info(db, cnpj)
    if not fund:
        raise HTTPException(status_code=404, detail="Fund not found")
    return FundInfoResponse.model_validate(fund)
