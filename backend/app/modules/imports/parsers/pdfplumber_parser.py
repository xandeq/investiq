"""pdfplumber-based fallback parser for broker PDFs.

Used when correpy returns no results. Attempts to extract transaction tables
using pdfplumber's table detection with SINACOR-optimized settings.

The SINACOR format uses ruled-line tables (both vertical and horizontal lines
are printed), so we use strategy="lines" for both axes.

Returns an empty list if no transaction-like rows are detected — this signals
the cascade to attempt GPT-4o next.

Reference: RESEARCH.md TABLE_SETTINGS section
"""
from __future__ import annotations

import io
import logging
import re
from decimal import Decimal, InvalidOperation
from typing import Any

logger = logging.getLogger(__name__)

# pdfplumber table extraction settings optimized for SINACOR-format PDFs.
# These settings come from empirical testing on XP and Clear notas.
TABLE_SETTINGS = {
    "vertical_strategy": "lines",
    "horizontal_strategy": "lines",
    "intersection_tolerance": 5,
    "snap_tolerance": 3,
    "join_tolerance": 3,
    "edge_min_length": 3,
}


def parse_with_pdfplumber(pdf_bytes: bytes) -> list[dict[str, Any]]:
    """Extract transaction rows from broker PDF using pdfplumber table detection.

    Detects rows containing C/V (Compra/Venda) in the first column, which is
    the SINACOR convention for buy/sell transactions.

    Args:
        pdf_bytes: Raw bytes of the PDF file.

    Returns:
        List of partial transaction dicts (same structure as correpy_parser output).
        Returns empty list if no transaction-like rows detected or on any error.
    """
    try:
        import pdfplumber

        results: list[dict[str, Any]] = []

        with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
            for page_num, page in enumerate(pdf.pages):
                try:
                    tables = page.extract_tables(TABLE_SETTINGS)
                    for table in tables:
                        rows = _extract_transaction_rows(table)
                        results.extend(rows)
                except Exception as page_exc:
                    logger.debug(
                        "pdfplumber: error on page %d: %s", page_num, page_exc
                    )
                    continue

        if results:
            logger.info(
                "pdfplumber: extracted %d transaction rows", len(results)
            )
        else:
            logger.debug(
                "pdfplumber: no transaction rows found — triggering GPT-4o fallback"
            )

        return results

    except Exception as exc:
        logger.debug("pdfplumber: parse failed (%s) — triggering fallback", exc)
        return []


def _extract_transaction_rows(table: list[list]) -> list[dict[str, Any]]:
    """Extract transaction rows from a pdfplumber table.

    SINACOR tables have C/V in the first column (Compra/Venda).
    Row format varies by broker but typically:
        [C/V, market, deadline, ticker, specification, qty, price, total, ...]
    """
    results = []
    if not table:
        return results

    for row in table:
        if not row or len(row) < 4:
            continue

        first_cell = str(row[0] or "").strip().upper()
        if first_cell not in ("C", "V"):
            continue

        # Best-effort extraction — columns vary by broker format
        try:
            txn_type = "buy" if first_cell == "C" else "sell"

            # Try to find ticker: look for B3-format pattern in cells 1-5
            ticker = None
            for cell in row[1:6]:
                cell_str = str(cell or "").strip().upper()
                match = re.search(r'\b([A-Z]{3,5}[0-9]{1,2}F?)\b', cell_str)
                if match:
                    ticker = match.group(1)
                    if ticker.endswith("F") and len(ticker) > 4:
                        ticker = ticker[:-1]
                    break

            if not ticker:
                continue

            # Find quantity and price — look for numeric values in later columns
            quantity = None
            unit_price = None
            for cell in reversed(row):
                cell_str = str(cell or "").strip()
                # Remove thousand separators (Brazilian format: 1.000,00)
                cell_clean = cell_str.replace(".", "").replace(",", ".")
                try:
                    val = Decimal(cell_clean)
                    if val > 0:
                        if unit_price is None and val < Decimal("100000"):
                            unit_price = val
                        elif quantity is None and val == val.to_integral_value():
                            quantity = val
                        if quantity and unit_price:
                            break
                except InvalidOperation:
                    continue

            if not quantity or not unit_price:
                continue

            total_value = quantity * unit_price

            results.append({
                "ticker": ticker,
                "asset_class": "acao",
                "transaction_type": txn_type,
                "transaction_date": None,  # pdfplumber doesn't always capture date per row
                "quantity": quantity,
                "unit_price": unit_price,
                "total_value": total_value,
                "brokerage_fee": Decimal("0"),
                "irrf_withheld": Decimal("0"),
                "parser_source": "pdfplumber",
            })

        except Exception as row_exc:
            logger.debug("pdfplumber: error parsing row %s: %s", row, row_exc)
            continue

    return results
