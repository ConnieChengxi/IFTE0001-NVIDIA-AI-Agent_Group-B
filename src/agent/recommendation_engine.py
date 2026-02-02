"""
Investment recommendation engine combining valuation methods.
"""

from typing import Dict, Optional
from config.settings import (
    BUY_THRESHOLD,
    SELL_THRESHOLD,
    MIN_INTEREST_COVERAGE,
    MIN_CURRENT_RATIO,
    COMPANY_TYPE_WEIGHTS
)


class RecommendationEngine:
    
    def __init__(
        self,
        company_type: str,
        current_price: float,
        dcf_result: Dict,
        multiples_result: Dict,
        ddm_result: Dict,
        ratios: Dict
    ):
        self.company_type = company_type
        self.current_price = current_price
        self.dcf_result = dcf_result
        self.multiples_result = multiples_result
        self.ddm_result = ddm_result
        self.ratios = ratios
    
    def calculate_weighted_fair_value(self) -> Optional[float]:
        weights = COMPANY_TYPE_WEIGHTS.get(self.company_type, COMPANY_TYPE_WEIGHTS['balanced'])
        
        dcf_fv = self.dcf_result.get('fair_value_per_share')
        multiples_fv = self.multiples_result.get('average_fair_value')
        ddm_fv = self.ddm_result.get('fair_value_per_share')
        
        total_weight = 0
        weighted_sum = 0
        
        if dcf_fv:
            weighted_sum += dcf_fv * weights['dcf']
            total_weight += weights['dcf']
        
        if multiples_fv:
            weighted_sum += multiples_fv * weights['multiples']
            total_weight += weights['multiples']
        
        if ddm_fv:
            weighted_sum += ddm_fv * weights['ddm']
            total_weight += weights['ddm']
        
        if total_weight == 0:
            return None
        
        weighted_fair_value = weighted_sum / total_weight
        
        return weighted_fair_value
    
    def calculate_upside_downside(self, fair_value: float) -> float:
        if not self.current_price or self.current_price <= 0:
            return 0.0
        
        return (fair_value - self.current_price) / self.current_price
    
    def check_risk_factors(self) -> Dict[str, bool]:
        interest_coverage = self.ratios.get('interest_coverage')
        solvency_risk = (
            interest_coverage is not None and 
            interest_coverage < MIN_INTEREST_COVERAGE
        )
        
        current_ratio = self.ratios.get('current_ratio')
        liquidity_risk = (
            current_ratio is not None and 
            current_ratio < MIN_CURRENT_RATIO
        )
        
        debt_to_equity = self.ratios.get('debt_to_equity')
        leverage_risk = (
            debt_to_equity is not None and 
            debt_to_equity > 5.0
        )
        
        return {
            'solvency_risk': solvency_risk,
            'liquidity_risk': liquidity_risk,
            'leverage_risk': leverage_risk,
            'has_risk_flags': solvency_risk or liquidity_risk or leverage_risk
        }
    
    def generate_recommendation(self) -> str:
        fair_value = self.calculate_weighted_fair_value()
        
        if not fair_value:
            return "HOLD"
        
        upside = self.calculate_upside_downside(fair_value)
        
        risks = self.check_risk_factors()
        
        if risks['has_risk_flags']:
            if upside >= BUY_THRESHOLD:
                return "HOLD"
            elif upside <= SELL_THRESHOLD:
                return "SELL"
            else:
                return "HOLD"
        
        if upside >= BUY_THRESHOLD:
            return "BUY"
        elif upside <= SELL_THRESHOLD:
            return "SELL"
        else:
            return "HOLD"
    
    def get_recommendation_summary(self) -> Dict:
        fair_value = self.calculate_weighted_fair_value()
        
        if not fair_value:
            return {
                'recommendation': 'HOLD',
                'fair_value': None,
                'current_price': self.current_price,
                'upside_downside': None,
                'error': 'Insufficient data for valuation'
            }
        
        upside = self.calculate_upside_downside(fair_value)
        risks = self.check_risk_factors()
        recommendation = self.generate_recommendation()
        
        reasoning = self._build_reasoning(
            recommendation,
            fair_value,
            upside,
            risks
        )
        
        dcf_fv = self.dcf_result.get('fair_value_per_share')
        multiples_fv = self.multiples_result.get('average_fair_value')
        ddm_fv = self.ddm_result.get('fair_value_per_share')
        
        weights = COMPANY_TYPE_WEIGHTS.get(self.company_type, COMPANY_TYPE_WEIGHTS['balanced'])
        
        return {
            'recommendation': recommendation,
            'reasoning': reasoning,
            'fair_value': fair_value,
            'current_price': self.current_price,
            'upside_downside': upside,
            'dcf_fair_value': dcf_fv,
            'multiples_fair_value': multiples_fv,
            'ddm_fair_value': ddm_fv,
            'company_type': self.company_type,
            'weights': weights,
            'risk_factors': risks,
            'thresholds': {
                'buy_threshold': BUY_THRESHOLD,
                'sell_threshold': SELL_THRESHOLD,
            }
        }
    
    def _build_reasoning(
        self,
        recommendation: str,
        fair_value: float,
        upside: float,
        risks: Dict[str, bool]
    ) -> str:
        upside_str = f"{upside:+.1%}"
        
        if recommendation == "BUY":
            base = f"Stock is undervalued with {upside_str} upside to fair value of ${fair_value:.2f}."
            
            if risks['has_risk_flags']:
                risk_warning = " However, risk factors present - proceed with caution."
                return base + risk_warning
            else:
                return base + " Strong fundamentals with manageable risk."
        
        elif recommendation == "SELL":
            base = f"Stock is overvalued with {upside_str} downside to fair value of ${fair_value:.2f}."
            
            if risks['has_risk_flags']:
                risk_flags = []
                if risks['solvency_risk']:
                    risk_flags.append("solvency concerns")
                if risks['liquidity_risk']:
                    risk_flags.append("liquidity issues")
                if risks['leverage_risk']:
                    risk_flags.append("excessive leverage")
                
                risk_warning = f" Additional concerns: {', '.join(risk_flags)}."
                return base + risk_warning
            else:
                return base + " Consider taking profits."
        
        else:
            base = f"Stock is fairly valued (current: ${self.current_price:.2f}, fair value: ${fair_value:.2f})."
            
            if risks['has_risk_flags']:
                risk_flags = []
                if risks['solvency_risk']:
                    risk_flags.append(f"low interest coverage (<{MIN_INTEREST_COVERAGE}x)")
                if risks['liquidity_risk']:
                    risk_flags.append(f"low current ratio (<{MIN_CURRENT_RATIO}x)")
                if risks['leverage_risk']:
                    risk_flags.append("high leverage")
                
                risk_warning = f" Risk factors present: {', '.join(risk_flags)}. Wait for better entry point."
                return base + risk_warning
            else:
                return base + f" Upside of {upside_str} does not meet {BUY_THRESHOLD:+.0%} threshold for BUY."