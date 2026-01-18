import yfinance as yf
import pandas as pd
import time
from datetime import datetime


def get_full_financial_data(ticker_symbol):

    print(f"--- Starting financial data retrieval for '{ticker_symbol}' ---")

    company = yf.Ticker(ticker_symbol)

    REQUEST_DELAY = 2.0

    all_data = {}

    try:
        # get data
        print("Retrieving company basic information...")
        all_data["Basic Info"] = pd.DataFrame.from_dict(company.info, orient='index', columns=['Value'])
        time.sleep(REQUEST_DELAY)

        print("Retrieving historical stock price (5 years)...")
        all_data["Historical Price"] = company.history(period="5y")
        time.sleep(REQUEST_DELAY)

        all_data["Annual Income Statement"] = company.financials
        time.sleep(REQUEST_DELAY)

        all_data["Quarterly Income Statement"] = company.quarterly_financials
        time.sleep(REQUEST_DELAY)

        all_data["Annual Balance Sheet"] = company.balance_sheet
        time.sleep(REQUEST_DELAY)

        all_data["Quarterly Balance Sheet"] = company.quarterly_balance_sheet
        time.sleep(REQUEST_DELAY)

        all_data["Annual Cash Flow Statement"] = company.cashflow
        time.sleep(REQUEST_DELAY)

        print("Retrieving quarterly cash flow statement...")
        all_data["Quarterly Cash Flow Statement"] = company.quarterly_cashflow

        print(f"--- All data for '{ticker_symbol}' successfully retrieved! ---")
        return all_data
    except Exception as e:
        print(f"!!! Critical error occurred while retrieving data: {e}")
        print("Please check if the stock ticker is correct or your internet connection. If repeated failures occur, your IP might be temporarily rate-limited.")
        return None


def save_data_to_excel(data_dict, ticker_symbol):
    """
    Save the retrieved data dictionary to a multi-sheet Excel file.
    """
    if not data_dict:
        print("Data dictionary is empty, cannot save to Excel file.")
        return


    filename = f"{ticker_symbol}_financial_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"

    print(f"\n--- Write data into a newly created Excel: '{filename}' ---")

    def remove_timezone(df: pd.DataFrame) -> pd.DataFrame:
        """
        Remove the timezone information if needed.
        """
        if isinstance(df.index, pd.DatetimeIndex) and df.index.tz is not None:
            df = df.copy()
            df.index = df.index.tz_localize(None)
        return df

    try:
        with pd.ExcelWriter(filename, engine='openpyxl') as writer:
            for sheet_name, data_frame in data_dict.items():
                if data_frame is None or data_frame.empty:
                    continue

                print(f"  -> creating '{sheet_name}'")

                #write timezone
                data_frame = remove_timezone(data_frame)

                data_frame.to_excel(writer, sheet_name=sheet_name)

        print("\n--- Excel created, including ---")
        for name in data_dict.keys():
            print(f"- {name}")

    except Exception as e:
        print(f"error: {e}")


# --- main analyzation ---
if __name__ == "__main__":

    TICKER_TO_ANALYZE = "NVDA"


    financial_data = get_full_financial_data(TICKER_TO_ANALYZE)

    if financial_data:
        save_data_to_excel(financial_data, TICKER_TO_ANALYZE)
    else:
        print("\n error")
