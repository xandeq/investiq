"""SQLAlchemy 2.x models for the imports module.

Models:
- ImportFile: stores raw uploaded file bytes permanently
- ImportJob: tracks the parse/review workflow lifecycle
- ImportStaging: holds parsed rows awaiting user confirmation

Design notes:
- ImportFile stores file_bytes as LargeBinary — never passed as Celery task arg.
  Celery tasks read bytes from DB by file_id to avoid Redis message size limits.
- import_hash on ImportStaging enables duplicate detection at confirm time.
- tenant_id on all tables — RLS policies enforce isolation at the DB level.
"""
from __future__ import annotations

import hashlib
import uuid
from datetime import date, datetime, timezone
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    Index,
    Integer,
    LargeBinary,
    Numeric,
    String,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.modules.auth.models import Base


def _utcnow() -> datetime:
    return datetime.now(tz=timezone.utc)


class ImportFile(Base):
    """Raw uploaded file — bytes stored permanently for re-parsing.

    Never pass file_bytes as a Celery task argument. Task reads bytes from DB
    by file_id. This avoids Redis message size limits (default 512 MB but
    PDFs can be 5-10 MB in production).
    """
    __tablename__ = "import_files"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    tenant_id: Mapped[str] = mapped_column(String(36), nullable=False)
    file_type: Mapped[str] = mapped_column(String(10))  # "pdf" | "csv"
    original_filename: Mapped[str] = mapped_column(String(255))
    file_bytes: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    file_size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    uploaded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow
    )

    __table_args__ = (Index("ix_import_files_tenant", "tenant_id"),)

    def __repr__(self) -> str:
        return (
            f"<ImportFile id={self.id} type={self.file_type} "
            f"size={self.file_size_bytes} tenant={self.tenant_id}>"
        )


class ImportJob(Base):
    """Tracks the lifecycle of one import operation.

    Status flow:
        pending → running → completed → confirmed
                          ↘ failed
        (any) → cancelled

    staging_count: set when Celery task completes (number of rows parsed)
    confirmed_count: set after user confirms (rows inserted into transactions)
    duplicate_count: set after user confirms (rows skipped as duplicates)
    """
    __tablename__ = "import_jobs"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    tenant_id: Mapped[str] = mapped_column(String(36), nullable=False)
    file_id: Mapped[str] = mapped_column(String(36), nullable=False)  # FK to import_files.id
    file_type: Mapped[str] = mapped_column(String(10))  # "pdf" | "csv"
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="pending"
    )  # "pending" | "running" | "completed" | "failed" | "confirmed" | "cancelled"
    staging_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    confirmed_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    duplicate_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    error_message: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    __table_args__ = (
        Index("ix_import_jobs_tenant_status", "tenant_id", "status"),
    )

    def __repr__(self) -> str:
        return (
            f"<ImportJob id={self.id} type={self.file_type} "
            f"status={self.status} tenant={self.tenant_id}>"
        )


class ImportStaging(Base):
    """Parsed transaction rows awaiting user review and confirmation.

    Rows are written by the Celery parse task and deleted after confirm or cancel.
    import_hash enables idempotent duplicate detection at confirm time.
    """
    __tablename__ = "import_staging"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    job_id: Mapped[str] = mapped_column(String(36), nullable=False)
    tenant_id: Mapped[str] = mapped_column(String(36), nullable=False)
    ticker: Mapped[str] = mapped_column(String(20), nullable=False)
    asset_class: Mapped[str] = mapped_column(String(20), nullable=False)
    transaction_type: Mapped[str] = mapped_column(String(20), nullable=False)
    transaction_date: Mapped[date] = mapped_column(Date, nullable=False)
    quantity: Mapped[Decimal] = mapped_column(Numeric(20, 8), nullable=False)
    unit_price: Mapped[Decimal] = mapped_column(Numeric(20, 8), nullable=False)
    total_value: Mapped[Decimal] = mapped_column(Numeric(20, 8), nullable=False)
    brokerage_fee: Mapped[Decimal] = mapped_column(
        Numeric(20, 8), default=Decimal("0")
    )
    irrf_withheld: Mapped[Decimal] = mapped_column(
        Numeric(20, 8), default=Decimal("0")
    )
    notes: Mapped[str] = mapped_column(String(500), default="")
    parser_source: Mapped[str] = mapped_column(
        String(20)
    )  # "correpy" | "pdfplumber" | "gpt4o" | "csv"
    import_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    is_duplicate: Mapped[bool] = mapped_column(Boolean, default=False)

    __table_args__ = (Index("ix_import_staging_job", "job_id"),)

    def __repr__(self) -> str:
        return (
            f"<ImportStaging id={self.id} ticker={self.ticker} "
            f"type={self.transaction_type} job={self.job_id}>"
        )


def compute_import_hash(
    tenant_id: str,
    ticker: str,
    txn_type: str,
    txn_date: date,
    quantity: Decimal,
    unit_price: Decimal,
) -> str:
    """Compute a deterministic hash for duplicate detection.

    The hash is based on the five dimensions that uniquely identify a
    transaction: tenant, ticker, type, date, quantity, and unit_price.
    Two staging rows with the same hash represent the same transaction —
    the second is considered a duplicate and skipped on confirm.

    Returns:
        64-character hex SHA-256 digest.
    """
    parts = "|".join([
        tenant_id,
        ticker.upper(),
        txn_type.lower(),
        str(txn_date),
        f"{quantity:.8f}",
        f"{unit_price:.8f}",
    ])
    return hashlib.sha256(parts.encode("utf-8")).hexdigest()
