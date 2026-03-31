"""Tests for Phase 12 foundation: analysis models, schemas, versioning, constants.

Fully implemented tests (7):
- test_analysis_job_model_fields
- test_analysis_quota_log_model_fields
- test_analysis_cost_log_model_fields
- test_data_version_id_format
- test_dcf_request_validation
- test_analysis_response_includes_disclaimer
- test_quota_limits_constants

Stub tests (10) — implemented in Plans 02 and 03.
"""
from __future__ import annotations

import re

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


# ---------------------------------------------------------------------------
# Fully implemented tests
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
        assert "\u00e1" in CVM_DISCLAIMER_PT  # a with acute (Analise -> Analise)
        assert "\u00e3" in CVM_DISCLAIMER_PT  # a with tilde (nao -> nao)


# ---------------------------------------------------------------------------
# Stub tests — implemented in Plans 02 and 03
# ---------------------------------------------------------------------------


class TestQuotaEnforcement:
    def test_quota_enforcement_free_tier_blocks_requests(self):
        pytest.skip("Implemented in Plan 02")

    def test_quota_enforcement_pro_tier_allows_50_per_month(self):
        pytest.skip("Implemented in Plan 02")


class TestRateLimiting:
    def test_rate_limiting_middleware_enforced(self):
        pytest.skip("Implemented in Plan 02")


class TestCostTracking:
    def test_cost_tracking_per_analysis_type(self):
        pytest.skip("Implemented in Plan 02")


class TestDataVersioning:
    def test_analysis_includes_data_version_id(self):
        pytest.skip("Implemented in Plan 03")

    def test_data_timestamp_visible_in_api(self):
        pytest.skip("Implemented in Plan 03")


class TestAsyncJobs:
    def test_async_job_lifecycle_complete(self):
        pytest.skip("Implemented in Plan 03")

    def test_celery_task_error_handling(self):
        pytest.skip("Implemented in Plan 03")


class TestAPIResponse:
    def test_api_response_includes_disclaimer(self):
        pytest.skip("Implemented in Plan 03")


class TestDisclaimerUI:
    def test_disclaimer_component_renders(self):
        pytest.skip("Implemented in Plan 03")
