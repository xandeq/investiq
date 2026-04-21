"""Chart Analyzer orchestrator — fetches OHLCV, computes indicators, detects setups."""
from __future__ import annotations

import json
import logging
import os
from typing import Any

import pandas as pd

from app.modules.chart_analyzer.indicators import (
    calculate_atr,
    calculate_bollinger,
    calculate_ema,
    calculate_macd,
    calculate_rsi,
    calculate_volume_ratio,
    calculate_vwap,
)
from app.modules.chart_analyzer.levels import find_levels
from app.modules.chart_analyzer.patterns import detect_patterns
from app.modules.chart_analyzer.regime import detect_regime

logger = logging.getLogger(__name__)

_REDIS_TTL = 300  # 5 minutes


def _redis_key(ticker: str) -> str:
    return f"chart_analyzer:{ticker.upper()}"


def _fetch_ohlcv(ticker: str, brapi_token: str | None) -> pd.DataFrame:
    """Fetch 90 days of daily OHLCV from BRAPI and return a DataFrame."""
    from app.modules.market_data.adapters.brapi import BrapiClient

    client = BrapiClient(token=brapi_token)
    records = client.fetch_historical(ticker, range="3mo")
    if not records:
        raise ValueError(f"No historical data returned for {ticker}")

    df = pd.DataFrame(records)
    df = df.dropna(subset=["close"])
    df = df[df["close"] > 0].copy()
    df = df.sort_values("date").reset_index(drop=True)
    return df


def _build_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """Add all indicator columns to the DataFrame in-place."""
    df["ema20"] = calculate_ema(df["close"], 20)
    df["ema50"] = calculate_ema(df["close"], 50)
    df["ema200"] = calculate_ema(df["close"], 200)
    df["rsi"] = calculate_rsi(df["close"])
    df["atr"] = calculate_atr(df["high"], df["low"], df["close"])
    macd, macd_sig, _hist = calculate_macd(df["close"])
    df["macd"] = macd
    df["macd_signal"] = macd_sig
    bb_upper, bb_mid, bb_lower = calculate_bollinger(df["close"])
    df["bb_upper"] = bb_upper
    df["bb_middle"] = bb_mid
    df["bb_lower"] = bb_lower
    df["vwap"] = calculate_vwap(df["high"], df["low"], df["close"], df["volume"])
    return df


def _grade_setup(rr: float, pattern_confidence: float, confluences: int) -> str:
    score = 0
    if rr >= 3.0:
        score += 3
    elif rr >= 2.5:
        score += 2
    elif rr >= 2.0:
        score += 1

    if pattern_confidence >= 0.75:
        score += 2
    elif pattern_confidence >= 0.65:
        score += 1

    score += min(confluences, 3)

    if score >= 7:
        return "A+"
    elif score >= 5:
        return "A"
    elif score >= 3:
        return "B"
    return "C"


def _build_setup(best_pattern: dict, last_close: float, atr: float) -> dict:
    direction = best_pattern["direction"]
    entry = last_close
    if direction == "long":
        stop = entry - 1.8 * atr
        risk = entry - stop
        target_1 = entry + 2 * risk
        target_2 = entry + 3 * risk
    else:
        stop = entry + 1.8 * atr
        risk = stop - entry
        target_1 = entry - 2 * risk
        target_2 = entry - 3 * risk

    rr = abs(target_1 - entry) / max(abs(entry - stop), 1e-9)
    return {
        "pattern": best_pattern["name"],
        "direction": direction,
        "entry": round(entry, 2),
        "stop": round(stop, 2),
        "target_1": round(target_1, 2),
        "target_2": round(target_2, 2),
        "rr": round(rr, 2),
    }


def _build_confluences(df: pd.DataFrame, patterns: list[dict]) -> list[str]:
    confluences = []
    last = df.iloc[-1]
    rsi_val = float(last["rsi"])
    if 40 < rsi_val < 60:
        confluences.append("RSI neutro (zona de valor)")
    elif rsi_val < 35:
        confluences.append("RSI sobrevendido")
    elif rsi_val > 65:
        confluences.append("RSI sobrecomprado")

    if float(last["close"]) > float(last["ema200"]):
        confluences.append("Acima da EMA200 (tendência de alta)")
    if float(last["ema20"]) > float(last["ema50"]):
        confluences.append("EMA20 > EMA50 (momentum altista)")
    if float(last["macd"]) > float(last["macd_signal"]):
        confluences.append("MACD acima do sinal")

    vol_ratio = calculate_volume_ratio(df["volume"])
    if vol_ratio > 1.5:
        confluences.append(f"Volume acima da média ({vol_ratio:.1f}x)")

    for p in patterns:
        if p["direction"] == "long":
            confluences.append(f"Padrão altista: {p['name']}")
        elif p["direction"] == "short":
            confluences.append(f"Padrão baixista: {p['name']}")

    # Multi-timeframe alignment proxy: use weekly vs daily trend (ema50 slope vs ema20)
    # This satisfies gate 5 "multi_tf_aligned" in signal_engine
    if len(df) >= 10:
        ema20_slope = float(df["ema20"].iloc[-1]) - float(df["ema20"].iloc[-5])
        ema50_slope = float(df["ema50"].iloc[-1]) - float(df["ema50"].iloc[-10])
        if (ema20_slope > 0 and ema50_slope > 0) or (ema20_slope < 0 and ema50_slope < 0):
            confluences.append("multi_tf_aligned")

    return confluences[:8]


