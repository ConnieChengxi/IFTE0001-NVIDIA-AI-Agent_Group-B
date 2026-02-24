"""Appendix — Methodology component."""

import streamlit as st

from utils.formatters import fmt_price, fmt_ratio, fmt_multiple

# DCF model parameters by company type (mirrors dcf_valuation.py)
_DCF_PARAMS = {
    'growth':   {'model': '3-Stage', 's1': 5, 's2': 5, 's2_end': 0.08},
    'balanced': {'model': '3-Stage', 's1': 5, 's2': 3, 's2_end': 0.04},
    'dividend': {'model': '2-Stage', 's1': 5, 's2': 0, 's2_end': None},
    'cyclical': {'model': '2-Stage', 's1': 5, 's2': 0, 's2_end': None},
}


def render_appendix(evidence: dict):
    """Render the methodology appendix inside an expander."""
    fundamental = evidence.get("fundamental", {})
    valuation = fundamental.get("valuation", {})
    dcf = valuation.get("dcf", {})
    multiples = valuation.get("multiples", {})
    weights = valuation.get("weights", {})
    dcf_w = int((weights.get("dcf", 0.7)) * 100)
    mult_w = int((weights.get("multiples", 0.3)) * 100)

    company_type = fundamental.get("classification", {}).get("company_type", "balanced")
    params = _DCF_PARAMS.get(company_type, _DCF_PARAMS["balanced"])

    with st.expander("Appendix \u2014 Methodology", expanded=False):
        col_dcf, col_mult = st.columns(2)

        with col_dcf:
            # Build stage rows dynamically
            stage_rows = (
                f'<div class="method-row"><span class="method-label">Model</span>'
                f'<span class="method-value">{params["model"]} DCF</span></div>'
                f'<div class="method-row"><span class="method-label">WACC</span>'
                f'<span class="method-value">{fmt_ratio(dcf.get("wacc"))}</span></div>'
                f'<div class="method-row"><span class="method-label">Stage 1 — High Growth ({params["s1"]}y)</span>'
                f'<span class="method-value">{fmt_ratio(dcf.get("stage1_growth"))}</span></div>'
            )
            if params["s2"] > 0 and params["s2_end"] is not None:
                stage_rows += (
                    f'<div class="method-row"><span class="method-label">'
                    f'Stage 2 — Fade ({params["s2"]}y)</span>'
                    f'<span class="method-value">'
                    f'{fmt_ratio(dcf.get("stage1_growth"))} → {fmt_ratio(params["s2_end"])}'
                    f'</span></div>'
                )
            stage_rows += (
                f'<div class="method-row"><span class="method-label">Terminal Growth</span>'
                f'<span class="method-value">{fmt_ratio(dcf.get("terminal_growth"))}</span></div>'
                f'<div class="method-row result"><span class="method-label">Fair Value</span>'
                f'<span class="method-value">{fmt_price(dcf.get("fair_value"))}</span></div>'
            )

            st.markdown(
                f'<div class="method-card">'
                f'<div class="method-card-header">DCF Valuation'
                f'<span class="method-weight">{dcf_w}% weight</span></div>'
                f'{stage_rows}'
                f'</div>',
                unsafe_allow_html=True,
            )

        with col_mult:
            peer_avgs = multiples.get("peer_averages", {})
            ev_ebitda = multiples.get("ev_ebitda")
            pb = multiples.get("pb")
            peer_ev = peer_avgs.get("ev_ebitda")
            peer_pb = peer_avgs.get("pb")

            ev_str = f"{ev_ebitda:.1f}x" if ev_ebitda is not None else "N/A"
            pb_str = f"{pb:.1f}x" if pb is not None else "N/A"
            peer_ev_str = f"{peer_ev:.1f}x" if peer_ev is not None else "N/A"
            peer_pb_str = f"{peer_pb:.1f}x" if peer_pb is not None else "N/A"

            st.markdown(f"""
<div class="method-card">
<div class="method-card-header">Multiples Valuation<span class="method-weight">{mult_w}% weight</span></div>
<div class="method-row"><span class="method-label">PEG Ratio</span><span class="method-value">{fmt_multiple(multiples.get("peg"))} <span class="method-vs">vs {fmt_multiple(peer_avgs.get("peg"))}</span></span></div>
<div class="method-row"><span class="method-label">EV/EBITDA</span><span class="method-value">{ev_str} <span class="method-vs">vs {peer_ev_str}</span></span></div>
<div class="method-row"><span class="method-label">P/B Ratio</span><span class="method-value">{pb_str} <span class="method-vs">vs {peer_pb_str}</span></span></div>
<div class="method-row result"><span class="method-label">Fair Value</span><span class="method-value">{fmt_price(multiples.get("fair_value"))}</span></div>
</div>
""", unsafe_allow_html=True)

        if evidence.get("technical") is not None:
            st.markdown("""
<div class="method-card" style="margin-top:16px;">
<div class="method-card-header">Technical Strategy</div>
<div style="display:grid; grid-template-columns:1fr 1fr; gap:0;">
<div class="method-row"><span class="method-label">Strategy</span><span class="method-value">Long/Flat</span></div>
<div class="method-row"><span class="method-label">Regime Filter</span><span class="method-value">Close > MA200</span></div>
<div class="method-row"><span class="method-label">Entry Signal</span><span class="method-value">MA20 x MA50 up</span></div>
<div class="method-row"><span class="method-label">Exit Signal</span><span class="method-value">MA20 x MA50 down</span></div>
<div class="method-row"><span class="method-label">Stop Loss</span><span class="method-value">12% fixed</span></div>
<div class="method-row"><span class="method-label">Trailing Stop</span><span class="method-value">3.5x ATR(14)</span></div>
<div class="method-row"><span class="method-label">Costs</span><span class="method-value">10 bps round-trip</span></div>
<div class="method-row"><span class="method-label">Execution</span><span class="method-value">Signal +1 day</span></div>
</div>
</div>
""", unsafe_allow_html=True)
