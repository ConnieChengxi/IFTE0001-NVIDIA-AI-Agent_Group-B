"""
Signal Generation Module.

Implements a hierarchical risk-aware signal generation system for technical trading.
Uses regime filtering (MA200), trend persistence (MA20/MA50), volatility targeting,
and soft de-risking controls (MACD, RSI, ATR) to compute continuous position weights.

Key features:
- Regime filter: Only allow exposure when Close > MA200
- Trend persistence: Enforce minimum exposure floor when MA20 > MA50
- Volatility targeting: Scale position size to maintain target annual volatility
- Soft de-risking: Reduce (not exit) on bearish MACD, high RSI, or extreme ATR
- Risk exits: ATR-based trailing stops and optional fixed stop-loss/take-profit
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import numpy as np
import pandas as pd


@dataclass
class SignalConfig:
    """
    Route A (Aggressive, no leverage):
      - If Close > MA200 and MA20 > MA50: enforce a minimum exposure floor (e.g., 0.60)
      - Use vol targeting to scale between [floor, 1.0] (no leverage)
      - MACD/RSI/ATR% only reduce/adjust weight (no hard entry gate)
      - Exit event is primarily regime break (Close < MA200) + risk exits (ATR trailing stop)

    Backtest must use `weight` for sizing (the backtest already does).
    """

    # Regime / trend definitions
    use_regime_ma200: bool = True

    # Vol targeting
    use_vol_target: bool = True
    vol_window: int = 20
    target_annual_vol: float = 0.35  # aggressive but no leverage
    max_weight: float = 1.0
    min_weight: float = 0.0

    # Route A: exposure floor when regime+trend are ON
    regime_trend_floor: float = 0.60  # <<< minimum weight in bull trend regime

    # Scaling factors (soft controls)
    weak_trend_scale: float = 0.85           # if Close>MA200 but MA20<=MA50, still hold but reduced
    bearish_momentum_scale: float = 0.75     # if MACD<signal, reduce (do not exit)

    # RSI shaping
    rsi_hot_1: float = 80.0
    rsi_hot_2: float = 90.0
    rsi_scale_hot_1: float = 0.90
    rsi_scale_hot_2: float = 0.75

    # Optional ATR% de-risking (weight only)
    atr_window: int = 14
    atr_pct_max: Optional[float] = None      # e.g. 0.12 to de-risk in extreme vol; None disables
    atr_high_scale: float = 0.70             # when ATR% too high, multiply weight by this

    # Cooldown (often unnecessary for trend-following; keep 0 for aggressive exposure)
    cooldown_days: int = 0

    # Fixed stop / TP (optional)
    stop_loss_pct: float = 0.12
    take_profit_pct: Optional[float] = None

    # ATR trailing stop
    use_atr_trailing_stop: bool = True
    atr_trail_mult: float = 3.5
    atr_trail_replaces_fixed_stop: bool = True


def _require_cols(df: pd.DataFrame, cols: set[str]) -> None:
    missing = cols - set(df.columns)
    if missing:
        raise ValueError(f"Missing required columns for build_signals: {missing}")


def _compute_atr(df: pd.DataFrame, window: int = 14) -> pd.Series:
    if not {"High", "Low", "Close"}.issubset(df.columns):
        return pd.Series(np.nan, index=df.index, name="ATR")

    high = df["High"].astype(float)
    low = df["Low"].astype(float)
    close = df["Close"].astype(float)
    prev_close = close.shift(1)

    tr = pd.concat(
        [(high - low).abs(), (high - prev_close).abs(), (low - prev_close).abs()],
        axis=1,
    ).max(axis=1)

    return tr.rolling(window=window, min_periods=window).mean().rename("ATR")


def build_signals(df: pd.DataFrame, cfg: SignalConfig = SignalConfig()) -> pd.DataFrame:
    """
    Generate trading signals with continuous position weights.

    This function implements a hierarchical signal generation system:
    1. Regime filter (MA200) determines if any exposure is allowed
    2. Trend persistence (MA20 > MA50) sets minimum exposure floor
    3. Volatility targeting scales base weight to maintain stable risk
    4. Soft de-risking reduces weight for bearish momentum, high RSI, extreme ATR
    5. State machine tracks risk exits (trailing stops, fixed stops)

    Args:
        df: DataFrame with required columns:
            - Close, High, Low (OHLC data)
            - MA20, MA50, MA200 (moving averages)
            - RSI_14 (14-period RSI)
            - MACD, MACD_Signal (MACD indicator)
        cfg: SignalConfig with strategy parameters

    Returns:
        DataFrame with added columns:
            - weight: Continuous position size [0.0, 1.0]
            - entry: Boolean entry signal (regime turned on)
            - exit: Boolean exit signal (regime off or risk exit)
            - position_hint: State machine position state
            - ATR, ATR_PCT: Average True Range and ATR as % of price
            - entry_reason, exit_reason: Diagnostic strings
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

    # ATR + ATR%
    atr = _compute_atr(out, window=cfg.atr_window)
    out["ATR"] = atr
    out["ATR_PCT"] = (atr / close.replace(0, np.nan)).rename("ATR_PCT")

    # Regime / trend
    regime_ok = (close > ma200) if cfg.use_regime_ma200 else pd.Series(True, index=out.index)
    trend_ok = ma20 > ma50
    bull_trend = regime_ok & trend_ok

    # Entry/exit events (event signals only; sizing handled by weight)
    entry_raw = regime_ok
    prev = entry_raw.shift(1, fill_value=False).astype(bool)
    entry = entry_raw.astype(bool) & (~prev)

    exit_event = ~regime_ok  # regime break

    # Base weight via vol targeting
    if cfg.use_vol_target:
        ret = close.pct_change()
        vol = ret.rolling(cfg.vol_window, min_periods=cfg.vol_window).std()

        target_daily_vol = float(cfg.target_annual_vol) / np.sqrt(252.0)
        base_w = (target_daily_vol / vol.replace(0, np.nan)).clip(
            lower=float(cfg.min_weight), upper=float(cfg.max_weight)
        ).fillna(0.0)
    else:
        base_w = pd.Series(float(cfg.max_weight), index=out.index)

    # Enforce exposure floor in bull trend regime
    w = base_w.copy()

    # Apply a floor in bull trend regime (no leverage, so cap at 1.0)
    floor = float(cfg.regime_trend_floor)
    w = w.where(~bull_trend, np.maximum(w, floor))

    # Outside bull trend but still above MA200, keep some exposure (softly reduced)
    w = w.where(bull_trend | (~regime_ok), w * float(cfg.weak_trend_scale))

    # If regime is off -> 0 exposure
    w = w.where(regime_ok, 0.0)

    # Soft de-risk scaling
    # Momentum: MACD bearish -> reduce
    w = w * np.where(macd >= macd_sig, 1.0, float(cfg.bearish_momentum_scale))

    # RSI hot -> reduce (avoid chasing)
    w = w * np.where((rsi >= float(cfg.rsi_hot_1)) & (rsi < float(cfg.rsi_hot_2)), float(cfg.rsi_scale_hot_1), 1.0)
    w = w * np.where(rsi >= float(cfg.rsi_hot_2), float(cfg.rsi_scale_hot_2), 1.0)

    # ATR% extreme vol -> reduce weight (optional)
    if cfg.atr_pct_max is not None and out["ATR_PCT"].notna().any():
        too_hot = out["ATR_PCT"] >= float(cfg.atr_pct_max)
        w = w * np.where(too_hot, float(cfg.atr_high_scale), 1.0)

    out["weight"] = pd.Series(w, index=out.index).clip(0.0, 1.0).fillna(0.0)

    # Risk exits state machine
    pos_hint = np.zeros(len(out), dtype=int)
    exit_sig = np.zeros(len(out), dtype=bool)

    entry_price: Optional[float] = None
    highest_close: Optional[float] = None
    state = 0
    cooldown_left = 0

    for i, (_dt, row) in enumerate(out.iterrows()):
        c = float(row["Close"])
        e = bool(entry.iloc[i])
        x_event = bool(exit_event.iloc[i])

        if cooldown_left > 0:
            cooldown_left -= 1

        if state == 0:
            if e and cooldown_left == 0:
                state = 1
                entry_price = c
                highest_close = c
            pos_hint[i] = state
            exit_sig[i] = False
            continue

        if entry_price is None:
            raise RuntimeError("entry_price is None while in position - this indicates a logic error")
        highest_close = max(highest_close, c) if highest_close is not None else c

        stop_hit = (c / entry_price - 1.0) <= (-float(cfg.stop_loss_pct))
        tp_hit = (
            (c / entry_price - 1.0) >= float(cfg.take_profit_pct)
            if cfg.take_profit_pct is not None
            else False
        )

        trail_hit = False
        if cfg.use_atr_trailing_stop:
            atr_i = float(row["ATR"]) if pd.notna(row.get("ATR", np.nan)) else np.nan
            if np.isfinite(atr_i) and highest_close is not None:
                stop_level = highest_close - float(cfg.atr_trail_mult) * atr_i
                trail_hit = c < stop_level

        if cfg.use_atr_trailing_stop and cfg.atr_trail_replaces_fixed_stop:
            risk_exit = trail_hit or tp_hit
        else:
            risk_exit = stop_hit or trail_hit or tp_hit

        if x_event or risk_exit:
            exit_sig[i] = True
            state = 0
            entry_price = None
            highest_close = None
            cooldown_left = int(cfg.cooldown_days)
        else:
            exit_sig[i] = False

        pos_hint[i] = state

    out["entry"] = entry.fillna(False).astype(bool)
    out["exit"] = pd.Series(exit_sig, index=out.index).fillna(False).astype(bool)
    out["position_hint"] = pd.Series(pos_hint, index=out.index).astype(int)

    out["entry_reason"] = np.where(out["entry"], "Regime ON (Close>MA200) + RouteA floor sizing", "")
    out["exit_reason"] = np.where(out["exit"], "Regime OFF (Close<MA200) or risk exit (trail/stop/tp)", "")

    return out
