"""Pydantic schemas for the Goldman Screener feature."""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class ScreenerRequest(BaseModel):
    """Input for a new screening run."""
    sector_filter: str | None = None   # ex: "Financeiro", "Energia", "Tecnologia"
    custom_notes: str | None = None    # ajuste livre do usuário


class StockAnalysis(BaseModel):
    """Full AI analysis for one recommended stock."""
    model_config = ConfigDict(from_attributes=True)

    ticker: str
    company_name: str
    sector: str

    # Valuation
    pe_ratio: float | None = None
    pe_vs_sector: str | None = None       # ex: "abaixo da média do setor"
    revenue_growth_5y: str | None = None  # ex: "+12% CAGR nos últimos 5 anos"

    # Health
    debt_to_equity: float | None = None
    debt_health: str | None = None        # ex: "saudável", "elevado", "crítico"

    # Income
    dividend_yield: float | None = None   # em %
    payout_score: str | None = None       # "sustentável" | "atenção" | "insustentável"

    # Qualitative
    moat_rating: str | None = None        # "fraco" | "moderado" | "forte"
    moat_description: str | None = None

    # Price targets (12 months)
    bull_target: float | None = None
    bear_target: float | None = None
    current_price_ref: float | None = None

    # Risk
    risk_score: int | None = None         # 1–10
    risk_reasoning: str | None = None

    # Entry
    entry_zone: str | None = None         # ex: "R$ 28–32"
    stop_loss: str | None = None          # ex: "abaixo de R$ 25"

    # Summary
    thesis: str | None = None            # tese de investimento em 2 linhas


class ScreenerResult(BaseModel):
    """Full screening report returned to the frontend."""
    stocks: list[StockAnalysis]
    summary: str                          # parágrafo executivo
    disclaimer: str
    generated_at: str


class ScreenerRunResponse(BaseModel):
    """API response for a screener run (job tracking)."""
    model_config = ConfigDict(from_attributes=True)

    id: str
    status: str
    sector_filter: str | None = None
    custom_notes: str | None = None
    created_at: datetime
    completed_at: datetime | None = None
    result: ScreenerResult | None = None
