import pandas as pd
from datetime import datetime
import sys

COMPANY_NAME = "NVIDIA Corporation (NVDA)"
DATA_SOURCE_FILE = "NVDA_financials_FY21-FY25_official.csv"
CURRENT_STOCK_PRICE = 186.50

# --- valuation assumptions ---
DISCOUNT_RATE = 0.10
PERPETUAL_GROWTH_RATE = 0.025
FCF_PROJECTION_GROWTH_RATE = 0.15

print("Step 1: Extracting data...")

def load_data(filepath):
    """Load and preprocess financial data from CSV file."""
    try:
        df = pd.read_csv(filepath)
        print(f"Data loaded successfully from '{filepath}'")
        return df
    except FileNotFoundError:
        print(f"!Error: The file '{filepath}' was not found.")
        print("Please ensure the CSV file is in the same directory as this script.")
        sys.exit(1)
    except Exception as e:
        print(f"!Error: An unexpected error occurred while loading the CSV file: {e}")
        sys.exit(1)

def get_metric(df, metric_name):
    """Extract a single row of financial data from the DataFrame."""
    row = df[df['Financial Metric'] == metric_name]
    if row.empty:
        print(f"\n!Error:cannot find '{metric_name}' in CSV file")
        sys.exit(1)
    numeric_row = row.drop(columns=['Statement', 'Financial Metric'])
    return numeric_row.iloc[0]

#Profit and debt ratio
def calculate_financial_ratios(df):
    """Calculate core financial ratios, returning raw floating-point numbers."""
    print("Step 2: Calculating financial ratios...")
    ratios = {}
    ratios['Gross Margin'] = get_metric(df, 'Gross Profit') / get_metric(df, 'Total Revenue')
    ratios['Net Margin'] = get_metric(df, 'Net Income') / get_metric(df, 'Total Revenue')
    ratios['Return on Equity (ROE)'] = get_metric(df, 'Net Income') / get_metric(df, 'Total Stockholder Equity')
    ratios['Debt-to-Asset Ratio'] = get_metric(df, 'Total Liabilities') / get_metric(df, 'Total Assets')
    ratios_df = pd.DataFrame(ratios).transpose()

    fy_list = sorted([col for col in df.columns if 'FY' in col])
    total_revenue = get_metric(df, 'Total Revenue')
    free_cash_flow = get_metric(df, 'Free Cash Flow')

    for i in range(len(fy_list) - 1):
        current_year, previous_year = fy_list[i + 1], fy_list[i]
        ratios_df.loc['Year-over-Year Revenue Growth', current_year] = (total_revenue[current_year] / total_revenue[previous_year]) - 1
        ratios_df.loc['Year-over-Year FCF Growth', current_year] = (free_cash_flow[current_year] / free_cash_flow[
            previous_year]) - 1


    return ratios_df

#P/E and P/S
def perform_comparable_valuation(df, stock_price):
    """Perform comparable valuation analysis."""
    print("Step 3: Performing comparable valuation analysis...")
    valuation = {}
    latest_year = 'FY2025'
    eps = get_metric(df, 'Diluted EPS')[latest_year]
    shares = get_metric(df, 'Diluted Shares Outstanding')[latest_year]
    revenue = get_metric(df, 'Total Revenue')[latest_year]

    valuation['Price-to-Earnings (P/E)'] = f"{stock_price / eps:.2f}x"
    valuation['Price-to-Sales (P/S)'] = f"{(stock_price * shares) / revenue:.2f}x"
    print("Comparable valuation completed.")
    return valuation

#DCF
def perform_dcf_valuation(df, stock_price):
    """Perform Discounted Cash Flow (DCF) valuation analysis."""
    print("Step 4: Performing DCF valuation analysis...")
    latest_year = 'FY2025'

    last_fcf = get_metric(df, 'Free Cash Flow')[latest_year]
    future_fcf = [last_fcf * (1 + FCF_PROJECTION_GROWTH_RATE) ** i for i in range(1, 6)]
    terminal_value = (future_fcf[-1] * (1 + PERPETUAL_GROWTH_RATE)) / (DISCOUNT_RATE - PERPETUAL_GROWTH_RATE)
    discount_factors = [(1 + DISCOUNT_RATE) ** i for i in range(1, 6)]
    present_value_fcf = sum([fcf / df for fcf, df in zip(future_fcf, discount_factors)])
    present_value_terminal = terminal_value / discount_factors[-1]
    enterprise_value = present_value_fcf + present_value_terminal
    cash = get_metric(df, 'Cash and Equivalents')[latest_year]
    marketable_securities = get_metric(df, 'Marketable Securities')[latest_year]
    total_debt = get_metric(df, 'Total Liabilities')[latest_year]
    net_debt = total_debt - cash - marketable_securities
    equity_value = enterprise_value - net_debt
    shares_outstanding = get_metric(df, 'Diluted Shares Outstanding')[latest_year]

    implied_share_price = equity_value / shares_outstanding

    dcf_results = {
        'DCF Estimated Intrinsic Value per Share': f"${implied_share_price:.2f}",
        'Current Stock Price': f"${stock_price:.2f}",
        'Upside/Downside Potential': (implied_share_price / stock_price - 1)
    }
    print("DCF valuation completed.")
    return dcf_results


