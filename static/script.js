const API_URL = 'http://localhost:8000';

// Estado da aplicação
let currentQuery = '';
let currentFilters = {
    category: '',
    minPrice: null,
    maxPrice: null,
    condition: [],
    ram: '',
    storage: '',
    freeShipping: false,
    full: false,
    sort: 'relevance',
    zipCode: ''
};

// Controle de requisições concorrentes
let currentSearchController = null;
let isSearching = false;

// Elementos DOM
const mainSearchInput = document.getElementById('mainSearchInput');
const mainSearchBtn = document.getElementById('mainSearchBtn');
const searchSuggestions = document.getElementById('searchSuggestions');
const sidebar = document.getElementById('sidebar');
const sidebarToggle = document.getElementById('sidebarToggle');
const sidebarClose = document.getElementById('sidebarClose');
const results = document.getElementById('results');
const resultsContent = document.getElementById('resultsContent');
const resultsTitle = document.getElementById('resultsTitle');
const loading = document.getElementById('loading');
const errorDiv = document.getElementById('error');
const emptyState = document.getElementById('emptyState');

// Filtros
const filterCategory = document.getElementById('filterCategory');
const filterMinPrice = document.getElementById('filterMinPrice');
const filterMaxPrice = document.getElementById('filterMaxPrice');
const filterConditionNew = document.getElementById('filterConditionNew');
const filterConditionUsed = document.getElementById('filterConditionUsed');
const filterConditionRefurbished = document.getElementById('filterConditionRefurbished');
const filterRam = document.getElementById('filterRam');
const filterStorage = document.getElementById('filterStorage');
const filterFreeShipping = document.getElementById('filterFreeShipping');
const filterFull = document.getElementById('filterFull');
const filterSort = document.getElementById('filterSort');
const filterZipCode = document.getElementById('filterZipCode');
const applyFiltersBtn = document.getElementById('applyFiltersBtn');
const clearFiltersBtn = document.getElementById('clearFiltersBtn');

// Event Listeners
mainSearchBtn.addEventListener('click', performSearch);
mainSearchInput.addEventListener('keypress', (e) => {
    if (e.key === 'Enter') performSearch();
});

// Sugestões de busca
searchSuggestions.addEventListener('click', (e) => {
    if (e.target.classList.contains('suggestion-chip')) {
        const query = e.target.getAttribute('data-query');
        mainSearchInput.value = query;
        performSearch();
    }
});

// Sidebar toggle
sidebarToggle.addEventListener('click', () => {
    sidebar.classList.add('open');
});

sidebarClose.addEventListener('click', () => {
    sidebar.classList.remove('open');
});

// Filtros
applyFiltersBtn.addEventListener('click', () => {
    collectFilters();
    if (currentQuery) {
        performSearch();
    } else {
        showError('Digite um termo de busca primeiro');
    }
});

clearFiltersBtn.addEventListener('click', () => {
    clearFilters();
    if (currentQuery) {
        performSearch();
    }
});

// Coleta filtros do formulário
function collectFilters() {
    currentFilters = {
        category: filterCategory.value,
        minPrice: filterMinPrice.value ? parseFloat(filterMinPrice.value) : null,
        maxPrice: filterMaxPrice.value ? parseFloat(filterMaxPrice.value) : null,
        condition: [],
        ram: filterRam.value,
        storage: filterStorage.value,
        freeShipping: filterFreeShipping.checked,
        full: filterFull.checked,
        sort: filterSort.value,
        zipCode: filterZipCode.value.replace(/\D/g, '')
    };
    
    // Coleta condições selecionadas
    if (filterConditionNew.checked) currentFilters.condition.push('new');
    if (filterConditionUsed.checked) currentFilters.condition.push('used');
    if (filterConditionRefurbished.checked) currentFilters.condition.push('refurbished');
}

