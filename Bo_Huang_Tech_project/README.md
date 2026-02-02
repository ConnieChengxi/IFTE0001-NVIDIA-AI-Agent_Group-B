# NVDA Technical Analyst Agent

## 1) Project Goal & Output Files
This project builds a reproducible technical-analysis backtesting and reporting pipeline for NVDA.

Key outputs:
- `outputs/main/` (main figures + metrics)
- `outputs/appendix/` (appendix experiments and extra figures/tables)
- `outputs/NVDA_investment_report.html` (final HTML report)
- `outputs/NVDA_investment_report.md` (LLM narrative, when enabled)
- `outputs/report_inputs.json` (deterministic payload used to render the report)

PDF: open the HTML report in a browser and use Print -> Save as PDF (A4).

## 2) Pipeline & Architecture
High-level pipeline:
1. Fetch 10-year OHLCV data for NVDA (Yahoo Finance).
2. Compute returns and signals, then split Train/Val/Test to grid-search on validation Sharpe.
3. Run the full backtest on the chosen parameters.
4. Write figures, tables, and report inputs to `outputs/`.
5. (Optional) call OpenAI to draft the narrative and export HTML.

Code layout (simplified):
- `run_demo.py`: main entrypoint and CLI
- `tech_agent/`: data, indicators, signal generation, backtest, report assembly
- `templates/`: report templates
- `webapp.py`: Streamlit app entrypoint
- `inputs/`: configuration inputs (e.g., fundamental override JSON)
- `external/`: external fundamental module/report artifacts (if you run this module, install its own `requirements.txt` in that folder)
- `data_cache/`: cached market data
- `sample_outputs/`: pre-generated sample report (HTML/MD) for reference

## 3) Environment Requirements
- Python 3.10+
- `yfinance==0.2.66` (lower versions may fail to fetch data)

## 4) API Key Configuration (.env)
If you enable LLM reporting, put your key in `.env` (do not commit it):
```
OPENAI_API_KEY=your_real_key_here
```
The runner auto-loads `.env` on startup.

## 5) How to Run
Create and activate venv:
```bash
python3.10 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

Backtest only (no LLM):
```bash
python run_demo.py --ticker NVDA --years 10 --as_of latest --no_llm
```

Full run (LLM + HTML export):
```bash
python run_demo.py --ticker NVDA --years 10 --as_of latest --yes_openai --openai_model gpt-4o-mini --export_html
```

Reproducible mode (pinned as-of date):
```bash
python run_demo.py --ticker NVDA --as_of 2026-01-31 --years 10 --yes_openai --openai_model gpt-4o-mini --export_html
```

## 6) Data Processing & Main Strategy (High-Level)
Data processing:
- Fetch OHLCV from Yahoo Finance.
- Clean, align, and standardize the data.
- Compute close-to-close returns and build features/signals.
- Apply multiple preprocessing steps to ensure consistent inputs for signals and backtests.
- Split data into train/validation/test by date.

Main strategy (high-level):
- Score-based signal framework built from multiple technical factors.
- Risk management includes volatility targeting and regime controls.
- Fundamental inputs are an explicit risk filter embedded in the strategy (used to cap exposure), not an alpha source.
- Long/flat only (no short selling).

Appendix experiments:
- Optional variants (e.g., pattern features, volume confirmation) are experimental and for comparison only.

## 7) Backtest Assumptions
Trading cost model:
- Trading costs are modeled as a simple commission-like cost:
  - cost = trading_cost * turnover
- Turnover is computed from executed positions (post-shift).

Execution timing (anti look-ahead):
- The backtest is the only place where positions are shifted:
  - position_exec = position_decision.shift(1)
- Returns are close-to-close and use adjusted close prices.

Benchmark:
- Benchmark is a fair Buy & Hold implemented using the same return and cost model, using the same execution convention.

## 8) Notes on Data Sources
- Primary: Yahoo Finance via yfinance. `auto_adjust=True` is used by default.
- Robustness (stable mode): if Yahoo/yfinance endpoints are blocked/unstable, the pipeline will try a Yahoo chart endpoint,
  then fall back to the most recent local Yahoo cache (if available), and only then fall back to Stooq.
  Stooq prices are **unadjusted**, so returns differ from adjusted-close results if the Stooq fallback is used.

## 9) Included Sample HTML Report (Reference)
This repo includes a pre-generated example report:
- HTML: `sample_outputs/outputs/NVDA_investment_report.html`
- Markdown: `sample_outputs/outputs/NVDA_investment_report.md`
- Deterministic inputs: `sample_outputs/outputs/report_inputs.json`

## 10) Discussion
- Strategy selection requires iterative testing; more indicators do not necessarily improve performance.
- Investment analysis needs to balance return and risk (e.g., Sharpe, drawdowns, stability).

Disclaimer: This project is for learning and academic discussion only and does not constitute investment advice.
