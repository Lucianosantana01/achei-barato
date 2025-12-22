import { useState } from 'react';
import { useNavigate, useSearchParams, Link } from 'react-router-dom';
import { Layout } from '@/components/layout/Layout';
import { SearchBar } from '@/components/search/SearchBar';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { useAuth } from '@/contexts/AuthContext';
import {
  Search,
  TrendingDown,
  Bell,
  Zap,
  Shield,
  Star,
  ArrowRight,
  Smartphone,
  Laptop,
  Tv,
  Gamepad2,
  Headphones,
  Watch,
} from 'lucide-react';

const popularSearches = [
  { term: 'iPhone 15', icon: Smartphone },
  { term: 'MacBook Air', icon: Laptop },
  { term: 'Smart TV 55"', icon: Tv },
  { term: 'PlayStation 5', icon: Gamepad2 },
  { term: 'AirPods Pro', icon: Headphones },
  { term: 'Apple Watch', icon: Watch },
];

const features = [
  {
    icon: TrendingDown,
    title: 'Menor Preço Garantido',
    description: 'Comparamos preços de diversas lojas para você encontrar a melhor oferta.',
  },
  {
    icon: Bell,
    title: 'Alertas de Preço',
    description: 'Crie alertas e seja notificado quando o preço do produto cair.',
  },
  {
    icon: Zap,
    title: 'Atualização em Tempo Real',
    description: 'Preços atualizados constantemente para você não perder nenhuma promoção.',
  },
  {
    icon: Shield,
    title: 'Lojas Confiáveis',
    description: 'Trabalhamos apenas com lojas verificadas e de confiança.',
  },
];

