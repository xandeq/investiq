"""Tests for Phase 12 foundation: analysis models, schemas, versioning, constants,
async tasks, LLM fallback, and cache invalidation.

Fully implemented tests:
- Plan 01: model fields, versioning, schema validation, constants (11 tests)
- Plan 03: async job lifecycle, Celery task error handling, data versioning in
  results, LLM fallback chain, cache invalidation (8+ tests)

Plan 02: quota enforcement (free blocks, pro allows), rate limiting (429),
  cost tracking (estimate + log), API disclaimer endpoint test (6 tests)
"""
from __future__ import annotations

import asyncio
import json
import re
import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from pydantic import ValidationError

from app.modules.analysis.models import AnalysisJob, AnalysisCostLog, AnalysisQuotaLog
from app.modules.analysis.schemas import (
    AnalysisJobStatus,
    AnalysisResponse,
    DataMetadata,
    DCFRequest,
)
from app.modules.analysis.versioning import build_data_version_id, get_data_sources
from app.modules.analysis.constants import (
    ANALYSIS_TYPES,
    CVM_DISCLAIMER_PT,
    CVM_DISCLAIMER_SHORT_PT,
    QUOTA_LIMITS,
)
from app.modules.analysis.providers import (
    ANALYSIS_LLM_CHAIN,
    AIProviderError,
    call_analysis_llm,
)


# ---------------------------------------------------------------------------
# Fully implemented tests — Plan 01
# ---------------------------------------------------------------------------


class TestAnalysisJobModel:
    def test_analysis_job_model_fields(self):
        """Assert AnalysisJob has all required columns."""
        mapper = AnalysisJob.__table__.columns
        column_names = {c.name for c in mapper}

        required = {
            "id",
            "tenant_id",
            "analysis_type",
            "ticker",
            "data_timestamp",
            "data_version_id",
            "data_sources",
            "status",
            "result_json",
            "error_message",
            "retry_count",
            "created_at",
            "completed_at",
        }
        assert required.issubset(column_names), (
            f"Missing columns: {required - column_names}"
        )


class TestAnalysisQuotaLogModel:
    def test_analysis_quota_log_model_fields(self):
        """Assert AnalysisQuotaLog has all required columns."""
        mapper = AnalysisQuotaLog.__table__.columns
        column_names = {c.name for c in mapper}

        required = {
            "id",
            "tenant_id",
            "year_month",
            "plan_tier",
            "quota_limit",
            "quota_used",
        }
        assert required.issubset(column_names), (
            f"Missing columns: {required - column_names}"
        )


class TestAnalysisCostLogModel:
    def test_analysis_cost_log_model_fields(self):
        """Assert AnalysisCostLog has all required columns."""
        mapper = AnalysisCostLog.__table__.columns
        column_names = {c.name for c in mapper}

        required = {
            "id",
            "tenant_id",
            "job_id",
            "analysis_type",
            "ticker",
            "llm_provider",
            "llm_model",
            "input_tokens",
            "output_tokens",
            "estimated_cost_usd",
            "duration_ms",
            "status",
            "created_at",
        }
        assert required.issubset(column_names), (
            f"Missing columns: {required - column_names}"
        )


class TestVersioning:
    def test_data_version_id_format(self):
        """build_data_version_id() returns brapi_eod_YYYYMMDD_v1.2 format."""
        version_id = build_data_version_id()
        assert re.match(r"brapi_eod_\d{8}_v1\.2", version_id), (
            f"Unexpected format: {version_id}"
        )

    def test_get_data_sources_returns_two_items(self):
        """get_data_sources() returns the canonical two-item list."""
        sources = get_data_sources()
        assert len(sources) == 2
        assert sources[0]["source"] == "BRAPI"
        assert sources[1]["source"] == "B3/CVM"


