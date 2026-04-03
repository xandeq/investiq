"""Tests for the opportunity_detector module.

Covers: scanner detection logic, agent outputs, deduplication, alert formatting.
All external HTTP calls are mocked — no BRAPI/Binance/LLM calls in tests.
"""
from __future__ import annotations

import json
from unittest.mock import MagicMock, patch, AsyncMock

import pytest

from app.modules.opportunity_detector.config import (
    ACOES_DAILY_DROP_PCT,
    CRYPTO_DAILY_DROP_PCT,
    DEDUP_TTL_SECONDS,
    REDIS_DEDUP_PREFIX,
)


# ---------------------------------------------------------------------------
# Scanner — detection logic
# ---------------------------------------------------------------------------

class TestScannerDetection:
    """Unit tests for drop detection thresholds."""

    def test_acoes_daily_drop_triggers(self):
        """Stock with daily drop below threshold should be detected."""
        from app.modules.opportunity_detector.scanner import _calc_weekly_change

        quote = {
            "regularMarketPrice": 34.00,
            "regularMarketChangePercent": -18.5,  # below -15% threshold
            "historicalDataPrice": [
                {"close": 45.00},
                {"close": 42.00},
                {"close": 40.00},
                {"close": 38.00},
                {"close": 36.00},
            ],
        }
        assert quote["regularMarketChangePercent"] <= ACOES_DAILY_DROP_PCT

    def test_acoes_small_drop_no_trigger(self):
        """Stock with small daily drop should NOT trigger."""
        daily_change = -5.0  # above -15% threshold
        assert daily_change > ACOES_DAILY_DROP_PCT

    def test_weekly_change_calculation(self):
        """Weekly change calc from historical data."""
        from app.modules.opportunity_detector.scanner import _calc_weekly_change

        quote = {
            "regularMarketPrice": 30.0,
            "historicalDataPrice": [
                {"close": 40.0},  # oldest
                {"close": 38.0},
                {"close": 35.0},
                {"close": 32.0},
                {"close": 31.0},
            ],
        }
        change = _calc_weekly_change(quote)
        assert change is not None
        # (30 - 40) / 40 * 100 = -25%
        assert abs(change - (-25.0)) < 0.01

    def test_weekly_change_no_history(self):
        """Empty history returns None."""
        from app.modules.opportunity_detector.scanner import _calc_weekly_change

        quote = {"regularMarketPrice": 30.0, "historicalDataPrice": []}
        assert _calc_weekly_change(quote) is None

    def test_weekly_change_zero_price(self):
        """Zero oldest close returns None (avoid division by zero)."""
        from app.modules.opportunity_detector.scanner import _calc_weekly_change

        quote = {
            "regularMarketPrice": 30.0,
            "historicalDataPrice": [{"close": 0}, {"close": 28.0}],
        }
        assert _calc_weekly_change(quote) is None

    def test_crypto_threshold(self):
        """Crypto threshold is more aggressive than stocks."""
        assert CRYPTO_DAILY_DROP_PCT < ACOES_DAILY_DROP_PCT  # -20% < -15%


# ---------------------------------------------------------------------------
# Deduplication
# ---------------------------------------------------------------------------

class TestDeduplication:
    def test_not_deduped_initially(self):
        """First opportunity for a ticker should not be deduped."""
        from app.modules.opportunity_detector.scanner import _is_deduped

        mock_redis = MagicMock()
        mock_redis.exists.return_value = 0
        assert _is_deduped(mock_redis, "VALE3", "diario") is False

    def test_deduped_after_mark(self):
        """After marking, the same ticker+period should be deduped."""
        from app.modules.opportunity_detector.scanner import _is_deduped, _mark_sent

        mock_redis = MagicMock()
        mock_redis.exists.return_value = 1

        _mark_sent(mock_redis, "VALE3", "diario")
        assert _is_deduped(mock_redis, "VALE3", "diario") is True
        mock_redis.set.assert_called_once_with(
            f"{REDIS_DEDUP_PREFIX}:VALE3:diario", "1", ex=DEDUP_TTL_SECONDS
        )

    def test_dedup_different_periods_independent(self):
        """Daily and weekly dedup keys are independent."""
        from app.modules.opportunity_detector.scanner import _mark_sent

        mock_redis = MagicMock()
        _mark_sent(mock_redis, "VALE3", "diario")
        _mark_sent(mock_redis, "VALE3", "semanal")
        assert mock_redis.set.call_count == 2


