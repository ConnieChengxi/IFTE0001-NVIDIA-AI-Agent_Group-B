"""
Hybrid Orchestrator - Dual-Gate Architecture

Runs fundamental and technical agents via subprocess,
reads their JSON outputs, applies gate logic.
"""

import os
import json
import subprocess
import shutil
from typing import Dict, Any, Tuple, Optional
from pathlib import Path


# Paths to agent directories
HYBRID_DIR = Path(__file__).parent.parent
PROJECT_ROOT = HYBRID_DIR.parent
FUNDAMENTAL_DIR = PROJECT_ROOT / "idaliia_fundamental"
TECHNICAL_DIR = PROJECT_ROOT / "connie_technical"
HYBRID_OUTPUT_DIR = HYBRID_DIR / "outputs"


def run_fundamental_agent(ticker: str) -> Dict[str, Any]:
    """
    Run fundamental analysis agent via subprocess.

    Returns:
        Parsed JSON evidence from fundamental agent
    """
    print(f"\n[FUNDAMENTAL] Running analysis for {ticker}...")

    result = subprocess.run(
        ["python3", "run_demo.py", ticker],
        cwd=str(FUNDAMENTAL_DIR),
        capture_output=True,
        text=True,
        env=os.environ
    )

    if result.returncode != 0:
        print(f"[FUNDAMENTAL] STDERR: {result.stderr}")
        raise RuntimeError(f"Fundamental agent failed: {result.stderr}")

    # Read JSON evidence
    evidence_path = FUNDAMENTAL_DIR / "outputs" / f"{ticker.upper()}_evidence.json"
    if not evidence_path.exists():
        raise FileNotFoundError(f"Fundamental evidence not found: {evidence_path}")

    with open(evidence_path, 'r') as f:
        evidence = json.load(f)

    print(f"[FUNDAMENTAL] Recommendation: {evidence['recommendation']['action']}")
    print(f"[FUNDAMENTAL] Fair Value: ${evidence['recommendation']['fair_value']:.2f}")
    print(f"[FUNDAMENTAL] Upside: {evidence['recommendation']['upside_downside']*100:+.1f}%")

    return evidence


def run_technical_agent(ticker: str) -> Dict[str, Any]:
    """
    Run technical analysis agent via subprocess.

    Returns:
        Parsed JSON evidence from technical agent
    """
    print(f"\n[TECHNICAL] Running analysis for {ticker}...")

    result = subprocess.run(
        ["python3", "run_demo.py", ticker, "--outdir", "outputs"],
        cwd=str(TECHNICAL_DIR),
        capture_output=True,
        text=True,
        env=os.environ
    )

    if result.returncode != 0:
        print(f"[TECHNICAL] STDERR: {result.stderr}")
        raise RuntimeError(f"Technical agent failed: {result.stderr}")

    # Read JSON evidence
    evidence_path = TECHNICAL_DIR / "outputs" / f"{ticker.upper()}_evidence.json"
    if not evidence_path.exists():
        raise FileNotFoundError(f"Technical evidence not found: {evidence_path}")

    with open(evidence_path, 'r') as f:
        evidence = json.load(f)

    metrics = evidence.get('metrics', {})
    latest = evidence.get('latest_state', {})

    print(f"[TECHNICAL] CAGR: {metrics.get('CAGR', 0)*100:.1f}%")
    print(f"[TECHNICAL] Sharpe: {metrics.get('Sharpe', 0):.2f}")
    print(f"[TECHNICAL] Max DD: {metrics.get('MaxDrawdown', 0)*100:.1f}%")
    print(f"[TECHNICAL] Regime: {'Bullish' if latest.get('regime_bullish') else 'Bearish'}")

    return evidence


