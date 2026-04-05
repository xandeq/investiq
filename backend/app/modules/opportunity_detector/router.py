"""Opportunity Detector history and follow endpoints (Phase 19).

GET  /opportunity-detector/history        — paginated history with filters
PATCH /opportunity-detector/{id}/follow   — toggle followed flag

Both endpoints use get_global_db (detected_opportunities is a global table, no RLS).
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_global_db
from app.core.limiter import limiter
from app.core.security import get_current_user
from app.modules.opportunity_detector.models import DetectedOpportunity
from app.modules.opportunity_detector.schemas import OpportunityHistoryResponse

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get(
    "/history",
    response_model=OpportunityHistoryResponse,
    summary="Histórico de oportunidades detectadas",
    tags=["opportunity-detector"],
)
@limiter.limit("30/minute")
async def get_opportunity_history(
    request: Request,
    current_user: dict = Depends(get_current_user),
    global_db: AsyncSession = Depends(get_global_db),
    asset_type: str | None = Query(default=None, description="Filter by asset type: acao | crypto | renda_fixa"),
    days: int = Query(default=30, ge=1, le=365, description="How many days back to include"),
) -> OpportunityHistoryResponse:
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    stmt = select(DetectedOpportunity).where(DetectedOpportunity.detected_at >= cutoff)
    if asset_type:
        stmt = stmt.where(DetectedOpportunity.asset_type == asset_type)
    stmt = stmt.order_by(DetectedOpportunity.detected_at.desc())
    result = await global_db.execute(stmt)
    rows = result.scalars().all()
    return OpportunityHistoryResponse(total=len(rows), results=rows)


@router.patch(
    "/{opportunity_id}/follow",
    summary="Toggle followed flag for an opportunity",
    tags=["opportunity-detector"],
)
@limiter.limit("30/minute")
async def mark_as_followed(
    request: Request,
    opportunity_id: str,
    current_user: dict = Depends(get_current_user),
    global_db: AsyncSession = Depends(get_global_db),
) -> dict:
    stmt = select(DetectedOpportunity).where(DetectedOpportunity.id == opportunity_id)
    result = await global_db.execute(stmt)
    opp = result.scalar_one_or_none()
    if not opp:
        raise HTTPException(status_code=404, detail="Opportunity not found")
    opp.followed = not opp.followed
    await global_db.commit()
    await global_db.refresh(opp)
    return {"id": opp.id, "followed": opp.followed}
