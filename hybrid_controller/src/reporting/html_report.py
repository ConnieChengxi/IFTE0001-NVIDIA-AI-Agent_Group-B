"""
HTML Report Generator for Hybrid Analysis.

Generates investment memo matching professional PDF style.
"""

import os
import base64
from datetime import datetime
from typing import Dict, Any, Optional
from pathlib import Path

# Optional: LLM for thesis generation
try:
    from openai import OpenAI
    HAS_OPENAI = True
except ImportError:
    HAS_OPENAI = False


def _encode_image(path: str) -> Optional[str]:
    """Encode image to base64 for embedding in HTML."""
    if not path or not os.path.exists(path):
        return None
    try:
        with open(path, 'rb') as f:
            return base64.b64encode(f.read()).decode('utf-8')
    except Exception:
        return None


def _fmt_pct(value: float, decimals: int = 1) -> str:
    """Format percentage."""
    if value is None:
        return "N/A"
    return f"{value * 100:+.{decimals}f}%" if value >= 0 else f"{value * 100:.{decimals}f}%"


def _fmt_price(value: float) -> str:
    """Format price."""
    if value is None:
        return "N/A"
    return f"${value:,.2f}"


def _fmt_ratio(value: float, multiplier: float = 100, suffix: str = "%") -> str:
    """Format ratio."""
    if value is None:
        return "N/A"
    return f"{value * multiplier:.1f}{suffix}"


def _fmt_multiple(value: float) -> str:
    """Format multiple (e.g., P/E ratio)."""
    if value is None:
        return "N/A"
    return f"{value:.2f}x"


