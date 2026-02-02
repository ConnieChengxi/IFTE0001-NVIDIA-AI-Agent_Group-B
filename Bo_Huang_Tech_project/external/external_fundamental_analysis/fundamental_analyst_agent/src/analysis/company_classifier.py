"""
Company Classifier
Classifies companies into: growth, balanced, dividend, or cyclical types.
"""

from typing import Dict, List, Optional
from config.settings import MIN_DIVIDEND_YIELD


CYCLICAL_INDUSTRIES = [
    "oil & gas", "energy", "materials", "mining", "steel",
    "chemicals", "airlines", "auto manufacturers", "construction",
    "aerospace & defense",
]


class CompanyClassifier:
    
    def __init__(self, company_data: Dict, ratios: Dict):
        self.overview = company_data.get('overview', {})
        self.income = company_data.get('income', [])
        self.ratios = ratios
    
    def _get_latest(self, data_list: List[Dict], field: str) -> Optional[float]:
        if not data_list:
            return None
        return data_list[0].get(field)
    
    def _is_cyclical_industry(self) -> bool:
        industry = self.overview.get('industry', '').lower()
        sector = self.overview.get('sector', '').lower()
        for cyclical in CYCLICAL_INDUSTRIES:
            if cyclical in industry or cyclical in sector:
                return True
        return False
    
    def _calculate_earnings_volatility(self) -> Optional[float]:
        """
        Calculate earnings volatility (standard deviation of growth rates).
        Note: High volatility doesn't always mean cyclical - could be growth acceleration.
        """
        earnings_history = []
        for i in range(min(5, len(self.income))):
            net_income = self.income[i].get('net_income')
            if net_income:
                earnings_history.append(net_income)
        
        if len(earnings_history) < 3:
            return None
        
        growth_rates = []
        for i in range(len(earnings_history) - 1):
            current = earnings_history[i]
            previous = earnings_history[i + 1]
            if previous and previous != 0:
                growth = (current - previous) / abs(previous)
                growth_rates.append(growth)
        
        if len(growth_rates) < 2:
            return None
        
        mean = sum(growth_rates) / len(growth_rates)
        variance = sum((x - mean) ** 2 for x in growth_rates) / len(growth_rates)
        std_dev = variance ** 0.5
        return std_dev
    
    def classify(self) -> str:
        """
        Classify company into one of four types.
        
        Decision tree:
        1. Cyclical: Sector-based (Energy, Materials, etc)
        2. Dividend: High yield (>4%), low growth (<10%)
        3. Growth: High growth (>15%), low dividend (<2%)
        4. Balanced: Everything else
        
        Note: We removed earnings volatility from cyclical check because
        high volatility can indicate growth acceleration, not just cycles.
        Example: NVDA has high volatility due to AI boom, but it's growth not cyclical.
        """
        revenue_growth = self.ratios.get('revenue_growth', 0) or 0
        dividend_yield = self.overview.get('dividend_yield', 0) or 0
        is_cyclical_industry = self._is_cyclical_industry()
        
        # STEP 1: Check cyclical industry (sector-based only)
        # High earnings volatility alone doesn't mean cyclical - could be growth acceleration
        if is_cyclical_industry:
            return "cyclical"
        
        # STEP 2: Check dividend (mature, stable companies)
        # Raised threshold to 4% to be more selective
        if dividend_yield >= 0.04 and revenue_growth < 0.10:
            return "dividend"
        
        # STEP 3: Check growth (high growth, low/no dividend)
        # Changed dividend threshold to 2% (was MIN_DIVIDEND_YIELD)
        if revenue_growth >= 0.15 and dividend_yield < 0.02:
            return "growth"
        
        # STEP 4: Default to balanced
        return "balanced"
    
    def get_classification_details(self) -> Dict:
        """Get classification with detailed reasoning and metrics."""
        company_type = self.classify()
        revenue_growth = self.ratios.get('revenue_growth', 0) or 0
        dividend_yield = self.overview.get('dividend_yield', 0) or 0
        earnings_volatility = self._calculate_earnings_volatility()
        is_cyclical_industry = self._is_cyclical_industry()
        
        if company_type == "growth":
            reasoning = f"Classified as GROWTH company due to: high revenue growth ({revenue_growth:.1%}), low dividend yield ({dividend_yield:.1%}), and focus on reinvesting for expansion."
        elif company_type == "dividend":
            reasoning = f"Classified as DIVIDEND company due to: high dividend yield ({dividend_yield:.1%}), mature business with stable cash flows, and lower growth rate ({revenue_growth:.1%})."
        elif company_type == "cyclical":
            reasons = []
            if is_cyclical_industry:
                sector = self.overview.get('sector', 'N/A')
                industry = self.overview.get('industry', 'N/A')
                reasons.append(f"operates in cyclical sector/industry ({sector}/{industry})")
            reasoning = f"Classified as CYCLICAL company due to: {', '.join(reasons)}. Performance tied to economic cycles."
        else:
            reasoning = f"Classified as BALANCED company due to: moderate revenue growth ({revenue_growth:.1%}), some dividend payments ({dividend_yield:.1%}), and mix of growth and income characteristics."
        
        return {
            'company_type': company_type,
            'reasoning': reasoning,
            'metrics': {
                'revenue_growth': revenue_growth,
                'dividend_yield': dividend_yield,
                'earnings_volatility': earnings_volatility,
                'is_cyclical_industry': is_cyclical_industry,
            }
        }