// Limpa filtros
function clearFilters() {
    filterCategory.value = '';
    filterMinPrice.value = '';
    filterMaxPrice.value = '';
    filterConditionNew.checked = false;
    filterConditionUsed.checked = false;
    filterConditionRefurbished.checked = false;
    filterRam.value = '';
    filterStorage.value = '';
    filterFreeShipping.checked = false;
    filterFull.checked = false;
    filterSort.value = 'relevance';
    filterZipCode.value = '';
    
    currentFilters = {
        category: '',
        minPrice: null,
        maxPrice: null,
        condition: [],
        ram: '',
        storage: '',
        freeShipping: false,
        full: false,
        sort: 'relevance',
        zipCode: ''
    };
}

// Realiza busca
async function performSearch() {
    const query = mainSearchInput.value.trim();
    if (!query) {
        showError('Por favor, digite um termo de busca');
        return;
    }
    
    // Cancela requisição anterior se existir
    if (currentSearchController) {
        currentSearchController.abort();
    }
    
    // Previne requisições concorrentes
    if (isSearching) {
        return;
    }
    
    isSearching = true;
    
    // LIMPEZA AGRESSIVA: Remove TODOS os resultados anteriores ANTES de iniciar nova busca
    // Remove todos os filhos do container de resultados
    while (resultsContent.firstChild) {
        resultsContent.removeChild(resultsContent.firstChild);
    }
    resultsContent.innerHTML = ''; // Garantia extra
    
    // Esconde todos os elementos de resultado
    results.classList.add('hidden');
    emptyState.classList.add('hidden');
    errorDiv.classList.add('hidden');
    
    // Resetar estatísticas
    document.getElementById('statTotal').textContent = '0';
    document.getElementById('statSuccess').textContent = '0';
    document.getElementById('statFailed').textContent = '0';
    
    // Desabilitar botão de busca durante carregamento
    mainSearchBtn.disabled = true;
    mainSearchBtn.textContent = 'Buscando...';
    
    currentQuery = query;
    collectFilters();
    
    loading.classList.remove('hidden');
    
    // Cria novo AbortController para esta requisição
    currentSearchController = new AbortController();
    const signal = currentSearchController.signal;
    
    try {
        // Prepara payload com filtros
        const payload = {
            query: query,
            max_paginas: 1,
            max_produtos: 20,
            filters: currentFilters
        };
        
        const response = await fetch(`${API_URL}/search`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(payload),
            signal: signal // Permite cancelar a requisição
        });
        
        if (!response.ok) {
            throw new Error(`Erro HTTP: ${response.status}`);
        }
        
        const data = await response.json();
        
        // Debug: log dados recebidos
        const plataformasAntes = data.products?.map(p => p.data?.plataforma || 'sem plataforma').reduce((acc, p) => {
            acc[p] = (acc[p] || 0) + 1;
            return acc;
        }, {}) || {};
        
        // Verifica se a requisição foi cancelada
        if (signal.aborted) {
            return;
        }
        
        // LIMPEZA FINAL antes de exibir novos resultados
        resultsContent.innerHTML = '';
        
        // Aplica filtros client-side como refinamento
        const filteredData = applyClientSideFilters(data, query);
        
        
        // Verifica novamente se não foi cancelada
        if (signal.aborted) {
            return;
        }
        
        displayResults(filteredData, query);
        
    } catch (error) {
        // Ignora erros de cancelamento
        if (error.name === 'AbortError') {
            return;
        }
        showError(`Erro ao buscar produtos: ${error.message}. Certifique-se de que o servidor está rodando em ${API_URL}`);
    } finally {
        // Reabilitar botão de busca
        mainSearchBtn.disabled = false;
        mainSearchBtn.textContent = 'Buscar';
        loading.classList.add('hidden');
        isSearching = false;
        currentSearchController = null;
    }
}

// Função auxiliar para normalizar texto (lower-case + remover acentos)
function normalizeText(text) {
    if (!text) return '';
    return text.toLowerCase()
        .trim()
        .normalize('NFD')
        .replace(/[\u0300-\u036f]/g, '')
        .replace(/\s+/g, ' '); // Normaliza espaços múltiplos
}

