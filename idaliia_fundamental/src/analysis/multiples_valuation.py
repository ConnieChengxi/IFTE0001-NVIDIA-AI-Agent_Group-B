"""
Comparable company valuation using P/E, P/B, EV/EBITDA, and PEG multiples.
"""

from typing import Dict, List, Optional
import logging
from src.utils.helpers import get_latest, safe_divide

logger = logging.getLogger(__name__)


class MultiplesValuator:

    def __init__(self, company_data: Dict, peer_data: Dict[str, Dict],
                 forward_estimates: Dict = None, peer_forward_estimates: Dict = None):
        self.overview = company_data.get('overview', {})
        self.income = company_data.get('income', [])
        self.balance = company_data.get('balance', [])
        self.cashflow = company_data.get('cashflow', [])

        self.peer_data = peer_data
        self.forward_estimates = forward_estimates or {}
        self.peer_forward_estimates = peer_forward_estimates or {}

    def _get_latest(self, data_list: List[Dict], field: str) -> Optional[float]:
        return get_latest(data_list, field, convert=True)

    def _safe_divide(self, numerator: float, denominator: float) -> Optional[float]:
        return safe_divide(numerator, denominator)

    def _calculate_ebitda(self) -> Optional[float]:
        """Calculate EBITDA with fallback methods."""
        ebitda = self._get_latest(self.income, 'ebitda')
        if ebitda and ebitda > 0:
            return ebitda

        operating_income = self._get_latest(self.income, 'operating_income')
        da = self._get_latest(self.cashflow, 'depreciation_amortization')

        if operating_income and da:
            ebitda = operating_income + abs(da)
            if ebitda > 0:
                return ebitda

        net_income = self._get_latest(self.income, 'net_income')
        interest = self._get_latest(self.income, 'interest_expense') or 0
        taxes = self._get_latest(self.income, 'income_tax_expense') or 0

        if net_income and da:
            ebitda = net_income + abs(interest) + abs(taxes) + abs(da)
            if ebitda > 0:
                return ebitda

        return None
    
    def calculate_revenue_growth(self) -> Optional[float]:
        """Calculate YoY revenue growth (for display/reporting)."""
        if len(self.income) < 2:
            return None

        current_revenue = self.income[0].get('revenue')
        previous_revenue = self.income[1].get('revenue')

        if not current_revenue or not previous_revenue or previous_revenue <= 0:
            return None

        growth = (current_revenue - previous_revenue) / previous_revenue

        logger.info(f"Revenue YoY: current={current_revenue:,.0f}, previous={previous_revenue:,.0f}, "
                   f"growth={growth*100:.1f}%")

        return growth

    def calculate_revenue_cagr(self, years: int = 5) -> Optional[float]:
        """
        Calculate revenue CAGR over specified years.
        More stable than YoY growth for valuation purposes.
        """
        available_years = min(years, len(self.income))
        if available_years < 2:
            return None

        current_revenue = self.income[0].get('revenue')
        oldest_revenue = self.income[available_years - 1].get('revenue')

        if not current_revenue or not oldest_revenue or oldest_revenue <= 0:
            return None

        periods = available_years - 1
        cagr = (current_revenue / oldest_revenue) ** (1 / periods) - 1

        logger.info(f"Revenue CAGR: current={current_revenue:,.0f}, oldest={oldest_revenue:,.0f}, "
                   f"periods={periods}, CAGR={cagr*100:.1f}%")

        return cagr
    
    def calculate_eps_growth(self) -> Optional[float]:
        if len(self.income) < 2:
            return None

        shares = self._to_float(self.overview.get('shares_outstanding'))
        if not shares:
            return None

        current_ni = self._to_float(self.income[0].get('net_income'))
        previous_ni = self._to_float(self.income[1].get('net_income'))

        if not current_ni or not previous_ni or previous_ni <= 0:
            return None

        growth = (current_ni - previous_ni) / abs(previous_ni)
        return growth
    
    def _to_float(self, value) -> Optional[float]:
        """Safely convert value to float."""
        if value is None:
            return None
        try:
            return float(value)
        except (ValueError, TypeError):
            return None

    def calculate_pe_ratio(self, use_forward: bool = True) -> Optional[float]:
        if use_forward:
            fwd_pe = self._to_float(self.forward_estimates.get('forward_pe'))
            if fwd_pe and fwd_pe > 0:
                return fwd_pe

        pe = self._to_float(self.overview.get('pe_ratio'))
        if pe and pe > 0:
            return pe

        market_cap = self._to_float(self.overview.get('market_cap'))
        net_income = self._get_latest(self.income, 'net_income')

        return self._safe_divide(market_cap, net_income)
    
    def calculate_trailing_pe(self) -> Optional[float]:
        return self.calculate_pe_ratio(use_forward=False)
    
    def calculate_forward_pe(self) -> Optional[float]:
        return self._to_float(self.forward_estimates.get('forward_pe'))
    
    def calculate_peg_ratio(self, use_forward: bool = True) -> Optional[float]:
        pe = self.calculate_pe_ratio(use_forward=use_forward)

        # Use 5-year CAGR for more stable growth metric, fallback to YoY
        growth = self.calculate_revenue_cagr(years=5)
        if not growth or growth <= 0:
            growth = self.calculate_revenue_growth()

        if not pe or not growth or growth <= 0:
            return None

        growth_pct = growth * 100

        if growth_pct < 5:
            return None

        peg = pe / growth_pct
        return peg
    
    def calculate_pb_ratio(self) -> Optional[float]:
        market_cap = self._to_float(self.overview.get('market_cap'))
        equity = self._get_latest(self.balance, 'total_shareholder_equity')
        return self._safe_divide(market_cap, equity)

    def calculate_ev_ebitda(self) -> Optional[float]:
        market_cap = self._to_float(self.overview.get('market_cap'))
        cash = self._get_latest(self.balance, 'cash') or 0
        long_term_debt = self._get_latest(self.balance, 'long_term_debt') or 0
        short_term_debt = self._get_latest(self.balance, 'short_term_debt') or 0
        debt = long_term_debt + short_term_debt

        if not market_cap:
            return None

        enterprise_value = market_cap + debt - cash
        ebitda = self._calculate_ebitda()

        return self._safe_divide(enterprise_value, ebitda)

    def calculate_ev_revenue(self) -> Optional[float]:
        market_cap = self._to_float(self.overview.get('market_cap'))
        cash = self._get_latest(self.balance, 'cash') or 0
        long_term_debt = self._get_latest(self.balance, 'long_term_debt') or 0
        short_term_debt = self._get_latest(self.balance, 'short_term_debt') or 0
        debt = long_term_debt + short_term_debt

        if not market_cap:
            return None

        enterprise_value = market_cap + debt - cash
        revenue = self._get_latest(self.income, 'revenue')

        return self._safe_divide(enterprise_value, revenue)
    
    def calculate_peer_multiples(self, use_forward_pe: bool = True) -> Dict[str, Dict]:
        peer_multiples = {}
        
        for ticker, data in self.peer_data.items():
            peer_fwd = self.peer_forward_estimates.get(ticker, {})
            
            peer_valuator = MultiplesValuator(
                data, {}, 
                forward_estimates=peer_fwd,
                peer_forward_estimates={}
            )
            
            pe = peer_valuator.calculate_pe_ratio(use_forward=use_forward_pe)
            forward_pe = peer_valuator._to_float(peer_fwd.get('forward_pe'))
            trailing_pe = peer_valuator.calculate_trailing_pe()
            growth = peer_valuator.calculate_revenue_cagr()
            peg = peer_valuator.calculate_peg_ratio(use_forward=use_forward_pe)

            peer_multiples[ticker] = {
                'pe': pe,
                'forward_pe': forward_pe,
                'trailing_pe': trailing_pe,
                'peg': peg,
                'revenue_growth': growth,
                'pb': peer_valuator.calculate_pb_ratio(),
                'ev_ebitda': peer_valuator.calculate_ev_ebitda(),
                'ev_revenue': peer_valuator.calculate_ev_revenue(),
                'market_cap': peer_valuator._to_float(data.get('overview', {}).get('market_cap')),
            }
        
        return peer_multiples
    
    def calculate_peer_averages(self, use_forward_pe: bool = True) -> Dict[str, float]:
        peer_multiples = self.calculate_peer_multiples(use_forward_pe=use_forward_pe)
        
        pe_values = []
        forward_pe_values = []
        trailing_pe_values = []
        peg_values = []
        growth_values = []
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
            if multiples.get('peg') and 0 < multiples['peg'] < 10:
                peg_values.append(multiples['peg'])
            if multiples.get('revenue_growth') and multiples['revenue_growth'] > 0:
                growth_values.append(multiples['revenue_growth'])
            if multiples['pb'] and multiples['pb'] > 0:
                pb_values.append(multiples['pb'])
            if multiples['ev_ebitda'] and multiples['ev_ebitda'] > 0:
                ev_ebitda_values.append(multiples['ev_ebitda'])
            if multiples['ev_revenue'] and multiples['ev_revenue'] > 0:
                ev_revenue_values.append(multiples['ev_revenue'])
        
        return {
            'avg_pe': sum(pe_values) / len(pe_values) if pe_values else None,
            'avg_forward_pe': sum(forward_pe_values) / len(forward_pe_values) if forward_pe_values else None,
            'avg_trailing_pe': sum(trailing_pe_values) / len(trailing_pe_values) if trailing_pe_values else None,
            'avg_peg': sum(peg_values) / len(peg_values) if peg_values else None,
            'avg_growth': sum(growth_values) / len(growth_values) if growth_values else None,
            'avg_pb': sum(pb_values) / len(pb_values) if pb_values else None,
            'avg_ev_ebitda': sum(ev_ebitda_values) / len(ev_ebitda_values) if ev_ebitda_values else None,
            'avg_ev_revenue': sum(ev_revenue_values) / len(ev_revenue_values) if ev_revenue_values else None,
            'pe_type': 'forward' if forward_pe_values else 'trailing',
        }
    
    def calculate_fair_value_peg(self, use_forward: bool = True) -> Optional[float]:
        peer_averages = self.calculate_peer_averages(use_forward_pe=use_forward)
        avg_peg = peer_averages.get('avg_peg')
        
        if not avg_peg:
            logger.warning("No valid PEG ratios from peers, falling back to P/E method")
            return None
        
        company_growth = self.calculate_revenue_cagr(years=5)
        if not company_growth or company_growth <= 0:
            company_growth = self.calculate_revenue_growth()
            if not company_growth or company_growth <= 0:
                logger.warning("No valid growth rate for company, falling back to P/E method")
                return None

        capped_growth = min(company_growth, 0.60)
        company_growth_pct = capped_growth * 100

        adjusted_pe = avg_peg * company_growth_pct
        
        forward_eps = self._to_float(self.forward_estimates.get('forward_eps'))
        if use_forward and forward_eps:
            eps = forward_eps
        else:
            net_income = self._get_latest(self.income, 'net_income')
            shares_outstanding = self._to_float(self.overview.get('shares_outstanding'))

            if not net_income or not shares_outstanding:
                return None

            eps = net_income / shares_outstanding

        fair_value = adjusted_pe * eps

        growth_note = f" (capped from {company_growth*100:.1f}%)" if company_growth > 0.60 else ""
        logger.info(f"PEG Fair Value: Peer Avg PEG={avg_peg:.2f}, Growth={company_growth_pct:.1f}%{growth_note}, "
                   f"Adjusted P/E={adjusted_pe:.1f}x, EPS=${eps:.2f}, Fair Value=${fair_value:.2f}")

        return fair_value

    def calculate_fair_value_pe(self, use_forward: bool = True) -> Optional[float]:
        peer_averages = self.calculate_peer_averages(use_forward_pe=use_forward)
        avg_pe = peer_averages.get('avg_pe')

        if not avg_pe:
            return None

        forward_eps = self._to_float(self.forward_estimates.get('forward_eps'))
        if use_forward and forward_eps:
            eps = forward_eps
        else:
            net_income = self._get_latest(self.income, 'net_income')
            shares_outstanding = self._to_float(self.overview.get('shares_outstanding'))

            if not net_income or not shares_outstanding:
                return None

            eps = net_income / shares_outstanding

        fair_value = avg_pe * eps
        return fair_value
    
    def calculate_fair_value_pb(self) -> Optional[float]:
        peer_averages = self.calculate_peer_averages()
        avg_pb = peer_averages.get('avg_pb')

        if not avg_pb:
            return None

        equity = self._get_latest(self.balance, 'total_shareholder_equity')
        shares_outstanding = self._to_float(self.overview.get('shares_outstanding'))

        if not equity or not shares_outstanding:
            return None

        book_value_per_share = equity / shares_outstanding
        fair_value = avg_pb * book_value_per_share
        return fair_value

    def calculate_fair_value_ev_ebitda(self) -> Optional[float]:
        peer_averages = self.calculate_peer_averages()
        avg_ev_ebitda = peer_averages.get('avg_ev_ebitda')

        if not avg_ev_ebitda:
            return None

        ebitda = self._calculate_ebitda()

        if not ebitda:
            return None

        implied_ev = avg_ev_ebitda * ebitda

        cash = self._get_latest(self.balance, 'cash') or 0
        long_term_debt = self._get_latest(self.balance, 'long_term_debt') or 0
        short_term_debt = self._get_latest(self.balance, 'short_term_debt') or 0
        debt = long_term_debt + short_term_debt

        equity_value = implied_ev + cash - debt

        shares_outstanding = self._to_float(self.overview.get('shares_outstanding'))

        if not shares_outstanding:
            return None

        fair_value = equity_value / shares_outstanding
        return fair_value
    
    def calculate_average_fair_value(self, use_forward: bool = True, use_peg: bool = True) -> Optional[float]:
        fair_values = []
        components = []

        if use_peg:
            fv_peg = self.calculate_fair_value_peg(use_forward=use_forward)
            if fv_peg and fv_peg > 0:
                fair_values.append(fv_peg)
                components.append(f"PEG=${fv_peg:.2f}")
            else:
                fv_pe = self.calculate_fair_value_pe(use_forward=use_forward)
                if fv_pe and fv_pe > 0:
                    fair_values.append(fv_pe)
                    components.append(f"P/E=${fv_pe:.2f}")
        else:
            fv_pe = self.calculate_fair_value_pe(use_forward=use_forward)
            if fv_pe and fv_pe > 0:
                fair_values.append(fv_pe)
                components.append(f"P/E=${fv_pe:.2f}")

        fv_pb = self.calculate_fair_value_pb()
        fv_ev_ebitda = self.calculate_fair_value_ev_ebitda()

        if fv_pb and fv_pb > 0:
            fair_values.append(fv_pb)
            components.append(f"P/B=${fv_pb:.2f}")
        if fv_ev_ebitda and fv_ev_ebitda > 0:
            fair_values.append(fv_ev_ebitda)
            components.append(f"EV/EBITDA=${fv_ev_ebitda:.2f}")

        if not fair_values:
            return None

        avg = sum(fair_values) / len(fair_values)
        logger.info(f"Multiples Average Fair Value: {' + '.join(components)} = ${avg:.2f} (avg of {len(fair_values)} methods)")

        return avg
    
    def get_multiples_summary(self, use_forward: bool = True, use_peg: bool = True) -> Dict:
        forward_pe = self.calculate_forward_pe()
        trailing_pe = self.calculate_trailing_pe()
        company_growth_yoy = self.calculate_revenue_growth()
        company_growth_cagr = self.calculate_revenue_cagr(years=5)
        company_growth = company_growth_cagr if company_growth_cagr and company_growth_cagr > 0 else company_growth_yoy
        company_peg = self.calculate_peg_ratio(use_forward=use_forward)
        
        company_multiples = {
            'pe': forward_pe if (use_forward and forward_pe) else trailing_pe,
            'forward_pe': forward_pe,
            'trailing_pe': trailing_pe,
            'peg': company_peg,
            'revenue_growth': company_growth_yoy,
            'revenue_growth_cagr': company_growth_cagr,
            'pb': self.calculate_pb_ratio(),
            'ev_ebitda': self.calculate_ev_ebitda(),
            'ev_revenue': self.calculate_ev_revenue(),
            'pe_type': 'forward' if (use_forward and forward_pe) else 'trailing',
        }
        
        peer_multiples = self.calculate_peer_multiples(use_forward_pe=use_forward)
        peer_averages = self.calculate_peer_averages(use_forward_pe=use_forward)
        
        fair_value_peg = self.calculate_fair_value_peg(use_forward=use_forward)
        fair_value_pe = self.calculate_fair_value_pe(use_forward=use_forward)
        fair_value_pb = self.calculate_fair_value_pb()
        fair_value_ev_ebitda = self.calculate_fair_value_ev_ebitda()
        average_fair_value = self.calculate_average_fair_value(use_forward=use_forward, use_peg=use_peg)
        
        pe_type_used = 'forward' if (use_forward and forward_pe) else 'trailing'
        valuation_method = 'PEG-adjusted' if (use_peg and fair_value_peg) else 'Simple P/E'
        
        return {
            'company_multiples': company_multiples,
            
            'peer_multiples': peer_multiples,
            'peer_averages': peer_averages,
            'peer_count': len(self.peer_data),
            
            'fair_value_peg': fair_value_peg,
            'fair_value_pe': fair_value_pe,
            'fair_value_pb': fair_value_pb,
            'fair_value_ev_ebitda': fair_value_ev_ebitda,
            'average_fair_value': average_fair_value,
            
            'forward_estimates': {
                'forward_pe': forward_pe,
                'forward_eps': self.forward_estimates.get('forward_eps'),
                'trailing_pe': trailing_pe,
                'trailing_eps': self.forward_estimates.get('trailing_eps'),
                'analyst_target': self.forward_estimates.get('target_price_mean'),
                'analyst_count': self.forward_estimates.get('analyst_count'),
            },
            
            'peg_analysis': {
                'company_peg': company_peg,
                'company_growth_yoy': company_growth_yoy,
                'company_growth_cagr': company_growth_cagr,
                'company_growth_used': company_growth,
                'company_growth_capped': min(company_growth, 0.60) if company_growth else None,
                'growth_was_capped': company_growth > 0.60 if company_growth else False,
                'peer_avg_peg': peer_averages.get('avg_peg'),
                'peer_avg_growth': peer_averages.get('avg_growth'),
                'growth_adjusted_pe': peer_averages.get('avg_peg') * (min(company_growth, 0.60) * 100) if peer_averages.get('avg_peg') and company_growth else None,
                'method_used': valuation_method,
            },
            
            'assumptions': {
                'method': 'Comparable Company Analysis with PEG Adjustment',
                'peers': list(self.peer_data.keys()),
                'multiples_used': ['PEG', 'P/B', 'EV/EBITDA'],
                'pe_type': pe_type_used,
                'valuation_method': valuation_method,
                'note': f'Using {valuation_method} for growth-adjusted valuation',
            }
        }