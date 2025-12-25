"""
API HTTP para comparação de preços.
Endpoint que recebe URLs e retorna dados estruturados.
"""
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel, HttpUrl
from typing import List, Optional, Dict, Any, Literal
from contextlib import asynccontextmanager
from fetcher import Fetcher
from extractor import Extractor
from normalizer import Normalizer
from storage import cache
from list_scraper import ListScraper
from price_history import price_history
from urllib.parse import urlparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Semaphore
import time
import random
import os
import logging
import re

logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Gerencia o ciclo de vida da aplicação."""
    # Startup
    yield
    # Shutdown
    try:
        if hasattr(fetcher, 'close'):
            fetcher.close()
    except Exception as e:
        logger.exception("Erro ao fechar fetcher no shutdown")
    
    try:
        if hasattr(list_scraper, 'close'):
            list_scraper.close()
    except Exception as e:
        logger.exception("Erro ao fechar list_scraper no shutdown")

app = FastAPI(title="Comparador de Preços", version="1.0.0", lifespan=lifespan)

# Servir arquivos estáticos
static_dir = os.path.join(os.path.dirname(__file__), "static")
if os.path.exists(static_dir):
    app.mount("/static", StaticFiles(directory=static_dir), name="static")

# Instâncias globais
fetcher = Fetcher()
extractor = Extractor()
normalizer = Normalizer()
list_scraper = ListScraper()


class DomainLimiter:
    """
    Controla rate limiting e concorrência por domínio.
    Garante que não haja rajadas de requisições no mesmo site.
    """
    def __init__(self, max_concurrent: int = 2, min_delay: float = 0.6, max_delay: float = 1.2):
        """
        Args:
            max_concurrent: Máximo de requisições simultâneas por domínio
            min_delay: Delay mínimo entre requisições (segundos)
            max_delay: Delay máximo entre requisições (segundos)
        """
        self.max_concurrent = max_concurrent
        self.min_delay = min_delay
        self.max_delay = max_delay
        self._semaphores: Dict[str, Semaphore] = {}
        self._last_request: Dict[str, float] = {}
        self._lock = Semaphore(1)  # Lock para acesso aos dicionários
    
    def _get_domain(self, url: str) -> str:
        """Extrai domínio da URL."""
        try:
            parsed = urlparse(url)
            return parsed.netloc.lower()
        except:
            return "unknown"
    
    def acquire(self, url: str) -> None:
        """
        Adquire permissão para fazer requisição ao domínio.
        Aguarda se necessário para respeitar rate limit.
        """
        domain = self._get_domain(url)
        
        # Cria semáforo para o domínio se não existir
        with self._lock:
            if domain not in self._semaphores:
                self._semaphores[domain] = Semaphore(self.max_concurrent)
                self._last_request[domain] = 0
        
        # Aguarda semáforo (limita concorrência)
        self._semaphores[domain].acquire()
        
        # Aguarda delay mínimo desde última requisição
        with self._lock:
            last_time = self._last_request.get(domain, 0)
            elapsed = time.time() - last_time
            
            # Delay aleatório com jitter
            delay = random.uniform(self.min_delay, self.max_delay)
            
            if elapsed < delay:
                time.sleep(delay - elapsed)
            
            self._last_request[domain] = time.time()
    
    def release(self, url: str) -> None:
        """Libera permissão após requisição."""
        domain = self._get_domain(url)
        if domain in self._semaphores:
            self._semaphores[domain].release()


# Instância global do DomainLimiter
domain_limiter = DomainLimiter(max_concurrent=2, min_delay=0.6, max_delay=1.2)


def fetch_with_retry(url: str, use_cache: bool = True, force_refresh: bool = False, max_retries: int = 2) -> tuple[Optional[str], Optional[str]]:
    """
    Busca HTML com retry leve para erros recuperáveis.
    
    Args:
        url: URL para buscar
        use_cache: Se deve usar cache
        force_refresh: Se deve forçar refresh
        max_retries: Número máximo de tentativas (incluindo primeira)
    
    Returns:
        Tuple (html, error_msg) onde:
        - html: HTML obtido ou None se falhou
        - error_msg: Mensagem de erro ou None se sucesso
    """
    last_error = None
    
    for attempt in range(max_retries):
        try:
            html = fetcher.fetch(url, use_cache=use_cache, force_refresh=force_refresh)
            return html, None
        except Exception as e:
            error_msg = str(e)
            last_error = error_msg
            
            # Não retry para 403/captcha/bloqueio permanente
            if "403" in error_msg or "bloqueio" in error_msg.lower() or "forbidden" in error_msg.lower() or "captcha" in error_msg.lower():
                return None, "Bloqueio detectado (403/captcha)"
            
            # Retry apenas para erros recuperáveis
            retryable = (
                "429" in error_msg or 
                "rate limit" in error_msg.lower() or
                "503" in error_msg or
                "502" in error_msg or
                "timeout" in error_msg.lower() or
                "timed out" in error_msg.lower()
            )
            
            if not retryable or attempt == max_retries - 1:
                # Última tentativa ou erro não recuperável
                return None, error_msg
            
            # Backoff com jitter: 1.0s depois 2.5s + jitter(0..0.5)
            if attempt == 0:
                delay = 1.0
            else:
                delay = 2.5 + random.uniform(0, 0.5)
            
            logger.warning(f"Tentativa {attempt + 1}/{max_retries} falhou para {url}: {error_msg}. Retry em {delay:.2f}s")
            time.sleep(delay)
    
    return None, last_error


def process_single_url(url_str: str, index: int, use_cache: bool, force_refresh: bool):
    """
    Processa uma única URL com rate limiting por domínio.
    
    Returns:
        Tuple (index, ProductResponse) para preservar ordem
    """
    try:
        # Adquire permissão do DomainLimiter
        domain_limiter.acquire(url_str)
        
        try:
            # Fetch HTML com retry
            html, fetch_error = fetch_with_retry(url_str, use_cache=use_cache, force_refresh=force_refresh)
            
            if fetch_error:
                # Detecta tipo de erro
                if "Bloqueio detectado" in fetch_error or "403" in fetch_error:
                    status = "blocked"
                elif "429" in fetch_error or "rate limit" in fetch_error:
                    status = "blocked"
                else:
                    status = "error"
                
                return index, ProductResponse(
                    success=False,
                    url=url_str,
                    status=status,
                    error=fetch_error
                )
            
            if not html:
                return index, ProductResponse(
                    success=False,
                    url=url_str,
                    status="error",
                    error="Não foi possível obter HTML da página"
                )
            
            # Extrai dados
            raw_data = extractor.extract(url_str, html)
            
            # Normaliza dados
            normalized_data = normalizer.normalize(raw_data)
            
            # Cria resposta
            product_data = ProductData(**normalized_data)
            
            # Salva snapshot no histórico
            save_product_snapshot(product_data)
            
            return index, ProductResponse(
                success=True,
                url=url_str,
                data=product_data,
                status=normalized_data.get('parse_status', 'ok')
            )
        
        finally:
            # Sempre libera permissão
            domain_limiter.release(url_str)
    
    except Exception as e:
        logger.exception(f"Erro ao processar {url_str}")
        return index, ProductResponse(
            success=False,
            url=url_str,
            status="error",
            error=str(e)
        )


class URLRequest(BaseModel):
    """Modelo de requisição com lista de URLs."""
    urls: List[HttpUrl]
    use_cache: bool = True
    force_refresh: bool = False  # Força atualização ignorando cache


class SearchRequest(BaseModel):
    """Modelo de requisição de busca."""
    query: str
    max_paginas: int = 1
    max_produtos: int = 20
    filters: Optional[Dict[str, Any]] = None


class ProductData(BaseModel):
    """Modelo de resposta com dados do produto."""
    plataforma: str
    titulo: Optional[str] = None
    preco: Optional[float] = None
    moeda: str = "BRL"
    imagem: Optional[str] = None
    frete_gratis: str = "unknown"
    texto_entrega: str = ""
    data_entrega: Optional[str] = None
    frete_gratis_detalhes: Optional[str] = None  # Ex: "FRETE GRÁTIS ACIMA DE R$ 19"
    data_entrega_detalhes: Optional[str] = None  # Ex: "Receba grátis segunda-feira"
    full_fulfillment: Optional[str] = None  # Ex: "Armazenado e enviado pelo FULL"
    loja_oficial: bool = False
    nota: Optional[float] = None
    num_avaliacoes: Optional[int] = None
    url_produto: str
    data_coleta: str
    # Novos campos extraídos do HTML
    preco_anterior: Optional[float] = None
    desconto_percentual: Optional[float] = None
    desconto_valor: Optional[float] = None
    parcelamento_numero: Optional[int] = None
    parcelamento_valor: Optional[float] = None
    parcelamento_juros: Optional[bool] = None
    preco_parcelado: Optional[float] = None  # Preço base para parcelamento (sem desconto)
    preco_total_parcelado: Optional[float] = None  # Total calculado (parcelas * valor_parcela)
    num_vendas: Optional[int] = None
    precisao_parcelamento: Optional[float] = None  # Precisão do valor de parcelamento (0-100%)
    # Campos de status de parsing
    parse_status: Literal["ok", "partial", "blocked", "error"] = "ok"
    missing_fields: List[str] = []


class ProductResponse(BaseModel):
    """Resposta com dados do produto ou erro."""
    success: bool
    url: str
    data: Optional[ProductData] = None
    error: Optional[str] = None
    status: Optional[str] = None  # "ok", "error", "partial"


class ComparisonResponse(BaseModel):
    """Resposta da comparação de preços."""
    total_urls: int
    successful: int
    failed: int
    products: List[ProductResponse]
    warnings: List[str] = []


def save_product_snapshot(product_data: ProductData) -> None:
    """
    Salva snapshot de preço do produto no histórico.
    Só salva se produto tem preço válido e não está bloqueado/erro.
    """
    try:
        # Só salva se tem preço válido e status ok/partial
        if (product_data.preco is not None and 
            product_data.preco > 0 and
            product_data.parse_status in ('ok', 'partial') and
            product_data.url_produto):
            
            price_history.save_snapshot(
                url=product_data.url_produto,
                plataforma=product_data.plataforma,
                titulo=product_data.titulo,
                preco=product_data.preco,
                moeda=product_data.moeda,
                data_coleta=product_data.data_coleta,
                parse_status=product_data.parse_status
            )
    except Exception as e:
        logger.warning(f"Erro ao salvar snapshot para {product_data.url_produto}: {e}")


@app.post("/compare", response_model=ComparisonResponse)
async def compare_prices(request: URLRequest):
    """
    Compara preços de múltiplas URLs usando processamento paralelo.
    
    Recebe uma lista de URLs de produtos e retorna dados estruturados
    para comparação de preços.
    """
    start_time = time.time()
    
    if not request.urls:
        raise HTTPException(status_code=400, detail="Lista de URLs não pode estar vazia")
    
    if len(request.urls) > 50:
        raise HTTPException(status_code=400, detail="Máximo de 50 URLs por requisição")
    
    total_urls = len(request.urls)
    results_dict = {}  # Dict para preservar ordem
    warnings = []
    
    # Processa URLs em paralelo com ThreadPoolExecutor
    max_workers = min(6, total_urls)  # Máximo 6 workers
    
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        # Submete todas as tarefas
        future_to_index = {
            executor.submit(
                process_single_url,
                str(url),
                idx,
                request.use_cache,
                request.force_refresh
            ): idx
            for idx, url in enumerate(request.urls)
        }
        
        # Coleta resultados conforme completam
        completed = 0
        for future in as_completed(future_to_index):
            try:
                index, result = future.result()
                results_dict[index] = result
                completed += 1
            except Exception as e:
                logger.exception(f"Erro ao processar URL no executor: {e}")
                index = future_to_index[future]
                results_dict[index] = ProductResponse(
                    success=False,
                    url=str(request.urls[index]),
                    status="error",
                    error=str(e)
                )
                completed += 1
    
    # Ordena resultados pela ordem original
    results = [results_dict[i] for i in range(total_urls)]
    
    # Conta resultados por status
    successful = sum(1 for r in results if r.success)
    failed = sum(1 for r in results if not r.success)
    blocked = sum(1 for r in results if r.status == "blocked")
    partial = sum(1 for r in results if r.status == "partial" or (r.success and r.data and r.data.parse_status == "partial"))
    error_count = sum(1 for r in results if r.status == "error" or (not r.success and r.status != "blocked"))
    
    # Calcula tempo total
    elapsed_time = time.time() - start_time
    
    # Log observabilidade
    logger.info(
        f"/compare: {total_urls} URLs processadas em {elapsed_time:.2f}s | "
        f"ok={successful} partial={partial} blocked={blocked} error={error_count} | "
        f"warnings={len(warnings)}"
    )
    
    # Adiciona warning se tempo limite (mais de 30s para muitas URLs)
    if elapsed_time > 30 and total_urls > 10:
        warnings.append(f"Tempo limite: resultado parcial ({elapsed_time:.1f}s)")
    
    return ComparisonResponse(
        total_urls=total_urls,
        successful=successful,
        failed=failed,
        products=results,
        warnings=warnings
    )


@app.get("/")
async def root():
    """Página inicial da interface web."""
    index_path = os.path.join(static_dir, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return {"message": "Interface web não encontrada. Acesse /docs para a documentação da API."}


@app.post("/search", response_model=ComparisonResponse)
async def search_products(request: SearchRequest):
    """
    Busca produtos em múltiplas plataformas (Mercado Livre e Amazon) por termo de busca.
    
    Recebe um termo de busca e retorna lista de produtos encontrados em ambas as plataformas.
    """
    start_time = time.time()
    
    if not request.query or not request.query.strip():
        raise HTTPException(status_code=400, detail="Termo de busca não pode estar vazio")
    
    if len(request.query) > 100:
        raise HTTPException(status_code=400, detail="Termo de busca muito longo (máximo 100 caracteres)")
    
    if request.max_produtos > 50:
        raise HTTPException(status_code=400, detail="Máximo de 50 produtos por busca")
    
    try:
        # Busca produtos em ambas as plataformas
        produtos_raw = []
        warnings = []
        
        # Busca no Mercado Livre
        try:
            produtos_ml = list_scraper.search(
                query=request.query.strip(),
                max_paginas=request.max_paginas,
                max_produtos=request.max_produtos,
                filters=request.filters or {}
            )
            produtos_raw.extend(produtos_ml)
            logger.info(f"Busca ML: {len(produtos_ml)} produtos encontrados")
        except Exception as e:
            error_msg = str(e)
            # Tenta extrair status code se existir
            if "403" in error_msg or "bloqueio" in error_msg.lower():
                warning_msg = f"Mercado Livre: Bloqueio detectado (403)"
            elif "429" in error_msg or "rate limit" in error_msg.lower():
                warning_msg = f"Mercado Livre: Rate limit excedido (429)"
            elif "status_code" in error_msg.lower() or "status" in error_msg.lower():
                # Tenta extrair código de status
                status_match = re.search(r'(\d{3})', error_msg)
                if status_match:
                    warning_msg = f"Mercado Livre: Erro HTTP {status_match.group(1)}"
                else:
                    warning_msg = f"Mercado Livre: {error_msg[:100]}"
            else:
                warning_msg = f"Mercado Livre: {error_msg[:100]}"
            warnings.append(warning_msg)
            logger.warning(f"Falha na busca do Mercado Livre: {error_msg}")
        
        # Busca na Amazon
        try:
            produtos_amazon, amazon_warning = list_scraper.search_amazon(
                query=request.query.strip(),
                max_paginas=request.max_paginas,
                max_produtos=request.max_produtos,
                filters=request.filters or {}
            )
            produtos_raw.extend(produtos_amazon)
            logger.info(f"Busca Amazon: {len(produtos_amazon)} produtos encontrados, blocked_detected={amazon_warning is not None}")
            
            # Adiciona warning se bloqueio foi detectado
            if amazon_warning:
                warnings.append(amazon_warning)
                logger.warning(f"Amazon bloqueada: {amazon_warning}")
        except Exception as e:
            error_msg = str(e)
            # Tenta extrair status code se existir
            if "403" in error_msg or "bloqueio" in error_msg.lower():
                warning_msg = f"Amazon: Bloqueio detectado (403)"
            elif "429" in error_msg or "rate limit" in error_msg.lower():
                warning_msg = f"Amazon: Rate limit excedido (429)"
            elif "status_code" in error_msg.lower() or "status" in error_msg.lower():
                # Tenta extrair código de status
                status_match = re.search(r'(\d{3})', error_msg)
                if status_match:
                    warning_msg = f"Amazon: Erro HTTP {status_match.group(1)}"
                else:
                    warning_msg = f"Amazon: {error_msg[:100]}"
            else:
                warning_msg = f"Amazon: {error_msg[:100]}"
            warnings.append(warning_msg)
            logger.warning(f"Falha na busca da Amazon: {error_msg}")
        
        # Adiciona warning se nenhum produto foi encontrado
        if not produtos_raw and not warnings:
            warnings.append("Nenhum produto encontrado em nenhuma plataforma")
        elif not produtos_raw:
            warnings.append("Nenhum produto encontrado após falhas nas plataformas")
        
        results = []
        successful = 0
        failed = 0
        
        # Separa produtos da Amazon que precisam de detalhamento
        produtos_amazon_detalhar = []
        outros_produtos = []
        
        for produto_raw in produtos_raw:
            if produto_raw.get('plataforma', '').startswith('amazon') and produto_raw.get('url_produto'):
                produtos_amazon_detalhar.append(produto_raw)
            else:
                outros_produtos.append(produto_raw)
        
        # Processa produtos da Amazon em paralelo (máximo 5) com DomainLimiter
        def detalhar_produto_amazon(produto_raw):
            """Detalha um produto da Amazon buscando página individual."""
            url_produto = produto_raw.get('url_produto', '')
            if not url_produto:
                return produto_raw
            
            try:
                # Adquire permissão do DomainLimiter
                domain_limiter.acquire(url_produto)
                
                try:
                    # Valores da listagem (para cálculo de precisão)
                    valor_listagem = produto_raw.get('parcelamento_valor')
                    
                    # Busca dados mais precisos da página individual (usa cache normal, não force_refresh)
                    html, fetch_error = fetch_with_retry(url_produto, use_cache=True, force_refresh=False)
                    
                    if html and not fetch_error:
                        dados_individuais = extractor.extract(url_produto, html)
                        valor_individual = dados_individuais.get('parcelamento_valor')
                        
                        # Calcula precisão baseada na diferença entre valores
                        if valor_listagem is not None and valor_individual is not None:
                            diferenca_absoluta = abs(valor_individual - valor_listagem)
                            valor_referencia = max(valor_individual, valor_listagem, 0.01)
                            diferenca_percentual = (diferenca_absoluta / valor_referencia) * 100
                            precisao = max(0, 100 - diferenca_percentual)
                            produto_raw['precisao_parcelamento'] = round(precisao, 2)
                        elif valor_individual is not None:
                            produto_raw['precisao_parcelamento'] = 100.0
                        else:
                            produto_raw['precisao_parcelamento'] = None
                        
                        # Atualiza com dados da página individual
                        if valor_individual is not None:
                            produto_raw['parcelamento_valor'] = valor_individual
                        
                        # Atualiza outros campos importantes
                        for field in ['preco_parcelado', 'preco_total_parcelado', 'parcelamento_juros', 
                                     'parcelamento_numero', 'preco', 'preco_anterior', 
                                     'desconto_percentual', 'desconto_valor']:
                            if dados_individuais.get(field) is not None:
                                produto_raw[field] = dados_individuais.get(field)
                
                finally:
                    domain_limiter.release(url_produto)
            
            except Exception as e:
                logger.warning(f"Erro ao detalhar produto Amazon {url_produto}: {e}")
                # Continua com dados da listagem
            
            return produto_raw
        
        # Processa produtos da Amazon em paralelo (máximo 5)
        if produtos_amazon_detalhar:
            max_amazon_workers = min(5, len(produtos_amazon_detalhar))
            with ThreadPoolExecutor(max_workers=max_amazon_workers) as executor:
                produtos_amazon_detalhar = list(executor.map(detalhar_produto_amazon, produtos_amazon_detalhar))
        
        # Combina todos os produtos
        todos_produtos = outros_produtos + produtos_amazon_detalhar
        
        # Normaliza cada produto
        for produto_raw in todos_produtos:
            try:
                normalized = normalizer.normalize(produto_raw)
                product_data = ProductData(**normalized)
                
                # Salva snapshot no histórico
                save_product_snapshot(product_data)
                
                results.append(ProductResponse(
                    success=True,
                    url=normalized.get('url_produto', ''),
                    data=product_data
                ))
                successful += 1
            except Exception as e:
                results.append(ProductResponse(
                    success=False,
                    url=produto_raw.get('url_produto', ''),
                    error=str(e)
                ))
                failed += 1
        
        # Calcula tempo total
        elapsed_time = time.time() - start_time
        
        # Conta resultados por status
        blocked = sum(1 for r in results if r.data and r.data.parse_status == "blocked")
        partial = sum(1 for r in results if r.data and r.data.parse_status == "partial")
        error_count = sum(1 for r in results if not r.success)
        
        # Log observabilidade
        logger.info(
            f"/search: query='{request.query}', {len(produtos_raw)} produtos em {elapsed_time:.2f}s | "
            f"ok={successful} partial={partial} blocked={blocked} error={error_count} | "
            f"warnings={len(warnings)}"
        )
        
        # Adiciona warning se tempo limite
        if elapsed_time > 20:
            warnings.append(f"Tempo limite: resultado parcial ({elapsed_time:.1f}s)")
        
        return ComparisonResponse(
            total_urls=len(produtos_raw),
            successful=successful,
            failed=failed,
            products=results,
            warnings=warnings
        )
    
    except Exception as e:
        logger.exception("Erro ao buscar produtos")
        raise HTTPException(status_code=500, detail=f"Erro ao buscar produtos: {str(e)}")


@app.get("/history")
async def get_price_history(url: str, limit: int = 30):
    """
    Retorna histórico de preços para uma URL.
    
    Args:
        url: URL do produto
        limit: Número máximo de registros (padrão: 30, máximo: 100)
    
    Returns:
        Lista de snapshots ordenados por data_coleta DESC
    """
    if not url or not url.strip():
        raise HTTPException(status_code=400, detail="URL não pode estar vazia")
    
    if limit > 100:
        limit = 100
    
    history = price_history.get_history(url, limit)
    
    return {
        "url": url,
        "total": len(history),
        "history": history
    }


@app.get("/health")
async def health_check():
    """Endpoint de health check."""
    return {"status": "ok", "cache_size": cache.size()}


@app.delete("/cache")
async def clear_cache(url: Optional[str] = None):
    """
    Limpa cache.
    
    Se 'url' for fornecida, limpa apenas essa URL.
    Caso contrário, limpa todo o cache.
    """
    if url:
        from urllib.parse import unquote
        from fetcher import Fetcher
        decoded_url = unquote(url)
        temp_fetcher = Fetcher()
        normalized_url = temp_fetcher._normalize_url(decoded_url)
        
        deleted = cache.delete(normalized_url)
        if deleted:
            return {"message": f"Cache removido para {normalized_url}", "cache_size": cache.size()}
        else:
            return {"message": f"URL não encontrada no cache: {normalized_url}", "cache_size": cache.size()}
    else:
        cache.clear()
        return {"message": "Cache limpo com sucesso", "cache_size": cache.size()}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

