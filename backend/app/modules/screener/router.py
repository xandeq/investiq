"""Router for the Goldman Screener feature.

Endpoints:
  POST /screener/analyze  — Create a new screening run (202 Accepted, async job)
  GET  /screener/jobs/{id} — Poll job status + retrieve result
  GET  /screener/history  — List last 10 runs for the user

Pro/Enterprise only — free users are blocked (plan == "free").
Trial users are elevated to "pro" via plan_gate.get_user_plan.
Rate limit: 3 screenings per hour.
"""

import json
import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.limiter import limiter
from app.core.middleware import get_authed_db, get_current_tenant_id
from app.core.plan_gate import get_user_plan
from app.modules.screener.models import ScreenerRun
from app.modules.screener.schemas import (
    ScreenerRequest,
    ScreenerResult,
    ScreenerRunResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter()


def _require_premium(plan: str) -> None:
    if plan == "free":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Triagem de Ações é uma funcionalidade Premium. Faça upgrade para acessar.",
        )


def _dispatch_screener(run: ScreenerRun) -> None:
    from app.celery_app import celery_app
    with celery_app.connection_for_write() as conn:
        celery_app.send_task(
            "screener.run_goldman_screener",
            kwargs={
                "run_id": run.id,
                "tenant_id": run.tenant_id,
                "sector_filter": run.sector_filter,
                "custom_notes": run.custom_notes,
            },
            connection=conn,
        )


def _parse_result(result_json: str | None) -> ScreenerResult | None:
    if not result_json:
        return None
    try:
        data = json.loads(result_json)
        return ScreenerResult(**data)
    except Exception:
        return None


@router.post(
    "/analyze",
    response_model=ScreenerRunResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Iniciar triagem Goldman Sachs (Premium)",
)
@limiter.limit("3/hour")
async def start_screener(
    request: Request,
    db: AsyncSession = Depends(get_authed_db),
    tenant_id: str = Depends(get_current_tenant_id),
    plan: str = Depends(get_user_plan),
) -> ScreenerRunResponse:
    """Submit a new stock screening run. Returns 202 with run_id for polling.

    Note: body is parsed manually from Request to avoid a slowapi + FastAPI
    body-parameter conflict (slowapi 0.1.9 treats Pydantic body params as
    query params when a Request object is also in the signature).
    """
    # Parse body manually to work around slowapi + FastAPI body-param conflict
    try:
        raw = await request.json()
    except Exception:
        raw = {}
    payload = ScreenerRequest(**raw)

    _require_premium(plan)

    run = ScreenerRun(
        id=str(uuid.uuid4()),
        tenant_id=tenant_id,
        sector_filter=payload.sector_filter,
        custom_notes=payload.custom_notes,
        status="pending",
    )
    db.add(run)
    await db.flush()
    await db.commit()  # commit before dispatching so the worker finds the row

    try:
        _dispatch_screener(run)
    except Exception as exc:
        logger.error("Failed to dispatch screener task %s: %s", run.id, exc)

    return ScreenerRunResponse(
        id=run.id,
        status=run.status,
        sector_filter=run.sector_filter,
        custom_notes=run.custom_notes,
        created_at=run.created_at,
        completed_at=run.completed_at,
        result=None,
    )


@router.get(
    "/jobs/{run_id}",
    response_model=ScreenerRunResponse,
    summary="Consultar status e resultado da triagem",
)
async def get_screener_run(
    run_id: str,
    db: AsyncSession = Depends(get_authed_db),
    tenant_id: str = Depends(get_current_tenant_id),
) -> ScreenerRunResponse:
    """Poll a screening run by ID. Returns status + result when completed."""
    result = await db.execute(
        select(ScreenerRun).where(
            ScreenerRun.id == run_id,
            ScreenerRun.tenant_id == tenant_id,
        )
    )
    run = result.scalar_one_or_none()
    if run is None:
        raise HTTPException(status_code=404, detail="Triagem não encontrada.")

    return ScreenerRunResponse(
        id=run.id,
        status=run.status,
        sector_filter=run.sector_filter,
        custom_notes=run.custom_notes,
        created_at=run.created_at,
        completed_at=run.completed_at,
        result=_parse_result(run.result_json),
    )


@router.get(
    "/history",
    response_model=list[ScreenerRunResponse],
    summary="Histórico das últimas triagens do usuário",
)
async def get_screener_history(
    db: AsyncSession = Depends(get_authed_db),
    tenant_id: str = Depends(get_current_tenant_id),
) -> list[ScreenerRunResponse]:
    """Return the last 10 screening runs for the authenticated user."""
    result = await db.execute(
        select(ScreenerRun)
        .where(ScreenerRun.tenant_id == tenant_id)
        .order_by(ScreenerRun.created_at.desc())
        .limit(10)
    )
    runs = result.scalars().all()

    return [
        ScreenerRunResponse(
            id=r.id,
            status=r.status,
            sector_filter=r.sector_filter,
            custom_notes=r.custom_notes,
            created_at=r.created_at,
            completed_at=r.completed_at,
            result=_parse_result(r.result_json) if r.status == "completed" else None,
        )
        for r in runs
    ]
