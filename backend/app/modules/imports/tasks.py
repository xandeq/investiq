"""Celery tasks for the broker import pipeline.

CRITICAL: Celery tasks are synchronous. NEVER use asyncpg or FastAPI
async sessions here. All DB access uses get_sync_db_session (psycopg2).

CRITICAL: NEVER pass file_bytes as a Celery task argument. File content
can be 5-10 MB in production — too large for Redis messages. Tasks read
bytes from the import_files table by file_id.

Task flow:
1. parse_pdf_import: read bytes → correpy → pdfplumber → gpt4o → write staging rows
2. parse_csv_import: read bytes → parse_csv() → write staging rows
"""
from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

from celery import shared_task
from sqlalchemy import delete, select, update

from app.core.db_sync import get_sync_db_session, get_superuser_sync_db_session

logger = logging.getLogger(__name__)


def _update_import_job_status(
    job_id: str,
    status: str,
    staging_count: int | None = None,
    error_message: str | None = None,
) -> None:
    """Update import_jobs row in DB using superuser connection to avoid race conditions.

    Uses postgres superuser so the UPDATE works even if the FastAPI transaction
    that inserted the row hasn't committed yet.
    """
    try:
        from app.modules.imports.models import ImportJob

        now = datetime.now(timezone.utc)
        values: dict[str, Any] = {"status": status}
        if staging_count is not None:
            values["staging_count"] = staging_count
        if error_message is not None:
            values["error_message"] = error_message
        if status in ("completed", "failed"):
            values["completed_at"] = now

        with get_superuser_sync_db_session() as session:
            session.execute(
                update(ImportJob)
                .where(ImportJob.id == job_id)
                .values(**values)
            )
    except Exception as exc:
        logger.error(
            "Failed to update import job %s status to %s: %s", job_id, status, exc
        )


def _write_staging_rows(
    job_id: str,
    tenant_id: str,
    transactions: list,
    session_factory=None,
) -> None:
    """Write parsed transactions to import_staging table.

    Accepts both dict (from PDF parsers) and CSVTransactionRow (from CSV parser).
    Uses a fresh sync DB session to write all rows in one commit.

    Args:
        job_id: ID of the ImportJob these rows belong to.
        tenant_id: Tenant ID for RLS scoping.
        transactions: List of dicts or CSVTransactionRow Pydantic models.
        session_factory: Optional override for testing (defaults to get_sync_db_session).
    """
    if not transactions:
        return

    from app.modules.imports.models import ImportStaging, compute_import_hash
    from app.modules.portfolio.models import Transaction

    factory = session_factory or get_sync_db_session

    with factory(tenant_id=tenant_id) as session:
        # Idempotent: delete any existing staging rows for this job before re-inserting.
        # This makes re-parse safe — no UniqueViolation on uq_import_staging_tenant_hash.
        session.execute(
            delete(ImportStaging).where(
                ImportStaging.job_id == job_id,
                ImportStaging.tenant_id == tenant_id,
            )
        )

        # Load confirmed transaction hashes for this tenant to flag duplicates at parse time.
        existing_hashes_result = session.execute(
            select(Transaction.import_hash).where(
                Transaction.tenant_id == tenant_id,
                Transaction.import_hash.is_not(None),
            )
        )
        existing_hashes: set[str] = {row[0] for row in existing_hashes_result}

        for txn in transactions:
            try:
                # Handle both dict (PDF parsers) and CSVTransactionRow (csv_parser)
                if hasattr(txn, "model_dump"):
                    # Pydantic model
                    data = txn.model_dump()
                else:
                    data = txn

                ticker = str(data.get("ticker", "")).upper()
                txn_type = str(data.get("transaction_type", "buy")).lower()
                txn_date = data.get("transaction_date")
                quantity = Decimal(str(data.get("quantity", 0)))
                unit_price = Decimal(str(data.get("unit_price", 0)))
                total_value = Decimal(str(data.get("total_value", 0))) or (
                    quantity * unit_price
                )
                asset_class = str(data.get("asset_class", "acao"))
                brokerage_fee = Decimal(str(data.get("brokerage_fee", 0)))
                irrf_withheld = Decimal(str(data.get("irrf_withheld", 0)))
                notes = str(data.get("notes", ""))
                parser_source = str(data.get("parser_source", "unknown"))

                import_hash = compute_import_hash(
                    tenant_id, ticker, txn_type, txn_date, quantity, unit_price
                )

                staging_row = ImportStaging(
                    id=str(uuid.uuid4()),
                    job_id=job_id,
                    tenant_id=tenant_id,
                    ticker=ticker,
                    asset_class=asset_class,
                    transaction_type=txn_type,
                    transaction_date=txn_date,
                    quantity=quantity,
                    unit_price=unit_price,
                    total_value=total_value,
                    brokerage_fee=brokerage_fee,
                    irrf_withheld=irrf_withheld,
                    notes=notes,
                    parser_source=parser_source,
                    import_hash=import_hash,
                    is_duplicate=import_hash in existing_hashes,
                )
                session.add(staging_row)
            except Exception as row_exc:
                logger.warning(
                    "Failed to write staging row for job %s: %s", job_id, row_exc
                )
                continue


