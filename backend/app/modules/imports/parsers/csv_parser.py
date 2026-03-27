"""CSV parser for manual transaction imports.

Validates CSV rows against the CSVTransactionRow Pydantic model.
Returns (valid_rows, errors) where errors contain row number + error description.

CSV format (see tests/fixtures/sample_import.csv):
    ticker,asset_class,transaction_type,transaction_date,quantity,unit_price,brokerage_fee,irrf_withheld,notes
"""
from __future__ import annotations

import io
import logging
from datetime import date
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, field_validator, model_validator

logger = logging.getLogger(__name__)

# Valid values for enum-like fields — mirrors portfolio.models enums
VALID_ASSET_CLASSES = {"acao", "fii", "renda_fixa", "bdr", "etf"}
VALID_TRANSACTION_TYPES = {"buy", "sell", "dividend", "jscp", "amortization"}


class CSVTransactionRow(BaseModel):
    """Validated representation of a single CSV import row.

    All string fields are stripped and normalized on input.
    Decimal fields accept strings (pandas reads numbers as strings from CSV).
    """
    ticker: str
    asset_class: str
    transaction_type: str
    transaction_date: date
    quantity: Decimal
    unit_price: Decimal
    brokerage_fee: Decimal = Decimal("0")
    irrf_withheld: Decimal = Decimal("0")
    notes: str = ""
    parser_source: str = "csv_parser"

    @field_validator("ticker", mode="before")
    @classmethod
    def normalize_ticker(cls, v: Any) -> str:
        return str(v).strip().upper()[:20]

    @field_validator("asset_class", mode="before")
    @classmethod
    def validate_asset_class(cls, v: Any) -> str:
        val = str(v).strip()
        if val not in VALID_ASSET_CLASSES:
            raise ValueError(
                f"asset_class must be one of {sorted(VALID_ASSET_CLASSES)}, got '{val}'"
            )
        return val

    @field_validator("transaction_type", mode="before")
    @classmethod
    def validate_transaction_type(cls, v: Any) -> str:
        val = str(v).strip().lower()
        if val not in VALID_TRANSACTION_TYPES:
            raise ValueError(
                f"transaction_type must be one of {sorted(VALID_TRANSACTION_TYPES)}, got '{val}'"
            )
        return val

    @field_validator("notes", mode="before")
    @classmethod
    def coerce_notes(cls, v: Any) -> str:
        if v is None or (isinstance(v, float) and v != v):  # NaN check
            return ""
        return str(v).strip()

    @field_validator("quantity", "unit_price", "brokerage_fee", "irrf_withheld", mode="before")
    @classmethod
    def coerce_decimal(cls, v: Any) -> Decimal:
        if v is None or (isinstance(v, float) and v != v):  # NaN -> 0
            return Decimal("0")
        try:
            return Decimal(str(v))
        except Exception:
            raise ValueError(f"Cannot convert '{v}' to Decimal")

    model_config = {"from_attributes": True}


def parse_csv(csv_bytes: bytes) -> tuple[list[CSVTransactionRow], list[dict]]:
    """Parse and validate CSV import file.

    Reads CSV using pandas, validates each row against CSVTransactionRow.
    Rows that fail validation are collected in the errors list (not raised).

    Args:
        csv_bytes: Raw bytes of the CSV file (UTF-8 or Latin-1).

    Returns:
        Tuple of (valid_rows, errors) where:
        - valid_rows: list[CSVTransactionRow] — rows that passed validation
        - errors: list[dict] with keys "row" (1-based CSV row number),
                  "field" (field name, if known), and "error" (message)
    """
    try:
        import pandas as pd
        from pydantic import ValidationError
    except ImportError as e:
        logger.error("csv_parser: missing dependency: %s", e)
        return [], [{"row": 0, "error": f"Missing dependency: {e}"}]

    try:
        # Try UTF-8 first, fall back to Latin-1 (common in Brazilian CSVs)
        try:
            df = pd.read_csv(io.BytesIO(csv_bytes), encoding="utf-8", dtype=str)
        except UnicodeDecodeError:
            df = pd.read_csv(io.BytesIO(csv_bytes), encoding="latin-1", dtype=str)

        # Normalize column names
        df.columns = [c.strip().lower() for c in df.columns]

        # Required columns
        required = {
            "ticker", "asset_class", "transaction_type",
            "transaction_date", "quantity", "unit_price",
        }
        missing = required - set(df.columns)
        if missing:
            return [], [{"row": 1, "error": f"Missing required columns: {sorted(missing)}"}]

    except Exception as exc:
        logger.warning("csv_parser: failed to read CSV: %s", exc)
        return [], [{"row": 0, "error": f"Failed to read CSV: {exc}"}]

    valid_rows: list[CSVTransactionRow] = []
    errors: list[dict] = []

    for idx, row in df.iterrows():
        row_num = int(idx) + 2  # +2: header row is row 1, data starts at row 2
        try:
            validated = CSVTransactionRow(**row.to_dict())
            valid_rows.append(validated)
        except Exception as exc:
            # Extract field name from Pydantic ValidationError if possible
            field = None
            error_msg = str(exc)
            if hasattr(exc, "errors"):
                first_error = exc.errors()[0] if exc.errors() else {}
                loc = first_error.get("loc", ())
                field = str(loc[0]) if loc else None
                error_msg = first_error.get("msg", error_msg)
            errors.append({"row": row_num, "field": field, "error": error_msg})
            logger.debug("csv_parser: row %d validation error: %s", row_num, exc)

    logger.info(
        "csv_parser: %d valid rows, %d errors from %d data rows",
        len(valid_rows), len(errors), len(df),
    )
    return valid_rows, errors