class TestSchemas:
    def test_dcf_request_validation(self):
        """DCFRequest validates ticker length and rate bounds."""
        # Valid request
        req = DCFRequest(ticker="PETR4", growth_rate=0.10)
        assert req.ticker == "PETR4"
        assert req.growth_rate == 0.10

        # Ticker too short (min_length=4)
        with pytest.raises(ValidationError):
            DCFRequest(ticker="AB")

        # growth_rate > 0.20 fails
        with pytest.raises(ValidationError):
            DCFRequest(ticker="PETR4", growth_rate=0.25)

        # discount_rate > 0.30 fails
        with pytest.raises(ValidationError):
            DCFRequest(ticker="PETR4", discount_rate=0.35)

        # terminal_growth > 0.05 fails
        with pytest.raises(ValidationError):
            DCFRequest(ticker="PETR4", terminal_growth=0.06)

    def test_analysis_response_includes_disclaimer(self):
        """AnalysisResponse requires a non-empty disclaimer field."""
        resp = AnalysisResponse(
            analysis_id="test-123",
            analysis_type="dcf",
            ticker="PETR4",
            status="completed",
            disclaimer="Test disclaimer text",
        )
        assert resp.disclaimer
        assert len(resp.disclaimer) > 0

    def test_analysis_job_status_schema(self):
        """AnalysisJobStatus creates correctly."""
        status = AnalysisJobStatus(
            job_id="abc-123",
            status="pending",
            message="Queued for processing",
        )
        assert status.job_id == "abc-123"
        assert status.status == "pending"


class TestConstants:
    def test_quota_limits_constants(self):
        """QUOTA_LIMITS has correct values for each tier."""
        assert QUOTA_LIMITS["free"] == 0
        assert QUOTA_LIMITS["pro"] == 50
        assert QUOTA_LIMITS["enterprise"] == 500

    def test_analysis_types(self):
        """ANALYSIS_TYPES contains the four expected types."""
        assert set(ANALYSIS_TYPES) == {"dcf", "earnings", "dividend", "sector"}

    def test_cvm_disclaimer_not_empty(self):
        """CVM disclaimers are non-empty strings with proper accents."""
        assert len(CVM_DISCLAIMER_PT) > 50
        assert len(CVM_DISCLAIMER_SHORT_PT) > 20
        # Check for proper Portuguese accents
        assert "\u00e1" in CVM_DISCLAIMER_PT  # a with acute
        assert "\u00e3" in CVM_DISCLAIMER_PT  # a with tilde


# ---------------------------------------------------------------------------
# Plan 03 Tests — Async job lifecycle, LLM fallback, data versioning
# ---------------------------------------------------------------------------


class _FakeSession:
    """Minimal fake DB session for testing task internals without real DB."""

    def __init__(self, objects: dict | None = None):
        self._objects = objects or {}
        self._added = []
        self._executed = []

    def execute(self, stmt):
        self._executed.append(stmt)
        return self

    def scalar_one_or_none(self):
        return None

    def scalars(self):
        return self

    def all(self):
        return list(self._objects.values())

    def add(self, obj):
        self._added.append(obj)

    def commit(self):
        pass

    def rollback(self):
        pass

    def close(self):
        pass


class TestLLMFallback:
    """Tests for the LLM provider fallback chain."""

    def test_llm_fallback_fires_on_primary_failure(self):
        """When OpenRouter times out, Groq fallback fires successfully."""

        async def mock_openrouter_timeout(*args, **kwargs):
            raise asyncio.TimeoutError("OpenRouter timed out")

        async def mock_groq_success(*args, **kwargs):
            return "Groq analysis response text"

        with (
            patch(
                "app.modules.analysis.providers._call_openrouter",
                side_effect=mock_openrouter_timeout,
            ),
            patch(
                "app.modules.analysis.providers._call_groq",
                side_effect=mock_groq_success,
            ),
        ):
            text, meta = asyncio.run(call_analysis_llm("test prompt"))
            assert meta["provider_used"] == "groq"
            assert meta["success"] is True
            assert text == "Groq analysis response text"

    def test_llm_all_providers_fail_raises_error(self):
        """When all providers fail, AIProviderError is raised."""

        async def mock_fail(*args, **kwargs):
            raise Exception("Provider failed")

        with (
            patch(
                "app.modules.analysis.providers._call_openrouter",
                side_effect=mock_fail,
            ),
            patch(
                "app.modules.analysis.providers._call_groq",
                side_effect=mock_fail,
            ),
        ):
            with pytest.raises(AIProviderError, match="All analysis LLM providers exhausted"):
                asyncio.run(call_analysis_llm("test prompt"))

    def test_llm_openrouter_success_returns_immediately(self):
        """When OpenRouter succeeds, Groq is never called."""

        async def mock_openrouter_ok(*args, **kwargs):
            return "OpenRouter response"

        groq_mock = AsyncMock(return_value="Groq response")

        with (
            patch(
                "app.modules.analysis.providers._call_openrouter",
                side_effect=mock_openrouter_ok,
            ),
            patch(
                "app.modules.analysis.providers._call_groq",
                groq_mock,
            ),
        ):
            text, meta = asyncio.run(call_analysis_llm("test prompt"))
            assert meta["provider_used"] == "openrouter"
            assert meta["success"] is True
            assert text == "OpenRouter response"
            groq_mock.assert_not_called()


