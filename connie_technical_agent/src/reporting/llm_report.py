from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Optional

import pandas as pd
from openai import OpenAI


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
) -> Dict[str, Any]:
    """
    Build a compact, structured evidence pack for the LLM.

    Key principle:
    - LLM writes narrative ONLY using numbers we computed (no invented data).
    """
    out = out.copy()

    start = str(out.index.min().date())
    end = str(out.index.max().date())

    latest = out.iloc[-1]
    latest_state = {
        "date": str(out.index[-1].date()),
        "close": float(latest["Close"]) if "Close" in out.columns else None,
        "position": float(latest["position"]) if "position" in out.columns else None,
        "RSI_14": float(latest["RSI_14"]) if "RSI_14" in out.columns else None,
        "MACD": float(latest["MACD"]) if "MACD" in out.columns else None,
        "MACD_Signal": float(latest["MACD_Signal"]) if "MACD_Signal" in out.columns else None,
        "MA20": float(latest["MA20"]) if "MA20" in out.columns else None,
        "MA50": float(latest["MA50"]) if "MA50" in out.columns else None,
        "MA200": float(latest["MA200"]) if "MA200" in out.columns else None,
    }

    trade_highlights: list[dict[str, Any]] = []
    if isinstance(trades, pd.DataFrame) and len(trades) > 0 and "trade_return" in trades.columns:
        t = trades.sort_values("trade_return")
        sample = pd.concat([t.head(2), t.tail(2)], axis=0)
        for _, r in sample.iterrows():
            trade_highlights.append(
                {
                    "entry_date": str(pd.to_datetime(r["entry_date"]).date()),
                    "exit_date": str(pd.to_datetime(r["exit_date"]).date()),
                    "trade_return": float(r["trade_return"]),
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
- Do NOT invent missing values. If something is missing, write "not available".
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
    Full report prompt.
    Preference order:
      1) src/reporting/prompts/full_report.md if it exists
      2) built-in fallback template
    """
    template = _safe_load_prompt_template("full_report.md")
    if template is None:
        template = """
# Role
You are a buy-side technical analyst writing a concise internal research memo.
Tone: rigorous, restrained, and professional. No hype. No marketing language.
Do NOT invent numbers, dates, or facts. Use only the evidence provided.

# Output requirements
Return a single Markdown document with the exact sections below.
If a required field is missing, explicitly write: "Not available from provided evidence."

# Sections (must follow exactly)
## 1. Context & Objective
## 2. Strategy Overview
## 3. Backtest Results
## 4. Equity Curve & Drawdown Interpretation
## 5. Current Signal Snapshot
## 6. Limitations & Next Steps
## 7. Disclaimer
""".strip()

    return f"""
{template}

EVIDENCE JSON:
{json.dumps(evidence, indent=2, ensure_ascii=False)}
""".strip()


# -----------------------------
# LLM calls
# -----------------------------
def llm_generate_trade_note(
    evidence: Dict[str, Any],
    model: str = "gpt-4.1-mini",
) -> str:
    """Calls OpenAI Responses API and returns Markdown text for the trade note."""
    client = OpenAI()
    prompt = _prompt_trade_note(evidence)

    resp = client.responses.create(
        model=model,
        input=prompt,
    )

    print("DEBUG llm_trade_note: output_text len =", len(resp.output_text))
    return resp.output_text


def llm_generate_full_report(
    evidence: Dict[str, Any],
    model: str = "gpt-4.1-mini",
) -> str:
    """Calls OpenAI Responses API and returns Markdown text for the full report."""
    client = OpenAI()
    prompt = _prompt_full_report(evidence)

    resp = client.responses.create(
        model=model,
        input=prompt,
    )

    print("DEBUG llm_full_report: output_text len =", len(resp.output_text))
    return resp.output_text
