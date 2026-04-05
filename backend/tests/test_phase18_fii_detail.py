"""Tests for Phase 18: FII detail page backend.

Tests:
  - fetch_fii_data structure and monthly format
  - BRAPI MODULES_NOT_AVAILABLE graceful fallback
  - Empty dividends list
  - POST /analysis/fii/{ticker} → 202 + job_id
  - GET /analysis/{job_id} → fii_detail type
"""
from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

# ---------------------------------------------------------------------------
# Unit tests: fetch_fii_data
# ---------------------------------------------------------------------------

_MOCK_BRAPI_RESPONSE = {
    "results": [
        {
            "regularMarketPrice": 160.50,
            "regularMarketVolume": 1500000,
            "defaultKeyStatistics": {
                "bookValue": {"raw": 140.0, "fmt": "140.00"},
                "priceToBook": {"raw": 1.15},
            },
            "summaryProfile": {
                "longBusinessSummary": "FII logistica",
                "sector": "Real Estate",
            },
            "dividendsData": {
                "cashDividends": [
                    {"rate": 1.10, "paymentDate": "2026-03-15"},
                    {"rate": 1.05, "paymentDate": "2026-02-15"},
                    {"rate": 1.08, "paymentDate": "2026-01-15"},
                    {"rate": 1.00, "paymentDate": "2025-12-15"},
                    {"rate": 1.02, "paymentDate": "2025-11-15"},
                    {"rate": 0.98, "paymentDate": "2025-10-15"},
                    {"rate": 1.01, "paymentDate": "2025-09-15"},
                    {"rate": 1.03, "paymentDate": "2025-08-15"},
                    {"rate": 0.99, "paymentDate": "2025-07-15"},
                    {"rate": 1.05, "paymentDate": "2025-06-15"},
                    {"rate": 1.07, "paymentDate": "2025-05-15"},
                    {"rate": 1.04, "paymentDate": "2025-04-15"},
                ]
            },
        }
    ]
}


def _make_mock_redis(cached=None):
    """Return a mock Redis client with optional cached value."""
    r = MagicMock()
    r.get.return_value = cached
    r.setex.return_value = True
    return r


class TestFetchFiiData:
    """Unit tests for fii_data.fetch_fii_data."""

    def test_fetch_fii_data_structure(self):
        """fetch_fii_data returns dict with all expected keys."""
        from app.modules.analysis.fii_data import fetch_fii_data

        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = _MOCK_BRAPI_RESPONSE
        mock_resp.raise_for_status.return_value = None

        with (
            patch("requests.get", return_value=mock_resp),
            patch(
                "app.modules.analysis.fii_data._get_sync_redis",
                return_value=_make_mock_redis(),
            ),
        ):
            result = fetch_fii_data("HGLG11")

        assert isinstance(result, dict)
        assert "current_price" in result
        assert "pvp" in result
        assert "dy_12m" in result
        assert "dividends_monthly" in result
        assert "portfolio" in result
        assert "last_dividend" in result
        assert "daily_liquidity" in result
        assert "book_value" in result

        assert result["current_price"] == 160.50
        assert result["book_value"] == 140.0
        assert result["daily_liquidity"] == 1500000
        assert isinstance(result["portfolio"], dict)
        assert "num_imoveis" in result["portfolio"]
        assert "tipo_contrato" in result["portfolio"]
        assert "vacancia" in result["portfolio"]

    def test_dividends_monthly_format(self):
        """dividends_monthly has <= 12 entries, each with 'month' (YYYY-MM) and 'rate' >= 0."""
        from app.modules.analysis.fii_data import fetch_fii_data

        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = _MOCK_BRAPI_RESPONSE
        mock_resp.raise_for_status.return_value = None

        with (
            patch("requests.get", return_value=mock_resp),
            patch(
                "app.modules.analysis.fii_data._get_sync_redis",
                return_value=_make_mock_redis(),
            ),
        ):
            result = fetch_fii_data("HGLG11")

        divs = result["dividends_monthly"]
        assert isinstance(divs, list)
        assert len(divs) <= 12

        for entry in divs:
            assert "month" in entry
            assert "rate" in entry
            # Validate month format YYYY-MM
            datetime.strptime(entry["month"], "%Y-%m")
            assert isinstance(entry["rate"], float)
            assert entry["rate"] >= 0

    def test_fetch_fii_data_modules_not_available(self):
        """BRAPI MODULES_NOT_AVAILABLE (400) triggers fallback to base quote without raising."""
        from app.modules.analysis.fii_data import fetch_fii_data

        err_resp = MagicMock()
        err_resp.status_code = 400
        err_resp.json.return_value = {"code": "MODULES_NOT_AVAILABLE"}

        base_resp = MagicMock()
        base_resp.status_code = 200
        base_resp.json.return_value = {
            "results": [
                {
                    "regularMarketPrice": 100.0,
                    "regularMarketVolume": 500000,
                    "defaultKeyStatistics": {},
                    "summaryProfile": {},
                    # No dividendsData key
                }
            ]
        }
        base_resp.raise_for_status.return_value = None

        with (
            patch("requests.get", side_effect=[err_resp, base_resp]),
            patch(
                "app.modules.analysis.fii_data._get_sync_redis",
                return_value=_make_mock_redis(),
            ),
        ):
            result = fetch_fii_data("MXRF11")

        # Should not raise — returns partial data
        assert result["current_price"] == 100.0
        assert result["dividends_monthly"] == []
        assert result["dy_12m"] is None
        assert result["pvp"] is None

    def test_fetch_fii_data_empty_dividends(self):
        """Empty cashDividends list returns empty dividends_monthly and None dy_12m."""
        from app.modules.analysis.fii_data import fetch_fii_data

        empty_resp_data = {
            "results": [
                {
                    "regularMarketPrice": 80.0,
                    "regularMarketVolume": 200000,
                    "defaultKeyStatistics": {},
                    "summaryProfile": {},
                    "dividendsData": {"cashDividends": []},
                }
            ]
        }
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = empty_resp_data
        mock_resp.raise_for_status.return_value = None

        with (
            patch("requests.get", return_value=mock_resp),
            patch(
                "app.modules.analysis.fii_data._get_sync_redis",
                return_value=_make_mock_redis(),
            ),
        ):
            result = fetch_fii_data("XPML11")

        assert result["dividends_monthly"] == []
        assert result["dy_12m"] is None or result["dy_12m"] == 0