def _parse_with_cascade(pdf_bytes: bytes) -> list[dict]:
    """Run PDF parser cascade: correpy → pdfplumber → gpt4o.

    Each parser returns a list of transaction dicts. The cascade stops at
    the first parser that returns non-empty results.

    Returns:
        List of transaction dicts (may be empty if all parsers fail).
    """
    from app.modules.imports.parsers.correpy_parser import parse_with_correpy
    from app.modules.imports.parsers.pdfplumber_parser import parse_with_pdfplumber
    from app.modules.imports.parsers.gpt4o_parser import parse_with_gpt4o

    # Step 1: try correpy (primary parser for SINACOR-format notas)
    results = parse_with_correpy(pdf_bytes)
    if results:
        logger.info("PDF cascade: correpy succeeded with %d transactions", len(results))
        return results

    # Step 2: try pdfplumber (table extraction fallback)
    results = parse_with_pdfplumber(pdf_bytes)
    if results:
        logger.info("PDF cascade: pdfplumber succeeded with %d transactions", len(results))
        return results

    # Step 3: try GPT-4o (vision-based last resort)
    results = parse_with_gpt4o(pdf_bytes)
    if results:
        logger.info("PDF cascade: gpt4o succeeded with %d transactions", len(results))
    else:
        logger.warning("PDF cascade: all parsers returned empty results")

    return results


@shared_task(name="imports.parse_pdf_import", bind=True, max_retries=2)
def parse_pdf_import(self, job_id: str, file_id: str, tenant_id: str) -> dict:
    """Parse a broker PDF nota de corretagem and write staging rows.

    Reads file bytes from DB (NOT passed as task arg — too large for Redis).
    Runs cascade: correpy → pdfplumber → gpt4o.
    Writes parsed rows to import_staging.

    Args:
        job_id: ImportJob ID to update with status.
        file_id: ImportFile ID to read bytes from.
        tenant_id: Tenant ID for RLS and staging rows.

    Returns:
        Dict with job_id and count of parsed transactions.
    """
    logger.info("parse_pdf_import: starting (job=%s, file=%s)", job_id, file_id)
    _update_import_job_status(job_id, "running")

    try:
        from app.modules.imports.models import ImportFile

        # Read file bytes from DB — NEVER passed as Celery task arg
        with get_sync_db_session(tenant_id=tenant_id) as session:
            file_row = session.get(ImportFile, file_id)
            if file_row is None:
                raise ValueError(f"ImportFile {file_id} not found")
            pdf_bytes = bytes(file_row.file_bytes)

        # Run parser cascade
        transactions = _parse_with_cascade(pdf_bytes)

        # Write staging rows
        _write_staging_rows(job_id, tenant_id, transactions)

        count = len(transactions)
        _update_import_job_status(job_id, "completed", staging_count=count)
        logger.info("parse_pdf_import: completed (job=%s, count=%d)", job_id, count)
        return {"job_id": job_id, "count": count}

    except Exception as exc:
        error_msg = str(exc)
        logger.error("parse_pdf_import: failed (job=%s): %s", job_id, error_msg)
        _update_import_job_status(job_id, "failed", error_message=error_msg)
        raise


