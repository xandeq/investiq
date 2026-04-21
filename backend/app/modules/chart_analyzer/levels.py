"""Support and resistance level detection via swing high/low clustering."""
from __future__ import annotations

import numpy as np
import pandas as pd


def _swing_highs(series: pd.Series, window: int) -> list[float]:
    vals = []
    arr = series.values
    for i in range(window, len(arr) - window):
        if arr[i] == max(arr[i - window : i + window + 1]):
            vals.append(float(arr[i]))
    return vals


def _swing_lows(series: pd.Series, window: int) -> list[float]:
    vals = []
    arr = series.values
    for i in range(window, len(arr) - window):
        if arr[i] == min(arr[i - window : i + window + 1]):
            vals.append(float(arr[i]))
    return vals


def _cluster(prices: list[float], tolerance: float) -> list[float]:
    """Merge prices within `tolerance` fraction of each other into a single level."""
    if not prices:
        return []
    sorted_p = sorted(prices)
    clusters: list[list[float]] = [[sorted_p[0]]]
    for p in sorted_p[1:]:
        center = sum(clusters[-1]) / len(clusters[-1])
        if abs(p - center) / center <= tolerance:
            clusters[-1].append(p)
        else:
            clusters.append([p])
    return [round(sum(c) / len(c), 2) for c in clusters]


def find_levels(
    df: pd.DataFrame,
    window: int = 5,
    tolerance: float = 0.02,
) -> dict:
    """Find support and resistance levels.

    Args:
        df: DataFrame with at least 'high' and 'low' columns.
        window: Number of bars on each side to confirm a swing high/low.
        tolerance: Max fractional distance to merge two price levels.

    Returns:
        {"support": [float, ...], "resistance": [float, ...]}
    """
    if len(df) < 2 * window + 1:
        last = float(df["close"].iloc[-1]) if "close" in df.columns else 0.0
        return {"support": [], "resistance": []}

    resistance = _cluster(_swing_highs(df["high"], window), tolerance)
    support = _cluster(_swing_lows(df["low"], window), tolerance)

    # Keep top-5 nearest to last close
    last_close = float(df["close"].iloc[-1]) if "close" in df.columns else 0.0

    def _sort_nearest(levels: list[float]) -> list[float]:
        return sorted(levels, key=lambda x: abs(x - last_close))[:5]

    return {
        "support": _sort_nearest(support),
        "resistance": _sort_nearest(resistance),
    }
