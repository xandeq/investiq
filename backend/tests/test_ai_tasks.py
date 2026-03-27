from __future__ import annotations

from contextlib import contextmanager
from types import SimpleNamespace
from unittest.mock import MagicMock

from app.modules.ai import tasks


def test_update_job_status_falls_back_to_tenant_session_when_superuser_env_missing(monkeypatch):
    """Regression: worker must still update job state without AUTH_DATABASE_URL."""
    tenant_session = MagicMock()
    tenant_session.execute.return_value = SimpleNamespace(rowcount=1)

    @contextmanager
    def fake_tenant_session(_tenant_id: str):
        yield tenant_session

    fake_superuser = MagicMock()

    monkeypatch.delenv("AUTH_DATABASE_URL", raising=False)
    monkeypatch.setattr("app.core.db_sync.get_sync_db_session", fake_tenant_session)
    monkeypatch.setattr("app.core.db_sync.get_superuser_sync_db_session", fake_superuser)

    tasks._update_job_status("job-1", "failed", tenant_id="8f164479-0d8f-422a-a6f4-a9c7c9add4b0", error_message="boom")

    tenant_session.execute.assert_called_once()
    fake_superuser.assert_not_called()


def test_update_job_status_retries_with_tenant_session_when_superuser_updates_zero_rows(monkeypatch):
    """Regression: zero-row superuser updates must not leave the job stuck in pending."""
    superuser_session = MagicMock()
    superuser_session.execute.return_value = SimpleNamespace(rowcount=0)
    tenant_session = MagicMock()
    tenant_session.execute.return_value = SimpleNamespace(rowcount=1)

    @contextmanager
    def fake_superuser_session():
        yield superuser_session

    @contextmanager
    def fake_tenant_session(_tenant_id: str):
        yield tenant_session

    monkeypatch.setenv("AUTH_DATABASE_URL", "postgresql+asyncpg://postgres:postgres@postgres:5432/investiq")
    monkeypatch.setattr("app.core.db_sync.get_superuser_sync_db_session", fake_superuser_session)
    monkeypatch.setattr("app.core.db_sync.get_sync_db_session", fake_tenant_session)

    tasks._update_job_status("job-2", "completed", tenant_id="8f164479-0d8f-422a-a6f4-a9c7c9add4b0", result_json='{"ok":true}')

    assert superuser_session.execute.call_count == 1
    assert tenant_session.execute.call_count == 1
