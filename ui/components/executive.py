"""Executive summary component — 9 key metrics in 3 rows."""

import streamlit as st

from utils.formatters import fmt_pct, fmt_price, fmt_market_cap


def render_executive_summary(evidence: dict):
    """Render 9 key metrics summarising the analysis."""
    st.markdown(
        '<div class="section-header">Executive Summary</div>',
        unsafe_allow_html=True,
    )

    meta = evidence["meta"]
    rec = evidence["fundamental"]["recommendation"]
    risk = evidence["fundamental"].get("risk_factors", {})
    classification = evidence["fundamental"].get("classification", {})
    upside = rec.get("upside_downside") or 0

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Recommendation", rec.get("action", "N/A"))
    with col2:
        st.metric("Current Price", fmt_price(rec.get("current_price")))
    with col3:
        st.metric("Fair Value", fmt_price(rec.get("fair_value")))

    col4, col5, col6 = st.columns(3)
    with col4:
        st.metric("Upside / Downside", fmt_pct(upside))
    with col5:
        st.metric("Market Cap", fmt_market_cap(meta.get("market_cap")))
    with col6:
        health = "Strong" if not risk.get("has_risk_flags") else "Caution"
        st.metric("Financial Health", health)

    col7, col8, col9 = st.columns(3)
    with col7:
        st.metric("Sector", meta.get("sector", "N/A"))
    with col8:
        st.metric("Industry", meta.get("industry", "N/A"))
    with col9:
        company_type = classification.get("company_type", "N/A")
        st.metric("Company Type", company_type.title() if company_type else "N/A")
