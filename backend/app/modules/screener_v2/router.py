"""FastAPI router for screener_v2 endpoints.

Endpoints (all read-only from pre-built snapshots — no external API calls):
  GET /screener/acoes   — Filter B3 acoes from screener_snapshots
  GET /screener/fiis    — Filter FIIs from screener_snapshots + fii_metadata
  GET /renda-fixa/catalog — Fixed income catalog with IR-adjusted net returns
  GET /renda-fixa/tesouro — Current Tesouro Direto rates from Redis

Rate limit: 30/minute (read-only from snapshots — far less costly than AI screener).
Auth: required — get_current_user + get_global_db for screener/catalog tables.
      Portfolio toggle (exclude_portfolio): also reads tenant-scoped DB.

CVM disclaimer: included in every response body per Res. 19/2021.
"""
import logging

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_global_db
from app.core.limiter import limiter
from app.core.middleware import get_authed_db, get_current_tenant_id
from app.core.security import get_current_user
from app.modules.screener_v2.schemas import (
    AcaoScreenerParams,
    AcaoScreenerResponse,
    FIIScreenerParams,
    FIIScreenerResponse,
    FixedIncomeCatalogResponse,
    MacroRatesResponse,
    ScreenerUniverseResponse,
    TesouroRatesResponse,
)
from app.modules.screener_v2.service import (
    query_acoes,
    query_fiis,
    query_fixed_income_catalog,
    query_macro_rates,
    query_screener_universe,
    query_tesouro_rates,
)

logger = logging.getLogger(__name__)

router = APIRouter()


# ---------------------------------------------------------------------------
# Acao screener
# ---------------------------------------------------------------------------


