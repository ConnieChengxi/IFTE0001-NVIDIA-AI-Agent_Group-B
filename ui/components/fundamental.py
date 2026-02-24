"""Fundamental analysis section component.

Renders valuation summary, sensitivity, historical ratios,
key financial ratios and risk assessment.
"""

import streamlit as st

from utils.formatters import fmt_pct, fmt_price, fmt_ratio, fmt_multiple


def render_fundamental_section(evidence: dict):
    """Render the full fundamental analysis section."""
    st.markdown(
        '<div class="section-header">Fundamental Analysis</div>',
        unsafe_allow_html=True,
    )

    fundamental = evidence.get("fundamental", {})
    valuation = fundamental.get("valuation", {})
    rec = fundamental.get("recommendation", {})
    ratios = fundamental.get("ratios", {})
    historical = fundamental.get("historical_ratios", [])
    risk = fundamental.get("risk_factors", {})
    peers = fundamental.get("peers", [])

    dcf = valuation.get("dcf", {})
    multiples = valuation.get("multiples", {})
    weights = valuation.get("weights", {})
    peers_str = ", ".join(peers[:3]) if peers else "N/A"

    # --- Valuation Summary ---
    st.markdown(f"""
<div class="section-subheader">Valuation Summary</div>
<table class="pro-table">
    <thead><tr><th>Method</th><th class="right">Fair Value</th><th class="right">Weight</th></tr></thead>
    <tbody>
        <tr>
            <td>DCF (Discounted Cash Flow)</td>
            <td class="right">{fmt_price(dcf.get("fair_value"))}</td>
            <td class="right">{int((weights.get("dcf", 0.7)) * 100)}%</td>
        </tr>
        <tr>
            <td>Multiples (Peers: {peers_str})</td>
            <td class="right">{fmt_price(multiples.get("fair_value"))}</td>
            <td class="right">{int((weights.get("multiples", 0.3)) * 100)}%</td>
        </tr>
        <tr class="highlight">
            <td>Weighted Fair Value</td>
            <td class="right">{fmt_price(rec.get("fair_value"))}</td>
            <td class="right">100%</td>
        </tr>
    </tbody>
</table>
""", unsafe_allow_html=True)

    # --- Valuation Sensitivity ---
    _render_sensitivity(evidence)

    # --- Historical Ratios ---
    if historical:
        _render_historical_ratios(historical)

    # --- Risk Assessment ---
    st.markdown(
        '<div class="section-subheader">Risk Assessment</div>',
        unsafe_allow_html=True,
    )
    if not risk.get("has_risk_flags"):
        st.markdown(
            '<span class="risk-ok">No Risk Flags Detected</span>',
            unsafe_allow_html=True,
        )
    else:
        flags_html = ""
        if risk.get("solvency_risk"):
            flags_html += '<span class="risk-flag">Solvency Risk (low interest coverage)</span> '
        if risk.get("liquidity_risk"):
            flags_html += '<span class="risk-flag">Liquidity Risk (low current ratio)</span> '
        if risk.get("leverage_risk"):
            flags_html += '<span class="risk-flag">Leverage Risk (high debt)</span> '
        if flags_html:
            st.markdown(flags_html, unsafe_allow_html=True)
        else:
            st.markdown(
                '<span class="risk-flag">Risk flags present</span>',
                unsafe_allow_html=True,
            )


def _render_sensitivity(evidence: dict):
    """Render bull / base / bear scenario table."""
    rec = evidence["fundamental"].get("recommendation", {})
    base_value = rec.get("fair_value") or 0
    current_price = rec.get("current_price") or 0

    scenarios = evidence["fundamental"].get("scenarios", {})
    if scenarios and scenarios.get("bear") and scenarios.get("bull"):
        bear = scenarios["bear"]
        base = scenarios["base"]
        bull = scenarios["bull"]
        bear_value = bear.get("target_price") or 0
        base_tp = base.get("target_price") or base_value
        bull_value = bull.get("target_price") or 0
        bear_upside = bear.get("upside") or 0
        base_upside = base.get("upside") or (rec.get("upside_downside") or 0)
        bull_upside = bull.get("upside") or 0
    elif base_value > 0 and current_price > 0:
        bear_value = base_value * 0.75
        bull_value = base_value * 1.25
        base_tp = base_value
        bear_upside = (bear_value - current_price) / current_price
        base_upside = (base_value - current_price) / current_price
        bull_upside = (bull_value - current_price) / current_price
    else:
        return

    if bear_value > 0 and bull_value > 0:
        st.markdown(f"""
<div class="section-subheader">Valuation Sensitivity</div>
<table class="pro-table">
    <thead><tr><th>Scenario</th><th class="right">Fair Value</th><th class="right">Upside</th></tr></thead>
    <tbody>
        <tr><td>Bear Case</td><td class="right">{fmt_price(bear_value)}</td><td class="right">{fmt_pct(bear_upside)}</td></tr>
        <tr class="highlight"><td>Base Case</td><td class="right">{fmt_price(base_tp)}</td><td class="right">{fmt_pct(base_upside)}</td></tr>
        <tr><td>Bull Case</td><td class="right">{fmt_price(bull_value)}</td><td class="right">{fmt_pct(bull_upside)}</td></tr>
    </tbody>
</table>
""", unsafe_allow_html=True)


def _render_historical_ratios(historical: list):
    """Render the 5-year historical ratios table."""
    years = [yr["year"] for yr in historical]

    all_metrics = [
        ("Profitability", None, None, None),
        ("Gross Margin", "profitability", "gross_margin", True),
        ("Operating Margin", "profitability", "operating_margin", True),
        ("Net Margin", "profitability", "net_margin", True),
        ("ROE", "profitability", "roe", True),
        ("ROA", "profitability", "roa", True),
        ("Leverage", None, None, None),
        ("Debt/Equity", "leverage", "debt_to_equity", True),
        ("Debt/Assets", "leverage", "debt_to_assets", True),
        ("Interest Coverage", "leverage", "interest_coverage", False),
        ("Liquidity", None, None, None),
        ("Current Ratio", "liquidity", "current_ratio", False),
        ("Quick Ratio", "liquidity", "quick_ratio", False),
    ]

    year_headers = "".join(f'<th class="right">{y}</th>' for y in years)
    rows_html = ""
    for item in all_metrics:
        label, section, key, is_pct = item
        if section is None:
            rows_html += (
                f'<tr class="category-row">'
                f'<td colspan="{len(years) + 1}">{label}</td></tr>'
            )
            continue
        cells = ""
        for yr in historical:
            val = yr.get(section, {}).get(key)
            if val is None:
                cells += '<td class="right">N/A</td>'
            elif is_pct:
                cells += f'<td class="right">{val * 100:.1f}%</td>'
            else:
                cells += f'<td class="right">{val:.1f}x</td>'
        rows_html += f"<tr><td>{label}</td>{cells}</tr>"

    st.markdown(f"""
<div class="section-subheader">Historical Financial Metrics (5-Year Trend)</div>
<table class="pro-table">
    <thead><tr><th>Metric</th>{year_headers}</tr></thead>
    <tbody>{rows_html}</tbody>
</table>
""", unsafe_allow_html=True)
