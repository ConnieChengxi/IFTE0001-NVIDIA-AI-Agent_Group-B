from __future__ import annotations

import pandas as pd

from .utils import _require_cols
from .signals import apply_risk_management
from .backtest import run_backtest, reconstruct_trades_aligned

def run_engine_light(
    df: pd.DataFrame,
    signals_exec: pd.DataFrame,
    *,
    trading_cost: float,
    initial_capital: float,
    target_vol: float = 0.15,
    vol_window: int = 20,
    max_leverage: float | pd.Series = 1.0,
    vol_floor: float = 0.02,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    For tuning only:
    - compute position_decision (vol targeting)
    - run strategy bt
    - reconstruct trades
    Returns: (bt, trades)
    """
    # signals_exec is decision-time. We expect an explicit target position column.
    # New naming: position_decision. Legacy alias: position_dec.
    if ("position_decision" not in signals_exec.columns) and ("position_dec" in signals_exec.columns):
        base_col = "position_dec"
    else:
        base_col = "position_decision"

    _require_cols(signals_exec, [base_col, "regime"])
    base_position = pd.to_numeric(signals_exec[base_col], errors="coerce").fillna(0.0).clip(lower=0.0)
    position_decision, _rm_meta = apply_risk_management(
        df=df,
        base_position=base_position,
        regime=signals_exec["regime"],
        target_vol=target_vol,
        vol_window=vol_window,
        max_leverage=max_leverage,
        vol_floor=vol_floor,
    )
    bt = run_backtest(df=df, position=position_decision, trading_cost=trading_cost, initial_capital=initial_capital)
    trades = reconstruct_trades_aligned(bt)
    return bt, trades

def run_engine_full(
    df: pd.DataFrame,
    signals_exec: pd.DataFrame,
    *,
    trading_cost: float,
    initial_capital: float,
    target_vol: float = 0.15,
    vol_window: int = 20,
    max_leverage: float | pd.Series = 1.0,
    vol_floor: float = 0.02,
) -> dict:
    """
    For final run only:
    Returns everything report needs, once.
    """
    # signals_exec is decision-time. We expect an explicit target position column.
    # New naming: position_decision. Legacy alias: position_dec.
    if ("position_decision" not in signals_exec.columns) and ("position_dec" in signals_exec.columns):
        base_col = "position_dec"
    else:
        base_col = "position_decision"

    _require_cols(signals_exec, [base_col, "regime"])
    base_position = pd.to_numeric(signals_exec[base_col], errors="coerce").fillna(0.0).clip(lower=0.0)
    position_decision, rm_meta = apply_risk_management(
        df=df,
        base_position=base_position,
        regime=signals_exec["regime"],
        target_vol=target_vol,
        vol_window=vol_window,
        max_leverage=max_leverage,
        vol_floor=vol_floor,
    )

    bt = run_backtest(df=df, position=position_decision, trading_cost=trading_cost, initial_capital=initial_capital)

    # FAIR benchmark: decision-time constant long, execution delay handled inside run_backtest() via shift(1)
    bm = run_backtest(
        df=df,
        position=pd.Series(1.0, index=df.index, dtype="float64"),
        trading_cost=trading_cost,
        initial_capital=initial_capital,
    )

    trades = reconstruct_trades_aligned(bt)

    meta = {
        "assumptions": {
            "returns": "close-to-close",
            "alignment": "signals are decision-time (NO SHIFT); run_backtest shifts once for execution",
            "benchmark": "fair buy&hold implemented via run_backtest(constant_long) with the same 1-bar execution delay",
            "cost_model": "commission-like: trading_cost * turnover",
        },
        "risk_management": rm_meta,
    }

    return {"position_decision": position_decision, "backtest": bt, "benchmark": bm, "trades": trades, "metadata": meta}
