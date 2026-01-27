# NVDA Fundamental Agent (Modular)

## What it does
Cache-first Alpha Vantage ingestion → standardised statements → ratio diagnostics + trend plots → peer TTM multiples (NVDA vs ADI/QCOM/TXN) with charts → DCF valuation (revenue-driven FCFF, WACC, terminal value) → LLM-grounded narrative report.

## How to run
1) Create `secrets.env`:
   - `ALPHAVANTAGE_API_KEY=YOUR_KEY`
   - (optional) `OPENAI_API_KEY=YOUR_KEY`
2) Install:
   - `pip install -r requirements.txt`
3) Run:
   - `python main.py`

## Project structure
- `src/data_fetcher.py`: AV cache-first ingestion
- `src/statements.py`: parse + standardise IS/BS/CF
- `src/ratios.py`: ratio metrics + summaries
- `src/multiples.py`: peer TTM multiples
- `src/dcf.py`: WACC + FCFF + DCF intrinsic value
- `src/visualization.py`: charts
- `src/llm_report.py`: LLM narrative grounded on computed outputs
