"""Unit tests for outcome tracker service (Sprint 3)."""
from decimal import Decimal

import pytest

from app.modules.outcome_tracker.service import calculate_r_multiple


def test_calculate_r_multiple_long_win():
    """Long trade that closes above entry — positive R-multiple."""
    r = calculate_r_multiple(
        entry=Decimal("50.00"),
        stop=Decimal("45.00"),
        exit_price=Decimal("60.00"),
        direction="long",
    )
    # R = (60 - 50) / (50 - 45) = 10 / 5 = 2.0
    assert r == Decimal("2.0")


def test_calculate_r_multiple_long_loss():
    """Long trade that closes below entry — negative R-multiple."""
    r = calculate_r_multiple(
        entry=Decimal("50.00"),
        stop=Decimal("45.00"),
        exit_price=Decimal("47.00"),
        direction="long",
    )
    # R = (47 - 50) / (50 - 45) = -3 / 5 = -0.6
    assert r == Decimal("-0.6")


def test_calculate_r_multiple_short():
    """Short trade that closes below entry — positive R-multiple."""
    r = calculate_r_multiple(
        entry=Decimal("100.00"),
        stop=Decimal("105.00"),
        exit_price=Decimal("90.00"),
        direction="short",
    )
    # R = (100 - 90) / |100 - 105| = 10 / 5 = 2.0
    assert r == Decimal("2.0")


def test_calculate_r_multiple_zero_risk():
    """Entry == stop → R is 0 (no division by zero)."""
    r = calculate_r_multiple(
        entry=Decimal("50.00"),
        stop=Decimal("50.00"),
        exit_price=Decimal("55.00"),
        direction="long",
    )
    assert r == Decimal("0")
