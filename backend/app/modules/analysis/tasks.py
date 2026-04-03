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

import requests
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
from app.modules.analysis.history import get_completeness_flag
from app.modules.analysis.dcf import calculate_dcf_with_sensitivity, calculate_wacc, estimate_growth_rate
from app.modules.analysis.dividend import calculate_dividend_analysis
from app.modules.analysis.earnings import calculate_earnings_analysis
from app.modules.analysis.sector import _SECTOR_TICKERS, calculate_sector_comparison, fetch_peer_fundamentals
from app.modules.analysis.versioning import build_data_version_id, get_data_sources

logger = logging.getLogger(__name__)

_STATIC_FALLBACK_NARRATIVE = (
    "Narrative generation unavailable. The DCF valuation above is based on "
    "quantitative inputs only. Please retry later for AI-generated commentary."
)

_STATIC_FALLBACK_NARRATIVE_EARNINGS = (
    "Narrative generation unavailable. The earnings analysis above is based on "
    "quantitative data only. Please retry later for AI-generated commentary."
)

_STATIC_FALLBACK_NARRATIVE_DIVIDEND = (
    "Narrative generation unavailable. The dividend analysis above is based on "
    "quantitative data only. Please retry later for AI-generated commentary."
)

_STATIC_FALLBACK_NARRATIVE_SECTOR = (
    "Narrative generation unavailable. The sector comparison above is based on "
    "quantitative data only. Please retry later for AI-generated commentary."
)


def archive_previous_completed_jobs(
    ticker: str,
    tenant_id: str,
    analysis_type: str,
    exclude_job_id: str,
) -> int:
    """Mark older completed jobs as stale after a fresh completed analysis."""
    with get_superuser_sync_db_session() as session:
        stmt = (
            update(AnalysisJob)
            .where(
                AnalysisJob.tenant_id == tenant_id,
                AnalysisJob.ticker == ticker.upper(),
                AnalysisJob.analysis_type == analysis_type,
                AnalysisJob.status == "completed",
                AnalysisJob.id != exclude_job_id,
            )
            .values(
                status="stale",
                error_message="Superseded by newer analysis",
            )
        )
        result = session.execute(stmt)
        return result.rowcount or 0


def _fetch_latest_quarterly_filing_date(ticker: str) -> datetime | None:
    """Fetch the most recent quarterly filing date from BRAPI."""
    from app.modules.analysis.data import _BRAPI_BASE_URL, _resolve_brapi_token

    try:
        token = _resolve_brapi_token()
        params = {
            "modules": "incomeStatementHistoryQuarterly",
            "fundamental": "true",
        }
        if token:
            params["token"] = token

        response = requests.get(
            f"{_BRAPI_BASE_URL}/quote/{ticker.upper()}",
            params=params,
            timeout=10,
        )
        response.raise_for_status()
        data = response.json()
        results = data.get("results", [])
        if not results:
            return None

        quarterly = results[0].get("incomeStatementHistoryQuarterly", [])
        if not quarterly:
            return None

        end_date = quarterly[0].get("endDate")
        if not end_date:
            return None

        return datetime.fromisoformat(end_date.replace("Z", "+00:00"))
    except Exception as exc:
        logger.warning("Failed to fetch filing date for %s: %s", ticker, exc)
        return None


def _archive_superseded_job(
    ticker: str,
    tenant_id: str,
    analysis_type: str,
    job_id: str,
) -> None:
    """Best-effort archival of older completed jobs after a successful refresh."""
    try:
        archive_previous_completed_jobs(
            ticker=ticker,
            tenant_id=tenant_id,
            analysis_type=analysis_type,
            exclude_job_id=job_id,
        )
    except Exception as exc:
        logger.warning(
            "Failed to archive previous %s analyses for %s/%s: %s",
            analysis_type,
            tenant_id,
            ticker,
            exc,
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
            "completeness_flag": get_completeness_flag(fundamentals.get("data_completeness", {})),
            "data_version_id": data_version_id,
            "data_timestamp": data_timestamp,
            "data_sources": data_sources,
            "disclaimer": CVM_DISCLAIMER_SHORT_PT,
        }

        # Step 7: Update job
        _update_job(job_id, "completed", result_json=json.dumps(result, ensure_ascii=False))
        _archive_superseded_job(ticker, tenant_id, "dcf", job_id)

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


