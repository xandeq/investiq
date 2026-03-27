"""InvestorProfile model — stores investor-specific context for AI personalization.

One row per tenant (upsert via POST /profile).
All fields are nullable — partial profiles are valid and progressively enriched.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import DateTime, Integer, Numeric, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.modules.auth.models import Base


def _utcnow() -> datetime:
    return datetime.now(tz=timezone.utc)


class InvestorProfile(Base):
    __tablename__ = "investor_profiles"
    __table_args__ = (UniqueConstraint("tenant_id", name="uq_investor_profiles_tenant"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id: Mapped[str] = mapped_column(String(36), nullable=False)

    # Dados pessoais
    idade: Mapped[int | None] = mapped_column(Integer, nullable=True)
    renda_mensal: Mapped[Decimal | None] = mapped_column(Numeric(18, 2), nullable=True)
    patrimonio_total: Mapped[Decimal | None] = mapped_column(Numeric(18, 2), nullable=True)

    # Objetivo e horizonte
    objetivo: Mapped[str | None] = mapped_column(String(50), nullable=True)   # aposentadoria|renda_passiva|crescimento|reserva
    horizonte_anos: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Tolerância ao risco
    tolerancia_risco: Mapped[str | None] = mapped_column(String(20), nullable=True)  # conservador|moderado|arrojado
    percentual_renda_fixa_alvo: Mapped[Decimal | None] = mapped_column(Numeric(5, 2), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, onupdate=_utcnow, server_default=func.now()
    )
