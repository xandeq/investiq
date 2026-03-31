"""SQLAlchemy models for the AI Analysis module (Phase 12).

Tables:
- analysis_jobs: Async analysis job tracking (DCF, earnings, dividend, sector)
- analysis_quota_logs: Per-tenant monthly quota enforcement
- analysis_cost_logs: Per-analysis LLM cost tracking

Status flow for AnalysisJob: pending -> running -> completed
                                                -> failed
                                                -> stale (data outdated)

All tables are tenant-scoped via tenant_id (same pattern as WizardJob).
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, Index, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.modules.auth.models import Base


def _utcnow() -> datetime:
    return datetime.now(tz=timezone.utc)


class AnalysisJob(Base):
    """Async AI analysis job (DCF, earnings, dividend, sector)."""

    __tablename__ = "analysis_jobs"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    tenant_id: Mapped[str] = mapped_column(String(36), nullable=False)
    analysis_type: Mapped[str] = mapped_column(
        String(50), nullable=False
    )  # dcf | earnings | dividend | sector
    ticker: Mapped[str] = mapped_column(String(10), nullable=False)
    data_timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    data_version_id: Mapped[str] = mapped_column(
        String(100), nullable=False
    )  # e.g. "brapi_eod_20260331_v1.2"
    data_sources: Mapped[str | None] = mapped_column(
        Text, nullable=True
    )  # JSON array string
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="pending"
    )  # pending | running | completed | failed | stale
    result_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    error_message: Mapped[str | None] = mapped_column(String(500), nullable=True)
    retry_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    __table_args__ = (
        Index("ix_analysis_jobs_tenant_status", "tenant_id", "status"),
        Index("ix_analysis_jobs_tenant_ticker", "tenant_id", "ticker"),
        Index("ix_analysis_jobs_created", "created_at"),
        Index("ix_analysis_jobs_data_version", "data_version_id"),
    )

    def __repr__(self) -> str:
        return (
            f"<AnalysisJob id={self.id} type={self.analysis_type} "
            f"ticker={self.ticker} status={self.status}>"
        )


class AnalysisQuotaLog(Base):
    """Per-tenant monthly quota tracking for analysis requests."""

    __tablename__ = "analysis_quota_logs"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    tenant_id: Mapped[str] = mapped_column(String(36), nullable=False)
    year_month: Mapped[str] = mapped_column(
        String(7), nullable=False
    )  # format "2026-03"
    plan_tier: Mapped[str] = mapped_column(
        String(20), nullable=False
    )  # free | pro | enterprise
    quota_limit: Mapped[int] = mapped_column(Integer, nullable=False)
    quota_used: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    __table_args__ = (
        Index("ix_quota_tenant_month", "tenant_id", "year_month", unique=True),
    )

    def __repr__(self) -> str:
        return (
            f"<AnalysisQuotaLog tenant={self.tenant_id} "
            f"month={self.year_month} used={self.quota_used}/{self.quota_limit}>"
        )


class AnalysisCostLog(Base):
    """Per-analysis LLM cost tracking for ops dashboard."""

    __tablename__ = "analysis_cost_logs"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    tenant_id: Mapped[str] = mapped_column(String(36), nullable=False)
    job_id: Mapped[str] = mapped_column(String(36), nullable=False)
    analysis_type: Mapped[str] = mapped_column(String(50), nullable=False)
    ticker: Mapped[str] = mapped_column(String(10), nullable=False)
    llm_provider: Mapped[str | None] = mapped_column(String(50), nullable=True)
    llm_model: Mapped[str | None] = mapped_column(String(100), nullable=True)
    input_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    output_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    estimated_cost_usd: Mapped[float | None] = mapped_column(
        Numeric(10, 4), nullable=True
    )
    duration_ms: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow
    )

    __table_args__ = (
        Index("ix_cost_tenant_created", "tenant_id", "created_at"),
        Index("ix_cost_analysis_type", "analysis_type"),
    )

    def __repr__(self) -> str:
        return (
            f"<AnalysisCostLog job={self.job_id} type={self.analysis_type} "
            f"cost=${self.estimated_cost_usd}>"
        )
