from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd


@dataclass(frozen=True)
class FundamentalView:
    """External fundamental view (from Idaliia report/module output).

    rating: one of BUY / HOLD / SELL (case-insensitive)
    as_of: optional ISO date string. If provided, overlay applies from this date onward.
    source: free-text provenance (e.g., 'Idaliia report')
    notes: optional list of bullet notes
    """
    rating: str
    as_of: str | None = None
    source: str | None = None
    notes: list[str] | None = None

    @property
    def rating_norm(self) -> str:
        return (self.rating or "").strip().upper()


def load_fundamental_override(path: str | Path) -> FundamentalView:
    p = Path(path)
    data = json.loads(p.read_text(encoding="utf-8"))
    return FundamentalView(
        rating=data.get("rating", "HOLD"),
        as_of=data.get("as_of"),
        source=data.get("source"),
        notes=data.get("notes"),
    )


def max_leverage_cap_from_view(
    index: pd.DatetimeIndex,
    view: FundamentalView,
    *,
    base_max_leverage: float = 1.0,
    sell_leverage_mult: float = 0.3,
) -> pd.Series:
    """Create a time-aligned max-leverage cap series implementing the fundamental filter.

    Rule (interpretable & reproducible):
      - BUY/HOLD: cap = base_max_leverage
      - SELL: cap = base_max_leverage * sell_leverage_mult (from `as_of` onward if provided)

    This avoids 'vol targeting re-leveraging' that can happen if you merely scale positions.
    """
    idx = index
    cap = pd.Series(float(base_max_leverage), index=idx, dtype="float64")

    r = view.rating_norm
    if r in {"SELL", "STRONG SELL"}:
        cap_val = float(base_max_leverage) * float(sell_leverage_mult)
        if view.as_of:
            cap.loc[pd.Timestamp(view.as_of):] = cap_val
        else:
            # If no as_of is provided, apply cap for the whole sample (document in report).
            cap.loc[:] = cap_val

    cap.name = "max_leverage_cap"
    return cap
