from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from .backtest import performance_summary, reconstruct_trades_aligned


def _equity_from_returns(r: pd.Series, initial: float = 1.0) -> pd.Series:
    r = pd.to_numeric(r, errors="coerce").replace([np.inf, -np.inf], np.nan).fillna(0.0).astype("float64")
    return float(initial) * (1.0 + r).cumprod()


def _annual_returns(equity: pd.Series, *, full_years_only: bool = False) -> pd.Series:
    eq = pd.to_numeric(equity, errors="coerce").replace([np.inf, -np.inf], np.nan).dropna()
    if len(eq) < 2:
        return pd.Series(dtype="float64")

    idx = pd.DatetimeIndex(eq.index)
    min_year = int(idx.min().year)
    max_year = int(idx.max().year)

    out = {}
    years = sorted(eq.index.year.unique())
    for y in years:
        s = eq.loc[eq.index.year == y]
        if len(s) < 2:
            continue
        if full_years_only:
            # Skip partial first/last years to avoid misleading "annual" figures.
            if int(y) == min_year:
                first_date = pd.Timestamp(s.index.min()).date()
                if first_date > pd.Timestamp(f"{y}-01-02").date():
                    continue
            if int(y) == max_year:
                last_date = pd.Timestamp(s.index.max()).date()
                if last_date < pd.Timestamp(f"{y}-12-30").date():
                    continue
        out[int(y)] = float(s.iloc[-1] / s.iloc[0] - 1.0)
    return pd.Series(out, dtype="float64", name="annual_return")


def _mark_splits(ax, train, val, test, alpha=0.08):
    if train is None or val is None or test is None:
        return

    for a, b, label in [
        (train.index.min(), train.index.max(), "Train"),
        (val.index.min(), val.index.max(), "Val"),
        (test.index.min(), test.index.max(), "Test"),
    ]:
        if a is None or b is None:
            continue
        ax.axvspan(a, b, alpha=alpha, label=label)

    for cut in [train.index.max(), val.index.max()]:
        if cut is not None:
            ax.axvline(cut, linewidth=1)


def _reference_index(train=None, val=None, test=None, bt_dict: dict | None = None) -> pd.DatetimeIndex:
    """Use the full df_all window if provided (train/val/test), otherwise fall back to strategy index."""
    # Prefer the full (train+val+test) reporting window whenever split frames are provided.
    # Do NOT require all three to be non-empty; using the full window avoids truncating early history
    # (which can inflate the benchmark).
    if (train is not None) and (val is not None) and (test is not None):
        idx = pd.DatetimeIndex([])
        if len(train):
            idx = idx.union(train.index)
        if len(val):
            idx = idx.union(val.index)
        if len(test):
            idx = idx.union(test.index)
        if len(idx):
            idx = idx.sort_values()
            return idx

    if not bt_dict:
        raise ValueError("bt_dict is empty and no split indices provided")

    # Prefer a non-benchmark label as reference (strategy window)
    for k, bt in bt_dict.items():
        name = str(k).lower()
        if ("benchmark" not in name) and ("buy" not in name) and ("hold" not in name):
            return bt.index

    # fallback: first bt
    return next(iter(bt_dict.values())).index


def _align_to_reference(bt: pd.DataFrame, ref_idx: pd.DatetimeIndex) -> pd.DataFrame:
    """Reindex bt to reference index; fill missing with flat exposure and 0 returns, then recompute equity/dd."""
    bt2 = bt.reindex(ref_idx).copy()

    # strategy_ret must exist to recompute equity consistently
    if "strategy_ret" not in bt2.columns:
        raise ValueError("bt must contain 'strategy_ret' for report alignment")

    bt2["strategy_ret"] = pd.to_numeric(bt2["strategy_ret"], errors="coerce").replace([np.inf, -np.inf], np.nan).fillna(0.0)

    # If missing, assume flat/no trading
    if "position" in bt2.columns:
        bt2["position"] = pd.to_numeric(bt2["position"], errors="coerce").replace([np.inf, -np.inf], np.nan).fillna(0.0)
    else:
        bt2["position"] = 0.0

    if "turnover" in bt2.columns:
        bt2["turnover"] = pd.to_numeric(bt2["turnover"], errors="coerce").replace([np.inf, -np.inf], np.nan).fillna(0.0)
    else:
        bt2["turnover"] = 0.0

    # Recompute equity & drawdown on the aligned window (starting from 1.0)
    eq = _equity_from_returns(bt2["strategy_ret"], initial=1.0)
    bt2["equity"] = eq
    bt2["drawdown"] = eq / eq.cummax() - 1.0

    return bt2


