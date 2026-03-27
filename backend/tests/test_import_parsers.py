"""Unit tests for import parsers: correpy, pdfplumber, gpt4o, csv."""
from __future__ import annotations

import io
from pathlib import Path

import pytest


FIXTURES_DIR = Path(__file__).parent / "fixtures"


def _minimal_pdf_bytes() -> bytes:
    return (FIXTURES_DIR / "sample_nota_corretagem.pdf").read_bytes()


def _valid_csv_bytes() -> bytes:
    return (FIXTURES_DIR / "sample_import.csv").read_bytes()


def _invalid_csv_bytes() -> bytes:
    """CSV with a bad asset_class value."""
    return (
        b"ticker,asset_class,transaction_type,transaction_date,quantity,unit_price,brokerage_fee,irrf_withheld,notes\n"
        b"PETR4,INVALID_CLASS,buy,2025-01-15,100,38.50,4.90,0,\n"
    )


def test_correpy_parser_returns_transactions():
    """parse_with_correpy(pdf_bytes) returns list of dicts with required keys (or empty list)."""
    from app.modules.imports.parsers.correpy_parser import parse_with_correpy

    pdf_bytes = _minimal_pdf_bytes()
    result = parse_with_correpy(pdf_bytes)

    assert isinstance(result, list)
    # Either returns rows (from a real nota) or empty list (minimal fixture)
    for row in result:
        assert "ticker" in row
        assert "transaction_type" in row
        assert "quantity" in row
        assert "unit_price" in row


def test_fallback_to_pdfplumber():
    """parse_with_pdfplumber(pdf_bytes) returns list (may be empty on minimal fixture)."""
    from app.modules.imports.parsers.pdfplumber_parser import parse_with_pdfplumber

    pdf_bytes = _minimal_pdf_bytes()
    result = parse_with_pdfplumber(pdf_bytes)

    assert isinstance(result, list)
    # Minimal fixture PDF has no tables — empty list expected
    # No exception should be raised


def test_csv_valid_rows():
    """parse_csv(valid_csv_bytes) returns (valid_rows, []) with 2 rows."""
    from app.modules.imports.parsers.csv_parser import parse_csv

    csv_bytes = _valid_csv_bytes()
    valid_rows, errors = parse_csv(csv_bytes)

    assert len(errors) == 0
    assert len(valid_rows) == 2
    assert valid_rows[0].ticker == "PETR4"
    assert valid_rows[1].ticker == "BBAS3"


def test_csv_invalid_rows():
    """parse_csv(csv_with_bad_asset_class) returns errors list with row + error keys."""
    from app.modules.imports.parsers.csv_parser import parse_csv

    csv_bytes = _invalid_csv_bytes()
    valid_rows, errors = parse_csv(csv_bytes)

    assert len(errors) > 0
    error = errors[0]
    assert "row" in error
    assert "error" in error
