import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { supabase } from '@/integrations/supabase/client';
import { Offer, SearchFilters } from '@/types';
import { useAuth } from '@/contexts/AuthContext';
import { toast } from 'sonner';

export function useSearch() {
  const { user, profile, refreshProfile } = useAuth();
  const queryClient = useQueryClient();
  const [searchTerm, setSearchTerm] = useState('');
  const [filters, setFilters] = useState<SearchFilters>({
    sortBy: 'price_asc',
  });

  const searchOffers = async (term: string, filters: SearchFilters): Promise<Offer[]> => {
    let query = supabase
      .from('offers')
      .select('*')
      .ilike('title', `%${term}%`);

    if (filters.stores && filters.stores.length > 0) {
      query = query.in('store_name', filters.stores);
    }

    if (filters.minPrice !== undefined) {
      query = query.gte('price', filters.minPrice);
    }

    if (filters.maxPrice !== undefined) {
      query = query.lte('price', filters.maxPrice);
    }

    if (filters.condition && filters.condition.length > 0) {
      query = query.in('condition', filters.condition);
    }

    if (filters.category) {
      query = query.eq('category', filters.category);
    }

    if (filters.freeShipping) {
      query = query.or('shipping_cost.eq.0,shipping_cost.is.null');
    }

    switch (filters.sortBy) {
      case 'price_asc':
        query = query.order('price', { ascending: true });
        break;
      case 'price_desc':
        query = query.order('price', { ascending: false });
        break;
      case 'rating_desc':
        query = query.order('rating', { ascending: false, nullsFirst: false });
        break;
      case 'newest':
        query = query.order('updated_at', { ascending: false });
        break;
      default:
        query = query.order('price', { ascending: true });
    }

    const { data, error } = await query;

    if (error) {
      throw error;
    }

    return (data || []) as Offer[];
  };

  const consumeCredit = async (term: string, resultsCount: number) => {
    if (!user) return;

    // Primeiro, registrar a busca
    await supabase.from('search_queries').insert([{
      user_id: user.id,
      term,
      filters: filters as any,
      credits_consumed: 1,
      results_count: resultsCount,
    }]);

    // Depois, decrementar os créditos
    const { error } = await supabase
      .from('profiles')
      .update({ credits_remaining: (profile?.credits_remaining || 1) - 1 })
      .eq('id', user.id);

    if (error) {
      console.error('Error consuming credit:', error);
    }

    await refreshProfile();
  };

  const searchMutation = useMutation({
    mutationFn: async ({ term, filters }: { term: string; filters: SearchFilters }) => {
      if (user && profile) {
        if (profile.credits_remaining <= 0) {
          throw new Error('Você não tem créditos suficientes para realizar esta busca.');
        }
      }

      const results = await searchOffers(term, filters);

      if (user) {
        await consumeCredit(term, results.length);
      }

      return results;
    },
    onError: (error: Error) => {
      toast.error(error.message);
    },
  });

  const { data: stores = [] } = useQuery({
    queryKey: ['stores'],
    queryFn: async () => {
      const { data } = await supabase
        .from('store_sources')
        .select('name')
        .eq('active', true);
      return data?.map(s => s.name) || [];
    },
  });

  const { data: categories = [] } = useQuery({
    queryKey: ['categories'],
    queryFn: async () => {
      const { data } = await supabase
        .from('offers')
        .select('category')
        .not('category', 'is', null);
      const uniqueCategories = [...new Set(data?.map(o => o.category).filter(Boolean))];
      return uniqueCategories as string[];
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
