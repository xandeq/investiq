"""Pydantic schemas for Redis cache serialization — market data module.

These models represent the shape of data stored in Redis and returned
by the MarketDataService. The data_stale flag is True when Redis returns
None (cache miss) and the service returns a fallback/empty value.

All Decimal conversions use Decimal(str(float_value)) — never Decimal(float_value)
to avoid IEEE 754 floating-point precision issues.
"""
from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict


class QuoteCache(BaseModel):
    """B3 stock quote stored in Redis at market:quote:{TICKER}."""

    model_config = ConfigDict(from_attributes=True)

    symbol: str
    price: Decimal
    change: Decimal
    change_pct: Decimal
    fetched_at: datetime
    data_stale: bool = False


class MacroCache(BaseModel):
    """Macro economic indicators stored in Redis at market:macro:*.

    Individual indicators are stored as separate keys:
      market:macro:selic, market:macro:cdi, market:macro:ipca,
      market:macro:ptax_usd, market:macro:fetched_at
    This model assembles them into a single response object.
    """

    model_config = ConfigDict(from_attributes=True)

    selic: Decimal
    cdi: Decimal
    ipca: Decimal
    ptax_usd: Decimal
    fetched_at: datetime
    data_stale: bool = False


class FundamentalsCache(BaseModel):
    """Fundamental analysis data stored in Redis at market:fundamentals:{TICKER}.

    Fields are nullable because brapi.dev may not return all values for
    every ticker (e.g., FIIs don't have EV/EBITDA).
    """

    model_config = ConfigDict(from_attributes=True)

    ticker: str
    pl: Decimal | None = None       # P/L (Price-to-Earnings) ratio
    pvp: Decimal | None = None      # P/VP (Price-to-Book) ratio
    dy: Decimal | None = None       # Dividend Yield %
    ev_ebitda: Decimal | None = None  # EV/EBITDA multiple
    fetched_at: datetime
    data_stale: bool = False


class HistoricalPoint(BaseModel):
    """Single OHLCV data point in a historical price series."""

    model_config = ConfigDict(from_attributes=True)

    date: int        # Unix epoch timestamp
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: int


class HistoricalCache(BaseModel):
    """Historical OHLCV data stored in Redis at market:historical:{TICKER}."""

    model_config = ConfigDict(from_attributes=True)

    ticker: str
    points: list[HistoricalPoint]
    fetched_at: datetime
    data_stale: bool = False
