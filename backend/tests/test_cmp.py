"""Unit tests for the CMP (Custo Médio Ponderado) calculation engine.

Tests follow TDD RED phase: written before implementation exists.
All B3 official examples from CONTEXT.md must pass.

Import will fail with ImportError until cmp.py is created (that is expected RED state).
"""
from decimal import Decimal

import pytest

from app.modules.portfolio.cmp import (
    Position,
    apply_buy,
    apply_sell,
    apply_corporate_event,
    build_position_from_history,
)
from app.modules.portfolio.models import AssetClass, CorporateActionType


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _pos(ticker="PETR4", qty="0", cmp="0", total_cost="0", asset_class="acao") -> Position:
    """Build an empty or seeded Position for test convenience."""
    return Position(
        ticker=ticker,
        quantity=Decimal(qty),
        cmp=Decimal(cmp),
        total_cost=Decimal(total_cost),
        asset_class=asset_class,
    )


def _empty(ticker="PETR4") -> Position:
    return _pos(ticker=ticker)


# ---------------------------------------------------------------------------
# B3 official test cases — must all pass (source: CONTEXT.md)
# ---------------------------------------------------------------------------

def test_cmp_initial_buy():
    """Buy 100@R$10 → CMP=10, qty=100, total_cost=1000."""
    pos = _empty()
    result = apply_buy(pos, Decimal("100"), Decimal("10"))

    assert result.quantity == Decimal("100")
    assert abs(result.cmp - Decimal("10")) < Decimal("0.01")
    assert abs(result.total_cost - Decimal("1000")) < Decimal("0.01")


def test_cmp_buy_sequence():
    """Buy 100@10, then 50@12 → CMP=(100×10+50×12)/150 = 10.6667, qty=150."""
    pos = _empty()
    pos = apply_buy(pos, Decimal("100"), Decimal("10"))
    pos = apply_buy(pos, Decimal("50"), Decimal("12"))

    assert pos.quantity == Decimal("150")
    # CMP = (1000 + 600) / 150 = 10.6666...
    expected_cmp = Decimal("10.66666667")
    assert abs(pos.cmp - expected_cmp) < Decimal("0.01")
    assert abs(pos.total_cost - Decimal("1600")) < Decimal("0.01")


def test_cmp_sell_does_not_change_cmp():
    """Buy 100@10, sell 50@15 → CMP stays 10.0."""
    pos = _empty()
    pos = apply_buy(pos, Decimal("100"), Decimal("10"))
    new_pos, pnl = apply_sell(pos, Decimal("50"), Decimal("15"))

    assert new_pos.quantity == Decimal("50")
    assert abs(new_pos.cmp - Decimal("10")) < Decimal("0.01")


def test_cmp_partial_sell():
    """Buy 100@10, buy 50@12 → CMP=10.6667; sell 80@15 → CMP unchanged, qty=70."""
    pos = _empty()
    pos = apply_buy(pos, Decimal("100"), Decimal("10"))
    pos = apply_buy(pos, Decimal("50"), Decimal("12"))
    new_pos, _ = apply_sell(pos, Decimal("80"), Decimal("15"))

    assert new_pos.quantity == Decimal("70")
    assert abs(new_pos.cmp - Decimal("10.66666667")) < Decimal("0.01")


def test_cmp_sell_pnl():
    """From partial sell scenario: P&L = (15 - 10.6667) × 80 ≈ 346.67."""
    pos = _empty()
    pos = apply_buy(pos, Decimal("100"), Decimal("10"))
    pos = apply_buy(pos, Decimal("50"), Decimal("12"))
    _, pnl = apply_sell(pos, Decimal("80"), Decimal("15"))

    # P&L = (15 - 10.66666...) × 80 = 4.33333... × 80 = 346.666...
    expected_pnl = Decimal("346.67")
    assert abs(pnl - expected_pnl) < Decimal("0.01")


