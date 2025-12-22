export type UserPlan = 'FREE' | 'PRO';
export type SourceType = 'API' | 'FEED' | 'MOCK';
export type ProductCondition = 'new' | 'used' | 'refurbished';
export type NotificationChannel = 'WHATSAPP' | 'EMAIL';
export type NotificationStatus = 'PENDING' | 'SENT' | 'FAILED';
export type AppRole = 'admin' | 'user';

export interface Profile {
  id: string;
  name: string | null;
  phone_whatsapp: string | null;
  plan: UserPlan;
  credits_remaining: number;
  credit_reset_at: string;
  pro_cycle_start: string | null;
  pro_cycle_end: string | null;
  created_at: string;
  updated_at: string;
}

export interface UserRole {
  id: string;
  user_id: string;
  role: AppRole;
  created_at: string;
}

export interface StoreSource {
  id: string;
  name: string;
  type: SourceType;
  config: Record<string, unknown>;
  logo_url: string | null;
  active: boolean;
  created_at: string;
  updated_at: string;
}

export interface Offer {
  id: string;
  source_id: string | null;
  external_id: string | null;
  title: string;
  description: string | null;
  image_url: string | null;
  store_name: string;
  price: number;
  original_price: number | null;
  currency: string;
  purchase_url: string;
  shipping_cost: number | null;
  shipping_info: string | null;
  condition: ProductCondition;
  category: string | null;
  brand: string | null;
  rating: number | null;
  rating_count: number | null;
  in_stock: boolean;
  created_at: string;
  updated_at: string;
}

export interface SearchQuery {
  id: string;
  user_id: string | null;
  term: string;
  filters: Record<string, unknown>;
  credits_consumed: number;
  results_count: number | null;
  created_at: string;
}

export interface PriceAlert {
  id: string;
  user_id: string;
  term: string;
  target_price: number;
  percentage_drop: number | null;
  stores: string[] | null;
  active: boolean;
  last_triggered_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface NotificationLog {
  id: string;
  user_id: string;
  alert_id: string | null;
  channel: NotificationChannel;
  status: NotificationStatus;
  payload: Record<string, unknown> | null;
  error_message: string | null;
  created_at: string;
}

export interface SystemSetting {
  id: string;
  key: string;
  value: unknown;
  description: string | null;
  updated_at: string;
}

export interface SearchFilters {
  stores?: string[];
  minPrice?: number;
  maxPrice?: number;
  condition?: ProductCondition[];
  category?: string;
  freeShipping?: boolean;
  sortBy?: 'price_asc' | 'price_desc' | 'rating_desc' | 'newest';
}
