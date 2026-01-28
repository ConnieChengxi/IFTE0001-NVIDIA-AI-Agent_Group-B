from __future__ import annotations

import pandas as pd
import numpy as np


def compute_ratio_tables(merged_df: pd.DataFrame) -> dict[str, pd.DataFrame]:
    """
    Notebook-style ratios:
    - Use 2020 as lag year for avg_assets/avg_equity
    - Output tables only for 2021-2025
    """
    df = merged_df.copy().sort_values("fiscal_year").reset_index(drop=True)

    # Averages for ROA / ROE
    df["avg_assets"] = (df["total_assets"] + df["total_assets"].shift(1)) / 2
    df["avg_equity"] = (df["total_shareholder_equity"] + df["total_shareholder_equity"].shift(1)) / 2

    # Profitability
    df["gross_margin"] = (df["revenue"] - df["cogs"]) / df["revenue"]
    df["operating_margin"] = df["operating_income"] / df["revenue"]
    df["net_margin"] = df["net_income"] / df["revenue"]
    df["roa"] = df["net_income"] / df["avg_assets"]
    df["roe"] = df["net_income"] / df["avg_equity"]

    # Leverage / liquidity
    df["debt_total"] = df[["long_term_debt", "short_term_debt"]].sum(axis=1, min_count=1)
    df["debt_to_equity"] = df["debt_total"] / df["total_shareholder_equity"]
    df["current_ratio"] = df["current_assets"] / df["current_liabilities"]
    df["interest_coverage"] = df["operating_income"] / df["interest_expense"]

    # Growth (YoY)
    df["revenue_yoy"] = df["revenue"].pct_change()
    df["net_income_yoy"] = df["net_income"].pct_change()
    df["fcf_yoy"] = df["free_cash_flow"].pct_change()

    # Efficiency
    df["asset_turnover"] = df["revenue"] / df["avg_assets"]
    df["fcf_margin"] = df["free_cash_flow"] / df["revenue"]
    df["cfo_to_net_income"] = df["operating_cash_flow"] / df["net_income"]

    # Keep only 2021-2025 for outputs
    df_out = df[df["fiscal_year"].between(2021, 2025)].reset_index(drop=True)

    # Tables
    metrics_table = (
        df_out.set_index("fiscal_year")[["gross_margin", "operating_margin", "net_margin", "roa", "roe"]]
        .T.rename(index={
            "gross_margin": "Gross margin",
            "operating_margin": "Operating margin",
            "net_margin": "Net margin",
            "roa": "ROA",
            "roe": "ROE",
        }).round(4)
    )

    leverage_table = (
        df_out.set_index("fiscal_year")[["debt_to_equity", "current_ratio", "interest_coverage"]]
        .T.rename(index={
            "debt_to_equity": "Debt-to-Equity",
            "current_ratio": "Current Ratio",
            "interest_coverage": "Interest Coverage",
        }).round(4)
    )

    growth_table = (
        df_out.set_index("fiscal_year")[["revenue_yoy", "net_income_yoy", "fcf_yoy"]]
        .T.rename(index={
            "revenue_yoy": "Revenue YoY Growth",
            "net_income_yoy": "Net Income YoY Growth",
            "fcf_yoy": "FCF YoY Growth",
        }).round(4)
    )

    efficiency_table = (
        df_out.set_index("fiscal_year")[["asset_turnover", "fcf_margin", "cfo_to_net_income"]]
        .T.rename(index={
            "asset_turnover": "Asset Turnover",
            "fcf_margin": "FCF Margin",
            "cfo_to_net_income": "CFO / Net Income",
        }).round(4)
    )

    return {
        "df_calc": df_out,   
        "metrics_table": metrics_table,
        "leverage_table": leverage_table,
        "growth_table": growth_table,
        "efficiency_table": efficiency_table,
    }
