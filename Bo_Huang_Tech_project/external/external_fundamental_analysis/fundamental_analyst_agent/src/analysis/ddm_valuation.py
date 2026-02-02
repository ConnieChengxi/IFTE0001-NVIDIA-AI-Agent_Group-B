"""
Dividend Discount Model (DDM)
Valuation for dividend-paying companies using Gordon Growth Model.
"""

from typing import Dict, List, Optional
from config.settings import (
    RISK_FREE_RATE,
    EQUITY_RISK_PREMIUM,
    MIN_DIVIDEND_YIELD,
    MIN_DIVIDEND_HISTORY
)


class DDMValuator:
    """Dividend Discount Model valuator."""
    
    def __init__(self, company_data: Dict):
        """
        Initialize DDM valuator.
        
        Args:
            company_data: Dict with keys: overview, income, balance, cashflow
        """
        self.overview = company_data.get('overview', {})
        self.income = company_data.get('income', [])
        self.balance = company_data.get('balance', [])
        self.cashflow = company_data.get('cashflow', [])
    
    def _get_latest(self, data_list: List[Dict], field: str) -> Optional[float]:
        """Get latest value for a field."""
        if not data_list:
            return None
        return data_list[0].get(field)
    
    def _get_historical(self, data_list: List[Dict], field: str, years: int = 5) -> List[float]:
        """Get historical values for a field."""
        values = []
        for i in range(min(years, len(data_list))):
            value = data_list[i].get(field)
            if value is not None:
                values.append(value)
        return values
    
    # ========================================
    # DDM APPLICABILITY CHECK
    # ========================================
    
    def is_ddm_applicable(self) -> tuple[bool, str]:
        """
        Check if DDM is applicable for this company.
        
        Criteria:
        1. Dividend yield >= MIN_DIVIDEND_YIELD (1%)
        2. Dividend history >= MIN_DIVIDEND_HISTORY (3 years)
        
        Returns:
            Tuple of (is_applicable, reason)
        """
        # Check dividend yield
        dividend_yield = self.overview.get('dividend_yield', 0)
        
        if not dividend_yield or dividend_yield < MIN_DIVIDEND_YIELD:
            return False, f"Dividend yield ({dividend_yield:.2%}) < {MIN_DIVIDEND_YIELD:.0%} minimum"
        
        # Check dividend history
        dividend_history = self._get_historical(self.cashflow, 'dividends_paid', years=MIN_DIVIDEND_HISTORY)
        
        if len(dividend_history) < MIN_DIVIDEND_HISTORY:
            return False, f"Insufficient dividend history ({len(dividend_history)} years < {MIN_DIVIDEND_HISTORY} required)"
        
        # Check for consistent dividends (all positive)
        if not all(div and abs(div) > 0 for div in dividend_history):
            return False, "Inconsistent dividend payments"
        
        return True, "DDM applicable"
    
    # ========================================
    # DIVIDEND METRICS
    # ========================================
    
    def calculate_dividend_growth_rate(self) -> Optional[float]:
        """
        Calculate historical dividend growth rate (CAGR).
        
        CAGR = (Dividend_latest / Dividend_oldest) ^ (1/years) - 1
        """
        dividend_history = self._get_historical(self.cashflow, 'dividends_paid', years=5)
        
        if len(dividend_history) < 2:
            return None
        
        # Dividends are usually negative in cash flow statement
        dividends = [abs(d) for d in dividend_history if d]
        
        if len(dividends) < 2:
            return None
        
        dividend_oldest = dividends[-1]  # Oldest
        dividend_latest = dividends[0]   # Most recent
        years = len(dividends) - 1
        
        if dividend_oldest <= 0:
            return None
        
        cagr = (dividend_latest / dividend_oldest) ** (1 / years) - 1
        
        # Cap at reasonable levels
        cagr = max(-0.10, min(cagr, 0.20))  # Between -10% and 20%
        
        return cagr
    
    def calculate_current_dividend_per_share(self) -> Optional[float]:
        """
        Calculate current annual dividend per share.
        
        DPS = Total Dividends Paid / Shares Outstanding
        """
        dividends_paid = abs(self._get_latest(self.cashflow, 'dividends_paid') or 0)
        shares_outstanding = self.overview.get('shares_outstanding')
        
        if not shares_outstanding or shares_outstanding <= 0:
            return None
        
        dps = dividends_paid / shares_outstanding
        
        return dps
    
    def calculate_required_return(self) -> float:
        """
        Calculate required return (cost of equity).
        
        Required Return = Risk-Free Rate + Beta × Equity Risk Premium
        """
        beta = self.overview.get('beta', 1.0)
        if not beta or beta <= 0:
            beta = 1.0
        
        required_return = RISK_FREE_RATE + (beta * EQUITY_RISK_PREMIUM)
        
        return required_return
    
    # ========================================
    # GORDON GROWTH MODEL
    # ========================================
    
    def calculate_fair_value_gordon(self) -> Optional[float]:
        """
        Calculate fair value using Gordon Growth Model.
        
        Fair Value = D1 / (r - g)
        
        Where:
        - D1 = Next year's expected dividend = D0 × (1 + g)
        - r = Required return (cost of equity)
        - g = Dividend growth rate
        """
        # Check if DDM is applicable
        is_applicable, reason = self.is_ddm_applicable()
        
        if not is_applicable:
            return None
        
        # Get current dividend per share
        d0 = self.calculate_current_dividend_per_share()
        
        if not d0 or d0 <= 0:
            return None
        
        # Get dividend growth rate
        g = self.calculate_dividend_growth_rate()
        
        if g is None:
            return None
        
        # Get required return
        r = self.calculate_required_return()
        
        # Check validity: r must be > g
        if r <= g:
            # Model breaks down if growth >= required return
            # Adjust growth down
            g = r - 0.02
        
        # Calculate next year's dividend
        d1 = d0 * (1 + g)
        
        # Gordon Growth Model
        fair_value = d1 / (r - g)
        
        return fair_value
    
    # ========================================
    # SUMMARY
    # ========================================
    
    def get_ddm_summary(self) -> Dict:
        """
        Get complete DDM analysis with assumptions and results.
        
        This preserves all key assumptions and calculations
        for use in the final investment report.
        """
        # Check applicability
        is_applicable, applicability_reason = self.is_ddm_applicable()
        
        if not is_applicable:
            return {
                'fair_value_per_share': None,
                'applicable': False,
                'reason': applicability_reason,
            }
        
        # Calculate metrics
        current_dps = self.calculate_current_dividend_per_share()
        dividend_growth = self.calculate_dividend_growth_rate()
        required_return = self.calculate_required_return()
        fair_value = self.calculate_fair_value_gordon()
        
        # Get dividend history
        dividend_history = self._get_historical(self.cashflow, 'dividends_paid', years=5)
        dividend_history = [abs(d) for d in dividend_history if d]
        
        return {
            # === APPLICABILITY ===
            'applicable': True,
            'reason': applicability_reason,
            
            # === ASSUMPTIONS ===
            'assumptions': {
                'risk_free_rate': RISK_FREE_RATE,
                'equity_risk_premium': EQUITY_RISK_PREMIUM,
                'beta': self.overview.get('beta', 1.0),
                'required_return': required_return,
                'dividend_growth_rate': dividend_growth,
                'model': 'Gordon Growth Model',
            },
            
            # === DIVIDEND DATA ===
            'current_dividend_per_share': current_dps,
            'dividend_yield': self.overview.get('dividend_yield', 0),
            'dividend_history': dividend_history,
            'dividend_history_years': len(dividend_history),
            
            # === RESULT ===
            'fair_value_per_share': fair_value,
        }
        