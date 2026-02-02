"""
LLM-powered report generation for technical analysis.

This module provides functions to build evidence packs from backtest results
and generate narrative reports using OpenAI's API.
"""
from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

import pandas as pd
from openai import OpenAI
def build_evidence_pack(
    out: pd.DataFrame,
    trades: pd.DataFrame,
    metrics: Dict[str, Any],
    ticker: str,
    chart_paths: Optional[Dict[str, str]] = None,
    df: Optional[pd.DataFrame] = None,
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
    except (IndexError, KeyError):
        # Empty DataFrame - use default None value
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
        except (IndexError, KeyError, AttributeError):
            # Empty DataFrame or missing columns - use default None values
            pass

    # Trade highlights (best/worst) - robust to column names
    trade_highlights: list[dict[str, Any]] = []
    all_trades: list[dict[str, Any]] = []

    if isinstance(trades, pd.DataFrame) and len(trades) > 0:
        # try infer return column
        ret_candidates = ["trade_return", "return", "ret", "pnl", "trade_pnl"]
        ret_col = next((c for c in ret_candidates if c in trades.columns), None)
        entry_col = next((c for c in ["entry_date", "entry", "EntryDate"] if c in trades.columns), None)
        exit_col = next((c for c in ["exit_date", "exit", "ExitDate"] if c in trades.columns), None)

        if ret_col is not None:
            # All trades sorted by entry date
            t_all = trades.sort_values(entry_col) if entry_col else trades
            for _, r in t_all.iterrows():
                all_trades.append(
                    {
                        "entry_date": str(pd.to_datetime(r[entry_col]).date()) if entry_col else None,
                        "exit_date": str(pd.to_datetime(r[exit_col]).date()) if exit_col else None,
                        "trade_metric_name": ret_col,
                        "trade_metric_value": float(r[ret_col]) if pd.notna(r[ret_col]) else None,
                    }
                )

            # Highlights: best/worst 2 trades
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
        "all_trades": all_trades,
        "assumptions": {
            "strategy_type": "long/flat",
            "signal_execution": "entry/exit signals shifted by 1 day to avoid look-ahead bias",
            "transaction_cost_model": "cost_bps applied per turnover (position change)",
        },
        "charts": chart_paths or {},
    }
    return evidence


