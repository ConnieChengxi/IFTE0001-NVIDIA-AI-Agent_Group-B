from typing import Dict, Optional
import logging

logger = logging.getLogger(__name__)

DEFAULT_RISK_FREE_RATE = 0.042


class YahooFinanceClient:
    
    def __init__(self, cache_manager=None):
        self.cache = cache_manager
        self._yf = None
    
    def _get_yfinance(self):
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
    
    def get_risk_free_rate(self) -> float:
        if self.cache:
            cached = self.cache.get('TREASURY', 'risk_free_rate')
            if cached:
                logger.info(f"Using cached risk-free rate: {cached:.2%}")
                return cached
        
        yf = self._get_yfinance()
        
        try:
            tnx = yf.Ticker("^TNX")
            data = tnx.history(period="5d")
            
            if not data.empty:
                rate = data['Close'].iloc[-1] / 100
                
                if 0 < rate < 0.20:
                    logger.info(f"Fetched risk-free rate: {rate:.2%}")
                    
                    if self.cache:
                        self.cache.save('TREASURY', 'risk_free_rate', rate)
                    
                    return rate
            
            logger.warning("Could not fetch Treasury yield, using default")
            return DEFAULT_RISK_FREE_RATE
            
        except Exception as e:
            logger.error(f"Error fetching risk-free rate: {e}")
            return DEFAULT_RISK_FREE_RATE
    
    def get_equity_risk_premium(self) -> float:
        return 0.055
    
    def get_forward_estimates(self, ticker: str) -> Dict:
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
                'forward_pe': info.get('forwardPE'),
                'trailing_pe': info.get('trailingPE'),
                'forward_eps': info.get('forwardEps'),
                'trailing_eps': info.get('trailingEps'),
                'peg_ratio': info.get('pegRatio'),
                'target_price_mean': info.get('targetMeanPrice'),
                'target_price_high': info.get('targetHighPrice'),
                'target_price_low': info.get('targetLowPrice'),
                'analyst_count': info.get('numberOfAnalystOpinions'),
                'recommendation_score': info.get('recommendationMean'),
                'recommendation': info.get('recommendationKey'),
                'price_to_book': info.get('priceToBook'),
                'enterprise_to_ebitda': info.get('enterpriseToEbitda'),
                'price_to_sales': info.get('priceToSalesTrailing12Months'),
                'current_price': info.get('currentPrice') or info.get('regularMarketPrice'),
            }
            
            if self.cache:
                self.cache.save(ticker, 'yf_forward_estimates', result)
            
            logger.info(f"Fetched Yahoo Finance data for {ticker}")
            return result
            
        except Exception as e:
            logger.error(f"Error fetching Yahoo Finance data for {ticker}: {e}")
            return {}
    
    def get_analyst_recommendations(self, ticker: str) -> Optional[Dict]:
        yf = self._get_yfinance()
        
        try:
            stock = yf.Ticker(ticker)
            recs = stock.recommendations
            
            if recs is None or recs.empty:
                return None
            
            recent = recs.tail(30)
            
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


def get_risk_free_rate(cache_manager=None) -> float:
    client = YahooFinanceClient(cache_manager)
    return client.get_risk_free_rate()


def get_forward_pe(ticker: str, cache_manager=None) -> Optional[float]:
    client = YahooFinanceClient(cache_manager)
    data = client.get_forward_estimates(ticker)
    return data.get('forward_pe')


def get_analyst_target(ticker: str, cache_manager=None) -> Optional[float]:
    client = YahooFinanceClient(cache_manager)
    data = client.get_forward_estimates(ticker)
    return data.get('target_price_mean')