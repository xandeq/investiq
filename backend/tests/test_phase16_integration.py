"""Phase 16 Plan 02 — Integration tests for the analysis API.

Covers:
1. Starting all 4 analysis job types (DCF, earnings, dividend, sector) returns distinct
   job_ids and 202 status.
2. Polling GET /analysis/{job_id} for a pending job returns correct fields.
3. Polling with a completed job (DB directly updated) returns result payload.
4. Tenant isolation: user B gets 404 for user A's job.
5. Quota exceeded returns 403 with QUOTA_EXCEEDED code.
6. Response shape validation: disclaimer contains "CVM", analysis_id is UUID.
"""
from __future__ import annotations

import asyncio
import json
import uuid
from contextlib import contextmanager
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy import select

from app.modules.analysis.models import AnalysisJob


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_celery_mock() -> MagicMock:
    """Return a MagicMock celery_app whose connection_for_write() is a context manager."""
    mock_celery = MagicMock()
    mock_conn = MagicMock()
    mock_celery.connection_for_write.return_value.__enter__ = MagicMock(return_value=mock_conn)
    mock_celery.connection_for_write.return_value.__exit__ = MagicMock(return_value=False)
    return mock_celery


def _quota_allowed() -> tuple:
    """Return quota tuple for an allowed request (pro tier, 0 used of 50)."""
    return (True, 0, 50)


def _quota_exhausted() -> tuple:
    """Return quota tuple for an exhausted quota (50 of 50 used)."""
    return (False, 50, 50)


# ---------------------------------------------------------------------------
# Test class: all 4 analysis types via POST
# ---------------------------------------------------------------------------


class TestStartAllAnalysisTypes:
    """POST to each of the 4 analysis endpoints returns 202 and distinct job_ids."""

    def test_all_four_types_return_distinct_job_ids(self, client, email_stub):
        async def _run():
            from tests.conftest import register_verify_and_login

            await register_verify_and_login(
                client,
                email_stub,
                email="phase16_all_types@test.com",
                password="SecurePass123!",
            )

            mock_celery = _make_celery_mock()

            with (
                patch(
                    "app.modules.analysis.router.check_analysis_rate_limit",
                    new=AsyncMock(return_value=(True, 0)),
                ),
                patch(
                    "app.modules.analysis.router.check_analysis_quota",
                    return_value=_quota_allowed(),
                ),
                patch(
                    "app.modules.analysis.router.increment_quota_used",
                ),
                patch(
                    "app.celery_app.celery_app",
                    mock_celery,
                ),
            ):
                resp_dcf = await client.post(
                    "/analysis/dcf", json={"ticker": "PETR4"}
                )
                resp_earnings = await client.post(
                    "/analysis/earnings", json={"ticker": "PETR4"}
                )
                resp_dividend = await client.post(
                    "/analysis/dividend", json={"ticker": "VALE3"}
                )
                resp_sector = await client.post(
                    "/analysis/sector", json={"ticker": "ITUB4", "max_peers": 5}
                )

            assert resp_dcf.status_code == 202, resp_dcf.text
            assert resp_earnings.status_code == 202, resp_earnings.text
            assert resp_dividend.status_code == 202, resp_dividend.text
            assert resp_sector.status_code == 202, resp_sector.text

            ids = [
                resp_dcf.json()["job_id"],
                resp_earnings.json()["job_id"],
                resp_dividend.json()["job_id"],
                resp_sector.json()["job_id"],
            ]
            # All four must be unique
            assert len(set(ids)) == 4, f"Expected 4 distinct job_ids, got: {ids}"

            # All responses must carry status == "pending"
            for resp in [resp_dcf, resp_earnings, resp_dividend, resp_sector]:
                assert resp.json()["status"] == "pending"

        asyncio.get_event_loop().run_until_complete(_run())


# ---------------------------------------------------------------------------
# Test class: GET /analysis/{job_id} for pending job
# ---------------------------------------------------------------------------


