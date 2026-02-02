from __future__ import annotations

import datetime as dt
import time
from pathlib import Path
from typing import Any

import contextlib
import io
import hashlib
import json
import numpy as np
import pandas as pd
import requests
import yfinance as yf
import math
import random

# -------------------------
# Schema constants
# -------------------------
PRICE_COLS: list[str] = ["open", "high", "low", "close"]
VOLUME_COL: str = "volume"
REQUIRED_COLS: list[str] = PRICE_COLS + [VOLUME_COL]

CACHE_DIR = Path("data_cache")
CACHE_DIR.mkdir(exist_ok=True)

# Bump when cache key/metadata semantics change.
# v3 introduces a "source" tag into the cache key so Yahoo (yfinance) and Stooq caches
# never collide (Stooq is an UNADJUSTED fallback).

CACHE_SCHEMA_VERSION: int = 3

# Helper to normalize as_of input for fetch_and_standardize_ohlcv
def _normalize_as_of(as_of: dt.date | str | None) -> dt.date | None:
    """Normalize as_of input.

    - None / 'latest' / '' / 'none' / 'null' => None (real-time mode)
    - 'YYYY-MM-DD' (or any parseable date) => dt.date
    - dt.date passthrough

    This prevents errors like pandas DateParseError when as_of='latest'.
    """
    if as_of is None:
        return None

    # Allow passing a real date/datetime
    if isinstance(as_of, dt.date) and not isinstance(as_of, dt.datetime):
        return as_of

    s = str(as_of).strip()
    if s == "":
        return None
    sl = s.lower()
    if sl in {"latest", "now", "realtime", "real-time", "none", "null"}:
        return None

    # Parse everything else as a date
    return pd.to_datetime(s).date()


def _cache_meta_path(data_path: Path) -> Path:
    return data_path.with_suffix(data_path.suffix + ".meta.json")


def _fingerprint_ohlcv(df: pd.DataFrame) -> str:
    """Stable-ish fingerprint for reproducibility checks (index + close + volume)."""
    # Use float64 representations to reduce platform differences
    idx_ns = pd.to_datetime(df.index, errors="coerce").view("int64")
    close = pd.to_numeric(df.get("close"), errors="coerce").astype("float64").to_numpy()
    vol = pd.to_numeric(df.get("volume"), errors="coerce").astype("float64").to_numpy()
    b = idx_ns.tobytes() + close.tobytes() + vol.tobytes()
    return hashlib.sha1(b).hexdigest()


def _cache_path(ticker: str, years: int, interval: str, auto_adjust: bool, end: dt.date, *, source: str) -> Path:
    # Include end date + schema version so the same run is reproducible.
    src = str(source or "unknown").lower().replace(" ", "_")
    key = (
        f"v{CACHE_SCHEMA_VERSION}_"
        f"{ticker}_{int(years)}y_{interval}_adj{int(bool(auto_adjust))}_src{src}_end{end.isoformat()}.csv.gz"
    )
    return CACHE_DIR / key


def _read_cache(path: Path) -> pd.DataFrame | None:
    if not path.exists():
        return None
    try:
        df = pd.read_csv(path, compression="gzip", index_col=0, parse_dates=True)
        if df is None or df.empty:
            return None
        df.index = pd.to_datetime(df.index, errors="coerce")
        df = df[~df.index.isna()].sort_index()

        meta_path = _cache_meta_path(path)
        if meta_path.exists():
            try:
                meta = json.loads(meta_path.read_text(encoding="utf-8"))
                df.attrs["cache_meta"] = meta
            except Exception:
                pass
        return df
    except Exception:
        return None


