# Hybrid Investment Analyst

Dual-agent system combining **Fundamental Valuation** with **Technical Execution** using sequential gate architecture.

## Architecture

The system consists of two sub-agents coordinated by an orchestrator:

1. **Fundamental Agent** — DCF valuation, multiples analysis, DDM, financial ratios, DuPont, Bull/Base/Bear scenarios 
2. **Technical Agent** — MA crossover backtest, risk metrics, regime filter

The orchestrator runs both agents sequentially and applies dual-gate logic to produce a final recommendation.

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Configure API keys
cp .env.example .env
# Edit .env: add ALPHA_VANTAGE_API_KEY, OPENAI_API_KEY

# Run analysis
python run_demo.py NVDA
```

## How It Works

### Gate 1 — Fundamental Agent

- Calculates fair value using DCF, Multiples, and DDM
- Classifies company type (Growth / Balanced / Dividend / Cyclical)
- Analyzes 5-year historical financial ratios
- Generates BUY / HOLD / SELL recommendation

### Gate 2 — Technical Agent

- Runs backtest on MA20/MA50 crossover strategy with MA200 regime filter
- Calculates Sharpe ratio, CAGR, max drawdown, hit rate
- Generates equity curves, drawdown charts, trade timeline
- Determines TRADE / WAIT based on current market regime

### Decision Logic

| Gate 1 (Fundamental) | Gate 2 (Technical) | Final Action |
|----------------------|-------------------|--------------|
| BUY / HOLD           | Close > MA200     | **TRADE**    |
| BUY / HOLD           | Close < MA200     | **WAIT**     |
| SELL                 | —                 | **NO_TRADE** |

## Project Structure

```
Hybrid/
├── run_analysis.py                  # Main entry point
├── requirements.txt                 # Dependencies
├── .env                             # API keys (not in git)
│
├── hybrid_controller/               # Orchestration layer
│   ├── src/
│   │   ├── orchestrator.py          # Runs agents, applies gate logic
│   │   └── reporting/
│   │       └── html_report.py       # Generates hybrid investment memo
│   └── outputs/                     # All generated reports
│
├── idaliia_fundamental/             # Fundamental Analysis Agent
│   ├── run_demo.py                  # Agent entry point
│   ├── src/
│   │   ├── analysis/                # DCF, DDM, Multiples, Ratios
│   │   ├── data_collection/         # Alpha Vantage, Yahoo Finance
│   │   └── reporting/               # Memo generation
│   └── outputs/
│
└── connie_technical/                # Technical Analysis Agent
    ├── run_demo.py                  # Agent entry point
    ├── src/
    │   ├── backtest/                # Backtest engine
    │   ├── signals/                 # MA crossover signals
    │   ├── viz/                     # Charts generation
    │   └── reporting/               # PDF report
    └── outputs/
```

## Output

Running `python run_demo.py NVDA` generates **3 reports** (PDF + HTML):

```
hybrid_controller/outputs/
├── NVDA_investment_memo.pdf / .html         # Hybrid report (main)
├── NVDA_fundamental_analysis.pdf / .html    # Fundamental valuation details
└── NVDA_technical_analysis.pdf / .html      # Technical backtest results
```

## API Keys

| Key | Required | Purpose | Source |
|-----|----------|---------|--------|
| `ALPHA_VANTAGE_API_KEY` | Yes | Financial statements, ratios | [alphavantage.co](https://www.alphavantage.co/support/#api-key) |
| `OPENAI_API_KEY` | No | AI-generated investment thesis | [platform.openai.com](https://platform.openai.com/api-keys) |

## Example Output

```
============================================================
  ANALYSIS COMPLETE
============================================================
  Company:         NVIDIA Corporation
  Recommendation:  BUY
  Current Price:   $131.29
  Fair Value:      $178.45
  Upside:          +35.9%
------------------------------------------------------------
  Gate 1 (Fund):   PASS
  Gate 2 (Tech):   PASS
  FINAL ACTION:    TRADE
============================================================
```