@shared_task(name="analysis.run_earnings", bind=True, max_retries=0)
def run_earnings(
    self,
    job_id: str,
    tenant_id: str,
    ticker: str,
) -> None:
    """Run earnings analysis as a Celery background task.

    Steps:
    1. Check quota
    2. Set status -> running
    3. Fetch fundamentals from BRAPI
    4. Calculate earnings analysis
    5. Call LLM for narrative (PT-BR)
    6. Build result with data versioning
    7. Update job status -> completed
    8. Log cost
    """
    logger.info("Earnings analysis started: job=%s ticker=%s", job_id, ticker)

    # Step 1: Quota check
    if not _check_and_increment_quota(tenant_id):
        _update_job(job_id, "failed", error="Analysis quota exhausted")
        log_analysis_cost(
            tenant_id, job_id, "earnings", ticker, duration_ms=0, status="failed"
        )
        return

    # Step 2: Mark running
    _update_job(job_id, "running")
    start_time = time.time()

    llm_meta: dict = {}

    try:
        # Step 3: Fetch fundamentals
        try:
            fundamentals = fetch_fundamentals(ticker)
        except DataFetchError as exc:
            _update_job(job_id, "failed", error=f"Data fetch failed: {exc}")
            duration_ms = int((time.time() - start_time) * 1000)
            log_analysis_cost(
                tenant_id, job_id, "earnings", ticker,
                duration_ms=duration_ms, status="failed",
            )
            return

        # Step 4: Calculate earnings analysis
        earnings_result = calculate_earnings_analysis(fundamentals)

        # Step 5: Call LLM for narrative
        narrative = _STATIC_FALLBACK_NARRATIVE_EARNINGS
        try:
            qm = earnings_result.get("quality_metrics", {})
            eps_val = fundamentals.get("eps", "N/A")
            cagr = earnings_result.get("eps_cagr_5y")
            cagr_str = f"{cagr:.1%}" if cagr is not None else "N/A"
            quality = qm.get("earnings_quality", "N/A")
            accrual = qm.get("accrual_ratio")
            accrual_str = f"{accrual:.2f}" if accrual is not None else "N/A"
            fcf_conv = qm.get("fcf_conversion")
            fcf_str = f"{fcf_conv:.2f}" if fcf_conv is not None else "N/A"

            prompt = (
                f"Resuma a analise de lucros de {ticker}. "
                f"EPS atual: R${eps_val}. "
                f"CAGR 5 anos: {cagr_str}. "
                f"Qualidade dos lucros: {quality}. "
                f"Accrual ratio: {accrual_str}. "
                f"Conversao FCF: {fcf_str}. "
                f"Seja conciso, 2-3 frases em portugues."
            )
            narrative_text, llm_meta = asyncio.run(
                call_analysis_llm(prompt, max_tokens=300)
            )
            narrative = narrative_text
        except AIProviderError:
            logger.warning(
                "All LLM providers failed for earnings job %s — using static fallback",
                job_id,
            )
            cached = _get_cached_analysis_with_outdated_badge(ticker, "earnings")
            if cached and "narrative" in cached:
                narrative = cached["narrative"]

        # Step 6: Build result with versioning
        data_version_id = build_data_version_id()
        data_sources = get_data_sources()
        data_timestamp = datetime.now(timezone.utc).isoformat()

        result = {
            "ticker": ticker,
            "eps_history": earnings_result.get("eps_history", []),
            "eps_cagr_5y": earnings_result.get("eps_cagr_5y"),
            "quality_metrics": earnings_result.get("quality_metrics", {}),
            "narrative": narrative,
            "data_completeness": earnings_result.get("data_completeness", {}),
            "completeness_flag": get_completeness_flag(earnings_result.get("data_completeness", {})),
            "data_version_id": data_version_id,
            "data_timestamp": data_timestamp,
            "data_sources": data_sources,
            "disclaimer": CVM_DISCLAIMER_SHORT_PT,
        }

        # Step 7: Update job
        _update_job(job_id, "completed", result_json=json.dumps(result, ensure_ascii=False))
        _archive_superseded_job(ticker, tenant_id, "earnings", job_id)

        # Step 8: Log cost
        duration_ms = int((time.time() - start_time) * 1000)
        log_analysis_cost(
            tenant_id,
            job_id,
            "earnings",
            ticker,
            duration_ms=duration_ms,
            status="completed",
            llm_provider=llm_meta.get("provider_used"),
            llm_model=llm_meta.get("model"),
        )

        logger.info("Earnings analysis completed: job=%s ticker=%s", job_id, ticker)

    except Exception as exc:
        duration_ms = int((time.time() - start_time) * 1000)
        logger.error("Earnings analysis failed for job %s: %s", job_id, exc)
        _update_job(job_id, "failed", error=str(exc)[:500])
        log_analysis_cost(
            tenant_id,
            job_id,
            "earnings",
            ticker,
            duration_ms=duration_ms,
            status="failed",
        )


