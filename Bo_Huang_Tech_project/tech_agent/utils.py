from __future__ import annotations

from typing import Iterable

import numpy as np
import pandas as pd

def _require_cols(df: pd.DataFrame, cols: Iterable[str]) -> None:
    """Fail-fast: ensure df contains required columns."""
    cols = list(cols)
    missing = [c for c in cols if c not in df.columns]
    if missing:
        raise ValueError(f"df missing required columns: {missing}. Got: {list(df.columns)}")

def _to_series(x, index: pd.Index, name: str | None = None, dtype=None) -> pd.Series:
    """Coerce scalar/array-like/Series into a Series aligned to index."""
    if isinstance(x, pd.Series):
        s = x.reindex(index)
    else:
        if np.ndim(x) == 0:
            s = pd.Series([x] * len(index), index=index)
        else:
            if len(x) != len(index):
                raise ValueError(f"Length mismatch: len(x)={len(x)} vs len(index)={len(index)}")
            s = pd.Series(x, index=index)
    if name is not None:
        s.name = name
    if dtype is not None:
        s = s.astype(dtype)
    return s

def time_split(df: pd.DataFrame, train_end: str, val_end: str):
    df = df.sort_index()
    train = df.loc[:train_end].copy()
    val = df.loc[train_end:val_end].copy()
    if len(val) > 0:
        val = val.iloc[1:]
    test = df.loc[val_end:].copy()
    if len(test) > 0:
        test = test.iloc[1:]
    return train, val, test