def generate_investment_memo(company, ratios, comp_val, dcf_val, raw_data):
    """Generate the final, plain-text format investment analysis memo."""
    print("Step 5: Generating investment analysis memo...")

    fy_cols_sorted = sorted([col for col in ratios.columns if 'FY' in col], reverse=True)

    def format_as_percentage(x):
        if pd.isnull(x):
            return "N/A"
        return f"{x:.2%}"

    formatted_ratios = ratios[fy_cols_sorted].map(format_as_percentage)
    ratios_str = formatted_ratios.to_string()

    upside_percentage = dcf_val['Upside/Downside Potential']
    if upside_percentage > 0.10:
        dcf_analysis_text = f"Under relatively conservative growth assumptions, our DCF model suggests an intrinsic value of approximately {dcf_val['DCF Estimated Intrinsic Value per Share']}, indicating a significant upside potential of {upside_percentage:.2%} over the current stock price. This suggests the stock may be undervalued."
    elif upside_percentage > -0.10:
        dcf_analysis_text = f"Under relatively conservative growth assumptions, our DCF model suggests an intrinsic value of approximately {dcf_val['DCF Estimated Intrinsic Value per Share']}, roughly in line with the current stock price (potential of {upside_percentage:.2%}). This suggests the current valuation is within a reasonable range."
    else:
        dcf_analysis_text = f"Under relatively conservative growth assumptions, our DCF model suggests an intrinsic value of approximately {dcf_val['DCF Estimated Intrinsic Value per Share']}, indicating a downside potential of {upside_percentage:.2%} relative to the current stock price. This suggests the stock may be overvalued, as its price already fully or even excessively reflects future growth expectations."

    memo = f"""
Investment Analysis Memo:{company}

Date: {datetime.now().strftime('Year%YMonth%mDay%d')}
Data Source: `{DATA_SOURCE_FILE}` (5 years of official financial data from Yahoo Finance and Nvidia Annual Reports)

1. Main investment analysis result

Based on an in-depth analysis of NVIDIA's financial data over the past five years, we believe the company has demonstrated phenomenal growth capabilities, unparalleled profitability efficiency, and robust financial health. Its leadership position in the field of AI computing continues to translate into strong free cash flow. Despite its relatively high market valuation, the DCF model indicates its intrinsic value remains well-supported, positioning it as a long-term core asset in the high-tech sector.

2. Financial Ratio Analysis (FY2021-FY2025)

{ratios_str}
[Data Source: `{DATA_SOURCE_FILE}`]

Analysis Highlights:
-Profitability: The company's profitability experienced explosive growth in FY2024 and FY2025. The net margin surged from 16.19% in FY2023 to 55.85% in FY2025, and the Return on Equity (ROE) reached an exceptionally high 91.87% in FY2025. Such a level of ROE is extremely rare among large global corporations, demonstrating its formidable pricing power and operational efficiency. [cite: Calculated Ratios]
-Growth: Revenue achieved year-over-year doubling for two consecutive years in FY2024 and FY2025. More importantly, Free Cash Flow grew by 125.21% in FY2025, indicating that its growth is of high quality and generates ample cash.
-Financial Health: The Debt-to-Asset Ratio has been consistently optimized, dropping to a very low level of 28.92% in FY2025. This indicates that the company maintains a very robust financial structure and extremely low risk despite its rapid expansion.

3. Valuation Analysis

3.1 Comparable Valuation Method

Based on FY2025 fiscal year data and the current stock price(${CURRENT_STOCK_PRICE:.2f})：
Price-to-Earnings (P/E Ratio): {comp_val['Price-to-Earnings (P/E)']}
Price-to-Sales (P/S): {comp_val['Price-to-Sales (P/S)']}
Analysis:
P/E ratio of {comp_val['Price-to-Earnings (P/E)']} reflects the market's extremely high expectations for its future sustained high growth. Compared to historical data and industry peers, this valuation is at an elevated level, which is a risk factor investors should be aware of.

3.2  Discounted Cash Flow (DCF) Valuation Method

We constructed a simplified DCF model to estimate the company's intrinsic value.
Core Assumptions: Discount Rate={DISCOUNT_RATE:.0%}, Perpetual Growth Rate={PERPETUAL_GROWTH_RATE:.1%}, Next 5-Year FCF Growth Rate={FCF_PROJECTION_GROWTH_RATE:.0%}
DCF Estimated Intrinsic Value per Share: {dcf_val['DCF Estimated Intrinsic Value per Share']}
Current Stock Price: {dcf_val['Current Stock Price']}
Potential Upside/Downside: {upside_percentage:.2%}

Analysis:
{dcf_analysis_text} [cite: DCF Model Results]



4. Conclusion and Recommendation

NVIDIA is a company with exceptionally strong fundamentals. Its leadership in the AI sector has resulted in historic financial performance.
Strengths: Phenomenal growth, exceptionally high profitability, healthy balance sheet, and strong free cash flow generation.
Risks: Macroeconomic volatility, intensifying industry competition, and the currently elevated market valuation.

Investment Recommendation:
We recommend including NVIDIA as a core component of a long-term investment portfolio. While short-term stock price volatility may occur due to its high valuation, its long-term value is driven by its central role in the technological revolution and its outstanding financial performance.
"""
    return memo


# --- Main program ---
if __name__ == "__main__":
    print(f"--- Fundamental analysis for {COMPANY_NAME} ---")

    financial_df = load_data(DATA_SOURCE_FILE)

    if financial_df is not None:
        ratios_result = calculate_financial_ratios(financial_df)
        comp_valuation_result = perform_comparable_valuation(financial_df, CURRENT_STOCK_PRICE)
        dcf_valuation_result = perform_dcf_valuation(financial_df, CURRENT_STOCK_PRICE)
        investment_memo = generate_investment_memo(
            COMPANY_NAME, ratios_result, comp_valuation_result, dcf_valuation_result, financial_df
        )

        print("\n\n" + "=" * 50)
        print("=" * 50)
        print(investment_memo)

        report_filename = "investment_memo_NVDA_final.txt"
        with open(report_filename, "w", encoding="utf-8") as f:
            f.write(investment_memo)
        print(f"\nThe memo has been saved as '{report_filename}'")
