"""Technical analysis section component.

Renders backtest performance, current market state,
strategy charts, and trade log.
"""

import os
from datetime import datetime
from pathlib import Path

import streamlit as st

from utils.formatters import fmt_pct, fmt_price, fmt_ratio
from utils.paths import TECH_DIR


def render_technical_section(evidence: dict):
    """Render the full technical analysis section (metrics + charts)."""
    technical = evidence.get("technical")
    if technical is None:
        return

    st.markdown(
        '<div class="section-header">Technical Analysis</div>',
        unsafe_allow_html=True,
    )

    metrics = technical.get("metrics", {})
    charts = technical.get("charts", {})

    # --- Backtest Performance (table, matching PDF report) ---
    cagr = metrics.get("CAGR")
    sharpe = metrics.get("Sharpe")
    max_dd = metrics.get("MaxDrawdown")
    hit_rate = metrics.get("HitRate")
    num_trades = metrics.get("NumTrades", "N/A")
    eq_mult = metrics.get("EquityMultiple")
    bh_mult = metrics.get("BuyHoldMultiple")

    st.markdown(f"""
<div class="section-subheader">Backtest Performance</div>
<table class="pro-table">
    <thead><tr><th>Metric</th><th class="right">Value</th></tr></thead>
    <tbody>
        <tr><td>CAGR (Compound Annual Growth Rate)</td><td class="right">{fmt_ratio(cagr)}</td></tr>
        <tr><td>Sharpe Ratio</td><td class="right">{f"{sharpe:.2f}" if sharpe is not None else "N/A"}</td></tr>
        <tr><td>Maximum Drawdown</td><td class="right">{fmt_ratio(max_dd)}</td></tr>
        <tr><td>Hit Rate</td><td class="right">{fmt_ratio(hit_rate)}</td></tr>
        <tr><td>Number of Trades</td><td class="right">{num_trades}</td></tr>
        <tr><td>Strategy Multiple (vs initial)</td><td class="right">{f"{eq_mult:.2f}x" if eq_mult is not None else "N/A"}</td></tr>
        <tr><td>Buy &amp; Hold Multiple</td><td class="right">{f"{bh_mult:.2f}x" if bh_mult is not None else "N/A"}</td></tr>
    </tbody>
</table>
""", unsafe_allow_html=True)

    # --- Strategy Charts (with descriptions matching PDF report) ---
    latest = technical.get("latest_state", {})
    ma20 = latest.get("ma20", 0)
    ma50 = latest.get("ma50", 0)
    ma200 = latest.get("ma200", 0)
    close = latest.get("close", 0)

    hr_val = (hit_rate or 0) * 100
    strat_m = f"{eq_mult:.2f}" if eq_mult is not None else "N/A"
    bh_m = f"{bh_mult:.2f}" if bh_mult is not None else "N/A"
    dd_val = (max_dd or 0) * 100
    trend_status = "uptrend" if ma20 > ma50 else "downtrend"
    regime_status = "bullish" if close > ma200 else "bearish"
    trend_sign = ">" if ma20 > ma50 else "<"

    chart_descriptions = {
        "golden_cross_trades": (
            f"MA200-based regime gate over the full backtest period. "
            f"Blue line: closing price, orange: MA50, green: MA200 (regime boundary). "
            f"Golden/Death Cross triangles mark regime transitions. "
            f"Green dots = entries, red crosses = exits. "
            f"Total {num_trades} trades with {hr_val:.0f}% hit rate."
        ),
        "equity_log_compare": (
            f"Log-scaled equity curves normalised to starting value of 1.0. "
            f"Buy-and-hold (blue): {bh_m}x multiple with full market exposure. "
            f"Strategy (orange): {strat_m}x multiple with conditional exposure. "
            f"Flat segments indicate periods when regime gate is closed "
            f"and capital is preserved."
        ),
        "drawdown_compare": (
            f"Strategy maximum drawdown of {dd_val:.1f}% compares favorably "
            f"to buy-and-hold, demonstrating shallower peak-to-trough losses. "
            f"MA200 regime filter exits positions during bearish phases, "
            f"prioritizing capital preservation while maintaining participation "
            f"in bullish trends."
        ),
        "price_ma_macd_6m": (
            f"Six-month price action with MA20/MA50/MA200 overlays. "
            f"Current trend: {trend_status} (MA20 {trend_sign} MA50), "
            f"regime: {regime_status}. Lower panel: MACD momentum analysis "
            f"\u2014 crossover above signal line indicates strengthening momentum."
        ),
    }

    chart_configs = [
        ("golden_cross_trades", "Trade Entry & Exit Points"),
        ("equity_log_compare", "Equity Comparison (Log Scale)"),
        ("drawdown_compare", "Drawdown Comparison"),
        ("price_ma_macd_6m", "Price with MAs & MACD (6 Months)"),
    ]

    st.markdown(
        '<div class="section-subheader">Strategy Charts</div>',
        unsafe_allow_html=True,
    )
    for chart_key, title in chart_configs:
        chart_path = charts.get(chart_key)
        if chart_path:
            full_path = (
                TECH_DIR / chart_path
                if not os.path.isabs(chart_path)
                else Path(chart_path)
            )
            if full_path.exists():
                desc = chart_descriptions.get(chart_key, "")
                st.markdown(
                    f'<div class="chart-wrapper">'
                    f'<div class="chart-title">{title}</div>'
                    f'</div>',
                    unsafe_allow_html=True,
                )
                st.image(str(full_path), use_container_width=True)
                if desc:
                    st.markdown(
                        f'<p style="color:#94a3b8; font-size:13px; '
                        f'line-height:1.7; margin:-8px 0 24px 0; '
                        f'padding:0 4px;">{desc}</p>',
                        unsafe_allow_html=True,
                    )

    # --- Trade Log ---
    _render_trade_log(technical)


def _render_trade_log(technical: dict):
    """Render the expandable trade log table."""
    all_trades = technical.get("all_trades", technical.get("trade_highlights", []))
    if not all_trades:
        return

    with st.expander("Trade Log", expanded=False):
        rows_html = ""
        for trade in all_trades:
            entry = trade.get("entry_date", "N/A")
            exit_date = trade.get("exit_date", "N/A")
            ret = trade.get("trade_metric_value", 0) or 0
            try:
                d1 = datetime.strptime(entry, "%Y-%m-%d")
                d2 = datetime.strptime(exit_date, "%Y-%m-%d")
                duration = f"{(d2 - d1).days} days"
            except Exception:
                duration = "\u2014"
            ret_color = "#4ade80" if ret > 0 else "#f87171"
            outcome = "Win" if ret > 0 else "Loss"
            rows_html += (
                f"<tr>"
                f"<td>{entry}</td><td>{exit_date}</td><td>{duration}</td>"
                f'<td class="right" style="color:{ret_color}">{ret * 100:+.1f}%</td>'
                f'<td style="color:{ret_color}">{outcome}</td>'
                f"</tr>"
            )

        st.markdown(f"""
<table class="pro-table">
    <thead><tr><th>Entry</th><th>Exit</th><th>Duration</th><th class="right">Return</th><th>Outcome</th></tr></thead>
    <tbody>{rows_html}</tbody>
</table>
""", unsafe_allow_html=True)
