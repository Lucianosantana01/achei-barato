import { Offer } from '@/types';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { 
  ExternalLink, 
  Star, 
  Truck, 
  TrendingDown,
  Store
} from 'lucide-react';
import { cn } from '@/lib/utils';

interface OfferCardProps {
  offer: Offer;
  featured?: boolean;
  rank?: number;
}

export function OfferCard({ offer, featured = false, rank }: OfferCardProps) {
  const discount = offer.original_price
    ? Math.round(((offer.original_price - offer.price) / offer.original_price) * 100)
    : 0;

  const formatPrice = (price: number) => {
    return new Intl.NumberFormat('pt-BR', {
      style: 'currency',
      currency: 'BRL',
    }).format(price);
  };

  const hasFreeShipping = offer.shipping_cost === 0 || offer.shipping_cost === null;

  return (
    <Card
      className={cn(
        'offer-card group flex flex-col',
        featured && 'ring-2 ring-primary/50'
      )}
    >
      {/* Discount Badge */}
      {discount > 0 && (
        <div className="discount-badge">
          <TrendingDown className="mr-1 inline h-3 w-3" />
          -{discount}%
        </div>
      )}

      {/* Rank Badge */}
      {rank === 1 && (
        <div className="absolute right-3 top-3 flex h-8 w-8 items-center justify-center rounded-full bg-primary text-sm font-bold text-primary-foreground shadow-lg">
          1º
        </div>
      )}

      {/* Image */}
      <div className="relative aspect-square overflow-hidden bg-secondary/30 p-4">
        {offer.image_url ? (
          <img
            src={offer.image_url}
            alt={offer.title}
            className="h-full w-full object-contain transition-transform duration-300 group-hover:scale-105"
          />
        ) : (
          <div className="flex h-full w-full items-center justify-center">
            <Store className="h-16 w-16 text-muted-foreground/30" />
          </div>
        )}
      </div>

      {/* Content */}
      <div className="flex flex-1 flex-col p-4">
        {/* Store */}
        <div className="mb-2 flex items-center gap-2">
          <span className="store-badge">
            <Store className="h-3 w-3" />
            {offer.store_name}
          </span>
          {offer.condition !== 'new' && (
            <Badge variant="outline" className="text-xs">
              {offer.condition === 'used' ? 'Usado' : 'Recondicionado'}
            </Badge>
          )}
        </div>

        {/* Title */}
        <h3 className="mb-2 line-clamp-2 text-sm font-semibold leading-tight">
          {offer.title}
        </h3>

        {/* Rating */}
        {offer.rating && (
          <div className="mb-3 flex items-center gap-1 text-sm text-muted-foreground">
            <Star className="h-4 w-4 fill-warning text-warning" />
            <span className="font-medium">{offer.rating.toFixed(1)}</span>
            {offer.rating_count && (
              <span className="text-xs">({offer.rating_count.toLocaleString('pt-BR')})</span>
            )}
          </div>
        )}

        {/* Price */}
        <div className="mt-auto space-y-1">
          {offer.original_price && offer.original_price > offer.price && (
            <p className="text-sm text-muted-foreground line-through">
              {formatPrice(offer.original_price)}
            </p>
          )}
          <p className="text-2xl font-bold text-success">
            {formatPrice(offer.price)}
          </p>
        </div>

        {/* Shipping */}
        <div className="mt-2 flex items-center gap-1 text-xs text-muted-foreground">
          <Truck className="h-3 w-3" />
          {hasFreeShipping ? (
            <span className="font-medium text-success">Frete Grátis</span>
          ) : offer.shipping_cost ? (
            <span>Frete: {formatPrice(offer.shipping_cost)}</span>
          ) : (
            <span>{offer.shipping_info || 'Consultar frete'}</span>
          )}
        </div>

        {/* Action */}
        <Button asChild className="mt-4 w-full gap-2">
          <a href={offer.purchase_url} target="_blank" rel="noopener noreferrer">
            Ver Oferta
            <ExternalLink className="h-4 w-4" />
          </a>
        </Button>
      </div>
    </Card>
  );
}
