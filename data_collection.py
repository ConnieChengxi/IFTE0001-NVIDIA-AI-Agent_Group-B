import yfinance as yf
import pandas as pd


def fetch_data(ticker: str = "NVDA", period: str = "10y", save_csv: bool = True) -> pd.DataFrame:
    """Download data with yfinance, basic cleaning, save CSV and return DataFrame."""
    df = yf.download(ticker, period=period, auto_adjust=False)
    # Flatten MultiIndex columns if yfinance returns grouped columns
    if isinstance(df.columns, pd.MultiIndex):
        # keep the first level (Close, High, Low, Open, Volume, etc.)
        df.columns = df.columns.get_level_values(0)
        print("flattened MultiIndex columns from yfinance download (kept level 0)")

    df = df.dropna()

    print("\n--- data preview (first 5 rows) ---")
    print(df.head())

    print(f"\n--- data statistics ---")
    print(f"total transaction days: {len(df)}")
    print(f"start date: {df.index[0].date()}")
    print(f"end date: {df.index[-1].date()}")

    if save_csv:
        file_name = f"{ticker}_10y_data.csv"
        df.to_csv(file_name)
        print(f"\ndata has been saved as: {file_name}")

    return df
