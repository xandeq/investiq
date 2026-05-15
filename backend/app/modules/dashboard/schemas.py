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


class RiskMetricsResponse(BaseModel):
    volatility_annual_pct: Decimal
    max_drawdown_pct: Decimal
    positive_days_pct: Decimal
    trading_days: int
    data_available: bool  # False when < 5 days of data


class SectorAllocationItem(BaseModel):
    sector: str
    value: Decimal
    pct: Decimal


class SectorAllocationResponse(BaseModel):
    sectors: list[SectorAllocationItem]


class DividendEventItem(BaseModel):
    ticker: str
    asset_class: str
    payment_date: str        # "YYYY-MM-DD" or "" if unknown
    ex_date: str             # "YYYY-MM-DD" or "" if unknown
    rate_per_share: Decimal  # R$ per share/quota
    quantity: Decimal        # user holds this many shares
    estimated_income: Decimal  # rate_per_share × quantity
    label: str               # e.g. "Dividendo", "JCP", "Rendimento"


class DividendCalendarResponse(BaseModel):
    events: list[DividendEventItem]
    data_available: bool     # False if brapi returned nothing
