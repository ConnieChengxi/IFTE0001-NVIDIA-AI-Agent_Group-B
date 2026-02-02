from __future__ import annotations

import numpy as np
import pandas as pd

from .utils import _require_cols


# =========================================================
# Price-based indicators
# =========================================================
# Clean, submission-friendly convention:
# - Indicators accept either a pd.Series (assumed to be a price series) OR
#   a pd.DataFrame plus `price_col`.
# - This avoids Series/DataFrame confusion in research scripts while keeping
#   the pipeline single-source-of-truth on `close`.


def _price_series(x: pd.DataFrame | pd.Series, price_col: str = "close") -> pd.Series:
    """Return a float64 price series from either a DataFrame or a Series."""
    if isinstance(x, pd.Series):
        s = x
    elif isinstance(x, pd.DataFrame):
        _require_cols(x, [price_col])
        s = x[price_col]
    else:
        raise TypeError("Expected a pandas Series or DataFrame")

    s = pd.to_numeric(s, errors="coerce").astype("float64")
    # Ensure a name for nicer downstream debugging
    if s.name is None:
        s = s.rename(price_col)
    return s


def ema(x: pd.DataFrame | pd.Series, span: int, price_col: str = "close") -> pd.Series:
    """Exponential moving average."""
    if int(span) <= 0:
        raise ValueError("span must be > 0")
    close = _price_series(x, price_col=price_col)
    return close.ewm(span=int(span), adjust=False).mean().rename(f"ema_{int(span)}")


def rsi(x: pd.DataFrame | pd.Series, window: int = 14, price_col: str = "close") -> pd.Series:
    """Wilder-style RSI using simple rolling means (stable, interpretable)."""
    if int(window) <= 0:
        raise ValueError("window must be > 0")
    close = _price_series(x, price_col=price_col)

    delta = close.diff()
    gain = delta.clip(lower=0.0)
    loss = (-delta).clip(lower=0.0)

    w = int(window)
    avg_gain = gain.rolling(window=w, min_periods=w).mean()
    avg_loss = loss.rolling(window=w, min_periods=w).mean()

    rs = avg_gain / avg_loss.replace(0.0, np.nan)
    out = 100.0 - (100.0 / (1.0 + rs))

    # edge cases
    out = out.copy()
    out.loc[(avg_loss == 0.0) & (avg_gain > 0.0)] = 100.0
    out.loc[(avg_loss == 0.0) & (avg_gain == 0.0)] = 50.0
    out.loc[(avg_gain == 0.0) & (avg_loss > 0.0)] = 0.0

    return out.rename(f"rsi_{w}")


def macd(
    x: pd.DataFrame | pd.Series,
    fast: int = 12,
    slow: int = 26,
    signal: int = 9,
    price_col: str = "close",
) -> pd.DataFrame:
    """MACD (line, signal, histogram)."""
    fast, slow, signal = int(fast), int(slow), int(signal)
    if fast <= 0 or slow <= 0 or signal <= 0:
        raise ValueError("MACD params must be > 0")
    if fast >= slow:
        raise ValueError("MACD requires fast < slow")

    close = _price_series(x, price_col=price_col)

    ema_fast = close.ewm(span=fast, adjust=False).mean()
    ema_slow = close.ewm(span=slow, adjust=False).mean()
    macd_line = ema_fast - ema_slow
    sig_line = macd_line.ewm(span=signal, adjust=False).mean()
    hist = macd_line - sig_line

    idx = close.index
    return pd.DataFrame(
        {"macd": macd_line, "macd_signal": sig_line, "macd_hist": hist},
        index=idx,
    )


def bollinger_bands(
    x: pd.DataFrame | pd.Series,
    window: int = 20,
    num_std: float = 2.0,
    price_col: str = "close",
) -> pd.DataFrame:
    """Bollinger Bands (mid, upper, lower).

    Returns both canonical column names used in the project:
      - bb_mid, bb_upper, bb_lower
    And convenience aliases:
      - mid, upper, lower
    """
    w = int(window)
    if w <= 0:
        raise ValueError("window must be > 0")
    if float(num_std) <= 0:
        raise ValueError("num_std must be > 0")

    close = _price_series(x, price_col=price_col)

    mid = close.rolling(window=w, min_periods=w).mean()
    std = close.rolling(window=w, min_periods=w).std(ddof=0)
    upper = mid + float(num_std) * std
    lower = mid - float(num_std) * std

    idx = close.index
    return pd.DataFrame(
        {
            "bb_mid": mid,
            "bb_upper": upper,
            "bb_lower": lower,
            # convenience aliases for notebooks / ad-hoc checks
            "mid": mid,
            "upper": upper,
            "lower": lower,
        },
        index=idx,
    )


def rolling_volatility(
    x: pd.DataFrame | pd.Series,
    window: int = 20,
    return_col: str = "ret",
    annualisation_factor: int = 252,
    price_col: str = "close",
) -> pd.Series:
    """Rolling annualised volatility.

    Clean default behaviour:
      - If a DataFrame contains `return_col`, it will be used.
      - Otherwise (or if a Series is passed), volatility is computed from close-to-close returns
        of the price series (pct_change).

    Note: this function remains for backward compatibility; the project backtest and signals
    do not rely on any stored `df['ret']` column.
    """
    w = int(window)
    if w <= 1:
        raise ValueError("window must be > 1")

    if isinstance(x, pd.DataFrame) and (return_col in x.columns):
        r = pd.to_numeric(x[return_col], errors="coerce").astype("float64")
    else:
        close = _price_series(x if isinstance(x, (pd.Series, pd.DataFrame)) else x, price_col=price_col)
        r = close.pct_change().fillna(0.0)

    vol = r.rolling(window=w, min_periods=w).std(ddof=0) * np.sqrt(float(annualisation_factor))
    return vol.rename(f"roll_vol_{w}")


