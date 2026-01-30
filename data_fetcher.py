import requests
import time
import json
import os
import pandas as pd
import yfinance as yf
from config import ALPHA_VANTAGE_KEY, SYMBOL, PEERS, RAW_DATA_DIR, PORTABLE_CACHE_FILE

class AlphaVantageFetcher:
    def __init__(self, api_key):
        self.api_key = api_key
        self.base_url = "https://www.alphavantage.co/query"
        self.call_count = 0
        self.start_time = time.time()
        self.portable_cache = self._load_portable_cache()

    def _load_portable_cache(self):
        """Load the monolithic cache file if it exists."""
        if os.path.exists(PORTABLE_CACHE_FILE):
            try:
                with open(PORTABLE_CACHE_FILE, 'r') as f:
                    return json.load(f)
            except Exception:
                return {}
        return {}

    def _save_to_portable_cache(self, key, data):
        """Save a specific key to the monolithic cache file."""
        self.portable_cache[key] = data
        try:
            with open(PORTABLE_CACHE_FILE, 'w') as f:
                json.dump(self.portable_cache, f, indent=4)
        except Exception as e:
            print(f"Warning: Could not save to portable cache: {e}")

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
        
        # Check primary cache (local folder)
        cached_data = None
        if os.path.exists(path):
            try:
                with open(path, 'r') as f:
                    cached_data = json.load(f)
                # If found in folder but not in portable bundle, add it now
                if filename not in self.portable_cache:
                    self._save_to_portable_cache(filename, cached_data)
            except (json.JSONDecodeError, KeyError):
                pass
        
        # Check secondary cache (portable monolithic file)
        if not cached_data and filename in self.portable_cache:
            print(f"File {filename} not in local folder, but found in portable cache.")
            cached_data = self.portable_cache[filename]
            # Optionally restore it to the local folder for consistency
            self.save_json(cached_data, filename)

        if cached_data:
            # Check for standard Alpha Vantage error keys or empty data
            data = cached_data
            if data and "Information" not in data and "Note" not in data and "Error Message" not in data:
                # Specific check for data presence
                if "annualReports" in data or "Symbol" in data or "data" in data or "Monthly Adjusted Time Series" in data:
                    print(f"Using cached version of {filename}. Skipping API call.")
                    return data
            print(f"Cached version of {filename} appears invalid. Retrying...")

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
        
        # Save to local folder
        path = os.path.join(RAW_DATA_DIR, filename)
        try:
            with open(path, 'w') as f:
                json.dump(data, f, indent=4)
            print(f"Saved to local folder: {path}")
        except Exception as e:
            print(f"Error saving to {path}: {e}")

        # Save to monolithic portable cache
        self._save_to_portable_cache(filename, data)

    def fetch_yfinance(self, symbol):
        """Fetch price data with portable cache support."""
        filename = f"{symbol}_price_yfinance.json"
        
        # Check portable cache and local file
        path = os.path.join(RAW_DATA_DIR, filename)
        if os.path.exists(path):
            try:
                with open(path, 'r') as f:
                    print(f"Using local cached yfinance data for {symbol}")
                    return json.load(f)
            except: pass
        
        if filename in self.portable_cache:
            print(f"Restoring yfinance data for {symbol} from portable cache.")
            data = self.portable_cache[filename]
            self.save_json(data, filename)
            return data

        print(f"Fetching Price Information for {symbol} via yfinance...")
        try:
            ticker = yf.Ticker(symbol)
            hist = ticker.history(period="5y", interval="1mo")
            if hist.empty:
                print(f"Warning: No historical data found for {symbol}")
                return None
            
            data = {
                "currentPrice": ticker.info.get('currentPrice'),
                "history_monthly": hist.to_json()
            }
            self.save_json(data, filename)
            return data
        except Exception as e:
            print(f"Failed to fetch yfinance data for {symbol}: {e}")
            return None

def restore_from_bundle():
    """Utility function to restore all files from the portable bundle to the local folder."""
    if not os.path.exists(PORTABLE_CACHE_FILE):
        return
    
    print(f"Checking for files to restore from {PORTABLE_CACHE_FILE}...")
    try:
        with open(PORTABLE_CACHE_FILE, 'r') as f:
            bundle = json.load(f)
        
        count = 0
        for filename, data in bundle.items():
            path = os.path.join(RAW_DATA_DIR, filename)
            if not os.path.exists(path):
                with open(path, 'w') as f_out:
                    json.dump(data, f_out, indent=4)
                count += 1
        if count > 0:
            print(f"Restored {count} files from portable bundle.")
    except Exception as e:
        print(f"Error during restoration: {e}")

def main():
    # Attempt to restore before doing anything else
    restore_from_bundle()
    
    fetcher = AlphaVantageFetcher(ALPHA_VANTAGE_KEY)
    
    # 1. Fetch NVDA Price Data via yfinance (with cache check)
    fetcher.fetch_yfinance(SYMBOL)

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
