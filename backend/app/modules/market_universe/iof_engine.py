"""IOF regressivo calculator for short-term fixed-income redemptions."""

from __future__ import annotations

from decimal import Decimal


class IOFEngine:
    """Calculate IOF over yield using Decreto 6.306/2007's 30-day table."""

    _REGRESSIVE_RATES: dict[int, Decimal] = {
        1: Decimal("0.96"),
        2: Decimal("0.93"),
        3: Decimal("0.90"),
        4: Decimal("0.86"),
        5: Decimal("0.83"),
        6: Decimal("0.80"),
        7: Decimal("0.76"),
        8: Decimal("0.73"),
        9: Decimal("0.70"),
        10: Decimal("0.66"),
        11: Decimal("0.63"),
        12: Decimal("0.60"),
        13: Decimal("0.56"),
        14: Decimal("0.53"),
        15: Decimal("0.50"),
        16: Decimal("0.46"),
        17: Decimal("0.43"),
        18: Decimal("0.40"),
        19: Decimal("0.36"),
        20: Decimal("0.33"),
        21: Decimal("0.30"),
        22: Decimal("0.26"),
        23: Decimal("0.23"),
        24: Decimal("0.20"),
        25: Decimal("0.16"),
        26: Decimal("0.13"),
        27: Decimal("0.10"),
        28: Decimal("0.06"),
        29: Decimal("0.03"),
        30: Decimal("0.00"),
    }

    def rate_for_days(self, holding_days: int) -> Decimal:
        """Return IOF rate as a fraction of yield, e.g. 0.96 for day 1."""
        if holding_days <= 0:
            raise ValueError("holding_days must be positive")
        if holding_days >= 30:
            return Decimal("0.00")
        return self._REGRESSIVE_RATES[holding_days]