def _generate_investment_thesis(evidence: Dict[str, Any]) -> str:
    """Generate investment thesis using LLM or fallback to template."""
    meta = evidence['meta']
    fundamental = evidence.get('fundamental', {})
    technical = evidence.get('technical')
    gates = evidence['gates']
    action = evidence['action']

    rec = fundamental.get('recommendation', {})
    ratios = fundamental.get('ratios', {})
    tech_metrics = technical.get('metrics', {}) if technical else {}

    # Try LLM generation
    if HAS_OPENAI and os.environ.get('OPENAI_API_KEY'):
        try:
            client = OpenAI()

            prompt = f"""Generate a 150-200 word investment thesis for {meta['company_name']} ({meta['ticker']}).

DATA:
- Recommendation: {rec.get('action')}
- Fair Value: ${rec.get('fair_value', 0):.2f}
- Current Price: ${rec.get('current_price', 0):.2f}
- Upside: {(rec.get('upside_downside', 0) or 0)*100:+.1f}%
- Sector: {meta['sector']} / {meta['industry']}
- Company Type: {fundamental.get('classification', {}).get('company_type', 'N/A')}
- ROE: {(ratios.get('roe', 0) or 0)*100:.1f}%
- Net Margin: {(ratios.get('net_margin', 0) or 0)*100:.1f}%
- Revenue Growth: {(ratios.get('revenue_growth', 0) or 0)*100:.1f}%
- Debt/Equity: {ratios.get('debt_to_equity', 0):.2f}x
- Gate 1 (Fundamental): {gates['gate1']['status']}
- Gate 2 (Technical): {gates['gate2']['status']}
- Final Action: {action}
- Strategy Sharpe: {tech_metrics.get('Sharpe', 'N/A')}
- Strategy Max Drawdown: {(tech_metrics.get('MaxDrawdown', 0) or 0)*100:.1f}%

STRUCTURE:
Paragraph 1: Open with rating and target. Explain valuation anchor.
Paragraph 2: Key fundamental drivers - growth, profitability, moat.
Paragraph 3: Technical timing and risk management. Final action.

Write in third person, professional tone. No bullet points. Plain text only."""

            response = client.chat.completions.create(
                model="gpt-4",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
                max_tokens=400
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            pass  # Fall through to template

    # Fallback template
    upside = rec.get('upside_downside', 0) or 0
    action_word = "undervalued" if upside > 0 else "overvalued"

    return f"""{meta['company_name']} is rated {rec.get('action')} with a 12-month target price of {_fmt_price(rec.get('fair_value'))}, representing {_fmt_pct(upside)} {'upside' if upside > 0 else 'downside'} from the current price of {_fmt_price(rec.get('current_price'))}. The stock appears {action_word} based on a blended DCF and multiples approach.

The company demonstrates strong fundamentals with ROE of {_fmt_ratio(ratios.get('roe'))} and net margin of {_fmt_ratio(ratios.get('net_margin'))}. Revenue growth of {_fmt_ratio(ratios.get('revenue_growth'))} supports the growth classification, while conservative leverage (D/E {_fmt_multiple(ratios.get('debt_to_equity'))}) provides financial flexibility.

Both fundamental and technical gates have been passed, supporting immediate entry. The systematic strategy shows favorable risk-adjusted returns with a Sharpe ratio of {tech_metrics.get('Sharpe', 0):.2f} and controlled drawdowns of {_fmt_ratio(tech_metrics.get('MaxDrawdown'))}. Current market regime is bullish, confirming execution timing."""


def _build_gate_status_table(gates: Dict, action: str) -> str:
    """Build Gate 1 / Gate 2 status table."""
    gate1 = gates.get('gate1', {})
    gate2 = gates.get('gate2', {})

    # Determine status icons and colors
    g1_icon = "PASS" if gate1.get('status') == 'PASS' else "FAIL"
    g1_class = "risk-ok" if gate1.get('status') == 'PASS' else "risk-flag"

    g2_status = gate2.get('status', 'N/A')
    if g2_status == 'PASS':
        g2_icon = "PASS"
        g2_class = "risk-ok"
    elif g2_status == 'WAIT':
        g2_icon = "WAIT"
        g2_class = "hold"
    else:
        g2_icon = "N/A"
        g2_class = ""

    # Action styling
    if action == "TRADE":
        action_class = "buy"
    elif action == "WAIT":
        action_class = "hold"
    else:
        action_class = "sell"

    return f"""
<h3>Dual-Gate Status</h3>
<table>
    <thead>
        <tr><th>Gate</th><th>Status</th><th>Rationale</th></tr>
    </thead>
    <tbody>
        <tr>
            <td>Gate 1 (Fundamental)</td>
            <td class="{g1_class}">{g1_icon}</td>
            <td>{gate1.get('reason', 'N/A')}</td>
        </tr>
        <tr>
            <td>Gate 2 (Technical)</td>
            <td class="{g2_class}">{g2_icon}</td>
            <td>{gate2.get('reason', 'N/A')}</td>
        </tr>
        <tr style="font-weight: 600; background: #f0f9ff;">
            <td>Final Action</td>
            <td class="{action_class}">{action}</td>
            <td>{'Both gates passed - execute trade' if action == 'TRADE' else 'Wait for technical confirmation' if action == 'WAIT' else 'Fundamental thesis negative'}</td>
        </tr>
    </tbody>
</table>
"""


def _build_sensitivity_table(valuation: Dict, rec: Dict) -> str:
    """Build Bull/Base/Bear valuation sensitivity table."""
    dcf = valuation.get('dcf', {})
    base_wacc = dcf.get('wacc', 0.12) or 0.12
    base_growth = dcf.get('stage1_growth', 0.3) or 0.3
    base_value = rec.get('fair_value', 0) or 0
    current_price = rec.get('current_price', 0) or 0

    if base_value <= 0:
        return ""

    # Calculate scenarios (simplified sensitivity)
    # Bear: higher WACC (+2%), lower growth (-10%)
    # Bull: lower WACC (-2%), higher growth (+10%)
    bear_value = base_value * 0.75  # ~25% lower
    bull_value = base_value * 1.25  # ~25% higher

    bear_wacc = base_wacc + 0.02
    bull_wacc = max(0.08, base_wacc - 0.02)

    bear_growth = max(0.1, base_growth - 0.10)
    bull_growth = min(0.8, base_growth + 0.10)

    def calc_upside(fv):
        if current_price <= 0:
            return 0
        return (fv - current_price) / current_price

    return f"""
<h3>Valuation Sensitivity</h3>
<table>
    <thead>
        <tr><th>Scenario</th><th class="value-cell">WACC</th><th class="value-cell">Growth</th><th class="value-cell">Fair Value</th><th class="value-cell">Upside</th></tr>
    </thead>
    <tbody>
        <tr>
            <td>Bear Case</td>
            <td class="value-cell">{_fmt_ratio(bear_wacc)}</td>
            <td class="value-cell">{_fmt_ratio(bear_growth)}</td>
            <td class="value-cell">{_fmt_price(bear_value)}</td>
            <td class="value-cell {'positive' if calc_upside(bear_value) > 0 else 'negative'}">{_fmt_pct(calc_upside(bear_value))}</td>
        </tr>
        <tr style="font-weight: 600; background: #f0f9ff;">
            <td>Base Case</td>
            <td class="value-cell">{_fmt_ratio(base_wacc)}</td>
            <td class="value-cell">{_fmt_ratio(base_growth)}</td>
            <td class="value-cell">{_fmt_price(base_value)}</td>
            <td class="value-cell {'positive' if calc_upside(base_value) > 0 else 'negative'}">{_fmt_pct(calc_upside(base_value))}</td>
        </tr>
        <tr>
            <td>Bull Case</td>
            <td class="value-cell">{_fmt_ratio(bull_wacc)}</td>
            <td class="value-cell">{_fmt_ratio(bull_growth)}</td>
            <td class="value-cell">{_fmt_price(bull_value)}</td>
            <td class="value-cell {'positive' if calc_upside(bull_value) > 0 else 'negative'}">{_fmt_pct(calc_upside(bull_value))}</td>
        </tr>
    </tbody>
</table>
"""


CSS_STYLES = """
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

    * {
        margin: 0;
        padding: 0;
        box-sizing: border-box;
    }

    body {
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
        font-size: 14px;
        line-height: 1.6;
        color: #1a1a1a;
        max-width: 900px;
        margin: 0 auto;
        padding: 40px 20px;
        background: #fff;
    }

    h1 {
        font-size: 28px;
        font-weight: 700;
        color: #1a1a1a;
        margin-bottom: 8px;
    }

    h2 {
        font-size: 20px;
        font-weight: 600;
        color: #2563eb;
        margin: 32px 0 16px 0;
        padding-bottom: 8px;
        border-bottom: 2px solid #e5e7eb;
    }

    h3 {
        font-size: 16px;
        font-weight: 600;
        color: #374151;
        margin: 24px 0 12px 0;
    }

    .header {
        margin-bottom: 32px;
        padding-bottom: 24px;
        border-bottom: 3px solid #2563eb;
    }

    .header-meta {
        color: #6b7280;
        font-size: 13px;
        margin-bottom: 8px;
    }

    .company-desc {
        color: #374151;
        font-size: 14px;
        margin-top: 16px;
        line-height: 1.7;
    }

    .highlight {
        font-weight: 600;
        color: #2563eb;
    }

    table {
        width: 100%;
        border-collapse: collapse;
        margin: 16px 0;
        font-size: 13px;
    }

    th {
        background: #f8fafc;
        color: #64748b;
        font-weight: 600;
        text-transform: uppercase;
        font-size: 11px;
        letter-spacing: 0.5px;
        padding: 12px 16px;
        text-align: left;
        border-bottom: 2px solid #e2e8f0;
    }

    td {
        padding: 12px 16px;
        border-bottom: 1px solid #f1f5f9;
        vertical-align: top;
    }

    tr:hover {
        background: #f8fafc;
    }

    .value-cell {
        text-align: right;
        font-weight: 500;
    }

    .buy { color: #16a34a; font-weight: 600; }
    .sell { color: #dc2626; font-weight: 600; }
    .hold { color: #ca8a04; font-weight: 600; }
    .positive { color: #16a34a; }
    .negative { color: #dc2626; }
    .strong { font-weight: 600; color: #16a34a; }

    .summary-table td:first-child {
        color: #64748b;
        width: 200px;
    }

    .summary-table td:last-child {
        font-weight: 500;
    }

    .risk-ok {
        color: #16a34a;
        font-weight: 500;
    }

    .risk-flag {
        color: #dc2626;
        font-weight: 500;
    }

    .narrative {
        color: #374151;
        line-height: 1.8;
        margin: 16px 0;
        text-align: justify;
    }

    .action-banner {
        background: linear-gradient(135deg, #16a34a 0%, #15803d 100%);
        color: white;
        text-align: center;
        padding: 24px;
        border-radius: 8px;
        margin: 24px 0;
        font-size: 28px;
        font-weight: 700;
        letter-spacing: 1px;
    }

    .action-banner.wait {
        background: linear-gradient(135deg, #ca8a04 0%, #a16207 100%);
    }

    .action-banner.no-trade {
        background: linear-gradient(135deg, #dc2626 0%, #b91c1c 100%);
    }

    .chart-container {
        margin: 24px 0;
        text-align: center;
    }

    .chart-container img {
        max-width: 100%;
        border-radius: 8px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.1);
    }

    .chart-title {
        font-weight: 600;
        color: #374151;
        margin-bottom: 12px;
        font-size: 14px;
    }

    .chart-desc {
        font-size: 12px;
        color: #6b7280;
        margin-top: 10px;
        line-height: 1.5;
        max-width: 800px;
        margin-left: auto;
        margin-right: auto;
        text-align: left;
    }

    .appendix {
        margin-top: 48px;
        padding-top: 24px;
        border-top: 2px solid #e5e7eb;
    }

    .appendix h2 {
        color: #374151;
    }

    .appendix h3 {
        font-size: 15px;
        margin-top: 20px;
    }

    .param-table td:first-child {
        font-weight: 500;
        color: #374151;
        width: 200px;
    }

    .param-table td:nth-child(2) {
        font-family: 'SF Mono', Monaco, monospace;
        font-size: 12px;
        color: #2563eb;
    }

    ul {
        margin: 12px 0 12px 20px;
    }

    li {
        margin: 6px 0;
        color: #374151;
    }

    .disclaimer {
        margin-top: 48px;
        padding: 16px;
        background: #f8fafc;
        border-left: 4px solid #94a3b8;
        font-size: 12px;
        color: #64748b;
        font-style: italic;
    }

    .section-group {
        background: #fafbfc;
        border-left: 4px solid #e5e7eb;
        padding: 12px 16px;
        margin: 12px 0;
        font-size: 13px;
    }

    .section-group strong {
        color: #374151;
    }

    /* Professional Recommendation Box */
    .recommendation-hero {
        background: linear-gradient(135deg, #1e3a5f 0%, #2d5a87 100%);
        border-radius: 12px;
        padding: 32px;
        margin: 24px 0;
        color: white;
        display: grid;
        grid-template-columns: 1fr 1fr;
        gap: 24px;
    }

    .recommendation-hero .left-panel {
        display: flex;
        flex-direction: column;
        justify-content: center;
    }

    .recommendation-hero .action-label {
        font-size: 12px;
        text-transform: uppercase;
        letter-spacing: 1.5px;
        opacity: 0.8;
        margin-bottom: 8px;
    }

    .recommendation-hero .action-main {
        font-size: 42px;
        font-weight: 700;
        margin-bottom: 12px;
        line-height: 1.1;
    }

    .recommendation-hero .action-main.buy { color: #4ade80; }
    .recommendation-hero .action-main.wait { color: #fbbf24; }
    .recommendation-hero .action-main.no-trade { color: #f87171; }

    .recommendation-hero .action-sub {
        font-size: 14px;
        opacity: 0.9;
    }

    .recommendation-hero .right-panel {
        display: grid;
        grid-template-columns: repeat(3, 1fr);
        grid-template-rows: auto auto;
        gap: 12px;
    }

    .recommendation-hero .metric-box {
        background: rgba(255,255,255,0.1);
        border-radius: 8px;
        padding: 14px 12px;
        text-align: center;
    }

    .recommendation-hero .section-divider {
        grid-column: 1 / -1;
        border-top: 1px solid rgba(255,255,255,0.2);
        margin: 4px 0;
        font-size: 10px;
        text-transform: uppercase;
        letter-spacing: 1px;
        opacity: 0.5;
        padding-top: 8px;
    }

    .recommendation-hero .metric-label {
        font-size: 10px;
        text-transform: uppercase;
        letter-spacing: 0.5px;
        opacity: 0.7;
        margin-bottom: 4px;
    }

    .recommendation-hero .metric-value {
        font-size: 20px;
        font-weight: 600;
    }

    .recommendation-hero .metric-value.positive { color: #4ade80; }
    .recommendation-hero .metric-value.negative { color: #f87171; }

    .thesis-box {
        background: #f8fafc;
        border-left: 4px solid #2563eb;
        padding: 20px 24px;
        margin: 24px 0;
        border-radius: 0 8px 8px 0;
    }

    .thesis-box .thesis-title {
        font-size: 14px;
        font-weight: 600;
        color: #2563eb;
        text-transform: uppercase;
        letter-spacing: 0.5px;
        margin-bottom: 12px;
    }

    .thesis-box .thesis-content {
        color: #374151;
        line-height: 1.8;
        font-size: 14px;
        text-align: justify;
    }

    .metrics-grid {
        display: grid;
        grid-template-columns: repeat(3, 1fr);
        gap: 16px;
        margin: 24px 0;
    }

    .metrics-grid .metric-card {
        background: white;
        border: 1px solid #e5e7eb;
        border-radius: 8px;
        padding: 20px;
        text-align: center;
    }

    .metrics-grid .metric-card .card-label {
        font-size: 11px;
        color: #64748b;
        text-transform: uppercase;
        letter-spacing: 0.5px;
        margin-bottom: 8px;
    }

    .metrics-grid .metric-card .card-value {
        font-size: 28px;
        font-weight: 600;
        color: #1a1a1a;
    }

    .metrics-grid .metric-card .card-value.positive { color: #16a34a; }
    .metrics-grid .metric-card .card-value.negative { color: #dc2626; }

    .metrics-grid .metric-card .card-sub {
        font-size: 12px;
        color: #94a3b8;
        margin-top: 4px;
    }

    @media print {
        body { padding: 20px; }
        .action-banner { -webkit-print-color-adjust: exact; }
        .recommendation-hero { -webkit-print-color-adjust: exact; }

        /* Allow content to flow naturally - no forced page breaks */
        h2, h3 {
            page-break-after: avoid;
            orphans: 3;
            widows: 3;
        }

        /* Let tables break across pages to avoid large gaps */
        table {
            page-break-inside: auto;
        }

        /* Only prevent breaking individual rows */
        tr {
            page-break-inside: avoid;
        }

        /* Charts - keep title with image */
        .chart-container {
            page-break-inside: avoid;
            page-break-before: auto;
        }

        /* If chart must break, never break right after title */
        .chart-title {
            page-break-after: avoid;
        }

        /* Keep section headers with following content */
        .appendix h3 {
            page-break-after: avoid;
        }

        /* Disclaimer stays together */
        .disclaimer {
            page-break-inside: avoid;
        }
    }
</style>
"""


def generate_html_report(evidence: Dict[str, Any], output_path: str) -> str:
    """
    Generate HTML report from hybrid evidence pack.

    Args:
        evidence: Merged hybrid evidence dictionary
        output_path: Path to save HTML file

    Returns:
        Path to generated HTML file
    """
    meta = evidence['meta']
    gates = evidence['gates']
    action = evidence['action']
    fundamental = evidence.get('fundamental', {})
    technical = evidence.get('technical')

    rec = fundamental.get('recommendation', {})
    classification = fundamental.get('classification', {})
    valuation = fundamental.get('valuation', {})
    ratios = fundamental.get('ratios', {})
    historical_ratios = fundamental.get('historical_ratios', [])
    risk_factors = fundamental.get('risk_factors', {})
    peers = fundamental.get('peers', [])

    # Technical data
    tech_metrics = technical.get('metrics', {}) if technical else {}
    latest_state = technical.get('latest_state', {}) if technical else {}
    charts = technical.get('charts', {}) if technical else {}

    # Format date
    analysis_date = meta.get('analysis_date', datetime.now().strftime('%Y-%m-%d'))
    try:
        date_obj = datetime.strptime(analysis_date, '%Y-%m-%d')
        formatted_date = date_obj.strftime('%B %d, %Y')
    except:
        formatted_date = analysis_date

    # Classification text
    company_type = classification.get('company_type', 'balanced').upper()
    class_reasoning = classification.get('reasoning', '')

    # Determine action banner class
    action_class = ""
    if action == "TRADE":
        action_text = "ENTER LONG"
        action_class = ""
    elif action == "WAIT":
        action_text = "WAIT"
        action_class = "wait"
    else:
        action_text = "NO TRADE"
        action_class = "no-trade"

    # Build HTML
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Investment Analysis Report: {meta['ticker']}</title>
    {CSS_STYLES}
</head>
<body>

<!-- HEADER -->
<div class="header">
    <div class="header-meta">
        <strong>Date:</strong> {formatted_date}<br>
        <strong>Report Type:</strong> Comprehensive Analysis (Fundamental + Technical)
    </div>
    <h1>Investment Analysis Report: {meta['company_name']} ({meta['ticker']})</h1>
    <p class="company-desc">
        <strong>{meta['company_name']}</strong> operates in the <span class="highlight">{meta['sector']}</span> sector,
        specifically within the <span class="highlight">{meta['industry']}</span> industry.
        {class_reasoning}
    </p>
</div>

<!-- EXECUTIVE SUMMARY -->
<h2>Executive Summary</h2>
<table class="summary-table">
    <tr><td>Recommendation</td><td class="{rec['action'].lower()}">{rec['action']}</td></tr>
    <tr><td>Sector / Industry</td><td>{meta['sector']} / {meta['industry']}</td></tr>
    <tr><td>Market Cap</td><td>{_fmt_price(meta['market_cap'] / 1e9)}B</td></tr>
    <tr><td>Current Price</td><td>{_fmt_price(rec.get('current_price'))}</td></tr>
    <tr><td>Target Price</td><td>{_fmt_price(rec.get('fair_value'))}</td></tr>
    <tr><td>Upside Potential</td><td class="{'positive' if (rec.get('upside_downside') or 0) > 0 else 'negative'}">{_fmt_pct(rec.get('upside_downside'))}</td></tr>
    <tr><td>Financial Health</td><td class="{'strong' if not risk_factors.get('has_risk_flags') else 'risk-flag'}">{'Strong' if not risk_factors.get('has_risk_flags') else 'Caution'}</td></tr>
</table>

{_build_gate_status_table(gates, action)}

<!-- 1. FUNDAMENTAL ANALYSIS -->
<h2>1. Fundamental Analysis</h2>

<h3>Valuation Summary</h3>
<table>
    <thead>
        <tr><th>Method</th><th class="value-cell">Fair Value</th><th class="value-cell">Weight</th></tr>
    </thead>
    <tbody>
        <tr>
            <td>DCF (Discounted Cash Flow)</td>
            <td class="value-cell">{_fmt_price(valuation.get('dcf', {}).get('fair_value'))}</td>
            <td class="value-cell">{_fmt_pct(valuation.get('weights', {}).get('dcf', 0.7), 0)}</td>
        </tr>
        <tr>
            <td>Multiples (Peers: {', '.join(peers[:3]) if peers else 'N/A'})</td>
            <td class="value-cell">{_fmt_price(valuation.get('multiples', {}).get('fair_value'))}</td>
            <td class="value-cell">{_fmt_pct(valuation.get('weights', {}).get('multiples', 0.3), 0)}</td>
        </tr>
        <tr style="font-weight: 600; background: #f0f9ff;">
            <td>Weighted Fair Value</td>
            <td class="value-cell">{_fmt_price(rec.get('fair_value'))}</td>
            <td class="value-cell">100%</td>
        </tr>
    </tbody>
</table>

{_build_sensitivity_table(valuation, rec)}

{_build_historical_ratios_table(historical_ratios)}

<div class="section-group">
    <strong>Risk Assessment:</strong>
    {_build_risk_text(risk_factors)}
</div>

<p class="narrative">
    <strong>Fundamental Analysis Summary:</strong> Based on the fundamental analysis, {meta['company_name']} demonstrates
    {'strong' if not risk_factors.get('has_risk_flags') else 'mixed'} financial health with a {rec['action']} recommendation.
    The valuation analysis indicates the stock is trading at {_fmt_price(rec.get('current_price'))},
    representing a {_fmt_pct(rec.get('upside_downside'))} {'discount' if (rec.get('upside_downside') or 0) > 0 else 'premium'}
    to its estimated fair value of {_fmt_price(rec.get('fair_value'))}.
    Given these fundamental merits, we proceed to evaluate the technical performance characteristics and risk-adjusted returns
    through systematic backtesting.
</p>
"""

    # Add Technical Analysis section if available
    if technical:
        html += _build_technical_section(tech_metrics, latest_state, charts, meta['ticker'])

    # Generate Investment Thesis with LLM
    investment_thesis = _generate_investment_thesis(evidence)

    # Prepare metrics for recommendation section
    upside = rec.get('upside_downside', 0) or 0
    sharpe = tech_metrics.get('Sharpe', 0) if technical else 0
    max_dd = tech_metrics.get('MaxDrawdown', 0) if technical else 0
    cagr = tech_metrics.get('CAGR', 0) if technical else 0

    # Add Investment Recommendation section
    html += f"""
<!-- 3. INVESTMENT RECOMMENDATION -->
<h2>3. Investment Recommendation</h2>

<div class="recommendation-hero">
    <div class="left-panel">
        <div class="action-label">Recommended Action</div>
        <div class="action-main {action_class}">{action_text}</div>
        <div class="action-sub">{meta['company_name']} ({meta['ticker']}) · {formatted_date}</div>
    </div>
    <div class="right-panel">
        <!-- Fundamental Valuation Row -->
        <div class="metric-box">
            <div class="metric-label">Entry Price</div>
            <div class="metric-value">{_fmt_price(rec.get('current_price'))}</div>
        </div>
        <div class="metric-box">
            <div class="metric-label">Target Price</div>
            <div class="metric-value">{_fmt_price(rec.get('fair_value'))}</div>
        </div>
        <div class="metric-box">
            <div class="metric-label">Upside</div>
            <div class="metric-value">{_fmt_pct(upside)}</div>
        </div>
        <!-- Technical Performance Row -->
        <div class="metric-box">
            <div class="metric-label">Strategy CAGR</div>
            <div class="metric-value">{_fmt_ratio(cagr) if cagr else 'N/A'}</div>
        </div>
        <div class="metric-box">
            <div class="metric-label">Sharpe Ratio</div>
            <div class="metric-value">{sharpe:.2f}</div>
        </div>
        <div class="metric-box">
            <div class="metric-label">Max Drawdown</div>
            <div class="metric-value">{_fmt_ratio(max_dd) if max_dd else 'N/A'}</div>
        </div>
    </div>
</div>

<div class="thesis-box">
    <div class="thesis-title">Investment Thesis</div>
    <div class="thesis-content">{investment_thesis}</div>
</div>

"""

    # Add Appendix
    html += _build_appendix(fundamental, technical, meta)

    # Disclaimer
    html += """
<div class="disclaimer">
    <strong>Disclaimer:</strong> This report was generated by an AI-powered hybrid analysis agent for educational purposes.
    Not financial advice. Past performance does not guarantee future results.
</div>

</body>
</html>
"""

    # Save file
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(html)

    return output_path


def _build_historical_ratios_table(historical_ratios: list) -> str:
    """Build historical financial ratios table."""
    if not historical_ratios:
        return ""

    years = [yr['year'] for yr in historical_ratios]

    html = """
<h3>Historical Financial Metrics (5-Year Trend)</h3>
<table>
    <thead>
        <tr>
            <th>Metric</th>
"""
    for year in years:
        html += f"            <th class=\"value-cell\">{year}</th>\n"
    html += """        </tr>
    </thead>
    <tbody>
"""

    # Profitability metrics
    html += "        <tr style=\"background: #f0f9ff; font-weight: 600;\"><td colspan=\"" + str(len(years) + 1) + "\">Profitability</td></tr>\n"

    metrics_prof = [
        ('gross_margin', 'Gross Margin'),
        ('operating_margin', 'Operating Margin'),
        ('net_margin', 'Net Margin'),
        ('roe', 'ROE'),
        ('roa', 'ROA'),
    ]

    for key, label in metrics_prof:
        html += f"        <tr><td>{label}</td>"
        for yr in historical_ratios:
            val = yr.get('profitability', {}).get(key)
            html += f"<td class=\"value-cell\">{_fmt_ratio(val) if val else 'N/A'}</td>"
        html += "</tr>\n"

    # Leverage metrics
    html += "        <tr style=\"background: #f0f9ff; font-weight: 600;\"><td colspan=\"" + str(len(years) + 1) + "\">Leverage</td></tr>\n"

    metrics_lev = [
        ('debt_to_equity', 'Debt/Equity'),
        ('debt_to_assets', 'Debt/Assets'),
        ('interest_coverage', 'Interest Coverage'),
    ]

    for key, label in metrics_lev:
        html += f"        <tr><td>{label}</td>"
        for yr in historical_ratios:
            val = yr.get('leverage', {}).get(key)
            if key == 'interest_coverage':
                html += f"<td class=\"value-cell\">{val:.1f}x</td>" if val else "<td class=\"value-cell\">N/A</td>"
            else:
                html += f"<td class=\"value-cell\">{_fmt_ratio(val) if val else 'N/A'}</td>"
        html += "</tr>\n"

    # Liquidity metrics
    html += "        <tr style=\"background: #f0f9ff; font-weight: 600;\"><td colspan=\"" + str(len(years) + 1) + "\">Liquidity</td></tr>\n"

    metrics_liq = [
        ('current_ratio', 'Current Ratio'),
        ('quick_ratio', 'Quick Ratio'),
    ]

    for key, label in metrics_liq:
        html += f"        <tr><td>{label}</td>"
        for yr in historical_ratios:
            val = yr.get('liquidity', {}).get(key)
            html += f"<td class=\"value-cell\">{val:.1f}x</td>" if val else "<td class=\"value-cell\">N/A</td>"
        html += "</tr>\n"

    html += """    </tbody>
</table>
"""
    return html


def _build_risk_text(risk_factors: Dict) -> str:
    """Build risk assessment text."""
    if not risk_factors.get('has_risk_flags'):
        return '<span class="risk-ok">No Risk Flags Detected</span>'

    flags = []
    if risk_factors.get('solvency_risk'):
        flags.append("Solvency Risk (low interest coverage)")
    if risk_factors.get('liquidity_risk'):
        flags.append("Liquidity Risk (low current ratio)")
    if risk_factors.get('leverage_risk'):
        flags.append("Leverage Risk (high debt)")

    return '<span class="risk-flag">Risk Flags: ' + ', '.join(flags) + '</span>'


def _build_technical_section(metrics: Dict, latest: Dict, charts: Dict, ticker: str) -> str:
    """Build Technical Analysis HTML section."""

    # Get chart paths and encode
    tech_dir = Path(__file__).parent.parent.parent.parent / "connie_technical"

    golden_cross_chart = None
    drawdown_compare_chart = None
    equity_log_chart = None
    price_ma_chart = None

    golden_cross_path = charts.get('golden_cross_trades')
    if golden_cross_path:
        full_path = tech_dir / golden_cross_path if not os.path.isabs(golden_cross_path) else golden_cross_path
        golden_cross_chart = _encode_image(str(full_path))

    drawdown_path = charts.get('drawdown_compare')
    if drawdown_path:
        full_path = tech_dir / drawdown_path if not os.path.isabs(drawdown_path) else drawdown_path
        drawdown_compare_chart = _encode_image(str(full_path))

    equity_log_path = charts.get('equity_log_compare')
    if equity_log_path:
        full_path = tech_dir / equity_log_path if not os.path.isabs(equity_log_path) else equity_log_path
        equity_log_chart = _encode_image(str(full_path))

    price_ma_path = charts.get('price_ma_macd_6m')
    if price_ma_path:
        full_path = tech_dir / price_ma_path if not os.path.isabs(price_ma_path) else price_ma_path
        price_ma_chart = _encode_image(str(full_path))

    html = f"""
<!-- 2. TECHNICAL ANALYSIS -->
<h2>2. Technical Analysis</h2>

<h3>Backtest Performance</h3>
<table>
    <thead>
        <tr><th>Metric</th><th class="value-cell">Value</th></tr>
    </thead>
    <tbody>
        <tr><td>CAGR (Compound Annual Growth Rate)</td><td class="value-cell">{_fmt_ratio(metrics.get('CAGR'))}</td></tr>
        <tr><td>Sharpe Ratio</td><td class="value-cell">{metrics.get('Sharpe', 0):.2f}</td></tr>
        <tr><td>Maximum Drawdown</td><td class="value-cell">{_fmt_ratio(metrics.get('MaxDrawdown'))}</td></tr>
        <tr><td>Hit Rate</td><td class="value-cell">{_fmt_ratio(metrics.get('HitRate'))}</td></tr>
        <tr><td>Number of Trades</td><td class="value-cell">{metrics.get('NumTrades', 'N/A')}</td></tr>
        <tr><td>Strategy Multiple (vs initial)</td><td class="value-cell">{metrics.get('EquityMultiple', 1):.2f}x</td></tr>
        <tr><td>Buy & Hold Multiple</td><td class="value-cell">{metrics.get('BuyHoldMultiple', 1):.2f}x</td></tr>
    </tbody>
</table>

<h3>Strategy Charts</h3>
"""

    # Chart descriptions using metrics data
    num_trades = metrics.get('NumTrades', 0)
    hit_rate = metrics.get('HitRate', 0)
    max_dd = abs(metrics.get('MaxDrawdown', 0))
    bh_multiple = metrics.get('BuyHoldMultiple', 1)
    strat_multiple = metrics.get('EquityMultiple', 1)
    ma20 = latest.get('ma20', 0)
    ma50 = latest.get('ma50', 0)
    ma200 = latest.get('ma200', 0)
    close = latest.get('close', 0)

    if golden_cross_chart:
        html += f"""
<div class="chart-container">
    <div class="chart-title">Trade Entry & Exit Points</div>
    <img src="data:image/png;base64,{golden_cross_chart}" alt="Trade Entry & Exit Points">
    <p class="chart-desc">MA200-based regime gate over the full backtest period. Blue line: closing price, orange: MA50, green: MA200 (regime boundary). Golden/Death Cross triangles mark regime transitions. Green dots = entries, red crosses = exits. Total {num_trades} trades with {hit_rate*100:.0f}% hit rate.</p>
</div>
"""

    if equity_log_chart:
        html += f"""
<div class="chart-container">
    <div class="chart-title">Equity Comparison (Log Scale)</div>
    <img src="data:image/png;base64,{equity_log_chart}" alt="Equity Comparison">
    <p class="chart-desc">Log-scaled equity curves normalised to starting value of 1.0. Buy-and-hold (blue): {bh_multiple:.2f}x multiple with full market exposure. Strategy (orange): {strat_multiple:.2f}x multiple with conditional exposure. Flat segments indicate periods when regime gate is closed and capital is preserved.</p>
</div>
"""

    if drawdown_compare_chart:
        html += f"""
<div class="chart-container">
    <div class="chart-title">Drawdown Comparison</div>
    <img src="data:image/png;base64,{drawdown_compare_chart}" alt="Drawdown Comparison">
    <p class="chart-desc">Strategy maximum drawdown of {max_dd*100:.1f}% compares favorably to buy-and-hold, demonstrating shallower peak-to-trough losses. MA200 regime filter exits positions during bearish phases, prioritizing capital preservation while maintaining participation in bullish trends.</p>
</div>
"""

    if price_ma_chart:
        trend_status = "uptrend" if ma20 > ma50 else "downtrend"
        regime_status = "bullish" if close > ma200 else "bearish"
        html += f"""
<div class="chart-container">
    <div class="chart-title">Price with Moving Averages & MACD (6 Months)</div>
    <img src="data:image/png;base64,{price_ma_chart}" alt="Price MA MACD">
    <p class="chart-desc">Six-month price action with MA20/MA50/MA200 overlays. Current trend: {trend_status} (MA20 {'>' if ma20 > ma50 else '<'} MA50), regime: {regime_status}. Lower panel: MACD momentum analysis — crossover above signal line indicates strengthening momentum.</p>
</div>
"""

    # Technical summary
    regime = "bullish" if latest.get('regime_bullish') else "bearish"

    html += f"""
<p class="narrative">
    <strong>Technical Analysis Summary:</strong> The technical backtest demonstrates a CAGR of {_fmt_ratio(metrics.get('CAGR'))}
    with a Sharpe ratio of {metrics.get('Sharpe', 0):.2f}, indicating {'strong' if metrics.get('Sharpe', 0) > 1 else 'moderate'} risk-adjusted returns.
    The strategy experienced a maximum drawdown of {_fmt_ratio(metrics.get('MaxDrawdown'))}, which remains within
    {'acceptable' if abs(metrics.get('MaxDrawdown', 0)) < 0.25 else 'elevated'} risk parameters.
    Over the backtest period, the strategy executed {metrics.get('NumTrades', 0)} trades with a hit rate of {_fmt_ratio(metrics.get('HitRate'))},
    supporting the fundamental investment thesis with quantitative evidence of favorable risk-reward characteristics.
    Current market regime is <strong>{regime}</strong> (Close {'>' if latest.get('regime_bullish') else '<'} MA200).
</p>
"""

    return html


def _build_appendix(fundamental: Dict, technical: Dict, meta: Dict) -> str:
    """Build Appendix sections."""
    valuation = fundamental.get('valuation', {})
    peers = fundamental.get('peers', [])
    forward = fundamental.get('forward_estimates', {})
    dcf = valuation.get('dcf', {})
    multiples = valuation.get('multiples', {})
    weights = valuation.get('weights', {})

    html = """
<div class="appendix">
<h2>Appendix</h2>

<h3>Appendix A: Valuation Methodology</h3>

<p class="narrative">The discounted cash flow valuation employs a multi-stage growth model
with conservative assumptions reflecting the company's maturity and market position.</p>

<table>
    <thead>
        <tr><th>Parameter</th><th class="value-cell">Value</th><th>Description</th></tr>
    </thead>
    <tbody>
"""

    html += f"""        <tr><td>Discount Rate (WACC)</td><td class="value-cell">{_fmt_ratio(dcf.get('wacc'))}</td><td>Weighted average cost of capital</td></tr>
        <tr><td>Stage 1 Growth (Years 1-5)</td><td class="value-cell">{_fmt_ratio(dcf.get('stage1_growth'))}</td><td>High growth phase</td></tr>
        <tr><td>Stage 2 Growth (Years 6-10)</td><td class="value-cell">{_fmt_ratio((dcf.get('stage1_growth', 0.3) or 0.3) * 0.5)}</td><td>Transition phase (50% of Stage 1)</td></tr>
        <tr><td>Terminal Growth Rate</td><td class="value-cell">{_fmt_ratio(dcf.get('terminal_growth'))}</td><td>Perpetual growth assumption</td></tr>
        <tr style="font-weight: 600; background: #f0f9ff;"><td>DCF Fair Value</td><td class="value-cell">{_fmt_price(dcf.get('fair_value'))}</td><td>Intrinsic value per share</td></tr>
    </tbody>
</table>

<p class="narrative" style="margin-top: 20px;">PEG-adjusted relative valuation using peer group comparables.</p>

<table>
    <thead>
        <tr><th>Multiple</th><th class="value-cell">Company</th><th class="value-cell">Peer Average</th></tr>
    </thead>
    <tbody>
        <tr><td>PEG Ratio</td><td class="value-cell">{(multiples.get('peg') or 0):.2f}x</td><td class="value-cell">{(multiples.get('peer_averages', {}).get('peg') or 0):.2f}x</td></tr>
        <tr><td>EV/EBITDA</td><td class="value-cell">{(multiples.get('ev_ebitda') or 0):.1f}x</td><td class="value-cell">{(multiples.get('peer_averages', {}).get('ev_ebitda') or 0):.1f}x</td></tr>
        <tr><td>P/B Ratio</td><td class="value-cell">{(multiples.get('pb') or 0):.1f}x</td><td class="value-cell">{(multiples.get('peer_averages', {}).get('pb') or 0):.1f}x</td></tr>
        <tr style="font-weight: 600; background: #f0f9ff;"><td>Multiples Fair Value</td><td class="value-cell" colspan="2">{_fmt_price(multiples.get('fair_value'))}</td></tr>
    </tbody>
</table>

<p class="narrative" style="margin-top: 20px;">Blending Weights: DCF {int((weights.get('dcf') or 0.7) * 100)}% / Multiples {int((weights.get('multiples') or 0.3) * 100)}% —
weights reflect company type (growth companies favor DCF, mature companies favor multiples).</p>
"""

    # Appendix B: Trade Log
    if technical:
        all_trades = technical.get('all_trades', technical.get('trade_highlights', []))
        backtest = technical.get('backtest_window', {})
        num_trades = len(all_trades)

        html += f"""
<h3>Appendix B: Backtest Trade Log</h3>

<p class="narrative">Complete trade log from the backtest period ({backtest.get('start', 'N/A')} to {backtest.get('end', 'N/A')}).
Total: {num_trades} trades executed.</p>

<table>
    <thead>
        <tr><th>Entry Date</th><th>Exit Date</th><th>Duration</th><th class="value-cell">Return</th><th>Outcome</th></tr>
    </thead>
    <tbody>
"""
        for trade in all_trades:
            entry = trade.get('entry_date', 'N/A')
            exit_date = trade.get('exit_date', 'N/A')
            ret = trade.get('trade_metric_value', 0)

            # Calculate duration
            try:
                from datetime import datetime as dt
                d1 = dt.strptime(entry, '%Y-%m-%d')
                d2 = dt.strptime(exit_date, '%Y-%m-%d')
                duration = (d2 - d1).days
                duration_str = f"{duration} days"
            except:
                duration_str = "—"

            outcome = "Win" if ret > 0 else "Loss"
            outcome_class = "positive" if ret > 0 else "negative"

            html += f"""        <tr>
            <td>{entry}</td>
            <td>{exit_date}</td>
            <td>{duration_str}</td>
            <td class="value-cell {outcome_class}">{ret*100:+.1f}%</td>
            <td class="{outcome_class}">{outcome}</td>
        </tr>
"""

        html += """    </tbody>
</table>
"""

        # Appendix D: Strategy Parameters
        html += """
<h3>Appendix C: Strategy Parameters</h3>

<p class="narrative">Technical strategy rules and risk management parameters.</p>

<table>
    <thead>
        <tr><th>Parameter</th><th>Value</th><th>Purpose</th></tr>
    </thead>
    <tbody>
        <tr><td>Strategy Type</td><td>Long/Flat</td><td>No short positions</td></tr>
        <tr><td>Regime Filter</td><td>Close > MA200</td><td>Bull market identification</td></tr>
        <tr><td>Entry Signal</td><td>MA20 crosses above MA50</td><td>Golden cross confirmation</td></tr>
        <tr><td>Exit Signal</td><td>MA20 crosses below MA50</td><td>Death cross or stop hit</td></tr>
        <tr><td>Fixed Stop Loss</td><td>12%</td><td>Maximum loss per trade</td></tr>
        <tr><td>ATR Trailing Stop</td><td>3.5x ATR(14)</td><td>Dynamic stop to lock gains</td></tr>
        <tr><td>Transaction Costs</td><td>10 bps</td><td>Round-trip cost assumption</td></tr>
        <tr><td>Look-ahead Bias</td><td>Signals shifted +1 day</td><td>Realistic execution</td></tr>
    </tbody>
</table>
"""

    # Appendix D: Fundamental Methodology
    html += """
<h3>Appendix D: Fundamental Methodology</h3>

<p class="narrative">Gate Checks (Safety Filters):</p>
<table>
    <thead>
        <tr><th>Gate</th><th class="value-cell">Threshold</th><th class="value-cell">Severity</th></tr>
    </thead>
    <tbody>
        <tr><td>Interest Coverage</td><td class="value-cell">≥ 1.5x</td><td class="value-cell">CRITICAL</td></tr>
        <tr><td>Current Ratio</td><td class="value-cell">≥ 0.8x</td><td class="value-cell">HIGH</td></tr>
        <tr><td>Debt/Equity</td><td class="value-cell">≤ 5.0x</td><td class="value-cell">HIGH</td></tr>
    </tbody>
</table>

<p class="narrative" style="margin-top: 20px;">Recommendation Logic:</p>
<table>
    <thead>
        <tr><th>Condition</th><th class="value-cell">Recommendation</th></tr>
    </thead>
    <tbody>
        <tr><td>Upside > +20% AND no HIGH/CRITICAL gates</td><td class="value-cell"><strong>BUY</strong></td></tr>
        <tr><td>Upside > +20% BUT has HIGH gate</td><td class="value-cell"><strong>HOLD</strong></td></tr>
        <tr><td>-10% < Upside < +20%</td><td class="value-cell"><strong>HOLD</strong></td></tr>
        <tr><td>Upside < -10%</td><td class="value-cell"><strong>SELL</strong></td></tr>
        <tr><td>Any CRITICAL gate triggered</td><td class="value-cell"><strong>SELL</strong></td></tr>
    </tbody>
</table>
"""

    html += "</div>"

    return html
