"""Admin endpoint: AI usage statistics and logs."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import Integer, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.db import get_db
from app.core.security import get_current_user
from app.modules.auth.models import User
from app.modules.ai.models import AIUsageLog

router = APIRouter()


async def _require_admin(
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    result = await db.execute(select(User).where(User.id == current_user["user_id"]))
    user = result.scalar_one_or_none()
    if not user or user.email not in settings.ADMIN_EMAILS:
        raise HTTPException(status_code=403, detail="Forbidden")


class UsageLogEntry(BaseModel):
    id: str
    created_at: datetime
    tenant_id: Optional[str]
    job_id: Optional[str]
    tier: str
    provider: str
    model: str
    duration_ms: int
    success: bool
    error: Optional[str]
    model_config = {"from_attributes": True}


class ProviderStat(BaseModel):
    provider: str
    calls: int
    success_rate: float
    avg_duration_ms: float


class TierStat(BaseModel):
    tier: str
    calls: int
    success_rate: float


class UsageStats(BaseModel):
    total_calls: int
    successful_calls: int
    failed_calls: int
    success_rate: float
    avg_duration_ms: float
    by_provider: list[ProviderStat]
    by_tier: list[TierStat]
    period_days: int


@router.get("/stats", response_model=UsageStats, dependencies=[Depends(_require_admin)])
async def get_usage_stats(
    days: int = Query(default=7, ge=1, le=90),
    db: AsyncSession = Depends(get_db),
) -> UsageStats:
    """Aggregate AI usage stats for the last N days."""
    since = datetime.now(tz=timezone.utc) - timedelta(days=days)

    total_q = await db.execute(
        select(func.count()).select_from(AIUsageLog).where(AIUsageLog.created_at >= since)
    )
    total = total_q.scalar() or 0

    success_q = await db.execute(
        select(func.count()).select_from(AIUsageLog).where(
            AIUsageLog.created_at >= since, AIUsageLog.success == True  # noqa: E712
        )
    )
    successful = success_q.scalar() or 0

    avg_q = await db.execute(
        select(func.avg(AIUsageLog.duration_ms)).where(AIUsageLog.created_at >= since)
    )
    avg_dur = float(avg_q.scalar() or 0)

    # By provider
    prov_q = await db.execute(
        select(
            AIUsageLog.provider,
            func.count().label("calls"),
            func.sum(func.cast(AIUsageLog.success, Integer)).label("successes"),
            func.avg(AIUsageLog.duration_ms).label("avg_dur"),
        )
        .where(AIUsageLog.created_at >= since)
        .group_by(AIUsageLog.provider)
        .order_by(func.count().desc())
    )
    by_provider = [
        ProviderStat(
            provider=r.provider,
            calls=r.calls,
            success_rate=round((r.successes or 0) / r.calls * 100, 1) if r.calls else 0.0,
            avg_duration_ms=round(float(r.avg_dur or 0), 0),
        )
        for r in prov_q.all()
    ]

    # By tier
    tier_q = await db.execute(
        select(
            AIUsageLog.tier,
            func.count().label("calls"),
            func.sum(func.cast(AIUsageLog.success, Integer)).label("successes"),
        )
        .where(AIUsageLog.created_at >= since)
        .group_by(AIUsageLog.tier)
        .order_by(func.count().desc())
    )
    by_tier = [
        TierStat(
            tier=r.tier,
            calls=r.calls,
            success_rate=round((r.successes or 0) / r.calls * 100, 1) if r.calls else 0.0,
        )
        for r in tier_q.all()
    ]

    return UsageStats(
        total_calls=total,
        successful_calls=successful,
        failed_calls=total - successful,
        success_rate=round(successful / total * 100, 1) if total else 0.0,
        avg_duration_ms=round(avg_dur, 0),
        by_provider=by_provider,
        by_tier=by_tier,
        period_days=days,
    )


@router.get("/logs", response_model=list[UsageLogEntry], dependencies=[Depends(_require_admin)])
async def list_usage_logs(
    days: int = Query(default=7, ge=1, le=90),
    tier: Optional[str] = Query(default=None),
    provider: Optional[str] = Query(default=None),
    success: Optional[bool] = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
) -> list[UsageLogEntry]:
    """List recent AI usage log entries with optional filters."""
    since = datetime.now(tz=timezone.utc) - timedelta(days=days)
    q = select(AIUsageLog).where(AIUsageLog.created_at >= since)
    if tier:
        q = q.where(AIUsageLog.tier == tier)
    if provider:
        q = q.where(AIUsageLog.provider == provider)
    if success is not None:
        q = q.where(AIUsageLog.success == success)  # noqa: E712
    q = q.order_by(AIUsageLog.created_at.desc()).limit(limit)
    result = await db.execute(q)
    return result.scalars().all()