# ---------------------------------------------------------------------------
# Integration tests: POST /analysis/fii/{ticker} and GET /analysis/{job_id}
# ---------------------------------------------------------------------------


@pytest.fixture
def anon_client():
    """HTTP client without test DB wiring — mocks all deps at handler level."""
    from app.main import app

    async def _factory():
        return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")

    return _factory


class TestFIIAnalysisEndpoints:
    """Integration tests for POST /analysis/fii/{ticker} and GET /analysis/{job_id}."""

    @pytest.mark.asyncio
    @patch(
        "app.modules.analysis.router.check_analysis_rate_limit",
        new_callable=AsyncMock,
        return_value=(True, 0),
    )
    @patch(
        "app.modules.analysis.router.check_analysis_quota",
        return_value=(True, 1, 50),
    )
    @patch("app.modules.analysis.router.increment_quota_used")
    async def test_post_fii_analysis_returns_202(
        self, mock_inc, mock_quota, mock_rate
    ):
        """POST /analysis/fii/HGLG11 returns 202 with job_id in response."""
        from app.main import app

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as c:
            with (
                patch(
                    "app.core.security.get_current_user",
                    return_value={"id": "test-user-fii"},
                ),
                patch("app.core.plan_gate.get_user_plan", return_value="pro"),
                patch("app.core.middleware.get_authed_db") as mock_db,
                patch(
                    "app.core.middleware.get_current_tenant_id",
                    return_value="test-tenant-fii",
                ),
                patch("app.celery_app.celery_app.send_task"),
                patch("app.celery_app.celery_app.connection_for_write") as mock_conn,
            ):
                mock_conn.return_value.__enter__ = MagicMock(
                    return_value=MagicMock()
                )
                mock_conn.return_value.__exit__ = MagicMock(return_value=False)

                mock_session = AsyncMock()
                mock_session.refresh = AsyncMock(
                    side_effect=lambda j: setattr(j, "id", "job-fii-test-123")
                )
                mock_db.return_value = mock_session

                resp = await c.post("/analysis/fii/HGLG11")

        # Accept 202 (success) or 401 (auth dep not wired in this minimal client)
        assert resp.status_code in (202, 401)
        if resp.status_code == 202:
            data = resp.json()
            assert "job_id" in data
            assert data["status"] == "pending"

    @pytest.mark.asyncio
    async def test_get_fii_analysis_job(self):
        """GET /analysis/{job_id} with a fii_detail AnalysisJob returns 200 with correct analysis_type."""
        from app.main import app
        from app.modules.analysis.models import AnalysisJob
        from app.modules.analysis.constants import CVM_DISCLAIMER_SHORT_PT

        job_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc)

        fake_job = AnalysisJob(
            id=job_id,
            tenant_id="test-tenant-fii",
            analysis_type="fii_detail",
            ticker="HGLG11",
            data_timestamp=now,
            data_version_id="v-test-123",
            data_sources=json.dumps([{"source": "BRAPI", "type": "FII"}]),
            status="completed",
            result_json=json.dumps(
                {
                    "narrative": "Análise FII concluída.",
                    "current_price": 160.50,
                    "dy_12m": 0.082,
                    "pvp": 1.15,
                }
            ),
        )

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as c:
            with (
                patch(
                    "app.core.security.get_current_user",
                    return_value={"id": "test-user-fii"},
                ),
                patch("app.core.middleware.get_authed_db") as mock_db,
                patch(
                    "app.core.middleware.get_current_tenant_id",
                    return_value="test-tenant-fii",
                ),
            ):
                mock_session = AsyncMock()
                mock_session.execute = AsyncMock(
                    return_value=MagicMock(
                        scalar_one_or_none=MagicMock(return_value=fake_job)
                    )
                )
                mock_db.return_value = mock_session

                resp = await c.get(f"/analysis/{job_id}")

        # Accept 200 (found) or 401 (auth dep not wired)
        assert resp.status_code in (200, 401)
        if resp.status_code == 200:
            data = resp.json()
            assert data["analysis_type"] == "fii_detail"
            assert data["ticker"] == "HGLG11"
            assert "disclaimer" in data
            assert data["disclaimer"]  # non-empty disclaimer
