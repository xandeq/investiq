"""Celery tasks for the Goldman Screener feature.

Follows the same pattern as app/modules/ai/tasks.py:
- Synchronous task body
- asyncio.run() for async skill calls
- Sync DB session for writes
- Sync Redis for reads
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
from datetime import datetime, timezone

import redis as sync_redis
from celery import shared_task
from sqlalchemy import update

from app.modules.screener.skills.goldman_screener import run_goldman_screener

logger = logging.getLogger(__name__)


def _get_sync_redis():
    url = os.environ.get("REDIS_URL", "redis://redis:6379/0")
    return sync_redis.from_url(url, decode_responses=True)


def _get_macro_from_redis() -> dict:
    r = _get_sync_redis()
    keys = ["selic", "cdi", "ipca", "ptax_usd"]
    result = {}
    for k in keys:
        val = r.get(f"market:macro:{k}")
        result[k] = val or "N/D"
    return result


def _get_investor_profile(tenant_id: str) -> dict | None:
    try:
        from app.core.db_sync import get_sync_db_session
        from app.modules.profile.models import InvestorProfile
        from sqlalchemy import select

        with get_sync_db_session(tenant_id) as session:
            row = session.execute(
                select(InvestorProfile).where(InvestorProfile.tenant_id == tenant_id)
            ).scalar_one_or_none()
            if row is None:
                return None
            return {
                "objetivo": row.objetivo,
                "horizonte_anos": row.horizonte_anos,
                "tolerancia_risco": row.tolerancia_risco,
                "percentual_renda_fixa_alvo": (
                    str(row.percentual_renda_fixa_alvo)
                    if row.percentual_renda_fixa_alvo else None
                ),
            }
    except Exception as exc:
        logger.warning("Could not fetch investor profile for %s: %s", tenant_id, exc)
        return None


def _get_portfolio_tickers(tenant_id: str) -> list[str]:
    """Return list of tickers the user currently holds (open positions)."""
    try:
        from app.core.db_sync import get_sync_db_session
        from app.modules.portfolio.models import Transaction
        from sqlalchemy import select

        with get_sync_db_session(tenant_id) as session:
            rows = session.execute(
                select(Transaction.ticker)
                .where(
                    Transaction.tenant_id == tenant_id,
                    Transaction.transaction_type.in_(["buy", "sell"]),
                    Transaction.deleted_at.is_(None),
                )
                .distinct()
            ).scalars().all()
            return list(rows)
    except Exception as exc:
        logger.warning("Could not fetch portfolio tickers for %s: %s", tenant_id, exc)
        return []


def _update_run_status(
    run_id: str,
    status: str,
    result_json: str | None = None,
    error_message: str | None = None,
) -> None:
    """Update screener_runs row using superuser connection to avoid race conditions.

    Uses get_superuser_sync_db_session so the UPDATE works even if the FastAPI
    transaction that inserted the row hasn't committed yet.
    """
    try:
        from app.core.db_sync import get_superuser_sync_db_session
        from app.modules.screener.models import ScreenerRun

        now = datetime.now(timezone.utc)
        with get_superuser_sync_db_session() as session:
            session.execute(
                update(ScreenerRun)
                .where(ScreenerRun.id == run_id)
                .values(
                    status=status,
                    result_json=result_json,
                    error_message=error_message,
                    completed_at=now if status in ("completed", "failed") else None,
                )
            )
    except Exception as exc:
        logger.error("Failed to update screener run %s to %s: %s", run_id, status, exc)


@shared_task(name="screener.cleanup_stale_runs")
def cleanup_stale_screener_runs() -> dict:
    """Mark screener runs stuck in pending/running for > 15 min as failed.

    Runs every 15 minutes via Celery Beat. Prevents users from seeing
    perpetual "Em andamento..." state when the dispatch or worker failed silently.
    """
    try:
        from app.core.db_sync import get_superuser_sync_db_session
        from app.modules.screener.models import ScreenerRun
        from datetime import timedelta
        from sqlalchemy import and_

        cutoff = datetime.now(timezone.utc) - timedelta(minutes=15)
        with get_superuser_sync_db_session() as session:
            result = session.execute(
                update(ScreenerRun)
                .where(
                    and_(
                        ScreenerRun.status.in_(["pending", "running"]),
                        ScreenerRun.created_at < cutoff,
                    )
                )
                .values(
                    status="failed",
                    error_message="Processamento interrompido. Por favor, tente novamente.",
                    completed_at=datetime.now(timezone.utc),
                )
            )
            count = result.rowcount
        if count:
            logger.info("cleanup_stale_screener_runs: marked %d stale run(s) as failed", count)
        return {"cleaned": count}
    except Exception as exc:
        logger.error("cleanup_stale_screener_runs failed: %s", exc)
        return {"cleaned": 0, "error": str(exc)}


@shared_task(name="screener.run_goldman_screener", bind=True, max_retries=1)
def run_screener_task(
    self,
    run_id: str,
    tenant_id: str,
    sector_filter: str | None,
    custom_notes: str | None,
) -> dict:
    """Execute Goldman Sachs stock screening for a user.

    Args:
        run_id: UUID of the screener_runs row to update.
        tenant_id: Tenant UUID for profile/portfolio lookup.
        sector_filter: Optional sector preference.
        custom_notes: Optional freeform user notes.
    """
    logger.info("Starting screener run %s for tenant %s", run_id, tenant_id)
    _update_run_status(run_id, "running")

    try:
        from app.modules.ai.provider import set_ai_context
        set_ai_context(tenant_id=tenant_id, job_id=run_id, tier="paid")

        macro = _get_macro_from_redis()
        investor_profile = _get_investor_profile(tenant_id)
        portfolio_tickers = _get_portfolio_tickers(tenant_id)

        result = asyncio.run(run_goldman_screener(
            investor_profile=investor_profile,
            portfolio_tickers=portfolio_tickers,
            macro=macro,
            sector_filter=sector_filter,
            custom_notes=custom_notes,
            tier="paid",
        ))

        _update_run_status(run_id, "completed", result_json=json.dumps(result))
        logger.info("Screener run %s completed with %d stocks", run_id, len(result.get("stocks", [])))
        return result

    except Exception as exc:
        error_msg = str(exc)
        logger.error("Screener run %s failed: %s", run_id, error_msg)
        _update_run_status(run_id, "failed", error_message=error_msg)
        raise
