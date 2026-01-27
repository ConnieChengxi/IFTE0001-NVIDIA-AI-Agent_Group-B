from typing import Dict, List, Optional
from config.settings import (
    INDUSTRY_PEERS,
    RELATED_INDUSTRIES,
    MIN_MARKET_CAP_RATIO,
    MAX_MARKET_CAP_RATIO,
    MAX_VALID_PE_RATIO,
    MIN_VALID_PE_RATIO,
    MAX_PEERS
)


class PeerSelector:
    
    def __init__(self, api_client, cache_manager=None):
        self.api_client = api_client
        self.cache = cache_manager
        self._yf = None
    
    def _get_yfinance(self):
        if self._yf is None:
            try:
                import yfinance as yf
                self._yf = yf
            except ImportError:
                raise ImportError(
                    "yfinance is required for peer selection. "
                    "Install with: pip install yfinance"
                )
        return self._yf
    
    def _get_yahoo_data(self, ticker: str) -> Optional[Dict]:
        yf = self._get_yfinance()
        
        try:
            stock = yf.Ticker(ticker)
            info = stock.info
            
            return {
                'ticker': ticker,
                'market_cap': info.get('marketCap'),
                'pe_ratio': info.get('trailingPE'),
                'forward_pe': info.get('forwardPE'),
                'price': info.get('currentPrice') or info.get('regularMarketPrice'),
                'sector': info.get('sector'),
                'industry': info.get('industry'),
            }
        except Exception as e:
            print(f"      Yahoo error for {ticker}: {e}")
            return None
    
    def _find_industry_peers(self, industry: str, exclude_ticker: str) -> List[str]:
        industry_lower = industry.lower()
        for ind, tickers in INDUSTRY_PEERS.items():
            if ind.lower() in industry_lower or industry_lower in ind.lower():
                return [t for t in tickers if t.upper() != exclude_ticker.upper()]
        return []
    
    def _find_related_industry_peers(self, industry: str, exclude_ticker: str) -> List[str]:
        industry_lower = industry.lower()
        peers = []
        for ind, related in RELATED_INDUSTRIES.items():
            if ind.lower() in industry_lower or industry_lower in ind.lower():
                for related_ind in related:
                    if related_ind in INDUSTRY_PEERS:
                        peers.extend(INDUSTRY_PEERS[related_ind])
        return [t for t in peers if t.upper() != exclude_ticker.upper()]
    
    def _calculate_market_cap_score(self, target_cap: float, peer_cap: float) -> float:
        if not target_cap or not peer_cap:
            return float('inf')
        ratio = max(target_cap, peer_cap) / min(target_cap, peer_cap)
        return ratio
    
    def _filter_candidates(
        self, 
        candidates: List[Dict], 
        target_cap: float,
        strict: bool = True
    ) -> List[Dict]:
        filtered = []
        
        for candidate in candidates:
            if not candidate:
                continue
                
            peer_cap = candidate.get('market_cap')
            pe = candidate.get('pe_ratio')
            
            if not peer_cap:
                continue
            
            if pe is not None:
                try:
                    pe = float(pe)
                    if not (MIN_VALID_PE_RATIO <= pe <= MAX_VALID_PE_RATIO):
                        continue
                except (ValueError, TypeError):
                    pass
            
            if target_cap and strict:
                try:
                    ratio = float(peer_cap) / float(target_cap)
                    if not (MIN_MARKET_CAP_RATIO <= ratio <= MAX_MARKET_CAP_RATIO):
                        continue
                except (ValueError, TypeError):
                    continue
            
            score = self._calculate_market_cap_score(target_cap, peer_cap)
            candidate['market_cap_score'] = score
            filtered.append(candidate)
        
        return filtered
    
    def select_peers(self, target_ticker: str, target_data: Dict, max_peers: int = None) -> List[str]:
        if max_peers is None:
            max_peers = MAX_PEERS
        
        industry = target_data.get('industry', '')
        target_cap = target_data.get('market_cap')
        
        try:
            target_cap = float(target_cap) if target_cap else None
        except (ValueError, TypeError):
            target_cap = None
        
        print(f"\n   Finding peers for {target_ticker} (max: {max_peers})...")
        print(f"   Using Yahoo Finance for peer screening (no API limits)...")
        
        candidate_tickers = self._find_industry_peers(industry, target_ticker)
        
        if not candidate_tickers:
            print(f"   No peers found for industry: {industry}")
            return []
        
        print(f"   Screening {len(candidate_tickers)} candidates from {industry}...")
        
        candidates = []
        for ticker in candidate_tickers:
            data = self._get_yahoo_data(ticker)
            if data:
                candidates.append(data)
        
        if not candidates:
            print(f"   No valid candidates found")
            return []
        
        filtered = self._filter_candidates(candidates, target_cap, strict=True)
        
        if len(filtered) < max_peers:
            print(f"   Only {len(filtered)} peers with strict filter, trying relaxed...")
            filtered = self._filter_candidates(candidates, target_cap, strict=False)
        
        if len(filtered) < max_peers:
            print(f"   Checking related industries...")
            related_tickers = self._find_related_industry_peers(industry, target_ticker)
            
            for ticker in related_tickers[:10]:
                data = self._get_yahoo_data(ticker)
                if data:
                    data['market_cap_score'] = self._calculate_market_cap_score(
                        target_cap, data.get('market_cap')
                    )
                    filtered.append(data)
        
        filtered.sort(key=lambda x: x.get('market_cap_score', float('inf')))
        selected = [c['ticker'] for c in filtered[:max_peers]]
        
        print(f"   Selected peers: {', '.join(selected) if selected else 'None'}")
        return selected
    
    def get_peer_data(self, peer_tickers: List[str]) -> Dict[str, Dict]:
        print(f"   Fetching Alpha Vantage data for {len(peer_tickers)} peers...")
        
        peer_data = {}
        for ticker in peer_tickers:
            try:
                data = self.api_client.get_all_financial_data(ticker)
                peer_data[ticker] = data
                print(f"      [OK] {ticker}")
            except Exception as e:
                print(f"      [ERROR] {ticker}: {e}")
        
        return peer_data