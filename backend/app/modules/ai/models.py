"""SQLAlchemy 2.x models for the AI analysis engine.

Models:
- AIAnalysisJob: tracks async AI analysis requests with status and result storage.

Design notes:
- tenant_id stored directly (no FK to users) — RLS policy handles isolation.
- result_json stores JSON-serialized analysis result (Text column — can be large).
- completed_at is nullable — set when status transitions to "completed" or "failed".
- Uses the shared Base from app.modules.auth.models for Alembic autogenerate.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.modules.auth.models import Base


def _utcnow() -> datetime:
    return datetime.now(tz=timezone.utc)


class AIAnalysisJob(Base):
    """Tracks async AI analysis jobs for the analysis pipeline.

    Status flow:
        pending → running → completed
                          ↘ failed

    result_json stores the serialized dict returned by the Celery task.
    error_message is set when status = "failed".
    """
    __tablename__ = "ai_analysis_jobs"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    tenant_id: Mapped[str] = mapped_column(String(36), nullable=False)
    job_type: Mapped[str] = mapped_column(
        String(20), nullable=False
    )  # "asset" | "macro" | "portfolio"
    ticker: Mapped[str | None] = mapped_column(
        String(20), nullable=True
    )  # for asset analysis; None for macro/portfolio
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="pending"
    )  # "pending" | "running" | "completed" | "failed"
    result_json: Mapped[str | None] = mapped_column(
        Text, nullable=True
    )  # JSON-serialized result dict
    error_message: Mapped[str | None] = mapped_column(
        String(500), nullable=True
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    __table_args__ = (
        Index("ix_ai_jobs_tenant_status", "tenant_id", "status"),
        Index("ix_ai_jobs_tenant_created", "tenant_id", "created_at"),
    )

    def __repr__(self) -> str:
        return (
            f"<AIAnalysisJob id={self.id} type={self.job_type} "
            f"ticker={self.ticker} status={self.status}>"
        )


class AIUsageLog(Base):
    """Tracks every LLM API call made by the AI engine."""
    __tablename__ = "ai_usage_logs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    tenant_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    job_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    tier: Mapped[str] = mapped_column(String(20), nullable=False)        # "free" | "paid" | "admin"
    provider: Mapped[str] = mapped_column(String(30), nullable=False)    # "openai" | "openrouter" | "groq" | "cerebras" | "gemini"
    model: Mapped[str] = mapped_column(String(100), nullable=False)
    duration_ms: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    success: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    error: Mapped[str | None] = mapped_column(String(300), nullable=True)

    __table_args__ = (
        Index("ix_ai_usage_created", "created_at"),
        Index("ix_ai_usage_tenant", "tenant_id"),
        Index("ix_ai_usage_tier", "tier"),
    )
