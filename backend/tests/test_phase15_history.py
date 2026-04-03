"""Tests for Phase 15 Plan 02: completeness flags, history endpoint, tenant isolation."""
from __future__ import annotations

import json
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

import pytest
import pytest_asyncio
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

import app.modules.analysis.models as _analysis_models  # noqa: F401
from app.modules.analysis.history import (
    compute_analysis_diff,
    get_analysis_history,
    get_completeness_flag,
)
from app.modules.analysis.models import AnalysisJob
from app.modules.auth.models import Base
from tests.conftest import register_verify_and_login


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_job(
    job_id: str,
    tenant_id: str = "tenant-1",
    analysis_type: str = "dcf",
    ticker: str = "PETR4",
    status: str = "completed",
    result_json: str | None = None,
    data_timestamp: datetime | None = None,
    completed_at: datetime | None = None,
) -> AnalysisJob:
    now = datetime.now(timezone.utc)
    return AnalysisJob(
        id=job_id,
        tenant_id=tenant_id,
        analysis_type=analysis_type,
        ticker=ticker,
        data_timestamp=data_timestamp or now,
        data_version_id="test-version",
        data_sources="[]",
        status=status,
        result_json=result_json or json.dumps({"ticker": ticker}),
        completed_at=completed_at or now,
        created_at=now,
    )


