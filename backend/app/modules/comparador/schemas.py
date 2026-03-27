"""Schemas for /comparador endpoints (Phase 9 — COMP-01, COMP-02)."""
from __future__ import annotations
from decimal import Decimal
from typing import Literal
from pydantic import BaseModel

CVM_DISCLAIMER = (
    "Análise informativa — não constitui recomendação de investimento (CVM Res. 19/2021)"
)

HOLDING_PERIODS: dict[str, int] = {"6m": 180, "1a": 365, "2a": 730, "5a": 1825}

PrazoLabel = Literal["6m", "1a", "2a", "5a"]


class ComparadorRow(BaseModel):
    label: str
    category: str          # tesouro | cdb | lci | lca | ibovespa | cdi | portfolio
    gross_pct: Decimal | None = None
    ir_rate_pct: Decimal | None = None
    net_pct: Decimal | None = None
    net_value: Decimal | None = None   # if valor_inicial provided
    is_exempt: bool = False
    risk_label: str        # Baixíssimo | Baixo | Moderado | Alto
    data_source: str       # "catalog" | "redis" | "yfinance" | "portfolio" | "bcb"
    is_best: bool = False
    is_portfolio: bool = False
    note: str | None = None


class ComparadorResponse(BaseModel):
    prazo: str
    holding_days: int
    valor_inicial: Decimal | None = None
    disclaimer: str = CVM_DISCLAIMER
    rows: list[ComparadorRow]
    best_category: str | None = None
    portfolio_cdb_equivalent: Decimal | None = None   # COMP-02
    ibovespa_data_stale: bool = False
    cdi_annual_pct: Decimal | None = None
