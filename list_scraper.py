"""
Módulo de scraping de listagens do Mercado Livre.
Raspa resultados de busca e retorna lista de produtos.
"""
import re
import time
import random
import logging
from typing import List, Dict, Optional, Any, Tuple
from urllib.parse import urlparse, quote
from bs4 import BeautifulSoup
from fetcher import Fetcher
from datetime import datetime

logger = logging.getLogger(__name__)


class ListScraper:
    """Raspa listagens de busca do Mercado Livre."""
    
    def __init__(self):
        self.fetcher = Fetcher()
    
    def search(self, query: str, max_paginas: int = 1, max_produtos: int = 20, filters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """
        Busca produtos no Mercado Livre.
        
        Args:
            query: Termo de busca (ex: "iphone", "notebook")
            max_paginas: Número máximo de páginas para raspar
            max_produtos: Número máximo de produtos para retornar
            filters: Dicionário com filtros (minPrice, maxPrice, condition, freeShipping, full, sort, category, zipCode)
            
        Returns:
            Lista de dicionários com dados dos produtos
        """
        filters = filters or {}
        
        # Constrói URL de busca com filtros
        query_encoded = quote(query.lower().strip())
        base_url = f"https://lista.mercadolivre.com.br/{query_encoded}"
        
        # Adiciona parâmetros de filtro na URL
        # O Mercado Livre usa hash (#) com formato específico para alguns filtros
        # e query parameters para outros
        query_params = []
        hash_params = None  # Parâmetros no formato applied_filter_id=value (dict quando usado)
        
        # Preço mínimo/máximo - adiciona no hash (formato antigo ainda funciona)
        hash_parts_old = []
        if filters.get('minPrice'):
            hash_parts_old.append(f"_Desde_{int(filters['minPrice'])}")
        if filters.get('maxPrice'):
            hash_parts_old.append(f"_PriceRange_{int(filters['maxPrice'])}")
        
        # Condição (Novo/Usado/Recondicionado) - hash (formato antigo)
        condition_map = {
            'new': '_ITEM*CONDITION_2230280',
            'used': '_ITEM*CONDITION_2230281',
            'refurbished': '_ITEM*CONDITION_2230282'
        }
        if filters.get('condition') and isinstance(filters['condition'], list):
            for cond in filters['condition']:
                if cond in condition_map:
                    hash_parts_old.append(condition_map[cond])
        
        # Frete grátis - NOVO FORMATO (baseado no exemplo do ML)
        # Formato: applied_filter_id=shipping_cost_highlighted_free&applied_value_id=free
        if filters.get('freeShipping'):
            # Adiciona sufixo no path para frete grátis
            if '_CustoFrete_Gratis' not in base_url:
                # Adiciona o sufixo antes do hash/query params
                base_url = base_url.rstrip('/') + '_CustoFrete_Gratis_NoIndex_True'
            
            # Parâmetros do hash (serão URL encoded)
            hash_params_dict = {
                'applied_filter_id': 'shipping_cost_highlighted_free',
                'applied_filter_name': 'Custo de envio',
                'applied_filter_order': '2',
                'applied_value_id': 'free',
                'applied_value_name': 'Grátis',
                'applied_value_order': '1',
                'is_custom': 'false'
            }
            hash_params = hash_params_dict
        
        # Full (Enviado pelo Mercado Livre) - hash (formato antigo)
        if filters.get('full'):
            hash_parts_old.append('_FULL*SHIPPING_1')
        
        # Ordenação - query parameter
        sort_map = {
            'relevance': 'relevance',
            'price_asc': 'price_asc',
            'price_desc': 'price_desc'
        }
        if filters.get('sort') and filters['sort'] in sort_map:
            query_params.append(('orderId', sort_map[filters['sort']]))
        
        # CEP (afeta frete) - query parameter
        if filters.get('zipCode'):
            cep_clean = re.sub(r'\D', '', str(filters['zipCode']))
            if len(cep_clean) == 8:
                query_params.append(('zipcode', cep_clean))
        
        # Monta URL final
        url = base_url
        if query_params:
            from urllib.parse import urlencode
            url += '?' + urlencode(query_params)
        
        # Monta hash - prioriza formato novo (applied_filter_id) se disponível
        if hash_params and isinstance(hash_params, dict):
            # Formato novo: URL encoded no hash
            from urllib.parse import urlencode
            hash_value = urlencode(hash_params)
            url += '#' + hash_value
        elif hash_parts_old:
            # Formato antigo: separado por hífen
            url += '#' + '-'.join(hash_parts_old)
        
        # Log da URL gerada para debug
        if filters.get('freeShipping'):
            print(f"DEBUG: URL com filtro frete grátis: {url}")
        
        print(f"DEBUG: URL de busca com filtros: {url}")
        
        produtos = []
        next_url = url
        
        for pagina in range(max_paginas):
            try:
                # Busca HTML
                html = self.fetcher.fetch(next_url, use_cache=True)
                if not html:
                    break
                
                soup = BeautifulSoup(html, 'html.parser')
                
                # Encontra itens de produto - tenta vários seletores
                items = []
                
                # Seletores possíveis do Mercado Livre
                selectors = [
                    "li.ui-search-layout__item",
                    "ol.ui-search-layout__item > li",
                    ".ui-search-result",
                    "li[class*='ui-search']",
                    ".ui-search-item",
                    "article.ui-search-result",
                    "div.ui-search-result",
                ]
                
                for selector in selectors:
                    items = soup.select(selector)
                    if items:
                        print(f"Encontrados {len(items)} itens com seletor: {selector}")
                        break
                
                # Se ainda não encontrou, procura por estrutura comum
                if not items:
                    # Procura por links que parecem ser de produtos
                    all_links = soup.find_all('a', href=re.compile(r'/.*MLB\d+|/.*-[A-Z]{3}-\d+'))
                    if all_links:
                        # Cria itens fictícios a partir dos links
                        for link in all_links[:max_produtos]:
                            parent = link.find_parent(['li', 'div', 'article'])
                            if parent:
                                items.append(parent)
                        if items:
                            print(f"Encontrados {len(items)} itens via links")
                
                print(f"Processando {len(items)} itens encontrados...")
                for idx, item in enumerate(items):
                    if len(produtos) >= max_produtos:
                        break
                    
                    produto_data = self._extract_product_from_item(item, query, filters)
                    if produto_data and produto_data.get('url_produto'):
                        produtos.append(produto_data)
                        if len(produtos) % 5 == 0:
                            print(f"  Extraídos {len(produtos)} produtos...")
                
                print(f"Total de produtos extraídos: {len(produtos)}")
                
                # Procura próxima página
                next_a = soup.select_one(
                    "a.andes-pagination__link[title='Seguinte'], "
                    "a.andes-pagination__link[aria-label='Seguinte'], "
                    ".andes-pagination__button--next a"
                )
                
                if not next_a or len(produtos) >= max_produtos:
                    break
                
                next_url = next_a.get('href')
                if not next_url or next_url == next_url:
                    break
                
                # Rate limiting entre páginas
                time.sleep(random.uniform(1.5, 3.0))
                
            except Exception as e:
                print(f"Erro ao processar página {pagina + 1}: {e}")
                break
        
        return produtos
    
    def _extract_product_from_item(self, item, query: str, filters: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
        """Extrai dados de um item de produto da listagem."""
        try:
            data = {
                'plataforma': 'www.mercadolivre.com.br',
                'query_busca': query,
            }
            
            # Link do produto - PRIORIDADE 1
            link_el = None
            link_selectors = [
                "a.ui-search-link",
                "h2.ui-search-item__title a",
                "a[href*='MLB']",
                "a[href*='/produto/']",
                "a[href*='item.mercadolivre.com.br']",
            ]
            
            for selector in link_selectors:
                link_el = item.select_one(selector)
                if link_el:
                    break
            
            # Se não encontrou, procura qualquer link com padrão MLB
            if not link_el:
                all_links = item.find_all('a', href=re.compile(r'.*MLB\d+|.*item\.mercadolivre'))
                if all_links:
                    link_el = all_links[0]
            
            if not link_el:
                return None
            
            href = link_el.get('href', '')
            if not href or 'MLB' not in href:
                return None
            
            # Garante URL completa
            if href.startswith('/'):
                href = 'https://www.mercadolivre.com.br' + href
            elif not href.startswith('http'):
                return None
            
            data['url_produto'] = href
            
            # Título
            title_selectors = [
                "h2.ui-search-item__title",
                ".ui-search-item__title",
                "h2",
                "a[href*='MLB']",
            ]
            
            for selector in title_selectors:
                title_el = item.select_one(selector)
                if title_el:
                    title_text = title_el.get_text(strip=True)
                    if title_text and len(title_text) > 5:
                        data['titulo'] = title_text
                        break
            
            # Se não encontrou título, tenta do link
            if 'titulo' not in data or not data['titulo']:
                data['titulo'] = link_el.get_text(strip=True) or f"Produto {query}"
            
            # Preço - IMPORTANTE: Prioriza preço atual (não riscado)
            # Primeiro, procura preço que NÃO está dentro de elemento riscado
            price_selectors = [
                ".ui-search-price__second-line .andes-money-amount__fraction:not(s .andes-money-amount__fraction)",
                ".ui-search-price .andes-money-amount__fraction:not(s .andes-money-amount__fraction)",
                ".andes-money-amount__fraction:not(s .andes-money-amount__fraction)",
                ".ui-search-price__second-line .price-tag-fraction:not(s .price-tag-fraction)",
                ".ui-search-price .price-tag-fraction:not(s .price-tag-fraction)",
                ".price-tag-fraction:not(s .price-tag-fraction)",
                "[class*='price'] [class*='fraction']:not(s [class*='fraction'])",
            ]
            
            price_el = None
            for selector in price_selectors:
                price_el = item.select_one(selector)
                if price_el:
                    # Verifica se não está dentro de elemento riscado
                    if price_el.find_parent('s') or 'previous' in str(price_el.get('class', [])).lower():
                        continue
                    break
            
            # Se não encontrou, tenta seletores genéricos mas verifica se não está riscado
            if not price_el:
                for selector in [".andes-money-amount__fraction", ".price-tag-fraction"]:
                    price_el = item.select_one(selector)
                    if price_el:
                        # Verifica se não está dentro de elemento riscado
                        if price_el.find_parent('s') or 'previous' in str(price_el.get('class', [])).lower():
                            continue
                        break
            
            if price_el:
                frac = price_el.get_text(strip=True)
                
                # Procura centavos no mesmo container do preço atual
                parent = price_el.find_parent(['div', 'span', 'li'])
                cents_el = None
                if parent:
                    cents_el = parent.select_one(
                        ".andes-money-amount__cents, "
                        ".price-tag-cents, "
                        "[class*='cents']"
                    )
                if not cents_el:
                    cents_el = item.select_one(
                        ".andes-money-amount__cents, "
                        ".price-tag-cents, "
                        "[class*='cents']"
                    )
                cents = cents_el.get_text(strip=True) if cents_el else "00"
                
                # Procura moeda
                currency_el = item.select_one(
                    ".andes-money-amount__currency-symbol, "
                    ".price-tag-symbol, "
                    "[class*='currency']"
                )
                moeda = currency_el.get_text(strip=True) if currency_el else "R$"
                
                # Limpa e converte
                frac = re.sub(r'[^\d]', '', frac) or "0"
                cents = re.sub(r'[^\d]', '', cents) or "00"
                
                # Limita centavos a 2 dígitos
                if len(cents) > 2:
                    cents = cents[:2]
                elif len(cents) == 1:
                    cents = cents + "0"
                
                try:
                    frac_int = int(frac) if frac else 0
                    cents_int = int(cents) if cents else 0
                    preco = float(f"{frac_int}.{cents_int:02d}")
                    # Validação: preço deve ser razoável (entre 1 e 1000000)
                    if 1 <= preco <= 1000000:
                        data['preco'] = preco
                        data['moeda'] = 'BRL' if 'R$' in moeda or 'BRL' in moeda else moeda
                except (ValueError, OverflowError):
                    pass
            
            # Imagem
            img_selectors = ["img", ".ui-search-result-image__element", "img[data-src]", "img[src]"]
            for selector in img_selectors:
                img_el = item.select_one(selector)
                if img_el:
                    for attr in ['data-src', 'data-lazy-src', 'src', 'data-zoom']:
                        img_url = img_el.get(attr)
                        if img_url:
                            if img_url.startswith('http'):
                                data['imagem'] = img_url
                                break
                            elif img_url.startswith('//'):
                                data['imagem'] = 'https:' + img_url
                                break
                    if 'imagem' in data:
                        break
            
            # Frete - procura em múltiplos lugares
            shipping_el = item.select_one(
                ".ui-search-item__shipping, "
                ".ui-search-item__shipping-label, "
                ".ui-search-item__group__element--shipping, "
                "[class*='shipping'], "
                "[class*='frete'], "
                "[class*='envio']"
            )
            
            # Se o filtro de frete grátis está ativo, assume que todos têm frete grátis
            if filters and filters.get('freeShipping'):
                data['frete_gratis'] = 'true'
                data['texto_entrega'] = 'Frete grátis'
            elif shipping_el:
                shipping_text = shipping_el.get_text(strip=True)
                data['texto_entrega'] = shipping_text
                
                # Interpreta frete
                shipping_lower = shipping_text.lower()
                if 'grátis' in shipping_lower or 'gratis' in shipping_lower or 'free' in shipping_lower:
                    data['frete_gratis'] = 'true'
                elif 'frete' in shipping_lower or 'envio' in shipping_lower:
                    data['frete_gratis'] = 'false'
                else:
                    data['frete_gratis'] = 'unknown'
            else:
                # Procura no texto geral do item
                item_text = item.get_text().lower()
                if 'frete grátis' in item_text or 'frete gratis' in item_text or 'envio grátis' in item_text:
                    data['frete_gratis'] = 'true'
                    data['texto_entrega'] = 'Frete grátis'
                elif 'frete' in item_text or 'envio' in item_text:
                    data['frete_gratis'] = 'false'
                else:
                    data['frete_gratis'] = 'unknown'
                data['texto_entrega'] = ''
            
            # Avaliações (se disponível)
            rating_el = item.select_one(".ui-search-reviews__rating")
            if rating_el:
                rating_text = rating_el.get_text(strip=True)
                rating_match = re.search(r'(\d+[.,]\d+|\d+)', rating_text)
                if rating_match:
                    try:
                        data['nota'] = float(rating_match.group(1).replace(',', '.'))
                    except ValueError:
                        pass
            
            # Preço anterior (riscado) - na listagem
            previous_price_el = item.select_one("s.andes-money-amount--previous, .andes-money-amount--previous")
            if previous_price_el:
                prev_text = previous_price_el.get_text(strip=True)
                if prev_text:
                    # Remove R$ e espaços, mantém apenas números
                    prev_clean = re.sub(r'[^\d,.]', '', prev_text)
                    if prev_clean:
                        try:
                            # Tenta parsear como float
                            prev_clean = prev_clean.replace('.', '').replace(',', '.')
                            data['preco_anterior'] = float(prev_clean)
                        except ValueError:
                            pass
            
            # Desconto - procura por badge de desconto
            discount_el = item.select_one("[class*='discount'], [class*='off'], [class*='desconto']")
            if discount_el:
                discount_text = discount_el.get_text(strip=True)
                discount_match = re.search(r'(\d+)\s*%', discount_text, re.IGNORECASE)
                if discount_match:
                    try:
                        data['desconto_percentual'] = float(discount_match.group(1))
                    except ValueError:
                        pass
            
            # Calcula desconto_valor se temos preço anterior e atual
            if data.get('preco_anterior') and data.get('preco'):
                data['desconto_valor'] = data['preco_anterior'] - data['preco']
                if not data.get('desconto_percentual'):
                    data['desconto_percentual'] = round((data['desconto_valor'] / data['preco_anterior']) * 100, 1)
            
            # Parcelamento - procura por texto de parcelas
            # IMPORTANTE: Na listagem pode mostrar valores aproximados, então precisamos ser mais cuidadosos
            installment_el = item.select_one("[class*='installment'], [class*='parcela']")
            if installment_el:
                installment_text = installment_el.get_text(strip=True)
                
                # Procura padrão "21x de R$ 250,22" ou "21x R$ 250,22"
                # Padrão mais específico: número + "x" + "de" (opcional) + "R$" + valor com centavos
                parcelas_match = re.search(r'(\d+)\s*x', installment_text, re.IGNORECASE)
                if parcelas_match:
                    try:
                        data['parcelamento_numero'] = int(parcelas_match.group(1))
                    except ValueError:
                        pass
                
                # Procura valor da parcela - procura por padrão mais específico com centavos
                # Prioriza padrão "R$ 250,22" ou "R$ 250.22" (com vírgula ou ponto decimal)
                valor_match = re.search(r'R\$\s*(\d{1,3}(?:\.\d{3})*(?:[.,]\d{2})?)', installment_text)
                if valor_match:
                    valor_str = valor_match.group(1)
                    # Remove pontos (milhares) e substitui vírgula por ponto (decimal)
                    valor_str = valor_str.replace('.', '').replace(',', '.')
                    try:
                        valor_parcela = float(valor_str)
                        # Validação: valor da parcela deve ser razoável (entre 1 e 10000)
                        if 1 <= valor_parcela <= 10000:
                            data['parcelamento_valor'] = valor_parcela
                    except ValueError:
                        pass
                
                # Se não encontrou valor específico, tenta calcular do preço parcelado
                # Procura por preço parcelado no texto (ex: "ou R$ 5.254,62 em 21x")
                preco_parcelado_match = re.search(r'(?:ou|em)\s*R\$\s*(\d+(?:\.\d{3})*(?:[.,]\d{2})?)', installment_text, re.IGNORECASE)
                if preco_parcelado_match:
                    preco_parcelado_str = preco_parcelado_match.group(1).replace('.', '').replace(',', '.')
                    try:
                        preco_parcelado = float(preco_parcelado_str)
                        if 1 <= preco_parcelado <= 1000000:
                            data['preco_parcelado'] = preco_parcelado
                            # Se temos número de parcelas e preço parcelado, calcula valor da parcela
                            if data.get('parcelamento_numero') and not data.get('parcelamento_valor'):
                                data['parcelamento_valor'] = round(preco_parcelado / data['parcelamento_numero'], 2)
                    except ValueError:
                        pass
                
                # Verifica se tem juros
                if 'sem juros' in installment_text.lower() or 'sem juro' in installment_text.lower():
                    data['parcelamento_juros'] = False
                elif 'juros' in installment_text.lower():
                    data['parcelamento_juros'] = True
            
            # Calcula preço total parcelado e valida valor da parcela
            if data.get('parcelamento_numero'):
                # Se temos preço parcelado, calcula valor da parcela corretamente
                if data.get('preco_parcelado'):
                    valor_calculado = round(data['preco_parcelado'] / data['parcelamento_numero'], 2)
                    # Se o valor extraído está muito diferente do calculado, usa o calculado (mais confiável)
                    if data.get('parcelamento_valor'):
                        diferenca = abs(data['parcelamento_valor'] - valor_calculado)
                        # Se a diferença for maior que 10% ou maior que 50 reais, usa o valor calculado
                        if diferenca > 50 or (data['parcelamento_valor'] > 0 and diferenca / data['parcelamento_valor'] > 0.1):
                            data['parcelamento_valor'] = valor_calculado
                    else:
                        data['parcelamento_valor'] = valor_calculado
                    data['preco_total_parcelado'] = round(data['parcelamento_numero'] * data['parcelamento_valor'], 2)
                elif data.get('parcelamento_valor'):
                    # Se não temos preço parcelado mas temos valor da parcela, calcula o total
                    data['preco_total_parcelado'] = round(data['parcelamento_numero'] * data['parcelamento_valor'], 2)
                    data['preco_parcelado'] = data['preco_total_parcelado']
            
            # Número de vendas - procura por "+100 vendidos"
            sales_text = item.get_text()
            sales_match = re.search(r'(?:mais\s+de|mais\s+que|\+)\s*(\d+)', sales_text, re.IGNORECASE)
            if sales_match:
                try:
                    data['num_vendas'] = int(sales_match.group(1))
                except ValueError:
                    pass
            
            # Data de coleta
            data['data_coleta'] = datetime.now().isoformat()
            
            # Loja oficial - procura por badges ou textos indicativos
            official_indicators = [
                '[class*="official"]',
                '[class*="oficial"]',
                '[class*="verified"]',
                '[class*="verificado"]',
                '.ui-search-official-store',
                '.ui-search-item__official-store',
            ]
            
            data['loja_oficial'] = False
            for selector in official_indicators:
                official_el = item.select_one(selector)
                if official_el:
                    data['loja_oficial'] = True
                    break
            
            # Se não encontrou por seletor, procura por texto
            if not data['loja_oficial']:
                item_text = item.get_text().lower()
                if any(term in item_text for term in ['loja oficial', 'official store', 'distribuidor autorizado', 'vendedor oficial']):
                    data['loja_oficial'] = True
            
            data['data_entrega'] = None
            data['num_avaliacoes'] = None
            
            return data
            
        except Exception as e:
            print(f"Erro ao extrair produto: {e}")
            return None
    
    def _detect_amazon_blocked(self, html: str, soup: BeautifulSoup, url: str) -> Tuple[bool, Optional[str]]:
        """
        Detecta se a página da Amazon está bloqueada (captcha, robot check, etc).
        
        Args:
            html: HTML da página
            soup: BeautifulSoup object da página
            url: URL que foi buscada
            
        Returns:
            Tuple (is_blocked, reason) onde:
            - is_blocked: True se bloqueado, False caso contrário
            - reason: Mensagem explicando o bloqueio (None se não bloqueado)
        """
        html_lower = html.lower()
        page_text = soup.get_text().lower() if soup else ''
        
        # Padrões específicos de bloqueio/captcha da Amazon
        blocked_patterns = [
            'robot check',
            'captcha',
            'enter the characters you see below',
            'not a robot',
            'sorry, we just need to make sure you\'re not a robot',
            'sorry, we just need to make sure you are not a robot',
            'try different image',
            'type the characters',
            'prove you are human',
            'unusual traffic',
            'to discuss automated access',
        ]
        
        # Verifica padrões no HTML e texto
        for pattern in blocked_patterns:
            if pattern in html_lower or pattern in page_text:
                return True, f"Captcha detectado: '{pattern}'"
        
        # Verifica se o container principal de resultados não existe
        # Seletores principais de resultados da Amazon
        main_containers = [
            '[data-component-type="s-search-result"]',
            '.s-result-item',
            '[data-asin]',  # Atributo data-asin presente em produtos
            '.s-main-slot',  # Container principal de resultados
        ]
        
        has_results = False
        for selector in main_containers:
            if soup.select(selector):
                has_results = True
                break
        
        # Se não encontrou resultados E a página não é vazia (tem conteúdo)
        if not has_results and len(html) > 1000:  # Página tem conteúdo mas sem resultados
            # Verifica se é página de erro ou bloqueio
            error_indicators = [
                'no results',
                'nenhum resultado',
                'try again',
                'tente novamente',
                'error',
                'erro',
            ]
            
            # Se tem indicadores de erro, provavelmente é bloqueio
            for indicator in error_indicators:
                if indicator in html_lower or indicator in page_text:
                    return True, "Container de resultados não encontrado (possível bloqueio)"
        
        # Verifica títulos de página que indicam bloqueio
        title = soup.find('title')
        if title:
            title_text = title.get_text().lower()
            if any(word in title_text for word in ['captcha', 'robot', 'blocked', 'bloqueado']):
                return True, f"Título indica bloqueio: '{title_text[:50]}'"
        
        return False, None
    
    def search_amazon(self, query: str, max_paginas: int = 1, max_produtos: int = 20, filters: Optional[Dict[str, Any]] = None) -> tuple[List[Dict[str, Any]], Optional[str]]:
        """
        Busca produtos na Amazon.
        
        Args:
            query: Termo de busca (ex: "iphone", "notebook")
            max_paginas: Número máximo de páginas para raspar
            max_produtos: Número máximo de produtos para retornar
            filters: Dicionário com filtros (minPrice, maxPrice, etc.)
            
        Returns:
            Tuple (produtos, warning) onde:
            - produtos: Lista de dicionários com dados dos produtos
            - warning: Mensagem de warning se bloqueio detectado, None caso contrário
        """
        filters = filters or {}
        produtos = []
        
        # Constrói URL de busca da Amazon
        query_encoded = quote(query.lower().strip())
        base_url = f"https://www.amazon.com.br/s?k={query_encoded}"
        
        # Adiciona filtros de preço se existirem
        query_params = []
        if filters.get('minPrice'):
            query_params.append(('rh', f"p_36:{int(filters['minPrice'])}00-"))
        if filters.get('maxPrice'):
            if query_params and 'rh' in query_params[-1][0]:
                # Adiciona ao mesmo parâmetro rh
                query_params[-1] = ('rh', query_params[-1][1] + f"{int(filters['maxPrice'])}00")
            else:
                query_params.append(('rh', f"p_36:-{int(filters['maxPrice'])}00"))
        
        if query_params:
            from urllib.parse import urlencode
            base_url += '&' + urlencode(query_params)
        
        next_url = base_url
        
        for pagina in range(max_paginas):
            try:
                # Busca HTML
                html = self.fetcher.fetch(next_url, use_cache=True)
                if not html:
                    break
                
                soup = BeautifulSoup(html, 'html.parser')
                
                # DETECÇÃO DE BLOQUEIO/CAPTCHA
                is_blocked, block_reason = self._detect_amazon_blocked(html, soup, next_url)
                if is_blocked:
                    warning_msg = f"Amazon indisponível (captcha/bloqueio): {block_reason}"
                    print(f"[AMAZON BLOCKED] Query: {query}, URL: {next_url}, Reason: {block_reason}, blocked_detected=true")
                    logger.warning(f"Amazon bloqueada para query '{query}', URL: {next_url}, Reason: {block_reason}, blocked_detected=true")
                    return [], warning_msg
                
                # Encontra itens de produto na Amazon
                items = soup.select('[data-component-type="s-search-result"]')
                
                if not items:
                    # Tenta seletores alternativos
                    items = soup.select('.s-result-item')
                
                print(f"Encontrados {len(items)} itens na Amazon")
                
                for idx, item in enumerate(items):
                    if len(produtos) >= max_produtos:
                        break
                    
                    produto_data = self._extract_product_from_amazon_item(item, query, filters)
                    if produto_data and produto_data.get('url_produto'):
                        produtos.append(produto_data)
                        if len(produtos) % 5 == 0:
                            print(f"  Extraídos {len(produtos)} produtos da Amazon...")
                
                print(f"Total de produtos extraídos da Amazon: {len(produtos)}")
                
                # Procura próxima página
                next_a = soup.select_one('a.s-pagination-next')
                if not next_a or len(produtos) >= max_produtos:
                    break
                
                next_href = next_a.get('href')
                if next_href:
                    if next_href.startswith('/'):
                        next_url = 'https://www.amazon.com.br' + next_href
                    elif next_href.startswith('http'):
                        next_url = next_href
                    else:
                        break
                else:
                    break
                
                # Rate limiting entre páginas
                time.sleep(random.uniform(2.0, 4.0))
                
            except Exception as e:
                print(f"Erro ao processar página {pagina + 1} da Amazon: {e}")
                logger.error(f"Erro ao processar página {pagina + 1} da Amazon: {e}")
                break
        
        return produtos, None
    
    def _extract_product_from_amazon_item(self, item, query: str, filters: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
        """Extrai dados de um item de produto da listagem da Amazon."""
        try:
            data = {
                'plataforma': 'www.amazon.com.br',
                'query_busca': query,
            }
            
            # Link do produto
            link_el = item.select_one('h2 a, .s-title-instructions-style a, a[href*="/dp/"], a[href*="/gp/product/"]')
            if not link_el:
                # Tenta encontrar qualquer link com padrão de produto
                all_links = item.find_all('a', href=re.compile(r'/dp/[A-Z0-9]+|/gp/product/[A-Z0-9]+'))
                if all_links:
                    link_el = all_links[0]
            
            if not link_el:
                return None
            
            href = link_el.get('href', '')
            if not href:
                return None
            
            # Garante URL completa
            if href.startswith('/'):
                href = 'https://www.amazon.com.br' + href
            elif not href.startswith('http'):
                return None
            
            # Remove parâmetros de tracking e normaliza URL
            if '/dp/' in href:
                dp_match = re.search(r'/dp/([A-Z0-9]+)', href)
                if dp_match:
                    href = f"https://www.amazon.com.br/dp/{dp_match.group(1)}"
            elif '/gp/product/' in href:
                gp_match = re.search(r'/gp/product/([A-Z0-9]+)', href)
                if gp_match:
                    href = f"https://www.amazon.com.br/dp/{gp_match.group(1)}"
            
            data['url_produto'] = href
            
            # Título - múltiplos seletores
            title_selectors = [
                'h2 a span',
                'h2 a',
                '.s-title-instructions-style a span',
                'a[href*="/dp/"] span',
                'a[href*="/gp/product/"] span',
            ]
            
            title_text = None
            for selector in title_selectors:
                title_el = item.select_one(selector)
                if title_el:
                    title_text = title_el.get_text(strip=True)
                    if title_text and len(title_text) > 5:
                        break
            
            if not title_text:
                title_text = link_el.get_text(strip=True)
            
            if title_text and len(title_text) > 5:
                data['titulo'] = title_text
            
            # Preço - melhorado com múltiplos seletores
            price_selectors = [
                '.a-price .a-offscreen',
                '.a-price-whole',
                '.a-price[data-a-color="base"] .a-offscreen',
                '[data-a-color="price"] .a-offscreen',
                '.a-price .a-price-whole',
                '.a-price-range .a-offscreen',
            ]
            
            price_el = None
            price_text = None
            for selector in price_selectors:
                price_el = item.select_one(selector)
                if price_el:
                    price_text = price_el.get_text(strip=True)
                    # Verifica se não está vazio e não é preço anterior
                    if price_text and 'a-text-price' not in str(price_el.get('class', [])):
                        break
            
            # Se não encontrou, tenta pegar do atributo data-a-price
            if not price_text:
                price_el = item.select_one('[data-a-price]')
                if price_el:
                    price_text = price_el.get('data-a-price', '')
            
            if price_text:
                # Remove R$ e espaços, mantém apenas números
                price_clean = re.sub(r'[^\d,.]', '', price_text)
                if price_clean:
                    try:
                        # Formato brasileiro: vírgula como decimal
                        price_clean = price_clean.replace('.', '').replace(',', '.')
                        preco = float(price_clean)
                        if 1 <= preco <= 1000000:
                            data['preco'] = preco
                            data['moeda'] = 'BRL'
                    except (ValueError, OverflowError):
                        pass
            
            # Preço anterior (riscado) - melhorado
            previous_price_selectors = [
                '.a-price.a-text-price .a-offscreen',
                '.a-price.a-text-strike .a-offscreen',
                '[data-a-strike="true"] .a-offscreen',
                '.a-text-strike .a-offscreen',
            ]
            
            for selector in previous_price_selectors:
                previous_price_el = item.select_one(selector)
                if previous_price_el:
                    prev_text = previous_price_el.get_text(strip=True)
                    if prev_text:
                        prev_clean = re.sub(r'[^\d,.]', '', prev_text)
                        if prev_clean:
                            try:
                                prev_clean = prev_clean.replace('.', '').replace(',', '.')
                                preco_anterior = float(prev_clean)
                                if 1 <= preco_anterior <= 1000000:
                                    data['preco_anterior'] = preco_anterior
                                    break
                            except ValueError:
                                pass
            
            # Calcula desconto se tiver preço anterior e atual
            if data.get('preco_anterior') and data.get('preco'):
                data['desconto_valor'] = data['preco_anterior'] - data['preco']
                data['desconto_percentual'] = round((data['desconto_valor'] / data['preco_anterior']) * 100, 1)
            
            # Parcelamento - procura por padrões de parcelas (melhorado baseado na página real)
            # Na página de resultados, o parcelamento aparece como: "ou em até 12x de R$ 358,24 sem juros"
            installment_selectors = [
                '.a-section.a-spacing-none.a-spacing-top-mini',
                '.a-text-price',
                '[class*="installment"]',
                '[class*="parcela"]',
                '[class*="a-size-base"]',
                '.a-row',
                '.a-price-symbol',
                '[data-a-color="secondary"]',
            ]
            
            installment_text = None
            installment_element = None
            
            # Primeiro tenta seletores específicos
            # PRIORIDADE: Procura primeiro por padrão "em até 12x R$" (sem "de") que é mais comum
            for selector in installment_selectors:
                elements = item.select(selector)
                for el in elements:
                    text = el.get_text(strip=True)
                    # PRIORIDADE 1: Procura padrão "em até 12x R$" (sem "de")
                    if re.search(r'em\s+até\s+\d+\s*x\s*R\$\s*\d+', text, re.IGNORECASE):
                        installment_text = text
                        installment_element = el
                        break
                    # PRIORIDADE 2: Procura padrão "12x R$" (sem "de")
                    elif re.search(r'\d+\s*x\s*R\$\s*\d+', text, re.IGNORECASE):
                        if not installment_text:  # Só usa se não encontrou o padrão prioritário
                            installment_text = text
                            installment_element = el
                    # PRIORIDADE 3: Procura padrão "12x de R$" (com "de")
                    elif re.search(r'\d+\s*x\s*de\s*R\$\s*\d+', text, re.IGNORECASE):
                        if not installment_text:  # Só usa se não encontrou os padrões prioritários
                            installment_text = text
                            installment_element = el
                if installment_text and 'em até' in installment_text.lower():
                    # Se encontrou o padrão prioritário, para aqui
                    break
            
            # Se não encontrou, procura no texto geral do item (área de preço)
            if not installment_text:
                # Procura na área de preço especificamente
                price_section = item.select_one('.a-price-section, [class*="price"]')
                if price_section:
                    price_section_text = price_section.get_text()
                    if re.search(r'\d+\s*x\s*(?:de\s*)?R\$\s*\d+', price_section_text, re.IGNORECASE) or re.search(r'em\s+até\s+\d+\s*x', price_section_text, re.IGNORECASE):
                        installment_text = price_section_text
                        installment_element = price_section
                
                # Se ainda não encontrou, procura em todo o item
                if not installment_text:
                    item_text = item.get_text()
                    # Procura padrões mais amplos
                    installment_patterns = [
                        r'(\d+)\s*x\s*(?:de\s*)?R\$\s*(\d+(?:\.\d{3})*(?:[.,]\d{2})?)',
                        r'em\s+até\s+(\d+)\s*x\s*(?:de\s*)?R\$\s*(\d+(?:\.\d{3})*(?:[.,]\d{2})?)',
                        r'(\d+)\s*vezes\s*(?:de\s*)?R\$\s*(\d+(?:\.\d{3})*(?:[.,]\d{2})?)',
                    ]
                    
                    for pattern in installment_patterns:
                        installment_match = re.search(pattern, item_text, re.IGNORECASE)
                        if installment_match:
                            installment_text = item_text
                            break
            
            if installment_text:
                # Extrai número de parcelas - múltiplos padrões
                parcelas_patterns = [
                    r'(\d+)\s*x\s',
                    r'em\s+até\s+(\d+)\s*x',
                    r'(\d+)\s*vezes',
                ]
                
                for pattern in parcelas_patterns:
                    parcelas_match = re.search(pattern, installment_text, re.IGNORECASE)
                    if parcelas_match:
                        try:
                            data['parcelamento_numero'] = int(parcelas_match.group(1))
                            break
                        except (ValueError, IndexError):
                            pass
                
                # Extrai valor da parcela - múltiplos padrões (melhorado para formato brasileiro)
                # Padrão: "12x de R$ 358,24" ou "em até 12x R$ 257,99 sem juros"
                # IMPORTANTE: O valor da parcela deve vir DEPOIS do "x de" ou "x"
                # PRIORIDADE: Padrões mais específicos primeiro
                # IMPORTANTE: Na Amazon, o formato pode ser "em até 12x R$ 257,99" (sem "de") ou "em até 12x de R$ 257,91" (com "de")
                # Priorizamos o padrão sem "de" que geralmente é mais preciso
                valor_patterns = [
                    r'em\s+até\s+\d+\s*x\s*R\$\s*(\d{1,3}(?:\.\d{3})*(?:[.,]\d{2})?)\s*(?:sem|com)',  # "Em até 12x R$ 257,99 sem juros" (PRIORIDADE 1 - sem "de")
                    r'(\d+)\s*x\s*R\$\s*(\d{1,3}(?:\.\d{3})*(?:[.,]\d{2})?)\s*(?:sem|com)',  # "12x R$ 257,99 sem juros" (PRIORIDADE 2 - sem "de")
                    r'em\s+até\s+\d+\s*x\s*de\s*R\$\s*(\d{1,3}(?:\.\d{3})*(?:[.,]\d{2})?)\s*(?:sem|com)',  # "Em até 12x de R$ 257,91 sem juros" (PRIORIDADE 3 - com "de")
                    r'(\d+)\s*x\s*de\s*R\$\s*(\d{1,3}(?:\.\d{3})*(?:[.,]\d{2})?)\s*(?:sem|com|/mês)',  # "12x de R$ 358,24 sem juros" (PRIORIDADE 4 - com "de")
                    r'(\d+)\s*x\s*(?:de\s*)?R\$\s*(\d{1,3}(?:\.\d{3})*(?:[.,]\d{2})?)',  # "12x de R$ 358,24" (PRIORIDADE 5 - fallback)
                ]
                
                for pattern in valor_patterns:
                    valor_match = re.search(pattern, installment_text, re.IGNORECASE)
                    if valor_match:
                        # Se tem 2 grupos, o segundo é o valor da parcela
                        if len(valor_match.groups()) == 2:
                            valor_str = valor_match.group(2)
                        elif len(valor_match.groups()) == 1:
                            # Se só tem 1 grupo, é o valor (padrão "em até Xx R$ Y")
                            valor_str = valor_match.group(1)
                        else:
                            # Se não tem grupos, ignora
                            continue
                        
                        # Remove pontos de milhar e substitui vírgula por ponto decimal
                        valor_str = valor_str.replace('.', '').replace(',', '.')
                        try:
                            valor_parcela = float(valor_str)
                            # Validação: valor da parcela deve ser menor que o preço à vista
                            # E deve estar em um range razoável (entre 1 e 10000)
                            if 1 <= valor_parcela <= 10000:
                                # Se tem preço à vista, valida que a parcela é menor
                                if data.get('preco'):
                                    if valor_parcela < data['preco']:
                                        data['parcelamento_valor'] = valor_parcela
                                        break
                                    else:
                                        # Valor inválido (parcela >= preço), ignora
                                        continue
                                else:
                                    # Não tem preço para validar, aceita
                                    data['parcelamento_valor'] = valor_parcela
                                    break
                        except ValueError:
                            pass
                
                # Extrai preço parcelado total (ex: "ou R$ 4.298,90 em 12x")
                # IMPORTANTE: Na Amazon, o formato é "ou R$ 4.298,90 em até 12x de R$ 358,26 sem juros"
                # O preço parcelado é o valor TOTAL, não o valor da parcela
                preco_parcelado_patterns = [
                    r'(?:ou|em)\s+R\$\s*(\d{1,3}(?:\.\d{3})*(?:[.,]\d{2})?)\s+em\s+(?:até\s+)?\d+\s*x',  # "ou R$ 4.298,90 em 12x"
                    r'R\$\s*(\d{1,3}(?:\.\d{3})*(?:[.,]\d{2})?)\s+em\s+(?:até\s+)?\d+\s*x',  # "R$ 4.298,90 em 12x"
                ]
                
                for pattern in preco_parcelado_patterns:
                    preco_match = re.search(pattern, installment_text, re.IGNORECASE)
                    if preco_match:
                        preco_str = preco_match.group(1)
                        # Remove pontos de milhar e substitui vírgula por ponto decimal
                        preco_str = preco_str.replace('.', '').replace(',', '.')
                        try:
                            preco_parcelado = float(preco_str)
                            # Validação: preço parcelado deve ser maior que o preço à vista (geralmente)
                            # Mas pode ser igual em alguns casos
                            if 1 <= preco_parcelado <= 1000000:
                                # Se o preço parcelado é muito maior que o preço à vista (mais de 2x), pode estar errado
                                if data.get('preco') and preco_parcelado > data['preco'] * 2:
                                    # Pode ser que capturou o valor errado, tenta validar
                                    # Se tem valor da parcela, valida: preco_parcelado deve ser aproximadamente parcelamento_numero * parcelamento_valor
                                    if data.get('parcelamento_numero') and data.get('parcelamento_valor'):
                                        valor_esperado = data['parcelamento_numero'] * data['parcelamento_valor']
                                        diferenca = abs(preco_parcelado - valor_esperado)
                                        # Se a diferença for muito grande (mais de 10%), pode estar errado
                                        if diferenca > valor_esperado * 0.1:
                                            # Usa o valor calculado em vez do capturado
                                            preco_parcelado = valor_esperado
                                
                                data['preco_parcelado'] = preco_parcelado
                                # Se não tem valor da parcela, calcula
                                if data.get('parcelamento_numero') and not data.get('parcelamento_valor'):
                                    data['parcelamento_valor'] = round(preco_parcelado / data['parcelamento_numero'], 2)
                                break
                        except ValueError:
                            pass
                
                # Verifica se tem juros
                if 'sem juros' in installment_text.lower() or 'sem juro' in installment_text.lower():
                    data['parcelamento_juros'] = False
                elif 'juros' in installment_text.lower() or 'com juros' in installment_text.lower():
                    data['parcelamento_juros'] = True
            
            # Calcula preço total parcelado (igual ao Mercado Livre)
            # IMPORTANTE: Valida se o valor da parcela não é o preço à vista
            if data.get('parcelamento_numero'):
                # Se o valor da parcela é igual ou muito próximo do preço à vista, está errado
                if data.get('parcelamento_valor') and data.get('preco'):
                    # Se a diferença é menor que 10%, provavelmente capturou o preço à vista errado
                    if abs(data['parcelamento_valor'] - data['preco']) < data['preco'] * 0.1:
                        # Limpa o valor errado, mas mantém o número de parcelas
                        data['parcelamento_valor'] = None
                
                if data.get('preco_parcelado'):
                    valor_calculado = round(data['preco_parcelado'] / data['parcelamento_numero'], 2)
                    # Validação: valor calculado deve ser menor que o preço à vista (parcelas são menores)
                    if data.get('preco') and valor_calculado >= data['preco']:
                        # Se o valor calculado é maior ou igual ao preço, o preco_parcelado está errado
                        # Tenta usar o parcelamento_valor se existir e for válido
                        if data.get('parcelamento_valor') and data['parcelamento_valor'] < data['preco']:
                            # Usa o valor da parcela e recalcula o preço parcelado
                            data['preco_parcelado'] = round(data['parcelamento_numero'] * data['parcelamento_valor'], 2)
                            data['preco_total_parcelado'] = data['preco_parcelado']
                        else:
                            # Se não tem valor válido, limpa o preco_parcelado mas mantém o número
                            data['preco_parcelado'] = None
                    else:
                        # Valor calculado é válido
                        if data.get('parcelamento_valor'):
                            diferenca = abs(data['parcelamento_valor'] - valor_calculado)
                            if diferenca > 50 or (data['parcelamento_valor'] > 0 and diferenca / data['parcelamento_valor'] > 0.1):
                                data['parcelamento_valor'] = valor_calculado
                        else:
                            data['parcelamento_valor'] = valor_calculado
                        data['preco_total_parcelado'] = round(data['parcelamento_numero'] * data['parcelamento_valor'], 2)
                elif data.get('parcelamento_valor'):
                    # Validação: valor da parcela deve ser menor que o preço à vista
                    if data.get('preco') and data['parcelamento_valor'] >= data['preco']:
                        # Valor inválido, limpa
                        data['parcelamento_valor'] = None
                    else:
                        data['preco_total_parcelado'] = round(data['parcelamento_numero'] * data['parcelamento_valor'], 2)
                        data['preco_parcelado'] = data['preco_total_parcelado']
            
            # Imagem - melhorado
            img_selectors = [
                'img[data-image-latency]',
                '.s-image',
                'img[src*="images-amazon"]',
                'img[data-src*="images-amazon"]',
            ]
            
            for selector in img_selectors:
                img_el = item.select_one(selector)
                if img_el:
                    img_url = img_el.get('src') or img_el.get('data-src') or img_el.get('data-lazy-src')
                    if img_url:
                        # Remove parâmetros de redimensionamento da Amazon
                        if '._' in img_url:
                            img_url = re.sub(r'\._[A-Z0-9_]+\.', '.', img_url)
                        if img_url.startswith('http'):
                            data['imagem'] = img_url
                            break
                        elif img_url.startswith('//'):
                            data['imagem'] = 'https:' + img_url
                            break
            
            # Avaliações - melhorado
            rating_selectors = [
                '.a-icon-alt',
                '[aria-label*="estrela"]',
                '[aria-label*="star"]',
                '.a-icon-star',
            ]
            
            for selector in rating_selectors:
                rating_el = item.select_one(selector)
                if rating_el:
                    rating_text = rating_el.get_text(strip=True) or rating_el.get('aria-label', '')
                    if rating_text:
                        rating_match = re.search(r'(\d+[.,]\d+|\d+)', rating_text)
                        if rating_match:
                            try:
                                data['nota'] = float(rating_match.group(1).replace(',', '.'))
                                break
                            except ValueError:
                                pass
            
            # Número de avaliações - melhorado
            reviews_selectors = [
                'a[href*="customerReviews"]',
                '[aria-label*="avaliação"]',
                '[aria-label*="review"]',
                '.a-size-base',
            ]
            
            for selector in reviews_selectors:
                reviews_el = item.select_one(selector)
                if reviews_el:
                    reviews_text = reviews_el.get_text(strip=True) or reviews_el.get('aria-label', '')
                    if reviews_text:
                        # Procura números no texto (pode ter formato "7.923" ou "7,923")
                        reviews_match = re.search(r'(\d+(?:[.,]\d+)?)', reviews_text.replace('.', '').replace(',', ''))
                        if reviews_match:
                            try:
                                # Remove pontos e vírgulas para converter
                                num_str = reviews_match.group(1).replace('.', '').replace(',', '')
                                data['num_avaliacoes'] = int(num_str)
                                break
                            except ValueError:
                                pass
            
            # Número de vendas - procura por padrões da Amazon (melhorado)
            # Exemplo: "Mais de 3 mil compras no mês passado"
            sales_text = item.get_text()
            sales_patterns = [
                r'mais\s+(?:de|que)\s*(\d+)\s*(?:mil|milhões?)?\s*(?:compras?|vendas?)',
                r'(\d+)\s*(?:mil|milhões?)?\s*(?:compras?|vendas?)',
                r'mais\s+de\s+(\d+)\s*(?:mil)?\s*compras?\s+no\s+mês',
            ]
            
            for pattern in sales_patterns:
                sales_match = re.search(pattern, sales_text, re.IGNORECASE)
                if sales_match:
                    try:
                        num_str = sales_match.group(1)
                        match_text = sales_match.group(0).lower()
                        # Se menciona "mil", multiplica por 1000
                        if 'mil' in match_text:
                            data['num_vendas'] = int(num_str) * 1000
                        elif 'milhões' in match_text or 'milhoes' in match_text:
                            data['num_vendas'] = int(num_str) * 1000000
                        else:
                            data['num_vendas'] = int(num_str)
                        break
                    except (ValueError, IndexError):
                        pass
            
            # Frete grátis - melhorado
            shipping_selectors = [
                '[class*="shipping"]',
                '[class*="frete"]',
                '[class*="prime"]',
                '.a-text-bold',
            ]
            
            shipping_text = ''
            for selector in shipping_selectors:
                shipping_el = item.select_one(selector)
                if shipping_el:
                    shipping_text = shipping_el.get_text(strip=True).lower()
                    if 'frete grátis' in shipping_text or 'frete gratis' in shipping_text or 'prime' in shipping_text:
                        data['frete_gratis'] = 'true'
                        data['texto_entrega'] = shipping_el.get_text(strip=True)
                        break
            
            # Se não encontrou, procura no texto geral
            if not shipping_text:
                item_text_lower = item.get_text().lower()
                if 'frete grátis' in item_text_lower or 'frete gratis' in item_text_lower or 'prime' in item_text_lower:
                    data['frete_gratis'] = 'true'
                    data['texto_entrega'] = 'Frete Grátis'
                elif 'frete' in item_text_lower or 'envio' in item_text_lower:
                    data['frete_gratis'] = 'false'
                    data['texto_entrega'] = ''
                else:
                    data['frete_gratis'] = 'unknown'
                    data['texto_entrega'] = ''
            
            # Loja oficial - melhorado
            seller_selectors = [
                '[class*="seller"]',
                '[class*="vendedor"]',
                '.a-text-bold',
            ]
            
            seller_text = ''
            for selector in seller_selectors:
                seller_el = item.select_one(selector)
                if seller_el:
                    seller_text = seller_el.get_text(strip=True).lower()
                    break
            
            if not seller_text:
                seller_text = item.get_text().lower()
            
            # Detecta se é vendido/enviado pela Amazon
            if 'vendido e enviado' in seller_text and 'amazon' in seller_text:
                data['loja_oficial'] = True
            elif 'amazon.com.br' in seller_text or 'enviado pela amazon' in seller_text:
                data['loja_oficial'] = True
            else:
                data['loja_oficial'] = False
            
            # Data de coleta
            data['data_coleta'] = datetime.now().isoformat()
            
            return data
            
        except Exception as e:
            print(f"Erro ao extrair produto da Amazon: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def close(self):
        """Fecha recursos."""
        self.fetcher.close()

