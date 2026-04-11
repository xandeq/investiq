"""Tests for Phase 15 Plan 01: cache invalidation, nightly polling, and refresh archival."""
from __future__ import annotations

import json
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

import app.modules.analysis.models as _analysis_models  # noqa: F401
from app.modules.analysis.invalidation import (
    get_last_analysis_data_timestamp,
    on_earnings_release,
)
from app.modules.analysis.models import AnalysisJob
from app.modules.analysis.tasks import (
    archive_previous_completed_jobs,
    check_earnings_releases,
)
from app.modules.auth.models import Base
from tests.conftest import register_verify_and_login


def _make_job(
    job_id: str,
    tenant_id: str = "tenant-1",
    analysis_type: str = "dcf",
    ticker: str = "PETR4",
    status: str = "completed",
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
        result_json=json.dumps({"ticker": ticker}),
        completed_at=completed_at,
        created_at=now,
    )


@pytest.fixture
def sync_session_factory():
    """Provide a synchronous SQLite session factory for Celery-side helpers."""
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


class TestOnEarningsRelease:
    def test_correct_cache_key_deleted(self, sync_session_factory):
        now = datetime.now(timezone.utc)
        filing_date = now
        old_job = _make_job(
            "job-old",
            completed_at=now - timedelta(days=2),
            data_timestamp=now - timedelta(days=3),
        )

        with sync_session_factory() as session:
            session.add(old_job)
            session.commit()

        mock_redis = MagicMock()
        with (
            patch(
                "app.modules.analysis.invalidation.get_superuser_sync_db_session",
                _superuser_ctx(sync_session_factory),
            ),
            patch(
                "app.modules.analysis.invalidation._get_sync_redis",
                return_value=mock_redis,
            ),
        ):
            count = on_earnings_release("petr4", filing_date)

        assert count == 1
        mock_redis.delete.assert_called_once_with("brapi:fundamentals:PETR4")

        with sync_session_factory() as session:
            refreshed = session.execute(
                select(AnalysisJob).where(AnalysisJob.id == "job-old")
            ).scalar_one()
            assert refreshed.status == "stale"

    def test_wrong_key_not_deleted(self, sync_session_factory):
        now = datetime.now(timezone.utc)
        with sync_session_factory() as session:
            session.add(
                _make_job(
                    "job-old",
                    completed_at=now - timedelta(days=2),
                    data_timestamp=now - timedelta(days=3),
                )
            )
            session.commit()

        mock_redis = MagicMock()
        with (
            patch(
                "app.modules.analysis.invalidation.get_superuser_sync_db_session",
                _superuser_ctx(sync_session_factory),
            ),
            patch(
                "app.modules.analysis.invalidation._get_sync_redis",
                return_value=mock_redis,
            ),
        ):
            on_earnings_release("PETR4", now)

        deleted_keys = [call.args[0] for call in mock_redis.delete.call_args_list]
        assert "analysis:cache:PETR4" not in deleted_keys

    def test_jobs_marked_stale(self, sync_session_factory):
        now = datetime.now(timezone.utc)
        with sync_session_factory() as session:
            session.add(
                _make_job(
                    "job-stale",
                    completed_at=now - timedelta(days=5),
                    data_timestamp=now - timedelta(days=6),
                )
            )
            session.commit()

        with (
            patch(
                "app.modules.analysis.invalidation.get_superuser_sync_db_session",
                _superuser_ctx(sync_session_factory),
            ),
            patch("app.modules.analysis.invalidation._get_sync_redis", return_value=MagicMock()),
        ):
            on_earnings_release("PETR4", now - timedelta(days=1))

        with sync_session_factory() as session:
            job = session.execute(
                select(AnalysisJob).where(AnalysisJob.id == "job-stale")
            ).scalar_one()
            assert job.status == "stale"
            assert "New earnings released" in (job.error_message or "")

    def test_newer_jobs_not_marked_stale(self, sync_session_factory):
        now = datetime.now(timezone.utc)
        with sync_session_factory() as session:
            session.add(
                _make_job(
                    "job-fresh",
                    completed_at=now,
                    data_timestamp=now - timedelta(hours=1),
                )
            )
            session.commit()

        with (
            patch(
                "app.modules.analysis.invalidation.get_superuser_sync_db_session",
                _superuser_ctx(sync_session_factory),
            ),
            patch("app.modules.analysis.invalidation._get_sync_redis", return_value=MagicMock()),
        ):
            count = on_earnings_release("PETR4", now - timedelta(hours=12))

        assert count == 0
        with sync_session_factory() as session:
            job = session.execute(
                select(AnalysisJob).where(AnalysisJob.id == "job-fresh")
            ).scalar_one()
            assert job.status == "completed"


