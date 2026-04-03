"""Tests for Phase 13 Plan 01: DCF Real Data Layer.

Tests cover:
- BRAPI fundamentals fetching and parsing (data.py)
- BCB SELIC rate fetching with fallback (data.py)
- Redis caching behavior (data.py)
- WACC CAPM calculation (dcf.py)
- 2-Stage FCFF DCF model (dcf.py)
- Sensitivity analysis (dcf.py)
- Growth rate estimation from historical FCF (dcf.py)
- Stub removal verification (tasks.py)
"""
from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest

from app.modules.analysis.dcf import (
    ERP_BRAZIL,
    calculate_dcf,
    calculate_dcf_with_sensitivity,
    calculate_wacc,
    estimate_growth_rate,
)

# ---------------------------------------------------------------------------
# Fixtures: realistic BRAPI response (based on PETR4 from RESEARCH.md)
# ---------------------------------------------------------------------------

MOCK_BRAPI_RESPONSE = {
    "results": [
        {
            "symbol": "PETR4",
            "regularMarketPrice": 48.67,
            "marketCap": 640_000_000_000,
            "summaryProfile": {
                "sector": "Energia",
                "sectorKey": "energia",
                "industry": "Petroleo e Gas Integrado",
            },
            "defaultKeyStatistics": {
                "priceToBook": {"raw": 1.533, "fmt": "1.53"},
                "trailingPE": {"raw": 6.368, "fmt": "6.37"},
                "earningsPerShare": {"raw": 8.582, "fmt": "8.58"},
                "beta": 1.2,
                "enterpriseValue": {"raw": 1_264_262_300_000, "fmt": "1.26T"},
                "enterpriseToEbitda": {"raw": 5.5, "fmt": "5.5"},
                "bookValue": {"raw": 32.399, "fmt": "32.40"},
                "marketCap": 640_000_000_000,
                "yield": 0.06,
            },
            "financialData": {
                "totalRevenue": {"raw": 497_549_000_000, "fmt": "497.5B"},
                "ebitda": {"raw": 230_015_990_000, "fmt": "230B"},
                "freeCashflow": {"raw": 94_680_000_000, "fmt": "94.7B"},
                "totalDebt": {"raw": 674_687_000_000, "fmt": "674.7B"},
                "totalCash": {"raw": 50_608_000_000, "fmt": "50.6B"},
                "debtToEquity": {"raw": 1.616, "fmt": "1.62"},
                "profitMargins": {"raw": 0.222, "fmt": "22.2%"},
                "returnOnEquity": {"raw": 0.265, "fmt": "26.5%"},
                "currentRatio": {"raw": 0.706, "fmt": "0.71"},
                "dividendYield": {"raw": 0.08, "fmt": "8%"},
            },
            "incomeStatementHistory": [
                {
                    "endDate": "2025-12-31",
                    "totalRevenue": 497_549_000_000,
                    "costOfRevenue": 300_000_000_000,
                    "grossProfit": 197_549_000_000,
                    "ebit": 150_000_000_000,
                    "netIncome": 110_000_000_000,
                },
            ],
            "cashflowHistory": [
                {"endDate": "2025-12-31", "operatingCashFlow": 150_000_000_000, "freeCashFlow": 94_680_000_000, "investmentCashFlow": -55_000_000_000, "financingCashFlow": -40_000_000_000},
                {"endDate": "2024-12-31", "operatingCashFlow": 140_000_000_000, "freeCashFlow": 85_000_000_000, "investmentCashFlow": -50_000_000_000, "financingCashFlow": -35_000_000_000},
                {"endDate": "2023-12-31", "operatingCashFlow": 130_000_000_000, "freeCashFlow": 78_000_000_000, "investmentCashFlow": -48_000_000_000, "financingCashFlow": -30_000_000_000},
                {"endDate": "2022-12-31", "operatingCashFlow": 120_000_000_000, "freeCashFlow": 70_000_000_000, "investmentCashFlow": -45_000_000_000, "financingCashFlow": -28_000_000_000},
                {"endDate": "2021-12-31", "operatingCashFlow": 100_000_000_000, "freeCashFlow": 60_000_000_000, "investmentCashFlow": -40_000_000_000, "financingCashFlow": -25_000_000_000},
            ],
            "dividendsData": {
                "cashDividends": [
                    {"rate": 1.50, "paymentDate": "2025-06-15", "lastDatePrior": "2025-06-01", "label": "DIVIDENDO"},
                ]
            },
        }
    ]
}

