import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv
import pandas as pd


@dataclass(frozen=True)
class Config:
    # Core
    symbol: str = "NVDA"
    peers: tuple[str, ...] = ("NVDA", "ADI", "QCOM", "TXN")
    years: set[int] = None  # annual statement years to keep
    asof: pd.Timestamp = pd.Timestamp("2025-01-31")

    # Paths
    cache_dir: Path = Path("data_raw/alphavantage")
    output_dir: str = "outputs"

    # DCF assumptions (align with your notebook defaults)
    forecast_years: int = 5
    terminal_g: float = 0.045

    # WACC defaults / fallbacks
    rf_fallback: float = 0.043       # risk-free (US)
    erp_fallback: float = 0.05       # ERP fallback (you used 5% fallback)
    tax_clip_low: float = 0.05
    tax_clip_high: float = 0.25

    # LLM
    use_llm: bool = True
    llm_model: str = "gpt-4o-mini"   # replace if your project standard differs
    llm_max_chars: int = 14000       # keep prompt bounded


def get_config() -> Config:
    # Load secrets.env like your notebook
    if Path("secrets.env").exists():
        load_dotenv("secrets.env")

    years = {2020, 2021, 2022, 2023, 2024, 2025}
    cfg = Config(years=years)

    # Hard requirement for AV key (same behaviour as your notebook)
    api_key = os.getenv("ALPHAVANTAGE_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("Missing ALPHAVANTAGE_API_KEY. Set env var or create secrets.env")

    return cfg

