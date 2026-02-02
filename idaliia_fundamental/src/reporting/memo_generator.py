"""
HTML investment memo generator with LLM-powered analysis.
"""

from typing import Dict, List
from datetime import datetime
from openai import OpenAI
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
        
        if OPENAI_API_KEY:
            self.client = OpenAI(api_key=OPENAI_API_KEY)
        else:
            self.client = None
    
    
    def _safe(self, val, default=0.0):
        if val is None or val == "N/A":
            return default
        try:
            return float(val)
        except (ValueError, TypeError):
            return default
    
    def _price(self, val):
        v = self._safe(val)
        return f"${v:,.2f}" if v != 0 else "N/A"
    
    def _pct(self, val):
        v = self._safe(val)
        if v == 0 and val not in [0, 0.0]:
            return "N/A"
        return f"{v * 100:.1f}%"
    
    def _mult(self, val):
        v = self._safe(val)
        return f"{v:.1f}x" if v != 0 else "N/A"
    
    def _num(self, val):
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
    
    
    def _llm(self, prompt: str, max_tokens: int = 500) -> str:
        if not self.client:
            return "[LLM unavailable - no API key configured]"
        
        try:
            response = self.client.chat.completions.create(
                model=LLM_MODEL,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a senior equity research analyst at Goldman Sachs writing investment memos for institutional clients. Be rigorous, balanced, and actionable. Use specific metrics. Write in professional Wall Street style. NEVER use 'we/our' - use third-person or passive voice."
                    },
                    {"role": "user", "content": prompt}
                ],
                max_tokens=max_tokens,
                temperature=LLM_TEMPERATURE
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            return f"[LLM Error: {str(e)}]"
    
    
    def _css(self) -> str:
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
                color: #111827;
                margin-bottom: 5px;
                border-bottom: 3px solid #2563eb;
                padding-bottom: 10px;
            }
            h2 {
                font-size: 14pt;
                font-weight: 700;
                color: #1e40af;
                border-bottom: 2px solid #93c5fd;
                padding-bottom: 5px;
                margin-top: 20px;
                margin-bottom: 10px;
                page-break-after: avoid;
                break-after: avoid;
            }
            h3 {
                font-size: 11pt;
                font-weight: 600;
                color: #374151;
                margin: 20px 0 10px 0;
                text-transform: uppercase;
                letter-spacing: 0.5px;
                page-break-after: avoid;
                break-after: avoid;
            }
            h4 {
                font-size: 10pt;
                font-weight: 600;
                color: #4b5563;
                margin: 15px 0 8px 0;
                page-break-after: avoid;
                break-after: avoid;
            }
            p {
                margin: 8px 0;
                text-align: justify;
                line-height: 1.6;
                orphans: 3;
                widows: 3;
            }
            table {
                width: 100%;
                border-collapse: collapse;
                margin: 12px 0;
                font-size: 9pt;
            }
            tr {
                page-break-inside: avoid;
                break-inside: avoid;
            }
            h2 + p, h2 + table, h3 + p, h3 + table {
                page-break-before: avoid;
                break-before: avoid;
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
                border-bottom: 1px solid #e5e7eb;
            }
            .text-right { text-align: right; }
            .text-center { text-align: center; }
            .highlight-row {
                background: #fef3c7;
                font-weight: 600;
            }
            .company-row {
                background: #eff6ff;
                font-weight: 700;
            }
            .section-header {
                background: #e5e7eb;
                font-weight: 700;
                text-transform: uppercase;
                font-size: 8pt;
                letter-spacing: 0.5px;
            }
            .positive { color: #059669; }
            .negative { color: #dc2626; }
            .neutral { color: #6b7280; }
            
            .rec-box {
                padding: 20px;
                margin: 20px 0;
                border-radius: 4px;
                text-align: center;
            }
            .rec-buy {
                background: #d1fae5;
                border: 3px solid #059669;
                color: #065f46;
            }
            .rec-hold {
                background: #fef3c7;
                border: 3px solid #d97706;
                color: #92400e;
            }
            .rec-sell {
                background: #fee2e2;
                border: 3px solid #dc2626;
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
                background: #d1fae5;
                border-color: #059669;
            }
            .valuation-fair {
                background: #fef3c7;
                border-color: #d97706;
            }
            .valuation-overvalued {
                background: #fee2e2;
                border-color: #dc2626;
            }
            
            .benchmark {
                font-size: 8pt;
                color: #6b7280;
                font-style: italic;
                margin-top: 5px;
            }
            
            .risk-high { color: #dc2626; }
            .risk-medium { color: #d97706; }
            .risk-low { color: #059669; }
            
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
                background-color: #059669;
                color: white;
                padding: 2px 8px;
                border-radius: 3px;
                font-size: 0.85em;
                font-weight: 600;
            }

            .rating-acceptable {
                background-color: #d97706;
                color: white;
                padding: 2px 8px;
                border-radius: 3px;
                font-size: 0.85em;
                font-weight: 600;
            }

            .rating-weak {
                background-color: #dc2626;
                color: white;
                padding: 2px 8px;
                border-radius: 3px;
                font-size: 0.85em;
                font-weight: 600;
            }

            @media print {
                body {
                    margin: 0;
                    padding: 15px;
                    font-size: 9pt;
                    -webkit-print-color-adjust: exact !important;
                    print-color-adjust: exact !important;
                }
                
                table {
                    width: 100% !important;
                    border-collapse: collapse !important;
                }

                th {
                    background-color: #f3f4f6 !important;
                    -webkit-print-color-adjust: exact !important;
                    print-color-adjust: exact !important;
                }

                tr {
                    page-break-inside: avoid !important;
                    break-inside: avoid !important;
                }

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

                h2, h3, h4 {
                    page-break-after: avoid !important;
                    break-after: avoid !important;
                }

                h2 + p, h2 + table, h3 + p, h3 + table, h4 + p, h4 + table {
                    page-break-before: avoid !important;
                    break-before: avoid !important;
                }

                .valuation-box {
                    -webkit-print-color-adjust: exact !important;
                    print-color-adjust: exact !important;
                    border-left: 4px solid !important;
                }
                
                .valuation-undervalued {
                    background-color: #d1fae5 !important;
                    border-color: #059669 !important;
                }
                
                .valuation-fair {
                    background-color: #fef3c7 !important;
                    border-color: #d97706 !important;
                }
                
                .valuation-overvalued {
                    background-color: #fee2e2 !important;
                    border-color: #dc2626 !important;
                }
                
                tr[style*="background-color"] {
                    -webkit-print-color-adjust: exact !important;
                    print-color-adjust: exact !important;
                }
                
                .page-break {
                    page-break-before: always;
                }
                
                .no-print {
                    display: none !important;
                }
            }
        </style>
        """
    
    
    def _get_historical_ratios(self) -> List[Dict]:
        historical = []
        
        num_years = min(5, len(self.income), len(self.balance))
        
        for i in range(num_years):
            year_data = {}
            
            fiscal_date = self.income[i].get('fiscal_date_ending') or self.income[i].get('fiscaldateending')
            if fiscal_date:
                try:
                    year_data['year'] = fiscal_date[:4]
                except (TypeError, IndexError):
                    year_data['year'] = f'Y-{i}'
            else:
                year_data['year'] = f'Y-{i}'
            
            revenue = self._safe(self.income[i].get('revenue'))
            cogs = self._safe(self.income[i].get('cost_of_revenue'))
            operating_income = self._safe(self.income[i].get('operating_income'))
            net_income = self._safe(self.income[i].get('net_income'))
            
            total_assets = self._safe(self.balance[i].get('total_assets'))
            total_equity = self._safe(self.balance[i].get('total_shareholder_equity'))
            current_assets = self._safe(self.balance[i].get('current_assets'))
            current_liabilities = self._safe(self.balance[i].get('current_liabilities'))
            inventory = self._safe(self.balance[i].get('inventory'))
            long_term_debt = self._safe(self.balance[i].get('long_term_debt'))
            short_term_debt = self._safe(self.balance[i].get('short_term_debt'))
            
            interest_expense = self._safe(self.income[i].get('interest_expense'))
            
            year_data['gross_margin'] = (revenue - cogs) / revenue if revenue > 0 else None
            year_data['operating_margin'] = operating_income / revenue if revenue > 0 else None
            year_data['net_margin'] = net_income / revenue if revenue > 0 else None
            year_data['roe'] = net_income / total_equity if total_equity > 0 else None
            year_data['roa'] = net_income / total_assets if total_assets > 0 else None
            
            total_debt = long_term_debt + short_term_debt
            year_data['debt_to_assets'] = total_debt / total_assets if total_assets > 0 else None
            year_data['debt_to_equity'] = total_debt / total_equity if total_equity > 0 else None
            year_data['interest_coverage'] = operating_income / interest_expense if interest_expense > 0 else None
            
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
            
            year_data['current_ratio'] = current_assets / current_liabilities if current_liabilities > 0 else None
            year_data['quick_ratio'] = (current_assets - inventory) / current_liabilities if current_liabilities > 0 else None
            
            historical.append(year_data)
        
        historical.reverse()
        
        return historical
    
    def _rate_gate_check_metric(self, metric_key: str, value: float) -> str:
        if value is None or value == 'N/A':
            return 'N/A'
        
        try:
            val = float(value)
        except (ValueError, TypeError):
            return 'N/A'
        
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
        gross_margin = self.ratios.get('gross_margin', 0)
        net_margin = self.ratios.get('net_margin', 0)
        roe = self.ratios.get('roe', 0)
        roa = self.ratios.get('roa', 0)

        debt_to_equity = self.ratios.get('debt_to_equity', 0)
        current_ratio = self.ratios.get('current_ratio')
        
        def rate_profitability():
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
            if debt_to_equity is None or debt_to_equity == 0:
                return "Strong"

            if debt_to_equity < 0.5:
                return "Strong"
            elif debt_to_equity < 1.0:
                return "Acceptable"
            elif debt_to_equity < 2.0:
                return "Elevated"
            else:
                return "Weak"
        
        def rate_liquidity():
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
            <h3>3.2 FINANCIAL HEALTH ASSESSMENT</h3>
            
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
        if not self.client:
            return "Financial analysis unavailable (LLM API key not configured)."
        
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
        if not values or len(values) < 2:
            return "—"
        
        first = next((v for v in values if v != 0), 0)
        last = next((v for v in reversed(values) if v != 0), 0)
        
        if first == 0 or last == 0:
            return "—"
        
        if metric_type == 'lower_better':
            if first > last * 1.1:
                return "Improving"
            elif first < last * 0.9:
                return "Declining"
        else:
            if last > first * 1.1:
                return "Improving"
            elif last < first * 0.9:
                return "Declining"
        
        return "Stable"
    
    
    def _page1_executive_summary(self) -> str:
        
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
        
        snapshot = f"""
        <h3>Investment Snapshot</h3>
        <table>
            <thead>
                <tr><th>Metric</th><th class="text-right">Value</th></tr>
            </thead>
            <tbody>
                <tr><td>Recommendation</td><td class="text-right"><strong>{rec}</strong></td></tr>
                <tr><td>Current Price</td><td class="text-right">{self._price(current)}</td></tr>
                <tr><td>12-Month Target Price</td><td class="text-right">{self._price(target)}</td></tr>
                <tr><td>Upside/Downside</td><td class="text-right {'positive' if upside > 0 else 'negative'}">{self._pct(upside)}</td></tr>
            </tbody>
        </table>
        """
        
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
        
        company_type = self.classification['company_type']
        upside_term = "upside" if upside > 0 else "downside"
        
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
    
    
    def _page2_company_overview(self) -> str:
        
        company_name = self.overview.get('name', self.ticker)
        sector = self.overview.get('sector', 'N/A')
        industry = self.overview.get('industry', 'N/A')
        market_cap = self._safe(self.overview.get('market_cap'))
        country = self.overview.get('country', 'United States')
        exchange = self.overview.get('exchange', 'NASDAQ')
        
        intro = f"<p>{company_name} ({self.ticker}) is a {country}-based company in the {industry} industry within the {sector} sector, listed on {exchange} with a market capitalization of approximately {self._num(market_cap)}.</p>"
        
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
    

    def _page3_financial_analysis(self) -> str:
        html = '''
        <h2>3. Financial Analysis</h2>
        
        <h3>3.1 FINANCIAL RATIOS</h3>
        
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
        
        historical = self._get_historical_ratios()
        
        while len(historical) < 5:
            historical.insert(0, {'year': '—'})
        
        historical = historical[-5:]
        
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
                
                for year_data in historical:
                    val = year_data.get(metric_key)
                    if val is None:
                        html += '<td>N/A</td>'
                    elif metric_key in ['gross_margin', 'operating_margin', 'net_margin', 'roe', 'roa', 'roic']:
                        html += f'<td>{self._pct(val)}</td>'
                    elif metric_key in ['current_ratio', 'quick_ratio', 'interest_coverage', 'debt_to_assets', 'debt_to_equity']:
                        html += f'<td>{self._mult(val)}</td>'
                    else:
                        html += f'<td>{val}</td>'
                
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
        
        html += self._financial_health_table()
        
        html += self._dupont_analysis_section()
        
        narrative = self._generate_financial_narrative()
        html += f'''
            <p style="text-align: justify; line-height: 1.6;">
                {narrative}
            </p>
        '''
        
        return html
    
    def _dupont_analysis_section(self) -> str:
        from src.analysis.financial_ratios import FinancialRatiosCalculator

        calculator = FinancialRatiosCalculator(self.company_data)
        dupont = calculator.get_dupont_analysis()

        net_margin = dupont.get('net_margin')
        asset_turnover = dupont.get('asset_turnover')
        equity_multiplier = dupont.get('equity_multiplier')
        actual_roe = dupont.get('actual_roe')

        def fmt_pct(v):
            return f"{v*100:.1f}%" if v is not None else "N/A"

        def fmt_mult(v):
            return f"{v:.2f}x" if v is not None else "N/A"

        driver_analysis = self._generate_dupont_analysis(
            net_margin, asset_turnover, equity_multiplier, actual_roe
        )

        html = f'''
            <h3>3.3 DUPONT ANALYSIS</h3>

            <p><strong>ROE Decomposition:</strong> {fmt_pct(actual_roe)} = {fmt_pct(net_margin)} × {fmt_mult(asset_turnover)} × {fmt_mult(equity_multiplier)}</p>

            <table>
                <thead>
                    <tr>
                        <th>Component</th>
                        <th>Formula</th>
                        <th>Value</th>
                    </tr>
                </thead>
                <tbody>
                    <tr>
                        <td><strong>Net Profit Margin</strong></td>
                        <td>Net Income / Revenue</td>
                        <td class="text-right">{fmt_pct(net_margin)}</td>
                    </tr>
                    <tr>
                        <td><strong>Asset Turnover</strong></td>
                        <td>Revenue / Assets</td>
                        <td class="text-right">{fmt_mult(asset_turnover)}</td>
                    </tr>
                    <tr>
                        <td><strong>Equity Multiplier</strong></td>
                        <td>Assets / Equity</td>
                        <td class="text-right">{fmt_mult(equity_multiplier)}</td>
                    </tr>
                    <tr class="highlight-row">
                        <td><strong>ROE</strong></td>
                        <td>Margin × Turnover × Multiplier</td>
                        <td class="text-right"><strong>{fmt_pct(actual_roe)}</strong></td>
                    </tr>
                </tbody>
            </table>

            <p style="margin-top: 0.5em; font-size: 9pt; color: #374151;">
                {driver_analysis}
            </p>
        '''

        return html

    def _generate_dupont_analysis(self, net_margin, asset_turnover, equity_multiplier, roe) -> str:
        """Generate LLM-powered DuPont analysis (one sentence)."""
        if not self.client:
            return self._fallback_dupont_analysis(net_margin, asset_turnover, equity_multiplier, roe)

        company_name = self.overview.get('name', self.ticker)
        industry = self.overview.get('industry', 'N/A')

        prompt = f"""{company_name} ({self.ticker}), {industry}.
DuPont: Margin={net_margin*100:.1f}%, Turnover={asset_turnover:.2f}x, Leverage={equity_multiplier:.2f}x, ROE={roe*100:.1f}%.

In ONE sentence: identify the primary ROE driver and why."""

        return self._llm(prompt, max_tokens=50)

    def _fallback_dupont_analysis(self, net_margin, asset_turnover, equity_multiplier, roe) -> str:
        """Fallback analysis when LLM is unavailable."""
        if not all([net_margin, asset_turnover, equity_multiplier]):
            return "Insufficient data for DuPont analysis."

        margin_contribution = net_margin / 0.10
        turnover_contribution = asset_turnover / 0.75
        leverage_contribution = equity_multiplier / 2.0

        if margin_contribution >= max(turnover_contribution, leverage_contribution):
            return f"<strong>Primary Driver:</strong> High net profit margin ({net_margin*100:.1f}%) indicates strong pricing power and cost efficiency."
        elif turnover_contribution >= leverage_contribution:
            return f"<strong>Primary Driver:</strong> Asset turnover ({asset_turnover:.2f}x) reflects efficient capital utilization."
        else:
            return f"<strong>Primary Driver:</strong> Financial leverage ({equity_multiplier:.2f}x) amplifies returns but increases risk."

    def _page4_valuation(self) -> str:
        
        current_price = self._safe(self.recommendation.get('current_price'), 100.0)
        fair_value = self._safe(self.recommendation.get('fair_value'))
        upside = self._safe(self.recommendation.get('upside_downside'))
        weights = self.recommendation.get('weights', {
            'dcf': 0.45,
            'multiples': 0.35,
            'ddm': 0.20
        })
        
        company_type = self.classification.get('company_type', 'balanced').title()
        
        dcf_value = self._safe(self.dcf_result.get('fair_value_per_share'))
        dcf_vs_current = ((dcf_value / current_price) - 1) if dcf_value and current_price else None
        
        mult_value = self._safe(self.multiples_result.get('average_fair_value'))
        mult_vs_current = ((mult_value / current_price) - 1) if mult_value and current_price else None
        
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
        
        html += f'''
                    <tr style="background-color: #fef3c7; font-weight: 600;">
                        <td>12-Month Target Price</td>
                        <td>{self._price(fair_value) if fair_value else 'N/A'}</td>
                        <td class="{'positive' if upside > 0 else 'negative'}">
                            {self._pct(upside)}
                        </td>
                        <td>100%</td>
                    </tr>
                </tbody>
            </table>
        '''
        
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
        
        valuation_narrative = self._generate_valuation_narrative()
        html += f'''
            <p style="text-align: justify; line-height: 1.6; margin-top: 1.5em;">
                <strong>Valuation Interpretation</strong><br><br>
                {valuation_narrative}
            </p>
            
            <h3 style="margin-top: 2em;">4.2 KEY VALUATION ASSUMPTIONS</h3>
        '''
        
        dcf_assumptions = self.dcf_result.get('assumptions', {})
        
        model_type = self.dcf_result.get('model_type', '3-stage')
        stage1_years = dcf_assumptions.get('stage1_years', 5)
        stage2_years = dcf_assumptions.get('stage2_years', 5)
        total_years = dcf_assumptions.get('total_projection_years', stage1_years + stage2_years)
        stage1_growth = dcf_assumptions.get('stage1_growth', 0)
        stage2_end_growth = dcf_assumptions.get('stage2_end_growth', 0.08)
        terminal_growth = dcf_assumptions.get('terminal_growth_rate', 0.025)
        wacc = dcf_assumptions.get('wacc', 0)
        beta = dcf_assumptions.get('beta', 1.0)
        risk_free = dcf_assumptions.get('risk_free_rate', 0.04)
        erp = dcf_assumptions.get('equity_risk_premium', 0.055)
        
        html += f'''
            <p><strong>DCF Methodology ({company_type} Company) - {model_type.upper()} MODEL:</strong></p>
            <ul style="line-height: 1.8;">
                <li>Stage 1 (High Growth): {stage1_years} years at {self._pct(stage1_growth)} growth</li>
                <li>Stage 2 (Fade Period): {stage2_years} years, declining to {self._pct(stage2_end_growth)}</li>
                <li>Terminal Growth: {self._pct(terminal_growth)}</li>
                <li>Total Projection Period: {total_years} years</li>
                <li>WACC: {self._pct(wacc)} (Cost of Equity: {self._pct(risk_free + beta * erp)}, Beta: {beta:.2f})</li>
            </ul>

            <p><strong>Multiples Approach (PEG-Adjusted):</strong></p>
            <ul style="line-height: 1.8;">
                <li>Peer Group: {', '.join(self.peer_tickers) if self.peer_tickers else 'N/A'}</li>
                <li>Metrics: PEG, P/B, EV/EBITDA</li>
                {self._get_peg_details()}
            </ul>
        '''
        
        html += self._scenario_analysis_section()
        
        return html
    
    def _get_peg_details(self) -> str:
        peg_analysis = self.multiples_result.get('peg_analysis', {})
        company_multiples = self.multiples_result.get('company_multiples', {})
        peer_averages = self.multiples_result.get('peer_averages', {})

        company_growth_yoy = company_multiples.get('revenue_growth')
        company_growth_cagr = company_multiples.get('revenue_growth_cagr')
        company_growth_capped = peg_analysis.get('company_growth_capped')
        growth_was_capped = peg_analysis.get('growth_was_capped', False)
        company_peg = company_multiples.get('peg')
        peer_avg_peg = peer_averages.get('avg_peg')
        peer_avg_growth = peer_averages.get('avg_growth')
        method_used = peg_analysis.get('method_used', 'Simple P/E')

        details = []

        if company_growth_cagr is not None:
            if growth_was_capped and company_growth_capped is not None:
                details.append(f'<li>Company Revenue CAGR: {self._pct(company_growth_cagr)} (capped to {self._pct(company_growth_capped)})</li>')
            else:
                details.append(f'<li>Company Revenue CAGR: {self._pct(company_growth_cagr)}</li>')
        elif company_growth_yoy is not None:
            if growth_was_capped and company_growth_capped is not None:
                details.append(f'<li>Company Revenue Growth: {self._pct(company_growth_yoy)} (capped to {self._pct(company_growth_capped)})</li>')
            else:
                details.append(f'<li>Company Revenue Growth: {self._pct(company_growth_yoy)}</li>')

        if peer_avg_growth is not None:
            details.append(f'<li>Peer Revenue CAGR: {self._pct(peer_avg_growth)}</li>')

        if company_peg is not None:
            details.append(f'<li>Company PEG: {company_peg:.2f}x</li>')

        if peer_avg_peg is not None:
            details.append(f'<li>Peer Avg PEG: {peer_avg_peg:.2f}x</li>')

        details.append(f'<li>Method: {method_used}</li>')

        return '\n                '.join(details)
    
    def _scenario_analysis_section(self) -> str:
        from src.analysis.dcf_valuation import DCFValuator
        from src.analysis.ddm_valuation import DDMValuator
        from config.settings import COMPANY_TYPE_WEIGHTS
        
        company_type = self.classification.get('company_type', 'balanced')
        weights = COMPANY_TYPE_WEIGHTS.get(company_type, COMPANY_TYPE_WEIGHTS['balanced'])
        dcf_weight = weights['dcf']
        mult_weight = weights['multiples']
        ddm_weight = weights['ddm']
        
        current_price = self.overview.get('price', 0) or 0
        
        multiples_fv = self.multiples_result.get('average_fair_value')
        
        dcf = DCFValuator(
            company_data=self.company_data,
            company_type=company_type,
            sector=self.overview.get('sector')
        )
        dcf_scenarios = dcf.get_scenario_analysis()
        
        ddm = DDMValuator(company_data=self.company_data)
        ddm_scenarios = ddm.get_scenario_analysis()
        ddm_applicable = ddm_scenarios.get('applicable', False)
        
        def fmt_price(v):
            return f"${v:,.2f}" if v else "N/A"
        
        def fmt_upside(v):
            if v is None:
                return "N/A"
            return f"{v*100:+.1f}%"
        
        def get_upside_class(upside):
            if upside is None:
                return ''
            if upside > 0.15:
                return 'class="positive"'
            elif upside < -0.10:
                return 'class="negative"'
            return ''
        
        scenario_results = {}
        
        for scenario_name in ['bear', 'base', 'bull']:
            dcf_data = dcf_scenarios['scenarios'].get(scenario_name, {})
            dcf_fv = dcf_data.get('fair_value')
            
            if ddm_applicable:
                ddm_data = ddm_scenarios['scenarios'].get(scenario_name, {})
                ddm_fv = ddm_data.get('fair_value')
            else:
                ddm_fv = None
            
            if ddm_fv is None and ddm_weight > 0:
                adj_dcf_weight = dcf_weight + (ddm_weight * dcf_weight / (dcf_weight + mult_weight)) if (dcf_weight + mult_weight) > 0 else dcf_weight
                adj_mult_weight = mult_weight + (ddm_weight * mult_weight / (dcf_weight + mult_weight)) if (dcf_weight + mult_weight) > 0 else mult_weight
            else:
                adj_dcf_weight = dcf_weight
                adj_mult_weight = mult_weight
            
            target_price = 0
            total_weight = 0
            
            if dcf_fv and dcf_fv > 0:
                target_price += dcf_fv * adj_dcf_weight
                total_weight += adj_dcf_weight
            
            if multiples_fv and multiples_fv > 0:
                target_price += multiples_fv * adj_mult_weight
                total_weight += adj_mult_weight
            
            if ddm_fv and ddm_fv > 0:
                target_price += ddm_fv * ddm_weight
                total_weight += ddm_weight
            
            if total_weight > 0 and total_weight < 1:
                target_price = target_price / total_weight
            
            if target_price > 0 and current_price > 0:
                upside = (target_price - current_price) / current_price
            else:
                upside = None
                target_price = None
            
            scenario_results[scenario_name] = {
                'dcf_fv': dcf_fv,
                'mult_fv': multiples_fv,
                'ddm_fv': ddm_fv,
                'target_price': target_price,
                'upside': upside,
            }
        
        bear = scenario_results['bear']
        base = scenario_results['base']
        bull = scenario_results['bull']
        
        html = f'''
            <h3 style="margin-top: 2em;">4.3 SCENARIO ANALYSIS</h3>
            
            <p>Target price sensitivity (weighted: DCF {dcf_weight*100:.0f}%, Multiples {mult_weight*100:.0f}%):</p>
            
            <table>
                <thead>
                    <tr>
                        <th>Scenario</th>
                        <th class="text-center">DCF</th>
                        <th class="text-center">Multiples</th>
                        <th class="text-center">Target Price</th>
                        <th class="text-center">vs Current</th>
                    </tr>
                </thead>
                <tbody>
                    <tr style="background: #fef2f2;">
                        <td><strong>Bear Case</strong></td>
                        <td class="text-center">{fmt_price(bear['dcf_fv'])}</td>
                        <td class="text-center">{fmt_price(bear['mult_fv'])}</td>
                        <td class="text-center"><strong>{fmt_price(bear['target_price'])}</strong></td>
                        <td class="text-center" {get_upside_class(bear['upside'])}>{fmt_upside(bear['upside'])}</td>
                    </tr>
                    <tr style="background: #f0fdf4;">
                        <td><strong>Base Case</strong></td>
                        <td class="text-center">{fmt_price(base['dcf_fv'])}</td>
                        <td class="text-center">{fmt_price(base['mult_fv'])}</td>
                        <td class="text-center"><strong>{fmt_price(base['target_price'])}</strong></td>
                        <td class="text-center" {get_upside_class(base['upside'])}>{fmt_upside(base['upside'])}</td>
                    </tr>
                    <tr style="background: #eff6ff;">
                        <td><strong>Bull Case</strong></td>
                        <td class="text-center">{fmt_price(bull['dcf_fv'])}</td>
                        <td class="text-center">{fmt_price(bull['mult_fv'])}</td>
                        <td class="text-center"><strong>{fmt_price(bull['target_price'])}</strong></td>
                        <td class="text-center" {get_upside_class(bull['upside'])}>{fmt_upside(bull['upside'])}</td>
                    </tr>
                </tbody>
            </table>
            
            <p style="font-size: 9pt; color: #6b7280; margin-top: 0.5em;">
                Current Price: {fmt_price(current_price)} | Multiples value fixed across scenarios
            </p>
            
            <p style="margin-top: 1em; padding: 10px; background: #f9fafb; border-left: 4px solid #6b7280;">
                <strong>Scenario Assumptions:</strong><br>
                <span style="font-size: 9pt;">
                • <strong>Bear:</strong> FCF/Dividend growth at 75% of base, discount rate +1.0%<br>
                • <strong>Base:</strong> Current growth trajectory and risk profile<br>
                • <strong>Bull:</strong> FCF/Dividend growth at 125% of base, discount rate -1.0%
                </span>
            </p>
        '''
        
        return html


    def _generate_valuation_narrative(self) -> str:
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
        if not self.client:
            return "The company's valuation reflects its competitive position within the industry peer group."
        
        company_multiples = self.multiples_result.get('company_multiples', {})
        peer_averages = self.multiples_result.get('peer_averages', {})
        
        pe = self._safe(company_multiples.get('pe'))
        peer_pe = self._safe(peer_averages.get('avg_pe'))
        ev_ebitda = self._safe(company_multiples.get('ev_ebitda'))
        peer_ev_ebitda = self._safe(peer_averages.get('avg_ev_ebitda'))
        
        revenue_growth = self._safe(self.ratios.get('revenue_growth'))
        gross_margin = self._safe(self.ratios.get('gross_margin'))
        operating_margin = self._safe(self.ratios.get('operating_margin'))
        roe = self._safe(self.ratios.get('roe'))
        
        pe_premium = ((pe / peer_pe) - 1) if (pe and peer_pe and peer_pe != 0) else 0

        industry = self.overview.get('industry', 'N/A')

        pe_str = f"{pe:.1f}x" if pe else "N/A"
        ev_ebitda_str = f"{ev_ebitda:.1f}x" if ev_ebitda else "N/A"
        peer_pe_str = f"{peer_pe:.1f}x" if peer_pe else "N/A"
        peer_ev_ebitda_str = f"{peer_ev_ebitda:.1f}x" if peer_ev_ebitda else "N/A"
        premium_str = f"{pe_premium*100:+.0f}%" if pe_premium else "N/A"
        
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


    def _page5_competitive_positioning(self) -> str:
        
        peer_multiples = self.multiples_result.get('peer_multiples', {})
        peer_averages = self.multiples_result.get('peer_averages', {})
        company_multiples = self.multiples_result.get('company_multiples', {})
        
        market_cap = self._safe(self.overview.get('market_cap'))
        company_peg = self._safe(company_multiples.get('peg'))
        ev_ebitda = self._safe(company_multiples.get('ev_ebitda'))
        pb = self._safe(company_multiples.get('pb'))

        peer_peg = self._safe(peer_averages.get('avg_peg'))
        peer_ev_ebitda = self._safe(peer_averages.get('avg_ev_ebitda'))
        peer_pb = self._safe(peer_averages.get('avg_pb'))

        html = f'''
            <h2>5. Competitive Positioning</h2>

            <h3>5.1 PEER COMPARISON MATRIX</h3>

            <p><strong>Industry:</strong> {self.overview.get('industry', 'N/A')}</p>

            <table>
                <thead>
                    <tr>
                        <th style="text-align: left;">COMPANY</th>
                        <th>MARKET CAP</th>
                        <th>PEG</th>
                        <th>EV/EBITDA</th>
                        <th>P/B</th>
                    </tr>
                </thead>
                <tbody>
                    <tr style="background-color: #eff6ff;">
                        <td><strong>{self.ticker}</strong></td>
                        <td>{self._num(market_cap)}</td>
                        <td>{self._mult(company_peg) if company_peg else 'N/A'}</td>
                        <td>{self._mult(ev_ebitda) if ev_ebitda else 'N/A'}</td>
                        <td>{self._mult(pb) if pb else 'N/A'}</td>
                    </tr>
        '''

        peer_market_caps = []
        peers_without_peg = []
        for peer_ticker in self.peer_tickers:
            peer_data = peer_multiples.get(peer_ticker, {})
            if peer_data:
                peer_mc = peer_data.get('market_cap')
                if peer_mc:
                    peer_market_caps.append(peer_mc)
                if peer_data.get('peg') is None:
                    peers_without_peg.append(peer_ticker)
                html += f'''
                    <tr>
                        <td>{peer_ticker}</td>
                        <td>{self._num(peer_data.get('market_cap'))}</td>
                        <td>{self._mult(peer_data.get('peg'))}</td>
                        <td>{self._mult(peer_data.get('ev_ebitda'))}</td>
                        <td>{self._mult(peer_data.get('pb'))}</td>
                    </tr>
                '''

        avg_market_cap = sum(peer_market_caps) / len(peer_market_caps) if peer_market_caps else None

        html += f'''
                    <tr style="background-color: #fef3c7; font-weight: 600;">
                        <td>Peer Average</td>
                        <td>{self._num(avg_market_cap) if avg_market_cap else '—'}</td>
                        <td>{self._mult(peer_peg) if peer_peg else 'N/A'}</td>
                        <td>{self._mult(peer_ev_ebitda) if peer_ev_ebitda else 'N/A'}</td>
                        <td>{self._mult(peer_pb) if peer_pb else 'N/A'}</td>
                    </tr>
                </tbody>
            </table>
        '''

        if peers_without_peg:
            html += f'''
            <p style="font-size: 8pt; color: #6b7280; margin-top: 8px;">
                <em>Note: PEG is N/A for {', '.join(peers_without_peg)} due to negative or insufficient revenue growth.</em>
            </p>
            '''

        html += '''
            <h3 style="margin-top: 2em;">5.2 OPERATING METRICS COMPARISON</h3>
            
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
        
        revenue_growth = self._safe(self.ratios.get('revenue_growth'))
        gross_margin = self._safe(self.ratios.get('gross_margin'))
        operating_margin = self._safe(self.ratios.get('operating_margin'))
        roe = self._safe(self.ratios.get('roe'))
        
        peer_rev_growth = 0.12
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
        
        competitive_narrative = self._generate_competitive_narrative()
        html += f'''
            <p style="text-align: justify; line-height: 1.6; margin-top: 1.5em;">
                <strong>Competitive Analysis</strong><br><br>
                {competitive_narrative}
            </p>
        '''
        
        return html

    
    def _page6_risk_assessment(self) -> str:
        
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
        
        risk_rows = []
        
        if upside < -0.30:
            risk_rows.append(('High', 'Valuation', f'Target {self._price(self.recommendation["fair_value"])} ({self._pct(upside)} downside)'))
        elif upside < -0.15:
            risk_rows.append(('Medium', 'Valuation', f'Target {self._price(self.recommendation["fair_value"])} ({self._pct(upside)} downside)'))
        
        if pb > 20:
            risk_rows.append(('High', 'Multiple', f'P/B {self._mult(pb)} reflects extreme expectations'))
        elif pe > 50:
            risk_rows.append(('Medium', 'Multiple', f'P/E {self._mult(pe)} above historical norms'))
        
        if revenue_growth < 0:
            risk_rows.append(('High', 'Growth', 'Revenue declining year-over-year'))
        elif revenue_growth > 0.50:
            risk_rows.append(('Medium', 'Growth', f'Revenue +{self._pct(revenue_growth)} may normalize (base effect)'))
        
        if risks['solvency_risk']:
            risk_rows.append(('High', 'Financial', 'Interest coverage below minimum threshold'))
        if risks['liquidity_risk']:
            risk_rows.append(('Medium', 'Financial', 'Current ratio indicates liquidity pressure'))
        if risks['leverage_risk']:
            risk_rows.append(('Medium', 'Financial', 'Elevated leverage may constrain flexibility'))
        
        if beta > 1.5:
            risk_rows.append(('Medium', 'Volatility', f'Beta {beta:.2f} amplifies market moves'))
        
        sector_risks = {
            'Technology': ('Medium', 'Competitive', 'Rapid innovation cycle; market share vulnerable'),
            'Energy': ('Medium', 'Regulatory', 'Export controls; geopolitical restrictions'),
            'Financial Services': ('Medium', 'Regulatory', 'Regulatory changes may impact profitability'),
        }
        
        for sector_key, (severity, category, signal) in sector_risks.items():
            if sector_key.lower() in sector.lower():
                risk_rows.append((severity, category, signal))
                break
        
        severity_order = {'High': 0, 'Medium': 1, 'Low': 2}
        risk_rows.sort(key=lambda x: severity_order.get(x[0], 3))
        
        risk_table_rows = ""
        for severity, category, signal in risk_rows:
            severity_class = f'risk-{severity.lower()}'
            risk_table_rows += f"""<tr>
                <td class="{severity_class}">{severity}</td>
                <td>{category}</td>
                <td>{signal}</td>
            </tr>"""
        
        risk_table = f"""
        <h3>6.1 KEY RISKS</h3>
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
    
    
    def _page7_recommendation(self) -> str:
        
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
                
        rec_class = f"rec-{rec.lower()}"
        upside_color = '#10b981' if upside > 0 else '#ef4444'
        
        rec_box = f"""
        <div class="rec-box {rec_class}">
            <div class="rec-title">INVESTMENT RECOMMENDATION: {rec}</div>
            <div class="rec-metrics">
                <div class="rec-metric">
                    <div class="rec-metric-label">12-Month Target</div>
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
        
        weights_text = f"DCF: {self._pct(weights['dcf'])} · Multiples: {self._pct(weights['multiples'])} · DDM: {self._pct(weights['ddm'])}"
        method_note = f"<p><strong>Valuation Method:</strong> {company_type.title()} ({weights_text})</p>"
        
        return rec_box + f"<p>{rationale}</p>" + method_note
    
    
    def _appendix_a_methodology(self) -> str:
        from config.settings import (
            COMPANY_TYPE_WEIGHTS,
            BUY_THRESHOLD,
            SELL_THRESHOLD,
            MIN_INTEREST_COVERAGE,
            MIN_CURRENT_RATIO
        )
        
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
    
    
    def _appendix_b_classification(self) -> str:
        from config.settings import COMPANY_TYPE_WEIGHTS
        
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

    def _appendix_c_limitations(self) -> str:
        return """
        <h2>Appendix C: Model Limitations</h2>

        <p style="margin-bottom: 10px;">This analysis has inherent limitations that users should consider:</p>

        <table>
            <thead>
                <tr>
                    <th>Category</th>
                    <th>Limitation</th>
                </tr>
            </thead>
            <tbody>
                <tr>
                    <td><strong>DCF Model</strong></td>
                    <td>Highly sensitive to growth rate assumptions; small changes significantly impact fair value</td>
                </tr>
                <tr>
                    <td><strong>Industry Metrics</strong></td>
                    <td>No sector-specific KPIs (ARR for SaaS, NIM for banks, same-store sales for retail)</td>
                </tr>
                <tr>
                    <td><strong>Peer Selection</strong></td>
                    <td>Based on market cap similarity, not business model or competitive positioning</td>
                </tr>
                <tr>
                    <td><strong>One-Time Items</strong></td>
                    <td>No adjustment for restructuring charges, asset impairments, or non-recurring gains</td>
                </tr>
                <tr>
                    <td><strong>Data Source</strong></td>
                    <td>Alpha Vantage free tier limited to 25 requests/day; some data may be delayed</td>
                </tr>
                <tr>
                    <td><strong>Beta</strong></td>
                    <td>Static beta from provider; not calculated from historical returns regression</td>
                </tr>
                <tr>
                    <td><strong>Qualitative Factors</strong></td>
                    <td>No assessment of management quality, competitive moat, or ESG considerations</td>
                </tr>
                <tr>
                    <td><strong>Earnings Quality</strong></td>
                    <td>No accruals analysis, cash conversion check, or revenue recognition review</td>
                </tr>
            </tbody>
        </table>
        """


    def generate_html_memo(self) -> str:
        
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
        appendix_c = self._appendix_c_limitations()

        print("  Complete!")
        
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
        <strong>Analyst:</strong> Idaliia Gafarova
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

    {appendix_c}

    <div style="margin-top: 50px; padding: 20px; background: #f9fafb; border-top: 2px solid #e5e7eb; text-align: center; font-size: 8pt; color: #6b7280;">
        <p><strong>Disclaimer:</strong> This investment memo was generated by an AI-powered equity research agent for educational purposes. All analysis is based on publicly available data and should not be considered as financial advice. Past performance does not guarantee future results. Please conduct your own due diligence and consult with a qualified financial advisor before making investment decisions.</p>
    </div>
</body>
</html>"""
        
        return html
    
    def save_memo(self, filepath: str, export_pdf: bool = True):
        html = self.generate_html_memo()
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(html)

        if export_pdf:
            pdf_path = filepath.replace('.html', '.pdf')
            self._export_to_pdf(filepath, pdf_path)

        return filepath

    def _export_to_pdf(self, html_path: str, pdf_path: str):
        """Export HTML to PDF using Playwright."""
        try:
            from playwright.sync_api import sync_playwright

            print(f"\n📑 Exporting to PDF...")

            with sync_playwright() as p:
                browser = p.chromium.launch()
                page = browser.new_page()
                page.goto(f'file://{html_path}')
                page.wait_for_load_state('networkidle')
                page.wait_for_timeout(500)
                page.pdf(
                    path=pdf_path,
                    format='A4',
                    margin={
                        'top': '20mm',
                        'bottom': '20mm',
                        'left': '15mm',
                        'right': '15mm'
                    },
                    print_background=True,
                    prefer_css_page_size=True
                )

                browser.close()

            print(f"   [OK] PDF saved: {pdf_path}")
            return pdf_path

        except ImportError:
            print("   [WARN] Playwright not installed. Run: pip install playwright && playwright install chromium")
            return None
        except Exception as e:
            print(f"   [ERROR] PDF export failed: {e}")
            return None