"""Quota enforcement for the AI Analysis module (Phase 12).

Tracks per-tenant monthly analysis usage against plan tier limits.
Free tier: 0 analyses (blocked entirely).
Pro tier: 50 analyses per month.
Enterprise tier: 500 analyses per month.

Uses synchronous DB sessions (same pattern as Celery tasks) because
quota checks happen in the hot path and must be fast.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone

from sqlalchemy import select

from app.core.db_sync import get_sync_db_session
from app.modules.analysis.constants import QUOTA_LIMITS
from app.modules.analysis.models import AnalysisQuotaLog

logger = logging.getLogger(__name__)


def _current_year_month() -> str:
    """Return current UTC year-month as 'YYYY-MM'."""
    return datetime.now(tz=timezone.utc).strftime("%Y-%m")


def check_analysis_quota(tenant_id: str, plan_tier: str) -> tuple[bool, int, int]:
    """Check if tenant has analysis quota remaining.

    Returns:
        (allowed, quota_used, quota_limit)
        For free tier (limit=0), always returns (False, 0, 0).
    """
    quota_limit = QUOTA_LIMITS.get(plan_tier, 0)

    # Free tier is always blocked
    if quota_limit == 0:
        logger.info(
            "analysis.quota_blocked tier=%s tenant_id=%s",
            plan_tier, tenant_id,
        )
        return (False, 0, 0)

    year_month = _current_year_month()

    with get_sync_db_session(tenant_id) as session:
        row = session.execute(
            select(AnalysisQuotaLog).where(
                AnalysisQuotaLog.tenant_id == tenant_id,
                AnalysisQuotaLog.year_month == year_month,
            )
        ).scalar_one_or_none()

        if row is None:
            row = AnalysisQuotaLog(
                tenant_id=tenant_id,
                year_month=year_month,
                plan_tier=plan_tier,
                quota_limit=quota_limit,
                quota_used=0,
            )
            session.add(row)
            session.flush()

        allowed = row.quota_used < row.quota_limit

        if not allowed:
            logger.info(
                "analysis.quota_exceeded tenant_id=%s used=%d limit=%d",
                tenant_id, row.quota_used, row.quota_limit,
            )

        return (allowed, row.quota_used, row.quota_limit)


def increment_quota_used(tenant_id: str) -> None:
    """Increment quota_used by 1 for current month."""
    year_month = _current_year_month()

    with get_sync_db_session(tenant_id) as session:
        row = session.execute(
            select(AnalysisQuotaLog).where(
                AnalysisQuotaLog.tenant_id == tenant_id,
                AnalysisQuotaLog.year_month == year_month,
            )
        ).scalar_one_or_none()

        if row is not None:
            row.quota_used += 1
            logger.debug(
                "analysis.quota_incremented tenant_id=%s used=%d",
                tenant_id, row.quota_used,
            )
