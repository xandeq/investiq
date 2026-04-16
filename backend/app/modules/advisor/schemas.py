"""Schemas for /advisor endpoints (Phase 23 — ADVI-01 through ADVI-02).

Endpoints:
  GET  /advisor/health          — synchronous portfolio health (4 metrics, no AI)
  POST /advisor/analyze         — start async AI narrative job (reuses WizardJob table)
  GET  /advisor/{job_id}        — poll job status + result
"""
from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel

CVM_DISCLAIMER = (
    "Análise informativa — não constitui recomendação de investimento (CVM Res. 19/2021)"
)

# ── Health Check ──────────────────────────────────────────────────────────────

class PortfolioHealth(BaseModel):
    """Deterministic portfolio health — computed on-demand, no AI.

    Scores:
      80-100  Portfólio equilibrado
      60-79   Atenção — pontos de melhoria
       0-59   Revisar — concentração ou risco elevado
    """
    health_score: int                    # 0-100 deterministic formula
    biggest_risk: str | None             # single-sentence risk alert, or None if healthy
    passive_income_monthly_brl: Decimal  # TTM dividends + JSCP ÷ 12
    underperformers: list[str]           # ["XXXX3 (-18%)", ...] max 3, variacao_12m < -10%
    data_as_of: datetime | None          # snapshot_date of screener data used (staleness signal)
    total_assets: int                    # number of distinct active positions
    has_portfolio: bool                  # False when no transactions found


# ── Advisor AI Job ─────────────────────────────────────────────────────────────

class AdvisorStartResponse(BaseModel):
    job_id: str
    status: str  # pending
    disclaimer: str = CVM_DISCLAIMER


class AdvisorResult(BaseModel):
    narrative: str                       # AI-generated educational text (PT-BR)
    health_score: int
    biggest_risk: str | None
    passive_income_monthly_brl: str      # Decimal serialized as string
    underperformers: list[str]
    provider_used: str | None
    completed_at: str | None


class AdvisorJobResponse(BaseModel):
    job_id: str
    status: str            # pending | running | completed | failed
    disclaimer: str = CVM_DISCLAIMER
    result: AdvisorResult | None = None
    error_message: str | None = None
    created_at: datetime
    completed_at: datetime | None = None
