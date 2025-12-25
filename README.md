# Achei Barato - Comparador de Preços

Sistema completo de comparação de preços com backend Python (API) e frontend React (página de vendas).

## 📁 Estrutura do Projeto

```
├── backend/              # API Python (FastAPI)
│   ├── app.py           # API principal
│   ├── extractor.py     # Extração de dados
│   ├── fetcher.py       # Requisições HTTP
│   ├── list_scraper.py  # Scraping de listagens
│   ├── normalizer.py    # Normalização de dados
│   ├── storage.py       # Cache em memória
│   ├── price_history.py # Histórico de preços (SQLite)
│   └── requirements.txt # Dependências Python
│
├── frontend/             # Frontend React (página de vendas)
│   ├── src/             # Código fonte React
│   ├── public/            # Arquivos públicos
│   ├── package.json       # Dependências Node.js
│   └── vite.config.ts     # Configuração Vite
│
└── static/               # Interface web antiga (legado)
    ├── index.html
    ├── script.js
    └── style.css
```

## 🚀 Backend (API Python)

### Características

- ✅ Extração de dados sem automação de navegador (apenas HTTP)
- ✅ Prioriza dados estruturados (JSON embutido, schema.org)
- ✅ Rate limiting por domínio (2-5 segundos)
- ✅ Cache em memória (10 minutos)
- ✅ Detecção de bloqueios (403/429)
- ✅ API REST com FastAPI
- ✅ Processamento paralelo com ThreadPoolExecutor
- ✅ Histórico de preços com SQLite

### Instalação

```bash
# Instalar dependências Python
pip install -r requirements.txt
```

### Uso

```bash
# Iniciar servidor
python app.py

# Ou com uvicorn
uvicorn app:app --host 0.0.0.0 --port 8000
```

### Endpoints

- `POST /search` - Busca produtos em múltiplas plataformas
- `POST /compare` - Compara preços de múltiplas URLs
- `GET /history?url=<url>` - Histórico de preços de um produto
- `GET /health` - Health check
- `DELETE /cache` - Limpa cache

## 🎨 Frontend (React)

### Tecnologias

- Vite
- TypeScript
- React
- shadcn-ui
- Tailwind CSS
- Supabase

### Instalação

```bash
# Instalar dependências Node.js
npm install

# Iniciar servidor de desenvolvimento
npm run dev
```

### Build

```bash
npm run build
```

## 📊 Histórico de Preços

O sistema salva automaticamente snapshots de preços em SQLite:

- Salva apenas produtos com `success=true` e `preco != None`
- Ignora duplicatas (mesma URL dentro de 2 minutos)
- Endpoint `/history?url=<url>` retorna histórico ordenado

## 🔧 Configuração

### Variáveis de Ambiente

Crie um arquivo `.env` na raiz do projeto:

```env
# Supabase (se usar)
SUPABASE_URL=your_supabase_url
SUPABASE_ANON_KEY=your_supabase_key

# API Backend
API_URL=http://localhost:8000
```

## 📝 Notas Importantes

- ⚠️ **Rate Limiting**: Delay de 0.6-1.2s entre requisições ao mesmo domínio
- ⚠️ **Cache**: Dados são cacheados por 10 minutos por padrão
- ⚠️ **Bloqueios**: Sistema detecta HTTP 403/429 e captcha
- ⚠️ **Paralelismo**: Máximo 6 workers para /compare, 5 para detalhamento Amazon

## 📚 Documentação

- Backend API: Acesse `http://localhost:8000/docs` para documentação Swagger
- Frontend: Interface React em `http://localhost:5173` (Vite dev server)