def _prompt_trade_note(evidence: Dict[str, Any]) -> str:
    """Trade note prompt: force the model to ONLY use provided numbers."""
    return f"""
You are a buy-side technical analyst writing a client-ready trade note in Markdown.

STRICT RULES:
- Use ONLY the numbers and facts in the EVIDENCE JSON.
- Do NOT invent missing values. If something is missing, write "Not available from provided evidence."
- Do not claim you "saw" charts; you may only refer to chart filenames as pipeline outputs.
- Be transparent about assumptions and limitations.
- Do NOT use bold formatting (**text**) inside bullet points. Write all bullet point content as plain text.

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
    Full report prompt that generates detailed report matching the PDF template.
    """
    ticker = evidence.get("ticker", "TICKER")
    metrics = evidence.get("metrics", {})
    latest = evidence.get("latest_state", {})
    window = evidence.get("backtest_window", {})
    trades = evidence.get("trade_highlights", [])

    return f"""
You are a buy-side technical analyst writing a professional technical analysis report in Markdown.

CRITICAL RULES:
- Use ONLY the numbers from EVIDENCE JSON below. Do NOT invent any numbers.
- Follow the EXACT structure below with all sections and subsections.
- Use bullet points for Backtest Setup, Interpretation, and Market Regimes sections.
- Use tables where specified.
- Include specific numbers from latest_state (close, MA20, MA50, MA200, MACD, MACD_Signal, RSI_14).
- Do NOT use bold formatting (**text**) inside bullet points. Only use bold for the fixed labels in Backtest Setup section (e.g., **Ticker:**). All other bullet point text should be plain text without bold.

REQUIRED STRUCTURE (follow exactly):

## Backtest Setup & Assumptions

- **Ticker:** {ticker}
- **Backtest Period:** [use backtest_window.start] – [use backtest_window.end]
- **Strategy Type:** Long/Flat
- **Signal Execution:** Entry and exit signals are shifted by one day to avoid look-ahead bias.
- **Transaction Costs:** 10 basis points applied per turnover (position change).
- **Initial Equity:** 1.0 unit
- **Final Equity:** [use metrics.EquityEnd] units
- **Number of Trades:** [use metrics.NumTrades] discrete trades executed over the backtest window.

## Performance Results

| METRIC | VALUE |
|--------|-------|
| CAGR | [metrics.CAGR]% |
| Sharpe Ratio | [metrics.Sharpe] |
| Max Drawdown (Strategy) | [metrics.MaxDrawdown]% |
| Max Drawdown (Buy-and-Hold) | [metrics.BuyHoldMaxDrawdown]% |
| Hit Rate | [metrics.HitRate]% |
| Equity Multiple | [metrics.EquityMultiple]x |
| Buy-and-Hold Multiple | [metrics.BuyHoldMultiple]x |

## Interpretation

Write 5 bullet points interpreting the performance metrics. Each bullet should:
- Reference a specific metric with its value
- Explain what it means for the strategy
- Be factual and professional

IMPORTANT interpretation guidelines:

For Max Drawdown: Compare the strategy's Max Drawdown [metrics.MaxDrawdown] against the buy-and-hold benchmark drawdown [metrics.BuyHoldMaxDrawdown]. Explicitly contrast these values, quantify the magnitude of drawdown reduction (e.g., "reduced drawdown by X percentage points"), and interpret this improvement in the context of risk management and downside protection. Focus on peak-to-trough risk rather than return performance. Maintain academic, institutional tone.

For Hit Rate: If the hit rate is low relative to trade frequency, explain the relationship between hit rate and payoff structure. A low hit rate combined with positive overall returns indicates that winning trades generate significantly larger gains than losing trades cost. Explain this as an intentional selectivity-payoff trade-off - the strategy prioritizes large gains on winning positions over trade frequency.

## Behaviour Across Market Regimes

### Regime Filtering (MA200)

Write 3 bullet points about MA200 as regime filter. Include:
- Current price vs MA200 comparison using latest_state values
- How it prevented exposure during adverse periods

### Trend Persistence (MA20 and MA50)

Write 3 bullet points about MA20/MA50. Include:
- Current MA20 and MA50 values from latest_state
- How they enforce minimum exposure floor

### Volatility Targeting

Write 3 bullet points about volatility targeting and risk budgeting.

### Momentum Degradation (MACD)

Write 3 bullet points about MACD. Include:
- Current MACD and MACD_Signal values from latest_state
- Whether MACD is above/below signal line

### Overextension Control (RSI)

Write 3 bullet points about RSI. Include:
- Current RSI_14 value from latest_state
- Whether it's below/above overextension thresholds

### Path-Dependent Risk Control (ATR and Trailing Stops)

Write 3 bullet points about ATR-based trailing stops and drawdown control.

## Trade Log

| ENTRY DATE | EXIT DATE | TRADE RETURN (%) | NOTES |
|------------|-----------|------------------|-------|
[Create table rows from all_trades (NOT trade_highlights). Include ALL trades from the all_trades array.

IMPORTANT for TRADE RETURN column formatting:
- For POSITIVE returns: wrap the value in <span class="positive">+XX.XX%</span>
- For NEGATIVE returns: wrap the value in <span class="negative">-XX.XX%</span>
- Always include the + or - sign before the number

For each trade, add a brief note like "Strong momentum capture" for gains >50%, "Extended trend participation" for gains 10-50%, "Short-term momentum degradation" or "Quick exit on momentum loss" for losses]

Write 3 bullet points analyzing the trade patterns across all trades.

## Limitations & Future Extensions

Write 4 bullet points about:
- Conservative exposure vs buy-and-hold in bull markets
- Low hit rate implications
- Future improvements (adaptive parameters, ML classifiers)

## Conclusion

Write one paragraph (4-5 sentences) summarizing:
- The disciplined, risk-aware approach
- Balance between capital preservation and regime participation
- Why it's valuable for institutional investors

EVIDENCE JSON:
{json.dumps(evidence, indent=2, ensure_ascii=False)}
""".strip()


def llm_generate_trade_note(evidence: Dict[str, Any], model: str = "gpt-4o-mini") -> str:
    """
    Generate a short trade note using OpenAI Chat Completions API.

    Args:
        evidence: Structured evidence pack with metrics and latest state.
        model: OpenAI model identifier (default: gpt-4o-mini).

    Returns:
        Markdown-formatted trade note.
    """
    client = OpenAI()
    prompt = _prompt_trade_note(evidence)
    resp = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        temperature=0,
        max_tokens=900,
    )
    return resp.choices[0].message.content


def llm_generate_full_report(evidence: Dict[str, Any], model: str = "gpt-4o-mini") -> str:
    """
    Generate a full technical analysis report using OpenAI Chat Completions API.

    Args:
        evidence: Structured evidence pack with metrics, latest state, and trade highlights.
        model: OpenAI model identifier (default: gpt-4o-mini).

    Returns:
        Markdown-formatted full report matching the PDF template structure.
    """
    client = OpenAI()
    prompt = _prompt_full_report(evidence)
    resp = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        temperature=0,
        max_tokens=4500,
    )
    return resp.choices[0].message.content