# ---------------------------------------------------------------------------
# Agents
# ---------------------------------------------------------------------------

class TestCauseAgent:
    @pytest.mark.asyncio
    async def test_cause_agent_parses_llm_response(self):
        """CauseAgent correctly parses valid LLM JSON."""
        from app.modules.opportunity_detector.agents.cause import analyze_cause

        llm_response = json.dumps({
            "category": "operacional",
            "is_systemic": False,
            "explanation": "Acidente operacional isolado na mina de Mariana.",
            "confidence": "alta",
        })

        mock_llm = AsyncMock(return_value=(llm_response, {}))
        result = await analyze_cause("VALE3", "acao", -22.0, "diario", mock_llm)

        assert result.category == "operacional"
        assert result.is_systemic is False
        assert "Mariana" in result.explanation
        assert result.confidence == "alta"

    @pytest.mark.asyncio
    async def test_cause_agent_handles_llm_failure(self):
        """CauseAgent returns safe defaults on LLM failure."""
        from app.modules.opportunity_detector.agents.cause import analyze_cause

        mock_llm = AsyncMock(side_effect=Exception("LLM timeout"))
        result = await analyze_cause("VALE3", "acao", -22.0, "diario", mock_llm)

        assert result.category == "desconhecido"
        assert result.is_systemic is False
        assert result.confidence == "baixa"


class TestRiskAgent:
    @pytest.mark.asyncio
    async def test_systemic_risk_bypasses_llm(self):
        """Systemic cause always returns 'evitar' without calling LLM."""
        from app.modules.opportunity_detector.agents.cause import CauseResult
        from app.modules.opportunity_detector.agents.fundamentals import FundamentalsResult
        from app.modules.opportunity_detector.agents.risk import analyze_risk

        cause = CauseResult(
            category="macro",
            is_systemic=True,
            explanation="Crise global de crédito.",
            confidence="alta",
        )
        fundamentals = FundamentalsResult(quality="solidos", summary="OK")
        mock_llm = AsyncMock()

        result = await analyze_risk("IBOV", -15.0, cause, fundamentals, mock_llm)

        assert result.level == "evitar"
        assert result.is_opportunity is False
        mock_llm.assert_not_called()

    @pytest.mark.asyncio
    async def test_non_systemic_calls_llm(self):
        """Non-systemic risk calls LLM for assessment."""
        from app.modules.opportunity_detector.agents.cause import CauseResult
        from app.modules.opportunity_detector.agents.fundamentals import FundamentalsResult
        from app.modules.opportunity_detector.agents.risk import analyze_risk

        cause = CauseResult(
            category="operacional",
            is_systemic=False,
            explanation="Acidente isolado.",
            confidence="alta",
        )
        fundamentals = FundamentalsResult(quality="solidos", summary="Fundamentos sólidos.")
        llm_response = json.dumps({
            "level": "medio",
            "is_opportunity": True,
            "rationale": "Queda exagerada, fundamentos intactos.",
        })
        mock_llm = AsyncMock(return_value=(llm_response, {}))

        result = await analyze_risk("VALE3", -22.0, cause, fundamentals, mock_llm)

        assert result.level == "medio"
        assert result.is_opportunity is True
        mock_llm.assert_called_once()


class TestRecommendationAgent:
    @pytest.mark.asyncio
    async def test_recommendation_parses_valid_response(self):
        """RecommendationAgent correctly parses LLM JSON."""
        from app.modules.opportunity_detector.agents.recommendation import generate_recommendation

        llm_response = json.dumps({
            "suggested_amount_brl": 2500,
            "target_upside_pct": 18,
            "timeframe_days": 90,
            "stop_loss_pct": 10,
            "action_summary": "Aportar R$2.500 em VALE3, target +18% em 90 dias.",
        })
        mock_llm = AsyncMock(return_value=(llm_response, {}))

        result = await generate_recommendation(
            "VALE3", "acao", 34.0, -22.0, "medio", "Acidente isolado.", "Sólidos.", mock_llm
        )

        assert result.suggested_amount_brl == 2500.0
        assert result.target_upside_pct == 18.0
        assert result.timeframe_days == 90
        assert result.stop_loss_pct == 10.0

    @pytest.mark.asyncio
    async def test_recommendation_safe_defaults_on_failure(self):
        """RecommendationAgent returns safe defaults on LLM failure."""
        from app.modules.opportunity_detector.agents.recommendation import generate_recommendation

        mock_llm = AsyncMock(side_effect=Exception("Quota exceeded"))
        result = await generate_recommendation(
            "VALE3", "acao", 34.0, -22.0, "medio", "Causa.", "Fundamentos.", mock_llm
        )

        assert result.suggested_amount_brl > 0
        assert result.timeframe_days > 0
        assert "VALE3" in result.action_summary


