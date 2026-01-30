# AI-Driven Institutional Equity Research Agent (NVDA Focus)

This is an advanced financial analysis agent that automates the generation of institutional-grade equity research reports. It integrates quantitative modeling (DCF, Multi-Model Valuation) with qualitative AI synthesis (GPT-4o) to evaluate NVIDIA (NVDA) against its industry peers.

## Key Features

1.  **Multi-Source Data Pipeline**:
    *   **Alpha Vantage**: Fetches comprehensive financial statements, macroeconomic data (GDP, Treasury yields), and peer fundamentals.
    *   **yfinance**: Provides high-frequency market pricing and benchmark data (SPY).
2.  **Robust Financial Engine**:
    *   **12+ Key Ratios**: Analyzes 12+ critical metrics including Profitability (ROE, Gross/Net Margins), Liquidity (Current Ratio), and Solvency (D/E).
    *   **Peer Benchmarking**: Cross-compares NVDA against 5 industry giants: **AMD, INTC, AVGO, QCOM, and MU**.
3.  **Portable Data & Caching**:
    *   **Monolithic Bundle**: Automatically generates a `data_bundle.json` in the root directory.
    *   **Full Portability**: The agent can be moved to any computer without a `data/` folder; it will restore all historical raw data from the bundle, bypassing API limits.
4.  **Advanced Valuation Modeling**:
    *   **Multi-Model Weighted Valuation**: A blended target price calculation integrating **DCF (Discounted Cash Flow)**, **DDM (Dividend Discount Model)**, and **Market Multiples**.
    *   **Dynamic DCF**: Automated WACC derivation using real-time Treasury yields (Risk-Free Rate) and historical SPY returns (Equity Risk Premium).
    *   **Relative Valuation**: Robust peer benchmarking using a 5-company group (**AMD, INTC, AVGO, QCOM, MU**).
    *   **Sensitivity Analysis**: Real-time heatmaps exploring valuation under varying Growth and Discount Rate assumptions.
4.  **AI-Powered Synthesis**:
    *   Integrates **GPT-4o** as a "Director of Equity Research" to provide multi-paragraph strategic insights, risk assessment, and competitive analysis.
5.  **Institutional-Grade Reporting**:
    *   Generates a professional multi-page PDF with custom branding, styled tables, and side-by-side high-resolution visualization charts.

## Project Structure

```text
Agent/
├── main.py             # Strategic entry point (Orchestrator)
├── data_fetcher.py     # API connector (Alpha Vantage & yfinance)
├── analyzer.py         # Financial ratio calculation engine
├── valuation.py        # DCF, Multiples, and Blended valuation models
├── visualizer.py       # High-res plot generation (Seaborn/Matplotlib)
├── report_gen.py       # PDF synthesis and AI content integration logic
├── config.py           # Peer lists, API parameters, and environment config
├── data_bundle.json    # Portable data bundle (Auto-generated/Self-restoring)
├── data/
│   ├── raw/            # Stored API raw data (Cache directory)
│   └── processed/      # Output: CSVs, Charts, and Final PDF Memo
└── .env                # API Credentials (REQUIRED)
```

## Setup & Execution

### 1. Environment Configuration
Create a `.env` file in the root directory and provide your API keys:
```dotenv
ALPHAVANTAGE_API_KEY=your_alpha_vantage_key
OPENAI_API_KEY=your_openai_api_key
```

### 2. Install Required Packages
Run the following command in your terminal to install all dependencies:
```powershell
pip install pandas matplotlib seaborn fpdf2 python-dotenv yfinance requests openai
```

### 3. Run the Analysis
Execute the main script to start the full data-to-PDF pipeline:
```powershell
python main.py
```

### 4. Portable Usage (Offline/New PC)
If moving to a new computer, simply copy your `.py` files, `.env`, and the `data_bundle.json`. The agent will automatically restore the `data/` directory upon execution.

## Output
Upon completion, the final investment report will be generated in:
`data/processed/NVDA_Investment_Report_[TIMESTAMP].pdf`

The report features automated tables for the Weighted Valuation breakdown, Peer Analytics, and DCF Assumption parameters.

## Performance Notes
*   **Deep Synthesis**: Step 5 (AI Generation) may take 60-90 seconds as it retrieves high-density research content from GPT-4o.
*   **Rate Limiting**: The system includes built-in pauses to accommodate Alpha Vantage Free Tier limitations.