def check_gate1(fundamental: Dict[str, Any]) -> Tuple[bool, str]:
    """
    Gate 1: Fundamental eligibility check.

    PASS if recommendation is BUY or HOLD
    FAIL if recommendation is SELL
    """
    action = fundamental['recommendation']['action'].upper()
    fair_value = fundamental['recommendation'].get('fair_value', 0)
    upside = fundamental['recommendation'].get('upside_downside', 0) or 0

    if action in ["BUY", "HOLD"]:
        reason = f"{action} recommendation, {upside*100:+.1f}% upside to ${fair_value:.2f}"
        return True, reason
    else:
        reason = f"{action} recommendation - fundamental thesis negative"
        return False, reason


def check_gate2(technical: Dict[str, Any]) -> Tuple[bool, str]:
    """
    Gate 2: Technical regime check.

    PASS if Close > MA200 (bullish regime)
    WAIT if Close < MA200 (bearish regime)
    """
    latest = technical.get('latest_state', {})
    close = latest.get('close', 0)
    ma200 = latest.get('ma200', 0)
    regime_bullish = latest.get('regime_bullish', False)

    if regime_bullish or (ma200 > 0 and close > ma200):
        reason = f"Bullish regime: Close ${close:.2f} > MA200 ${ma200:.2f}"
        return True, reason
    else:
        reason = f"Bearish regime: Close ${close:.2f} < MA200 ${ma200:.2f}"
        return False, reason


def determine_action(gate1_pass: bool, gate2_pass: bool) -> str:
    """
    Determine final action based on gate results.

    Returns: TRADE, WAIT, or NO_TRADE
    """
    if not gate1_pass:
        return "NO_TRADE"
    elif gate1_pass and gate2_pass:
        return "TRADE"
    else:  # gate1_pass and not gate2_pass
        return "WAIT"


def _convert_html_to_pdf(html_path: Path, pdf_path: Path) -> bool:
    """Convert HTML file to PDF using Playwright."""
    try:
        from playwright.sync_api import sync_playwright
        with sync_playwright() as p:
            browser = p.chromium.launch()
            page = browser.new_page()
            page.goto(f"file://{html_path.absolute()}")
            page.pdf(
                path=str(pdf_path),
                format="A4",
                margin={"top": "1.5cm", "bottom": "1.5cm", "left": "2cm", "right": "2cm"},
                print_background=True,
            )
            browser.close()
        return True
    except Exception as e:
        print(f"[WARN] PDF conversion failed: {e}")
        return False


def consolidate_reports(ticker: str) -> Dict[str, Optional[Path]]:
    """
    Copy agent reports to hybrid output directory.
    Always copies both HTML and PDF for each report.
    Converts HTML to PDF if PDF not available from agent.

    Returns:
        Dictionary with paths to all consolidated reports (PDF paths)
    """
    ticker = ticker.upper()
    HYBRID_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    reports = {
        "fundamental": None,
        "technical": None,
        "hybrid": None,
    }

    # Fundamental report
    fund_pdf = FUNDAMENTAL_DIR / "outputs" / f"{ticker}_Investment_Memo.pdf"
    fund_html = FUNDAMENTAL_DIR / "outputs" / f"{ticker}_Investment_Memo.html"
    dest_fund_pdf = HYBRID_OUTPUT_DIR / f"{ticker}_fundamental_analysis.pdf"
    dest_fund_html = HYBRID_OUTPUT_DIR / f"{ticker}_fundamental_analysis.html"

    if fund_html.exists():
        shutil.copy2(fund_html, dest_fund_html)
        print(f"[REPORTS] Fundamental HTML: {dest_fund_html}")

    if fund_pdf.exists():
        shutil.copy2(fund_pdf, dest_fund_pdf)
        print(f"[REPORTS] Fundamental PDF: {dest_fund_pdf}")
    elif fund_html.exists():
        if _convert_html_to_pdf(fund_html, dest_fund_pdf):
            print(f"[REPORTS] Fundamental PDF (converted): {dest_fund_pdf}")

    if dest_fund_pdf.exists():
        reports["fundamental"] = dest_fund_pdf

    # Technical report
    tech_pdf = TECHNICAL_DIR / "outputs" / f"{ticker}_final_report.pdf"
    tech_html = TECHNICAL_DIR / "outputs" / f"{ticker}_final_report.html"
    dest_tech_pdf = HYBRID_OUTPUT_DIR / f"{ticker}_technical_analysis.pdf"
    dest_tech_html = HYBRID_OUTPUT_DIR / f"{ticker}_technical_analysis.html"

    if tech_html.exists():
        shutil.copy2(tech_html, dest_tech_html)
        print(f"[REPORTS] Technical HTML: {dest_tech_html}")

    if tech_pdf.exists():
        shutil.copy2(tech_pdf, dest_tech_pdf)
        print(f"[REPORTS] Technical PDF: {dest_tech_pdf}")
    elif tech_html.exists():
        if _convert_html_to_pdf(tech_html, dest_tech_pdf):
            print(f"[REPORTS] Technical PDF (converted): {dest_tech_pdf}")

    if dest_tech_pdf.exists():
        reports["technical"] = dest_tech_pdf

    return reports


