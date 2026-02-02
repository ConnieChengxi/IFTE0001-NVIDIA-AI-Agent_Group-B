"""
Cache Manager
Handles caching of API responses to disk.
"""

import os
import json
import time
import hashlib
from typing import Any, Optional
from config.settings import CACHE_DIR, CACHE_TTL_HOURS


class CacheManager:
    """Manages caching of API responses."""
    
    def __init__(self, cache_dir: str = CACHE_DIR):
        self.cache_dir = cache_dir
        self.ttl_seconds = CACHE_TTL_HOURS * 3600
        self._ensure_cache_dir()
    
    def _ensure_cache_dir(self):
        """Create cache directory if it doesn't exist."""
        os.makedirs(self.cache_dir, exist_ok=True)
    
    def _get_cache_path(self, symbol: str, function: str) -> str:
        """Generate cache file path for given symbol and function."""
        # Create subdirectory for each symbol
        symbol_dir = os.path.join(self.cache_dir, symbol.upper())
        os.makedirs(symbol_dir, exist_ok=True)
        
        # Create filename from function name
        filename = f"{function.lower()}.json"
        return os.path.join(symbol_dir, filename)
    
    def _is_cache_valid(self, filepath: str) -> bool:
        """Check if cache file exists and is still valid (within TTL)."""
        if not os.path.exists(filepath):
            return False
        
        # Check file age
        file_age = time.time() - os.path.getmtime(filepath)
        return file_age < self.ttl_seconds
    
    def get(self, symbol: str, function: str) -> Optional[Any]:
        """
        Retrieve data from cache if valid.
        
        Args:
            symbol: Stock ticker
            function: API function name
            
        Returns:
            Cached data or None if not found/expired
        """
        filepath = self._get_cache_path(symbol, function)
        
        if not self._is_cache_valid(filepath):
            return None
        
        try:
            with open(filepath, 'r') as f:
                cache_data = json.load(f)
                return cache_data.get('data')
        except (json.JSONDecodeError, IOError) as e:
            print(f"   ⚠️  Cache read error: {e}")
            return None
    
    def save(self, symbol: str, function: str, data: Any) -> None:
        """
        Save data to cache.
        
        Args:
            symbol: Stock ticker
            function: API function name
            data: Data to cache
        """
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
            print(f"   ⚠️  Cache write error: {e}")
    
    def clear(self, symbol: Optional[str] = None) -> None:
        """
        Clear cache for specific symbol or all cache.
        
        Args:
            symbol: Stock ticker to clear, or None to clear all
        """
        if symbol:
            symbol_dir = os.path.join(self.cache_dir, symbol.upper())
            if os.path.exists(symbol_dir):
                import shutil
                shutil.rmtree(symbol_dir)
                print(f"   🗑️  Cleared cache for {symbol}")
        else:
            if os.path.exists(self.cache_dir):
                import shutil
                shutil.rmtree(self.cache_dir)
                self._ensure_cache_dir()
                print(f"   🗑️  Cleared all cache")
    
    def get_cache_info(self, symbol: str) -> dict:
        """
        Get information about cached data for a symbol.
        
        Returns:
            Dict with cache status for each function
        """
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

