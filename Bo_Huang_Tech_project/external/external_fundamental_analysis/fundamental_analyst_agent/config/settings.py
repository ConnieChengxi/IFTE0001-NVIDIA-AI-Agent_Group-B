import os

# Optional dependency: keep the external module runnable even if python-dotenv isn't installed.
try:
    from dotenv import load_dotenv  # type: ignore
except Exception:  # pragma: no cover
    def load_dotenv(*_args, **_kwargs):  # type: ignore
        return False

# Load environment variables
load_dotenv()

# ============================================================================
# DIRECTORY SETTINGS
# ============================================================================

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CACHE_DIR = os.path.join(PROJECT_ROOT, 'cache')
OUTPUT_DIR = os.path.join(PROJECT_ROOT, 'outputs')
CACHE_TTL_HOURS = 24

# ============================================================================
# API SETTINGS
# ============================================================================

ALPHA_VANTAGE_API_KEY = os.getenv('ALPHA_VANTAGE_API_KEY', '')
ALPHA_VANTAGE_BASE_URL = "https://www.alphavantage.co/query"

# ============================================================================
# DCF SETTINGS
# ============================================================================

RISK_FREE_RATE = 0.042
EQUITY_RISK_PREMIUM = 0.055
TERMINAL_GROWTH_RATE = 0.04
DCF_PROJECTION_YEARS = 5

# ============================================================================
# PEER SELECTION
# ============================================================================

MIN_MARKET_CAP_RATIO = 0.2
MAX_MARKET_CAP_RATIO = 7.0
MAX_VALID_PE_RATIO = 300
MIN_VALID_PE_RATIO = -100

# Industry peers dictionary
INDUSTRY_PEERS = {
    "semiconductors": ["NVDA", "AMD", "INTC", "QCOM", "AVGO", "TXN", "MU", "MRVL"],
    "software - infrastructure": ["MSFT", "ORCL", "CRM", "NOW", "SNOW", "GOOGL"],
    "beverages - non-alcoholic": ["KO", "PEP", "MNST", "KDP"],
    # ... (rest of your industries)
}

RELATED_INDUSTRIES = {
    "semiconductors": ["software - infrastructure", "consumer electronics"],
    # ... (rest of your related industries)
}

# ============================================================================
# BENCHMARKS
# ============================================================================

PROFITABILITY_BENCHMARKS = {
    "gross_margin": {"excellent": 0.50, "good": 0.40, "average": 0.25, "poor": 0.15},
    "operating_margin": {"excellent": 0.20, "good": 0.15, "average": 0.08, "poor": 0.05},
    "net_margin": {"excellent": 0.15, "good": 0.10, "average": 0.05, "poor": 0.02},
    "roe": {"excellent": 0.20, "good": 0.15, "average": 0.10, "poor": 0.05},
    "roa": {"excellent": 0.10, "good": 0.05, "average": 0.03, "poor": 0.01},
    "roic": {"excellent": 0.15, "good": 0.12, "average": 0.08, "poor": 0.05}
}

LEVERAGE_BENCHMARKS = {
    "debt_to_equity": {"excellent": 0.5, "good": 1.0, "average": 2.0, "poor": 3.0},
    "debt_to_assets": {"excellent": 0.3, "good": 0.5, "average": 0.7, "poor": 0.8},
    "interest_coverage": {"excellent": 8.0, "good": 3.0, "average": 1.5, "poor": 1.0}
}

LIQUIDITY_BENCHMARKS = {
    "current_ratio": {"excellent": 2.5, "good": 1.5, "average": 1.2, "poor": 1.0},
    "quick_ratio": {"excellent": 1.5, "good": 1.0, "average": 0.8, "poor": 0.5}
}

GROWTH_BENCHMARKS = {
    "revenue_growth": {"exceptional": 0.30, "high": 0.15, "moderate": 0.05, "low": 0.00},
    "earnings_growth": {"exceptional": 0.30, "high": 0.15, "moderate": 0.05, "low": 0.00}
}

EFFICIENCY_BENCHMARKS = {
    "asset_turnover": {"excellent": 1.5, "good": 1.0, "average": 0.7, "poor": 0.5}
}

# ============================================================================
# RISK THRESHOLDS
# ============================================================================

MIN_INTEREST_COVERAGE = 1.5
MAX_DEBT_TO_EBITDA = 5.0
MIN_CURRENT_RATIO = 0.8

# ============================================================================
# RECOMMENDATION THRESHOLDS
# ============================================================================

BUY_THRESHOLD = 0.20
SELL_THRESHOLD = -0.10

# ============================================================================
# DDM SETTINGS
# ============================================================================

MIN_DIVIDEND_YIELD = 0.01
MIN_DIVIDEND_HISTORY = 3

# ============================================================================
# COMPANY TYPE WEIGHTS
# ============================================================================

COMPANY_TYPE_WEIGHTS = {
    "growth": {"dcf": 0.70, "multiples": 0.30, "ddm": 0.00},
    "balanced": {"dcf": 0.50, "multiples": 0.30, "ddm": 0.20},
    "dividend": {"dcf": 0.30, "multiples": 0.20, "ddm": 0.50},
    "cyclical": {"dcf": 0.30, "multiples": 0.60, "ddm": 0.10}
}

# ============================================================================
# LLM SETTINGS
# ============================================================================

OPENAI_API_KEY = os.getenv('OPENAI_API_KEY', '')
LLM_MODEL = "gpt-4"
LLM_TEMPERATURE = 0.3
LLM_MAX_TOKENS = 4000
