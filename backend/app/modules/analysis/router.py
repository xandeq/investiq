"""FastAPI router for /analysis endpoints (Phase 12).

POST /analysis/dcf  — create DCF analysis job, return job_id (202)
GET  /analysis/{job_id} — get analysis result with CVM disclaimer
"""

import json
import logging
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.middleware import get_authed_db, get_current_tenant_id
from app.core.plan_gate import get_user_plan
from app.core.rate_limit import check_analysis_rate_limit
from app.core.security import get_current_user
from app.modules.analysis.constants import CVM_DISCLAIMER_SHORT_PT
from app.modules.analysis.models import AnalysisCostLog, AnalysisJob
from app.modules.analysis.quota import check_analysis_quota, increment_quota_used
from app.modules.analysis.schemas import (
    AnalysisHistoryItem,
    AnalysisJobStatus,
    AnalysisResponse,
    DCFRequest,
    DividendRequest,
    EarningsRequest,
    FIIAnalysisRequest,
    SectorRequest,
)
from app.modules.analysis.versioning import build_data_version_id, get_data_sources

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post(
    "/dcf",
    response_model=AnalysisJobStatus,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Solicitar análise DCF (Discounted Cash Flow)",
    tags=["analysis"],
)
async def request_dcf_analysis(
    body: DCFRequest,
    current_user: dict = Depends(get_current_user),
    plan: str = Depends(get_user_plan),
    db: AsyncSession = Depends(get_authed_db),
    tenant_id: str = Depends(get_current_tenant_id),
):
    """Request a DCF analysis for a given ticker.

    Returns 202 with job_id immediately. Poll GET /analysis/{job_id} until
    status == 'completed' or 'failed'.

    Guards:
    - Rate limiting: per-request cooldown based on plan tier
    - Quota enforcement: monthly limits per plan tier
    """
    # Step 1: Rate limiting
    allowed, retry_after = await check_analysis_rate_limit(tenant_id, plan)
    if not allowed:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail={
                "code": "RATE_LIMITED",
                "retry_after": retry_after,
            },
            headers={"Retry-After": str(retry_after)},
        )

    # Step 2: Quota enforcement
    quota_allowed, quota_used, quota_limit = check_analysis_quota(tenant_id, plan)
    if not quota_allowed:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "code": "QUOTA_EXCEEDED",
                "message": (
                    f"Você atingiu o limite de {quota_limit} análises deste mês. "
                    "Faça upgrade para continuar usando análises de IA."
                ),
                "quota_used": quota_used,
                "quota_limit": quota_limit,
                "upgrade_url": "/planos",
            },
        )

    # Step 3: Create AnalysisJob record
    now = datetime.now(tz=timezone.utc)
    job = AnalysisJob(
        tenant_id=tenant_id,
        analysis_type="dcf",
        ticker=body.ticker.upper(),
        data_timestamp=now,
        data_version_id=build_data_version_id(),
        data_sources=json.dumps(get_data_sources()),
        status="pending",
    )
    db.add(job)
    await db.commit()
    await db.refresh(job)

    # Increment quota after successful job creation
    increment_quota_used(tenant_id)

    logger.info(
        "analysis.job_created job_id=%s type=dcf ticker=%s tenant_id=%s",
        job.id, body.ticker, tenant_id,
    )

    # Step 4: Dispatch Celery task
    from app.celery_app import celery_app

    with celery_app.connection_for_write() as conn:
        celery_app.send_task(
            "analysis.run_dcf",
            kwargs={
                "job_id": job.id,
                "tenant_id": tenant_id,
                "ticker": body.ticker.upper(),
                "assumptions": {
                    "growth_rate": body.growth_rate,
                    "discount_rate": body.discount_rate,
                    "terminal_growth": body.terminal_growth,
                },
            },
            connection=conn,
        )

    return AnalysisJobStatus(
        job_id=job.id,
        status="pending",
        message="Analysis queued",
    )