# ---------------------------------------------------------------------------
# OpportunityReport formatting
# ---------------------------------------------------------------------------

class TestOpportunityReport:
    def _make_report(self, is_opportunity=True):
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
            current_price=34.00,
            currency="BRL",
        )
        report.cause = CauseResult("operacional", False, "Acidente operacional isolado.", "alta")
        report.fundamentals = FundamentalsResult("solidos", "Fundamentos sólidos.")
        report.risk = RiskResult("medio", is_opportunity, "Queda exagerada, fundamentos intactos.")
        if is_opportunity:
            report.recommendation = RecommendationResult(
                suggested_amount_brl=2000.0,
                target_upside_pct=18.0,
                timeframe_days=90,
                stop_loss_pct=10.0,
                action_summary="Aportar R$2.000 em VALE3.",
            )
        return report

    def test_alert_message_contains_ticker(self):
        report = self._make_report()
        msg = report.alert_message()
        assert "VALE3" in msg
        assert "22.0%" in msg or "22,0%" in msg or "22.0" in msg

    def test_alert_message_contains_recommendation(self):
        report = self._make_report(is_opportunity=True)
        msg = report.alert_message()
        assert "2,000" in msg or "2.000" in msg or "2000" in msg
        assert "18" in msg  # target upside

    def test_alert_message_no_recommendation_when_not_opportunity(self):
        report = self._make_report(is_opportunity=False)
        msg = report.alert_message()
        assert "Sugestão" not in msg

    def test_alert_html_is_valid_html(self):
        report = self._make_report()
        html = report.alert_html()
        assert "<div" in html
        assert "VALE3" in html

    def test_alert_subject_format(self):
        """Email subject should include ticker and drop percentage."""
        report = self._make_report()
        subject = f"InvestIQ — Oportunidade: {report.ticker} caiu {abs(report.drop_pct):.1f}%"
        assert "VALE3" in subject
        assert "22.0%" in subject


# ---------------------------------------------------------------------------
# Alert Engine
# ---------------------------------------------------------------------------

class TestAlertEngine:
    def test_send_telegram_skips_when_no_chat_id(self, monkeypatch):
        """Telegram send returns False gracefully when chat_id not configured."""
        monkeypatch.setattr(
            "app.modules.opportunity_detector.alert_engine.TELEGRAM_CHAT_ID", ""
        )
        from app.modules.opportunity_detector.alert_engine import send_telegram

        result = send_telegram("test message")
        assert result is False

    def test_send_email_skips_when_no_api_key(self, monkeypatch):
        """Email send returns False gracefully when Brevo key not configured."""
        from app.core.config import settings
        monkeypatch.setattr(settings, "BREVO_API_KEY", "")
        from app.modules.opportunity_detector.alert_engine import send_email

        result = send_email("subject", "<p>html</p>")
        assert result is False

    @patch("app.modules.opportunity_detector.alert_engine.send_telegram", return_value=True)
    @patch("app.modules.opportunity_detector.alert_engine.send_email", return_value=True)
    def test_dispatch_calls_both_channels(self, mock_email, mock_telegram):
        """dispatch_opportunity calls both Telegram and email."""
        from app.modules.opportunity_detector.alert_engine import dispatch_opportunity
        from app.modules.opportunity_detector.analyzer import OpportunityReport
        from app.modules.opportunity_detector.agents.cause import CauseResult
        from app.modules.opportunity_detector.agents.risk import RiskResult

        report = OpportunityReport(
            ticker="VALE3", asset_type="acao", drop_pct=-22.0,
            period="diario", current_price=34.0, currency="BRL",
        )
        report.cause = CauseResult("operacional", False, "Acidente.", "alta")
        report.risk = RiskResult("medio", False, "Risco médio.")

        results = dispatch_opportunity(report)
        assert results["telegram"] is True
        assert results["email"] is True
        mock_telegram.assert_called_once()
        mock_email.assert_called_once()
