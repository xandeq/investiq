"""AI Analysis Engine router.

Endpoints:
  POST /ai/analyze/{ticker}   — request asset analysis (202 + job_id); premium only
  POST /ai/analyze/macro      — request macro portfolio analysis (202 + job_id); premium only
  GET  /ai/jobs/{job_id}      — poll job status + result
  GET  /ai/jobs               — list last 10 jobs for current tenant

Design notes:
- Premium gate: free users receive 403 with an upgrade message.
- Rate limit: 5 AI requests per user per hour (slowapi + Redis).
- Job creation: writes a "pending" row to ai_analysis_jobs, dispatches Celery task,
  returns 202 immediately. The task writes "completed"/"failed" back to the same row.
- Plan is read from the users table (not the JWT payload) — JWT only carries user_id
  and tenant_id for minimal surface area.
- Macro analysis fetches the authenticated user's portfolio allocation from
  PortfolioService so the LLM receives real context.
"""

import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger(__name__)

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.limiter import limiter
from app.core.middleware import get_authed_db, get_current_tenant_id
from app.core.plan_gate import get_user_plan
from app.core.security import get_current_user
from app.modules.ai.models import AIAnalysisJob
from app.modules.ai.schemas import (
    JobResponse,
    JobResultResponse,
)
from app.modules.auth.models import User
from app.modules.portfolio.service import PortfolioService

router = APIRouter()

_UPGRADE_MESSAGE = (
    "Análise IA é um recurso Premium. "
    "Faça upgrade para acessar DCF, valuation e análise de impacto macro."
)

_NOT_FOUND_MESSAGE = "Job não encontrado."


def _get_portfolio_service() -> PortfolioService:
    """Dependency: return a stateless PortfolioService instance."""
    return PortfolioService()


def _get_redis():
    """Dependency: async Redis client for portfolio price enrichment."""
    import redis.asyncio as aioredis
    from app.core.config import settings
    return aioredis.from_url(settings.REDIS_URL, decode_responses=False)



async def _get_tier(
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_authed_db),
) -> str:
    """Dependency: return the LLM routing tier for the current user.

    "admin" — admin emails: free pool first, paid as last resort.
    "ultra" — pro users with ai_mode="ultra": premium model chain.
    "paid"  — pro users with ai_mode="standard": paid chain first, free as fallback.
    "free"  — free-plan / trial users: free pool only.
    """
    from app.core.config import settings
    user_id = current_user["user_id"]
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if user is None:
        return "free"  # safe default
    if user.email in settings.ADMIN_EMAILS:
        return "admin"
    if user.plan == "pro":
        ai_mode = getattr(user, "ai_mode", "standard") or "standard"
        return "ultra" if ai_mode == "ultra" else "paid"
    return "free"  # free plan or active trial


def _require_premium(plan: str) -> None:
    """Raise 403 if user is on the free plan."""
    if plan == "free":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=_UPGRADE_MESSAGE,
        )


def _dispatch_asset_analysis(job: AIAnalysisJob, tier: str = "free") -> None:
    from app.celery_app import celery_app
    with celery_app.connection_for_write() as conn:
        celery_app.send_task("ai.run_asset_analysis", args=[job.id, job.ticker, job.tenant_id, tier], connection=conn)


def _dispatch_macro_analysis(job: AIAnalysisJob, allocation: list[dict], tier: str = "free") -> None:
    from app.celery_app import celery_app
    with celery_app.connection_for_write() as conn:
        celery_app.send_task("ai.run_macro_analysis", args=[job.id, job.tenant_id, allocation, tier], connection=conn)


def _dispatch_portfolio_analysis(job: AIAnalysisJob, positions: list, pnl: dict, allocation: list, tier: str = "free") -> None:
    from app.celery_app import celery_app
    with celery_app.connection_for_write() as conn:
        celery_app.send_task("ai.run_portfolio_analysis", args=[job.id, job.tenant_id, positions, pnl, allocation, tier], connection=conn)


