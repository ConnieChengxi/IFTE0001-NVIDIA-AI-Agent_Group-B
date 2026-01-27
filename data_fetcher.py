import json
import os
import time
from pathlib import Path
from typing import Any

import requests

from config import Config

AV_BASE = "https://www.alphavantage.co/query"

FUNCTIONS = {
    "income_statement": "INCOME_STATEMENT",
    "balance_sheet": "BALANCE_SHEET",
    "cash_flow": "CASH_FLOW",
}


def ensure_cache_dir(cache_dir: Path) -> None:
    cache_dir.mkdir(parents=True, exist_ok=True)


def _api_key() -> str:
    key = os.getenv("ALPHAVANTAGE_API_KEY", "").strip()
    if not key:
        raise RuntimeError("Missing ALPHAVANTAGE_API_KEY")
    return key


def av_get(function: str, symbol: str | None = None, *, cache_dir: Path, sleep_s: int = 12, **kwargs) -> dict:
    """
    Cache-first Alpha Vantage getter.
    - If cache exists and looks valid -> return cache
    - Else call API, cache JSON, then return
    """
    ensure_cache_dir(cache_dir)
    sym = symbol or "GLOBAL"
    cache_path = cache_dir / f"{sym}_{function}.json"

    if cache_path.exists():
        try:
            return json.loads(cache_path.read_text(encoding="utf-8"))
        except Exception:
            pass

    params: dict[str, Any] = {"function": function, "apikey": _api_key(), **kwargs}
    if symbol:
        params["symbol"] = symbol

    r = requests.get(AV_BASE, params=params, timeout=60)
    r.raise_for_status()
    data = r.json()

    # basic validation (like your notebook)
    if "Error Message" in data:
        raise RuntimeError(f"Alpha Vantage error: {data['Error Message']}")
    if "Note" in data:
        raise RuntimeError(f"Alpha Vantage rate limit: {data['Note']}")

    cache_path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    time.sleep(sleep_s)
    return data


def fetch_financial_statements_cached(symbol: str, cfg: Config) -> dict[str, Path]:
    """
    Download (or reuse) statement JSONs and return their paths.
    """
    paths: dict[str, Path] = {}
    for name, fn in FUNCTIONS.items():
        p = cfg.cache_dir / f"{symbol}_{name}.json"
        if not p.exists():
            data = av_get(fn, symbol, cache_dir=cfg.cache_dir)
            p.write_text(json.dumps(data, indent=2), encoding="utf-8")
        paths[name] = p
    return paths


def fetch_overview_cached(symbol: str, cfg: Config) -> dict:
    return av_get("OVERVIEW", symbol, cache_dir=cfg.cache_dir)


def market_price_realtime_av(symbol: str, cfg: Config) -> float | None:
    """
    Uses GLOBAL_QUOTE; returns None if missing.
    """
    data = av_get("GLOBAL_QUOTE", symbol, cache_dir=cfg.cache_dir)
    q = data.get("Global Quote", {})
    price = q.get("05. price") or q.get("05. Price") or q.get("price")
    try:
        return float(price)
    except Exception:
        return None
