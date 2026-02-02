"""
Multiples Valuation
Valuation using comparable company analysis (P/E, P/B, EV/EBITDA, etc.)

Enhanced with Forward P/E support via Yahoo Finance for more accurate
growth company valuations.
"""

from typing import Dict, List, Optional
import logging

logger = logging.getLogger(__name__)


class MultiplesValuator:
    """Valuation using market multiples with Forward P/E support."""
    
    def __init__(self, company_data: Dict, peer_data: Dict[str, Dict], 
                 forward_estimates: Dict = None, peer_forward_estimates: Dict = None):
        """
        Initialize multiples valuator.
        
        Args:
            company_data: Target company data
            peer_data: Dict mapping peer ticker to their data
            forward_estimates: Forward estimates for target company (from Yahoo Finance)
            peer_forward_estimates: Dict mapping peer ticker to their forward estimates
        """
        self.overview = company_data.get('overview', {})
        self.income = company_data.get('income', [])
        self.balance = company_data.get('balance', [])
        self.cashflow = company_data.get('cashflow', [])
        
        self.peer_data = peer_data
        self.forward_estimates = forward_estimates or {}
        self.peer_forward_estimates = peer_forward_estimates or {}
    
    def _get_latest(self, data_list: List[Dict], field: str) -> Optional[float]:
        """Get latest value for a field."""
        if not data_list:
            return None
        return data_list[0].get(field)
    
    def _safe_divide(self, numerator: float, denominator: float) -> Optional[float]:
        """Safely divide two numbers."""
        if not denominator or denominator == 0:
            return None
        return numerator / denominator
    
    # ========================================
    # COMPANY MULTIPLES
    # ========================================
    
    def calculate_pe_ratio(self, use_forward: bool = True) -> Optional[float]:
        """
        P/E Ratio - prefers Forward P/E if available.
        
        Args:
            use_forward: If True, use Forward P/E when available
            
        Returns:
            P/E ratio (Forward if available and use_forward=True, else Trailing)
        """
        # Try Forward P/E first (from Yahoo Finance)
        if use_forward and self.forward_estimates.get('forward_pe'):
            return self.forward_estimates['forward_pe']
        
        # Fall back to Trailing P/E from overview
        pe = self.overview.get('pe_ratio')
        if pe and pe > 0:
            return pe
        
        # Calculate from market cap and net income
        market_cap = self.overview.get('market_cap')
        net_income = self._get_latest(self.income, 'net_income')
        
        return self._safe_divide(market_cap, net_income)
    
    def calculate_trailing_pe(self) -> Optional[float]:
        """Get Trailing P/E only (for comparison)."""
        return self.calculate_pe_ratio(use_forward=False)
    
    def calculate_forward_pe(self) -> Optional[float]:
        """Get Forward P/E only (from Yahoo Finance)."""
        return self.forward_estimates.get('forward_pe')
    
    def calculate_pb_ratio(self) -> Optional[float]:
        """
        P/B Ratio = Market Cap / Book Value
        """
        market_cap = self.overview.get('market_cap')
        equity = self._get_latest(self.balance, 'total_shareholder_equity')
        
        return self._safe_divide(market_cap, equity)
    
    def calculate_ev_ebitda(self) -> Optional[float]:
        """
        EV/EBITDA = Enterprise Value / EBITDA
        
        Where:
        Enterprise Value = Market Cap + Debt - Cash
        """
        # Calculate Enterprise Value
        market_cap = self.overview.get('market_cap')
        cash = self._get_latest(self.balance, 'cash') or 0
        long_term_debt = self._get_latest(self.balance, 'long_term_debt') or 0
        short_term_debt = self._get_latest(self.balance, 'short_term_debt') or 0
        debt = long_term_debt + short_term_debt
        
        if not market_cap:
            return None
        
        enterprise_value = market_cap + debt - cash
        
        # Get EBITDA
        ebitda = self._get_latest(self.income, 'ebitda')
        
        return self._safe_divide(enterprise_value, ebitda)
    
    def calculate_ev_revenue(self) -> Optional[float]:
        """
        EV/Revenue = Enterprise Value / Revenue
        """
        # Calculate Enterprise Value
        market_cap = self.overview.get('market_cap')
        cash = self._get_latest(self.balance, 'cash') or 0
        long_term_debt = self._get_latest(self.balance, 'long_term_debt') or 0
        short_term_debt = self._get_latest(self.balance, 'short_term_debt') or 0
        debt = long_term_debt + short_term_debt
        
        if not market_cap:
            return None
        
        enterprise_value = market_cap + debt - cash
        
        # Get Revenue
        revenue = self._get_latest(self.income, 'revenue')
        
        return self._safe_divide(enterprise_value, revenue)
    
    # ========================================
    # PEER MULTIPLES
    # ========================================
    
    def calculate_peer_multiples(self, use_forward_pe: bool = True) -> Dict[str, Dict]:
        """
        Calculate multiples for all peer companies.
        
        Args:
            use_forward_pe: If True, use Forward P/E for peers when available
        
        Returns:
            Dict mapping peer ticker to their multiples
        """
        peer_multiples = {}
        
        for ticker, data in self.peer_data.items():
            # Get forward estimates for this peer if available
            peer_fwd = self.peer_forward_estimates.get(ticker, {})
            
            # Create temporary valuator for peer
            peer_valuator = MultiplesValuator(
                data, {}, 
                forward_estimates=peer_fwd,
                peer_forward_estimates={}
            )
            
            # Get P/E (Forward if available, else Trailing)
            pe = peer_valuator.calculate_pe_ratio(use_forward=use_forward_pe)
            forward_pe = peer_fwd.get('forward_pe')
            trailing_pe = peer_valuator.calculate_trailing_pe()
            
            peer_multiples[ticker] = {
                'pe': pe,  # Best available (Forward preferred)
                'forward_pe': forward_pe,
                'trailing_pe': trailing_pe,
                'pb': peer_valuator.calculate_pb_ratio(),
                'ev_ebitda': peer_valuator.calculate_ev_ebitda(),
                'ev_revenue': peer_valuator.calculate_ev_revenue(),
                'market_cap': data.get('overview', {}).get('market_cap'),
            }
        
        return peer_multiples
    
    def calculate_peer_averages(self, use_forward_pe: bool = True) -> Dict[str, float]:
        """
        Calculate average multiples across all peers.
        
        Args:
            use_forward_pe: If True, use Forward P/E in averages
        
        Returns:
            Dict with average P/E, P/B, EV/EBITDA, EV/Revenue
        """
        peer_multiples = self.calculate_peer_multiples(use_forward_pe=use_forward_pe)
        
        # Collect valid values for each multiple
        pe_values = []
        forward_pe_values = []
        trailing_pe_values = []
        pb_values = []
        ev_ebitda_values = []
        ev_revenue_values = []
        
        for ticker, multiples in peer_multiples.items():
            if multiples['pe'] and multiples['pe'] > 0:
                pe_values.append(multiples['pe'])
            if multiples.get('forward_pe') and multiples['forward_pe'] > 0:
                forward_pe_values.append(multiples['forward_pe'])
            if multiples.get('trailing_pe') and multiples['trailing_pe'] > 0:
                trailing_pe_values.append(multiples['trailing_pe'])
            if multiples['pb'] and multiples['pb'] > 0:
                pb_values.append(multiples['pb'])
            if multiples['ev_ebitda'] and multiples['ev_ebitda'] > 0:
                ev_ebitda_values.append(multiples['ev_ebitda'])
            if multiples['ev_revenue'] and multiples['ev_revenue'] > 0:
                ev_revenue_values.append(multiples['ev_revenue'])
        
        # Calculate averages
        return {
            'avg_pe': sum(pe_values) / len(pe_values) if pe_values else None,
            'avg_forward_pe': sum(forward_pe_values) / len(forward_pe_values) if forward_pe_values else None,
            'avg_trailing_pe': sum(trailing_pe_values) / len(trailing_pe_values) if trailing_pe_values else None,
            'avg_pb': sum(pb_values) / len(pb_values) if pb_values else None,
            'avg_ev_ebitda': sum(ev_ebitda_values) / len(ev_ebitda_values) if ev_ebitda_values else None,
            'avg_ev_revenue': sum(ev_revenue_values) / len(ev_revenue_values) if ev_revenue_values else None,
            'pe_type': 'forward' if forward_pe_values else 'trailing',
        }
    
    # ========================================
    # FAIR VALUE CALCULATION
    # ========================================
    
    def calculate_fair_value_pe(self, use_forward: bool = True) -> Optional[float]:
        """
        Fair Value based on P/E multiple.
        
        Uses Forward P/E and Forward EPS if available for consistency.
        
        Fair Value = Peer Avg P/E × Company EPS
        """
        peer_averages = self.calculate_peer_averages(use_forward_pe=use_forward)
        avg_pe = peer_averages.get('avg_pe')
        
        if not avg_pe:
            return None
        
        # Use Forward EPS if available and using forward multiples
        if use_forward and self.forward_estimates.get('forward_eps'):
            eps = self.forward_estimates['forward_eps']
            logger.info(f"Using Forward EPS for fair value: ${eps:.2f}")
        else:
            # Fall back to trailing EPS
            net_income = self._get_latest(self.income, 'net_income')
            shares_outstanding = self.overview.get('shares_outstanding')
            
            if not net_income or not shares_outstanding:
                return None
            
            eps = net_income / shares_outstanding
        
        fair_value = avg_pe * eps
        
        return fair_value
    
    def calculate_fair_value_pb(self) -> Optional[float]:
        """
        Fair Value based on P/B multiple.
        
        Fair Value = Peer Avg P/B × Company Book Value per Share
        """
        peer_averages = self.calculate_peer_averages()
        avg_pb = peer_averages.get('avg_pb')
        
        if not avg_pb:
            return None
        
        # Get company's book value per share
        equity = self._get_latest(self.balance, 'total_shareholder_equity')
        shares_outstanding = self.overview.get('shares_outstanding')
        
        if not equity or not shares_outstanding:
            return None
        
        book_value_per_share = equity / shares_outstanding
        fair_value = avg_pb * book_value_per_share
        
        return fair_value
    
    def calculate_fair_value_ev_ebitda(self) -> Optional[float]:
        """
        Fair Value based on EV/EBITDA multiple.
        
        Steps:
        1. Enterprise Value = Peer Avg EV/EBITDA × Company EBITDA
        2. Equity Value = EV + Cash - Debt
        3. Fair Value = Equity Value / Shares
        """
        peer_averages = self.calculate_peer_averages()
        avg_ev_ebitda = peer_averages.get('avg_ev_ebitda')
        
        if not avg_ev_ebitda:
            return None
        
        # Calculate implied Enterprise Value
        ebitda = self._get_latest(self.income, 'ebitda')
        
        if not ebitda:
            return None
        
        implied_ev = avg_ev_ebitda * ebitda
        
        # Convert to Equity Value
        cash = self._get_latest(self.balance, 'cash') or 0
        long_term_debt = self._get_latest(self.balance, 'long_term_debt') or 0
        short_term_debt = self._get_latest(self.balance, 'short_term_debt') or 0
        debt = long_term_debt + short_term_debt
        
        equity_value = implied_ev + cash - debt
        
        # Calculate per share
        shares_outstanding = self.overview.get('shares_outstanding')
        
        if not shares_outstanding:
            return None
        
        fair_value = equity_value / shares_outstanding
        
        return fair_value
    
    def calculate_average_fair_value(self, use_forward: bool = True) -> Optional[float]:
        """
        Calculate average fair value across all multiples methods.
        
        Args:
            use_forward: If True, use Forward P/E in P/E-based fair value
        """
        fair_values = []
        
        fv_pe = self.calculate_fair_value_pe(use_forward=use_forward)
        fv_pb = self.calculate_fair_value_pb()
        fv_ev_ebitda = self.calculate_fair_value_ev_ebitda()
        
        if fv_pe and fv_pe > 0:
            fair_values.append(fv_pe)
        if fv_pb and fv_pb > 0:
            fair_values.append(fv_pb)
        if fv_ev_ebitda and fv_ev_ebitda > 0:
            fair_values.append(fv_ev_ebitda)
        
        if not fair_values:
            return None
        
        return sum(fair_values) / len(fair_values)
    
    # ========================================
    # SUMMARY
    # ========================================
    
    def get_multiples_summary(self, use_forward: bool = True) -> Dict:
        """
        Get complete multiples analysis with assumptions and results.
        
        Args:
            use_forward: If True, prefer Forward P/E over Trailing P/E
        
        Returns:
            Complete multiples analysis including forward estimates
        """
        # Company multiples
        forward_pe = self.calculate_forward_pe()
        trailing_pe = self.calculate_trailing_pe()
        
        company_multiples = {
            'pe': forward_pe if (use_forward and forward_pe) else trailing_pe,
            'forward_pe': forward_pe,
            'trailing_pe': trailing_pe,
            'pb': self.calculate_pb_ratio(),
            'ev_ebitda': self.calculate_ev_ebitda(),
            'ev_revenue': self.calculate_ev_revenue(),
            'pe_type': 'forward' if (use_forward and forward_pe) else 'trailing',
        }
        
        # Peer multiples
        peer_multiples = self.calculate_peer_multiples(use_forward_pe=use_forward)
        peer_averages = self.calculate_peer_averages(use_forward_pe=use_forward)
        
        # Fair values
        fair_value_pe = self.calculate_fair_value_pe(use_forward=use_forward)
        fair_value_pb = self.calculate_fair_value_pb()
        fair_value_ev_ebitda = self.calculate_fair_value_ev_ebitda()
        average_fair_value = self.calculate_average_fair_value(use_forward=use_forward)
        
        # Determine which P/E type was used
        pe_type_used = 'forward' if (use_forward and forward_pe) else 'trailing'
        
        return {
            # === COMPANY MULTIPLES ===
            'company_multiples': company_multiples,
            
            # === PEER DATA ===
            'peer_multiples': peer_multiples,
            'peer_averages': peer_averages,
            'peer_count': len(self.peer_data),
            
            # === FAIR VALUES ===
            'fair_value_pe': fair_value_pe,
            'fair_value_pb': fair_value_pb,
            'fair_value_ev_ebitda': fair_value_ev_ebitda,
            'average_fair_value': average_fair_value,
            
            # === FORWARD ESTIMATES ===
            'forward_estimates': {
                'forward_pe': forward_pe,
                'forward_eps': self.forward_estimates.get('forward_eps'),
                'trailing_pe': trailing_pe,
                'trailing_eps': self.forward_estimates.get('trailing_eps'),
                'analyst_target': self.forward_estimates.get('target_price_mean'),
                'analyst_count': self.forward_estimates.get('analyst_count'),
            },
            
            # === ASSUMPTIONS ===
            'assumptions': {
                'method': 'Comparable Company Analysis',
                'peers': list(self.peer_data.keys()),
                'multiples_used': ['P/E', 'P/B', 'EV/EBITDA'],
                'pe_type': pe_type_used,
                'note': f'Using {pe_type_used.title()} P/E for valuation',
            }
        }