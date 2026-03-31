"""Celery tasks for the AI Analysis module (Phase 12).

Pattern: sync Celery task + asyncio.run() for LLM call.
DB writes use superuser session (bypass RLS race condition).
DB reads use tenant-scoped sync session.

Follows the same pattern as wizard/tasks.py.
"""
from __future__ import annotations

import asyncio
import json
import logging
import time
from datetime import datetime, timezone

from celery import shared_task
from sqlalchemy import select, update

from app.core.db_sync import get_superuser_sync_db_session
from app.modules.analysis.constants import CVM_DISCLAIMER_SHORT_PT, QUOTA_LIMITS
from app.modules.analysis.cost import log_analysis_cost
from app.modules.analysis.models import AnalysisJob, AnalysisQuotaLog
from app.modules.analysis.providers import (
    AIProviderError,
    _get_cached_analysis_with_outdated_badge,
    call_analysis_llm,
)
from app.modules.analysis.versioning import build_data_version_id, get_data_sources

logger = logging.getLogger(__name__)

_STATIC_FALLBACK_NARRATIVE = (
    "Narrative generation unavailable. The DCF valuation above is based on "
    "quantitative inputs only. Please retry later for AI-generated commentary."
)


def _update_job(
    job_id: str,
    status: str,
    result_json: str | None = None,
    error: str | None = None,
) -> None:
    """Update AnalysisJob status and optional fields.

    Uses superuser session to bypass RLS (same pattern as wizard/tasks.py).
    """
    try:
        now = datetime.now(timezone.utc)
        values: dict = {"status": status}
        if result_json is not None:
            values["result_json"] = result_json
        if error is not None:
            values["error_message"] = error[:500]
        if status in ("completed", "failed"):
            values["completed_at"] = now

        with get_superuser_sync_db_session() as session:
            session.execute(
                update(AnalysisJob)
                .where(AnalysisJob.id == job_id)
                .values(**values)
            )
    except Exception as exc:
        logger.error("_update_job failed for job %s: %s", job_id, exc)


def _check_and_increment_quota(tenant_id: str) -> bool:
    """Check if tenant has remaining analysis quota and increment if so.

    Returns True if the request is allowed, False if quota exhausted.
    """
    try:
        year_month = datetime.now(timezone.utc).strftime("%Y-%m")

        with get_superuser_sync_db_session() as session:
            stmt = select(AnalysisQuotaLog).where(
                AnalysisQuotaLog.tenant_id == tenant_id,
                AnalysisQuotaLog.year_month == year_month,
            )
            quota_log = session.execute(stmt).scalar_one_or_none()

            if quota_log is None:
                # No quota record means no plan configured — block by default
                logger.warning(
                    "No quota record for tenant %s month %s — blocking",
                    tenant_id,
                    year_month,
                )
                return False

            # Free tier (quota_limit == 0) always blocked
            if quota_log.quota_limit == 0:
                return False

            # Check if quota exhausted
            if quota_log.quota_used >= quota_log.quota_limit:
                return False

            # Increment and allow
            quota_log.quota_used += 1
            session.add(quota_log)
            return True

    except Exception as exc:
        logger.error("Quota check failed for tenant %s: %s", tenant_id, exc)
        return False


def _fetch_fundamentals_stub(ticker: str) -> dict:
    """Return hardcoded sample fundamentals data.

    Real BRAPI integration comes in Phase 13. This stub provides realistic
    values for testing the full DCF pipeline.
    """
    return {
        "current_price": 27.80,
        "eps": 3.50,
        "pe_ratio": 7.94,
        "revenue": 500_000_000_000,
        "free_cash_flow": 50_000_000_000,
        "dividend_yield": 0.08,
        "market_cap": 400_000_000_000,
    }


def _calculate_dcf_stub(
    ticker: str, fundamentals: dict, assumptions: dict | None
) -> dict:
    """Return hardcoded DCF calculation results.

    Real DCF calculation comes in Phase 13. This stub returns plausible
    values to test the full task pipeline.
    """
    assumptions = assumptions or {}
    return {
        "fair_value": 28.50,
        "low": 26.00,
        "high": 31.00,
        "upside_pct": 2.5,
        "growth_rate": assumptions.get("growth_rate", 0.05),
        "discount_rate": assumptions.get("discount_rate", 0.10),
        "terminal_growth": assumptions.get("terminal_growth", 0.03),
    }


