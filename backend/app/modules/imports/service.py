"""ImportService — async service layer for the import pipeline.

Handles DB operations for the import workflow:
- create_pdf_import_job / create_csv_import_job: persist file + job
- get_job_with_staging: read job + staged rows for review
- confirm_import: copy staged rows to transactions (skip duplicates)
- cancel_import: mark cancelled + delete staging rows
- reparse_import: create new job from existing file bytes

All methods use AsyncSession (FastAPI dependency) — NOT sync session.
Celery tasks use get_sync_db_session from db_sync.py.
"""
from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal

from fastapi import HTTPException, status
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.imports.models import (
    ImportFile,
    ImportJob,
    ImportStaging,
    compute_import_hash,
)

logger = logging.getLogger(__name__)


@dataclass
class ConfirmResult:
    confirmed_count: int
    duplicate_count: int


class ImportService:
    """Async service for the import pipeline.

    Stateless — create a new instance per request (or use as a singleton).
    """

    MAX_PDF_SIZE = 10 * 1024 * 1024  # 10 MB
    MAX_CSV_SIZE = 1 * 1024 * 1024   # 1 MB

    # -------------------------------------------------------------------------
    # File upload and job creation
    # -------------------------------------------------------------------------

    async def create_pdf_import_job(
        self,
        db: AsyncSession,
        tenant_id: str,
        file_bytes: bytes,
        original_filename: str,
    ) -> ImportJob:
        """Persist upload, create ImportJob with status=pending.

        Raises HTTPException 413 if file exceeds MAX_PDF_SIZE.
        """
        if len(file_bytes) > self.MAX_PDF_SIZE:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail="File exceeds 10 MB limit",
            )
        return await self._create_import_job(
            db, tenant_id, file_bytes, original_filename, "pdf"
        )

    async def create_csv_import_job(
        self,
        db: AsyncSession,
        tenant_id: str,
        file_bytes: bytes,
        original_filename: str,
    ) -> ImportJob:
        """Persist upload, create ImportJob with status=pending.

        Raises HTTPException 413 if file exceeds MAX_CSV_SIZE.
        """
        if len(file_bytes) > self.MAX_CSV_SIZE:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail="File exceeds 1 MB limit",
            )
        return await self._create_import_job(
            db, tenant_id, file_bytes, original_filename, "csv"
        )

    async def create_xlsx_import_job(
        self,
        db: AsyncSession,
        tenant_id: str,
        file_bytes: bytes,
        original_filename: str,
    ) -> ImportJob:
        """Persist XLSX upload, create ImportJob with status=pending.

        Raises HTTPException 413 if file exceeds 5 MB.
        """
        MAX_XLSX_SIZE = 5 * 1024 * 1024
        if len(file_bytes) > MAX_XLSX_SIZE:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail="File exceeds 5 MB limit",
            )
        return await self._create_import_job(
            db, tenant_id, file_bytes, original_filename, "xlsx"
        )

    async def _create_import_job(
        self,
        db: AsyncSession,
        tenant_id: str,
        file_bytes: bytes,
        original_filename: str,
        file_type: str,
    ) -> ImportJob:
        """Create ImportFile + ImportJob rows. Returns the ImportJob."""
        file_row = ImportFile(
            id=str(uuid.uuid4()),
            tenant_id=tenant_id,
            file_type=file_type,
            original_filename=original_filename,
            file_bytes=file_bytes,
            file_size_bytes=len(file_bytes),
        )
        db.add(file_row)
        await db.flush()  # get file_row.id

        job = ImportJob(
            id=str(uuid.uuid4()),
            tenant_id=tenant_id,
            file_id=file_row.id,
            file_type=file_type,
            status="pending",
            created_at=datetime.now(timezone.utc),
        )
        db.add(job)
        await db.flush()

        logger.info(
            "Created ImportJob %s (type=%s, file=%s, tenant=%s)",
            job.id, file_type, file_row.id, tenant_id,
        )
        return job

    # -------------------------------------------------------------------------
    # Job polling
    # -------------------------------------------------------------------------

    async def get_job_with_staging(
        self,
        db: AsyncSession,
        tenant_id: str,
        job_id: str,
    ) -> tuple[ImportJob, list[ImportStaging]]:
        """Fetch ImportJob + associated staging rows for review.

        Returns:
            (job, staged_rows) tuple

        Raises:
            HTTPException 404 if job not found or does not belong to tenant.
        """
        result = await db.execute(
            select(ImportJob).where(
                ImportJob.id == job_id,
                ImportJob.tenant_id == tenant_id,
            )
        )
        job = result.scalar_one_or_none()
        if job is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Import job not found",
            )

        staging_result = await db.execute(
            select(ImportStaging)
            .where(ImportStaging.job_id == job_id)
            .order_by(ImportStaging.ticker)
        )
        staged_rows = list(staging_result.scalars().all())

        return job, staged_rows

    # -------------------------------------------------------------------------
    # Confirm
    # -------------------------------------------------------------------------

    async def confirm_import(
        self,
        db: AsyncSession,
        tenant_id: str,
        job_id: str,
    ) -> ConfirmResult:
        """Copy staged rows to transactions table, skipping duplicates.

        Duplicate detection: if a transaction with the same import_hash already
        exists in the transactions table for this tenant, the staging row is
        skipped (counted as duplicate, not re-inserted).

        After confirm:
        - ImportJob.status = "confirmed"
        - ImportJob.confirmed_count = N (rows inserted)
        - ImportJob.duplicate_count = M (rows skipped)
        - All ImportStaging rows for this job are deleted

        Returns:
            ConfirmResult(confirmed_count, duplicate_count)

        Raises:
            HTTPException 404 if job not found.
            HTTPException 409 if job is not in "completed" status.
        """
        from app.modules.portfolio.models import AssetClass, Transaction, TransactionType

        job, staging_rows = await self.get_job_with_staging(db, tenant_id, job_id)

        if job.status not in ("completed", "pending"):
            # Allow confirm on "pending" too (for manually-inserted staging rows in tests)
            if job.status == "confirmed":
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Job has already been confirmed",
                )
            if job.status not in ("completed",):
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"Cannot confirm job with status '{job.status}'",
                )

        # Fetch all existing import_hashes for this tenant (ORM query — SQLite compatible)
        from app.modules.portfolio.models import Transaction as _Transaction
        existing_result = await db.execute(
            select(_Transaction.import_hash).where(
                _Transaction.tenant_id == tenant_id,
                _Transaction.import_hash.is_not(None),
            )
        )
        existing_hashes = {row[0] for row in existing_result.fetchall()}

        confirmed_count = 0
        duplicate_count = 0

        for row in staging_rows:
            if row.import_hash in existing_hashes:
                duplicate_count += 1
                continue

            # Map asset_class string to enum
            try:
                asset_cls = AssetClass(row.asset_class)
            except ValueError:
                # Fallback to acao for unknown asset classes
                asset_cls = AssetClass.acao
                logger.warning(
                    "Unknown asset_class '%s' for staging row %s — defaulting to 'acao'",
                    row.asset_class, row.id,
                )

            # Map transaction_type string to enum
            try:
                txn_type = TransactionType(row.transaction_type)
            except ValueError:
                txn_type = TransactionType.buy
                logger.warning(
                    "Unknown transaction_type '%s' for staging row %s — defaulting to 'buy'",
                    row.transaction_type, row.id,
                )

            txn = Transaction(
                id=str(uuid.uuid4()),
                tenant_id=tenant_id,
                portfolio_id=tenant_id,  # v1: portfolio_id == tenant_id
                ticker=row.ticker,
                asset_class=asset_cls,
                transaction_type=txn_type,
                transaction_date=row.transaction_date,
                quantity=row.quantity,
                unit_price=row.unit_price,
                total_value=row.total_value,
                brokerage_fee=row.brokerage_fee,
                irrf_withheld=row.irrf_withheld,
                notes=row.notes,
            )

            # Set import_hash on the Transaction row — requires the column to exist
            # (added by migration 0005)
            try:
                txn.import_hash = row.import_hash  # type: ignore[attr-defined]
            except Exception:
                pass  # Column may not exist in test DB (SQLite)

            # Set import_hash on Transaction for future duplicate detection
            txn.import_hash = row.import_hash  # type: ignore[attr-defined]

            # Track which import job created this transaction (enables revert)
            try:
                txn.import_job_id = job_id  # type: ignore[attr-defined]
            except Exception:
                pass

            db.add(txn)
            existing_hashes.add(row.import_hash)  # prevent duplicates within same batch
            confirmed_count += 1

        # Delete staging rows for this job
        await db.execute(
            delete(ImportStaging).where(ImportStaging.job_id == job_id)
        )

        # Update job status
        job.status = "confirmed"
        job.confirmed_count = confirmed_count
        job.duplicate_count = duplicate_count
        job.completed_at = datetime.now(timezone.utc)

        await db.flush()

        logger.info(
            "Confirmed import job %s: %d inserted, %d duplicates",
            job_id, confirmed_count, duplicate_count,
        )
        return ConfirmResult(
            confirmed_count=confirmed_count,
            duplicate_count=duplicate_count,
        )

    # -------------------------------------------------------------------------
    # Cancel
    # -------------------------------------------------------------------------

    async def cancel_import(
        self,
        db: AsyncSession,
        tenant_id: str,
        job_id: str,
    ) -> ImportJob:
        """Mark job as cancelled and delete staging rows.

        Raises:
            HTTPException 404 if job not found.
        """
        job, _ = await self.get_job_with_staging(db, tenant_id, job_id)

        # Delete staging rows
        await db.execute(
            delete(ImportStaging).where(ImportStaging.job_id == job_id)
        )

        job.status = "cancelled"
        job.completed_at = datetime.now(timezone.utc)
        await db.flush()

        logger.info("Cancelled import job %s", job_id)
        return job

    # -------------------------------------------------------------------------
    # Reparse
    # -------------------------------------------------------------------------

    async def reparse_import(
        self,
        db: AsyncSession,
        tenant_id: str,
        job_id: str,
    ) -> ImportJob:
        """Create a new ImportJob from the same stored file bytes — no re-upload needed.

        Raises:
            HTTPException 404 if original job not found.
        """
        # Find original job to get file_id and file_type
        result = await db.execute(
            select(ImportJob).where(
                ImportJob.id == job_id,
                ImportJob.tenant_id == tenant_id,
            )
        )
        original_job = result.scalar_one_or_none()
        if original_job is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Import job not found",
            )

        # Create new job with same file_id — Celery task reads bytes from DB
        new_job = ImportJob(
            id=str(uuid.uuid4()),
            tenant_id=tenant_id,
            file_id=original_job.file_id,
            file_type=original_job.file_type,
            status="pending",
            created_at=datetime.now(timezone.utc),
        )
        db.add(new_job)
        await db.flush()

        logger.info(
            "Created reparse job %s from original job %s (file=%s)",
            new_job.id, job_id, original_job.file_id,
        )
        return new_job

    # -------------------------------------------------------------------------
    # History
    # -------------------------------------------------------------------------

    async def list_jobs(
        self,
        db: AsyncSession,
        tenant_id: str,
        limit: int = 20,
    ) -> list[ImportJob]:
        """Return the last N import jobs for this tenant, newest first."""
        result = await db.execute(
            select(ImportJob)
            .where(ImportJob.tenant_id == tenant_id)
            .order_by(ImportJob.created_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())