@router.post(
    "/earnings",
    response_model=AnalysisJobStatus,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Solicitar análise de lucros (Earnings Quality)",
    tags=["analysis"],
)
async def request_earnings_analysis(
    body: EarningsRequest,
    current_user: dict = Depends(get_current_user),
    plan: str = Depends(get_user_plan),
    db: AsyncSession = Depends(get_authed_db),
    tenant_id: str = Depends(get_current_tenant_id),
):
    """Request an earnings quality analysis for a given ticker.

    Returns 202 with job_id immediately. Poll GET /analysis/{job_id} until
    status == 'completed' or 'failed'.
    """
    # Step 1: Rate limiting
    allowed, retry_after = await check_analysis_rate_limit(tenant_id, plan)
    if not allowed:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail={"code": "RATE_LIMITED", "retry_after": retry_after},
            headers={"Retry-After": str(retry_after)},
        )

    # Step 2: Quota enforcement
    quota_allowed, quota_used, quota_limit = check_analysis_quota(tenant_id, plan)
    if not quota_allowed:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "code": "QUOTA_EXCEEDED",
                "message": (
                    f"Voce atingiu o limite de {quota_limit} analises deste mes. "
                    "Faca upgrade para continuar usando analises de IA."
                ),
                "quota_used": quota_used,
                "quota_limit": quota_limit,
                "upgrade_url": "/planos",
            },
        )

    # Step 3: Create AnalysisJob record
    now = datetime.now(tz=timezone.utc)
    job = AnalysisJob(
        tenant_id=tenant_id,
        analysis_type="earnings",
        ticker=body.ticker.upper(),
        data_timestamp=now,
        data_version_id=build_data_version_id(),
        data_sources=json.dumps(get_data_sources()),
        status="pending",
    )
    db.add(job)
    await db.commit()
    await db.refresh(job)

    # Increment quota after successful job creation
    increment_quota_used(tenant_id)

    logger.info(
        "analysis.job_created job_id=%s type=earnings ticker=%s tenant_id=%s",
        job.id, body.ticker, tenant_id,
    )

    # Step 4: Dispatch Celery task
    from app.celery_app import celery_app

    with celery_app.connection_for_write() as conn:
        celery_app.send_task(
            "analysis.run_earnings",
            kwargs={
                "job_id": job.id,
                "tenant_id": tenant_id,
                "ticker": body.ticker.upper(),
            },
            connection=conn,
        )

    return AnalysisJobStatus(
        job_id=job.id,
        status="pending",
        message="Earnings analysis queued",
    )


@router.post(
    "/dividend",
    response_model=AnalysisJobStatus,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Solicitar análise de dividendos (Dividend Sustainability)",
    tags=["analysis"],
)
async def request_dividend_analysis(
    body: DividendRequest,
    current_user: dict = Depends(get_current_user),
    plan: str = Depends(get_user_plan),
    db: AsyncSession = Depends(get_authed_db),
    tenant_id: str = Depends(get_current_tenant_id),
):
    """Request a dividend sustainability analysis for a given ticker.

    Returns 202 with job_id immediately. Poll GET /analysis/{job_id} until
    status == 'completed' or 'failed'.
    """
    # Step 1: Rate limiting
    allowed, retry_after = await check_analysis_rate_limit(tenant_id, plan)
    if not allowed:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail={"code": "RATE_LIMITED", "retry_after": retry_after},
            headers={"Retry-After": str(retry_after)},
        )

    # Step 2: Quota enforcement
    quota_allowed, quota_used, quota_limit = check_analysis_quota(tenant_id, plan)
    if not quota_allowed:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "code": "QUOTA_EXCEEDED",
                "message": (
                    f"Voce atingiu o limite de {quota_limit} analises deste mes. "
                    "Faca upgrade para continuar usando analises de IA."
                ),
                "quota_used": quota_used,
                "quota_limit": quota_limit,
                "upgrade_url": "/planos",
            },
        )

    # Step 3: Create AnalysisJob record
    now = datetime.now(tz=timezone.utc)
    job = AnalysisJob(
        tenant_id=tenant_id,
        analysis_type="dividend",
        ticker=body.ticker.upper(),
        data_timestamp=now,
        data_version_id=build_data_version_id(),
        data_sources=json.dumps(get_data_sources()),
        status="pending",
    )
    db.add(job)
    await db.commit()
    await db.refresh(job)

    # Increment quota after successful job creation
    increment_quota_used(tenant_id)

    logger.info(
        "analysis.job_created job_id=%s type=dividend ticker=%s tenant_id=%s",
        job.id, body.ticker, tenant_id,
    )

    # Step 4: Dispatch Celery task
    from app.celery_app import celery_app

    with celery_app.connection_for_write() as conn:
        celery_app.send_task(
            "analysis.run_dividend",
            kwargs={
                "job_id": job.id,
                "tenant_id": tenant_id,
                "ticker": body.ticker.upper(),
            },
            connection=conn,
        )

    return AnalysisJobStatus(
        job_id=job.id,
        status="pending",
        message="Dividend analysis queued",
    )


