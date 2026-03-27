"""Celery tasks for AI analysis engine.

CRITICAL: Celery tasks are synchronous. All async skill functions are called
via asyncio.run(). Never import asyncpg or FastAPI async session here.

DB writes use get_sync_db_session (psycopg2) from app.core.db_sync.
Redis reads use the sync redis.Redis client.

Task result format (stored in DB as result_json):
  Asset analysis: {"job_id", "ticker", "dcf", "valuation", "earnings", "completed_at"}
  Macro analysis: {"job_id", "macro", "completed_at"}
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

from app.modules.ai.provider import set_ai_context
from app.modules.ai.skills.dcf import run_dcf
from app.modules.ai.skills.valuation import run_valuation
from app.modules.ai.skills.earnings import run_earnings
from app.modules.ai.skills.macro import run_macro_impact
from app.modules.ai.skills.portfolio_advisor import run_portfolio_advisor

logger = logging.getLogger(__name__)


def _get_sync_redis():
    """Return a synchronous Redis client for Celery tasks."""
    redis_url = os.environ.get("REDIS_URL", "redis://redis:6379/0")
    return sync_redis.from_url(redis_url, decode_responses=True)


def _get_fundamentals_from_redis(ticker: str) -> dict:
    """Read fundamentals for a ticker from Redis (sync)."""
    r = _get_sync_redis()
    raw = r.get(f"market:fundamentals:{ticker.upper()}")
    if raw:
        try:
            data = json.loads(raw)
            return data
        except json.JSONDecodeError:
            logger.warning("Invalid JSON in fundamentals cache for %s", ticker)
    return {}


def _get_investor_profile(tenant_id: str) -> dict | None:
    """Read InvestorProfile for a tenant from DB (sync). Returns None if not found."""
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
                "percentual_renda_fixa_alvo": str(row.percentual_renda_fixa_alvo) if row.percentual_renda_fixa_alvo else None,
            }
    except Exception as exc:
        logger.warning("Could not fetch investor profile for tenant %s: %s", tenant_id, exc)
        return None


def _get_macro_from_redis() -> dict:
    """Read macro indicators from Redis (sync)."""
    r = _get_sync_redis()
    keys = ["selic", "cdi", "ipca", "ptax_usd"]
    result = {}
    for k in keys:
        val = r.get(f"market:macro:{k}")
        result[k] = val or "N/D"
    return result


def _update_job_status(job_id: str, status: str, tenant_id: str | None = None, result_json: str | None = None, error_message: str | None = None) -> None:
    """Update ai_analysis_jobs row in DB using superuser connection to bypass RLS.

    Uses the postgres superuser (AUTH_DATABASE_URL) so the UPDATE works even if:
    - The FastAPI transaction that inserted the row hasn't committed yet (race condition)
    - RLS would otherwise block the update on app_user

    Silently logs errors to avoid cascading failures.
    """
    now = datetime.now(timezone.utc)
    values = dict(
        status=status,
        result_json=result_json,
        error_message=error_message,
        completed_at=now if status in ("completed", "failed") else None,
    )

    try:
        from app.core.db_sync import get_superuser_sync_db_session, get_sync_db_session
        from app.modules.ai.models import AIAnalysisJob

        rowcount = 0
        auth_database_url = os.environ.get("AUTH_DATABASE_URL")

        if auth_database_url:
            with get_superuser_sync_db_session() as session:
                result = session.execute(
                    update(AIAnalysisJob)
                    .where(AIAnalysisJob.id == job_id)
                    .values(**values)
                )
                rowcount = result.rowcount or 0

        if rowcount == 0 and tenant_id:
            with get_sync_db_session(tenant_id) as session:
                result = session.execute(
                    update(AIAnalysisJob)
                    .where(AIAnalysisJob.id == job_id)
                    .values(**values)
                )
                rowcount = result.rowcount or 0

        if rowcount == 0:
            logger.error(
                "No rows updated for AI job %s status transition to %s",
                job_id,
                status,
            )
            return

    except Exception as exc:
        logger.error("Failed to update job %s status to %s: %s", job_id, status, exc)


def _mark_job_running(job_id: str, tenant_id: str | None = None) -> None:
    _update_job_status(job_id, "running", tenant_id=tenant_id)


def _mark_job_failed(
    job_id: str,
    error_message: str,
    tenant_id: str | None = None,
) -> None:
    _update_job_status(job_id, "failed", tenant_id=tenant_id, error_message=error_message)


def _mark_job_completed(
    job_id: str,
    result: dict,
    tenant_id: str | None = None,
) -> None:
    _update_job_status(
        job_id,
        "completed",
        tenant_id=tenant_id,
        result_json=json.dumps(result),
    )


@shared_task(name="ai.run_asset_analysis", bind=True, max_retries=1)
def run_asset_analysis(self, job_id: str, ticker: str, tenant_id: str, tier: str = "free") -> dict:
    """Run DCF + valuation + earnings analysis for a B3 asset.

    Args:
        job_id: UUID of the ai_analysis_jobs row to update.
        ticker: B3 ticker symbol (e.g. "VALE3").
        tenant_id: Tenant UUID (for RLS scoping if needed in future).
        tier: LLM routing tier — "free", "paid", or "admin".

    Returns:
        Dict with job_id, ticker, dcf, valuation, earnings, completed_at.
    """
    logger.info("Starting asset analysis for %s (job=%s, tier=%s)", ticker, job_id, tier)
    set_ai_context(tenant_id=tenant_id, job_id=job_id, tier=tier)
    _mark_job_running(job_id, tenant_id=tenant_id)

    try:
        fundamentals = _get_fundamentals_from_redis(ticker)
        macro = _get_macro_from_redis()
        investor_profile = _get_investor_profile(tenant_id)

        # Run all three skills sequentially (each makes one LLM call)
        dcf_result = asyncio.run(run_dcf(ticker, fundamentals, macro, investor_profile, tier=tier))
        valuation_result = asyncio.run(run_valuation(ticker, fundamentals, tier=tier))
        earnings_result = asyncio.run(run_earnings(ticker, fundamentals, tier=tier))

        result = {
            "job_id": job_id,
            "ticker": ticker,
            "dcf": dcf_result,
            "valuation": valuation_result,
            "earnings": earnings_result,
            "completed_at": datetime.now(timezone.utc).isoformat(),
        }

        _mark_job_completed(job_id, result, tenant_id=tenant_id)
        logger.info("Asset analysis completed for %s (job=%s)", ticker, job_id)
        return result

    except Exception as exc:
        error_msg = str(exc)
        logger.error("Asset analysis failed for %s (job=%s): %s", ticker, job_id, error_msg)
        _mark_job_failed(job_id, error_msg, tenant_id=tenant_id)
        raise


@shared_task(name="ai.run_macro_analysis", bind=True, max_retries=1)
def run_macro_analysis(self, job_id: str, tenant_id: str, allocation: list, tier: str = "free") -> dict:
    """Run macro economic impact analysis for a portfolio allocation.

    Args:
        job_id: UUID of the ai_analysis_jobs row to update.
        tenant_id: Tenant UUID.
        allocation: List of allocation dicts from portfolio PnL response.
        tier: LLM routing tier — "free", "paid", or "admin".

    Returns:
        Dict with job_id, macro analysis result, completed_at.
    """
    logger.info("Starting macro analysis (job=%s, tenant=%s, tier=%s)", job_id, tenant_id, tier)
    set_ai_context(tenant_id=tenant_id, job_id=job_id, tier=tier)
    _mark_job_running(job_id, tenant_id=tenant_id)

    try:
        macro = _get_macro_from_redis()
        investor_profile = _get_investor_profile(tenant_id)
        macro_result = asyncio.run(run_macro_impact(macro, allocation, investor_profile, tier=tier))

        result = {
            "job_id": job_id,
            "macro": macro_result,
            "completed_at": datetime.now(timezone.utc).isoformat(),
        }

        _mark_job_completed(job_id, result, tenant_id=tenant_id)
        logger.info("Macro analysis completed (job=%s)", job_id)
        return result

    except Exception as exc:
        error_msg = str(exc)
        logger.error("Macro analysis failed (job=%s): %s", job_id, error_msg)
        _mark_job_failed(job_id, error_msg, tenant_id=tenant_id)
        raise


@shared_task(name="ai.run_portfolio_analysis", bind=True, max_retries=1)
def run_portfolio_analysis(self, job_id: str, tenant_id: str, positions: list, pnl: dict, allocation: list, tier: str = "free") -> dict:
    """Run full portfolio AI analysis (AI Advisor).

    Args:
        job_id: UUID of the ai_analysis_jobs row to update.
        tenant_id: Tenant UUID.
        positions: List of position dicts from portfolio service.
        pnl: Portfolio P&L summary dict.
        allocation: List of allocation dicts.
        tier: LLM routing tier — "free", "paid", or "admin".

    Returns:
        Dict with job_id, advisor result, completed_at.
    """
    logger.info("Starting portfolio analysis (job=%s, tenant=%s, tier=%s)", job_id, tenant_id, tier)
    set_ai_context(tenant_id=tenant_id, job_id=job_id, tier=tier)
    _mark_job_running(job_id, tenant_id=tenant_id)

    try:
        macro = _get_macro_from_redis()
        investor_profile = _get_investor_profile(tenant_id)
        advisor_result = asyncio.run(run_portfolio_advisor(
            positions=positions,
            pnl=pnl,
            allocation=allocation,
            macro=macro,
            investor_profile=investor_profile,
            tier=tier,
        ))

        result = {
            "job_id": job_id,
            "advisor": advisor_result,
            "completed_at": datetime.now(timezone.utc).isoformat(),
        }

        _mark_job_completed(job_id, result, tenant_id=tenant_id)
        logger.info("Portfolio analysis completed (job=%s)", job_id)
        return result

    except Exception as exc:
        error_msg = str(exc)
        logger.error("Portfolio analysis failed (job=%s): %s", job_id, error_msg)
        _mark_job_failed(job_id, error_msg, tenant_id=tenant_id)
        raise
