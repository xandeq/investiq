"""Shared Pydantic models for ADR-002 spike.

These models are the SAME for both implementations — the spike is
about orchestration ergonomics, not schema differences.
"""
from __future__ import annotations

from datetime import datetime
from typing import Any


from pydantic import BaseModel, Field


class PortfolioContext(BaseModel):
    current_allocation: dict[str, float]
    capital_available: float


class DecisionInput(BaseModel):
    query: str
    user_id: str
    portfolio_context: PortfolioContext


class IntentResult(BaseModel):
    intent: str  # "dividend_income" | "growth" | "balanced"
    confidence: float
    reasoning: str


class PortfolioResult(BaseModel):
    available_capital: float
    current_stocks_pct: float
    current_fii_pct: float
    current_rf_pct: float
    rebalancing_needed: bool


class AssetResult(BaseModel):
    candidates: list[dict[str, Any]]
    filter_applied: str
    universe_size: int


class NewsResult(BaseModel):
    headlines: list[str]
    sentiment: str  # "positive" | "neutral" | "negative"
    relevant_tickers: list[str]


class Recommendation(BaseModel):
    ticker: str
    asset_class: str
    allocation_pct: float
    rationale: str
    confidence: float


class AgentTrace(BaseModel):
    agent: str
    started_at: datetime
    completed_at: datetime
    duration_ms: float
    status: str  # "ok" | "error" | "degraded"
    error: str | None = None


class DecisionOutput(BaseModel):
    recommendations: list[Recommendation]
    portfolio_context: PortfolioContext
    intent: IntentResult
    generated_at: datetime
    trace: list[AgentTrace]
