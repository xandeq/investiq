"""SQLAlchemy models for the Opportunity Detector module (Phase 19).

Tables:
- detected_opportunities: persists every opportunity dispatched by the
  alert engine so the frontend can display history with filters.

This is a GLOBAL table (no tenant_id) — same pattern as FIIMetadata/ScreenerSnapshot.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.modules.auth.models import Base


class DetectedOpportunity(Base):
    """A single opportunity report persisted from the alert engine."""

    __tablename__ = "detected_opportunities"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    ticker: Mapped[str] = mapped_column(String(20), nullable=False)
    asset_type: Mapped[str] = mapped_column(String(20), nullable=False)
    drop_pct: Mapped[float] = mapped_column(Numeric(8, 4), nullable=False)
    period: Mapped[str] = mapped_column(String(20), nullable=False)
    current_price: Mapped[float] = mapped_column(Numeric(18, 6), nullable=False)
    currency: Mapped[str] = mapped_column(String(5), nullable=False)
    risk_level: Mapped[str | None] = mapped_column(String(20), nullable=True)
    is_opportunity: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    cause_category: Mapped[str | None] = mapped_column(String(50), nullable=True)
    cause_explanation: Mapped[str | None] = mapped_column(Text, nullable=True)
    risk_rationale: Mapped[str | None] = mapped_column(Text, nullable=True)
    recommended_amount_brl: Mapped[float | None] = mapped_column(
        Numeric(12, 2), nullable=True
    )
    target_upside_pct: Mapped[float | None] = mapped_column(Numeric(8, 2), nullable=True)
    telegram_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    followed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    detected_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