@shared_task(name="imports.parse_xlsx_import", bind=True, max_retries=2)
def parse_xlsx_import(self, job_id: str, file_id: str, tenant_id: str) -> dict:
    """Parse a Clear PosicaoDetalhada.xlsx and write synthetic buy staging rows.

    Reads file bytes from DB. Converts each position (ação or FII) to a
    synthetic 'buy' transaction using preço médio × quantidade.

    Args:
        job_id: ImportJob ID to update with status.
        file_id: ImportFile ID to read bytes from.
        tenant_id: Tenant ID for RLS and staging rows.

    Returns:
        Dict with job_id and count of parsed transactions.
    """
    logger.info("parse_xlsx_import: starting (job=%s, file=%s)", job_id, file_id)
    _update_import_job_status(job_id, "running")

    try:
        from app.modules.imports.models import ImportFile
        from app.modules.imports.parsers.xlsx_parser import parse_xlsx

        with get_sync_db_session(tenant_id=tenant_id) as session:
            file_row = session.get(ImportFile, file_id)
            if file_row is None:
                raise ValueError(f"ImportFile {file_id} not found")
            xlsx_bytes = bytes(file_row.file_bytes)

        transactions, warnings = parse_xlsx(xlsx_bytes)

        if warnings:
            logger.warning(
                "parse_xlsx_import: %d warnings (job=%s): %s",
                len(warnings), job_id, warnings,
            )

        _write_staging_rows(job_id, tenant_id, transactions)

        count = len(transactions)
        _update_import_job_status(job_id, "completed", staging_count=count)
        logger.info("parse_xlsx_import: completed (job=%s, count=%d)", job_id, count)
        return {"job_id": job_id, "count": count, "warnings": warnings}

    except Exception as exc:
        error_msg = str(exc)
        logger.error("parse_xlsx_import: failed (job=%s): %s", job_id, error_msg)
        _update_import_job_status(job_id, "failed", error_message=error_msg)
        raise


@shared_task(name="imports.parse_csv_import", bind=True, max_retries=2)
def parse_csv_import(self, job_id: str, file_id: str, tenant_id: str) -> dict:
    """Parse a CSV transaction import and write staging rows.

    Reads file bytes from DB. Validates rows via CSVTransactionRow Pydantic model.
    Writes valid rows to import_staging. Invalid rows are logged but do not
    fail the job — partial staging is acceptable.

    Args:
        job_id: ImportJob ID to update with status.
        file_id: ImportFile ID to read bytes from.
        tenant_id: Tenant ID for RLS and staging rows.

    Returns:
        Dict with job_id and count of valid staging rows written.
    """
    logger.info("parse_csv_import: starting (job=%s, file=%s)", job_id, file_id)
    _update_import_job_status(job_id, "running")

    try:
        from app.modules.imports.models import ImportFile
        from app.modules.imports.parsers.csv_parser import parse_csv

        # Read file bytes from DB
        with get_sync_db_session(tenant_id=tenant_id) as session:
            file_row = session.get(ImportFile, file_id)
            if file_row is None:
                raise ValueError(f"ImportFile {file_id} not found")
            csv_bytes = bytes(file_row.file_bytes)

        # Parse and validate CSV rows
        valid_rows, errors = parse_csv(csv_bytes)

        if errors:
            logger.warning(
                "parse_csv_import: %d validation errors (job=%s): %s",
                len(errors), job_id, errors[:3],  # log first 3 errors
            )

        # Write valid staging rows (even if some rows failed validation)
        _write_staging_rows(job_id, tenant_id, valid_rows)

        count = len(valid_rows)
        _update_import_job_status(job_id, "completed", staging_count=count)
        logger.info("parse_csv_import: completed (job=%s, count=%d)", job_id, count)
        return {"job_id": job_id, "count": count, "error_count": len(errors)}

    except Exception as exc:
        error_msg = str(exc)
        logger.error("parse_csv_import: failed (job=%s): %s", job_id, error_msg)
        _update_import_job_status(job_id, "failed", error_message=error_msg)
        raise
