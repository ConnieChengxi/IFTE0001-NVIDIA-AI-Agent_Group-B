from __future__ import annotations

import numpy as np
import pandas as pd

from .utils import _require_cols, _to_series
from .indicators import (
    ema,
    rsi,
    macd,
    bollinger_bands,
    relative_volume,
    candlestick_engulfing,
    hammer_shooting_star,
    donchian_breakout,
)


def compute_regime_3state(
    df: pd.DataFrame,
    long_window: int = 200,
    buffer_pct: float = 0.01,
    *,
    ema_long: pd.Series | None = None,
) -> pd.Series:
    _require_cols(df, ["close"])
    close = pd.to_numeric(df["close"], errors="coerce").astype("float64")
    if ema_long is None:
        ema_long = ema(df, span=int(long_window), price_col="close")
    ema_long = pd.to_numeric(ema_long, errors="coerce").astype("float64").reindex(df.index)
    upper = ema_long * (1.0 + float(buffer_pct))
    lower = ema_long * (1.0 - float(buffer_pct))
    reg = np.where(close > upper, 1, np.where(close < lower, -1, 0)).astype("int8")
    return pd.Series(reg, index=df.index, name="regime", dtype="int8")


def compute_adaptive_threshold(
    vol: pd.Series,
    base_threshold: float,
    *,
    sensitivity: float = 0.4,
    min_mult: float = 0.85,
    max_mult: float = 1.20,
    n_factors: int = 4,
    min_req: float = 2.0,
    use_tanh: bool = True,
    median_vol_fit: float | None = None,
) -> pd.Series:
    vol = pd.to_numeric(vol, errors="coerce").astype("float64")
    median_vol = float(median_vol_fit) if median_vol_fit is not None else float(vol.replace(0.0, np.nan).median())
    if (not np.isfinite(median_vol)) or median_vol <= 0:
        thr = pd.Series(float(base_threshold), index=vol.index, dtype="float64")
        return thr.clip(lower=float(min_req), upper=float(n_factors))
    vol_norm = (vol / median_vol) - 1.0
    if bool(use_tanh):
        vol_norm = np.tanh(vol_norm)
    mult = (1.0 + float(sensitivity) * vol_norm).clip(float(min_mult), float(max_mult))
    thr = (float(base_threshold) * mult).astype("float64")
    return thr.clip(lower=float(min_req), upper=float(n_factors))


