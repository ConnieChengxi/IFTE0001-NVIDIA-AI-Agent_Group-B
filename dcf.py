import numpy as np
import pandas as pd

from config import Config
from src.data_fetcher import av_get


def compute_wacc(overview: dict, cfg: Config, tax_rate: float) -> dict:
    """
    WACC = wE*Re + wD*Rd*(1-T)
    Re = rf + beta*ERP
    """
    # beta (try overview, else fallback to 2.0-ish)
    beta = overview.get("Beta")
    try:
        beta = float(beta)
    except Exception:
        beta = 2.0

    rf = cfg.rf_fallback
    erp = cfg.erp_fallback

    cost_of_equity = rf + beta * erp

    # Debt cost: try InterestRate in overview, else conservative low default
    rd = overview.get("InterestRate")
    try:
        cost_of_debt = float(rd)
    except Exception:
        cost_of_debt = 0.028225  # matches your notebook-style small Rd

    # Capital structure: market cap vs total debt (overview)
    mcap = overview.get("MarketCapitalization")
    debt = overview.get("TotalDebt")
    try:
        E = float(mcap)
    except Exception:
        E = np.nan
    try:
        D = float(debt)
    except Exception:
        D = 0.0

    if not np.isfinite(E) or E <= 0:
        # fallback: almost all equity weight
        wE, wD = 0.99, 0.01
    else:
        V = E + max(D, 0.0)
        wE = E / V
        wD = max(D, 0.0) / V

    wacc = wE * cost_of_equity + wD * cost_of_debt * (1 - tax_rate)

    return {
        "rf": rf,
        "beta": beta,
        "erp": erp,
        "cost_of_equity": cost_of_equity,
        "cost_of_debt": cost_of_debt,
        "wE": wE,
        "wD": wD,
        "wacc": wacc,
        "tax_rate": tax_rate,
    }


def _calc_tax_rate_from_is(is_df: pd.DataFrame, cfg: Config) -> float:
    # robust recent-median tax rate like your notebook
    s = (is_df["income_tax_expense"] / is_df["income_before_tax"])
    s = s.replace([np.inf, -np.inf], np.nan).dropna()
    if len(s) == 0:
        return 0.12
    tax = float(np.nanmedian(s.tail(3)))
    return float(np.clip(tax, cfg.tax_clip_low, cfg.tax_clip_high))


def revenue_cagr(is_df: pd.DataFrame, start_year: int, end_year: int) -> float:
    s = is_df.set_index("fiscal_year")["revenue"]
    if start_year not in s.index or end_year not in s.index:
        raise RuntimeError("Missing revenue years for CAGR")
    rev0 = float(s.loc[start_year])
    rev1 = float(s.loc[end_year])
    n = end_year - start_year
    return (rev1 / rev0) ** (1 / n) - 1


def forecast_revenue(rev0: float, cagr: float, years: list[int]) -> pd.Series:
    vals = []
    cur = rev0
    for _ in years:
        cur = cur * (1 + cagr)
        vals.append(cur)
    return pd.Series(vals, index=years, name="revenue_forecast")


