"""Analysis progress component — animated step tracker."""

import time as _time
import json

import streamlit as st

from utils.paths import OUTPUT_DIR
from src.orchestrator import (
    run_fundamental_agent,
    run_technical_agent,
    check_gate1,
    check_gate2,
    merge_evidence,
    consolidate_reports,
    _convert_html_to_pdf,
)
from src.reporting.html_report import generate_html_report


def _render_steps(container, ticker, steps):
    """Render styled progress steps."""
    rows = ""
    for s in steps:
        state = s["state"]
        detail_html = ""
        if s.get("detail"):
            dcls = s.get("detail_cls", "")
            detail_html = f'<div class="step-detail {dcls}">{s["detail"]}</div>'
        time_html = ""
        if s.get("time"):
            time_html = f'<div class="step-time">{s["time"]}</div>'
        rows += (
            f'<div class="step-row {state}">'
            f'<div class="step-icon {state}"><span>{s["num"]}</span></div>'
            f'<div class="step-body">'
            f'<div class="step-name">{s["name"]}</div>'
            f'{detail_html}'
            f'</div>'
            f'{time_html}'
            f'</div>'
        )

    html = (
        f'<div class="progress-container">'
        f'<div class="progress-title">Analyzing <span>{ticker}</span></div>'
        f'{rows}'
        f'</div>'
    )
    container.markdown(html, unsafe_allow_html=True)


def run_analysis_with_progress(ticker: str) -> dict:
    """Run the full hybrid analysis pipeline with animated progress UI.

    Returns the merged evidence dict.
    """
    progress = st.progress(0)
    step_area = st.empty()

    steps = [
        {"num": "1", "name": "Fundamental Analysis", "state": "active",
         "detail": "Fetching financial data from Alpha Vantage..."},
        {"num": "2", "name": "Gate 1 \u2014 Fundamental Evaluation", "state": "pending"},
        {"num": "3", "name": "Technical Analysis", "state": "pending"},
        {"num": "4", "name": "Gate 2 \u2014 Technical Evaluation", "state": "pending"},
        {"num": "5", "name": "Report Generation", "state": "pending"},
    ]

    _render_steps(step_area, ticker, steps)
    progress.progress(5)

    # Step 1: Fundamental
    t0 = _time.time()
    fundamental = run_fundamental_agent(ticker)
    elapsed1 = _time.time() - t0

    steps[0] = {"num": "1", "name": "Fundamental Analysis", "state": "done",
                "detail": "Financial statements loaded", "time": f"{elapsed1:.0f}s"}
    steps[1] = {"num": "2", "name": "Gate 1 \u2014 Fundamental Evaluation", "state": "active",
                "detail": "Checking valuation thesis..."}
    _render_steps(step_area, ticker, steps)
    progress.progress(45)

    # Step 2: Gate 1
    gate1_pass, gate1_reason = check_gate1(fundamental)

    if gate1_pass:
        steps[1] = {"num": "2", "name": "Gate 1 \u2014 Fundamental Evaluation", "state": "done",
                     "detail": f"PASS \u2014 {gate1_reason}", "detail_cls": "pass"}
    else:
        steps[1] = {"num": "2", "name": "Gate 1 \u2014 Fundamental Evaluation", "state": "done",
                     "detail": f"FAIL \u2014 {gate1_reason}", "detail_cls": "fail"}
    _render_steps(step_area, ticker, steps)
    progress.progress(50)

    # Step 3 + 4: Technical (only if Gate 1 passes)
    technical = None
    gate2_result = (False, "Skipped \u2014 Gate 1 failed")

    if gate1_pass:
        steps[2] = {"num": "3", "name": "Technical Analysis", "state": "active",
                     "detail": "Running backtest on price history..."}
        _render_steps(step_area, ticker, steps)
        progress.progress(55)

        t1 = _time.time()
        technical = run_technical_agent(ticker)
        elapsed2 = _time.time() - t1

        steps[2] = {"num": "3", "name": "Technical Analysis", "state": "done",
                     "detail": "Backtest complete", "time": f"{elapsed2:.0f}s"}
        steps[3] = {"num": "4", "name": "Gate 2 \u2014 Technical Evaluation", "state": "active",
                     "detail": "Checking market regime..."}
        _render_steps(step_area, ticker, steps)
        progress.progress(85)

        gate2_pass, gate2_reason = check_gate2(technical)
        gate2_result = (gate2_pass, gate2_reason)

        if gate2_pass:
            steps[3] = {"num": "4", "name": "Gate 2 \u2014 Technical Evaluation", "state": "done",
                         "detail": f"PASS \u2014 {gate2_reason}", "detail_cls": "pass"}
        else:
            steps[3] = {"num": "4", "name": "Gate 2 \u2014 Technical Evaluation", "state": "done",
                         "detail": f"WAIT \u2014 {gate2_reason}", "detail_cls": "wait"}
        _render_steps(step_area, ticker, steps)
        progress.progress(90)
    else:
        steps[2] = {"num": "3", "name": "Technical Analysis", "state": "done",
                     "detail": "Skipped \u2014 Gate 1 failed", "detail_cls": "fail"}
        steps[3] = {"num": "4", "name": "Gate 2 \u2014 Technical Evaluation", "state": "done",
                     "detail": "Skipped", "detail_cls": "fail"}
        _render_steps(step_area, ticker, steps)
        progress.progress(90)

    # Step 5: Reports
    steps[4] = {"num": "5", "name": "Report Generation", "state": "active",
                "detail": "Building investment memo..."}
    _render_steps(step_area, ticker, steps)
    progress.progress(92)

    evidence = merge_evidence(
        ticker, fundamental, technical,
        (gate1_pass, gate1_reason), gate2_result,
    )

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    evidence_path = OUTPUT_DIR / f"{ticker}_hybrid_evidence.json"
    with open(evidence_path, "w") as f:
        json.dump(evidence, f, indent=2, default=str)

    html_path = OUTPUT_DIR / f"{ticker}_investment_memo.html"
    generate_html_report(evidence, str(html_path))

    pdf_path = OUTPUT_DIR / f"{ticker}_investment_memo.pdf"
    _convert_html_to_pdf(html_path, pdf_path)

    consolidate_reports(ticker)

    steps[4] = {"num": "5", "name": "Report Generation", "state": "done",
                "detail": "Reports ready"}
    _render_steps(step_area, ticker, steps)
    progress.progress(100)

    _time.sleep(1)
    step_area.empty()
    progress.empty()

    return evidence
