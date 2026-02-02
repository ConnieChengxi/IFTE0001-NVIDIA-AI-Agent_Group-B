# Fundamental Analyst Agent

Automated equity research tool that generates investment memos with BUY/HOLD/SELL recommendations.

## Setup

```bash
git clone <repository-url>
cd idaliia_fundamental
pip install -r requirements.txt
cp .env.example .env 
# Add your API keys to .env
python run_demo.py NVDA
```

**API Keys:**
- Alpha Vantage (required): https://www.alphavantage.co/support/#api-key
- OpenAI (optional): https://platform.openai.com/api-keys

## Architecture

```
├── config/settings.py           # All assumptions and thresholds
├── src/
│   ├── data_collection/
│   │   ├── alpha_vantage_client.py   # Financial statements
│   │   ├── yahoo_finance_client.py   # Forward estimates, risk-free rate
│   │   ├── peer_selector.py          # Comparable companies
│   │   └── cache_manager.py          # 24h cache
│   ├── analysis/
│   │   ├── company_classifier.py     # Growth/Balanced/Dividend/Cyclical
│   │   ├── financial_ratios.py       # 15 ratios + DuPont
│   │   ├── dcf_valuation.py          # Multi-stage DCF
│   │   ├── multiples_valuation.py    # PEG, P/B, EV/EBITDA
│   │   └── ddm_valuation.py          # Gordon Growth Model
│   ├── agent/
│   │   └── recommendation_engine.py  # Weighted fair value + risk gates
│   ├── reporting/
│   │   └── memo_generator.py         # HTML/PDF output + GPT narratives
│   └── utils/
│       └── helpers.py                # Shared utility functions
└── run_demo.py
```

## Company Classification

Companies are classified based on financial metrics:

| Type | Criteria |
|------|----------|
| Cyclical | Industry in cyclical list (oil, airlines, mining, etc.) |
| Dividend | Dividend yield ≥4% AND revenue growth <10% |
| Growth | Revenue growth ≥15% AND dividend yield <2% |
| Balanced | Default for all other companies |

## Valuation Methods

### 1. DCF (Discounted Cash Flow)

**Global Assumptions:**
- Risk-free rate: 10Y Treasury (dynamic) or 4.2% fallback
- Equity risk premium: 5.5%
- Terminal growth: 2.5%
- WACC range: 5% – 20%

**Model by Company Type:**

| Type | Model | Stage 1 | Stage 2 (Fade) | Growth Range | Growth Method |
|------|-------|---------|----------------|--------------|---------------|
| Growth | 3-stage | 5 years | 5 years → 8% | 2.5% – 60% | Weighted recent (70/30) |
| Balanced | 3-stage | 5 years | 3 years → 4% | 7.5% – 20% | Historical average |
| Dividend | 2-stage | 5 years | — | 2.5% – 10% | Conservative (25th percentile) |
| Cyclical | 2-stage | 5 years | — | 2.5% – 15% | Normalized (median-adjusted) |

### 2. Multiples (Comparable Company Analysis)

**Peer Selection (4-step priority):**
1. Main industry candidates first
2. Filter by market cap (0.05x – 7x) and PEG (0.3 – 5.0)
3. Add from related industries if < 3 peers
4. Relax filters if still insufficient
- Max 3 peers, sorted by market cap similarity

**Valuation Multiples:**
- PEG-adjusted P/E (primary) — fair P/E = peer avg PEG × company growth
  - Uses 5-year revenue CAGR for both company and peers (fallback to YoY if unavailable)
  - Company growth capped at 60% for PEG calculation
- P/B (Price to Book)
- EV/EBITDA (with 3-method fallback if EBITDA unavailable)

**EBITDA Fallback:**
1. Direct EBITDA from income statement
2. Operating Income + D&A
3. Net Income + Interest + Taxes + D&A

### 3. DDM (Dividend Discount Model)

Gordon Growth Model: `Fair Value = D₁ / (r - g)`

**Assumptions:**
- Minimum yield: 0.3%
- Minimum history: 3 years (uses up to 5 years for CAGR)
- Cost of equity: Risk-free + β × ERP
- Dividend growth: CAGR capped at -10% to +20%; if g ≥ r, then g = r - 2%

## Blended Fair Value

Weighted average based on company type:

| Type | DCF | Multiples | DDM |
|------|-----|-----------|-----|
| Growth | 70% | 30% | 0% |
| Balanced | 50% | 30% | 20% |
| Dividend | 30% | 20% | 50% |
| Cyclical | 30% | 60% | 10% |

## Scenario Analysis

DCF and DDM provide Bear/Base/Bull scenarios:

| Scenario | Growth Adjustment | Discount Rate Adjustment |
|----------|-------------------|--------------------------|
| Bear | × 0.75 | +1% |
| Base | × 1.00 | 0% |
| Bull | × 1.25 | −1% |

## Recommendation Logic

**Thresholds:**
- BUY: Upside ≥ +20%
- SELL: Downside ≤ -10%
- HOLD: Between -10% and +20%

**Risk Gates (downgrade BUY → HOLD if any triggered):**
- Interest coverage < 1.5x
- Current ratio < 0.8x
- Debt/Equity > 5.0x

## Financial Ratios

**Profitability:** Gross Margin, Operating Margin, Net Margin, ROE, ROA, ROIC

**Leverage:** Debt/Equity, Debt/Assets, Interest Coverage

**Liquidity:** Current Ratio, Quick Ratio

**DuPont Analysis:** ROE = Net Margin × Asset Turnover × Equity Multiplier

## Limitations

- DCF sensitive to growth assumptions
- No industry-specific metrics (ARR, NIM, etc.)
- Peer selection by market cap, not business model
- No adjustment for one-time items
- Alpha Vantage free tier: 25 requests/day
- Static beta from data provider, not calculated from historical returns
- No qualitative factors (management, competitive moat, ESG)
- No earnings quality assessment (accruals, cash conversion)

## Output

- HTML: `outputs/{TICKER}_Investment_Memo.html`
- PDF: `outputs/{TICKER}_Investment_Memo.pdf` (via Playwright)

---

**Author:** Idaliia Gafarova
**Project:** UCL MSc Banking and Digital finance 2025-2026
**Disclaimer:** Educational project. Not investment advice.
