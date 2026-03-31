"""Test fixtures for the AI Analysis module (Phase 12).

Provides sample tickers, mock BRAPI fundamentals data, and
mock AnalysisJob constructor kwargs for use in tests.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

import pytest


@pytest.fixture
def sample_tickers() -> list[str]:
    """Return a list of sample B3 tickers for testing."""
    return ["PETR4", "VALE3", "BBDC4", "ITUB4", "WEGE3"]


# Static mock data for each sample ticker (realistic but deterministic values)
_MOCK_FUNDAMENTALS = {
    "PETR4": {
        "current_price": 38.50,
        "eps": 5.12,
        "pe_ratio": 7.52,
        "dividend_yield": 0.0845,
        "free_cash_flow": 125_000_000_000,
        "revenue": 510_000_000_000,
        "market_cap": 498_000_000_000,
    },
    "VALE3": {
        "current_price": 62.30,
        "eps": 8.74,
        "pe_ratio": 7.13,
        "dividend_yield": 0.0920,
        "free_cash_flow": 68_000_000_000,
        "revenue": 215_000_000_000,
        "market_cap": 280_000_000_000,
    },
    "BBDC4": {
        "current_price": 15.20,
        "eps": 2.18,
        "pe_ratio": 6.97,
        "dividend_yield": 0.0680,
        "free_cash_flow": 22_000_000_000,
        "revenue": 98_000_000_000,
        "market_cap": 155_000_000_000,
    },
    "ITUB4": {
        "current_price": 32.80,
        "eps": 3.95,
        "pe_ratio": 8.30,
        "dividend_yield": 0.0520,
        "free_cash_flow": 35_000_000_000,
        "revenue": 145_000_000_000,
        "market_cap": 310_000_000_000,
    },
    "WEGE3": {
        "current_price": 44.10,
        "eps": 1.42,
        "pe_ratio": 31.06,
        "dividend_yield": 0.0135,
        "free_cash_flow": 4_500_000_000,
        "revenue": 28_000_000_000,
        "market_cap": 92_000_000_000,
    },
}


@pytest.fixture
def mock_brapi_fundamentals():
    """Return a function that provides mock BRAPI fundamentals for a ticker."""

    def _get(ticker: str) -> dict:
        if ticker in _MOCK_FUNDAMENTALS:
            return _MOCK_FUNDAMENTALS[ticker]
        # Fallback for unknown tickers
        return {
            "current_price": 10.00,
            "eps": 1.00,
            "pe_ratio": 10.0,
            "dividend_yield": 0.05,
            "free_cash_flow": 1_000_000_000,
            "revenue": 5_000_000_000,
            "market_cap": 10_000_000_000,
        }

    return _get


@pytest.fixture
def mock_analysis_job():
    """Return a function that creates mock AnalysisJob constructor kwargs."""

    def _make(
        tenant_id: str,
        ticker: str,
        analysis_type: str = "dcf",
    ) -> dict:
        from app.modules.analysis.versioning import build_data_version_id

        return {
            "id": str(uuid.uuid4()),
            "tenant_id": tenant_id,
            "analysis_type": analysis_type,
            "ticker": ticker,
            "data_timestamp": datetime.now(tz=timezone.utc),
            "data_version_id": build_data_version_id(),
            "data_sources": '[{"source": "BRAPI", "type": "fundamentals", "freshness": "1d"}]',
            "status": "pending",
            "result_json": None,
            "error_message": None,
            "retry_count": 0,
        }

    return _make
