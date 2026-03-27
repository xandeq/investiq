"""Integration-level tests for build_position_from_history.

Tests use simple dataclasses as Transaction/CorporateAction surrogates
(no SQLAlchemy models) — the CMP engine accepts any duck-typed objects.
"""
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal

import pytest

from app.modules.portfolio.cmp import build_position_from_history
from app.modules.portfolio.models import CorporateActionType


# ---------------------------------------------------------------------------
# Lightweight surrogates (duck-typed — no SQLAlchemy dependency)
# ---------------------------------------------------------------------------

@dataclass
class FakeTx:
    """Minimal transaction surrogate for CMP engine tests."""
    ticker: str
    transaction_type: str   # "buy" | "sell"
    transaction_date: date
    quantity: Decimal
    unit_price: Decimal
    brokerage_fee: Decimal | None = None


@dataclass
class FakeCorporateAction:
    """Minimal corporate action surrogate."""
    ticker: str
    action_type: str        # CorporateActionType value
    action_date: date
    factor: Decimal
    issue_price: Decimal | None = None  # bonificacao only


# ---------------------------------------------------------------------------
# Integration tests
# ---------------------------------------------------------------------------

def test_position_after_split_then_sell():
    """Multi-step: Buy 200@10, desdobramento 1:3, sell 150@5.

    After buy: qty=200, cmp=10, total_cost=2000
    After split(factor=3): qty=600, cmp=3.33333, total_cost=2000 (invariant)
    After sell 150@5: qty=450, cmp=3.33333, pnl=(5-3.33333)×150≈250
    """
    transactions = [
        FakeTx("VALE3", "buy", date(2024, 1, 10), Decimal("200"), Decimal("10")),
        FakeTx("VALE3", "sell", date(2024, 3, 1), Decimal("150"), Decimal("5")),
    ]
    corporate_actions = [
        FakeCorporateAction("VALE3", CorporateActionType.desdobramento.value, date(2024, 2, 1), Decimal("3")),
    ]

    pos = build_position_from_history("VALE3", "acao", transactions, corporate_actions)

    assert pos.quantity == Decimal("450")
    expected_cmp = Decimal("10") / Decimal("3")   # ≈ 3.33333...
    assert abs(pos.cmp - expected_cmp) < Decimal("0.01")


def test_multiple_buys_then_grupamento():
    """3 buys followed by reverse split — verify final CMP.

    Buy 100@10 → cmp=10, total_cost=1000
    Buy 200@15 → cmp=(1000+3000)/300 = 13.3333, total_cost=4000
    Buy 100@20 → cmp=(4000+2000)/400 = 15, total_cost=6000
    Grupamento factor=4: qty=100, cmp=60, total_cost=6000 (invariant)
    """
    transactions = [
        FakeTx("BBAS3", "buy", date(2024, 1, 5), Decimal("100"), Decimal("10")),
        FakeTx("BBAS3", "buy", date(2024, 2, 5), Decimal("200"), Decimal("15")),
        FakeTx("BBAS3", "buy", date(2024, 3, 5), Decimal("100"), Decimal("20")),
    ]
    corporate_actions = [
        FakeCorporateAction("BBAS3", CorporateActionType.grupamento.value, date(2024, 4, 1), Decimal("4")),
    ]

    pos = build_position_from_history("BBAS3", "acao", transactions, corporate_actions)

    assert pos.quantity == Decimal("100")
    assert abs(pos.cmp - Decimal("60")) < Decimal("0.01")
    assert abs(pos.total_cost - Decimal("6000")) < Decimal("0.01")


def test_build_position_from_history_ordering():
    """Corporate action on same date as transaction — corporate event applied first.

    Sequence:
    - Buy 100@10 on 2024-01-10
    - On 2024-02-01: desdobramento factor=2 AND a sell of 50 shares
      B3 ex-date rule: split happens first → qty=200, cmp=5
      Then sell 50@8 → qty=150, cmp=5 unchanged

    If ordering were wrong (sell before split), we'd sell from qty=100 and
    the resulting qty would be 150 × 2 = 150 but with wrong CMP.
    """
    transactions = [
        FakeTx("ITUB4", "buy", date(2024, 1, 10), Decimal("100"), Decimal("10")),
        FakeTx("ITUB4", "sell", date(2024, 2, 1), Decimal("50"), Decimal("8")),  # same date as corporate
    ]
    corporate_actions = [
        FakeCorporateAction("ITUB4", CorporateActionType.desdobramento.value, date(2024, 2, 1), Decimal("2")),
    ]

    pos = build_position_from_history("ITUB4", "acao", transactions, corporate_actions)

    # After split: qty=200, cmp=5
    # After sell 50@8: qty=150, cmp=5 (unchanged)
    assert pos.quantity == Decimal("150")
    assert abs(pos.cmp - Decimal("5")) < Decimal("0.01")
