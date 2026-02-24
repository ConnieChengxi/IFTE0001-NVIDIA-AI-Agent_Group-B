"""Investment thesis component."""

import streamlit as st

from src.reporting.html_report import _generate_investment_thesis


def render_investment_thesis(evidence: dict):
    """Render the blue-bordered investment thesis block."""
    thesis = _generate_investment_thesis(evidence)
    st.markdown(f"""
<div class="thesis-box">
    <div class="thesis-title">Investment Thesis</div>
    <div class="thesis-content">{thesis}</div>
</div>
""", unsafe_allow_html=True)
