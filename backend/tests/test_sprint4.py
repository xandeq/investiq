"""Sprint 4 — unit tests for calibration, CoinGecko fallback, chart PNG, dynamic universe."""
from __future__ import annotations

import importlib
from decimal import Decimal
from unittest.mock import MagicMock, patch

import numpy as np
import pandas as pd
import pytest


# ---------------------------------------------------------------------------
# 1. Kelly fraction (pure math — no I/O)
# ---------------------------------------------------------------------------

def test_kelly_fraction_pure():
    from app.modules.signal_engine.kelly import kelly_fraction

    # 50% win rate, 2.5R avg win → full kelly = (0.5*2.5 - 0.5*1.0) / 2.5 = 0.3
    # quarter kelly = 0.075
    frac = kelly_fraction(win_rate=0.5, avg_win_r=2.5, avg_loss_r=1.0)
    assert abs(frac - 0.075) < 1e-6

    # Negative expectancy → 0
    assert kelly_fraction(win_rate=0.3, avg_win_r=1.0) == 0.0

    # avg_win_r <= 0 → 0
    assert kelly_fraction(win_rate=0.8, avg_win_r=0.0) == 0.0


# ---------------------------------------------------------------------------
# 2. CoinGecko fallback — radar must not raise when API is down
# ---------------------------------------------------------------------------

def test_coingecko_fallback_doesnt_raise():
    """Simulating CoinGecko failure — _build_crypto_radar must not raise."""
    from app.modules.opportunity_detector import radar

    with patch.object(radar, "_fetch_coingecko_data", side_effect=Exception("timeout")):
        try:
            result = radar._build_crypto_radar()
        except Exception as exc:
            pytest.fail(f"_build_crypto_radar raised unexpectedly: {exc}")

    # Result should be a list (may be empty if error is caught inside the loop)
    assert isinstance(result, list)


def test_coingecko_fallback_returns_partial_row():
    """When CoinGecko is unavailable, partial row (with None prices) is included."""
    from app.modules.opportunity_detector import radar

    # Simulate API returning None (unreachable)
    with patch.object(radar, "_fetch_coingecko_data", return_value=None):
        result = radar._build_crypto_radar()

    assert isinstance(result, list)
    # At least one row per configured crypto asset
    assert len(result) == len(radar.RADAR_CRYPTO)
    for row in result:
        assert row.get("current_price_brl") is None
        assert "CoinGecko indisponível" in row.get("signal", "")


# ---------------------------------------------------------------------------
# 3. Chart PNG — generate with synthetic data, verify bytes returned
# ---------------------------------------------------------------------------

def _make_synthetic_df(n: int = 70) -> pd.DataFrame:
    rng = np.random.default_rng(42)
    close = 100 + np.cumsum(rng.normal(0, 1, n))
    open_ = close + rng.normal(0, 0.5, n)
    high = np.maximum(close, open_) + rng.uniform(0, 1, n)
    low = np.minimum(close, open_) - rng.uniform(0, 1, n)
    volume = np.abs(rng.normal(1_000_000, 200_000, n))
    ema20 = pd.Series(close).ewm(span=20, adjust=False).mean().values
    ema50 = pd.Series(close).ewm(span=50, adjust=False).mean().values
    return pd.DataFrame({
        "open": open_,
        "high": high,
        "low": low,
        "close": close,
        "volume": volume,
        "ema20": ema20,
        "ema50": ema50,
    })


def test_generate_chart_png_returns_bytes():
    from app.modules.chart_analyzer.chart_image import generate_chart_png

    df = _make_synthetic_df()
    result = generate_chart_png(df, "TEST")

    assert isinstance(result, bytes)
    assert len(result) > 1000, "PNG should be more than 1KB"
    # PNG magic bytes
    assert result[:4] == b"\x89PNG", "Output should be a valid PNG"


def test_generate_chart_png_with_setup():
    from app.modules.chart_analyzer.chart_image import generate_chart_png

    df = _make_synthetic_df()
    setup = {
        "pattern": "breakout",
        "direction": "long",
        "entry": 102.0,
        "stop": 99.0,
        "target_1": 108.0,
        "target_2": 111.0,
    }
    result = generate_chart_png(df, "TEST", setup=setup)

    assert isinstance(result, bytes)
    assert result[:4] == b"\x89PNG"