def _find_latest_cache_path(
    *,
    ticker: str,
    years: int,
    interval: str,
    auto_adjust: bool,
    source: str,
) -> Path | None:
    """
    Find the most recently-written cache file for the given parameters.

    Used as a "cache fallback" when Yahoo(yfinance) endpoints are temporarily unavailable.
    We prefer a cached Yahoo run over switching the upstream data source (e.g., Stooq),
    but we still disclose this in report metadata.
    """
    t = str(ticker).upper()
    adj = int(bool(auto_adjust))
    src = str(source or "").lower().replace(" ", "_")

    patterns: list[str] = []
    # Newer v3 schema includes source tag in the filename.
    patterns.append(f"v3_{t}_{int(years)}y_{interval}_adj{adj}_src{src}_end*.csv.gz")
    # Older v2 schema didn't include source; treat it as Yahoo unless meta says otherwise.
    patterns.append(f"v2_{t}_{int(years)}y_{interval}_adj{adj}_end*.csv.gz")
    # Very old schema variant.
    patterns.append(f"{t}_{int(years)}y_{interval}_adj{adj}.csv.gz")

    candidates: list[Path] = []
    for pat in patterns:
        candidates.extend(sorted(CACHE_DIR.glob(pat)))

    if not candidates:
        return None

    def _meta_end_date(p: Path) -> dt.date | None:
        meta_path = _cache_meta_path(p)
        if not meta_path.exists():
            return None
        try:
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
        except Exception:
            return None
        src_used = str(meta.get("data_source_used") or "").lower()
        if src_used != src:
            return None
        ed = meta.get("end_date")
        if not ed:
            return None
        try:
            return pd.to_datetime(ed).date()
        except Exception:
            return None

    # Prefer the cache with the latest end_date for the desired upstream source.
    dated: list[tuple[dt.date, Path]] = []
    for p in candidates:
        d = _meta_end_date(p)
        if d is not None:
            dated.append((d, p))
    if dated:
        dated.sort(key=lambda x: x[0], reverse=True)
        return dated[0][1]

    # Fallback: newest by mtime (best-effort).
    candidates.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    return candidates[0]


def _write_cache(path: Path, df: pd.DataFrame, meta: dict[str, Any] | None = None) -> None:
    try:
        df.to_csv(path, compression="gzip")
    except Exception:
        return

    # Best-effort write of a sidecar meta json for reproducibility.
    if meta is not None:
        try:
            meta_path = _cache_meta_path(path)
            meta_path.write_text(json.dumps(meta, indent=2, default=str), encoding="utf-8")
        except Exception:
            pass


def _download_from_stooq(ticker: str, start: dt.date, end: dt.date) -> pd.DataFrame:
    """Fallback daily data source: Stooq (UNADJUSTED)."""
    sym = ticker.lower()
    if "." not in sym:
        sym = sym + ".us"
    url = f"https://stooq.com/q/d/l/?s={sym}&i=d"
    r = requests.get(url, timeout=20)
    r.raise_for_status()
    text = r.text.strip()
    if len(text) < 50 or "Date,Open,High,Low,Close,Volume" not in text:
        raise ValueError("Stooq returned unexpected content")
    df = pd.read_csv(io.StringIO(text))
    df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
    df = df.dropna(subset=["Date"]).set_index("Date").sort_index()
    df = df.loc[pd.Timestamp(start):pd.Timestamp(end)]
    return df


