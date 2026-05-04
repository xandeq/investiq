"""FastAPI router for /advisor endpoints (Phase 23 — ADVI-01, ADVI-02 + Action Inbox v1).

GET  /advisor/health          — synchronous portfolio health (4 metrics, no AI, cached 3600s)
POST /advisor/health/refresh  — bypass cache, compute fresh
GET  /advisor/inbox           — ranked decision cards from 5 existing sources
POST /advisor/analyze         — start async AI narrative job
GET  /advisor/{job_id}        — poll job status + result
GET  /advisor/screener        — complementary assets (Phase 25 — ADVI-03)
GET  /advisor/signals/portfolio — on-demand entry signals (Phase 26 — ADVI-04)
GET  /advisor/signals/universe  — batch universe signals (Phase 26 — ADVI-04)

Job persistence: reuses WizardJob table with perfil="advisor" as discriminator.
CVM compliance: disclaimer mandatory in all responses that involve AI output.
Caching: Redis with TTL=3600 per tenant_id.
"""

import json
import logging
import os
from typing import Annotated

import redis as redis_lib
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
    EntrySignal,
    InboxResponse,
    PortfolioHealth,
)
from app.modules.advisor.service import (
    compute_inbox,
    compute_portfolio_health,
    get_complementary_assets,
    get_portfolio_entry_signals,
    get_universe_entry_signals,
    ComplementaryAssetRow,
)
from app.modules.wizard.models import WizardJob


def _get_inbox_redis():
    """Dependency: async Redis client used by the swing_signals source.

    Override in tests via app.dependency_overrides[_get_inbox_redis]. Import is
    deferred so test envs without redis installed don't fail at import time.
    Returning None makes the swing_signals source skip silently (still 200).
    """
    try:
        import redis.asyncio as aioredis
        from app.core.config import settings
        return aioredis.from_url(settings.REDIS_URL, decode_responses=False)
    except Exception:
        return None

logger = logging.getLogger(__name__)
router = APIRouter()


# ── Redis dependency ──────────────────────────────────────────────────────

def _get_redis():
    """Get Redis client for caching. Can be overridden in tests."""
    redis_url = os.environ.get("REDIS_URL", "redis://localhost:6379/0")
    return redis_lib.Redis.from_url(redis_url, decode_responses=True)

# WizardJob discriminator for advisor jobs
_ADVISOR_PERFIL = "advisor"


# ── GET /advisor/health ────────────────────────────────────────────────────────

@limiter.limit("30/minute")
@router.get(
    "/health",
    response_model=PortfolioHealth,
    summary="Saúde da carteira — 4 métricas determinísticas, sem IA (cached 3600s)",
    tags=["advisor"],
)
async def get_portfolio_health(
    request: Request,
    current_user: dict = Depends(get_current_user),
    tenant_db: AsyncSession = Depends(get_authed_db),
    global_db: AsyncSession = Depends(get_global_db),
    tenant_id: str = Depends(get_current_tenant_id),
) -> PortfolioHealth:
    """Compute portfolio health synchronously with Redis caching.

    Returns health_score (0-100), biggest_risk (one sentence or null),
    passive_income_monthly_brl (TTM ÷ 12), underperformers (max 3 tickers),
    and data_as_of (screener snapshot date — staleness signal).

    Cache TTL: 3600 seconds (1 hour) per tenant.
    No AI involved. Target latency: <300ms from cache.
    """
    tenant_id_str = tenant_id
    cache_key = f"portfolio_health:{tenant_id_str}"

    # Try to get from cache
    try:
        r = _get_redis()
        cached = r.get(cache_key)
        if cached:
            data = json.loads(cached)
            return PortfolioHealth(**data)
    except Exception as exc:
        logger.warning("get_portfolio_health: Redis error (will compute fresh): %s", exc)

    # Compute fresh
    health = await compute_portfolio_health(
        tenant_db=tenant_db,
        global_db=global_db,
        tenant_id=tenant_id_str,
    )

    # Cache result
    try:
        r = _get_redis()
        data_dict = health.model_dump(mode="json")
        r.setex(cache_key, 3600, json.dumps(data_dict))
    except Exception as exc:
        logger.error("get_portfolio_health: Failed to cache: %s", exc)

    return health


# ── POST /advisor/health/refresh ──────────────────────────────────────────────

