"""Swing Trade router (Phase 20).

Endpoints:
  GET    /swing-trade/signals                       — portfolio + radar signals
  GET    /swing-trade/operations                    — list user's operations
  POST   /swing-trade/operations                    — create manual operation
  PATCH  /swing-trade/operations/{id}/close         — close open operation
  DELETE /swing-trade/operations/{id}               — soft delete operation

All endpoints are tenant-scoped through get_authed_db + get_current_tenant_id.
Signals reads Redis only — no external market data calls per request.
"""
from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from sqlalchemy import select

from app.core.limiter import limiter
from app.core.middleware import get_authed_db, get_current_tenant_id
from app.core.security import get_current_user
from app.modules.auth.models import User
from app.modules.portfolio.service import PortfolioService
from app.modules.swing_trade.schemas import (
    CopilotResponse,
    OperationClose,
    OperationCreate,
    OperationListResponse,
    OperationResponse,
    SwingSignalsResponse,
)
from app.modules.swing_trade.service import (
    close_operation,
    compute_signals,
    create_operation,
    delete_operation,
    get_operations,
)

logger = logging.getLogger(__name__)

router = APIRouter()


def _get_redis():
    """Dependency: async Redis client for signal + quote enrichment.

    Override in tests via app.dependency_overrides[_get_redis]. Import is
    deferred so test envs without redis installed don't fail at import time.
    """
    import redis.asyncio as aioredis
    from app.core.config import settings

    return aioredis.from_url(settings.REDIS_URL, decode_responses=False)


# ---------------------------------------------------------------------------
# GET /swing-trade/signals
# ---------------------------------------------------------------------------


@limiter.limit("30/minute")
@router.get(
    "/signals",
    response_model=SwingSignalsResponse,
    summary="Swing trade signals — portfolio + radar from Redis cache",
)
async def get_signals(
    request: Request,
    db: AsyncSession = Depends(get_authed_db),
    tenant_id: str = Depends(get_current_tenant_id),
    redis=Depends(_get_redis),
    current_user: dict = Depends(get_current_user),
) -> SwingSignalsResponse:
    """Compute buy/sell/neutral signals for user portfolio + curated radar."""
    portfolio_svc = PortfolioService()
    positions = await portfolio_svc.get_positions(db, tenant_id, redis)
    portfolio_tickers = [p.ticker for p in positions]
    portfolio_quantities = {p.ticker: p.quantity for p in positions}
    return await compute_signals(
        redis_client=redis,
        portfolio_tickers=portfolio_tickers,
        portfolio_quantities=portfolio_quantities,
    )


# ---------------------------------------------------------------------------
# GET /swing-trade/operations
# ---------------------------------------------------------------------------


@limiter.limit("60/minute")
@router.get(
    "/operations",
    response_model=OperationListResponse,
    summary="List swing trade operations for current tenant",
)
async def list_operations(
    request: Request,
    db: AsyncSession = Depends(get_authed_db),
    tenant_id: str = Depends(get_current_tenant_id),
    redis=Depends(_get_redis),
    current_user: dict = Depends(get_current_user),
    status_filter: str | None = Query(
        default=None,
        alias="status",
        description="Filter by operation status: open | closed | stopped",
    ),
    limit: int = Query(default=50, ge=1, le=200, description="Page size"),
    offset: int = Query(default=0, ge=0, description="Page offset"),
) -> OperationListResponse:
    return await get_operations(
        db=db,
        tenant_id=tenant_id,
        redis_client=redis,
        status_filter=status_filter,
        limit=limit,
        offset=offset,
    )


# ---------------------------------------------------------------------------
# POST /swing-trade/operations
# ---------------------------------------------------------------------------


@limiter.limit("30/minute")
@router.post(
    "/operations",
    response_model=OperationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a manual swing trade operation",
)
async def create_operation_endpoint(
    request: Request,
    data: OperationCreate,
    db: AsyncSession = Depends(get_authed_db),
    tenant_id: str = Depends(get_current_tenant_id),
    current_user: dict = Depends(get_current_user),
) -> OperationResponse:
    row = await create_operation(db=db, tenant_id=tenant_id, data=data)
    return OperationResponse.model_validate(row)


# ---------------------------------------------------------------------------
# PATCH /swing-trade/operations/{id}/close
# ---------------------------------------------------------------------------


@limiter.limit("30/minute")
@router.patch(
    "/operations/{operation_id}/close",
    response_model=OperationResponse,
    summary="Close an open swing trade operation with exit price",
)
async def close_operation_endpoint(
    request: Request,
    operation_id: str,
    data: OperationClose,
    db: AsyncSession = Depends(get_authed_db),
    tenant_id: str = Depends(get_current_tenant_id),
    current_user: dict = Depends(get_current_user),
) -> OperationResponse:
    row = await close_operation(
        db=db, tenant_id=tenant_id, op_id=operation_id, data=data
    )
    if row is None:
        raise HTTPException(status_code=404, detail="Operation not found")
    return OperationResponse.model_validate(row)


# ---------------------------------------------------------------------------
# DELETE /swing-trade/operations/{id}
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# GET /swing-trade/copilot
# ---------------------------------------------------------------------------


@limiter.limit("10/minute")
@router.get(
    "/copilot",
    response_model=CopilotResponse,
    summary="Copiloto de Swing Trade — 5 picks prontas com entry/stop/gain/thesis",
)
async def get_copilot(
    request: Request,
    tenant_id: str = Depends(get_current_tenant_id),
    redis=Depends(_get_redis),
    db: AsyncSession = Depends(get_authed_db),
    current_user: dict = Depends(get_current_user),
    force: bool = False,
) -> CopilotResponse:
    """Return AI-curated swing trade and dividend picks ready to execute."""
    from app.core.config import settings
    from app.modules.swing_trade.copilot import build_copilot_picks

    user_id = current_user["user_id"]
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if user is None:
        tier = "free"
    elif user.email in settings.ADMIN_EMAILS:
        tier = "admin"
    elif user.plan == "pro":
        ai_mode = getattr(user, "ai_mode", "standard") or "standard"
        tier = "ultra" if ai_mode == "ultra" else "paid"
    else:
        tier = "free"

    result = await build_copilot_picks(redis_client=redis, force=force, tier=tier)
    return CopilotResponse(**result)


@limiter.limit("30/minute")
@router.delete(
    "/operations/{operation_id}",
    status_code=status.HTTP_200_OK,
    summary="Soft delete a swing trade operation",
)
async def delete_operation_endpoint(
    request: Request,
    operation_id: str,
    db: AsyncSession = Depends(get_authed_db),
    tenant_id: str = Depends(get_current_tenant_id),
    current_user: dict = Depends(get_current_user),
) -> dict:
    ok = await delete_operation(db=db, tenant_id=tenant_id, op_id=operation_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Operation not found")
    return {"deleted": True}