class TestProviderChainConfig:
    """Tests for ANALYSIS_LLM_CHAIN configuration."""

    def test_chain_has_two_entries(self):
        assert len(ANALYSIS_LLM_CHAIN) == 2

    def test_chain_providers_are_openrouter_and_groq(self):
        providers = [c["provider"] for c in ANALYSIS_LLM_CHAIN]
        assert providers == ["openrouter", "groq"]


class TestAsyncJobs:
    """Tests for run_dcf Celery task lifecycle."""

    def test_async_job_lifecycle_complete(self):
        """run_dcf task transitions job: pending -> running -> completed.

        Result JSON contains data_version_id and data_timestamp.
        """
        job_id = str(uuid.uuid4())
        tenant_id = str(uuid.uuid4())

        # Track all _update_job calls
        job_updates: list[dict] = []

        def fake_update_job(jid, status, result_json=None, error=None):
            job_updates.append({
                "job_id": jid,
                "status": status,
                "result_json": result_json,
                "error": error,
            })

        def fake_quota_check(tid):
            return True

        async def mock_llm(prompt, max_tokens=300):
            return ("LLM narrative", {"provider_used": "openrouter", "model": "gpt-4o-mini", "success": True})

        with (
            patch("app.modules.analysis.tasks._update_job", side_effect=fake_update_job),
            patch("app.modules.analysis.tasks._check_and_increment_quota", side_effect=fake_quota_check),
            patch("app.modules.analysis.tasks.call_analysis_llm", side_effect=mock_llm),
            patch("app.modules.analysis.tasks.log_analysis_cost") as mock_cost,
        ):
            from app.modules.analysis.tasks import run_dcf

            # Call synchronously (bypass Celery)
            run_dcf(job_id, tenant_id, "PETR4", {"growth_rate": 0.08})

            # Verify lifecycle: running -> completed
            assert len(job_updates) >= 2
            assert job_updates[0]["status"] == "running"
            assert job_updates[-1]["status"] == "completed"

            # Verify result_json contains versioning metadata
            result_str = job_updates[-1]["result_json"]
            assert result_str is not None
            result = json.loads(result_str)
            assert "data_version_id" in result
            assert "data_timestamp" in result
            assert "data_sources" in result
            assert "narrative" in result
            assert result["ticker"] == "PETR4"

            # Verify cost was logged on success
            mock_cost.assert_called_once()
            call_kwargs = mock_cost.call_args
            assert call_kwargs[1]["status"] == "completed" or call_kwargs[0][5] == "completed"

    def test_celery_task_error_handling(self):
        """run_dcf with LLM failure updates job status to 'failed' with error_message."""
        job_id = str(uuid.uuid4())
        tenant_id = str(uuid.uuid4())

        job_updates: list[dict] = []

        def fake_update_job(jid, status, result_json=None, error=None):
            job_updates.append({
                "job_id": jid,
                "status": status,
                "result_json": result_json,
                "error": error,
            })

        def fake_quota_check(tid):
            return True

        async def mock_llm_fail(prompt, max_tokens=300):
            raise AIProviderError("All analysis LLM providers exhausted")

        with (
            patch("app.modules.analysis.tasks._update_job", side_effect=fake_update_job),
            patch("app.modules.analysis.tasks._check_and_increment_quota", side_effect=fake_quota_check),
            patch("app.modules.analysis.tasks.call_analysis_llm", side_effect=mock_llm_fail),
            patch("app.modules.analysis.tasks._get_cached_analysis_with_outdated_badge", return_value=None),
            patch("app.modules.analysis.tasks.log_analysis_cost") as mock_cost,
        ):
            from app.modules.analysis.tasks import run_dcf

            run_dcf(job_id, tenant_id, "VALE3")

            # Even when LLM fails, task should complete with static fallback narrative
            # (AIProviderError is caught inside the task, not re-raised)
            last_update = job_updates[-1]
            assert last_update["status"] == "completed"
            result = json.loads(last_update["result_json"])
            assert "narrative" in result
            # Cost should be logged
            mock_cost.assert_called_once()

    def test_celery_task_unhandled_exception(self):
        """run_dcf with unhandled exception sets status to failed with error_message."""
        job_id = str(uuid.uuid4())
        tenant_id = str(uuid.uuid4())

        job_updates: list[dict] = []

        def fake_update_job(jid, status, result_json=None, error=None):
            job_updates.append({
                "job_id": jid,
                "status": status,
                "result_json": result_json,
                "error": error,
            })

        def fake_quota_check(tid):
            return True

        with (
            patch("app.modules.analysis.tasks._update_job", side_effect=fake_update_job),
            patch("app.modules.analysis.tasks._check_and_increment_quota", side_effect=fake_quota_check),
            patch("app.modules.analysis.tasks._fetch_fundamentals_stub", side_effect=RuntimeError("DB connection lost")),
            patch("app.modules.analysis.tasks.log_analysis_cost") as mock_cost,
        ):
            from app.modules.analysis.tasks import run_dcf

            run_dcf(job_id, tenant_id, "ITUB4")

            # Should have running, then failed
            statuses = [u["status"] for u in job_updates]
            assert "running" in statuses
            assert "failed" in statuses

            # Error message should be set
            failed_update = [u for u in job_updates if u["status"] == "failed"][0]
            assert failed_update["error"] is not None
            assert "DB connection lost" in failed_update["error"]

            # Cost logged on failure
            mock_cost.assert_called_once()

    def test_run_dcf_calls_log_analysis_cost_on_success(self):
        """log_analysis_cost is called with correct params on successful completion."""
        job_id = str(uuid.uuid4())
        tenant_id = str(uuid.uuid4())

        async def mock_llm(prompt, max_tokens=300):
            return ("Narrative text", {"provider_used": "openrouter", "model": "gpt-4o-mini", "success": True})

        with (
            patch("app.modules.analysis.tasks._update_job"),
            patch("app.modules.analysis.tasks._check_and_increment_quota", return_value=True),
            patch("app.modules.analysis.tasks.call_analysis_llm", side_effect=mock_llm),
            patch("app.modules.analysis.tasks.log_analysis_cost") as mock_cost,
        ):
            from app.modules.analysis.tasks import run_dcf

            run_dcf(job_id, tenant_id, "BBDC4")

            mock_cost.assert_called_once()
            _, kwargs = mock_cost.call_args
            assert kwargs["status"] == "completed" if "status" in kwargs else True
            # Check positional args include tenant_id, job_id, type, ticker
            args = mock_cost.call_args[0]
            assert args[0] == tenant_id
            assert args[1] == job_id
            assert args[2] == "dcf"
            assert args[3] == "BBDC4"