def merge_evidence(
    ticker: str,
    fundamental: Dict[str, Any],
    technical: Dict[str, Any],
    gate1_result: Tuple[bool, str],
    gate2_result: Tuple[bool, str]
) -> Dict[str, Any]:
    """
    Merge fundamental and technical evidence into hybrid pack.
    """
    gate1_pass, gate1_reason = gate1_result
    gate2_pass, gate2_reason = gate2_result

    action = determine_action(gate1_pass, gate2_pass)

    return {
        "meta": {
            "ticker": ticker.upper(),
            "company_name": fundamental['meta']['company_name'],
            "sector": fundamental['meta']['sector'],
            "industry": fundamental['meta']['industry'],
            "analysis_date": fundamental['meta']['analysis_date'],
            "market_cap": fundamental['meta']['market_cap'],
        },
        "gates": {
            "gate1": {
                "name": "Fundamental",
                "status": "PASS" if gate1_pass else "FAIL",
                "reason": gate1_reason,
            },
            "gate2": {
                "name": "Technical",
                "status": "PASS" if gate2_pass else "WAIT",
                "reason": gate2_reason,
            },
        },
        "action": action,
        "fundamental": fundamental,
        "technical": technical,
    }


def run_hybrid_analysis(ticker: str) -> Dict[str, Any]:
    """
    Main entry point for hybrid analysis.

    Implements Dual-Gate architecture:
    1. Run Fundamental → check Gate 1
    2. If Gate 1 PASS → Run Technical → check Gate 2
    3. Merge evidence → determine action
    """
    print("=" * 60)
    print(f"  HYBRID ANALYST AGENT")
    print(f"  Ticker: {ticker.upper()}")
    print("=" * 60)

    # Step 1: Run Fundamental Analysis
    fundamental = run_fundamental_agent(ticker)

    # Step 2: Check Gate 1
    gate1_pass, gate1_reason = check_gate1(fundamental)
    print(f"\n[GATE 1] {'PASS' if gate1_pass else 'FAIL'}: {gate1_reason}")

    # Step 3: If Gate 1 fails, stop here
    if not gate1_pass:
        print("\n[HYBRID] Gate 1 FAILED - No technical analysis needed")
        return merge_evidence(
            ticker=ticker,
            fundamental=fundamental,
            technical=None,
            gate1_result=(gate1_pass, gate1_reason),
            gate2_result=(False, "Skipped - Gate 1 failed")
        )

    # Step 4: Run Technical Analysis
    technical = run_technical_agent(ticker)

    # Step 5: Check Gate 2
    gate2_pass, gate2_reason = check_gate2(technical)
    print(f"\n[GATE 2] {'PASS' if gate2_pass else 'WAIT'}: {gate2_reason}")

    # Step 6: Merge evidence
    hybrid_evidence = merge_evidence(
        ticker=ticker,
        fundamental=fundamental,
        technical=technical,
        gate1_result=(gate1_pass, gate1_reason),
        gate2_result=(gate2_pass, gate2_reason)
    )

    print(f"\n[HYBRID] Action: {hybrid_evidence['action']}")

    return hybrid_evidence
