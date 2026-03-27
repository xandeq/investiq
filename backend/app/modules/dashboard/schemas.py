"""Pydantic v2 schemas for the dashboard module.

All Decimal fields serialize as strings in FastAPI JSON responses automatically
via Pydantic v2's default JSON mode. No custom serializer needed.
"""
from __future__ import annotations
from datetime import date
from decimal import Decimal
from pydantic import BaseModel


class AllocationSummary(BaseModel):
    asset_class: str
    value: Decimal
    pct: Decimal


class TimeseriesPoint(BaseModel):
    date: date
    value: Decimal


class RecentTransaction(BaseModel):
    ticker: str
    type: str
    quantity: Decimal
    unit_price: Decimal
    date: date


class DashboardSummaryResponse(BaseModel):
    net_worth: Decimal
    total_invested: Decimal
    total_return: Decimal
    total_return_pct: Decimal
    daily_pnl: Decimal
    daily_pnl_pct: Decimal
    data_stale: bool = False
    asset_allocation: list[AllocationSummary]
    portfolio_timeseries: list[TimeseriesPoint]
    recent_transactions: list[RecentTransaction]
