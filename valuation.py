import pandas as pd
import json
import os
from config import SYMBOL, PEERS, RAW_DATA_DIR, PROCESSED_DATA_DIR

class Valuator:
    def __init__(self):
        self.symbol = SYMBOL
        self.ratios_path = os.path.join(PROCESSED_DATA_DIR, f"{SYMBOL}_ratios_annual.csv")
        self.overview = self._load_json(f"{SYMBOL}_overview.json")
        self.cash_flow = self._load_json(f"{SYMBOL}_cash_flow.json")
        self.price_yfinance = self._load_price_yfinance()

    def _load_json(self, filename):
        path = os.path.join(RAW_DATA_DIR, filename)
        if not os.path.exists(path): return None
        with open(path, 'r') as f:
            data = json.load(f)
            return data if ("annualReports" in data or "Symbol" in data) else None

    def _load_price_yfinance(self):
        path = os.path.join(RAW_DATA_DIR, f"{SYMBOL}_price_yfinance.json")
        if not os.path.exists(path): return None
        with open(path, 'r') as f:
            return json.load(f)

    def _safe_float(self, value, default=0.0):
        """Safely convert Alpha Vantage string values to float."""
        if value is None or str(value).lower() == 'none' or str(value).strip() == '-':
            return default
        try:
            return float(value)
        except (ValueError, TypeError):
            return default

    def dcf_valuation(self):
        """Standard DCF with assumptions derived strictly from Alpha Vantage data."""
        if not self.cash_flow or "annualReports" not in self.cash_flow or not self.overview:
            return None
        
        # 1. Derive Risk Free Rate (Rf) from 10yr Treasury Yield
        rf_path = os.path.join(RAW_DATA_DIR, "ECON_treasury_yield.json")
        if not os.path.exists(rf_path):
            print("Missing ECON_treasury_yield.json. Please run data_fetcher.py with a valid key.")
            return None
        with open(rf_path, 'r') as f:
            rf_data = json.load(f)
            risk_free_rate = self._safe_float(rf_data["data"][0]["value"]) / 100

        # 2. Derive Market Risk Premium (MRP) from SPY returns vs Rf
        spy_path = os.path.join(RAW_DATA_DIR, "SPY_time_series_monthly_adjusted.json")
        if not os.path.exists(spy_path):
            print("Missing SPY_time_series_monthly_adjusted.json. Calculation aborted.")
            return None
        with open(spy_path, 'r') as f:
            spy_raw = json.load(f)
            spy_df = pd.DataFrame.from_dict(spy_raw["Monthly Adjusted Time Series"], orient='index')
            spy_df['5. adjusted close'] = pd.to_numeric(spy_df['5. adjusted close'])
            # Calc annual return (5yr)
            spy_return = (spy_df['5. adjusted close'].iloc[0] / spy_df['5. adjusted close'].iloc[60]) ** (1/5) - 1
            market_risk_premium = max(0.04, spy_return - risk_free_rate) # Floor at 4%

        beta = self._safe_float(self.overview.get("Beta", 1.0))
        discount_rate = risk_free_rate + (beta * market_risk_premium)
        
        # 3. Derive Terminal Growth from Real GDP data
        gdp_path = os.path.join(RAW_DATA_DIR, "ECON_real_gdp.json")
        if not os.path.exists(gdp_path):
            print("Missing ECON_real_gdp.json. Calculation aborted.")
            return None
        with open(gdp_path, 'r') as f:
            gdp_data = json.load(f)
            # Use 5-year average annual GDP growth as terminal proxy
            gdp_vals = [self._safe_float(x["value"]) for x in gdp_data["data"][:6]]
            gdp_growth_series = pd.Series(gdp_vals[::-1]).pct_change().dropna()
            terminal_growth = max(0.01, gdp_growth_series.mean()) 
            
        # 4. Cash Flow Projections
        df_cf = pd.DataFrame(self.cash_flow["annualReports"])
        df_cf["operatingCashflow"] = pd.to_numeric(df_cf["operatingCashflow"], errors='coerce')
        df_cf["capitalExpenditures"] = pd.to_numeric(df_cf["capitalExpenditures"], errors='coerce')
        df_cf["fcf"] = df_cf["operatingCashflow"] - df_cf["capitalExpenditures"]
        
        fcf_series = df_cf["fcf"].iloc[::-1].reset_index(drop=True) 
        
        # 4. Cash Flow Projections - Using CAGR instead of Simple Average
        def calculate_cagr(series):
            if len(series) < 2: return 0.05 # Default if data missing
            start_val = series.iloc[0]
            end_val = series.iloc[-1]
            n_periods = len(series) - 1
            
            # Handle negative starting values or zero
            if start_val <= 0:
                # Fallback to simple mean of positive changes if start is negative
                return min(series.pct_change().dropna().iloc[-3:].mean(), 0.50)
            
            cagr = (end_val / start_val) ** (1 / n_periods) - 1
            return cagr

        projected_growth = calculate_cagr(fcf_series)
        
        # Upper bound limit (e.g. 60%) to keep it mathematically sane even for high-growth firms
        projected_growth = min(projected_growth, 0.60) 
        
        latest_fcf = df_cf["fcf"].iloc[0]
        
        def calculate_intrinsic(g, d):
            projected = [latest_fcf * ((1 + g) ** i) for i in range(1, 6)]
            pv_cf = sum([fcf / ((1 + d) ** i) for i, fcf in enumerate(projected, 1)])
            tv = (projected[-1] * (1 + terminal_growth)) / (d - terminal_growth)
            pv_tv = tv / ((1 + d) ** 5)
            return pv_cf + pv_tv

        intrinsic_value = calculate_intrinsic(projected_growth, discount_rate)
        shares = self._safe_float(self.overview.get("SharesOutstanding", 0))
        
        # 4a. Get Projected and Historical FCF for reporting
        fcf_history = fcf_series.tolist()
        fcf_projected = [latest_fcf * ((1 + projected_growth) ** i) for i in range(1, 6)]

        # 5. Sensitivity Analysis
        sensitivity = {}
        for g_adj in [-0.02, 0, 0.02]:
            g_curr = projected_growth + g_adj
            sensitivity[f"Growth_{g_curr:.1%}"] = {}
            for d_adj in [-0.01, 0, 0.01]:
                d_curr = discount_rate + d_adj
                val = calculate_intrinsic(g_curr, d_curr)
                sensitivity[f"Growth_{g_curr:.1%}"].update({
                    f"Discount_{d_curr:.1%}": val / shares if shares > 0 else 0
                })

        return {
            "Intrinsic Price": intrinsic_value / shares if shares > 0 else 0,
            "Assumptions": {
                "Beta (AV)": beta,
                "Risk Free Rate (AV 10Y)": risk_free_rate,
                "Market Return (AV SPY 5Y)": spy_return,
                "Derived MRP": market_risk_premium,
                "Derived Discount Rate": discount_rate,
                "Terminal Growth (AV GDP)": terminal_growth,
                "Projected Business Growth": projected_growth
            },
            "FCF_Data": {
                "Historical": fcf_history,
                "Projected": fcf_projected
            },
            "Sensitivity Analysis": sensitivity
        }

    def multiple_valuation(self):
        """Perform Relative Valuation by calculating implied price from peer averages."""
        if not self.overview: return None
        
        # 1. Base data for NVDA
        nvda_pe = self._safe_float(self.overview.get("PERatio", 0))
        nvda_eps = self._safe_float(self.overview.get("EPS", 0))
        
        results = {
            "Tickers": {
                self.symbol: {
                    "MarketCap": self._safe_float(self.overview.get("MarketCapitalization", 0)),
                    "PE": nvda_pe,
                    "ForwardPE": self._safe_float(self.overview.get("ForwardPE", 0)),
                    "PB": self._safe_float(self.overview.get("PriceToBookRatio", 0)),
                    "ROE": self._safe_float(self.overview.get("ReturnOnEquityTTM", 0)),
                    "EV_EBITDA": self._safe_float(self.overview.get("EVToEBITDA", 0))
                }
            }
        }
        
        peer_pes = []
        for peer in PEERS:
            peer_data = self._load_json(f"{peer}_overview.json")
            if peer_data:
                pe = self._safe_float(peer_data.get("PERatio", 0))
                # Filter out extreme outliers (e.g., > 500 or <= 0) for a cleaner average
                if 0 < pe < 500:
                    peer_pes.append(pe)
                
                results["Tickers"][peer] = {
                    "MarketCap": self._safe_float(peer_data.get("MarketCapitalization", 0)),
                    "PE": pe,
                    "ForwardPE": self._safe_float(peer_data.get("ForwardPE", 0)),
                    "PB": self._safe_float(peer_data.get("PriceToBookRatio", 0)),
                    "ROE": self._safe_float(peer_data.get("ReturnOnEquityTTM", 0)),
                    "EV_EBITDA": self._safe_float(peer_data.get("EVToEBITDA", 0))
                }
        
        # 2. Calculate Implied Price
        if peer_pes:
            avg_peer_pe = sum(peer_pes) / len(peer_pes)
            implied_price = avg_peer_pe * nvda_eps
            
            results["Peer_Average_PE"] = avg_peer_pe
            results["Implied_Price"] = implied_price
            results["Valuation_Status"] = "Success"
        else:
            results["Valuation_Status"] = "No valid peer PE data found"
            results["Implied_Price"] = 0
        
        return results

    def ddm_valuation(self, discount_rate, terminal_growth):
        """Dividend Discount Model (Gordon Growth Model)."""
        if not self.overview: return None
        
        # 1. Get current dividend
        dps = self._safe_float(self.overview.get("DividendPerShare", 0))
        if dps == 0:
            return {
                "Intrinsic Price": 0,
                "Status": "Company does not pay significant dividends."
            }
        
        # 2. Estimate Growth Rate (use terminal growth or projected FCF growth capped)
        # For simplicity in this summary model, we'll use a conservative version
        g = min(discount_rate - 0.02, terminal_growth) 
        
        # 3. GGM Formula: P = D0 * (1+g) / (r - g)
        intrinsic_price = (dps * (1 + g)) / (discount_rate - g) if discount_rate > g else 0
        
        return {
            "Intrinsic Price": intrinsic_price,
            "Dividend Per Share": dps,
            "Applied Growth": g,
            "Status": "Success" if intrinsic_price > 0 else "Calculation Error (r <= g)"
        }

    def run(self):
        dcf = self.dcf_valuation()
        multiples = self.multiple_valuation()
        
        # Extract common assumptions from DCF for DDM
        discount_rate = dcf["Assumptions"]["Derived Discount Rate"] if dcf else 0.10
        terminal_growth = dcf["Assumptions"]["Terminal Growth (AV GDP)"] if dcf else 0.02
        
        ddm = self.ddm_valuation(discount_rate, terminal_growth)
        
        current_market_price = self.price_yfinance.get("currentPrice") if self.price_yfinance else 0
        
        # Weighted Intrinsic Value Calculation
        dcf_val = dcf["Intrinsic Price"] if dcf else 0
        ddm_val = ddm["Intrinsic Price"] if ddm else 0
        multiples_val = multiples["Implied_Price"] if multiples else 0
        
        weights = {"DCF": 0.4, "DDM": 0.0, "Multiples": 0.6}
        weighted_value = (dcf_val * weights["DCF"]) + \
                         (ddm_val * weights["DDM"]) + \
                         (multiples_val * weights["Multiples"])
        
        upside = (weighted_value / current_market_price - 1) if current_market_price > 0 else 0
        recommendation = "Undervalued" if upside > 0.1 else "Overvalued" if upside < -0.1 else "Fair Value"

        output = {
            "DCF": dcf,
            "DDM": ddm,
            "Multiples": multiples,
            "CurrentMarketPrice": current_market_price,
            "WeightedValuation": {
                "IntrinsicValue": weighted_value,
                "Weights": weights,
                "Upside": upside,
                "Recommendation": recommendation
            }
        }
        
        path = os.path.join(PROCESSED_DATA_DIR, f"{SYMBOL}_valuation.json")
        with open(path, 'w') as f:
            json.dump(output, f, indent=4)
        print(f"Valuation saved to {path}")
        return output

if __name__ == "__main__":
    v = Valuator()
    print(v.run())