def test_desdobramento_preserves_total_cost():
    """After partial sell (qty=70, cmp=10.6667), apply split factor=2.

    Expected: qty=140, cmp=5.3333, total_cost unchanged (≈746.67).
    """
    pos = _empty()
    pos = apply_buy(pos, Decimal("100"), Decimal("10"))
    pos = apply_buy(pos, Decimal("50"), Decimal("12"))
    pos, _ = apply_sell(pos, Decimal("80"), Decimal("15"))

    # State: qty=70, cmp≈10.6667, total_cost≈746.67
    total_cost_before = pos.total_cost
    result = apply_corporate_event(pos, CorporateActionType.desdobramento.value, Decimal("2"))

    assert result.quantity == Decimal("140")
    assert abs(result.cmp - Decimal("5.33333333")) < Decimal("0.01")
    # total_cost must be invariant (allow small rounding delta)
    assert abs(result.total_cost - total_cost_before) < Decimal("0.01")


def test_grupamento_preserves_total_cost():
    """Buy 100@10, apply reverse split factor=2 → qty=50, cmp=20, total_cost=1000."""
    pos = _empty()
    pos = apply_buy(pos, Decimal("100"), Decimal("10"))
    total_cost_before = pos.total_cost  # 1000

    result = apply_corporate_event(pos, CorporateActionType.grupamento.value, Decimal("2"))

    assert result.quantity == Decimal("50")
    assert abs(result.cmp - Decimal("20")) < Decimal("0.01")
    assert abs(result.total_cost - total_cost_before) < Decimal("0.01")
    assert abs(result.total_cost - Decimal("1000")) < Decimal("0.01")


def test_bonificacao_adjusts_cmp():
    """Buy 100@10 (total_cost=1000), bonificação 10% at issue R$8.

    New shares: 10. New CMP = (100×10 + 10×8) / 110 = 1080/110 ≈ 9.8182.
    New total_cost = 1080.
    """
    pos = _empty()
    pos = apply_buy(pos, Decimal("100"), Decimal("10"))

    result = apply_corporate_event(
        pos,
        CorporateActionType.bonificacao.value,
        Decimal("0.10"),   # 10% bonus rate
        issue_price=Decimal("8"),
    )

    assert result.quantity == Decimal("110")
    expected_cmp = Decimal("9.81818182")
    assert abs(result.cmp - expected_cmp) < Decimal("0.01")
    assert abs(result.total_cost - Decimal("1080")) < Decimal("0.01")


def test_corporate_event_before_sell():
    """Buy 100@10, desdobramento 1:2 (qty=200, cmp=5), sell 100@8 → P&L=(8-5)×100=300."""
    pos = _empty()
    pos = apply_buy(pos, Decimal("100"), Decimal("10"))
    pos = apply_corporate_event(pos, CorporateActionType.desdobramento.value, Decimal("2"))

    assert pos.quantity == Decimal("200")
    assert abs(pos.cmp - Decimal("5")) < Decimal("0.01")

    new_pos, pnl = apply_sell(pos, Decimal("100"), Decimal("8"))
    assert abs(pnl - Decimal("300")) < Decimal("0.01")
    assert new_pos.quantity == Decimal("100")


def test_sell_more_than_held_raises():
    """Buy 10@10, sell 20@15 → raises ValueError."""
    pos = _empty()
    pos = apply_buy(pos, Decimal("10"), Decimal("10"))

    with pytest.raises(ValueError, match="Cannot sell"):
        apply_sell(pos, Decimal("20"), Decimal("15"))


def test_renda_fixa_buy_only():
    """CDB/renda_fixa buy — same CMP formula applies (no sell for RF in v1)."""
    pos = _pos(ticker="CDB-BANCO-X", qty="0", cmp="0", total_cost="0", asset_class="renda_fixa")
    pos = apply_buy(pos, Decimal("1000"), Decimal("1"))  # 1000 cotas @ R$1.00
    pos = apply_buy(pos, Decimal("500"), Decimal("1.05"))  # additional 500 @ R$1.05

    # CMP = (1000×1 + 500×1.05) / 1500 = (1000 + 525) / 1500 = 1525/1500 ≈ 1.01667
    expected_cmp = Decimal("1.01666667")
    assert pos.quantity == Decimal("1500")
    assert abs(pos.cmp - expected_cmp) < Decimal("0.01")
