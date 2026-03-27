"""Integration tests for GET /dashboard/summary.

Wave 0: Test stubs — all tests currently FAIL (404) because dashboard module
does not exist yet. Plan 03-02 implements the module and makes these green.

Follows the exact pattern of test_portfolio_api.py:
  - Uses register_verify_and_login() helper from conftest
  - Overrides _get_redis from dashboard.router in conftest client fixture
  - Uses fakeredis.aioredis.FakeRedis() for Redis isolation

RLS isolation: all queries are scoped to the tenant via get_authed_db.
Monetary values in responses are strings (Pydantic v2 Decimal -> str).
"""
import pytest
import pytest_asyncio
from decimal import Decimal
from httpx import AsyncClient

from tests.conftest import register_verify_and_login


pytestmark = pytest.mark.asyncio


async def _seed_transaction(client: AsyncClient, ticker: str = "VALE3") -> None:
    """Helper: create a buy transaction so the portfolio is non-empty."""
    await client.post("/portfolio/transactions", json={
        "ticker": ticker,
        "asset_class": "acao",
        "transaction_type": "buy",
        "transaction_date": "2025-01-15",
        "quantity": "100",
        "unit_price": "65.50",
    })


async def test_dashboard_requires_auth(client: AsyncClient) -> None:
    """GET /dashboard/summary returns 401 when no auth cookie present."""
    resp = await client.get("/dashboard/summary")
    assert resp.status_code == 401


async def test_dashboard_summary_empty_portfolio(
    client: AsyncClient, email_stub
) -> None:
    """GET /dashboard/summary returns valid response for user with no transactions."""
    await register_verify_and_login(client, email_stub)
    resp = await client.get("/dashboard/summary")
    assert resp.status_code == 200
    data = resp.json()
    assert "net_worth" in data
    assert "total_invested" in data
    assert "total_return" in data
    assert "total_return_pct" in data
    assert "daily_pnl" in data
    assert "daily_pnl_pct" in data
    assert "data_stale" in data
    assert "asset_allocation" in data
    assert "portfolio_timeseries" in data
    assert "recent_transactions" in data


async def test_dashboard_summary_returns_allocation(
    client: AsyncClient, email_stub
) -> None:
    """GET /dashboard/summary returns asset_allocation grouped by asset_class (not raw tickers)."""
    await register_verify_and_login(client, email_stub)
    await _seed_transaction(client, "VALE3")
    await _seed_transaction(client, "PETR4")

    resp = await client.get("/dashboard/summary")
    assert resp.status_code == 200
    data = resp.json()

    allocation = data["asset_allocation"]
    assert isinstance(allocation, list)
    # Each item has asset_class, value, pct — no ticker field
    for item in allocation:
        assert "asset_class" in item
        assert "value" in item
        assert "pct" in item
        assert "ticker" not in item  # Must be grouped by class, not per ticker
    # With 2 acao transactions, there should be exactly 1 acao entry
    asset_classes = [item["asset_class"] for item in allocation]
    assert asset_classes.count("acao") == 1


async def test_pnl_fields_present(
    client: AsyncClient, email_stub
) -> None:
    """total_return and daily_pnl are present and are string-encoded Decimals."""
    await register_verify_and_login(client, email_stub)
    await _seed_transaction(client)

    resp = await client.get("/dashboard/summary")
    assert resp.status_code == 200
    data = resp.json()

    # Monetary fields must be strings (Pydantic v2 Decimal -> str)
    assert isinstance(data["net_worth"], str)
    assert isinstance(data["total_return"], str)
    assert isinstance(data["daily_pnl"], str)
    # Must be parseable as Decimal
    from decimal import Decimal
    Decimal(data["net_worth"])
    Decimal(data["total_return"])
    Decimal(data["daily_pnl"])


async def test_data_stale_on_cache_miss(
    client: AsyncClient, email_stub
) -> None:
    """data_stale=true when Redis has no cached prices (fakeredis is empty by default)."""
    await register_verify_and_login(client, email_stub)
    await _seed_transaction(client)

    resp = await client.get("/dashboard/summary")
    assert resp.status_code == 200
    data = resp.json()
    # fakeredis starts empty — no prices cached — must be stale
    assert data["data_stale"] is True


async def test_timeseries_nonempty(
    client: AsyncClient, email_stub
) -> None:
    """portfolio_timeseries returns at least one point for user with transactions."""
    await register_verify_and_login(client, email_stub)
    await _seed_transaction(client)

    resp = await client.get("/dashboard/summary")
    assert resp.status_code == 200
    data = resp.json()
    ts = data["portfolio_timeseries"]
    assert isinstance(ts, list)
    assert len(ts) >= 1
    # Each point has date and value
    for point in ts:
        assert "date" in point
        assert "value" in point
        assert isinstance(point["value"], str)


async def test_recent_transactions_limit(
    client: AsyncClient, email_stub
) -> None:
    """recent_transactions returns at most 10 items."""
    await register_verify_and_login(client, email_stub)
    # Seed 12 transactions
    tickers = ["VALE3", "PETR4", "ITUB4", "BBDC4", "ABEV3",
               "WEGE3", "RENT3", "LREN3", "MGLU3", "BRFS3", "CPLE6", "SBSP3"]
    for ticker in tickers:
        await _seed_transaction(client, ticker)

    resp = await client.get("/dashboard/summary")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["recent_transactions"]) <= 10
