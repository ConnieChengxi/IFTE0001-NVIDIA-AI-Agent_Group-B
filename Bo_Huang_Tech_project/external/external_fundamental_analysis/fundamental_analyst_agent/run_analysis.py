"""
Main analysis script for fundamental analyst agent.
Runs complete equity research analysis for a given ticker.
"""

import os
import sys
from datetime import datetime

# Add project root to path
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

# Import configuration
from config.settings import OUTPUT_DIR

# Import modules - FIXED PATHS
from src.data_collection.cache_manager import CacheManager
from src.data_collection.alpha_vantage_client import AlphaVantageClient
from src.data_collection.yahoo_finance_client import YahooFinanceClient
from src.data_collection.peer_selector import PeerSelector
from src.analysis.financial_ratios import FinancialRatiosCalculator
from src.analysis.company_classifier import CompanyClassifier
from src.analysis.dcf_valuation import DCFValuator
from src.analysis.multiples_valuation import MultiplesValuator
from src.analysis.ddm_valuation import DDMValuator
from src.agent.recommendation_engine import RecommendationEngine
from src.reporting.memo_generator import MemoGenerator


def print_banner(ticker: str):
    """Print analysis banner."""
    print("\n" + "=" * 60)
    print(f"   FUNDAMENTAL ANALYST AGENT")
    print(f"   Equity Research Analysis: {ticker.upper()}")
    print(f"   {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)


def run_analysis(ticker: str):
    """
    Run complete fundamental analysis for a ticker.
    
    Steps:
    1. Fetch company data
    2. Calculate financial ratios
    3. Classify company type
    4. Run valuation models (DCF, Multiples, DDM)
    5. Generate recommendation
    6. Generate HTML investment memo
    """
    
    print_banner(ticker)
    
    # Initialize clients
    cache = CacheManager()
    api_client = AlphaVantageClient(cache)
    yf_client = YahooFinanceClient(cache)
    peer_selector = PeerSelector(api_client)
    
    # ========================================
    # STEP 1: FETCH COMPANY DATA
    # ========================================
    print("\n📊 STEP 1: Fetching Company Data")
    print("-" * 60)
    
    try:
        print(f"   Fetching data for {ticker.upper()}...")
        company_data = api_client.get_all_financial_data(ticker)
        overview = company_data['overview']
        
        print(f"   ✅ Company: {overview.get('name', ticker)}")
        print(f"   ✅ Sector: {overview.get('sector', 'N/A')}")
        print(f"   ✅ Industry: {overview.get('industry', 'N/A')}")
        print(f"   ✅ Market Cap: ${overview.get('market_cap', 0):,.0f}")
        
    except Exception as e:
        print(f"\n❌ Error fetching company data: {e}")
        return
    
    # ========================================
    # STEP 1b: FETCH FORWARD ESTIMATES (Yahoo Finance)
    # ========================================
    print("\n📈 STEP 1b: Fetching Forward Estimates (Yahoo Finance)")
    print("-" * 60)
    
    forward_estimates = {}
    try:
        forward_estimates = yf_client.get_forward_estimates(ticker)
        
        if forward_estimates.get('forward_pe'):
            print(f"   ✅ Forward P/E: {forward_estimates['forward_pe']:.1f}x")
            print(f"   ✅ Trailing P/E: {forward_estimates.get('trailing_pe', 'N/A')}")
            print(f"   ✅ Forward EPS: ${forward_estimates.get('forward_eps', 0):.2f}")
            print(f"   ✅ Analyst Target: ${forward_estimates.get('target_price_mean', 0):.2f}")
            print(f"   ✅ Analyst Count: {forward_estimates.get('analyst_count', 0)}")
        else:
            print(f"   ⚠️  Forward estimates not available")
            
    except Exception as e:
        print(f"   ⚠️  Could not fetch forward estimates: {e}")
        forward_estimates = {}
    
    # ========================================
    # STEP 2: CALCULATE FINANCIAL RATIOS
    # ========================================
    print("\n📈 STEP 2: Calculating Financial Ratios")
    print("-" * 60)
    
    try:
        calculator = FinancialRatiosCalculator(company_data)
        ratios = calculator.calculate_all_ratios()
        
        # Helper function to safely format ratios
        def fmt_ratio(val, multiplier=100, decimals=1):
            if val is None or val == 'N/A':
                return "N/A"
            try:
                return f"{float(val) * multiplier:.{decimals}f}"
            except:
                return "N/A"
        
        print(f"   ✅ Profitability Ratios:")
        print(f"      • Gross Margin: {fmt_ratio(ratios.get('gross_margin'))}%")
        print(f"      • Net Margin: {fmt_ratio(ratios.get('net_margin'))}%")
        print(f"      • ROE: {fmt_ratio(ratios.get('roe'))}%")
        print(f"      • ROA: {fmt_ratio(ratios.get('roa'))}%")
        
        print(f"\n   ✅ Leverage Ratios:")
        print(f"      • Debt/Equity: {fmt_ratio(ratios.get('debt_to_equity'), 1, 2)}x")
        print(f"      • Interest Coverage: {fmt_ratio(ratios.get('interest_coverage'), 1, 1)}x")
        
        print(f"\n   ✅ Liquidity Ratios:")
        print(f"      • Current Ratio: {fmt_ratio(ratios.get('current_ratio'), 1, 2)}x")
        print(f"      • Quick Ratio: {fmt_ratio(ratios.get('quick_ratio'), 1, 2)}x")
        
        print(f"\n   ✅ Growth Metrics:")
        print(f"      • Revenue Growth: {fmt_ratio(ratios.get('revenue_growth'))}%")
        print(f"      • Earnings Growth: {fmt_ratio(ratios.get('earnings_growth'))}%")
        
    except Exception as e:
        print(f"\n❌ Error calculating ratios: {e}")
        import traceback
        traceback.print_exc()
        return

    # ========================================
    # STEP 3: CLASSIFY COMPANY TYPE
    # ========================================
    print("\n🏷️  STEP 3: Classifying Company Type")
    print("-" * 60)
    
    try:
        classifier = CompanyClassifier(company_data, ratios)
        classification = classifier.get_classification_details()
        
        print(f"   ✅ Company Type: {classification['company_type'].upper()}")
        print(f"   ✅ Reasoning: {classification['reasoning']}")
        
    except Exception as e:
        print(f"\n❌ Error classifying company: {e}")
        return
    
    # ========================================
    # STEP 4: RUN VALUATION MODELS
    # ========================================
    print("\n💰 STEP 4: Running Valuation Models")
    print("-" * 60)
    
    # Get current price
    current_price = overview.get('price')
    if not current_price:
        print("   ⚠️  No current price found in overview, using fallback...")
        current_price = 100.0  # Fallback
    
    print(f"   Current Price: ${current_price:.2f}")
    
    # --- 4a. DCF Valuation ---
    print("\n   [4a] DCF Valuation...")
    try:
        dcf_valuator = DCFValuator(
            company_data=company_data,
            company_type=classification['company_type'],
            sector=overview.get('sector')
        )
        dcf_result = dcf_valuator.get_dcf_summary()
        
        if dcf_result.get('fair_value_per_share'):
            print(f"      ✅ DCF Fair Value: ${dcf_result['fair_value_per_share']:.2f}")
            print(f"      • WACC: {dcf_result['assumptions']['wacc']*100:.1f}%")
            print(f"      • FCF Growth: {dcf_result['assumptions']['fcf_cagr']*100:.1f}%")
        else:
            print(f"      ⚠️  DCF not calculable: {dcf_result.get('error', 'Unknown')}")
    except Exception as e:
        print(f"      ❌ DCF Error: {e}")
        dcf_result = {'fair_value_per_share': None}
    
    # --- 4b. Select Peers ---
    print("\n   [4b] Selecting Peer Companies...")
    try:
        peer_tickers = peer_selector.select_peers(ticker, overview, max_peers=3)
        
        if peer_tickers:
            print(f"      ✅ Selected Peers: {', '.join(peer_tickers)}")
        else:
            print(f"      ⚠️  No peers found")
            peer_tickers = []
    except Exception as e:
        print(f"      ❌ Peer Selection Error: {e}")
        peer_tickers = []
    
    # --- 4c. Fetch Peer Data ---
    print("\n   [4c] Fetching Peer Data...")
    peer_data = {}
    if peer_tickers:
        try:
            peer_data = peer_selector.get_peer_data(peer_tickers)
            print(f"      ✅ Fetched data for {len(peer_data)} peers")
        except Exception as e:
            print(f"      ❌ Error fetching peer data: {e}")
    
    # --- 4c2. Fetch Peer Forward Estimates (Yahoo Finance) ---
    print("\n   [4c2] Fetching Peer Forward Estimates...")
    peer_forward_estimates = {}
    for peer_ticker in peer_tickers:
        try:
            peer_fwd = yf_client.get_forward_estimates(peer_ticker)
            if peer_fwd.get('forward_pe'):
                peer_forward_estimates[peer_ticker] = peer_fwd
                print(f"      ✅ {peer_ticker}: Forward P/E = {peer_fwd['forward_pe']:.1f}x")
            else:
                print(f"      ⚠️  {peer_ticker}: Forward P/E not available")
        except Exception as e:
            print(f"      ⚠️  {peer_ticker}: Error fetching forward estimates")
    
    # --- 4d. Multiples Valuation ---
    print("\n   [4d] Multiples Valuation...")
    try:
        multiples_valuator = MultiplesValuator(
            company_data, 
            peer_data,
            forward_estimates=forward_estimates,
            peer_forward_estimates=peer_forward_estimates
        )
        multiples_result = multiples_valuator.get_multiples_summary(use_forward=True)
        
        if multiples_result.get('average_fair_value'):
            pe_type = multiples_result['company_multiples'].get('pe_type', 'trailing')
            pe_value = multiples_result['company_multiples'].get('pe', 0)
            print(f"      ✅ Multiples Fair Value: ${multiples_result['average_fair_value']:.2f}")
            print(f"      • {pe_type.title()} P/E: {pe_value:.1f}x")
            print(f"      • P/B: {multiples_result['company_multiples'].get('pb', 0):.1f}x")
            print(f"      • EV/EBITDA: {multiples_result['company_multiples'].get('ev_ebitda', 0):.1f}x")
        else:
            print(f"      ⚠️  Multiples not calculable")
    except Exception as e:
        print(f"      ❌ Multiples Error: {e}")
        import traceback
        traceback.print_exc()
        multiples_result = {'average_fair_value': None, 'company_multiples': {}, 'peer_multiples': {}, 'peer_averages': {}}
    
    # --- 4e. DDM Valuation ---
    print("\n   [4e] DDM Valuation...")
    try:
        ddm_valuator = DDMValuator(company_data)
        ddm_result = ddm_valuator.get_ddm_summary()
        
        if ddm_result.get('applicable'):
            print(f"      ✅ DDM Fair Value: ${ddm_result['fair_value_per_share']:.2f}")
            print(f"      • Dividend Yield: {ddm_result['dividend_yield']*100:.1f}%")
            print(f"      • Growth Rate: {ddm_result['assumptions']['dividend_growth_rate']*100:.1f}%")
        else:
            print(f"      ⚠️  DDM not applicable: {ddm_result.get('reason', 'N/A')}")
    except Exception as e:
        print(f"      ❌ DDM Error: {e}")
        ddm_result = {'applicable': False, 'fair_value_per_share': None}
    
    # ========================================
    # STEP 5: GENERATE RECOMMENDATION
    # ========================================
    print("\n🎯 STEP 5: Generating Investment Recommendation")
    print("-" * 60)
    
    try:
        engine = RecommendationEngine(
            company_type=classification['company_type'],
            current_price=current_price,
            dcf_result=dcf_result,
            multiples_result=multiples_result,
            ddm_result=ddm_result,
            ratios=ratios
        )
        
        recommendation = engine.get_recommendation_summary()
        
        # Safe formatting helper
        def fmt_price(val):
            if val is None or val == 'N/A':
                return "N/A"
            try:
                return f"${float(val):.2f}"
            except:
                return "N/A"
        
        def fmt_pct(val):
            if val is None or val == 'N/A':
                return "N/A"
            try:
                return f"{float(val)*100:+.1f}%"
            except:
                return "N/A"
        
        print(f"\n   ✅ RECOMMENDATION: {recommendation['recommendation']}")
        print(f"   ✅ Target Price: {fmt_price(recommendation.get('fair_value'))}")
        print(f"   ✅ Current Price: {fmt_price(recommendation.get('current_price'))}")
        print(f"   ✅ Upside/Downside: {fmt_pct(recommendation.get('upside_downside'))}")
        print(f"\n   Reasoning: {recommendation.get('reasoning', 'N/A')}")
        
        # Show weights
        weights = recommendation.get('weights', {})
        print(f"\n   Valuation Weights ({classification['company_type'].title()}):")
        print(f"      • DCF: {weights.get('dcf', 0)*100:.0f}%")
        print(f"      • Multiples: {weights.get('multiples', 0)*100:.0f}%")
        print(f"      • DDM: {weights.get('ddm', 0)*100:.0f}%")
        
        # Show risk flags
        risk_factors = recommendation.get('risk_factors', {})
        if risk_factors.get('has_risk_flags'):
            print(f"\n   ⚠️  Risk Flags:")
            if risk_factors.get('solvency_risk'):
                print(f"      • Solvency Risk (low interest coverage)")
            if risk_factors.get('liquidity_risk'):
                print(f"      • Liquidity Risk (low current ratio)")
            if risk_factors.get('leverage_risk'):
                print(f"      • Leverage Risk (high debt)")
        
    except Exception as e:
        print(f"\n❌ Error generating recommendation: {e}")
        import traceback
        traceback.print_exc()
        return
    # ========================================
    # STEP 6: GENERATE HTML INVESTMENT MEMO
    # ========================================
    print("\n📄 STEP 6: Generating HTML Investment Memo")
    print("-" * 60)
    
    try:
        generator = MemoGenerator(
            ticker=ticker.upper(),
            company_data=company_data,
            ratios=ratios,
            classification=classification,
            dcf_result=dcf_result,
            multiples_result=multiples_result,
            ddm_result=ddm_result,
            recommendation=recommendation,
            peer_tickers=peer_tickers,
            forward_estimates=forward_estimates
        )
        
        # Create output directory
        os.makedirs(OUTPUT_DIR, exist_ok=True)
        
        # Generate and save memo
        output_path = os.path.join(OUTPUT_DIR, f"{ticker.upper()}_Investment_Memo.html")
        generator.save_memo(output_path)
        
        print(f"\n   ✅ Investment Memo saved: {output_path}")
        print(f"   📄 Open in browser to view/print/save as PDF")
        print(f"\n   Full path: {os.path.abspath(output_path)}")
        
    except Exception as e:
        print(f"\n❌ Error generating memo: {e}")
        import traceback
        traceback.print_exc()
        return
    
    # ========================================
    # ANALYSIS COMPLETE
    # ========================================
    print("\n" + "=" * 60)
    print("   ✅ ANALYSIS COMPLETE!")
    print("=" * 60)
    print(f"\n   Ticker: {ticker.upper()}")
    print(f"   Company: {overview.get('name', ticker)}")
    print(f"   Classification: {classification['company_type'].upper()}")
    print(f"   Recommendation: {recommendation['recommendation']}")
    
    # Safe formatting
    fair_value = recommendation.get('fair_value')
    upside = recommendation.get('upside_downside')
    
    if fair_value is not None:
        print(f"   Target Price: ${fair_value:.2f}")
    else:
        print(f"   Target Price: N/A")
    
    if upside is not None:
        print(f"   Upside: {upside*100:+.1f}%")
    else:
        print(f"   Upside: N/A")
    
    print(f"\n   Report: {output_path}")
    print("\n" + "=" * 60 + "\n")


def main():
    """Main entry point."""
    
    if len(sys.argv) < 2:
        print("\n❌ Error: Please provide a ticker symbol")
        print("\nUsage:")
        print("   python run_analysis.py TICKER")
        print("\nExample:")
        print("   python run_analysis.py NVDA")
        print("   python run_analysis.py AAPL")
        print("   python run_analysis.py MSFT")
        sys.exit(1)
    
    ticker = sys.argv[1].upper()
    
    try:
        run_analysis(ticker)
    except KeyboardInterrupt:
        print("\n\n⚠️  Analysis interrupted by user")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()