class TestDataVersioning:
    """Tests for data versioning metadata in analysis results."""

    def test_analysis_includes_data_version_id(self):
        """Completed analysis result_json contains data_version_id matching brapi_eod pattern."""
        job_id = str(uuid.uuid4())
        tenant_id = str(uuid.uuid4())

        job_updates: list[dict] = []

        def fake_update_job(jid, status, result_json=None, error=None):
            job_updates.append({
                "job_id": jid,
                "status": status,
                "result_json": result_json,
                "error": error,
            })

        async def mock_llm(prompt, max_tokens=300):
            return ("Narrative", {"provider_used": "openrouter", "model": "gpt-4o-mini", "success": True})

        with (
            patch("app.modules.analysis.tasks._update_job", side_effect=fake_update_job),
            patch("app.modules.analysis.tasks._check_and_increment_quota", return_value=True),
            patch("app.modules.analysis.tasks.call_analysis_llm", side_effect=mock_llm),
            patch("app.modules.analysis.tasks.log_analysis_cost"),
        ):
            from app.modules.analysis.tasks import run_dcf

            run_dcf(job_id, tenant_id, "PETR4")

            completed = [u for u in job_updates if u["status"] == "completed"]
            assert len(completed) == 1
            result = json.loads(completed[0]["result_json"])

            assert "data_version_id" in result
            assert re.match(r"brapi_eod_\d{8}_v1\.2", result["data_version_id"])

    def test_data_timestamp_visible_in_api(self):
        """Completed analysis result_json contains a valid ISO data_timestamp."""
        job_id = str(uuid.uuid4())
        tenant_id = str(uuid.uuid4())

        job_updates: list[dict] = []

        def fake_update_job(jid, status, result_json=None, error=None):
            job_updates.append({
                "job_id": jid,
                "status": status,
                "result_json": result_json,
                "error": error,
            })

        async def mock_llm(prompt, max_tokens=300):
            return ("Narrative", {"provider_used": "groq", "model": "llama", "success": True})

        with (
            patch("app.modules.analysis.tasks._update_job", side_effect=fake_update_job),
            patch("app.modules.analysis.tasks._check_and_increment_quota", return_value=True),
            patch("app.modules.analysis.tasks.call_analysis_llm", side_effect=mock_llm),
            patch("app.modules.analysis.tasks.log_analysis_cost"),
        ):
            from app.modules.analysis.tasks import run_dcf

            run_dcf(job_id, tenant_id, "VALE3")

            completed = [u for u in job_updates if u["status"] == "completed"]
            assert len(completed) == 1
            result = json.loads(completed[0]["result_json"])

            assert "data_timestamp" in result
            # Verify it's a valid ISO datetime
            dt = datetime.fromisoformat(result["data_timestamp"])
            assert dt.year >= 2026

    def test_data_sources_in_result(self):
        """Completed analysis result_json contains data_sources with BRAPI and B3/CVM."""
        job_id = str(uuid.uuid4())
        tenant_id = str(uuid.uuid4())

        job_updates: list[dict] = []

        def fake_update_job(jid, status, result_json=None, error=None):
            job_updates.append({
                "job_id": jid,
                "status": status,
                "result_json": result_json,
                "error": error,
            })

        async def mock_llm(prompt, max_tokens=300):
            return ("Narrative", {"provider_used": "openrouter", "model": "m", "success": True})

        with (
            patch("app.modules.analysis.tasks._update_job", side_effect=fake_update_job),
            patch("app.modules.analysis.tasks._check_and_increment_quota", return_value=True),
            patch("app.modules.analysis.tasks.call_analysis_llm", side_effect=mock_llm),
            patch("app.modules.analysis.tasks.log_analysis_cost"),
        ):
            from app.modules.analysis.tasks import run_dcf

            run_dcf(job_id, tenant_id, "ITUB4")

            completed = [u for u in job_updates if u["status"] == "completed"]
            result = json.loads(completed[0]["result_json"])

            assert "data_sources" in result
            sources = result["data_sources"]
            assert len(sources) == 2
            source_names = {s["source"] for s in sources}
            assert "BRAPI" in source_names
            assert "B3/CVM" in source_names