@router.post(
    "/sector",
    response_model=AnalysisJobStatus,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Solicitar análise de comparação setorial (Sector Peer Comparison)",
    tags=["analysis"],
)
async def request_sector_analysis(
    body: SectorRequest,
    current_user: dict = Depends(get_current_user),
    plan: str = Depends(get_user_plan),
    db: AsyncSession = Depends(get_authed_db),
    tenant_id: str = Depends(get_current_tenant_id),
):
    """Request a sector peer comparison analysis for a given ticker.

    Returns 202 with job_id immediately. Poll GET /analysis/{job_id} until
    status == 'completed' or 'failed'.
    """
    # Step 1: Rate limiting
    allowed, retry_after = await check_analysis_rate_limit(tenant_id, plan)
    if not allowed:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail={"code": "RATE_LIMITED", "retry_after": retry_after},
            headers={"Retry-After": str(retry_after)},
        )

    # Step 2: Quota enforcement
    quota_allowed, quota_used, quota_limit = check_analysis_quota(tenant_id, plan)
    if not quota_allowed:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "code": "QUOTA_EXCEEDED",
                "message": (
                    f"Voce atingiu o limite de {quota_limit} analises deste mes. "
                    "Faca upgrade para continuar usando analises de IA."
                ),
                "quota_used": quota_used,
                "quota_limit": quota_limit,
                "upgrade_url": "/planos",
            },
        )

    # Step 3: Create AnalysisJob record
    now = datetime.now(tz=timezone.utc)
    job = AnalysisJob(
        tenant_id=tenant_id,
        analysis_type="sector",
        ticker=body.ticker.upper(),
        data_timestamp=now,
        data_version_id=build_data_version_id(),
        data_sources=json.dumps(get_data_sources()),
        status="pending",
    )
    db.add(job)
    await db.commit()
    await db.refresh(job)

    # Increment quota after successful job creation
    increment_quota_used(tenant_id)

    logger.info(
        "analysis.job_created job_id=%s type=sector ticker=%s tenant_id=%s max_peers=%s",
        job.id, body.ticker, tenant_id, body.max_peers,
    )

    # Step 4: Dispatch Celery task
    from app.celery_app import celery_app

    with celery_app.connection_for_write() as conn:
        celery_app.send_task(
            "analysis.run_sector",
            kwargs={
                "job_id": job.id,
                "tenant_id": tenant_id,
                "ticker": body.ticker.upper(),
                "max_peers": body.max_peers,
            },
            connection=conn,
        )

    return AnalysisJobStatus(
        job_id=job.id,
        status="pending",
        message="Sector analysis queued",
    )


@router.post(
    "/fii/{ticker}",
    response_model=AnalysisJobStatus,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Solicitar análise de FII",
    tags=["analysis"],
)
async def request_fii_analysis(
    ticker: str,
    current_user: dict = Depends(get_current_user),
    plan: str = Depends(get_user_plan),
    db: AsyncSession = Depends(get_authed_db),
    tenant_id: str = Depends(get_current_tenant_id),
):
    """Request a FII detail analysis for a given ticker.

    Returns 202 with job_id immediately. Poll GET /analysis/{job_id} until
    status == 'completed' or 'failed'. Available to all plan tiers (no premium gate).
    """
    # Step 1: Rate limiting
    allowed, retry_after = await check_analysis_rate_limit(tenant_id, plan)
    if not allowed:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail={"code": "RATE_LIMITED", "retry_after": retry_after},
            headers={"Retry-After": str(retry_after)},
        )

    # Step 2: Quota enforcement
    quota_allowed, quota_used, quota_limit = check_analysis_quota(tenant_id, plan)
    if not quota_allowed:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "code": "QUOTA_EXCEEDED",
                "message": (
                    f"Você atingiu o limite de {quota_limit} análises deste mês. "
                    "Faça upgrade para continuar usando análises de IA."
                ),
                "quota_used": quota_used,
                "quota_limit": quota_limit,
                "upgrade_url": "/planos",
            },
        )

    # Step 3: Create AnalysisJob record
    now = datetime.now(tz=timezone.utc)
    job = AnalysisJob(
        tenant_id=tenant_id,
        analysis_type="fii_detail",
        ticker=ticker.upper(),
        data_timestamp=now,
        data_version_id=build_data_version_id(),
        data_sources=json.dumps(get_data_sources()),
        status="pending",
    )
    db.add(job)
    await db.commit()
    await db.refresh(job)

    # Increment quota after successful job creation
    increment_quota_used(tenant_id)

    logger.info(
        "analysis.job_created job_id=%s type=fii_detail ticker=%s tenant_id=%s",
        job.id, ticker, tenant_id,
    )

    # Step 4: Dispatch Celery task
    from app.celery_app import celery_app

    with celery_app.connection_for_write() as conn:
        celery_app.send_task(
            "analysis.run_fii_analysis",
            kwargs={
                "job_id": job.id,
                "tenant_id": tenant_id,
                "ticker": ticker.upper(),
            },
            connection=conn,
        )

    return AnalysisJobStatus(
        job_id=job.id,
        status="pending",
        message="FII analysis queued",
    )


