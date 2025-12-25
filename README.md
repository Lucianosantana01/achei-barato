# Comparador de Preços - MVP

Backend em Python para comparação de preços coletando dados de páginas públicas de e-commerce e marketplaces.

## Características

- ✅ Extração de dados sem automação de navegador (apenas HTTP)
- ✅ Prioriza dados estruturados (JSON embutido, schema.org)
- ✅ Rate limiting por domínio (2-5 segundos)
- ✅ Cache em memória (10 minutos)
- ✅ Detecção de bloqueios (403/429)
- ✅ API REST com FastAPI

## Instalação

### Windows (PowerShell)

**Opção 1: Script automático (Recomendado)**
```powershell
.\instalar_python.ps1
```

**Opção 2: Manual**
1. Instale Python 3.11 ou 3.12:
   - Via Microsoft Store: Procure "Python 3.11" e instale
   - Ou baixe de https://www.python.org/downloads/
   - **IMPORTANTE**: Marque "Add Python to PATH" durante a instalação

2. Instale as dependências:
   ```powershell
   python -m pip install -r requirements.txt
   ```

**Se `pip` não funcionar, use:**
```powershell
python -m pip install -r requirements.txt
```

Veja `INSTALACAO.md` para mais detalhes sobre problemas de instalação.

## Uso

### Iniciar o servidor

```bash
python app.py
```

Ou com uvicorn diretamente:

```bash
uvicorn app:app --host 0.0.0.0 --port 8000
```

### Endpoint de comparação

```bash
curl -X POST "http://localhost:8000/compare" \
  -H "Content-Type: application/json" \
  -d '{
    "urls": [
      "https://www.mercadolivre.com.br/produto/123456",
      "https://www.mercadolivre.com.br/produto/789012"
    ],
    "use_cache": true
  }'
```

### Exemplo de resposta

```json
{
  "total_urls": 2,
  "successful": 2,
  "failed": 0,
  "products": [
    {
      "success": true,
      "url": "https://www.mercadolivre.com.br/produto/123456",
      "data": {
        "plataforma": "www.mercadolivre.com.br",
        "titulo": "Produto Exemplo",
        "preco": 68.34,
        "moeda": "BRL",
        "imagem": "https://...",
        "frete_gratis": "true",
        "texto_entrega": "Frete grátis",
        "url_produto": "https://www.mercadolivre.com.br/produto/123456",
        "data_coleta": "2024-01-15T10:30:00"
      }
    }
  ]
}
```

## Estrutura do Projeto

- `storage.py` - Cache em memória com TTL
- `fetcher.py` - Requisições HTTP com rate limiting
- `extractor.py` - Extração de dados (JSON primeiro, HTML fallback)
- `normalizer.py` - Normalização de preços e interpretação de frete
- `app.py` - API HTTP com FastAPI

## Estratégia de Extração

1. **Prioridade 1**: JSON embutido
   - Schema.org (`application/ld+json`)
   - Variáveis globais (`__NEXT_DATA__`, `__PRELOADED_STATE__`)

2. **Prioridade 2**: Seletores HTML simples
   - Apenas quando JSON não está disponível
   - Seletores semânticos e data-testid

## Campos Extraídos

- `plataforma` - Domínio da URL
- `titulo` - Nome do produto
- `preco` - Valor numérico
- `moeda` - Código da moeda (BRL, USD, etc)
- `imagem` - URL da imagem principal
- `frete_gratis` - true/false/unknown
- `texto_entrega` - Texto capturado sobre entrega
- `url_produto` - URL original
- `data_coleta` - Timestamp ISO

## Limitações

- Máximo de 50 URLs por requisição
- Cache em memória (não persiste entre execuções)
- Rate limiting básico (pode precisar ajuste por plataforma)

## Exemplo de Uso Programático

```python
from fetcher import Fetcher
from extractor import Extractor
from normalizer import Normalizer

fetcher = Fetcher()
extractor = Extractor()
normalizer = Normalizer()

url = "https://www.mercadolivre.com.br/produto/123456"
html = fetcher.fetch(url)
raw_data = extractor.extract(url, html)
normalized_data = normalizer.normalize(raw_data)

print(normalized_data)

# Não esqueça de fechar o fetcher
fetcher.close()
```

## Testes

Execute os testes básicos:

```bash
python test_basic.py
```

Teste com uma URL real do Mercado Livre:

```bash
python example_mercadolivre.py https://www.mercadolivre.com.br/produto/MLB1234567890
```

## Notas Importantes

- ⚠️ **Rate Limiting**: O sistema implementa delay de 2-5 segundos entre requisições ao mesmo domínio
- ⚠️ **Cache**: Dados são cacheados por 10 minutos por padrão
- ⚠️ **Bloqueios**: O sistema detecta HTTP 403 e 429 e lança exceções
- ⚠️ **User-Agent**: Usa User-Agent de navegador comum para evitar bloqueios básicos

