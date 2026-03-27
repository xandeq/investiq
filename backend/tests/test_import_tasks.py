"""Unit tests for Celery import tasks."""
from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


FIXTURES_DIR = Path(__file__).parent / "fixtures"


def test_parse_pdf_writes_staging():
    """parse_pdf_import task (called directly) calls _write_staging_rows."""
    import uuid
    from app.modules.imports.tasks import parse_pdf_import

    tenant_id = str(uuid.uuid4())
    file_id = str(uuid.uuid4())
    job_id = str(uuid.uuid4())

    pdf_bytes = (FIXTURES_DIR / "sample_nota_corretagem.pdf").read_bytes()

    # Mock sync DB session to return file bytes
    mock_file = MagicMock()
    mock_file.file_bytes = pdf_bytes

    mock_session = MagicMock()
    mock_session.get.return_value = mock_file
    mock_session.__enter__ = MagicMock(return_value=mock_session)
    mock_session.__exit__ = MagicMock(return_value=False)

    with patch("app.modules.imports.tasks.get_sync_db_session", return_value=mock_session):
        with patch("app.modules.imports.tasks._write_staging_rows") as mock_write:
            with patch("app.modules.imports.tasks._update_import_job_status"):
                # Call task function directly (not .delay() — no Celery worker needed)
                parse_pdf_import(job_id, file_id, tenant_id)
                assert mock_write.called
                # Verify called with correct job_id and tenant_id
                call_args = mock_write.call_args
                assert call_args[0][0] == job_id
                assert call_args[0][1] == tenant_id


def test_parse_csv_writes_staging():
    """parse_csv_import task (called directly) calls _write_staging_rows."""
    import uuid
    from app.modules.imports.tasks import parse_csv_import

    tenant_id = str(uuid.uuid4())
    file_id = str(uuid.uuid4())
    job_id = str(uuid.uuid4())

    csv_bytes = (FIXTURES_DIR / "sample_import.csv").read_bytes()

    mock_file = MagicMock()
    mock_file.file_bytes = csv_bytes

    mock_session = MagicMock()
    mock_session.get.return_value = mock_file
    mock_session.__enter__ = MagicMock(return_value=mock_session)
    mock_session.__exit__ = MagicMock(return_value=False)

    with patch("app.modules.imports.tasks.get_sync_db_session", return_value=mock_session):
        with patch("app.modules.imports.tasks._write_staging_rows") as mock_write:
            with patch("app.modules.imports.tasks._update_import_job_status"):
                parse_csv_import(job_id, file_id, tenant_id)
                assert mock_write.called
                call_args = mock_write.call_args
                assert call_args[0][0] == job_id
                assert call_args[0][1] == tenant_id
