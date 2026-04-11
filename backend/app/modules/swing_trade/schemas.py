"""Pydantic v2 schemas for the Swing Trade module (Phase 20).

Exposes:
- SwingSignalItem / SwingSignalsResponse — radar + portfolio signal rows
- OperationCreate / OperationClose / OperationResponse / OperationListResponse
  — CRUD payloads for manual swing trade operations.

Design notes:
- All monetary values use Decimal — never float — to avoid IEEE-754 drift.
- OperationResponse carries enriched read-only fields (current_price,
  pnl_pct, pnl_brl, days_open, target_progress_pct, live_signal).
  These are computed on read and not stored in the DB.
"""
from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict


class SwingSignalItem(BaseModel):
    """A single swing trade signal row (used for both portfolio + radar)."""

    ticker: str
    name: str
    sector: str
    current_price: Decimal
    high_30d: Decimal
    discount_pct: float  # negative = down from 30d high
    dy: Decimal | None = None
    signal: str  # "buy" | "sell" | "neutral"
    signal_strength: float  # abs(discount_pct) — convenience for sorting / UI
    in_portfolio: bool = False
    quantity: Decimal | None = None  # present when in_portfolio=True


class SwingSignalsResponse(BaseModel):
    """GET /swing-trade/signals response envelope."""

    portfolio_signals: list[SwingSignalItem]
    radar_signals: list[SwingSignalItem]
    generated_at: datetime


class OperationCreate(BaseModel):
    """POST /swing-trade/operations payload."""

    ticker: str
    asset_class: str = "acao"
    quantity: Decimal
    entry_price: Decimal
    entry_date: datetime
    target_price: Decimal | None = None
    stop_price: Decimal | None = None
    notes: str | None = None


class OperationClose(BaseModel):
    """PATCH /swing-trade/operations/{id}/close payload."""

    exit_price: Decimal
    exit_date: datetime | None = None


class OperationResponse(BaseModel):
    """Row returned by GET /swing-trade/operations — DB + enriched fields."""

    model_config = ConfigDict(from_attributes=True)

    # Persisted fields
    id: str
    ticker: str
    asset_class: str
    quantity: Decimal
    entry_price: Decimal
    entry_date: datetime
    target_price: Decimal | None = None
    stop_price: Decimal | None = None
    status: str
    exit_price: Decimal | None = None
    exit_date: datetime | None = None
    notes: str | None = None
    created_at: datetime

    # Enriched (computed at read time — not in DB)
    current_price: Decimal | None = None
    pnl_pct: float | None = None
    pnl_brl: float | None = None
    days_open: int | None = None
    target_progress_pct: float | None = None
    live_signal: str | None = None  # "sell" when pnl_pct >= 10, "stop" when <= stop


class OperationListResponse(BaseModel):
    """GET /swing-trade/operations response envelope."""

    open_count: int
    closed_count: int
    results: list[OperationResponse]
