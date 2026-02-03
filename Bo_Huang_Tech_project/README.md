# NVDA Technical Analyst Agent
author：BO HUANG

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

Appendix (what it contains and why):
- **Sensitivity analysis table**: parameter robustness checks (reported as a table only).
- **MA-only baseline**: a simple moving-average crossover benchmark to contextualize the main strategy.
- **Relative volume confirmation experiment**: an experimental variant that adds a relative-volume (RVOL) confirmation filter; compared against the main strategy and Buy & Hold.
- **Pattern-enabled experiment**: an experimental variant (candlestick/pattern features) compared against the main strategy and Buy & Hold.
- **Fundamental overlay detail**: documented as a short paragraph in the main report and a fuller discussion in **Appendix C** (risk filter only; not an alpha signal).

In this coursework, the **main report focuses only on Buy & Hold vs the main strategy**. All additional variants and robustness checks are placed in the Appendix to keep the main narrative concise and reproducible.

Code layout (framework)

```
project_root/
├─ run_demo.py        Main entrypoint and CLI
├─ tech_agent/        Core library
│  ├─ data.py         Data ingestion, caching, standardisation
│  ├─ indicators.py   Technical indicators (EMA, RSI, MACD, Bollinger)
│  ├─ signals.py      Signal scoring, regime, position mapping
│  ├─ engines.py      Risk management wrapper (vol targeting, caps) and orchestration
│  ├─ backtest.py     Execution delay (shift), trading costs, performance metrics
│  ├─ visualization.py Figures and tables (main and appendix)
│  ├─ llm_provider.py LLM narrative generation (OpenAI)
│  └─ html_report.py  HTML rendering from template + payload
├─ templates/         HTML template(s) used for the report
├─ webapp.py          Streamlit web app entrypoint
├─ inputs/            Configuration inputs (e.g., fundamental override JSON)
├─ external/          External fundamental module and its artifacts
├─ data_cache/        Cached market data  
└─ sample_outputs/    Generated artifacts from a run
```

## 3) Environment Requirements
- Python 3.10+
- `yfinance==0.2.66` (lower versions may fail to fetch data)

## 4) Environment Variables (.env) & API Keys
This project requires API keys via a `.env` file in the **project root** (do not commit it).

**`.env.example`**
```env
ALPHA_VANTAGE_API_KEY=your_alpha_vantage_key_here  # Required for external fundamental analysis
OPENAI_API_KEY= your_real_key_here  # LLM reporting
```

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

## 6) Data Processing & Main Strategy
Data processing:
- Fetch OHLCV from Yahoo Finance.
- Clean, align, and standardize the data.
- Compute close-to-close returns and build features/signals.
- Apply multiple preprocessing steps to ensure consistent inputs for signals and backtests.
- Split data into train/validation/test by date.

Main strategy overview:
- Score-based signal framework built from multiple technical factors.
- Risk management includes volatility targeting and regime controls.
- Fundamental inputs are an explicit risk filter embedded in the strategy (used to cap exposure), not an alpha source.
- Long/flat only (no short selling).

Main strategy signals:
- **Trend filter**: `EMA_fast > EMA_slow` (trend_up).  
  - EMA windows are selected by grid-search. The default grid includes (20,100), (30,150), (50,200).
- **Other signals**:
  - Pullback: `price < BB_mid * 1.01` (BB window=20, num_std=2)
  - Strength: `RSI(14) > 45`
  - Momentum: `MACD_hist > 0` (12/26/9)
- **Score**: `score = 2*trend_up + (pullback + strength + macd)` → range 0–5.
- **Entry/hold rules**:
  - Entry if `score >= 4`
  - Hold if `score >= 2`
- **Regime (3-state)**: based on price vs `EMA_slow` with a buffer:
  - Bull: full position (1.0)
  - Neutral: half position (0.5)
  - Bear: only strongest signal allowed (score==5 → 0.25), otherwise 0
- **Vol targeting**: use `target_vol` and `vol_window` to size exposure; cap by max leverage.
- **Risk filter (fundamental)**: apply a max-leverage cap; when fundamental analysis is SELL, the cap is scaled by `sell_leverage_mult`.

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
- Benchmark is a fair Buy & Hold baseline (buy once at the beginning and hold until the end, with no further trading).

## 8) Notes on Data Sources
- Primary: Yahoo Finance via yfinance. `auto_adjust=True` is used by default.
- Robustness (stable mode): if Yahoo/yfinance endpoints are blocked/unstable, the pipeline will try a Yahoo chart endpoint,
  then fall back to the most recent local Yahoo cache (if available), and only then fall back to Stooq.
  Stooq prices are **unadjusted**, so returns differ from adjusted-close results if the Stooq fallback is used.

## 9) Included HTML Report
- HTML: `sample_outputs/outputs/NVDA_investment_report.html`
- Markdown: `sample_outputs/outputs/NVDA_investment_report.md`
- Deterministic inputs: `sample_outputs/outputs/report_inputs.json`

## 10) Discussion
- Strategy selection requires iterative testing; more indicators do not necessarily improve performance.
- Investment analysis needs to balance return and risk (e.g., Sharpe, drawdowns, stability).

Disclaimer: This project is for learning and academic discussion only and does not constitute investment advice.