class TestGetPendingJob:
    """Polling a newly created (pending) job returns correct shape and status."""

    def test_pending_job_get_returns_correct_fields(self, client, email_stub):
        async def _run():
            from tests.conftest import register_verify_and_login

            await register_verify_and_login(
                client,
                email_stub,
                email="phase16_pending_poll@test.com",
                password="SecurePass123!",
            )

            mock_celery = _make_celery_mock()

            with (
                patch(
                    "app.modules.analysis.router.check_analysis_rate_limit",
                    new=AsyncMock(return_value=(True, 0)),
                ),
                patch(
                    "app.modules.analysis.router.check_analysis_quota",
                    return_value=_quota_allowed(),
                ),
                patch("app.modules.analysis.router.increment_quota_used"),
                patch("app.celery_app.celery_app", mock_celery),
            ):
                create_resp = await client.post(
                    "/analysis/dcf", json={"ticker": "BBDC4"}
                )

            assert create_resp.status_code == 202, create_resp.text
            job_id = create_resp.json()["job_id"]

            # Now poll the job — no mocks needed for GET
            get_resp = await client.get(f"/analysis/{job_id}")
            assert get_resp.status_code == 200, get_resp.text

            data = get_resp.json()
            # Required fields must be present
            assert "analysis_id" in data
            assert "analysis_type" in data
            assert "ticker" in data
            assert "status" in data
            assert "disclaimer" in data

            assert data["analysis_id"] == job_id
            assert data["ticker"] == "BBDC4"
            assert data["status"] == "pending"
            assert data["result"] is None  # no result yet

        asyncio.get_event_loop().run_until_complete(_run())


# ---------------------------------------------------------------------------
# Test class: GET /analysis/{job_id} for completed job
# ---------------------------------------------------------------------------


class TestGetCompletedJob:
    """Directly updating DB to completed status makes GET return result payload."""

    def test_completed_job_get_returns_result(self, client, email_stub, db_session):
        async def _run():
            from tests.conftest import register_verify_and_login

            await register_verify_and_login(
                client,
                email_stub,
                email="phase16_completed_poll@test.com",
                password="SecurePass123!",
            )

            mock_celery = _make_celery_mock()

            with (
                patch(
                    "app.modules.analysis.router.check_analysis_rate_limit",
                    new=AsyncMock(return_value=(True, 0)),
                ),
                patch(
                    "app.modules.analysis.router.check_analysis_quota",
                    return_value=_quota_allowed(),
                ),
                patch("app.modules.analysis.router.increment_quota_used"),
                patch("app.celery_app.celery_app", mock_celery),
            ):
                create_resp = await client.post(
                    "/analysis/earnings", json={"ticker": "VALE3"}
                )

            assert create_resp.status_code == 202, create_resp.text
            job_id = create_resp.json()["job_id"]

            # Directly update the DB record to simulate task completion
            result = await db_session.execute(
                select(AnalysisJob).where(AnalysisJob.id == job_id)
            )
            job = result.scalar_one_or_none()
            assert job is not None, "Job should exist in DB"

            fake_result = {
                "ticker": "VALE3",
                "narrative": "Lucros consistentes e crescentes.",
                "earnings_quality_score": 8.5,
                "data_version_id": "brapi_eod_20260403_v1.2",
                "data_timestamp": "2026-04-03T10:00:00+00:00",
            }
            job.status = "completed"
            job.result_json = json.dumps(fake_result)
            await db_session.commit()

            # Now GET should return the completed result
            get_resp = await client.get(f"/analysis/{job_id}")
            assert get_resp.status_code == 200, get_resp.text

            data = get_resp.json()
            assert data["status"] == "completed"
            assert data["result"] is not None
            assert data["result"]["ticker"] == "VALE3"
            assert "narrative" in data["result"]

        asyncio.get_event_loop().run_until_complete(_run())


# ---------------------------------------------------------------------------
# Test class: tenant isolation
# ---------------------------------------------------------------------------


