"""
Investment Memo Generator
Professional HTML-based investment memo with LLM-generated narratives.
Pure HTML tables (no divs), professional equity research style.
"""

from typing import Dict, List, Optional
from datetime import datetime
from config.settings import OPENAI_API_KEY, LLM_MODEL, LLM_TEMPERATURE


class MemoGenerator:
    
    def __init__(self, ticker: str, company_data: Dict, ratios: Dict, classification: Dict,
                 dcf_result: Dict, multiples_result: Dict, ddm_result: Dict,
                 recommendation: Dict, peer_tickers: List[str], 
                 forward_estimates: Dict = None):
        
        self.ticker = ticker
        self.company_data = company_data
        self.ratios = ratios
        self.classification = classification
        self.dcf_result = dcf_result
        self.multiples_result = multiples_result
        self.ddm_result = ddm_result
        self.recommendation = recommendation
        self.peer_tickers = peer_tickers
        self.forward_estimates = forward_estimates or {}
        
        self.overview = company_data.get('overview', {})
        self.income = company_data.get('income', [])
        self.balance = company_data.get('balance', [])
        self.cashflow = company_data.get('cashflow', [])
        
        # IMPORTANT: Disable external LLM calls inside the Idaliia module.
        # This project generates the narrative separately (OpenAI is used by our own report pipeline).
        # Keeping this deterministic avoids unexpected costs and makes the fundamental memo reproducible.
        self.client = None
    
    # ========================================
    # FORMATTING HELPERS
    # ========================================
    
    def _safe(self, val, default=0.0):
        """Safely convert to float."""
        if val is None or val == "N/A":
            return default
        try:
            return float(val)
        except:
            return default
    
    def _price(self, val):
        """Format as price: $123.45"""
        v = self._safe(val)
        return f"${v:,.2f}" if v != 0 else "N/A"
    
    def _pct(self, val):
        """Format as percentage: 12.5%"""
        v = self._safe(val)
        if v == 0 and val not in [0, 0.0]:
            return "N/A"
        return f"{v * 100:.1f}%"
    
    def _mult(self, val):
        """Format as multiple: 25.5x"""
        v = self._safe(val)
        return f"{v:.1f}x" if v != 0 else "N/A"
    
    def _num(self, val):
        """Format large numbers: $1.5B"""
        v = self._safe(val)
        if v == 0:
            return "N/A"
        if v >= 1e12:
            return f"${v/1e12:.1f}T"
        elif v >= 1e9:
            return f"${v/1e9:.1f}B"
        elif v >= 1e6:
            return f"${v/1e6:.0f}M"
        return f"${v:,.0f}"
    
    # ========================================
    # LLM CALLS
    # ========================================
    
    def _llm(self, prompt: str, max_tokens: int = 500) -> str:
        """Call LLM with system prompt."""
        return "[LLM narrative omitted in this run (disabled for reproducibility).]"
    
    # ========================================
    # CSS STYLING
    # ========================================
    
    def _css(self) -> str:
        """Professional CSS styles for investment memo."""
        return """
        <style>
            @page { margin: 1cm; }
            body {
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
                font-size: 10pt;
                line-height: 1.4;
                color: #1f2937;
                margin: 20px;
                max-width: 1000px;
            }
            h1 {
                font-size: 20pt;
                font-weight: 700;
                color: #1e3a8a;
                margin-bottom: 5px;
                border-bottom: 3px solid #1e3a8a;
                padding-bottom: 10px;
            }
            h2 {
                font-size: 14pt;
                font-weight: 700;
                color: #1e3a8a;
                border-bottom: 2px solid #3b82f6;
                padding-bottom: 5px;
                margin-top: 30px;
                margin-bottom: 15px;
            }
            h3 {
                font-size: 11pt;
                font-weight: 600;
                color: #374151;
                margin: 20px 0 10px 0;
                text-transform: uppercase;
                letter-spacing: 0.5px;
            }
            h4 {
                font-size: 10pt;
                font-weight: 600;
                color: #4b5563;
                margin: 15px 0 8px 0;
            }
            p {
                margin: 8px 0;
                text-align: justify;
                line-height: 1.6;
            }
            table {
                width: 100%;
                border-collapse: collapse;
                margin: 12px 0;
                font-size: 9pt;
            }
            th {
                background: #f3f4f6;
                padding: 8px 10px;
                text-align: left;
                font-weight: 600;
                color: #374151;
                border-bottom: 2px solid #d1d5db;
                font-size: 8pt;
                text-transform: uppercase;
                letter-spacing: 0.3px;
            }
            td {
                padding: 6px 10px;
                border-bottom: 1px solid #f3f4f6;
            }
            .text-right { text-align: right; }
            .text-center { text-align: center; }
            .highlight-row {
                background: #fef3c7;
                font-weight: 600;
            }
            .company-row {
                background: #dbeafe;
                font-weight: 700;
            }
            .section-header {
                background: #e0e7ff;
                font-weight: 700;
                text-transform: uppercase;
                font-size: 8pt;
                letter-spacing: 0.5px;
            }
            .positive { color: #10b981; font-weight: 600; }
            .negative { color: #ef4444; font-weight: 600; }
            .neutral { color: #6b7280; }
            
            .rec-box {
                padding: 20px;
                margin: 20px 0;
                border-radius: 4px;
                text-align: center;
            }
            .rec-buy {
                background: #f0fdf4;
                border: 3px solid #10b981;
                color: #065f46;
            }
            .rec-hold {
                background: #fffbeb;
                border: 3px solid #f59e0b;
                color: #92400e;
            }
            .rec-sell {
                background: #fef2f2;
                border: 3px solid #ef4444;
                color: #991b1b;
            }
            .rec-title {
                font-size: 16pt;
                font-weight: 700;
                margin-bottom: 15px;
            }
            .rec-metrics {
                display: flex;
                justify-content: space-around;
                margin-top: 10px;
            }
            .rec-metric {
                text-align: center;
            }
            .rec-metric-label {
                font-size: 8pt;
                color: #6b7280;
                margin-bottom: 5px;
            }
            .rec-metric-value {
                font-size: 16pt;
                font-weight: 700;
            }
            
            .valuation-box {
                padding: 12px;
                margin: 15px 0;
                border-radius: 4px;
                border-left: 4px solid;
            }
            .valuation-undervalued {
                background: #f0fdf4;
                border-color: #10b981;
            }
            .valuation-fair {
                background: #eff6ff;
                border-color: #3b82f6;
            }
            .valuation-overvalued {
                background: #fef2f2;
                border-color: #ef4444;
            }
            
            .benchmark {
                font-size: 8pt;
                color: #6b7280;
                font-style: italic;
                margin-top: 5px;
            }
            
            .risk-high { color: #ef4444; font-weight: 600; }
            .risk-medium { color: #f59e0b; font-weight: 600; }
            .risk-low { color: #10b981; font-weight: 600; }
            
            ul {
                margin: 8px 0;
                padding-left: 25px;
            }
            li {
                margin: 4px 0;
            }
            
            pre {
                background: #f9fafb;
                padding: 10px;
                border-left: 3px solid #d1d5db;
                font-size: 8pt;
                overflow-x: auto;
            }

            .rating-strong {
                background-color: #10b981;
                color: white;
                padding: 2px 8px;
                border-radius: 3px;
                font-size: 0.85em;
                font-weight: 600;
            }

            .rating-acceptable {
                background-color: #f59e0b;
                color: white;
                padding: 2px 8px;
                border-radius: 3px;
                font-size: 0.85em;
                font-weight: 600;
            }

            .rating-weak {
                background-color: #ef4444;
                color: white;
                padding: 2px 8px;
                border-radius: 3px;
                font-size: 0.85em;
                font-weight: 600;
            }

            /* ========================================
               PRINT STYLES - Better PDF Output
               ======================================== */
            @media print {
                body {
                    margin: 0;
                    padding: 15px;
                    font-size: 9pt;
                    -webkit-print-color-adjust: exact !important;
                    print-color-adjust: exact !important;
                }
                
                /* Preserve table styling */
                table {
                    width: 100% !important;
                    border-collapse: collapse !important;
                    page-break-inside: avoid;
                }
                
                th {
                    background-color: #f3f4f6 !important;
                    -webkit-print-color-adjust: exact !important;
                    print-color-adjust: exact !important;
                }
                
                tr {
                    page-break-inside: avoid;
                }
                
                /* Preserve colored backgrounds */
                .rec-buy, .rec-hold, .rec-sell {
                    -webkit-print-color-adjust: exact !important;
                    print-color-adjust: exact !important;
                }
                
                .rating-strong, .rating-acceptable, .rating-weak {
                    -webkit-print-color-adjust: exact !important;
                    print-color-adjust: exact !important;
                }
                
                .positive, .negative {
                    -webkit-print-color-adjust: exact !important;
                    print-color-adjust: exact !important;
                }
                
                /* Section headers - keep with content */
                h2, h3 {
                    page-break-after: avoid;
                }
                
                /* Valuation box */
                .valuation-box {
                    -webkit-print-color-adjust: exact !important;
                    print-color-adjust: exact !important;
                    border-left: 4px solid !important;
                }
                
                .valuation-undervalued {
                    background-color: #f0fdf4 !important;
                    border-color: #10b981 !important;
                }
                
                .valuation-fair {
                    background-color: #eff6ff !important;
                    border-color: #3b82f6 !important;
                }
                
                .valuation-overvalued {
                    background-color: #fef2f2 !important;
                    border-color: #ef4444 !important;
                }
                
                /* Highlighted rows */
                tr[style*="background-color"] {
                    -webkit-print-color-adjust: exact !important;
                    print-color-adjust: exact !important;
                }
                
                /* Page breaks */
                .page-break {
                    page-break-before: always;
                }
                
                /* Hide non-essential elements */
                .no-print {
                    display: none !important;
                }
            }
        </style>
        """
    
    # ========================================
    # HISTORICAL DATA CALCULATION
    # ========================================
    
    def _get_historical_ratios(self) -> List[Dict]:
        """
        Calculate historical financial ratios for last 5 years.
        Returns list of dicts with year and ratio values.
        """
        historical = []
        
        # Get up to 5 years of data
        num_years = min(5, len(self.income), len(self.balance))
        
        for i in range(num_years):
            year_data = {}
            
            # Get fiscal year
            fiscal_date = self.income[i].get('fiscal_date_ending') or self.income[i].get('fiscaldateending')
            if fiscal_date:
                try:
                    year_data['year'] = fiscal_date[:4]
                except:
                    year_data['year'] = f'Y-{i}'
            else:
                year_data['year'] = f'Y-{i}'
            
            # Revenue and costs
            revenue = self._safe(self.income[i].get('revenue'))
            cogs = self._safe(self.income[i].get('cost_of_revenue'))
            operating_income = self._safe(self.income[i].get('operating_income'))
            net_income = self._safe(self.income[i].get('net_income'))
            
            # Balance sheet
            total_assets = self._safe(self.balance[i].get('total_assets'))
            total_equity = self._safe(self.balance[i].get('total_shareholder_equity'))
            current_assets = self._safe(self.balance[i].get('current_assets'))
            current_liabilities = self._safe(self.balance[i].get('current_liabilities'))
            inventory = self._safe(self.balance[i].get('inventory'))
            long_term_debt = self._safe(self.balance[i].get('long_term_debt'))
            short_term_debt = self._safe(self.balance[i].get('short_term_debt'))
            
            # Interest expense
            interest_expense = self._safe(self.income[i].get('interest_expense'))
            
            # Calculate ratios
            # Profitability
            year_data['gross_margin'] = (revenue - cogs) / revenue if revenue > 0 else None
            year_data['operating_margin'] = operating_income / revenue if revenue > 0 else None
            year_data['net_margin'] = net_income / revenue if revenue > 0 else None
            year_data['roe'] = net_income / total_equity if total_equity > 0 else None
            year_data['roa'] = net_income / total_assets if total_assets > 0 else None
            
            # Leverage (must be before ROIC!)
            total_debt = long_term_debt + short_term_debt
            year_data['debt_to_assets'] = total_debt / total_assets if total_assets > 0 else None
            year_data['debt_to_equity'] = total_debt / total_equity if total_equity > 0 else None
            year_data['interest_coverage'] = operating_income / interest_expense if interest_expense > 0 else None
            
            # ROIC calculation (after total_debt is defined)
            tax_expense = self._safe(self.income[i].get('income_tax_expense'))
            cash = self._safe(self.balance[i].get('cash'))
            
            if net_income and tax_expense and (net_income + tax_expense) != 0:
                tax_rate = tax_expense / (net_income + tax_expense)
                tax_rate = max(0, min(tax_rate, 0.50))
            else:
                tax_rate = 0.21
            
            if operating_income:
                nopat = operating_income * (1 - tax_rate)
                invested_capital = total_equity + total_debt - cash if (total_equity + total_debt - cash) > 0 else None
                year_data['roic'] = nopat / invested_capital if invested_capital and invested_capital > 0 else None
            else:
                year_data['roic'] = None
            
            # Liquidity
            year_data['current_ratio'] = current_assets / current_liabilities if current_liabilities > 0 else None
            year_data['quick_ratio'] = (current_assets - inventory) / current_liabilities if current_liabilities > 0 else None
            
            historical.append(year_data)
        
        # Reverse to show oldest → newest
        historical.reverse()
        
        return historical
    
    def _rate_gate_check_metric(self, metric_key: str, value: float) -> str:
        """
        Rate financial metrics.
        Returns: Strong, Acceptable, or Weak
        """
        if value is None or value == 'N/A':
            return 'N/A'
        
        try:
            val = float(value)
        except:
            return 'N/A'
        
        # === PROFITABILITY METRICS ===
        if metric_key == 'gross_margin':
            if val >= 0.50:
                return 'Strong'
            elif val >= 0.30:
                return 'Acceptable'
            else:
                return 'Weak'
        
        elif metric_key == 'operating_margin':
            if val >= 0.20:
                return 'Strong'
            elif val >= 0.10:
                return 'Acceptable'
            else:
                return 'Weak'
        
        elif metric_key == 'net_margin':
            if val >= 0.15:
                return 'Strong'
            elif val >= 0.05:
                return 'Acceptable'
            else:
                return 'Weak'
        
        elif metric_key == 'roe':
            if val >= 0.20:
                return 'Strong'
            elif val >= 0.10:
                return 'Acceptable'
            else:
                return 'Weak'
        
        elif metric_key == 'roa':
            if val >= 0.10:
                return 'Strong'
            elif val >= 0.05:
                return 'Acceptable'
            else:
                return 'Weak'
        
        elif metric_key == 'roic':
            if val >= 0.15:
                return 'Strong'
            elif val >= 0.08:
                return 'Acceptable'
            else:
                return 'Weak'
        
        # === LEVERAGE METRICS (lower is better) ===
        elif metric_key == 'debt_to_assets':
            if val <= 0.30:
                return 'Strong'
            elif val <= 0.50:
                return 'Acceptable'
            else:
                return 'Weak'
        
        elif metric_key == 'debt_to_equity':
            if val <= 0.50:
                return 'Strong'
            elif val <= 1.00:
                return 'Acceptable'
            else:
                return 'Weak'
        
        elif metric_key == 'interest_coverage':
            if val >= 5.0:
                return 'Strong'
            elif val >= 2.5:
                return 'Acceptable'
            else:
                return 'Weak'
        
        # === LIQUIDITY METRICS ===
        elif metric_key == 'current_ratio':
            if val >= 2.0:
                return 'Strong'
            elif val >= 1.5:
                return 'Acceptable'
            else:
                return 'Weak'
        
        elif metric_key == 'quick_ratio':
            if val >= 1.5:
                return 'Strong'
            elif val >= 1.0:
                return 'Acceptable'
            else:
                return 'Weak'
        
        return 'N/A'
    
    def _financial_health_table(self) -> str:
        """
        Generate Financial Health Assessment table.
        Rates profitability, leverage, and liquidity.
        """
        # Get current ratios
        gross_margin = self.ratios.get('gross_margin', 0)
        net_margin = self.ratios.get('net_margin', 0)
        roe = self.ratios.get('roe', 0)
        roa = self.ratios.get('roa', 0)
        
        debt_to_equity = self.ratios.get('debt_to_equity', 0)
        debt_to_assets = self.ratios.get('debt_to_assets', 0)
        interest_coverage = self.ratios.get('interest_coverage')
        
        current_ratio = self.ratios.get('current_ratio')
        quick_ratio = self.ratios.get('quick_ratio')
        
        # Rate categories
        def rate_profitability():
            """Rate overall profitability."""
            score = 0
            if gross_margin and gross_margin > 0.40: score += 1
            if net_margin and net_margin > 0.10: score += 1
            if roe and roe > 0.15: score += 1
            if roa and roa > 0.10: score += 1
            
            if score >= 3:
                return "Strong"
            elif score >= 2:
                return "Acceptable"
            else:
                return "Weak"
        
        def rate_leverage():
            """Rate financial leverage/risk."""
            if debt_to_equity is None or debt_to_equity == 0:
                return "Conservative"
            
            if debt_to_equity < 0.5:
                return "Conservative"
            elif debt_to_equity < 1.0:
                return "Moderate"
            elif debt_to_equity < 2.0:
                return "Elevated"
            else:
                return "High"
        
        def rate_liquidity():
            """Rate liquidity position."""
            if not current_ratio or current_ratio < 1.0:
                return "Weak"
            elif current_ratio < 1.5:
                return "Adequate"
            else:
                return "Strong"
        
        profitability_rating = rate_profitability()
        leverage_rating = rate_leverage()
        liquidity_rating = rate_liquidity()
        
        html = f'''
            <h3>FINANCIAL HEALTH ASSESSMENT</h3>
            
            <table>
                <thead>
                    <tr>
                        <th style="text-align: left;">CATEGORY</th>
                        <th>RATING</th>
                    </tr>
                </thead>
                <tbody>
                    <tr>
                        <td>Profitability</td>
                        <td><strong>{profitability_rating}</strong></td>
                    </tr>
                    <tr>
                        <td>Leverage</td>
                        <td><strong>{leverage_rating}</strong></td>
                    </tr>
                    <tr>
                        <td>Liquidity</td>
                        <td><strong>{liquidity_rating}</strong></td>
                    </tr>
                </tbody>
            </table>
        '''
        
        return html

    def _generate_financial_narrative(self) -> str:
        """
        Generate LLM narrative for Financial Analysis.
        100-120 words analyzing financial health.
        """
        if not self.client:
            return "Financial analysis unavailable (LLM API key not configured)."
        
        # Get key metrics
        gross_margin = self.ratios.get('gross_margin', 0)
        net_margin = self.ratios.get('net_margin', 0)
        roe = self.ratios.get('roe', 0)
        roa = self.ratios.get('roa', 0)
        
        debt_to_equity = self.ratios.get('debt_to_equity', 0)
        debt_to_assets = self.ratios.get('debt_to_assets', 0)
        interest_coverage = self.ratios.get('interest_coverage')
        
        current_ratio = self.ratios.get('current_ratio')
        quick_ratio = self.ratios.get('quick_ratio')
        
        revenue_growth = self.ratios.get('revenue_growth', 0)
        
        prompt = f"""Write a financial health assessment (100-120 words, single paragraph) for {self.ticker}.

Data:
Profitability:
- Gross Margin: {self._pct(gross_margin)}
- Net Margin: {self._pct(net_margin)}
- ROE: {self._pct(roe)}
- ROA: {self._pct(roa)}

Leverage:
- Debt/Equity: {self._mult(debt_to_equity) if debt_to_equity else 'N/A'}
- Debt/Assets: {self._mult(debt_to_assets) if debt_to_assets else 'N/A'}
- Interest Coverage: {self._mult(interest_coverage) if interest_coverage else 'N/A'}

Liquidity:
- Current Ratio: {self._mult(current_ratio) if current_ratio else 'N/A'}
- Quick Ratio: {self._mult(quick_ratio) if quick_ratio else 'N/A'}

Growth:
- Revenue Growth: {self._pct(revenue_growth)}

Instructions:
Write ONE paragraph covering:
1. Profitability assessment (margins, returns)
2. Leverage/financial risk position
3. Liquidity position
4. Overall financial health characterization

Use specific numbers. Third-person, professional tone.
Format: Plain text paragraph only."""
        
        return self._llm(prompt, max_tokens=250)
        
    def _calculate_trend(self, values: List[float], metric_type: str = 'higher_better') -> str:
        """Calculate trend from historical values."""
        if not values or len(values) < 2:
            return "—"
        
        first = next((v for v in values if v != 0), 0)
        last = next((v for v in reversed(values) if v != 0), 0)
        
        if first == 0 or last == 0:
            return "—"
        
        # For debt ratios, LOWER is better
        if metric_type == 'lower_better':
            if first > last * 1.1:
                return "Improving"
            elif first < last * 0.9:
                return "Declining"
        # For most metrics, HIGHER is better
        else:
            if last > first * 1.1:
                return "Improving"
            elif last < first * 0.9:
                return "Declining"
        
        return "Stable"
    
    # ========================================
    # PAGE 1: EXECUTIVE SUMMARY
    # ========================================
    
    def _page1_executive_summary(self) -> str:
        """Generate Page 1: Executive Summary."""
        
        company_name = self.overview.get('name', self.ticker)
        rec = self.recommendation['recommendation']
        current = self._safe(self.recommendation['current_price'])
        target = self._safe(self.recommendation['fair_value'])
        upside = self._safe(self.recommendation['upside_downside'])
        
        pe = self._safe(self.overview.get('pe_ratio'))
        forward_pe = self._safe(self.forward_estimates.get('forward_pe'))
        margin = self._safe(self.ratios.get('net_margin'))
        growth = self._safe(self.ratios.get('revenue_growth'))
        roe = self._safe(self.ratios.get('roe'))
        
        # Investment Snapshot Table
        snapshot = f"""
        <h3>Investment Snapshot</h3>
        <table>
            <thead>
                <tr><th>Metric</th><th class="text-right">Value</th></tr>
            </thead>
            <tbody>
                <tr><td>Recommendation</td><td class="text-right"><strong>{rec}</strong></td></tr>
                <tr><td>Current Price</td><td class="text-right">{self._price(current)}</td></tr>
                <tr><td>Target Price</td><td class="text-right">{self._price(target)}</td></tr>
                <tr><td>Upside/Downside</td><td class="text-right {'positive' if upside > 0 else 'negative'}">{self._pct(upside)}</td></tr>
            </tbody>
        </table>
        """
        
        # Key Metrics Table - use Forward P/E if available, else Trailing P/E
        pe_label = "Forward P/E" if forward_pe else "P/E Ratio"
        pe_value = forward_pe if forward_pe else pe
        
        key_metrics = f"""
        <h3>Key Metrics</h3>
        <table>
            <thead>
                <tr><th>Metric</th><th class="text-right">Value</th></tr>
            </thead>
            <tbody>
                <tr><td>{pe_label}</td><td class="text-right">{self._mult(pe_value)}</td></tr>
                <tr><td>Profit Margin</td><td class="text-right">{self._pct(margin)}</td></tr>
                <tr><td>Revenue Growth</td><td class="text-right">{self._pct(growth)}</td></tr>
                <tr><td>ROE</td><td class="text-right">{self._pct(roe)}</td></tr>
            </tbody>
        </table>
        """
        
        # LLM: Investment Thesis
        company_type = self.classification['company_type']
        upside_term = "upside" if upside > 0 else "downside"
        
        # Use Forward P/E in prompt if available
        pe_for_prompt = f"Forward P/E: {self._mult(forward_pe)}" if forward_pe else f"P/E: {self._mult(pe)}"
        
        prompt = f"""Write a concise investment thesis (150-200 words, 2 paragraphs) for {company_name} ({self.ticker}).

Data:
- Recommendation: {rec}
- Target Price: {self._price(target)} vs Current: {self._price(current)} ({self._pct(upside)} potential)
- Company Type: {company_type}
- Key Metrics:
  * Revenue Growth: {self._pct(growth)}
  * Net Margin: {self._pct(margin)}
  * ROE: {self._pct(roe)}
  * {pe_for_prompt}

Structure:
Paragraph 1: Open with "{company_name} is rated {rec} with a 12-month target of {self._price(target)} (vs {self._price(current)} current; {self._pct(upside)} {upside_term})." Then state the core investment thesis in 2-3 sentences covering: (1) valuation view relative to fundamentals, (2) primary opportunity/catalyst.

Paragraph 2: Describe the key risk or consideration that could impact the thesis (1-2 sentences). Close with a decisive statement on why the {rec} rating is appropriate.

Tone: Professional, third-person, data-driven. NO "we/our". Use: "The analysis indicates...", "{self.ticker} exhibits...", "The stock trades at..."
Format: Plain text paragraphs only. No headers, no bullet points."""

        thesis = self._llm(prompt, max_tokens=300)
        
        if len(thesis) < 50:
            thesis = f"{company_name} is rated {rec} with a 12-month target of {self._price(target)} (vs {self._price(current)} current; {self._pct(upside)} {upside_term}). The stock appears {'undervalued' if upside > 0 else 'overvalued'} relative to fundamentals based on the {company_type}-weighted valuation analysis."
        
        thesis_section = f"<h3>Investment Thesis</h3><p>{thesis}</p>"
        
        return snapshot + key_metrics + thesis_section
    
    # ========================================
    # PAGE 2: COMPANY OVERVIEW
    # ========================================
    
    def _page2_company_overview(self) -> str:
        """Generate Page 2: Company Overview."""
        
        company_name = self.overview.get('name', self.ticker)
        sector = self.overview.get('sector', 'N/A')
        industry = self.overview.get('industry', 'N/A')
        market_cap = self._safe(self.overview.get('market_cap'))
        country = self.overview.get('country', 'United States')
        exchange = self.overview.get('exchange', 'NASDAQ')
        
        # Introduction paragraph (template-based)
        intro = f"<p>{company_name} ({self.ticker}) is a {country}-based company in the {industry} industry within the {sector} sector, listed on {exchange} with a market capitalization of approximately {self._num(market_cap)}.</p>"
        
        # LLM: Business Description
        prompt = f"""Write a business description (120-150 words, 3-4 sentences) for {company_name} ({self.ticker}) in the {industry} industry.

Cover in separate sentences:
1. Core business model and primary revenue streams
2. Key products or service offerings (name 2-3 specific products/platforms)
3. Competitive positioning and core competitive advantages (moat)
4. Geographic footprint (headquarters location and key markets)

Tone: Professional, factual, third-person. NO marketing language.
Format: Plain text sentences. No bullet points, no headers.
Example opening: "{company_name} operates as a {industry} company, generating revenue primarily through..."

Write ONLY the description. No preamble."""

        content = self._llm(prompt, max_tokens=400)
        
        if len(content) < 100 or not content.startswith(company_name):
            content = f"{company_name} operates in the {industry} industry, providing products and services to customers globally. The company maintains operations across multiple geographic markets with headquarters in {country}."
        
        return intro + f"<p>{content}</p>"
    
    # ========================================
    # PAGE 3: FINANCIAL ANALYSIS
    # ========================================

    def _page3_financial_analysis(self) -> str:
        """
        Page 3: Financial Analysis
        - Historical ratios table (5 years, NO TREND column)
        - Financial Health Assessment
        - LLM narrative
        """
        html = '''
        <h2>3. Financial Analysis</h2>
        
        <h3>FINANCIAL RATIOS</h3>
        
        <table>
            <thead>
                <tr>
                    <th style="text-align: left;">METRIC</th>
                    <th>2021</th>
                    <th>2022</th>
                    <th>2023</th>
                    <th>2024</th>
                    <th>2025</th>
                    <th>RATING</th>
                </tr>
            </thead>
            <tbody>
        '''
        
        # Get historical data
        historical = self._get_historical_ratios()
        
        # Ensure we have 5 years (pad with empty if needed)
        while len(historical) < 5:
            historical.insert(0, {'year': '—'})
        
        # Take last 5 years
        historical = historical[-5:]
        
        # Define metrics to display
        metrics = [
            ('PROFITABILITY', [
                ('Gross Margin', 'gross_margin', True),
                ('Operating Margin', 'operating_margin', True),
                ('Net Profit Margin', 'net_margin', True),
                ('ROE', 'roe', True),
                ('ROA', 'roa', True),
                ('ROIC', 'roic', True),
            ]),
            ('LEVERAGE', [
                ('Debt/Assets', 'debt_to_assets', True),
                ('Debt/Equity', 'debt_to_equity', True),
                ('Interest Coverage', 'interest_coverage', True),
            ]),
            ('LIQUIDITY', [
                ('Current Ratio', 'current_ratio', True),
                ('Quick Ratio', 'quick_ratio', True),
            ]),
        ]
        
        for section_name, section_metrics in metrics:
            html += f'''
                    <tr class="section-header">
                        <td colspan="7"><strong>{section_name}</strong></td>
                    </tr>
            '''
            
            for metric_name, metric_key, show_rating in section_metrics:
                html += f'<tr><td>{metric_name}</td>'
                
                # 5 years of data
                for year_data in historical:
                    val = year_data.get(metric_key)
                    if val is None:
                        html += '<td>N/A</td>'
                    elif metric_key in ['gross_margin', 'operating_margin', 'net_margin', 'roe', 'roa', 'roic']:
                        html += f'<td>{self._pct(val)}</td>'  # ← FIXED!
                    elif metric_key in ['current_ratio', 'quick_ratio', 'interest_coverage', 'debt_to_assets', 'debt_to_equity']:
                        html += f'<td>{self._mult(val)}</td>'  # ← FIXED!
                    else:
                        html += f'<td>{val}</td>'
                
                # Rating column (only for gate check metrics)
                if show_rating:
                    current_val = self.ratios.get(metric_key)
                    rating = self._rate_gate_check_metric(metric_key, current_val)
                    html += f'<td><span class="rating-{rating.lower()}">{rating}</span></td>'
                else:
                    html += '<td>—</td>'
                
                html += '</tr>'
        
        html += '''
                </tbody>
            </table>
        '''
        
        # Financial Health Assessment table
        html += self._financial_health_table()
        
        # LLM narrative
        narrative = self._generate_financial_narrative()
        html += f'''
            <p style="text-align: justify; line-height: 1.6;">
                {narrative}
            </p>
        '''
        
        return html
  # ========================================
    # PAGE 4: VALUATION
    # ========================================

    def _page4_valuation(self) -> str:
        """
        Page 4: Valuation (restructured)
        - 4.1 Intrinsic Value Summary + LLM interpretation
        - 4.2 Key Valuation Assumptions
        """
        
        # Get data - use _safe() to handle None values
        current_price = self._safe(self.recommendation.get('current_price'), 100.0)
        fair_value = self._safe(self.recommendation.get('fair_value'))
        upside = self._safe(self.recommendation.get('upside_downside'))
        weights = self.recommendation.get('weights', {
            'dcf': 0.45,
            'multiples': 0.35,
            'ddm': 0.20
        })
        
        company_type = self.classification.get('company_type', 'balanced').title()
        
        # DCF values
        dcf_value = self._safe(self.dcf_result.get('fair_value_per_share'))
        dcf_vs_current = ((dcf_value / current_price) - 1) if dcf_value and current_price else None
        
        # Multiples values
        mult_value = self._safe(self.multiples_result.get('average_fair_value'))
        mult_vs_current = ((mult_value / current_price) - 1) if mult_value and current_price else None
        
        # DDM values
        ddm_applicable = self.ddm_result.get('applicable', False)
        ddm_value = self.ddm_result.get('fair_value_per_share') if ddm_applicable else None
        ddm_vs_current = ((ddm_value / current_price) - 1) if ddm_value and current_price else None
        
        html = f'''
            <h2>4. Valuation</h2>
            
            <h3>4.1 INTRINSIC VALUE SUMMARY</h3>
            
            <p><strong>Company Type:</strong> {company_type}</p>
            
            <table>
                <thead>
                    <tr>
                        <th style="text-align: left;">METHOD</th>
                        <th>FAIR VALUE</th>
                        <th>VS CURRENT (${current_price:.2f})</th>
                        <th>WEIGHT</th>
                    </tr>
                </thead>
                <tbody>
                    <tr>
                        <td>DCF</td>
                        <td>{self._price(dcf_value) if dcf_value else 'N/A'}</td>
                        <td class="{'positive' if dcf_vs_current and dcf_vs_current > 0 else 'negative'}">
                            {self._pct(dcf_vs_current) if dcf_vs_current is not None else 'N/A'}
                        </td>
                        <td>{weights['dcf']*100:.1f}%</td>
                    </tr>
                    <tr>
                        <td>Multiples</td>
                        <td>{self._price(mult_value) if mult_value else 'N/A'}</td>
                        <td class="{'positive' if mult_vs_current and mult_vs_current > 0 else 'negative'}">
                            {self._pct(mult_vs_current) if mult_vs_current is not None else 'N/A'}
                        </td>
                        <td>{weights['multiples']*100:.1f}%</td>
                    </tr>
        '''
        
        # Conditionally show DDM row
        if weights.get('ddm', 0) > 0:
            html += f'''
                    <tr>
                        <td>DDM</td>
                        <td>{self._price(ddm_value) if ddm_value else 'N/A'}</td>
                        <td class="{'positive' if ddm_vs_current and ddm_vs_current > 0 else 'negative'}">
                            {self._pct(ddm_vs_current) if ddm_vs_current is not None else 'N/A'}
                        </td>
                        <td>{weights['ddm']*100:.1f}%</td>
                    </tr>
            '''
        
        # Target Price row (highlighted)
        html += f'''
                    <tr style="background-color: #fef3c7; font-weight: 600;">
                        <td>Target Price</td>
                        <td>{self._price(fair_value) if fair_value else 'N/A'}</td>
                        <td class="{'positive' if upside > 0 else 'negative'}">
                            {self._pct(upside)}
                        </td>
                        <td>100%</td>
                    </tr>
                </tbody>
            </table>
        '''
        
        # Valuation conclusion box
        if fair_value and upside is not None:
            upside_pct = upside * 100
            if upside > 0.20:
                conclusion = "Undervalued"
                color = "#d1fae5"
                text_color = "#065f46"
                explanation = f"Trading below intrinsic value with {upside_pct:+.1f}% to target price."
            elif upside < -0.10:
                conclusion = "Overvalued"
                color = "#fee2e2"
                text_color = "#991b1b"
                explanation = f"Current price stretched relative to fundamentals ({upside_pct:.1f}% to target)."
            else:
                conclusion = "Fairly Valued"
                color = "#fef3c7"
                text_color = "#92400e"
                explanation = f"Trading near intrinsic value with {upside_pct:.1f}% to target price."
            
            html += f'''
            <div style="background-color: {color}; border-left: 4px solid {text_color}; padding: 1em; margin: 1em 0;">
                <p style="margin: 0; color: {text_color}; font-weight: 600;">
                    <strong>{conclusion}:</strong> {explanation}
                </p>
            </div>
            '''
        
        # LLM Valuation Interpretation
        valuation_narrative = self._generate_valuation_narrative()
        html += f'''
            <p style="text-align: justify; line-height: 1.6; margin-top: 1.5em;">
                <strong>💡 Valuation Interpretation</strong><br><br>
                {valuation_narrative}
            </p>
            
            <h3 style="margin-top: 2em;">4.2 KEY VALUATION ASSUMPTIONS</h3>
        '''
        
        # DCF Assumptions
        dcf_assumptions = self.dcf_result.get('assumptions', {})
        html += f'''
            <p><strong>DCF Methodology ({company_type} Company):</strong></p>
            <ul style="line-height: 1.8;">
                <li><strong>Projection Period:</strong> {dcf_assumptions.get('projection_years', 5)} years</li>
                <li><strong>FCF Growth Rate:</strong> {self._pct(dcf_assumptions.get('fcf_cagr', 0))} 
                    (Growth Method: {dcf_assumptions.get('growth_method', 'N/A').replace('_', ' ').title()})</li>
                <li><strong>Terminal Growth:</strong> {self._pct(dcf_assumptions.get('terminal_growth_rate', 0.025))}</li>
                <li><strong>WACC:</strong> {self._pct(dcf_assumptions.get('wacc', 0))} 
                    (Beta: {dcf_assumptions.get('beta', 1.0):.2f}, Risk-Free: {self._pct(dcf_assumptions.get('risk_free_rate', 0.04))}, 
                    ERP: {self._pct(dcf_assumptions.get('equity_risk_premium', 0.06))})</li>
            </ul>
            
            <p><strong>Multiples Approach:</strong></p>
            <ul style="line-height: 1.8;">
                <li><strong>Peer Group:</strong> {', '.join(self.peer_tickers) if self.peer_tickers else 'N/A'}</li>
                <li><strong>Metrics:</strong> P/E, EV/EBITDA, P/B</li>
                <li><strong>Note:</strong> Premium/discount to peers reflects growth differential and competitive positioning</li>
            </ul>
        '''
        
        return html

    # ========================================
    # LLM NARRATIVES FOR VALUATION & COMPETITIVE
    # ========================================

    def _generate_valuation_narrative(self) -> str:
        """
        Generate LLM narrative for Valuation Interpretation.
        80-100 words explaining the blended valuation approach.
        """
        if not self.client:
            return "Our blended valuation approach combines DCF and multiples analysis weighted according to company characteristics."
        
        current_price = self._safe(self.recommendation.get('current_price'), 100.0)
        fair_value = self._safe(self.recommendation.get('fair_value'))
        upside = self._safe(self.recommendation.get('upside_downside'))
        
        dcf_value = self._safe(self.dcf_result.get('fair_value_per_share'))
        mult_value = self._safe(self.multiples_result.get('average_fair_value'))
        
        weights = self.recommendation.get('weights', {'dcf': 0.45, 'multiples': 0.35, 'ddm': 0.20})
        company_type = self.classification.get('company_type', 'balanced')
        
        dcf_assumptions = self.dcf_result.get('assumptions', {})
        fcf_growth = self._safe(dcf_assumptions.get('fcf_cagr'))
        wacc = self._safe(dcf_assumptions.get('wacc'))
        growth_method = dcf_assumptions.get('growth_method', 'historical_avg')
        
        # Format values safely
        fair_value_fmt = f"{fair_value:.2f}" if fair_value else "N/A"
        dcf_value_fmt = f"{dcf_value:.2f}" if dcf_value else "N/A"
        mult_value_fmt = f"{mult_value:.2f}" if mult_value else "N/A"
        current_price_fmt = f"{current_price:.2f}" if current_price else "N/A"
        upside_fmt = f"{upside*100:+.1f}%" if upside is not None else "N/A"
        fcf_growth_fmt = f"{fcf_growth*100:.1f}%" if fcf_growth else "N/A"
        wacc_fmt = f"{wacc*100:.1f}%" if wacc else "N/A"
        dcf_weight = weights.get('dcf', 0) * 100
        mult_weight = weights.get('multiples', 0) * 100
        
        prompt = f"""Write 80-100 words explaining the valuation conclusion for {self.ticker}.

    Context:
    - Target: ${fair_value_fmt}, Current: ${current_price_fmt}, Upside: {upside_fmt}
    - DCF: ${dcf_value_fmt} (weight {dcf_weight:.0f}%)
    - Multiples: ${mult_value_fmt} (weight {mult_weight:.0f}%)
    - Company Type: {company_type}
    - FCF Growth: {fcf_growth_fmt} ({growth_method}), WACC: {wacc_fmt}

    Explain: (1) blended fair value, (2) why these weights for {company_type}, (3) key driver.
    Third-person, professional tone. Use specific numbers."""
        
        return self._llm(prompt, max_tokens=200)
        
    def _generate_competitive_narrative(self) -> str:
        """
        Generate LLM narrative for Competitive Analysis.
        100-120 words analyzing valuation vs peers.
        """
        if not self.client:
            return "The company's valuation reflects its competitive position within the industry peer group."
        
        company_multiples = self.multiples_result.get('company_multiples', {})
        peer_averages = self.multiples_result.get('peer_averages', {})
        
        # Use _safe() to handle None values
        pe = self._safe(company_multiples.get('pe'))
        peer_pe = self._safe(peer_averages.get('avg_pe'))  # Fixed: key is 'avg_pe' not 'pe'
        ev_ebitda = self._safe(company_multiples.get('ev_ebitda'))
        peer_ev_ebitda = self._safe(peer_averages.get('avg_ev_ebitda'))  # Fixed: key is 'avg_ev_ebitda'
        
        revenue_growth = self._safe(self.ratios.get('revenue_growth'))
        gross_margin = self._safe(self.ratios.get('gross_margin'))
        operating_margin = self._safe(self.ratios.get('operating_margin'))
        roe = self._safe(self.ratios.get('roe'))
        
        pe_premium = ((pe / peer_pe) - 1) if (pe and peer_pe and peer_pe != 0) else 0
        
        sector = self.overview.get('sector', 'N/A')
        industry = self.overview.get('industry', 'N/A')
        
        # Format values safely for prompt
        pe_str = f"{pe:.1f}x" if pe else "N/A"
        ev_ebitda_str = f"{ev_ebitda:.1f}x" if ev_ebitda else "N/A"
        peer_pe_str = f"{peer_pe:.1f}x" if peer_pe else "N/A"
        peer_ev_ebitda_str = f"{peer_ev_ebitda:.1f}x" if peer_ev_ebitda else "N/A"
        premium_str = f"{pe_premium*100:+.0f}%" if pe_premium else "N/A"
        
        # Format company metrics safely
        rev_growth_str = f"{revenue_growth*100:.1f}%" if revenue_growth else "N/A"
        gross_margin_str = f"{gross_margin*100:.1f}%" if gross_margin else "N/A"
        op_margin_str = f"{operating_margin*100:.1f}%" if operating_margin else "N/A"
        roe_str = f"{roe*100:.1f}%" if roe else "N/A"
        
        prompt = f"""Write 100-120 words analyzing {self.ticker}'s valuation vs peers.

    Data:
    - {self.ticker}: P/E {pe_str}, EV/EBITDA {ev_ebitda_str}
    - Peers: P/E {peer_pe_str}, EV/EBITDA {peer_ev_ebitda_str}  
    - Premium: {premium_str}
    - {self.ticker}: Revenue Growth {rev_growth_str}, Gross Margin {gross_margin_str}, Op Margin {op_margin_str}, ROE {roe_str}
    - Industry: {industry}
    - Peers: {', '.join(self.peer_tickers) if self.peer_tickers else 'N/A'}

    Explain: (1) if premium justified, (2) competitive advantages with specific numbers, (3) concerns.
    Professional, objective, third-person."""
        
        return self._llm(prompt, max_tokens=250)


    # ========================================
    # PAGE 5: COMPETITIVE POSITIONING (NEW!)
    # ========================================

    def _page5_competitive_positioning(self) -> str:
        """
        Page 5: Competitive Positioning (NEW SECTION!)
        - Peer Comparison Matrix
        - Operating Metrics Comparison
        - LLM Competitive Analysis
        """
        
        # Get peer data
        peer_multiples = self.multiples_result.get('peer_multiples', {})
        peer_averages = self.multiples_result.get('peer_averages', {})
        company_multiples = self.multiples_result.get('company_multiples', {})
        
        # Company metrics - use Forward P/E if available
        market_cap = self._safe(self.overview.get('market_cap'))
        trailing_pe = self._safe(company_multiples.get('pe'))
        forward_pe = self._safe(self.forward_estimates.get('forward_pe'))
        pe = forward_pe if forward_pe else trailing_pe  # Prefer Forward P/E
        pe_label = "Fwd P/E" if forward_pe else "P/E"
        
        ev_ebitda = self._safe(company_multiples.get('ev_ebitda'))
        pb = self._safe(company_multiples.get('pb'))
        
        # Peer averages - use correct keys from calculate_peer_averages()
        peer_pe = self._safe(peer_averages.get('avg_pe'))
        peer_ev_ebitda = self._safe(peer_averages.get('avg_ev_ebitda'))
        peer_pb = self._safe(peer_averages.get('avg_pb'))
        
        html = f'''
            <h2>5. Competitive Positioning</h2>
            
            <h3>PEER COMPARISON MATRIX</h3>
            
            <p><strong>Industry:</strong> {self.overview.get('industry', 'N/A')}</p>
            
            <table>
                <thead>
                    <tr>
                        <th style="text-align: left;">COMPANY</th>
                        <th>MARKET CAP</th>
                        <th>{pe_label}</th>
                        <th>EV/EBITDA</th>
                        <th>P/B</th>
                    </tr>
                </thead>
                <tbody>
                    <tr style="background-color: #eff6ff;">
                        <td><strong>{self.ticker}</strong></td>
                        <td>{self._num(market_cap)}</td>
                        <td>{self._mult(pe) if pe else 'N/A'}</td>
                        <td>{self._mult(ev_ebitda) if ev_ebitda else 'N/A'}</td>
                        <td>{self._mult(pb) if pb else 'N/A'}</td>
                    </tr>
        '''
        
        # Individual peers
        for peer_ticker in self.peer_tickers:
            peer_data = peer_multiples.get(peer_ticker, {})
            if peer_data:
                html += f'''
                    <tr>
                        <td>{peer_ticker}</td>
                        <td>{self._num(peer_data.get('market_cap'))}</td>
                        <td>{self._mult(peer_data.get('pe'))}</td>
                        <td>{self._mult(peer_data.get('ev_ebitda'))}</td>
                        <td>{self._mult(peer_data.get('pb'))}</td>
                    </tr>
                '''
        
        # Peer Average row (highlighted)
        html += f'''
                    <tr style="background-color: #fef3c7; font-weight: 600;">
                        <td>Peer Average</td>
                        <td>—</td>
                        <td>{self._mult(peer_pe) if peer_pe else 'N/A'}</td>
                        <td>{self._mult(peer_ev_ebitda) if peer_ev_ebitda else 'N/A'}</td>
                        <td>{self._mult(peer_pb) if peer_pb else 'N/A'}</td>
                    </tr>
                </tbody>
            </table>
            
            <h3 style="margin-top: 2em;">OPERATING METRICS COMPARISON</h3>
            
            <table>
                <thead>
                    <tr>
                        <th style="text-align: left;">METRIC</th>
                        <th>{self.ticker}</th>
                        <th>PEER AVG</th>
                        <th>DIFFERENTIAL</th>
                    </tr>
                </thead>
                <tbody>
        '''
        
        # Company metrics - use _safe() to handle None values
        revenue_growth = self._safe(self.ratios.get('revenue_growth'))
        gross_margin = self._safe(self.ratios.get('gross_margin'))
        operating_margin = self._safe(self.ratios.get('operating_margin'))
        roe = self._safe(self.ratios.get('roe'))
        
        # Mock peer averages (ideally calculate from peer data)
        peer_rev_growth = 0.12  # 12% typical for mature semis
        peer_gross_margin = 0.55
        peer_op_margin = 0.28
        peer_roe = 0.25
        
        metrics_comparison = [
            ('Revenue Growth', revenue_growth, peer_rev_growth),
            ('Gross Margin', gross_margin, peer_gross_margin),
            ('Operating Margin', operating_margin, peer_op_margin),
            ('ROE', roe, peer_roe),
        ]
        
        for metric_name, company_val, peer_val in metrics_comparison:
            diff = company_val - peer_val if (company_val and peer_val) else None
            diff_pp = diff * 100 if diff is not None else None
            
            html += f'''
                    <tr>
                        <td>{metric_name}</td>
                        <td>{self._pct(company_val) if company_val else 'N/A'}</td>
                        <td>{self._pct(peer_val) if peer_val else 'N/A'}</td>
                        <td class="{'positive' if diff and diff > 0 else 'negative'}">
                            {f'{diff_pp:+.0f}pp' if diff_pp is not None else 'N/A'}
                        </td>
                    </tr>
            '''
        
        html += '''
                </tbody>
            </table>
        '''
        
        # LLM Competitive Analysis
        competitive_narrative = self._generate_competitive_narrative()
        html += f'''
            <p style="text-align: justify; line-height: 1.6; margin-top: 1.5em;">
                <strong>💡 Competitive Analysis</strong><br><br>
                {competitive_narrative}
            </p>
        '''
        
        return html

    # ========================================
    # PAGE 6: RISK ASSESSMENT
    # ========================================
    
    def _page6_risk_assessment(self) -> str:
        """Generate Page 6: Risk Assessment."""
        
        risks = self.recommendation.get('risk_factors', {
        'solvency_risk': False,
        'liquidity_risk': False,
        'leverage_risk': False,
        'has_risk_flags': False
        })
        upside = self._safe(self.recommendation.get('upside_downside'))
        pe = self._safe(self.overview.get('pe_ratio'))
        pb = self._safe(self.multiples_result.get('company_multiples', {}).get('pb'))
        revenue_growth = self._safe(self.ratios.get('revenue_growth'))
        beta = self._safe(self.overview.get('beta'), 1.0)
        sector = self.overview.get('sector', '')
        
        # Build risk table
        risk_rows = []
        
        # Valuation risk
        if upside < -0.30:
            risk_rows.append(('High', 'Valuation', f'Target {self._price(self.recommendation["fair_value"])} ({self._pct(upside)} downside)'))
        elif upside < -0.15:
            risk_rows.append(('Medium', 'Valuation', f'Target {self._price(self.recommendation["fair_value"])} ({self._pct(upside)} downside)'))
        
        # Multiple risk
        if pb > 20:
            risk_rows.append(('High', 'Multiple', f'P/B {self._mult(pb)} reflects extreme expectations'))
        elif pe > 50:
            risk_rows.append(('Medium', 'Multiple', f'P/E {self._mult(pe)} above historical norms'))
        
        # Growth risk
        if revenue_growth < 0:
            risk_rows.append(('High', 'Growth', 'Revenue declining year-over-year'))
        elif revenue_growth > 0.50:
            risk_rows.append(('Medium', 'Growth', f'Revenue +{self._pct(revenue_growth)} may normalize (base effect)'))
        
        # Financial risks
        if risks['solvency_risk']:
            risk_rows.append(('High', 'Financial', 'Interest coverage below minimum threshold'))
        if risks['liquidity_risk']:
            risk_rows.append(('Medium', 'Financial', 'Current ratio indicates liquidity pressure'))
        if risks['leverage_risk']:
            risk_rows.append(('Medium', 'Financial', 'Elevated leverage may constrain flexibility'))
        
        # Market risk
        if beta > 1.5:
            risk_rows.append(('Medium', 'Volatility', f'Beta {beta:.2f} amplifies market moves'))
        
        # Sector-specific risks (simplified)
        sector_risks = {
            'Technology': ('Medium', 'Competitive', 'Rapid innovation cycle; market share vulnerable'),
            'Energy': ('Medium', 'Regulatory', 'Export controls; geopolitical restrictions'),
            'Financial Services': ('Medium', 'Regulatory', 'Regulatory changes may impact profitability'),
        }
        
        for sector_key, (severity, category, signal) in sector_risks.items():
            if sector_key.lower() in sector.lower():
                risk_rows.append((severity, category, signal))
                break
        
        # Sort by severity
        severity_order = {'High': 0, 'Medium': 1, 'Low': 2}
        risk_rows.sort(key=lambda x: severity_order.get(x[0], 3))
        
        # Build table HTML
        risk_table_rows = ""
        for severity, category, signal in risk_rows:
            severity_class = f'risk-{severity.lower()}'
            risk_table_rows += f"""<tr>
                <td class="{severity_class}">{severity}</td>
                <td>{category}</td>
                <td>{signal}</td>
            </tr>"""
        
        risk_table = f"""
        <h3>Key Risks</h3>
        <table>
            <thead>
                <tr>
                    <th>Severity</th>
                    <th>Risk Category</th>
                    <th>Signal</th>
                </tr>
            </thead>
            <tbody>
                {risk_table_rows if risk_table_rows else '<tr><td colspan="3">No material risks identified</td></tr>'}
            </tbody>
        </table>
        """
        
        # LLM: Risk Summary
        risks_list = [f"{sev} {cat}: {sig}" for sev, cat, sig in risk_rows]
        
        prompt = f"""Write a risk summary (100-120 words, single paragraph) for {self.ticker} based on the identified risks.

Identified Risks:
{chr(10).join('- ' + r for r in risks_list) if risks_list else '- No material risks identified'}

Instructions:
Synthesize the key risks in ONE paragraph:
1. Start with the most severe risk category
2. Acknowledge 2-3 additional material risks
3. Note any offsetting factors or risk mitigants (if applicable)
4. Close with overall risk profile characterization

Tone: Balanced, third-person. NO "we believe". Use: "The primary risk is...", "Additional considerations include...", "The risk profile reflects..."
Format: Plain text paragraph. No bullet points."""

        risk_summary = self._llm(prompt, max_tokens=250)
        
        if len(risk_summary) < 50:
            if risk_rows:
                primary_risk = risk_rows[0]
                risk_summary = f"The primary risk is {primary_risk[1].lower()}, with {primary_risk[2].lower()}. The overall risk profile reflects the {self.classification['company_type']} nature of the business."
            else:
                risk_summary = f"The risk profile appears balanced with no critical concerns identified. Standard market and operational risks apply to {self.ticker} as a {self.classification['company_type']} company."
        
        return risk_table + f"<p>{risk_summary}</p>"
    
    # ========================================
    # PAGE 7: INVESTMENT RECOMMENDATION
    # ========================================
    
    def _page7_recommendation(self) -> str:
        """Generate Page 7: Investment Recommendation."""
        
        rec = self.recommendation['recommendation']
        target = self._safe(self.recommendation['fair_value'])
        current = self._safe(self.recommendation['current_price'])
        upside = self._safe(self.recommendation['upside_downside'])
        company_type = self.classification['company_type']
        weights = self.recommendation.get('weights', {
            'dcf': 0.45,
            'multiples': 0.35,
            'ddm': 0.20
        })
                
        # Recommendation Box
        rec_class = f"rec-{rec.lower()}"
        upside_color = '#10b981' if upside > 0 else '#ef4444'
        
        rec_box = f"""
        <div class="rec-box {rec_class}">
            <div class="rec-title">INVESTMENT RECOMMENDATION: {rec}</div>
            <div class="rec-metrics">
                <div class="rec-metric">
                    <div class="rec-metric-label">Target Price</div>
                    <div class="rec-metric-value">{self._price(target)}</div>
                </div>
                <div class="rec-metric">
                    <div class="rec-metric-label">Current Price</div>
                    <div class="rec-metric-value">{self._price(current)}</div>
                </div>
                <div class="rec-metric">
                    <div class="rec-metric-label">Upside/Downside</div>
                    <div class="rec-metric-value" style="color: {upside_color};">{self._pct(upside)}</div>
                </div>
            </div>
        </div>
        """
        
        # LLM: Recommendation Rationale
        risk_flags = self.recommendation.get('risk_factors', {
        'has_risk_flags': False
        })
        upside_term = "upside" if upside > 0 else "downside"
        
        prompt = f"""Write a recommendation rationale (150-180 words, 2 paragraphs) for {self.ticker}.

Data:
- Recommendation: {rec}
- Target Price: {self._price(target)}
- Current Price: {self._price(current)}
- Upside: {self._pct(upside)}
- Company Type: {company_type}
- Key Risk Flags: {', '.join([k for k, v in risk_flags.items() if v and k != 'has_risk_flags']) if risk_flags['has_risk_flags'] else 'None'}

Structure:
Paragraph 1: Open with "Based on the valuation analysis, {self.ticker} is rated {rec} with a 12-month target of {self._price(target)}, representing {self._pct(upside)} {upside_term} from the current price of {self._price(current)}." Then state the core rationale in 2-3 sentences: why the stock is overvalued/undervalued/fairly valued relative to the {company_type}-weighted fair value estimate. Reference key risk flags if present.

Paragraph 2: Close with the key catalyst or risk to monitor and a definitive statement on why the rating is appropriate.

Tone: Decisive, professional, third-person. Use: "The analysis indicates...", "{self.ticker} appears...", "The stock trades..."
Format: Plain text paragraphs."""

        rationale = self._llm(prompt, max_tokens=300)
        
        if len(rationale) < 50:
            rationale = f"Based on the valuation analysis, {self.ticker} is rated {rec} with a 12-month target of {self._price(target)}, representing {self._pct(upside)} {upside_term} from the current price of {self._price(current)}. The stock appears {'undervalued' if upside > 0 else 'overvalued' if upside < -0.15 else 'fairly valued'} relative to the {company_type}-weighted fair value estimate."
        
        # Valuation Method Note
        weights_text = f"DCF: {self._pct(weights['dcf'])} · Multiples: {self._pct(weights['multiples'])} · DDM: {self._pct(weights['ddm'])}"
        method_note = f"<p><strong>Valuation Method:</strong> {company_type.title()} ({weights_text})</p>"
        
        return rec_box + f"<p>{rationale}</p>" + method_note
    
    # ========================================
    # APPENDIX A: SCORING METHODOLOGY
    # ========================================
    
    def _appendix_a_methodology(self) -> str:
        """Generate Appendix A: Scoring Methodology with dynamic values from settings."""
        from config.settings import (
            COMPANY_TYPE_WEIGHTS,
            BUY_THRESHOLD,
            SELL_THRESHOLD,
            MIN_INTEREST_COVERAGE,
            MIN_CURRENT_RATIO,
            MAX_DEBT_TO_EBITDA
        )
        
        # Get weights for each company type
        growth_w = COMPANY_TYPE_WEIGHTS.get('growth', {})
        balanced_w = COMPANY_TYPE_WEIGHTS.get('balanced', {})
        dividend_w = COMPANY_TYPE_WEIGHTS.get('dividend', {})
        cyclical_w = COMPANY_TYPE_WEIGHTS.get('cyclical', {})
        
        return f"""
        <h2>Appendix A: Scoring Methodology</h2>
        
        <p>The recommendation is based on valuation upside—the percentage difference between the calculated Target Price and Current Price. The Target Price is a weighted blend of three valuation methods, with weights determined by company classification.</p>
        
        <h3>Step 1: Calculate Target Price</h3>
        
        <table>
            <thead>
                <tr>
                    <th>Method</th>
                    <th>Description</th>
                </tr>
            </thead>
            <tbody>
                <tr>
                    <td><strong>DCF</strong></td>
                    <td>Intrinsic value based on projected free cash flows discounted to present value</td>
                </tr>
                <tr>
                    <td><strong>Multiples</strong></td>
                    <td>Fair value based on P/E, EV/EBITDA, and P/B multiples vs peer companies</td>
                </tr>
                <tr>
                    <td><strong>DDM</strong></td>
                    <td>Value based on expected dividend stream using Gordon Growth Model</td>
                </tr>
            </tbody>
        </table>
        
        <h3>Valuation Weights by Company Type</h3>
        
        <table>
            <thead>
                <tr>
                    <th>Company Type</th>
                    <th class="text-center">DCF</th>
                    <th class="text-center">Multiples</th>
                    <th class="text-center">DDM</th>
                </tr>
            </thead>
            <tbody>
                <tr>
                    <td>Growth</td>
                    <td class="text-center">{growth_w.get('dcf', 0)*100:.0f}%</td>
                    <td class="text-center">{growth_w.get('multiples', 0)*100:.0f}%</td>
                    <td class="text-center">{growth_w.get('ddm', 0)*100:.0f}%</td>
                </tr>
                <tr>
                    <td>Balanced</td>
                    <td class="text-center">{balanced_w.get('dcf', 0)*100:.0f}%</td>
                    <td class="text-center">{balanced_w.get('multiples', 0)*100:.0f}%</td>
                    <td class="text-center">{balanced_w.get('ddm', 0)*100:.0f}%</td>
                </tr>
                <tr>
                    <td>Dividend</td>
                    <td class="text-center">{dividend_w.get('dcf', 0)*100:.0f}%</td>
                    <td class="text-center">{dividend_w.get('multiples', 0)*100:.0f}%</td>
                    <td class="text-center">{dividend_w.get('ddm', 0)*100:.0f}%</td>
                </tr>
                <tr>
                    <td>Cyclical</td>
                    <td class="text-center">{cyclical_w.get('dcf', 0)*100:.0f}%</td>
                    <td class="text-center">{cyclical_w.get('multiples', 0)*100:.0f}%</td>
                    <td class="text-center">{cyclical_w.get('ddm', 0)*100:.0f}%</td>
                </tr>
            </tbody>
        </table>
        
        <h3>Step 2: Calculate Upside</h3>
        <p><code>Upside = (Target Price - Current Price) / Current Price × 100%</code></p>
        
        <h3>Step 3: Gate Checks (Safety Filters)</h3>
        
        <table>
            <thead>
                <tr>
                    <th>Gate</th>
                    <th class="text-center">Threshold</th>
                    <th class="text-center">Severity</th>
                </tr>
            </thead>
            <tbody>
                <tr>
                    <td>Interest Coverage</td>
                    <td class="text-center">≥ {MIN_INTEREST_COVERAGE}x</td>
                    <td class="text-center">CRITICAL</td>
                </tr>
                <tr>
                    <td>Current Ratio</td>
                    <td class="text-center">≥ {MIN_CURRENT_RATIO}x</td>
                    <td class="text-center">HIGH</td>
                </tr>
                <tr>
                    <td>Debt/Equity</td>
                    <td class="text-center">≤ 5.0x</td>
                    <td class="text-center">HIGH</td>
                </tr>
            </tbody>
        </table>
        
        <h3>Step 4: Recommendation Logic</h3>
        
        <table>
            <thead>
                <tr>
                    <th>Condition</th>
                    <th>Recommendation</th>
                </tr>
            </thead>
            <tbody>
                <tr>
                    <td>Upside &gt; {BUY_THRESHOLD*100:+.0f}% AND no HIGH/CRITICAL gates</td>
                    <td><strong>BUY</strong></td>
                </tr>
                <tr>
                    <td>Upside &gt; {BUY_THRESHOLD*100:+.0f}% BUT has HIGH gate</td>
                    <td><strong>HOLD</strong></td>
                </tr>
                <tr>
                    <td>{SELL_THRESHOLD*100:.0f}% &lt; Upside &lt; {BUY_THRESHOLD*100:+.0f}%</td>
                    <td><strong>HOLD</strong></td>
                </tr>
                <tr>
                    <td>Upside &lt; {SELL_THRESHOLD*100:.0f}%</td>
                    <td><strong>SELL</strong></td>
                </tr>
                <tr>
                    <td>Any CRITICAL gate triggered</td>
                    <td><strong>SELL</strong></td>
                </tr>
            </tbody>
        </table>
        """
    
    # ========================================
    # APPENDIX B: COMPANY CLASSIFICATION
    # ========================================
    
    def _appendix_b_classification(self) -> str:
        """Generate Appendix B: Company Classification Framework - clean and structured."""
        from config.settings import COMPANY_TYPE_WEIGHTS
        
        # Get weights for each company type
        growth_w = COMPANY_TYPE_WEIGHTS.get('growth', {})
        balanced_w = COMPANY_TYPE_WEIGHTS.get('balanced', {})
        dividend_w = COMPANY_TYPE_WEIGHTS.get('dividend', {})
        cyclical_w = COMPANY_TYPE_WEIGHTS.get('cyclical', {})
        
        return f"""
        <h2>Appendix B: Company Classification Framework</h2>
        
        <p>Companies are classified into four types based on dividend yield, revenue growth, and sector. Each type uses different valuation weights optimized for its characteristics.</p>
        
        <h3>Classification Criteria & Valuation Weights</h3>
        
        <table>
            <thead>
                <tr>
                    <th>Type</th>
                    <th>Criteria</th>
                    <th class="text-center">DCF</th>
                    <th class="text-center">Multiples</th>
                    <th class="text-center">DDM</th>
                    <th>Typical Sectors</th>
                </tr>
            </thead>
            <tbody>
                <tr>
                    <td><strong>Growth</strong></td>
                    <td>Dividend &lt;2%, Revenue Growth &gt;15%</td>
                    <td class="text-center">{growth_w.get('dcf', 0)*100:.0f}%</td>
                    <td class="text-center">{growth_w.get('multiples', 0)*100:.0f}%</td>
                    <td class="text-center">{growth_w.get('ddm', 0)*100:.0f}%</td>
                    <td>Technology, Biotech, Software, Semiconductors</td>
                </tr>
                <tr>
                    <td><strong>Balanced</strong></td>
                    <td>Dividend 2-4%, Revenue Growth 10-15%</td>
                    <td class="text-center">{balanced_w.get('dcf', 0)*100:.0f}%</td>
                    <td class="text-center">{balanced_w.get('multiples', 0)*100:.0f}%</td>
                    <td class="text-center">{balanced_w.get('ddm', 0)*100:.0f}%</td>
                    <td>Healthcare, Financials, Industrials</td>
                </tr>
                <tr>
                    <td><strong>Dividend</strong></td>
                    <td>Dividend &gt;4%, Revenue Growth &lt;10%</td>
                    <td class="text-center">{dividend_w.get('dcf', 0)*100:.0f}%</td>
                    <td class="text-center">{dividend_w.get('multiples', 0)*100:.0f}%</td>
                    <td class="text-center">{dividend_w.get('ddm', 0)*100:.0f}%</td>
                    <td>Utilities, REITs, Telecom, Consumer Staples</td>
                </tr>
                <tr>
                    <td><strong>Cyclical</strong></td>
                    <td>Sector-based classification</td>
                    <td class="text-center">{cyclical_w.get('dcf', 0)*100:.0f}%</td>
                    <td class="text-center">{cyclical_w.get('multiples', 0)*100:.0f}%</td>
                    <td class="text-center">{cyclical_w.get('ddm', 0)*100:.0f}%</td>
                    <td>Energy, Materials, Chemicals, Automotive</td>
                </tr>
            </tbody>
        </table>
        
        <h3>Classification Logic</h3>
        
        <table>
            <thead>
                <tr>
                    <th>Step</th>
                    <th>Check</th>
                    <th>Result</th>
                </tr>
            </thead>
            <tbody>
                <tr>
                    <td>1</td>
                    <td>Sector in [Energy, Materials, Chemicals, Automotive]</td>
                    <td>→ <strong>CYCLICAL</strong></td>
                </tr>
                <tr>
                    <td>2</td>
                    <td>Dividend Yield &gt; 4%</td>
                    <td>→ <strong>DIVIDEND</strong></td>
                </tr>
                <tr>
                    <td>3</td>
                    <td>Revenue Growth &gt; 15% AND Dividend &lt; 2%</td>
                    <td>→ <strong>GROWTH</strong></td>
                </tr>
                <tr>
                    <td>4</td>
                    <td>All other cases</td>
                    <td>→ <strong>BALANCED</strong></td>
                </tr>
            </tbody>
        </table>
        
        <h3>Weighting Rationale</h3>
        
        <table>
            <thead>
                <tr>
                    <th>Method</th>
                    <th>Best For</th>
                    <th>Limitations</th>
                </tr>
            </thead>
            <tbody>
                <tr>
                    <td><strong>DCF</strong></td>
                    <td>Companies with visible, sustainable cash flows</td>
                    <td>Less reliable for high-growth (forecast uncertainty) and cyclical (volatile earnings)</td>
                </tr>
                <tr>
                    <td><strong>Multiples</strong></td>
                    <td>Peer benchmarking when sector dynamics drive valuation</td>
                    <td>Requires comparable peers; can reflect market mispricing</td>
                </tr>
                <tr>
                    <td><strong>DDM</strong></td>
                    <td>Companies with established, stable dividend policies</td>
                    <td>Not applicable for non-dividend or variable dividend companies</td>
                </tr>
            </tbody>
        </table>
        """
    
    # ========================================
    # MAIN GENERATOR
    # ========================================
    
    def generate_html_memo(self) -> str:
        """Generate complete HTML investment memo."""
        
        company_name = self.overview.get('name', self.ticker)
        date_str = datetime.now().strftime('%B %d, %Y')
        
        print(f"\n📄 Generating Investment Memo for {self.ticker}...")
        
        print("  [1/8] Executive Summary...")
        page1 = self._page1_executive_summary()
        
        print("  [2/8] Company Overview...")
        page2 = self._page2_company_overview()
        
        print("  [3/8] Financial Analysis...")
        page3 = self._page3_financial_analysis()
        
        print("  [4/8] Valuation...")
        page4 = self._page4_valuation()
        
        print("  [5/8] Competitive Positioning...")
        page5 = self._page5_competitive_positioning()
        
        print("  [6/8] Risk Assessment...")
        page6 = self._page6_risk_assessment()
        
        print("  [7/8] Investment Recommendation...")
        page7 = self._page7_recommendation()
        
        print("  [8/8] Appendices...")
        appendix_a = self._appendix_a_methodology()
        appendix_b = self._appendix_b_classification()
        
        print("  ✅ Complete!")
        
        html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Investment Memo: {self.ticker} - {company_name}</title>
    {self._css()}
