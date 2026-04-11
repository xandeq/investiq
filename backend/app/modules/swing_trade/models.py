"""SQLAlchemy models for the Swing Trade module (Phase 20).

Tables:
- swing_trade_operations: user-registered swing trade operations (manual).
  Scoped by tenant_id (RLS enforced at DB level in PostgreSQL migration).

Design notes:
- tenant_id mirrors the pattern used by Transaction / PortfolioPosition —
  one row per user operation, RLS policy restricts visibility by tenant.
- status transitions: "open" -> "closed" | "stopped" (via close_operation).
- deleted_at implements soft delete consistent with Transaction.
- Numeric(18, 6) matches existing portfolio schema for price/qty fields.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.modules.auth.models import Base


class SwingTradeOperation(Base):
    """A single manual swing trade operation registered by the user."""

    __tablename__ = "swing_trade_operations"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    tenant_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    ticker: Mapped[str] = mapped_column(String(20), nullable=False)
    asset_class: Mapped[str] = mapped_column(String(20), nullable=False, default="acao")
    quantity: Mapped[float] = mapped_column(Numeric(18, 6), nullable=False)
    entry_price: Mapped[float] = mapped_column(Numeric(18, 6), nullable=False)
    entry_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    target_price: Mapped[float | None] = mapped_column(Numeric(18, 6), nullable=True)
    stop_price: Mapped[float | None] = mapped_column(Numeric(18, 6), nullable=True)
    # status: "open" | "closed" | "stopped"
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="open")
    exit_price: Mapped[float | None] = mapped_column(Numeric(18, 6), nullable=True)
    exit_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
