"""FastAPI router for the broker import pipeline.

Endpoints:
  POST /imports/pdf                    — upload PDF nota de corretagem (202 + job)
  POST /imports/csv                    — upload CSV transactions file (202 + job)
  GET  /imports/jobs/{job_id}          — poll job status + staged rows
  POST /imports/jobs/{job_id}/confirm  — confirm: copy staged rows to transactions
  POST /imports/jobs/{job_id}/cancel   — cancel: delete staging rows
  POST /imports/jobs/{job_id}/reparse  — reparse from stored bytes (no re-upload)
  GET  /imports/history                — list last 20 import jobs
  GET  /imports/template.csv           — download CSV template

Design notes:
- Upload endpoints accept multipart/form-data with a single "file" field.
- File bytes are stored immediately in import_files (DB), then Celery task is
  dispatched. The task reads bytes from DB by file_id — never passed in task args.
- _dispatch_pdf_parse / _dispatch_csv_parse are separate functions to allow
  mocking in tests without importing the Celery task module at startup.
"""

import logging

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.middleware import get_authed_db, get_current_tenant_id
from app.core.plan_gate import get_user_plan, require_import_slot
from app.modules.imports.models import ImportJob
from app.modules.imports.schemas import (
    ConfirmResponse,
    ImportJobDetailResponse,
    ImportJobResponse,
    StagingRowResponse,
)
from app.modules.imports.service import ImportService

logger = logging.getLogger(__name__)
router = APIRouter()

# ---------------------------------------------------------------------------
# Celery dispatch helpers — lazy import prevents worker startup issues in tests
# ---------------------------------------------------------------------------

def _dispatch_pdf_parse(job: ImportJob) -> None:
    """Dispatch parse_pdf_import via configured celery_app to use correct broker URL."""
    from app.celery_app import celery_app
    celery_app.send_task("imports.parse_pdf_import", args=[job.id, job.file_id, job.tenant_id])


def _dispatch_csv_parse(job: ImportJob) -> None:
    """Dispatch parse_csv_import via configured celery_app to use correct broker URL."""
    from app.celery_app import celery_app
    celery_app.send_task("imports.parse_csv_import", args=[job.id, job.file_id, job.tenant_id])


def _dispatch_xlsx_parse(job: ImportJob) -> None:
    """Dispatch parse_xlsx_import via configured celery_app."""
    from app.celery_app import celery_app
    celery_app.send_task("imports.parse_xlsx_import", args=[job.id, job.file_id, job.tenant_id])


# ---------------------------------------------------------------------------
# Upload endpoints
# ---------------------------------------------------------------------------

@router.post(
    "/pdf",
    response_model=ImportJobResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Upload broker PDF nota de corretagem",
)
async def upload_pdf(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_authed_db),
    tenant_id: str = Depends(get_current_tenant_id),
    plan: str = Depends(get_user_plan),
) -> ImportJobResponse:
    """Upload a PDF broker note for parsing.

    Stores file bytes immediately, dispatches Celery parse task, returns 202.
    Poll GET /imports/jobs/{id} to check parse status.

    Free tier: limited to 3 uploads per calendar month. Returns 403 when limit reached.

    Raises:
        400: If file content-type is not PDF.
        403: If free user has reached monthly import limit.
        413: If file exceeds 10 MB.
        401: If not authenticated.
    """
    await require_import_slot(plan, tenant_id, db)
    content_type = (file.content_type or "").lower()
    if "pdf" not in content_type and content_type != "application/octet-stream":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only PDF files accepted",
        )

    content = await file.read()

    svc = ImportService()
    job = await svc.create_pdf_import_job(
        db, tenant_id, content, file.filename or "upload.pdf"
    )

    try:
        _dispatch_pdf_parse(job)
    except Exception as exc:
        # Task dispatch failure does not block the response — job stays "pending"
        logger.warning("PDF parse task dispatch failed for job %s: %s", job.id, exc)

    return ImportJobResponse.model_validate(job)


