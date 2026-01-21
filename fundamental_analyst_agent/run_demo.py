#!/usr/bin/env python3
"""
Demo Script for Fundamental Analyst Agent
==========================================

This script demonstrates the capabilities of the equity research agent
by analyzing companies across different classification types:

- Growth: NVDA (NVIDIA)
- Balanced: MSFT (Microsoft)  
- Dividend: KO (Coca-Cola)
- Cyclical: XOM (Exxon Mobil)

Run this script to generate investment memos for all demo companies.

Usage:
    python run_demo.py              # Run all demos
    python run_demo.py --quick      # Run only 2 companies (faster)
    python run_demo.py NVDA AAPL    # Run specific tickers
"""

import os
import sys
import time
from datetime import datetime

# Add project root to path
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

from config.settings import OUTPUT_DIR

# Demo companies representing each classification type
DEMO_COMPANIES = {
    'growth': {
        'ticker': 'NVDA',
        'name': 'NVIDIA Corporation',
        'description': 'AI/GPU leader with explosive growth',
    },
    'balanced': {
        'ticker': 'MSFT', 
        'name': 'Microsoft Corporation',
        'description': 'Diversified tech with growth + dividends',
    },
    'dividend': {
        'ticker': 'KO',
        'name': 'The Coca-Cola Company',
        'description': 'Stable dividend aristocrat',
    },
    'cyclical': {
        'ticker': 'XOM',
        'name': 'Exxon Mobil Corporation', 
        'description': 'Energy sector, commodity-driven',
    },
}

# Quick demo - just 2 companies
QUICK_DEMO = ['NVDA', 'MSFT']


def print_banner():
    """Print demo banner."""
    print("\n" + "=" * 70)
    print("   FUNDAMENTAL ANALYST AGENT - DEMONSTRATION")
    print("   " + "=" * 50)
    print(f"   Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)


def print_demo_overview():
    """Print overview of demo companies."""
    print("\nDEMO COMPANIES:")
    print("-" * 70)
    print(f"{'Type':<12} {'Ticker':<8} {'Company':<30} {'Description':<25}")
    print("-" * 70)
    
    for company_type, info in DEMO_COMPANIES.items():
        print(f"{company_type.upper():<12} {info['ticker']:<8} {info['name']:<30} {info['description']:<25}")
    
    print("-" * 70)


def run_single_analysis(ticker: str) -> dict:
    """
    Run analysis for a single ticker.
    
    Returns dict with status and results.
    """
    from run_analysis import run_analysis
    
    start_time = time.time()
    
    try:
        run_analysis(ticker)
        elapsed = time.time() - start_time
        
        # Check if output file was created
        output_path = os.path.join(OUTPUT_DIR, f"{ticker}_Investment_Memo.html")
        success = os.path.exists(output_path)
        
        return {
            'ticker': ticker,
            'success': success,
            'elapsed_time': elapsed,
            'output_path': output_path if success else None,
            'error': None,
        }
        
    except Exception as e:
        elapsed = time.time() - start_time
        return {
            'ticker': ticker,
            'success': False,
            'elapsed_time': elapsed,
            'output_path': None,
            'error': str(e),
        }


def print_summary(results: list):
    """Print summary of all analyses."""
    print("\n" + "=" * 70)
    print("   DEMO SUMMARY")
    print("=" * 70)
    
    successful = [r for r in results if r['success']]
    failed = [r for r in results if not r['success']]
    
    print(f"\nSuccessful: {len(successful)}/{len(results)}")
    print(f"Failed: {len(failed)}/{len(results)}")
    
    # Results table
    print("\n" + "-" * 70)
    print(f"{'Ticker':<10} {'Status':<12} {'Time':<12} {'Output':<40}")
    print("-" * 70)
    
    for r in results:
        status = "OK" if r['success'] else "FAILED"
        time_str = f"{r['elapsed_time']:.1f}s"
        output = os.path.basename(r['output_path']) if r['output_path'] else r.get('error', 'N/A')[:35]
        print(f"{r['ticker']:<10} {status:<12} {time_str:<12} {output:<40}")
    
    print("-" * 70)
    
    # Total time
    total_time = sum(r['elapsed_time'] for r in results)
    print(f"\nTotal Time: {total_time:.1f} seconds")
    
    # Output directory
    print(f"\nOutput Directory: {os.path.abspath(OUTPUT_DIR)}")
    
    # List generated files
    if successful:
        print("\nGenerated Reports:")
        for r in successful:
            print(f"   - {r['output_path']}")


def run_demo(tickers: list = None, quick: bool = False):
    """
    Run demo analysis for multiple companies.
    
    Args:
        tickers: List of specific tickers to analyze (optional)
        quick: If True, run only 2 companies for faster demo
    """
    print_banner()
    
    # Determine which tickers to analyze
    if tickers:
        demo_tickers = [t.upper() for t in tickers]
        print(f"\nRunning analysis for specified tickers: {', '.join(demo_tickers)}")
    elif quick:
        demo_tickers = QUICK_DEMO
        print(f"\nQuick Demo Mode: {', '.join(demo_tickers)}")
    else:
        print_demo_overview()
        demo_tickers = [info['ticker'] for info in DEMO_COMPANIES.values()]
        print(f"\nRunning full demo for {len(demo_tickers)} companies...")
    
    # Confirm before running
    print("\n" + "-" * 70)
    input("Press ENTER to start the demo (or Ctrl+C to cancel)...")
    
    # Create output directory
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    # Run analyses
    results = []
    for i, ticker in enumerate(demo_tickers, 1):
        print(f"\n\n{'='*70}")
        print(f"   ANALYZING {ticker} ({i}/{len(demo_tickers)})")
        print(f"{'='*70}")
        
        result = run_single_analysis(ticker)
        results.append(result)
        
        # Small delay between API calls to avoid rate limits
        if i < len(demo_tickers):
            print("\n   Waiting 5 seconds before next analysis (API rate limit)...")
            time.sleep(5)
    
    # Print summary
    print_summary(results)
    
    print("\n" + "=" * 70)
    print("   DEMO COMPLETE!")
    print("=" * 70 + "\n")
    
    return results


def main():
    """Main entry point."""
    
    # Parse arguments
    args = sys.argv[1:]
    
    if '--help' in args or '-h' in args:
        print(__doc__)
        sys.exit(0)
    
    quick = '--quick' in args or '-q' in args
    
    # Remove flags from args
    tickers = [a for a in args if not a.startswith('-')]
    
    try:
        if tickers:
            run_demo(tickers=tickers)
        else:
            run_demo(quick=quick)
            
    except KeyboardInterrupt:
        print("\n\nDemo interrupted by user")
        sys.exit(0)
    except Exception as e:
        print(f"\nDemo error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()