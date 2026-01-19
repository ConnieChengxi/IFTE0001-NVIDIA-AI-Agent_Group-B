# src/viz/equity.py
from __future__ import annotations

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt


def _to_series(x) -> pd.Series:
    if isinstance(x, pd.Series):
        return x.dropna()
    if isinstance(x, pd.DataFrame):
        # if a DF is passed accidentally, try common column names
        for c in ["equity", "Equity", "value", "Value", "Portfolio_Value", "portfolio_value"]:
            if c in x.columns:
                return x[c].astype(float).dropna()
        raise ValueError("DataFrame passed but no equity-like column found.")
    raise TypeError(f"Unsupported type: {type(x)}")


def _drawdown(equity: pd.Series) -> pd.Series:
    equity = equity.astype(float).dropna()
    peak = equity.cummax()
    dd = (equity / peak) - 1.0
    return dd


def plot_equity_log(
    bh: pd.Series,
    strat: pd.Series,
    title: str = "Equity (log scale)",
    path: str | None = None,
) -> None:
    """
    Plot Buy&Hold vs Strategy on log-scale. Inputs should already be normalized (start=1.0).
    """
    bh = _to_series(bh)
    strat = _to_series(strat)

    # align dates
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