class TestTenantIsolation:
    """User B cannot access User A's analysis jobs."""

    def test_user_b_gets_404_for_user_a_job(self, client, email_stub):
        async def _run():
            from tests.conftest import register_verify_and_login

            # Register and login User A
            await register_verify_and_login(
                client,
                email_stub,
                email="phase16_tenant_a@test.com",
                password="SecurePass123!",
            )

            mock_celery = _make_celery_mock()

            with (
                patch(
                    "app.modules.analysis.router.check_analysis_rate_limit",
                    new=AsyncMock(return_value=(True, 0)),
                ),
                patch(
                    "app.modules.analysis.router.check_analysis_quota",
                    return_value=_quota_allowed(),
                ),
                patch("app.modules.analysis.router.increment_quota_used"),
                patch("app.celery_app.celery_app", mock_celery),
            ):
                create_resp = await client.post(
                    "/analysis/dcf", json={"ticker": "PETR4"}
                )

            assert create_resp.status_code == 202, create_resp.text
            job_id_a = create_resp.json()["job_id"]

            # Register and login User B (overwrites session cookie)
            await register_verify_and_login(
                client,
                email_stub,
                email="phase16_tenant_b@test.com",
                password="SecurePass123!",
            )

            # User B tries to access User A's job
            get_resp = await client.get(f"/analysis/{job_id_a}")
            assert get_resp.status_code == 404, (
                f"Expected 404 for tenant isolation, got {get_resp.status_code}: {get_resp.text}"
            )

        asyncio.get_event_loop().run_until_complete(_run())


# ---------------------------------------------------------------------------
# Test class: quota exceeded
# ---------------------------------------------------------------------------


class TestQuotaExceeded:
    """POST /analysis/dcf with exhausted quota returns 403 QUOTA_EXCEEDED."""

    def test_quota_exceeded_returns_403_with_code(self, client, email_stub):
        async def _run():
            from tests.conftest import register_verify_and_login

            await register_verify_and_login(
                client,
                email_stub,
                email="phase16_quota_exceeded@test.com",
                password="SecurePass123!",
            )

            with (
                patch(
                    "app.modules.analysis.router.check_analysis_rate_limit",
                    new=AsyncMock(return_value=(True, 0)),
                ),
                patch(
                    "app.modules.analysis.router.check_analysis_quota",
                    return_value=_quota_exhausted(),
                ),
            ):
                resp = await client.post(
                    "/analysis/dcf", json={"ticker": "PETR4"}
                )

            assert resp.status_code == 403, resp.text
            data = resp.json()
            assert data["detail"]["code"] == "QUOTA_EXCEEDED"
            assert data["detail"]["quota_used"] == 50
            assert data["detail"]["quota_limit"] == 50

        asyncio.get_event_loop().run_until_complete(_run())

    def test_quota_exceeded_for_all_endpoints(self, client, email_stub):
        """All 4 endpoints enforce quota and return 403 with QUOTA_EXCEEDED code."""

        async def _run():
            from tests.conftest import register_verify_and_login

            await register_verify_and_login(
                client,
                email_stub,
                email="phase16_quota_all_eps@test.com",
                password="SecurePass123!",
            )

            endpoints_payloads = [
                ("/analysis/dcf", {"ticker": "PETR4"}),
                ("/analysis/earnings", {"ticker": "PETR4"}),
                ("/analysis/dividend", {"ticker": "VALE3"}),
                ("/analysis/sector", {"ticker": "ITUB4", "max_peers": 5}),
            ]

            with (
                patch(
                    "app.modules.analysis.router.check_analysis_rate_limit",
                    new=AsyncMock(return_value=(True, 0)),
                ),
                patch(
                    "app.modules.analysis.router.check_analysis_quota",
                    return_value=_quota_exhausted(),
                ),
            ):
                for endpoint, payload in endpoints_payloads:
                    resp = await client.post(endpoint, json=payload)
                    assert resp.status_code == 403, (
                        f"{endpoint} should return 403, got {resp.status_code}: {resp.text}"
                    )
                    assert resp.json()["detail"]["code"] == "QUOTA_EXCEEDED"

        asyncio.get_event_loop().run_until_complete(_run())


