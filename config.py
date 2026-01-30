# Configuration for Fundamental Analyst Agent
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

ALPHA_VANTAGE_KEY = os.getenv("ALPHAVANTAGE_API_KEY")
if not ALPHA_VANTAGE_KEY:
    raise ValueError("ALPHAVANTAGE_API_KEY not found in environment variables. Please check your .env file.")

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    print("Warning: OPENAI_API_KEY not found. LLM report generation will be disabled.")

SYMBOL = "NVDA"
PEERS = ["AMD", "INTC", "AVGO", "QCOM", "MU"]  # Selected peers for comparison

# Directory paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
RAW_DATA_DIR = os.path.join(BASE_DIR, "data", "raw")
PROCESSED_DATA_DIR = os.path.join(BASE_DIR, "data", "processed")
PLOTS_DIR = os.path.join(PROCESSED_DATA_DIR, "plots")

# Portable cache file (monolithic file in root)
PORTABLE_CACHE_FILE = os.path.join(BASE_DIR, "data_bundle.json")

# Create directories if they don't exist
os.makedirs(RAW_DATA_DIR, exist_ok=True)
os.makedirs(PROCESSED_DATA_DIR, exist_ok=True)
os.makedirs(PLOTS_DIR, exist_ok=True)