def test_generate_chart_png_never_raises_on_bad_data():
    """Even with completely bad input, generate_chart_png should return bytes (fallback PNG)."""
    from app.modules.chart_analyzer.chart_image import generate_chart_png

    bad_df = pd.DataFrame({"open": [], "high": [], "low": [], "close": [], "volume": []})
    result = generate_chart_png(bad_df, "BAD")
    # Must return bytes even on error
    assert isinstance(result, bytes)
    assert len(result) > 0


# ---------------------------------------------------------------------------
# 4. Calibration — default weights when no DB outcomes available
# ---------------------------------------------------------------------------

def test_recalibration_default_weights():
    """Without a DB session, weights should all be 1.0 (defaults)."""
    from app.modules.signal_engine.calibration import get_pattern_weights, PATTERN_WEIGHTS

    weights = get_pattern_weights(db_session=None)
    assert isinstance(weights, dict)
    assert len(weights) > 0
    for pattern, w in weights.items():
        assert w == 1.0, f"Expected default weight 1.0 for {pattern}, got {w}"


def test_recalibration_disables_negative_expectancy():
    """Pattern with expectancy < 0 and N >= 30 should get weight 0.0."""
    from app.modules.signal_engine import calibration

    mock_db = MagicMock()
    mock_result = MagicMock()
    mock_result.fetchall.return_value = [
        ("breakout", 35, -0.3, 0.40),  # expectancy=-0.3, n=35 → disable
        ("pullback_ema20", 12, 0.8, 0.60),  # expectancy=0.8, n=12 → boost
    ]
    mock_db.execute.return_value = mock_result

    with patch.object(calibration, "_fetch_expectancy_sync", return_value={
        "breakout": {"n": 35, "expectancy": -0.3, "win_rate": 0.40},
        "pullback_ema20": {"n": 12, "expectancy": 0.8, "win_rate": 0.60},
    }):
        weights = calibration.get_pattern_weights(db_session=mock_db)

    assert weights["breakout"] == 0.0
    assert weights["pullback_ema20"] == calibration.BOOST_WEIGHT
    # Other patterns remain at 1.0
    assert weights.get("flag", 1.0) == 1.0


# ---------------------------------------------------------------------------
# 5. Dynamic universe — always includes base UNIVERSE tickers
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_dynamic_universe_includes_base():
    """Dynamic universe must always include all base UNIVERSE tickers."""
    from app.modules.signal_engine.scanner import get_dynamic_universe, UNIVERSE

    # Without DB
    result = await get_dynamic_universe(db=None)
    assert isinstance(result, list)
    for ticker in UNIVERSE:
        assert ticker in result, f"Base ticker {ticker} missing from dynamic universe"


@pytest.mark.asyncio
async def test_dynamic_universe_adds_portfolio_tickers():
    """Portfolio tickers not in UNIVERSE should be added."""
    from app.modules.signal_engine.scanner import get_dynamic_universe, UNIVERSE

    mock_db = MagicMock()
    mock_result = MagicMock()
    mock_result.fetchall.return_value = [("XPML11",), ("PETR4",)]
    mock_db.execute = MagicMock(return_value=mock_result)

    # Make awaitable
    async def fake_execute(stmt):
        return mock_result

    mock_db.execute = fake_execute

    result = await get_dynamic_universe(db=mock_db)

    assert "XPML11" in result  # portfolio-only ticker included
    for ticker in UNIVERSE:
        assert ticker in result


@pytest.mark.asyncio
async def test_dynamic_universe_db_failure_fallback():
    """If DB query raises, should fall back to base UNIVERSE without raising."""
    from app.modules.signal_engine.scanner import get_dynamic_universe, UNIVERSE

    mock_db = MagicMock()

    async def failing_execute(stmt):
        raise RuntimeError("DB unavailable")

    mock_db.execute = failing_execute

    result = await get_dynamic_universe(db=mock_db)
    assert isinstance(result, list)
    for ticker in UNIVERSE:
        assert ticker in result