@router.post(
    "/analyze/macro",
    response_model=JobResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Request AI macro portfolio analysis (premium only)",
)
@limiter.limit("5/hour")
async def request_macro_analysis(
    request: Request,
    db: AsyncSession = Depends(get_authed_db),
    tenant_id: str = Depends(get_current_tenant_id),
    plan: str = Depends(get_user_plan),
    tier: str = Depends(_get_tier),
    portfolio_service: PortfolioService = Depends(_get_portfolio_service),
    redis_client=Depends(_get_redis),
) -> JobResponse:
    """Submit an async AI macro portfolio analysis request.

    Fetches the authenticated user's current portfolio allocation and
    passes it to the Celery macro analysis task as context.

    Returns 202 Accepted immediately with a job_id.
    Poll GET /ai/jobs/{job_id} for status + result.

    Raises:
        403: If user is on the free plan.
        429: If rate limit exceeded (5 requests/hour).
    """
    _require_premium(plan)

    # Fetch current portfolio allocation for macro context
    try:
        pnl = await portfolio_service.get_pnl(db, tenant_id, redis_client)
        allocation = [
            {
                "asset_class": item.asset_class,
                "total_value": str(item.total_value),
                "percentage": str(item.percentage),
            }
            for item in pnl.allocation
        ]
    except Exception:
        # Portfolio fetch failure is non-fatal — macro analysis still runs without context
        allocation = []

    job = AIAnalysisJob(
        id=str(uuid.uuid4()),
        tenant_id=tenant_id,
        job_type="macro",
        ticker=None,
        status="pending",
        created_at=datetime.now(timezone.utc),
    )
    db.add(job)
    await db.flush()
    await db.commit()  # commit before dispatching so the worker finds the row

    try:
        _dispatch_macro_analysis(job, allocation, tier)
    except Exception as exc:
        logger.error("Failed to dispatch macro analysis task for job %s: %s", job.id, exc)

    return JobResponse(
        id=job.id,
        job_type=job.job_type,
        ticker=job.ticker,
        status=job.status,
        created_at=job.created_at,
        completed_at=job.completed_at,
        error_message=job.error_message,
    )


@router.post(
    "/analyze/portfolio",
    response_model=JobResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Request AI full portfolio analysis (premium only)",
)
@limiter.limit("5/hour")
async def request_portfolio_analysis(
    request: Request,
    db: AsyncSession = Depends(get_authed_db),
    tenant_id: str = Depends(get_current_tenant_id),
    plan: str = Depends(get_user_plan),
    tier: str = Depends(_get_tier),
    portfolio_service: PortfolioService = Depends(_get_portfolio_service),
    redis_client=Depends(_get_redis),
) -> JobResponse:
    """Submit an async AI portfolio advisor analysis request.

    Fetches current positions, P&L and allocation to build full context.
    The LLM produces a structured diagnosis with positives, concerns, suggestions.

    Returns 202 Accepted immediately with a job_id.
    Poll GET /ai/jobs/{job_id} for status + result.

    Raises:
        403: If user is on the free plan.
        429: If rate limit exceeded (5 requests/hour).
    """
    _require_premium(plan)

    try:
        pnl_data = await portfolio_service.get_pnl(db, tenant_id, redis_client)
        positions = [
            {
                "ticker": p.ticker,
                "asset_class": p.asset_class,
                "quantity": str(p.quantity),
                "cmp": str(p.cmp),
                "total_cost": str(p.total_cost),
                "current_price": str(p.current_price) if p.current_price else None,
                "unrealized_pnl": str(p.unrealized_pnl) if p.unrealized_pnl else None,
                "unrealized_pnl_pct": str(p.unrealized_pnl_pct) if p.unrealized_pnl_pct else None,
            }
            for p in pnl_data.positions
        ]
        pnl = {
            "realized_pnl_total": str(pnl_data.realized_pnl_total),
            "unrealized_pnl_total": str(pnl_data.unrealized_pnl_total),
            "total_portfolio_value": str(pnl_data.total_portfolio_value),
        }
        allocation = [
            {
                "asset_class": item.asset_class,
                "total_value": str(item.total_value),
                "percentage": str(item.percentage),
            }
            for item in pnl_data.allocation
        ]
    except Exception:
        positions, pnl, allocation = [], {}, []

    job = AIAnalysisJob(
        id=str(uuid.uuid4()),
        tenant_id=tenant_id,
        job_type="portfolio",
        ticker=None,
        status="pending",
        created_at=datetime.now(timezone.utc),
    )
    db.add(job)
    await db.flush()
    await db.commit()  # commit before dispatching so the worker finds the row

    try:
        _dispatch_portfolio_analysis(job, positions, pnl, allocation, tier)
    except Exception as exc:
        logger.error("Failed to dispatch portfolio analysis task for job %s: %s", job.id, exc)

    return JobResponse(
        id=job.id,
        job_type=job.job_type,
        ticker=job.ticker,
        status=job.status,
        created_at=job.created_at,
        completed_at=job.completed_at,
        error_message=job.error_message,
    )


