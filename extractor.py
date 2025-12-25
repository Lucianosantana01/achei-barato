"""
Módulo de extração de dados de produtos.
Prioriza JSON embutido, depois HTML parsing.
"""
import re
import json
from typing import Dict, Optional, Any
from urllib.parse import urlparse
from bs4 import BeautifulSoup
from datetime import datetime


class Extractor:
    """Extrai dados de produtos de páginas HTML."""
    
    def extract(self, url: str, html: str) -> Dict[str, Any]:
        """
        Extrai dados do produto de uma página HTML.
        
        Args:
            url: URL da página
            html: Conteúdo HTML da página
            
        Returns:
            Dicionário com dados extraídos
        """
        data = {
            'plataforma': self._extract_platform(url),
            'url_produto': url,
            'data_coleta': datetime.now().isoformat(),
        }
        
        if not html:
            data['parse_status'] = 'error'
            return data
        
        soup = BeautifulSoup(html, 'html.parser')
        
        # Detecta bloqueios antes de processar
        blocked = self._detect_blocked(html, soup)
        if blocked:
            data['parse_status'] = 'blocked'
            return data
        
        # Prioridade 1: JSON embutido
        json_data = self._extract_json_data(html, soup)
        if json_data:
            data.update(json_data)
        
        # Prioridade 2: HTML parsing (complementa ou substitui se JSON não tiver dados)
        html_data = self._extract_from_html(soup, url)
        
        # Mescla dados (HTML tem prioridade se JSON não tiver o campo)
        for key, value in html_data.items():
            if value is not None or key not in data:
                data[key] = value
        
        return data
    
    def _detect_blocked(self, html: str, soup: BeautifulSoup) -> bool:
        """
        Detecta se a página é um bloqueio (403, 429, captcha, etc).
        
        Returns:
            True se bloqueado, False caso contrário
        """
        html_lower = html.lower()
        page_text = soup.get_text().lower() if soup else ''
        
        # Padrões de bloqueio
        blocked_patterns = [
            '403',
            'forbidden',
            'access denied',
            'acesso negado',
            '429',
            'too many requests',
            'rate limit',
            'captcha',
            'cloudflare',
            'checking your browser',
            'just a moment',
            'ray id',
            'blocked',
            'bloqueado',
        ]
        
        # Verifica no HTML e texto
        for pattern in blocked_patterns:
            if pattern in html_lower or pattern in page_text:
                return True
        
        # Verifica títulos comuns de páginas de erro
        title = soup.find('title')
        if title:
            title_text = title.get_text().lower()
            if any(keyword in title_text for keyword in ['403', '429', 'forbidden', 'blocked', 'captcha']):
                return True
        
        return False
    
    def _extract_platform(self, url: str) -> str:
        """Extrai plataforma da URL."""
        try:
            parsed = urlparse(url)
            domain = parsed.netloc or parsed.path
            # Remove www. se presente
            if domain.startswith('www.'):
                domain = domain[4:]
            return domain
        except:
            return 'unknown'
    
    def _extract_json_data(self, html: str, soup: BeautifulSoup) -> Optional[Dict[str, Any]]:
        """Extrai dados de JSON embutido no HTML."""
        data = {}
        
        # 1. Schema.org (application/ld+json)
        schema_scripts = soup.find_all('script', type='application/ld+json')
        for script in schema_scripts:
            try:
                schema_data = json.loads(script.string)
                if isinstance(schema_data, dict):
                    if schema_data.get('@type') == 'Product':
                        data.update(self._parse_schema_product(schema_data))
                elif isinstance(schema_data, list):
                    for item in schema_data:
                        if isinstance(item, dict) and item.get('@type') == 'Product':
                            data.update(self._parse_schema_product(item))
                            break
            except (json.JSONDecodeError, AttributeError):
                continue
        
        # 2. Variáveis globais JavaScript (__NEXT_DATA__, __PRELOADED_STATE__, etc)
        json_patterns = [
            r'__NEXT_DATA__\s*=\s*({.+?});',
            r'__PRELOADED_STATE__\s*=\s*({.+?});',
            r'window\.__INITIAL_STATE__\s*=\s*({.+?});',
            r'window\.__PRELOADED_STATE__\s*=\s*({.+?});',
        ]
        
        for pattern in json_patterns:
            matches = re.finditer(pattern, html, re.DOTALL)
            for match in matches:
                try:
                    json_str = match.group(1)
                    json_obj = json.loads(json_str)
                    extracted = self._parse_js_state(json_obj)
                    if extracted:
                        data.update(extracted)
                        break
                except (json.JSONDecodeError, AttributeError):
                    continue
        
        return data if data else None
    
    def _parse_schema_product(self, schema: Dict[str, Any]) -> Dict[str, Any]:
        """Parse Schema.org Product."""
        data = {}
        
        if 'name' in schema:
            data['titulo'] = schema['name']
        
        if 'offers' in schema:
            offers = schema['offers']
            if isinstance(offers, dict):
                offers = [offers]
            
            for offer in offers:
                if 'price' in offer:
                    price = offer['price']
                    if isinstance(price, (int, float)):
                        data['preco'] = float(price)
                    elif isinstance(price, str):
                        # Tenta extrair número
                        price_clean = re.sub(r'[^\d.,]', '', price)
                        if price_clean:
                            try:
                                price_clean = price_clean.replace('.', '').replace(',', '.')
                                data['preco'] = float(price_clean)
                            except ValueError:
                                pass
                
                if 'priceCurrency' in offer:
                    data['moeda'] = offer['priceCurrency']
        
        if 'image' in schema:
            image = schema['image']
            if isinstance(image, str):
                data['imagem'] = image
            elif isinstance(image, list) and image:
                data['imagem'] = image[0]
        
        if 'aggregateRating' in schema:
            rating = schema['aggregateRating']
            if 'ratingValue' in rating:
                try:
                    data['nota'] = float(rating['ratingValue'])
                except (ValueError, TypeError):
                    pass
            if 'reviewCount' in rating:
                try:
                    data['num_avaliacoes'] = int(rating['reviewCount'])
                except (ValueError, TypeError):
                    pass
        
        return data
    
    def _parse_js_state(self, state: Any) -> Optional[Dict[str, Any]]:
        """Parse JavaScript state objects."""
        data = {}
        
        # Procura recursivamente por dados de produto
        if isinstance(state, dict):
            # Mercado Livre patterns
            if 'initialState' in state:
                return self._parse_js_state(state['initialState'])
            if 'props' in state:
                return self._parse_js_state(state['props'])
            if 'pageProps' in state:
                return self._parse_js_state(state['pageProps'])
            
            # Procura por campos específicos
            if 'title' in state or 'name' in state:
                data['titulo'] = state.get('title') or state.get('name')
            
            if 'price' in state or 'originalPrice' in state:
                price = state.get('price') or state.get('originalPrice')
                if price:
                    try:
                        data['preco'] = float(price)
                    except (ValueError, TypeError):
                        pass
            
            if 'currency' in state or 'currencyId' in state:
                data['moeda'] = state.get('currency') or state.get('currencyId')
            
            if 'pictures' in state or 'images' in state:
                pics = state.get('pictures') or state.get('images')
                if isinstance(pics, list) and pics:
                    data['imagem'] = pics[0] if isinstance(pics[0], str) else pics[0].get('url', '')
                elif isinstance(pics, str):
                    data['imagem'] = pics
        
        return data if data else None
    
    def _extract_from_html(self, soup: BeautifulSoup, url: str) -> Dict[str, Any]:
        """Extrai dados diretamente do HTML."""
        data = {}
        
        # Detecta se é Amazon
        is_amazon = 'amazon.com.br' in url.lower() or 'amazon.com' in url.lower()
        
        if is_amazon:
            return self._extract_from_amazon_html(soup, url)
        
        # Título
        title_selectors = [
            'h1[class*="title"]',
            'h1[class*="name"]',
            'h1',
            '[data-testid="title"]',
            '.ui-pdp-title',
            '.item-title',
        ]
        for selector in title_selectors:
            el = soup.select_one(selector)
            if el:
                title = el.get_text(strip=True)
                if title and len(title) > 3:
                    data['titulo'] = title
                    break
        
        # Preço atual
        price_selectors = [
            '[class*="price"] [class*="fraction"]:not(s [class*="fraction"])',
            '.andes-money-amount__fraction:not(s .andes-money-amount__fraction)',
            '.price-tag-fraction:not(s .price-tag-fraction)',
            '[data-testid="price"]',
            '.ui-pdp-price__second-line .andes-money-amount__fraction',
        ]
        
        price_el = None
        for selector in price_selectors:
            price_el = soup.select_one(selector)
            if price_el:
                # Verifica se não está riscado
                if price_el.find_parent('s') or 'previous' in str(price_el.get('class', [])).lower():
                    continue
                break
        
        if price_el:
            frac = price_el.get_text(strip=True)
            frac_clean = re.sub(r'[^\d]', '', frac) or "0"
            
            # Centavos
            parent = price_el.find_parent(['div', 'span', 'section'])
            cents_el = None
            if parent:
                cents_el = parent.select_one('.andes-money-amount__cents, .price-tag-cents, [class*="cents"]')
            if not cents_el:
                cents_el = soup.select_one('.andes-money-amount__cents, .price-tag-cents, [class*="cents"]')
            cents = cents_el.get_text(strip=True) if cents_el else "00"
            cents_clean = re.sub(r'[^\d]', '', cents) or "00"
            if len(cents_clean) > 2:
                cents_clean = cents_clean[:2]
            elif len(cents_clean) == 1:
                cents_clean = cents_clean + "0"
            
            try:
                frac_int = int(frac_clean) if frac_clean else 0
                cents_int = int(cents_clean) if cents_clean else 0
                preco = float(f"{frac_int}.{cents_int:02d}")
                if 1 <= preco <= 1000000:
                    data['preco'] = preco
            except (ValueError, OverflowError):
                pass
        
        # Moeda
        currency_el = soup.select_one('.andes-money-amount__currency-symbol, .price-tag-symbol, [class*="currency"]')
        if currency_el:
            moeda = currency_el.get_text(strip=True)
            data['moeda'] = 'BRL' if 'R$' in moeda or 'BRL' in moeda else moeda
        else:
            data['moeda'] = 'BRL'
        
        # Preço anterior (riscado)
        previous_price_el = soup.select_one('s.andes-money-amount--previous, .andes-money-amount--previous, s [class*="price"]')
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
                    except ValueError:
                        pass
        
        # Desconto
        discount_el = soup.select_one('[class*="discount"], [class*="off"], [class*="desconto"]')
        if discount_el:
            discount_text = discount_el.get_text(strip=True)
            discount_match = re.search(r'(\d+)\s*%', discount_text, re.IGNORECASE)
            if discount_match:
                try:
                    data['desconto_percentual'] = float(discount_match.group(1))
                except ValueError:
                    pass
        
        # Calcula desconto_valor
        if data.get('preco_anterior') and data.get('preco'):
            data['desconto_valor'] = data['preco_anterior'] - data['preco']
            if not data.get('desconto_percentual'):
                data['desconto_percentual'] = round((data['desconto_valor'] / data['preco_anterior']) * 100, 1)
        
        # Parcelamento
        installment_el = soup.select_one('[class*="installment"], [class*="parcela"], [class*="installments"]')
        if installment_el:
            installment_text = installment_el.get_text(strip=True)
            
            # Número de parcelas
            parcelas_match = re.search(r'(\d+)\s*x', installment_text, re.IGNORECASE)
            if parcelas_match:
                try:
                    data['parcelamento_numero'] = int(parcelas_match.group(1))
                except ValueError:
                    pass
            
            # Valor da parcela
            valor_match = re.search(r'R\$\s*(\d{1,3}(?:\.\d{3})*(?:[.,]\d{2})?)', installment_text)
            if valor_match:
                valor_str = valor_match.group(1).replace('.', '').replace(',', '.')
                try:
                    valor_parcela = float(valor_str)
                    if 1 <= valor_parcela <= 10000:
                        data['parcelamento_valor'] = valor_parcela
                except ValueError:
                    pass
            
            # Preço parcelado
            preco_parcelado_match = re.search(r'(?:ou|em)\s*R\$\s*(\d+(?:\.\d{3})*(?:[.,]\d{2})?)', installment_text, re.IGNORECASE)
            if preco_parcelado_match:
                preco_parcelado_str = preco_parcelado_match.group(1).replace('.', '').replace(',', '.')
                try:
                    preco_parcelado = float(preco_parcelado_str)
                    if 1 <= preco_parcelado <= 1000000:
                        data['preco_parcelado'] = preco_parcelado
                        if data.get('parcelamento_numero') and not data.get('parcelamento_valor'):
                            data['parcelamento_valor'] = round(preco_parcelado / data['parcelamento_numero'], 2)
                except ValueError:
                    pass
            
            # Juros
            if 'sem juros' in installment_text.lower() or 'sem juro' in installment_text.lower():
                data['parcelamento_juros'] = False
            elif 'juros' in installment_text.lower():
                data['parcelamento_juros'] = True
        
        # Calcula preço total parcelado
        if data.get('parcelamento_numero'):
            if data.get('preco_parcelado'):
                valor_calculado = round(data['preco_parcelado'] / data['parcelamento_numero'], 2)
                if data.get('parcelamento_valor'):
                    diferenca = abs(data['parcelamento_valor'] - valor_calculado)
                    if diferenca > 50 or (data['parcelamento_valor'] > 0 and diferenca / data['parcelamento_valor'] > 0.1):
                        data['parcelamento_valor'] = valor_calculado
                else:
                    data['parcelamento_valor'] = valor_calculado
                data['preco_total_parcelado'] = round(data['parcelamento_numero'] * data['parcelamento_valor'], 2)
            elif data.get('parcelamento_valor'):
                data['preco_total_parcelado'] = round(data['parcelamento_numero'] * data['parcelamento_valor'], 2)
                data['preco_parcelado'] = data['preco_total_parcelado']
        
        # Imagem
        img_selectors = [
            '[class*="gallery"] img',
            '[class*="image"] img',
            '[data-testid="gallery-image"]',
            '.ui-pdp-gallery__figure img',
            'img[class*="product"]',
        ]
        for selector in img_selectors:
            img_el = soup.select_one(selector)
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
        
        # Frete e entrega
        shipping_data = self._extract_shipping_info(soup)
        data.update(shipping_data)
        
        # Avaliações
        rating_el = soup.select_one('[class*="rating"], [class*="reviews"], [data-testid="rating"]')
        if rating_el:
            rating_text = rating_el.get_text(strip=True)
            rating_match = re.search(r'(\d+[.,]\d+|\d+)', rating_text)
            if rating_match:
                try:
                    data['nota'] = float(rating_match.group(1).replace(',', '.'))
                except ValueError:
                    pass
        
        # Número de avaliações
        reviews_el = soup.select_one('[class*="review"], [class*="avaliacao"], [data-testid="reviews"]')
        if reviews_el:
            reviews_text = reviews_el.get_text(strip=True)
            reviews_match = re.search(r'(\d+)', reviews_text)
            if reviews_match:
                try:
                    data['num_avaliacoes'] = int(reviews_match.group(1))
                except ValueError:
                    pass
        
        # Número de vendas
        sales_text = soup.get_text()
        sales_match = re.search(r'(?:mais\s+de|mais\s+que|\+)\s*(\d+)', sales_text, re.IGNORECASE)
        if sales_match:
            try:
                data['num_vendas'] = int(sales_match.group(1))
            except ValueError:
                pass
        
        # Loja oficial
        official_indicators = [
            '[class*="official"]',
            '[class*="oficial"]',
            '[class*="verified"]',
            '[class*="verificado"]',
        ]
        data['loja_oficial'] = False
        for selector in official_indicators:
            official_el = soup.select_one(selector)
            if official_el:
                data['loja_oficial'] = True
                break
        
        if not data['loja_oficial']:
            page_text = soup.get_text().lower()
            if any(term in page_text for term in ['loja oficial', 'official store', 'distribuidor autorizado', 'vendedor oficial']):
                data['loja_oficial'] = True
        
        return data
    
    def _extract_shipping_info(self, soup: BeautifulSoup) -> Dict[str, Any]:
        """Extrai informações de frete e entrega."""
        data = {}
        
        # Texto de entrega geral
        shipping_selectors = [
            '[class*="shipping"]',
            '[class*="frete"]',
            '[class*="envio"]',
            '[class*="delivery"]',
            '[data-testid="shipping"]',
        ]
        
        shipping_el = None
        for selector in shipping_selectors:
            shipping_el = soup.select_one(selector)
            if shipping_el:
                shipping_text = shipping_el.get_text(strip=True)
                if shipping_text:
                    data['texto_entrega'] = shipping_text
                    break
        
        # Interpreta frete grátis
        if data.get('texto_entrega'):
            texto_lower = data['texto_entrega'].lower()
            if any(kw in texto_lower for kw in ['frete grátis', 'frete gratis', 'frete gratuito', 'entrega grátis', 'envio grátis', 'free shipping']):
                data['frete_gratis'] = 'true'
            elif any(kw in texto_lower for kw in ['frete a partir de', 'frete de', 'custo de envio']):
                data['frete_gratis'] = 'false'
            else:
                data['frete_gratis'] = 'unknown'
        else:
            data['frete_gratis'] = 'unknown'
            data['texto_entrega'] = ''
        
        # Detalhes de frete grátis
        frete_detalhes = self._extract_free_shipping_details(soup)
        if frete_detalhes:
            data['frete_gratis_detalhes'] = frete_detalhes
        
        # Detalhes de entrega
        entrega_detalhes = self._extract_delivery_details(soup)
        if entrega_detalhes:
            data['data_entrega_detalhes'] = entrega_detalhes
        
        # FULL fulfillment
        full_info = self._extract_full_fulfillment(soup)
        if full_info:
            data['full_fulfillment'] = full_info
        
        return data
    
    def _extract_free_shipping_details(self, soup: BeautifulSoup) -> Optional[str]:
        """Extrai detalhes de frete grátis (ex: 'FRETE GRÁTIS ACIMA DE R$ 19')."""
        selectors = [
            '[class*="free-shipping"]',
            '[class*="frete-gratis"]',
            '[class*="shipping-free"]',
            '[data-testid*="free-shipping"]',
        ]
        
        for selector in selectors:
            el = soup.select_one(selector)
            if el:
                text = el.get_text(strip=True)
                if text and len(text) > 5:
                    # Limpa e retorna
                    text = re.sub(r'\s+', ' ', text).strip()
                    if 'grátis' in text.lower() or 'gratis' in text.lower() or 'free' in text.lower():
                        return text.upper() if text.isupper() else text
        
        # Procura por padrão no texto
        page_text = soup.get_text()
        patterns = [
            r'FRETE\s+GRÁTIS(?:\s+ACIMA\s+DE\s+R\$\s*\d+)?',
            r'FRETE\s+GRATIS(?:\s+ACIMA\s+DE\s+R\$\s*\d+)?',
            r'ENVIO\s+GRÁTIS(?:\s+ACIMA\s+DE\s+R\$\s*\d+)?',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, page_text, re.IGNORECASE)
            if match:
                return match.group(0).strip()
        
        return None
    
    def _extract_delivery_details(self, soup: BeautifulSoup) -> Optional[str]:
        """Extrai detalhes de entrega (ex: 'Receba grátis segunda-feira')."""
        selectors = [
            '[class*="delivery-date"]',
            '[class*="data-entrega"]',
            '[class*="receba"]',
            '[data-testid*="delivery"]',
        ]
        
        for selector in selectors:
            el = soup.select_one(selector)
            if el:
                text = el.get_text(strip=True)
                if text and len(text) > 5:
                    # Verifica se menciona data ou dia
                    if any(word in text.lower() for word in ['segunda', 'terça', 'quarta', 'quinta', 'sexta', 'sábado', 'domingo', 'dia', 'receba', 'chegará']):
                        return text.strip()
        
        # Procura por padrão no texto
        page_text = soup.get_text()
        patterns = [
            r'Receba\s+grátis\s+\w+',
            r'Chegará\s+em\s+\d+\s+dias?',
            r'Entrega\s+em\s+\d+\s+dias?',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, page_text, re.IGNORECASE)
            if match:
                return match.group(0).strip()
        
        return None
    
    def _extract_full_fulfillment(self, soup: BeautifulSoup) -> Optional[str]:
        """Extrai informação sobre FULL (ex: 'Armazenado e enviado pelo FULL')."""
        selectors = [
            '[class*="full"]',
            '[class*="fulfillment"]',
            '[data-testid*="full"]',
        ]
        
        for selector in selectors:
            el = soup.select_one(selector)
            if el:
                text = el.get_text(strip=True)
                if text and 'full' in text.lower():
                    return text.strip()
        
        # Procura por padrão no texto
        page_text = soup.get_text()
        patterns = [
            r'Armazenado\s+e\s+enviado\s+pelo\s+FULL',
            r'Enviado\s+pelo\s+FULL',
            r'FULL\s+Shipping',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, page_text, re.IGNORECASE)
            if match:
                return match.group(0).strip()
        
        return None
    
    def _extract_from_amazon_html(self, soup: BeautifulSoup, url: str) -> Dict[str, Any]:
        """Extrai dados de páginas de produto da Amazon."""
        data = {}
        
        # Título
        title_selectors = [
            '#productTitle',
            'h1.a-size-large',
            'h1[data-automation-id="title"]',
            'span#productTitle',
            'h1',
        ]
        for selector in title_selectors:
            el = soup.select_one(selector)
            if el:
                title = el.get_text(strip=True)
                if title and len(title) > 3:
                    data['titulo'] = title
                    break
        
        # Preço atual - Amazon
        price_selectors = [
            '.a-price .a-offscreen',
            '.a-price-whole',
            '#priceblock_ourprice',
            '#priceblock_dealprice',
            '#priceblock_saleprice',
            '.a-price[data-a-color="base"] .a-offscreen',
            '[data-a-color="price"] .a-offscreen',
            '.a-price-range .a-offscreen',
        ]
        
        price_el = None
        price_text = None
        for selector in price_selectors:
            price_el = soup.select_one(selector)
            if price_el:
                price_text = price_el.get_text(strip=True)
                if price_text:
                    break
        
        # Tenta pegar do atributo data-a-price
        if not price_text:
            price_el = soup.select_one('[data-a-price]')
            if price_el:
                price_text = price_el.get('data-a-price', '')
        
        if price_text:
            price_clean = re.sub(r'[^\d,.]', '', price_text)
            if price_clean:
                try:
                    price_clean = price_clean.replace('.', '').replace(',', '.')
                    preco = float(price_clean)
                    if 1 <= preco <= 1000000:
                        data['preco'] = preco
                        data['moeda'] = 'BRL'
                except (ValueError, OverflowError):
                    pass
        
        # Preço anterior (riscado) - Amazon
        previous_price_selectors = [
            '.a-price.a-text-price .a-offscreen',
            '.a-price.a-text-strike .a-offscreen',
            '[data-a-strike="true"] .a-offscreen',
            '.a-text-strike .a-offscreen',
            '.basisPrice .a-offscreen',
        ]
        
        for selector in previous_price_selectors:
            previous_price_el = soup.select_one(selector)
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
        
        # Desconto - procura também por badges de desconto (igual ao Mercado Livre)
        discount_selectors = [
            '[class*="discount"]',
            '[class*="off"]',
            '[class*="desconto"]',
            '[class*="savings"]',
            '.a-size-base.a-color-price',
            '[id*="savings"]',
        ]
        
        for selector in discount_selectors:
            discount_el = soup.select_one(selector)
            if discount_el:
                discount_text = discount_el.get_text(strip=True)
                discount_match = re.search(r'(\d+(?:[.,]\d+)?)\s*%', discount_text, re.IGNORECASE)
                if discount_match:
                    try:
                        discount_pct = float(discount_match.group(1).replace(',', '.'))
                        if not data.get('desconto_percentual'):
                            data['desconto_percentual'] = discount_pct
                        break
                    except ValueError:
                        pass
        
        # Calcula desconto (igual ao Mercado Livre)
        if data.get('preco_anterior') and data.get('preco'):
            data['desconto_valor'] = data['preco_anterior'] - data['preco']
            if not data.get('desconto_percentual'):
                data['desconto_percentual'] = round((data['desconto_valor'] / data['preco_anterior']) * 100, 1)
        
        # Parcelamento - Amazon (melhorado)
        # Primeiro procura em seletores específicos
        installment_selectors = [
            '#installmentOptions_feature_div',
            '[id*="installment"]',
            '.a-section.a-spacing-none.a-spacing-top-mini',
            '[class*="installment"]',
            '.a-text-price',
            '[data-a-name="installment"]',
        ]
        
        installment_text = None
        for selector in installment_selectors:
            elements = soup.select(selector)
            for el in elements:
                text = el.get_text(strip=True)
                # Verifica se tem padrão de parcelas
                if re.search(r'\d+\s*x\s*(?:de|R\$|sem|com|/mês)|em\s+at[ée]\s+\d+\s*x', text, re.IGNORECASE):
                    installment_text = text
                    break
            if installment_text:
                break
        
        # Se não encontrou, procura no texto geral da página (área de preço)
        if not installment_text:
            # Procura na área de preço e seus pais
            price_section = soup.select_one('#price, #priceblock_ourprice, #priceblock_dealprice, .a-price, [class*="price"]')
            if price_section:
                # Procura no elemento e em seus pais
                current = price_section
                for _ in range(3):  # Sobe até 3 níveis
                    if current:
                        text = current.get_text(strip=True)
                        if re.search(r'\d+\s*x\s*(?:de|R\$|sem|com|/mês)|em\s+at[ée]\s+\d+\s*x', text, re.IGNORECASE):
                            installment_text = text
                            break
                        current = current.find_parent(['div', 'span', 'section'])
        
        # Se ainda não encontrou, procura em toda a área de pagamento
        if not installment_text:
            payment_section = soup.select_one('[id*="payment"], [class*="payment"], [id*="buybox"], [class*="buybox"], #twister')
            if payment_section:
                text = payment_section.get_text(strip=True)
                if re.search(r'\d+\s*x\s*(?:de|R\$|sem|com|/mês)|em\s+at[ée]\s+\d+\s*x', text, re.IGNORECASE):
                    installment_text = text
        
        if installment_text:
            # Número de parcelas - múltiplos padrões
            parcelas_patterns = [
                r'em\s+at[ée]\s+(\d+)\s*x',
                r'(\d+)\s*x\s*(?:de|R\$|sem|com|/mês)',
                r'(\d+)\s*vezes',
                r'(\d+)\s*x\s*de',
            ]
            
            for pattern in parcelas_patterns:
                parcelas_match = re.search(pattern, installment_text, re.IGNORECASE)
                if parcelas_match:
                    try:
                        data['parcelamento_numero'] = int(parcelas_match.group(1))
                        break
                    except (ValueError, IndexError):
                        pass
            
            # Valor da parcela - múltiplos padrões (PRIORIDADE: padrões mais específicos primeiro)
            # Formato Amazon: "Em até 12x R$ 257,99 sem juros" ou "12x de R$ 257,99 sem juros"
            valor_patterns = [
                r'em\s+at[ée]\s+\d+\s*x\s*R\$\s*(\d{1,3}(?:\.\d{3})*(?:[.,]\d{2})?)\s*(?:sem|com)',  # "Em até 12x R$ 257,99 sem juros"
                r'(\d+)\s*x\s*(?:de\s*)?R\$\s*(\d{1,3}(?:\.\d{3})*(?:[.,]\d{2})?)\s*(?:sem|com)',  # "12x de R$ 257,99 sem juros" ou "12x R$ 257,99 sem juros"
                r'(\d+)\s*x\s*de\s*R\$\s*(\d{1,3}(?:\.\d{3})*(?:[.,]\d{2})?)',  # "12x de R$ 257,99"
                r'(?:de\s*)?R\$\s*(\d{1,3}(?:\.\d{3})*(?:[.,]\d{2})?)\s*(?:sem|com|por|/mês)',  # "R$ 257,99 sem juros"
                r'(\d{1,3}(?:\.\d{3})*(?:[.,]\d{2})?)\s*(?:por|cada|parcela|/mês)',
            ]
            
            # Se o padrão capturou 2 grupos, o segundo é o valor
            for pattern in valor_patterns:
                valor_match = re.search(pattern, installment_text, re.IGNORECASE)
                if valor_match:
                    # Se tem 2 grupos, pega o segundo (valor)
                    if len(valor_match.groups()) == 2:
                        valor_str = valor_match.group(2)
                    else:
                        valor_str = valor_match.group(1)
                    
                    # Remove pontos de milhar e substitui vírgula por ponto decimal
                    valor_str = valor_str.replace('.', '').replace(',', '.')
                    
                    try:
                        valor_parcela = float(valor_str)
                        # Validação: valor da parcela deve ser menor que o preço
                        # E deve estar em um range razoável (entre 1 e 10000)
                        if 1 <= valor_parcela <= 10000:
                            if not data.get('preco') or valor_parcela < data['preco']:
                                data['parcelamento_valor'] = valor_parcela
                                break
                    except (ValueError, IndexError):
                        pass
            
            
            # Preço parcelado total - múltiplos padrões
            preco_parcelado_patterns = [
                r'(?:ou|em)\s+R\$\s*(\d+(?:\.\d{3})*(?:[.,]\d{2})?)\s+em\s+\d+\s*x',
                r'R\$\s*(\d+(?:\.\d{3})*(?:[.,]\d{2})?)\s+em\s+(?:até\s+)?\d+\s*x',
                r'(\d+(?:\.\d{3})*(?:[.,]\d{2})?)\s+em\s+\d+\s*x',
            ]
            
            for pattern in preco_parcelado_patterns:
                preco_match = re.search(pattern, installment_text, re.IGNORECASE)
                if preco_match:
                    preco_str = preco_match.group(1).replace('.', '').replace(',', '.')
                    try:
                        preco_parcelado = float(preco_str)
                        if 1 <= preco_parcelado <= 1000000:
                            data['preco_parcelado'] = preco_parcelado
                            # Se não tem valor da parcela, calcula
                            if data.get('parcelamento_numero') and not data.get('parcelamento_valor'):
                                data['parcelamento_valor'] = round(preco_parcelado / data['parcelamento_numero'], 2)
                            break
                    except ValueError:
                        pass
            
            # Juros
            if 'sem juros' in installment_text.lower() or 'sem juro' in installment_text.lower():
                data['parcelamento_juros'] = False
            elif 'juros' in installment_text.lower() or 'com juros' in installment_text.lower():
                data['parcelamento_juros'] = True
        
        # Calcula preço total parcelado
        if data.get('parcelamento_numero'):
            if data.get('preco_parcelado'):
                valor_calculado = round(data['preco_parcelado'] / data['parcelamento_numero'], 2)
                if data.get('parcelamento_valor'):
                    diferenca = abs(data['parcelamento_valor'] - valor_calculado)
                    if diferenca > 50 or (data['parcelamento_valor'] > 0 and diferenca / data['parcelamento_valor'] > 0.1):
                        data['parcelamento_valor'] = valor_calculado
                else:
                    data['parcelamento_valor'] = valor_calculado
                data['preco_total_parcelado'] = round(data['parcelamento_numero'] * data['parcelamento_valor'], 2)
            elif data.get('parcelamento_valor'):
                data['preco_total_parcelado'] = round(data['parcelamento_numero'] * data['parcelamento_valor'], 2)
                data['preco_parcelado'] = data['preco_total_parcelado']
        
        # Imagem - Amazon
        img_selectors = [
            '#landingImage',
            '#imgBlkFront',
            '#main-image',
            'img[data-a-dynamic-image]',
            '.a-dynamic-image',
        ]
        
        for selector in img_selectors:
            img_el = soup.select_one(selector)
            if img_el:
                img_url = img_el.get('src') or img_el.get('data-src') or img_el.get('data-a-dynamic-image')
                if img_url:
                    # Se data-a-dynamic-image é JSON, extrai a primeira URL
                    if img_url.startswith('{'):
                        try:
                            img_data = json.loads(img_url)
                            if isinstance(img_data, dict) and img_data:
                                img_url = list(img_data.keys())[0]
                        except:
                            pass
                    
                    # Remove parâmetros de redimensionamento
                    if '._' in img_url:
                        img_url = re.sub(r'\._[A-Z0-9_]+\.', '.', img_url)
                    
                    if img_url.startswith('http'):
                        data['imagem'] = img_url
                        break
                    elif img_url.startswith('//'):
                        data['imagem'] = 'https:' + img_url
                        break
        
        # Avaliações - Amazon
        rating_selectors = [
            '#acrCustomerReviewText',
            '.a-icon-alt',
            '[aria-label*="estrela"]',
            '[aria-label*="star"]',
            '#acrPopover',
        ]
        
        for selector in rating_selectors:
            rating_el = soup.select_one(selector)
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
        
        # Número de avaliações - Amazon
        reviews_selectors = [
            '#acrCustomerReviewText',
            'a[href*="customerReviews"]',
            '[aria-label*="avaliação"]',
            '[aria-label*="review"]',
            '[id*="acrCustomerReview"]',
        ]
        
        for selector in reviews_selectors:
            reviews_el = soup.select_one(selector)
            if reviews_el:
                reviews_text = reviews_el.get_text(strip=True) or reviews_el.get('aria-label', '')
                if reviews_text:
                    # Procura números (pode ter formato "7.923" ou "7,923")
                    reviews_match = re.search(r'(\d+(?:[.,]\d+)?)', reviews_text.replace('.', '').replace(',', ''))
                    if reviews_match:
                        try:
                            num_str = reviews_match.group(1).replace('.', '').replace(',', '')
                            data['num_avaliacoes'] = int(num_str)
                            break
                        except ValueError:
                            pass
        
        # Número de vendas - Amazon (igual ao Mercado Livre)
        sales_text = soup.get_text()
        sales_patterns = [
            r'mais\s+(?:de|que)\s*(\d+)\s*(?:mil|milhões?)?\s*(?:compras?|vendas?)',
            r'(\d+)\s*(?:mil|milhões?)?\s*(?:compras?|vendas?)',
            r'(\d+)\s*(?:comprado|vendido)',
            r'mais\s+de\s+(\d+)\s*(?:mil)?\s*compras?\s+no\s+mês',
        ]
        
        for pattern in sales_patterns:
            sales_match = re.search(pattern, sales_text, re.IGNORECASE)
            if sales_match:
                try:
                    num_str = sales_match.group(1)
                    # Se menciona "mil", multiplica por 1000
                    if 'mil' in sales_match.group(0).lower():
                        data['num_vendas'] = int(num_str) * 1000
                    elif 'milhões' in sales_match.group(0).lower() or 'milhoes' in sales_match.group(0).lower():
                        data['num_vendas'] = int(num_str) * 1000000
                    else:
                        data['num_vendas'] = int(num_str)
                    break
                except (ValueError, IndexError):
                    pass
        
        # Frete e entrega - Amazon
        shipping_data = self._extract_amazon_shipping_info(soup)
        data.update(shipping_data)
        
        # Loja oficial - Amazon
        seller_text = soup.get_text().lower()
        if 'vendido e enviado' in seller_text and 'amazon' in seller_text:
            data['loja_oficial'] = True
        elif 'enviado pela amazon' in seller_text or 'amazon.com.br' in seller_text:
            data['loja_oficial'] = True
        else:
            data['loja_oficial'] = False
        
        return data
    
    def _extract_amazon_shipping_info(self, soup: BeautifulSoup) -> Dict[str, Any]:
        """Extrai informações de frete e entrega da Amazon (igual ao Mercado Livre)."""
        data = {}
        
        # Frete grátis - múltiplos seletores
        shipping_selectors = [
            '[id*="delivery"]',
            '[class*="shipping"]',
            '[class*="frete"]',
            '[class*="entrega"]',
            '.a-section.a-spacing-mini',
            '[data-a-name="delivery"]',
        ]
        
        shipping_text = ''
        shipping_element = None
        for selector in shipping_selectors:
            shipping_el = soup.select_one(selector)
            if shipping_el:
                text = shipping_el.get_text(strip=True)
                text_lower = text.lower()
                if any(keyword in text_lower for keyword in ['frete grátis', 'frete gratis', 'prime', 'entrega grátis', 'entrega gratis', 'free shipping']):
                    shipping_text = text
                    shipping_element = shipping_el
                    data['frete_gratis'] = 'true'
                    data['texto_entrega'] = text
                    break
        
        # Se não encontrou, procura no texto geral (área de preço/pagamento)
        if not shipping_text:
            # Procura na área de buybox/pagamento
            buybox = soup.select_one('#buybox, [id*="buybox"], [class*="buybox"]')
            if buybox:
                buybox_text = buybox.get_text().lower()
                if any(keyword in buybox_text for keyword in ['frete grátis', 'frete gratis', 'prime', 'entrega grátis', 'free shipping']):
                    data['frete_gratis'] = 'true'
                    data['texto_entrega'] = 'Frete Grátis'
                elif any(keyword in buybox_text for keyword in ['frete', 'envio', 'entrega']):
                    data['frete_gratis'] = 'false'
                    data['texto_entrega'] = ''
                else:
                    data['frete_gratis'] = 'unknown'
                    data['texto_entrega'] = ''
            else:
                # Procura em toda a página
                page_text = soup.get_text().lower()
                if any(keyword in page_text for keyword in ['frete grátis', 'frete gratis', 'prime', 'entrega grátis', 'free shipping']):
                    data['frete_gratis'] = 'true'
                    data['texto_entrega'] = 'Frete Grátis'
                elif any(keyword in page_text for keyword in ['frete', 'envio', 'entrega']):
                    data['frete_gratis'] = 'false'
                    data['texto_entrega'] = ''
                else:
                    data['frete_gratis'] = 'unknown'
                    data['texto_entrega'] = ''
        
        # Detalhes de entrega (igual ao Mercado Livre)
        delivery_selectors = [
            '[id*="delivery"]',
            '[class*="delivery"]',
            '[class*="entrega"]',
            '[id*="deliveryMessage"]',
        ]
        
        delivery_details = None
        for selector in delivery_selectors:
            delivery_el = soup.select_one(selector)
            if delivery_el:
                delivery_text = delivery_el.get_text(strip=True)
                if delivery_text and len(delivery_text) > 5:
                    # Verifica se tem informações de data/dia
                    if any(word in delivery_text.lower() for word in ['segunda', 'terça', 'quarta', 'quinta', 'sexta', 'sábado', 'domingo', 'dia', 'receba', 'chegará', 'dezembro', 'janeiro', 'fevereiro', 'março', 'abril', 'maio', 'junho', 'julho', 'agosto', 'setembro', 'outubro', 'novembro']):
                        delivery_details = delivery_text
                        break
        
        if delivery_details:
            data['data_entrega_detalhes'] = delivery_details
            # Se não tem texto_entrega, usa os detalhes
            if not data.get('texto_entrega'):
                data['texto_entrega'] = delivery_details
        
        # Frete grátis detalhes (igual ao Mercado Livre)
        if shipping_element:
            shipping_full_text = shipping_element.get_text(strip=True)
            if shipping_full_text and shipping_full_text != data.get('texto_entrega'):
                # Procura por condições de frete grátis
                if any(keyword in shipping_full_text.lower() for keyword in ['acima de', 'a partir de', 'compras acima']):
                    data['frete_gratis_detalhes'] = shipping_full_text
        
        return data
