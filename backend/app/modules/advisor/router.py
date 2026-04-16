"""FastAPI router for /advisor endpoints (Phase 23 — ADVI-01, ADVI-02).

GET  /advisor/health          — synchronous portfolio health (4 metrics, no AI)
POST /advisor/analyze         — start async AI narrative job
GET  /advisor/{job_id}        — poll job status + result

Job persistence: reuses WizardJob table with perfil="advisor" as discriminator.
CVM compliance: disclaimer mandatory in all responses that involve AI output.
"""
from __future__ import annotations

import json
import logging

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.limiter import limiter
from app.core.middleware import get_authed_db, get_current_tenant_id
from app.core.db import get_global_db
from app.core.plan_gate import get_user_plan
from app.core.security import get_current_user
from app.modules.advisor.schemas import (
    AdvisorJobResponse,
    AdvisorResult,
    AdvisorStartResponse,
    CVM_DISCLAIMER,
    PortfolioHealth,
)
from app.modules.advisor.service import compute_portfolio_health
from app.modules.wizard.models import WizardJob

logger = logging.getLogger(__name__)
router = APIRouter()

# WizardJob discriminator for advisor jobs
_ADVISOR_PERFIL = "advisor"


# ── GET /advisor/health ────────────────────────────────────────────────────────

@limiter.limit("30/minute")
@router.get(
    "/health",
    response_model=PortfolioHealth,
    summary="Saúde da carteira — 4 métricas determinísticas, sem IA",
    tags=["advisor"],
)
async def get_portfolio_health(
    request: Request,
    current_user: dict = Depends(get_current_user),
    tenant_db: AsyncSession = Depends(get_authed_db),
    global_db: AsyncSession = Depends(get_global_db),
    tenant_id: str = Depends(get_current_tenant_id),
) -> PortfolioHealth:
    """Compute portfolio health synchronously.

    Returns health_score (0-100), biggest_risk (one sentence or null),
    passive_income_monthly_brl (TTM ÷ 12), underperformers (max 3 tickers),
    and data_as_of (screener snapshot date — staleness signal).

    No AI involved. Target latency: <300ms.
    """
    return await compute_portfolio_health(
        tenant_db=tenant_db,
        global_db=global_db,
        tenant_id=tenant_id,
    )


# ── POST /advisor/analyze ──────────────────────────────────────────────────────

@limiter.limit("3/minute")
@router.post(
    "/analyze",
    response_model=AdvisorStartResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Iniciar análise IA da carteira (educacional, CVM-compliant)",
    tags=["advisor"],
)
async def start_advisor(
    request: Request,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_authed_db),
    tenant_id: str = Depends(get_current_tenant_id),
    plan: str = Depends(get_user_plan),
) -> AdvisorStartResponse:
    """Start an async AI portfolio analysis job.

    Returns 202 with job_id immediately. Poll GET /advisor/{job_id} for result.

    Rate limit: 3/minute — AI calls are expensive; prevents abuse.
    CVM compliance: disclaimer always present in all responses.
    """
    job = WizardJob(
        tenant_id=tenant_id,
        perfil=_ADVISOR_PERFIL,  # discriminator: advisor vs wizard
        prazo="n/a",
        valor=0.0,
        status="pending",
    )
    db.add(job)
    await db.flush()
    job_id = job.id
    await db.commit()

    use_free_tier = plan not in ("pro", "enterprise")
    try:
        from app.celery_app import celery_app
        celery_app.send_task(
            "advisor.run_analysis",
            args=[job_id, tenant_id, use_free_tier],
        )
    except Exception as exc:
        logger.warning("Advisor task dispatch failed for job %s: %s", job_id, exc)

    return AdvisorStartResponse(job_id=job_id, status="pending")


# ── GET /advisor/{job_id} ──────────────────────────────────────────────────────

@limiter.limit("60/minute")
@router.get(
    "/{job_id}",
    response_model=AdvisorJobResponse,
    summary="Consultar status e resultado da análise de portfólio",
    tags=["advisor"],
)
async def get_advisor_job(
    request: Request,
    job_id: str,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_authed_db),
    tenant_id: str = Depends(get_current_tenant_id),
) -> AdvisorJobResponse:
    """Poll advisor job status.

    Returns status 'pending' | 'running' | 'completed' | 'failed'.
    When completed, result contains AI narrative + health snapshot.
    """
    row = await db.execute(
        select(WizardJob).where(
            WizardJob.id == job_id,
            WizardJob.tenant_id == tenant_id,
            WizardJob.perfil == _ADVISOR_PERFIL,
        )
    )
    job = row.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="Advisor job not found")

    result: AdvisorResult | None = None
    if job.status == "completed" and job.result_json:
        try:
            data = json.loads(job.result_json)
            result = AdvisorResult(**data)
        except Exception as exc:
            logger.warning("Failed to parse advisor result for job %s: %s", job.id, exc)

    return AdvisorJobResponse(
        job_id=job.id,
        status=job.status,
        disclaimer=CVM_DISCLAIMER,
        result=result,
        error_message=job.error_message,
        created_at=job.created_at,
        completed_at=job.completed_at,
    )
