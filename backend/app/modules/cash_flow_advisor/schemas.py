"""Schemas for the DIAX-driven Cash Parking Advisor."""

from __future__ import annotations

from datetime import date, datetime, timezone
from decimal import Decimal

from pydantic import BaseModel, Field


class NextBigOutflow(BaseModel):
    date: date
    amount: Decimal
    description: str


class DailyBalanceItem(BaseModel):
    date: date
    opening_balance: Decimal
    total_income: Decimal
    total_expenses: Decimal
    closing_balance: Decimal
    is_negative: bool
    has_high_priority_expense: bool


class CashFlowProjection(BaseModel):
    current_balance: Decimal
    available_to_invest: Decimal
    next_big_outflow: NextBigOutflow | None
    daily_projection: list[DailyBalanceItem] = []
    fetched_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class CashParkingRow(BaseModel):
    label: str
    gross_annual_pct: Decimal
    holding_days: int
    iof_pct: Decimal
    ir_pct: Decimal
    gross_value_brl: Decimal
    iof_value_brl: Decimal
    ir_value_brl: Decimal
    net_value_brl: Decimal
    net_pct: Decimal
    rank: int
    note: str | None = None


class CashParkingResponse(BaseModel):
    amount: Decimal
    holding_days: int
    rows: list[CashParkingRow]
    next_big_outflow: NextBigOutflow | None
    generated_at: datetime
    warnings: list[str] = []
