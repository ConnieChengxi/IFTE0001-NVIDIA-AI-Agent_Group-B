import os
from dotenv import load_dotenv

load_dotenv()

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CACHE_DIR = os.path.join(PROJECT_ROOT, 'cache')
OUTPUT_DIR = os.path.join(PROJECT_ROOT, 'outputs')
CACHE_TTL_HOURS = 24

ALPHA_VANTAGE_API_KEY = os.getenv('ALPHA_VANTAGE_API_KEY', '')
ALPHA_VANTAGE_BASE_URL = "https://www.alphavantage.co/query"

RISK_FREE_RATE_FALLBACK = 0.042
EQUITY_RISK_PREMIUM = 0.055
TERMINAL_GROWTH_RATE = 0.025
DCF_PROJECTION_YEARS = 5

MAX_PEERS = 3
MIN_MARKET_CAP_RATIO = 0.05
MAX_MARKET_CAP_RATIO = 7.0
MAX_VALID_PE_RATIO = 300
MIN_VALID_PE_RATIO = -100

INDUSTRY_PEERS = {
    "semiconductors": [
        "NVDA", "AMD", "INTC", "QCOM", "AVGO", "TXN", "MU", "MRVL", 
        "ASML", "LRCX", "KLAC", "AMAT", "ADI", "NXPI", "ON", "SWKS"
    ],
    "software - infrastructure": [
        "MSFT", "ORCL", "CRM", "NOW", "SNOW", "PLTR", "MDB", "DDOG",
        "NET", "ZS", "CRWD", "PANW", "FTNT", "SPLK"
    ],
    "software - application": [
        "ADBE", "INTU", "WDAY", "TEAM", "HUBS", "ZM", "DOCU", "OKTA",
        "BILL", "PAYC", "PCTY", "MANH", "ANSS", "CDNS", "SNPS"
    ],
    "internet content & information": [
        "GOOGL", "META", "SNAP", "PINS", "TWTR", "MTCH", "BMBL", "YELP"
    ],
    "consumer electronics": [
        "AAPL", "SONY", "HPQ", "DELL", "LOGI", "HEAR", "KOSS", "GPRO"
    ],
    "communication equipment": [
        "CSCO", "JNPR", "ANET", "MSI", "NOK", "ERIC", "CIEN", "VIAV"
    ],
    "electronic components": [
        "APH", "TEL", "GLW", "JBL", "FLEX", "CLS", "PLXS", "TTMI"
    ],
    "it services": [
        "IBM", "ACN", "CTSH", "INFY", "WIT", "EPAM", "GLOB", "DXC"
    ],
    "drug manufacturers - general": [
        "JNJ", "PFE", "MRK", "LLY", "ABBV", "BMY", "AMGN", "GILD"
    ],
    "drug manufacturers - specialty & generic": [
        "TEVA", "MYL", "VTRS", "PRGO", "ZTS", "ELAN", "JAZZ", "NBIX"
    ],
    "biotechnology": [
        "MRNA", "REGN", "VRTX", "BIIB", "ILMN", "SGEN", "ALNY", "BMRN",
        "EXAS", "SRPT", "RARE", "IONS", "BNTX", "CRSP", "BEAM", "EDIT"
    ],
    "medical devices": [
        "MDT", "ABT", "SYK", "BSX", "EW", "ISRG", "DXCM", "ALGN",
        "HOLX", "BAX", "BDX", "ZBH", "PODD", "SWAV", "NVST"
    ],
    "healthcare plans": [
        "UNH", "CVS", "CI", "HUM", "CNC", "MOH", "ANTM", "ELV"
    ],
    "medical care facilities": [
        "HCA", "THC", "UHS", "CYH", "ACHC", "SGRY", "SEM", "NHC"
    ],
    "diagnostics & research": [
        "TMO", "DHR", "A", "LH", "DGX", "PKI", "BIO", "QGEN", "NTRA"
    ],
    "banks - diversified": [
        "JPM", "BAC", "WFC", "C", "GS", "MS", "USB", "PNC", "TFC"
    ],
    "banks - regional": [
        "FITB", "KEY", "RF", "CFG", "HBAN", "MTB", "ZION", "CMA", "FHN"
    ],
    "credit services": [
        "V", "MA", "AXP", "DFS", "COF", "SYF", "ALLY", "PYPL", "SQ"
    ],
    "asset management": [
        "BLK", "BX", "KKR", "APO", "ARES", "CG", "OWL", "TROW", "IVZ"
    ],
    "insurance - diversified": [
        "BRK.B", "AIG", "MET", "PRU", "AFL", "ALL", "TRV", "PGR", "CB"
    ],
    "insurance - life": [
        "LNC", "PFG", "VOYA", "UNM", "GL", "CNO", "FAF", "RGA"
    ],
    "insurance - property & casualty": [
        "PGR", "ALL", "TRV", "CB", "HIG", "CNA", "WRB", "CINF", "AFG"
    ],
    "capital markets": [
        "SCHW", "IBKR", "HOOD", "VIRT", "MKTX", "TW", "NDAQ", "ICE"
    ],
    "financial data & stock exchanges": [
        "SPGI", "MSCI", "MCO", "FDS", "MORN", "ICE", "NDAQ", "CME", "CBOE"
    ],
    "internet retail": [
        "AMZN", "BABA", "JD", "PDD", "MELI", "SE", "CPNG", "ETSY", "W", "CHWY"
    ],
    "specialty retail": [
        "HD", "LOW", "TJX", "ROST", "ULTA", "BBY", "TSCO", "WSM", "RH", "FIVE"
    ],
    "apparel retail": [
        "TGT", "GPS", "ANF", "AEO", "URBN", "EXPR", "PLCE", "GIII"
    ],
    "auto manufacturers": [
        "TSLA", "F", "GM", "TM", "HMC", "STLA", "RIVN", "LCID", "NIO", "XPEV"
    ],
    "auto parts": [
        "APTV", "BWA", "LEA", "MGA", "VC", "ALV", "AXL", "DAN", "ADNT"
    ],
    "restaurants": [
        "MCD", "SBUX", "CMG", "YUM", "DRI", "DARDEN", "QSR", "WEN", "DPZ", "PZZA"
    ],
    "travel & leisure": [
        "BKNG", "ABNB", "EXPE", "MAR", "HLT", "H", "WH", "IHG", "RCL", "CCL", "NCLH"
    ],
    "apparel manufacturing": [
        "NKE", "LULU", "UAA", "VFC", "PVH", "RL", "GOOS", "SKX", "DECK"
    ],
    "home improvement retail": [
        "HD", "LOW", "FND", "TILE", "BLDR", "BECN", "GMS"
    ],
    "gambling": [
        "LVS", "MGM", "WYNN", "CZR", "DKNG", "PENN", "BYD", "MLCO"
    ],
    "beverages - non-alcoholic": [
        "KO", "PEP", "MNST", "KDP", "FIZZ", "COKE", "CELH"
    ],
    "beverages - alcoholic": [
        "BUD", "DEO", "STZ", "TAP", "SAM", "ABEV", "BF.B"
    ],
    "household products": [
        "PG", "CL", "CLX", "KMB", "CHD", "SPB", "EPC", "HELE"
    ],
    "packaged foods": [
        "MDLZ", "GIS", "K", "CPB", "SJM", "HSY", "HRL", "CAG", "MKC", "POST"
    ],
    "food distribution": [
        "SYY", "USFD", "PFGC", "CHEF", "UNFI"
    ],
    "grocery stores": [
        "KR", "WMT", "COST", "TGT", "ACI", "SFM", "GO", "IMKTA"
    ],
    "tobacco": [
        "PM", "MO", "BTI", "JAPAF", "TPB", "VGR", "UVV"
    ],
    "discount stores": [
        "WMT", "COST", "TGT", "DG", "DLTR", "BJ", "OLLI", "BIG"
    ],
    "aerospace & defense": [
        "BA", "LMT", "RTX", "NOC", "GD", "LHX", "TDG", "HWM", "TXT", "HII"
    ],
    "airlines": [
        "DAL", "UAL", "LUV", "AAL", "ALK", "JBLU", "SAVE", "HA"
    ],
    "railroads": [
        "UNP", "CSX", "NSC", "CP", "CNI", "KSU"
    ],
    "trucking": [
        "ODFL", "SAIA", "XPO", "JBHT", "WERN", "KNX", "SNDR", "HTLD"
    ],
    "integrated freight & logistics": [
        "UPS", "FDX", "EXPD", "CHRW", "HUBG", "GXO", "FWRD"
    ],
    "farm & heavy construction machinery": [
        "DE", "CAT", "AGCO", "CNHI", "PCAR", "OSK", "TEX", "MTW"
    ],
    "industrial machinery": [
        "HON", "EMR", "ETN", "PH", "ROK", "AME", "DOV", "ITW", "GNRC"
    ],
    "electrical equipment & parts": [
        "ABBNY", "SIEGY", "GNRC", "NVT", "AYI", "HUBB", "POWL"
    ],
    "conglomerates": [
        "GE", "MMM", "DHR", "HON", "ITW", "CMI", "PNR", "ROP"
    ],
    "engineering & construction": [
        "ACM", "J", "FLR", "PWR", "EME", "MTZ", "GVA", "TPC"
    ],
    "waste management": [
        "WM", "RSG", "WCN", "CLH", "CWST", "GFL", "MEG"
    ],
    "rental & leasing services": [
        "URI", "HEES", "WSC", "MGRC", "GATX", "AL", "AER"
    ],
    "security & protection services": [
        "ALLE", "ASSA.B", "JCI", "LDOS", "BAH", "CACI", "SAIC"
    ],
    "staffing & employment services": [
        "ADP", "PAYX", "RHI", "KFRC", "MAN", "ASGN", "NSP", "KELYA"
    ],
    "consulting services": [
        "ACN", "IT", "TTEK", "FTI", "HURN", "EXLS", "FCN"
    ],
    "oil & gas integrated": [
        "XOM", "CVX", "SHEL", "TTE", "BP", "COP", "EOG"
    ],
    "oil & gas e&p": [
        "PXD", "DVN", "FANG", "EOG", "COP", "OXY", "APA", "MRO", "HES"
    ],
    "oil & gas equipment & services": [
        "SLB", "HAL", "BKR", "FTI", "NOV", "CHX", "WHD", "LBRT"
    ],
    "oil & gas midstream": [
        "KMI", "WMB", "OKE", "ET", "EPD", "MPLX", "PAA", "TRGP"
    ],
    "oil & gas refining & marketing": [
        "VLO", "MPC", "PSX", "PBF", "DINO", "HFC", "DK", "CVI"
    ],
    "uranium": [
        "CCJ", "UEC", "DNN", "UUUU", "NXE", "LEU"
    ],
    "coal": [
        "BTU", "ARCH", "CEIX", "AMR", "HCC", "METC", "NC"
    ],
    "gold": [
        "NEM", "GOLD", "AEM", "KGC", "AU", "FNV", "WPM", "RGLD"
    ],
    "silver": [
        "PAAS", "HL", "AG", "CDE", "EXK", "FSM", "MAG"
    ],
    "copper": [
        "FCX", "SCCO", "TECK", "HBM", "ERO", "CPER"
    ],
    "steel": [
        "NUE", "STLD", "CLF", "X", "RS", "CMC", "ATI", "TMST"
    ],
    "aluminum": [
        "AA", "CENX", "KALU", "ARNC"
    ],
    "specialty chemicals": [
        "LIN", "APD", "SHW", "ECL", "PPG", "ALB", "DD", "EMN", "CE"
    ],
    "agricultural inputs": [
        "MOS", "NTR", "CF", "FMC", "CTVA", "SMG", "AVD"
    ],
    "building materials": [
        "VMC", "MLM", "CX", "SUM", "EXP", "USLM", "ITE"
    ],
    "paper & paper products": [
        "IP", "PKG", "WRK", "GPK", "SON", "CLW", "SLVM"
    ],
    "lumber & wood production": [
        "WY", "RYN", "PCH", "LPX", "UFPI", "JELD"
    ],
    "reit - industrial": [
        "PLD", "DRE", "FR", "STAG", "REXR", "TRNO", "COLD"
    ],
    "reit - retail": [
        "SPG", "O", "NNN", "REG", "FRT", "KIM", "BRX", "AKR"
    ],
    "reit - residential": [
        "AVB", "EQR", "MAA", "UDR", "ESS", "CPT", "INVH", "AMH"
    ],
    "reit - office": [
        "BXP", "VNO", "SLG", "KRC", "DEI", "JBGS", "CUZ", "OFC"
    ],
    "reit - healthcare facilities": [
        "WELL", "VTR", "PEAK", "OHI", "HR", "DOC", "LTC", "NHI"
    ],
    "reit - diversified": [
        "WPC", "STOR", "EPRT", "ADC", "GTY", "FCPT"
    ],
    "reit - specialty": [
        "AMT", "CCI", "SBAC", "EQIX", "DLR", "PSA", "EXR", "CUBE", "LSI"
    ],
    "real estate services": [
        "CBRE", "JLL", "CWK", "NMRK", "OPEN", "RDFN", "EXPI"
    ],
    "utilities - regulated electric": [
        "NEE", "DUK", "SO", "D", "AEP", "XEL", "WEC", "ED", "EIX", "PEG"
    ],
    "utilities - regulated gas": [
        "SRE", "ATO", "NI", "OGS", "NJR", "NFG", "SPH"
    ],
    "utilities - diversified": [
        "EXC", "ES", "CMS", "DTE", "PPL", "FE", "AEE", "EVRG"
    ],
    "utilities - renewable": [
        "BEP", "CWEN", "AQN", "ORA", "RNW", "NEP", "ARRY"
    ],
    "utilities - independent power producers": [
        "NRG", "VST", "TALEN", "CEG"
    ],
    "telecom services": [
        "T", "VZ", "TMUS", "LUMN", "FTR", "USM", "SHEN"
    ],
    "entertainment": [
        "DIS", "NFLX", "WBD", "PARA", "LGF.A", "CMCSA", "FOX", "ROKU", "SPOT"
    ],
    "interactive media & services": [
        "GOOGL", "META", "SNAP", "PINS", "TWTR", "MTCH", "BMBL"
    ],
    "advertising agencies": [
        "OMC", "IPG", "WPP", "PUBGY", "TTD", "MGNI", "APPS", "DV"
    ],
    "publishing": [
        "NYT", "NWSA", "GCI", "LEE", "TRNC", "SSP"
    ],
    "gaming": [
        "ATVI", "EA", "TTWO", "RBLX", "U", "SE", "NTDOY", "PLTK"
    ],
}