MOCK_BCB_RESPONSE = [
    {"data": "19/03/2026", "valor": "14.75"}
]


# ---------------------------------------------------------------------------
# data.py tests
# ---------------------------------------------------------------------------

class TestFetchFundamentals:
    """Tests for fetch_fundamentals() in data.py."""

    @patch("app.modules.analysis.data._get_sync_redis")
    @patch("app.modules.analysis.data.requests.get")
    @patch("app.modules.analysis.data._resolve_brapi_token", return_value="test-token")
    def test_fetch_fundamentals_parses_brapi_response(self, mock_token, mock_get, mock_redis):
        """Verify all expected fields are extracted from BRAPI response."""
        from app.modules.analysis.data import fetch_fundamentals

        mock_redis_instance = MagicMock()
        mock_redis_instance.get.return_value = None  # cache miss
        mock_redis.return_value = mock_redis_instance

        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = MOCK_BRAPI_RESPONSE
        mock_get.return_value = mock_resp

        result = fetch_fundamentals("PETR4")

        assert result["current_price"] == 48.67
        assert result["eps"] == 8.582
        assert result["pe_ratio"] == 6.368
        assert result["price_to_book"] == 1.533
        assert result["beta"] == 1.2
        assert result["free_cash_flow"] == 94_680_000_000
        assert result["total_debt"] == 674_687_000_000
        assert result["sector"] == "Energia"
        assert result["shares_outstanding"] is not None
        assert result["shares_outstanding"] > 0
        assert "data_completeness" in result
        assert "available" in result["data_completeness"]

    @patch("app.modules.analysis.data._get_sync_redis")
    @patch("app.modules.analysis.data.requests.get")
    @patch("app.modules.analysis.data._resolve_brapi_token", return_value="test-token")
    def test_fetch_fundamentals_caches_in_redis(self, mock_token, mock_get, mock_redis):
        """Verify Redis setex is called with correct key and TTL."""
        from app.modules.analysis.data import fetch_fundamentals

        mock_redis_instance = MagicMock()
        mock_redis_instance.get.return_value = None
        mock_redis.return_value = mock_redis_instance

        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = MOCK_BRAPI_RESPONSE
        mock_get.return_value = mock_resp

        fetch_fundamentals("PETR4")

        mock_redis_instance.setex.assert_called_once()
        call_args = mock_redis_instance.setex.call_args
        assert call_args[0][0] == "brapi:fundamentals:PETR4"
        assert call_args[0][1] == 86400  # 24h TTL

    @patch("app.modules.analysis.data._get_sync_redis")
    def test_fetch_fundamentals_returns_cache_hit(self, mock_redis):
        """Verify cached data is returned without calling BRAPI."""
        from app.modules.analysis.data import fetch_fundamentals

        cached_data = {"current_price": 48.67, "free_cash_flow": 94_680_000_000}
        mock_redis_instance = MagicMock()
        mock_redis_instance.get.return_value = json.dumps(cached_data)
        mock_redis.return_value = mock_redis_instance

        result = fetch_fundamentals("PETR4")

        assert result["current_price"] == 48.67
        assert result["free_cash_flow"] == 94_680_000_000


