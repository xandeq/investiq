"""API integration tests for the imports module."""
from __future__ import annotations

import uuid
from datetime import date
from decimal import Decimal
from pathlib import Path
from unittest.mock import patch

import pytest

from app.modules.imports.models import ImportFile, ImportJob, ImportStaging

FIXTURES_DIR = Path(__file__).parent / "fixtures"

pytestmark = pytest.mark.anyio


async def _login_user(client, email_stub, email: str):
    """Register, verify, and login a unique user. Returns user_id."""
    from tests.conftest import register_verify_and_login
    return await register_verify_and_login(client, email_stub, email=email)


async def test_upload_pdf_returns_202(client, db_session, email_stub):
    """POST /imports/pdf with multipart PDF file returns 202 + job_id."""
    await _login_user(client, email_stub, email="pdf_user@example.com")

    with patch("app.modules.imports.router._dispatch_pdf_parse"):
        resp = await client.post(
            "/imports/pdf",
            files={"file": ("test.pdf", b"%PDF-1.4 stub", "application/pdf")},
        )
    assert resp.status_code == 202
    data = resp.json()
    assert "id" in data
    assert data["status"] == "pending"
    assert data["file_type"] == "pdf"


async def test_upload_csv_returns_202(client, db_session, email_stub):
    """POST /imports/csv with multipart CSV file returns 202 + job_id."""
    await _login_user(client, email_stub, email="csv_user@example.com")
    csv_content = (FIXTURES_DIR / "sample_import.csv").read_bytes()

    with patch("app.modules.imports.router._dispatch_csv_parse"):
        resp = await client.post(
            "/imports/csv",
            files={"file": ("test.csv", csv_content, "text/csv")},
        )
    assert resp.status_code == 202
    data = resp.json()
    assert "id" in data
    assert data["status"] == "pending"
    assert data["file_type"] == "csv"


async def test_file_bytes_stored(client, db_session, email_stub):
    """After PDF upload, ImportFile row in DB has non-null file_bytes."""
    from sqlalchemy import select

    await _login_user(client, email_stub, email="bytes_user@example.com")

    with patch("app.modules.imports.router._dispatch_pdf_parse"):
        resp = await client.post(
            "/imports/pdf",
            files={"file": ("test.pdf", b"%PDF-1.4 stub content", "application/pdf")},
        )
    assert resp.status_code == 202

    # Verify file bytes stored in DB
    result = await db_session.execute(select(ImportFile).limit(1))
    file_row = result.scalar_one_or_none()
    assert file_row is not None
    assert file_row.file_bytes is not None
    assert len(file_row.file_bytes) > 0


