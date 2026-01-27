import os
import json
import time
import hashlib
from typing import Any, Optional
from config.settings import CACHE_DIR, CACHE_TTL_HOURS


class CacheManager:
    
    def __init__(self, cache_dir: str = CACHE_DIR):
        self.cache_dir = cache_dir
        self.ttl_seconds = CACHE_TTL_HOURS * 3600
        self._ensure_cache_dir()
    
    def _ensure_cache_dir(self):
        os.makedirs(self.cache_dir, exist_ok=True)
    
    def _get_cache_path(self, symbol: str, function: str) -> str:
        symbol_dir = os.path.join(self.cache_dir, symbol.upper())
        os.makedirs(symbol_dir, exist_ok=True)
        
        filename = f"{function.lower()}.json"
        return os.path.join(symbol_dir, filename)
    
    def _is_cache_valid(self, filepath: str) -> bool:
        if not os.path.exists(filepath):
            return False
        
        file_age = time.time() - os.path.getmtime(filepath)
        return file_age < self.ttl_seconds
    
    def get(self, symbol: str, function: str) -> Optional[Any]:
        filepath = self._get_cache_path(symbol, function)
        
        if not self._is_cache_valid(filepath):
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
                import shutil
                shutil.rmtree(symbol_dir)
                print(f"   Cleared cache for {symbol}")
        else:
            if os.path.exists(self.cache_dir):
                import shutil
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
                
                file_age = time.time() - os.path.getmtime(filepath)
                hours_old = file_age / 3600
                is_valid = file_age < self.ttl_seconds
                
                info[function] = {
                    'valid': is_valid,
                    'age_hours': round(hours_old, 1),
                    'expires_in_hours': round((self.ttl_seconds - file_age) / 3600, 1) if is_valid else 0
                }
        
        return info