# =========================================================
# Volume-based indicators (optional; used for appendix experiments)
# =========================================================

def relative_volume(
    df: pd.DataFrame,
    *,
    window: int = 20,
    volume_col: str = "volume",
) -> pd.Series:
    """Relative volume = volume / SMA(volume, window).

    This is a simple, reproducible proxy for "unusually high activity" and is commonly used as a
    confirmation filter (e.g., only enter when relative volume exceeds a threshold).
    """
    w = int(window)
    if w <= 1:
        raise ValueError("window must be > 1")
    _require_cols(df, [volume_col])
    v = pd.to_numeric(df[volume_col], errors="coerce").astype("float64")
    v = v.replace([np.inf, -np.inf], np.nan).fillna(0.0)
    denom = v.rolling(window=w, min_periods=w).mean().replace(0.0, np.nan)
    out = (v / denom).replace([np.inf, -np.inf], np.nan)
    return out.rename(f"rel_vol_{w}")


# =========================================================
# Candlestick / price-action patterns (lightweight, interpretable)
# =========================================================

def candlestick_engulfing(df: pd.DataFrame, *, open_col: str = "open", close_col: str = "close") -> pd.Series:
    """Bullish/Bearish engulfing pattern.

    Returns a Series in {-1, 0, +1}:
      +1: bullish engulfing
      -1: bearish engulfing
       0: otherwise

    Definition (simple and reproducible):
      Bullish: prev candle red (close<open) AND current green (close>open) AND
               current body engulfs previous body (close>=prev_open and open<=prev_close)
      Bearish: prev green AND current red AND body engulfs (open>=prev_close and close<=prev_open)
    """
    _require_cols(df, [open_col, close_col])
    o = pd.to_numeric(df[open_col], errors="coerce").astype("float64")
    c = pd.to_numeric(df[close_col], errors="coerce").astype("float64")
    o1 = o.shift(1)
    c1 = c.shift(1)

    prev_red = c1 < o1
    prev_green = c1 > o1
    cur_green = c > o
    cur_red = c < o

    bull = prev_red & cur_green & (c >= o1) & (o <= c1)
    bear = prev_green & cur_red & (o >= c1) & (c <= o1)

    out = pd.Series(0, index=df.index, dtype="int8")
    out[bull] = 1
    out[bear] = -1
    return out.rename("pattern_engulfing")


def hammer_shooting_star(
    df: pd.DataFrame,
    *,
    open_col: str = "open",
    high_col: str = "high",
    low_col: str = "low",
    close_col: str = "close",
    body_min: float = 1e-12,
    wick_ratio: float = 2.0,
) -> pd.Series:
    """Hammer / Shooting Star approximation.

    Returns {-1,0,+1}:
      +1: hammer-like (bullish reversal)
      -1: shooting-star-like (bearish reversal)

    Heuristic (interpretable, robust):
      body = |close-open|
      lower_wick = min(open,close)-low
      upper_wick = high-max(open,close)

      Hammer: lower_wick >= wick_ratio*body AND upper_wick <= 0.5*body
      Star:   upper_wick >= wick_ratio*body AND lower_wick <= 0.5*body
    """
    _require_cols(df, [open_col, high_col, low_col, close_col])
    o = pd.to_numeric(df[open_col], errors="coerce").astype("float64")
    h = pd.to_numeric(df[high_col], errors="coerce").astype("float64")
    l = pd.to_numeric(df[low_col], errors="coerce").astype("float64")
    c = pd.to_numeric(df[close_col], errors="coerce").astype("float64")

    body = (c - o).abs().clip(lower=body_min)
    lower_wick = (np.minimum(o, c) - l).clip(lower=0.0)
    upper_wick = (h - np.maximum(o, c)).clip(lower=0.0)

    hammer = (lower_wick >= wick_ratio * body) & (upper_wick <= 0.5 * body)
    star = (upper_wick >= wick_ratio * body) & (lower_wick <= 0.5 * body)

    out = pd.Series(0, index=df.index, dtype="int8")
    out[hammer] = 1
    out[star] = -1
    return out.rename("pattern_hammer_star")


def donchian_breakout(df: pd.DataFrame, window: int = 20, *, high_col: str = "high", low_col: str = "low") -> pd.Series:
    """Donchian channel breakout.

    Returns {-1,0,+1}:
      +1: close breaks above rolling max(high, window) from previous day
      -1: close breaks below rolling min(low, window) from previous day

    Note: uses previous window (shifted) to avoid look-ahead.
    """
    _require_cols(df, [high_col, low_col, "close"])
    w = int(window)
    if w <= 1:
        raise ValueError("window must be > 1")
    high = pd.to_numeric(df[high_col], errors="coerce").astype("float64")
    low = pd.to_numeric(df[low_col], errors="coerce").astype("float64")
    close = pd.to_numeric(df["close"], errors="coerce").astype("float64")

    upper = high.rolling(w, min_periods=w).max().shift(1)
    lower = low.rolling(w, min_periods=w).min().shift(1)

    bull = close > upper
    bear = close < lower

    out = pd.Series(0, index=df.index, dtype="int8")
    out[bull] = 1
    out[bear] = -1
    return out.rename(f"pattern_donchian_{w}")
