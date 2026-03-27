"""Tests for market data adapters — brapi.py, bcb.py, yfinance_adapter.py.

RED phase tests: written before implementation.
"""
from __future__ import annotations

import json
from decimal import Decimal
from unittest.mock import MagicMock, patch

import pytest


# ---------------------------------------------------------------------------
# BrapiClient tests
# ---------------------------------------------------------------------------

def test_brapi_client_fetch_quotes_returns_list():
    """BrapiClient.fetch_quotes returns list with required keys."""
    from app.modules.market_data.adapters.brapi import BrapiClient

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "results": [
            {
                "symbol": "PETR4",
                "regularMarketPrice": 38.50,
                "regularMarketChange": 0.50,
                "regularMarketChangePercent": 1.32,
            }
        ]
    }
    mock_resp.raise_for_status = MagicMock()

    with patch("requests.get", return_value=mock_resp):
        client = BrapiClient(token="test-token")
        result = client.fetch_quotes(["PETR4"])

    assert isinstance(result, list)
    assert len(result) == 1
    q = result[0]
    assert q["symbol"] == "PETR4"
    assert "regularMarketPrice" in q
    assert "regularMarketChange" in q
    assert "regularMarketChangePercent" in q


def test_brapi_client_fetch_fundamentals_returns_dict():
    """BrapiClient.fetch_fundamentals returns dict with pl, pvp, dy, ev_ebitda."""
    from app.modules.market_data.adapters.brapi import BrapiClient

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "results": [
            {
                "symbol": "PETR4",
                "defaultKeyStatistics": {
                    "priceToBook": {"raw": 1.2},
                    "trailingEps": {"raw": 5.0},
                    "forwardPE": {"raw": 7.5},
                    "enterpriseToEbitda": {"raw": 4.2},
                },
                "financialData": {
                    "dividendYield": {"raw": 0.085},
                },
            }
        ]
    }
    mock_resp.raise_for_status = MagicMock()

    with patch("requests.get", return_value=mock_resp):
        client = BrapiClient(token="test-token")
        result = client.fetch_fundamentals("PETR4")

    assert isinstance(result, dict)
    assert "pvp" in result
    assert "dy" in result


def test_brapi_client_fetch_historical_returns_ohlcv():
    """BrapiClient.fetch_historical returns list of OHLCV dicts."""
    from app.modules.market_data.adapters.brapi import BrapiClient

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "results": [
            {
                "symbol": "PETR4",
                "historicalDataPrice": [
                    {
                        "date": 1700000000,
                        "open": 38.0,
                        "high": 39.0,
                        "low": 37.0,
                        "close": 38.5,
                        "volume": 1000000,
                    }
                ],
            }
        ]
    }
    mock_resp.raise_for_status = MagicMock()

    with patch("requests.get", return_value=mock_resp):
        client = BrapiClient(token="test-token")
        result = client.fetch_historical("PETR4")

    assert isinstance(result, list)
    assert len(result) == 1
    point = result[0]
    assert "date" in point
    assert "open" in point
    assert "close" in point
    assert "volume" in point


def test_brapi_client_fetch_ibovespa():
    """BrapiClient.fetch_ibovespa returns a quote dict."""
    from app.modules.market_data.adapters.brapi import BrapiClient

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "results": [
            {
                "symbol": "^BVSP",
                "regularMarketPrice": 128000.0,
                "regularMarketChange": 500.0,
                "regularMarketChangePercent": 0.39,
            }
        ]
    }
    mock_resp.raise_for_status = MagicMock()

    with patch("requests.get", return_value=mock_resp):
        client = BrapiClient(token="test-token")
        result = client.fetch_ibovespa()

    assert isinstance(result, dict)
    assert "regularMarketPrice" in result


# ---------------------------------------------------------------------------
# fetch_macro_indicators tests
# ---------------------------------------------------------------------------

def test_fetch_macro_indicators_returns_required_keys():
    """fetch_macro_indicators() returns dict with selic, cdi, ipca, ptax_usd."""
    from app.modules.market_data.adapters.bcb import fetch_macro_indicators
    import pandas as pd

    # Mock bcb.sgs.get and PTAX
    mock_df = pd.DataFrame(
        {"CDI": [0.055], "SELIC": [0.1375], "IPCA": [0.52]},
        index=pd.to_datetime(["2024-01-31"]),
    )
    mock_ptax_df = pd.DataFrame(
        {"cotacaoVenda": [5.25]},
        index=[0],
    )

    with patch("bcb.sgs.get", return_value=mock_df):
        with patch(
            "app.modules.market_data.adapters.bcb._fetch_ptax_usd",
            return_value=Decimal("5.25"),
        ):
            result = fetch_macro_indicators()

    assert "selic" in result
    assert "cdi" in result
    assert "ipca" in result
    assert "ptax_usd" in result
    assert "fetched_at" in result
    assert isinstance(result["cdi"], Decimal)
    assert isinstance(result["selic"], Decimal)


# ---------------------------------------------------------------------------
# Schema tests
# ---------------------------------------------------------------------------

def test_quote_cache_schema():
    """QuoteCache Pydantic model validates correctly."""
    from app.modules.market_data.schemas import QuoteCache
    from datetime import datetime

    q = QuoteCache(
        symbol="PETR4",
        price=Decimal("38.50"),
        change=Decimal("0.50"),
        change_pct=Decimal("1.32"),
        fetched_at=datetime.utcnow(),
    )
    assert q.symbol == "PETR4"
    assert q.data_stale is False


def test_macro_cache_schema():
    """MacroCache Pydantic model validates correctly."""
    from app.modules.market_data.schemas import MacroCache
    from datetime import datetime

    m = MacroCache(
        selic=Decimal("13.75"),
        cdi=Decimal("13.65"),
        ipca=Decimal("4.83"),
        ptax_usd=Decimal("5.25"),
        fetched_at=datetime.utcnow(),
    )
    assert m.data_stale is False


def test_fundamentals_cache_schema():
    """FundamentalsCache allows None fields."""
    from app.modules.market_data.schemas import FundamentalsCache
    from datetime import datetime

    f = FundamentalsCache(
        ticker="PETR4",
        fetched_at=datetime.utcnow(),
    )
    assert f.pl is None
    assert f.data_stale is False


def test_historical_cache_schema():
    """HistoricalCache validates with HistoricalPoint list."""
    from app.modules.market_data.schemas import HistoricalCache, HistoricalPoint
    from datetime import datetime

    h = HistoricalCache(
        ticker="PETR4",
        points=[
            HistoricalPoint(
                date=1700000000,
                open=Decimal("38.0"),
                high=Decimal("39.0"),
                low=Decimal("37.0"),
                close=Decimal("38.5"),
                volume=1000000,
            )
        ],
        fetched_at=datetime.utcnow(),
    )
    assert len(h.points) == 1
    assert h.data_stale is False
