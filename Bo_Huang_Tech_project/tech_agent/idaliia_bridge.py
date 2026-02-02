from __future__ import annotations

import os
import re
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class IdaliiaRunResult:
    """Result of running the external Idaliia fundamental module (best-effort)."""

    ok: bool
    memo_copy_rel: str | None
    log_copy_rel: str | None
    recommendation: str | None
    target_price: float | None
    upside: float | None
    generated_at_utc: str
    error: str | None = None


def _parse_stdout_for_key_lines(text: str) -> tuple[str | None, float | None, float | None]:
    """
    Parse Idaliia's stdout for a few stable, high-signal fields.
    This avoids changing their code and still keeps the pipeline explainable.
    """
    rec = None
    target = None
    upside = None

    m = re.search(r"Recommendation:\s*([A-Za-z ]+)\s*$", text, flags=re.M)
    if m:
        rec = m.group(1).strip().upper()

    m = re.search(r"Target Price:\s*\\$([0-9]+(?:\\.[0-9]+)?)", text)
    if m:
        try:
            target = float(m.group(1))
        except Exception:
            target = None

    m = re.search(r"Upside:\s*([+-]?[0-9]+(?:\\.[0-9]+)?)%", text)
    if m:
        try:
            upside = float(m.group(1)) / 100.0
        except Exception:
            upside = None

    return rec, target, upside


def run_idaliia_fundamental_memo(
    *,
    ticker: str,
    out_dir: str | Path,
    timeout_s: int = 360,
) -> IdaliiaRunResult:
    """
    Run the external Idaliia fundamental_analyst_agent to generate an HTML memo, then copy it into `out_dir`.

    Notes
    - This may require network access and an `ALPHA_VANTAGE_API_KEY` in the environment.
    - We intentionally disable Idaliia's own LLM narrative (if any) in our patched external code,
      so this step should not consume OpenAI credits.
    """
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    generated_at = datetime.now(timezone.utc).isoformat()

    ext_root = (
        Path(__file__).resolve().parents[1]
        / "external"
        / "idaliia_fundamental"
        / "fundamental_analyst_agent"
    )
    script = ext_root / "run_analysis.py"
    ext_outputs = ext_root / "outputs"

    log_path = out_dir / "FUND_idaliia_run.log"
    memo_copy = out_dir / "FUND_idaliia_report.html"

    if not script.exists():
        return IdaliiaRunResult(
            ok=False,
            memo_copy_rel=None,
            log_copy_rel=None,
            recommendation=None,
            target_price=None,
            upside=None,
            generated_at_utc=generated_at,
            error="Idaliia run_analysis.py not found.",
        )

    # Run as a subprocess to keep external dependencies isolated.
    env = os.environ.copy()
    # Defensive: avoid any accidental LLM calls from the external project.
    env["OPENAI_API_KEY"] = ""

    try:
        proc = subprocess.run(
            [sys.executable, str(script), str(ticker).upper()],
            cwd=str(ext_root),
            env=env,
            capture_output=True,
            text=True,
            timeout=timeout_s,
        )
    except subprocess.TimeoutExpired:
        log_path.write_text("Idaliia run timed out.\n", encoding="utf-8")
        return IdaliiaRunResult(
            ok=False,
            memo_copy_rel=None,
            log_copy_rel=str(log_path.relative_to(out_dir.parent)),
            recommendation=None,
            target_price=None,
            upside=None,
            generated_at_utc=generated_at,
            error=f"Timed out after {timeout_s}s.",
        )
    except Exception as e:
        log_path.write_text(f"Idaliia run failed: {e}\n", encoding="utf-8")
        return IdaliiaRunResult(
            ok=False,
            memo_copy_rel=None,
            log_copy_rel=str(log_path.relative_to(out_dir.parent)),
            recommendation=None,
            target_price=None,
            upside=None,
            generated_at_utc=generated_at,
            error=str(e),
        )

    # Persist stdout/stderr for reproducibility.
    log_path.write_text(
        (proc.stdout or "") + "\n\n--- STDERR ---\n" + (proc.stderr or ""),
        encoding="utf-8",
    )

    rec, target, upside = _parse_stdout_for_key_lines((proc.stdout or "") + "\n" + (proc.stderr or ""))

    src = ext_outputs / f"{str(ticker).upper()}_Investment_Memo.html"
    if proc.returncode != 0:
        return IdaliiaRunResult(
            ok=False,
            memo_copy_rel=None,
            log_copy_rel=str(log_path.relative_to(out_dir.parent)),
            recommendation=rec,
            target_price=target,
            upside=upside,
            generated_at_utc=generated_at,
            error=f"Idaliia subprocess exit code {proc.returncode}.",
        )

    if not src.exists():
        return IdaliiaRunResult(
            ok=False,
            memo_copy_rel=None,
            log_copy_rel=str(log_path.relative_to(out_dir.parent)),
            recommendation=rec,
            target_price=target,
            upside=upside,
            generated_at_utc=generated_at,
            error="Idaliia did not produce the expected HTML memo file.",
        )

    try:
        memo_copy.write_text(src.read_text(encoding="utf-8"), encoding="utf-8")
    except Exception as e:
        return IdaliiaRunResult(
            ok=False,
            memo_copy_rel=None,
            log_copy_rel=str(log_path.relative_to(out_dir.parent)),
            recommendation=rec,
            target_price=target,
            upside=upside,
            generated_at_utc=generated_at,
            error=f"Failed to copy memo: {e}",
        )

    return IdaliiaRunResult(
        ok=True,
        memo_copy_rel=str(memo_copy.relative_to(out_dir.parent)),
        log_copy_rel=str(log_path.relative_to(out_dir.parent)),
        recommendation=rec,
        target_price=target,
        upside=upside,
        generated_at_utc=generated_at,
        error=None,
    )

