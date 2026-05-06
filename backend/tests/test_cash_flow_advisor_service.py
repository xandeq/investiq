"""Tests for CashParkingService ranking logic."""

from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal
from types import SimpleNamespace

import pytest

from app.modules.cash_flow_advisor.schemas import CashFlowProjection, NextBigOutflow
from app.modules.cash_flow_advisor.service import CashParkingService


def _tax_rows():
    return [
        SimpleNamespace(
            asset_class="renda_fixa",
            holding_days_min=0,
            holding_days_max=180,
            rate_percent=Decimal("22.50"),
            is_exempt=False,
        ),
        SimpleNamespace(
            asset_class="renda_fixa",
            holding_days_min=181,
            holding_days_max=360,
            rate_percent=Decimal("20.00"),
            is_exempt=False,
        ),
    ]


@pytest.mark.asyncio
async def test_rank_options_returns_empty_when_available_cash_is_too_low() -> None:
    projection = CashFlowProjection(
        current_balance=Decimal("500.00"),
        available_to_invest=Decimal("500.00"),
        next_big_outflow=None,
        daily_projection=[],
    )

    result = await CashParkingService(
        cdi_annual_pct=Decimal("10.00"),
        selic_annual_pct=Decimal("10.50"),
        tax_config_rows=_tax_rows(),
    ).rank_options(projection, today=date(2026, 5, 6))

    assert result.amount == Decimal("500.00")
    assert result.rows == []
    assert "abaixo do minimo" in result.warnings[0]


@pytest.mark.asyncio
async def test_rank_options_uses_next_big_outflow_as_holding_window_and_ranks_net_return() -> None:
    today = date(2026, 5, 6)
    projection = CashFlowProjection(
        current_balance=Decimal("25000.00"),
        available_to_invest=Decimal("17000.00"),
        next_big_outflow=NextBigOutflow(
            date=today + timedelta(days=17),
            amount=Decimal("8000.00"),
            description="Cartao",
        ),
        daily_projection=[],
    )

    result = await CashParkingService(
        cdi_annual_pct=Decimal("10.00"),
        selic_annual_pct=Decimal("10.50"),
        tax_config_rows=_tax_rows(),
    ).rank_options(projection, today=today)

    assert result.amount == Decimal("17000.00")
    assert result.holding_days == 17
    assert len(result.rows) == 6
    assert [row.rank for row in result.rows] == [1, 2, 3, 4, 5, 6]
    assert result.rows[0].net_pct >= result.rows[-1].net_pct
    assert any(row.label == "CDB DI 110% CDI" for row in result.rows)
    poupanca = next(row for row in result.rows if row.label == "Poupanca")
    assert poupanca.ir_pct == Decimal("0.00")
    assert poupanca.iof_pct == Decimal("0.00")


@pytest.mark.asyncio
async def test_rank_options_caps_long_holding_window_at_90_days() -> None:
    today = date(2026, 5, 6)
    projection = CashFlowProjection(
        current_balance=Decimal("25000.00"),
        available_to_invest=Decimal("17000.00"),
        next_big_outflow=NextBigOutflow(
            date=today + timedelta(days=180),
            amount=Decimal("8000.00"),
            description="Compra planejada",
        ),
        daily_projection=[],
    )

    result = await CashParkingService(
        cdi_annual_pct=Decimal("10.00"),
        selic_annual_pct=Decimal("10.50"),
        tax_config_rows=_tax_rows(),
    ).rank_options(projection, today=today)

    assert result.holding_days == 90
    assert any("limitada a 90 dias" in warning for warning in result.warnings)
