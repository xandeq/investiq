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
from app.modules.analysis.data import DataFetchError, fetch_fundamentals, get_selic_rate
from app.modules.analysis.dcf import calculate_dcf_with_sensitivity, calculate_wacc, estimate_growth_rate
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
    3. Fetch fundamentals from BRAPI (real data, cached in Redis)
    3.5. Fetch SELIC rate from BCB
    3.6. Calculate WACC via CAPM
    3.7. Estimate growth rate if not provided
    4. Calculate DCF with sensitivity analysis
    5. Call LLM for narrative (with fallback chain)
    6. Build result with data versioning metadata
    7. Update job status -> completed
    8. Log cost

    On any failure: status -> failed, cost logged.
    """
    logger.info("DCF analysis started: job=%s ticker=%s", job_id, ticker)
    assumptions = assumptions or {}

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
        # Step 3: Fetch fundamentals from BRAPI
        try:
            fundamentals = fetch_fundamentals(ticker)
        except DataFetchError as exc:
            _update_job(job_id, "failed", error=f"Data fetch failed: {exc}")
            duration_ms = int((time.time() - start_time) * 1000)
            log_analysis_cost(
                tenant_id, job_id, "dcf", ticker,
                duration_ms=duration_ms, status="failed",
            )
            return

        # Validate critical DCF field
        if not fundamentals.get("free_cash_flow"):
            _update_job(
                job_id, "failed",
                error=f"DCF requires Free Cash Flow data which is unavailable for {ticker}",
            )
            duration_ms = int((time.time() - start_time) * 1000)
            log_analysis_cost(
                tenant_id, job_id, "dcf", ticker,
                duration_ms=duration_ms, status="failed",
            )
            return

        # Step 3.5: Fetch SELIC rate from BCB
        selic_rate, selic_date, selic_is_fallback = get_selic_rate()

        # Step 3.6: Calculate WACC via CAPM
        wacc = calculate_wacc(
            selic=selic_rate,
            beta=fundamentals.get("beta"),
            debt=fundamentals.get("total_debt", 0) or 0,
            equity=fundamentals.get("market_cap", 0) or 0,
        )

        # Step 3.7: Estimate growth rate if not provided by user
        growth = assumptions.get("growth_rate") or estimate_growth_rate(
            fundamentals.get("cashflow_history", [])
        )

        # Step 4: Calculate DCF with sensitivity
        net_debt = (fundamentals.get("total_debt", 0) or 0) - (fundamentals.get("total_cash", 0) or 0)
        shares = fundamentals.get("shares_outstanding")
        if not shares or shares <= 0:
            _update_job(
                job_id, "failed",
                error=f"Cannot calculate DCF: shares outstanding unavailable for {ticker}",
            )
            duration_ms = int((time.time() - start_time) * 1000)
            log_analysis_cost(
                tenant_id, job_id, "dcf", ticker,
                duration_ms=duration_ms, status="failed",
            )
            return

        dcf_result = calculate_dcf_with_sensitivity(
            fcf_current=fundamentals["free_cash_flow"],
            shares_outstanding=shares,
            growth_rate=growth,
            wacc=assumptions.get("discount_rate") or wacc,
            terminal_growth=assumptions.get("terminal_growth") or 0.03,
            net_debt=net_debt,
        )

        # Calculate upside from current price
        current_price = fundamentals.get("current_price", 0) or 0
        if current_price > 0 and dcf_result["fair_value"]:
            dcf_result["upside_pct"] = round(
                ((dcf_result["fair_value"] - current_price) / current_price) * 100, 2
            )

        # Step 5: Call LLM for narrative
        narrative = _STATIC_FALLBACK_NARRATIVE
        try:
            fv = dcf_result["fair_value"]
            fv_range = dcf_result.get("fair_value_range", {})
            upside = dcf_result.get("upside_pct", 0) or 0
            prompt = (
                f"Forneça uma breve narrativa de análise DCF para {ticker}. "
                f"Preço atual: R${current_price:.2f}. "
                f"Valor justo estimado: R${fv:.2f} "
                f"(faixa: R${fv_range.get('low', 0) or 0:.2f} a R${fv_range.get('high', 0) or 0:.2f}). "
                f"Upside: {upside:.1f}%. "
                f"Taxa de crescimento: {growth:.1%}. "
                f"WACC: {wacc:.1%}. "
                f"Drivers principais: {'; '.join(dcf_result.get('key_drivers', [])[:2])}. "
                f"Seja conciso, 2-3 frases em Português (PT-BR)."
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

        # Step 6: Build result with full breakdown
        data_version_id = build_data_version_id()
        data_sources = get_data_sources()
        # Append BCB source
        data_sources.append({
            "source": "BCB",
            "type": "SELIC rate",
            "date": selic_date,
        })
        data_timestamp = datetime.now(timezone.utc).isoformat()

        result = {
            "ticker": ticker,
            "fair_value": dcf_result["fair_value"],
            "fair_value_range": dcf_result.get("fair_value_range", {}),
            "current_price": current_price,
            "upside_pct": dcf_result.get("upside_pct"),
            "assumptions": {
                "growth_rate": growth,
                "discount_rate": assumptions.get("discount_rate") or wacc,
                "terminal_growth": assumptions.get("terminal_growth") or 0.03,
                "selic_rate": selic_rate,
                "beta": fundamentals.get("beta"),
                "selic_is_fallback": selic_is_fallback,
            },
            "projected_fcfs": dcf_result.get("projected_fcfs", []),
            "key_drivers": dcf_result.get("key_drivers", []),
            "scenarios": dcf_result.get("scenarios", {}),
            "narrative": narrative,
            "data_completeness": fundamentals.get("data_completeness", {}),
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
