"""Pydantic schemas for the funds module."""
from __future__ import annotations

from datetime import date
from decimal import Decimal

from pydantic import BaseModel, ConfigDict


class FundInfoResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    cnpj: str
    name: str
    admin: str | None = None
    fund_class: str | None = None
    status: str | None = None


class FundSearchResult(BaseModel):
    cnpj: str
    name: str
    admin: str | None = None
    fund_class: str | None = None


class FundQuoteResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    cnpj: str
    quote_date: date
    nav_per_quota: Decimal
    net_assets_brl: Decimal | None = None


class FundPosition(BaseModel):
    cnpj: str
    name: str
    quantity: Decimal
    cmp: Decimal
    total_cost: Decimal
    current_nav: Decimal | None = None
    nav_stale: bool = True
    unrealized_pnl: Decimal | None = None
    unrealized_pnl_pct: Decimal | None = None
    quote_date: date | None = None
