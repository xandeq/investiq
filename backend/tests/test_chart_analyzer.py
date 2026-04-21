"""Unit tests for the chart_analyzer module — no HTTP calls, synthetic data only."""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest


def _make_df(n: int = 60) -> pd.DataFrame:
    """Generate synthetic OHLCV + indicator DataFrame."""
    np.random.seed(42)
    close = pd.Series(50 + np.cumsum(np.random.randn(n) * 0.5))
    high = close + abs(np.random.randn(n) * 0.3)
    low = close - abs(np.random.randn(n) * 0.3)
    open_ = close.shift(1).fillna(close)
    volume = pd.Series(np.random.randint(100_000, 500_000, size=n), dtype=float)

    from app.modules.chart_analyzer.indicators import (
        calculate_atr,
        calculate_bollinger,
        calculate_ema,
        calculate_rsi,
    )

    ema20 = calculate_ema(close, 20)
    ema50 = calculate_ema(close, 50)
    ema200 = calculate_ema(close, 200)
    rsi = calculate_rsi(close)
    atr = calculate_atr(high, low, close)
    bb_upper, _bb_mid, bb_lower = calculate_bollinger(close)

    df = pd.DataFrame(
        {
            "open": open_,
            "high": high,
            "low": low,
            "close": close,
            "volume": volume,
            "ema20": ema20,
            "ema50": ema50,
            "ema200": ema200,
            "rsi": rsi,
            "atr": atr,
            "bb_upper": bb_upper,
            "bb_lower": bb_lower,
        }
    )
    return df.dropna().reset_index(drop=True)


# ---------------------------------------------------------------------------
# Indicator tests
# ---------------------------------------------------------------------------

def test_rsi_basic():
    """RSI must be in [0, 100] for all values."""
    from app.modules.chart_analyzer.indicators import calculate_rsi

    close = pd.Series([10, 11, 12, 11, 10, 9, 10, 11, 12, 13, 14, 13, 12, 11, 10])
    rsi = calculate_rsi(close, period=5)
    valid = rsi.dropna()
    assert (valid >= 0).all(), "RSI below 0 found"
    assert (valid <= 100).all(), "RSI above 100 found"


def test_rsi_length_matches_input():
    """RSI Series length must match input length."""
    from app.modules.chart_analyzer.indicators import calculate_rsi

    close = pd.Series(list(range(30)), dtype=float)
    rsi = calculate_rsi(close)
    assert len(rsi) == len(close)


def test_ema_converges():
    """EMA of a flat series must equal that constant."""
    from app.modules.chart_analyzer.indicators import calculate_ema

    close = pd.Series([100.0] * 50)
    ema = calculate_ema(close, 20)
    assert abs(float(ema.iloc[-1]) - 100.0) < 0.01


def test_atr_non_negative():
    """ATR must be non-negative."""
    from app.modules.chart_analyzer.indicators import calculate_atr

    n = 30
    close = pd.Series(list(range(1, n + 1)), dtype=float)
    high = close + 1.0
    low = close - 1.0
    atr = calculate_atr(high, low, close)
    assert (atr.dropna() >= 0).all()


def test_bollinger_order():
    """Upper band must be >= middle >= lower."""
    from app.modules.chart_analyzer.indicators import calculate_bollinger

    close = pd.Series(50 + np.cumsum(np.random.randn(50)))
    upper, mid, lower = calculate_bollinger(close)
    valid = upper.dropna().index
    assert (upper.loc[valid] >= mid.loc[valid]).all()
    assert (mid.loc[valid] >= lower.loc[valid]).all()


def test_volume_ratio_returns_float():
    """volume_ratio must return a plain float."""
    from app.modules.chart_analyzer.indicators import calculate_volume_ratio

    volume = pd.Series([100_000.0] * 25)
    ratio = calculate_volume_ratio(volume)
    assert isinstance(ratio, float)
    assert ratio > 0


# ---------------------------------------------------------------------------
# Pattern detection tests
# ---------------------------------------------------------------------------

def test_detect_patterns_returns_list():
    """detect_patterns must return a list (can be empty)."""
    from app.modules.chart_analyzer.patterns import detect_patterns

    df = _make_df(60)
    result = detect_patterns(df)
    assert isinstance(result, list)


