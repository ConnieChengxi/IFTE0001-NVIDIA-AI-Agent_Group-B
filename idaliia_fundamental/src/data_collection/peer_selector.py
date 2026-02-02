"""
Peer company selector based on industry, market cap, and PEG ratio.
"""

from typing import Dict, List, Optional
from config.settings import (
    INDUSTRY_PEERS,
    RELATED_INDUSTRIES,
    MIN_MARKET_CAP_RATIO,
    MAX_MARKET_CAP_RATIO,
    MIN_VALID_PEG,
    MAX_VALID_PEG,
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

            peg = info.get('pegRatio')
            if not peg:
                pe = info.get('trailingPE')
                growth = info.get('earningsGrowth')
                if pe and growth and growth > 0:
                    peg = pe / (growth * 100)

            return {
                'ticker': ticker,
                'market_cap': info.get('marketCap'),
                'peg': peg,
                'pe_ratio': info.get('trailingPE'),
                'forward_pe': info.get('forwardPE'),
                'earnings_growth': info.get('earningsGrowth'),
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
            peg = candidate.get('peg')

            if not peer_cap:
                continue

            if peg is not None:
                try:
                    peg = float(peg)
                    if not (MIN_VALID_PEG <= peg <= MAX_VALID_PEG):
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

        main_industry_tickers = self._find_industry_peers(industry, target_ticker)
        print(f"   Step 1: Found {len(main_industry_tickers)} candidates from {industry}")

        main_candidates = []
        for ticker in main_industry_tickers:
            data = self._get_yahoo_data(ticker)
            if data:
                main_candidates.append(data)

        filtered = self._filter_candidates(main_candidates, target_cap, strict=True)
        print(f"   Step 2: {len(filtered)} peers from main industry passed filter")

        if len(filtered) < max_peers:
            print(f"   Step 3: Need more peers, checking related industries...")
            related_tickers = self._find_related_industry_peers(industry, target_ticker)
            related_tickers = [t for t in related_tickers if t not in main_industry_tickers]
            print(f"   Step 3: Found {len(related_tickers)} candidates from related industries")

            related_candidates = []
            for ticker in related_tickers:
                data = self._get_yahoo_data(ticker)
                if data:
                    related_candidates.append(data)

            related_filtered = self._filter_candidates(related_candidates, target_cap, strict=True)
            print(f"   Step 3: {len(related_filtered)} related peers passed filter")
            filtered.extend(related_filtered)

        if len(filtered) < max_peers:
            print(f"   Step 4: Only {len(filtered)} peers, trying relaxed filter on all...")
            all_candidates = main_candidates + [c for c in related_candidates if c not in main_candidates] if 'related_candidates' in dir() else main_candidates
            filtered = self._filter_candidates(all_candidates, target_cap, strict=False)
            print(f"   Step 4: {len(filtered)} peers with relaxed filter")

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