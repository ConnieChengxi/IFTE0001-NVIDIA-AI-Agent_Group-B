from __future__ import annotations

import textwrap
from pathlib import Path
import os

import pandas as pd
from openai import OpenAI

from config import CFG


def df_to_md(df, title, max_rows=50):
    if df is None:
        return f"### {title}\n(N/A)\n"
    d = df.copy()
    if d.shape[0] > max_rows:
        d = d.head(max_rows)
    return f"### {title}\n{d.to_markdown()}\n"


def col_trend_summary(table, row_name, label, years=None, pct=True):
    s = table.loc[row_name].dropna()
    if years is not None:
        s = s.loc[[y for y in years if y in s.index]]
    if s.empty:
        return f"- {label}: N/A"
    y0, y1 = int(s.index[0]), int(s.index[-1])
    v0, v1 = float(s.iloc[0]), float(s.iloc[-1])
    vmin, ymin = float(s.min()), int(s.idxmin())
    vmax, ymax = float(s.max()), int(s.idxmax())
    fmt = (lambda x: f"{x:.2%}") if pct else (lambda x: f"{x:.2f}")
    return f"- {label}: {fmt(v0)} ({y0}) → {fmt(v1)} ({y1}); min {fmt(vmin)} ({ymin}), max {fmt(vmax)} ({ymax})."


def generate_investment_memo(symbol: str, ratio_out: dict, multiples_ttm: pd.DataFrame, dcf_out: dict) -> Path:
    metrics_table = ratio_out["metrics_table"]
    leverage_table = ratio_out["leverage_table"]
    efficiency_table = ratio_out["efficiency_table"]
    growth_tbl = ratio_out["growth_table"]

    wacc_tbl = dcf_out["wacc_tbl"]
    fcff_forecast_tbl = dcf_out["fcff_forecast_tbl"]
    compare_now = dcf_out["compare_now"]
    valuation = dcf_out["valuation"]

    intrinsic_price = valuation["ImpliedPrice"]
    market_price_now = valuation["MarketPriceNow"]

    years = [2021, 2022, 2023, 2024, 2025]

    profit_facts = "\n".join([
        col_trend_summary(metrics_table, "Gross margin", "Gross margin", years, True),
        col_trend_summary(metrics_table, "Operating margin", "Operating margin", years, True),
        col_trend_summary(metrics_table, "Net margin", "Net margin", years, True),
        col_trend_summary(metrics_table, "ROA", "ROA", years, True),
        col_trend_summary(metrics_table, "ROE", "ROE", years, True),
    ])

    lev_facts = "\n".join([
        col_trend_summary(leverage_table, "Debt-to-Equity", "Debt-to-Equity", years, False),
        col_trend_summary(leverage_table, "Current Ratio", "Current Ratio", years, False),
        col_trend_summary(leverage_table, "Interest Coverage", "Interest Coverage", years, False),
    ])

    eff_facts = "\n".join([
        col_trend_summary(efficiency_table, "Asset Turnover", "Asset Turnover", years, False),
        col_trend_summary(efficiency_table, "FCF Margin", "FCF Margin", years, True),
        col_trend_summary(efficiency_table, "CFO / Net Income", "CFO / Net Income", years, False),
    ])

    ratio_facts_text = f"""
Profitability facts:
{profit_facts}

Leverage/Liquidity facts:
{lev_facts}

Efficiency/Cash quality facts:
{eff_facts}
""".strip()

    prompt = f"""
You are a senior equity research analyst writing an investment memo for {symbol}.

Intrinsic value (USD/share): {intrinsic_price:.2f}
Market price (USD/share): {market_price_now:.2f}

=====================
RATIO TABLE FACTS
=====================
{ratio_facts_text}

=====================
MULTIPLES PEER COMPARISON
=====================
{multiples_ttm.to_markdown()}

=====================
DCF INPUTS AND OUTPUTS
=====================
WACC: {float(wacc_tbl.loc["WACC","value"]):.4f}
FCFF forecast:
{fcff_forecast_tbl[["FCFF"]].to_markdown()}
""".strip()

    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.3,
    )

    memo_text = response.choices[0].message.content

    CFG.out_dir.mkdir(parents=True, exist_ok=True)
    memo_path = CFG.out_dir / "investment_memo.md"
    memo_path.write_text(memo_text, encoding="utf-8")
    return memo_path
