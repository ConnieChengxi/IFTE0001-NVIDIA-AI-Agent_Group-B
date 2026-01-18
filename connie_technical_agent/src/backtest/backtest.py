from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Tuple, Dict

import numpy as np
import pandas as pd

@dataclass
class BacktestConfig:
    cost_bps: float = 10.0
    initial_equity: float = 1.0
    annualization: int = 252

def _max_drawdown(equity: pd.Series) -> float:
    peak = equity.cummax()
    dd = (equity / peak) - 1.0
    return float(dd.min())

def build_position_from_signals(out: pd.DataFrame) -> pd.Series:
    out = out.copy()
    out["entry_prev"] = out["entry"].shift(1).fillna(False).astype(bool)
    out["exit_prev"] = out["exit"].shift(1).fillna(False).astype(bool)

    pos = np.zeros(len(out), dtype=float)
    state = 0
    for i in range(len(out)):
        entry_prev = bool(out["entry_prev"].iloc[i])
        exit_prev = bool(out["exit_prev"].iloc[i])
        if state == 0 and entry_prev:
            state = 1
        elif state == 1 and exit_prev:
            state = 0
        pos[i] = state

    return pd.Series(pos, index=out.index, name="position")

def extract_trades(out: pd.DataFrame) -> pd.DataFrame:
    trades = []
    in_trade = False
    entry_date = None
    entry_price = None

    for dt, row in out.iterrows():
        if (not in_trade) and row["position"] == 1:
            in_trade = True
            entry_date = dt
            entry_price = row["Close"]
        elif in_trade and row["position"] == 0:
            exit_date = dt
            exit_price = row["Close"]
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
    out = df.copy()

    required_cols = {"Close", "entry", "exit"}
    missing = required_cols - set(out.columns)
    if missing:
        raise ValueError(f"Missing required columns for backtest: {missing}")

    out["position"] = build_position_from_signals(out)
    out["ret"] = out["Close"].pct_change().fillna(0.0)

    out["turnovers"] = out["position"].diff().abs().fillna(0.0)
    out["cost"] = (cfg.cost_bps / 10000.0) * out["turnovers"]

    out["strategy_ret"] = out["position"] * out["ret"] - out["cost"]
    out["equity"] = cfg.initial_equity * (1.0 + out["strategy_ret"]).cumprod()

    trades_df = extract_trades(out)
    metrics = compute_metrics(out, cfg)
    metrics["NumTrades"] = int(len(trades_df))
    return out, trades_df, metrics

def save_metrics(metrics: Dict, path: str) -> None:
    with open(path, "w") as f:
        json.dump(metrics, f, indent=2, default=str)
