"""FastAPI router for /comparador endpoints (Phase 9 — COMP-01, COMP-02).

GET /comparador/compare — compare RF vs RV returns for a holding period.
"""
import logging
from decimal import Decimal

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_global_db
from app.core.limiter import limiter
from app.core.middleware import get_authed_db, get_current_tenant_id
from app.core.security import get_current_user
from app.modules.comparador.schemas import ComparadorResponse, HOLDING_PERIODS, PrazoLabel
from app.modules.comparador.service import build_comparison

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get(
    "/compare",
    response_model=ComparadorResponse,
    summary="Comparar retorno líquido RF vs RV por prazo",
    tags=["comparador"],
)
@limiter.limit("20/minute")
async def compare(
    request: Request,
    prazo: PrazoLabel = Query("1a", description="Prazo: 6m | 1a | 2a | 5a"),
    valor: float | None = Query(None, gt=0, description="Valor inicial para projeção (R$)"),
    current_user: dict = Depends(get_current_user),
    global_db: AsyncSession = Depends(get_global_db),
    tenant_id: str = Depends(get_current_tenant_id),
    authed_db: AsyncSession = Depends(get_authed_db),
) -> ComparadorResponse:
    """Compare net IR-adjusted returns across CDB, LCI, LCA, Tesouro Direto,
    CDI, and IBOVESPA historical for the selected holding period.

    Also shows the user's portfolio annualized return alongside fixed income
    benchmarks (COMP-02) and computes the CDB-equivalent gross rate.

    Results read from pre-built snapshots and Redis — no external API calls
    at request time (IBOVESPA cached 24h; CDI from macro cache).
    """
    valor_dec = Decimal(str(valor)) if valor else None
    result = await build_comparison(
        prazo=prazo,
        valor_inicial=valor_dec,
        global_db=global_db,
        tenant_db=authed_db,
        tenant_id=tenant_id,
    )

    return ComparadorResponse(
        prazo=prazo,
        holding_days=HOLDING_PERIODS[prazo],
        valor_inicial=valor_dec,
        rows=result["rows"],
        best_category=result["best_category"],
        portfolio_cdb_equivalent=result["portfolio_cdb_equivalent"],
        ibovespa_data_stale=result["ibovespa_data_stale"],
        cdi_annual_pct=result["cdi_annual_pct"],
    )
