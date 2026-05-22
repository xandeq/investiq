"""Regression tests for timezone-safe datetime utilities."""
from datetime import datetime, timezone, date
import pytest

from app.core.dt_utils import utc_now, as_utc, to_date


class TestUtcNow:
    def test_returns_aware_datetime(self):
        now = utc_now()
        assert now.tzinfo is not None
        assert now.tzinfo == timezone.utc

    def test_is_recent(self):
        now = utc_now()
        delta = (datetime.now(timezone.utc) - now).total_seconds()
        assert abs(delta) < 5


class TestAsUtc:
    def test_naive_becomes_utc(self):
        naive = datetime(2024, 1, 15, 12, 0, 0)
        result = as_utc(naive)
        assert result.tzinfo == timezone.utc
        assert result.year == 2024 and result.hour == 12

    def test_aware_utc_passthrough(self):
        aware = datetime(2024, 1, 15, 12, 0, 0, tzinfo=timezone.utc)
        result = as_utc(aware)
        assert result == aware

    def test_none_returns_none(self):
        assert as_utc(None) is None

    def test_no_shift_for_utc_naive(self):
        """A naive datetime treated as UTC must not shift the hour."""
        naive = datetime(2024, 6, 1, 9, 30, 0)
        result = as_utc(naive)
        assert result.hour == 9  # must not add/subtract hours

    def test_aware_non_utc_normalizes_to_utc(self):
        from datetime import timedelta
        brt = timezone(timedelta(hours=-3))
        aware_brt = datetime(2024, 1, 15, 9, 0, 0, tzinfo=brt)  # 9h BRT = 12h UTC
        result = as_utc(aware_brt)
        assert result.tzinfo == timezone.utc
        assert result.hour == 12


class TestToDate:
    def test_naive_datetime_returns_date(self):
        naive = datetime(2024, 3, 20, 23, 0, 0)
        result = to_date(naive)
        assert isinstance(result, date)
        assert result == date(2024, 3, 20)

    def test_none_returns_none(self):
        assert to_date(None) is None

    def test_aware_returns_utc_date(self):
        aware = datetime(2024, 3, 20, 23, 0, 0, tzinfo=timezone.utc)
        assert to_date(aware) == date(2024, 3, 20)
