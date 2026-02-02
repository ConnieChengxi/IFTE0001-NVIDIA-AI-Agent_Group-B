NVIDIA Technical Agent
=================================

Project Overview
----------------
This repository contains scripts for collecting market data, computing indicators, running backtests, and generating an LLM-based report focused on NVIDIA (NVDA) analysis.

Key Scripts
-----------
- `data_collection.py`: Fetches and stores market data used by the analysis and backtests.
- `indicators.py`: Implements technical indicator calculations used by the strategy/backtest.
- `backtesting.py`: Runs historical backtests for strategies built with the provided indicators.
- `llm_report.py`: Generates an AI-assisted analysis report.

Requirements
------------
- Python 3.8+ recommended
- Install required packages:

```bash
pip install -r requirements.txt
```

Quick Start
-----------
1. Collect data (if applicable):

```bash
python data_collection.py
```

2. Run backtest:

```bash
python backtesting.py
```

3. Generate AI/LLM report:

```bash
python llm_report.py
```

Outputs
-------
- Generated reports and artifacts are stored in the `outputs/` directory. Example: `outputs/NVDA_ai_Report.txt`.

Project Structure
-----------------
- `backtesting.py` - Backtest runner
- `data_collection.py` - Data ingestion utilities
- `indicators.py` - Indicator implementations
- `llm_report.py` - LLM-driven report generator
- `requirements.txt` - Python dependencies
- `outputs/` - Stored reports and results

Notes
-----
- Review and update `requirements.txt` to ensure compatibility with your environment.
- If external API keys are needed for data collection, set them via environment variables or a local config (not committed to repo).

