"""Recommendation hero banner component."""

from datetime import datetime

import streamlit as st

from utils.formatters import fmt_pct, fmt_price, fmt_ratio


def render_recommendation_hero(evidence: dict):
    """Render the large action banner with key metrics."""
    action = evidence["action"]
    meta = evidence["meta"]
    rec = evidence["fundamental"]["recommendation"]
    technical = evidence.get("technical")
    tech_metrics = technical.get("metrics", {}) if technical else {}

    upside = rec.get("upside_downside") or 0
    cagr = tech_metrics.get("CAGR")
    sharpe = tech_metrics.get("Sharpe") or 0
    max_dd = tech_metrics.get("MaxDrawdown")

    if action == "TRADE":
        action_class = "trade"
        label = "ENTER LONG"
    elif action == "WAIT":
        action_class = "wait"
        label = "WAIT"
    else:
        action_class = "notrade"
        label = "NO TRADE"

    upside_class = "pos" if upside > 0 else "neg"

    date_str = meta.get("analysis_date", "")
    try:
        date_obj = datetime.strptime(date_str, "%Y-%m-%d")
        formatted_date = date_obj.strftime("%B %d, %Y")
    except Exception:
        formatted_date = date_str

    cagr_display = fmt_ratio(cagr) if cagr is not None else "N/A"
    sharpe_display = f"{sharpe:.2f}"
    max_dd_display = fmt_ratio(max_dd) if max_dd is not None else "N/A"

    st.markdown(f"""
<div class="rec-hero">
    <div class="left">
        <div class="action-label">Recommended Action</div>
        <div class="action-main {action_class}">{label}</div>
        <div class="action-sub">{meta["company_name"]} ({meta["ticker"]}) &middot; {formatted_date}</div>
    </div>
    <div class="right">
        <div class="mbox">
            <div class="mlabel">Entry Price</div>
            <div class="mval">{fmt_price(rec.get("current_price"))}</div>
        </div>
        <div class="mbox">
            <div class="mlabel">Target Price</div>
            <div class="mval">{fmt_price(rec.get("fair_value"))}</div>
        </div>
        <div class="mbox">
            <div class="mlabel">Upside</div>
            <div class="mval {upside_class}">{fmt_pct(upside)}</div>
        </div>
        <div class="mbox">
            <div class="mlabel">Strategy CAGR</div>
            <div class="mval">{cagr_display}</div>
        </div>
        <div class="mbox">
            <div class="mlabel">Sharpe Ratio</div>
            <div class="mval">{sharpe_display}</div>
        </div>
        <div class="mbox">
            <div class="mlabel">Max Drawdown</div>
            <div class="mval">{max_dd_display}</div>
        </div>
    </div>
</div>
""", unsafe_allow_html=True)
