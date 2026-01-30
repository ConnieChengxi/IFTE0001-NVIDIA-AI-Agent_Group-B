import data_fetcher
import analyzer
import valuation
import report_gen
import visualizer
import os
import json
from config import SYMBOL, RAW_DATA_DIR

def check_data_validity():
    """Verify if the fetched JSON files contain real data."""
    essential_files = [f"{SYMBOL}_overview.json", f"{SYMBOL}_income_statement.json"]
    for f in essential_files:
        path = os.path.join(RAW_DATA_DIR, f)
        if not os.path.exists(path):
            return False, f"Missing {f}. Data might not have been fetched due to API limits."
    return True, "Data is valid."

def main():
    print("=== Fundamental Analyst Agent: NVIDIA (NVDA) ===")
    
    # 1. Data Ingestion
    print("\nStep 1: Data Ingestion...")
    # data_fetcher.main()
    # Note: I commented it out for visual testing if data already exists, 
    # but for the user it should be active.
    data_fetcher.main()
    
    valid, msg = check_data_validity()
    if not valid:
        print(f"\n[ALERT] {msg}")
        print("Alpha Vantage API limit might have been reached (25 calls/day).")
        print("Proceeding with partial data analysis if possible...")

    # 2. Ratio Analysis
    print("\nStep 2: Financial Ratio Analysis...")
    fa = analyzer.FinancialAnalyzer()
    ratios = fa.analyze()
    
    # 3. Valuation
    if ratios is not None:
        print("\nStep 3: Business Valuation...")
        v = valuation.Valuator()
        v_results = v.run()
        
        # 4. Visualization
        print("\nStep 4: Generating Visualization Charts...")
        viz = visualizer.Visualizer()
        viz.run_all()
        
        # 5. Report Generation
        print("\nStep 5: Investment Memo Generation...")
        gen = report_gen.ReportGenerator()
        memo_info = gen.generate_memo()
        
        print("\n=== Agent Process Complete ===")
        print(f"Final Report: {memo_info}")
        print("Supporting charts saved to data/processed/plots/")
    else:
        print("\n[ERROR] Analysis aborted due to missing financial statements.")
        print("Please check your Alpha Vantage API usage limit.")

if __name__ == "__main__":
    main()
