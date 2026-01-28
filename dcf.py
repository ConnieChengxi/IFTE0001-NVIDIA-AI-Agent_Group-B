from __future__ import annotations

import numpy as np
import pandas as pd
import requests
from pathlib import Path
from typing import Dict, Any, Tuple

from config import CFG
from data_fetcher import av_get


# =========================
# Helpers: Overview / Market Price
# =========================
def to_float(x):
    try:
        return float(x)
    except Exception:
        return pd.NA


def overview_table(symbol: str, api_key: str) -> pd.DataFrame:
    ov = av_get("OVERVIEW", api_key=api_key, symbol=symbol)
    tbl = pd.DataFrame([{
        "MarketCap (USD bn)": to_float(ov.get("MarketCapitalization")) / 1e9,
        "Shares Outstanding (bn)": to_float(ov.get("SharesOutstanding")) / 1e9,
        "Beta": to_float(ov.get("Beta")),
        "52W High (USD)": to_float(ov.get("52WeekHigh")),
        "52W Low (USD)": to_float(ov.get("52WeekLow")),
    }])
    return tbl


def shares_outstanding_bn_from_av(symbol: str, api_key: str) -> float:
    ov = av_get("OVERVIEW", api_key=api_key, symbol=symbol)  # cache-first
    sh = ov.get("SharesOutstanding", None)
    try:
        return float(sh) / 1e9  # bn shares
    except Exception:
        return np.nan


def market_price_realtime_av(symbol: str, api_key: str) -> float:
    """
    Get near-real-time price from Alpha Vantage GLOBAL_QUOTE.
    """
    data = av_get("GLOBAL_QUOTE", api_key=api_key, symbol=symbol)
    q = data.get("Global Quote", {}) or {}
    px = q.get("05. price", None)
    try:
        return float(px)
    except Exception:
        return np.nan


# =========================
# Risk-free (FRED 10Y)
# =========================
def risk_free_rate_us() -> float:
    url = "https://fred.stlouisfed.org/graph/fredgraph.csv?id=DGS10"
    df = pd.read_csv(url)
    df["DGS10"] = pd.to_numeric(df["DGS10"], errors="coerce")
    rf = df["DGS10"].dropna().iloc[-1]
    return float(rf) / 100.0


# =========================
# ERP (Damodaran) - multi-source + cache
# =========================
def _download(url: str) -> bytes | None:
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        r = requests.get(url, headers=headers, timeout=60, allow_redirects=True)
        r.raise_for_status()
        return r.content
    except Exception:
        return None


def _erp_from_ctryprem_xlsx(xlsx_path: Path) -> float:
    xls = pd.read_excel(xlsx_path, sheet_name=0)
    cols = {str(c).strip().lower(): c for c in xls.columns}

    col_found = None
    for low, orig in cols.items():
        if ("mature" in low) and ("premium" in low):
            col_found = orig
            break
    if col_found is None:
        raise RuntimeError(f"Cannot find Mature Market premium column. Columns: {list(xls.columns)}")

    ser = pd.to_numeric(xls[col_found], errors="coerce").dropna()
    if ser.empty:
        raise RuntimeError("Mature Market premium column has no numeric values.")

    return float(ser.median()) / 100.0  # percent -> decimal


def _erp_from_histimpl_xls(xls_path: Path) -> float:
    xls = pd.read_excel(xls_path, sheet_name=0)

    col = None
    for c in xls.columns:
        low = str(c).lower()
        if "erp" in low:
            col = c
            break
        if "implied" in low and "premium" in low:
            col = c
            break
    if col is None:
        raise RuntimeError(f"Cannot find ERP column in histimpl. Columns: {list(xls.columns)}")

    ser = pd.to_numeric(xls[col], errors="coerce").dropna()
    if ser.empty:
        raise RuntimeError("ERP column has no numeric values.")

    return float(ser.iloc[-1]) / 100.0


def erp_us_auto() -> tuple[float, str]:
    RAW_DIR = CFG.raw_dir
    RAW_DIR.mkdir(parents=True, exist_ok=True)

    ctry_cache = RAW_DIR / "damodaran_ctryprem.xlsx"
    hist_cache = RAW_DIR / "damodaran_histimpl.xls"

    urls = [
        ("ctryprem", "https://pages.stern.nyu.edu/~adamodar/New_Home_Page/datafile/ctryprem.xlsx", ctry_cache),
        ("histimpl", "https://pages.stern.nyu.edu/~adamodar/New_Home_Page/datafile/histimpl.xls", hist_cache),
    ]

    # try download then parse
    for tag, url, path in urls:
        content = _download(url)
        if content:
            try:
                path.write_bytes(content)
                if tag == "ctryprem":
                    return _erp_from_ctryprem_xlsx(path), "Damodaran ctryprem.xlsx (downloaded)"
                else:
                    return _erp_from_histimpl_xls(path), "Damodaran histimpl.xls (downloaded)"
            except Exception:
                pass

    # try cached
    if ctry_cache.exists() and ctry_cache.stat().st_size > 10_000:
        try:
            return _erp_from_ctryprem_xlsx(ctry_cache), "Damodaran ctryprem.xlsx (cached)"
        except Exception:
            pass
    if hist_cache.exists() and hist_cache.stat().st_size > 5_000:
        try:
            return _erp_from_histimpl_xls(hist_cache), "Damodaran histimpl.xls (cached)"
        except Exception:
            pass

    return 0.05, "Fallback default 5% (all external ERP fetch failed)"


