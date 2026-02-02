from __future__ import annotations

import numpy as np
import pandas as pd

from .utils import _require_cols, _to_series


def run_backtest(
    df: pd.DataFrame,
    position: pd.Series,
    *,
    trading_cost: float = 0.0005,
    initial_capital: float = 1.0,
) -> pd.DataFrame:
    """Core backtest (long/flat), with strict timing convention.

    Convention:
      - Caller passes DECISION-TIME position (no shift).
      - We shift ONCE inside this function to simulate next-bar execution.

    Returns a DataFrame with:
      position (executed), turnover, cost_ret, strategy_ret, equity, drawdown
    """
    _require_cols(df, ["close"])
    idx = df.index

    close = _to_series(df["close"], idx, name="close", dtype="float64")

    # Always recompute close-to-close returns from the provided close series.
    # This guarantees consistency even if other parts of the pipeline accidentally add/overwrite a 'ret' column.
    ret = close.pct_change().fillna(0.0).rename("ret")

    # Caller passes DECISION-TIME target position (no shift). Execution delay is applied here.
    position_decision = _to_series(position, idx, name="position_decision", dtype="float64").fillna(0.0)
    pos_exec = position_decision.shift(1).fillna(0.0).rename("position")

    turnover = pos_exec.diff().abs()
    if len(turnover) > 0:
        turnover.iloc[0] = abs(float(pos_exec.iloc[0]))
    turnover = turnover.fillna(0.0).rename("turnover")

    cost_ret = (float(trading_cost) * turnover).rename("cost_ret")
    strat_ret = (pos_exec * ret - cost_ret).rename("strategy_ret")

    equity = (float(initial_capital) * (1.0 + strat_ret).cumprod()).rename("equity")
    drawdown = (equity / equity.cummax() - 1.0).rename("drawdown")

    return pd.DataFrame(
        {
            "position": pos_exec,
            "turnover": turnover,
            "ret": ret,
            "cost_ret": cost_ret,
            "strategy_ret": strat_ret,
            "equity": equity,
            "drawdown": drawdown,
        },
        index=idx,
    )


def run_buy_and_hold_benchmark(
    df: pd.DataFrame,
    *,
    trading_cost: float = 0.0005,
    initial_capital: float = 1.0,
) -> pd.DataFrame:
    """Buy & hold benchmark aligned to the same return series and cost model (1-bar delayed execution)."""
    _require_cols(df, ["close"])
    idx = df.index

    close = _to_series(df["close"], idx, name="close", dtype="float64")

    # Always recompute close-to-close returns from the provided close series.
    # This guarantees consistency even if other parts of the pipeline accidentally add/overwrite a 'ret' column.
    ret = close.pct_change().fillna(0.0).rename("ret")

    # Decision-time constant long, executed with the same 1-bar delay as the strategy.
    position_decision = pd.Series(1.0, index=idx, name="position_decision", dtype="float64")
    pos_exec = position_decision.shift(1).fillna(0.0).rename("position")

    turnover = pos_exec.diff().abs()
    if len(turnover) > 0:
        turnover.iloc[0] = abs(float(pos_exec.iloc[0]))
    turnover = turnover.fillna(0.0).rename("turnover")

    cost_ret = (float(trading_cost) * turnover).rename("cost_ret")
    strat_ret = (pos_exec * ret - cost_ret).rename("strategy_ret")

    equity = (float(initial_capital) * (1.0 + strat_ret).cumprod()).rename("equity")
    drawdown = (equity / equity.cummax() - 1.0).rename("drawdown")

    return pd.DataFrame(
        {
            "position": pos_exec,
            "turnover": turnover,
            "ret": ret,
            "cost_ret": cost_ret,
            "strategy_ret": strat_ret,
            "equity": equity,
            "drawdown": drawdown,
        },
        index=idx,
    )


