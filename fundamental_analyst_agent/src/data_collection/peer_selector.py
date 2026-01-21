"""
Peer Selector
Selects comparable companies for valuation analysis.
"""

from typing import Dict, List
from config.settings import (
    INDUSTRY_PEERS,
    RELATED_INDUSTRIES,
    MIN_MARKET_CAP_RATIO,
    MAX_MARKET_CAP_RATIO,
    MAX_VALID_PE_RATIO,
    MIN_VALID_PE_RATIO
)


class PeerSelector:
    """Selects peer companies for comparable analysis."""
    
    def __init__(self, api_client):
        self.api_client = api_client
    
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
    
    def _filter_by_market_cap(self, target_cap: float, peers: List[Dict], strict: bool = True) -> List[Dict]:
        if not target_cap:
            return peers
        filtered = []
        for peer in peers:
            peer_cap = peer['data'].get('market_cap')
            if not peer_cap:
                continue
            if strict:
                ratio = peer_cap / target_cap
                if MIN_MARKET_CAP_RATIO <= ratio <= MAX_MARKET_CAP_RATIO:
                    score = self._calculate_market_cap_score(target_cap, peer_cap)
                    peer['market_cap_score'] = score
                    filtered.append(peer)
            else:
                score = self._calculate_market_cap_score(target_cap, peer_cap)
                peer['market_cap_score'] = score
                filtered.append(peer)
        return filtered
    
    def _filter_by_pe_ratio(self, peers: List[Dict]) -> List[Dict]:
        filtered = []
        for peer in peers:
            pe = peer['data'].get('pe_ratio')
            if pe is None:
                filtered.append(peer)
            elif MIN_VALID_PE_RATIO <= pe <= MAX_VALID_PE_RATIO:
                filtered.append(peer)
        return filtered
    
    def select_peers(self, target_ticker: str, target_data: Dict, max_peers: int = 3) -> List[str]:
        industry = target_data.get('industry', '')
        target_cap = target_data.get('market_cap')
        
        print(f"\n   Finding peers for {target_ticker}...")
        candidate_tickers = self._find_industry_peers(industry, target_ticker)
        
        if not candidate_tickers:
            return []
        
        candidates = []
        for ticker in candidate_tickers:
            try:
                overview = self.api_client.get_company_overview(ticker)
                candidates.append({'ticker': ticker, 'data': overview})
            except:
                continue
        
        if not candidates:
            return []
        
        candidates = self._filter_by_pe_ratio(candidates)
        candidates = self._filter_by_market_cap(target_cap, candidates, strict=True)
        
        if len(candidates) < max_peers:
            candidates_all = []
            for ticker in candidate_tickers:
                try:
                    overview = self.api_client.get_company_overview(ticker)
                    candidates_all.append({'ticker': ticker, 'data': overview})
                except:
                    continue
            candidates_all = self._filter_by_pe_ratio(candidates_all)
            candidates = self._filter_by_market_cap(target_cap, candidates_all, strict=False)
        
        if len(candidates) < max_peers:
            related_tickers = self._find_related_industry_peers(industry, target_ticker)
            for ticker in related_tickers[:10]:
                try:
                    overview = self.api_client.get_company_overview(ticker)
                    peer = {'ticker': ticker, 'data': overview}
                    peer['market_cap_score'] = self._calculate_market_cap_score(target_cap, overview.get('market_cap'))
                    candidates.append(peer)
                except:
                    continue
            candidates = self._filter_by_pe_ratio(candidates)
        
        candidates.sort(key=lambda x: x.get('market_cap_score', float('inf')))
        selected = [c['ticker'] for c in candidates[:max_peers]]
        
        print(f"   Selected peers: {', '.join(selected)}")
        return selected
    
    def get_peer_data(self, peer_tickers: List[str]) -> Dict[str, Dict]:
        peer_data = {}
        for ticker in peer_tickers:
            try:
                data = self.api_client.get_all_financial_data(ticker)
                peer_data[ticker] = data
            except Exception as e:
                print(f"   Error fetching {ticker}: {e}")
        return peer_data
