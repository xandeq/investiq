"""Pydantic schemas for the investor profile module."""
from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class InvestorProfileUpsert(BaseModel):
    """Input schema for POST /profile (create or update)."""
    idade: int | None = Field(None, ge=18, le=120)
    renda_mensal: Decimal | None = Field(None, ge=0)
    patrimonio_total: Decimal | None = Field(None, ge=0)
    objetivo: str | None = Field(None, pattern="^(aposentadoria|renda_passiva|crescimento|reserva)$")
    horizonte_anos: int | None = Field(None, ge=1, le=50)
    tolerancia_risco: str | None = Field(None, pattern="^(conservador|moderado|arrojado)$")
    percentual_renda_fixa_alvo: Decimal | None = Field(None, ge=0, le=100)


class InvestorProfileResponse(InvestorProfileUpsert):
    """Response schema for GET /profile."""
    model_config = ConfigDict(from_attributes=True)

    id: str
    tenant_id: str
    completion_pct: int = 0  # computed, not stored
    updated_at: datetime | None = None
