"""Schemas for /advisor endpoints (Phase 23 — ADVI-01 through ADVI-02 + Action Inbox v1).

Endpoints:
  GET  /advisor/health          — synchronous portfolio health (4 metrics, no AI)
  POST /advisor/health/refresh  — bypass cache, compute fresh
  POST /advisor/analyze         — start async AI narrative job (reuses WizardJob table)
  GET  /advisor/{job_id}        — poll job status + result
  GET  /advisor/inbox           — ranked decision cards from 5 existing sources
  GET  /advisor/screener        — complementary assets (Phase 25 — ADVI-03)
  GET  /advisor/signals/portfolio — on-demand entry signals (Phase 26 — ADVI-04)
  GET  /advisor/signals/universe  — batch universe signals (Phase 26 — ADVI-04)
"""
from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, Field

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


# ── Action Inbox (Phase 1) ────────────────────────────────────────────────────

InboxCardKind = Literal[
    "concentration_risk",
    "low_diversification",
    "underperformer",
    "no_passive_income",
    "opportunity_detected",
    "insight",
    "watchlist_alert",
    "swing_signal",
]
InboxSeverity = Literal["info", "warn", "alert"]


class InboxCardCTA(BaseModel):
    label: str
    href: str


class InboxCard(BaseModel):
    """One ranked decision card. Aggregated by GET /advisor/inbox."""

    id: str                              # stable; React key + dedup
    kind: InboxCardKind
    priority: float = Field(ge=0.0, le=1.0)
    title: str                           # ≤ 80 chars (not enforced server-side)
    body: str                            # ≤ 200 chars (not enforced server-side)
    ticker: str | None = None
    severity: InboxSeverity
    cta: InboxCardCTA | None = None
    created_at: datetime


class InboxMeta(BaseModel):
    """Source health for the inbox aggregation. Failed sources degrade gracefully."""

    sources_ok: list[str]
    sources_failed: list[str]


class InboxResponse(BaseModel):
    """GET /advisor/inbox — ranked cards capped at 10.

    Aggregates 5 existing sources (no new tables, no new pipelines, no LLM):
      health_check, opportunity_detector, insights, watchlist_alerts, swing_signals.
    """

    generated_at: datetime
    cards: list[InboxCard]
    meta: InboxMeta


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
