import { useState } from 'react';
import { useMutation } from '@tanstack/react-query';
import { searchProductsPython, pythonProductToOffer, PythonSearchResponse } from '@/lib/api';
import { Offer, SearchFilters } from '@/types';
import { toast } from 'sonner';

/**
 * Hook para buscar produtos usando a API Python
 * Retorna resultados em tempo real de Amazon e Mercado Livre
 */
export function usePythonSearch() {
  const [searchTerm, setSearchTerm] = useState('');
  const [filters, setFilters] = useState<SearchFilters>({
    sortBy: 'price_asc',
  });

  const searchMutation = useMutation({
    mutationFn: async ({ term, filters }: { term: string; filters: SearchFilters }) => {
      // Busca produtos usando a API Python
      const response: PythonSearchResponse = await searchProductsPython(term);

      // Converte produtos Python para formato Offer
      const offers: Offer[] = response.products
        .map((product) => pythonProductToOffer(product))
        .filter((offer): offer is Offer => offer !== null);

      // Aplica filtros client-side
      let filteredOffers = offers;

      // Filtro por lojas
      if (filters.stores && filters.stores.length > 0) {
        filteredOffers = filteredOffers.filter((offer) =>
          filters.stores!.some((store) =>
            offer.store_name.toLowerCase().includes(store.toLowerCase())
          )
        );
      }

      // Filtro por preço mínimo
      if (filters.minPrice !== undefined) {
        filteredOffers = filteredOffers.filter((offer) => offer.price >= filters.minPrice!);
      }

      // Filtro por preço máximo
      if (filters.maxPrice !== undefined) {
        filteredOffers = filteredOffers.filter((offer) => offer.price <= filters.maxPrice!);
      }

      // Filtro por condição
      if (filters.condition && filters.condition.length > 0) {
        filteredOffers = filteredOffers.filter((offer) =>
          filters.condition!.includes(offer.condition)
        );
      }

      // Filtro por frete grátis
      if (filters.freeShipping) {
        filteredOffers = filteredOffers.filter(
          (offer) => offer.shipping_cost === 0 || offer.shipping_cost === null
        );
      }

      // Ordenação
      switch (filters.sortBy) {
        case 'price_asc':
          filteredOffers.sort((a, b) => a.price - b.price);
          break;
        case 'price_desc':
          filteredOffers.sort((a, b) => b.price - a.price);
          break;
        case 'rating_desc':
          filteredOffers.sort((a, b) => (b.rating || 0) - (a.rating || 0));
          break;
        case 'newest':
          filteredOffers.sort(
            (a, b) =>
              new Date(b.updated_at).getTime() - new Date(a.updated_at).getTime()
          );
          break;
      }

      // Mostra warnings se houver
      if (response.warnings && response.warnings.length > 0) {
        response.warnings.forEach((warning) => {
          toast.warning(warning);
        });
      }

      return filteredOffers;
    },
    onError: (error: Error) => {
      toast.error(`Erro ao buscar produtos: ${error.message}`);
    },
  });

  const performSearch = (term: string) => {
    setSearchTerm(term);
    if (term.trim()) {
      searchMutation.mutate({ term, filters });
    }
  };

  const updateFilters = (newFilters: Partial<SearchFilters>) => {
    const updatedFilters = { ...filters, ...newFilters };
    setFilters(updatedFilters);
    if (searchTerm.trim()) {
      searchMutation.mutate({ term: searchTerm, filters: updatedFilters });
    }
  };

  // Extrai lojas únicas dos resultados
  const stores = Array.from(
    new Set(searchMutation.data?.map((offer) => offer.store_name) || [])
  );

  // Extrai categorias únicas dos resultados (se houver)
  const categories: string[] = [];

  return {
    searchTerm,
    setSearchTerm,
    filters,
    setFilters: updateFilters,
    results: searchMutation.data || [],
    isLoading: searchMutation.isPending,
    error: searchMutation.error,
    performSearch,
    stores,
    categories,
  };
}

