"""
Yahoo Finance Client
Fetches forward-looking estimates and analyst data not available in Alpha Vantage.

Data provided:
- Forward P/E, Forward EPS
- Analyst target prices (mean, high, low)
- Analyst recommendations
- PEG Ratio
"""

from typing import Dict, Optional
import logging

logger = logging.getLogger(__name__)


class YahooFinanceClient:
    """
    Client for fetching forward-looking data from Yahoo Finance.
    
    Complements Alpha Vantage with:
    - Forward estimates (Forward P/E, Forward EPS)
    - Analyst consensus (target prices, recommendations)
    """
    
    def __init__(self, cache_manager=None):
        """
        Initialize Yahoo Finance client.
        
        Args:
            cache_manager: Optional cache manager for storing results
        """
        self.cache = cache_manager
        self._yf = None
    
    def _get_yfinance(self):
        """Lazy load yfinance module."""
        if self._yf is None:
            try:
                import yfinance as yf
                self._yf = yf
            except ImportError:
                raise ImportError(
                    "yfinance is required for forward estimates. "
                    "Install with: pip install yfinance"
                )
        return self._yf
    
    def get_forward_estimates(self, ticker: str) -> Dict:
        """
        Get forward-looking estimates for a ticker.
        
        Args:
            ticker: Stock ticker symbol (e.g., 'NVDA')
            
        Returns:
            Dict with forward estimates:
            {
                'forward_pe': float,
                'trailing_pe': float,
                'forward_eps': float,
                'trailing_eps': float,
                'peg_ratio': float,
                'target_price_mean': float,
                'target_price_high': float,
                'target_price_low': float,
                'analyst_count': int,
                'recommendation': str,  # 'buy', 'hold', 'sell'
            }
        """
        # Check cache first - use symbol and function name format
        if self.cache:
            cached = self.cache.get(ticker, 'yf_forward_estimates')
            if cached:
                logger.info(f"Using cached Yahoo Finance data for {ticker}")
                return cached
        
        yf = self._get_yfinance()
        
        try:
            stock = yf.Ticker(ticker)
            info = stock.info
            
            result = {
                # Forward estimates
                'forward_pe': info.get('forwardPE'),
                'trailing_pe': info.get('trailingPE'),
                'forward_eps': info.get('forwardEps'),
                'trailing_eps': info.get('trailingEps'),
                'peg_ratio': info.get('pegRatio'),
                
                # Analyst targets
                'target_price_mean': info.get('targetMeanPrice'),
                'target_price_high': info.get('targetHighPrice'),
                'target_price_low': info.get('targetLowPrice'),
                'analyst_count': info.get('numberOfAnalystOpinions'),
                
                # Recommendation
                'recommendation_score': info.get('recommendationMean'),  # 1=Buy, 5=Sell
                'recommendation': info.get('recommendationKey'),  # 'buy', 'hold', etc.
                
                # Additional valuation
                'price_to_book': info.get('priceToBook'),
                'enterprise_to_ebitda': info.get('enterpriseToEbitda'),
                'price_to_sales': info.get('priceToSalesTrailing12Months'),
                
                # Current price for reference
                'current_price': info.get('currentPrice') or info.get('regularMarketPrice'),
            }
            
            # Cache the result - use symbol and function name format
            if self.cache:
                self.cache.save(ticker, 'yf_forward_estimates', result)
            
            logger.info(f"Fetched Yahoo Finance data for {ticker}")
            return result
            
        except Exception as e:
            logger.error(f"Error fetching Yahoo Finance data for {ticker}: {e}")
            return {}
    
    def get_analyst_recommendations(self, ticker: str) -> Optional[Dict]:
        """
        Get detailed analyst recommendations history.
        
        Args:
            ticker: Stock ticker symbol
            
        Returns:
            Dict with recommendation summary or None
        """
        yf = self._get_yfinance()
        
        try:
            stock = yf.Ticker(ticker)
            recs = stock.recommendations
            
            if recs is None or recs.empty:
                return None
            
            # Get recent recommendations (last 3 months)
            recent = recs.tail(30)
            
            # Count by type
            summary = {
                'strong_buy': 0,
                'buy': 0,
                'hold': 0,
                'sell': 0,
                'strong_sell': 0,
                'total': len(recent),
            }
            
            for _, row in recent.iterrows():
                grade = str(row.get('To Grade', '')).lower()
                if 'strong buy' in grade:
                    summary['strong_buy'] += 1
                elif 'buy' in grade:
                    summary['buy'] += 1
                elif 'hold' in grade or 'neutral' in grade:
                    summary['hold'] += 1
                elif 'strong sell' in grade:
                    summary['strong_sell'] += 1
                elif 'sell' in grade:
                    summary['sell'] += 1
            
            return summary
            
        except Exception as e:
            logger.error(f"Error fetching recommendations for {ticker}: {e}")
            return None


def get_forward_pe(ticker: str, cache_manager=None) -> Optional[float]:
    """
    Convenience function to get just Forward P/E.
    
    Args:
        ticker: Stock ticker symbol
        cache_manager: Optional cache manager
        
    Returns:
        Forward P/E ratio or None
    """
    client = YahooFinanceClient(cache_manager)
    data = client.get_forward_estimates(ticker)
    return data.get('forward_pe')


def get_analyst_target(ticker: str, cache_manager=None) -> Optional[float]:
    """
    Convenience function to get analyst mean target price.
    
    Args:
        ticker: Stock ticker symbol
        cache_manager: Optional cache manager
        
    Returns:
        Mean analyst target price or None
    """
    client = YahooFinanceClient(cache_manager)
    data = client.get_forward_estimates(ticker)
    return data.get('target_price_mean')