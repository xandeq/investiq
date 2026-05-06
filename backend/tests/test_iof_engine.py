"""IOF regressivo engine tests."""

from decimal import Decimal

import pytest

from app.modules.market_universe.iof_engine import IOFEngine


@pytest.mark.parametrize(
    ("days", "expected"),
    [
        (1, "0.96"),
        (2, "0.93"),
        (3, "0.90"),
        (4, "0.86"),
        (5, "0.83"),
        (6, "0.80"),
        (7, "0.76"),
        (8, "0.73"),
        (9, "0.70"),
        (10, "0.66"),
        (11, "0.63"),
        (12, "0.60"),
        (13, "0.56"),
        (14, "0.53"),
        (15, "0.50"),
        (16, "0.46"),
        (17, "0.43"),
        (18, "0.40"),
        (19, "0.36"),
        (20, "0.33"),
        (21, "0.30"),
        (22, "0.26"),
        (23, "0.23"),
        (24, "0.20"),
        (25, "0.16"),
        (26, "0.13"),
        (27, "0.10"),
        (28, "0.06"),
        (29, "0.03"),
        (30, "0.00"),
    ],
)
def test_rate_for_days_matches_decreto_6306_table(days: int, expected: str) -> None:
    assert IOFEngine().rate_for_days(days) == Decimal(expected)


@pytest.mark.parametrize("days", [30, 31, 365])
def test_rate_for_days_returns_zero_after_30_days(days: int) -> None:
    assert IOFEngine().rate_for_days(days) == Decimal("0.00")


@pytest.mark.parametrize("days", [0, -1])
def test_rate_for_days_rejects_non_positive_days(days: int) -> None:
    with pytest.raises(ValueError, match="holding_days must be positive"):
        IOFEngine().rate_for_days(days)
