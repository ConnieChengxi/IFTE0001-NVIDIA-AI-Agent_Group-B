# Hybrid Investment Analyst

Dual-agent system combining **Fundamental Valuation** with **Technical Execution** using sequential gate architecture.

## Quick Start

```bash
# Install
pip install -r requirements.txt

# Configure API keys
cp .env.example .env
# Edit .env: add ALPHA_VANTAGE_API_KEY (required), OPENAI_API_KEY (optional)

# Run
python run_demo.py NVDA
```

## How It Works

**Gate 1 — Fundamental Agent:**
- Calculates fair value using DCF, Multiples (PEG, EV/EBITDA), and DDM
- Classifies company type (Growth / Balanced / Dividend / Cyclical)
- Generates BUY / HOLD / SELL recommendation

**Gate 2 — Technical Agent:**
- Runs backtest on MA20/MA50 crossover strategy with MA200 regime filter
- Calculates Sharpe ratio, CAGR, max drawdown
- Determines TRADE / WAIT based on current market regime

**Decision Logic:**

| Fundamental | Technical (Close vs MA200) | Action |
|-------------|---------------------------|--------|
| BUY / HOLD  | Above                     | TRADE  |
| BUY / HOLD  | Below                     | WAIT   |
| SELL        | —                         | NO_TRADE |

## Project Structure

```
Hybrid/
├── run_demo.py              # Entry point
├── .env                         # API keys (not in git)
├── hybrid_controller/           # Orchestrator + report generation
├── idaliia_fundamental/         # DCF, multiples, DDM valuation
└── connie_technical/            # Backtest, signals, charts
```

## Output

```
hybrid_controller/outputs/
├── {TICKER}_hybrid_report.html       # Main report
├── {TICKER}_fundamental_report.html  # Fundamental analysis
└── {TICKER}_technical_report.pdf     # Technical backtest
```

## API Keys

| Key | Required | Source |
|-----|----------|--------|
| `ALPHA_VANTAGE_API_KEY` | Yes | [alphavantage.co](https://www.alphavantage.co/support/#api-key) |
| `OPENAI_API_KEY` | No | For AI-generated thesis |


