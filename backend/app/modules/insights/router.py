"""User Insights router."""
from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, status
from fastapi.responses import Response
from pydantic import BaseModel, ConfigDict
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.middleware import get_authed_db, get_current_tenant_id
from app.modules.insights.models import UserInsight

router = APIRouter()


class InsightResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    type: str
    title: str
    body: str
    severity: str
    ticker: str | None = None
    seen: bool
    created_at: datetime | None = None


@router.get("/unread-count")
async def get_unread_count(
    db: AsyncSession = Depends(get_authed_db),
    tenant_id: str = Depends(get_current_tenant_id),
) -> dict:
    """Return count of unseen insights for the current user."""
    result = await db.execute(
        select(func.count())
        .select_from(UserInsight)
        .where(UserInsight.tenant_id == tenant_id, UserInsight.seen == False)  # noqa: E712
    )
    return {"count": result.scalar_one()}


@router.get("", response_model=list[InsightResponse])
async def list_insights(
    db: AsyncSession = Depends(get_authed_db),
    tenant_id: str = Depends(get_current_tenant_id),
) -> list[InsightResponse]:
    result = await db.execute(
        select(UserInsight)
        .where(UserInsight.tenant_id == tenant_id)
        .order_by(UserInsight.seen.asc(), UserInsight.created_at.desc())
        .limit(50)
    )
    return [InsightResponse.model_validate(r) for r in result.scalars().all()]


@router.patch("/{insight_id}/seen", status_code=204)
async def mark_seen(
    insight_id: str,
    db: AsyncSession = Depends(get_authed_db),
    tenant_id: str = Depends(get_current_tenant_id),
) -> Response:
    await db.execute(
        update(UserInsight)
        .where(UserInsight.id == insight_id, UserInsight.tenant_id == tenant_id)
        .values(seen=True)
    )
    return Response(status_code=204)
