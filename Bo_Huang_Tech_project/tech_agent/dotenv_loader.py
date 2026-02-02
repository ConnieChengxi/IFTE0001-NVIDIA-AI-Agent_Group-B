from __future__ import annotations

import os
from pathlib import Path


def load_dotenv_file(path: str | Path = ".env", *, override: bool = False) -> dict[str, str]:
    """
    Minimal .env loader (no external dependency).

    - Supports KEY=VALUE lines, optionally quoted values.
    - Ignores blank lines and comments starting with '#'.
    - By default, does NOT override existing environment variables.
    """
    p = Path(path)
    if not p.exists() or not p.is_file():
        return {}

    loaded: dict[str, str] = {}
    for raw in p.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            continue
        k, v = line.split("=", 1)
        key = k.strip()
        val = v.strip()
        if not key:
            continue
        # Strip matching quotes.
        if len(val) >= 2 and ((val[0] == val[-1] == '"') or (val[0] == val[-1] == "'")):
            val = val[1:-1]

        if override or (key not in os.environ):
            os.environ[key] = val
        loaded[key] = val

    return loaded

