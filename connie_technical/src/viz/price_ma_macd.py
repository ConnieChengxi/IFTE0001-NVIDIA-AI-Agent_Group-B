"""
Price with moving averages and MACD visualization module.

Provides candlestick charts with MA overlays and MACD indicator panels
using mplfinance for professional-grade technical analysis plots.
"""
from __future__ import annotations

import os
from typing import Optional, Sequence

import numpy as np
import pandas as pd


def _ensure_dir(path: str) -> None:
    """Create directory for output path if it doesn't exist."""
    d = os.path.dirname(path)
    if d:
        os.makedirs(d, exist_ok=True)


def plot_price_ma_macd(
    df: pd.DataFrame,
    ticker: str = "NVDA",
    path: str = "outputs/price_ma_macd.png",
    ma_cols: Sequence[str] = ("MA20", "MA50", "MA200"),
    macd_col: str = "MACD",
    macd_signal_col: str = "MACD_Signal",
    macd_hist_col: Optional[str] = "MACD_Hist",
    use_volume: bool = False,
) -> str:
    """
    Create a 2-panel chart similar to common TA platforms:
      Panel 0: Candles + MA overlays
      Panel 1: MACD line + Signal line + Histogram + Zero line

    Required columns:
      - Open, High, Low, Close (candles)
      - MACD, MACD_Signal
      - MACD_Hist optional (if missing, it will be computed as MACD - MACD_Signal)
      - MA columns optional (only those found will be plotted)

    Returns:
      - saved file path
    """
    # Local import so the repo doesn't crash if mplfinance isn't installed
    try:
        import mplfinance as mpf
    except ImportError as e:
        raise ImportError(
            "Missing dependency: mplfinance. Install via `pip install mplfinance` "
            "and add it to requirements.txt."
        ) from e

    required_ohlc = {"Open", "High", "Low", "Close"}
    missing = required_ohlc - set(df.columns)
    if missing:
        raise ValueError(f"plot_price_ma_macd: missing required OHLC columns: {missing}")

    if macd_col not in df.columns or macd_signal_col not in df.columns:
        raise ValueError(
            f"plot_price_ma_macd: missing MACD columns: "
            f"{[c for c in (macd_col, macd_signal_col) if c not in df.columns]}"
        )

    d = df.copy()
    d = d.sort_index()

    # Ensure numeric
    for c in ["Open", "High", "Low", "Close", macd_col, macd_signal_col]:
        d[c] = pd.to_numeric(d[c], errors="coerce")

    # MACD histogram
    if macd_hist_col and macd_hist_col in d.columns:
        d[macd_hist_col] = pd.to_numeric(d[macd_hist_col], errors="coerce")
    else:
        macd_hist_col = "MACD_Hist"
        d[macd_hist_col] = d[macd_col] - d[macd_signal_col]

    # Build addplots
    apds = []

    # MA overlays (only plot those that exist)
    for ma in ma_cols:
        if ma in d.columns:
            d[ma] = pd.to_numeric(d[ma], errors="coerce")
            apds.append(mpf.make_addplot(d[ma], panel=0))

    # MACD panel
    # MACD line
    apds.append(
        mpf.make_addplot(
            d[macd_col],
            panel=1,
            color="#1f77b4",
            width=1.2,
            label="MACD"
        )
    )

    # Signal line
    apds.append(
        mpf.make_addplot(
            d[macd_signal_col],
            panel=1,
            color="#ff7f0e",
            width=1.2,
            label="Signal"
        )
    )

    # Histogram as bars (color handled by mplfinance default; keep neutral)
    hist = d[macd_hist_col]
    colors = np.where(hist >= 0, "#2ca02c", "#d62728")

    apds.append(
        mpf.make_addplot(
            hist,
            type="bar",
            panel=1,
            color=colors,
            alpha=0.6,
            label="Histogram"
        )
    )

    # Zero line
    apds.append(mpf.make_addplot(np.zeros(len(d)), panel=1, linestyle="--", color="gray", alpha=0.7, label="Zero"))

    _ensure_dir(path)

    mpf.plot(
        d,
        type="candle",
        addplot=apds,
        volume=use_volume and ("Volume" in d.columns),
        panel_ratios=(3, 1),
        figsize=(10, 5),
        title=f"{ticker}: Price + Moving Averages + MACD",
        ylabel="Price (USD)",
        ylabel_lower="MACD (12, 26, 9)",
        warn_too_much_data=300,
        savefig=dict(fname=path, dpi=180, bbox_inches="tight"),
        returnfig=True,
        )

    return path
