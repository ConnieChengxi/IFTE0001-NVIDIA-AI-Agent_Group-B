import os
import json
import time
from pathlib import Path

import requests
from dotenv import load_dotenv

from .config import DEFAULT_SLEEP_S

# =========================
# Alpha Vantage config
# =========================
AV_BASE = "https://www.alphavantage.co/query"

FUNCTIONS = {
    "income_statement": "INCOME_STATEMENT",
    "balance_sheet": "BALANCE_SHEET",
    "cash_flow": "CASH_FLOW",
}

RAW_DIR = Path("data_raw/alphavantage")
RAW_DIR.mkdir(parents=True, exist_ok=True)

BASE_DIR = Path(__file__).resolve().parents[1]  # agents/extra/Zehui_fundamental
SECRETS_PATH = BASE_DIR / "secrets.env"

if SECRETS_PATH.exists():
    load_dotenv(SECRETS_PATH)


def get_api_key() -> str:
    api_key = os.getenv("ALPHAVANTAGE_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError(
            "Missing ALPHAVANTAGE_API_KEY. "
            "Put it in agents/extra/Zehui_fundamental/secrets.env"
        )
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


def fetch_annual_statement_paths(
    symbol: str,
    sleep_s: int = DEFAULT_SLEEP_S,
) -> dict:
    """
    Download (or reuse cached) annual income/balance/cashflow JSON files.
    Returns: {name: Path}
    """
    api_key = get_api_key()
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
