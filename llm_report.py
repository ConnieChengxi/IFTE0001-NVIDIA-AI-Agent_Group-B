from __future__ import annotations

from pathlib import Path
import os
import textwrap

import pandas as pd

from config import Config


def df_to_md(df: pd.DataFrame, max_rows: int = 12) -> str:
    return df.head(max_rows).to_markdown()


def _build_grounded_prompt(cfg: Config, ratios_df: pd.DataFrame, multiples_df: pd.DataFrame, dcf_out: dict, live_price: float | None) -> str:
    tbl = dcf_out["forecast_table"][["Revenue (USD bn)", "FCFF (USD bn)"]].copy()
    wacc = dcf_out["wacc_block"]["wacc"]
    cagr = dcf_out["cagr_2021_to_base"]
    intrinsic = dcf_out["intrinsic_value_per_share"]

    upside_str = "N/A"
    if live_price is not None and live_price > 0 and intrinsic == intrinsic:
        upside_str = f"{(intrinsic / live_price - 1):.2%}"

    prompt = f"""
You are a finance analyst. Write a concise NVDA fundamental summary grounded ONLY on the computed outputs below.
Do not invent numbers. If something is missing, say "not available".

Key computed outputs:
- Revenue CAGR (2021->{dcf_out['base_year']}): {cagr:.4f}
- WACC: {wacc:.4f}
- Terminal g: {cfg.terminal_g:.4f}
- DCF intrinsic value per share: {intrinsic:.2f}
- Live market price: {live_price if live_price is not None else 'N/A'}
- Upside: {upside_str}

Ratios (merged statements, recent years):
{df_to_md(ratios_df[['fiscal_year','gross_margin','operating_margin','net_margin','roa','roe']])}

Peer multiples (NVDA vs peers):
{df_to_md(multiples_df[['P/E','EV/EBITDA','EV/Sales']])}

FCFF forecast:
{df_to_md(tbl)}
"""
    return textwrap.dedent(prompt).strip()


def generate_llm_report(cfg: Config, ratios_df: pd.DataFrame, multiples_df: pd.DataFrame, dcf_out: dict,
                        live_price: float | None, out_dir: Path) -> Path:
    """
    If OPENAI_API_KEY exists and cfg.use_llm=True, call LLM to generate narrative grounded on computed tables.
    Otherwise, write a deterministic template report.
    """
    report_path = out_dir / "nvda_fundamental_report.md"
    prompt = _build_grounded_prompt(cfg, ratios_df, multiples_df, dcf_out, live_price)

    if cfg.use_llm and os.getenv("OPENAI_API_KEY", "").strip():
        try:
            from openai import OpenAI
            client = OpenAI()
            resp = client.chat.completions.create(
                model=cfg.llm_model,
                messages=[
                    {"role": "system", "content": "You are a careful analyst. Use only provided numbers."},
                    {"role": "user", "content": prompt[: cfg.llm_max_chars]},
                ],
                temperature=0.2,
            )
            text = resp.choices[0].message.content.strip()
            report_path.write_text(text, encoding="utf-8")
            return report_path
        except Exception as e:
            # fall back to template
            pass

    # Template fallback (still grounded)
    intrinsic = dcf_out["intrinsic_value_per_share"]
    wacc = dcf_out["wacc_block"]["wacc"]
    cagr = dcf_out["cagr_2021_to_base"]
    upside = None
    if live_price is not None and live_price > 0 and intrinsic == intrinsic:
        upside = intrinsic / live_price - 1

    text = f"""# NVDA Fundamental Agent Report (Grounded)

## Key valuation outputs
- Revenue CAGR (2021->{dcf_out['base_year']}): {cagr:.4f}
- WACC: {wacc:.4f}
- DCF intrinsic value per share: {intrinsic:.2f}
- Live market price: {live_price if live_price is not None else 'N/A'}
- Upside: {upside:.2%} if upside is not None else N/A

## Ratios (recent years)
{df_to_md(ratios_df[['fiscal_year','gross_margin','operating_margin','net_margin','roa','roe']])}

## Peer multiples (NVDA vs peers)
{df_to_md(multiples_df[['P/E','EV/EBITDA','EV/Sales']])}

## FCFF forecast (DCF)
{df_to_md(dcf_out['forecast_table'][['Revenue (USD bn)','FCFF (USD bn)','PV(FCFF) (USD bn)']])}
"""
    report_path.write_text(text, encoding="utf-8")
    return report_path
