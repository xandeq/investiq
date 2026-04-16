"""Pydantic v2 schemas for the portfolio module.

Covers all Phase 2 API contracts:
- TransactionCreate / TransactionResponse (create/read transactions)
- PositionResponse (current holdings with CMP and Redis price enrichment)
- PnLResponse / AllocationItem (portfolio-level P&L and allocation breakdown)
- BenchmarkResponse (CDI + IBOVESPA from Redis macro cache)
- DividendResponse (dividend history per asset)

All response schemas use ConfigDict(from_attributes=True) so they can be
constructed from SQLAlchemy ORM instances via model_validate().
"""
from __future__ import annotations

import uuid
from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from app.modules.portfolio.models import AssetClass, TransactionType


class TransactionCreate(BaseModel):
    """Input schema for creating a new transaction.

    Validates all required fields. Asset-class-specific fields are optional —
    callers only populate coupon_rate/maturity_date for renda_fixa transactions.
    """
    ticker: str = Field(..., max_length=20)
    asset_class: AssetClass
    transaction_type: TransactionType
    transaction_date: date
    quantity: Decimal = Field(..., gt=0)
    unit_price: Decimal = Field(..., gt=0)
    brokerage_fee: Decimal | None = None

    # Asset-class-specific optional fields
    coupon_rate: Decimal | None = None      # renda_fixa: annual coupon rate
    maturity_date: date | None = None       # renda_fixa: bond maturity date
    is_exempt: bool = False                 # FII: dividend exempt from IR

    notes: str | None = Field(None, max_length=500)


class TransactionResponse(TransactionCreate):
    """Response schema — adds server-assigned fields.

    Returned by POST /portfolio/transactions and GET /portfolio/transactions/{id}.
    """
    model_config = ConfigDict(from_attributes=True)

    id: str
    tenant_id: str
    portfolio_id: str
    total_value: Decimal
    irrf_withheld: Decimal | None = None
    gross_profit: Decimal | None = None
    created_at: datetime | None = None


class TransactionUpdate(BaseModel):
    """Partial update schema for PATCH /portfolio/transactions/{id}.

    All fields are optional — only provided fields are updated.
    """
    transaction_date: date | None = None
    quantity: Decimal | None = Field(None, gt=0)
    unit_price: Decimal | None = Field(None, gt=0)
    brokerage_fee: Decimal | None = None
    notes: str | None = Field(None, max_length=500)
    is_exempt: bool | None = None


class BulkDeleteRequest(BaseModel):
    """Request body for DELETE /portfolio/transactions/bulk."""
    ids: list[str]  # list of transaction UUIDs


class TransactionListParams(BaseModel):
    """Query parameters for GET /portfolio/transactions."""
    ticker: str | None = None
    asset_class: AssetClass | None = None
    transaction_type: TransactionType | None = None
    date_from: date | None = None
    date_to: date | None = None
    limit: int = Field(100, ge=1, le=500)
    offset: int = Field(0, ge=0)


class PositionResponse(BaseModel):
    """Current position for a single ticker.

    Enriched with Redis price when available; data_stale=True when cache miss.
    """
    model_config = ConfigDict(from_attributes=True)

    ticker: str
    asset_class: str
    quantity: Decimal
    cmp: Decimal
    total_cost: Decimal
    current_price: Decimal | None = None
    current_price_stale: bool = False
    unrealized_pnl: Decimal | None = None
    unrealized_pnl_pct: Decimal | None = None


class AllocationItem(BaseModel):
    """Portfolio allocation for a single asset class."""
    asset_class: str
    total_value: Decimal
    percentage: Decimal


class PnLResponse(BaseModel):
    """Portfolio-level P&L and allocation breakdown.

    total_invested: sum of total_cost across all open positions (cost basis).
    total_return_pct: (unrealized + realized) / total_invested * 100.
      None when total_invested == 0 (empty portfolio).
    """
    positions: list[PositionResponse]
    realized_pnl_total: Decimal
    unrealized_pnl_total: Decimal
    total_portfolio_value: Decimal
    total_invested: Decimal                  # cost basis of all open positions
    total_return_pct: Decimal | None         # (unrealized + realized) / invested * 100
    allocation: list[AllocationItem]


class BenchmarkResponse(BaseModel):
    """CDI rate and IBOVESPA index price from Redis macro/quote cache."""
    cdi: Decimal | None = None
    ibovespa_price: Decimal | None = None
    data_stale: bool = False
    fetched_at: datetime | None = None


class DividendResponse(BaseModel):
    """A single dividend, JSCP, or amortization transaction."""
    model_config = ConfigDict(from_attributes=True)

    id: str
    ticker: str
    asset_class: str
    transaction_type: str
    transaction_date: date
    quantity: Decimal
    unit_price: Decimal
    total_value: Decimal
    is_exempt: bool
