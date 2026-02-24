"""Landing page component — shown before any analysis is run."""

import streamlit as st


def render_landing():
    """Render the dark landing page with 3 step cards."""
    st.markdown("""
<div class="landing-container">
    <div class="landing-badge">AI-Powered Analysis</div>
    <div class="landing-title">Hybrid Investment<br/>Analyst</div>
    <div class="landing-subtitle">
        Comprehensive stock analysis combining fundamental valuation
        with technical execution using dual-gate architecture.
    </div>
    <div class="landing-grid">
        <div class="landing-card">
            <div class="card-step">Step 1</div>
            <div class="card-title">Fundamental Agent</div>
            <div class="card-desc">DCF, Multiples, DDM valuation with 5-year ratio analysis and DuPont decomposition</div>
        </div>
        <div class="landing-card">
            <div class="card-step">Step 2</div>
            <div class="card-title">Technical Agent</div>
            <div class="card-desc">MA crossover backtest with regime filter, risk metrics and equity curves</div>
        </div>
        <div class="landing-card">
            <div class="card-step">Step 3</div>
            <div class="card-title">Dual-Gate Decision</div>
            <div class="card-desc">TRADE / WAIT / NO_TRADE recommendation based on both agents' consensus</div>
        </div>
    </div>
    <div class="landing-hint">
        Enter a ticker in the sidebar to begin
    </div>
</div>
""", unsafe_allow_html=True)
