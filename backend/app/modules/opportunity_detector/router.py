"""Opportunity Detector history, follow and radar endpoints.

GET  /opportunity-detector/history        — paginated alert history
GET  /opportunity-detector/radar          — comprehensive market opportunity radar
POST /opportunity-detector/scan           — trigger alert scanners
POST /opportunity-detector/radar/refresh  — force-refresh radar report
PATCH /opportunity-detector/{id}/follow   — toggle followed flag
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_global_db
from app.core.limiter import limiter
from app.core.security import get_current_user
from app.modules.opportunity_detector.models import DetectedOpportunity
from app.modules.opportunity_detector.radar import generate_radar_report, get_cached_radar_report
from app.modules.opportunity_detector.schemas import OpportunityHistoryResponse

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post(
    "/scan",
    summary="Acionar scan manual de oportunidades",
    tags=["opportunity-detector"],
)
@limiter.limit("5/minute")
async def trigger_manual_scan(
    request: Request,
    current_user: dict = Depends(get_current_user),
) -> dict:
    """Dispara os 3 scanners (ações, crypto, renda fixa) imediatamente via Celery.
    Os resultados aparecem na tabela em ~10–20s após o retorno.
    """
    from app.celery_app import celery_app

    task_acoes = celery_app.send_task("opportunity_detector.scan_acoes")
    task_crypto = celery_app.send_task("opportunity_detector.scan_crypto")
    task_fixed = celery_app.send_task("opportunity_detector.scan_fixed_income")

    logger.info(
        "Manual scan triggered by user %s — tasks: acoes=%s crypto=%s fixed=%s",
        current_user.get("sub"),
        task_acoes.id,
        task_crypto.id,
        task_fixed.id,
    )
    return {
        "status": "triggered",
        "tasks": {
            "acoes": task_acoes.id,
            "crypto": task_crypto.id,
            "fixed_income": task_fixed.id,
        },
    }


@router.get(
    "/radar",
    summary="Radar de oportunidades — relatório completo de ativos descontados",
    tags=["opportunity-detector"],
)
@limiter.limit("10/minute")
async def get_radar(
    request: Request,
    current_user: dict = Depends(get_current_user),
    force: bool = Query(default=False, description="Forçar atualização ignorando cache"),
) -> dict:
    """Retorna relatório com ações, FIIs, crypto e renda fixa avaliados quanto ao desconto.

    Cache de 30 minutos no Redis. Use ?force=true para forçar atualização (mais lento).
    """
    if force:
        # Run in thread pool to avoid blocking event loop
        import asyncio
        loop = asyncio.get_event_loop()
        report = await loop.run_in_executor(None, lambda: generate_radar_report(force_refresh=True))
    else:
        cached = get_cached_radar_report()
        if cached:
            return cached
        # No cache — generate synchronously in thread pool
        import asyncio
        loop = asyncio.get_event_loop()
        report = await loop.run_in_executor(None, lambda: generate_radar_report(force_refresh=False))

    return report


@router.post(
    "/radar/refresh",
    summary="Força atualização do radar de oportunidades em background",
    tags=["opportunity-detector"],
)
@limiter.limit("2/minute")
async def refresh_radar(
    request: Request,
    current_user: dict = Depends(get_current_user),
) -> dict:
    """Dispara geração do radar via Celery em background. Retorna imediatamente.
    O novo relatório estará disponível em ~45s via GET /radar.
    """
    from app.celery_app import celery_app
    celery_app.send_task("opportunity_detector.generate_radar")
    return {"status": "refresh_triggered", "ready_in_seconds": 45}


@router.get(
    "/history",
    response_model=OpportunityHistoryResponse,
    summary="Histórico de oportunidades detectadas",
    tags=["opportunity-detector"],
)
@limiter.limit("30/minute")
async def get_opportunity_history(
    request: Request,
    current_user: dict = Depends(get_current_user),
    global_db: AsyncSession = Depends(get_global_db),
    asset_type: str | None = Query(default=None, description="Filter by asset type: acao | crypto | renda_fixa"),
    days: int = Query(default=30, ge=1, le=365, description="How many days back to include"),
) -> OpportunityHistoryResponse:
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    stmt = select(DetectedOpportunity).where(DetectedOpportunity.detected_at >= cutoff)
    if asset_type:
        stmt = stmt.where(DetectedOpportunity.asset_type == asset_type)
    stmt = stmt.order_by(DetectedOpportunity.detected_at.desc())
    result = await global_db.execute(stmt)
    rows = result.scalars().all()
    return OpportunityHistoryResponse(total=len(rows), results=rows)


@router.patch(
    "/{opportunity_id}/follow",
    summary="Toggle followed flag for an opportunity",
    tags=["opportunity-detector"],
)
@limiter.limit("30/minute")
async def mark_as_followed(
    request: Request,
    opportunity_id: str,
    current_user: dict = Depends(get_current_user),
    global_db: AsyncSession = Depends(get_global_db),
) -> dict:
    stmt = select(DetectedOpportunity).where(DetectedOpportunity.id == opportunity_id)
    result = await global_db.execute(stmt)
    opp = result.scalar_one_or_none()
    if not opp:
        raise HTTPException(status_code=404, detail="Opportunity not found")
    opp.followed = not opp.followed
    await global_db.commit()
    await global_db.refresh(opp)
    return {"id": opp.id, "followed": opp.followed}
