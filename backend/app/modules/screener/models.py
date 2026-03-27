"""SQLAlchemy model for the Goldman Screener feature.

ScreenerRun tracks each async screening job per tenant.
Result stored as JSON (list of 10 stocks with full analysis).
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.modules.auth.models import Base


def _utcnow() -> datetime:
    return datetime.now(tz=timezone.utc)


class ScreenerRun(Base):
    """One stock screening execution per user request.

    Status flow: pending → running → completed / failed
    result_json stores serialized list[StockAnalysis] on completion.
    """

    __tablename__ = "screener_runs"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    tenant_id: Mapped[str] = mapped_column(String(36), nullable=False)

    # Input context saved for history display
    sector_filter: Mapped[str | None] = mapped_column(String(100), nullable=True)
    custom_notes: Mapped[str | None] = mapped_column(String(500), nullable=True)

    # Job lifecycle
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="pending"
    )  # pending | running | completed | failed
    result_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    error_message: Mapped[str | None] = mapped_column(String(500), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    __table_args__ = (
        Index("ix_screener_runs_tenant_created", "tenant_id", "created_at"),
        Index("ix_screener_runs_tenant_status", "tenant_id", "status"),
    )

    def __repr__(self) -> str:
        return f"<ScreenerRun id={self.id} status={self.status} sector={self.sector_filter}>"
