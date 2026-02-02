from __future__ import annotations

from pathlib import Path
from typing import Any

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt


def _num(x: Any) -> float | None:
    try:
        v = float(x)
        if v != v:  # nan
            return None
        return v
    except Exception:
        return None


def write_fundamental_charts(
    *,
    out_dir: str | Path,
    ticker: str,
    snapshot: dict[str, Any],
) -> list[Path]:
    """
    Create small, report-friendly fundamental charts.

    Uses a single-point snapshot (not time series) because that's what the external module provides
    reliably via Yahoo Finance info. These are for contextual display only.
    """
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    written: list[Path] = []

    cur = _num(snapshot.get("current_price"))
    t_mean = _num(snapshot.get("target_price_mean"))
    t_low = _num(snapshot.get("target_price_low"))
    t_high = _num(snapshot.get("target_price_high"))

    # --- Chart 1: Analyst target range vs current price ---
    if cur is not None and (t_mean is not None or t_low is not None or t_high is not None):
        fig, ax = plt.subplots(figsize=(6.5, 2.6))
        ax.set_title(f"{ticker}: Analyst target range (snapshot)")

        xs = []
        ys = []
        labels = []
        if t_low is not None:
            xs.append(0)
            ys.append(t_low)
            labels.append("Low")
        if t_mean is not None:
            xs.append(1)
            ys.append(t_mean)
            labels.append("Mean")
        if t_high is not None:
            xs.append(2)
            ys.append(t_high)
            labels.append("High")

        ax.scatter(xs, ys, s=55, zorder=3)
        ax.plot(xs, ys, linewidth=1.5, alpha=0.7)
        ax.axhline(cur, color="#111827", linestyle="--", linewidth=1.5, label=f"Current: {cur:.2f}")
        ax.set_xticks(xs, labels)
        ax.set_ylabel("Price (USD)")
        ax.grid(True, axis="y", alpha=0.25)
        ax.legend(loc="best", fontsize=8)

        p = out_dir / "FUND_targets.png"
        fig.tight_layout()
        fig.savefig(p, dpi=160)
        plt.close(fig)
        written.append(p)

    # --- Chart 2: Key valuation multiples (snapshot) ---
    fields = [
        ("Trailing P/E", snapshot.get("trailing_pe")),
        ("Forward P/E", snapshot.get("forward_pe")),
        ("P/S (TTM)", snapshot.get("price_to_sales")),
        ("P/B", snapshot.get("price_to_book")),
        ("EV/EBITDA", snapshot.get("enterprise_to_ebitda")),
    ]
    lab = []
    val = []
    for k, v in fields:
        nv = _num(v)
        if nv is None:
            continue
        lab.append(k)
        val.append(nv)

    if val:
        fig, ax = plt.subplots(figsize=(6.5, 3.2))
        ax.set_title(f"{ticker}: Valuation multiples (snapshot)")
        y = list(range(len(val)))
        ax.barh(y, val, color="#1d4ed8", alpha=0.85)
        ax.set_yticks(y, lab)
        ax.invert_yaxis()
        ax.set_xlabel("Multiple")
        ax.grid(True, axis="x", alpha=0.25)

        # add value labels
        for yi, vv in zip(y, val):
            ax.text(vv, yi, f"  {vv:.2f}", va="center", fontsize=8)

        p = out_dir / "FUND_multiples.png"
        fig.tight_layout()
        fig.savefig(p, dpi=160)
        plt.close(fig)
        written.append(p)

    return written
