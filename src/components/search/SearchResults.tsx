import { Offer } from '@/types';
import { OfferCard } from './OfferCard';
import { Skeleton } from '@/components/ui/skeleton';
import { PackageX, Search } from 'lucide-react';

interface SearchResultsProps {
  results: Offer[];
  isLoading: boolean;
  searchTerm: string;
}

export function SearchResults({ results, isLoading, searchTerm }: SearchResultsProps) {
  if (isLoading) {
    return (
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
        {Array.from({ length: 8 }).map((_, i) => (
          <div key={i} className="rounded-2xl border border-border bg-card p-4">
            <Skeleton className="aspect-square w-full rounded-lg" />
            <div className="mt-4 space-y-2">
              <Skeleton className="h-4 w-24" />
              <Skeleton className="h-4 w-full" />
              <Skeleton className="h-4 w-3/4" />
              <Skeleton className="h-8 w-32" />
              <Skeleton className="h-10 w-full" />
            </div>
          </div>
        ))}
      </div>
    );
  }

  if (!searchTerm) {
    return (
      <div className="flex flex-col items-center justify-center py-16 text-center">
        <div className="mb-4 flex h-20 w-20 items-center justify-center rounded-full bg-secondary">
          <Search className="h-10 w-10 text-muted-foreground" />
        </div>
        <h3 className="text-xl font-semibold">Busque por um produto</h3>
        <p className="mt-2 max-w-md text-muted-foreground">
          Digite o nome do produto que você procura para encontrar as melhores ofertas em diversas lojas.
        </p>
      </div>
    );
  }

  if (results.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-16 text-center">
        <div className="mb-4 flex h-20 w-20 items-center justify-center rounded-full bg-secondary">
          <PackageX className="h-10 w-10 text-muted-foreground" />
        </div>
        <h3 className="text-xl font-semibold">Nenhum resultado encontrado</h3>
        <p className="mt-2 max-w-md text-muted-foreground">
          Não encontramos ofertas para "{searchTerm}". Tente usar termos diferentes ou verifique a ortografia.
        </p>
      </div>
    );
  }

  return (
    <div>
      <div className="mb-4 text-sm text-muted-foreground">
        {results.length} {results.length === 1 ? 'oferta encontrada' : 'ofertas encontradas'} para "{searchTerm}"
      </div>
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
        {results.map((offer, index) => (
          <OfferCard
            key={offer.id}
            offer={offer}
            featured={index === 0}
            rank={index + 1}
          />
        ))}
      </div>
    </div>
  );
}
