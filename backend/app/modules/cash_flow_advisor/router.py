"""Routes for Cash Parking Advisor."""

from __future__ import annotations

import logging
import os
from decimal import Decimal, InvalidOperation

import redis as redis_lib
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_global_db
from app.core.limiter import limiter
from app.core.security import get_current_user
from app.modules.cash_flow_advisor.client import DiaxClient, DiaxNotConfigured, DiaxUnreachable
from app.modules.cash_flow_advisor.schemas import CashParkingResponse
from app.modules.cash_flow_advisor.service import CashParkingService
from app.modules.comparador.service import _get_cdi_annual
from app.modules.market_universe.models import TaxConfig

logger = logging.getLogger(__name__)
router = APIRouter()


def _safe_decimal(value) -> Decimal | None:
    try:
        return Decimal(str(value)) if value is not None else None
    except (InvalidOperation, TypeError):
        return None


def _get_selic_annual() -> Decimal | None:
    try:
        redis_url = os.environ.get("REDIS_URL", "redis://localhost:6379/0")
        client = redis_lib.Redis.from_url(redis_url, decode_responses=True)
        return _safe_decimal(client.get("market:macro:selic"))
    except Exception as exc:
        logger.warning("_get_selic_annual: Redis error: %s", exc)
        return None


def _get_cash_parking_redis():
    try:
        import redis.asyncio as aioredis
        from app.core.config import settings

        return aioredis.from_url(settings.REDIS_URL, decode_responses=True)
    except Exception:
        return None


@limiter.limit("20/minute")
@router.get(
    "/cash-parking",
    response_model=CashParkingResponse,
    summary="Onde aplicar caixa parado usando DIAX cash-flow + IR/IOF",
    tags=["advisor"],
)
async def get_cash_parking(
    request: Request,
    _current_user: dict = Depends(get_current_user),
    global_db: AsyncSession = Depends(get_global_db),
    redis_client=Depends(_get_cash_parking_redis),
) -> CashParkingResponse:
    cdi = _get_cdi_annual()
    selic = _get_selic_annual()
    if not cdi or not selic:
        raise HTTPException(503, "Macro rates (CDI/Selic) unavailable in Redis")

    try:
        async with DiaxClient(redis_client=redis_client) as diax:
            projection = await diax.get_cash_flow_projection()
    except DiaxNotConfigured as exc:
        raise HTTPException(503, f"DIAX integration not configured: {exc}") from exc
    except DiaxUnreachable as exc:
        raise HTTPException(502, f"DIAX unreachable: {exc}") from exc

    tax_rows = (await global_db.execute(select(TaxConfig))).scalars().all()
    service = CashParkingService(
        cdi_annual_pct=cdi,
        selic_annual_pct=selic,
        tax_config_rows=tax_rows,
    )
    return await service.rank_options(projection)