# =========================
# Cost of debt from statements (no manual)
# =========================
def cost_of_debt_from_statements(is_view: pd.DataFrame, bs_view: pd.DataFrame, year: int) -> float:
    interest = float(is_view.loc["interest_expense", year])
    debt = float(bs_view.loc["long_term_debt", year] + bs_view.loc["short_term_debt", year])
    interest = abs(interest)
    if debt <= 0:
        return np.nan
    return interest / debt


# =========================
# WACC (NOTE: Equity uses your multiples input table MarketCap)
# =========================
def compute_wacc(
    symbol: str,
    base_year: int,
    is_view: pd.DataFrame,
    bs_view: pd.DataFrame,
    tax_rate: float,
    table: pd.DataFrame,   # multiples input table
    api_key: str,
) -> Dict[str, Any]:
    rf = risk_free_rate_us()
    ov = av_get("OVERVIEW", api_key=api_key, symbol=symbol)
    beta = float(ov.get("Beta", np.nan))

    erp, erp_source = erp_us_auto()
    re = rf + beta * erp

    rd = cost_of_debt_from_statements(is_view, bs_view, base_year)

    D = float(bs_view.loc["long_term_debt", base_year] + bs_view.loc["short_term_debt", base_year])

    # IMPORTANT: Equity uses your multiples table MarketCap (stable, consistent with ASOF)
    E = float(table.loc["MarketCap (USD bn)", symbol])

    V = D + E
    wE = E / V if V > 0 else np.nan
    wD = D / V if V > 0 else np.nan

    wacc = wE * re + wD * rd * (1 - tax_rate)

    return {
        "Risk-free rate (10Y)": rf,
        "Beta": beta,
        "ERP": erp,
        "ERP source": erp_source,
        "Cost of equity (Re)": re,
        "Cost of debt (Rd)": rd,
        "Tax rate": float(tax_rate),
        "Debt (D, USD bn)": D,
        "Equity (E, USD bn)": E,
        "wE": wE,
        "wD": wD,
        "WACC": wacc,
    }


