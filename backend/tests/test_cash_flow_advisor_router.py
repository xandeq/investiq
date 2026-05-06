"""Tests for GET /advisor/cash-parking."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from types import SimpleNamespace
import uuid

import pytest
from httpx import AsyncClient

from app.modules.cash_flow_advisor.schemas import CashFlowProjection, NextBigOutflow
from tests.conftest import register_verify_and_login


@pytest.mark.asyncio
async def test_cash_parking_requires_auth(client: AsyncClient) -> None:
    resp = await client.get("/advisor/cash-parking")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_cash_parking_returns_503_when_diax_unconfigured(
    client: AsyncClient,
    email_stub,
    monkeypatch,
) -> None:
    await register_verify_and_login(client, email_stub, email="cash_unconfigured@example.com")
    monkeypatch.setattr("app.modules.cash_flow_advisor.client.settings.DIAX_BASE_URL", "")
    monkeypatch.setattr("app.modules.cash_flow_advisor.client.settings.DIAX_INTEGRATION_KEY", "")
    monkeypatch.setattr("app.modules.cash_flow_advisor.router._get_cdi_annual", lambda: Decimal("10.00"))
    monkeypatch.setattr("app.modules.cash_flow_advisor.router._get_selic_annual", lambda: Decimal("10.50"))

    resp = await client.get("/advisor/cash-parking")

    assert resp.status_code == 503
    assert "DIAX" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_cash_parking_happy_path(
    client: AsyncClient,
    db_session,
    email_stub,
    monkeypatch,
) -> None:
    from app.modules.market_universe.models import TaxConfig

    await register_verify_and_login(client, email_stub, email="cash_ok@example.com")
    db_session.add(
        TaxConfig(
            id=str(uuid.uuid4()),
            asset_class="renda_fixa",
            holding_days_min=0,
            holding_days_max=180,
            rate_percent=Decimal("22.50"),
            is_exempt=False,
            label="RF ate 180 dias",
        )
    )
    await db_session.commit()

    projection = CashFlowProjection(
        current_balance=Decimal("25000.00"),
        available_to_invest=Decimal("17000.00"),
        next_big_outflow=NextBigOutflow(
            date=date.today().replace(day=min(date.today().day + 10, 28)),
            amount=Decimal("8000.00"),
            description="Cartao",
        ),
        daily_projection=[],
    )

    class StubDiaxClient:
        def __init__(self, *args, **kwargs) -> None:
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb) -> None:
            pass

        async def get_cash_flow_projection(self):
            return projection

    monkeypatch.setattr("app.modules.cash_flow_advisor.router.DiaxClient", StubDiaxClient)
    monkeypatch.setattr("app.modules.cash_flow_advisor.router._get_cdi_annual", lambda: Decimal("10.00"))
    monkeypatch.setattr("app.modules.cash_flow_advisor.router._get_selic_annual", lambda: Decimal("10.50"))

    resp = await client.get("/advisor/cash-parking")

    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["amount"] == "17000.00"
    assert len(data["rows"]) == 6
    assert data["rows"][0]["rank"] == 1
    assert data["rows"][0]["net_pct"] >= data["rows"][-1]["net_pct"]
