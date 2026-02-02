"""
Equity and drawdown visualization module.

Provides functions to plot equity curves and drawdown comparisons
for strategy vs buy-and-hold performance analysis.
"""
from __future__ import annotations

from typing import Union

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt


def _to_series(x: Union[pd.Series, pd.DataFrame]) -> pd.Series:
    """Convert input to a float Series, extracting equity column if DataFrame."""
    if isinstance(x, pd.Series):
        return x.astype(float).dropna()
    if isinstance(x, pd.DataFrame):
        for c in ["equity", "Equity", "value", "Value", "Portfolio_Value", "portfolio_value"]:
            if c in x.columns:
                return x[c].astype(float).dropna()
        raise ValueError("DataFrame passed but no equity-like column found.")
    raise TypeError(f"Unsupported type: {type(x)}")


def _drawdown(equity: pd.Series) -> pd.Series:
    """Calculate drawdown series from equity curve."""
    equity = equity.astype(float).dropna()
    peak = equity.cummax()
    return (equity / peak) - 1.0


def plot_equity_log(
    bh: pd.Series,
    strat: pd.Series,
    title: str = "Equity (log scale)",
    path: str | None = None,
) -> None:
    """
    Plot Buy&Hold vs Strategy on log-scale. Inputs should be normalized (start=1.0).
    """
    bh = _to_series(bh)
    strat = _to_series(strat)

    idx = bh.index.intersection(strat.index)
    bh = bh.reindex(idx)
    strat = strat.reindex(idx)

    plt.figure(figsize=(12, 5))
    plt.plot(idx, bh.values, label="Buy & Hold (start=1.0)")
    plt.plot(idx, strat.values, label="Strategy (start=1.0)")
    plt.yscale("log")
    plt.title(title)
    plt.xlabel("Date")
    plt.ylabel("Equity (log scale)")
    plt.legend()
    plt.grid(True, which="both", linestyle="--", alpha=0.4)
    plt.tight_layout()

    if path:
        plt.savefig(path, dpi=200, bbox_inches="tight")
        plt.close()
    else:
        plt.show()


def plot_drawdown_compare(
    bh: pd.Series,
    strat: pd.Series,
    title: str = "Drawdown Comparison",
    path: str | None = None,
) -> None:
    """
    Plot drawdowns of Buy&Hold vs Strategy. Inputs should be normalized (start=1.0).
    """
    bh = _to_series(bh)
    strat = _to_series(strat)

    idx = bh.index.intersection(strat.index)
    bh = bh.reindex(idx)
    strat = strat.reindex(idx)

    dd_bh = _drawdown(bh)
    dd_strat = _drawdown(strat)

    plt.figure(figsize=(12, 4))
    plt.plot(idx, dd_bh.values, label="Buy & Hold DD")
    plt.plot(idx, dd_strat.values, label="Strategy DD")
    plt.title(title)
    plt.xlabel("Date")
    plt.ylabel("Drawdown")
    plt.legend()
    plt.grid(True, linestyle="--", alpha=0.4)
    plt.tight_layout()

    if path:
        plt.savefig(path, dpi=200, bbox_inches="tight")
        plt.close()
    else:
        plt.show()


def plot_combined_equity_drawdown(
    bh: pd.Series,
    strat: pd.Series,
    ticker: str = "",
    path: str | None = None,
) -> None:
    """
    Combined 2-panel chart:
    1. Log-scaled equity curve (strategy vs. buy-and-hold) - return comparison
    2. Drawdown comparison (strategy vs. buy-and-hold) - risk comparison

    Inputs should be normalized (start=1.0).
    """
    bh = _to_series(bh)
    strat = _to_series(strat)

    idx = bh.index.intersection(strat.index)
    bh = bh.reindex(idx)
    strat = strat.reindex(idx)

    dd_bh = _drawdown(bh)
    dd_strat = _drawdown(strat)

    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 8), sharex=True)

    # Panel 1: Log-scaled equity curve
    ax1.plot(idx, bh.values, label="Buy & Hold", linewidth=1.5)
    ax1.plot(idx, strat.values, label="Strategy", linewidth=1.5)
    ax1.set_yscale("log")
    ax1.set_title(f"{ticker} Equity Comparison (log scale)")
    ax1.set_ylabel("Equity (log scale)")
    ax1.legend(loc="upper left")
    ax1.grid(True, which="both", linestyle="--", alpha=0.4)

    # Panel 2: Drawdown comparison (lines only, no fill)
    ax2.plot(idx, dd_bh.values, linewidth=1.5, label="Buy & Hold DD")
    ax2.plot(idx, dd_strat.values, linewidth=1.5, label="Strategy DD")
    ax2.axhline(y=0, color='black', linewidth=0.5)
    ax2.set_title("Drawdown Comparison")
    ax2.set_xlabel("Date")
    ax2.set_ylabel("Drawdown")
    ax2.legend(loc="lower left")
    ax2.grid(True, linestyle="--", alpha=0.4)

    plt.tight_layout()

    if path:
        plt.savefig(path, dpi=200, bbox_inches="tight")
        plt.close(fig)
    else:
        plt.show()
