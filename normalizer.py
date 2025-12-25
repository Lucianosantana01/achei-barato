"""
Módulo de normalização de dados.
Usa IA apenas para normalização de preços e interpretação de texto de entrega.
"""
import re
from typing import Dict, Optional, Any, Tuple, List


class Normalizer:
    """Normaliza e interpreta dados extraídos."""
    
    def normalize(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Normaliza dados do produto.
        
        Args:
            data: Dicionário com dados brutos extraídos
            
        Returns:
            Dicionário com dados normalizados
        """
        normalized = data.copy()
        
        # Normaliza preço
        if 'preco' in normalized:
            normalized['preco'] = self._normalize_price(normalized['preco'])
        
        # Normaliza moeda
        if 'moeda' in normalized:
            normalized['moeda'] = self._normalize_currency(normalized['moeda'])
        
        # Interpreta frete
        if 'texto_entrega' in normalized:
            normalized['frete_gratis'] = self._interpret_frete(normalized['texto_entrega'])
        else:
            normalized['frete_gratis'] = 'unknown'
            normalized['texto_entrega'] = ''
        
        # Preserva dados de parcelamento (garante que não sejam perdidos)
        parcelamento_fields = [
            'parcelamento_numero',
            'parcelamento_valor',
            'parcelamento_juros',
            'preco_parcelado',
            'preco_total_parcelado',
        ]
        
        for field in parcelamento_fields:
            if field in data and data[field] is not None:
                normalized[field] = data[field]
        
        # Determina parse_status e missing_fields
        normalized['parse_status'], normalized['missing_fields'] = self._determine_parse_status(normalized)
        
        return normalized
    
    def _determine_parse_status(self, data: Dict[str, Any]) -> Tuple[str, List[str]]:
        """
        Determina o status do parsing e campos faltando.
        
        Returns:
            Tupla (parse_status, missing_fields)
        """
        missing_fields = []
        
        # Campos essenciais
        essential_fields = {
            'titulo': 'Título',
            'preco': 'Preço',
            'url_produto': 'URL do produto'
        }
        
        # Verifica campos essenciais
        for field, name in essential_fields.items():
            if not data.get(field):
                missing_fields.append(name)
        
        # Verifica se foi bloqueado (detectado no extractor ou fetcher)
        if data.get('parse_status') == 'blocked':
            return ('blocked', missing_fields)
        
        if data.get('parse_status') == 'error':
            return ('error', missing_fields)
        
        # Se tem título, preço e URL, está ok
        if data.get('titulo') and data.get('preco') and data.get('url_produto'):
            # Verifica campos importantes (mas não essenciais)
            important_fields = {
                'imagem': 'Imagem',
                'frete_gratis': 'Informação de frete'
            }
            
            for field, name in important_fields.items():
                if not data.get(field) or (field == 'frete_gratis' and data.get(field) == 'unknown'):
                    missing_fields.append(name)
            
            if missing_fields:
                return ('partial', missing_fields)
            else:
                return ('ok', [])
        else:
            # Falta algo essencial
            return ('partial', missing_fields)
    
    def _normalize_price(self, price: Any) -> Optional[float]:
        """
        Normaliza preço para valor numérico.
        Pode usar IA se necessário, mas tenta primeiro métodos simples.
        """
        if price is None:
            return None
        
        if isinstance(price, (int, float)):
            return float(price)
        
        if isinstance(price, str):
            # Remove espaços e caracteres especiais
            cleaned = price.strip()
            
            # Padrões comuns: "R$ 68,34", "68.34", "R$68,34", etc.
            # Remove símbolos de moeda
            cleaned = re.sub(r'[R$€$£¥]', '', cleaned, flags=re.IGNORECASE)
            cleaned = cleaned.strip()
            
            # Remove espaços
            cleaned = cleaned.replace(' ', '')
            
            # Detecta formato brasileiro (vírgula como decimal)
            if ',' in cleaned and '.' in cleaned:
                # Tem ambos: remove pontos (milhares) e substitui vírgula
                cleaned = cleaned.replace('.', '').replace(',', '.')
            elif ',' in cleaned:
                # Só vírgula: verifica se é decimal ou milhar
                parts = cleaned.split(',')
                if len(parts) == 2 and len(parts[1]) <= 2:
                    # Provavelmente decimal
                    cleaned = cleaned.replace(',', '.')
                else:
                    # Provavelmente milhar, remove vírgula
                    cleaned = cleaned.replace(',', '')
            
            try:
                return float(cleaned)
            except ValueError:
                # Se falhar, tenta extrair apenas números
                numbers = re.findall(r'\d+', cleaned)
                if numbers:
                    # Concatena todos os números e divide por 100 se parecer centavos
                    num_str = ''.join(numbers)
                    if len(num_str) > 2 and num_str[-2:] == '00':
                        return float(num_str[:-2] + '.' + num_str[-2:])
                    return float(num_str)
        
        return None
    
    def _normalize_currency(self, currency: Any) -> str:
        """Normaliza código de moeda."""
        if not currency:
            return 'BRL'  # Default para Brasil
        
        currency_str = str(currency).strip().upper()
        
        # Mapeamento comum
        currency_map = {
            'R$': 'BRL',
            'REAL': 'BRL',
            'REAIS': 'BRL',
            'BRL': 'BRL',
            'USD': 'USD',
            'EUR': 'EUR',
            'EUR€': 'EUR',
            'GBP': 'GBP',
            'ARS': 'ARS',
        }
        
        return currency_map.get(currency_str, currency_str[:3] if len(currency_str) >= 3 else 'BRL')
    
    def _interpret_frete(self, texto_entrega: str) -> str:
        """
        Interpreta texto de entrega para determinar se frete é grátis.
        Usa regras simples, pode ser estendido com IA se necessário.
        
        Returns:
            'true', 'false', ou 'unknown'
        """
        if not texto_entrega:
            return 'unknown'
        
        texto_lower = texto_entrega.lower()
        
        # Palavras-chave para frete grátis
        gratis_keywords = [
            'frete grátis',
            'frete gratis',
            'frete gratuito',
            'entrega grátis',
            'entrega gratis',
            'entrega gratuita',
            'envio grátis',
            'envio gratis',
            'envio gratuito',
            'free shipping',
            'frete zero',
            'sem frete',
            'sem custo de envio',
        ]
        
        # Palavras-chave para frete pago
        pago_keywords = [
            'frete a partir de',
            'frete de',
            'custo de envio',
            'taxa de entrega',
            'valor do frete',
            'calcular frete',
            'consulte o frete',
        ]
        
        # Verifica frete grátis
        for keyword in gratis_keywords:
            if keyword in texto_lower:
                return 'true'
        
        # Verifica frete pago (se menciona valores)
        if any(keyword in texto_lower for keyword in pago_keywords):
            # Se menciona valores numéricos, provavelmente é pago
            if re.search(r'\d+[.,]\d+', texto_entrega):
                return 'false'
        
        # Se menciona valores mas não tem keywords de grátis, assume pago
        if re.search(r'[R$]\s*\d+', texto_entrega, re.IGNORECASE):
            return 'false'
        
        return 'unknown'


