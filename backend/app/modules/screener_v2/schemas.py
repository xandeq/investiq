"""Pydantic schemas for screener_v2 endpoints.

Screener endpoints: /screener/acoes, /screener/fiis
Renda fixa endpoints: /renda-fixa/catalog, /renda-fixa/tesouro

All responses include a CVM disclaimer per Res. 19/2021.
"""
from __future__ import annotations

from decimal import Decimal
from typing import Any

from pydantic import BaseModel, Field

# CVM Res. 19/2021 mandatory disclaimer text
CVM_DISCLAIMER = (
    "Análise informativa — não constitui recomendação de investimento (CVM Res. 19/2021)"
)

# Holding periods used for net IR return calculations
HOLDING_PERIODS = {
    "6m": 180,
    "1a": 365,
    "2a": 730,
    "5a": 1825,
}


# ---------------------------------------------------------------------------
# Acao screener
# ---------------------------------------------------------------------------


class AcaoScreenerParams(BaseModel):
    """Query parameters for GET /screener/acoes."""

    min_dy: Decimal | None = Field(None, description="Dividend yield minimo (%)")
    max_pl: Decimal | None = Field(None, description="P/L maximo")
    max_pvp: Decimal | None = Field(None, description="P/VP maximo")
    max_ev_ebitda: Decimal | None = Field(None, description="EV/EBITDA maximo")
    sector: str | None = Field(None, description="Setor exato (case-insensitive)")
    min_volume: int | None = Field(None, description="Volume financeiro minimo (R$)")
    min_market_cap: int | None = Field(None, description="Market cap minimo (R$)")
    exclude_portfolio: bool = Field(False, description="Excluir tickers ja na carteira do usuario")
    limit: int = Field(50, ge=1, le=200, description="Itens por pagina")
    offset: int = Field(0, ge=0, description="Offset para paginacao")


class AcaoRow(BaseModel):
    """Single acao row in screener results."""

    ticker: str
    short_name: str | None
    sector: str | None
    price: Decimal | None
    change_pct: Decimal | None
    volume: int | None
    market_cap: int | None
    pl: Decimal | None
    pvp: Decimal | None
    dy: Decimal | None
    ev_ebitda: Decimal | None
    snapshot_date: str


class AcaoScreenerResponse(BaseModel):
    """Response for GET /screener/acoes."""

    disclaimer: str = CVM_DISCLAIMER
    total: int
    limit: int
    offset: int
    results: list[AcaoRow]


# ---------------------------------------------------------------------------
# Universe screener (client-side filtering — per D-09, D-10)
# ---------------------------------------------------------------------------


class ScreenerUniverseRow(BaseModel):
    """Single row in the full universe screener (client-side filtering)."""

    ticker: str
    short_name: str | None
    sector: str | None
    regular_market_price: Decimal | None
    variacao_12m_pct: Decimal | None
    dy: Decimal | None
    pl: Decimal | None
    market_cap: int | None


class ScreenerUniverseResponse(BaseModel):
    """Response for GET /screener/universe -- all tickers, no pagination."""

    disclaimer: str = CVM_DISCLAIMER
    results: list[ScreenerUniverseRow]


# ---------------------------------------------------------------------------
# FII screener
# ---------------------------------------------------------------------------


class FIIScreenerParams(BaseModel):
    """Query parameters for GET /screener/fiis."""

    min_dy: Decimal | None = Field(None, description="DY minimo (%)")
    max_pvp: Decimal | None = Field(None, description="P/VP maximo")
    segmento: str | None = Field(None, description="Segmento: Tijolo, Papel, Hibrido, FoF, Agro")
    max_vacancia: Decimal | None = Field(None, description="Vacancia financeira maxima (%)")
    min_cotistas: int | None = Field(None, description="Numero minimo de cotistas")
    min_volume: int | None = Field(None, description="Volume minimo (R$)")
    exclude_portfolio: bool = Field(False, description="Excluir tickers ja na carteira")
    limit: int = Field(50, ge=1, le=200, description="Itens por pagina")
    offset: int = Field(0, ge=0, description="Offset para paginacao")


class FIIRow(BaseModel):
    """Single FII row in screener results."""

    ticker: str
    short_name: str | None
    segmento: str | None
    price: Decimal | None
    change_pct: Decimal | None
    volume: int | None
    pvp: Decimal | None
    dy: Decimal | None
    vacancia_financeira: Decimal | None
    num_cotistas: int | None
    snapshot_date: str


class FIIScreenerResponse(BaseModel):
    """Response for GET /screener/fiis."""

    disclaimer: str = CVM_DISCLAIMER
    total: int
    limit: int
    offset: int
    results: list[FIIRow]


# ---------------------------------------------------------------------------
# Renda fixa catalog
# ---------------------------------------------------------------------------


class IRBreakdown(BaseModel):
    """IR-adjusted net return by holding period."""

    period_label: str   # "6m", "1a", "2a", "5a"
    holding_days: int
    gross_pct: Decimal
    ir_rate_pct: Decimal
    net_pct: Decimal
    is_exempt: bool


class FixedIncomeCatalogRow(BaseModel):
    """Single instrument row in the renda fixa catalog."""

    instrument_type: str   # CDB, LCI, LCA
    indexer: str           # CDI, IPCA, PREFIXADO, SELIC
    label: str
    min_months: int
    max_months: int | None
    min_rate_pct: Decimal
    max_rate_pct: Decimal | None
    ir_breakdowns: list[IRBreakdown]
    note: str = "Taxa de referencia de mercado — nao constitui oferta ao vivo"


class FixedIncomeCatalogResponse(BaseModel):
    """Response for GET /renda-fixa/catalog."""

    disclaimer: str = CVM_DISCLAIMER
    results: list[FixedIncomeCatalogRow]


# ---------------------------------------------------------------------------
# Tesouro Direto rates
# ---------------------------------------------------------------------------


class TesouroRateRow(BaseModel):
    """Single Tesouro Direto bond from Redis tesouro:rates:* keys."""

    tipo_titulo: str
    vencimento: str
    taxa_indicativa: Decimal | None
    pu: Decimal | None
    data_base: str
    source: str


class TesouroRatesResponse(BaseModel):
    """Response for GET /renda-fixa/tesouro."""

    disclaimer: str = CVM_DISCLAIMER
    note: str = "Taxas de referencia de mercado — nao constitui oferta ao vivo"
    results: list[TesouroRateRow]


# ---------------------------------------------------------------------------
# Macro rates (CDI / IPCA from Redis)
# ---------------------------------------------------------------------------


class MacroRatesResponse(BaseModel):
    """Response for GET /renda-fixa/macro-rates."""

    cdi: Decimal | None = Field(None, description="CDI annual rate as percentage, e.g. 10.65")
    ipca: Decimal | None = Field(None, description="IPCA annual rate as percentage, e.g. 5.06")