class TestCompletenessHelpers:
    def test_get_last_analysis_data_timestamp_returns_max(self, sync_session_factory):
        now = datetime.now(timezone.utc)
        with sync_session_factory() as session:
            session.add_all(
                [
                    _make_job(
                        "job-1",
                        data_timestamp=now - timedelta(days=2),
                        completed_at=now - timedelta(days=2),
                    ),
                    _make_job(
                        "job-2",
                        data_timestamp=now - timedelta(hours=1),
                        completed_at=now - timedelta(hours=1),
                    ),
                    _make_job(
                        "job-3",
                        status="failed",
                        data_timestamp=now,
                    ),
                ]
            )
            session.commit()

        with patch(
            "app.modules.analysis.invalidation.get_superuser_sync_db_session",
            _superuser_ctx(sync_session_factory),
        ):
            ts = get_last_analysis_data_timestamp("PETR4")

        assert ts == now - timedelta(hours=1)

    def test_get_last_analysis_data_timestamp_no_jobs(self, sync_session_factory):
        with patch(
            "app.modules.analysis.invalidation.get_superuser_sync_db_session",
            _superuser_ctx(sync_session_factory),
        ):
            ts = get_last_analysis_data_timestamp("PETR4")

        assert ts is None


class TestEarningsPollTask:
    def test_check_earnings_releases_detects_new_filing(self):
        last_ts = datetime(2026, 4, 1, tzinfo=timezone.utc)
        filing_ts = datetime(2026, 4, 2, tzinfo=timezone.utc)

        with (
            patch(
                "app.modules.analysis.invalidation.get_analyzed_tickers_recent_7d",
                return_value=["PETR4"],
            ),
            patch(
                "app.modules.analysis.tasks._fetch_latest_quarterly_filing_date",
                return_value=filing_ts,
            ),
            patch(
                "app.modules.analysis.invalidation.get_last_analysis_data_timestamp",
                return_value=last_ts,
            ),
            patch(
                "app.modules.analysis.invalidation.on_earnings_release",
                return_value=2,
            ) as mock_invalidate,
        ):
            result = check_earnings_releases()

        mock_invalidate.assert_called_once_with("PETR4", filing_ts)
        assert result == {"tickers_checked": 1, "analyses_invalidated": 2}

    def test_check_earnings_releases_no_new_filing(self):
        last_ts = datetime(2026, 4, 2, tzinfo=timezone.utc)
        filing_ts = datetime(2026, 4, 1, tzinfo=timezone.utc)

        with (
            patch(
                "app.modules.analysis.invalidation.get_analyzed_tickers_recent_7d",
                return_value=["PETR4"],
            ),
            patch(
                "app.modules.analysis.tasks._fetch_latest_quarterly_filing_date",
                return_value=filing_ts,
            ),
            patch(
                "app.modules.analysis.invalidation.get_last_analysis_data_timestamp",
                return_value=last_ts,
            ),
            patch("app.modules.analysis.invalidation.on_earnings_release") as mock_invalidate,
        ):
            result = check_earnings_releases()

        mock_invalidate.assert_not_called()
        assert result == {"tickers_checked": 1, "analyses_invalidated": 0}

    def test_check_earnings_releases_caps_at_50_tickers(self):
        tickers = [f"TICK{i}" for i in range(100)]

        with (
            patch(
                "app.modules.analysis.invalidation.get_analyzed_tickers_recent_7d",
                return_value=tickers,
            ),
            patch(
                "app.modules.analysis.tasks._fetch_latest_quarterly_filing_date",
                return_value=None,
            ) as mock_fetch,
            patch("app.modules.analysis.invalidation.get_last_analysis_data_timestamp") as mock_last,
            patch("app.modules.analysis.invalidation.on_earnings_release") as mock_invalidate,
        ):
            result = check_earnings_releases()

        assert mock_fetch.call_count == 50
        mock_last.assert_not_called()
        mock_invalidate.assert_not_called()
        assert result == {"tickers_checked": 50, "analyses_invalidated": 0}


