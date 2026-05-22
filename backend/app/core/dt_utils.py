"""Timezone-safe datetime utilities.

All datetimes stored in the DB are naive UTC (PostgreSQL TIMESTAMP WITHOUT TIME ZONE).
These helpers normalize them to UTC-aware consistently.
"""
from __future__ import annotations
from datetime import date, datetime, timezone


def utc_now() -> datetime:
    """Current UTC time, always timezone-aware."""
    return datetime.now(timezone.utc)


def as_utc(dt: datetime | None) -> datetime | None:
    """Coerce a naive datetime (assumed UTC) to UTC-aware. Pass-through if already aware."""
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def to_date(dt: datetime | None) -> date | None:
    """Extract UTC date from a datetime (aware or naive-UTC)."""
    if dt is None:
        return None
    return as_utc(dt).date()  # type: ignore[union-attr]