def reconstruct_trades_aligned(
    bt: pd.DataFrame,
    *,
    pos_col: str = "position",
    net_ret_col: str = "strategy_ret",
    eps: float = 1e-12,
) -> pd.DataFrame:
    for c in [pos_col, net_ret_col]:
        if c not in bt.columns:
            raise ValueError(f"bt missing required column: {c}")

    idx = bt.index
    pos = pd.to_numeric(bt[pos_col], errors="coerce").fillna(0.0).astype("float64").values
    net = pd.to_numeric(bt[net_ret_col], errors="coerce").fillna(0.0).astype("float64").values

    def sgn(x: float) -> int:
        if abs(x) <= eps:
            return 0
        return 1 if x > 0 else -1

    trades: list[dict] = []
    in_trade = False
    start_i = 0
    direction = 0

    for i in range(len(idx)):
        si = sgn(pos[i])
        if not in_trade:
            if si != 0:
                in_trade = True
                start_i = i
                direction = si
            continue
        if si == 0 or si != direction:
            end_i = i - 1
            if end_i >= start_i:
                seg = slice(start_i, end_i + 1)
                entry_bar = idx[start_i]
                exit_bar = idx[end_i]
                pnl_net = float(np.prod(1.0 + net[seg]) - 1.0)
                trades.append(
                    {
                        "entry_bar": entry_bar,
                        "exit_bar": exit_bar,
                        "direction": float(direction),
                        "holding_bars": int(end_i - start_i + 1),
                        "holding_days": float((exit_bar - entry_bar).days),
                        "pnl_pct_net": pnl_net,
                    }
                )
            in_trade = False
            direction = 0
            if si != 0:
                in_trade = True
                start_i = i
                direction = si

    if in_trade:
        end_i = len(idx) - 1
        seg = slice(start_i, end_i + 1)
        entry_bar = idx[start_i]
        exit_bar = idx[end_i]
        pnl_net = float(np.prod(1.0 + net[seg]) - 1.0)
        trades.append(
            {
                "entry_bar": entry_bar,
                "exit_bar": exit_bar,
                "direction": float(direction),
                "holding_bars": int(end_i - start_i + 1),
                "holding_days": float((exit_bar - entry_bar).days),
                "pnl_pct_net": pnl_net,
            }
        )

    return pd.DataFrame(trades)


def trade_performance_summary(trades: pd.DataFrame) -> dict:
    if trades is None or len(trades) == 0:
        return {"num_trades": 0, "hit_rate": np.nan, "avg_holding_days": np.nan}
    for c in ["pnl_pct_net", "holding_days"]:
        if c not in trades.columns:
            raise ValueError(f"trades missing required column: {c}")
    pnl = pd.to_numeric(trades["pnl_pct_net"], errors="coerce").dropna()
    holding = pd.to_numeric(trades["holding_days"], errors="coerce")
    hit_rate = float((pnl > 0).mean()) if len(pnl) else np.nan
    avg_holding_days = float(holding.mean()) if len(holding.dropna()) else np.nan
    return {"num_trades": int(len(trades)), "hit_rate": hit_rate, "avg_holding_days": avg_holding_days}


def slice_trades_to_window(trades_df: pd.DataFrame | None, start_dt, end_dt):
    if trades_df is None or len(trades_df) == 0:
        return trades_df
    if "entry_bar" not in trades_df.columns or "exit_bar" not in trades_df.columns:
        raise ValueError("trades_df must contain 'entry_bar' and 'exit_bar'")
    entry = pd.to_datetime(trades_df["entry_bar"], errors="coerce")
    exit_ = pd.to_datetime(trades_df["exit_bar"], errors="coerce")
    start_dt = pd.to_datetime(start_dt)
    end_dt = pd.to_datetime(end_dt)
    mask = (entry <= end_dt) & (exit_ >= start_dt)
    return trades_df.loc[mask].copy()


