"""Dual-gate status table component."""

import streamlit as st


def render_gate_status(evidence: dict):
    """Render the Gate 1 / Gate 2 / Final Action table."""
    st.markdown(
        '<div class="section-header">Dual-Gate Status</div>',
        unsafe_allow_html=True,
    )

    gates = evidence["gates"]
    action = evidence["action"]
    g1 = gates["gate1"]
    g2 = gates["gate2"]

    g1_class = "gate-pass" if g1["status"] == "PASS" else "gate-fail"
    if g2["status"] == "PASS":
        g2_class = "gate-pass"
    elif g2["status"] == "WAIT":
        g2_class = "gate-wait"
    else:
        g2_class = "gate-fail"

    if action == "TRADE":
        a_class = "gate-pass"
    elif action == "WAIT":
        a_class = "gate-wait"
    else:
        a_class = "gate-fail"

    action_reason = (
        "Both gates passed \u2014 execute trade" if action == "TRADE"
        else "Wait for technical confirmation" if action == "WAIT"
        else "Fundamental thesis negative"
    )

    st.markdown(f"""
<table class="gate-table">
    <thead>
        <tr><th>Gate</th><th>Status</th><th>Rationale</th></tr>
    </thead>
    <tbody>
        <tr>
            <td>Gate 1 \u2014 Fundamental</td>
            <td><span class="{g1_class}">{g1["status"]}</span></td>
            <td>{g1["reason"]}</td>
        </tr>
        <tr>
            <td>Gate 2 \u2014 Technical</td>
            <td><span class="{g2_class}">{g2["status"]}</span></td>
            <td>{g2["reason"]}</td>
        </tr>
        <tr>
            <td>Final Action</td>
            <td><span class="{a_class}">{action}</span></td>
            <td>{action_reason}</td>
        </tr>
    </tbody>
</table>
""", unsafe_allow_html=True)
