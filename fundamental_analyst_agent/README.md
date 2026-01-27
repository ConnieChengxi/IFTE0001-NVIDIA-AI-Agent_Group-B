# Fundamental Analyst Agent

Automated equity research tool that generates investment memos for publicly traded companies.

UCL MSc Artificial Intelligence | 2025-2026

## Features

**Valuation**
- 3-stage DCF model (high growth → fade → terminal)
- Peer multiples analysis (P/E, EV/EBITDA, P/B)
- Dividend discount model (Gordon Growth)
- Blended target price weighted by company type

**Financial Analysis**
- 5-year ratio trends (profitability, leverage, liquidity)
- DuPont decomposition (ROE = Margin × Turnover × Leverage)
- Peer comparison with operating metrics differential

**Risk & Recommendation**
- Gate checks (interest coverage, current ratio, D/E)
- Risk severity scoring
- BUY/HOLD/SELL with 12-month target price

**Output**
- HTML investment memo (can be saved as PDF)

## Project Structure

```
├── config/settings.py              
├── src/
│   ├── data_collection/
│   │   ├── alpha_vantage_client.py 
│   │   ├── yahoo_finance_client.py 
│   │   └── cache_manager.py        
│   ├── analysis/
│   │   ├── financial_ratios.py     
│   │   ├── dcf_valuation.py        
│   │   ├── multiples_valuation.py  
│   │   ├── ddm_valuation.py        
│   │   ├── peer_selector.py        
│   │   └── company_classifier.py   
│   ├── agent/
│   │   └── recommendation_engine.py
│   └── reporting/
│       └── memo_generator.py       
├── run_analysis.py                 
├── cache/                          
└── outputs/                        
```

## API Keys

Alpha Vantage — financial statements (free tier: 25 req/day)
OpenAI — report narratives (pay-per-use)

## Valuation Weights

Growth — DCF 70%, Multiples 30%, DDM 0%
Balanced — DCF 50%, Multiples 30%, DDM 20%
Dividend — DCF 30%, Multiples 20%, DDM 50%
Cyclical — DCF 30%, Multiples 60%, DDM 10%

## Key Assumptions

Terminal growth rate: 2.5% (all companies)
Equity risk premium: 5.5%
Risk-free rate: 10Y Treasury yield (fetched dynamically)
Peer market cap ratio: 0.05x – 7x of target company
Valid P/E range: -100 to 300

## Limitations

DCF output is sensitive to growth assumptions
Peer selection is automated based on market cap, not business model
No adjustment for one-time items or extraordinary events
No industry-specific metrics (SaaS: ARR/NRR, banks: NIM/NPL)
Data quality depends on Alpha Vantage coverage
Alpha Vantage free tier: 25 requests/day

## Disclaimer

Educational project. Not investment advice.

## Author

Idaliia Gafarova