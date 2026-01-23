import os
import json
import time
from pathlib import Path

import requests
from dotenv import load_dotenv

if Path("secrets.env").exists():
    load_dotenv("secrets.env")

API_KEY = os.getenv("ALPHAVANTAGE_API_KEY", "").strip()
if not API_KEY:
    raise RuntimeError(
        "Missing ALPHAVANTAGE_API_KEY. Set env var or create secrets.env"
    )

AV_BASE = "https://www.alphavantage.co/query"