async def test_poll_job_returns_staged_rows(client, db_session, email_stub):
    """GET /imports/jobs/{id} returns status=completed + staged_rows list."""
    user_id = await _login_user(client, email_stub, email="poll_user@example.com")

    # Manually insert a completed job + staging row
    job = ImportJob(
        id=str(uuid.uuid4()),
        tenant_id=user_id,
        file_id=str(uuid.uuid4()),
        file_type="csv",
        status="completed",
        staging_count=1,
    )
    db_session.add(job)

    staging = ImportStaging(
        id=str(uuid.uuid4()),
        job_id=job.id,
        tenant_id=user_id,
        ticker="PETR4",
        asset_class="acao",
        transaction_type="buy",
        transaction_date=date(2025, 1, 15),
        quantity=Decimal("100"),
        unit_price=Decimal("38.50"),
        total_value=Decimal("3850.00"),
        parser_source="csv",
        import_hash="a" * 64,
    )
    db_session.add(staging)
    await db_session.flush()

    resp = await client.get(f"/imports/jobs/{job.id}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "completed"
    assert len(data["staged_rows"]) == 1
    assert data["staged_rows"][0]["ticker"] == "PETR4"


async def test_confirm_writes_transactions(client, db_session, email_stub):
    """POST /imports/jobs/{id}/confirm moves staged rows to transactions table."""
    from sqlalchemy import select
    from app.modules.portfolio.models import Transaction

    user_id = await _login_user(client, email_stub, email="confirm_user@example.com")

    job = ImportJob(
        id=str(uuid.uuid4()),
        tenant_id=user_id,
        file_id=str(uuid.uuid4()),
        file_type="csv",
        status="completed",
        staging_count=1,
    )
    db_session.add(job)

    staging = ImportStaging(
        id=str(uuid.uuid4()),
        job_id=job.id,
        tenant_id=user_id,
        ticker="BBAS3",
        asset_class="acao",
        transaction_type="buy",
        transaction_date=date(2025, 1, 20),
        quantity=Decimal("50"),
        unit_price=Decimal("55.20"),
        total_value=Decimal("2760.00"),
        parser_source="csv",
        import_hash="b" * 64,
    )
    db_session.add(staging)
    await db_session.flush()

    resp = await client.post(f"/imports/jobs/{job.id}/confirm")
    assert resp.status_code == 200
    data = resp.json()
    assert data["confirmed_count"] >= 1

    result = await db_session.execute(
        select(Transaction).where(Transaction.ticker == "BBAS3")
    )
    txns = result.scalars().all()
    assert len(txns) >= 1


async def test_cancel_deletes_staging(client, db_session, email_stub):
    """POST /imports/jobs/{id}/cancel deletes ImportStaging rows for that job."""
    from sqlalchemy import select

    user_id = await _login_user(client, email_stub, email="cancel_user@example.com")

    job = ImportJob(
        id=str(uuid.uuid4()),
        tenant_id=user_id,
        file_id=str(uuid.uuid4()),
        file_type="csv",
        status="completed",
        staging_count=1,
    )
    db_session.add(job)

    staging = ImportStaging(
        id=str(uuid.uuid4()),
        job_id=job.id,
        tenant_id=user_id,
        ticker="VALE3",
        asset_class="acao",
        transaction_type="buy",
        transaction_date=date(2025, 2, 1),
        quantity=Decimal("30"),
        unit_price=Decimal("75.00"),
        total_value=Decimal("2250.00"),
        parser_source="csv",
        import_hash="c" * 64,
    )
    db_session.add(staging)
    await db_session.flush()

    resp = await client.post(f"/imports/jobs/{job.id}/cancel")
    assert resp.status_code == 200
    assert resp.json()["status"] == "cancelled"

    result = await db_session.execute(
        select(ImportStaging).where(ImportStaging.job_id == job.id)
    )
    rows = result.scalars().all()
    assert len(rows) == 0


async def test_duplicate_detection(client, db_session, email_stub):
    """Confirming same job twice skips duplicates — no 500, returns duplicate_count > 0."""
    user_id = await _login_user(client, email_stub, email="dup_user@example.com")

    hash_val = "d" * 64

    # First confirm
    job1 = ImportJob(
        id=str(uuid.uuid4()),
        tenant_id=user_id,
        file_id=str(uuid.uuid4()),
        file_type="csv",
        status="completed",
        staging_count=1,
    )
    db_session.add(job1)
    staging1 = ImportStaging(
        id=str(uuid.uuid4()),
        job_id=job1.id,
        tenant_id=user_id,
        ticker="ITUB4",
        asset_class="acao",
        transaction_type="buy",
        transaction_date=date(2025, 3, 1),
        quantity=Decimal("20"),
        unit_price=Decimal("25.00"),
        total_value=Decimal("500.00"),
        parser_source="csv",
        import_hash=hash_val,
    )
    db_session.add(staging1)
    await db_session.flush()

    resp1 = await client.post(f"/imports/jobs/{job1.id}/confirm")
    assert resp1.status_code == 200

    # Second job with same hash
    job2 = ImportJob(
        id=str(uuid.uuid4()),
        tenant_id=user_id,
        file_id=str(uuid.uuid4()),
        file_type="csv",
        status="completed",
        staging_count=1,
    )
    db_session.add(job2)
    staging2 = ImportStaging(
        id=str(uuid.uuid4()),
        job_id=job2.id,
        tenant_id=user_id,
        ticker="ITUB4",
        asset_class="acao",
        transaction_type="buy",
        transaction_date=date(2025, 3, 1),
        quantity=Decimal("20"),
        unit_price=Decimal("25.00"),
        total_value=Decimal("500.00"),
        parser_source="csv",
        import_hash=hash_val,
    )
    db_session.add(staging2)
    await db_session.flush()

    resp2 = await client.post(f"/imports/jobs/{job2.id}/confirm")
    assert resp2.status_code == 200  # no 500
    assert resp2.json()["duplicate_count"] > 0


async def test_reparse_from_stored_bytes(client, db_session, email_stub):
    """POST /imports/jobs/{id}/reparse returns new job_id without re-uploading file."""
    user_id = await _login_user(client, email_stub, email="reparse_user@example.com")

    file_row = ImportFile(
        id=str(uuid.uuid4()),
        tenant_id=user_id,
        file_type="pdf",
        original_filename="nota.pdf",
        file_bytes=b"%PDF-1.4 stub",
        file_size_bytes=13,
    )
    db_session.add(file_row)

    job = ImportJob(
        id=str(uuid.uuid4()),
        tenant_id=user_id,
        file_id=file_row.id,
        file_type="pdf",
        status="completed",
        staging_count=0,
    )
    db_session.add(job)
    await db_session.flush()

    with patch("app.modules.imports.router._dispatch_pdf_parse"):
        resp = await client.post(f"/imports/jobs/{job.id}/reparse")
    assert resp.status_code == 202
    data = resp.json()
    assert data["id"] != job.id  # new job created
    assert data["status"] == "pending"


async def test_unauthenticated_returns_401(client):
    """Unauthenticated requests to protected endpoints return 401."""
    resp = await client.post(
        "/imports/pdf",
        files={"file": ("test.pdf", b"%PDF-1.4", "application/pdf")},
    )
    assert resp.status_code == 401


async def test_csv_template_download(client):
    """GET /imports/template.csv returns CSV content without authentication."""
    resp = await client.get("/imports/template.csv")
    assert resp.status_code == 200
    assert "text/csv" in resp.headers.get("content-type", "")
    text = resp.text
    assert "ticker" in text
    assert "PETR4" in text
