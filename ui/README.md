# Hybrid Investment Analyst — Streamlit UI

Interactive dashboard that orchestrates both agents (Fundamental + Technical),
applies the dual-gate decision logic, and displays the full analysis in a single page.

## Quick Start

```bash
# From the project root
pip install -r requirements.txt        # core dependencies
pip install -r ui/requirements.txt     # streamlit + dotenv

streamlit run ui/app.py
```

Make sure `.env` exists in the project root with at least:

```
ALPHA_VANTAGE_API_KEY=your_key
OPENAI_API_KEY=your_key          # optional, for LLM-generated thesis
```

## How It Works

1. User enters a ticker in the sidebar and clicks **Run Analysis**.
2. `progress.py` runs the pipeline with animated steps:
   - Step 1 — Fundamental Agent (Alpha Vantage + Yahoo Finance data, DCF/Multiples/DDM valuation)
   - Step 2 — Gate 1 check (BUY recommendation + no critical risk flags)
   - Step 3 — Technical Agent (MA crossover backtest) — only if Gate 1 passes
   - Step 4 — Gate 2 check (bullish regime: Close > MA200)
   - Step 5 — Merge evidence, generate HTML/PDF reports
3. Results are displayed as a dashboard: hero banner, executive summary, gate status, investment thesis, fundamental section, technical section, download buttons, and methodology appendix.
4. The evidence JSON is saved to `hybrid_controller/outputs/` so previously analysed tickers can be loaded instantly from the sidebar cache.

## File Structure

```
ui/
├── app.py                  # Entry point — sidebar, routing, dashboard assembly
├── styles.py               # All CSS (dark theme, tables, cards, charts)
├── requirements.txt        # streamlit, python-dotenv
├── components/
│   ├── __init__.py         # Re-exports all render functions
│   ├── landing.py          # Landing page (before analysis)
│   ├── progress.py         # Animated step tracker + pipeline execution
│   ├── hero.py             # Recommendation banner (TRADE / WAIT / NO TRADE)
│   ├── executive.py        # 9 key metrics in 3 rows
│   ├── gates.py            # Gate 1 / Gate 2 / Final Action table
│   ├── thesis.py           # Investment Thesis (LLM-generated or fallback)
│   ├── fundamental.py      # Valuation, sensitivity, historical ratios, risk
│   ├── technical.py        # Backtest metrics, strategy charts, trade log
│   ├── downloads.py        # PDF / HTML download buttons
│   └── appendix.py         # Methodology (DCF params, multiples, strategy rules)
└── utils/
    ├── __init__.py
    ├── paths.py            # PROJECT_ROOT, OUTPUT_DIR, TECH_DIR resolution
    └── formatters.py       # fmt_pct, fmt_price, fmt_ratio, fmt_multiple, fmt_market_cap
```
## Key Design Decisions

- **No existing files modified** — the UI lives entirely in `ui/` and imports from the existing agents.
- **Single data source** — every component reads from the same `evidence` dict; no duplicate API calls.
- **Cached results** — the sidebar scans `hybrid_controller/outputs/` for previous analyses, enabling instant reload without re-running the pipeline.
- **LLM is optional** — the Investment Thesis uses GPT-4 if `OPENAI_API_KEY` is set; otherwise a template-based fallback generates the text.