@router.get(
    "/admin/costs",
    summary="Custo por tipo e por dia (admin)",
    tags=["analysis"],
)
async def get_admin_costs(
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_authed_db),
    tenant_id: str = Depends(get_current_tenant_id),
    days: int = Query(default=7, ge=1, le=90),
):
    """Get aggregated LLM cost data for the current tenant.

    Returns cost aggregated by analysis type and by day.
    Query param: days (1-90, default 7).
    """
    cutoff = datetime.now(tz=timezone.utc) - timedelta(days=days)

    # Aggregate by analysis_type
    by_type_result = await db.execute(
        select(
            AnalysisCostLog.analysis_type,
            func.count(AnalysisCostLog.id).label("count"),
            func.avg(AnalysisCostLog.duration_ms).label("avg_duration_ms"),
            func.sum(AnalysisCostLog.estimated_cost_usd).label("total_cost_usd"),
        )
        .where(
            AnalysisCostLog.tenant_id == tenant_id,
            AnalysisCostLog.created_at >= cutoff,
        )
        .group_by(AnalysisCostLog.analysis_type)
    )
    by_type_rows = by_type_result.all()

    # Aggregate by day
    by_day_result = await db.execute(
        select(
            func.date(AnalysisCostLog.created_at).label("date"),
            func.count(AnalysisCostLog.id).label("count"),
            func.sum(AnalysisCostLog.estimated_cost_usd).label("total_cost_usd"),
        )
        .where(
            AnalysisCostLog.tenant_id == tenant_id,
            AnalysisCostLog.created_at >= cutoff,
        )
        .group_by(func.date(AnalysisCostLog.created_at))
        .order_by(func.date(AnalysisCostLog.created_at).desc())
    )
    by_day_rows = by_day_result.all()

    total_analyses = sum(row.count for row in by_type_rows)
    total_cost_usd = float(
        sum(float(row.total_cost_usd or 0) for row in by_type_rows)
    )

    return {
        "period_days": days,
        "by_type": [
            {
                "analysis_type": row.analysis_type,
                "count": row.count,
                "avg_duration_ms": int(row.avg_duration_ms or 0),
                "total_cost_usd": float(row.total_cost_usd or 0),
            }
            for row in by_type_rows
        ],
        "by_day": [
            {
                "date": str(row.date),
                "count": row.count,
                "total_cost_usd": float(row.total_cost_usd or 0),
            }
            for row in by_day_rows
        ],
        "total_analyses": total_analyses,
        "total_cost_usd": round(total_cost_usd, 6),
    }


@router.get(
    "/history/{ticker}",
    response_model=list[AnalysisHistoryItem],
    summary="Histórico de análises para um ticker",
    tags=["analysis"],
)
async def get_ticker_analysis_history(
    ticker: str,
    analysis_type: str | None = Query(default=None, description="Filtrar por tipo: dcf|earnings|dividend|sector"),
    limit: int = Query(default=10, ge=1, le=50, description="Máximo de itens (1-50)"),
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_authed_db),
    tenant_id: str = Depends(get_current_tenant_id),
):
    """Return past analyses for a ticker, newest first.

    Includes completed and stale analyses. Tenant-scoped.
    Use compute_analysis_diff() on consecutive results to surface changes.
    """
    from app.modules.analysis.history import get_analysis_history

    history = get_analysis_history(
        ticker=ticker,
        tenant_id=tenant_id,
        analysis_type=analysis_type,
        limit=limit,
    )
    return [AnalysisHistoryItem(**item) for item in history]


@router.get(
    "/{job_id}",
    response_model=AnalysisResponse,
    summary="Obter resultado de análise",
    tags=["analysis"],
)
async def get_analysis_result(
    job_id: str,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_authed_db),
    tenant_id: str = Depends(get_current_tenant_id),
):
    """Get analysis result by job ID.

    Returns the analysis result with CVM disclaimer.
    Only returns jobs belonging to the authenticated tenant.
    """
    result = await db.execute(
        select(AnalysisJob).where(
            AnalysisJob.id == job_id,
            AnalysisJob.tenant_id == tenant_id,
        )
    )
    job = result.scalar_one_or_none()

    if job is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Analysis job not found",
        )

    # Parse result JSON if available
    result_data = None
    if job.result_json:
        try:
            result_data = json.loads(job.result_json)
        except (json.JSONDecodeError, TypeError):
            logger.warning("Failed to parse result_json for job %s", job_id)

    # Parse data sources
    data_sources = []
    if job.data_sources:
        try:
            data_sources = json.loads(job.data_sources)
        except (json.JSONDecodeError, TypeError):
            pass

    return AnalysisResponse(
        analysis_id=job.id,
        analysis_type=job.analysis_type,
        ticker=job.ticker,
        status=job.status,
        result=result_data,
        disclaimer=CVM_DISCLAIMER_SHORT_PT,
        error_message=job.error_message,
    )