def run_dcf_valuation(is_df: pd.DataFrame, bs_df: pd.DataFrame, cf_df: pd.DataFrame, overview: dict, cfg: Config) -> dict:
    base_year = max(is_df["fiscal_year"])
    base_rev = float(is_df.loc[is_df["fiscal_year"] == base_year, "revenue"].iloc[0])
    base_ebit = float(is_df.loc[is_df["fiscal_year"] == base_year, "operating_income"].iloc[0])
    ebit_margin = base_ebit / base_rev if base_rev else 0.0

    # tax rate from statements
    tax_rate = _calc_tax_rate_from_is(is_df, cfg)

    # WACC
    wacc_block = compute_wacc(overview, cfg, tax_rate)
    wacc = wacc_block["wacc"]

    # Growth driver (align with your notebook: CAGR 2021->2025)
    cagr = revenue_cagr(is_df, start_year=2021, end_year=base_year)

    # Forecast horizon
    forecast_years = [base_year + i for i in range(1, cfg.forecast_years + 1)]
    rev_f = forecast_revenue(base_rev, cagr, forecast_years)

    # FCFF drivers from history (use recent medians/means like notebook style)
    da_ratio = float(np.nanmedian((cf_df["depreciation_and_amortization"] / is_df["revenue"]).replace([np.inf, -np.inf], np.nan)))
    capex_ratio = float(np.nanmedian((-cf_df["capital_expenditures"] / is_df["revenue"]).replace([np.inf, -np.inf], np.nan)))
    # working capital proxy (optional; keep simple & stable)
    nwc_ratio = 0.0

    da_ratio = 0.02 if not np.isfinite(da_ratio) else da_ratio
    capex_ratio = 0.01 if not np.isfinite(capex_ratio) else capex_ratio

    # Build forecast table
    tbl = pd.DataFrame(index=forecast_years)
    tbl["Revenue (USD bn)"] = rev_f
    tbl["EBIT (USD bn)"] = tbl["Revenue (USD bn)"] * ebit_margin
    tbl["NOPAT (USD bn)"] = tbl["EBIT (USD bn)"] * (1 - tax_rate)
    tbl["D&A (USD bn)"] = tbl["Revenue (USD bn)"] * da_ratio
    tbl["Capex (USD bn)"] = tbl["Revenue (USD bn)"] * capex_ratio
    tbl["ΔNWC (USD bn)"] = tbl["Revenue (USD bn)"] * nwc_ratio
    tbl["FCFF (USD bn)"] = tbl["NOPAT (USD bn)"] + tbl["D&A (USD bn)"] - tbl["Capex (USD bn)"] - tbl["ΔNWC (USD bn)"]

    # Discount
    t = np.arange(1, cfg.forecast_years + 1)
    disc = 1 / ((1 + wacc) ** t)
    tbl["Discount Factor"] = disc
    tbl["PV(FCFF) (USD bn)"] = tbl["FCFF (USD bn)"] * tbl["Discount Factor"]

    # Terminal value
    fcff_last = float(tbl["FCFF (USD bn)"].iloc[-1])
    tv = fcff_last * (1 + cfg.terminal_g) / (wacc - cfg.terminal_g)
    pv_tv = tv * float(tbl["Discount Factor"].iloc[-1])

    ev = float(tbl["PV(FCFF) (USD bn)"].sum() + pv_tv)

    # Equity value & per share
    mcap = overview.get("MarketCapitalization")
    shares = overview.get("SharesOutstanding")
    cash = overview.get("CashAndCashEquivalents")
    debt = overview.get("TotalDebt")

    try:
        shares = float(shares)
    except Exception:
        shares = np.nan

    try:
        cash_bn = float(cash) / 1e9
    except Exception:
        cash_bn = 0.0
    try:
        debt_bn = float(debt) / 1e9
    except Exception:
        debt_bn = 0.0

    equity_value_bn = ev - debt_bn + cash_bn
    intrinsic_per_share = equity_value_bn * 1e9 / shares if (np.isfinite(shares) and shares > 0) else np.nan

    return {
        "base_year": base_year,
        "cagr_2021_to_base": float(cagr),
        "wacc_block": wacc_block,
        "drivers": {"ebit_margin": ebit_margin, "da_ratio": da_ratio, "capex_ratio": capex_ratio, "nwc_ratio": nwc_ratio},
        "forecast_table": tbl,
        "terminal_value_bn": float(tv),
        "pv_terminal_value_bn": float(pv_tv),
        "enterprise_value_bn": float(ev),
        "equity_value_bn": float(equity_value_bn),
        "intrinsic_value_per_share": float(intrinsic_per_share) if np.isfinite(intrinsic_per_share) else np.nan,
    }

