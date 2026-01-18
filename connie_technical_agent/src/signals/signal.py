# src/signals/signal.py
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import numpy as np
import pandas as pd


@dataclass
class SignalConfig:
    """
    A simple, interpretable long/flat signal model for a buy-side technical analyst.

    Indicators used (3-5):
      1) Regime filter: Close > MA200 (trend regime)
      2) Trend confirmation: MA20 > MA50
      3) Momentum confirmation: MACD > MACD_Signal
      4) Momentum/mean-reversion guardrail: RSI_14 between [rsi_entry_min, rsi_entry_max]
      5) Optional volatility filter: ATR% < atr_pct_max (avoid extreme volatility regimes)
    """
    rsi_entry_min: float = 40.0
    rsi_entry_max: float = 70.0

    # Exit triggers
    rsi_exit_overbought: float = 80.0
    stop_loss_pct: float = 0.10          # 10% from entry
    take_profit_pct: float = 0.30        # 30% from entry (optional)

    # Optional ATR% filter (set to None to disable)
    atr_window: int = 14
    atr_pct_max: Optional[float] = 0.08  # 8% of price


def _require_cols(df: pd.DataFrame, cols: set[str]) -> None:
    missing = cols - set(df.columns)
    if missing:
        raise ValueError(f"Missing required columns for build_signals: {missing}")


def _compute_atr_pct(df: pd.DataFrame, window: int = 14) -> pd.Series:
    """
    ATR% = ATR / Close
    Uses classic True Range with High/Low/Close.
    If High/Low are not available, returns NaNs (filter will auto-disable).
    """
    if not {"High", "Low", "Close"}.issubset(df.columns):
        return pd.Series(np.nan, index=df.index, name="ATR_PCT")

    high = df["High"].astype(float)
    low = df["Low"].astype(float)
    close = df["Close"].astype(float)
    prev_close = close.shift(1)

    tr = pd.concat(
        [
            (high - low).abs(),
            (high - prev_close).abs(),
            (low - prev_close).abs(),
        ],
        axis=1,
    ).max(axis=1)

    atr = tr.rolling(window=window, min_periods=window).mean()
    atr_pct = atr / close.replace(0, np.nan)
    return atr_pct.rename("ATR_PCT")


def build_signals(df: pd.DataFrame, cfg: SignalConfig = SignalConfig()) -> pd.DataFrame:
    """
    Build entry/exit boolean signals with NO look-ahead.
    The backtest engine should execute signals with a 1-day delay (t+1), which your
    backtest.build_position_from_signals() already does by shifting entry/exit by 1 day.

    Expected input columns (from your run_demo.py features):
      - Close, MA20, MA50, MA200, RSI_14, MACD, MACD_Signal
      - (optional for ATR filter): High, Low

    Output columns added:
      - entry (bool), exit (bool)
      - position_hint (0/1) purely diagnostic (NOT used by backtest)
      - entry_reason / exit_reason (strings, optional for reporting)
      - atr_pct (optional)
    """
    required = {"Close", "MA20", "MA50", "MA200", "RSI_14", "MACD", "MACD_Signal"}
    _require_cols(df, required)

    out = df.copy()

    close = out["Close"].astype(float)
    ma20 = out["MA20"].astype(float)
    ma50 = out["MA50"].astype(float)
    ma200 = out["MA200"].astype(float)
    rsi = out["RSI_14"].astype(float)
    macd = out["MACD"].astype(float)
    macd_sig = out["MACD_Signal"].astype(float)

    # Optional ATR% filter
    atr_pct = _compute_atr_pct(out, window=cfg.atr_window)
    out["ATR_PCT"] = atr_pct

    atr_ok = pd.Series(True, index=out.index)
    if cfg.atr_pct_max is not None:
        # If ATR% is all NaN (no High/Low), disable filter gracefully
        if atr_pct.notna().any():
            atr_ok = atr_pct < float(cfg.atr_pct_max)

    # -----------------------
    # Entry conditions
    # -----------------------
    regime_ok = close > ma200                      # long-term trend regime
    trend_ok = ma20 > ma50                         # medium-term trend confirmation
    momentum_ok = macd > macd_sig                  # momentum confirmation
    rsi_ok = (rsi >= cfg.rsi_entry_min) & (rsi <= cfg.rsi_entry_max)

    entry_raw = regime_ok & trend_ok & momentum_ok & rsi_ok & atr_ok

    # Entry trigger: cross from False -> True
    entry = entry_raw & (~entry_raw.shift(1).fillna(False))

    # -----------------------
    # Exit conditions (event-driven)
    # -----------------------
    # Soft exits: regime breakdown OR trend reversal OR MACD cross-down
    regime_break = close < ma200
    trend_break = ma20 < ma50
    macd_cross_down = macd < macd_sig

    # Guardrail exit: RSI extremely overbought
    rsi_overbought = rsi >= cfg.rsi_exit_overbought

    # Price-based exit will be applied using an internal position_hint state machine.
    # This does NOT look ahead; it uses current close and stored entry price.
    exit_event = regime_break | trend_break | macd_cross_down | rsi_overbought

    # -----------------------
    # Build position_hint + exits with stop/take-profit
    # -----------------------
    pos = np.zeros(len(out), dtype=int)
    exit_sig = np.zeros(len(out), dtype=bool)

    entry_price: Optional[float] = None
    state = 0

    for i, (dt, row) in enumerate(out.iterrows()):
        c = float(row["Close"])
        e = bool(entry.iloc[i])
        x_event = bool(exit_event.iloc[i])

        if state == 0:
            if e:
                state = 1
                entry_price = c
            pos[i] = state
            exit_sig[i] = False
            continue

        # state == 1
        assert entry_price is not None

        # stop / take-profit relative to entry
        stop_hit = (c / entry_price - 1.0) <= (-float(cfg.stop_loss_pct))
        tp_hit = (c / entry_price - 1.0) >= (float(cfg.take_profit_pct)) if cfg.take_profit_pct is not None else False

        if x_event or stop_hit or tp_hit:
            # exit signal at time t; backtest will execute at t+1
            exit_sig[i] = True
            state = 0
            entry_price = None
        else:
            exit_sig[i] = False

        pos[i] = state

    out["entry"] = entry.fillna(False).astype(bool)
    out["exit"] = pd.Series(exit_sig, index=out.index).fillna(False).astype(bool)

    # Diagnostics (not used by backtest, but helpful for charts/report)
    out["position_hint"] = pd.Series(pos, index=out.index).astype(int)

    # Optional reasons (simple and transparent)
    out["entry_reason"] = np.where(out["entry"], "Regime+Trend+MACD+RSI(+ATR)", "")
    out["exit_reason"] = np.where(out["exit"], "Exit rule triggered (regime/trend/MACD/RSI/stop/tp)", "")

    return out