</head>
<body>
    <h1>Investment Memo: {company_name} ({self.ticker})</h1>
    <p style="font-size: 9pt; color: #6b7280; margin-bottom: 20px;">
        <strong>Date:</strong> {date_str}<br>
        <strong>Analyst:</strong> Idaliia Gafarova<br>
        <strong>Classification:</strong> {self.classification['company_type'].title()}
    </p>
    
    <h2>1. Executive Summary</h2>
    {page1}
    
    <h2>2. Company Overview</h2>
    {page2}
    
    {page3}
    
    {page4}
    
    {page5}
    
    <h2>6. Risk Assessment</h2>
    {page6}
    
    <h2>7. Investment Recommendation</h2>
    {page7}
    
    {appendix_a}
    
    {appendix_b}
    
    <div style="margin-top: 50px; padding: 20px; background: #f9fafb; border-top: 2px solid #e5e7eb; text-align: center; font-size: 8pt; color: #6b7280;">
        <p><strong>Disclaimer:</strong> This investment memo was generated by an AI-powered equity research agent for educational purposes. All analysis is based on publicly available data and should not be considered as financial advice. Past performance does not guarantee future results. Please conduct your own due diligence and consult with a qualified financial advisor before making investment decisions.</p>
    </div>
</body>
</html>"""
        
        return html
    
    def save_memo(self, filepath: str):
        """Generate and save HTML memo to file."""
        html = self.generate_html_memo()
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(html)
        return filepath