# ---------------------------------------------------------------------------
# Test class: response shape validation
# ---------------------------------------------------------------------------


class TestResponseShape:
    """Validate that GET /analysis/{job_id} returns correct field types and values."""

    def test_disclaimer_contains_cvm(self, client, email_stub):
        """GET /analysis/{job_id} response.disclaimer must contain 'CVM'."""

        async def _run():
            from tests.conftest import register_verify_and_login

            await register_verify_and_login(
                client,
                email_stub,
                email="phase16_shape_disclaimer@test.com",
                password="SecurePass123!",
            )

            mock_celery = _make_celery_mock()

            with (
                patch(
                    "app.modules.analysis.router.check_analysis_rate_limit",
                    new=AsyncMock(return_value=(True, 0)),
                ),
                patch(
                    "app.modules.analysis.router.check_analysis_quota",
                    return_value=_quota_allowed(),
                ),
                patch("app.modules.analysis.router.increment_quota_used"),
                patch("app.celery_app.celery_app", mock_celery),
            ):
                create_resp = await client.post(
                    "/analysis/dcf", json={"ticker": "PETR4"}
                )

            assert create_resp.status_code == 202, create_resp.text
            job_id = create_resp.json()["job_id"]

            get_resp = await client.get(f"/analysis/{job_id}")
            assert get_resp.status_code == 200, get_resp.text

            data = get_resp.json()
            assert "CVM" in data["disclaimer"], (
                f"Disclaimer should contain 'CVM', got: {data['disclaimer']}"
            )

        asyncio.get_event_loop().run_until_complete(_run())

    def test_analysis_id_is_uuid(self, client, email_stub):
        """GET /analysis/{job_id} response.analysis_id must be a valid UUID."""

        async def _run():
            from tests.conftest import register_verify_and_login

            await register_verify_and_login(
                client,
                email_stub,
                email="phase16_shape_uuid@test.com",
                password="SecurePass123!",
            )

            mock_celery = _make_celery_mock()

            with (
                patch(
                    "app.modules.analysis.router.check_analysis_rate_limit",
                    new=AsyncMock(return_value=(True, 0)),
                ),
                patch(
                    "app.modules.analysis.router.check_analysis_quota",
                    return_value=_quota_allowed(),
                ),
                patch("app.modules.analysis.router.increment_quota_used"),
                patch("app.celery_app.celery_app", mock_celery),
            ):
                create_resp = await client.post(
                    "/analysis/sector", json={"ticker": "BBAS3", "max_peers": 5}
                )

            assert create_resp.status_code == 202, create_resp.text
            job_id = create_resp.json()["job_id"]

            get_resp = await client.get(f"/analysis/{job_id}")
            assert get_resp.status_code == 200, get_resp.text

            data = get_resp.json()
            # analysis_id must be a valid UUID
            try:
                parsed = uuid.UUID(data["analysis_id"])
                assert str(parsed) == data["analysis_id"].lower()
            except (ValueError, AttributeError) as exc:
                pytest.fail(f"analysis_id is not a valid UUID: {data['analysis_id']} — {exc}")

        asyncio.get_event_loop().run_until_complete(_run())

    def test_get_nonexistent_job_returns_404(self, client, email_stub):
        """GET /analysis/{random_uuid} returns 404 when job does not exist."""

        async def _run():
            from tests.conftest import register_verify_and_login

            await register_verify_and_login(
                client,
                email_stub,
                email="phase16_shape_404@test.com",
                password="SecurePass123!",
            )

            fake_id = str(uuid.uuid4())
            get_resp = await client.get(f"/analysis/{fake_id}")
            assert get_resp.status_code == 404, (
                f"Expected 404 for unknown job_id, got {get_resp.status_code}"
            )

        asyncio.get_event_loop().run_until_complete(_run())