def _download_from_yahoo_chart(
    ticker: str,
    start: dt.date,
    end: dt.date,
    *,
    interval: str,
    auto_adjust: bool,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    """
    Download OHLCV via Yahoo's chart endpoint.

    Why:
    - yfinance can intermittently fail with tz/crumb issues depending on network environment.
    - The chart endpoint is often more stable and still counts as "Yahoo" data.

    Notes:
    - We use adjusted close when auto_adjust=True and scale OHLC by adj/close to preserve candle shapes.
    - This is a best-effort approximation consistent with common "auto-adjust" behavior.
    """
    # Yahoo expects seconds since epoch; we request a slightly wider window and then slice.
    p1 = int(pd.Timestamp(start).timestamp())
    p2 = int((pd.Timestamp(end) + pd.Timedelta(days=1)).timestamp())
    sym = str(ticker).upper()
    # query1/query2 are both used by Yahoo; try both for resilience.
    urls = [
        "https://query1.finance.yahoo.com/v8/finance/chart/"
        f"{sym}?period1={p1}&period2={p2}&interval={interval}&events=div%7Csplit&corsDomain=finance.yahoo.com",
        "https://query2.finance.yahoo.com/v8/finance/chart/"
        f"{sym}?period1={p1}&period2={p2}&interval={interval}&events=div%7Csplit&corsDomain=finance.yahoo.com",
    ]
    headers = {
        "User-Agent": "Mozilla/5.0",
        "Accept": "application/json,text/plain,*/*",
    }

    # Very small retry budget; if Yahoo rate-limits (429), we back off and then fail fast.
    last_exc: Exception | None = None
    js = None
    for url in urls:
        for attempt in range(3):
            try:
                r = requests.get(url, timeout=20, headers=headers)
                if r.status_code == 429:
                    # Exponential backoff with jitter.
                    sleep_s = min(8.0, 1.0 * (2**attempt)) + random.random() * 0.25
                    time.sleep(sleep_s)
                    continue
                r.raise_for_status()
                js = r.json()
                break
            except Exception as e:
                last_exc = e
                # Small backoff for transient errors.
                time.sleep(0.5 + random.random() * 0.25)
                continue
        if js is not None:
            break
    if js is None:
        raise ValueError(f"Yahoo chart failed after retries: {last_exc}")
    result = (((js or {}).get("chart") or {}).get("result") or [None])[0]
    if not isinstance(result, dict):
        raise ValueError("Yahoo chart: missing result")

    meta = result.get("meta") if isinstance(result.get("meta"), dict) else {}
    timestamps = result.get("timestamp") or []
    if not timestamps:
        raise ValueError("Yahoo chart: no timestamps")

    ind = result.get("indicators") if isinstance(result.get("indicators"), dict) else {}
    quote = (ind.get("quote") or [None])[0] if isinstance(ind.get("quote"), list) else None
    if not isinstance(quote, dict):
        raise ValueError("Yahoo chart: missing quote")

    def _arr(name: str) -> list[float | None]:
        a = quote.get(name)
        return a if isinstance(a, list) else []

    o = _arr("open")
    h = _arr("high")
    l = _arr("low")
    c = _arr("close")
    v = _arr("volume")

    # adjusted close lives under indicators.adjclose[0].adjclose
    adjclose = None
    adj = (ind.get("adjclose") or [None])[0] if isinstance(ind.get("adjclose"), list) else None
    if isinstance(adj, dict):
        ac = adj.get("adjclose")
        if isinstance(ac, list):
            adjclose = ac

    idx = pd.to_datetime(pd.Series(timestamps, dtype="int64"), unit="s", utc=True).dt.tz_convert(None)
    df = pd.DataFrame(
        {
            "open": pd.to_numeric(pd.Series(o), errors="coerce"),
            "high": pd.to_numeric(pd.Series(h), errors="coerce"),
            "low": pd.to_numeric(pd.Series(l), errors="coerce"),
            "close": pd.to_numeric(pd.Series(c), errors="coerce"),
            "volume": pd.to_numeric(pd.Series(v), errors="coerce"),
        },
        index=idx,
    ).sort_index()

    # Slice to requested window.
    df = df.loc[pd.Timestamp(start) : pd.Timestamp(end)]

    if auto_adjust and isinstance(adjclose, list) and len(adjclose) == len(idx):
        ac = pd.to_numeric(pd.Series(adjclose), errors="coerce")
        # Align to df index after slicing.
        ac.index = idx
        ac = ac.loc[df.index]
        # Scale factor: adj_close / close
        close = df["close"].astype("float64")
        ratio = (ac.astype("float64") / close).replace([np.inf, -np.inf], np.nan)
        # Apply only where sensible.
        ratio = ratio.where((ratio > 0) & ratio.notna(), other=np.nan)
        for col in ["open", "high", "low", "close"]:
            df[col] = (df[col].astype("float64") * ratio).where(ratio.notna(), other=np.nan)

    # Basic cleanup
    df = df.dropna(subset=["close"]).copy()
    df["volume"] = df["volume"].fillna(0.0)

    # Meta for exchange/currency where available.
    ticker_meta: dict[str, Any] = {}
    if isinstance(meta, dict):
        ticker_meta["exchange"] = meta.get("exchangeName") or meta.get("fullExchangeName") or meta.get("exchange")
        ticker_meta["currency"] = meta.get("currency")
    return df, ticker_meta


# =========================================================
# 1) Fetch & Standardize OHLCV (NO ret here)
# =========================================================

def fetch_and_standardize_ohlcv(
    ticker: str,
    years: int = 10,
    interval: str = "1d",
    auto_adjust: bool = True,
    *,
    as_of: dt.date | str | None = None,
    allow_stooq_fallback: bool = True,
) -> pd.DataFrame:
    """Fetch OHLCV and standardize to open/high/low/close/volume.

    Primary path matches the notebook (Yahoo via yfinance). To improve robustness in script
    environments, we additionally:
      1) read/write a gzip CSV cache in ./data_cache
      2) try yf.Ticker().history if yf.download fails
      3) fall back to Stooq if Yahoo endpoints are blocked

    Note: if Stooq fallback is used, prices are UNADJUSTED.
    as_of='latest' (or None) means real-time mode; otherwise pin to the provided date.
    """

    # Reproducibility: allow pinning an as_of (end) date.
    # as_of=None or as_of='latest' => real-time mode (end=today).
    end_norm = _normalize_as_of(as_of)
    end = dt.date.today() if end_norm is None else end_norm
    start = end - dt.timedelta(days=int(years * 365.25))

    # Cache by *intended* upstream source so Yahoo and Stooq data never collide.
    # If Yahoo fetch fails and Stooq fallback is used, we write into the Stooq cache key.
    cache_path = _cache_path(ticker, years, interval, auto_adjust, end=end, source="yfinance")
    cached = _read_cache(cache_path)
    if cached is not None and not cached.empty:
        # Ensure required columns
        if isinstance(cached.columns, pd.MultiIndex):
            cached.columns = cached.columns.get_level_values(0)
        # Standardize possible title-case columns
        cached = cached.rename(columns={"Open":"open","High":"high","Low":"low","Close":"close","Volume":"volume"})
        if set(REQUIRED_COLS).issubset(set(cached.columns)):
            out = cached[REQUIRED_COLS].copy()
            for c in REQUIRED_COLS:
                out[c] = pd.to_numeric(out[c], errors="coerce").astype("float64")
            out.index = pd.to_datetime(out.index, errors="coerce")
            out = out[~out.index.isna()].sort_index()
            out.attrs["data_source_used"] = "cache"
            # Preserve any cache meta loaded by _read_cache
            if "cache_meta" in cached.attrs:
                out.attrs["cache_meta"] = cached.attrs["cache_meta"]
            return out

    df = None
    last_err = None
    yfinance_error: str | None = None
    yahoo_chart_error: str | None = None
    ticker_meta: dict[str, Any] = {}

    # Try notebook-style download first
    try:
        # yfinance can emit noisy stdout/stderr logs (tz/JSON parse errors) even when we can recover via cache.
        # Capture them to keep CLI output clean; errors are recorded in metadata fields instead.
        _buf_out, _buf_err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(_buf_out), contextlib.redirect_stderr(_buf_err):
            df = yf.download(
                ticker,
                start=start,
                end=end,
                interval=interval,
                auto_adjust=auto_adjust,
                progress=False,
                actions=False,
                group_by="column",
                threads=False,
            )
        if df is None or df.empty:
            yfinance_error = "yfinance download returned empty dataframe"
        try:
            _buf_out, _buf_err = io.StringIO(), io.StringIO()
            with contextlib.redirect_stdout(_buf_out), contextlib.redirect_stderr(_buf_err):
                fi = yf.Ticker(ticker).fast_info
            if isinstance(fi, dict):
                ticker_meta["exchange"] = fi.get("exchange") or fi.get("exchangeName")
                ticker_meta["currency"] = fi.get("currency")
        except Exception:
            pass
    except Exception as e:
        last_err = e
        yfinance_error = str(e)
        df = None

    # Fallback: ticker.history
    if df is None or df.empty:
        for _ in range(2):
            try:
                _buf_out, _buf_err = io.StringIO(), io.StringIO()
                with contextlib.redirect_stdout(_buf_out), contextlib.redirect_stderr(_buf_err):
                    df = yf.Ticker(ticker).history(
                        start=start,
                        end=end,
                        interval=interval,
                        auto_adjust=auto_adjust,
                        actions=False,
                    )
                if df is not None and not df.empty:
                    try:
                        _buf_out, _buf_err = io.StringIO(), io.StringIO()
                        with contextlib.redirect_stdout(_buf_out), contextlib.redirect_stderr(_buf_err):
                            fi = yf.Ticker(ticker).fast_info
                        if isinstance(fi, dict):
                            ticker_meta["exchange"] = fi.get("exchange") or fi.get("exchangeName")
                            ticker_meta["currency"] = fi.get("currency")
                    except Exception:
                        pass
                    break
            except Exception as e:
                last_err = last_err or e
                yfinance_error = yfinance_error or str(e)
                df = None
                time.sleep(1.0)

    # Fallback chain
    data_source_used = "yfinance"
    if df is None or df.empty:
        # Prefer patching a known-good Yahoo cache with a small "recent" Yahoo chart fetch.
        # This greatly reduces request size and tends to avoid rate limits.
        latest_yf_cache = _find_latest_cache_path(
            ticker=ticker,
            years=years,
            interval=interval,
            auto_adjust=auto_adjust,
            source="yfinance",
        )
        cached2 = _read_cache(latest_yf_cache) if latest_yf_cache is not None else None

        if cached2 is not None and not cached2.empty:
            # Standardize cached frame.
            if isinstance(cached2.columns, pd.MultiIndex):
                cached2.columns = cached2.columns.get_level_values(0)
            cached2 = cached2.rename(columns={"Open": "open", "High": "high", "Low": "low", "Close": "close", "Volume": "volume"})
            if set(REQUIRED_COLS).issubset(set(cached2.columns)):
                base = cached2[REQUIRED_COLS].copy()
                base.index = pd.to_datetime(base.index, errors="coerce")
                base = base[~base.index.isna()].sort_index()
                base_end = pd.to_datetime(base.index.max()).date() if len(base) else None

                # Patch window: last ~120 days up to today end.
                try:
                    patch_start = (base_end - dt.timedelta(days=120)) if base_end else start
                    df_patch, meta2 = _download_from_yahoo_chart(
                        ticker=ticker,
                        start=patch_start,
                        end=end,
                        interval=interval,
                        auto_adjust=auto_adjust,
                    )
                    if df_patch is not None and (not df_patch.empty):
                        merged = pd.concat([base, df_patch], axis=0)
                        merged = merged[~merged.index.duplicated(keep="last")].sort_index()
                        df = merged.loc[pd.Timestamp(start) : pd.Timestamp(end)]
                        data_source_used = "yahoo_patch"
                        ticker_meta.update({k: v for k, v in (meta2 or {}).items() if v})
                        cache_path = _cache_path(ticker, years, interval, auto_adjust, end=end, source="yahoo_patch")
                    else:
                        yahoo_chart_error = "Yahoo chart patch returned empty dataframe"
                except Exception as e:
                    yahoo_chart_error = str(e)
                    last_err = last_err or e

                # If patching failed, fall back to the cached Yahoo history (still better than switching sources).
                if df is None or df.empty:
                    out = base.copy()
                    for c in REQUIRED_COLS:
                        out[c] = pd.to_numeric(out[c], errors="coerce").astype("float64")
                    out.attrs["data_source_used"] = "cache"
                    if "cache_meta" in cached2.attrs:
                        out.attrs["cache_meta"] = cached2.attrs["cache_meta"]
                    if yfinance_error:
                        out.attrs["yfinance_error"] = yfinance_error
                    if yahoo_chart_error:
                        out.attrs["yahoo_chart_error"] = yahoo_chart_error
                    return out

        # 1) Try Yahoo chart endpoint for full history as a true "live Yahoo" alternative.
        try:
            df2, meta2 = _download_from_yahoo_chart(
                ticker=ticker,
                start=start,
                end=end,
                interval=interval,
                auto_adjust=auto_adjust,
            )
            if df2 is None or df2.empty:
                raise ValueError("Yahoo chart returned empty dataframe")
            df = df2
            data_source_used = "yahoo_chart"
            ticker_meta.update({k: v for k, v in (meta2 or {}).items() if v})
            cache_path = _cache_path(ticker, years, interval, auto_adjust, end=end, source="yahoo_chart")
        except Exception as e:
            yahoo_chart_error = yahoo_chart_error or str(e)
            last_err = last_err or e

        # 3) Last resort: Stooq (unadjusted)
        if df is None or df.empty:
            if not bool(allow_stooq_fallback):
                raise ValueError(f"No data returned for ticker={ticker!r}") from (last_err or ValueError("empty"))
            try:
                df = _download_from_stooq(ticker, start, end)
                data_source_used = "stooq"
                cache_path = _cache_path(ticker, years, interval, auto_adjust, end=end, source="stooq")
            except Exception as e:
                raise ValueError(f"No data returned for ticker={ticker!r}") from (last_err or e)

    # Preserve index name
    original_index_name = df.index.name

    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)

    df = df.rename(columns={
        "Open": "open",
        "High": "high",
        "Low": "low",
        "Close": "close",
        "Volume": "volume",
        "Adj Close": "adj_close",
    })

    missing = set(REQUIRED_COLS) - set(df.columns)
    if missing:
        raise ValueError(f"Missing required OHLCV columns: {missing}. Got: {list(df.columns)}")

    df = df[REQUIRED_COLS].copy()

    df.index = pd.to_datetime(df.index, errors="coerce")
    if df.index.isna().any():
        bad = df[df.index.isna()].head(5)
        raise ValueError(f"Found non-parsable datetime index rows:\n{bad}")

    if getattr(df.index, "tz", None) is not None:
        df.index = df.index.tz_convert("UTC").tz_localize(None)

    df = df.sort_index()
    df = df[~df.index.duplicated(keep="first")]
    df.index.name = original_index_name

    for col in REQUIRED_COLS:
        df[col] = pd.to_numeric(df[col], errors="coerce").astype("float64")

    # fail-fast checks (match notebook)
    if df[PRICE_COLS].isna().any(axis=1).any():
        bad = df[df[PRICE_COLS].isna().any(axis=1)].head(5)
        raise ValueError(f"Found rows with missing OHLC values:\n{bad}")

    if (df["high"] < df["low"]).any():
        bad = df[df["high"] < df["low"]].head(5)
        raise ValueError(f"Found high < low rows:\n{bad}")

    open_out = (df["open"] > df["high"]) | (df["open"] < df["low"])
    if open_out.any():
        bad = df[open_out].head(5)
        raise ValueError(f"Open price outside high-low range:\n{bad}")

    close_out = (df["close"] > df["high"]) | (df["close"] < df["low"])
    if close_out.any():
        bad = df[close_out].head(5)
        raise ValueError(f"Close price outside high-low range:\n{bad}")

    if (df[PRICE_COLS] <= 0).any().any():
        bad = df[(df[PRICE_COLS] <= 0).any(axis=1)].head(5)
        raise ValueError(f"Found non-positive prices:\n{bad}")

    vol = df[VOLUME_COL]
    neg_mask = vol.notna() & (vol < 0)
    if neg_mask.any():
        bad = df[neg_mask].head(5)
        raise ValueError(f"Found negative volume:\n{bad}")

    df.attrs["data_source_used"] = data_source_used
    if yfinance_error:
        # Keep for transparency in the report payload (helps explain why fallback happened).
        df.attrs["yfinance_error"] = yfinance_error
    if yahoo_chart_error:
        df.attrs["yahoo_chart_error"] = yahoo_chart_error

    cache_meta: dict[str, Any] = {
        "schema_version": int(CACHE_SCHEMA_VERSION),
        "ticker": ticker,
        "years": int(years),
        "interval": interval,
        "auto_adjust": bool(auto_adjust),
        "start_date": start.isoformat(),
        "end_date": end.isoformat(),
        "data_source_used": data_source_used,
        "fetched_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
        "fingerprint_sha1": _fingerprint_ohlcv(df),
        "exchange": ticker_meta.get("exchange"),
        "currency": ticker_meta.get("currency"),
        "yfinance_error": yfinance_error,
        "yahoo_chart_error": yahoo_chart_error,
    }
    _write_cache(cache_path, df, meta=cache_meta)

    # Ensure provenance is available to callers
    df.attrs["cache_meta"] = cache_meta

    return df



