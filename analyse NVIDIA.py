import pandas as pd
from datetime import datetime
import sys
import numpy as np

COMPANY_NAME = "NVIDIA Corporation (NVDA)"
DATA_SOURCE_FILE = "NVDA_financials_FY21-FY25_official.csv"
CURRENT_STOCK_PRICE = None
FCF_PROJECTION_GROWTH_RATE = None
PERPETUAL_GROWTH_RATE = None
DISCOUNT_RATE = None

# Data Loading
def load_data(filepath):
    try:
        df = pd.read_csv(filepath)
        print(f"Data loaded successfully from '{filepath}'")
        return df
    except FileNotFoundError:
        print(f"!Error: The file '{filepath}' was not found.")
        sys.exit(1)

def get_metric(df, metric_name):
    row = df[df['Financial Metric'] == metric_name]
    if row.empty:
        print(f"!Error: cannot find '{metric_name}' in CSV file")
        sys.exit(1)
    numeric_row = row.drop(columns=['Statement', 'Financial Metric'])
    return numeric_row.iloc[0]

import yfinance as yf

def get_current_stock_price(ticker):
    try:
        stock = yf.Ticker(ticker)
        hist = stock.history(period="5d")
        if hist.empty:
            raise ValueError("No price data returned")
        latest_price = hist['Close'].iloc[-1]
        print(f"Latest market price fetched from Yahoo Finance: ${latest_price:.2f}")
        return float(latest_price)
    except Exception as e:
        print(f"!Warning: Failed to fetch live stock price ({e})")
        print("Using fallback price: 186.50")
        return 186.50


# automatic parameter estimation
def estimate_fcf_growth_rate(df, cap=0.25):
    fcf = get_metric(df, 'Free Cash Flow')
    fy_cols = sorted([c for c in fcf.index if 'FY' in c])
    start, end = fcf[fy_cols[0]], fcf[fy_cols[-1]]
    n = len(fy_cols) - 1
    cagr = (end / start) ** (1 / n) - 1
    return min(cagr, cap)

def implied_discount_rate(df, stock_price, fcf_g, terminal_g):
    last_fcf = get_metric(df, 'Free Cash Flow')['FY2025']
    shares = get_metric(df, 'Diluted Shares Outstanding')['FY2025']

    def dcf_price(r):
        future_fcf = [last_fcf * (1 + fcf_g) ** i for i in range(1, 6)]
        tv = future_fcf[-1] * (1 + terminal_g) / (r - terminal_g)
        pv = sum(f / (1 + r) ** i for i, f in enumerate(future_fcf, 1))
        pv += tv / (1 + r) ** 5
        return pv / shares

    for r in np.linspace(0.06, 0.16, 600):
        if abs(dcf_price(r) - stock_price) / stock_price < 0.02:
            return r
    return 0.10  # fallback

#Profit and debt ratio
def calculate_financial_ratios(df):
    """Calculate core financial ratios, returning raw floating-point numbers."""
    print("Step 1: Calculating financial ratios...")
    ratios = {}
    ratios['Gross Margin'] = get_metric(df, 'Gross Profit') / get_metric(df, 'Total Revenue')
    ratios['Net Margin'] = get_metric(df, 'Net Income') / get_metric(df, 'Total Revenue')
    ratios['Return on Equity (ROE)'] = get_metric(df, 'Net Income') / get_metric(df, 'Total Stockholder Equity')
    ratios['Debt-to-Asset Ratio'] = get_metric(df, 'Total Liabilities') / get_metric(df, 'Total Assets')
    ratios_df = pd.DataFrame(ratios).transpose()
    fy_list = sorted([col for col in df.columns if 'FY' in col])
    revenue = get_metric(df, 'Total Revenue')
    fcf = get_metric(df, 'Free Cash Flow')
    for i in range(len(fy_list) - 1):
        ratios_df.loc['Year-over-Year Revenue Growth', fy_list[i + 1]] = revenue[fy_list[i + 1]] / revenue[fy_list[i]] - 1
        ratios_df.loc['Year-over-Year FCF Growth', fy_list[i + 1]] = fcf[fy_list[i + 1]] / fcf[fy_list[i]] - 1

    return ratios_df

#P/E and P/S
def perform_comparable_valuation(df, stock_price):
    """Perform comparable valuation analysis."""
    print("Step 2: Performing comparable valuation analysis and getting peer company...")
    latest_year = 'FY2025'
    eps = get_metric(df, 'Diluted EPS')[latest_year]
    shares = get_metric(df, 'Diluted Shares Outstanding')[latest_year]
    revenue = get_metric(df, 'Total Revenue')[latest_year]
    return {
        'Price-to-Earnings (P/E)': f"{stock_price / eps:.2f}x",
        'Price-to-Sales (P/S)': f"{(stock_price * shares) / revenue:.2f}x"
    }

