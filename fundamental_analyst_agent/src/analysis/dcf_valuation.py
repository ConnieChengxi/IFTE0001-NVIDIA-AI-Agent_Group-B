"""
DCF Valuation Model - Multi-Stage Version
Discounted Cash Flow valuation with company-type specific assumptions.

Enhanced with 3-stage DCF for growth companies:
- Stage 1: High growth phase (years 1-5)
- Stage 2: Transition/fade phase (years 6-10)
- Stage 3: Terminal value at GDP growth rate

This approach addresses the expert feedback that applying terminal growth
immediately after 5 years is unrealistic for high-growth companies.
"""

from typing import Dict, List, Optional, Tuple
from config.settings import (
    RISK_FREE_RATE_FALLBACK,
    EQUITY_RISK_PREMIUM,
    TERMINAL_GROWTH_RATE,
    DCF_PROJECTION_YEARS
)
from src.data_collection.yahoo_finance_client import get_risk_free_rate


class DCFValuator:
    """
    Multi-stage DCF valuation model with company-type specific growth assumptions.
    
    Supports 4 company types with different stage structures:
    - Growth: 3-stage model (high growth → fade → terminal)
    - Balanced: 2-stage model (moderate growth → fade → terminal)
    - Dividend: 1-stage model (stable growth → terminal) - no fade needed
    - Cyclical: 1-stage model (normalized growth → terminal) - no fade needed
    """
    
    
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
        """
        Initialize DCF valuator.
        
        Args:
            company_data: Dict with keys: overview, income, balance, cashflow
            company_type: 'growth', 'balanced', 'dividend', or 'cyclical'
            sector: Company sector (for future sector-specific adjustments)
            cache_manager: Optional cache manager for fetching risk-free rate
        """
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
            if fcf > 0:
                fcf_history.append(fcf)
        
        fcf_history.reverse()
        
        return fcf_history
    
    def _calculate_cagr(self, values: List[float]) -> float:
        """
        Calculate Compound Annual Growth Rate.
        
        CAGR = (End Value / Start Value)^(1/years) - 1
        """
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
        """
        Weight recent years more heavily (for growth companies).
        
        Used for companies experiencing acceleration (e.g., NVDA AI boom).
        Formula: 70% recent growth + 30% historical growth
        """
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
        """
        Conservative growth using 25th percentile (for dividend companies).
        """
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
        """
        Normalized growth for cyclical companies.
        Use median FCF to avoid peak/trough distortions.
        """
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
        """
        Calculate FCF growth rate for Stage 1 based on company type.
        
        Applies company-type specific caps to ensure realistic projections:
        - Growth: max 50%
        - Balanced: max 20%
        - Dividend: max 10%
        - Cyclical: max 15%
        """
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
        """
        Calculate WACC (Weighted Average Cost of Capital).
        
        Simplified: WACC = Risk-Free Rate + Beta × Equity Risk Premium
        
        Risk-free rate is fetched dynamically from 10-Year Treasury yield.
        """
        beta = self.overview.get('beta', 1.0)
        if not beta or beta <= 0:
            beta = 1.0
        
        wacc = self.risk_free_rate + (beta * EQUITY_RISK_PREMIUM)
        
        wacc = max(0.05, min(wacc, 0.20))
        
        return wacc
    
    
    def _calculate_fade_schedule(self, start_growth: float, end_growth: float, years: int) -> List[float]:
        """
        Calculate linear fade schedule from start_growth to end_growth over N years.
        
        Example:
            start_growth = 0.30 (30%)
            end_growth = 0.08 (8%)
            years = 5
            Returns: [0.256, 0.212, 0.168, 0.124, 0.08]
        """
        if years <= 0:
            return []
        
        fade_rates = []
        step = (start_growth - end_growth) / years
        
        for year in range(1, years + 1):
            rate = start_growth - (step * year)
            fade_rates.append(rate)
        
        return fade_rates
    
    def project_fcf_multistage(self) -> Dict:
        """
        Project Free Cash Flow using multi-stage model.
        
        Returns:
            Dict containing:
            - stage1_projections: List of FCF for stage 1
            - stage2_projections: List of FCF for stage 2 (fade period)
            - all_projections: Combined list of all projected FCFs
            - stage1_growth: Growth rate used in stage 1
            - fade_schedule: List of declining growth rates in stage 2
            - terminal_growth: Final perpetual growth rate
            - model_type: '1-stage', '2-stage', or '3-stage'
        """
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
        """
        Calculate Terminal Value using Gordon Growth Model.
        
        TV = FCF_next / (WACC - g)
        where FCF_next = Final FCF × (1 + terminal_growth_rate)
        """
        wacc = self.calculate_wacc()
        terminal_growth = self.params['terminal_growth']
        
        if wacc <= terminal_growth:
            wacc = terminal_growth + 0.02
        
        fcf_next = final_fcf * (1 + terminal_growth)
        
        terminal_value = fcf_next / (wacc - terminal_growth)
        return terminal_value
    
    def calculate_enterprise_value_multistage(self, projections: Dict) -> Dict:
        """
        Calculate Enterprise Value using multi-stage projections.
        
        EV = PV(Stage 1 FCFs) + PV(Stage 2 FCFs) + PV(Terminal Value)
        """
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
        Calculate fair value per share using multi-stage DCF.
        """
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
        """
        Legacy method for backward compatibility.
        Returns all projections and stage 1 growth rate.
        """
        projections = self.project_fcf_multistage()
        return projections['all_projections'], projections['stage1_growth']
    
    
    def get_dcf_summary(self) -> Dict:
        """
        Get complete DCF analysis with all assumptions and results.
        
        Enhanced to include multi-stage model details.
        """
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
        """
        Calculate fair value for a specific scenario.
        
        Args:
            scenario: 'bear', 'base', or 'bull'
            
        Returns:
            Fair value per share for the scenario
        """
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
        """
        Get complete scenario analysis with Bear/Base/Bull cases.
        
        Returns:
            Dict with fair values and assumptions for each scenario
        """
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