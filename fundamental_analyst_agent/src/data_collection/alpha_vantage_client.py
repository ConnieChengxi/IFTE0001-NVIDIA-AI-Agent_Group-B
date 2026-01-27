import requests
import time
from typing import Dict, List, Optional
from .cache_manager import CacheManager
from config.settings import ALPHA_VANTAGE_API_KEY, ALPHA_VANTAGE_BASE_URL


class AlphaVantageClient:
    
    def __init__(self, cache_manager: Optional[CacheManager] = None):
        self.api_key = ALPHA_VANTAGE_API_KEY
        self.base_url = ALPHA_VANTAGE_BASE_URL
        self.cache_manager = cache_manager
        self.last_request_time = 0
        self.rate_limit_delay = 12
        
        if not self.api_key:
            raise ValueError("Alpha Vantage API key not found in config/settings.py")
    
    def _rate_limit(self):
        elapsed = time.time() - self.last_request_time
        if elapsed < self.rate_limit_delay:
            sleep_time = self.rate_limit_delay - elapsed
            print(f"   ⏳ Waiting {sleep_time:.1f}s (rate limit)...")
            time.sleep(sleep_time)
        self.last_request_time = time.time()
    
    def _fetch_json(self, symbol: str, function: str) -> Optional[Dict]:
        if self.cache_manager:
            cached_data = self.cache_manager.get(symbol, function)
            if cached_data:
                print(f"   📦 Cached: {function}")
                return cached_data
        
        self._rate_limit()
        
        print(f"   🌐 API: {function}")
        params = {
            'function': function,
            'symbol': symbol,
            'apikey': self.api_key
        }
        
        try:
            response = requests.get(self.base_url, params=params, timeout=30)
            
            if response.status_code != 200:
                raise Exception(f"API request failed with status {response.status_code}")
            
            data = response.json()
            
            if 'Error Message' in data:
                raise Exception(f"API error: {data['Error Message']}")
            if 'Note' in data:
                raise Exception(f"API rate limit exceeded: {data['Note']}")
            if 'Information' in data:
                raise Exception(f"API info: {data['Information']}")
            
            if self.cache_manager:
                self.cache_manager.save(symbol, function, data)
            
            return data
            
        except requests.exceptions.RequestException as e:
            raise Exception(f"Network error: {str(e)}")
    
    def _convert_to_number(self, value):
        if value is None or value == 'None' or value == '':
            return None
        
        if isinstance(value, (int, float)):
            return float(value)
        
        try:
            cleaned = str(value).strip()
            
            if cleaned.endswith('%'):
                cleaned = cleaned.rstrip('%')
            
            return float(cleaned)
            
        except (ValueError, TypeError, AttributeError):
            return None
    
    def _normalize_keys(self, data: Dict) -> Dict:
        if not isinstance(data, dict):
            return data
        
        normalized = {}
        for key, value in data.items():
            new_key = key.lower().replace(' ', '_').replace('-', '_')
            
            if isinstance(value, dict):
                normalized[new_key] = self._normalize_keys(value)
            elif isinstance(value, str):
                num_value = self._convert_to_number(value)
                normalized[new_key] = num_value if num_value is not None else value
            else:
                normalized[new_key] = value
        
        return normalized
    
    def _map_fields(self, data: Dict) -> Dict:

        field_mappings = {
            'total_revenue': 'revenue',
            'totalrevenue': 'revenue',
            'TotalRevenue': 'revenue',
            'revenues': 'revenue',
            'sales': 'revenue',
            'total_sales': 'revenue',
            
            'cost_of_revenue': 'cost_of_revenue',
            'costofrevenue': 'cost_of_revenue',
            'CostOfRevenue': 'cost_of_revenue',
            'cogs': 'cost_of_revenue',
            'COGS': 'cost_of_revenue',
            'cost_of_goods_sold': 'cost_of_revenue',
            'costofgoodssold': 'cost_of_revenue',
            'CostOfGoodsSold': 'cost_of_revenue',
            'costofgoodsandservicessold': 'cost_of_revenue',
            'cost_of_goods_and_services_sold': 'cost_of_revenue',
            
            'operating_income': 'operating_income',
            'operatingincome': 'operating_income',
            'OperatingIncome': 'operating_income',
            'ebit': 'operating_income',
            'EBIT': 'operating_income',
            'operating_profit': 'operating_income',
            
            'net_income': 'net_income',
            'netincome': 'net_income',
            'NetIncome': 'net_income',
            'net_profit': 'net_income',
            'netprofit': 'net_income',
            'earnings': 'net_income',
            
            'gross_profit': 'gross_profit',
            'grossprofit': 'gross_profit',
            'GrossProfit': 'gross_profit',
            
            'interest_expense': 'interest_expense',
            'interestexpense': 'interest_expense',
            'InterestExpense': 'interest_expense',
            'interest_paid': 'interest_expense',
            
            'income_tax_expense': 'income_tax_expense',
            'incometaxexpense': 'income_tax_expense',
            'IncomeTaxExpense': 'income_tax_expense',
            'tax_expense': 'income_tax_expense',
            'taxes': 'income_tax_expense',
            
            'total_assets': 'total_assets',
            'totalassets': 'total_assets',
            'TotalAssets': 'total_assets',
            
            'current_assets': 'current_assets',
            'currentassets': 'current_assets',
            'CurrentAssets': 'current_assets',
            'total_current_assets': 'current_assets',
            'totalcurrentassets': 'current_assets',
            'TotalCurrentAssets': 'current_assets',
            
            'cash': 'cash',
            'Cash': 'cash',
            'cash_and_cash_equivalents': 'cash',
            'cashandcashequivalents': 'cash',
            'CashAndCashEquivalents': 'cash',
            'cash_and_cash_equivalents_at_carrying_value': 'cash',
            'cashandcashequivalentsatcarryingvalue': 'cash',
            'cash_and_short_term_investments': 'cash',
            'cashandshortterminvestments': 'cash',
            
            'inventory': 'inventory',
            'Inventory': 'inventory',
            'inventories': 'inventory',
            
            'property_plant_equipment': 'ppe',
            'propertyplantequipment': 'ppe',
            'PropertyPlantEquipment': 'ppe',
            'property_plant_and_equipment': 'ppe',
            'ppe': 'ppe',
            'PPE': 'ppe',
            'fixed_assets': 'ppe',
            
            'goodwill': 'goodwill',
            'Goodwill': 'goodwill',
            
            'intangible_assets': 'intangible_assets',
            'intangibleassets': 'intangible_assets',
            'IntangibleAssets': 'intangible_assets',
            
            'total_liabilities': 'total_liabilities',
            'totalliabilities': 'total_liabilities',
            'TotalLiabilities': 'total_liabilities',
            
            'current_liabilities': 'current_liabilities',
            'currentliabilities': 'current_liabilities',
            'CurrentLiabilities': 'current_liabilities',
            'total_current_liabilities': 'current_liabilities',
            'totalcurrentliabilities': 'current_liabilities',
            'TotalCurrentLiabilities': 'current_liabilities',
            
            'accounts_payable': 'accounts_payable',
            'accountspayable': 'accounts_payable',
            'AccountsPayable': 'accounts_payable',
            'current_accounts_payable': 'accounts_payable',
            'currentaccountspayable': 'accounts_payable',
            
            'long_term_debt': 'long_term_debt',
            'longtermdebt': 'long_term_debt',
            'LongTermDebt': 'long_term_debt',
            'long_term_debt_total': 'long_term_debt',
            'longtermdebtotal': 'long_term_debt',
            'noncurrent_debt': 'long_term_debt',
            
            'short_term_debt': 'short_term_debt',
            'shorttermdebt': 'short_term_debt',
            'ShortTermDebt': 'short_term_debt',
            'current_debt': 'short_term_debt',
            'currentdebt': 'short_term_debt',
            'short_long_term_debt_total': 'short_term_debt',
            'shortlongtermdebttotal': 'short_term_debt',
            'ShortLongTermDebtTotal': 'short_term_debt',
            'debt_current': 'short_term_debt',
            
            'total_shareholder_equity': 'total_shareholder_equity',
            'totalshareholderequity': 'total_shareholder_equity',
            'TotalShareholderEquity': 'total_shareholder_equity',
            'total_stockholder_equity': 'total_shareholder_equity',
            'totalstockholderequity': 'total_shareholder_equity',
            'TotalStockholderEquity': 'total_shareholder_equity',
            'shareholder_equity': 'total_shareholder_equity',
            'shareholderequity': 'total_shareholder_equity',
            'ShareholderEquity': 'total_shareholder_equity',
            'stockholder_equity': 'total_shareholder_equity',
            'stockholderequity': 'total_shareholder_equity',
            'StockholderEquity': 'total_shareholder_equity',
            'shareholders_equity': 'total_shareholder_equity',
            'equity': 'total_shareholder_equity',
            'Equity': 'total_shareholder_equity',
            'total_equity': 'total_shareholder_equity',
            'owners_equity': 'total_shareholder_equity',
            
            'retained_earnings': 'retained_earnings',
            'retainedearnings': 'retained_earnings',
            'RetainedEarnings': 'retained_earnings',
            
            'common_stock': 'common_stock',
            'commonstock': 'common_stock',
            'CommonStock': 'common_stock',
            
            'operating_cash_flow': 'operating_cashflow',
            'operatingcashflow': 'operating_cashflow',
            'OperatingCashFlow': 'operating_cashflow',
            'cash_flow_from_operations': 'operating_cashflow',
            'cashflowfromoperations': 'operating_cashflow',
            'cash_flow_from_operating_activities': 'operating_cashflow',
            'cashflowfromoperatingactivities': 'operating_cashflow',
            'operating_activities_cash_flow': 'operating_cashflow',
            'ocf': 'operating_cashflow',
            'OCF': 'operating_cashflow',
            
            'capital_expenditures': 'capital_expenditures',
            'capitalexpenditures': 'capital_expenditures',
            'CapitalExpenditures': 'capital_expenditures',
            'capex': 'capital_expenditures',
            'CAPEX': 'capital_expenditures',
            'capital_expenditure': 'capital_expenditures',
            'payments_for_capital_expenditures': 'capital_expenditures',
            
            'dividends_paid': 'dividends_paid',
            'dividendspaid': 'dividends_paid',
            'DividendsPaid': 'dividends_paid',
            'dividend_payout': 'dividends_paid',
            'dividendpayout': 'dividends_paid',
            'dividends_payout': 'dividends_paid',
            'dividendspayout': 'dividends_paid',
            'dividend_payout_common_stock': 'dividends_paid',
            'dividendpayoutcommonstock': 'dividends_paid',
            
            'cash_flow_from_financing': 'financing_cashflow',
            'cashflowfromfinancing': 'financing_cashflow',
            'CashFlowFromFinancing': 'financing_cashflow',
            'financing_activities_cash_flow': 'financing_cashflow',
            
            'cash_flow_from_investment': 'investing_cashflow',
            'cashflowfrominvestment': 'investing_cashflow',
            'CashFlowFromInvestment': 'investing_cashflow',
            'cash_flow_from_investing': 'investing_cashflow',
            'investing_activities_cash_flow': 'investing_cashflow',
            
            'market_capitalization': 'market_cap',
            'marketcapitalization': 'market_cap',
            'MarketCapitalization': 'market_cap',
            'market_cap': 'market_cap',
            'marketcap': 'market_cap',
            'MarketCap': 'market_cap',
            
            'shares_outstanding': 'shares_outstanding',
            'sharesoutstanding': 'shares_outstanding',
            'SharesOutstanding': 'shares_outstanding',
            'common_stock_shares_outstanding': 'shares_outstanding',
            'commonstocksharesoutstanding': 'shares_outstanding',
            'CommonStockSharesOutstanding': 'shares_outstanding',
            'outstanding_shares': 'shares_outstanding',
            
            'dividend_yield': 'dividend_yield',
            'dividendyield': 'dividend_yield',
            'DividendYield': 'dividend_yield',
            
            'beta': 'beta',
            'Beta': 'beta',
            
            'pe_ratio': 'pe_ratio',
            'peratio': 'pe_ratio',
            'PERatio': 'pe_ratio',
            'price_to_earnings': 'pe_ratio',
            'pricetoearnings': 'pe_ratio',
            'p/e': 'pe_ratio',
            'P/E': 'pe_ratio',
        }
        
        mapped_data = {}
        for key, value in data.items():
            mapped_key = field_mappings.get(key, key)
            mapped_data[mapped_key] = value
        
        return mapped_data
    
    def get_quote(self, symbol: str) -> Dict:
        data = self._fetch_json(symbol, 'GLOBAL_QUOTE')
        
        if not data or 'Global Quote' not in data:
            return {'price': None, 'change_percent': None}
        
        quote = data['Global Quote']
        
        price_str = quote.get('05. price')
        change_str = quote.get('10. change percent', '').replace('%', '')
        
        result = {
            'symbol': quote.get('01. symbol'),
            'price': self._convert_to_number(price_str),
            'change_percent': self._convert_to_number(change_str),
        }
        
        return result
    
    def get_company_overview(self, symbol: str) -> Dict:
        data = self._fetch_json(symbol, 'OVERVIEW')
        
        if not data:
            return {}
        
        normalized = self._normalize_keys(data)
        mapped = self._map_fields(normalized)
        
        if mapped.get('price') is None:
            try:
                quote_data = self.get_quote(symbol)
                if quote_data.get('price'):
                    mapped['price'] = quote_data['price']
                    print(f"   ✅ Added price from QUOTE: ${quote_data['price']:.2f}")
            except Exception as e:
                print(f"   ⚠️  Could not fetch quote: {e}")
        
        return mapped
    
    def get_income_statement(self, symbol: str) -> List[Dict]:
        data = self._fetch_json(symbol, 'INCOME_STATEMENT')
        
        if not data or 'annualReports' not in data:
            return []
        
        statements = []
        for report in data['annualReports'][:5]:
            normalized = self._normalize_keys(report)
            mapped = self._map_fields(normalized)
            statements.append(mapped)
        
        return statements
    
    def get_balance_sheet(self, symbol: str) -> List[Dict]:
        data = self._fetch_json(symbol, 'BALANCE_SHEET')
        
        if not data or 'annualReports' not in data:
            return []
        
        statements = []
        for report in data['annualReports'][:5]:
            normalized = self._normalize_keys(report)
            mapped = self._map_fields(normalized)
            statements.append(mapped)
        
        return statements
    
    def get_cash_flow(self, symbol: str) -> List[Dict]:
        data = self._fetch_json(symbol, 'CASH_FLOW')
        
        if not data or 'annualReports' not in data:
            return []
        
        statements = []
        for report in data['annualReports'][:5]:
            normalized = self._normalize_keys(report)
            mapped = self._map_fields(normalized)
            statements.append(mapped)
        
        return statements
    
    def get_all_financial_data(self, symbol: str) -> Dict:
        return {
            'overview': self.get_company_overview(symbol),
            'income': self.get_income_statement(symbol),
            'balance': self.get_balance_sheet(symbol),
            'cashflow': self.get_cash_flow(symbol)
        }