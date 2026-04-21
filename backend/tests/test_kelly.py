"""Unit tests for Kelly fractional position sizing (Sprint 3)."""
from decimal import Decimal

import pytest

from app.modules.signal_engine.kelly import (
    MAX_OPEN_POSITIONS,
    MAX_POSITION_PCT,
    calculate_position_size,
    kelly_fraction,
)


# ── kelly_fraction tests ──────────────────────────────────────────────────────


def test_kelly_fraction_positive_expectancy():
    """Win rate 60%, avg win 2R → positive Kelly fraction."""
    fraction = kelly_fraction(win_rate=0.6, avg_win_r=2.0)
    # full_kelly = (0.6*2 - 0.4*1) / 2 = (1.2 - 0.4) / 2 = 0.4
    # quarter kelly = 0.4 / 4 = 0.10
    assert abs(fraction - 0.10) < 1e-6


def test_kelly_fraction_zero_win_rate():
    """Zero win rate → Kelly fraction is 0."""
    fraction = kelly_fraction(win_rate=0.0, avg_win_r=2.0)
    assert fraction == 0.0


def test_kelly_fraction_max_cap():
    """Even very favourable odds → fraction is positive and non-negative."""
    fraction = kelly_fraction(win_rate=0.9, avg_win_r=10.0)
    assert fraction > 0
    # Quarter Kelly should keep it below 1
    assert fraction < 1.0


def test_kelly_fraction_zero_avg_win():
    """avg_win_r = 0 → return 0 (guard against division by zero)."""
    fraction = kelly_fraction(win_rate=0.6, avg_win_r=0.0)
    assert fraction == 0.0


def test_kelly_fraction_negative_expectancy():
    """Negative expectancy → clamped to 0."""
    fraction = kelly_fraction(win_rate=0.2, avg_win_r=1.0)
    assert fraction == 0.0


# ── calculate_position_size tests ─────────────────────────────────────────────


def test_position_size_blocked_by_drawdown():
    """Daily drawdown at or below -2% blocks new entries."""
    result = calculate_position_size(
        book_value=Decimal("100000"),
        entry=Decimal("50"),
        stop=Decimal("45"),
        daily_pnl_pct=-0.025,  # -2.5%
    )
    assert result["blocked"] is True
    assert result["block_reason"] is not None
    assert result["shares"] == 0
    assert result["amount_brl"] == Decimal("0")


def test_position_size_blocked_by_max_positions():
    """Having MAX_OPEN_POSITIONS open positions blocks new entries."""
    result = calculate_position_size(
        book_value=Decimal("100000"),
        entry=Decimal("50"),
        stop=Decimal("45"),
        open_positions=MAX_OPEN_POSITIONS,
    )
    assert result["blocked"] is True
    assert "position" in result["block_reason"].lower() or "maximum" in result["block_reason"].lower()
    assert result["shares"] == 0


def test_position_size_valid():
    """Valid inputs → non-zero position size, not blocked."""
    result = calculate_position_size(
        book_value=Decimal("100000"),
        entry=Decimal("50.00"),
        stop=Decimal("45.00"),
        win_rate=0.55,
        avg_win_r=2.0,
        open_positions=2,
        daily_pnl_pct=0.005,
    )
    assert result["blocked"] is False
    assert result["block_reason"] is None
    assert result["fraction"] > 0
    assert result["amount_brl"] > 0
    assert result["shares"] > 0


def test_position_size_capped_at_max_pct():
    """Very high Kelly fraction is capped at MAX_POSITION_PCT."""
    result = calculate_position_size(
        book_value=Decimal("100000"),
        entry=Decimal("50"),
        stop=Decimal("49"),
        win_rate=0.9,
        avg_win_r=10.0,
    )
    # fraction must not exceed MAX_POSITION_PCT
    assert Decimal(str(result["fraction"])) <= MAX_POSITION_PCT + Decimal("0.001")
    assert any("capped" in w.lower() for w in result["warnings"])


def test_position_size_zero_risk_blocked():
    """Entry == stop → blocked (zero risk)."""
    result = calculate_position_size(
        book_value=Decimal("100000"),
        entry=Decimal("50"),
        stop=Decimal("50"),
    )
    assert result["blocked"] is True
