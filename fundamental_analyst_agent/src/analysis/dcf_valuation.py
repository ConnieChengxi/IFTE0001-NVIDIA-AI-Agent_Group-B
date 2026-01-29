from typing import Dict, List, Optional, Tuple
from config.settings import (
    RISK_FREE_RATE_FALLBACK,
    EQUITY_RISK_PREMIUM,
    TERMINAL_GROWTH_RATE,
    DCF_PROJECTION_YEARS
)
from src.data_collection.yahoo_finance_client import get_risk_free_rate


class DCFValuator:
    
    
    DCF_PARAMS_BY_TYPE = {
        'growth': {
            'model_type': '3-stage',
            'stage1_years': 5,
            'stage2_years': 5,
            'growth_method': 'weighted_recent',
            'recent_years_weight': 2,
            'max_stage1_growth': 0.65,
            'stage2_end_growth': 0.08,
        },
        'balanced': {
            'model_type': '2-stage',
            'stage1_years': 5,
            'stage2_years': 3,
            'growth_method': 'historical_avg',
            'recent_years_weight': 0,
            'max_stage1_growth': 0.20,
            'stage2_end_growth': 0.04,
        },
        'dividend': {
            'model_type': '1-stage',
            'stage1_years': 5,
            'stage2_years': 0,
            'growth_method': 'conservative',
            'recent_years_weight': 0,
            'max_stage1_growth': 0.10,
            'stage2_end_growth': None,
        },
        'cyclical': {
            'model_type': '1-stage',
            'stage1_years': 5,
            'stage2_years': 0,
            'growth_method': 'normalized',
            'recent_years_weight': 0,
            'max_stage1_growth': 0.15,
            'stage2_end_growth': None,
        }
    }
    
    def __init__(self, company_data: Dict, company_type: str = 'balanced', sector: str = None, cache_manager=None):
        self.overview = company_data.get('overview', {})
        self.income = company_data.get('income', [])
        self.balance = company_data.get('balance', [])
        self.cashflow = company_data.get('cashflow', [])
        
        self.company_type = company_type
        self.sector = sector
        
        self.params = self.DCF_PARAMS_BY_TYPE.get(company_type, self.DCF_PARAMS_BY_TYPE['balanced']).copy()
        
        self.params['terminal_growth'] = TERMINAL_GROWTH_RATE
        
        try:
            self.risk_free_rate = get_risk_free_rate(cache_manager)
        except Exception:
            self.risk_free_rate = RISK_FREE_RATE_FALLBACK
        
        self.fcf_history = self._calculate_fcf_history()
    
    
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
    
    def _calculate_fcf_history(self) -> List[float]:
        ocf_history = self._get_historical(self.cashflow, 'operating_cashflow', years=5)
        capex_history = self._get_historical(self.cashflow, 'capital_expenditures', years=5)
        
        if not ocf_history or not capex_history:
            return []
        
        fcf_history = []
        for i in range(min(len(ocf_history), len(capex_history))):
            ocf = ocf_history[i]
            capex = abs(capex_history[i]) if capex_history[i] else 0
            fcf = ocf - capex
            if fcf > 0:
                fcf_history.append(fcf)
        
        fcf_history.reverse()
        
        return fcf_history
    
    def _calculate_cagr(self, values: List[float]) -> float:
        if not values or len(values) < 2:
            return 0.10
        
        start_value = values[0]
        end_value = values[-1]
        years = len(values) - 1
        
        if start_value <= 0 or end_value <= 0:
            return 0.10
        
        cagr = (end_value / start_value) ** (1 / years) - 1
        
        return cagr
    
    
    def _weighted_recent_growth(self) -> float:
        if not self.fcf_history or len(self.fcf_history) < 3:
            return 0.10
        
        recent_weight = self.params['recent_years_weight']
        
        if len(self.fcf_history) >= recent_weight + 1:
            recent_fcf = self.fcf_history[-recent_weight:]
            recent_growth = self._calculate_cagr(recent_fcf)
        else:
            recent_growth = 0.10
        
        full_growth = self._calculate_cagr(self.fcf_history)
        
        weighted_growth = (recent_growth * 0.7) + (full_growth * 0.3)
        
        return weighted_growth
    
    def _conservative_growth(self) -> float:
        if not self.fcf_history or len(self.fcf_history) < 3:
            return 0.03
        
        growth_rates = []
        for i in range(len(self.fcf_history) - 2):
            period = self.fcf_history[i:i+3]
            growth = self._calculate_cagr(period)
            growth_rates.append(growth)
        
        if not growth_rates:
            return 0.03
        
        growth_rates.sort()
        index_25 = max(0, len(growth_rates) // 4)
        percentile_25 = growth_rates[index_25]
        
        return max(percentile_25, 0.02)
    
    def _normalized_growth(self) -> float:
        if not self.fcf_history or len(self.fcf_history) < 3:
            return 0.05
        
        sorted_fcf = sorted(self.fcf_history)
        median_fcf = sorted_fcf[len(sorted_fcf) // 2]
        current_fcf = self.fcf_history[-1]
        
        if current_fcf > median_fcf * 1.5:
            return 0.03
        
        if current_fcf < median_fcf * 0.7:
            return 0.05
        
        return self._calculate_cagr(self.fcf_history)
    
    def _calculate_stage1_growth_rate(self) -> float:
        if not self.fcf_history or len(self.fcf_history) < 2:
            return 0.05
        
        method = self.params['growth_method']
        
        if method == 'weighted_recent':
            growth = self._weighted_recent_growth()
        elif method == 'normalized':
            growth = self._normalized_growth()
        elif method == 'conservative':
            growth = self._conservative_growth()
        else:
            growth = self._calculate_cagr(self.fcf_history)
        
        max_growth = self.params.get('max_stage1_growth', 0.50)
        final_growth = min(growth, max_growth)
        
        final_growth = max(final_growth, -0.10)
        
        return final_growth
    
    
    def calculate_wacc(self) -> float:
        TAX_RATE = 0.25
        
        beta = self.overview.get('beta', 1.0)
        if not beta or beta <= 0:
            beta = 1.0
        
        cost_of_equity = self.risk_free_rate + (beta * EQUITY_RISK_PREMIUM)
        
        market_cap = self.overview.get('market_cap', 0) or 0
        long_term_debt = self._get_latest(self.balance, 'long_term_debt') or 0
        short_term_debt = self._get_latest(self.balance, 'short_term_debt') or 0
        total_debt = long_term_debt + short_term_debt
        
        interest_expense = abs(self._get_latest(self.income, 'interest_expense') or 0)
        if total_debt > 0 and interest_expense > 0:
            cost_of_debt = interest_expense / total_debt
            cost_of_debt = min(cost_of_debt, 0.15)
        else:
            cost_of_debt = self.risk_free_rate + 0.02
        
        total_value = market_cap + total_debt
        
        if total_value > 0:
            equity_weight = market_cap / total_value
            debt_weight = total_debt / total_value
        else:
            equity_weight = 1.0
            debt_weight = 0.0
        
        wacc = (equity_weight * cost_of_equity) + (debt_weight * cost_of_debt * (1 - TAX_RATE))
        
        wacc = max(0.05, min(wacc, 0.20))
        
        return wacc
    
    
    def _calculate_fade_schedule(self, start_growth: float, end_growth: float, years: int) -> List[float]:
        if years <= 0:
            return []
        
        fade_rates = []
        step = (start_growth - end_growth) / years
        
        for year in range(1, years + 1):
            rate = start_growth - (step * year)
            fade_rates.append(rate)
        
        return fade_rates
    
    def project_fcf_multistage(self) -> Dict:
        current_ocf = self._get_latest(self.cashflow, 'operating_cashflow')
        current_capex = abs(self._get_latest(self.cashflow, 'capital_expenditures') or 0)
        current_fcf = current_ocf - current_capex if current_ocf else None
        
        if not current_fcf or current_fcf <= 0:
            return {
                'stage1_projections': [],
                'stage2_projections': [],
                'all_projections': [],
                'stage1_growth': 0.0,
                'fade_schedule': [],
                'terminal_growth': self.params['terminal_growth'],
                'model_type': self.params['model_type'],
                'error': 'Negative or zero FCF'
            }
        
        model_type = self.params['model_type']
        stage1_years = self.params['stage1_years']
        stage2_years = self.params['stage2_years']
        terminal_growth = self.params['terminal_growth']
        
        stage1_growth = self._calculate_stage1_growth_rate()
        
        stage1_projections = []
        fcf = current_fcf
        
        for year in range(1, stage1_years + 1):
            fcf = fcf * (1 + stage1_growth)
            stage1_projections.append(fcf)
        
        stage2_projections = []
        fade_schedule = []
        
        if model_type in ['2-stage', '3-stage'] and stage2_years > 0:
            stage2_end_growth = self.params['stage2_end_growth']
            
            fade_schedule = self._calculate_fade_schedule(
                start_growth=stage1_growth,
                end_growth=stage2_end_growth,
                years=stage2_years
            )
            
            fcf = stage1_projections[-1]
            
            for fade_rate in fade_schedule:
                fcf = fcf * (1 + fade_rate)
                stage2_projections.append(fcf)
        
        all_projections = stage1_projections + stage2_projections
        
        return {
            'stage1_projections': stage1_projections,
            'stage2_projections': stage2_projections,
            'all_projections': all_projections,
            'stage1_growth': stage1_growth,
            'fade_schedule': fade_schedule,
            'terminal_growth': terminal_growth,
            'model_type': model_type,
            'current_fcf': current_fcf,
        }
    
    
    def calculate_terminal_value(self, final_fcf: float) -> float:
        wacc = self.calculate_wacc()
        terminal_growth = self.params['terminal_growth']
        
        if wacc <= terminal_growth:
            wacc = terminal_growth + 0.02
        
        fcf_next = final_fcf * (1 + terminal_growth)
        
        terminal_value = fcf_next / (wacc - terminal_growth)
        return terminal_value
    
    def calculate_enterprise_value_multistage(self, projections: Dict) -> Dict:
        wacc = self.calculate_wacc()
        all_projections = projections['all_projections']
        stage1_projections = projections['stage1_projections']
        stage2_projections = projections['stage2_projections']
        
        if not all_projections:
            return {
                'pv_stage1': 0,
                'pv_stage2': 0,
                'pv_terminal': 0,
                'enterprise_value': 0,
            }
        
        pv_stage1 = 0
        for year, fcf in enumerate(stage1_projections, start=1):
            pv_stage1 += fcf / ((1 + wacc) ** year)
        
        pv_stage2 = 0
        stage1_years = len(stage1_projections)
        for i, fcf in enumerate(stage2_projections):
            year = stage1_years + i + 1
            pv_stage2 += fcf / ((1 + wacc) ** year)
        
        final_fcf = all_projections[-1]
        terminal_value = self.calculate_terminal_value(final_fcf)
        total_years = len(all_projections)
        pv_terminal = terminal_value / ((1 + wacc) ** total_years)
        
        enterprise_value = pv_stage1 + pv_stage2 + pv_terminal
        
        return {
            'pv_stage1': pv_stage1,
            'pv_stage2': pv_stage2,
            'terminal_value': terminal_value,
            'pv_terminal': pv_terminal,
            'enterprise_value': enterprise_value,
        }
    
    def calculate_equity_value(self, enterprise_value: float) -> float:
        cash = self._get_latest(self.balance, 'cash') or 0
        long_term_debt = self._get_latest(self.balance, 'long_term_debt') or 0
        short_term_debt = self._get_latest(self.balance, 'short_term_debt') or 0
        total_debt = long_term_debt + short_term_debt
        
        equity_value = enterprise_value + cash - total_debt
        return equity_value
    
    def calculate_fair_value_per_share(self) -> Optional[float]:
        projections = self.project_fcf_multistage()
        
        if not projections['all_projections']:
            return None
        
        ev_components = self.calculate_enterprise_value_multistage(projections)
        enterprise_value = ev_components['enterprise_value']
        
        equity_value = self.calculate_equity_value(enterprise_value)
        
        shares_outstanding = self.overview.get('shares_outstanding')
        if not shares_outstanding or shares_outstanding <= 0:
            return None
        
        fair_value_per_share = equity_value / shares_outstanding
        return fair_value_per_share
    
    
    def project_fcf(self) -> Tuple[List[float], float]:
        projections = self.project_fcf_multistage()
        return projections['all_projections'], projections['stage1_growth']
    
    
    def get_dcf_summary(self) -> Dict:
        wacc = self.calculate_wacc()
        
        projections = self.project_fcf_multistage()
        
        if not projections['all_projections']:
            return {
                'fair_value_per_share': None,
                'error': projections.get('error', 'Insufficient data for DCF calculation')
            }
        
        ev_components = self.calculate_enterprise_value_multistage(projections)
        enterprise_value = ev_components['enterprise_value']
        equity_value = self.calculate_equity_value(enterprise_value)
        
        shares_outstanding = self.overview.get('shares_outstanding', 0)
        fair_value = equity_value / shares_outstanding if shares_outstanding else None
        
        cash = self._get_latest(self.balance, 'cash') or 0
        debt = (self._get_latest(self.balance, 'long_term_debt') or 0) + \
               (self._get_latest(self.balance, 'short_term_debt') or 0)
        
        return {
            'model_type': projections['model_type'],
            
            'assumptions': {
                'risk_free_rate': self.risk_free_rate,
                'equity_risk_premium': EQUITY_RISK_PREMIUM,
                'beta': self.overview.get('beta', 1.0),
                'wacc': wacc,
                'company_type': self.company_type,
                'growth_method': self.params['growth_method'],
                
                'stage1_years': self.params['stage1_years'],
                'stage1_growth': projections['stage1_growth'],
                
                'stage2_years': self.params['stage2_years'],
                'stage2_end_growth': self.params.get('stage2_end_growth'),
                'fade_schedule': projections['fade_schedule'],
                
                'terminal_growth_rate': projections['terminal_growth'],
                'total_projection_years': len(projections['all_projections']),
            },
            
            'current_fcf': projections['current_fcf'],
            'stage1_projections': projections['stage1_projections'],
            'stage2_projections': projections['stage2_projections'],
            'fcf_projections': projections['all_projections'],
            
            'pv_stage1': ev_components['pv_stage1'],
            'pv_stage2': ev_components['pv_stage2'],
            'pv_fcf': ev_components['pv_stage1'] + ev_components['pv_stage2'],
            'terminal_value': ev_components['terminal_value'],
            'pv_terminal_value': ev_components['pv_terminal'],
            'enterprise_value': enterprise_value,
            
            'cash': cash,
            'debt': debt,
            'equity_value': equity_value,
            
            'shares_outstanding': shares_outstanding,
            'fair_value_per_share': fair_value,
        }
    
    
    SCENARIO_PARAMS = {
        'bear': {
            'growth_multiplier': 0.75,
            'wacc_adjustment': 0.01,
            'description': 'Pessimistic case: slower growth, higher risk'
        },
        'base': {
            'growth_multiplier': 1.00,
            'wacc_adjustment': 0.00,
            'description': 'Base case: current trends continue'
        },
        'bull': {
            'growth_multiplier': 1.25,
            'wacc_adjustment': -0.01,
            'description': 'Optimistic case: exceeds expectations'
        }
    }
    
    def calculate_scenario_fair_value(self, scenario: str) -> Optional[float]:
        if scenario not in self.SCENARIO_PARAMS:
            return None
        
        params = self.SCENARIO_PARAMS[scenario]
        
        base_growth = self._calculate_stage1_growth_rate()
        base_wacc = self.calculate_wacc()
        
        scenario_growth = base_growth * params['growth_multiplier']
        scenario_wacc = base_wacc + params['wacc_adjustment']
        
        max_growth = self.params.get('max_stage1_growth', 0.70)
        scenario_growth = min(scenario_growth, max_growth)
        
        scenario_wacc = max(scenario_wacc, 0.05)
        
        current_ocf = self._get_latest(self.cashflow, 'operating_cashflow')
        current_capex = abs(self._get_latest(self.cashflow, 'capital_expenditures') or 0)
        current_fcf = current_ocf - current_capex if current_ocf else None
        
        if not current_fcf or current_fcf <= 0:
            return None
        
        stage1_years = self.params['stage1_years']
        stage1_projections = []
        fcf = current_fcf
        
        for year in range(1, stage1_years + 1):
            fcf = fcf * (1 + scenario_growth)
            stage1_projections.append(fcf)
        
        stage2_years = self.params['stage2_years']
        stage2_projections = []
        
        if stage2_years > 0:
            stage2_end_growth = self.params.get('stage2_end_growth', 0.08)
            fade_schedule = self._calculate_fade_schedule(
                start_growth=scenario_growth,
                end_growth=stage2_end_growth,
                years=stage2_years
            )
            
            fcf = stage1_projections[-1]
            for fade_rate in fade_schedule:
                fcf = fcf * (1 + fade_rate)
                stage2_projections.append(fcf)
        
        all_projections = stage1_projections + stage2_projections
        
        if not all_projections:
            return None
        
        pv_fcf = 0
        for i, proj_fcf in enumerate(all_projections):
            year = i + 1
            pv_fcf += proj_fcf / ((1 + scenario_wacc) ** year)
        
        final_fcf = all_projections[-1]
        terminal_growth = self.params['terminal_growth']
        
        if scenario_wacc <= terminal_growth:
            scenario_wacc = terminal_growth + 0.02
        
        fcf_next = final_fcf * (1 + terminal_growth)
        terminal_value = fcf_next / (scenario_wacc - terminal_growth)
        
        total_years = len(all_projections)
        pv_terminal = terminal_value / ((1 + scenario_wacc) ** total_years)
        
        enterprise_value = pv_fcf + pv_terminal
        
        cash = self._get_latest(self.balance, 'cash') or 0
        long_term_debt = self._get_latest(self.balance, 'long_term_debt') or 0
        short_term_debt = self._get_latest(self.balance, 'short_term_debt') or 0
        total_debt = long_term_debt + short_term_debt
        
        equity_value = enterprise_value + cash - total_debt
        
        shares_outstanding = self.overview.get('shares_outstanding')
        if not shares_outstanding or shares_outstanding <= 0:
            return None
        
        fair_value = equity_value / shares_outstanding
        
        return fair_value
    
    def get_scenario_analysis(self) -> Dict:
        base_growth = self._calculate_stage1_growth_rate()
        base_wacc = self.calculate_wacc()
        current_price = self.overview.get('price', 0) or 0
        
        scenarios = {}
        
        for scenario_name in ['bear', 'base', 'bull']:
            params = self.SCENARIO_PARAMS[scenario_name]
            
            adj_growth = base_growth * params['growth_multiplier']
            adj_wacc = base_wacc + params['wacc_adjustment']
            
            max_growth = self.params.get('max_stage1_growth', 0.70)
            adj_growth = min(adj_growth, max_growth)
            adj_wacc = max(adj_wacc, 0.05)
            
            fair_value = self.calculate_scenario_fair_value(scenario_name)
            
            if fair_value and current_price and current_price > 0:
                upside = (fair_value - current_price) / current_price
            else:
                upside = None
            
            scenarios[scenario_name] = {
                'fair_value': fair_value,
                'growth_rate': adj_growth,
                'wacc': adj_wacc,
                'upside': upside,
                'description': params['description'],
                'growth_multiplier': params['growth_multiplier'],
                'wacc_adjustment': params['wacc_adjustment'],
            }
        
        return {
            'scenarios': scenarios,
            'base_growth': base_growth,
            'base_wacc': base_wacc,
            'current_price': current_price,
            'terminal_growth': self.params['terminal_growth'],
        }