// Aplica filtros client-side (refinamento após receber resultados)
function applyClientSideFilters(data, query) {
    if (!data.products || data.products.length === 0) {
        return data;
    }
    
    // Cria tokens da query: lower-case, remover acentos, split por espaço
    // Ignora tokens com menos de 3 caracteres
    const queryTokens = query
        ? normalizeText(query)
            .split(/\s+/)
            .filter(token => token.length >= 3)
        : [];
    
    
    let filteredProducts = data.products.filter(product => {
        // FILTRO DE RELEVÂNCIA POR TERMO (aplicado ANTES dos outros filtros)
        if (queryTokens.length > 0) {
            // Para produtos com success=true: verifica se título contém pelo menos 1 token
            if (product.success && product.data) {
                const title = product.data.titulo || '';
                if (!title || title.trim().length === 0) {
                    // Se não tem título, mantém o produto (pode ser relevante)
                    return true;
                }
                const normalizedTitle = normalizeText(title);
                // Testa cada token individualmente para debug
                const tokenMatches = queryTokens.map(token => ({
                    token: token,
                    encontrado: normalizedTitle.includes(token),
                    posicao: normalizedTitle.indexOf(token)
                }));
                const hasRelevantToken = queryTokens.some(token => 
                    normalizedTitle.includes(token)
                );
                if (!hasRelevantToken) {
                    return false; // Descarta produto irrelevante
                }
            } else {
                // Para produtos com success=false (erros): remove todos quando há filtro de relevância
                // (não podemos verificar relevância sem título)
                return false;
            }
        }
        
        // Se chegou aqui e não tem success/data, mantém (apenas se não houver filtro de relevância)
        if (!product.success || !product.data) return true;
        
        const p = product.data;
        
        // Filtro de preço (client-side como refinamento)
        if (currentFilters.minPrice !== null && p.preco !== null && p.preco < currentFilters.minPrice) {
            return false;
        }
        if (currentFilters.maxPrice !== null && p.preco !== null && p.preco > currentFilters.maxPrice) {
            return false;
        }
        
        // Filtro de RAM
        if (currentFilters.ram) {
            const title = (p.titulo || '').toLowerCase();
            const ramValue = currentFilters.ram.replace('gb', '').toLowerCase();
            // Procura por padrões como "8gb ram", "8 gb", "8gb de ram", etc.
            const ramPattern = new RegExp(`\\b${ramValue}\\s*(gb|gb\\s*ram|gb\\s*de\\s*ram)\\b`, 'i');
            if (!ramPattern.test(title)) {
                return false;
            }
        }
        
        // Filtro de Armazenamento
        if (currentFilters.storage) {
            const title = (p.titulo || '').toLowerCase();
            const storageValue = currentFilters.storage.replace('gb', '').replace('tb', '').toLowerCase();
            const storageUnit = currentFilters.storage.includes('tb') ? 'tb' : 'gb';
            
            // Padrões mais flexíveis: aceita "512gb", "512 gb", "512GB", "512ssd", "512 ssd", "512gb ssd", etc.
            // Procura pelo número seguido de espaço opcional e depois gb/tb/ssd/hd
            const patterns = [
                new RegExp(`\\b${storageValue}\\s*${storageUnit}\\b`, 'i'), // 512gb, 512 gb
                new RegExp(`\\b${storageValue}\\s*ssd\\b`, 'i'), // 512ssd, 512 ssd
                new RegExp(`\\b${storageValue}\\s*hd\\b`, 'i'), // 512hd, 512 hd
                new RegExp(`\\b${storageValue}\\s*${storageUnit}\\s*ssd\\b`, 'i'), // 512gb ssd
                new RegExp(`\\b${storageValue}\\s*${storageUnit}\\s*hd\\b`, 'i'), // 512gb hd
            ];
            
            // Verifica se algum padrão corresponde
            const matches = patterns.some(pattern => pattern.test(title));
            if (!matches) {
                return false;
            }
        }
        
        // Filtro de frete grátis
        if (currentFilters.freeShipping && p.frete_gratis !== 'true') {
            return false;
        }
        
        return true;
    });
    
    // Ordenação client-side (se necessário)
    if (currentFilters.sort === 'price_asc') {
        filteredProducts.sort((a, b) => {
            if (!a.success || !a.data || !a.data.preco) return 1;
            if (!b.success || !b.data || !b.data.preco) return -1;
            return a.data.preco - b.data.preco;
        });
    } else if (currentFilters.sort === 'price_desc') {
        filteredProducts.sort((a, b) => {
            if (!a.success || !a.data || !a.data.preco) return 1;
            if (!b.success || !b.data || !b.data.preco) return -1;
            return b.data.preco - a.data.preco;
        });
    }
    
    return {
        ...data,
        products: filteredProducts,
        total_urls: filteredProducts.length,
        successful: filteredProducts.filter(p => p.success).length,
        failed: filteredProducts.filter(p => !p.success).length
    };
}

