import json
from pathlib import Path

import pandas as pd
import numpy as np


def year_from_fiscal_date(date_str: str) -> int:
    # "2025-01-28" -> 2025
    return int(str(date_str)[:4])


def to_int(x):
    try:
        if x is None:
            return np.nan
        x = str(x).replace(",", "").strip()
        if x == "" or x.lower() == "none":
            return np.nan
        return int(float(x))
    except Exception:
        return np.nan


def to_float(x):
    try:
        if x is None:
            return np.nan
        x = str(x).replace(",", "").strip()
        if x == "" or x.lower() == "none":
            return np.nan
        return float(x)
    except Exception:
        return np.nan


def load_reports(path: Path) -> list[dict]:
    data = json.loads(path.read_text(encoding="utf-8"))
    reps = data.get("annualReports", [])
    if not reps:
        raise RuntimeError(f"No annualReports found in {path}")
    return reps


def to_billions_inplace(df: pd.DataFrame, cols: list[str]) -> pd.DataFrame:
    for c in cols:
        if c in df.columns:
            df[c] = df[c] / 1e9
    return df


def standardize_income(path: Path, years: set[int]) -> pd.DataFrame:
    reps = load_reports(path)
    rows = []
    for r in reps:
        fy = year_from_fiscal_date(r.get("fiscalDateEnding"))
        if fy not in years:
            continue
        rows.append({
            "fiscal_year": fy,
            "fiscal_date_ending": r.get("fiscalDateEnding"),
            "revenue": to_int(r.get("totalRevenue")),
            "cogs": to_int(r.get("costOfRevenue")),
            "gross_profit": to_int(r.get("grossProfit")),
            "operating_income": to_int(r.get("operatingIncome")),
            "income_before_tax": to_int(r.get("incomeBeforeTax")),
            "income_tax_expense": to_int(r.get("incomeTaxExpense")),
            "net_income": to_int(r.get("netIncome")),
            "ebitda": to_int(r.get("ebitda")),
            "interest_expense": to_int(r.get("interestExpense")),
        })
    df = pd.DataFrame(rows).sort_values("fiscal_year").reset_index(drop=True)
    money_cols = [c for c in df.columns if c not in ("fiscal_year", "fiscal_date_ending")]
    to_billions_inplace(df, money_cols)
    return df


def standardize_balance(path: Path, years: set[int]) -> pd.DataFrame:
    reps = load_reports(path)
    rows = []
    for r in reps:
        fy = year_from_fiscal_date(r.get("fiscalDateEnding"))
        if fy not in years:
            continue
        rows.append({
            "fiscal_year": fy,
            "fiscal_date_ending": r.get("fiscalDateEnding"),
            "total_assets": to_int(r.get("totalAssets")),
            "total_liabilities": to_int(r.get("totalLiabilities")),
            "total_shareholder_equity": to_int(r.get("totalShareholderEquity")),
            "cash_and_cash_equivalents": to_int(r.get("cashAndCashEquivalentsAtCarryingValue")),
            "short_term_debt": to_int(r.get("shortTermDebt")),
            "long_term_debt": to_int(r.get("longTermDebt")),
        })
    df = pd.DataFrame(rows).sort_values("fiscal_year").reset_index(drop=True)
    money_cols = [c for c in df.columns if c not in ("fiscal_year", "fiscal_date_ending")]
    to_billions_inplace(df, money_cols)
    # total debt (bn)
    df["total_debt"] = df[["short_term_debt", "long_term_debt"]].sum(axis=1, min_count=1)
    return df


def standardize_cashflow(path: Path, years: set[int]) -> pd.DataFrame:
    reps = load_reports(path)
    rows = []
    for r in reps:
        fy = year_from_fiscal_date(r.get("fiscalDateEnding"))
        if fy not in years:
            continue
        rows.append({
            "fiscal_year": fy,
            "fiscal_date_ending": r.get("fiscalDateEnding"),
            "operating_cashflow": to_int(r.get("operatingCashflow")),
            "capital_expenditures": to_int(r.get("capitalExpenditures")),
            "depreciation_and_amortization": to_int(r.get("depreciationDepletionAndAmortization")),
            "change_in_working_capital": to_int(r.get("changeInOperatingLiabilities")),  # fallback proxy
        })
    df = pd.DataFrame(rows).sort_values("fiscal_year").reset_index(drop=True)
    money_cols = [c for c in df.columns if c not in ("fiscal_year", "fiscal_date_ending")]
    to_billions_inplace(df, money_cols)
    return df


def build_standardized_statements(paths: dict[str, Path], years: set[int]):
    is_df = standardize_income(paths["income_statement"], years)
    bs_df = standardize_balance(paths["balance_sheet"], years)
    cf_df = standardize_cashflow(paths["cash_flow"], years)
    return is_df, bs_df, cf_df

