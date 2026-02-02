# External Fundamental Analyst Agent

Automated equity research system for generating investment memos. Built as part of UCL MSc AI coursework.

## Overview

This project automates fundamental analysis of publicly traded companies. It pulls financial data, runs DCF models, compares peer valuations, and generates professional investment memos in HTML format.

The system classifies companies (Growth/Dividend/Balanced/Cyclical) and applies appropriate valuation methods. LLM integration provides narrative analysis throughout the report.

## Installation

```bash
# Clone and navigate to project
cd fundamental_analyst_agent

# Set up virtual environment (recommended)
python -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

## Configuration

1. Copy the environment template:
```bash
cp .env.example .env
```

2. Edit `.env` and add your API keys:
   - Alpha Vantage API key (free tier available)
   - OpenAI API key (pay-per-use)

See `.env.example` for the format.

## Usage

```bash
python run_analysis.py NVDA
```

Output appears in `outputs/NVDA_Investment_Memo.html`

## Project Structure

```
├── config/settings.py           # Constants and configuration
├── src/
│   ├── data_collection/         # API client and caching
│   ├── analysis/                # Valuation models and ratios
│   ├── agent/                   # Recommendation engine
│   └── reporting/               # HTML report generation
├── cache/                       # API response cache
├── outputs/                     # Generated memos
├── .env.example                 # Template for API keys
└── requirements.txt             # Python dependencies
```

## Key Design Choices

**Company Classification**

The system categorizes companies to apply appropriate valuation weights:

- **Growth** (>15% revenue growth, <2% yield): Heavy multiples weight since DCF is uncertain over long horizons
- **Dividend** (>4% yield, <10% growth): DDM emphasis for income valuation
- **Balanced**: Equal weighting across methods
- **Cyclical** (sector-based): Normalized multiples to avoid peak/trough distortion

**DCF Growth Rates**

Different company types need different approaches:

- Growth companies: Weight recent years 70/30 vs historical (captures acceleration like AI boom)
- Cyclical: Use median FCF to normalize through the cycle
- Dividend: Take 25th percentile growth for conservatism
- Balanced: Simple CAGR

Maximum growth caps prevent unrealistic projections (40% for growth, 20% balanced, etc.)

**Gate Checks**

Valuation gets overridden by critical risks:
- Interest coverage <1.5x → automatic SELL
- Current ratio <0.8x → downgrade recommendation
- D/E >5.0x → risk flag

## Limitations

**Data Quality & Coverage**
- Only works with US-listed stocks (Alpha Vantage limitation)
- Relies on quarterly/annual filings - no real-time data
- Historical data limited to what Alpha Vantage provides (typically 5 years)
- Some companies have incomplete financial data (recent IPOs, SPACs, etc.)
- No access to management guidance or non-GAAP metrics

**Valuation Methodology**
- DCF assumes stable business models - poor for turnarounds or distressed situations
- Peer selection is manual and subjective
- No adjustment for one-time items or extraordinary events
- Terminal growth rate (2.5%) is fixed across all industries
- Beta from market data may not reflect forward-looking risk

**Analysis Scope**
- No qualitative factors (management quality, competitive moat strength)
- No industry-specific metrics (SaaS: ARR/CAC, Banks: NIM/NPL, etc.)
- Cannot analyze private companies or unlisted securities
- No M&A scenarios or sum-of-parts valuation
- Ignores market sentiment and technical factors

**Technical Constraints**
- Alpha Vantage free tier: 25 requests/day (limits to ~4-5 companies daily)
- Field mapping may break if API changes format
- LLM narratives can be generic if insufficient context
- HTML output only (no PDF, Excel, or database export)
- Single-threaded processing (no batch mode)

**Regulatory & Compliance**
- Not registered investment advice
- No compliance checks or disclosures
- No consideration of investor suitability
- Historical backtesting not implemented

**Known Failure Cases**
- Companies with negative FCF in all periods (unprofitable growth stocks)
- Highly levered companies where D/E calculation breaks
- Post-merger entities with discontinuous financials
- Companies that changed fiscal year-end
- Stocks with multiple share classes

## Known Issues

**Alpha Vantage Rate Limits**

Free tier allows 25 requests/day. Each analysis uses 5-6 requests. If you hit the limit:
- Wait 24 hours for reset
- Cache prevents repeated calls for the same company
- Consider upgrading to premium tier for production use

**Field Mapping**

Alpha Vantage returns fields in inconsistent formats (camelCase, snake_case, etc). The client has comprehensive mappings but edge cases exist. Check `alpha_vantage_client.py` if ratios show N/A.

**LLM Costs**

Each report makes 5-8 OpenAI API calls (~2,000-3,000 tokens total). Monitor your usage if running batch analyses.

## Academic Context

This is coursework for UCL MSc AI. The goal was to build an agentic system that:
- Integrates multiple data sources
- Applies domain-specific logic (not just generic LLM)
- Produces structured, professional output
- Makes defensible recommendations with clear methodology

It's not meant for actual investment decisions. Just demonstrating how AI can augment traditional equity research workflows.

## Technical Notes

**Why HTML not PDF?**  
HTML is easier to generate programmatically and looks good in browsers. Can always print to PDF if needed.

**Why cache locally not database?**  
Simpler for a prototype. Each ticker gets a folder with JSON files. Easy to inspect and debug.

**Why rules-based classification not ML?**  
The classification logic is transparent and deterministic. For a student project, interpretability matters more than ML sophistication.

## Requirements

- Python 3.9+
- See `requirements.txt` for packages
- Alpha Vantage API key (free tier sufficient for testing)
- OpenAI API key (pay-per-use)

## Disclaimer

This tool generates analysis from historical data and AI narratives. It is:
- **NOT** registered investment advice
- **NOT** suitable for making actual investment decisions
- **NOT** tested for accuracy or reliability
- **FOR EDUCATIONAL PURPOSES ONLY**

Always consult qualified financial advisors before making investment decisions. Past performance does not guarantee future results. The author assumes no liability for any financial losses resulting from use of this tool.
