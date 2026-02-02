from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import json

@dataclass(frozen=True)
class FundamentalSnapshot:
    """Best-effort fundamental snapshot for display (not used as alpha)."""

    source: str
    fetched_at_utc: str
    data: dict[str, Any]


def fetch_idaliia_yahoo_snapshot(ticker: str) -> FundamentalSnapshot | None:
    """
    Fetch a small set of valuation / analyst consensus fields using the Idaliia fundamental module
    (external/external_fundamental_analysis/.../yahoo_finance_client.py).

    Best-effort:
      - Returns None on failure (caller should degrade gracefully).
      - Network access may be required if not cached.
    """
    try:
        t = str(ticker).strip().upper()

        # Local cache for reproducibility + rate-limit resilience.
        cache_path = (
            Path(__file__).resolve().parents[1]
            / "data_cache"
            / "fundamentals"
            / f"{t}_yahoo_snapshot.json"
        )
        if cache_path.exists():
            try:
                obj = json.loads(cache_path.read_text(encoding="utf-8"))
                if isinstance(obj, dict) and isinstance(obj.get("data"), dict) and obj.get("data"):
                    return FundamentalSnapshot(
                        source=str(obj.get("source") or "Yahoo Finance snapshot (cached)"),
                        fetched_at_utc=str(obj.get("fetched_at_utc") or ""),
                        data=dict(obj.get("data") or {}),
                    )
            except Exception:
                # Ignore cache corruption; fall back to live fetch.
                pass

        ext_root = (
            Path(__file__).resolve().parents[1]
            / "external"
            / "idaliia_fundamental"
            / "fundamental_analyst_agent"
        )

        if not ext_root.exists():
            return None

        import sys

        sys.path.insert(0, str(ext_root))

        from src.data_collection.yahoo_finance_client import YahooFinanceClient  # type: ignore

        # CacheManager depends on python-dotenv in the external project; keep this optional so the
        # main project doesn't need that extra dependency just to fetch a snapshot.
        cache = None
        try:
            from src.data_collection.cache_manager import CacheManager  # type: ignore

            cache = CacheManager()
        except Exception:
            cache = None

        client = YahooFinanceClient(cache)
        data = client.get_forward_estimates(t) or {}

        fetched_at = datetime.now(timezone.utc).isoformat()
        snap = FundamentalSnapshot(
            source="Yahoo Finance snapshot (via Idaliia fundamental module)",
            fetched_at_utc=fetched_at,
            data=data,
        )
        # Cache only if we got something meaningful (avoid persisting empty shells).
        if isinstance(data, dict) and data and any(v is not None for v in data.values()):
            try:
                cache_path.parent.mkdir(parents=True, exist_ok=True)
                cache_path.write_text(
                    json.dumps(
                        {"source": snap.source, "fetched_at_utc": snap.fetched_at_utc, "data": snap.data},
                        indent=2,
                        default=str,
                    ),
                    encoding="utf-8",
                )
            except Exception:
                pass
        return snap
    except Exception:
        return None
