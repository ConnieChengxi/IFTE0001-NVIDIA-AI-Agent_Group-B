### README


# NVDA Technical Analysis Agent

This project implements a systematic technical trading strategy for NVIDIA (NVDA) using daily price data. The strategy is designed to be transparent, interpretable, and reproducible, and was developed as part of MSc coursework in asset management.

The project combines traditional technical analysis with a lightweight agent-style pipeline and demonstrates the use of external APIs and a large language model (LLM) at a high level.

---

## Strategy Overview

The trading strategy follows a long-only trend-following framework and uses the following components:

- **EMA (20, 50):** Identifies the prevailing price trend  
- **RSI (14):** Acts as a momentum filter to avoid entering overbought conditions  
- **ATR (14):** Used for volatility-based position sizing and risk management  
- **MACD and Bollinger Bands:** Included for supplementary analysis and visual diagnostics  

Transaction costs are included in the backtest to better reflect realistic trading conditions.

---

## Project Structure

```text
NVDA-technical-agent/
│
├── run_demo.py              # Main executable script
├── requirements.txt         # Python dependencies
├── README.md
│
├── src/
│   ├── data_loader.py       # Data loading via Yahoo Finance API
│   ├── indicators.py        # Technical indicator calculations
│   ├── strategy.py          # Trading signal logic
│   ├── backtest.py          # Backtesting engine
│   ├── metrics.py           # Performance metrics
│   └── llm_report.py        # LLM-assisted reporting (optional)
│
├── notebooks/
│   └── nvda_exploration.ipynb   # Full exploratory analysis and final strategy
│
├── figures/                 # Saved plots used in the report
└── outputs/
    └── llm_summary.md       # LLM-generated narrative summary (optional)

---

## How to Run 

1. Install dependencies
From the project root:
pip install -r requirements.txt

2. Run the demo script
cd ~/NVDA-technical-agent
python run_demo.py


This will:
download NVDA price data via the Yahoo Finance API
compute technical indicators
run the backtest
print performance metrics to the terminal


## LLM and API Integration

This project uses external APIs in two ways:
Market data API: NVDA price data is retrieved programmatically using Yahoo Finance via the yfinance package.
LLM API (optional): A large language model is integrated to generate an initial narrative summary of strategy performance based on computed metrics.
The LLM does not make trading decisions. Instead, it is used as an analytical assistant to help translate numerical results into draft explanatory text. The generated summary is saved to:
outputs/llm_summary.md
If no API key is provided, the LLM step is skipped gracefully and the rest of the pipeline runs normally.


## Notes

The Jupyter notebook contains the full exploratory analysis and the final risk-managed strategy.
The run_demo.py script provides a simplified, reproducible entry point for demonstrating the strategy pipeline.