@router.post(
    "/csv",
    response_model=ImportJobResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Upload CSV transaction file",
)
async def upload_csv(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_authed_db),
    tenant_id: str = Depends(get_current_tenant_id),
    plan: str = Depends(get_user_plan),
) -> ImportJobResponse:
    """Upload a CSV transaction file for parsing and review.

    Stores file bytes immediately, dispatches Celery parse task, returns 202.

    Free tier: limited to 3 uploads per calendar month. Returns 403 when limit reached.

    Raises:
        403: If free user has reached monthly import limit.
        413: If file exceeds 1 MB.
        401: If not authenticated.
    """
    await require_import_slot(plan, tenant_id, db)
    content = await file.read()

    svc = ImportService()
    job = await svc.create_csv_import_job(
        db, tenant_id, content, file.filename or "upload.csv"
    )

    try:
        _dispatch_csv_parse(job)
    except Exception as exc:
        logger.warning("CSV parse task dispatch failed for job %s: %s", job.id, exc)

    return ImportJobResponse.model_validate(job)


@router.post(
    "/xlsx",
    response_model=ImportJobResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Upload Clear PosicaoDetalhada.xlsx position snapshot",
)
async def upload_xlsx(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_authed_db),
    tenant_id: str = Depends(get_current_tenant_id),
    plan: str = Depends(get_user_plan),
) -> ImportJobResponse:
    """Upload a Clear PosicaoDetalhada.xlsx position snapshot.

    Converts each ação/FII position to a synthetic 'buy' transaction using
    preço médio × quantidade. Useful for bootstrapping portfolio history.

    Free tier: limited to 3 uploads per calendar month.

    Raises:
        403: If free user has reached monthly import limit.
        413: If file exceeds 5 MB.
        401: If not authenticated.
    """
    await require_import_slot(plan, tenant_id, db)
    content = await file.read()

    svc = ImportService()
    job = await svc.create_xlsx_import_job(
        db, tenant_id, content, file.filename or "PosicaoDetalhada.xlsx"
    )

    try:
        _dispatch_xlsx_parse(job)
    except Exception as exc:
        logger.warning("XLSX parse task dispatch failed for job %s: %s", job.id, exc)

    return ImportJobResponse.model_validate(job)


# ---------------------------------------------------------------------------
# Job management endpoints
# ---------------------------------------------------------------------------

@router.get(
    "/jobs/{job_id}",
    response_model=ImportJobDetailResponse,
    summary="Get import job status and staged rows",
)
async def get_job(
    job_id: str,
    db: AsyncSession = Depends(get_authed_db),
    tenant_id: str = Depends(get_current_tenant_id),
) -> ImportJobDetailResponse:
    """Return import job status and staged rows for review.

    Staged rows are available when status == "completed".
    Poll this endpoint after uploading until status is not "pending" or "running".

    Raises:
        404: If job not found for this tenant.
    """
    svc = ImportService()
    job, staging_rows = await svc.get_job_with_staging(db, tenant_id, job_id)

    staged_rows_response = [
        StagingRowResponse(
            id=row.id,
            ticker=row.ticker,
            asset_class=row.asset_class,
            transaction_type=row.transaction_type,
            transaction_date=row.transaction_date,
            quantity=str(row.quantity),
            unit_price=str(row.unit_price),
            total_value=str(row.total_value),
            brokerage_fee=str(row.brokerage_fee),
            irrf_withheld=str(row.irrf_withheld),
            notes=row.notes,
            parser_source=row.parser_source,
            is_duplicate=row.is_duplicate,
        )
        for row in staging_rows
    ]

    return ImportJobDetailResponse(
        id=job.id,
        file_id=job.file_id,
        file_type=job.file_type,
        status=job.status,
        staging_count=job.staging_count,
        confirmed_count=job.confirmed_count,
        duplicate_count=job.duplicate_count,
        error_message=job.error_message,
        created_at=job.created_at,
        completed_at=job.completed_at,
        staged_rows=staged_rows_response,
    )


