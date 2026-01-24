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
    You are a Senior Technical Analyst at a top-tier Asset Management firm.
    Your task is to write a professional "Investment Memo" for {ticker}.

    --- QUANTITATIVE DATA (From our Algorithm) ---
    1. Strategy: Multi-Factor Momentum (Removed Bollinger Band cap).
    2. Performance (10-Year Backtest):
       - Total Return: {metrics['total_return']:.2%} (Alpha Generation).
       - Sharpe Ratio: {metrics['sharpe']:.2f} (Risk-Adjusted).
       - Max Drawdown: {metrics['drawdown']:.2%} (Risk Exposure).
    3. Current Setup (Latest Day):
       - Price: ${latest_row['Close']:.2f}
       - RSI (14): {latest_row['RSI']:.2f}

    Please write a detailed report (approx. 600-800 words) using the following structure:
    1. Executive Summary
    2. Strategy Mechanics & Logic
    3. Quantitative Performance Analysis
    4. Current Technical Setup
    5. Investment Conclusion & Forward Guidance
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
        with open("NVDA_ai_Report.txt", "w", encoding="utf-8") as f:
            f.write(full_report)
        print("\nThe report has been saved as 'NVDA_ai_Report.txt'")
    except Exception:
        pass

    return full_report
