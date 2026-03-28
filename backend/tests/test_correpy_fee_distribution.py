"""Tests for proportional brokerage fee distribution in correpy_parser.

Verifies that when a nota de corretagem has multiple transactions, the
operational_fee is distributed proportionally by each transaction's
total_value rather than being duplicated on every row.
"""
from __future__ import annotations

from decimal import Decimal
from unittest.mock import MagicMock, patch


def test_brokerage_fee_distributed_proportionally():
    """
    When a nota has multiple transactions, brokerage_fee is distributed
    proportionally by total_value, not duplicated across all transactions.

    Nota total fee: R$30
    Txn1: PETR4, 10 x R$100 = R$1000 (1/3 of total) -> fee R$10
    Txn2: VALE3, 20 x R$100 = R$2000 (2/3 of total) -> fee R$20
    """
    from app.modules.imports.parsers.correpy_parser import parse_with_correpy

    # mock_txn.transaction_type is passed directly to _map_transaction_type
    # which does str(raw_type).upper() — so pass a plain string "C" (Compra)
    mock_txn1 = MagicMock()
    mock_txn1.security.name = "PETR4"
    mock_txn1.transaction_type = "C"
    mock_txn1.quantity = 10
    mock_txn1.unit_price = 100  # total = 1000
    mock_txn1.irrf = 0

    mock_txn2 = MagicMock()
    mock_txn2.security.name = "VALE3"
    mock_txn2.transaction_type = "C"
    mock_txn2.quantity = 20
    mock_txn2.unit_price = 100  # total = 2000
    mock_txn2.irrf = 0

    mock_note = MagicMock()
    mock_note.operational_fee = 30  # R$30 total fee for the entire nota
    mock_note.settlement_date = None
    mock_note.reference_date = None
    mock_note.transactions = [mock_txn1, mock_txn2]

    mock_parser = MagicMock()
    mock_parser.parse_brokerage_note.return_value = [mock_note]

    # ParserFactory is imported lazily inside parse_with_correpy — patch at source
    with patch("correpy.parsers.brokerage_notes.parser_factory.ParserFactory") as mock_factory:
        mock_factory.get_parser.return_value = mock_parser
        results = parse_with_correpy(b"fake pdf bytes")

    assert len(results) == 2

    # Total of all assigned fees must equal the nota's total fee
    total_fees = sum(r["brokerage_fee"] for r in results)
    assert abs(total_fees - Decimal("30")) < Decimal("0.0001"), (
        f"Total fees should sum to ~30, got {total_fees}"
    )

    # Fee should be proportional: txn2 has 2x the value of txn1, so 2x the fee
    fees = sorted(r["brokerage_fee"] for r in results)  # [10, 20]
    ratio = fees[1] / fees[0] if fees[0] > 0 else Decimal("0")
    assert abs(ratio - Decimal("2")) < Decimal("0.001"), (
        f"Fee ratio should be ~2.0 (larger txn gets double fee), got {ratio}"
    )

    # Guard against the original bug: duplicated fees would sum to 60, not 30
    assert total_fees < Decimal("31"), (
        f"Fees are being duplicated (old bug would give 60). Got total: {total_fees}"
    )


def test_brokerage_fee_single_transaction():
    """Single transaction gets 100% of the fee — no distribution needed."""
    from app.modules.imports.parsers.correpy_parser import parse_with_correpy

    mock_txn = MagicMock()
    mock_txn.security.name = "ITUB4"
    mock_txn.transaction_type = "C"
    mock_txn.quantity = 100
    mock_txn.unit_price = 25  # total = 2500
    mock_txn.irrf = 0

    mock_note = MagicMock()
    mock_note.operational_fee = 15
    mock_note.settlement_date = None
    mock_note.reference_date = None
    mock_note.transactions = [mock_txn]

    mock_parser = MagicMock()
    mock_parser.parse_brokerage_note.return_value = [mock_note]

    # ParserFactory is imported lazily inside parse_with_correpy — patch at source
    with patch("correpy.parsers.brokerage_notes.parser_factory.ParserFactory") as mock_factory:
        mock_factory.get_parser.return_value = mock_parser
        results = parse_with_correpy(b"fake pdf bytes")

    assert len(results) == 1
    assert abs(results[0]["brokerage_fee"] - Decimal("15")) < Decimal("0.0001"), (
        f"Single transaction should receive 100% of fee (R$15), got {results[0]['brokerage_fee']}"
    )


