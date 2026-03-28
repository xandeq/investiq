"""correpy-based parser for Brazilian broker nota de corretagem PDFs.

correpy supports XP, Clear, Rico, BTG, Modal, and other SINACOR-format brokers.
It is the primary parser in the cascade — if it returns non-empty results,
pdfplumber and GPT-4o fallbacks are skipped.

Pitfalls:
- ALWAYS pass password="" (empty string), NOT None. Passing None causes
  AttributeError on some PDF versions where correpy tries bytes.decode(password).
- Some SINACOR PDFs have empty nota tables (zero transactions for the period).
  parse_with_correpy returns [] in this case — triggers fallback.
- correpy ticker names are raw SINACOR security names (e.g. "PETROBRAS PN N2 ED").
  _normalize_ticker() strips suffixes and extracts B3-format ticker symbols.

Reference: https://github.com/igorbenav/correpy
"""
from __future__ import annotations

import io
import logging
import re
from decimal import Decimal
from typing import Any

logger = logging.getLogger(__name__)


def _normalize_ticker(name: str) -> str:
    """Extract B3-format ticker from raw SINACOR security name.

    SINACOR names look like:
    - "PETROBRAS PN N2 ED" -> PETR4
    - "VALE ON NM" -> VALE3
    - "ITAUSA PN N1" -> ITSA4
    - "FII XPML11" -> XPML11
    - "PETR4F" -> PETR4 (fracionário suffix)

    Strategy:
    1. Try regex to find B3-format ticker (3-5 letters + 1-2 digits + optional F)
    2. If no match, take first word uppercased, truncated to 6 chars
    """
    if not name:
        return "UNKNOWN"

    upper = name.upper().strip()

    # Remove common SINACOR suffixes that follow the ticker
    # These are category descriptors, not part of the ticker
    suffixes_to_strip = [
        " PN N2", " ON NM", " UNT N2", " DRN", " N1", " N2", " NM",
        " ED", " PN", " ON", " UNT", " CI",
    ]
    for suffix in suffixes_to_strip:
        if suffix in upper:
            upper = upper.replace(suffix, "")

    upper = upper.strip()

    # Try to find B3-format ticker: 3-5 uppercase letters + 1-2 digits + optional F
    match = re.search(r'\b([A-Z]{3,5}[0-9]{1,2}F?)\b', upper)
    if match:
        ticker = match.group(1)
        # Remove trailing F (fracionário) — same underlying asset
        if ticker.endswith("F") and len(ticker) > 4:
            ticker = ticker[:-1]
        return ticker

    # Fallback: first word, max 6 chars
    first_word = upper.split()[0] if upper.split() else upper
    return first_word[:6]


def parse_with_correpy(pdf_bytes: bytes) -> list[dict[str, Any]]:
    """Parse a broker nota de corretagem PDF using the correpy library.

    Attempts to parse the PDF as a SINACOR-format nota de corretagem.
    Returns an empty list if parsing fails for any reason — this signals
    the cascade to attempt pdfplumber next.

    Args:
        pdf_bytes: Raw bytes of the PDF file.

    Returns:
        List of transaction dicts, each containing:
        - ticker: str (normalized B3 format, e.g. "PETR4")
        - asset_class: str (always "acao" — correpy handles equity notas)
        - transaction_type: str ("buy" or "sell")
        - transaction_date: date
        - quantity: Decimal
        - unit_price: Decimal
        - total_value: Decimal
        - brokerage_fee: Decimal
        - irrf_withheld: Decimal
        - parser_source: "correpy"

        Empty list signals fallback to pdfplumber.
    """
    try:
        from correpy.parsers.brokerage_notes.parser_factory import ParserFactory

        file_obj = io.BytesIO(pdf_bytes)
        # CRITICAL: always pass password="" (not None) — see module docstring
        parser = ParserFactory.get_parser(file_obj, password="")

        if parser is None:
            logger.debug("correpy: no parser found for this PDF format")
            return []

        brokerage_notes = parser.parse_brokerage_note()
        if not brokerage_notes:
            logger.debug("correpy: parsed 0 brokerage notes from PDF")
            return []

        results: list[dict[str, Any]] = []
        for note in brokerage_notes:
            # note.operational_fee is the brokerage fee for the entire nota.
            # Distribute it proportionally by each transaction's total_value so
            # that the sum of all assigned fees equals the nota's total fee.
            total_fee = Decimal(str(note.operational_fee or 0))
            reference_date = note.settlement_date or note.reference_date

            # First pass: build transaction data with computed total_value
            txn_data: list[dict[str, Any]] = []
            for txn in note.transactions:
                try:
                    ticker = _normalize_ticker(txn.security.name if txn.security else "")
                    txn_type = _map_transaction_type(txn.transaction_type)
                    quantity = Decimal(str(txn.quantity or 0))
                    unit_price = Decimal(str(txn.unit_price or 0))
                    total_value = quantity * unit_price
                    irrf = Decimal(str(txn.irrf or 0))
                    txn_data.append({
                        "ticker": ticker,
                        "txn_type": txn_type,
                        "quantity": quantity,
                        "unit_price": unit_price,
                        "total_value": total_value,
                        "irrf": irrf,
                    })
                except Exception as txn_exc:
                    logger.warning("correpy: error processing transaction: %s", txn_exc)
                    continue

            # Calculate sum of total_values for proportional distribution
            sum_total_value = sum(d["total_value"] for d in txn_data)

            # Second pass: assign proportional fee and build result dicts
            n = len(txn_data)
            for d in txn_data:
                if sum_total_value > 0:
                    proportional_fee = (
                        total_fee * d["total_value"] / sum_total_value
                    ).quantize(Decimal("0.00000001"))
                else:
                    # Fallback: split equally when all total_values are zero
                    proportional_fee = (
                        (total_fee / n).quantize(Decimal("0.00000001"))
                        if n > 0
                        else Decimal("0")
                    )

                results.append({
                    "ticker": d["ticker"],
                    "asset_class": "acao",
                    "transaction_type": d["txn_type"],
                    "transaction_date": reference_date,
                    "quantity": d["quantity"],
                    "unit_price": d["unit_price"],
                    "total_value": d["total_value"],
                    "brokerage_fee": proportional_fee,
                    "irrf_withheld": d["irrf"],
                    "parser_source": "correpy",
                })

        logger.info("correpy: parsed %d transactions from PDF", len(results))
        return results

    except Exception as exc:
        logger.debug("correpy: parse failed (%s) — triggering fallback", exc)
        return []


def _map_transaction_type(raw_type: str | None) -> str:
    """Map correpy transaction type codes to our enum values."""
    if raw_type is None:
        return "buy"
    raw_upper = str(raw_type).upper()
    # correpy uses "BUY"/"SELL" or "C"/"V" (Compra/Venda in Portuguese)
    if raw_upper in ("BUY", "C", "COMPRA"):
        return "buy"
    if raw_upper in ("SELL", "V", "VENDA"):
        return "sell"
    return "buy"  # default to buy for unknown types