@shared_task(name="analysis.run_dcf", bind=True, max_retries=0)
def run_dcf(
    self,
    job_id: str,
    tenant_id: str,
    ticker: str,
    assumptions: dict | None = None,
) -> None:
    """Run DCF analysis as a Celery background task.

    Steps:
    1. Check quota
    2. Set status -> running
    3. Fetch fundamentals (stub in Phase 12)
    4. Calculate DCF (stub in Phase 12)
    5. Call LLM for narrative (with fallback chain)
    6. Build result with data versioning metadata
    7. Update job status -> completed
    8. Log cost

    On any failure: status -> failed, cost logged.
    """
    logger.info("DCF analysis started: job=%s ticker=%s", job_id, ticker)

    # Step 1: Quota check
    if not _check_and_increment_quota(tenant_id):
        _update_job(job_id, "failed", error="Analysis quota exhausted")
        log_analysis_cost(
            tenant_id, job_id, "dcf", ticker, duration_ms=0, status="failed"
        )
        return

    # Step 2: Mark running
    _update_job(job_id, "running")
    start_time = time.time()

    llm_meta: dict = {}

    try:
        # Step 3: Fetch fundamentals
        fundamentals = _fetch_fundamentals_stub(ticker)

        # Step 4: Calculate DCF
        dcf_result = _calculate_dcf_stub(ticker, fundamentals, assumptions)

        # Step 5: Call LLM for narrative
        narrative = _STATIC_FALLBACK_NARRATIVE
        try:
            prompt = (
                f"Provide a brief DCF analysis narrative for {ticker}. "
                f"Current price: R${fundamentals['current_price']:.2f}. "
                f"Fair value estimate: R${dcf_result['fair_value']:.2f}. "
                f"Upside: {dcf_result['upside_pct']:.1f}%. "
                f"Growth rate: {dcf_result['growth_rate']:.1%}. "
                f"Discount rate: {dcf_result['discount_rate']:.1%}. "
                f"Be concise, 2-3 sentences in Portuguese (PT-BR)."
            )
            narrative_text, llm_meta = asyncio.run(
                call_analysis_llm(prompt, max_tokens=300)
            )
            narrative = narrative_text
        except AIProviderError:
            logger.warning(
                "All LLM providers failed for job %s — checking cache", job_id
            )
            cached = _get_cached_analysis_with_outdated_badge(ticker, "dcf")
            if cached and "narrative" in cached:
                narrative = cached["narrative"]
            # else: keep _STATIC_FALLBACK_NARRATIVE

        # Step 6: Build result
        data_version_id = build_data_version_id()
        data_sources = get_data_sources()
        data_timestamp = datetime.now(timezone.utc).isoformat()

        result = {
            "ticker": ticker,
            "fair_value": dcf_result["fair_value"],
            "fair_value_range": {
                "low": dcf_result["low"],
                "high": dcf_result["high"],
            },
            "current_price": fundamentals["current_price"],
            "upside_pct": dcf_result["upside_pct"],
            "assumptions": {
                "growth_rate": dcf_result["growth_rate"],
                "discount_rate": dcf_result["discount_rate"],
                "terminal_growth": dcf_result["terminal_growth"],
            },
            "narrative": narrative,
            "data_version_id": data_version_id,
            "data_timestamp": data_timestamp,
            "data_sources": data_sources,
            "disclaimer": CVM_DISCLAIMER_SHORT_PT,
        }

        # Step 7: Update job
        _update_job(job_id, "completed", result_json=json.dumps(result, ensure_ascii=False))

        # Step 8: Log cost
        duration_ms = int((time.time() - start_time) * 1000)
        log_analysis_cost(
            tenant_id,
            job_id,
            "dcf",
            ticker,
            duration_ms=duration_ms,
            status="completed",
            llm_provider=llm_meta.get("provider_used"),
            llm_model=llm_meta.get("model"),
        )

        logger.info("DCF analysis completed: job=%s ticker=%s", job_id, ticker)

    except Exception as exc:
        duration_ms = int((time.time() - start_time) * 1000)
        logger.error("DCF analysis failed for job %s: %s", job_id, exc)
        _update_job(job_id, "failed", error=str(exc)[:500])
        log_analysis_cost(
            tenant_id,
            job_id,
            "dcf",
            ticker,
            duration_ms=duration_ms,
            status="failed",
        )