// Exibe resultados
function displayResults(data, query) {
    // LIMPEZA AGRESSIVA: Remove TODOS os resultados anteriores (SUBSTITUI, nunca concatena)
    // Remove todos os nós filhos primeiro
    while (resultsContent.firstChild) {
        resultsContent.removeChild(resultsContent.firstChild);
    }
    // Depois limpa o innerHTML como garantia extra
    resultsContent.innerHTML = '';
    
    // Verifica se a query ainda é a atual (evita mostrar resultados de busca antiga)
    if (query !== currentQuery) {
        console.log('Resultado ignorado - query mudou:', query, '!=', currentQuery);
        return;
    }
    
    // Atualiza título
    resultsTitle.textContent = `Resultados para "${query}"`;
    
    // Atualiza estatísticas
    document.getElementById('statTotal').textContent = data.total_urls || 0;
    document.getElementById('statSuccess').textContent = data.successful || 0;
    document.getElementById('statFailed').textContent = data.failed || 0;
    
    // Exibe warnings se existirem (no topo, antes dos produtos)
    if (data.warnings && data.warnings.length > 0) {
        data.warnings.forEach(warning => {
            const warningDiv = document.createElement('div');
            warningDiv.className = 'warning-message';
            // Destaque especial para bloqueios da Amazon
            const isAmazonBlock = warning.toLowerCase().includes('amazon') && 
                                 (warning.toLowerCase().includes('bloqueio') || 
                                  warning.toLowerCase().includes('captcha') ||
                                  warning.toLowerCase().includes('indisponível') ||
                                  warning.toLowerCase().includes('indisponivel') ||
                                  warning.toLowerCase().includes('403') || 
                                  warning.toLowerCase().includes('429'));
            const bgColor = isAmazonBlock ? '#f8d7da' : '#fff3cd';
            const textColor = isAmazonBlock ? '#721c24' : '#856404';
            const borderColor = isAmazonBlock ? '#dc3545' : '#ffc107';
            warningDiv.style.cssText = `background: ${bgColor}; color: ${textColor}; padding: 12px; margin-bottom: 12px; border-radius: 8px; border-left: 4px solid ${borderColor}; font-weight: ${isAmazonBlock ? 'bold' : 'normal'};`;
            warningDiv.textContent = `⚠️ ${warning}`;
            resultsContent.appendChild(warningDiv);
            // Log no console também
            console.warn('⚠️ Warning:', warning);
        });
    }
    
    // Se não há produtos, mostra empty state
    if (data.total_urls === 0 || !data.products || data.products.length === 0) {
        emptyState.classList.remove('hidden');
        results.classList.add('hidden');
        return;
    }
    
    emptyState.classList.add('hidden');
    
    // Adiciona produtos (SUBSTITUI conteúdo anterior, NUNCA concatena)
    // Usa DocumentFragment para melhor performance
    const fragment = document.createDocumentFragment();
    data.products.forEach(product => {
        const card = createProductCard(product);
        fragment.appendChild(card);
    });
    resultsContent.appendChild(fragment);
    
    results.classList.remove('hidden');
}

