from __future__ import annotations

import pandas as pd

from config import CFG, ensure_dirs, load_api_key
from data_fetcher import fetch_annual_statements
from statements import build_statement_tables
from ratios import compute_ratio_tables
from multiples import (
    build_multiples_input_table,
    compute_multiples_from_input,
    add_benchmarks,
)
from dcf import run_dcf_notebook_style
from visualization import plot_ratio_panels, plot_multiples_figures
from llm_report import generate_investment_memo


def _write_table(df: pd.DataFrame, name: str):
    ensure_dirs(CFG)
    df.to_csv(CFG.out_dir / f"{name}.csv", index=True)


def run_pipeline() -> dict:
    ensure_dirs(CFG)
    api_key = load_api_key()

    print("Step 1: Fetching annual statements...")
    paths = fetch_annual_statements(CFG.symbol, api_key)

    print("Step 2: Building standardized statement tables (already USD bn)...")
    is_df, bs_df, cf_df, merged_df = build_statement_tables(paths)

    # ================= NOTEBOOK STYLE VIEW (NO MORE UNIT CONVERSION) =================
    income_items = [
        "revenue", "cogs", "gross_profit", "operating_income",
        "net_income", "interest_expense", "income_before_tax",
        "income_tax_expense"
    ]

    balance_items = [
        "total_assets", "total_liabilities", "total_shareholder_equity",
        "cash_and_cash_equivalents", "current_assets",
        "current_liabilities", "long_term_debt",
        "short_term_debt", "short_term_investments"
    ]

    cashflow_items = [
        "operating_cash_flow", "capex_outflow",
        "depreciation_and_amortization", "free_cash_flow"
    ]

    is_view = is_df.set_index("fiscal_year")[income_items].T
    bs_view = bs_df.set_index("fiscal_year")[balance_items].T
    cf_view = cf_df.set_index("fiscal_year")[cashflow_items].T

    print("\n========== NVDA Income Statement (USD bn) ==========")
    print(is_view.round(3).to_string())

    print("\n========== NVDA Balance Sheet (USD bn) ==========")
    print(bs_view.round(3).to_string())

    print("\n========== NVDA Cash Flow Statement (USD bn) ==========")
    print(cf_view.round(3).to_string())
    # ================================================================================

    print("\nStep 3: Computing ratios...")
    ratio_out = compute_ratio_tables(merged_df)

    print("\n========== NVDA Profitability Ratios (2021-2025) ==========")
    print(ratio_out["metrics_table"].to_string())

    print("\n========== NVDA Leverage & Liquidity (2021-2025) ==========")
    print(ratio_out["leverage_table"].to_string())

    print("\n========== NVDA Growth (YoY, 2021-2025) ==========")
    print(ratio_out["growth_table"].to_string())

    print("\n========== NVDA Efficiency (2021-2025) ==========")
    print(ratio_out["efficiency_table"].to_string())

    print("\nStep 4: Fetching multiples (TTM)...")
    multiples_input = build_multiples_input_table(api_key=api_key)
    multiples = compute_multiples_from_input(multiples_input)
    multiples = add_benchmarks(multiples)

    print("\nMultiples (TTM):")
    print(multiples.round(2).to_string())

    # ====================== DCF (YOUR NOTEBOOK LOGIC, PRINT TABLES) ======================
    print("\nStep 5: Running DCF model (notebook style)...")
    dcf_out = run_dcf_notebook_style(
        symbol=CFG.symbol,
        api_key=api_key,
        is_view=is_view,
        bs_view=bs_view,
        cf_view=cf_view,
        table=multiples_input,                 # ✅ 关键：你的 notebook 用的 table (MarketCap)
        base_year=CFG.base_year,
        start_year=CFG.start_year_for_cagr,
        horizon=CFG.horizon,
        terminal_growth=CFG.terminal_growth,
    )

    print("\n========== Overview (Alpha Vantage OVERVIEW) ==========")
    print(dcf_out["overview_tbl"].round(4).to_string(index=False))

    print("\n========== DCF Assumptions (Base Year) ==========")
    print(dcf_out["assumption_view"].round(6).to_string())

    print("\n========== FCFF Forecast Table ==========")
    print(dcf_out["fcff_forecast_tbl"].round(4).to_string())

    print("\n========== WACC Table ==========")
    print(dcf_out["wacc_tbl"].round(6).to_string())

    print("\n========== Market vs Intrinsic (NOW) ==========")
    print(dcf_out["compare_now"].to_string(index=False))

    print("\nDCF Valuation Summary:")
    for k, v in dcf_out["valuation"].items():
        print(f"{k}: {v}")
    # ================================================================================

    print("\nStep 6: Saving tables...")
    _write_table(is_view, "income_view")
    _write_table(bs_view, "balance_view")
    _write_table(cf_view, "cashflow_view")

    _write_table(ratio_out["metrics_table"], "ratios_profitability")
    _write_table(ratio_out["leverage_table"], "ratios_leverage_liquidity")
    _write_table(ratio_out["growth_table"], "ratios_growth")
    _write_table(ratio_out["efficiency_table"], "ratios_efficiency")

    _write_table(multiples_input, "multiples_inputs")
    _write_table(multiples, "multiples_ttm")

    # ✅ Save DCF tables (your notebook artifacts)
    _write_table(dcf_out["overview_tbl"], "dcf_overview_tbl")
    _write_table(dcf_out["assumption_view"], "dcf_assumption_view")
    _write_table(dcf_out["fcff_forecast_tbl"], "dcf_fcff_forecast_tbl")
    _write_table(dcf_out["wacc_tbl"], "dcf_wacc_tbl")
    _write_table(dcf_out["compare_now"], "dcf_compare_now")

    print("\nStep 7: Generating figures...")
    plot_ratio_panels(ratio_out["df_calc"])
    plot_multiples_figures(multiples)

    print("\nStep 8: Generating investment memo (LLM)...")
    memo_path = generate_investment_memo(CFG.symbol, ratio_out, multiples, dcf_out)

    print("\nPipeline complete.")
    print(f"Memo saved to: {memo_path}")

    return {
        "is_view": is_view,
        "bs_view": bs_view,
        "cf_view": cf_view,
        "ratios": ratio_out,
        "multiples": multiples,
        "dcf": dcf_out,
        "memo_path": str(memo_path),
    }
