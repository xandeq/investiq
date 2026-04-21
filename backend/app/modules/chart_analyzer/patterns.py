"""Algorithmic pattern detection (deterministic, no ML)."""
from __future__ import annotations

import numpy as np
import pandas as pd


def detect_patterns(df: pd.DataFrame) -> list[dict]:
    """Detect up to 8 technical patterns in the given OHLCV + indicator DataFrame.

    Required columns: open, high, low, close, volume,
                      ema20, ema50, ema200, rsi, atr, bb_upper, bb_lower
    Returns a list of dicts, each with: name, direction, confidence (0-1).
    """
    if len(df) < 21:
        return []

    patterns: list[dict] = []
    c = df["close"]
    h = df["high"]
    v = df["volume"]
    ema20 = df["ema20"]
    ema50 = df["ema50"]
    rsi = df["rsi"]
    atr = df["atr"]
    bb_upper = df["bb_upper"]
    bb_lower = df["bb_lower"]

    last_close = float(c.iloc[-1])
    last_rsi = float(rsi.iloc[-1])
    last_atr = float(atr.iloc[-1])
    vol_mean = float(v.iloc[-21:-1].mean()) if len(v) > 21 else float(v.mean())

    # 1. Breakout
    window_high = float(h.iloc[-21:-1].max())
    if last_close > window_high and float(v.iloc[-1]) > 1.5 * vol_mean:
        patterns.append({"name": "breakout", "direction": "long", "confidence": 0.75})

    # 2. Pullback to EMA20
    last_ema20 = float(ema20.iloc[-1])
    last_ema50 = float(ema50.iloc[-1])
    if last_close < last_ema20 and last_close > last_ema50 and 40 < last_rsi < 60:
        patterns.append({"name": "pullback_ema20", "direction": "long", "confidence": 0.65})

    # 3. RSI Bullish Divergence (last 10 candles)
    window = min(10, len(df) - 1)
    sub_c = c.iloc[-window:]
    sub_rsi = rsi.iloc[-window:]
    prev_min_idx = sub_c.iloc[:-1].idxmin()
    if sub_c.iloc[-1] < float(sub_c.loc[prev_min_idx]) and float(sub_rsi.iloc[-1]) > float(sub_rsi.loc[prev_min_idx]):
        patterns.append({"name": "rsi_divergence", "direction": "long", "confidence": 0.70})

    # 4. Flag — tight consolidation after strong move
    recent_atr = float(atr.iloc[-5:].mean()) if len(atr) >= 5 else last_atr
    avg_atr = float(atr.iloc[-21:].mean()) if len(atr) >= 21 else last_atr
    move_5 = float(c.iloc[-1] / c.iloc[-6] - 1) if len(c) >= 6 else 0.0
    prior_move = float(c.iloc[-6] / c.iloc[-11] - 1) if len(c) >= 11 else 0.0
    if recent_atr < 0.5 * avg_atr and prior_move > 0.05:
        patterns.append({"name": "flag", "direction": "long", "confidence": 0.60})

    # 5. Head and Shoulders (OCO bearish)
    if len(df) >= 30:
        highs = h.iloc[-30:].values
        # Look for 3 peaks with middle largest
        thirds = len(highs) // 3
        left_peak = float(highs[:thirds].max())
        head_peak = float(highs[thirds: 2 * thirds].max())
        right_peak = float(highs[2 * thirds:].max())
        if head_peak > left_peak * 1.02 and head_peak > right_peak * 1.02 and abs(left_peak - right_peak) / head_peak < 0.05:
            patterns.append({"name": "oco", "direction": "short", "confidence": 0.55})

    # 6. Bollinger Band Squeeze
    bb_width = float((bb_upper.iloc[-1] - bb_lower.iloc[-1]) / last_close)
    hist_bb_upper = df["bb_upper"].iloc[-60:] if len(df) >= 60 else df["bb_upper"]
    hist_bb_lower = df["bb_lower"].iloc[-60:] if len(df) >= 60 else df["bb_lower"]
    hist_bb_width = float(((hist_bb_upper - hist_bb_lower) / c.iloc[-len(hist_bb_upper):]).mean())
    if hist_bb_width > 0 and bb_width < 0.10 * hist_bb_width:
        patterns.append({"name": "squeeze_bb", "direction": "neutral", "confidence": 0.65})

    # 7. Volume Climax — exhaustion
    last_candle_size = abs(float(c.iloc[-1]) - float(df["open"].iloc[-1]))
    if float(v.iloc[-1]) > 3 * vol_mean and last_candle_size > 2 * last_atr:
        patterns.append({"name": "volume_climax", "direction": "neutral", "confidence": 0.60})

    # 8. Gap Fill
    if len(df) >= 2:
        prev_close = float(c.iloc[-2])
        today_open = float(df["open"].iloc[-1])
        gap = abs(today_open - prev_close)
        partially_closed = (
            (today_open > prev_close and last_close < today_open)
            or (today_open < prev_close and last_close > today_open)
        )
        if gap > 1.5 * last_atr and partially_closed:
            patterns.append({"name": "gap_fill", "direction": "neutral", "confidence": 0.55})

    return patterns