@shared_task(name="analysis.run_dividend", bind=True, max_retries=0)
def run_dividend(
    self,
    job_id: str,
    tenant_id: str,
    ticker: str,
) -> None:
    """Run dividend sustainability analysis as a Celery background task.

    Steps:
    1. Check quota
    2. Set status -> running
    3. Fetch fundamentals from BRAPI
    4. Calculate dividend analysis
    5. Call LLM for narrative (PT-BR)
    6. Build result with data versioning
    7. Update job status -> completed
    8. Log cost
    """
    logger.info("Dividend analysis started: job=%s ticker=%s", job_id, ticker)

    # Step 1: Quota check
    if not _check_and_increment_quota(tenant_id):
        _update_job(job_id, "failed", error="Analysis quota exhausted")
        log_analysis_cost(
            tenant_id, job_id, "dividend", ticker, duration_ms=0, status="failed"
        )
        return

    # Step 2: Mark running
    _update_job(job_id, "running")
    start_time = time.time()

    llm_meta: dict = {}

    try:
        # Step 3: Fetch fundamentals
        try:
            fundamentals = fetch_fundamentals(ticker)
        except DataFetchError as exc:
            _update_job(job_id, "failed", error=f"Data fetch failed: {exc}")
            duration_ms = int((time.time() - start_time) * 1000)
            log_analysis_cost(
                tenant_id, job_id, "dividend", ticker,
                duration_ms=duration_ms, status="failed",
            )
            return

        # Step 4: Calculate dividend analysis
        dividend_result = calculate_dividend_analysis(fundamentals)

        # Step 5: Call LLM for narrative
        narrative = _STATIC_FALLBACK_NARRATIVE_DIVIDEND
        try:
            yield_val = dividend_result.get("current_yield")
            yield_str = f"{yield_val:.1%}" if yield_val is not None else "N/A"
            payout = dividend_result.get("payout_ratio")
            payout_str = f"{payout:.1%}" if payout is not None else "N/A"
            coverage = dividend_result.get("coverage_ratio")
            coverage_str = f"{coverage:.2f}x" if coverage is not None else "N/A"
            sust = dividend_result.get("sustainability", "N/A")
            consistency = dividend_result.get("consistency", {})
            score = consistency.get("score", "N/A")

            prompt = (
                f"Resuma a analise de dividendos de {ticker}. "
                f"Yield: {yield_str}. "
                f"Payout: {payout_str}. "
                f"Cobertura: {coverage_str}. "
                f"Sustentabilidade: {sust}. "
                f"Consistencia: {score} de 5 anos. "
                f"Seja conciso, 2-3 frases em portugues."
            )
            narrative_text, llm_meta = asyncio.run(
                call_analysis_llm(prompt, max_tokens=300)
            )
            narrative = narrative_text
        except AIProviderError:
            logger.warning(
                "All LLM providers failed for dividend job %s — using static fallback",
                job_id,
            )
            cached = _get_cached_analysis_with_outdated_badge(ticker, "dividend")
            if cached and "narrative" in cached:
                narrative = cached["narrative"]

        # Step 6: Build result with versioning
        data_version_id = build_data_version_id()
        data_sources = get_data_sources()
        data_timestamp = datetime.now(timezone.utc).isoformat()

        result = {
            "ticker": ticker,
            "current_yield": dividend_result.get("current_yield"),
            "payout_ratio": dividend_result.get("payout_ratio"),
            "coverage_ratio": dividend_result.get("coverage_ratio"),
            "consistency": dividend_result.get("consistency", {}),
            "sustainability": dividend_result.get("sustainability"),
            "dividend_history": dividend_result.get("dividend_history", []),
            "narrative": narrative,
            "data_completeness": dividend_result.get("data_completeness", {}),
            "completeness_flag": get_completeness_flag(dividend_result.get("data_completeness", {})),
            "data_version_id": data_version_id,
            "data_timestamp": data_timestamp,
            "data_sources": data_sources,
            "disclaimer": CVM_DISCLAIMER_SHORT_PT,
        }

        # Step 7: Update job
        _update_job(job_id, "completed", result_json=json.dumps(result, ensure_ascii=False))
        _archive_superseded_job(ticker, tenant_id, "dividend", job_id)

        # Step 8: Log cost
        duration_ms = int((time.time() - start_time) * 1000)
        log_analysis_cost(
            tenant_id,
            job_id,
            "dividend",
            ticker,
            duration_ms=duration_ms,
            status="completed",
            llm_provider=llm_meta.get("provider_used"),
            llm_model=llm_meta.get("model"),
        )

        logger.info("Dividend analysis completed: job=%s ticker=%s", job_id, ticker)

    except Exception as exc:
        duration_ms = int((time.time() - start_time) * 1000)
        logger.error("Dividend analysis failed for job %s: %s", job_id, exc)
        _update_job(job_id, "failed", error=str(exc)[:500])
        log_analysis_cost(
            tenant_id,
            job_id,
            "dividend",
            ticker,
            duration_ms=duration_ms,
            status="failed",
        )


