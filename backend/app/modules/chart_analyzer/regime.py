"""Market regime detection."""
from __future__ import annotations

import numpy as np
import pandas as pd


def detect_regime(df: pd.DataFrame) -> str:
    """Classify the current market regime.

    Args:
        df: DataFrame with columns: close, ema20, ema50, atr.

    Returns:
        One of: 'trending_up' | 'trending_down' | 'volatile' | 'choppy'
    """
    if len(df) < 20:
        return "choppy"

    close = df["close"]
    ema20 = df["ema20"]
    ema50 = df["ema50"]
    atr = df["atr"]

    last_close = float(close.iloc[-1])
    last_ema20 = float(ema20.iloc[-1])
    last_ema50 = float(ema50.iloc[-1])
    last_atr = float(atr.iloc[-1])

    # ATR-based volatility regime
    hist_atr_mean = float(atr.iloc[-60:].mean()) if len(atr) >= 60 else float(atr.mean())
    if hist_atr_mean > 0 and last_atr > 2 * hist_atr_mean:
        return "volatile"

    # ADX-like directional measure: use range expansion over 14 bars
    if len(df) >= 14:
        dm_up = (df["high"].diff().clip(lower=0)).iloc[-14:]
        dm_dn = (-df["low"].diff().clip(upper=0)).iloc[-14:]
        tr = (df["high"] - df["low"]).iloc[-14:]
        tr_sum = tr.sum()
        if tr_sum > 0:
            dip = dm_up.sum() / tr_sum * 100
            dim = dm_dn.sum() / tr_sum * 100
            dx = abs(dip - dim) / (dip + dim + 1e-9) * 100
        else:
            dx = 0.0
    else:
        dx = 0.0

    if last_close > last_ema50 and last_ema20 > last_ema50 and dx > 25:
        return "trending_up"

    if last_close < last_ema50 and last_ema20 < last_ema50:
        return "trending_down"

    return "choppy"