def generate_signals(
    df: pd.DataFrame,
    *,
    ema_fast: int = 50,
    ema_slow: int = 200,
    regime_buffer_pct: float = 0.01,
    rsi_window: int = 14,
    bb_window: int = 20,
    bb_nstd: float = 2.0,
    macd_fast: int = 12,
    macd_slow: int = 26,
    macd_signal: int = 9,
    vol_window: int = 20,
    use_patterns: bool = False,
    donchian_window: int = 20,
    use_volume_confirm: bool = False,
    vol_confirm_window: int = 20,
    vol_confirm_min_ratio: float = 1.1,
    enter_score: float = 2.8,
    exit_score: float = 1.0,
    vol_sensitivity: float = 0.4,
    min_mult: float = 0.85,
    max_mult: float = 1.20,
    min_req: float = 2.0,
    use_tanh: bool = True,
    regime_penalty: int = 1,
    hysteresis_buffer: int = 1,
    median_vol_fit: float | None = None,
) -> pd.DataFrame:
    _require_cols(df, ["close"])
    if int(macd_fast) >= int(macd_slow):
        raise ValueError("MACD requires macd_fast < macd_slow")
    if int(vol_window) <= 1:
        raise ValueError("vol_window must be > 1")

    idx = df.index
    price = pd.to_numeric(df["close"], errors="coerce").astype("float64")

    ema_f = ema(df, span=int(ema_fast), price_col="close").astype("float64")
    ema_s = ema(df, span=int(ema_slow), price_col="close").astype("float64")
    r = rsi(df, window=int(rsi_window), price_col="close").astype("float64")

    macd_hist = pd.to_numeric(
        macd(df, fast=int(macd_fast), slow=int(macd_slow), signal=int(macd_signal), price_col="close")["macd_hist"],
        errors="coerce",
    ).astype("float64").reindex(idx)

    bb_mid = pd.to_numeric(
        bollinger_bands(df, window=int(bb_window), num_std=float(bb_nstd), price_col="close")["bb_mid"],
        errors="coerce",
    ).astype("float64").reindex(idx)

    # Optional volume confirmation (entry-only): rel_vol >= threshold.
    if bool(use_volume_confirm):
        _require_cols(df, ["volume"])
        rel_vol = relative_volume(df, window=int(vol_confirm_window), volume_col="volume").reindex(idx)
        vol_entry_ok = (pd.to_numeric(rel_vol, errors="coerce").fillna(0.0) >= float(vol_confirm_min_ratio)).astype(bool)
    else:
        rel_vol = pd.Series(np.nan, index=idx, dtype="float64", name=f"rel_vol_{int(vol_confirm_window)}")
        vol_entry_ok = pd.Series(True, index=idx, dtype=bool, name="vol_entry_ok")

    # realised vol (annualised)
    ret_cc = price.pct_change().fillna(0.0)
    vol = (ret_cc.rolling(int(vol_window), min_periods=int(vol_window)).std(ddof=0) * np.sqrt(252.0)).astype("float64")

    regime = compute_regime_3state(df, long_window=int(ema_slow), buffer_pct=float(regime_buffer_pct), ema_long=ema_s)
    reg = regime.values

    # optional patterns (experimental)
    if bool(use_patterns):
        p_eng = candlestick_engulfing(df)
        p_hs = hammer_shooting_star(df)
        p_dc = donchian_breakout(df, window=int(donchian_window))
        pattern_bull = ((p_eng == 1) | (p_hs == 1) | (p_dc == 1)).reindex(idx).fillna(False)
        pattern_bear = ((p_eng == -1) | (p_hs == -1) | (p_dc == -1)).reindex(idx).fillna(False)
    else:
        pattern_bull = pd.Series(False, index=idx)
        pattern_bear = pd.Series(False, index=idx)

    trend_up = (ema_f > ema_s).fillna(False)
    pullback_ok = price < (bb_mid * 1.01)
    strength_ok = r > 45.0
    macd_ok = (macd_hist > 0).fillna(False)

    # score system
    n_factors = 5 if bool(use_patterns) else 4
    confirm_count = (pullback_ok.astype(int) + strength_ok.astype(int) + macd_ok.astype(int)).astype("int8")

    if bool(use_patterns):
        long_score = (trend_up.astype(int) + confirm_count.astype(int) + pattern_bull.astype(int)).astype("int8")

        threshold_eff = compute_adaptive_threshold(
            vol=vol,
            base_threshold=float(enter_score),
            sensitivity=float(vol_sensitivity),
            min_mult=float(min_mult),
            max_mult=float(max_mult),
            n_factors=n_factors,
            min_req=float(min_req),
            use_tanh=bool(use_tanh),
            median_vol_fit=median_vol_fit,
        ).fillna(float(np.clip(enter_score, min_req, 5)))

        req_k_base = np.ceil(threshold_eff.values).astype("int8")
        req_k_long_entry = req_k_base.copy()
        if int(regime_penalty) != 0:
            req_k_long_entry = np.where(reg == -1, req_k_long_entry + int(regime_penalty), req_k_long_entry)
        req_k_long_entry = np.clip(req_k_long_entry, 1, 5).astype("int8")

        exit_k = int(np.ceil(float(exit_score)))
        exit_k = max(1, min(exit_k, 5))
        req_k_long_hold = np.maximum(exit_k, req_k_long_entry - int(hysteresis_buffer))
        req_k_long_hold = np.clip(req_k_long_hold, 1, 5).astype("int8")

        long_entry_ok = (long_score.values >= req_k_long_entry) & vol_entry_ok.values
        long_hold_ok = long_score.values >= req_k_long_hold

        threshold_eff_series = threshold_eff
        req_k_entry_arr = req_k_long_entry
        req_k_hold_arr = req_k_long_hold

    else:
        # MAIN: score + hysteresis (entry=4, hold=2)
        score = (2 * trend_up.astype(int) + confirm_count.astype(int)).astype("int8")
        long_score = score

        entry_req = np.int8(4)
        hold_req = np.int8(2)

        threshold_eff_series = pd.Series(np.nan, index=idx, dtype="float64")
        req_k_entry_arr = np.full(len(df), int(entry_req), dtype="int8")
        req_k_hold_arr = np.full(len(df), int(hold_req), dtype="int8")

        long_entry_ok = (score.values >= entry_req) & vol_entry_ok.values
        long_hold_ok = score.values >= hold_req

    # state machine (NO SHIFT)
    pos = 0
    raw = np.zeros(len(df), dtype="int8")
    for i in range(len(df)):
        if pos == 0:
            pos = 1 if long_entry_ok[i] else 0
        else:
            pos = 1 if long_hold_ok[i] else 0
            if pos == 1 and bool(use_patterns) and bool(pattern_bear.iloc[i]):
                pos = 0
        raw[i] = pos

    out = pd.DataFrame(index=idx)
    out["signal_bin"] = pd.Series(raw, index=idx, dtype="int8")
    out["regime"] = regime.astype("int8")
    out["threshold_eff"] = threshold_eff_series.astype("float64")
    out["use_patterns"] = bool(use_patterns)
    out["n_factors"] = int(n_factors)
    out["pattern_bull"] = pattern_bull.astype(int).rename("pattern_bull")
    out["pattern_bear"] = pattern_bear.astype(int).rename("pattern_bear")
    out["long_score"] = long_score
    out["confirm_count"] = confirm_count
    out["req_k_long_entry"] = pd.Series(req_k_entry_arr, index=idx, dtype="int8")
    out["req_k_long_hold"] = pd.Series(req_k_hold_arr, index=idx, dtype="int8")
    out["ema_fast"] = ema_f
    out["ema_slow"] = ema_s
    out["macd_hist"] = macd_hist
    out["bb_mid"] = bb_mid
    out["rel_vol"] = pd.to_numeric(rel_vol, errors="coerce").astype("float64")
    out["vol_entry_ok"] = pd.Series(vol_entry_ok.values, index=idx, dtype=bool)
    return out


