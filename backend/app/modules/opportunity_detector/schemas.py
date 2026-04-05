"""Pydantic v2 schemas for the Opportunity Detector history API (Phase 19)."""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class OpportunityRowSchema(BaseModel):
    id: str
    ticker: str
    asset_type: str
    drop_pct: float
    period: str
    current_price: float
    currency: str
    risk_level: str | None = None
    is_opportunity: bool
    cause_category: str | None = None
    cause_explanation: str | None = None
    risk_rationale: str | None = None
    recommended_amount_brl: float | None = None
    target_upside_pct: float | None = None
    telegram_message: str | None = None
    followed: bool
    detected_at: datetime

    model_config = {"from_attributes": True}


class OpportunityHistoryResponse(BaseModel):
    total: int
    results: list[OpportunityRowSchema]