class TestGetSelicRate:
    """Tests for get_selic_rate() in data.py."""

    @patch("app.modules.analysis.data._get_sync_redis")
    @patch("app.modules.analysis.data.requests.get")
    def test_get_selic_rate_parses_bcb_response(self, mock_get, mock_redis):
        """Verify BCB response is parsed correctly."""
        from app.modules.analysis.data import get_selic_rate

        mock_redis_instance = MagicMock()
        mock_redis_instance.get.return_value = None
        mock_redis.return_value = mock_redis_instance

        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = MOCK_BCB_RESPONSE
        mock_get.return_value = mock_resp

        rate, date_str, is_fallback = get_selic_rate()

        assert rate == 0.1475
        assert date_str == "2026-03-19"
        assert is_fallback is False

    @patch("app.modules.analysis.data._get_sync_redis")
    @patch("app.modules.analysis.data.requests.get")
    def test_get_selic_rate_fallback_on_error(self, mock_get, mock_redis):
        """Verify fallback is returned when BCB API fails."""
        from app.modules.analysis.data import get_selic_rate

        mock_redis_instance = MagicMock()
        mock_redis_instance.get.return_value = None
        mock_redis.return_value = mock_redis_instance

        mock_get.side_effect = Exception("BCB API down")

        rate, date_str, is_fallback = get_selic_rate()

        assert rate == 0.1475
        assert is_fallback is True


# ---------------------------------------------------------------------------
# dcf.py tests
# ---------------------------------------------------------------------------

class TestCalculateWacc:
    """Tests for calculate_wacc() in dcf.py."""

    def test_calculate_wacc_capm_formula(self):
        """Beta=1.0, SELIC=0.1475 -> Ke=0.2175, verify WACC."""
        wacc = calculate_wacc(
            selic=0.1475,
            beta=1.0,
            debt=500_000,
            equity=1_000_000,
            tax_rate=0.34,
        )
        # Ke = 0.1475 + 1.0 * 0.07 = 0.2175
        # Kd = 0.1475 + 0.02 = 0.1675
        # D/(D+E) = 500k/1.5M = 0.3333
        # E/(D+E) = 1M/1.5M = 0.6667
        # WACC = 0.2175 * 0.6667 + 0.1675 * 0.66 * 0.3333
        expected_ke = 0.2175
        expected_kd = 0.1675
        e_ratio = 1_000_000 / 1_500_000
        d_ratio = 500_000 / 1_500_000
        expected_wacc = expected_ke * e_ratio + expected_kd * (1 - 0.34) * d_ratio
        assert abs(wacc - expected_wacc) < 0.0001

    def test_calculate_wacc_no_beta_defaults_to_1(self):
        """Beta=None should default to 1.0."""
        wacc_with_beta = calculate_wacc(0.1475, 1.0, 500_000, 1_000_000)
        wacc_no_beta = calculate_wacc(0.1475, None, 500_000, 1_000_000)
        assert wacc_with_beta == wacc_no_beta

    def test_calculate_wacc_zero_capital_returns_ke(self):
        """When total capital <= 0, should return cost of equity."""
        wacc = calculate_wacc(0.1475, 1.2, 0, 0)
        expected_ke = 0.1475 + 1.2 * ERP_BRAZIL
        assert abs(wacc - expected_ke) < 0.0001


class TestCalculateDcf:
    """Tests for calculate_dcf() in dcf.py."""

    def test_calculate_dcf_basic(self):
        """Known FCF/growth/WACC produces fair value in expected range."""
        result = calculate_dcf(
            fcf_current=10_000_000_000,
            shares_outstanding=1_000_000_000,
            growth_rate=0.05,
            wacc=0.15,
            terminal_growth=0.03,
        )
        assert result["fair_value"] > 0
        assert "enterprise_value" in result
        assert "terminal_value" in result
        assert "projected_fcfs" in result
        assert len(result["projected_fcfs"]) == 5
        # Fair value should be reasonable (not absurdly high or near zero)
        assert 5 < result["fair_value"] < 200

    def test_calculate_dcf_wacc_below_terminal_raises(self):
        """WACC <= terminal_growth should raise ValueError."""
        with pytest.raises(ValueError, match="WACC"):
            calculate_dcf(
                fcf_current=10_000_000_000,
                shares_outstanding=1_000_000_000,
                growth_rate=0.05,
                wacc=0.03,
                terminal_growth=0.03,
            )

    def test_calculate_dcf_projections_increase(self):
        """Projected FCFs should increase with positive growth."""
        result = calculate_dcf(
            fcf_current=10_000_000_000,
            shares_outstanding=1_000_000_000,
            growth_rate=0.05,
            wacc=0.15,
            terminal_growth=0.03,
        )
        fcfs = result["projected_fcfs"]
        for i in range(1, len(fcfs)):
            assert fcfs[i]["fcf"] > fcfs[i - 1]["fcf"]


