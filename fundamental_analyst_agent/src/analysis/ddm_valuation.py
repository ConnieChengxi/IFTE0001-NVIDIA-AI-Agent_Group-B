from typing import Dict, List, Optional
from config.settings import (
    RISK_FREE_RATE_FALLBACK,
    EQUITY_RISK_PREMIUM,
    MIN_DIVIDEND_YIELD,
    MIN_DIVIDEND_HISTORY
)
from src.data_collection.yahoo_finance_client import get_risk_free_rate

class DDMValuator:
    
    def __init__(self, company_data: Dict, cache_manager=None):
        self.overview = company_data.get('overview', {})
        self.income = company_data.get('income', [])
        self.balance = company_data.get('balance', [])
        self.cashflow = company_data.get('cashflow', [])
        
        try:
            self.risk_free_rate = get_risk_free_rate(cache_manager)
        except Exception:
            self.risk_free_rate = RISK_FREE_RATE_FALLBACK
    
    def _get_latest(self, data_list: List[Dict], field: str) -> Optional[float]:
        if not data_list:
            return None
        return data_list[0].get(field)
    
    def _get_historical(self, data_list: List[Dict], field: str, years: int = 5) -> List[float]:
        values = []
        for i in range(min(years, len(data_list))):
            value = data_list[i].get(field)
            if value is not None:
                values.append(value)
        return values
    
    def is_ddm_applicable(self) -> tuple[bool, str]:
        dividend_yield = self.overview.get('dividend_yield', 0)
        
        if not dividend_yield or dividend_yield < MIN_DIVIDEND_YIELD:
            return False, f"Dividend yield ({dividend_yield:.2%}) < {MIN_DIVIDEND_YIELD:.0%} minimum"
        
        dividend_history = self._get_historical(self.cashflow, 'dividends_paid', years=MIN_DIVIDEND_HISTORY)
        
        if len(dividend_history) < MIN_DIVIDEND_HISTORY:
            return False, f"Insufficient dividend history ({len(dividend_history)} years < {MIN_DIVIDEND_HISTORY} required)"
        
        if not all(div and abs(div) > 0 for div in dividend_history):
            return False, "Inconsistent dividend payments"
        
        return True, "DDM applicable"
    
    def calculate_dividend_growth_rate(self) -> Optional[float]:
        dividend_history = self._get_historical(self.cashflow, 'dividends_paid', years=5)
        
        if len(dividend_history) < 2:
            return None
        
        dividends = [abs(d) for d in dividend_history if d]
        
        if len(dividends) < 2:
            return None
        
        dividend_oldest = dividends[-1]
        dividend_latest = dividends[0]
        years = len(dividends) - 1
        
        if dividend_oldest <= 0:
            return None
        
        cagr = (dividend_latest / dividend_oldest) ** (1 / years) - 1
        
        cagr = max(-0.10, min(cagr, 0.20))
        
        return cagr
    
    def calculate_current_dividend_per_share(self) -> Optional[float]:
        dividends_paid = abs(self._get_latest(self.cashflow, 'dividends_paid') or 0)
        shares_outstanding = self.overview.get('shares_outstanding')
        
        if not shares_outstanding or shares_outstanding <= 0:
            return None
        
        dps = dividends_paid / shares_outstanding
        
        return dps
    
    def calculate_required_return(self) -> float:
        beta = self.overview.get('beta', 1.0)
        if not beta or beta <= 0:
            beta = 1.0
        
        required_return = self.risk_free_rate + (beta * EQUITY_RISK_PREMIUM)
        
        return required_return
    
    def calculate_fair_value_gordon(self) -> Optional[float]:
        is_applicable, reason = self.is_ddm_applicable()
        
        if not is_applicable:
            return None
        
        d0 = self.calculate_current_dividend_per_share()
        
        if not d0 or d0 <= 0:
            return None
        
        g = self.calculate_dividend_growth_rate()
        
        if g is None:
            return None
        
        r = self.calculate_required_return()
        
        if r <= g:
            g = r - 0.02
        
        d1 = d0 * (1 + g)
        
        fair_value = d1 / (r - g)
        
        return fair_value
    
    def get_ddm_summary(self) -> Dict:
        is_applicable, applicability_reason = self.is_ddm_applicable()
        
        if not is_applicable:
            return {
                'fair_value_per_share': None,
                'applicable': False,
                'reason': applicability_reason,
            }
        
        current_dps = self.calculate_current_dividend_per_share()
        dividend_growth = self.calculate_dividend_growth_rate()
        required_return = self.calculate_required_return()
        fair_value = self.calculate_fair_value_gordon()
        
        dividend_history = self._get_historical(self.cashflow, 'dividends_paid', years=5)
        dividend_history = [abs(d) for d in dividend_history if d]
        
        return {
            'applicable': True,
            'reason': applicability_reason,
            'assumptions': {
                'risk_free_rate': self.risk_free_rate,
                'equity_risk_premium': EQUITY_RISK_PREMIUM,
                'beta': self.overview.get('beta', 1.0),
                'required_return': required_return,
                'dividend_growth_rate': dividend_growth,
                'model': 'Gordon Growth Model',
            },
            'current_dividend_per_share': current_dps,
            'dividend_yield': self.overview.get('dividend_yield', 0),
            'dividend_history': dividend_history,
            'dividend_history_years': len(dividend_history),
            'fair_value_per_share': fair_value,
        }
    
    SCENARIO_PARAMS = {
        'bear': {
            'growth_multiplier': 0.75,
            'required_return_adj': 0.01,
        },
        'base': {
            'growth_multiplier': 1.00,
            'required_return_adj': 0.00,
        },
        'bull': {
            'growth_multiplier': 1.25,
            'required_return_adj': -0.01,
        }
    }
    
    def calculate_scenario_fair_value(self, scenario: str) -> Optional[float]:
        if scenario not in self.SCENARIO_PARAMS:
            return None
        
        is_applicable, _ = self.is_ddm_applicable()
        if not is_applicable:
            return None
        
        params = self.SCENARIO_PARAMS[scenario]
        
        d0 = self.calculate_current_dividend_per_share()
        if not d0 or d0 <= 0:
            return None
        
        base_growth = self.calculate_dividend_growth_rate()
        if base_growth is None:
            return None
        
        base_required_return = self.calculate_required_return()
        
        scenario_growth = base_growth * params['growth_multiplier']
        scenario_required_return = base_required_return + params['required_return_adj']
        
        scenario_growth = max(-0.05, min(scenario_growth, 0.15))
        
        scenario_required_return = max(0.05, scenario_required_return)
        
        if scenario_required_return <= scenario_growth:
            scenario_growth = scenario_required_return - 0.02
        
        d1 = d0 * (1 + scenario_growth)
        
        fair_value = d1 / (scenario_required_return - scenario_growth)
        
        return fair_value
    
    def get_scenario_analysis(self) -> Dict:
        is_applicable, reason = self.is_ddm_applicable()
        
        if not is_applicable:
            return {
                'applicable': False,
                'reason': reason,
                'scenarios': {
                    'bear': {'fair_value': None},
                    'base': {'fair_value': None},
                    'bull': {'fair_value': None},
                }
            }
        
        base_growth = self.calculate_dividend_growth_rate()
        base_required_return = self.calculate_required_return()
        
        scenarios = {}
        
        for scenario_name in ['bear', 'base', 'bull']:
            params = self.SCENARIO_PARAMS[scenario_name]
            
            adj_growth = base_growth * params['growth_multiplier'] if base_growth else None
            adj_required_return = base_required_return + params['required_return_adj']
            
            if adj_growth is not None:
                adj_growth = max(-0.05, min(adj_growth, 0.15))
            adj_required_return = max(0.05, adj_required_return)
            
            fair_value = self.calculate_scenario_fair_value(scenario_name)
            
            scenarios[scenario_name] = {
                'fair_value': fair_value,
                'dividend_growth': adj_growth,
                'required_return': adj_required_return,
            }
        
        return {
            'applicable': True,
            'scenarios': scenarios,
            'base_growth': base_growth,
            'base_required_return': base_required_return,
        }