// Cria card de produto
function createProductCard(product) {
    const card = document.createElement('div');
    card.className = `product-card ${!product.success ? 'error' : ''}`;
    
    if (!product.success) {
        card.innerHTML = `
            <div class="product-card-content">
                <div class="product-info">
                    <div class="product-header">
                        <div class="product-title">Erro ao processar produto</div>
                    </div>
                    <div class="product-details">
                        <div class="detail-item">
                            <div class="detail-label">URL</div>
                            <div class="detail-value">${product.url}</div>
                        </div>
                        <div class="detail-item">
                            <div class="detail-label">Erro</div>
                            <div class="detail-value" style="color: var(--danger)">${product.error}</div>
                        </div>
                    </div>
                </div>
            </div>
        `;
        return card;
    }
    
    const data = product.data;
    const freteClass = data.frete_gratis === 'true' ? 'frete-gratis' : 
                      data.frete_gratis === 'false' ? 'frete-pago' : 'frete-unknown';
    const freteText = data.frete_gratis === 'true' ? 'Frete Grátis' : 
                     data.frete_gratis === 'false' ? 'Frete Pago' : 'Desconhecido';
    
    // Detecta se é Mercado Livre
    const isMercadoLivre = data.plataforma && (
        data.plataforma.toLowerCase().includes('mercadolivre') || 
        data.plataforma.toLowerCase().includes('mercadolivre.com.br') ||
        data.url_produto && data.url_produto.toLowerCase().includes('mercadolivre')
    );
    
    // Detecta se é Amazon
    const isAmazon = data.plataforma && (
        data.plataforma.toLowerCase().includes('amazon') || 
        data.plataforma.toLowerCase().includes('amazon.com.br') ||
        data.url_produto && data.url_produto.toLowerCase().includes('amazon')
    );
    
    // Formata preço - estilo Mercado Livre (simplificado)
    let priceHtml = '';
    if (data.preco) {
        const moeda = data.moeda || 'BRL';
        // Formata preço com separador de milhares
        const precoFormatado = data.preco.toFixed(2).replace('.', ',').replace(/\B(?=(\d{3})+(?!\d))/g, '.');
        const precoAnteriorHtml = data.preco_anterior ? `
            <div class="price-previous">
                <s>R$ ${data.preco_anterior.toFixed(2).replace('.', ',').replace(/\B(?=(\d{3})+(?!\d))/g, '.')}</s>
            </div>
        ` : '';
        const descontoHtml = data.desconto_percentual ? `
            <span class="discount-badge">${data.desconto_percentual}% OFF</span>
        ` : '';
        
        priceHtml = `
            <div class="price-section">
                ${precoAnteriorHtml}
                <div class="price-current-row">
                    <div class="price-value">
                        <span class="price-currency">${moeda === 'BRL' ? 'R$' : moeda}</span>
                        ${precoFormatado}
                    </div>
                    ${descontoHtml}
                </div>
            </div>
        `;
    } else {
        priceHtml = `
            <div class="price-section">
                <div class="price-value" style="color: var(--text-muted); font-size: 16px;">Não disponível</div>
            </div>
        `;
    }
    
    // Parcelamento - melhorado para capturar mais casos
    let installmentHtml = '';
    let precisaoNotificacao = '';
    
    // Tenta calcular valor da parcela se não tiver mas tiver número de parcelas e preço
    if (data.parcelamento_numero) {
        // PRIORIDADE 1: parcelamento_valor (valor direto da extração - MAIS PRECISO)
        let parcelValor = data.parcelamento_valor;
        
        // PRIORIDADE 2: Se tem preco_parcelado, calcula dele (se não tiver parcelamento_valor)
        if (!parcelValor && data.preco_parcelado && data.parcelamento_numero) {
            parcelValor = data.preco_parcelado / data.parcelamento_numero;
        }
        
        // PRIORIDADE 3: Se tem preco_total_parcelado, calcula dele (se não tiver os anteriores)
        if (!parcelValor && data.preco_total_parcelado && data.parcelamento_numero) {
            parcelValor = data.preco_total_parcelado / data.parcelamento_numero;
        }
        
        // PRIORIDADE 4: Último recurso - calcula do preço à vista (só se não tiver nenhum dos anteriores)
        if (!parcelValor && !data.preco_parcelado && !data.preco_total_parcelado && data.preco && data.parcelamento_numero) {
            parcelValor = data.preco / data.parcelamento_numero;
        }
        
        // Validação: valor da parcela deve ser razoável (entre 1 e 10000)
        if (parcelValor && (parcelValor < 1 || parcelValor > 10000)) {
            parcelValor = null;
        }
        
        // Verifica precisão e adiciona notificação se necessário
        // REGRA: Mostra notificação quando:
        // 1. Precisão <= 99% (99% ou menos - inclui 99% exato)
        // 2. E o valor parcelado é menor que o valor à vista
        if (data.precisao_parcelamento !== null && data.precisao_parcelamento !== undefined) {
            // Calcula valor total parcelado para comparar com preço à vista
            const valorTotalParcelado = parcelValor && data.parcelamento_numero 
                ? parcelValor * data.parcelamento_numero 
                : (data.preco_parcelado || data.preco_total_parcelado);
            
            // Verifica se valor parcelado é menor que preço à vista
            const parceladoMenorQueVista = data.preco && valorTotalParcelado 
                ? valorTotalParcelado < data.preco 
                : false;
            
            // Mostra notificação se precisão <= 99% E parcelado < à vista
            // IMPORTANTE: Inclui 99% exato, pois ainda indica diferença
            if (data.precisao_parcelamento <= 99 && parceladoMenorQueVista) {
                const precisaoFormatada = data.precisao_parcelamento.toFixed(1);
                precisaoNotificacao = `
                    <div class="precision-warning" title="Valores podem ter diferença. Precisão: ${data.precisao_parcelamento.toFixed(2)}%">
                        <span class="precision-icon">⚠️</span>
                        <span class="precision-text">Precisão: ${precisaoFormatada}%</span>
                    </div>
                `;
            }
        }
        
        if (parcelValor) {
            const parcelValorFormatado = parcelValor.toFixed(2).replace('.', ',').replace(/\B(?=(\d{3})+(?!\d))/g, '.');
            const jurosText = data.parcelamento_juros === false ? ' sem juros' : (data.parcelamento_juros === true ? ' com juros' : '');
            
            // Mostra o parcelamento
            // Se tem preço parcelado diferente do preço à vista, mostra "ou R$ X em Yx"
            let precoParceladoInfo = '';
            const precoParceladoParaMostrar = data.preco_parcelado || data.preco_total_parcelado;
            if (precoParceladoParaMostrar && data.preco && precoParceladoParaMostrar !== data.preco) {
                const precoParceladoFormatado = precoParceladoParaMostrar.toFixed(2).replace('.', ',').replace(/\B(?=(\d{3})+(?!\d))/g, '.');
                precoParceladoInfo = ` ou R$ ${precoParceladoFormatado} em ${data.parcelamento_numero}x`;
            }
            
            installmentHtml = `
                <div class="installment-section">
                    <span class="installment-text">${data.parcelamento_numero}x de R$ ${parcelValorFormatado}${jurosText}${precoParceladoInfo}</span>
                    ${precisaoNotificacao}
                </div>
            `;
        } else if (data.parcelamento_numero && (data.preco_parcelado || data.preco_total_parcelado)) {
            // Se só tem número de parcelas e preço parcelado, calcula dele
            const precoParaCalcular = data.preco_parcelado || data.preco_total_parcelado;
            const parcelValorCalculado = (precoParaCalcular / data.parcelamento_numero).toFixed(2).replace('.', ',').replace(/\B(?=(\d{3})+(?!\d))/g, '.');
            installmentHtml = `
                <div class="installment-section">
                    <span class="installment-text">${data.parcelamento_numero}x de R$ ${parcelValorCalculado}</span>
                </div>
            `;
        } else if (data.parcelamento_numero && data.preco) {
            // Último recurso: se só tem número de parcelas e preço à vista
            const parcelValorCalculado = (data.preco / data.parcelamento_numero).toFixed(2).replace('.', ',').replace(/\B(?=(\d{3})+(?!\d))/g, '.');
            installmentHtml = `
                <div class="installment-section">
                    <span class="installment-text">${data.parcelamento_numero}x de R$ ${parcelValorCalculado}</span>
                </div>
            `;
        }
    }
    
    // Número de vendas
    let salesHtml = '';
    if (data.num_vendas) {
        salesHtml = `
            <div class="sales-badge">
                +${data.num_vendas} vendidos
            </div>
        `;
    }
    
    // HTML do card
    card.innerHTML = `
        <div class="product-card-content">
            ${isMercadoLivre ? `
                <div class="platform-badge mercado-livre-badge">
                    <img src="https://jlrgspohnhtxbxdhvtpk.supabase.co/storage/v1/object/public/ImagensBarateiro/mercadolivre-removebg-preview.png" 
                         alt="Mercado Livre" 
                         class="ml-logo">
                </div>
            ` : ''}
            ${isAmazon ? `
                <div class="platform-badge amazon-badge">
                    <img src="https://jlrgspohnhtxbxdhvtpk.supabase.co/storage/v1/object/public/ImagensBarateiro/amazonimagen-removebg-preview.png" 
                         alt="Amazon" 
                         class="amazon-logo">
                </div>
            ` : ''}
            
            ${data.imagem ? `
                <div class="product-image-container">
                    <img src="${data.imagem}" alt="${data.titulo || 'Produto'}" class="product-image" onerror="this.parentElement.innerHTML='<div style=\'color: var(--text-muted); font-size: 12px;\'>Sem imagem</div>'">
                </div>
            ` : `
                <div class="product-image-container" style="color: var(--text-muted); font-size: 12px; display: flex; align-items: center; justify-content: center;">
                    Sem imagem
                </div>
            `}
            
            <div class="product-info">
                <div class="product-header">
                    <div class="product-title-row">
                        <div class="product-title">${data.titulo || 'Sem título'}</div>
                    </div>
                    ${salesHtml}
                </div>
                
                ${priceHtml}
                ${installmentHtml}
                
                <div class="product-badges">
                    ${data.loja_oficial ? '<span class="official-badge">✓ Loja Oficial</span>' : ''}
                    ${data.frete_gratis === 'true' ? '<span class="frete-gratis-badge">Frete Grátis</span>' : ''}
                </div>
                
                ${data.frete_gratis_detalhes && data.frete_gratis_detalhes !== 'FRETE GRÁTIS' ? `
                    <div class="shipping-details">
                        <span class="shipping-badge">${data.frete_gratis_detalhes}</span>
                    </div>
                ` : ''}
                
                ${data.data_entrega_detalhes ? `
                    <div class="delivery-details">
                        <span class="delivery-text">${data.data_entrega_detalhes}</span>
                    </div>
                ` : ''}
                
                ${data.full_fulfillment ? `
                    <div class="full-fulfillment">
                        <span class="full-badge">⚡ ${data.full_fulfillment}</span>
                    </div>
                ` : ''}
                
                <div class="product-actions">
                    <a href="${data.url_produto}" target="_blank" class="product-link">
                        Ver produto original →
                    </a>
                    <button class="history-btn" onclick="showPriceHistory('${data.url_produto}')" title="Ver histórico de preços">
                        📊 Histórico
                    </button>
                </div>
            </div>
        </div>
    `;
    
    return card;
}