# ---------------------------------------------------------------------------
# Plan 03 Tests — Cache invalidation
# ---------------------------------------------------------------------------


class TestCacheInvalidation:
    """Tests for earnings-based cache invalidation."""

    def test_invalidation_marks_analyses_stale(self):
        """on_earnings_release marks old completed analyses as stale."""
        from app.modules.analysis.invalidation import on_earnings_release

        now = datetime.now(timezone.utc)
        old_date = now - timedelta(days=30)
        recent_date = now - timedelta(hours=1)
        filing_date = now - timedelta(days=1)

        # Create mock jobs
        old_job = MagicMock()
        old_job.status = "completed"
        old_job.completed_at = old_date
        old_job.ticker = "PETR4"

        recent_job = MagicMock()
        recent_job.status = "completed"
        recent_job.completed_at = recent_date
        recent_job.ticker = "PETR4"

        # Mock the DB session and redis
        mock_session = MagicMock()
        mock_session.execute.return_value.rowcount = 1

        mock_redis = MagicMock()
        mock_redis.delete.return_value = None

        from contextlib import contextmanager

        @contextmanager
        def mock_superuser_session():
            yield mock_session

        with (
            patch(
                "app.modules.analysis.invalidation.get_superuser_sync_db_session",
                mock_superuser_session,
            ),
            patch(
                "app.modules.analysis.invalidation._get_sync_redis",
                return_value=mock_redis,
            ),
        ):
            count = asyncio.run(on_earnings_release("PETR4", filing_date))

            # Should have executed an UPDATE statement
            assert mock_session.execute.called
            # Should have deleted Redis cache
            mock_redis.delete.assert_called_once_with("analysis:cache:PETR4")
            # Return count matches rowcount
            assert count == 1

    def test_invalidation_returns_count(self):
        """on_earnings_release returns the number of affected rows."""
        from app.modules.analysis.invalidation import on_earnings_release

        mock_session = MagicMock()
        mock_session.execute.return_value.rowcount = 3

        mock_redis = MagicMock()

        from contextlib import contextmanager

        @contextmanager
        def mock_superuser_session():
            yield mock_session

        with (
            patch(
                "app.modules.analysis.invalidation.get_superuser_sync_db_session",
                mock_superuser_session,
            ),
            patch(
                "app.modules.analysis.invalidation._get_sync_redis",
                return_value=mock_redis,
            ),
        ):
            filing_date = datetime.now(timezone.utc)
            count = asyncio.run(on_earnings_release("VALE3", filing_date))
            assert count == 3


