"""
DCF Valuation Model
Discounted Cash Flow valuation with company-type specific assumptions.
Supports different growth calculation methods for growth, balanced, dividend, and cyclical companies.
"""

from typing import Dict, List, Optional, Tuple
from config.settings import (
    RISK_FREE_RATE,
    EQUITY_RISK_PREMIUM,
    TERMINAL_GROWTH_RATE,
    DCF_PROJECTION_YEARS
)


class DCFValuator:
    """
    DCF valuation model with company-type specific growth assumptions.
    
    Supports 4 company types:
    - Growth: Weight recent years more heavily (AI boom, new products)
    - Balanced: Use historical average (steady growth)
    - Dividend: Conservative approach (lower bound)
    - Cyclical: Normalize through cycle (ignore peaks/troughs)
    """
    
    # Parameters by company type
    # Note: terminal_growth will be set dynamically in __init__ from settings.py
    DCF_PARAMS_BY_TYPE = {
        'growth': {
            'projection_years': 5,
            'growth_method': 'weighted_recent',
            'recent_years_weight': 2,  # Last 2 years weighted more
            'max_growth_rate': 0.40,   # Not used anymore (no cap)
        },
        'balanced': {
            'projection_years': 5,
            'growth_method': 'historical_avg',
            'recent_years_weight': 0,
            'max_growth_rate': 0.20,
        },
        'dividend': {
            'projection_years': 5,
            'growth_method': 'conservative',
            'recent_years_weight': 0,
            'max_growth_rate': 0.10,
        },
        'cyclical': {
            'projection_years': 5,
            'growth_method': 'normalized',
            'recent_years_weight': 0,
            'max_growth_rate': 0.15,
        }
    }
    
    def __init__(self, company_data: Dict, company_type: str = 'balanced', sector: str = None):
        """
        Initialize DCF valuator.
        
        Args:
            company_data: Dict with keys: overview, income, balance, cashflow
            company_type: 'growth', 'balanced', 'dividend', or 'cyclical'
            sector: Company sector (for future sector-specific adjustments)
        """
        self.overview = company_data.get('overview', {})
        self.income = company_data.get('income', [])
        self.balance = company_data.get('balance', [])
        self.cashflow = company_data.get('cashflow', [])
        
        # Company classification
        self.company_type = company_type
        self.sector = sector
        
        # Get parameters for this company type (make a copy to avoid modifying class variable)
        self.params = self.DCF_PARAMS_BY_TYPE.get(company_type, self.DCF_PARAMS_BY_TYPE['balanced']).copy()
        
        # Add terminal_growth from settings.py (dynamically, not at class load time)
        self.params['terminal_growth'] = TERMINAL_GROWTH_RATE
        
        # Calculate FCF history for growth calculations
        self.fcf_history = self._calculate_fcf_history()
    
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
    
    def _calculate_fcf_history(self) -> List[float]:
        """
        Calculate historical Free Cash Flow.
        FCF = Operating Cash Flow - CapEx
        Returns list from oldest to newest.
        """
        ocf_history = self._get_historical(self.cashflow, 'operating_cashflow', years=5)
        capex_history = self._get_historical(self.cashflow, 'capital_expenditures', years=5)
        
        if not ocf_history or not capex_history:
            return []
        
        fcf_history = []
        for i in range(min(len(ocf_history), len(capex_history))):
            ocf = ocf_history[i]
            capex = abs(capex_history[i]) if capex_history[i] else 0
            fcf = ocf - capex
            if fcf > 0:  # Only include positive FCF
                fcf_history.append(fcf)
        
        # Reverse to get oldest → newest
        fcf_history.reverse()
        
        return fcf_history
    
    def _calculate_cagr(self, values: List[float]) -> float:
        """
        Calculate Compound Annual Growth Rate.
        
        CAGR = (End Value / Start Value)^(1/years) - 1
        """
        if not values or len(values) < 2:
            return 0.10  # Default 10%
        
        start_value = values[0]
        end_value = values[-1]
        years = len(values) - 1
        
        if start_value <= 0 or end_value <= 0:
            return 0.10
        
        cagr = (end_value / start_value) ** (1 / years) - 1
        
        return cagr
    
    # ========================================
    # GROWTH CALCULATION METHODS
    # ========================================
    
    def _weighted_recent_growth(self) -> float:
        """
        Weight recent years more heavily (for growth companies).
        
        Used for companies experiencing acceleration (e.g., NVDA AI boom).
        Formula: 70% recent growth + 30% historical growth
        
        Example:
        - Last 2 years: 25B → 60B = 140% CAGR
        - Full 5 years: 10B → 60B = 56% CAGR
        - Weighted: 140% × 0.7 + 56% × 0.3 = 115%
        """
        if not self.fcf_history or len(self.fcf_history) < 3:
            return 0.10  # Default 10%
        
        recent_weight = self.params['recent_years_weight']
        
        # Calculate recent growth (last N years)
        if len(self.fcf_history) >= recent_weight + 1:
            recent_fcf = self.fcf_history[-recent_weight:]
            recent_growth = self._calculate_cagr(recent_fcf)
        else:
            recent_growth = 0.10
        
        # Calculate full period growth
        full_growth = self._calculate_cagr(self.fcf_history)
        
        # Weighted average: 70% recent, 30% historical
        weighted_growth = (recent_growth * 0.7) + (full_growth * 0.3)
        
        return weighted_growth
    
    def _conservative_growth(self) -> float:
        """
        Conservative growth using 25th percentile (for dividend companies).
        
        Calculate growth for all rolling 3-year periods, then take lower bound.
        This avoids overestimating growth for mature, stable companies.
        
        Example:
        - Period 1 (2020-2022): -2.5%/year
        - Period 2 (2021-2023): -2.3%/year  
        - Period 3 (2022-2024): +10.2%/year
        - 25th percentile: -2.4% → Floor at 2% = 2%
        """
        if not self.fcf_history or len(self.fcf_history) < 3:
            return 0.03  # Default 3%
        
        # Calculate growth for all rolling 3-year periods
        growth_rates = []
        for i in range(len(self.fcf_history) - 2):
            period = self.fcf_history[i:i+3]
            growth = self._calculate_cagr(period)
            growth_rates.append(growth)
        
        if not growth_rates:
            return 0.03
        
        # Sort and take 25th percentile (conservative)
        growth_rates.sort()
        index_25 = max(0, len(growth_rates) // 4)
        percentile_25 = growth_rates[index_25]
        
        # Floor at 2% (no negative growth in perpetuity)
        return max(percentile_25, 0.02)
    
    def _normalized_growth(self) -> float:
        """
        Normalized growth for cyclical companies.
        
        Use median FCF to avoid peak/trough distortions.
        If currently at peak (FCF >> median), use conservative growth.
        If at trough (FCF << median), use moderate rebound.
        
        Example (Exxon):
        - History: [30B, 5B, 20B, 55B, 40B, 35B]
        - Median: 32.5B
        - Current: 35B (near median)
        - Use normalized CAGR
        """
        if not self.fcf_history or len(self.fcf_history) < 3:
            return 0.05  # Default 5%
        
        # Calculate median FCF (ignores outliers)
        sorted_fcf = sorted(self.fcf_history)
        median_fcf = sorted_fcf[len(sorted_fcf) // 2]
        current_fcf = self.fcf_history[-1]
        
        # Check if at peak
        if current_fcf > median_fcf * 1.5:
            return 0.03  # Conservative 3% (expect mean reversion)
        
        # Check if at trough
        if current_fcf < median_fcf * 0.7:
            return 0.05  # Moderate 5% rebound
        
        # Normal case: use full historical CAGR
        return self._calculate_cagr(self.fcf_history)
    
    def _calculate_fcf_growth_rate(self) -> float:
        """
        Calculate FCF growth rate based on company type.
        
        Dispatches to appropriate method based on growth_method parameter.
        Caps at 100% max (even hypergrowth companies can't sustain >100% for 5 years).
        """
        if not self.fcf_history or len(self.fcf_history) < 2:
            return 0.05  # Default 5%
        
        method = self.params['growth_method']
        
        # Calculate growth using appropriate method
        if method == 'weighted_recent':
            growth = self._weighted_recent_growth()
        elif method == 'normalized':
            growth = self._normalized_growth()
        elif method == 'conservative':
            growth = self._conservative_growth()
        else:  # 'historical_avg'
            growth = self._calculate_cagr(self.fcf_history)
        
        # Cap at 100% (no company can realistically grow >100% for 5 years)
        final_growth = min(growth, 1.00)
        
        # Floor at -10% (avoid extreme negative projections)
        final_growth = max(final_growth, -0.10)
        
        return final_growth
    
    # ========================================
    # WACC CALCULATION
    # ========================================
    
    def calculate_wacc(self) -> float:
        """
        Calculate WACC (Weighted Average Cost of Capital).
        
        Simplified: WACC = Risk-Free Rate + Beta × Equity Risk Premium
        Beta is sourced from Alpha Vantage company overview.
        
        Note: We don't add sector adjustments because Beta already captures
        company-specific risk relative to the market.
        """
        beta = self.overview.get('beta', 1.0)
        if not beta or beta <= 0:
            beta = 1.0  # Default to market beta
        
        wacc = RISK_FREE_RATE + (beta * EQUITY_RISK_PREMIUM)
        
        # Sanity check: WACC should be between 5% and 20%
        wacc = max(0.05, min(wacc, 0.20))
        
        return wacc
    
    # ========================================
    # FCF PROJECTION
    # ========================================
    
    def project_fcf(self) -> Tuple[List[float], float]:
        """
        Project Free Cash Flow for 5 years using company-type specific growth.
        
        Returns:
            Tuple of (fcf_projections, growth_rate_used)
        """
        # Get current FCF
        current_ocf = self._get_latest(self.cashflow, 'operating_cashflow')
        current_capex = abs(self._get_latest(self.cashflow, 'capital_expenditures') or 0)
        current_fcf = current_ocf - current_capex if current_ocf else None
        
        if not current_fcf or current_fcf <= 0:
            return [], 0.0
        
        # Calculate growth rate based on company type
        fcf_growth_rate = self._calculate_fcf_growth_rate()
        
        # Project FCF for 5 years
        projection_years = self.params['projection_years']
        projections = []
        fcf = current_fcf
        
        for year in range(1, projection_years + 1):
            fcf = fcf * (1 + fcf_growth_rate)
            projections.append(fcf)
        
        return projections, fcf_growth_rate
    
    # ========================================
    # TERMINAL VALUE & VALUATION
    # ========================================
    
    def calculate_terminal_value(self, final_fcf: float) -> float:
        """
        Calculate Terminal Value using Gordon Growth Model.
        
        TV = FCF_year6 / (WACC - g)
        where FCF_year6 = FCF_year5 × (1 + terminal_growth_rate)
        
        Uses company-type specific terminal growth rate.
        """
        wacc = self.calculate_wacc()
        terminal_growth = self.params['terminal_growth']
        
        if wacc <= terminal_growth:
            # Invalid: WACC must be > terminal growth
            # Adjust WACC up slightly
            wacc = terminal_growth + 0.02
        
        # Year 6 FCF for terminal value calculation
        fcf_year6 = final_fcf * (1 + terminal_growth)
        
        terminal_value = fcf_year6 / (wacc - terminal_growth)
        return terminal_value
    
    def calculate_enterprise_value(self, fcf_projections: List[float], terminal_value: float) -> float:
        """
        Calculate Enterprise Value by discounting all cash flows.
        
        EV = PV(FCF_1...5) + PV(Terminal Value)
        """
        wacc = self.calculate_wacc()
        
        # Discount projected FCFs
        pv_fcf = 0
        for year, fcf in enumerate(fcf_projections, start=1):
            pv_fcf += fcf / ((1 + wacc) ** year)
        
        # Discount terminal value (discounted from end of year 5)
        pv_terminal = terminal_value / ((1 + wacc) ** len(fcf_projections))
        
        enterprise_value = pv_fcf + pv_terminal
        return enterprise_value
    
    def calculate_equity_value(self, enterprise_value: float) -> float:
        """
        Calculate Equity Value from Enterprise Value.
        
        Equity Value = Enterprise Value + Cash - Debt
        """
        cash = self._get_latest(self.balance, 'cash') or 0
        long_term_debt = self._get_latest(self.balance, 'long_term_debt') or 0
        short_term_debt = self._get_latest(self.balance, 'short_term_debt') or 0
        total_debt = long_term_debt + short_term_debt
        
        equity_value = enterprise_value + cash - total_debt
        return equity_value
    
    def calculate_fair_value_per_share(self) -> Optional[float]:
        """
        Calculate fair value per share.
        
        Fair Value = Equity Value / Shares Outstanding
        """
        # Project FCF
        fcf_projections, _ = self.project_fcf()
        
        if not fcf_projections:
            return None
        
        # Calculate Terminal Value
        final_fcf = fcf_projections[-1]
        terminal_value = self.calculate_terminal_value(final_fcf)
        
        # Calculate Enterprise Value
        enterprise_value = self.calculate_enterprise_value(fcf_projections, terminal_value)
        
        # Calculate Equity Value
        equity_value = self.calculate_equity_value(enterprise_value)
        
        # Calculate per share
        shares_outstanding = self.overview.get('shares_outstanding')
        if not shares_outstanding or shares_outstanding <= 0:
            return None
        
        fair_value_per_share = equity_value / shares_outstanding
        return fair_value_per_share
    
    # ========================================
    # SUMMARY OUTPUT
    # ========================================
    
    def get_dcf_summary(self) -> Dict:
        """
        Get complete DCF analysis with all assumptions and results.
        
        This preserves all key assumptions and intermediate calculations
        for use in the final investment report.
        """
        # Calculate components
        wacc = self.calculate_wacc()
        fcf_projections, fcf_growth_rate = self.project_fcf()
        
        if not fcf_projections:
            return {
                'fair_value_per_share': None,
                'error': 'Insufficient data for DCF calculation'
            }
        
        final_fcf = fcf_projections[-1]
        terminal_value = self.calculate_terminal_value(final_fcf)
        enterprise_value = self.calculate_enterprise_value(fcf_projections, terminal_value)
        equity_value = self.calculate_equity_value(enterprise_value)
        shares_outstanding = self.overview.get('shares_outstanding', 0)
        fair_value = equity_value / shares_outstanding if shares_outstanding else None
        
        # Get current FCF
        current_ocf = self._get_latest(self.cashflow, 'operating_cashflow') or 0
        current_capex = abs(self._get_latest(self.cashflow, 'capital_expenditures') or 0)
        current_fcf = current_ocf - current_capex
        
        # Get cash and debt
        cash = self._get_latest(self.balance, 'cash') or 0
        debt = (self._get_latest(self.balance, 'long_term_debt') or 0) + \
               (self._get_latest(self.balance, 'short_term_debt') or 0)
        
        return {
            # === ASSUMPTIONS (for report) ===
            'assumptions': {
                'risk_free_rate': RISK_FREE_RATE,
                'equity_risk_premium': EQUITY_RISK_PREMIUM,
                'beta': self.overview.get('beta', 1.0),
                'wacc': wacc,
                'terminal_growth_rate': self.params['terminal_growth'],
                'projection_years': self.params['projection_years'],
                'fcf_cagr': fcf_growth_rate,
                'company_type': self.company_type,
                'growth_method': self.params['growth_method'],
            },
            
            # === CASH FLOWS ===
            'current_fcf': current_fcf,
            'fcf_projections': fcf_projections,
            
            # === VALUATION COMPONENTS ===
            'terminal_value': terminal_value,
            'pv_fcf': sum(fcf / ((1 + wacc) ** (i + 1)) for i, fcf in enumerate(fcf_projections)),
            'pv_terminal_value': terminal_value / ((1 + wacc) ** len(fcf_projections)),
            'enterprise_value': enterprise_value,
            
            # === ADJUSTMENTS ===
            'cash': cash,
            'debt': debt,
            'equity_value': equity_value,
            
            # === RESULT ===
            'shares_outstanding': shares_outstanding,
            'fair_value_per_share': fair_value,
        }