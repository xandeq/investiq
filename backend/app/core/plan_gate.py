"""Freemium plan gate — centralized limits and enforcement.

FREE tier hard limits:
  - 50 transactions total (portfolio size cap)
  - 3 import uploads per calendar month
  - AI analysis: blocked entirely (premium-only feature)

Pro/Enterprise: no limits on any of the above.

Usage in routers:
    from app.core.plan_gate import get_user_plan, require_transaction_slot, require_import_slot

    @router.post("/transactions")
    async def create_transaction(
        ...,
        plan: str = Depends(get_user_plan),
        tenant_id: str = Depends(get_current_tenant_id),
        db: AsyncSession = Depends(get_authed_db),
    ):
        await require_transaction_slot(plan, tenant_id, db)
        ...
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone

from fastapi import Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.middleware import get_authed_db
from app.core.security import get_current_user
from app.modules.auth.models import User

logger = logging.getLogger(__name__)

# -----------------------------------------------------------------------
# Tier limits
# -----------------------------------------------------------------------
FREE_TRANSACTION_LIMIT: int = 50
FREE_IMPORTS_PER_MONTH: int = 3


# -----------------------------------------------------------------------
# Shared dependency
# -----------------------------------------------------------------------
async def get_user_plan(
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_authed_db),
) -> str:
    """FastAPI dependency: return the authenticated user's effective plan.

    Trial users (plan=="free" but trial_ends_at in the future) are elevated to
    "pro" for all gate checks. This is the single place trial elevation happens.

    Returns:
        str: "free" | "pro" | "enterprise"
    """
    result = await db.execute(select(User).where(User.id == current_user["user_id"]))
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found.")

    # Trial elevation: free user with active trial gets pro access
    if user.plan == "free" and user.trial_ends_at is not None:
        # Normalize to aware datetimes for comparison (SQLite returns naive datetimes)
        trial_ends = user.trial_ends_at
        if trial_ends.tzinfo is None:
            trial_ends = trial_ends.replace(tzinfo=timezone.utc)
        if trial_ends > datetime.now(tz=timezone.utc):
            logger.debug("plan_gate.trial_elevation user_id=%s", user.id)
            return "pro"

    return user.plan


# -----------------------------------------------------------------------
# Enforcement helpers
# -----------------------------------------------------------------------
async def require_transaction_slot(plan: str, tenant_id: str, db: AsyncSession) -> None:
    """Raise 403 if a free user has reached the total transaction limit.

    Pro/Enterprise users pass through unconditionally.
    """
    if plan != "free":
        return
    from app.modules.portfolio.models import Transaction  # lazy — avoids circular import

    count = await db.scalar(
        select(func.count())
        .select_from(Transaction)
        .where(Transaction.tenant_id == tenant_id)
    )
    if (count or 0) >= FREE_TRANSACTION_LIMIT:
        logger.info(
            "billing.limit_hit code=LIMIT_TRANSACTION tenant_id=%s used=%d limit=%d",
            tenant_id, count, FREE_TRANSACTION_LIMIT,
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "code": "LIMIT_TRANSACTION",
                "message": (
                    f"Você atingiu o limite de {FREE_TRANSACTION_LIMIT} transações do plano Free. "
                    "Faça upgrade para continuar registrando transações."
                ),
                "upgrade_url": "/planos",
            },
        )


async def require_import_slot(plan: str, tenant_id: str, db: AsyncSession) -> None:
    """Raise 403 if a free user has reached the monthly import limit.

    Counts ImportJob rows created in the current calendar month.
    Pro/Enterprise users pass through unconditionally.
    """
    if plan != "free":
        return
    from app.modules.imports.models import ImportJob  # lazy — avoids circular import

    now = datetime.now(tz=timezone.utc)
    start_of_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    count = await db.scalar(
        select(func.count())
        .select_from(ImportJob)
        .where(
            ImportJob.tenant_id == tenant_id,
            ImportJob.created_at >= start_of_month,
        )
    )
    if (count or 0) >= FREE_IMPORTS_PER_MONTH:
        logger.info(
            "billing.limit_hit code=LIMIT_IMPORT tenant_id=%s used=%d limit=%d",
            tenant_id, count, FREE_IMPORTS_PER_MONTH,
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "code": "LIMIT_IMPORT",
                "message": (
                    f"Você atingiu o limite de {FREE_IMPORTS_PER_MONTH} importações deste mês. "
                    "Faça upgrade para continuar importando arquivos."
                ),
                "upgrade_url": "/planos",
            },
        )
