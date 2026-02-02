"""
Trade timeline visualization module.

Provides functions to plot price charts with moving averages,
golden/death cross markers, and trade entry/exit points.
"""
from __future__ import annotations

import os
import pandas as pd
import matplotlib.pyplot as plt


def plot_golden_cross_with_trades(
    df: pd.DataFrame,
    ticker: str,
    path: str,
    ma_fast: str = "MA50",
    ma_slow: str = "MA200",
    close_col: str = "Close",
    entry_col: str = "entry",
    exit_col: str = "exit",
) -> str:
    """
    Long-horizon chart: Close + MA50/MA200 + golden/death cross markers + entry/exit markers.
    Requires df to contain Close, MA50, MA200 and entry/exit (bool).
    """
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)

    dfx = df.copy().dropna(subset=[close_col, ma_fast, ma_slow])
    if len(dfx) < 5:
        raise ValueError("Not enough data after dropping NaNs for golden cross plot.")

    # Cross events
    spread = dfx[ma_fast] - dfx[ma_slow]
    prev = spread.shift(1)

    golden = (prev <= 0) & (spread > 0)   # MA50 crosses above MA200
    death = (prev >= 0) & (spread < 0)    # MA50 crosses below MA200

    has_entry = entry_col in dfx.columns
    has_exit = exit_col in dfx.columns

    plt.figure(figsize=(14, 6))
    plt.plot(dfx.index, dfx[close_col].values, label=f"{ticker} Close")
    plt.plot(dfx.index, dfx[ma_fast].values, label=ma_fast)
    plt.plot(dfx.index, dfx[ma_slow].values, label=ma_slow)

    if golden.any():
        plt.scatter(dfx.index[golden], dfx.loc[golden, close_col], marker="^", s=35, label="Golden Cross")
    if death.any():
        plt.scatter(dfx.index[death], dfx.loc[death, close_col], marker="v", s=35, label="Death Cross")

    if has_entry and dfx[entry_col].astype(bool).any():
        m = dfx[entry_col].astype(bool)
        plt.scatter(dfx.index[m], dfx.loc[m, close_col], marker="o", s=20, label="Entry")

    if has_exit and dfx[exit_col].astype(bool).any():
        m = dfx[exit_col].astype(bool)
        plt.scatter(dfx.index[m], dfx.loc[m, close_col], marker="x", s=30, label="Exit")

    plt.title(f"{ticker}: Golden/Death Cross and Trade Timeline")
    plt.legend()
    plt.savefig(path, dpi=220, bbox_inches="tight")
    plt.close()
    return path