@shared_task(name="analysis.run_sector", bind=True, max_retries=0)
def run_sector(
    self,
    job_id: str,
    tenant_id: str,
    ticker: str,
    max_peers: int = 10,
) -> None:
    """Run sector peer comparison analysis as a Celery background task.

    Steps:
    1. Check quota
    2. Set status -> running
    3. Fetch target fundamentals from BRAPI
    4. Look up peer tickers from _SECTOR_TICKERS; if sector unmapped, fail gracefully
    5. Fetch peer fundamentals (skip failures)
    6. Calculate sector comparison
    7. Call LLM for narrative (PT-BR, 2-3 sentences)
    8. Build result with data versioning
    9. Update job status -> completed
    10. Log cost

    On any failure: status -> failed, cost logged.
    """
    logger.info("Sector analysis started: job=%s ticker=%s max_peers=%s", job_id, ticker, max_peers)

    # Step 1: Quota check
    if not _check_and_increment_quota(tenant_id):
        _update_job(job_id, "failed", error="Analysis quota exhausted")
        log_analysis_cost(
            tenant_id, job_id, "sector", ticker, duration_ms=0, status="failed"
        )
        return

    # Step 2: Mark running
    _update_job(job_id, "running")
    start_time = time.time()

    llm_meta: dict = {}

    try:
        # Step 3: Fetch target fundamentals
        try:
            target_fundamentals = fetch_fundamentals(ticker)
        except DataFetchError as exc:
            _update_job(job_id, "failed", error=f"Data fetch failed: {exc}")
            duration_ms = int((time.time() - start_time) * 1000)
            log_analysis_cost(
                tenant_id, job_id, "sector", ticker,
                duration_ms=duration_ms, status="failed",
            )
            return

        # Step 4: Look up peers from sector mapping
        sector_key = target_fundamentals.get("sector_key")
        if not sector_key:
            _update_job(job_id, "failed", error="Sector data unavailable for this ticker")
            duration_ms = int((time.time() - start_time) * 1000)
            log_analysis_cost(
                tenant_id, job_id, "sector", ticker,
                duration_ms=duration_ms, status="failed",
            )
            return

        peer_tickers_all = _SECTOR_TICKERS.get(sector_key)
        if not peer_tickers_all:
            _update_job(
                job_id, "failed",
                error=f"Sector '{sector_key}' is not mapped. Cannot find peers for {ticker}.",
            )
            duration_ms = int((time.time() - start_time) * 1000)
            log_analysis_cost(
                tenant_id, job_id, "sector", ticker,
                duration_ms=duration_ms, status="failed",
            )
            return

        # Exclude target ticker, limit to max_peers
        peer_tickers = [t for t in peer_tickers_all if t.upper() != ticker.upper()][:max_peers]

        # Step 5: Fetch peer fundamentals (skip failures)
        peer_fundamentals, missing_tickers = fetch_peer_fundamentals(peer_tickers, ticker)

        # Inject metadata for calculate_sector_comparison to use
        target_fundamentals = dict(target_fundamentals)
        target_fundamentals["_peers_attempted"] = len(peer_tickers)
        target_fundamentals["_max_peers"] = max_peers
        target_fundamentals["_missing_tickers"] = missing_tickers

        # Step 6: Calculate sector comparison
        sector_result = calculate_sector_comparison(target_fundamentals, peer_fundamentals, ticker)

        # Step 7: Call LLM for narrative
        narrative = _STATIC_FALLBACK_NARRATIVE_SECTOR
        try:
            tm = sector_result.get("target_metrics", {})
            sa = sector_result.get("sector_averages", {})
            sector_name = sector_result.get("sector", sector_key)
            peers_found = sector_result.get("peers_found", 0)

            pe_val = tm.get("pe_ratio")
            pb_val = tm.get("price_to_book")
            dy_val = tm.get("dividend_yield")
            roe_val = tm.get("roe")
            avg_pe = sa.get("pe_ratio")

            pe_str = f"{pe_val:.1f}" if pe_val is not None else "N/D"
            pb_str = f"{pb_val:.2f}" if pb_val is not None else "N/D"
            dy_str = f"{dy_val:.1%}" if dy_val is not None else "N/D"
            roe_str = f"{roe_val:.1%}" if roe_val is not None else "N/D"
            avg_pe_str = f"{avg_pe:.1f}" if avg_pe is not None else "N/D"

            prompt = (
                f"Compare {ticker} com seus pares do setor {sector_name} ({peers_found} empresas). "
                f"Metricas de {ticker}: P/L {pe_str}, P/VP {pb_str}, DY {dy_str}, ROE {roe_str}. "
                f"Media do setor: P/L {avg_pe_str}. "
                f"Seja conciso, 2-3 frases em Portugues (PT-BR), destacando pontos positivos e negativos relativos ao setor."
            )
            narrative_text, llm_meta = asyncio.run(
                call_analysis_llm(prompt, max_tokens=300)
            )
            narrative = narrative_text
        except AIProviderError:
            logger.warning(
                "All LLM providers failed for sector job %s — using static fallback",
                job_id,
            )
            cached = _get_cached_analysis_with_outdated_badge(ticker, "sector")
            if cached and "narrative" in cached:
                narrative = cached["narrative"]

        # Step 8: Build result with versioning
        data_version_id = build_data_version_id()
        data_sources = get_data_sources()
        data_timestamp = datetime.now(timezone.utc).isoformat()

        result = {
            "ticker": ticker,
            "sector": sector_result.get("sector"),
            "sector_key": sector_result.get("sector_key"),
            "peers_found": sector_result.get("peers_found"),
            "peers_attempted": sector_result.get("peers_attempted"),
            "max_peers": sector_result.get("max_peers"),
            "target_metrics": sector_result.get("target_metrics", {}),
            "sector_averages": sector_result.get("sector_averages", {}),
            "sector_medians": sector_result.get("sector_medians", {}),
            "target_percentiles": sector_result.get("target_percentiles", {}),
            "peers": sector_result.get("peers", []),
            "data_completeness": sector_result.get("data_completeness", {}),
            "completeness_flag": get_completeness_flag(
                {
                    "completeness": (
                        f"{int((sector_result.get('peers_with_data', 0) / sector_result.get('peers_attempted', 1)) * 100)}%"
                        if sector_result.get("peers_attempted", 0) > 0
                        else "0%"
                    )
                }
            ),
            "narrative": narrative,
            "data_version_id": data_version_id,
            "data_timestamp": data_timestamp,
            "data_sources": data_sources,
            "disclaimer": CVM_DISCLAIMER_SHORT_PT,
        }

        # Step 9: Update job
        _update_job(job_id, "completed", result_json=json.dumps(result, ensure_ascii=False))
        _archive_superseded_job(ticker, tenant_id, "sector", job_id)

        # Step 10: Log cost
        duration_ms = int((time.time() - start_time) * 1000)
        log_analysis_cost(
            tenant_id,
            job_id,
            "sector",
            ticker,
            duration_ms=duration_ms,
            status="completed",
            llm_provider=llm_meta.get("provider_used"),
            llm_model=llm_meta.get("model"),
        )

        logger.info("Sector analysis completed: job=%s ticker=%s peers=%s", job_id, ticker, sector_result.get("peers_found"))

    except Exception as exc:
        duration_ms = int((time.time() - start_time) * 1000)
        logger.error("Sector analysis failed for job %s: %s", job_id, exc)
        _update_job(job_id, "failed", error=str(exc)[:500])
        log_analysis_cost(
            tenant_id,
            job_id,
            "sector",
            ticker,
            duration_ms=duration_ms,
            status="failed",
        )


@shared_task(name="analysis.check_earnings_releases", bind=False)
def check_earnings_releases() -> dict:
    """Nightly Beat task to invalidate stale analyses after new filings."""
    from app.modules.analysis.invalidation import (
        get_analyzed_tickers_recent_7d,
        get_last_analysis_data_timestamp,
        on_earnings_release,
    )

    tickers = get_analyzed_tickers_recent_7d()[:50]
    invalidated = 0

    for ticker in tickers:
        filing_date = _fetch_latest_quarterly_filing_date(ticker)
        if filing_date is None:
            continue

        last_timestamp = get_last_analysis_data_timestamp(ticker)
        if last_timestamp is None:
            continue

        if last_timestamp.tzinfo is None:
            last_timestamp = last_timestamp.replace(tzinfo=timezone.utc)
        if filing_date.tzinfo is None:
            filing_date = filing_date.replace(tzinfo=timezone.utc)

        if filing_date > last_timestamp:
            invalidated += on_earnings_release(ticker, filing_date)

    logger.info(
        "check_earnings_releases invalidated=%d tickers_checked=%d",
        invalidated,
        len(tickers),
    )
    return {
        "tickers_checked": len(tickers),
        "analyses_invalidated": invalidated,
    }
