import requests
import time
import json
import os
import pandas as pd
import yfinance as yf
from config import ALPHA_VANTAGE_KEY, SYMBOL, PEERS, RAW_DATA_DIR

class AlphaVantageFetcher:
    def __init__(self, api_key):
        self.api_key = api_key
        self.base_url = "https://www.alphavantage.co/query"
        self.call_count = 0
        self.start_time = time.time()

    def _wait_if_needed(self):
        """Handle both per-second and per-minute limits."""
        # Minimum 2s between any call to avoid "1 request per second" limit
        time.sleep(2)
        
        self.call_count += 1
        if self.call_count > 5:
            elapsed = time.time() - self.start_time
            if elapsed < 60:
                wait_time = 60 - elapsed + 2
                print(f"Rate limit reached. Waiting for {wait_time:.2f} seconds...")
                time.sleep(wait_time)
            self.call_count = 1
            self.start_time = time.time()

    def fetch_data(self, function, symbol=None, extra_params=None):
        """Fetch data from Alpha Vantage with intelligent caching and error checking."""
        # Determine filename
        if symbol:
            filename = f"{symbol}_{function.lower()}.json"
            if function == "OVERVIEW" and symbol in PEERS:
                filename = f"{symbol}_overview.json"
        else:
            filename = f"ECON_{function.lower()}.json"
        
        path = os.path.join(RAW_DATA_DIR, filename)
        
        # Check cache
        if os.path.exists(path):
            try:
                with open(path, 'r') as f:
                    data = json.load(f)
                
                # Check for standard Alpha Vantage error keys or empty data
                if data and "Information" not in data and "Note" not in data and "Error Message" not in data:
                    # Specific check for data presence
                    if "annualReports" in data or "Symbol" in data or "data" in data or "Monthly Adjusted Time Series" in data:
                        print(f"File {filename} already exists and is valid. Skipping API call.")
                        return data
                print(f"File {filename} exists but appears invalid (contains API error or missing data). Retrying...")
            except (json.JSONDecodeError, KeyError):
                print(f"File {filename} is corrupted. Re-fetching...")

        self._wait_if_needed()
        params = {
            "function": function,
            "apikey": self.api_key
        }
        if symbol:
            params["symbol"] = symbol
        if extra_params:
            params.update(extra_params)
            
        try:
            response = requests.get(self.base_url, params=params)
            response.raise_for_status()
            data = response.json()
            
            if "Information" in data:
                print(f"API Daily Limit Reached for {function}: {data['Information']}")
                return None
            if "Note" in data:
                print(f"API Rate Limit Note for {function}: {data['Note']}")
                time.sleep(60)
                return self.fetch_data(function, symbol, extra_params)
            if "Error Message" in data:
                print(f"API Error for {function}: {data['Error Message']}")
                return None
                
            # If successful, save it
            self.save_json(data, filename)
            return data
        except Exception as e:
            print(f"Exception during fetch for {function}: {e}")
            return None

    def save_json(self, data, filename):
        if not data or "Information" in data or "Note" in data:
            print(f"Skipping save for {filename} due to API limit/error message.")
            return
        path = os.path.join(RAW_DATA_DIR, filename)
        with open(path, 'w') as f:
            json.dump(data, f, indent=4)
        print(f"Saved: {path}")

def main():
    fetcher = AlphaVantageFetcher(ALPHA_VANTAGE_KEY)
    
    # 1. Fetch NVDA Price Data via yfinance (as requested)
    print(f"Fetching Price Information for {SYMBOL} via yfinance...")
    try:
        ticker = yf.Ticker(SYMBOL)
        price_data = {
            "currentPrice": ticker.info.get('currentPrice'),
            "history_monthly": ticker.history(period="5y", interval="1mo").to_json()
        }
        with open(os.path.join(RAW_DATA_DIR, f"{SYMBOL}_price_yfinance.json"), 'w') as f:
            json.dump(price_data, f, indent=4)
        print(f"Saved yfinance price data for {SYMBOL}")
    except Exception as e:
        print(f"Failed to fetch yfinance data for {SYMBOL}: {e}")

    # 2. Fetch NVDA Core Financial Data (Keep others in Alpha Vantage as they are disclosure-related)
    functions = ["OVERVIEW", "INCOME_STATEMENT", "BALANCE_SHEET", "CASH_FLOW"]
    
    for func in functions:
        print(f"Fetching {func} for {SYMBOL}...")
        fetcher.fetch_data(func, SYMBOL)

    # 3. Fetch Market Data (SPY) for MRP calculation
    print("Fetching SPY Monthly Adjusted for Market Risk Premium calculation...")
    fetcher.fetch_data("TIME_SERIES_MONTHLY_ADJUSTED", "SPY")

    # 4. Fetch Economic Indicators for Valuation Assumptions
    econ_functions = {
        "TREASURY_YIELD": "10year", # Risk Free Rate proxy
        "REAL_GDP": "annual"        # Terminal Growth proxy
    }
    for func, interval in econ_functions.items():
        print(f"Fetching Economic Indicator: {func}...")
        fetcher.fetch_data(func, extra_params={"interval": interval})

    # 5. Fetch Peer Overview Data for comparison
    for peer in PEERS:
        print(f"Fetching OVERVIEW for peer {peer}...")
        fetcher.fetch_data("OVERVIEW", peer)

    print("Data ingestion complete.")

if __name__ == "__main__":
    main()
