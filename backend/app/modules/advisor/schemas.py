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
    """Structured AI analysis result from run_portfolio_advisor() skill."""
    diagnostico: str                     # narrative paragraph (PT-BR)
    pontos_positivos: list[str]          # up to 3 positive aspects
    pontos_de_atencao: list[str]         # up to 3 attention points
    sugestoes: list[str]                 # up to 3 actionable suggestions
    proximos_passos: list[str]           # up to 3 next steps
    disclaimer: str = CVM_DISCLAIMER
    # Health snapshot (context for UI — mirrors PortfolioHealth fields)
    health_score: int | None = None
    biggest_risk: str | None = None
    passive_income_monthly_brl: str | None = None
    underperformers: list[str] = []
    completed_at: str | None = None


class AdvisorJobResponse(BaseModel):
    job_id: str
    status: str            # pending | running | completed | failed
    disclaimer: str = CVM_DISCLAIMER
    result: AdvisorResult | None = None
    error_message: str | None = None
    created_at: datetime
    completed_at: datetime | None = None


# ── Entry Signals (Phase 26 — ADVI-04) ────────────────────────────────────────

class EntrySignal(BaseModel):
    """A single actionable entry signal combining technical + fundamental data.

    Generated from swing_trade compute_signals() output (portfolio) or
    ScreenerSnapshot data (universe batch via Celery).

    Fields:
      ticker             — B3 ticker code (e.g. "VALE3")
      suggested_amount_brl — recommended position size as BRL string
      target_upside_pct  — expected recovery % (positive = upside potential)
      timeframe_days     — standard swing-trade horizon (fixed 90 days)
      stop_loss_pct      — standard stop-loss % (fixed 8.0%)
      rsi                — RSI value (None if unavailable)
      ma_signal          — "buy" | "sell" | "neutral" from swing-trade signal
      generated_at       — UTC datetime when signal was computed
    """
    ticker: str
    suggested_amount_brl: str           # Decimal serialised as string
    target_upside_pct: float
    timeframe_days: int
    stop_loss_pct: float
    rsi: float | None = None
    ma_signal: str | None = None        # "buy" | "sell" | "neutral"
    generated_at: datetime
