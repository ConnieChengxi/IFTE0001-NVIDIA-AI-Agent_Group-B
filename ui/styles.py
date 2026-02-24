"""
All custom CSS for the Hybrid Investment Analyst Streamlit UI.
Extracted from the original monolithic app.py for maintainability.
"""

import streamlit as st

MAIN_CSS = """
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');

    /* ============ GLOBAL ============ */
    html, body, [class*="css"] {
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif !important;
    }
    .block-container {
        padding-top: 1.5rem;
        padding-bottom: 2rem;
        max-width: 1200px;
    }

    /* ============ SIDEBAR (LIGHT) ============ */
    section[data-testid="stSidebar"] {
        background: #ffffff;
        border-right: 1px solid #e2e8f0;
    }
    section[data-testid="stSidebar"] .stMarkdown p,
    section[data-testid="stSidebar"] .stMarkdown li,
    section[data-testid="stSidebar"] label {
        color: #334155 !important;
    }
    section[data-testid="stSidebar"] .stTextInput input {
        background: #f8fafc;
        border: 1px solid #e2e8f0;
        color: #0f172a;
        border-radius: 10px;
        padding: 12px 14px;
        font-size: 15px;
        font-weight: 500;
    }
    section[data-testid="stSidebar"] .stTextInput input::placeholder {
        color: #94a3b8;
    }
    section[data-testid="stSidebar"] .stTextInput input:focus {
        border-color: #3b82f6;
        box-shadow: 0 0 0 3px rgba(59,130,246,0.15);
    }
    section[data-testid="stSidebar"] .stSelectbox > div > div {
        background: #f8fafc;
        border: 1px solid #e2e8f0;
        color: #0f172a;
        border-radius: 10px;
    }
    section[data-testid="stSidebar"] hr {
        border-color: #e2e8f0;
    }

    /* Sidebar button */
    section[data-testid="stSidebar"] .stButton > button {
        background: linear-gradient(135deg, #0f172a 0%, #1e3a5f 100%);
        color: white;
        border: none;
        border-radius: 10px;
        padding: 12px 24px;
        font-weight: 600;
        font-size: 15px;
        letter-spacing: 0.3px;
        transition: all 0.2s ease;
        box-shadow: 0 4px 12px rgba(15,23,42,0.2);
    }
    section[data-testid="stSidebar"] .stButton > button:hover {
        background: linear-gradient(135deg, #1e293b 0%, #2d5a87 100%);
        box-shadow: 0 6px 20px rgba(15,23,42,0.3);
        transform: translateY(-1px);
    }

    /* ============ MAIN AREA (DARK) ============ */
    .stMainBlockContainer, [data-testid="stAppViewBlockContainer"] {
        background: #0b1121;
    }

    /* ============ LANDING PAGE ============ */
    .landing-container {
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        min-height: 70vh;
        padding: 40px 20px;
    }
    .landing-badge {
        display: inline-flex;
        align-items: center;
        background: rgba(59,130,246,0.12);
        color: #60a5fa;
        padding: 6px 16px;
        border-radius: 20px;
        font-size: 12px;
        font-weight: 600;
        letter-spacing: 0.5px;
        text-transform: uppercase;
        margin-bottom: 24px;
        border: 1px solid rgba(59,130,246,0.2);
    }
    .landing-title {
        font-size: 48px;
        font-weight: 800;
        color: #f1f5f9;
        text-align: center;
        line-height: 1.15;
        margin-bottom: 16px;
        letter-spacing: -1px;
    }
    .landing-subtitle {
        font-size: 18px;
        color: #64748b;
        text-align: center;
        max-width: 560px;
        line-height: 1.7;
        margin-bottom: 48px;
        font-weight: 400;
    }
    .landing-grid {
        display: grid;
        grid-template-columns: repeat(3, 1fr);
        gap: 24px;
        max-width: 900px;
        width: 100%;
        margin-bottom: 48px;
    }
    @media (max-width: 768px) {
        .landing-grid {
            grid-template-columns: 1fr;
            gap: 16px;
        }
        .landing-title {
            font-size: 32px;
        }
    }
    .landing-card {
        background: rgba(255,255,255,0.04);
        border: 1px solid rgba(255,255,255,0.08);
        border-radius: 16px;
        padding: 32px 24px 28px;
        text-align: center;
        transition: all 0.25s ease;
        position: relative;
        overflow: hidden;
    }
    .landing-card::before {
        content: '';
        position: absolute;
        top: 0; left: 0; right: 0;
        height: 3px;
        border-radius: 16px 16px 0 0;
    }
    .landing-card:nth-child(1)::before { background: linear-gradient(90deg, #2563eb, #3b82f6); }
    .landing-card:nth-child(2)::before { background: linear-gradient(90deg, #7c3aed, #8b5cf6); }
    .landing-card:nth-child(3)::before { background: linear-gradient(90deg, #059669, #10b981); }
    .landing-card:hover {
        transform: translateY(-4px);
        background: rgba(255,255,255,0.06);
        border-color: rgba(255,255,255,0.12);
    }
    .landing-card .card-step {
        font-size: 11px;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 1.5px;
        color: #64748b;
        margin-bottom: 10px;
    }
    .landing-card .card-title {
        font-size: 17px;
        font-weight: 700;
        color: #f1f5f9;
        margin-bottom: 10px;
    }
    .landing-card .card-desc {
        font-size: 13px;
        color: #94a3b8;
        line-height: 1.6;
    }
    .landing-hint {
        display: flex;
        align-items: center;
        gap: 8px;
        color: #475569;
        font-size: 13px;
    }

    /* ============ SECTION HEADERS ============ */
    .section-header {
        font-size: 20px;
        font-weight: 700;
        color: #f1f5f9;
        padding-bottom: 12px;
        border-bottom: 1px solid rgba(255,255,255,0.08);
        margin: 40px 0 20px 0;
    }
    .section-subheader {
        font-size: 15px;
        font-weight: 600;
        color: #cbd5e1;
        margin: 28px 0 14px 0;
        padding-left: 2px;
    }

    /* ============ RECOMMENDATION HERO ============ */
    .rec-hero {
        background: linear-gradient(135deg, #131b2e 0%, #1a2744 60%, #1e3a5f 100%);
        border: 1px solid rgba(255,255,255,0.06);
        border-radius: 16px;
        padding: 36px 40px;
        color: white;
        display: flex;
        justify-content: space-between;
        align-items: center;
        gap: 36px;
        margin-bottom: 32px;
        position: relative;
        overflow: hidden;
    }
    .rec-hero::after {
        content: '';
        position: absolute;
        top: -50%; right: -10%;
        width: 400px; height: 400px;
        border-radius: 50%;
        background: radial-gradient(circle, rgba(59,130,246,0.08) 0%, transparent 70%);
        pointer-events: none;
    }
    .rec-hero .left { flex: 1; position: relative; z-index: 1; }
    .rec-hero .right {
        display: grid;
        grid-template-columns: repeat(3, 1fr);
        gap: 12px;
        position: relative;
        z-index: 1;
    }
    @media (max-width: 900px) {
        .rec-hero {
            flex-direction: column;
            padding: 28px 24px;
        }
        .rec-hero .right {
            grid-template-columns: repeat(2, 1fr);
            width: 100%;
        }
    }
    .rec-hero .action-label {
        font-size: 11px;
        text-transform: uppercase;
        letter-spacing: 2px;
        opacity: 0.4;
        margin-bottom: 8px;
        font-weight: 500;
    }
    .rec-hero .action-main {
        font-size: 48px;
        font-weight: 800;
        line-height: 1.1;
        margin-bottom: 10px;
        letter-spacing: -1px;
    }
    .rec-hero .action-main.trade   { color: #4ade80; text-shadow: 0 0 40px rgba(74,222,128,0.2); }
    .rec-hero .action-main.wait    { color: #fbbf24; text-shadow: 0 0 40px rgba(251,191,36,0.2); }
    .rec-hero .action-main.notrade { color: #f87171; text-shadow: 0 0 40px rgba(248,113,113,0.2); }
    .rec-hero .action-sub {
        font-size: 15px;
        opacity: 0.5;
        font-weight: 400;
    }
    .rec-hero .mbox {
        background: rgba(255,255,255,0.04);
        border: 1px solid rgba(255,255,255,0.06);
        border-radius: 12px;
        padding: 22px 24px;
        text-align: center;
        min-width: 140px;
    }
    .rec-hero .mbox .mlabel {
        font-size: 10px;
        text-transform: uppercase;
        letter-spacing: 0.8px;
        opacity: 0.35;
        margin-bottom: 6px;
        font-weight: 500;
    }
    .rec-hero .mbox .mval {
        font-size: 22px;
        font-weight: 700;
        color: #e2e8f0;
    }

    /* ============ METRIC CARDS ============ */
    [data-testid="stMetric"] {
        background: rgba(255,255,255,0.03);
        border: 1px solid rgba(255,255,255,0.06);
        border-radius: 12px;
        padding: 20px 18px;
        transition: all 0.2s ease;
    }
    [data-testid="stMetric"]:hover {
        background: rgba(255,255,255,0.05);
        border-color: rgba(255,255,255,0.1);
    }
    [data-testid="stMetric"] label {
        font-size: 11px !important;
        color: #64748b !important;
        text-transform: uppercase;
        letter-spacing: 0.8px;
        font-weight: 600 !important;
    }
    [data-testid="stMetric"] [data-testid="stMetricValue"] {
        font-size: 22px !important;
        font-weight: 700 !important;
        color: #f1f5f9 !important;
    }

    /* ============ THESIS BOX ============ */
    .thesis-box {
        background: rgba(37,99,235,0.06);
        border-left: 4px solid #2563eb;
        padding: 24px 28px;
        border-radius: 0 12px 12px 0;
        margin: 20px 0 32px 0;
    }
    .thesis-box .thesis-title {
        font-size: 12px;
        font-weight: 700;
        color: #60a5fa;
        text-transform: uppercase;
        letter-spacing: 1px;
        margin-bottom: 14px;
    }
    .thesis-box .thesis-content {
        color: #cbd5e1;
        line-height: 1.85;
        font-size: 14px;
        text-align: justify;
    }

    /* ============ GATE TABLE ============ */
    .gate-table {
        width: 100%;
        border-collapse: separate;
        border-spacing: 0;
        font-size: 14px;
        margin: 12px 0 28px 0;
        border-radius: 12px;
        overflow: hidden;
        border: 1px solid rgba(255,255,255,0.06);
    }
    .gate-table th {
        background: rgba(255,255,255,0.03);
        color: #64748b;
        font-weight: 600;
        text-transform: uppercase;
        font-size: 11px;
        letter-spacing: 0.8px;
        padding: 14px 20px;
        text-align: left;
        border-bottom: 1px solid rgba(255,255,255,0.06);
    }
    .gate-table td {
        padding: 16px 20px;
        border-bottom: 1px solid rgba(255,255,255,0.04);
        color: #cbd5e1;
    }
    .gate-table tr:last-child td {
        font-weight: 600;
        background: rgba(59,130,246,0.06);
        border-bottom: none;
    }
    .gate-pass {
        display: inline-flex;
        align-items: center;
        color: #4ade80;
        font-weight: 700;
        background: rgba(74,222,128,0.1);
        padding: 4px 12px;
        border-radius: 6px;
        font-size: 12px;
        border: 1px solid rgba(74,222,128,0.15);
    }
    .gate-fail {
        display: inline-flex;
        align-items: center;
        color: #f87171;
        font-weight: 700;
        background: rgba(248,113,113,0.1);
        padding: 4px 12px;
        border-radius: 6px;
        font-size: 12px;
        border: 1px solid rgba(248,113,113,0.15);
    }
    .gate-wait {
        display: inline-flex;
        align-items: center;
        color: #fbbf24;
        font-weight: 700;
        background: rgba(251,191,36,0.1);
        padding: 4px 12px;
        border-radius: 6px;
        font-size: 12px;
        border: 1px solid rgba(251,191,36,0.15);
    }

    /* ============ PRO DATA TABLE ============ */
    .pro-table {
        width: 100%;
        border-collapse: separate;
        border-spacing: 0;
        font-size: 13px;
        margin: 12px 0 24px 0;
        border-radius: 12px;
        overflow: hidden;
        border: 1px solid rgba(255,255,255,0.06);
    }
    .pro-table th {
        background: rgba(255,255,255,0.03);
        color: #64748b;
        font-weight: 600;
        text-transform: uppercase;
        font-size: 11px;
        letter-spacing: 0.5px;
        padding: 13px 18px;
        text-align: left;
        border-bottom: 1px solid rgba(255,255,255,0.06);
    }
    .pro-table th.right, .pro-table td.right { text-align: right; }
    .pro-table td {
        padding: 13px 18px;
        border-bottom: 1px solid rgba(255,255,255,0.04);
        color: #cbd5e1;
    }
    .pro-table tr:last-child td { border-bottom: none; }
    .pro-table tr.highlight {
        font-weight: 600;
        background: rgba(59,130,246,0.06);
    }
    .pro-table tr.highlight td { color: #f1f5f9; }
    .pro-table tr:hover { background: rgba(255,255,255,0.02); }
    .pro-table .category-row {
        background: rgba(255,255,255,0.04);
        font-weight: 700;
        color: #94a3b8;
        font-size: 12px;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }
    .pro-table .category-row td { color: #94a3b8; }

    /* ============ CHART CONTAINERS ============ */
    .chart-wrapper {
        background: rgba(255,255,255,0.02);
        border: 1px solid rgba(255,255,255,0.06);
        border-radius: 12px;
        padding: 20px;
        margin: 16px 0;
    }
    .chart-wrapper .chart-title {
        font-weight: 600;
        color: #cbd5e1;
        margin-bottom: 12px;
        font-size: 14px;
    }

    /* ============ RISK BADGES ============ */
    .risk-ok {
        display: inline-flex;
        align-items: center;
        gap: 6px;
        background: rgba(74,222,128,0.1);
        color: #4ade80;
        padding: 8px 18px;
        border-radius: 8px;
        font-weight: 600;
        font-size: 13px;
        border: 1px solid rgba(74,222,128,0.15);
    }
    .risk-flag {
        display: inline-flex;
        align-items: center;
        gap: 6px;
        background: rgba(248,113,113,0.1);
        color: #f87171;
        padding: 8px 18px;
        border-radius: 8px;
        font-weight: 600;
        font-size: 13px;
        margin: 4px 6px 4px 0;
        border: 1px solid rgba(248,113,113,0.15);
    }

    /* ============ DOWNLOAD BUTTONS ============ */
    .stDownloadButton > button {
        background: rgba(255,255,255,0.06) !important;
        color: #e2e8f0 !important;
        border: 1px solid rgba(255,255,255,0.1) !important;
        border-radius: 10px !important;
        font-weight: 600 !important;
        font-size: 13px !important;
        padding: 10px 20px !important;
        transition: all 0.2s ease !important;
    }
    .stDownloadButton > button:hover {
        background: rgba(255,255,255,0.1) !important;
        border-color: rgba(255,255,255,0.15) !important;
        transform: translateY(-1px);
    }

    /* ============ EXPANDER ============ */
    [data-testid="stExpander"] {
        border: 1px solid rgba(255,255,255,0.06);
        border-radius: 12px;
    }
    [data-testid="stExpander"] summary {
        color: #cbd5e1;
    }

    /* ============ METHOD CARDS (Appendix) ============ */
    .method-card {
        background: rgba(255,255,255,0.03);
        border: 1px solid rgba(255,255,255,0.06);
        border-radius: 10px;
        overflow: hidden;
    }
    .method-card-header {
        display: flex;
        align-items: center;
        justify-content: space-between;
        padding: 12px 16px;
        font-size: 13px;
        font-weight: 700;
        color: #e2e8f0;
        background: rgba(255,255,255,0.04);
        border-bottom: 1px solid rgba(255,255,255,0.06);
        letter-spacing: 0.3px;
    }
    .method-weight {
        font-size: 11px;
        font-weight: 500;
        color: #64748b;
    }
    .method-row {
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding: 9px 16px;
        border-bottom: 1px solid rgba(255,255,255,0.04);
    }
    .method-row:last-child { border-bottom: none; }
    .method-row.result {
        background: rgba(59,130,246,0.06);
        border-bottom: none;
    }
    .method-label {
        font-size: 12px;
        color: #94a3b8;
    }
    .method-value {
        font-size: 12px;
        font-weight: 600;
        color: #e2e8f0;
    }
    .method-row.result .method-value {
        color: #60a5fa;
        font-size: 13px;
    }
    .method-vs {
        font-weight: 400;
        color: #64748b;
        font-size: 11px;
    }

    /* ============ MISC ============ */
    #MainMenu { visibility: hidden; }
    footer { visibility: hidden; }
    hr { margin: 32px 0; border-color: rgba(255,255,255,0.06); }

    .disclaimer {
        margin-top: 48px;
        padding: 18px 24px;
        background: rgba(255,255,255,0.02);
        border: 1px solid rgba(255,255,255,0.06);
        border-radius: 10px;
        font-size: 12px;
        color: #475569;
        line-height: 1.6;
    }
    .disclaimer strong { color: #64748b; }

    .stProgress > div > div > div {
        background: linear-gradient(90deg, #2563eb, #3b82f6);
        border-radius: 10px;
    }

    /* ============ ANALYSIS PROGRESS ============ */
    [data-testid="stStatusWidget"] {
        display: none !important;
    }

    .progress-container {
        max-width: 680px;
        margin: 40px auto 0;
    }
    .progress-title {
        font-size: 22px;
        font-weight: 700;
        color: #f1f5f9;
        margin-bottom: 28px;
        text-align: center;
    }
    .progress-title span {
        color: #60a5fa;
    }

    .step-row {
        display: flex;
        align-items: flex-start;
        gap: 16px;
        margin-bottom: 8px;
        padding: 14px 20px;
        border-radius: 10px;
        transition: all 0.3s ease;
    }
    .step-row.active {
        background: rgba(59,130,246,0.08);
        border: 1px solid rgba(59,130,246,0.18);
    }
    .step-row.done {
        opacity: 0.65;
    }
    .step-row.pending {
        opacity: 0.3;
    }

    .step-icon {
        width: 28px;
        height: 28px;
        border-radius: 50%;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 13px;
        font-weight: 700;
        flex-shrink: 0;
        margin-top: 1px;
    }
    .step-icon.done {
        background: rgba(74,222,128,0.15);
        color: #4ade80;
        border: 1.5px solid rgba(74,222,128,0.3);
    }
    .step-icon.active {
        background: rgba(59,130,246,0.15);
        color: #60a5fa;
        border: 1.5px solid rgba(59,130,246,0.3);
    }
    .step-icon.pending {
        background: rgba(255,255,255,0.04);
        color: #475569;
        border: 1.5px solid rgba(255,255,255,0.08);
    }

    .step-body {
        flex: 1;
    }
    .step-name {
        font-size: 14px;
        font-weight: 600;
        color: #e2e8f0;
        line-height: 1.3;
    }
    .step-row.pending .step-name {
        color: #475569;
    }
    .step-detail {
        font-size: 12px;
        color: #64748b;
        margin-top: 3px;
        line-height: 1.4;
    }
    .step-detail.pass { color: #4ade80; }
    .step-detail.fail { color: #f87171; }
    .step-detail.wait { color: #fbbf24; }

    .step-time {
        font-size: 11px;
        color: #475569;
        flex-shrink: 0;
        margin-top: 3px;
    }

    @keyframes pulse-dot {
        0%, 100% { opacity: 1; }
        50% { opacity: 0.4; }
    }
    .step-icon.active::after {
        content: '';
        display: block;
        width: 6px;
        height: 6px;
        border-radius: 50%;
        background: #60a5fa;
        animation: pulse-dot 1.2s ease-in-out infinite;
    }
    .step-icon.active span { display: none; }
    .step-icon.done span { display: none; }
    .step-icon.done::after { content: '\\2713'; }
    .step-icon.pending span { display: inline; }
"""


def inject_css():
    """Inject the full CSS stylesheet into the Streamlit page."""
    st.markdown(f"<style>{MAIN_CSS}</style>", unsafe_allow_html=True)
