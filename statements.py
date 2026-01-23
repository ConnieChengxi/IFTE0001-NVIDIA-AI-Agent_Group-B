import json
from pathlib import Path
import pandas as pd


def load_reports(path: Path) -> list[dict]:
    data = json.loads(path.read_text(encoding="utf-8"))
    reps = data.get("annualReports", [])
    if not reps:
        raise RuntimeError(f"No annualReports found in {path}")
    return reps


def year_from_fiscal_date(s: str) -> int:
    return int(s[:4])


def to_int(x):
    try:
        return int(float(x))
    except Exception:
        return pd.NA


def standardize_income(path: Path, years: set[int]) -> pd.DataFrame:
    reps = load_reports(path)
    rows = []
    for r in reps:
        y = year_from_fiscal_date(r["fiscalDateEnding"])
        if y not in years:
            continue
        rows.append({
            "fiscal_year": y,
            "fiscal_date_ending": r["fiscalDateEnding"],
            "revenue": to_int(r.get("totalRevenue")),
            "cogs": to_int(r.get("costOfRevenue")),
            "gross_profit": to_int(r.get("grossProfit")),
            "operating_income": to_int(r.get("operatingIncome")),
            "net_income": to_int(r.get("netIncome")),
            "interest_expense": to_int(r.get("interestExpense")),
            "income_before_tax": to_int(r.get("incomeBeforeTax")),
            "income_tax_expense": to_int(r.get("incomeTaxExpense")),
        })
    return pd.DataFrame(rows).sort_values("fiscal_year").reset_index(drop=True)


def standardize_balance(path: Path, years: set[int]) -> pd.DataFrame:
    reps = load_reports(path)
    rows = []
    for r in reps:
        y = year_from_fiscal_date(r["fiscalDateEnding"])
        if y not in years:
            continue
        rows.append({
            "fiscal_year": y,
            "fiscal_date_ending": r["fiscalDateEnding"],
            "total_assets": to_int(r.get("totalAssets")),
            "total_liabilities": to_int(r.get("totalLiabilities")),
            "total_shareholder_equity": to_int(r.get("totalShareholderEquity")),
            "cash_and_cash_equivalents": to_int(r.get("cashAndCashEquivalentsAtCarryingValue")),
            "current_assets": to_int(r.get("totalCurrentAssets")),
            "current_liabilities": to_int(r.get("totalCurrentLiabilities")),
            "long_term_debt": to_int(r.get("longTermDebt")),
            "short_term_debt": to_int(r.get("shortTermDebt")),
            "short_term_investments": to_int(r.get("shortTermInvestments")),
        })
    return pd.DataFrame(rows).sort_values("fiscal_year").reset_index(drop=True)


def standardize_cashflow(path: Path, years: set[int]) -> pd.DataFrame:
    reps = load_reports(path)
    rows = []
    for r in reps:
        y = year_from_fiscal_date(r["fiscalDateEnding"])
        if y not in years:
            continue

        cfo = to_int(r.get("operatingCashflow"))
        capex = to_int(r.get("capitalExpenditures"))

        capex_outflow = abs(capex) if pd.notna(capex) else pd.NA
        da = to_int(r.get("depreciationDepletionAndAmortization"))
        fcf = (cfo - capex_outflow) if (pd.notna(cfo) and pd.notna(capex_outflow)) else pd.NA

        rows.append({
            "fiscal_year": y,
            "fiscal_date_ending": r["fiscalDateEnding"],
            "operating_cash_flow": cfo,
            "capex": capex,
            "capex_outflow": capex_outflow,
            "free_cash_flow": fcf,
            "depreciation_and_amortization": da,
        })

    return pd.DataFrame(rows).sort_values("fiscal_year").reset_index(drop=True)


def to_billions_inplace(df: pd.DataFrame, cols: list[str]) -> None:
    for c in cols:
        if c in df.columns:
            df[c] = df[c].astype("float64") / 1e9


INCOME_ITEMS = ["revenue","cogs","gross_profit","operating_income","net_income","interest_expense","income_before_tax","income_tax_expense"]
BALANCE_ITEMS = ["total_assets","total_liabilities","total_shareholder_equity","cash_and_cash_equivalents","current_assets","current_liabilities","long_term_debt","short_term_debt","short_term_investments"]
CASHFLOW_ITEMS = ["operating_cash_flow","capex_outflow","depreciation_and_amortization","free_cash_flow"]


def build_annual_dfs(paths: dict, years: set[int]):
    is_df = standardize_income(paths["income_statement"], years)
    bs_df = standardize_balance(paths["balance_sheet"], years)
    cf_df = standardize_cashflow(paths["cash_flow"], years)
    return is_df, bs_df, cf_df


def to_views_in_bn(is_df, bs_df, cf_df):
    to_billions_inplace(is_df, INCOME_ITEMS)
    to_billions_inplace(bs_df, BALANCE_ITEMS)
    to_billions_inplace(cf_df, CASHFLOW_ITEMS)

    is_view = is_df.set_index("fiscal_year")[INCOME_ITEMS].T
    bs_view = bs_df.set_index("fiscal_year")[BALANCE_ITEMS].T
    cf_view = cf_df.set_index("fiscal_year")[CASHFLOW_ITEMS].T

    return is_view, bs_view, cf_view

