from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Optional

import pandas as pd
from openai import OpenAI

from src.reporting.strategy_rationale import get_strategy_rationale



# -----------------------------
# Prompt templates
# -----------------------------
def load_prompt_template(name: str) -> str:
    """
    Load a prompt template from src/reporting/prompts/<name>.
    Raises FileNotFoundError if missing.
    """
    p = Path(__file__).resolve().parent / "prompts" / name
    return p.read_text(encoding="utf-8")


def _safe_load_prompt_template(name: str) -> Optional[str]:
    """Return template string if exists; otherwise None."""
    p = Path(__file__).resolve().parent / "prompts" / name
    if p.exists():
        return p.read_text(encoding="utf-8")
    return None


# -----------------------------
# Evidence pack
# -----------------------------
def build_evidence_pack(
    out: pd.DataFrame,
    trades: pd.DataFrame,
    metrics: Dict[str, Any],
    ticker: str,
    chart_paths: Optional[Dict[str, str]] = None,
    df: Optional[pd.DataFrame] = None,  # ✅ NEW: prefer df for latest_state
) -> Dict[str, Any]:
    """
    Build a compact, structured evidence pack for the LLM.

    Key principle:
    - LLM writes narrative ONLY using numbers we computed (no invented data).
    - latest_state should come from df (features/signals), not out.
    """
    out = out.copy()
    start = str(out.index.min().date())
    end = str(out.index.max().date())

    # Prefer df for latest state (RSI/MACD/MA live here)
    latest_state = {
        "date": None,
        "close": None,
        "position": None,
        "entry": None,
        "exit": None,
        "RSI_14": None,
        "MACD": None,
        "MACD_Signal": None,
        "MA20": None,
        "MA50": None,
        "MA200": None,
    }

    # position might be in out
    try:
        latest_out = out.iloc[-1]
        if "position" in out.columns:
            latest_state["position"] = float(latest_out["position"])
    except Exception:
        pass

    # Pull technical snapshot from df if provided
    if isinstance(df, pd.DataFrame) and len(df) > 0:
        dfx = df.copy()
        last = dfx.iloc[-1]
        latest_state["date"] = str(dfx.index[-1].date())
        if "Close" in dfx.columns:
            latest_state["close"] = float(last["Close"])
        if "entry" in dfx.columns:
            latest_state["entry"] = bool(last["entry"])
        if "exit" in dfx.columns:
            latest_state["exit"] = bool(last["exit"])
        for k in ["RSI_14", "MACD", "MACD_Signal", "MA20", "MA50", "MA200"]:
            if k in dfx.columns and pd.notna(last[k]):
                latest_state[k] = float(last[k])
    else:
        # fallback: attempt from out (best-effort)
        try:
            latest_out = out.iloc[-1]
            latest_state["date"] = str(out.index[-1].date())
            if "Close" in out.columns:
                latest_state["close"] = float(latest_out["Close"])
            for k in ["RSI_14", "MACD", "MACD_Signal", "MA20", "MA50", "MA200"]:
                if k in out.columns and pd.notna(latest_out[k]):
                    latest_state[k] = float(latest_out[k])
        except Exception:
            pass

    # Trade highlights (best/worst) - robust to column names
    trade_highlights: list[dict[str, Any]] = []

    if isinstance(trades, pd.DataFrame) and len(trades) > 0:
        # try infer return column
        ret_candidates = ["trade_return", "return", "ret", "pnl", "trade_pnl"]
        ret_col = next((c for c in ret_candidates if c in trades.columns), None)
        entry_col = next((c for c in ["entry_date", "entry", "EntryDate"] if c in trades.columns), None)
        exit_col = next((c for c in ["exit_date", "exit", "ExitDate"] if c in trades.columns), None)

        if ret_col is not None:
            t = trades.sort_values(ret_col)
            sample = pd.concat([t.head(2), t.tail(2)], axis=0)
            for _, r in sample.iterrows():
                trade_highlights.append(
                    {
                        "entry_date": str(pd.to_datetime(r[entry_col]).date()) if entry_col else None,
                        "exit_date": str(pd.to_datetime(r[exit_col]).date()) if exit_col else None,
                        "trade_metric_name": ret_col,
                        "trade_metric_value": float(r[ret_col]) if pd.notna(r[ret_col]) else None,
                    }
                )

    evidence = {
        "ticker": ticker,
        "backtest_window": {"start": start, "end": end},
        "metrics": metrics,
        "latest_state": latest_state,
        "trade_highlights": trade_highlights,
        "assumptions": {
            "strategy_type": "long/flat",
            "signal_execution": "entry/exit signals shifted by 1 day to avoid look-ahead bias",
            "transaction_cost_model": "cost_bps applied per turnover (position change)",
        },
        "charts": chart_paths or {},
    }
    return evidence


# -----------------------------
# Prompts
# -----------------------------
def _prompt_trade_note(evidence: Dict[str, Any]) -> str:
    """Trade note prompt: force the model to ONLY use provided numbers."""
    return f"""
You are a buy-side technical analyst writing a client-ready trade note in Markdown.

STRICT RULES:
- Use ONLY the numbers and facts in the EVIDENCE JSON.
- Do NOT invent missing values. If something is missing, write "Not available from provided evidence."
- Do not claim you "saw" charts; you may only refer to chart filenames as pipeline outputs.
- Be transparent about assumptions and limitations.

OUTPUT (use these headings exactly):
# {evidence.get("ticker", "TICKER")} - Technical Trade Note
## 1. Executive Summary
## 2. Current Signal Snapshot
## 3. Backtest Results (with transaction costs)
## 4. Risk & Position Sizing Considerations
## 5. Limitations & Next Steps

EVIDENCE JSON:
{json.dumps(evidence, indent=2, ensure_ascii=False)}
""".strip()


def _prompt_full_report(evidence: Dict[str, Any]) -> str:
    """
    Full report prompt with fixed Strategy Rationale injected verbatim.
    The LLM must not modify or reinterpret the strategy section.
    """
    strategy_rationale = get_strategy_rationale()

    return f"""
You are writing a buy-side technical research report.

IMPORTANT INSTRUCTIONS:
- The Strategy Design Philosophy section below is FIXED.
- Do NOT rewrite, summarise, reinterpret, or critique it.
- All subsequent analysis must be consistent with this philosophy.
- Use ONLY the numbers and facts provided in the EVIDENCE JSON.

{strategy_rationale}

---

## Backtest Setup & Assumptions

## Performance Results

## Behaviour Across Market Regimes

## Limitations & Future Extensions

## Conclusion

EVIDENCE JSON:
{json.dumps(evidence, indent=2, ensure_ascii=False)}
""".strip()



# -----------------------------
# LLM calls
# -----------------------------
def llm_generate_trade_note(evidence: Dict[str, Any], model: str = "gpt-4.1-mini") -> str:
    client = OpenAI()
    prompt = _prompt_trade_note(evidence)
    resp = client.responses.create(
        model=model,
        input=prompt,
        temperature=0,
        max_output_tokens=900,
    )
    return resp.output_text


def llm_generate_full_report(evidence: Dict[str, Any], model: str = "gpt-4.1-mini") -> str:
    client = OpenAI()
    prompt = _prompt_full_report(evidence)
    resp = client.responses.create(
        model=model,
        input=prompt,
        temperature=0,
        max_output_tokens=1400,
    )
    return resp.output_text
