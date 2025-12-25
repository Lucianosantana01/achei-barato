"""
Módulo de fetch HTTP com rate limiting e detecção de bloqueios.
Usa httpx para requisições assíncronas.
"""
import time
import httpx
import re
from typing import Optional, Dict
from urllib.parse import urlparse, urlunparse
from storage import cache


class RateLimiter:
    """Gerencia rate limiting por domínio."""
    
    def __init__(self, min_delay: float = 2.0, max_delay: float = 5.0):
        self.min_delay = min_delay
        self.max_delay = max_delay
        self._last_request: Dict[str, float] = {}
    
    def wait_if_needed(self, url: str) -> None:
        """Aguarda se necessário para respeitar rate limit."""
        domain = urlparse(url).netloc
        last_time = self._last_request.get(domain, 0)
        elapsed = time.time() - last_time
        
        # Delay aleatório entre min e max
        import random
        delay = random.uniform(self.min_delay, self.max_delay)
        
        if elapsed < delay:
            time.sleep(delay - elapsed)
        
        self._last_request[domain] = time.time()


class Fetcher:
    """Faz requisições HTTP com rate limiting e cache."""
    
    def __init__(self, min_delay: float = 2.0, max_delay: float = 5.0):
        self.rate_limiter = RateLimiter(min_delay, max_delay)
        self.client = httpx.Client(
            timeout=30.0,
            follow_redirects=True,
            headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            }
        )
    
    def _normalize_url(self, url: str, debug: bool = False) -> str:
        """
        Normaliza URL removendo query params desnecessários e mantendo apenas whitelist.
        
        IMPORTANTE: NÃO agrupa variações (cor, capacidade) no mesmo cache,
        pois cada variação pode ter preço diferente.
        
        Whitelist de params mantidos:
        - k: Query de busca (Amazon)
        - q: Query de busca (alternativa)
        - rh: Filtros de preço (Amazon)
        - p: Página (Amazon)
        - page: Página (alternativa)
        - s: Ordenação (Amazon)
        - sort: Ordenação (alternativa)
        - orderId: Ordenação (Mercado Livre)
        
        Remove:
        - Query params de tracking/analytics
        - Fragmentos (#)
        - Parâmetros de sessão
        - Qualquer param fora da whitelist
        
        Mantém:
        - Path completo (incluindo variações como cor/capacidade)
        - Query params essenciais (ordenados e normalizados)
        """
        from urllib.parse import parse_qs, urlencode, quote, unquote, quote_plus
        
        parsed = urlparse(url)
        
        # Whitelist de parâmetros essenciais
        WHITELIST_PARAMS = {'k', 'q', 'rh', 'p', 'page', 's', 'sort', 'orderId'}
        
        # Preserva query params essenciais da whitelist
        normalized_params = {}
        if parsed.query:
            params = parse_qs(parsed.query, keep_blank_values=False)
            
            for key, values in params.items():
                if key in WHITELIST_PARAMS:
                    # Normaliza valores: remove espaços extras, normaliza encoding
                    normalized_values = []
                    for value in values:
                        if value:
                            # Decodifica primeiro para normalizar espaços
                            # parse_qs já decodifica automaticamente, mas vamos garantir
                            try:
                                decoded = unquote(value, encoding='utf-8')
                            except:
                                decoded = value
                            # Remove espaços extras e normaliza
                            normalized = ' '.join(decoded.split())
                            # Re-encoda usando quote_plus para garantir que espaços virem + (padrão URL)
                            normalized_values.append(quote_plus(normalized, safe=''))
                    if normalized_values:
                        normalized_params[key] = normalized_values
        
        # Ordena parâmetros para garantir chave consistente
        sorted_params = sorted(normalized_params.items())
        query_string = urlencode(sorted_params, doseq=True) if sorted_params else ''
        
        # Mantém path completo para preservar variações
        normalized = urlunparse((
            parsed.scheme,
            parsed.netloc,
            parsed.path,
            '',  # params
            query_string,  # Query params normalizados e ordenados
            ''   # fragment (sempre removido)
        ))
        
        # Debug: mostra transformação
        if debug:
            print(f"[CACHE DEBUG] URL original: {url}")
            print(f"[CACHE DEBUG] Cache key:     {normalized}")
            if parsed.query != query_string:
                print(f"[CACHE DEBUG] Query params removidos: {set(parse_qs(parsed.query).keys()) - WHITELIST_PARAMS}")
        
        return normalized
    
    def fetch(self, url: str, use_cache: bool = True, force_refresh: bool = False) -> Optional[str]:
        """
        Busca conteúdo HTML da URL.
        
        Args:
            url: URL para buscar
            use_cache: Se deve usar cache
            force_refresh: Se True, ignora cache e busca novamente
        
        Returns:
            HTML como string ou None se houver erro/bloqueio
        """
        # Normaliza URL para chave de cache consistente
        # Ativa debug apenas em desenvolvimento (pode ser controlado por env var)
        import os
        debug_cache = os.getenv('DEBUG_CACHE', 'false').lower() == 'true'
        cache_key = self._normalize_url(url, debug=debug_cache) if use_cache else url
        
        # Verifica cache (a menos que force_refresh seja True)
        if use_cache and not force_refresh:
            cached = cache.get(cache_key)
            if cached is not None:
                return cached
        
        # Rate limiting
        self.rate_limiter.wait_if_needed(url)
        
        try:
            response = self.client.get(url)
            
            # Detecção de bloqueios
            if response.status_code == 403:
                raise Exception(f"Bloqueio detectado (403) para {url}")
            elif response.status_code == 429:
                raise Exception(f"Rate limit excedido (429) para {url}. Aguarde antes de tentar novamente.")
            elif response.status_code != 200:
                raise Exception(f"Erro HTTP {response.status_code} para {url}")
            
            html = response.text
            
            # Armazena no cache usando chave normalizada
            if use_cache:
                cache.set(cache_key, html)
            
            return html
        
        except httpx.RequestError as e:
            raise Exception(f"Erro na requisição para {url}: {str(e)}")
        finally:
            pass  # Client mantido aberto para reutilização
    
    def close(self) -> None:
        """Fecha o cliente HTTP."""
        self.client.close()