def test_detect_patterns_structure():
    """Each detected pattern must have name, direction, confidence keys."""
    from app.modules.chart_analyzer.patterns import detect_patterns

    df = _make_df(60)
    result = detect_patterns(df)
    for p in result:
        assert "name" in p
        assert "direction" in p
        assert "confidence" in p
        assert 0.0 <= p["confidence"] <= 1.0
        assert p["direction"] in ("long", "short", "neutral")


def test_detect_patterns_short_df_returns_empty():
    """Fewer than 21 rows should return empty list."""
    from app.modules.chart_analyzer.patterns import detect_patterns

    df = _make_df(10)
    result = detect_patterns(df)
    assert result == []


# ---------------------------------------------------------------------------
# Level detection tests
# ---------------------------------------------------------------------------

def test_find_levels_returns_dict():
    """find_levels must return a dict with support and resistance keys."""
    from app.modules.chart_analyzer.levels import find_levels

    df = _make_df(60)
    result = find_levels(df)
    assert isinstance(result, dict)
    assert "support" in result
    assert "resistance" in result
    assert isinstance(result["support"], list)
    assert isinstance(result["resistance"], list)


def test_find_levels_values_are_floats():
    """All level values must be numeric."""
    from app.modules.chart_analyzer.levels import find_levels

    df = _make_df(60)
    result = find_levels(df)
    for price in result["support"] + result["resistance"]:
        assert isinstance(price, (int, float))


# ---------------------------------------------------------------------------
# Regime detection tests
# ---------------------------------------------------------------------------

def test_detect_regime_returns_valid():
    """detect_regime must return one of the 4 valid strings."""
    from app.modules.chart_analyzer.regime import detect_regime

    df = _make_df(60)
    regime = detect_regime(df)
    assert regime in ("trending_up", "trending_down", "choppy", "volatile")


def test_detect_regime_short_df():
    """Short DataFrame falls back gracefully."""
    from app.modules.chart_analyzer.regime import detect_regime

    df = _make_df(10)
    regime = detect_regime(df)
    assert regime in ("trending_up", "trending_down", "choppy", "volatile")


# ---------------------------------------------------------------------------
# Service / formatting tests
# ---------------------------------------------------------------------------

def test_format_analysis_message_no_setup():
    """format_analysis_message with has_setup=False must not raise."""
    import asyncio
    from app.modules.telegram_bot.service import format_analysis_message

    analysis = {
        "ticker": "BBSE3",
        "has_setup": False,
        "setup": None,
        "indicators": {
            "rsi_14": 52.3,
            "volume_ratio": 1.2,
            "regime": "choppy",
            "ema20": 30.0,
            "ema50": 29.5,
            "ema200": 28.0,
            "atr": 0.45,
            "macd": 0.01,
            "macd_signal": 0.005,
        },
        "confluences": ["RSI neutro (zona de valor)"],
        "levels": {"support": [29.0, 28.5], "resistance": [31.0, 32.0]},
        "error": None,
    }

    msg = asyncio.run(format_analysis_message(analysis))
    assert isinstance(msg, str)
    assert "BBSE3" in msg
    assert len(msg) > 10


def test_format_analysis_message_with_setup():
    """format_analysis_message with a setup dict includes entry/stop info."""
    import asyncio
    from app.modules.telegram_bot.service import format_analysis_message

    analysis = {
        "ticker": "PETR4",
        "has_setup": True,
        "setup": {
            "pattern": "breakout",
            "direction": "long",
            "entry": 38.50,
            "stop": 37.10,
            "target_1": 40.80,
            "target_2": 42.70,
            "rr": 2.3,
            "grade": "A",
        },
        "indicators": {
            "rsi_14": 61.0,
            "volume_ratio": 1.8,
            "regime": "trending_up",
            "ema20": 37.5,
            "ema50": 36.0,
            "ema200": 33.0,
            "atr": 0.78,
            "macd": 0.12,
            "macd_signal": 0.08,
        },
        "confluences": ["RSI neutro", "Acima da EMA200"],
        "levels": {"support": [37.0], "resistance": [40.0]},
        "error": None,
    }

    msg = asyncio.run(format_analysis_message(analysis))
    assert "breakout" in msg.lower()
    assert "38.5" in msg or "38,5" in msg or "38.50" in msg
