"""
Backtesting Engine Module.

Implements a vectorized backtesting engine that supports continuous position sizing.
Handles transaction cost modeling, equity curve computation, and performance metrics.

Key features:
- Supports both binary (0/1) and continuous (0.0 to 1.0) position sizing
- Transaction costs modeled as basis points per turnover
- T+1 signal execution to avoid look-ahead bias
- Computes standard performance metrics (CAGR, Sharpe, MaxDrawdown, etc.)
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Dict, List, Tuple

import numpy as np
import pandas as pd


@dataclass
class BacktestConfig:
    """
    Configuration for backtest execution.

    Attributes:
        cost_bps: Transaction cost in basis points per unit of turnover
        initial_equity: Starting portfolio value (default 1.0 for normalized returns)
        annualization: Trading days per year for annualized metrics
    """
    cost_bps: float = 10.0
    initial_equity: float = 1.0
    annualization: int = 252


def _max_drawdown(equity: pd.Series) -> float:
    """Calculate maximum drawdown from equity curve as a negative decimal."""
    peak = equity.cummax()
    dd = (equity / peak) - 1.0
    return float(dd.min())


def build_position_from_signals(out: pd.DataFrame) -> pd.Series:
    """
    Build a position series with t+1 execution.

    If `weight` column exists:
      - position is continuous in [0,1] (or whatever weight is clipped to)
      - when state=1, position = weight[t]
      - when state=0, position = 0

    If no `weight`:
      - fallback to classic 0/1 position
    """
    out = out.copy()

    # Use shift with fill_value to avoid FutureWarning/downcasting
    entry_prev = out["entry"].shift(1, fill_value=False).astype(bool)
    exit_prev = out["exit"].shift(1, fill_value=False).astype(bool)

    has_weight = "weight" in out.columns
    if has_weight:
        w = out["weight"].astype(float).fillna(0.0)
        # Safety clip: keep within [0,1] by default
        w = w.clip(lower=0.0, upper=1.0)
    else:
        w = pd.Series(1.0, index=out.index)

    pos = np.zeros(len(out), dtype=float)
    state = 0

    for i in range(len(out)):
        if state == 0 and bool(entry_prev.iloc[i]):
            state = 1
        elif state == 1 and bool(exit_prev.iloc[i]):
            state = 0

        # dynamic sizing: when in position, apply today's weight
        pos[i] = (float(w.iloc[i]) if state == 1 else 0.0)

    return pd.Series(pos, index=out.index, name="position")


def extract_trades(out: pd.DataFrame) -> pd.DataFrame:
    """
    Extract trades based on crossing from 0 -> >0 and >0 -> 0.

    Note: with continuous weights, partial scale-in/out isn't treated as separate trades;
    this keeps trades interpretable.

    Args:
        out: DataFrame with 'position' and 'Close' columns.

    Returns:
        DataFrame with trade entries: entry_date, exit_date, entry_price, exit_price, trade_return.

    Raises:
        ValueError: If required columns are missing.
    """
    required = {"position", "Close"}
    missing = required - set(out.columns)
    if missing:
        raise ValueError(f"extract_trades: missing required columns: {missing}")

    trades: List[Dict[str, Any]] = []
    in_trade = False
    entry_date = None
    entry_price = None

    for dt, row in out.iterrows():
        pos = float(row["position"])
        if (not in_trade) and (pos > 0):
            in_trade = True
            entry_date = dt
            entry_price = float(row["Close"])
        elif in_trade and (pos == 0):
            exit_date = dt
            exit_price = float(row["Close"])
            trade_ret = (exit_price / entry_price) - 1.0
            trades.append(
                dict(
                    entry_date=entry_date,
                    exit_date=exit_date,
                    entry_price=float(entry_price),
                    exit_price=float(exit_price),
                    trade_return=float(trade_ret),
                )
            )
            in_trade = False
            entry_date, entry_price = None, None

    return pd.DataFrame(trades)


def compute_metrics(out: pd.DataFrame, cfg: BacktestConfig) -> Dict:
    """Compute performance metrics from backtest results."""
    if len(out) == 0:
        raise ValueError("Cannot compute metrics on empty DataFrame")

    daily = out["strategy_ret"].fillna(0.0)
    ann = float(cfg.annualization)

    final_equity = float(out["equity"].iloc[-1])
    years = len(out) / ann if len(out) > 0 else np.nan
    cagr = float(final_equity ** (1.0 / years) - 1.0) if years and years > 0 else np.nan

    vol = float(daily.std(ddof=0) * np.sqrt(ann))
    sharpe = float((daily.mean() * ann) / vol) if vol > 0 else np.nan

    mdd = _max_drawdown(out["equity"])
    hit_rate = float((daily > 0).mean())

    turnovers = out["turnovers"].fillna(0.0)
    # With continuous sizing, "number of trades" from turnovers is less meaningful,
    # but we keep it as a rough approximation.
    num_trades = int((turnovers > 0).sum() / 2)

    return dict(
        row=int(len(out)),
        cost_bps=float(cfg.cost_bps),
        initial_equity=float(cfg.initial_equity),
        final_equity=final_equity,
        CAGR=cagr,
        Sharpe=sharpe,
        MaxDrawdown=float(mdd),
        HitRate=hit_rate,
        NumTradesApprox=num_trades,
    )


def run_backtest(df: pd.DataFrame, cfg: BacktestConfig = BacktestConfig()) -> Tuple[pd.DataFrame, pd.DataFrame, Dict]:
    """
    Execute a backtest on signal data.

    Args:
        df: DataFrame with required columns:
            - Close: Asset price series
            - entry: Boolean entry signals
            - exit: Boolean exit signals
            - weight (optional): Continuous position sizing [0.0, 1.0]
        cfg: BacktestConfig with cost and equity parameters

    Returns:
        Tuple of (out_df, trades_df, metrics):
            - out_df: DataFrame with added columns (position, ret, equity, etc.)
            - trades_df: DataFrame of individual trades with entry/exit info
            - metrics: Dict with performance metrics (CAGR, Sharpe, MaxDrawdown, etc.)
    """
    out = df.copy()

    required_cols = {"Close", "entry", "exit"}
    missing = required_cols - set(out.columns)
    if missing:
        raise ValueError(f"Missing required columns for backtest: {missing}")

    # Build position (0/1 or 0..1 if weight exists)
    out["position"] = build_position_from_signals(out)

    # Asset returns
    out["ret"] = out["Close"].pct_change().fillna(0.0)

    # Turnover = abs(change in position). This naturally supports continuous sizing.
    out["turnovers"] = out["position"].diff().abs().fillna(0.0)

    # Costs proportional to turnover
    out["cost"] = (cfg.cost_bps / 10000.0) * out["turnovers"]

    # Strategy return
    out["strategy_ret"] = out["position"] * out["ret"] - out["cost"]

    # Equity curve
    out["equity"] = cfg.initial_equity * (1.0 + out["strategy_ret"]).cumprod()

    trades_df = extract_trades(out)
    metrics = compute_metrics(out, cfg)
    metrics["NumTrades"] = int(len(trades_df))
    return out, trades_df, metrics


def save_metrics(metrics: Dict, path: str) -> None:
    with open(path, "w") as f:
        json.dump(metrics, f, indent=2, default=str)
