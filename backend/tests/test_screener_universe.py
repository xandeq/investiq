"""Tests for GET /screener/universe endpoint."""
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
async def test_universe_requires_auth(client: AsyncClient):
    """Unauthenticated request returns 401."""
    resp = await client.get("/screener/universe")
    assert resp.status_code == 401


# ---------------------------------------------------------------------------
# Authenticated tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_universe_empty(client: AsyncClient, db_session, email_stub):
    """Empty screener_snapshots returns empty results list."""
    await register_verify_and_login(
        client, email_stub, email="universe_empty@example.com"
    )

    resp = await client.get("/screener/universe")
    assert resp.status_code == 200
    data = resp.json()
    assert "results" in data
    assert data["results"] == []
    assert "disclaimer" in data


@pytest.mark.asyncio
async def test_universe_returns_latest_snapshot(client: AsyncClient, db_session, email_stub):
    """With data, returns rows from the latest snapshot_date only."""
    from app.modules.market_universe.models import ScreenerSnapshot

    await register_verify_and_login(
        client, email_stub, email="universe_latest@example.com"
    )

    # Insert two dates -- only the latest should be returned
    old_row = ScreenerSnapshot(
        id=str(uuid.uuid4()), ticker="OLD3", snapshot_date=date(2026, 4, 10),
        short_name="Old Corp", sector="Financeiro",
        regular_market_price=Decimal("10.00"), market_cap=5_000_000_000,
        dy=Decimal("0.05"), pl=Decimal("12.0"),
    )
    new_row = ScreenerSnapshot(
        id=str(uuid.uuid4()), ticker="NEW4", snapshot_date=date(2026, 4, 11),
        short_name="New Corp", sector="Tecnologia",
        regular_market_price=Decimal("25.50"), market_cap=8_000_000_000,
        dy=Decimal("0.09"), pl=Decimal("15.5"),
        variacao_12m_pct=Decimal("0.123456"),
    )
    db_session.add_all([old_row, new_row])
    await db_session.commit()

    resp = await client.get("/screener/universe")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["results"]) == 1
    row = data["results"][0]
    assert row["ticker"] == "NEW4"
    assert row["short_name"] == "New Corp"
    assert row["sector"] == "Tecnologia"
    assert row["variacao_12m_pct"] is not None
    assert row["dy"] is not None
    assert row["pl"] is not None
    assert row["market_cap"] == 8_000_000_000


@pytest.mark.asyncio
async def test_universe_response_schema(client: AsyncClient, db_session, email_stub):
    """Response row contains exactly the 8 required fields per D-10."""
    from app.modules.market_universe.models import ScreenerSnapshot

    await register_verify_and_login(
        client, email_stub, email="universe_schema@example.com"
    )

    row = ScreenerSnapshot(
        id=str(uuid.uuid4()), ticker="PETR4", snapshot_date=date(2026, 4, 12),
        short_name="Petrobras", sector="Energia",
        regular_market_price=Decimal("38.50"), market_cap=450_000_000_000,
        dy=Decimal("0.12"), pl=Decimal("5.2"),
        variacao_12m_pct=Decimal("-0.045000"),
    )
    db_session.add(row)
    await db_session.commit()

    resp = await client.get("/screener/universe")
    data = resp.json()
    assert len(data["results"]) >= 1
    # Find our specific row
    rows_by_ticker = {r["ticker"]: r for r in data["results"]}
    assert "PETR4" in rows_by_ticker
    row_data = rows_by_ticker["PETR4"]
    expected_keys = {
        "ticker", "short_name", "sector",
        "regular_market_price", "variacao_12m_pct",
        "dy", "pl", "market_cap",
    }
    assert set(row_data.keys()) == expected_keys
