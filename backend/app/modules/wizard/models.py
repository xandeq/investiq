"""SQLAlchemy model for the Wizard Onde Investir async job (Phase 11).

Status flow: pending → running → completed
                               ↘ failed

result_json stores the JSON-serialized WizardResult when completed.
RLS policy ensures tenants see only their own wizard jobs.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, Index, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.modules.auth.models import Base


def _utcnow() -> datetime:
    return datetime.now(tz=timezone.utc)


class WizardJob(Base):
    """Async AI recommendation job for the Wizard Onde Investir feature."""

    __tablename__ = "wizard_jobs"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    tenant_id: Mapped[str] = mapped_column(String(36), nullable=False)
    perfil: Mapped[str] = mapped_column(String(20), nullable=False)   # conservador | moderado | arrojado
    prazo: Mapped[str] = mapped_column(String(5), nullable=False)     # 6m | 1a | 2a | 5a
    valor: Mapped[float] = mapped_column(Numeric(20, 2), nullable=False)
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="pending"
    )  # pending | running | completed | failed
    result_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    error_message: Mapped[str | None] = mapped_column(String(500), nullable=True)
    retry_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        Index("ix_wizard_jobs_tenant_status", "tenant_id", "status"),
        Index("ix_wizard_jobs_tenant_created", "tenant_id", "created_at"),
    )

    def __repr__(self) -> str:
        return f"<WizardJob id={self.id} perfil={self.perfil} status={self.status}>"