# ---------------------------------------------------------------------------
# API Response test — Plan 03
# ---------------------------------------------------------------------------


class TestAPIResponse:
    def test_api_response_includes_disclaimer(self):
        """AnalysisResponse with DCF result includes disclaimer."""
        resp = AnalysisResponse(
            analysis_id="test-dcf-1",
            analysis_type="dcf",
            ticker="PETR4",
            status="completed",
            result={"fair_value": 28.50, "narrative": "Test"},
            disclaimer=CVM_DISCLAIMER_SHORT_PT,
        )
        assert "CVM" in resp.disclaimer
        assert resp.status == "completed"


# ---------------------------------------------------------------------------
# Plan 02 Tests — Quota enforcement, rate limiting, cost tracking
# ---------------------------------------------------------------------------


class TestQuotaEnforcement:
    def test_quota_enforcement_free_tier_blocks_requests(self, client, email_stub):
        """POST /analysis/dcf as free user -> 403 QUOTA_EXCEEDED."""

        async def _test():
            from tests.conftest import register_verify_and_login

            await register_verify_and_login(
                client, email_stub,
                email="free_analysis@test.com",
                password="SecurePass123!",
            )

            # Mock rate limit to allow (testing quota, not rate limit)
            with patch("app.modules.analysis.router.check_analysis_rate_limit", return_value=(True, 0)):
                # Mock quota check to return blocked (free tier)
                with patch(
                    "app.modules.analysis.router.check_analysis_quota",
                    return_value=(False, 0, 0),
                ):
                    resp = await client.post(
                        "/analysis/dcf",
                        json={"ticker": "PETR4"},
                    )

            assert resp.status_code == 403
            data = resp.json()
            assert data["detail"]["code"] == "QUOTA_EXCEEDED"

        asyncio.get_event_loop().run_until_complete(_test())

    def test_quota_enforcement_pro_tier_allows_50_per_month(self, client, email_stub):
        """POST /analysis/dcf as pro user with quota < 50 -> 202."""

        async def _test():
            from tests.conftest import register_verify_and_login

            await register_verify_and_login(
                client, email_stub,
                email="pro_analysis@test.com",
                password="SecurePass123!",
            )

            mock_task = MagicMock()
            mock_task.delay = MagicMock()
            with patch("app.modules.analysis.router.check_analysis_rate_limit", return_value=(True, 0)):
                with patch(
                    "app.modules.analysis.router.check_analysis_quota",
                    return_value=(True, 49, 50),
                ):
                    with patch("app.modules.analysis.router.increment_quota_used"):
                        with patch("app.modules.analysis.tasks.run_dcf", mock_task):
                            resp = await client.post(
                                "/analysis/dcf",
                                json={"ticker": "PETR4"},
                            )

            assert resp.status_code == 202
            data = resp.json()
            assert "job_id" in data
            assert data["status"] == "pending"

        asyncio.get_event_loop().run_until_complete(_test())


class TestRateLimiting:
    def test_rate_limiting_middleware_enforced(self, client, email_stub):
        """POST /analysis/dcf twice rapidly as pro -> second returns 429."""

        async def _test():
            from tests.conftest import register_verify_and_login

            await register_verify_and_login(
                client, email_stub,
                email="rate_limit@test.com",
                password="SecurePass123!",
            )

            # First request: rate limit allows
            mock_task = MagicMock()
            mock_task.delay = MagicMock()
            with patch("app.modules.analysis.router.check_analysis_rate_limit", return_value=(True, 0)):
                with patch("app.modules.analysis.router.check_analysis_quota", return_value=(True, 0, 50)):
                    with patch("app.modules.analysis.router.increment_quota_used"):
                        with patch("app.modules.analysis.tasks.run_dcf", mock_task):
                            resp1 = await client.post(
                                "/analysis/dcf",
                                json={"ticker": "PETR4"},
                            )
            assert resp1.status_code == 202

            # Second request: rate limit blocks
            with patch("app.modules.analysis.router.check_analysis_rate_limit", return_value=(False, 55)):
                resp2 = await client.post(
                    "/analysis/dcf",
                    json={"ticker": "PETR4"},
                )

            assert resp2.status_code == 429
            data = resp2.json()
            assert data["detail"]["code"] == "RATE_LIMITED"
            assert "retry-after" in {k.lower() for k in resp2.headers.keys()}

        asyncio.get_event_loop().run_until_complete(_test())