// Modal de histórico de preços
function showPriceHistory(url) {
    // Cria modal se não existir
    let modal = document.getElementById('historyModal');
    if (!modal) {
        modal = document.createElement('div');
        modal.id = 'historyModal';
        modal.className = 'history-modal';
        modal.innerHTML = `
            <div class="history-modal-content">
                <div class="history-modal-header">
                    <h3>Histórico de Preços</h3>
                    <button class="history-modal-close" onclick="closePriceHistory()">×</button>
                </div>
                <div class="history-modal-body" id="historyModalBody">
                    <div class="loading">Carregando histórico...</div>
                </div>
            </div>
        `;
        document.body.appendChild(modal);
        
        // Fecha ao clicar fora
        modal.addEventListener('click', (e) => {
            if (e.target === modal) {
                closePriceHistory();
            }
        });
    }
    
    // Mostra modal
    modal.style.display = 'flex';
    document.getElementById('historyModalBody').innerHTML = '<div class="loading">Carregando histórico...</div>';
    
    // Busca histórico
    fetch(`${API_URL}/history?url=${encodeURIComponent(url)}&limit=30`)
        .then(response => response.json())
        .then(data => {
            const body = document.getElementById('historyModalBody');
            
            if (!data.history || data.history.length === 0) {
                body.innerHTML = `
                    <div class="history-empty">
                        <p>Nenhum histórico disponível para este produto.</p>
                        <p class="history-empty-hint">O histórico será criado automaticamente após algumas buscas.</p>
                    </div>
                `;
                return;
            }
            
            // Formata histórico
            let historyHtml = '<div class="history-list">';
            data.history.forEach(item => {
                const date = new Date(item.data_coleta);
                const dateStr = date.toLocaleString('pt-BR', {
                    day: '2-digit',
                    month: '2-digit',
                    year: 'numeric',
                    hour: '2-digit',
                    minute: '2-digit'
                });
                
                const precoFormatado = item.preco.toFixed(2).replace('.', ',').replace(/\B(?=(\d{3})+(?!\d))/g, '.');
                const moeda = item.moeda === 'BRL' ? 'R$' : item.moeda;
                
                historyHtml += `
                    <div class="history-item">
                        <div class="history-date">${dateStr}</div>
                        <div class="history-price">${moeda} ${precoFormatado}</div>
                        <div class="history-platform">${item.plataforma}</div>
                    </div>
                `;
            });
            historyHtml += '</div>';
            
            body.innerHTML = `
                <div class="history-summary">
                    <p>Total de registros: ${data.total}</p>
                </div>
                ${historyHtml}
            `;
        })
        .catch(error => {
            document.getElementById('historyModalBody').innerHTML = `
                <div class="history-error">
                    <p>Erro ao carregar histórico: ${error.message}</p>
                </div>
            `;
        });
}

