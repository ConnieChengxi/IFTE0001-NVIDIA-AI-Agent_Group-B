# src/llm_report.py
"""
LLM reporting helpers.

This module generates a structured technical trade note from:
- latest market snapshot (ticker, date, close)
- indicator settings / strategy description
- backtest metrics

The OpenAI API key is read from the environment:
    OPENAI_API_KEY=...

If the key is missing, the calling pipeline can choose to skip the LLM step.
"""

from __future__ import annotations

import os
from typing import Any, Dict, Optional

from openai import OpenAI


def _require_api_key(env_name: str = "OPENAI_API_KEY") -> str:
    key = os.getenv(env_name)
    if not key:
        raise RuntimeError(
            f"{env_name} is not set.\n"
            "macOS/Linux:\n"
            f"  export {env_name}='your_key_here'\n"
            "Windows (PowerShell):\n"
            f"  setx {env_name} \"your_key_here\"\n"
            "Then restart your terminal / Jupyter kernel."
        )
    return key


def _format_kv_block(title: str, payload: Any) -> str:
    """Formats dictionaries / primitives into a simple readable block for the prompt."""
    lines = [f"{title}:"]
    if isinstance(payload, dict):
        for k, v in payload.items():
            lines.append(f"- {k}: {v}")
    else:
        lines.append(str(payload))
    return "\n".join(lines)


def generate_trade_note(
    ticker: str,
    company_name: str,
    latest_date: str,
    latest_close: float,
    indicators: Dict[str, Any],
    metrics: Dict[str, Any],
    strategy_desc: str,
    assumptions: Optional[Dict[str, Any]] = None,
    model: str = "gpt-4o-mini",
) -> str:
    """
    Generate technical trade note.

    Notes:
    - This function does NOT fetch market data; it only writes the note.
    - Keep inputs honest (no fabricated values). The prompt instructs the model
      to only use provided data.
    """
    _require_api_key()

    client = OpenAI()

    assumptions = assumptions or {}

    header = (
        "You are writing as a buy-side technical analyst at an asset management firm.\n"
        "No hype, no guarantees, no 'this proves' language.\n"
    )

    structure = (
        "Use the following section headings exactly:\n"
        "1) Trade Overview\n"
        "2) Executive Summary\n"
        "3) Technical Evidence\n"
        "4) Strategy & Signal Logic\n"
        "5) Backtest Summary\n"
        "6) Risks, Assumptions, and Limitations\n"
        "7) Conclusion & Trade Recommendation\n"
    )

    requirements = (
        "Hard requirements:\n"
        "- Length: approximately 1–2 pages in markdown.\n"
        "- Include: Ticker, Company, Asset class (Equity), Data end date, Latest closing price\n"
        "- Executive Summary: 3–6 bullet points with headline metrics and a recommendation\n"
        "- Backtest Summary must explicitly state: CAGR, Sharpe, Max Drawdown, Hit Rate, Number of Trades\n"
        "- Risks must include at least: regime dependence, single-stock concentration, trading frictions, parameter sensitivity\n"
        "- Recommendation must be one of: Enter / Hold / Avoid, plus conditions that would invalidate it\n"
    )

    context_lines = [
        "INPUT DATA",
        "---------",
        f"Ticker: {ticker}",
        f"Company: {company_name}",
        "Asset class: Equity",
        f"Data end date: {latest_date}",
        f"Latest closing price: {latest_close}",
        "",
        _format_kv_block("Indicator settings / components", indicators),
        "",
        "Strategy description (plain English):",
        strategy_desc.strip(),
        "",
        _format_kv_block("Backtest metrics (computed)", metrics),
        "",
        _format_kv_block("Assumptions / notes", assumptions),
    ]

    prompt = "\n\n".join([header, structure, requirements, "\n".join(context_lines)]).strip()

    resp = client.responses.create(
        model=model,
        input=prompt,
    )

    return resp.output_text


def save_trade_note(text: str, out_path: str = "outputs/trade_note.md") -> None:
    folder = os.path.dirname(out_path)
    if folder:
        os.makedirs(folder, exist_ok=True)

    with open(out_path, "w", encoding="utf-8") as f:
        f.write(text.strip() + "\n")