@limiter.limit("10/minute")
@router.post(
    "/health/refresh",
    response_model=PortfolioHealth,
    summary="Atualizar saúde da carteira (bypass cache)",
    tags=["advisor"],
)
async def refresh_portfolio_health(
    request: Request,
    current_user: dict = Depends(get_current_user),
    tenant_db: AsyncSession = Depends(get_authed_db),
    global_db: AsyncSession = Depends(get_global_db),
    tenant_id: str = Depends(get_current_tenant_id),
) -> PortfolioHealth:
    """Compute fresh portfolio health, bypass cache.

    Clears the cached entry and returns newly computed result.
    Rate limit: 10/minute — refresh is less common than reads.
    """
    tenant_id_str = tenant_id
    cache_key = f"portfolio_health:{tenant_id_str}"

    # Clear cache
    try:
        r = _get_redis()
        r.delete(cache_key)
    except Exception as exc:
        logger.warning("refresh_portfolio_health: Failed to clear cache: %s", exc)

    # Compute fresh
    health = await compute_portfolio_health(
        tenant_db=tenant_db,
        global_db=global_db,
        tenant_id=tenant_id_str,
    )

    # Re-cache
    try:
        r = _get_redis()
        data_dict = health.model_dump(mode="json")
        r.setex(cache_key, 3600, json.dumps(data_dict))
    except Exception as exc:
        logger.error("refresh_portfolio_health: Failed to cache: %s", exc)

    return health


# ── GET /advisor/inbox ─────────────────────────────────────────────────────────

@limiter.limit("30/minute")
@router.get(
    "/inbox",
    response_model=InboxResponse,
    summary="Caixa de entrada de decisões — agrega 5 fontes existentes, sem IA",
    tags=["advisor"],
)
async def get_inbox(
    request: Request,
    current_user: dict = Depends(get_current_user),
    tenant_db: AsyncSession = Depends(get_authed_db),
    global_db: AsyncSession = Depends(get_global_db),
    tenant_id: str = Depends(get_current_tenant_id),
    redis_client=Depends(_get_inbox_redis),
) -> InboxResponse:
    """Aggregate ranked decision cards from 5 existing sources.

    Sources: portfolio health, opportunity_detector, insights, watchlist alerts,
    swing_trade signals (Redis). Per-source try/except: a single source failure
    never breaks the response — failed sources land in `meta.sources_failed`.

    No AI. No new tables. No new Celery. Target latency: <500ms.
    """
    return await compute_inbox(
        tenant_db=tenant_db,
        global_db=global_db,
        tenant_id=tenant_id,
        redis_client=redis_client,
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


# ── GET /advisor/screener ──────────────────────────────────────────────────────

@limiter.limit("30/minute")
@router.get(
    "/screener",
    response_model=list[ComplementaryAssetRow],
    summary="Smart Screener — ativos complementares à carteira (setores ausentes)",
    tags=["advisor"],
)
async def smart_screener(
    request: Request,
    current_user: dict = Depends(get_current_user),
    tenant_db: AsyncSession = Depends(get_authed_db),
    global_db: AsyncSession = Depends(get_global_db),
    tenant_id: str = Depends(get_current_tenant_id),
    limit: int = 100,
) -> list[ComplementaryAssetRow]:
    """Return screener universe filtered to complementary assets.

    Complementary = sectors NOT already held in the user's portfolio.
    Results are ranked by relevance to identified health gaps (DY + entry price).

    Empty portfolio: returns full screener universe (all sectors are complementary).
    Rate limit: 30/minute — data is pre-calculated, no heavy computation.
    """
    return await get_complementary_assets(
        tenant_db=tenant_db,
        global_db=global_db,
        tenant_id=tenant_id,
        limit=limit,
    )


# ── GET /advisor/signals/portfolio ────────────────────────────────────────────

@limiter.limit("10/minute")
@router.get(
    "/signals/portfolio",
    response_model=list[EntrySignal],
    summary="On-demand entry signals for owned assets (cached <5min)",
    tags=["advisor"],
)
async def portfolio_entry_signals(
    request: Request,
    current_user: dict = Depends(get_current_user),
    tenant_db: AsyncSession = Depends(get_authed_db),
    global_db: AsyncSession = Depends(get_global_db),
    tenant_id: str = Depends(get_current_tenant_id),
) -> list[EntrySignal]:
    """Return on-demand entry signals for user's owned assets.

    Signals are computed from swing_trade compute_signals() which reads
    Redis-cached market data (30d high, DY, price). Results cached 5 minutes.
    Returns [] when portfolio is empty or market data is unavailable.
    """
    return await get_portfolio_entry_signals(
        tenant_db=tenant_db,
        global_db=global_db,
        tenant_id=tenant_id,
    )


# ── GET /advisor/signals/universe ─────────────────────────────────────────────

@limiter.limit("30/minute")
@router.get(
    "/signals/universe",
    response_model=list[EntrySignal],
    summary="Daily batch entry signals for screener universe",
    tags=["advisor"],
)
async def universe_entry_signals(
    request: Request,
    current_user: dict = Depends(get_current_user),
) -> list[EntrySignal]:
    """Return daily batch signals for the screener universe.

    Signals are pre-computed nightly by the advisor.refresh_universe_entry_signals
    Celery beat task and stored in Redis. Returns [] if the batch hasn't run yet.
    Rate limit: 30/minute — pure cache read, no heavy computation.
    """
    return await get_universe_entry_signals()


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
            # Filter to only known fields (ignore extra keys from old format)
            known = AdvisorResult.model_fields.keys()
            result = AdvisorResult(**{k: v for k, v in data.items() if k in known})
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