#comparable company
def get_peer_valuation(tickers):
    """Fetch valuation multiples for peer companies from Yahoo Finance"""
    peer_data = {}
    for ticker in tickers:
        try:
            stock = yf.Ticker(ticker)
            info = stock.info

            peer_data[ticker] = {
                "Company Name": info.get("shortName", "N/A"),
                "Price": info.get("currentPrice", np.nan),
                "Market Cap ($B)": info.get("marketCap", np.nan) / 1e9,
                "P/E": info.get("trailingPE", np.nan),
                "P/S": info.get("priceToSalesTrailing12Months", np.nan)
            }
        except Exception as e:
            print(f"! Warning: Failed to fetch data for {ticker}: {e}")
    df = pd.DataFrame(peer_data).T
    return df


#DCF
def perform_dcf_valuation(df, stock_price, fcf_g, terminal_g, discount_rate):
    print("Step 3: Performing DCF valuation analysis...")
    latest_year = 'FY2025'

    last_fcf = get_metric(df, 'Free Cash Flow')[latest_year]
    future_fcf = [last_fcf * (1 + fcf_g) ** i for i in range(1, 6)]
    terminal_value = future_fcf[-1] * (1 + terminal_g) / (discount_rate - terminal_g)
    discount_factors = [(1 + discount_rate) ** i for i in range(1, 6)]
    pv_fcf = sum(f / d for f, d in zip(future_fcf, discount_factors))
    pv_terminal = terminal_value / discount_factors[-1]
    enterprise_value = pv_fcf + pv_terminal
    cash = get_metric(df, 'Cash and Equivalents')[latest_year]
    securities = get_metric(df, 'Marketable Securities')[latest_year]
    debt = get_metric(df, 'Total Liabilities')[latest_year]
    net_debt = debt - cash - securities
    equity_value = enterprise_value - net_debt
    shares = get_metric(df, 'Diluted Shares Outstanding')[latest_year]
    implied_price = equity_value / shares
    return {
        'DCF Estimated Intrinsic Value per Share': f"${implied_price:.2f}",
        'Current Stock Price': f"${stock_price:.2f}",
        'Upside/Downside Potential': implied_price / stock_price - 1
    }




#memo
def generate_investment_memo(company, ratios, comp_val, dcf_val, fcf_g, terminal_g, discount_rate, current_stock_price, peer_df):
    """Generate the final, plain-text format investment analysis memo."""
    print("Step 4: Generating investment analysis memo...")
    #format financial ratios
    fy_cols_sorted = sorted([col for col in ratios.columns if 'FY' in col], reverse=True)
    def format_pct(x):
        return "N/A" if pd.isna(x) else f"{x:.2%}"
    formatted = ratios[fy_cols_sorted].map(format_pct)
    ratios_str = formatted.to_string()
    upside_percentage = dcf_val['Upside/Downside Potential']
    if upside_percentage > 0.10:
        dcf_analysis_text = f"Under relatively conservative growth assumptions, our DCF model suggests an intrinsic value of approximately {dcf_val['DCF Estimated Intrinsic Value per Share']}, indicating a significant upside potential of {upside_percentage:.2%} over the current stock price. This suggests the stock may be undervalued."
    elif upside_percentage > -0.10:
        dcf_analysis_text = f"Under relatively conservative growth assumptions, our DCF model suggests an intrinsic value of approximately {dcf_val['DCF Estimated Intrinsic Value per Share']}, roughly in line with the current stock price (potential of {upside_percentage:.2%}). This suggests the current valuation is within a reasonable range."
    else:
        dcf_analysis_text = f"Under relatively conservative growth assumptions, our DCF model suggests an intrinsic value of approximately {dcf_val['DCF Estimated Intrinsic Value per Share']}, indicating a downside potential of {upside_percentage:.2%} relative to the current stock price. This suggests the stock may be overvalued, as its price already fully or even excessively reflects future growth expectations."
    if peer_df is not None and not peer_df.empty:
        peer_table = peer_df.round(2).to_string()
    else:
        peer_table = "Peer valuation data is unavailable."

    #memo text
    memo = f"""
Investment Analysis Memo: {company}

Date: {datetime.now().strftime('%Y-%m-%d')}
Data Source: `{DATA_SOURCE_FILE}` (5 years of official financial data from Yahoo Finance and Nvidia Annual Reports)

1. Main investment analysis result
Based on an in-depth analysis of NVIDIA's financial performance over the past five fiscal years, the company has demonstrated exceptional growth capabilities, unparalleled profitability efficiency, and a robust financial structure. NVIDIA’s leadership in AI computing and accelerated computing continues to translate into strong and scalable free cash flow generation.Despite its elevated market valuation, the DCF model—grounded in market-implied discount rates and conservative long-term growth assumptions—suggests that NVIDIA’s intrinsic value remains well supported, reinforcing its position as a long-term core asset within the global technology sector.

2. Financial Ratio Analysis (FY2021-FY2025)
{ratios_str}
Analysis Highlights:
- Profitability: NVIDIA’s profitability surged in FY2024 and FY2025, with net margins and ROE reaching historically exceptional levels, underscoring strong pricing power and operational leverage.
- Growth Quality: Revenue expansion has been accompanied by even stronger Free Cash Flow growth, indicating that earnings growth is cash-backed and of high quality.
- Financial Health: A consistently low Debt-to-Asset ratio reflects a conservative capital structure and strong balance sheet resilience.

3. Valuation Analysis

3.1 Comparable Valuation Method
Based on FY2025 fiscal year data and the current market price (${current_stock_price:.2f}):
- Price-to-Earnings (P/E): {comp_val['Price-to-Earnings (P/E)']}
- Price-to-Sales (P/S): {comp_val['Price-to-Sales (P/S)']}
The elevated valuation multiples indicate that the market assigns significant value to NVIDIA’s future growth prospects, particularly in AI-related end markets.

3.2 Peer Company Comparison
The following table presents a valuation comparison between NVIDIA and selected peer companies operating in the semiconductor and AI computing space:
{peer_table}
Compared with its major peers, NVIDIA trades at a premium across valuation multiples, reflecting its dominant position in AI acceleration, superior growth visibility, and exceptional profitability. While peers such as AMD and Broadcom also benefit from AI-related demand, NVIDIA’s valuation premium suggests that the market views it as the primary long-term winner in the AI infrastructure ecosystem.

3.3  Discounted Cash Flow (DCF) Valuation Method
DCF Core Assumptions:
- FCF Growth Rate (Next 5 Years): {fcf_g:.2%}
- Perpetual Growth Rate: {terminal_g:.2%}
- Discount Rate (Implied by Market): {discount_rate:.2%}

DCF Result:
- Intrinsic Value per Share: {dcf_val['DCF Estimated Intrinsic Value per Share']}
- Current Stock Price: {dcf_val['Current Stock Price']}
- Upside / Downside Potential: {upside_percentage:.2%}

{dcf_analysis_text}

4. Conclusion and Recommendation
NVIDIA exhibits exceptionally strong fundamentals driven by its dominant position in AI infrastructure, superior profitability, and robust free cash flow generation.
Strengths:
- Structural growth exposure to AI and high-performance computing
- Exceptional margins and capital efficiency
- Strong balance sheet and cash generation capability
Risks:
- Macroeconomic volatility
- Intensifying industry competition
- Elevated market valuation embedding high growth expectations

Investment Recommendation:
We recommend NVIDIA as a long-term core holding for investors seeking exposure to structural growth in artificial intelligence and advanced computing. While short-term valuation-driven volatility may persist, the company's long-term value creation remains compelling.
"""
    return memo


