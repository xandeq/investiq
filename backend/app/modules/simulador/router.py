"""FastAPI router for /simulador endpoints (Phase 10 — SIM-01, SIM-02, SIM-03).

POST /simulador/simulate — deterministic allocation simulation with 3 scenarios.
"""
import logging
from decimal import Decimal

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_global_db
from app.core.limiter import limiter
from app.core.middleware import get_authed_db
from app.core.security import get_current_user
from app.modules.simulador.schemas import SimuladorRequest, SimuladorResponse
from app.modules.simulador.service import build_simulation

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post(
    "/simulate",
    response_model=SimuladorResponse,
    summary="Simular alocação por perfil de risco com 3 cenários IR-ajustados",
    tags=["simulador"],
)
@limiter.limit("30/minute")
async def simulate(
    request: Request,
    body: SimuladorRequest,
    current_user: dict = Depends(get_current_user),
    global_db: AsyncSession = Depends(get_global_db),
    authed_db: AsyncSession = Depends(get_authed_db),
) -> SimuladorResponse:
    """Simulate an allocation plan for a given valor, prazo, and perfil.

    Returns:
    - SIM-01: Deterministic allocation mix in percentages by asset class
    - SIM-02: 3 scenarios (pessimista/base/otimista) with IR-adjusted projections
    - SIM-03: Portfolio delta comparing current allocation vs suggested ideal

    All calculations are deterministic and complete in under 500ms.
    No external API calls at request time (CDI from Redis macro cache).
    """
    return await build_simulation(
        valor=Decimal(str(body.valor)),
        prazo=body.prazo,
        perfil=body.perfil,
        global_db=global_db,
        tenant_db=authed_db,
    )
