import { useState, FormEvent } from 'react';
import { useNavigate } from 'react-router-dom';
import { Search, Sparkles } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { cn } from '@/lib/utils';

interface SearchBarProps {
  className?: string;
  size?: 'default' | 'large';
  placeholder?: string;
  onSearch?: (term: string) => void;
  defaultValue?: string;
}

export function SearchBar({
  className,
  size = 'default',
  placeholder = 'Buscar produtos... Ex: iPhone 15 128GB',
  onSearch,
  defaultValue = '',
}: SearchBarProps) {
  const [term, setTerm] = useState(defaultValue);
  const navigate = useNavigate();

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault();
    if (term.trim()) {
      if (onSearch) {
        onSearch(term.trim());
      } else {
        navigate(`/buscar?q=${encodeURIComponent(term.trim())}`);
      }
    }
  };

  const isLarge = size === 'large';

  return (
    <form onSubmit={handleSubmit} className={cn('relative w-full', className)}>
      <div className="relative">
        <Search
          className={cn(
            'absolute left-4 top-1/2 -translate-y-1/2 text-muted-foreground',
            isLarge ? 'h-6 w-6' : 'h-5 w-5'
          )}
        />
        <input
          type="text"
          value={term}
          onChange={(e) => setTerm(e.target.value)}
          placeholder={placeholder}
          className={cn(
            'w-full rounded-2xl border-2 border-border bg-card pl-12 pr-32 shadow-md transition-all duration-300',
            'placeholder:text-muted-foreground/60',
            'focus:border-primary focus:ring-4 focus:ring-primary/20 focus:shadow-lg focus:outline-none',
            isLarge ? 'h-16 text-lg' : 'h-12 text-base'
          )}
        />
        <Button
          type="submit"
          size={isLarge ? 'lg' : 'default'}
          className={cn(
            'absolute right-2 top-1/2 -translate-y-1/2 gap-2',
            isLarge ? 'h-12 px-6' : 'h-8 px-4'
          )}
        >
          <Sparkles className={cn(isLarge ? 'h-5 w-5' : 'h-4 w-4')} />
          <span className="hidden sm:inline">Comparar</span>
        </Button>
      </div>
    </form>
  );
}
