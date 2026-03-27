"""FastAPI router for /wizard endpoints (Phase 11 — WIZ-01 through WIZ-05).

POST /wizard/start  — create wizard job, dispatch Celery task, return job_id
GET  /wizard/{job_id} — poll job status and result
"""
import json
import logging

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.limiter import limiter
from app.core.middleware import get_authed_db, get_current_tenant_id
from app.core.plan_gate import get_user_plan
from app.core.security import get_current_user
from app.modules.wizard.models import WizardJob
from app.modules.wizard.schemas import (
    WizardJobResponse,
    WizardResult,
    WizardStartRequest,
    WizardStartResponse,
    CVM_DISCLAIMER,
)

logger = logging.getLogger(__name__)
router = APIRouter()


def _dispatch(job: WizardJob, use_free_tier: bool) -> None:
    from app.celery_app import celery_app
    celery_app.send_task(
        "wizard.run_recommendation",
        args=[job.id, job.tenant_id, job.perfil, job.prazo, float(job.valor), use_free_tier],
    )


def _job_to_response(job: WizardJob) -> WizardJobResponse:
    result = None
    if job.status == "completed" and job.result_json:
        try:
            data = json.loads(job.result_json)
            result = WizardResult(**data)
        except Exception as exc:
            logger.warning("Failed to parse wizard result for job %s: %s", job.id, exc)

    return WizardJobResponse(
        job_id=job.id,
        status=job.status,
        perfil=job.perfil,
        prazo=job.prazo,
        valor=float(job.valor),
        disclaimer=CVM_DISCLAIMER,
        result=result,
        error_message=job.error_message,
        created_at=job.created_at,
        completed_at=job.completed_at,
    )


@router.post(
    "/start",
    response_model=WizardStartResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Iniciar recomendação de alocação via IA (Wizard Onde Investir)",
    tags=["wizard"],
)
@limiter.limit("5/minute")
async def start_wizard(
    request: Request,
    body: WizardStartRequest,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_authed_db),
    tenant_id: str = Depends(get_current_tenant_id),
    plan: str = Depends(get_user_plan),
) -> WizardStartResponse:
    """Start an AI allocation recommendation job.

    Returns 202 with job_id immediately. Poll GET /wizard/{job_id} until
    status == 'completed' or 'failed'.

    WIZ-03: CVM disclaimer is returned in the response — UI must display it
    before showing any result.
    """
    job = WizardJob(
        tenant_id=tenant_id,
        perfil=body.perfil,
        prazo=body.prazo,
        valor=body.valor,
        status="pending",
    )
    db.add(job)
    await db.flush()
    job_id = job.id
    await db.commit()

    use_free_tier = plan not in ("pro", "enterprise")
    try:
        _dispatch(job, use_free_tier)
    except Exception as exc:
        logger.warning("Wizard task dispatch failed for job %s: %s", job_id, exc)

    return WizardStartResponse(job_id=job_id, status="pending")


@router.get(
    "/{job_id}",
    response_model=WizardJobResponse,
    summary="Consultar status e resultado do Wizard",
    tags=["wizard"],
)
@limiter.limit("30/minute")
async def get_wizard_job(
    request: Request,
    job_id: str,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_authed_db),
    tenant_id: str = Depends(get_current_tenant_id),
) -> WizardJobResponse:
    """Poll wizard job status.

    Returns status 'pending' | 'running' | 'completed' | 'failed'.
    When completed, result contains the AI allocation recommendation.

    WIZ-02: allocation field contains only asset class percentages — no tickers.
    WIZ-05: macro field contains the SELIC/CDI/IPCA context used in the analysis.
    """
    result = await db.execute(
        select(WizardJob).where(
            WizardJob.id == job_id,
            WizardJob.tenant_id == tenant_id,
        )
    )
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="Wizard job not found")

    return _job_to_response(job)
