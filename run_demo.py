#!/usr/bin/env python3
"""
Hybrid Investment Analyst - Main Entry Point

Combines Fundamental Valuation + Technical Execution using Dual-Gate architecture:
- Gate 1 (Fundamental): BUY/HOLD -> PASS, SELL -> NO_TRADE
- Gate 2 (Technical): Close > MA200 -> TRADE, else WAIT

Usage:
    python run_analysis.py NVDA
    python run_analysis.py AAPL --output my_reports
"""

import os
import sys
import argparse
from pathlib import Path

# Load environment variables from root .env
from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).parent
load_dotenv(PROJECT_ROOT / ".env")

# Add hybrid_controller to path
sys.path.insert(0, str(PROJECT_ROOT / "hybrid_controller"))

from src.orchestrator import run_hybrid_analysis, consolidate_reports, _convert_html_to_pdf
from src.reporting.html_report import generate_html_report
import json


def main():
    parser = argparse.ArgumentParser(
        description="Hybrid Investment Analyst - Fundamental + Technical Analysis",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    python run_analysis.py NVDA           # Analyze NVIDIA
    python run_analysis.py AAPL           # Analyze Apple
    python run_analysis.py MSFT --output reports  # Custom output dir

Required API Keys (in .env file):
    ALPHA_VANTAGE_API_KEY  - Required for financial data
    OPENAI_API_KEY         - Optional for AI-generated thesis
        """
    )
    parser.add_argument(
        "ticker",
        type=str,
        help="Stock ticker symbol (e.g., NVDA, AAPL, MSFT)"
    )
    parser.add_argument(
        "--output",
        type=str,
        default="hybrid_controller/outputs",
        help="Output directory (default: hybrid_controller/outputs)"
    )

    args = parser.parse_args()
    ticker = args.ticker.upper()

    # Validate API key
    if not os.getenv("ALPHA_VANTAGE_API_KEY"):
        print("\n[ERROR] ALPHA_VANTAGE_API_KEY not found!")
        print("Please create .env file with your API key:")
        print("  cp .env.example .env")
        print("  # Edit .env and add your key")
        sys.exit(1)

    print("\n" + "=" * 60)
    print("  HYBRID INVESTMENT ANALYST")
    print("  Fundamental Valuation + Technical Execution")
    print("=" * 60)
    print(f"  Ticker: {ticker}")
    print(f"  Output: {args.output}")
    print("=" * 60)

    try:
        # Run hybrid analysis
        print(f"\n[1/4] Running hybrid analysis...")
        evidence = run_hybrid_analysis(ticker)

        # Prepare output directory
        output_dir = PROJECT_ROOT / args.output
        output_dir.mkdir(parents=True, exist_ok=True)

        # Save evidence JSON
        evidence_path = output_dir / f"{ticker}_hybrid_evidence.json"
        with open(evidence_path, 'w') as f:
            json.dump(evidence, f, indent=2, default=str)
        print(f"\n[2/4] Evidence saved: {evidence_path}")

        # Generate HTML report
        html_path = output_dir / f"{ticker}_investment_memo.html"
        generate_html_report(evidence, str(html_path))
        print(f"[3/4] HTML report saved: {html_path}")

        # Convert to PDF
        pdf_path = output_dir / f"{ticker}_investment_memo.pdf"
        if _convert_html_to_pdf(html_path, pdf_path):
            result_path = str(pdf_path)
        else:
            result_path = str(html_path)

        # Consolidate all reports to output directory
        print(f"\n[4/4] Consolidating all reports...")
        reports = consolidate_reports(ticker)
        reports["hybrid"] = result_path

        # Print summary
        meta = evidence['meta']
        gates = evidence['gates']
        action = evidence['action']
        rec = evidence['fundamental']['recommendation']

        print("\n" + "=" * 60)
        print("  ANALYSIS COMPLETE")
        print("=" * 60)
        print(f"  Company:         {meta['company_name']}")
        print(f"  Recommendation:  {rec['action']}")
        print(f"  Current Price:   ${rec.get('current_price', 0):.2f}")
        print(f"  Fair Value:      ${rec.get('fair_value', 0):.2f}")
        print(f"  Upside:          {(rec.get('upside_downside', 0) or 0)*100:+.1f}%")
        print("-" * 60)
        print(f"  Gate 1 (Fund):   {gates['gate1']['status']}")
        print(f"  Gate 2 (Tech):   {gates['gate2']['status']}")
        print(f"  FINAL ACTION:    {action}")
        print("=" * 60)
        print("\n  GENERATED REPORTS:")
        print("-" * 60)
        if reports.get("hybrid"):
            print(f"  [HYBRID]      {reports['hybrid']}")
        if reports.get("fundamental"):
            print(f"  [FUNDAMENTAL] {reports['fundamental']}")
        if reports.get("technical"):
            print(f"  [TECHNICAL]   {reports['technical']}")
        print("-" * 60)
        print(f"\n  Open hybrid report: file://{result_path}")
        print("\n")

        return 0

    except KeyboardInterrupt:
        print("\n\n[WARN] Analysis interrupted by user")
        return 0
    except Exception as e:
        print(f"\n[ERROR] Analysis failed: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