class TestDcfSensitivity:
    """Tests for calculate_dcf_with_sensitivity() in dcf.py."""

    def test_dcf_sensitivity_bear_lt_base_lt_bull(self):
        """Bear < Base < Bull fair values."""
        result = calculate_dcf_with_sensitivity(
            fcf_current=10_000_000_000,
            shares_outstanding=1_000_000_000,
            growth_rate=0.06,
            wacc=0.15,
            terminal_growth=0.03,
            net_debt=5_000_000_000,
        )
        low = result["fair_value_range"]["low"]
        high = result["fair_value_range"]["high"]
        base = result["fair_value"]

        assert low is not None
        assert high is not None
        assert low < base < high

    def test_dcf_sensitivity_has_key_drivers(self):
        """Result should contain key_drivers list."""
        result = calculate_dcf_with_sensitivity(
            fcf_current=10_000_000_000,
            shares_outstanding=1_000_000_000,
            growth_rate=0.06,
            wacc=0.15,
            terminal_growth=0.03,
            net_debt=5_000_000_000,
        )
        assert "key_drivers" in result
        assert len(result["key_drivers"]) >= 1

    def test_dcf_sensitivity_has_projected_fcfs(self):
        """Result should include projected FCFs from base scenario."""
        result = calculate_dcf_with_sensitivity(
            fcf_current=10_000_000_000,
            shares_outstanding=1_000_000_000,
            growth_rate=0.06,
            wacc=0.15,
            terminal_growth=0.03,
            net_debt=5_000_000_000,
        )
        assert "projected_fcfs" in result
        assert len(result["projected_fcfs"]) == 5


class TestEstimateGrowthRate:
    """Tests for estimate_growth_rate() in dcf.py."""

    def test_estimate_growth_rate_from_history(self):
        """5 years of FCF data should produce reasonable CAGR."""
        history = [
            {"free_cash_flow": 94_680_000_000},  # newest (BRAPI order)
            {"free_cash_flow": 85_000_000_000},
            {"free_cash_flow": 78_000_000_000},
            {"free_cash_flow": 70_000_000_000},
            {"free_cash_flow": 60_000_000_000},  # oldest
        ]
        rate = estimate_growth_rate(history)
        # CAGR of 60B -> 94.68B over 4 years ~ 12.1%
        assert 0.05 < rate < 0.20

    def test_estimate_growth_rate_fallback_insufficient_data(self):
        """Less than 3 data points should return default."""
        rate = estimate_growth_rate([{"free_cash_flow": 100}], default=0.05)
        assert rate == 0.05

    def test_estimate_growth_rate_fallback_negative_fcf(self):
        """Negative FCF should return default."""
        history = [
            {"free_cash_flow": -10_000},
            {"free_cash_flow": 20_000},
            {"free_cash_flow": -5_000},
        ]
        rate = estimate_growth_rate(history, default=0.05)
        assert rate == 0.05

    def test_estimate_growth_rate_empty_history(self):
        """Empty list should return default."""
        rate = estimate_growth_rate([], default=0.07)
        assert rate == 0.07


class TestStubRemoval:
    """Verify Phase 12 stubs are deleted from tasks.py."""

    def test_run_dcf_task_uses_real_functions(self):
        """Confirm _fetch_fundamentals_stub no longer exists in tasks module."""
        import app.modules.analysis.tasks as tasks_mod

        assert not hasattr(tasks_mod, "_fetch_fundamentals_stub")
        assert not hasattr(tasks_mod, "_calculate_dcf_stub")

    def test_tasks_imports_real_modules(self):
        """Confirm tasks.py imports from data.py and dcf.py."""
        import app.modules.analysis.tasks as tasks_mod
        import inspect
        source = inspect.getsource(tasks_mod)
        assert "from app.modules.analysis.data import" in source
        assert "from app.modules.analysis.dcf import" in source
