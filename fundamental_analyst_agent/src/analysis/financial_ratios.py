"""
Financial Ratios Calculator
"""

from typing import Dict, List, Optional
from config.settings import (
    PROFITABILITY_BENCHMARKS,
    LEVERAGE_BENCHMARKS,
    LIQUIDITY_BENCHMARKS,
    GROWTH_BENCHMARKS,
    EFFICIENCY_BENCHMARKS
)


class FinancialRatiosCalculator:
    
    def __init__(self, company_data: Dict):
        self.overview = company_data.get('overview', {})
        self.income = company_data.get('income', [])
        self.balance = company_data.get('balance', [])
        self.cashflow = company_data.get('cashflow', [])
    
    def _to_float(self, value) -> Optional[float]:
        """Safely convert value to float."""
        if value is None or value == 'None':
            return None
        try:
            return float(value)
        except (ValueError, TypeError):
            return None
    
    def _safe_divide(self, numerator: Optional[float], denominator: Optional[float]) -> Optional[float]:
        if numerator is None or denominator is None:
            return None
        if denominator == 0:
            return None
        return numerator / denominator
    
    def _get_latest(self, data_list: List[Dict], field: str) -> Optional[float]:
        if not data_list:
            return None
        value = data_list[0].get(field)
        return self._to_float(value)
    
    def _get_historical(self, data_list: List[Dict], field: str, years: int = 5) -> List[float]:
        values = []
        for i in range(min(years, len(data_list))):
            value = self._to_float(data_list[i].get(field))
            if value is not None:
                values.append(value)
        return values
    
    def _calculate_growth_rate(self, current: float, previous: float) -> Optional[float]:
        if not previous or previous == 0:
            return None
        return (current - previous) / previous
    
    def calculate_gross_margin(self) -> Optional[float]:
        revenue = self._get_latest(self.income, 'revenue')
        cogs = self._get_latest(self.income, 'cost_of_revenue')
        if revenue and cogs:
            return (revenue - cogs) / revenue
        return None
    
    def calculate_operating_margin(self) -> Optional[float]:
        operating_income = self._get_latest(self.income, 'operating_income')
        revenue = self._get_latest(self.income, 'revenue')
        return self._safe_divide(operating_income, revenue)
    
    def calculate_net_margin(self) -> Optional[float]:
        net_income = self._get_latest(self.income, 'net_income')
        revenue = self._get_latest(self.income, 'revenue')
        return self._safe_divide(net_income, revenue)
    
    def calculate_roe(self) -> Optional[float]:
        net_income = self._get_latest(self.income, 'net_income')
        equity = self._get_latest(self.balance, 'total_shareholder_equity')
        return self._safe_divide(net_income, equity)
    
    def calculate_roa(self) -> Optional[float]:
        net_income = self._get_latest(self.income, 'net_income')
        assets = self._get_latest(self.balance, 'total_assets')
        return self._safe_divide(net_income, assets)
    
    def calculate_roic(self) -> Optional[float]:
        """
        Calculate Return on Invested Capital.
        
        ROIC = NOPAT / Invested Capital
        
        Where:
        - NOPAT = Operating Income × (1 - Tax Rate)
        - Invested Capital = Total Equity + Total Debt - Cash
          (Alternative: NWC + PPE + Goodwill + Intangibles)
        """
        operating_income = self._get_latest(self.income, 'operating_income')
        net_income = self._get_latest(self.income, 'net_income')
        tax_expense = self._get_latest(self.income, 'income_tax_expense')
        
        if not operating_income:
            return None
        
        # Calculate tax rate
        if net_income and tax_expense and (net_income + tax_expense) != 0:
            tax_rate = tax_expense / (net_income + tax_expense)
            # Sanity check: tax rate should be between 0 and 50%
            tax_rate = max(0, min(tax_rate, 0.50))
        else:
            tax_rate = 0.21  # Default US corporate tax rate
        
        nopat = operating_income * (1 - tax_rate)
        
        # Method 1: Equity + Debt - Cash
        total_equity = self._get_latest(self.balance, 'total_shareholder_equity') or 0
        long_term_debt = self._get_latest(self.balance, 'long_term_debt') or 0
        short_term_debt = self._get_latest(self.balance, 'short_term_debt') or 0
        total_debt = long_term_debt + short_term_debt
        cash = self._get_latest(self.balance, 'cash') or 0
        
        invested_capital_method1 = total_equity + total_debt - cash
        
        # Method 2: NWC + Fixed Assets
        current_assets = self._get_latest(self.balance, 'current_assets') or 0
        current_liabilities = self._get_latest(self.balance, 'current_liabilities') or 0
        nwc = current_assets - current_liabilities
        
        ppe = self._get_latest(self.balance, 'ppe') or 0
        goodwill = self._get_latest(self.balance, 'goodwill') or 0
        intangibles = self._get_latest(self.balance, 'intangible_assets') or 0
        
        invested_capital_method2 = nwc + ppe + goodwill + intangibles
        
        # Use Method 1 if valid, otherwise Method 2
        if invested_capital_method1 > 0:
            invested_capital = invested_capital_method1
        elif invested_capital_method2 > 0:
            invested_capital = invested_capital_method2
        else:
            # Fallback: use total assets - current liabilities
            total_assets = self._get_latest(self.balance, 'total_assets') or 0
            invested_capital = total_assets - current_liabilities
        
        if invested_capital <= 0:
            return None
        
        return self._safe_divide(nopat, invested_capital)
    
    def calculate_debt_to_equity(self) -> Optional[float]:
        long_term_debt = self._get_latest(self.balance, 'long_term_debt') or 0
        short_term_debt = self._get_latest(self.balance, 'short_term_debt') or 0
        total_debt = long_term_debt + short_term_debt
        equity = self._get_latest(self.balance, 'total_shareholder_equity')
        return self._safe_divide(total_debt, equity)
    
    def calculate_debt_to_assets(self) -> Optional[float]:
        long_term_debt = self._get_latest(self.balance, 'long_term_debt') or 0
        short_term_debt = self._get_latest(self.balance, 'short_term_debt') or 0
        total_debt = long_term_debt + short_term_debt
        assets = self._get_latest(self.balance, 'total_assets')
        return self._safe_divide(total_debt, assets)
    
    def calculate_interest_coverage(self) -> Optional[float]:
        ebit = self._get_latest(self.income, 'operating_income')
        interest_expense = self._get_latest(self.income, 'interest_expense')
        return self._safe_divide(ebit, interest_expense)
    
    def calculate_current_ratio(self) -> Optional[float]:
        current_assets = self._get_latest(self.balance, 'current_assets')
        current_liabilities = self._get_latest(self.balance, 'current_liabilities')
        return self._safe_divide(current_assets, current_liabilities)
    
    def calculate_quick_ratio(self) -> Optional[float]:
        current_assets = self._get_latest(self.balance, 'current_assets')
        inventory = self._get_latest(self.balance, 'inventory') or 0
        current_liabilities = self._get_latest(self.balance, 'current_liabilities')
        if current_assets and current_liabilities:
            return (current_assets - inventory) / current_liabilities
        return None
    
    def calculate_revenue_growth(self) -> Optional[float]:
        revenues = self._get_historical(self.income, 'revenue', years=2)
        if len(revenues) >= 2:
            return self._calculate_growth_rate(revenues[0], revenues[1])
        return None
    
    def calculate_earnings_growth(self) -> Optional[float]:
        earnings = self._get_historical(self.income, 'net_income', years=2)
        if len(earnings) >= 2:
            return self._calculate_growth_rate(earnings[0], earnings[1])
        return None
    
    def calculate_free_cash_flow(self) -> Optional[float]:
        ocf = self._get_latest(self.cashflow, 'operating_cashflow')
        capex = self._get_latest(self.cashflow, 'capital_expenditures') or 0
        if ocf:
            return ocf - abs(capex)
        return None
    
    def calculate_asset_turnover(self) -> Optional[float]:
        revenue = self._get_latest(self.income, 'revenue')
        assets = self._get_latest(self.balance, 'total_assets')
        return self._safe_divide(revenue, assets)
    
    def calculate_all_ratios(self) -> Dict:
        return {
            'gross_margin': self.calculate_gross_margin(),
            'operating_margin': self.calculate_operating_margin(),
            'net_margin': self.calculate_net_margin(),
            'roe': self.calculate_roe(),
            'roa': self.calculate_roa(),
            'roic': self.calculate_roic(),
            'debt_to_equity': self.calculate_debt_to_equity(),
            'debt_to_assets': self.calculate_debt_to_assets(),
            'interest_coverage': self.calculate_interest_coverage(),
            'current_ratio': self.calculate_current_ratio(),
            'quick_ratio': self.calculate_quick_ratio(),
            'revenue_growth': self.calculate_revenue_growth(),
            'earnings_growth': self.calculate_earnings_growth(),
            'free_cash_flow': self.calculate_free_cash_flow(),
            'asset_turnover': self.calculate_asset_turnover(),
        }
    
    def rate_ratio(self, ratio_name: str, ratio_value: Optional[float]) -> str:
        if ratio_value is None:
            return "N/A"
        
        if ratio_name in PROFITABILITY_BENCHMARKS:
            benchmarks = PROFITABILITY_BENCHMARKS[ratio_name]
            if ratio_value >= benchmarks['excellent']:
                return "Excellent"
            elif ratio_value >= benchmarks['good']:
                return "Good"
            elif ratio_value >= benchmarks['average']:
                return "Average"
            else:
                return "Poor"
        
        elif ratio_name in LEVERAGE_BENCHMARKS:
            benchmarks = LEVERAGE_BENCHMARKS[ratio_name]
            if ratio_name == 'interest_coverage':
                if ratio_value >= benchmarks['excellent']:
                    return "Excellent"
                elif ratio_value >= benchmarks['good']:
                    return "Good"
                elif ratio_value >= benchmarks['average']:
                    return "Average"
                else:
                    return "Poor"
            else:
                if ratio_value <= benchmarks['excellent']:
                    return "Excellent"
                elif ratio_value <= benchmarks['good']:
                    return "Good"
                elif ratio_value <= benchmarks['average']:
                    return "Average"
                else:
                    return "Poor"
        
        elif ratio_name in LIQUIDITY_BENCHMARKS:
            benchmarks = LIQUIDITY_BENCHMARKS[ratio_name]
            if ratio_value >= benchmarks['excellent']:
                return "Excellent"
            elif ratio_value >= benchmarks['good']:
                return "Good"
            elif ratio_value >= benchmarks['average']:
                return "Average"
            else:
                return "Poor"
        
        elif ratio_name in GROWTH_BENCHMARKS:
            benchmarks = GROWTH_BENCHMARKS[ratio_name]
            if ratio_value >= benchmarks['exceptional']:
                return "Exceptional"
            elif ratio_value >= benchmarks['high']:
                return "High"
            elif ratio_value >= benchmarks['moderate']:
                return "Moderate"
            elif ratio_value >= benchmarks['low']:
                return "Low"
            else:
                return "Negative"
        
        elif ratio_name in EFFICIENCY_BENCHMARKS:
            benchmarks = EFFICIENCY_BENCHMARKS[ratio_name]
            if ratio_value >= benchmarks['excellent']:
                return "Excellent"
            elif ratio_value >= benchmarks['good']:
                return "Good"
            elif ratio_value >= benchmarks['average']:
                return "Average"
            else:
                return "Poor"
        
        return "N/A"