function closePriceHistory() {
    const modal = document.getElementById('historyModal');
    if (modal) {
        modal.style.display = 'none';
    }
}

// Funções auxiliares
function generateStars(rating) {
    const fullStars = Math.floor(rating);
    const hasHalfStar = rating % 1 >= 0.5;
    const emptyStars = 5 - fullStars - (hasHalfStar ? 1 : 0);
    
    let stars = '';
    for (let i = 0; i < fullStars; i++) {
        stars += '<span class="star star-full">★</span>';
    }
    if (hasHalfStar) {
        stars += '<span class="star star-half">★</span>';
    }
    for (let i = 0; i < emptyStars; i++) {
        stars += '<span class="star star-empty">★</span>';
    }
    return stars;
}

function formatNumber(num) {
    if (num >= 1000000) {
        return (num / 1000000).toFixed(1) + 'M';
    } else if (num >= 1000) {
        return (num / 1000).toFixed(1) + 'k';
    }
    return num.toString();
}

function showError(message) {
    errorDiv.textContent = message;
    errorDiv.classList.remove('hidden');
    setTimeout(() => {
        errorDiv.classList.add('hidden');
    }, 5000);
}

// Fecha sidebar ao clicar fora (mobile)
document.addEventListener('click', (e) => {
    if (window.innerWidth <= 900) {
        if (sidebar.classList.contains('open') && 
            !sidebar.contains(e.target) && 
            !sidebarToggle.contains(e.target)) {
            sidebar.classList.remove('open');
        }
    }
});