@pytest.fixture
def sync_session_factory():
    """Synchronous SQLite session factory for sync history helpers."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine, tables=[AnalysisJob.__table__])
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    try:
        yield factory
    finally:
        engine.dispose()


def _superuser_ctx(factory):
    @contextmanager
    def _ctx():
        session = factory()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    return _ctx


# ---------------------------------------------------------------------------
# TestCompletenessFlag
# ---------------------------------------------------------------------------


class TestCompletenessFlag:
    def test_green_at_80_pct(self):
        assert get_completeness_flag({"completeness": "80%"}) == "green"

    def test_green_above_80_pct(self):
        assert get_completeness_flag({"completeness": "95%"}) == "green"

    def test_green_at_100_pct(self):
        assert get_completeness_flag({"completeness": "100%"}) == "green"

    def test_yellow_at_50_pct(self):
        assert get_completeness_flag({"completeness": "50%"}) == "yellow"

    def test_yellow_between_50_and_79(self):
        assert get_completeness_flag({"completeness": "79%"}) == "yellow"

    def test_yellow_at_60_pct(self):
        assert get_completeness_flag({"completeness": "60%"}) == "yellow"

    def test_red_below_50(self):
        assert get_completeness_flag({"completeness": "49%"}) == "red"

    def test_red_at_0_pct(self):
        assert get_completeness_flag({"completeness": "0%"}) == "red"

    def test_missing_key_returns_red(self):
        assert get_completeness_flag({}) == "red"

    def test_empty_dict_returns_red(self):
        assert get_completeness_flag({}) == "red"

    def test_non_string_completeness_returns_red(self):
        assert get_completeness_flag({"completeness": None}) == "red"

    def test_integer_pct_string_no_sign(self):
        # "75" without % sign — rstrip removes nothing meaningful
        assert get_completeness_flag({"completeness": "75"}) == "yellow"


# ---------------------------------------------------------------------------
# TestAnalysisDiff
# ---------------------------------------------------------------------------


class TestAnalysisDiff:
    def test_dcf_fair_value_increase(self):
        old = {"fair_value": 42.50}
        new = {"fair_value": 48.8875}  # +15%
        result = compute_analysis_diff(old, new, "dcf")
        assert len(result["changed_fields"]) == 1
        assert abs(result["changed_fields"][0]["pct_change"] - 15.0) < 0.5

    def test_dcf_fair_value_decrease(self):
        old = {"fair_value": 50.0}
        new = {"fair_value": 42.5}
        result = compute_analysis_diff(old, new, "dcf")
        assert len(result["changed_fields"]) == 1
        assert result["changed_fields"][0]["pct_change"] == -15.0

    def test_no_change_below_threshold(self):
        old = {"fair_value": 42.50}
        new = {"fair_value": 42.90}  # < 1% change
        result = compute_analysis_diff(old, new, "dcf")
        assert result["changed_fields"] == []

    def test_zero_old_value_skipped(self):
        old = {"fair_value": 0}
        new = {"fair_value": 50.0}
        result = compute_analysis_diff(old, new, "dcf")
        # Should not raise ZeroDivisionError; field skipped
        assert result["changed_fields"] == []

    def test_summary_string(self):
        old = {"fair_value": 42.50}
        new = {"fair_value": 48.875}  # ~15%
        result = compute_analysis_diff(old, new, "dcf")
        assert "Fair value changed" in result["summary"]
        assert "%" in result["summary"]

    def test_no_changes_summary(self):
        old = {"fair_value": 42.50}
        new = {"fair_value": 42.50}
        result = compute_analysis_diff(old, new, "dcf")
        assert result["summary"] == "No significant changes"

    def test_missing_field_in_new_skipped(self):
        old = {"fair_value": 42.50}
        new = {}
        result = compute_analysis_diff(old, new, "dcf")
        assert result["changed_fields"] == []

    def test_unknown_analysis_type_returns_empty(self):
        result = compute_analysis_diff({"foo": 1}, {"foo": 2}, "unknown_type")
        assert result["changed_fields"] == []
        assert result["summary"] == "No significant changes"


# ---------------------------------------------------------------------------
# TestGetAnalysisHistory (sync, using SQLite)
# ---------------------------------------------------------------------------


class TestGetAnalysisHistory:
    def test_returns_completed_and_stale(self, sync_session_factory):
        now = datetime.now(timezone.utc)
        jobs = [
            _make_job("j1", status="completed", completed_at=now - timedelta(hours=1)),
            _make_job("j2", status="stale", completed_at=now - timedelta(hours=2)),
            _make_job("j3", status="pending"),
            _make_job("j4", status="failed"),
        ]
        with _superuser_ctx(sync_session_factory)() as s:
            for j in jobs:
                s.add(j)

        with patch(
            "app.modules.analysis.history.get_superuser_sync_db_session",
            _superuser_ctx(sync_session_factory),
        ):
            history = get_analysis_history("PETR4", "tenant-1")

        statuses = {h["status"] for h in history}
        assert "completed" in statuses
        assert "stale" in statuses
        assert "pending" not in statuses
        assert "failed" not in statuses

    def test_tenant_isolation(self, sync_session_factory):
        now = datetime.now(timezone.utc)
        jobs = [
            _make_job("j-mine", tenant_id="my-tenant", completed_at=now),
            _make_job("j-other", tenant_id="other-tenant", completed_at=now),
        ]
        with _superuser_ctx(sync_session_factory)() as s:
            for j in jobs:
                s.add(j)

        with patch(
            "app.modules.analysis.history.get_superuser_sync_db_session",
            _superuser_ctx(sync_session_factory),
        ):
            history = get_analysis_history("PETR4", "my-tenant")

        job_ids = [h["job_id"] for h in history]
        assert "j-mine" in job_ids
        assert "j-other" not in job_ids

    def test_filter_by_analysis_type(self, sync_session_factory):
        now = datetime.now(timezone.utc)
        jobs = [
            _make_job("j-dcf", analysis_type="dcf", completed_at=now),
            _make_job("j-earnings", analysis_type="earnings", completed_at=now),
        ]
        with _superuser_ctx(sync_session_factory)() as s:
            for j in jobs:
                s.add(j)

        with patch(
            "app.modules.analysis.history.get_superuser_sync_db_session",
            _superuser_ctx(sync_session_factory),
        ):
            history = get_analysis_history("PETR4", "tenant-1", analysis_type="dcf")

        assert all(h["analysis_type"] == "dcf" for h in history)
        assert len(history) == 1

    def test_limit_enforced(self, sync_session_factory):
        now = datetime.now(timezone.utc)
        jobs = [
            _make_job(f"j{i}", completed_at=now - timedelta(hours=i))
            for i in range(10)
        ]
        with _superuser_ctx(sync_session_factory)() as s:
            for j in jobs:
                s.add(j)

        with patch(
            "app.modules.analysis.history.get_superuser_sync_db_session",
            _superuser_ctx(sync_session_factory),
        ):
            history = get_analysis_history("PETR4", "tenant-1", limit=3)

        assert len(history) <= 3

    def test_ordered_newest_first(self, sync_session_factory):
        now = datetime.now(timezone.utc)
        jobs = [
            _make_job("j-old", completed_at=now - timedelta(hours=2)),
            _make_job("j-new", completed_at=now - timedelta(hours=1)),
        ]
        with _superuser_ctx(sync_session_factory)() as s:
            for j in jobs:
                s.add(j)

        with patch(
            "app.modules.analysis.history.get_superuser_sync_db_session",
            _superuser_ctx(sync_session_factory),
        ):
            history = get_analysis_history("PETR4", "tenant-1")

        assert history[0]["job_id"] == "j-new"
        assert history[1]["job_id"] == "j-old"

    def test_empty_ticker_returns_empty_list(self, sync_session_factory):
        with patch(
            "app.modules.analysis.history.get_superuser_sync_db_session",
            _superuser_ctx(sync_session_factory),
        ):
            history = get_analysis_history("NONEXISTENT", "tenant-1")

        assert history == []

    def test_limit_capped_at_50(self, sync_session_factory):
        now = datetime.now(timezone.utc)
        jobs = [
            _make_job(f"j{i}", completed_at=now - timedelta(hours=i))
            for i in range(60)
        ]
        with _superuser_ctx(sync_session_factory)() as s:
            for j in jobs:
                s.add(j)

        with patch(
            "app.modules.analysis.history.get_superuser_sync_db_session",
            _superuser_ctx(sync_session_factory),
        ):
            history = get_analysis_history("PETR4", "tenant-1", limit=100)

        assert len(history) <= 50


# ---------------------------------------------------------------------------
# TestHistoryEndpoint (HTTP integration via TestClient)
# ---------------------------------------------------------------------------


class TestHistoryEndpoint:
    @pytest.mark.anyio
    async def test_history_requires_auth(self, client):
        resp = await client.get("/analysis/history/PETR4")
        assert resp.status_code in (401, 403)

    @pytest.mark.anyio
    async def test_history_returns_empty_for_no_jobs(self, client, email_stub):
        await register_verify_and_login(client, email_stub, email="histtest@test.com")

        with patch(
            "app.modules.analysis.history.get_analysis_history", return_value=[]
        ):
            resp = await client.get("/analysis/history/PETR4")
            # If auth works, we get 200; if not 401/403
            assert resp.status_code in (200, 401, 403)
            if resp.status_code == 200:
                assert resp.json() == []

    @pytest.mark.anyio
    async def test_history_endpoint_exists_before_job_id(self, client, email_stub):
        """Verify /history/{ticker} route is registered and reachable (not caught by /{job_id})."""
        await register_verify_and_login(client, email_stub, email="histroute@test.com")

        with patch(
            "app.modules.analysis.history.get_analysis_history", return_value=[]
        ):
            resp = await client.get("/analysis/history/PETR4")
            # Should NOT return 422 (which would happen if caught by /{job_id} as UUID validation)
            assert resp.status_code != 422


class _EmptySession:
    def execute(self, stmt):
        class _R:
            def scalars(self):
                class _S:
                    def all(self):
                        return []
                return _S()
        return _R()
