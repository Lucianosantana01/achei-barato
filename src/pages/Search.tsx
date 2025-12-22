import { useEffect } from 'react';
import { useSearchParams } from 'react-router-dom';
import { Layout } from '@/components/layout/Layout';
import { SearchBar } from '@/components/search/SearchBar';
import { SearchFiltersComponent } from '@/components/search/SearchFilters';
import { SearchResults } from '@/components/search/SearchResults';
import { useSearch } from '@/hooks/useSearch';
import { useAuth } from '@/contexts/AuthContext';
import { Card } from '@/components/ui/card';
import { CreditCard, Sparkles } from 'lucide-react';

export default function SearchPage() {
  const [searchParams] = useSearchParams();
  const queryFromUrl = searchParams.get('q') || '';
  const { user, profile } = useAuth();
  const {
    searchTerm,
    filters,
    setFilters,
    results,
    isLoading,
    performSearch,
    stores,
    categories,
  } = useSearch();

  useEffect(() => {
    if (queryFromUrl && queryFromUrl !== searchTerm) {
      performSearch(queryFromUrl);
    }
  }, [queryFromUrl]);

  return (
    <Layout>
      <div className="container py-6">
        {/* Search Header */}
        <div className="mb-6">
          <SearchBar
            defaultValue={searchTerm || queryFromUrl}
            onSearch={performSearch}
          />
        </div>

        {/* Credits Info */}
        {user && profile && (
          <Card className="mb-6 flex items-center justify-between p-4">
            <div className="flex items-center gap-3">
              <div className="flex h-10 w-10 items-center justify-center rounded-full bg-primary/10">
                <CreditCard className="h-5 w-5 text-primary" />
              </div>
              <div>
                <p className="text-sm font-medium">
                  {profile.credits_remaining} créditos restantes
                </p>
                <p className="text-xs text-muted-foreground">
                  Cada busca consome 1 crédito
                </p>
              </div>
            </div>
            <span className={profile.plan === 'PRO' ? 'plan-badge-pro' : 'plan-badge-free'}>
              {profile.plan}
            </span>
          </Card>
        )}

        {/* Main Content */}
        <div className="flex gap-6">
          {/* Filters Sidebar (Desktop) */}
          <aside className="hidden w-72 shrink-0 lg:block">
            <SearchFiltersComponent
              filters={filters}
              onFiltersChange={setFilters}
              stores={stores}
              categories={categories}
            />
          </aside>

          {/* Results */}
          <div className="flex-1">
            {/* Mobile Filters */}
            <div className="mb-4 flex items-center gap-2 lg:hidden">
              <SearchFiltersComponent
                filters={filters}
                onFiltersChange={setFilters}
                stores={stores}
                categories={categories}
              />
            </div>

            <SearchResults
              results={results}
              isLoading={isLoading}
              searchTerm={searchTerm || queryFromUrl}
            />
          </div>
        </div>
      </div>
    </Layout>
  );
}