def build_exec_signals_from_multi(sig_df: pd.DataFrame, index: pd.DatetimeIndex) -> pd.DataFrame:
    s = sig_df.reindex(index)

    if "signal_bin" in s.columns:
        sig_raw = s["signal_bin"]
    elif "signal" in s.columns:
        sig_raw = s["signal"]
    else:
        raise ValueError("signals must contain 'signal_bin' (or legacy 'signal')")

    if "regime" not in s.columns:
        raise ValueError("signals must contain column: 'regime'")

    sig01 = pd.to_numeric(sig_raw, errors="coerce").fillna(0).astype(int).clip(lower=0, upper=1)
    reg = pd.to_numeric(s["regime"], errors="coerce").fillna(0).astype(int).clip(lower=-1, upper=1)

    position_decision = pd.Series(0.0, index=index, dtype="float64")

    # bull / neutral
    position_decision[(sig01 == 1) & (reg == 1)] = 1.0
    position_decision[(sig01 == 1) & (reg == 0)] = 0.5

    # bear: only strongest score gets a reduced position
    bear_scale = 0.25
    ls = pd.to_numeric(s.get("long_score", 0), errors="coerce").fillna(0).astype(int)
    position_decision[(sig01 == 1) & (reg == -1) & (ls == 5)] = float(bear_scale)
    position_decision[(reg == -1) & ~((sig01 == 1) & (ls == 5))] = 0.0

    position_decision[(sig01 == 0)] = 0.0

    out = pd.DataFrame(index=index)
    out["signal_bin"] = sig01.astype("int8")
    out["position_decision"] = position_decision
    out["regime"] = reg.astype("int8")
    return out


def apply_risk_management(
    df: pd.DataFrame,
    base_position: pd.Series,
    regime: pd.Series,
    *,
    target_vol: float = 0.15,
    vol_window: int = 20,
    max_leverage: float | pd.Series = 1.0,
    vol_floor: float = 0.02,
    bear_leverage_mult: float = 0.7,
) -> tuple[pd.Series, dict]:
    _require_cols(df, ["close"])
    idx = df.index
    close = _to_series(df["close"], idx, name="close", dtype="float64")
    base_position = _to_series(base_position, idx, name="base_position", dtype="float64").fillna(0.0)
    reg = _to_series(regime, idx, name="regime", dtype="float64").fillna(0.0)

    vw = int(vol_window)
    if vw <= 1:
        raise ValueError("vol_window must be > 1")

    ret = close.pct_change().fillna(0.0)
    vol_realised = ret.rolling(vw, min_periods=2).std(ddof=0) * np.sqrt(252.0)
    vol_realised = vol_realised.fillna(float(vol_floor)).clip(lower=float(vol_floor))

    cap = _to_series(max_leverage, idx, name="max_leverage_cap", dtype="float64").clip(lower=0.0).fillna(0.0)
    # Reduce leverage cap in bear regime (interpretable risk-off)
    if float(bear_leverage_mult) < 1.0:
        bear_mask = reg < 0
        cap = cap.where(~bear_mask, cap * float(bear_leverage_mult))
    lev_raw = float(target_vol) / vol_realised.replace(0.0, np.nan)
    lev = lev_raw.clip(lower=0.0).clip(upper=cap).fillna(0.0)
    desired = (base_position * lev).fillna(0.0).astype("float64").rename("desired_position")


    meta = {
        "avg_leverage": float(lev.mean()),
        "max_leverage_observed": float(lev.max()),
        "params": {
            "target_vol": float(target_vol),
            "vol_window": int(vol_window),
            "vol_min_periods": 2,
            "max_leverage_cap_max": float(cap.max()),
            "vol_floor": float(vol_floor),
            "bear_leverage_mult": float(bear_leverage_mult),
        },
    }
    return desired, meta