export default function Index() {
  const { user, profile } = useAuth();
  const navigate = useNavigate();

  const handleSearch = (term: string) => {
    navigate(`/buscar?q=${encodeURIComponent(term)}`);
  };

  return (
    <Layout>
      {/* Hero Section */}
      <section className="hero-section py-16 md:py-24">
        <div className="container">
          <div className="mx-auto max-w-3xl text-center">
            {/* Badge */}
            <div className="mb-6 inline-flex items-center gap-2 rounded-full border border-primary/20 bg-primary/5 px-4 py-1.5 text-sm">
              <Star className="h-4 w-4 text-primary" />
              <span>Compare preços em segundos</span>
            </div>

            {/* Headline */}
            <h1 className="mb-4 text-4xl font-extrabold tracking-tight md:text-5xl lg:text-6xl">
              Encontre o{' '}
              <span className="text-gradient">Menor Preço</span>
              <br />
              em Milhares de Produtos
            </h1>

            {/* Subheadline */}
            <p className="mb-8 text-lg text-muted-foreground md:text-xl">
              Compare ofertas de diversas lojas, crie alertas de preço e economize tempo e dinheiro nas suas compras.
            </p>

            {/* Search Bar */}
            <SearchBar size="large" onSearch={handleSearch} className="mb-6" />

            {/* Popular Searches */}
            <div className="flex flex-wrap items-center justify-center gap-2">
              <span className="text-sm text-muted-foreground">Populares:</span>
              {popularSearches.slice(0, 4).map((item) => (
                <button
                  key={item.term}
                  onClick={() => handleSearch(item.term)}
                  className="filter-chip"
                >
                  <item.icon className="h-3 w-3" />
                  {item.term}
                </button>
              ))}
            </div>
          </div>
        </div>

        {/* Decorative Elements */}
        <div className="pointer-events-none absolute inset-0 overflow-hidden">
          <div className="absolute -left-40 -top-40 h-80 w-80 rounded-full bg-primary/5 blur-3xl" />
          <div className="absolute -bottom-40 -right-40 h-80 w-80 rounded-full bg-primary/10 blur-3xl" />
        </div>
      </section>

      {/* Features Section */}
      <section className="py-16 md:py-24">
        <div className="container">
          <div className="mb-12 text-center">
            <h2 className="mb-4 text-3xl font-bold">Por que usar o Comparador?</h2>
            <p className="mx-auto max-w-2xl text-muted-foreground">
              Nossa plataforma foi criada para ajudar você a encontrar as melhores ofertas sem perder tempo.
            </p>
          </div>

          <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-4">
            {features.map((feature, index) => (
              <Card
                key={index}
                className="group p-6 transition-all duration-300 hover:shadow-lg hover:-translate-y-1"
              >
                <div className="mb-4 flex h-12 w-12 items-center justify-center rounded-xl bg-primary/10 text-primary transition-colors group-hover:bg-primary group-hover:text-primary-foreground">
                  <feature.icon className="h-6 w-6" />
                </div>
                <h3 className="mb-2 font-semibold">{feature.title}</h3>
                <p className="text-sm text-muted-foreground">{feature.description}</p>
              </Card>
            ))}
          </div>
        </div>
      </section>

      {/* Categories Section */}
      <section className="border-y border-border bg-secondary/30 py-16 md:py-24">
        <div className="container">
          <div className="mb-12 text-center">
            <h2 className="mb-4 text-3xl font-bold">Categorias Populares</h2>
            <p className="mx-auto max-w-2xl text-muted-foreground">
              Encontre ofertas nas categorias mais buscadas
            </p>
          </div>

          <div className="grid gap-4 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-6">
            {popularSearches.map((item, index) => (
              <button
                key={index}
                onClick={() => handleSearch(item.term)}
                className="group flex flex-col items-center gap-3 rounded-2xl border border-border bg-card p-6 transition-all duration-300 hover:border-primary/30 hover:shadow-lg hover:-translate-y-1"
              >
                <div className="flex h-14 w-14 items-center justify-center rounded-xl bg-primary/10 text-primary transition-colors group-hover:bg-primary group-hover:text-primary-foreground">
                  <item.icon className="h-7 w-7" />
                </div>
                <span className="text-sm font-medium">{item.term}</span>
              </button>
            ))}
          </div>
        </div>
      </section>

      {/* CTA Section */}
      <section className="py-16 md:py-24">
        <div className="container">
          <Card className="overflow-hidden">
            <div className="relative p-8 md:p-12" style={{ background: 'var(--gradient-primary)' }}>
              <div className="relative z-10 mx-auto max-w-2xl text-center text-primary-foreground">
                <h2 className="mb-4 text-3xl font-bold">
                  Crie Alertas de Preço Personalizados
                </h2>
                <p className="mb-6 text-primary-foreground/80">
                  Não perca mais nenhuma oferta! Crie alertas para os produtos que você deseja e seja
                  notificado por WhatsApp ou e-mail quando o preço cair.
                </p>
                <div className="flex flex-col items-center justify-center gap-4 sm:flex-row">
                  {user ? (
                    <Button
                      asChild
                      size="lg"
                      variant="secondary"
                      className="gap-2"
                    >
                      <Link to="/alertas">
                        Criar Alerta
                        <ArrowRight className="h-4 w-4" />
                      </Link>
                    </Button>
                  ) : (
                    <>
                      <Button asChild size="lg" variant="secondary" className="gap-2">
                        <Link to="/auth?tab=signup">
                          Criar Conta Grátis
                          <ArrowRight className="h-4 w-4" />
                        </Link>
                      </Button>
                      <Button
                        asChild
                        size="lg"
                        variant="ghost"
                        className="text-primary-foreground hover:bg-primary-foreground/10"
                      >
                        <Link to="/auth">Já tenho conta</Link>
                      </Button>
                    </>
                  )}
                </div>
              </div>

              {/* Background Pattern */}
              <div className="absolute inset-0 opacity-10">
                <div className="absolute right-0 top-0 h-64 w-64 -translate-y-1/2 translate-x-1/2 rounded-full bg-white blur-3xl" />
                <div className="absolute bottom-0 left-0 h-64 w-64 -translate-x-1/2 translate-y-1/2 rounded-full bg-white blur-3xl" />
              </div>
            </div>
          </Card>
        </div>
      </section>

      {/* Stats Section */}
      {!user && (
        <section className="border-t border-border py-16">
          <div className="container">
            <div className="grid gap-8 text-center sm:grid-cols-3">
              <div>
                <div className="text-4xl font-bold text-primary">50k+</div>
                <div className="mt-1 text-muted-foreground">Produtos Comparados</div>
              </div>
              <div>
                <div className="text-4xl font-bold text-primary">100+</div>
                <div className="mt-1 text-muted-foreground">Lojas Parceiras</div>
              </div>
              <div>
                <div className="text-4xl font-bold text-primary">10k+</div>
                <div className="mt-1 text-muted-foreground">Usuários Ativos</div>
              </div>
            </div>
          </div>
        </section>
      )}
    </Layout>
  );
}