def performance_summary(bt: pd.DataFrame, rf_annual: float = 0.0, trades: pd.DataFrame | None = None) -> dict:
    """Compute performance metrics.

    Conventions (IMPORTANT):
      - total_return and CAGR are DECIMALS (e.g., 0.75 means 75%).
      - equity_end is the final equity value starting from initial_capital (usually 1.0).
    """
    required = ["equity", "strategy_ret"]
    missing = [c for c in required if c not in bt.columns]
    if missing:
        raise ValueError(f"bt must contain columns: {missing}")

    eq = pd.to_numeric(bt["equity"], errors="coerce").replace([np.inf, -np.inf], np.nan).dropna()
    r = pd.to_numeric(bt["strategy_ret"], errors="coerce").replace([np.inf, -np.inf], np.nan).fillna(0.0)
    if len(eq) < 2:
        return {}

    # infer initial capital robustly (keeps compatibility even if first return isn't 0)
    r0 = float(r.iloc[0]) if len(r) else 0.0
    denom = 1.0 + r0
    initial_capital = float(eq.iloc[0] / denom) if (np.isfinite(denom) and denom > 0) else float(eq.iloc[0])

    equity_end = float(eq.iloc[-1])

    # Total return as DECIMAL (e.g., 275.72 means +27,572%)
    total_return = float(equity_end / initial_capital - 1.0)

    days = int((eq.index[-1] - eq.index[0]).days)
    years_cal = (days / 365.25) if days > 0 else np.nan
    cagr = (equity_end / initial_capital) ** (1.0 / years_cal) - 1.0 if (years_cal and years_cal > 0) else np.nan

    vol = float(r.std(ddof=0) * np.sqrt(252.0))
    rf_daily = (1.0 + float(rf_annual)) ** (1.0 / 252.0) - 1.0
    excess = r - rf_daily
    sharpe = float(excess.mean() / (excess.std(ddof=0) + 1e-12) * np.sqrt(252.0))

    max_dd = (
        float(pd.to_numeric(bt["drawdown"], errors="coerce").replace([np.inf, -np.inf], np.nan).min())
        if "drawdown" in bt.columns
        else np.nan
    )

    exposure = np.nan
    if "position" in bt.columns:
        pos = pd.to_numeric(bt["position"], errors="coerce").replace([np.inf, -np.inf], np.nan).fillna(0.0)
        exposure = float((pos.abs() > 1e-9).mean())

    turnover_sum = np.nan
    if "turnover" in bt.columns:
        turnover_sum = float(pd.to_numeric(bt["turnover"], errors="coerce").replace([np.inf, -np.inf], np.nan).fillna(0.0).sum())

    r_clean = r.replace([np.inf, -np.inf], np.nan).dropna()
    skew = float(r_clean.skew()) if len(r_clean) else np.nan
    kurt_excess = float(r_clean.kurtosis()) if len(r_clean) else np.nan

    hit_rate = np.nan
    num_trades = np.nan
    avg_holding_days = np.nan
    try:
        tdf = trades if trades is not None else reconstruct_trades_aligned(bt)
        ts = trade_performance_summary(tdf)
        hit_rate = float(ts.get("hit_rate", np.nan))
        num_trades = float(ts.get("num_trades", np.nan))
        avg_holding_days = float(ts.get("avg_holding_days", np.nan))
    except Exception:
        pass

    return {
        "equity_end": equity_end,
        "total_return": total_return,
        "CAGR": float(cagr) if cagr == cagr else np.nan,
        "Sharpe": sharpe,
        "vol": vol,
        "max_drawdown": max_dd,
        "hit_rate": hit_rate,
        "num_trades": num_trades,
        "avg_holding_days": avg_holding_days,
        "exposure": exposure,
        "turnover_sum": turnover_sum,
        "skew": skew,
        "kurt_excess": kurt_excess,
    }


def sharpe_from_bt(bt_slice: pd.DataFrame, rf_annual: float = 0.0, min_len: int = 60) -> float:
    if "strategy_ret" not in bt_slice.columns:
        raise ValueError("bt_slice must contain 'strategy_ret'")
    r = pd.to_numeric(bt_slice["strategy_ret"], errors="coerce").replace([np.inf, -np.inf], np.nan).dropna()
    if len(r) < int(min_len):
        return -np.inf
    std = float(r.std(ddof=0))
    if std == 0.0:
        return -np.inf
    rf_daily = (1.0 + float(rf_annual)) ** (1.0 / 252.0) - 1.0
    excess = r - rf_daily
    return float(excess.mean() / (float(excess.std(ddof=0)) + 1e-12) * np.sqrt(252.0))
