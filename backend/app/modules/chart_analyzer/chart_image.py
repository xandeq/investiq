"""Geração de PNG de candlestick com matplotlib puro (sem mplfinance)."""
from __future__ import annotations

import io
import logging
from typing import Optional

import matplotlib
matplotlib.use("Agg")  # non-interactive backend — must be set before pyplot import

import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import pandas as pd
import numpy as np

logger = logging.getLogger(__name__)


def generate_chart_png(
    df: pd.DataFrame,
    ticker: str,
    setup: Optional[dict] = None,
    last_n_candles: int = 60,
) -> bytes:
    """Generate a candlestick PNG chart and return it as bytes.

    Args:
        df: DataFrame with columns: open, high, low, close, volume, ema20, ema50.
            Additional optional columns: support/resistance levels are extracted
            from the 'levels' dict passed via setup if needed.
        ticker: Asset ticker for the chart title.
        setup: Optional setup dict with keys: pattern, direction, entry, stop,
               target_1, target_2.
        last_n_candles: How many candles to display (most recent).

    Returns:
        PNG image as bytes. Never raises — logs and returns a minimal fallback
        chart on any error.
    """
    try:
        return _render_chart(df, ticker, setup, last_n_candles)
    except Exception as exc:
        logger.error("generate_chart_png failed for %s: %s", ticker, exc)
        return _render_fallback_chart(ticker, str(exc))


def _render_chart(
    df: pd.DataFrame,
    ticker: str,
    setup: Optional[dict],
    last_n_candles: int,
) -> bytes:
    # Slice to last N candles
    plot_df = df.tail(last_n_candles).reset_index(drop=True)

    required = {"open", "high", "low", "close", "volume"}
    missing = required - set(plot_df.columns)
    if missing:
        raise ValueError(f"DataFrame missing required columns: {missing}")

    n = len(plot_df)
    x = np.arange(n)

    # Setup figure with two subplots: price (top) and volume (bottom)
    fig, (ax_price, ax_vol) = plt.subplots(
        2, 1,
        figsize=(14, 8),
        gridspec_kw={"height_ratios": [3, 1]},
        facecolor="#1a1a2e",
    )
    fig.subplots_adjust(hspace=0.05)

    for ax in (ax_price, ax_vol):
        ax.set_facecolor("#16213e")
        ax.tick_params(colors="#cccccc", labelsize=8)
        for spine in ax.spines.values():
            spine.set_edgecolor("#2a2a4a")

    # --- Candlesticks ---
    candle_width = 0.6
    up_color = "#26a69a"    # teal for bull candles
    down_color = "#ef5350"  # red for bear candles

    for i in range(n):
        o = float(plot_df.loc[i, "open"])
        h = float(plot_df.loc[i, "high"])
        lo = float(plot_df.loc[i, "low"])
        c = float(plot_df.loc[i, "close"])

        color = up_color if c >= o else down_color

        # Wick (high-low)
        ax_price.plot([i, i], [lo, h], color=color, linewidth=0.8, zorder=2)

        # Body (open-close)
        body_bottom = min(o, c)
        body_height = abs(c - o) or 0.001  # avoid zero-height rect
        rect = mpatches.FancyBboxPatch(
            (i - candle_width / 2, body_bottom),
            candle_width,
            body_height,
            boxstyle="square,pad=0",
            facecolor=color,
            edgecolor=color,
            linewidth=0.5,
            zorder=3,
        )
        ax_price.add_patch(rect)

    # --- EMA lines ---
    if "ema20" in plot_df.columns:
        ax_price.plot(x, plot_df["ema20"].values, color="#42a5f5", linewidth=1.2,
                      label="EMA20", zorder=4)
    if "ema50" in plot_df.columns:
        ax_price.plot(x, plot_df["ema50"].values, color="#ffa726", linewidth=1.2,
                      label="EMA50", zorder=4)

    # --- Setup lines (entry, stop, targets) ---
    if setup:
        entry = setup.get("entry")
        stop = setup.get("stop")
        target_1 = setup.get("target_1")
        target_2 = setup.get("target_2")
        pattern = setup.get("pattern", "")
        direction = setup.get("direction", "")

        def _hline(val, color, label, ls="-", lw=1.4):
            if val is not None:
                ax_price.axhline(y=val, color=color, linestyle=ls, linewidth=lw,
                                 alpha=0.85, zorder=5, label=label)

        _hline(entry, "#66bb6a", f"Entrada {entry}", lw=1.6)
        _hline(stop, "#ef5350", f"Stop {stop}")
        _hline(target_1, "#ffee58", f"Alvo1 {target_1}")
        _hline(target_2, "#ffee58", f"Alvo2 {target_2}", ls="--")

    # --- Volume bars ---
    vol_colors = []
    for i in range(n):
        o = float(plot_df.loc[i, "open"])
        c = float(plot_df.loc[i, "close"])
        vol_colors.append(up_color if c >= o else down_color)

    ax_vol.bar(x, plot_df["volume"].values, color=vol_colors, alpha=0.7, width=0.8)
    ax_vol.set_xlim(-1, n)
    ax_vol.yaxis.set_major_formatter(
        plt.FuncFormatter(lambda v, _: f"{v/1e6:.1f}M" if v >= 1e6 else f"{v/1e3:.0f}K")
    )

    # --- X-axis ticks (show date labels if available) ---
    ax_price.set_xlim(-1, n)
    if "date" in plot_df.columns:
        step = max(1, n // 8)
        tick_idx = list(range(0, n, step))
        ax_price.set_xticks([])  # hide on price axis
        ax_vol.set_xticks(tick_idx)
        ax_vol.set_xticklabels(
            [str(plot_df.loc[i, "date"])[:10] for i in tick_idx],
            rotation=30,
            ha="right",
            fontsize=7,
            color="#cccccc",
        )
    else:
        ax_vol.set_xticks([])

    # --- Title ---
    title_parts = [ticker]
    if setup:
        pattern = setup.get("pattern", "")
        direction = setup.get("direction", "")
        if pattern:
            title_parts.append(f"{pattern} ({direction})")
    fig.suptitle(" — ".join(title_parts), color="#e0e0e0", fontsize=13, fontweight="bold", y=0.98)

    # --- Legend ---
    handles, labels = ax_price.get_legend_handles_labels()
    if handles:
        ax_price.legend(
            handles, labels,
            loc="upper left",
            fontsize=7,
            facecolor="#1a1a2e",
            edgecolor="#2a2a4a",
            labelcolor="#cccccc",
            framealpha=0.8,
        )

    # --- Render to bytes ---
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=120, bbox_inches="tight", facecolor=fig.get_facecolor())
    plt.close(fig)
    buf.seek(0)
    return buf.read()


def _render_fallback_chart(ticker: str, error_msg: str) -> bytes:
    """Return a minimal error placeholder PNG."""
    fig, ax = plt.subplots(figsize=(8, 4), facecolor="#1a1a2e")
    ax.set_facecolor("#16213e")
    ax.text(
        0.5, 0.5,
        f"Chart indisponível\n{ticker}\n{error_msg[:80]}",
        ha="center", va="center",
        color="#ef5350",
        fontsize=10,
        transform=ax.transAxes,
        wrap=True,
    )
    ax.set_axis_off()
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=80, bbox_inches="tight", facecolor=fig.get_facecolor())
    plt.close(fig)
    buf.seek(0)
    return buf.read()