def report_block(
    title: str,
    bt_dict: dict,
    *,
    train=None,
    val=None,
    test=None,
    price_df: pd.DataFrame | None = None,
    ema_fast: int | None = None,
    ema_slow: int | None = None,
    ticker: str = "NVDA",
    out_dir: str | Path = "outputs",
    show: bool = False,
) -> dict[str, Path]:
    """Notebook-aligned report block (root-correct).

    Key fix:
      - We DO NOT intersect indices across bt_dict (that can truncate early data and inflate benchmark).
      - We align all series to a single reference window (df_all) and treat missing early parts as flat (0 return).
      - Metrics are computed strictly from the aligned bt used for plots.
    """
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    ref_idx = _reference_index(train=train, val=val, test=test, bt_dict=bt_dict)
    bt_aligned = {k: _align_to_reference(v, ref_idx) for k, v in bt_dict.items()}

    # cache trades once (on aligned bt)
    trades_cache = {}
    for label, bt in bt_aligned.items():
        try:
            trades_cache[label] = reconstruct_trades_aligned(bt)
        except Exception:
            trades_cache[label] = None

    # ===== Metrics table (STRICTLY from bt_aligned) =====
    rows = []
    for label, bt in bt_aligned.items():
        tr = trades_cache.get(label, None)
        met = performance_summary(bt, rf_annual=0.0, trades=tr)
        rows.append({"name": label, **met})

    dfm = pd.DataFrame(rows)
    metrics_path = out_dir / f"{title}_metrics.csv"
    dfm.to_csv(metrics_path, index=False)

    # ===== Equity plot (rebased) =====
    fig, ax = plt.subplots(figsize=(12, 6))
    for name, bt in bt_aligned.items():
        eq = pd.to_numeric(bt["equity"], errors="coerce").replace([np.inf, -np.inf], np.nan).ffill().fillna(1.0)
        eqr = (eq / float(eq.iloc[0])).astype("float64")
        ax.plot(eqr.index, eqr.values, label=name, linewidth=2, linestyle=":" if "Buy" in str(name) else "-")
    if train is not None:
        _mark_splits(ax, train, val, test)
    ax.set_title(f"{ticker} {title}: Equity (rebased)")
    ax.legend()
    equity_path = out_dir / f"{title}_equity.png"
    fig.tight_layout()
    fig.savefig(equity_path, dpi=160)
    if show:
        plt.show()
    plt.close(fig)

    # ===== Drawdown plot =====
    fig, ax = plt.subplots(figsize=(12, 4.5))
    for name, bt in bt_aligned.items():
        dd = pd.to_numeric(bt["drawdown"], errors="coerce").replace([np.inf, -np.inf], np.nan).fillna(0.0)
        ax.plot(dd.index, dd.values, label=name, linewidth=2, linestyle=":" if "Buy" in str(name) else "-")
    ax.axhline(0.0, linewidth=1)
    if train is not None:
        _mark_splits(ax, train, val, test)
    ax.set_title(f"{ticker} {title}: Drawdown")
    ax.legend()
    dd_path = out_dir / f"{title}_drawdown.png"
    fig.tight_layout()
    fig.savefig(dd_path, dpi=160)
    if show:
        plt.show()
    plt.close(fig)

    # ===== Annual returns (table + plot) =====
    ar = pd.DataFrame({k: _annual_returns(v["equity"], full_years_only=False) for k, v in bt_aligned.items()}).dropna(how="all")
    ar = ar.sort_index()
    ar_path = out_dir / f"{title}_annual_returns.csv"
    ar.to_csv(ar_path)

    # If the last year is not complete, label it as YTD in the plot to avoid confusion.
    ytd_year = None
    try:
        last_dt = pd.Timestamp(ref_idx.max()).date()
        if (last_dt.month, last_dt.day) != (12, 31):
            max_year = int(pd.DatetimeIndex(ref_idx).max().year)
            if len(ar.index) and int(ar.index.max()) == max_year:
                ytd_year = max_year
    except Exception:
        ytd_year = None

    fig = plt.figure(figsize=(12, 5))
    for col in ar.columns:
        plt.plot(ar.index, ar[col].values, marker="o", linewidth=2, linestyle=":" if "Buy" in str(col) else "-", label=col)
    if train is not None:
        for y in [train.index.max().year, val.index.max().year]:
            plt.axvline(y, linewidth=1)
    plt.axhline(0, linewidth=1)
    title_suffix = " (YTD for latest year)" if ytd_year is not None else ""
    plt.title(f"{ticker} {title}: Annual Return{title_suffix}")
    plt.ylabel("Annual Return")
    if len(ar.index):
        labels = []
        for y in ar.index:
            yi = int(y)
            labels.append(f"{yi} YTD" if (ytd_year is not None and yi == int(ytd_year)) else f"{yi}")
        plt.xticks(ar.index, labels)
    plt.grid(True, axis="y", alpha=0.3)
    plt.legend()
    annual_plot_path = out_dir / f"{title}_annual_return.png"
    fig.tight_layout()
    fig.savefig(annual_plot_path, dpi=160)
    if show:
        plt.show()
    plt.close(fig)

    # ===== Price chart (close + optional EMAs + entry/exit markers) =====
    price_plot_path = None
    try:
        if price_df is not None and "close" in price_df.columns:
            close = pd.to_numeric(price_df["close"], errors="coerce").reindex(ref_idx).astype("float64")
            close = close.ffill().dropna()
            if len(close) >= 2:
                fig, ax = plt.subplots(figsize=(12, 5))
                # Rebase to 1.0 for readability across long horizons
                rebased = (close / float(close.iloc[0])).astype("float64")
                ax.plot(rebased.index, rebased.values, label="Close (rebased)", linewidth=2)

                if ema_fast and int(ema_fast) > 1:
                    ef = rebased.ewm(span=int(ema_fast), adjust=False).mean()
                    ax.plot(ef.index, ef.values, label=f"EMA({int(ema_fast)})", linewidth=1.6, alpha=0.9)
                if ema_slow and int(ema_slow) > 1:
                    es = rebased.ewm(span=int(ema_slow), adjust=False).mean()
                    ax.plot(es.index, es.values, label=f"EMA({int(ema_slow)})", linewidth=1.6, alpha=0.9)

                # Entry/exit markers from the first non-benchmark series
                strat_label = None
                for k in bt_aligned.keys():
                    name = str(k).lower()
                    if ("benchmark" not in name) and ("buy" not in name) and ("hold" not in name):
                        strat_label = k
                        break
                if strat_label is not None:
                    bt = bt_aligned[strat_label]
                    pos = pd.to_numeric(bt.get("position", 0.0), errors="coerce").fillna(0.0)
                    pos_on = pos > 0.0
                    entry = pos_on & (~pos_on.shift(1).fillna(False))
                    exit_ = (~pos_on) & (pos_on.shift(1).fillna(False))
                    ax.scatter(rebased.index[entry.reindex(rebased.index).fillna(False)], rebased[entry.reindex(rebased.index).fillna(False)],
                               s=28, marker="^", label="Entry", zorder=4)
                    ax.scatter(rebased.index[exit_.reindex(rebased.index).fillna(False)], rebased[exit_.reindex(rebased.index).fillna(False)],
                               s=28, marker="v", label="Exit", zorder=4)

                if train is not None:
                    _mark_splits(ax, train, val, test, alpha=0.06)
                ax.set_title(f"{ticker} {title}: Price (rebased) + Trend overlays")
                ax.legend()
                ax.grid(True, axis="y", alpha=0.25)
                price_plot_path = out_dir / f"{title}_price.png"
                fig.tight_layout()
                fig.savefig(price_plot_path, dpi=160)
                if show:
                    plt.show()
                plt.close(fig)
    except Exception:
        price_plot_path = None

    return {
        "metrics": metrics_path,
        "annual_returns": ar_path,
        "equity": equity_path,
        "drawdown": dd_path,
        "annual_return_plot": annual_plot_path,
        **({} if price_plot_path is None else {"price": price_plot_path}),
    }
