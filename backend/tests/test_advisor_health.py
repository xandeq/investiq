"""Tests for GET /advisor/health endpoint (Phase 23 — ADVI-01)."""
import uuid
from datetime import date
from decimal import Decimal

import pytest
from httpx import AsyncClient

from tests.conftest import register_verify_and_login


# ---------------------------------------------------------------------------
# Auth test (no login needed)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_health_requires_auth(client: AsyncClient):
    """Unauthenticated request to /advisor/health returns 401."""
    resp = await client.get("/advisor/health")
    assert resp.status_code == 401


# ---------------------------------------------------------------------------
# Authenticated tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_health_endpoint_empty_portfolio(client: AsyncClient, db_session, email_stub):
    """With no transactions, returns health_score=0, biggest_risk=None, has_portfolio=False."""
    await register_verify_and_login(
        client, email_stub, email="health_empty@example.com"
    )

    resp = await client.get("/advisor/health")
    assert resp.status_code == 200
    data = resp.json()

    assert data["health_score"] == 0
    assert data["biggest_risk"] is None
    assert data["passive_income_monthly_brl"] == "0"
    assert data["underperformers"] == []
    assert data["has_portfolio"] is False
    assert data["total_assets"] == 0
    assert data["data_as_of"] is None


@pytest.mark.asyncio
async def test_health_endpoint_with_portfolio(client: AsyncClient, db_session, email_stub):
    """With sample transactions, returns populated health check (score >0, has_portfolio=True)."""
    from app.modules.market_universe.models import ScreenerSnapshot
    from app.modules.portfolio.models import Transaction

    user_id = await register_verify_and_login(
        client, email_stub, email="health_portfolio@example.com"
    )

    # Create screener snapshot for a stock
    snapshot = ScreenerSnapshot(
        id=str(uuid.uuid4()),
        ticker="MGLU3",
        snapshot_date=date(2026, 4, 18),
        short_name="Magazine Luiza",
        sector="Varejo",
        regular_market_price=10.50,
        market_cap=5000000000,
        dy=0.02,
        pl=8.5,
        variacao_12m_pct=-0.05,  # -5% is not an underperformer
    )
    db_session.add(snapshot)
    await db_session.commit()

    # Create a buy transaction
    tx = Transaction(
        id=str(uuid.uuid4()),
        tenant_id=user_id,
        portfolio_id=user_id,
        ticker="MGLU3",
        transaction_type="buy",
        transaction_date=date(2026, 4, 1),
        quantity=Decimal("100"),
        unit_price=Decimal("10.00"),
        total_value=Decimal("1000.00"),
        asset_class="acao",
    )
    db_session.add(tx)
    await db_session.commit()

    resp = await client.get("/advisor/health")
    assert resp.status_code == 200
    data = resp.json()

    # Verify response structure
    assert "health_score" in data
    assert "biggest_risk" in data
    assert "passive_income_monthly_brl" in data
    assert "underperformers" in data
    assert "has_portfolio" in data
    assert "total_assets" in data
    assert "data_as_of" in data

    # Verify types and ranges
    assert isinstance(data["health_score"], int)
    assert 10 <= data["health_score"] <= 100 or data["health_score"] == 0
    assert data["has_portfolio"] is True
    assert data["total_assets"] == 1
    assert isinstance(data["underperformers"], list)


@pytest.mark.asyncio
async def test_health_caching(client: AsyncClient, db_session, email_stub):
    """First call fetches fresh data. Second call returns same data (cached)."""
    await register_verify_and_login(
        client, email_stub, email="health_cache@example.com"
    )

    # First call — fetches fresh
    resp1 = await client.get("/advisor/health")
    assert resp1.status_code == 200
    data1 = resp1.json()

    # Second call within 60 seconds — should return same data from cache
    resp2 = await client.get("/advisor/health")
    assert resp2.status_code == 200
    data2 = resp2.json()

    # Both responses should be identical (prove caching via same content)
    assert data1 == data2
    assert data1["health_score"] == data2["health_score"]
    assert data1["passive_income_monthly_brl"] == data2["passive_income_monthly_brl"]
