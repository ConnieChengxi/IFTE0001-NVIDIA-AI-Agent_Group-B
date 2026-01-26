import pandas as pd
import json
import os
from config import SYMBOL, RAW_DATA_DIR, PROCESSED_DATA_DIR

class FinancialAnalyzer:
    def __init__(self):
        self.symbol = SYMBOL
        self.income_statement = self._load_json(f"{SYMBOL}_income_statement.json")
        self.balance_sheet = self._load_json(f"{SYMBOL}_balance_sheet.json")
        self.cash_flow = self._load_json(f"{SYMBOL}_cash_flow.json")
        self.overview = self._load_json(f"{SYMBOL}_overview.json")

    def _load_json(self, filename):
        path = os.path.join(RAW_DATA_DIR, filename)
        if not os.path.exists(path):
            print(f"Warning: {path} not found.")
            return None
        with open(path, 'r') as f:
            data = json.load(f)
            # Check if it contains real data or just API limits
            if "annualReports" in data or "Symbol" in data:
                return data
            return None

    def _extract_annual_reports(self, data):
        if data and "annualReports" in data:
            return pd.DataFrame(data["annualReports"])
        return pd.DataFrame()

    def analyze(self):
        if not self.income_statement or not self.balance_sheet:
            print("Insufficient data for analysis.")
            return None

        # Prepare DataFrames
        df_is = self._extract_annual_reports(self.income_statement)
        df_bs = self._extract_annual_reports(self.balance_sheet)
        df_cf = self._extract_annual_reports(self.cash_flow)

        if df_is.empty or df_bs.empty:
            return None

        # Convert numeric columns
        for df in [df_is, df_bs, df_cf]:
            cols = df.columns.drop('fiscalDateEnding') if 'fiscalDateEnding' in df.columns else df.columns
            df[cols] = df[cols].apply(pd.to_numeric, errors='coerce')

        # 1. Profitability
        ratios = pd.DataFrame()
        ratios['fiscalDateEnding'] = df_is['fiscalDateEnding']
        ratios['Gross Margin'] = df_is['grossProfit'] / df_is['totalRevenue']
        ratios['Operating Margin'] = df_is['operatingIncome'] / df_is['totalRevenue']
        ratios['Net Margin'] = df_is['netIncome'] / df_is['totalRevenue']
        ratios['ROE'] = df_is['netIncome'] / df_bs['totalShareholderEquity']
        ratios['ROA'] = df_is['netIncome'] / df_bs['totalAssets']
        
        # 2. Leverage & Liquidity
        ratios['Debt to Equity'] = df_bs['totalLiabilities'] / df_bs['totalShareholderEquity']
        ratios['Current Ratio'] = df_bs['totalCurrentAssets'] / df_bs['totalCurrentLiabilities']
        
        if 'ebit' in df_is.columns and 'interestExpense' in df_is.columns:
             # Handle zero interest expense
             ratios['Interest Coverage'] = df_is['ebit'] / df_is['interestExpense'].replace(0, float('nan'))
        
        # 3. Growth (t / t-1 - 1, hence pct_change(-1) as data is descending by date)
        ratios['Revenue Growth'] = df_is['totalRevenue'].pct_change(-1)
        ratios['Net Income Growth'] = df_is['netIncome'].pct_change(-1)
        if 'reportedEPS' in df_is.columns:
            ratios['EPS Growth'] = df_is['reportedEPS'].pct_change(-1)

        # 4. Efficiency
        ratios['Asset Turnover'] = df_is['totalRevenue'] / df_bs['totalAssets']
        # Inventory Turnover = COGS / Inventory
        cogs_col = 'costOfRevenue' if 'costOfRevenue' in df_is.columns else 'costofGoodsAndServicesSold'
        if cogs_col in df_is.columns and 'inventory' in df_bs.columns:
            ratios['Inventory Turnover'] = df_is[cogs_col] / df_bs['inventory'].replace(0, float('nan'))
        
        # Save to CSV
        output_path = os.path.join(PROCESSED_DATA_DIR, f"{SYMBOL}_ratios_annual.csv")
        ratios.to_csv(output_path, index=False)
        print(f"Ratios saved to {output_path}")
        return ratios

def main():
    analyzer = FinancialAnalyzer()
    ratios = analyzer.analyze()
    if ratios is not None:
        print(ratios.head())

if __name__ == "__main__":
    main()