@router.get(
    "/acoes",
    response_model=AcaoScreenerResponse,
    summary="Screener de Acoes B3 (por snapshot diario)",
    tags=["screener-v2"],
)
@limiter.limit("30/minute")
async def screener_acoes(
    request: Request,
    # Filter params via Query
    min_dy: float | None = Query(None, description="DY minimo (%)"),
    max_pl: float | None = Query(None, description="P/L maximo"),
    max_pvp: float | None = Query(None, description="P/VP maximo"),
    max_ev_ebitda: float | None = Query(None, description="EV/EBITDA maximo"),
    sector: str | None = Query(None, description="Setor (busca parcial, case-insensitive)"),
    min_volume: int | None = Query(None, description="Volume minimo (R$)"),
    min_market_cap: int | None = Query(None, description="Market cap minimo (R$)"),
    exclude_portfolio: bool = Query(False, description="Excluir tickers ja na carteira"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    # Dependencies
    current_user: dict = Depends(get_current_user),
    global_db: AsyncSession = Depends(get_global_db),
    tenant_id: str = Depends(get_current_tenant_id),
    authed_db: AsyncSession = Depends(get_authed_db),
) -> AcaoScreenerResponse:
    """Filter B3 acoes from the latest daily screener snapshot.

    Results come exclusively from the pre-built screener_snapshots table —
    this endpoint never calls brapi.dev or any external API at request time.

    The CVM disclaimer is included in the response body per Res. 19/2021.
    """
    from decimal import Decimal

    params = AcaoScreenerParams(
        min_dy=Decimal(str(min_dy)) if min_dy is not None else None,
        max_pl=Decimal(str(max_pl)) if max_pl is not None else None,
        max_pvp=Decimal(str(max_pvp)) if max_pvp is not None else None,
        max_ev_ebitda=Decimal(str(max_ev_ebitda)) if max_ev_ebitda is not None else None,
        sector=sector,
        min_volume=min_volume,
        min_market_cap=min_market_cap,
        exclude_portfolio=exclude_portfolio,
        limit=limit,
        offset=offset,
    )

    tenant_db = authed_db if exclude_portfolio else None
    tid = tenant_id if exclude_portfolio else None

    total, rows = await query_acoes(
        db=global_db,
        params=params,
        tenant_db=tenant_db,
        tenant_id=tid,
    )

    return AcaoScreenerResponse(
        total=total,
        limit=limit,
        offset=offset,
        results=rows,
    )


# ---------------------------------------------------------------------------
# Universe endpoint (all tickers, client-side filtering — per D-09)
# ---------------------------------------------------------------------------


@router.get(
    "/universe",
    response_model=ScreenerUniverseResponse,
    summary="Universo completo de acoes B3 (snapshot diario, sem filtros)",
    tags=["screener-v2"],
)
@limiter.limit("30/minute")
async def screener_universe(
    request: Request,
    current_user: dict = Depends(get_current_user),
    global_db: AsyncSession = Depends(get_global_db),
) -> ScreenerUniverseResponse:
    """Return all ~900 tickers from the latest daily screener snapshot.

    No server-side filtering -- the frontend applies filters client-side with useMemo.
    The CVM disclaimer is included in the response body per Res. 19/2021.
    """
    rows = await query_screener_universe(db=global_db)
    return ScreenerUniverseResponse(results=rows)


# ---------------------------------------------------------------------------
# FII screener
# ---------------------------------------------------------------------------


@router.get(
    "/fiis",
    response_model=FIIScreenerResponse,
    summary="Screener de FIIs (por snapshot diario + metadados CVM)",
    tags=["screener-v2"],
)
@limiter.limit("30/minute")
async def screener_fiis(
    request: Request,
    min_dy: float | None = Query(None, description="DY minimo (%)"),
    max_pvp: float | None = Query(None, description="P/VP maximo"),
    segmento: str | None = Query(None, description="Segmento: Tijolo, Papel, Hibrido, FoF, Agro"),
    max_vacancia: float | None = Query(None, description="Vacancia financeira maxima (%)"),
    min_cotistas: int | None = Query(None, description="Num cotistas minimo"),
    min_volume: int | None = Query(None, description="Volume minimo (R$)"),
    exclude_portfolio: bool = Query(False, description="Excluir tickers ja na carteira"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    current_user: dict = Depends(get_current_user),
    global_db: AsyncSession = Depends(get_global_db),
    tenant_id: str = Depends(get_current_tenant_id),
    authed_db: AsyncSession = Depends(get_authed_db),
) -> FIIScreenerResponse:
    """Filter FIIs from the latest snapshot joined with CVM segment metadata.

    Results come from screener_snapshots + fii_metadata — no external API calls.
    The segmento column is always present (null if CVM data not yet available for that FII).

    The CVM disclaimer is included in the response body per Res. 19/2021.
    """
    from decimal import Decimal

    params = FIIScreenerParams(
        min_dy=Decimal(str(min_dy)) if min_dy is not None else None,
        max_pvp=Decimal(str(max_pvp)) if max_pvp is not None else None,
        segmento=segmento,
        max_vacancia=Decimal(str(max_vacancia)) if max_vacancia is not None else None,
        min_cotistas=min_cotistas,
        min_volume=min_volume,
        exclude_portfolio=exclude_portfolio,
        limit=limit,
        offset=offset,
    )

    tenant_db = authed_db if exclude_portfolio else None
    tid = tenant_id if exclude_portfolio else None

    total, rows = await query_fiis(
        db=global_db,
        params=params,
        tenant_db=tenant_db,
        tenant_id=tid,
    )

    return FIIScreenerResponse(
        total=total,
        limit=limit,
        offset=offset,
        results=rows,
    )


# ---------------------------------------------------------------------------
# Renda fixa catalog
# ---------------------------------------------------------------------------


@router.get(
    "/catalog",
    response_model=FixedIncomeCatalogResponse,
    summary="Catalogo de renda fixa com retorno liquido (apos IR)",
    tags=["renda-fixa"],
)
@limiter.limit("30/minute")
async def renda_fixa_catalog(
    request: Request,
    current_user: dict = Depends(get_current_user),
    global_db: AsyncSession = Depends(get_global_db),
) -> FixedIncomeCatalogResponse:
    """Return the fixed income catalog with IR-adjusted net returns per holding period.

    Each row shows gross rate range (min_rate_pct / max_rate_pct) plus net returns
    after IR regressivo for holding periods of 6m, 1a, 2a, 5a.

    LCI and LCA rows are marked is_exempt=True — IR = 0% (PF exemption).

    Rates are reference market ranges — not live offers. UI must label accordingly.
    """
    rows = await query_fixed_income_catalog(db=global_db)

    return FixedIncomeCatalogResponse(results=rows)


# ---------------------------------------------------------------------------
# Tesouro Direto rates
# ---------------------------------------------------------------------------


@router.get(
    "/tesouro",
    response_model=TesouroRatesResponse,
    summary="Taxas Tesouro Direto (do cache Redis — atualizadas a cada 6h)",
    tags=["renda-fixa"],
)
@limiter.limit("30/minute")
async def tesouro_rates(
    request: Request,
    current_user: dict = Depends(get_current_user),
) -> TesouroRatesResponse:
    """Return Tesouro Direto bond rates from Redis cache.

    Rates are populated by the refresh_tesouro_rates Celery beat task (every 6h).
    Source is ANBIMA API (primary) or CKAN CSV (fallback).

    Returns empty list if Redis is unavailable or task has not run yet.
    """
    rows = await query_tesouro_rates()

    return TesouroRatesResponse(results=rows)


# ---------------------------------------------------------------------------
# Macro rates (CDI / IPCA)
# ---------------------------------------------------------------------------


@router.get(
    "/macro-rates",
    response_model=MacroRatesResponse,
    summary="CDI e IPCA anuais do cache Redis",
    tags=["renda-fixa"],
)
@limiter.limit("30/minute")
async def macro_rates(
    request: Request,
    current_user: dict = Depends(get_current_user),
) -> MacroRatesResponse:
    """Return current CDI and IPCA annual rates from Redis cache.

    Rates populated by refresh_macro Celery beat task (every 7h).
    Returns null values if Redis is unavailable.
    """
    return await query_macro_rates()