@router.post(
    "/jobs/{job_id}/confirm",
    response_model=ConfirmResponse,
    summary="Confirm import: copy staged rows to transactions",
)
async def confirm_import(
    job_id: str,
    db: AsyncSession = Depends(get_authed_db),
    tenant_id: str = Depends(get_current_tenant_id),
) -> ConfirmResponse:
    """Confirm import job: copy staged rows to the transactions table.

    Duplicate detection: rows with matching import_hash in transactions are
    skipped silently (counted in duplicate_count).

    Raises:
        404: If job not found.
        409: If job already confirmed or in non-confirmable state.
    """
    svc = ImportService()
    result = await svc.confirm_import(db, tenant_id, job_id)

    return ConfirmResponse(
        job_id=job_id,
        confirmed_count=result.confirmed_count,
        duplicate_count=result.duplicate_count,
        status="confirmed",
    )


@router.post(
    "/jobs/{job_id}/cancel",
    response_model=ImportJobResponse,
    summary="Cancel import: delete staged rows",
)
async def cancel_import(
    job_id: str,
    db: AsyncSession = Depends(get_authed_db),
    tenant_id: str = Depends(get_current_tenant_id),
) -> ImportJobResponse:
    """Cancel import job and delete all associated staging rows.

    Raises:
        404: If job not found.
    """
    svc = ImportService()
    job = await svc.cancel_import(db, tenant_id, job_id)
    return ImportJobResponse.model_validate(job)


@router.post(
    "/jobs/{job_id}/reparse",
    response_model=ImportJobResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Reparse import from stored file bytes",
)
async def reparse_import(
    job_id: str,
    db: AsyncSession = Depends(get_authed_db),
    tenant_id: str = Depends(get_current_tenant_id),
) -> ImportJobResponse:
    """Create a new import job from stored file bytes — no re-upload needed.

    Useful when a parser update is available and you want to re-extract data
    from a previously uploaded file.

    Raises:
        404: If original job not found.
    """
    svc = ImportService()
    new_job = await svc.reparse_import(db, tenant_id, job_id)

    try:
        if new_job.file_type == "pdf":
            _dispatch_pdf_parse(new_job)
        else:
            _dispatch_csv_parse(new_job)
    except Exception as exc:
        logger.warning("Reparse task dispatch failed for job %s: %s", new_job.id, exc)

    return ImportJobResponse.model_validate(new_job)


# ---------------------------------------------------------------------------
# History and template
# ---------------------------------------------------------------------------

@router.get(
    "/history",
    response_model=list[ImportJobResponse],
    summary="List recent import jobs",
)
async def list_imports(
    db: AsyncSession = Depends(get_authed_db),
    tenant_id: str = Depends(get_current_tenant_id),
) -> list[ImportJobResponse]:
    """Return the last 20 import jobs for the authenticated tenant, newest first."""
    svc = ImportService()
    jobs = await svc.list_jobs(db, tenant_id, limit=20)
    return [ImportJobResponse.model_validate(j) for j in jobs]


@router.get(
    "/template.csv",
    summary="Download CSV import template",
)
async def download_csv_template() -> StreamingResponse:
    """Return a downloadable CSV template with headers and example rows.

    No authentication required — this is a public template.
    """
    template_content = (
        "ticker,asset_class,transaction_type,transaction_date,quantity,unit_price,brokerage_fee,irrf_withheld,notes\n"
        "PETR4,acao,buy,2025-01-15,100,38.50,4.90,0,\n"
        "BBAS3,acao,sell,2025-01-20,50,55.20,2.90,0.028,Test note\n"
    )

    return StreamingResponse(
        iter([template_content]),
        media_type="text/csv",
        headers={
            "Content-Disposition": 'attachment; filename="import_template.csv"',
        },
    )
