from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]

FUND_RUN = REPO_ROOT / "fundamental_analyst_agent" / "run_demo.py"
TECH_RUN = REPO_ROOT / "connie_technical_agent" / "run_demo.py"


def run_and_capture(cmd: list[str]) -> str:
    """Run a command, print stdout/stderr, and return combined text."""
    print("\n[CMD]", " ".join(cmd))
    p = subprocess.run(cmd, text=True, capture_output=True)

    if p.stdout:
        print(p.stdout)
    if p.stderr:
        print(p.stderr)

    if p.returncode != 0:
        raise RuntimeError(f"Command failed with code {p.returncode}: {' '.join(cmd)}")

    return (p.stdout or "") + "\n" + (p.stderr or "")


def extract_recommendation(text: str) -> str:
    """
    Parse fundamental output like:
      [OK] RECOMMENDATION: BUY
    """
    m = re.search(r"RECOMMENDATION:\s*([A-Z ]+)", text.upper())
    if not m:
        return "UNKNOWN"
    r = m.group(1).strip()
    if "BUY" in r:
        return "BUY"
    if "HOLD" in r or "NEUTRAL" in r:
        return "HOLD"
    if "SELL" in r:
        return "SELL"
    return r


def main() -> int:
    ap = argparse.ArgumentParser(description="Hybrid Controller (minimal): fundamental gate -> technical run")
    ap.add_argument("--ticker", default="NVDA", help="Ticker for fundamental gate (positional for their run_demo)")
    ap.add_argument("--allow", default="BUY,HOLD", help="Gate passes for these recommendations")
    args = ap.parse_args()

    if not FUND_RUN.exists():
        raise FileNotFoundError(f"Fundamental run_demo not found: {FUND_RUN}")
    if not TECH_RUN.exists():
        raise FileNotFoundError(f"Technical run_demo not found: {TECH_RUN}")

    # 1) Run fundamental (positional ticker)
    fund_cmd = [sys.executable, str(FUND_RUN), args.ticker]
    fund_out = run_and_capture(fund_cmd)

    rec = extract_recommendation(fund_out)
    allowed = {x.strip().upper() for x in args.allow.split(",") if x.strip()}
    print(f"\n[FUND] recommendation = {rec} | allowed = {sorted(allowed)}")

    # 2) Gate
    if rec not in allowed:
        print("[HYBRID] Gate blocked -> skip technical (position = 0)")
        return 0

    # 3) Run technical (no args for now, most robust)
    tech_cmd = [sys.executable, str(TECH_RUN)]
    run_and_capture(tech_cmd)

    print("\n[HYBRID] Done.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())