def clean_ohlcv_and_compute_returns(
    df: pd.DataFrame,
    *,
    fetch_metadata: dict[str, Any] | None = None,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    """
    Minimal cleaning (no indicators, no strategy logic) + compute close-to-close returns.

    Cleaning rules:
      - volume NaN -> 0.0 (do not alter prices)
      - (no 'ret' column is stored) diagnostics use close-to-close returns computed on the fly
    """
    # Basic schema check (reuse: df is expected standardized already)
    missing = set(REQUIRED_COLS) - set(df.columns)
    if missing:
        raise ValueError(f"df missing columns: {missing}")

    out = df.copy()

    # Metadata
    data_metadata: dict[str, Any] = {
        "start_date": out.index.min(),
        "end_date": out.index.max(),
        "rows": int(len(out)),
        "cleaning_timestamp_utc": dt.datetime.now(dt.timezone.utc),
    }

    # Merge fetch metadata if provided (cleaning keys win)
    if fetch_metadata is not None:
        merged = dict(fetch_metadata)
        merged.update(data_metadata)
        data_metadata = merged

    # Ensure return_definition is present and accurate
    if "return_definition" not in data_metadata or not data_metadata.get("return_definition"):
        data_metadata["return_definition"] = "close-to-close returns (definition unspecified)"

    # Minimal cleaning
    out[VOLUME_COL] = out[VOLUME_COL].fillna(0.0)

    # Diagnostics only (computed from close-to-close returns; do not persist returns in data layer)
    ret_cc = pd.to_numeric(out["close"], errors="coerce").astype("float64").pct_change().fillna(0.0)
    max_abs_ret = float(ret_cc.abs().max()) if len(out) else 0.0
    data_metadata["max_abs_return"] = max_abs_ret
    data_metadata["warning_spike_detected"] = bool(max_abs_ret > 0.5)

    if len(out) > 1:
        expected_bdays = pd.date_range(out.index[0], out.index[-1], freq="B")
        missing_bdays = expected_bdays.difference(out.index)
        data_metadata["missing_business_days_vs_B"] = int(len(missing_bdays))
    else:
        data_metadata["missing_business_days_vs_B"] = 0

    return out, data_metadata

def load_clean_ohlcv(
    ticker: str,
    years: int = 10,
    interval: str = "1d",
    auto_adjust: bool = True,
    *,
    as_of: dt.date | str | None = None,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    """
    Pipeline:
      1) fetch_and_standardize_ohlcv (OHLCV only)
      2) clean_ohlcv_and_compute_returns (minimal cleaning + metadata; does NOT add 'ret')
    """
    raw = fetch_and_standardize_ohlcv(
        ticker=ticker,
        years=years,
        interval=interval,
        auto_adjust=auto_adjust,
        as_of=as_of,
    )

    source_used = str(raw.attrs.get("data_source_used", "yfinance"))
    cache_meta = raw.attrs.get("cache_meta") if isinstance(raw.attrs, dict) else None
    yfinance_error = raw.attrs.get("yfinance_error") if isinstance(raw.attrs, dict) else None
    yahoo_chart_error = raw.attrs.get("yahoo_chart_error") if isinstance(raw.attrs, dict) else None

    # If data came from cache, recover the true upstream source from cache_meta.
    cache_hit = (source_used == "cache")
    true_source_used = source_used
    if cache_hit and isinstance(cache_meta, dict):
        true_source_used = str(cache_meta.get("data_source_used", source_used))
        yfinance_error = yfinance_error or cache_meta.get("yfinance_error")
        yahoo_chart_error = yahoo_chart_error or cache_meta.get("yahoo_chart_error")

    fetch_metadata: dict[str, Any] = {
        "source": true_source_used,
        "ticker": ticker,
        "years": int(years),
        "interval": interval,
        "auto_adjust": bool(auto_adjust),
        "fetch_date_local": dt.date.today().isoformat(),
        "exchange": (cache_meta.get("exchange") if isinstance(cache_meta, dict) else None),
        "currency": (cache_meta.get("currency") if isinstance(cache_meta, dict) else None),
        "return_definition": (
            "price_return (unadjusted close; Stooq fallback after Yahoo(yfinance) failure)"
            if true_source_used == "stooq"
            else (
                "total_return (Yahoo; cached history + recent chart patch; auto_adjust=True)"
                if (true_source_used == "yahoo_patch" and bool(auto_adjust))
                else (
                    "price_return (Yahoo; cached history + recent chart patch; auto_adjust=False)"
                    if (true_source_used == "yahoo_patch" and (not bool(auto_adjust)))
                    else (
                "total_return (Yahoo chart API; auto_adjust=True with adjusted-close scaling)"
                if (true_source_used == "yahoo_chart" and bool(auto_adjust))
                else (
                    "price_return (Yahoo chart API; auto_adjust=False on unadjusted close)"
                    if (true_source_used == "yahoo_chart" and (not bool(auto_adjust)))
                    else (
                        "total_return (auto_adjust=True; close-to-close returns on adjusted close)"
                        if bool(auto_adjust)
                        else "price_return (auto_adjust=False; close-to-close returns on unadjusted close)"
                    )
                )
                    )
                )
            )
        ),
        "warning_unadjusted_fallback": bool(true_source_used == "stooq"),
        "yfinance_error": (str(yfinance_error) if yfinance_error else None),
        "yahoo_chart_error": (str(yahoo_chart_error) if yahoo_chart_error else None),
        "cache_meta": cache_meta,
        "cache_hit": bool(cache_hit),
        "data_source_reported": source_used,
    }

    # Best-effort enrich exchange/currency.
    #
    # IMPORTANT: Avoid making additional yfinance network calls when:
    # - we already served OHLCV from cache, or
    # - live Yahoo fetch already errored.
    #
    # These extra calls are non-essential and can produce noisy tz/JSON parse errors.
    if (
        (not bool(fetch_metadata.get("cache_hit")))
        and (not bool(fetch_metadata.get("yfinance_error")))
        and (not bool(fetch_metadata.get("yahoo_chart_error")))
        and true_source_used in ("yfinance", "yahoo_chart")
        and (fetch_metadata.get("exchange") is None or fetch_metadata.get("currency") is None)
    ):
        try:
            import yfinance as yf  # local import to keep dependency surface small

            fi = yf.Ticker(ticker).fast_info
            if isinstance(fi, dict):
                fetch_metadata["exchange"] = fetch_metadata.get("exchange") or fi.get("exchange") or fi.get("exchangeName")
                fetch_metadata["currency"] = fetch_metadata.get("currency") or fi.get("currency")
        except Exception:
            pass

    df, meta = clean_ohlcv_and_compute_returns(raw, fetch_metadata=fetch_metadata)
    return df, meta