# =========================
# Main DCF (your notebook logic)
# =========================
def run_dcf_notebook_style(
    symbol: str,
    api_key: str,
    is_view: pd.DataFrame,
    bs_view: pd.DataFrame,
    cf_view: pd.DataFrame,
    table: pd.DataFrame,      # multiples input table
    base_year: int = 2025,
    start_year: int = 2021,
    horizon: int = 5,
    terminal_growth: float = 0.045,
) -> Dict[str, Any]:
    # 1) Overview table
    overview_tbl = overview_table(symbol, api_key)

    # 2) Core assumptions from base year
    rev0 = float(is_view.loc["revenue", base_year])
    ebit0 = float(is_view.loc["operating_income", base_year])
    ebit_margin = ebit0 / rev0

    tax_rate = (is_view.loc["income_tax_expense"] / is_view.loc["income_before_tax"]).loc[2023:2025].median()
    tax_rate = float(np.clip(tax_rate, 0.05, 0.25))

    da_ratio = (cf_view.loc["depreciation_and_amortization"] / is_view.loc["revenue"]).loc[2023:2025].median()
    capex_ratio = (cf_view.loc["capex_outflow"] / is_view.loc["revenue"]).loc[2023:2025].median()

    operating_nwc = (
        bs_view.loc["current_assets"]
        - bs_view.loc["cash_and_cash_equivalents"]
        - bs_view.loc["short_term_investments"]
        - (bs_view.loc["current_liabilities"] - bs_view.loc["short_term_debt"])
    )
    nwc_ratio = (operating_nwc / is_view.loc["revenue"]).loc[2023:2025].median()

    D = float(bs_view.loc["long_term_debt", base_year] + bs_view.loc["short_term_debt", base_year])
    E = float(overview_tbl.loc[0, "MarketCap (USD bn)"])

    assumption_view = pd.DataFrame(
        {
            base_year: [
                rev0,
                ebit_margin,
                tax_rate,
                float(da_ratio),
                float(capex_ratio),
                float(nwc_ratio),
                D,
                E,
            ]
        },
        index=[
            "Base Revenue",
            "EBIT Margin",
            "Tax Rate",
            "D&A / Revenue",
            "CapEx / Revenue",
            "NWC / Revenue",
            "Debt (D)",
            "Equity (E)",
        ],
    )

    # 3) Revenue CAGR
    rev_start = float(is_view.loc["revenue", start_year])
    rev_base = float(is_view.loc["revenue", base_year])
    n = base_year - start_year
    rev_cagr = (rev_base / rev_start) ** (1 / n) - 1
    assumption_view.loc[f"Revenue CAGR (from {start_year} to {base_year})", base_year] = float(rev_cagr)

    years_fwd = list(range(base_year + 1, base_year + 1 + horizon))
    revenue_forecast = pd.Series(
        [rev_base * ((1 + rev_cagr) ** i) for i in range(1, horizon + 1)],
        index=years_fwd,
        name="Revenue_Forecast (USD bn)",
    )

    # 4) FCFF build
    ebit_f = revenue_forecast * ebit_margin
    nopat_f = ebit_f * (1 - tax_rate)

    da_f = revenue_forecast * da_ratio
    capex_f = revenue_forecast * capex_ratio
    nwc_level_f = revenue_forecast * nwc_ratio

    nwc_base = float(
        (
            bs_view.loc["current_assets", base_year]
            - bs_view.loc["cash_and_cash_equivalents", base_year]
            - bs_view.loc["short_term_investments", base_year]
            - (bs_view.loc["current_liabilities", base_year] - bs_view.loc["short_term_debt", base_year])
        )
    )

    delta_nwc_f = nwc_level_f - pd.Series(
        [nwc_base] + list(nwc_level_f.values[:-1]),
        index=revenue_forecast.index,
    )

    fcff_f = nopat_f + da_f - capex_f - delta_nwc_f

    fcff_forecast_tbl = pd.DataFrame(
        {
            "Revenue": revenue_forecast,
            "EBIT": ebit_f,
            "NOPAT": nopat_f,
            "D&A": da_f,
            "CapEx": capex_f,
            "NWC_Level": nwc_level_f,
            "ΔNWC": delta_nwc_f,
            "FCFF": fcff_f,
        }
    ).round(4)

    # 5) WACC table
    wacc_out = compute_wacc(symbol, base_year, is_view, bs_view, tax_rate, table, api_key=api_key)
    wacc_tbl = pd.DataFrame(wacc_out, index=["value"]).T

    # 6) PV + TV + EV
    fcffs = fcff_f.astype(float).to_numpy()
    wacc = float(wacc_out["WACC"])
    g = float(terminal_growth)

    tv = fcffs[-1] * (1 + g) / (wacc - g)
    pv_fcff = sum([fcffs[i] / (1 + wacc) ** (i + 1) for i in range(horizon)])
    pv_tv = tv / (1 + wacc) ** horizon
    EV = pv_fcff + pv_tv

    shares_bn = shares_outstanding_bn_from_av(symbol, api_key)
    debt = float(D)
    cash = float(bs_view.loc["cash_and_cash_equivalents", base_year])
    equity = EV - debt + cash
    intrinsic_price = equity / shares_bn

    # 7) Compare with market price now (GLOBAL_QUOTE)
    market_price_now = market_price_realtime_av(symbol, api_key)
    compare_now = pd.DataFrame(
        {
            "Market price NOW (USD/share)": [market_price_now],
            "Intrinsic value (USD/share)": [float(intrinsic_price)],
        }
    )
    compare_now["Upside / Downside"] = compare_now["Intrinsic value (USD/share)"] / compare_now["Market price NOW (USD/share)"] - 1
    compare_now = compare_now.round(4)

    valuation = {
        "PV_FCFF": float(pv_fcff),
        "PV_TV": float(pv_tv),
        "EV": float(EV),
        "Debt": float(debt),
        "Cash": float(cash),
        "Equity": float(equity),
        "Shares_bn": float(shares_bn),
        "ImpliedPrice": float(intrinsic_price),
        "MarketPriceNow": float(market_price_now) if pd.notna(market_price_now) else np.nan,
        "UpsideDownside": float(compare_now.loc[0, "Upside / Downside"]) if pd.notna(compare_now.loc[0, "Upside / Downside"]) else np.nan,
    }

    return {
        "overview_tbl": overview_tbl,
        "assumption_view": assumption_view,
        "revenue_forecast": revenue_forecast,
        "fcff_forecast_tbl": fcff_forecast_tbl,
        "wacc_tbl": wacc_tbl,
        "compare_now": compare_now,
        "valuation": valuation,
    }