def test_brokerage_fee_three_transactions_sum_preserved():
    """
    Three transactions: R$1000, R$2000, R$3000 — total fee R$30.
    Expected: R$5, R$10, R$15 (proportional by 1/6, 2/6, 3/6).
    Sum must equal exactly R$30 (within rounding).
    """
    from app.modules.imports.parsers.correpy_parser import parse_with_correpy

    def _txn(name: str, qty: int, price: int) -> MagicMock:
        m = MagicMock()
        m.security.name = name
        m.transaction_type = "C"
        m.quantity = qty
        m.unit_price = price
        m.irrf = 0
        return m

    mock_note = MagicMock()
    mock_note.operational_fee = 30
    mock_note.settlement_date = None
    mock_note.reference_date = None
    mock_note.transactions = [
        _txn("PETR4", 10, 100),   # total = 1000, expected fee = 5
        _txn("VALE3", 20, 100),   # total = 2000, expected fee = 10
        _txn("ITUB4", 30, 100),   # total = 3000, expected fee = 15
    ]

    mock_parser = MagicMock()
    mock_parser.parse_brokerage_note.return_value = [mock_note]

    # ParserFactory is imported lazily inside parse_with_correpy — patch at source
    with patch("correpy.parsers.brokerage_notes.parser_factory.ParserFactory") as mock_factory:
        mock_factory.get_parser.return_value = mock_parser
        results = parse_with_correpy(b"fake pdf bytes")

    assert len(results) == 3

    total_fees = sum(r["brokerage_fee"] for r in results)
    assert abs(total_fees - Decimal("30")) < Decimal("0.0001"), (
        f"Sum of proportional fees should equal nota total (R$30), got {total_fees}"
    )

    # Sort results by total_value to verify proportions
    sorted_results = sorted(results, key=lambda r: r["total_value"])
    expected_fees = [Decimal("5"), Decimal("10"), Decimal("15")]
    for result, expected in zip(sorted_results, expected_fees):
        assert abs(result["brokerage_fee"] - expected) < Decimal("0.0001"), (
            f"For total_value={result['total_value']}, expected fee={expected}, "
            f"got {result['brokerage_fee']}"
        )


def test_brokerage_fee_zero_values_fallback_equal_split():
    """
    Edge case: all transactions have zero total_value (qty=0 or price=0).
    Fee should be split equally rather than crashing.
    """
    from app.modules.imports.parsers.correpy_parser import parse_with_correpy

    def _zero_txn(name: str) -> MagicMock:
        m = MagicMock()
        m.security.name = name
        m.transaction_type = "C"
        m.quantity = 0  # zero quantity -> total_value = 0
        m.unit_price = 100
        m.irrf = 0
        return m

    mock_note = MagicMock()
    mock_note.operational_fee = 10
    mock_note.settlement_date = None
    mock_note.reference_date = None
    mock_note.transactions = [_zero_txn("PETR4"), _zero_txn("VALE3")]

    mock_parser = MagicMock()
    mock_parser.parse_brokerage_note.return_value = [mock_note]

    # ParserFactory is imported lazily inside parse_with_correpy — patch at source
    with patch("correpy.parsers.brokerage_notes.parser_factory.ParserFactory") as mock_factory:
        mock_factory.get_parser.return_value = mock_parser
        results = parse_with_correpy(b"fake pdf bytes")

    assert len(results) == 2

    # Each transaction should get half of R$10 = R$5
    for r in results:
        assert abs(r["brokerage_fee"] - Decimal("5")) < Decimal("0.0001"), (
            f"Equal split fallback: each of 2 txns should get R$5, got {r['brokerage_fee']}"
        )

    total_fees = sum(r["brokerage_fee"] for r in results)
    assert abs(total_fees - Decimal("10")) < Decimal("0.0001"), (
        f"Total fees should still sum to R$10, got {total_fees}"
    )