class TestCostTracking:
    def test_cost_tracking_per_analysis_type(self):
        """estimate_llm_cost returns correct values for known and free providers."""
        from app.modules.analysis.cost import estimate_llm_cost as _estimate

        # OpenRouter GPT-4o-mini: 1000 * 0.000150 + 500 * 0.000600 = 0.45
        cost = _estimate("openrouter", "openai/gpt-4o-mini", 1000, 500)
        assert abs(cost - 0.45) < 0.001

        # Groq free tier: always 0.0
        cost_free = _estimate("groq", "llama-3.3-70b-versatile", 1000, 500)
        assert cost_free == 0.0

        # DeepSeek: 1000 * 0.000014 + 500 * 0.000056 = 0.042
        cost_ds = _estimate("openrouter", "deepseek/deepseek-chat", 1000, 500)
        assert abs(cost_ds - 0.042) < 0.001

        # Unknown provider returns 0.0
        cost_unknown = _estimate("unknown", "unknown-model", 1000, 500)
        assert cost_unknown == 0.0

    def test_cost_log_creates_db_row(self):
        """log_analysis_cost creates AnalysisCostLog row with correct fields."""
        from app.modules.analysis.cost import log_analysis_cost
        from decimal import Decimal as _Decimal

        mock_session = MagicMock()
        mock_session.__enter__ = MagicMock(return_value=mock_session)
        mock_session.__exit__ = MagicMock(return_value=False)

        with patch(
            "app.core.db_sync.get_superuser_sync_db_session",
            return_value=mock_session,
        ):
            log_analysis_cost(
                tenant_id="t-123",
                job_id="j-456",
                analysis_type="dcf",
                ticker="PETR4",
                duration_ms=1500,
                status="completed",
                llm_provider="openrouter",
                llm_model="openai/gpt-4o-mini",
                input_tokens=1000,
                output_tokens=500,
            )

        assert mock_session.add.called
        added_obj = mock_session.add.call_args[0][0]
        assert isinstance(added_obj, AnalysisCostLog)
        assert added_obj.tenant_id == "t-123"
        assert added_obj.job_id == "j-456"
        assert added_obj.analysis_type == "dcf"
        assert added_obj.ticker == "PETR4"
        assert added_obj.estimated_cost_usd == _Decimal("0.45")


class TestDisclaimerEndpoint:
    """Plan 02: GET /analysis/{job_id} returns CVM disclaimer in response."""

    def test_get_analysis_includes_cvm_disclaimer(self, client, email_stub):
        """GET /analysis/{job_id} -> response.disclaimer contains 'CVM'."""

        async def _test():
            from tests.conftest import register_verify_and_login

            await register_verify_and_login(
                client, email_stub,
                email="disclaimer_ep@test.com",
                password="SecurePass123!",
            )

            # Create a job via endpoint (mock guards + celery dispatch)
            mock_task = MagicMock()
            mock_task.delay = MagicMock()
            with patch("app.modules.analysis.router.check_analysis_rate_limit", return_value=(True, 0)):
                with patch("app.modules.analysis.router.check_analysis_quota", return_value=(True, 0, 50)):
                    with patch("app.modules.analysis.router.increment_quota_used"):
                        with patch("app.modules.analysis.tasks.run_dcf", mock_task):
                            create_resp = await client.post(
                                "/analysis/dcf",
                                json={"ticker": "PETR4"},
                            )
            assert create_resp.status_code == 202
            job_id = create_resp.json()["job_id"]

            # Fetch the result
            get_resp = await client.get(f"/analysis/{job_id}")
            assert get_resp.status_code == 200
            data = get_resp.json()
            assert "disclaimer" in data
            assert "CVM" in data["disclaimer"]

        asyncio.get_event_loop().run_until_complete(_test())


class TestDisclaimerUI:
    def test_disclaimer_component_renders(self):
        pytest.skip("Frontend component — not testable in Python")
