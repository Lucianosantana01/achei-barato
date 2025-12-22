-- Enums para planos e tipos
CREATE TYPE public.user_plan AS ENUM ('FREE', 'PRO');
CREATE TYPE public.source_type AS ENUM ('API', 'FEED', 'MOCK');
CREATE TYPE public.product_condition AS ENUM ('new', 'used', 'refurbished');
CREATE TYPE public.notification_channel AS ENUM ('WHATSAPP', 'EMAIL');
CREATE TYPE public.notification_status AS ENUM ('PENDING', 'SENT', 'FAILED');

-- Tabela de perfis de usuário
CREATE TABLE public.profiles (
  id UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
  name TEXT,
  phone_whatsapp TEXT,
  plan user_plan NOT NULL DEFAULT 'FREE',
  credits_remaining INTEGER NOT NULL DEFAULT 10,
  credit_reset_at TIMESTAMPTZ NOT NULL DEFAULT (CURRENT_DATE + INTERVAL '1 day'),
  pro_cycle_start TIMESTAMPTZ,
  pro_cycle_end TIMESTAMPTZ,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Tabela de roles (separada por segurança)
CREATE TYPE public.app_role AS ENUM ('admin', 'user');

CREATE TABLE public.user_roles (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE NOT NULL,
  role app_role NOT NULL DEFAULT 'user',
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  UNIQUE (user_id, role)
);

-- Função para verificar role
CREATE OR REPLACE FUNCTION public.has_role(_user_id UUID, _role app_role)
RETURNS BOOLEAN
LANGUAGE sql
STABLE
SECURITY DEFINER
SET search_path = public
AS $$
  SELECT EXISTS (
    SELECT 1
    FROM public.user_roles
    WHERE user_id = _user_id
      AND role = _role
  )
$$;

-- Fontes de dados (APIs, Feeds, Mock)
CREATE TABLE public.store_sources (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  name TEXT NOT NULL,
  type source_type NOT NULL DEFAULT 'MOCK',
  config JSONB DEFAULT '{}',
  logo_url TEXT,
  active BOOLEAN NOT NULL DEFAULT true,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Ofertas de produtos
CREATE TABLE public.offers (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  source_id UUID REFERENCES public.store_sources(id) ON DELETE CASCADE,
  external_id TEXT,
  title TEXT NOT NULL,
  description TEXT,
  image_url TEXT,
  store_name TEXT NOT NULL,
  price DECIMAL(12,2) NOT NULL,
  original_price DECIMAL(12,2),
  currency TEXT NOT NULL DEFAULT 'BRL',
  purchase_url TEXT NOT NULL,
  shipping_cost DECIMAL(12,2),
  shipping_info TEXT,
  condition product_condition NOT NULL DEFAULT 'new',
  category TEXT,
  brand TEXT,
  rating DECIMAL(3,2),
  rating_count INTEGER,
  in_stock BOOLEAN DEFAULT true,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Histórico de buscas
CREATE TABLE public.search_queries (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE,
  term TEXT NOT NULL,
  filters JSONB DEFAULT '{}',
  credits_consumed INTEGER NOT NULL DEFAULT 1,
  results_count INTEGER,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Alertas de preço
CREATE TABLE public.price_alerts (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE NOT NULL,
  term TEXT NOT NULL,
  target_price DECIMAL(12,2) NOT NULL,
  percentage_drop DECIMAL(5,2),
  stores TEXT[],
  active BOOLEAN NOT NULL DEFAULT true,
  last_triggered_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Log de notificações
CREATE TABLE public.notification_logs (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE NOT NULL,
  alert_id UUID REFERENCES public.price_alerts(id) ON DELETE CASCADE,
  channel notification_channel NOT NULL,
  status notification_status NOT NULL DEFAULT 'PENDING',
  payload JSONB,
  error_message TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Configurações do sistema
CREATE TABLE public.system_settings (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  key TEXT UNIQUE NOT NULL,
  value JSONB NOT NULL,
  description TEXT,
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Índices para performance
CREATE INDEX idx_offers_title ON public.offers USING gin(to_tsvector('portuguese', title));
CREATE INDEX idx_offers_price ON public.offers(price);
CREATE INDEX idx_offers_store ON public.offers(store_name);
CREATE INDEX idx_offers_category ON public.offers(category);
CREATE INDEX idx_offers_updated ON public.offers(updated_at DESC);
CREATE INDEX idx_search_queries_user ON public.search_queries(user_id);
CREATE INDEX idx_price_alerts_user ON public.price_alerts(user_id);

-- Função para criar perfil automaticamente
CREATE OR REPLACE FUNCTION public.handle_new_user()
RETURNS TRIGGER
LANGUAGE plpgsql
SECURITY DEFINER SET search_path = public
AS $$
BEGIN
  INSERT INTO public.profiles (id, name)
  VALUES (NEW.id, COALESCE(NEW.raw_user_meta_data ->> 'name', NEW.email));
  
  INSERT INTO public.user_roles (user_id, role)
  VALUES (NEW.id, 'user');
  
  RETURN NEW;
END;
$$;

CREATE TRIGGER on_auth_user_created
  AFTER INSERT ON auth.users
  FOR EACH ROW EXECUTE FUNCTION public.handle_new_user();

-- Função para atualizar updated_at
CREATE OR REPLACE FUNCTION public.update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = NOW();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql SET search_path = public;

CREATE TRIGGER update_profiles_updated_at BEFORE UPDATE ON public.profiles
  FOR EACH ROW EXECUTE FUNCTION public.update_updated_at_column();

CREATE TRIGGER update_store_sources_updated_at BEFORE UPDATE ON public.store_sources
  FOR EACH ROW EXECUTE FUNCTION public.update_updated_at_column();

CREATE TRIGGER update_offers_updated_at BEFORE UPDATE ON public.offers
  FOR EACH ROW EXECUTE FUNCTION public.update_updated_at_column();

CREATE TRIGGER update_price_alerts_updated_at BEFORE UPDATE ON public.price_alerts
  FOR EACH ROW EXECUTE FUNCTION public.update_updated_at_column();

-- Enable RLS
ALTER TABLE public.profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.user_roles ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.store_sources ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.offers ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.search_queries ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.price_alerts ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.notification_logs ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.system_settings ENABLE ROW LEVEL SECURITY;

-- RLS Policies para profiles
CREATE POLICY "Users can view own profile" ON public.profiles
  FOR SELECT USING (auth.uid() = id);

CREATE POLICY "Users can update own profile" ON public.profiles
  FOR UPDATE USING (auth.uid() = id);

-- RLS para user_roles (apenas leitura do próprio)
CREATE POLICY "Users can view own roles" ON public.user_roles
  FOR SELECT USING (auth.uid() = user_id);

-- RLS para store_sources (público para leitura, admin para escrita)
CREATE POLICY "Anyone can view active sources" ON public.store_sources
  FOR SELECT USING (active = true);

CREATE POLICY "Admins can manage sources" ON public.store_sources
  FOR ALL USING (public.has_role(auth.uid(), 'admin'));

-- RLS para offers (público para leitura)
CREATE POLICY "Anyone can view offers" ON public.offers
  FOR SELECT USING (true);

CREATE POLICY "Admins can manage offers" ON public.offers
  FOR ALL USING (public.has_role(auth.uid(), 'admin'));

-- RLS para search_queries
CREATE POLICY "Users can view own searches" ON public.search_queries
  FOR SELECT USING (auth.uid() = user_id);

CREATE POLICY "Users can insert own searches" ON public.search_queries
  FOR INSERT WITH CHECK (auth.uid() = user_id);

-- RLS para price_alerts
CREATE POLICY "Users can view own alerts" ON public.price_alerts
  FOR SELECT USING (auth.uid() = user_id);

CREATE POLICY "Users can manage own alerts" ON public.price_alerts
  FOR ALL USING (auth.uid() = user_id);

-- RLS para notification_logs
CREATE POLICY "Users can view own notifications" ON public.notification_logs
  FOR SELECT USING (auth.uid() = user_id);

-- RLS para system_settings (admin only)
CREATE POLICY "Admins can manage settings" ON public.system_settings
  FOR ALL USING (public.has_role(auth.uid(), 'admin'));

CREATE POLICY "Anyone can read settings" ON public.system_settings
  FOR SELECT USING (true);

-- Inserir configurações padrão
INSERT INTO public.system_settings (key, value, description) VALUES
  ('credits_per_search', '1', 'Número de créditos consumidos por pesquisa'),
  ('free_daily_credits', '10', 'Créditos diários para usuários FREE'),
  ('pro_monthly_credits', '1000', 'Créditos mensais para usuários PRO');

-- Inserir fontes mock
INSERT INTO public.store_sources (name, type, logo_url, active) VALUES
  ('Loja Virtual A', 'MOCK', 'https://placehold.co/100x40/2563eb/white?text=LojaA', true),
  ('Mega Store', 'MOCK', 'https://placehold.co/100x40/dc2626/white?text=MegaStore', true),
  ('Tech Shop', 'MOCK', 'https://placehold.co/100x40/16a34a/white?text=TechShop', true),
  ('Eletrônicos BR', 'MOCK', 'https://placehold.co/100x40/9333ea/white?text=EletronicosBR', true),
  ('Super Ofertas', 'MOCK', 'https://placehold.co/100x40/ea580c/white?text=SuperOfertas', true);

-- Inserir ofertas mock para demonstração
INSERT INTO public.offers (source_id, external_id, title, description, image_url, store_name, price, original_price, purchase_url, shipping_cost, shipping_info, condition, category, brand, rating, rating_count)
SELECT 
  s.id,
  'MOCK-' || md5(random()::text),
  'iPhone 15 128GB ' || s.name,
  'Apple iPhone 15 128GB, Tela Super Retina XDR 6.1", Chip A16 Bionic, Câmera dupla de 48MP',
  'https://placehold.co/400x400/1a1a1a/white?text=iPhone+15',
  s.name,
  ROUND((4500 + random() * 1500)::numeric, 2),
  ROUND((5500 + random() * 1000)::numeric, 2),
  'https://example.com/produto/' || md5(random()::text),
  CASE WHEN random() > 0.5 THEN 0 ELSE ROUND((15 + random() * 50)::numeric, 2) END,
  CASE WHEN random() > 0.5 THEN 'Frete Grátis' ELSE 'Entrega em 3-5 dias' END,
  'new',
  'Smartphones',
  'Apple',
  ROUND((4 + random())::numeric, 1),
  FLOOR(random() * 5000 + 100)::integer
FROM public.store_sources s WHERE s.type = 'MOCK';

-- Mais produtos mock
INSERT INTO public.offers (source_id, external_id, title, image_url, store_name, price, original_price, purchase_url, shipping_cost, shipping_info, condition, category, brand, rating, rating_count)
SELECT 
  s.id,
  'MOCK-' || md5(random()::text),
  'Samsung Galaxy S24 256GB',
  'https://placehold.co/400x400/1a1a1a/white?text=Galaxy+S24',
  s.name,
  ROUND((3800 + random() * 1200)::numeric, 2),
  ROUND((4800 + random() * 800)::numeric, 2),
  'https://example.com/produto/' || md5(random()::text),
  CASE WHEN random() > 0.5 THEN 0 ELSE ROUND((15 + random() * 50)::numeric, 2) END,
  CASE WHEN random() > 0.5 THEN 'Frete Grátis' ELSE 'Entrega em 2-4 dias' END,
  'new',
  'Smartphones',
  'Samsung',
  ROUND((4 + random())::numeric, 1),
  FLOOR(random() * 3000 + 50)::integer
FROM public.store_sources s WHERE s.type = 'MOCK';

INSERT INTO public.offers (source_id, external_id, title, image_url, store_name, price, original_price, purchase_url, shipping_cost, shipping_info, condition, category, brand, rating, rating_count)
SELECT 
  s.id,
  'MOCK-' || md5(random()::text),
  'MacBook Air M3 256GB',
  'https://placehold.co/400x400/1a1a1a/white?text=MacBook+Air',
  s.name,
  ROUND((8500 + random() * 2000)::numeric, 2),
  ROUND((10500 + random() * 1500)::numeric, 2),
  'https://example.com/produto/' || md5(random()::text),
  0,
  'Frete Grátis',
  'new',
  'Notebooks',
  'Apple',
  ROUND((4.5 + random() * 0.5)::numeric, 1),
  FLOOR(random() * 2000 + 100)::integer
FROM public.store_sources s WHERE s.type = 'MOCK';

INSERT INTO public.offers (source_id, external_id, title, image_url, store_name, price, original_price, purchase_url, shipping_cost, shipping_info, condition, category, brand, rating, rating_count)
SELECT 
  s.id,
  'MOCK-' || md5(random()::text),
  'PlayStation 5 Digital Edition',
  'https://placehold.co/400x400/1a1a1a/white?text=PS5',
  s.name,
  ROUND((3200 + random() * 800)::numeric, 2),
  ROUND((4200 + random() * 500)::numeric, 2),
  'https://example.com/produto/' || md5(random()::text),
  CASE WHEN random() > 0.3 THEN 0 ELSE ROUND((30 + random() * 70)::numeric, 2) END,
  CASE WHEN random() > 0.3 THEN 'Frete Grátis' ELSE 'Entrega em 5-7 dias' END,
  'new',
  'Games',
  'Sony',
  ROUND((4.3 + random() * 0.7)::numeric, 1),
  FLOOR(random() * 4000 + 200)::integer
FROM public.store_sources s WHERE s.type = 'MOCK';

INSERT INTO public.offers (source_id, external_id, title, image_url, store_name, price, original_price, purchase_url, shipping_cost, shipping_info, condition, category, brand, rating, rating_count)
SELECT 
  s.id,
  'MOCK-' || md5(random()::text),
  'Smart TV LG 55" 4K OLED',
  'https://placehold.co/400x400/1a1a1a/white?text=LG+OLED+55',
  s.name,
  ROUND((4500 + random() * 1500)::numeric, 2),
  ROUND((6000 + random() * 1000)::numeric, 2),
  'https://example.com/produto/' || md5(random()::text),
  CASE WHEN random() > 0.4 THEN 0 ELSE ROUND((80 + random() * 120)::numeric, 2) END,
  CASE WHEN random() > 0.4 THEN 'Frete Grátis' ELSE 'Entrega em 7-10 dias' END,
  'new',
  'TVs',
  'LG',
  ROUND((4.2 + random() * 0.8)::numeric, 1),
  FLOOR(random() * 1500 + 50)::integer
FROM public.store_sources s WHERE s.type = 'MOCK';

INSERT INTO public.offers (source_id, external_id, title, image_url, store_name, price, original_price, purchase_url, shipping_cost, shipping_info, condition, category, brand, rating, rating_count)
SELECT 
  s.id,
  'MOCK-' || md5(random()::text),
  'AirPods Pro 2ª Geração',
  'https://placehold.co/400x400/1a1a1a/white?text=AirPods+Pro',
  s.name,
  ROUND((1400 + random() * 600)::numeric, 2),
  ROUND((2100 + random() * 400)::numeric, 2),
  'https://example.com/produto/' || md5(random()::text),
  CASE WHEN random() > 0.6 THEN 0 ELSE ROUND((10 + random() * 25)::numeric, 2) END,
  CASE WHEN random() > 0.6 THEN 'Frete Grátis' ELSE 'Entrega em 1-3 dias' END,
  'new',
  'Acessórios',
  'Apple',
  ROUND((4.4 + random() * 0.6)::numeric, 1),
  FLOOR(random() * 6000 + 300)::integer
FROM public.store_sources s WHERE s.type = 'MOCK';