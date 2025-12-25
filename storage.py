"""
Módulo de armazenamento em cache em memória.
Gerencia cache com TTL mínimo de 10 minutos.
"""
import time
from typing import Optional, Dict, Any


class MemoryCache:
    """Cache em memória com TTL configurável."""
    
    def __init__(self, default_ttl: int = 600):  # 10 minutos padrão
        self._cache: Dict[str, Dict[str, Any]] = {}
        self.default_ttl = default_ttl
    
    def get(self, key: str) -> Optional[Any]:
        """Recupera valor do cache se ainda válido."""
        if key not in self._cache:
            return None
        
        entry = self._cache[key]
        if time.time() > entry['expires_at']:
            del self._cache[key]
            return None
        
        return entry['value']
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """Armazena valor no cache com TTL."""
        ttl = ttl or self.default_ttl
        self._cache[key] = {
            'value': value,
            'expires_at': time.time() + ttl
        }
    
    def clear(self) -> None:
        """Limpa todo o cache."""
        self._cache.clear()
    
    def delete(self, key: str) -> bool:
        """
        Remove uma entrada específica do cache.
        
        Returns:
            True se a chave existia e foi removida, False caso contrário
        """
        if key in self._cache:
            del self._cache[key]
            return True
        return False
    
    def delete_by_pattern(self, pattern: str) -> int:
        """
        Remove entradas do cache que correspondem a um padrão.
        
        Args:
            pattern: Padrão para buscar nas chaves (substring)
        
        Returns:
            Número de entradas removidas
        """
        import re
        keys_to_delete = [key for key in self._cache.keys() if pattern in key or re.search(pattern, key)]
        count = 0
        for key in keys_to_delete:
            if key in self._cache:
                del self._cache[key]
                count += 1
        return count
    
    def size(self) -> int:
        """Retorna número de entradas no cache."""
        return len(self._cache)


# Instância global do cache
cache = MemoryCache()

