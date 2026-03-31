"""Data versioning utilities for the AI Analysis module (Phase 12).

Every analysis must be tagged with:
- data_version_id: unique identifier for the data snapshot used
- data_sources: list of data providers with freshness metadata

This ensures users and auditors can trace which data backed any analysis.
"""
from __future__ import annotations

from datetime import datetime, timezone


def build_data_version_id() -> str:
    """Build a unique data version identifier for today's data snapshot.

    Format: brapi_eod_YYYYMMDD_v1.2
    The version suffix (v1.2) tracks the data pipeline version.
    """
    today = datetime.now(tz=timezone.utc).strftime("%Y%m%d")
    return f"brapi_eod_{today}_v1.2"


def get_data_sources() -> list[dict]:
    """Return the canonical list of data sources used for analysis.

    Each source includes provider name, data type, and freshness window.
    """
    return [
        {
            "source": "BRAPI",
            "type": "fundamentals",
            "freshness": "1d",
        },
        {
            "source": "B3/CVM",
            "type": "financial_statements",
            "freshness": "1q",
        },
    ]
