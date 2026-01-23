import os
import json
import time
from pathlib import Path

import requests
from dotenv import load_dotenv

AV_BASE = "https://www.alphavantage.co/query"

FUNCTIONS = {
    "income_statement": "INCOME_STATEMENT",
    "balance_sheet": "BALANCE_SHEET",
    "cash_flow": "CASH_FLOW",
}

RAW_DIR = Path("data_raw/alphavantage")
RAW_DIR.mkdir(parents=True, exist_ok=True)


def get_api_key() -> str:
    if Path("secrets.env").exists():
        load_dotenv("secrets.env")

    api_key = os.getenv("ALPHAVANTAGE_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("Missing ALPHAVANTAGE_API_KEY. Set env var or create secrets.env")
    return api_key


def fetch_av_json(function: str, symbol: str, api_key: str) -> dict:
    params = {"function": function, "symbol": symbol, "apikey": api_key}
    r = requests.get(AV_BASE, params=params, timeout=60)
    r.raise_for_status()
    data = r.json()
    if "Error Message" in data:
        raise RuntimeError(f"Alpha Vantage error: {data['Error Message']}")
    if "Note" in data:
        raise RuntimeError(f"Alpha Vantage rate limit: {data['Note']}")
    return data


def save_json(data: dict, path: Path) -> None:
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")


def fetch_annual_statement_paths(symbol: str, api_key: str | None = None, sleep_s: int = 12) -> dict:
    api_key = api_key or get_api_key()

    paths: dict[str, Path] = {}
    for name, fn in FUNCTIONS.items():
        out_path = RAW_DIR / f"{symbol}_{name}.json"

        if out_path.exists():
            paths[name] = out_path
            continue

        data = fetch_av_json(fn, symbol, api_key)
        save_json(data, out_path)
        paths[name] = out_path
        time.sleep(sleep_s)

    return paths
