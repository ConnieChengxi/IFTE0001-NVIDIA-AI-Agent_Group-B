# Pipeline Chain (What Runs to Produce the Final Report)

This document lists the *actual* execution chain for generating the NVDA report in this project.

## 1) Entry point
- `run_demo.py`

## 2) Data ingestion (prices)
- `tech_agent/data.py`: fetch + clean OHLCV (default source: Yahoo Finance via `yfinance`).
- Caching (best-effort): `data_cache/ohlcv/`.

## 3) Indicators + signal construction
- `tech_agent/indicators.py`: computes EMA trend, Bollinger pullback check, RSI, MACD histogram, regime state, etc.
- `tech_agent/signals.py`: builds the score, hysteresis long/flat state (`signal_bin`), and maps regime to base exposure.

## 4) Risk management + execution + backtest
- `tech_agent/engines.py`: applies volatility targeting + leverage caps to convert base exposure into a target position.
- `tech_agent/backtest.py`: applies the **1-bar execution delay** (decision-time -> next-bar execution) and transaction costs.

## 5) Benchmark and metrics
- `tech_agent/backtest.py`: benchmark is Buy & Hold with the same execution convention.
- `tech_agent/visualization.py`: writes metrics tables + figures to `outputs/main/` and `outputs/appendix/`.

## 6) External fundamental overlay (risk control only; enabled by default)
- `tech_agent/fundamental_filter.py`: applies a point-in-time Buy/Hold/Sell view as a *maximum exposure cap*.
- `tech_agent/fundamental_metrics.py`: fetches a Yahoo snapshot via Idaliia's module (best-effort, cached to `data_cache/fundamentals/`).
- `tech_agent/idaliia_bridge.py` (optional): runs Idaliia's memo generator as a subprocess.
- External package used:
  - `external/external_fundamental_analysis/fundamental_analyst_agent/` (this is the only Idaliia external component used).

## 7) Report generation
- `tech_agent/report_payload.py`: builds the JSON payload (`outputs/report_inputs.json`).
- `tech_agent/llm_provider.py`: generates the Markdown narrative via OpenAI (optional; gated by `--yes_openai`).
- `tech_agent/report_postprocess.py`: deterministic cleanup + ensures appendices exist and fixes common formatting drift.

## 8) Rendering
- `tech_agent/html_report.py`: renders the Markdown into HTML using `templates/report.html`.
PDF is produced by printing the generated HTML from a browser (Print → Save as PDF).

## 9) Outputs
- `outputs/NVDA_investment_report.md` (only when LLM is enabled)
- `outputs/NVDA_investment_report.html` (when `--export_html` is used; print this page to PDF in a browser)
- `outputs/report_inputs.json`
- Figures:
  - `outputs/main/*.png`
  - `outputs/appendix/*.png`
