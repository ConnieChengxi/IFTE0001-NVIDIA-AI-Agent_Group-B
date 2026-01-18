# Tech Analyst Agent (Prototype) 

This repository implements a prototype **Technical Analyst Agent** for financial market research and asset management applications. 

The project demonstrates how systematic technical analysis, backtesting, and AI-assisted reporting can be combined within a modular engineering pipeline to support **buy-side investment insight**, particularly in market timing and risk management contexts. 

The work is developed in the context of **IFTE0001: Introduction to Financial Markets**, and is designed to emulate the workflow of a **buy-side technical analyst** operating within an asset management firm. 

---

## Pipeline Overview 

The agent follows a modular, end-to-end research workflow aligned with professional asset management practices: 

1. **Data Ingestion** 
   Historical market data is collected from public data sources and validated for analysis. 

2. **Feature Engineering** 
   Core technical indicators are constructed using rolling and exponentially weighted statistics, with explicit safeguards to reduce look-ahead bias. 

3. **Signal Generation**
   Systematic trading signals are derived from combinations of trend, momentum, and market regime filters. 
   
4. **Backtesting & Evaluation** 
   A vectorised backtesting engine evaluates strategy performance, producing equity curves, drawdowns, and standard risk-adjusted metrics.  

5. **Visualisation** 
   Visual outputs such as equity curves and drawdown charts are generated to support interpretation of stratefy behaviour and portfolio-level risk dynamics. 

---


## Data 
- **Source:** Yahoo Finance (yfinance) 
- **Asset:** NVIDIA Corporation (NVDA) 
- **Market:** US Equities 
- **Frequency:** Daily 
- **Time Horizon:** 10 years 

--- 

## Features & Signals 
The agent constructs commonly used technical indicators, including: 
- Moving averages (short-, medium-, and long-term) 
- Momentum indicators (e.g., RSI, MACD)
- Trend and regime filters These features are combined to generate **systematic long/flat trading signals**. The emphasis is placed on **clarity, reproducibility, and financial logic**, rather than indicator novelty or parameter optimisation. 

---

## Backtesting
Strategy performance is evaluated using a vectorised backtesting framework. Key outputs include: 
- Equity curve and drawdown profile 
- Performance metrics such as CAGR, Sharpe ratio, and hit rate 
- Transaction cost-adjusted results Backtesting is used to assess whether technical signals generate **interpretable and economically meaningful insights** that could inform portfolio-level timing or risk overlays. 

---

## AI-Assisted Reporting
In addition to numerical evaluation, the pipeline supports **AI-assisted reporting** via a large language model (LLM). The LLM is used strictly as a **post-processing and communication tool**: it transforms pre-computed signals and backtest metrics into a structured, readable technical trade note. All analytical reasoning is grounded in deterministic code outputs; the LLM does **not** generate signals or make investment decisions. 

---

## How to Run
```bash
pip install -r requirements.txt
export OPENAI_API_KEY="YOUR_API_KEY"
python run_demo.py
```