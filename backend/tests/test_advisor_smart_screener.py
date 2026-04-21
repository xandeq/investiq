"""Tests for GET /advisor/screener endpoint (Phase 25 — ADVI-03).

3 test cases:
  1. Auth guard — unauthenticated returns 401
  2. Empty portfolio — all screener assets are complementary
  3. Sector filtering — portfolio sectors are excluded from results
"""
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
async def test_screener_requires_auth(client: AsyncClient):
    """Unauthenticated request to /advisor/screener returns 401."""
    resp = await client.get("/advisor/screener")
    assert resp.status_code == 401


# ---------------------------------------------------------------------------
# Authenticated tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_screener_empty_portfolio(client: AsyncClient, db_session, email_stub):
    """With no transactions, returns all screener tickers (full universe is complementary).

    Since the user has no portfolio, all sectors are 'missing' — so all tickers
    from the latest screener snapshot should be returned.
    """
    from app.modules.market_universe.models import ScreenerSnapshot

    await register_verify_and_login(
        client, email_stub, email="screener_empty@example.com"
    )

    # Insert screener snapshots in two sectors
    snap1 = ScreenerSnapshot(
        id=str(uuid.uuid4()),
        ticker="PETR4",
        snapshot_date=date(2026, 4, 18),
        short_name="Petrobras",
        sector="Energia",
        regular_market_price=Decimal("38.50"),
        market_cap=450_000_000_000,
        dy=Decimal("0.12"),
        pl=Decimal("5.2"),
        variacao_12m_pct=Decimal("0.10"),
    )
    snap2 = ScreenerSnapshot(
        id=str(uuid.uuid4()),
        ticker="MGLU3",
        snapshot_date=date(2026, 4, 18),
        short_name="Magazine Luiza",
        sector="Varejo",
        regular_market_price=Decimal("10.50"),
        market_cap=5_000_000_000,
        dy=Decimal("0.02"),
        pl=Decimal("8.5"),
        variacao_12m_pct=Decimal("-0.05"),
    )
    db_session.add_all([snap1, snap2])
    await db_session.commit()

    resp = await client.get("/advisor/screener")
    assert resp.status_code == 200

    data = resp.json()
    assert isinstance(data, list)
    # With no portfolio, all tickers in latest snapshot should appear
    tickers = {row["ticker"] for row in data}
    assert "PETR4" in tickers
    assert "MGLU3" in tickers

    # Each row must have required fields
    for row in data:
        assert "ticker" in row
        assert "sector" in row
        assert "dy_12m_pct" in row
        assert "variacao_12m_pct" in row
        assert "preco_atual" in row
        assert "relevance_score" in row


@pytest.mark.asyncio
async def test_screener_filters_by_missing_sectors(
    client: AsyncClient, db_session, email_stub
):
    """Portfolio sectors are excluded from screener results.

    Setup:
    - User buys MGLU3 (Varejo) and VALE3 (Mineração)
    - Screener has MGLU3 (Varejo), VALE3 (Mineração), PETR4 (Energia), RENT3 (Mobilidade)
    - Expected: only PETR4 and RENT3 returned (Energia and Mobilidade are not in portfolio)
    - MGLU3 and VALE3 must NOT appear (sectors already held)
    """
    from app.modules.market_universe.models import ScreenerSnapshot
    from app.modules.portfolio.models import Transaction

    user_id = await register_verify_and_login(
        client, email_stub, email="screener_filter@example.com"
    )

    snap_date = date(2026, 4, 18)

    # Insert 4 screener snapshots
    snaps = [
        ScreenerSnapshot(
            id=str(uuid.uuid4()), ticker="MGLU3", snapshot_date=snap_date,
            short_name="Magazine Luiza", sector="Varejo",
            regular_market_price=Decimal("10.50"), market_cap=5_000_000_000,
            dy=Decimal("0.02"), pl=Decimal("8.5"), variacao_12m_pct=Decimal("-0.05"),
        ),
        ScreenerSnapshot(
            id=str(uuid.uuid4()), ticker="VALE3", snapshot_date=snap_date,
            short_name="Vale", sector="Mineração",
            regular_market_price=Decimal("70.00"), market_cap=300_000_000_000,
            dy=Decimal("0.15"), pl=Decimal("4.0"), variacao_12m_pct=Decimal("0.08"),
        ),
        ScreenerSnapshot(
            id=str(uuid.uuid4()), ticker="PETR4", snapshot_date=snap_date,
            short_name="Petrobras", sector="Energia",
            regular_market_price=Decimal("38.50"), market_cap=450_000_000_000,
            dy=Decimal("0.20"), pl=Decimal("5.2"), variacao_12m_pct=Decimal("0.10"),
        ),
        ScreenerSnapshot(
            id=str(uuid.uuid4()), ticker="RENT3", snapshot_date=snap_date,
            short_name="Localiza", sector="Mobilidade",
            regular_market_price=Decimal("55.00"), market_cap=50_000_000_000,
            dy=Decimal("0.01"), pl=Decimal("12.0"), variacao_12m_pct=Decimal("0.05"),
        ),
    ]
    db_session.add_all(snaps)
    await db_session.commit()

    # Buy MGLU3 (Varejo) and VALE3 (Mineração)
    transactions = [
        Transaction(
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
        ),
        Transaction(
            id=str(uuid.uuid4()),
            tenant_id=user_id,
            portfolio_id=user_id,
            ticker="VALE3",
            transaction_type="buy",
            transaction_date=date(2026, 4, 1),
            quantity=Decimal("50"),
            unit_price=Decimal("70.00"),
            total_value=Decimal("3500.00"),
            asset_class="acao",
        ),
    ]
    db_session.add_all(transactions)
    await db_session.commit()

    resp = await client.get("/advisor/screener")
    assert resp.status_code == 200

    data = resp.json()
    assert isinstance(data, list)

    returned_tickers = {row["ticker"] for row in data}

    # PETR4 and RENT3 should be present (complementary sectors)
    assert "PETR4" in returned_tickers, f"PETR4 missing from results: {returned_tickers}"
    assert "RENT3" in returned_tickers, f"RENT3 missing from results: {returned_tickers}"

    # MGLU3 and VALE3 must NOT appear (sectors already in portfolio)
    assert "MGLU3" not in returned_tickers, "MGLU3 (Varejo) should be filtered out"
    assert "VALE3" not in returned_tickers, "VALE3 (Mineração) should be filtered out"
