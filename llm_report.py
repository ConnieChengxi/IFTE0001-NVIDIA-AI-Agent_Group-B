import os
from openai import OpenAI


def generate_report(metrics: dict, latest_row, api_key: str = None, ticker: str = "NVDA") -> str:
    """Generate AI research report using OpenAI; returns the text or None if no key."""
    # Try to load .env if python-dotenv is available (optional dependency)
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except Exception:
        pass

    api_key = api_key or os.getenv("OPENAI_API_KEY")
    if not api_key or not api_key.startswith("sk-"):
        print("Missing OpenAI API key. Set OPENAI_API_KEY environment variable to enable report generation.")
        return None

    client = OpenAI(api_key=api_key)

    prompt = f"""
    *** ROLE & OBJECTIVE ***
    You are a Senior Quantitative Equity Analyst at a top-tier Asset Management firm. 
    Your task is to write a sophisticated, data-driven **"Investment Memorandum"** for {ticker} based on the backtesting results of our proprietary "AI Momentum Strategy".

    *** DATA INPUTS (Real-Time Backtest Results) ***
    - **Strategy**: Multi-Factor Momentum (MACD + RSI + OBV).
    - **Total Return (10 Years)**: {metrics['total_return']:.2%} (Note: Compare this implicitly to market beta).
    - **Sharpe Ratio**: {metrics['sharpe']:.2f} (Evaluate risk-adjusted performance).
    - **Max Drawdown**: {metrics['drawdown']:.2%} (Address the downside risk).
    - **Current Price**: ${latest_row['Close']:.2f}
    - **Current RSI (14)**: {latest_row['RSI']:.2f} (Thresholds: >70 Overbought, <30 Oversold).

    *** REPORT STRUCTURE (Strictly Follow This) ***
    
    1. **Executive Summary & Recommendation**
       - Provide a clear rating: **STRONG BUY**, **BUY**, **HOLD**, or **SELL**.
       - Summarize the key reason based on the Total Return and Momentum strength.

    2. **Performance Diagnosis**
       - Analyze the **Total Return**: Is this alpha generation or just riding the sector trend?
       - Critically assess the **Max Drawdown**: Explain that while volatility is high, the strategy successfully captured the long-term upside.
       - Comment on the **Sharpe Ratio**: Does the return justify the risk taken?

    3. **Technical Outlook (Short-Term)**
    - Interpret the current **RSI** ({latest_row['RSI']:.2f}). Is the stock currently overheated (needing a pullback) or is there room to run?
       - Provide a specific "Watch Level" for the price.

    4. **Forward Guidance**
       - Conclude with a final strategic advice for the investment committee.

    *** TONE & STYLE ***
    - Professional, concise, institutional, and objective.
    - Avoid generic AI phrases like "In conclusion" or "It is important to note".
    - Focus on financial logic and actionable insights.
    """

    print("A deep report is currently being written (GPT is thinking...).")

    try:
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "You are a senior financial analyst."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=1500
        )
        full_report = response.choices[0].message.content
    except Exception as e:
        full_report = f"Call failed: {e}"

    try:
        # ensure outputs directory exists
        os.makedirs("outputs", exist_ok=True)
        out_path = os.path.join("outputs", f"{ticker}_ai_Report.txt")
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(full_report)
        print(f"\nThe report has been saved as '{out_path}'")
    except Exception as e:
        print(f"Failed to save report: {e}")

    return full_report


if __name__ == "__main__":
    # Simple runnable flow: fetch data, compute indicators, backtest, then generate report
    try:
        from data_collection import fetch_data
        from indicators import add_indicators
        from backtesting import run_backtest
    except Exception as e:
        print(f"Failed to import project modules: {e}")
        raise

    ticker = os.getenv("TICKER", "NVDA")
    print(f"Preparing report for {ticker}...")

    # Fetch and prepare data
    df = fetch_data(ticker=ticker, period="10y", save_csv=False)
    df = add_indicators(df)

    metrics, bt_data = run_backtest(df)

    latest_row = bt_data.iloc[-1].to_dict()

    # Use OPENAI_API_KEY from environment by default
    report = generate_report(metrics, latest_row, api_key=None, ticker=ticker)

    if report:
        print("\nReport generated successfully. Preview:\n")
        print(report[:1000])
    else:
        print("No report generated. Ensure OPENAI_API_KEY is set and valid.")