class TestArchiveOnRefresh:
    def test_archive_previous_completed_jobs(self, sync_session_factory):
        now = datetime.now(timezone.utc)
        with sync_session_factory() as session:
            session.add_all(
                [
                    _make_job(
                        "old-1",
                        tenant_id="tenant-a",
                        analysis_type="dcf",
                        ticker="PETR4",
                        completed_at=now - timedelta(days=2),
                    ),
                    _make_job(
                        "old-2",
                        tenant_id="tenant-a",
                        analysis_type="dcf",
                        ticker="PETR4",
                        completed_at=now - timedelta(days=1),
                    ),
                    _make_job(
                        "other-type",
                        tenant_id="tenant-a",
                        analysis_type="earnings",
                        ticker="PETR4",
                        completed_at=now - timedelta(days=1),
                    ),
                    _make_job(
                        "other-tenant",
                        tenant_id="tenant-b",
                        analysis_type="dcf",
                        ticker="PETR4",
                        completed_at=now - timedelta(days=1),
                    ),
                ]
            )
            session.commit()

        with patch(
            "app.modules.analysis.tasks.get_superuser_sync_db_session",
            _superuser_ctx(sync_session_factory),
        ):
            count = archive_previous_completed_jobs(
                ticker="PETR4",
                tenant_id="tenant-a",
                analysis_type="dcf",
                exclude_job_id="new-job",
            )

        assert count == 2
        with sync_session_factory() as session:
            jobs = {
                job.id: job
                for job in session.execute(select(AnalysisJob)).scalars().all()
            }
            assert jobs["old-1"].status == "stale"
            assert jobs["old-2"].status == "stale"
            assert jobs["other-type"].status == "completed"
            assert jobs["other-tenant"].status == "completed"


class TestRefreshQuota:
    @pytest.mark.asyncio
    async def test_refresh_deducts_quota(self, client, db_session, email_stub):
        await register_verify_and_login(
            client,
            email_stub,
            email="phase15-refresh@test.com",
            password="SecurePass123!",
        )

        me_resp = await client.get("/me")
        assert me_resp.status_code == 200
        tenant_id = me_resp.json()["tenant_id"]

        existing = AnalysisJob(
            tenant_id=tenant_id,
            analysis_type="dcf",
            ticker="PETR4",
            data_timestamp=datetime.now(timezone.utc) - timedelta(days=1),
            data_version_id="old-version",
            data_sources="[]",
            status="completed",
            result_json=json.dumps({"ticker": "PETR4", "fair_value": 42}),
            completed_at=datetime.now(timezone.utc) - timedelta(days=1),
        )
        db_session.add(existing)
        await db_session.commit()

        with (
            patch(
                "app.modules.analysis.router.check_analysis_rate_limit",
                new=AsyncMock(return_value=(True, 0)),
            ),
            patch(
                "app.modules.analysis.router.check_analysis_quota",
                return_value=(True, 1, 50),
            ),
            patch("app.modules.analysis.router.increment_quota_used") as mock_increment,
            patch("app.celery_app.celery_app.send_task"),
            patch("app.celery_app.celery_app.connection_for_write") as mock_conn,
        ):
            mock_conn.return_value.__enter__ = MagicMock(return_value=MagicMock())
            mock_conn.return_value.__exit__ = MagicMock(return_value=False)

            resp = await client.post("/analysis/dcf", json={"ticker": "PETR4"})

        assert resp.status_code == 202, resp.text
        mock_increment.assert_called_once_with(tenant_id)