@router.post(
    "/analyze/{ticker}",
    response_model=JobResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Request AI asset analysis (premium only)",
)
@limiter.limit("5/hour")
async def request_asset_analysis(
    request: Request,
    ticker: str,
    db: AsyncSession = Depends(get_authed_db),
    tenant_id: str = Depends(get_current_tenant_id),
    plan: str = Depends(get_user_plan),
    tier: str = Depends(_get_tier),
) -> JobResponse:
    """Submit an async AI analysis request for a B3 asset.

    Returns 202 Accepted immediately with a job_id.
    Poll GET /ai/jobs/{job_id} for status + result.

    Raises:
        403: If user is on the free plan.
        429: If rate limit exceeded (5 requests/hour).
    """
    _require_premium(plan)

    job = AIAnalysisJob(
        id=str(uuid.uuid4()),
        tenant_id=tenant_id,
        job_type="asset",
        ticker=ticker.upper(),
        status="pending",
        created_at=datetime.now(timezone.utc),
    )
    db.add(job)
    await db.flush()
    await db.commit()  # commit before dispatching so the worker finds the row

    try:
        _dispatch_asset_analysis(job, tier)
    except Exception as exc:
        logger.error("Failed to dispatch asset analysis task for job %s: %s", job.id, exc)

    return JobResponse(
        id=job.id,
        job_type=job.job_type,
        ticker=job.ticker,
        status=job.status,
        created_at=job.created_at,
        completed_at=job.completed_at,
        error_message=job.error_message,
    )


@router.get(
    "/jobs/{job_id}",
    response_model=JobResultResponse,
    summary="Poll AI job status and retrieve result",
)
async def get_job(
    job_id: str,
    db: AsyncSession = Depends(get_authed_db),
    tenant_id: str = Depends(get_current_tenant_id),
) -> JobResultResponse:
    """Return the current status of an AI analysis job.

    If status == 'completed', the result dict is included.
    If status == 'pending' or 'running', result is null.
    If status == 'failed', result is null and error is stored internally.

    Raises:
        404: If job not found or does not belong to the authenticated tenant.
    """
    result = await db.execute(
        select(AIAnalysisJob).where(
            AIAnalysisJob.id == job_id,
            AIAnalysisJob.tenant_id == tenant_id,
        )
    )
    job = result.scalar_one_or_none()
    if job is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=_NOT_FOUND_MESSAGE,
        )

    parsed_result: dict[str, Any] | None = None
    if job.status == "completed" and job.result_json:
        try:
            parsed_result = json.loads(job.result_json)
        except json.JSONDecodeError:
            parsed_result = None

    return JobResultResponse(
        id=job.id,
        job_type=job.job_type,
        ticker=job.ticker,
        status=job.status,
        created_at=job.created_at,
        completed_at=job.completed_at,
        result=parsed_result,
        error_message=job.error_message,
    )


@router.get(
    "/jobs",
    response_model=list[JobResponse],
    summary="List recent AI analysis jobs for current tenant",
)
async def list_jobs(
    db: AsyncSession = Depends(get_authed_db),
    tenant_id: str = Depends(get_current_tenant_id),
) -> list[JobResponse]:
    """Return the last 10 AI analysis jobs for the authenticated tenant.

    Jobs are ordered by created_at descending (newest first).
    """
    result = await db.execute(
        select(AIAnalysisJob)
        .where(AIAnalysisJob.tenant_id == tenant_id)
        .order_by(AIAnalysisJob.created_at.desc())
        .limit(10)
    )
    jobs = result.scalars().all()

    return [
        JobResponse(
            id=j.id,
            job_type=j.job_type,
            ticker=j.ticker,
            status=j.status,
            created_at=j.created_at,
            completed_at=j.completed_at,
            error_message=j.error_message,
        )
        for j in jobs
    ]
