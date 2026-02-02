"""
File-based cache manager for API responses.
"""

import os
import json
import time
import shutil
from typing import Any, Optional
from config.settings import CACHE_DIR, CACHE_TTL_HOURS, CACHE_TTL_STATEMENTS_DAYS, STATEMENT_FUNCTIONS


class CacheManager:
    
    def __init__(self, cache_dir: str = CACHE_DIR):
        self.cache_dir = cache_dir
        self.ttl_market_seconds = CACHE_TTL_HOURS * 3600  # 24 hours for market data
        self.ttl_statements_seconds = CACHE_TTL_STATEMENTS_DAYS * 24 * 3600  # 90 days for statements
        self._ensure_cache_dir()

    def _get_ttl_for_function(self, function: str) -> int:
        """Get appropriate TTL based on data type."""
        if function.upper() in STATEMENT_FUNCTIONS:
            return self.ttl_statements_seconds
        return self.ttl_market_seconds
    
    def _ensure_cache_dir(self):
        os.makedirs(self.cache_dir, exist_ok=True)
    
    def _get_cache_path(self, symbol: str, function: str) -> str:
        symbol_dir = os.path.join(self.cache_dir, symbol.upper())
        os.makedirs(symbol_dir, exist_ok=True)
        
        filename = f"{function.lower()}.json"
        return os.path.join(symbol_dir, filename)
    
    def _is_cache_valid(self, filepath: str, function: str) -> bool:
        if not os.path.exists(filepath):
            return False

        ttl = self._get_ttl_for_function(function)
        file_age = time.time() - os.path.getmtime(filepath)
        return file_age < ttl
    
    def get(self, symbol: str, function: str) -> Optional[Any]:
        filepath = self._get_cache_path(symbol, function)

        if not self._is_cache_valid(filepath, function):
            return None
        
        try:
            with open(filepath, 'r') as f:
                cache_data = json.load(f)
                return cache_data.get('data')
        except (json.JSONDecodeError, IOError) as e:
            print(f"   [WARN] Cache read error: {e}")
            return None
    
    def save(self, symbol: str, function: str, data: Any) -> None:
        filepath = self._get_cache_path(symbol, function)
        
        cache_obj = {
            'cached_at': time.time(),
            'symbol': symbol.upper(),
            'function': function,
            'data': data
        }
        
        try:
            with open(filepath, 'w') as f:
                json.dump(cache_obj, f, indent=2)
        except IOError as e:
            print(f"   [WARN] Cache write error: {e}")
    
    def clear(self, symbol: Optional[str] = None) -> None:
        if symbol:
            symbol_dir = os.path.join(self.cache_dir, symbol.upper())
            if os.path.exists(symbol_dir):
                shutil.rmtree(symbol_dir)
                print(f"   Cleared cache for {symbol}")
        else:
            if os.path.exists(self.cache_dir):
                shutil.rmtree(self.cache_dir)
                self._ensure_cache_dir()
                print(f"   Cleared all cache")
    
    def get_cache_info(self, symbol: str) -> dict:
        symbol_dir = os.path.join(self.cache_dir, symbol.upper())

        if not os.path.exists(symbol_dir):
            return {}

        info = {}
        for filename in os.listdir(symbol_dir):
            if filename.endswith('.json'):
                filepath = os.path.join(symbol_dir, filename)
                function = filename.replace('.json', '').upper()

                ttl = self._get_ttl_for_function(function)
                file_age = time.time() - os.path.getmtime(filepath)
                hours_old = file_age / 3600
                is_valid = file_age < ttl

                info[function] = {
                    'valid': is_valid,
                    'age_hours': round(hours_old, 1),
                    'ttl_days': round(ttl / 3600 / 24, 1),
                    'expires_in_hours': round((ttl - file_age) / 3600, 1) if is_valid else 0
                }

        return info