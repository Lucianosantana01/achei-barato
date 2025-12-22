import { SearchFilters, ProductCondition } from '@/types';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Checkbox } from '@/components/ui/checkbox';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
  SheetTrigger,
} from '@/components/ui/sheet';
import { SlidersHorizontal, X } from 'lucide-react';
import { useState } from 'react';

interface SearchFiltersProps {
  filters: SearchFilters;
  onFiltersChange: (filters: Partial<SearchFilters>) => void;
  stores: string[];
  categories: string[];
}

export function SearchFiltersComponent({
  filters,
  onFiltersChange,
  stores,
  categories,
}: SearchFiltersProps) {
  const [minPrice, setMinPrice] = useState(filters.minPrice?.toString() || '');
  const [maxPrice, setMaxPrice] = useState(filters.maxPrice?.toString() || '');

  const handlePriceChange = () => {
    onFiltersChange({
      minPrice: minPrice ? parseFloat(minPrice) : undefined,
      maxPrice: maxPrice ? parseFloat(maxPrice) : undefined,
    });
  };

  const handleStoreToggle = (store: string) => {
    const currentStores = filters.stores || [];
    const newStores = currentStores.includes(store)
      ? currentStores.filter((s) => s !== store)
      : [...currentStores, store];
    onFiltersChange({ stores: newStores.length > 0 ? newStores : undefined });
  };

  const handleConditionToggle = (condition: ProductCondition) => {
    const currentConditions = filters.condition || [];
    const newConditions = currentConditions.includes(condition)
      ? currentConditions.filter((c) => c !== condition)
      : [...currentConditions, condition];
    onFiltersChange({ condition: newConditions.length > 0 ? newConditions : undefined });
  };

  const clearFilters = () => {
    setMinPrice('');
    setMaxPrice('');
    onFiltersChange({
      stores: undefined,
      minPrice: undefined,
      maxPrice: undefined,
      condition: undefined,
      category: undefined,
      freeShipping: undefined,
    });
  };

  const hasActiveFilters =
    (filters.stores && filters.stores.length > 0) ||
    filters.minPrice !== undefined ||
    filters.maxPrice !== undefined ||
    (filters.condition && filters.condition.length > 0) ||
    filters.category !== undefined ||
    filters.freeShipping;

  const FilterContent = () => (
    <div className="space-y-6">
      {/* Sort */}
      <div className="space-y-2">
        <Label>Ordenar por</Label>
        <Select
          value={filters.sortBy || 'price_asc'}
          onValueChange={(value) => onFiltersChange({ sortBy: value as SearchFilters['sortBy'] })}
        >
          <SelectTrigger>
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="price_asc">Menor Preço</SelectItem>
            <SelectItem value="price_desc">Maior Preço</SelectItem>
            <SelectItem value="rating_desc">Melhor Avaliação</SelectItem>
            <SelectItem value="newest">Mais Recentes</SelectItem>
          </SelectContent>
        </Select>
      </div>

      {/* Price Range */}
      <div className="space-y-2">
        <Label>Faixa de Preço</Label>
        <div className="flex items-center gap-2">
          <Input
            type="number"
            placeholder="Mín"
            value={minPrice}
            onChange={(e) => setMinPrice(e.target.value)}
            onBlur={handlePriceChange}
            className="h-9"
          />
          <span className="text-muted-foreground">-</span>
          <Input
            type="number"
            placeholder="Máx"
            value={maxPrice}
            onChange={(e) => setMaxPrice(e.target.value)}
            onBlur={handlePriceChange}
            className="h-9"
          />
        </div>
      </div>

      {/* Free Shipping */}
      <div className="flex items-center space-x-2">
        <Checkbox
          id="freeShipping"
          checked={filters.freeShipping || false}
          onCheckedChange={(checked) => onFiltersChange({ freeShipping: checked as boolean })}
        />
        <Label htmlFor="freeShipping" className="cursor-pointer">
          Apenas Frete Grátis
        </Label>
      </div>

      {/* Condition */}
      <div className="space-y-2">
        <Label>Condição</Label>
        <div className="flex flex-wrap gap-2">
          {(['new', 'used', 'refurbished'] as ProductCondition[]).map((condition) => (
            <button
              key={condition}
              onClick={() => handleConditionToggle(condition)}
              className={
                filters.condition?.includes(condition)
                  ? 'filter-chip-active'
                  : 'filter-chip'
              }
            >
              {condition === 'new' ? 'Novo' : condition === 'used' ? 'Usado' : 'Recondicionado'}
            </button>
          ))}
        </div>
      </div>

      {/* Category */}
      {categories.length > 0 && (
        <div className="space-y-2">
          <Label>Categoria</Label>
          <Select
            value={filters.category || 'all'}
            onValueChange={(value) =>
              onFiltersChange({ category: value === 'all' ? undefined : value })
            }
          >
            <SelectTrigger>
              <SelectValue placeholder="Todas as categorias" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">Todas as categorias</SelectItem>
              {categories.map((category) => (
                <SelectItem key={category} value={category}>
                  {category}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
      )}

      {/* Stores */}
      {stores.length > 0 && (
        <div className="space-y-2">
          <Label>Lojas</Label>
          <div className="flex flex-wrap gap-2">
            {stores.map((store) => (
              <button
                key={store}
                onClick={() => handleStoreToggle(store)}
                className={
                  filters.stores?.includes(store) ? 'filter-chip-active' : 'filter-chip'
                }
              >
                {store}
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Clear Filters */}
      {hasActiveFilters && (
        <Button variant="outline" onClick={clearFilters} className="w-full">
          <X className="mr-2 h-4 w-4" />
          Limpar Filtros
        </Button>
      )}
    </div>
  );

  return (
    <>
      {/* Desktop Filters */}
      <div className="hidden lg:block">
        <div className="sticky top-24 rounded-2xl border border-border bg-card p-6">
          <h3 className="mb-4 font-semibold">Filtros</h3>
          <FilterContent />
        </div>
      </div>

      {/* Mobile Filters */}
      <Sheet>
        <SheetTrigger asChild>
          <Button variant="outline" className="gap-2 lg:hidden">
            <SlidersHorizontal className="h-4 w-4" />
            Filtros
            {hasActiveFilters && (
              <span className="flex h-5 w-5 items-center justify-center rounded-full bg-primary text-xs text-primary-foreground">
                !
              </span>
            )}
          </Button>
        </SheetTrigger>
        <SheetContent side="left" className="w-full max-w-sm overflow-y-auto">
          <SheetHeader>
            <SheetTitle>Filtros</SheetTitle>
          </SheetHeader>
          <div className="mt-6">
            <FilterContent />
          </div>
        </SheetContent>
      </Sheet>
    </>
  );
}
