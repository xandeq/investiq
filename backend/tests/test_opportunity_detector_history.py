"""Tests for the opportunity_detector history and follow endpoints.

Covers: save_opportunity_to_db persistence, GET /history (sorting, pagination,
filters by asset_type and days), PATCH /{id}/follow toggle, auth enforcement.

All DB tests use the shared in-memory SQLite session from conftest.py.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

import pytest
import pytest_asyncio

from tests.conftest import register_verify_and_login


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_opp(
    ticker: str = "VALE3",
    asset_type: str = "acao",
    detected_at: datetime | None = None,
    followed: bool = False,
) -> "DetectedOpportunity":
    from app.modules.opportunity_detector.models import DetectedOpportunity

    return DetectedOpportunity(
        id=str(uuid.uuid4()),
        ticker=ticker,
        asset_type=asset_type,
        drop_pct=-22.0,
        period="diario",
        current_price=34.0,
        currency="BRL",
        risk_level="medio",
        is_opportunity=True,
        cause_category="operacional",
        cause_explanation="Acidente isolado.",
        risk_rationale="Queda exagerada.",
        recommended_amount_brl=2000.0,
        target_upside_pct=18.0,
        telegram_message="Test message",
        followed=followed,
        detected_at=detected_at or datetime.now(timezone.utc),
    )


@pytest_asyncio.fixture
async def authed_client(client, email_stub):
    """Client with a registered and logged-in user."""
    unique_email = f"opdet_{uuid.uuid4().hex[:8]}@example.com"
    await register_verify_and_login(client, email_stub, email=unique_email)
    return client


# ---------------------------------------------------------------------------
# TestSaveOpportunityToDB — unit tests (sync session mocked)
# ---------------------------------------------------------------------------

class TestSaveOpportunityToDB:
    def _make_report(self, with_recommendation: bool = True):
        from app.modules.opportunity_detector.analyzer import OpportunityReport
        from app.modules.opportunity_detector.agents.cause import CauseResult
        from app.modules.opportunity_detector.agents.fundamentals import FundamentalsResult
        from app.modules.opportunity_detector.agents.risk import RiskResult
        from app.modules.opportunity_detector.agents.recommendation import RecommendationResult

        report = OpportunityReport(
            ticker="VALE3",
            asset_type="acao",
            drop_pct=-22.0,
            period="diario",
            current_price=34.0,
            currency="BRL",
        )
        report.cause = CauseResult("operacional", False, "Acidente operacional isolado.", "alta")
        report.fundamentals = FundamentalsResult("solidos", "Sólidos.")
        report.risk = RiskResult("medio", True, "Queda exagerada.")
        if with_recommendation:
            report.recommendation = RecommendationResult(
                suggested_amount_brl=2000.0,
                target_upside_pct=18.0,
                timeframe_days=90,
                stop_loss_pct=10.0,
                action_summary="Aportar R$2.000 em VALE3.",
            )
        return report

    def test_persists_all_fields(self):
        """save_opportunity_to_db maps all 17 OpportunityReport fields."""
        from app.modules.opportunity_detector.alert_engine import save_opportunity_to_db
        from app.modules.opportunity_detector.models import DetectedOpportunity

        report = self._make_report(with_recommendation=True)
        saved_instances = []

        mock_session = MagicMock()
        mock_session.__enter__ = MagicMock(return_value=mock_session)
        mock_session.__exit__ = MagicMock(return_value=False)
        mock_session.add = lambda obj: saved_instances.append(obj)
        mock_session.commit = MagicMock()

        with patch(
            "app.core.db_sync.get_superuser_sync_db_session",
            return_value=mock_session,
        ):
            import app.modules.opportunity_detector.alert_engine as ae
            result = ae.save_opportunity_to_db(report)

        assert result is True
        assert len(saved_instances) == 1
        opp = saved_instances[0]
        assert isinstance(opp, DetectedOpportunity)
        assert opp.ticker == "VALE3"
        assert opp.asset_type == "acao"
        assert float(opp.drop_pct) == -22.0
        assert opp.period == "diario"
        assert float(opp.current_price) == 34.0
        assert opp.currency == "BRL"
        assert opp.risk_level == "medio"
        assert opp.is_opportunity is True
        assert opp.cause_category == "operacional"
        assert "Acidente" in opp.cause_explanation
        assert "Queda" in opp.risk_rationale
        assert float(opp.recommended_amount_brl) == 2000.0
        assert float(opp.target_upside_pct) == 18.0
        assert "VALE3" in opp.telegram_message
        assert opp.followed is False
        assert opp.detected_at is not None

    def test_handles_none_recommendation(self):
        """Report with recommendation=None results in NULL amount/upside in DB."""
        from app.modules.opportunity_detector.alert_engine import save_opportunity_to_db
        from app.modules.opportunity_detector.models import DetectedOpportunity

        report = self._make_report(with_recommendation=False)
        saved_instances = []

        mock_session = MagicMock()
        mock_session.__enter__ = MagicMock(return_value=mock_session)
        mock_session.__exit__ = MagicMock(return_value=False)
        mock_session.add = lambda obj: saved_instances.append(obj)
        mock_session.commit = MagicMock()

        with patch(
            "app.core.db_sync.get_superuser_sync_db_session",
            return_value=mock_session,
        ):
            import app.modules.opportunity_detector.alert_engine as ae
            result = ae.save_opportunity_to_db(report)

        assert result is True
        opp = saved_instances[0]
        assert opp.recommended_amount_brl is None
        assert opp.target_upside_pct is None


# ---------------------------------------------------------------------------
# TestHistoryEndpoint — integration via async test client
# ---------------------------------------------------------------------------

class TestHistoryEndpoint:
    @pytest.mark.anyio
    async def test_returns_sorted_by_detected_at_desc(self, authed_client, db_session):
        """GET /history results are ordered newest-first."""
        prefix = uuid.uuid4().hex[:4].upper()
        now = datetime.now(timezone.utc)
        tickers_with_times = [
            (f"{prefix}A11", now - timedelta(hours=2)),
            (f"{prefix}B22", now - timedelta(hours=1)),
            (f"{prefix}C33", now),
        ]
        test_tickers = {t for t, _ in tickers_with_times}
        rows = [
            _make_opp(ticker=t, asset_type="acao", detected_at=dt)
            for t, dt in tickers_with_times
        ]
        for r in rows:
            db_session.add(r)
        await db_session.commit()

        resp = await authed_client.get("/opportunity-detector/history?asset_type=acao")
        assert resp.status_code == 200, resp.text
        data = resp.json()

        # Extract our 3 tickers (others may exist from other tests)
        filtered = [r for r in data["results"] if r["ticker"] in test_tickers]
        assert len(filtered) == 3, f"Expected 3 test rows, got {len(filtered)}: {[r['ticker'] for r in data['results']]}"

        detected_ats = [r["detected_at"] for r in filtered]
        assert detected_ats == sorted(detected_ats, reverse=True), (
            f"Not sorted desc: {detected_ats}"
        )

    @pytest.mark.anyio
    async def test_returns_total_count(self, authed_client, db_session):
        """total in response reflects number of matching rows."""
        prefix = uuid.uuid4().hex[:6]
        tickers = [f"{prefix[:3].upper()}{i:02d}" for i in range(5)]
        now = datetime.now(timezone.utc)
        for t in tickers:
            db_session.add(_make_opp(ticker=t, asset_type="renda_fixa", detected_at=now))
        await db_session.commit()

        resp = await authed_client.get("/opportunity-detector/history?asset_type=renda_fixa")
        assert resp.status_code == 200, resp.text
        data = resp.json()
        test_results = [r for r in data["results"] if r["ticker"] in tickers]
        assert len(test_results) == 5
        # total must be >= 5 (other renda_fixa rows may exist)
        assert data["total"] >= 5


# ---------------------------------------------------------------------------
# TestHistoryFilters — asset_type filtering
# ---------------------------------------------------------------------------

class TestHistoryFilters:
    @pytest.mark.anyio
    async def test_filter_by_asset_type_acao(self, authed_client, db_session):
        """?asset_type=acao returns only acao rows."""
        prefix = uuid.uuid4().hex[:4].upper()
        now = datetime.now(timezone.utc)
        db_session.add(_make_opp(ticker=f"{prefix}ACA", asset_type="acao", detected_at=now))
        db_session.add(_make_opp(ticker=f"{prefix}CRY", asset_type="crypto", detected_at=now))
        await db_session.commit()

        resp = await authed_client.get("/opportunity-detector/history?asset_type=acao")
        assert resp.status_code == 200, resp.text
        data = resp.json()
        asset_types = {r["asset_type"] for r in data["results"]}
        assert asset_types == {"acao"}, f"Expected only acao, got: {asset_types}"

    @pytest.mark.anyio
    async def test_filter_by_asset_type_crypto(self, authed_client, db_session):
        """?asset_type=crypto returns only crypto rows."""
        prefix = uuid.uuid4().hex[:4].upper()
        now = datetime.now(timezone.utc)
        db_session.add(_make_opp(ticker=f"{prefix}ACA", asset_type="acao", detected_at=now))
        db_session.add(_make_opp(ticker=f"{prefix}CRY", asset_type="crypto", detected_at=now))
        await db_session.commit()

        resp = await authed_client.get("/opportunity-detector/history?asset_type=crypto")
        assert resp.status_code == 200, resp.text
        data = resp.json()
        asset_types = {r["asset_type"] for r in data["results"]}
        assert asset_types == {"crypto"}, f"Expected only crypto, got: {asset_types}"


# ---------------------------------------------------------------------------
# TestHistoryDaysFilter — days parameter
# ---------------------------------------------------------------------------

class TestHistoryDaysFilter:
    @pytest.mark.anyio
    async def test_days_7_excludes_old(self, authed_client, db_session):
        """?days=7 excludes rows older than 7 days."""
        prefix = uuid.uuid4().hex[:4].upper()
        now = datetime.now(timezone.utc)
        # Recent row (3 days ago) — should appear
        recent = _make_opp(
            ticker=f"{prefix}REC",
            asset_type="renda_fixa",
            detected_at=now - timedelta(days=3),
        )
        # Old row (10 days ago) — should be excluded
        old = _make_opp(
            ticker=f"{prefix}OLD",
            asset_type="renda_fixa",
            detected_at=now - timedelta(days=10),
        )
        db_session.add(recent)
        db_session.add(old)
        await db_session.commit()

        resp = await authed_client.get(
            f"/opportunity-detector/history?days=7&asset_type=renda_fixa"
        )
        assert resp.status_code == 200, resp.text
        data = resp.json()
        tickers = {r["ticker"] for r in data["results"]}
        assert f"{prefix}REC" in tickers, "Recent row must appear in ?days=7"
        assert f"{prefix}OLD" not in tickers, "Old row must be excluded from ?days=7"

    @pytest.mark.anyio
    async def test_days_default_30(self, authed_client, db_session):
        """Default 30-day window: 20d-ago row appears, 40d-ago row does not."""
        prefix = uuid.uuid4().hex[:4].upper()
        now = datetime.now(timezone.utc)
        recent = _make_opp(
            ticker=f"{prefix}R30",
            asset_type="renda_fixa",
            detected_at=now - timedelta(days=20),
        )
        old = _make_opp(
            ticker=f"{prefix}O30",
            asset_type="renda_fixa",
            detected_at=now - timedelta(days=40),
        )
        db_session.add(recent)
        db_session.add(old)
        await db_session.commit()

        resp = await authed_client.get(
            f"/opportunity-detector/history?asset_type=renda_fixa"
        )
        assert resp.status_code == 200, resp.text
        data = resp.json()
        tickers = {r["ticker"] for r in data["results"]}
        assert f"{prefix}R30" in tickers, "20d-ago row must appear in default 30d window"
        assert f"{prefix}O30" not in tickers, "40d-ago row must not appear in default 30d window"


# ---------------------------------------------------------------------------
# TestFollowEndpoint — toggle followed flag
# ---------------------------------------------------------------------------

class TestFollowEndpoint:
    @pytest.mark.anyio
    async def test_toggles_followed_flag(self, authed_client, db_session):
        """PATCH /{id}/follow toggles followed flag (False → True → False)."""
        opp = _make_opp(followed=False)
        db_session.add(opp)
        await db_session.commit()

        # First PATCH: False → True
        resp = await authed_client.patch(f"/opportunity-detector/{opp.id}/follow")
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert data["id"] == opp.id
        assert data["followed"] is True

        # Second PATCH: True → False
        resp2 = await authed_client.patch(f"/opportunity-detector/{opp.id}/follow")
        assert resp2.status_code == 200, resp2.text
        data2 = resp2.json()
        assert data2["followed"] is False

    @pytest.mark.anyio
    async def test_returns_404_for_nonexistent(self, authed_client):
        """PATCH with unknown UUID returns 404."""
        fake_id = str(uuid.uuid4())
        resp = await authed_client.patch(f"/opportunity-detector/{fake_id}/follow")
        assert resp.status_code == 404, f"Expected 404, got {resp.status_code}: {resp.text}"


# ---------------------------------------------------------------------------
# TestAuthRequired — unauthenticated requests must return 401
# ---------------------------------------------------------------------------

class TestAuthRequired:
    @pytest.mark.anyio
    async def test_history_unauthenticated_returns_401(self, client):
        """GET /opportunity-detector/history without auth → 401."""
        resp = await client.get("/opportunity-detector/history")
        assert resp.status_code == 401, f"Expected 401, got {resp.status_code}: {resp.text}"

    @pytest.mark.anyio
    async def test_follow_unauthenticated_returns_401(self, client):
        """PATCH /opportunity-detector/{id}/follow without auth → 401."""
        resp = await client.patch(f"/opportunity-detector/{uuid.uuid4()}/follow")
        assert resp.status_code == 401, f"Expected 401, got {resp.status_code}: {resp.text}"