#Main program
if __name__ == "__main__":
    print(f"--- Fundamental analysis for {COMPANY_NAME} ---")

    financial_df = load_data(DATA_SOURCE_FILE)
    TICKER = "NVDA"
    CURRENT_STOCK_PRICE = get_current_stock_price(TICKER)



    #Automatically estimate parameters for DCF
    FCF_PROJECTION_GROWTH_RATE = estimate_fcf_growth_rate(financial_df)
    PERPETUAL_GROWTH_RATE = min(0.03, FCF_PROJECTION_GROWTH_RATE * 0.3)
    DISCOUNT_RATE = implied_discount_rate(
        financial_df,
        CURRENT_STOCK_PRICE,
        FCF_PROJECTION_GROWTH_RATE,
        PERPETUAL_GROWTH_RATE
    )

    print("\nAuto-estimated assumptions:")
    print(f"FCF Growth Rate: {FCF_PROJECTION_GROWTH_RATE:.2%}")
    print(f"Perpetual Growth Rate: {PERPETUAL_GROWTH_RATE:.2%}")
    print(f"Discount Rate: {DISCOUNT_RATE:.2%}")

    ratios_result = calculate_financial_ratios(financial_df)
    comp_val_result = perform_comparable_valuation(financial_df, CURRENT_STOCK_PRICE)
    dcf_val_result = perform_dcf_valuation(
        financial_df,
        CURRENT_STOCK_PRICE,
        FCF_PROJECTION_GROWTH_RATE,
        PERPETUAL_GROWTH_RATE,
        DISCOUNT_RATE
    )

    # Peer company analysis
    PEER_TICKERS = ["NVDA", "AMD", "INTC", "AVGO"]
    peer_valuation_df = get_peer_valuation(PEER_TICKERS)
    
    memo = generate_investment_memo(
        COMPANY_NAME,
        ratios_result,
        comp_val_result,
        dcf_val_result,
        FCF_PROJECTION_GROWTH_RATE,
        PERPETUAL_GROWTH_RATE,
        DISCOUNT_RATE,
        CURRENT_STOCK_PRICE,
         peer_valuation_df
    )

    print("\n" + "=" * 60)
    print(memo)

    with open("investment_memo_NVDA_final.txt", "w", encoding="utf-8") as f:
        f.write(memo)

    print("\nMemo saved as 'investment_memo_NVDA_final.txt'")

