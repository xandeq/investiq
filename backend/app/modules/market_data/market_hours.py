"""Market hours utilities for BR, US, and CRYPTO markets.

Provides is_market_open(), market_status_prefix() and next_open() for
use in any endpoint or Telegram command that serves price-sensitive data.
"""
from __future__ import annotations

from datetime import datetime, time, timezone, timedelta
from typing import Literal

# BRT = UTC-3
BRT = timezone(timedelta(hours=-3))

# B3 holidays 2025-2026 (YYYY-MM-DD)
_B3_HOLIDAYS = {
    "2025-01-01", "2025-04-18", "2025-04-21", "2025-05-01",
    "2025-06-19", "2025-09-07", "2025-10-12", "2025-11-02",
    "2025-11-15", "2025-11-20", "2025-12-25",
    "2026-01-01", "2026-02-16", "2026-02-17", "2026-04-03",
    "2026-04-21", "2026-05-01", "2026-06-04", "2026-09-07",
    "2026-10-12", "2026-11-02", "2026-11-15", "2026-11-20",
    "2026-12-25",
}

MarketType = Literal["BR", "US", "CRYPTO"]


def _now_brt() -> datetime:
    return datetime.now(BRT)


def is_market_open(market: MarketType = "BR") -> bool:
    """Return True if the given market is currently open."""
    if market == "CRYPTO":
        return True

    now = _now_brt()
    weekday = now.weekday()  # 0=Mon … 6=Sun

    if market == "BR":
        if weekday >= 5:
            return False
        date_str = now.strftime("%Y-%m-%d")
        if date_str in _B3_HOLIDAYS:
            return False
        t = now.time()
        return time(10, 0) <= t <= time(17, 30)

    if market == "US":
        # NYSE: 9h30-16h ET = 10h30-17h BRT (approx, ignoring DST edge)
        if weekday >= 5:
            return False
        t = now.time()
        return time(10, 30) <= t <= time(17, 0)

    return False


def last_close_str(market: MarketType = "BR") -> str:
    """Human-readable last close description."""
    now = _now_brt()
    if market == "BR":
        # Find last weekday that was a trading day
        for days_back in range(1, 8):
            candidate = now - timedelta(days=days_back)
            ds = candidate.strftime("%Y-%m-%d")
            if candidate.weekday() < 5 and ds not in _B3_HOLIDAYS:
                return candidate.strftime("%d/%m/%Y às 17h30")
    return (now - timedelta(days=1)).strftime("%d/%m/%Y")


def next_open_str(market: MarketType = "BR") -> str:
    """Human-readable next open description."""
    now = _now_brt()
    if market == "BR":
        candidate = now
        for _ in range(8):
            candidate += timedelta(days=1)
            ds = candidate.strftime("%Y-%m-%d")
            if candidate.weekday() < 5 and ds not in _B3_HOLIDAYS:
                return candidate.strftime("%d/%m/%Y às 10h00")
        return "próximo dia útil"
    return "em breve"


def market_status_prefix(market: MarketType = "BR") -> str:
    """Return a warning prefix string when the market is closed, else empty string."""
    if is_market_open(market):
        return ""
    return (
        f"⚠️ <b>MERCADO FECHADO</b> — dados do fechamento de {last_close_str(market)}.\n"
        f"Próxima abertura: {next_open_str(market)}. "
        f"<b>NÃO execute ordens com base nesses preços.</b>\n\n"
    )