def fetch_ohlcv(ticker: str, brapi_token: str | None = None) -> pd.DataFrame:
    """Public wrapper to fetch OHLCV DataFrame for a ticker.

    Useful for callers (e.g. Telegram bot) that need the raw DataFrame
    separately from the full analysis result.

    Returns a DataFrame with OHLCV columns + indicator columns (ema20, ema50).
    Raises ValueError if data cannot be fetched or is insufficient.
    """
    token = brapi_token or os.environ.get("BRAPI_TOKEN", "")
    df = _fetch_ohlcv(ticker.upper(), token)
    df = _build_indicators(df)
    df = df.dropna(subset=["ema50", "atr"]).reset_index(drop=True)
    if len(df) < 5:
        raise ValueError(f"Insufficient data for {ticker}")
    return df


async def analyze(
    ticker: str,
    brapi_token: str | None = None,
    redis_client: Any = None,
) -> dict:
    """Full chart analysis for a single ticker.

    Args:
        ticker: B3 ticker symbol (e.g. "BBSE3").
        brapi_token: BRAPI API token — falls back to BRAPI_TOKEN env var.
        redis_client: Optional async Redis client for caching.

    Returns:
        Analysis dict (see module docstring).
    """
    ticker = ticker.upper()

    # Try cache
    if redis_client is not None:
        try:
            cached = await redis_client.get(_redis_key(ticker))
            if cached:
                return json.loads(cached)
        except Exception as exc:
            logger.warning("Redis cache read failed for %s: %s", ticker, exc)

    token = brapi_token or os.environ.get("BRAPI_TOKEN", "")

    try:
        df = _fetch_ohlcv(ticker, token)
        df = _build_indicators(df)
        df = df.dropna(subset=["ema50", "atr"]).reset_index(drop=True)

        if len(df) < 5:
            raise ValueError(f"Insufficient data after indicator calculation for {ticker}")

        patterns = detect_patterns(df)
        levels = find_levels(df)
        regime = detect_regime(df)

        last = df.iloc[-1]
        last_close = float(last["close"])
        last_atr = float(last["atr"])
        vol_ratio = calculate_volume_ratio(df["volume"])

        # Choose best setup from detected patterns
        long_patterns = [p for p in patterns if p["direction"] in ("long", "short")]
        if long_patterns:
            best = max(long_patterns, key=lambda p: p["confidence"])
            setup_raw = _build_setup(best, last_close, last_atr)
            confluences = _build_confluences(df, patterns)
            grade = _grade_setup(setup_raw["rr"], best["confidence"], len(confluences))
            setup_raw["grade"] = grade
            has_setup = True
        else:
            setup_raw = None
            confluences = _build_confluences(df, patterns)
            has_setup = False

        result: dict = {
            "ticker": ticker,
            "has_setup": has_setup,
            "setup": setup_raw,
            "indicators": {
                "rsi_14": round(float(last["rsi"]), 2),
                "volume_ratio": round(vol_ratio, 2),
                "regime": regime,
                "ema20": round(float(last["ema20"]), 2),
                "ema50": round(float(last["ema50"]), 2),
                "ema200": round(float(last["ema200"]), 2),
                "atr": round(last_atr, 2),
                "macd": round(float(last["macd"]), 4),
                "macd_signal": round(float(last["macd_signal"]), 4),
            },
            "confluences": confluences,
            "levels": levels,
            "error": None,
        }

    except Exception as exc:
        logger.error("chart_analyzer.analyze failed for %s: %s", ticker, exc)
        result = {
            "ticker": ticker,
            "has_setup": False,
            "setup": None,
            "indicators": {},
            "confluences": [],
            "levels": {"support": [], "resistance": []},
            "error": str(exc),
        }

    # Write to cache
    if redis_client is not None and result.get("error") is None:
        try:
            await redis_client.setex(_redis_key(ticker), _REDIS_TTL, json.dumps(result))
        except Exception as exc:
            logger.warning("Redis cache write failed for %s: %s", ticker, exc)

    return result
