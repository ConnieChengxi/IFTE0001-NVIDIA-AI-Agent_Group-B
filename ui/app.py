#!/usr/bin/env python3
"""
Hybrid Investment Analyst — Streamlit UI

Launch from the project root:
    cd ui && streamlit run app.py
"""

import os
import sys
import json
from pathlib import Path

# ---------------------------------------------------------------------------
# Path setup — MUST happen before any orchestrator / component imports
# ---------------------------------------------------------------------------
_UI_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(_UI_DIR))

from utils.paths import setup_paths, PROJECT_ROOT, OUTPUT_DIR
setup_paths()

from dotenv import load_dotenv
load_dotenv(PROJECT_ROOT / ".env")

import streamlit as st

# ---------------------------------------------------------------------------
# Page config (must be the first Streamlit call)
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="Hybrid Investment Analyst",
    page_icon="H",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---------------------------------------------------------------------------
# CSS injection
# ---------------------------------------------------------------------------
from styles import inject_css
inject_css()

# ---------------------------------------------------------------------------
# Components
# ---------------------------------------------------------------------------
from components import (
    render_landing,
    run_analysis_with_progress,
    render_recommendation_hero,
    render_executive_summary,
    render_gate_status,
    render_investment_thesis,
    render_fundamental_section,
    render_technical_section,
    render_downloads,
    render_appendix,
)


# ===================================================================
# Helpers
# ===================================================================

def get_cached_tickers():
    """Return list of tickers with cached evidence files."""
    if not OUTPUT_DIR.exists():
        return []
    tickers = []
    for f in sorted(OUTPUT_DIR.glob("*_hybrid_evidence.json"), reverse=True):
        ticker = f.stem.replace("_hybrid_evidence", "")
        if ticker not in tickers:
            tickers.append(ticker)
    return tickers


def load_cached_evidence(ticker: str):
    """Load evidence JSON for a previously analysed ticker."""
    path = OUTPUT_DIR / f"{ticker}_hybrid_evidence.json"
    if path.exists():
        with open(path, "r") as f:
            return json.load(f)
    return None


# ===================================================================
# Sidebar
# ===================================================================

def render_sidebar():
    with st.sidebar:
        st.markdown("""
<div style="text-align:center; padding: 20px 0 8px 0;">
    <div style="font-size: 20px; font-weight: 800; color: #0f172a; letter-spacing: -0.5px;">Hybrid Investment</div>
    <div style="font-size: 20px; font-weight: 800; color: #0f172a; letter-spacing: -0.5px;">Analyst</div>
    <div style="font-size: 12px; color: #94a3b8; margin-top: 6px; font-weight: 500;">Fundamental + Technical</div>
</div>
""", unsafe_allow_html=True)

        st.divider()

        if not os.getenv("ALPHA_VANTAGE_API_KEY"):
            st.error("ALPHA_VANTAGE_API_KEY not found in .env")
            st.stop()

        ticker_input = st.text_input(
            "Stock Ticker",
            placeholder="e.g. NVDA, AAPL, MSFT",
        ).strip().upper()

        run_button = st.button(
            "Run Analysis", type="primary", use_container_width=True,
        )

        st.divider()
        cached = get_cached_tickers()
        selected_cached = ""
        if cached:
            st.markdown(
                '<p style="color:#64748b; font-size:12px; font-weight:600; '
                'text-transform:uppercase; letter-spacing:1px; margin-bottom:8px;">'
                'Previous Analyses</p>',
                unsafe_allow_html=True,
            )
            selected_cached = st.selectbox(
                "Load from cache",
                options=[""] + cached,
                format_func=lambda x: "Select ticker..." if x == "" else x,
                label_visibility="collapsed",
            )

        st.markdown('<div style="height: 40px;"></div>', unsafe_allow_html=True)
        st.markdown("""
<div style="text-align:center; padding: 16px 12px; background: #f8fafc; border-radius: 10px; border: 1px solid #e2e8f0;">
    <div style="font-size: 11px; color: #94a3b8; line-height: 1.5;">
        Dual-agent system using<br/>sequential gate architecture
    </div>
</div>
""", unsafe_allow_html=True)

    return ticker_input, run_button, selected_cached


# ===================================================================
# Main
# ===================================================================

def main():
    ticker_input, run_button, selected_cached = render_sidebar()

    evidence = st.session_state.get("evidence")
    current_ticker = st.session_state.get("current_ticker")

    # --- Run new analysis ---
    if run_button and ticker_input:
        try:
            evidence = run_analysis_with_progress(ticker_input)
            st.session_state["evidence"] = evidence
            st.session_state["current_ticker"] = ticker_input
            st.rerun()
        except Exception as e:
            st.error(f"Analysis failed: {e}")
            st.info(
                "Please verify the ticker symbol is valid (e.g. NVDA, AAPL, MSFT)"
            )
            return

    # --- Load from cache ---
    if selected_cached:
        cached_evidence = load_cached_evidence(selected_cached)
        if cached_evidence and (
            current_ticker != selected_cached or evidence is None
        ):
            st.session_state["evidence"] = cached_evidence
            st.session_state["current_ticker"] = selected_cached
            st.rerun()

    # --- Landing page (no evidence yet) ---
    if evidence is None:
        render_landing()
        return

    # --- Results dashboard ---
    render_recommendation_hero(evidence)
    render_executive_summary(evidence)
    render_gate_status(evidence)
    render_investment_thesis(evidence)
    render_fundamental_section(evidence)
    render_technical_section(evidence)
    render_downloads(current_ticker)
    render_appendix(evidence)

    st.markdown("""
<div class="disclaimer">
    <strong>Disclaimer:</strong> This report was generated by an AI-powered
    hybrid analysis agent for educational purposes only. Not financial advice.
    Past performance does not guarantee future results. Always consult a
    qualified financial advisor before making investment decisions.
</div>
""", unsafe_allow_html=True)


if __name__ == "__main__":
    main()
