/**
 * Cliente para a API Python de comparação de preços
 */

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

export interface PythonProductData {
  plataforma: string;
  titulo: string;
  preco: number;
  moeda: string;
  imagem?: string;
  frete_gratis?: string;
  texto_entrega?: string;
  url_produto: string;
  data_coleta: string;
  parse_status?: string;
}

export interface PythonProductResponse {
  success: boolean;
  url?: string;
  data?: PythonProductData;
  error?: string;
}

export interface PythonSearchResponse {
  total_urls: number;
  successful: number;
  failed: number;
  products: PythonProductResponse[];
  warnings?: string[];
  produtos_por_plataforma?: Record<string, number>;
}

export interface PythonHistoryEntry {
  data_coleta: string;
  preco: number;
  moeda: string;
  plataforma: string;
  parse_status: string;
  titulo?: string;
}

/**
 * Busca produtos usando a API Python
 */
export async function searchProductsPython(
  query: string,
  platforms: string[] = ['amazon', 'mercadolivre']
): Promise<PythonSearchResponse> {
  const response = await fetch(`${API_BASE_URL}/search`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      query,
      platforms,
    }),
  });

  if (!response.ok) {
    throw new Error(`Erro na API: ${response.status} ${response.statusText}`);
  }

  return response.json();
}

/**
 * Compara preços de múltiplas URLs
 */
export async function compareProductsPython(
  urls: string[],
  use_cache: boolean = true
): Promise<PythonSearchResponse> {
  const response = await fetch(`${API_BASE_URL}/compare`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      urls,
      use_cache,
    }),
  });

  if (!response.ok) {
    throw new Error(`Erro na API: ${response.status} ${response.statusText}`);
  }

  return response.json();
}

/**
 * Obtém histórico de preços de um produto
 */
export async function getPriceHistoryPython(
  url: string,
  limit: number = 30
): Promise<PythonHistoryEntry[]> {
  const response = await fetch(
    `${API_BASE_URL}/history?url=${encodeURIComponent(url)}&limit=${limit}`
  );

  if (!response.ok) {
    throw new Error(`Erro na API: ${response.status} ${response.statusText}`);
  }

  return response.json();
}

/**
 * Converte dados da API Python para o formato Offer do frontend
 */
export function pythonProductToOffer(
  product: PythonProductResponse,
  sourceId?: string
): any {
  if (!product.success || !product.data) {
    return null;
  }

  const data = product.data;

  return {
    id: product.url || `python-${Date.now()}-${Math.random()}`,
    source_id: sourceId || null,
    external_id: product.url || null,
    title: data.titulo,
    description: null,
    image_url: data.imagem || null,
    store_name: data.plataforma,
    price: data.preco,
    original_price: null,
    currency: data.moeda || 'BRL',
    purchase_url: data.url_produto,
    shipping_cost: data.frete_gratis === 'true' ? 0 : null,
    shipping_info: data.texto_entrega || null,
    condition: 'new' as const,
    category: null,
    brand: null,
    rating: null,
    rating_count: null,
    in_stock: true,
    created_at: data.data_coleta,
    updated_at: data.data_coleta,
    // Campos extras da API Python
    _python_data: data,
    _parse_status: data.parse_status || 'ok',
  };
}