RELATED_INDUSTRIES = {
    "semiconductors": ["software - infrastructure", "consumer electronics", "communication equipment"],
    "software - infrastructure": ["software - application", "it services", "semiconductors"],
    "software - application": ["software - infrastructure", "internet content & information"],
    "consumer electronics": ["semiconductors", "communication equipment"],
    "drug manufacturers - general": ["drug manufacturers - specialty & generic", "biotechnology"],
    "biotechnology": ["drug manufacturers - general", "diagnostics & research"],
    "medical devices": ["diagnostics & research", "healthcare plans"],
    "banks - diversified": ["banks - regional", "capital markets"],
    "banks - regional": ["banks - diversified", "credit services"],
    "credit services": ["banks - diversified", "asset management"],
    "insurance - diversified": ["insurance - life", "insurance - property & casualty"],
    "internet retail": ["specialty retail", "discount stores"],
    "restaurants": ["packaged foods", "food distribution"],
    "auto manufacturers": ["auto parts", "specialty retail"],
    "beverages - non-alcoholic": ["beverages - alcoholic", "packaged foods"],
    "aerospace & defense": ["airlines", "conglomerates"],
    "airlines": ["travel & leisure", "aerospace & defense"],
    "railroads": ["trucking", "integrated freight & logistics"],
    "oil & gas integrated": ["oil & gas e&p", "oil & gas refining & marketing"],
    "oil & gas e&p": ["oil & gas integrated", "oil & gas equipment & services"],
    "gold": ["copper", "steel"],
    "specialty chemicals": ["agricultural inputs", "building materials"],
    "reit - industrial": ["reit - retail", "reit - diversified"],
    "reit - specialty": ["reit - industrial", "reit - office"],
    "utilities - regulated electric": ["utilities - diversified", "utilities - renewable"],
    "entertainment": ["gaming", "interactive media & services"],
    "telecom services": ["communication equipment", "internet content & information"],
}

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

MIN_INTEREST_COVERAGE = 1.5
MAX_DEBT_TO_EBITDA = 5.0
MIN_CURRENT_RATIO = 0.8

BUY_THRESHOLD = 0.20
SELL_THRESHOLD = -0.10

MIN_DIVIDEND_YIELD = 0.01
MIN_DIVIDEND_HISTORY = 3

COMPANY_TYPE_WEIGHTS = {
    "growth": {"dcf": 0.70, "multiples": 0.30, "ddm": 0.00},
    "balanced": {"dcf": 0.50, "multiples": 0.30, "ddm": 0.20},
    "dividend": {"dcf": 0.30, "multiples": 0.20, "ddm": 0.50},
    "cyclical": {"dcf": 0.30, "multiples": 0.60, "ddm": 0.10}
}

OPENAI_API_KEY = os.getenv('OPENAI_API_KEY', '')
LLM_MODEL = "gpt-4"
LLM_TEMPERATURE = 0.3
LLM_MAX_TOKENS = 4000