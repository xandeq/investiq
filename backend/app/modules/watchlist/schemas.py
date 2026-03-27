from __future__ import annotations
from datetime import datetime
from decimal import Decimal
from pydantic import BaseModel, ConfigDict, Field


class WatchlistItemCreate(BaseModel):
    ticker: str = Field(..., max_length=20)
    notes: str | None = Field(None, max_length=300)
    price_alert_target: Decimal | None = Field(None, gt=0)


class WatchlistItemResponse(WatchlistItemCreate):
    model_config = ConfigDict(from_attributes=True)
    id: str
    tenant_id: str
    created_at: datetime | None = None


class WatchlistItemUpdate(BaseModel):
    notes: str | None = Field(None, max_length=300)
    price_alert_target: Decimal | None = None
