"""Tests for GET /advisor/signals/portfolio and GET /advisor/signals/universe endpoints (Phase 26 — ADVI-04)."""
import uuid
from datetime import date
from decimal import Decimal
from unittest.mock import patch, MagicMock

import pytest
from httpx import AsyncClient

from tests.conftest import register_verify_and_login


# ---------------------------------------------------------------------------
# Test 1: Auth guard — no login returns 401
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_portfolio_signals_requires_auth(client: AsyncClient):
    """Unauthenticated request to /advisor/signals/portfolio returns 401."""
    resp = await client.get("/advisor/signals/portfolio")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_universe_signals_requires_auth(client: AsyncClient):
    """Unauthenticated request to /advisor/signals/universe returns 401."""
    resp = await client.get("/advisor/signals/universe")
    assert resp.status_code == 401


# ---------------------------------------------------------------------------
# Test 2: Empty portfolio — 200 with empty list
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_portfolio_signals_empty_portfolio(client: AsyncClient, db_session, email_stub):
    """With no transactions, GET /advisor/signals/portfolio returns 200 + empty list."""
    await register_verify_and_login(
        client, email_stub, email="signals_empty_portfolio@example.com"
    )

    resp = await client.get("/advisor/signals/portfolio")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    assert data == []


# ---------------------------------------------------------------------------
# Test 3: Portfolio with positions — 200 with list of signals
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_portfolio_signals_with_positions(client: AsyncClient, db_session, email_stub):
    """With buy transactions, GET /advisor/signals/portfolio returns 200 + list of signals.

    Mocks compute_signals to return empty SwingSignalsResponse
    (no Redis/market-data in tests), then verifies the endpoint:
    - Returns 200
    - Returns a list (possibly empty since no Redis market data)
    - Each signal has required fields if present
    """
    from app.modules.portfolio.models import Transaction

    user_id = await register_verify_and_login(
        client, email_stub, email="signals_with_positions@example.com"
    )

    # Create 2 buy transactions (portfolio_id required — use user_id as portfolio ID)
    tx1 = Transaction(
        id=str(uuid.uuid4()),
        tenant_id=user_id,
        portfolio_id=user_id,
        ticker="MGLU3",
        transaction_type="buy",
        transaction_date=date(2026, 1, 10),
        quantity=Decimal("100"),
        unit_price=Decimal("15.00"),
        total_value=Decimal("1500.00"),
        asset_class="acao",
    )
    tx2 = Transaction(
        id=str(uuid.uuid4()),
        tenant_id=user_id,
        portfolio_id=user_id,
        ticker="VALE3",
        transaction_type="buy",
        transaction_date=date(2026, 1, 15),
        quantity=Decimal("50"),
        unit_price=Decimal("70.00"),
        total_value=Decimal("3500.00"),
        asset_class="acao",
    )
    db_session.add_all([tx1, tx2])
    await db_session.commit()

    # Mock compute_signals so tests don't need Redis + market data
    from app.modules.swing_trade.schemas import SwingSignalsResponse
    from datetime import datetime, timezone

    mock_response = SwingSignalsResponse(
        portfolio_signals=[],
        radar_signals=[],
        generated_at=datetime.now(timezone.utc),
    )

    with patch(
        "app.modules.advisor.service.compute_signals",
        return_value=mock_response,
    ):
        resp = await client.get("/advisor/signals/portfolio")

    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    # With mocked compute_signals returning empty signals, result is empty list
    # Each signal in list must have required fields
    for signal in data:
        assert "ticker" in signal
        assert "suggested_amount_brl" in signal
        assert "target_upside_pct" in signal
        assert "timeframe_days" in signal
        assert "stop_loss_pct" in signal
        assert "generated_at" in signal


# ---------------------------------------------------------------------------
# Test 4: Universe signals endpoint — 200 + empty list when cache is empty
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_universe_signals_endpoint(client: AsyncClient, db_session, email_stub):
    """GET /advisor/signals/universe returns 200 + empty list when Redis cache is empty.

    The universe signals are populated by a nightly Celery batch task.
    In tests, Redis cache is empty, so endpoint returns [].
    """
    await register_verify_and_login(
        client, email_stub, email="signals_universe_empty@example.com"
    )

    resp = await client.get("/advisor/signals/universe")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    # Cache is empty in tests — returns empty list
    assert data == []
