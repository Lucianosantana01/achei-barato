import { useEffect } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { Layout } from '@/components/layout/Layout';
import { useAuth } from '@/contexts/AuthContext';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Separator } from '@/components/ui/separator';
import { useQuery } from '@tanstack/react-query';
import { supabase } from '@/integrations/supabase/client';
import { SearchQuery } from '@/types';
import {
  User,
  CreditCard,
  Bell,
  Clock,
  Crown,
  Zap,
  Check,
  ArrowRight,
  History,
  Search,
} from 'lucide-react';
import { format } from 'date-fns';
import { ptBR } from 'date-fns/locale';

export default function AccountPage() {
  const { user, profile, loading } = useAuth();
  const navigate = useNavigate();

  useEffect(() => {
    if (!loading && !user) {
      navigate('/auth');
    }
  }, [user, loading, navigate]);

  const { data: searchHistory = [] } = useQuery({
    queryKey: ['searchHistory', user?.id],
    queryFn: async () => {
      const { data } = await supabase
        .from('search_queries')
        .select('*')
        .eq('user_id', user!.id)
        .order('created_at', { ascending: false })
        .limit(10);
      return (data || []) as SearchQuery[];
    },
    enabled: !!user,
  });

  if (loading || !user || !profile) {
    return null;
  }

  const formatDate = (dateString: string) => {
    return format(new Date(dateString), "d 'de' MMMM 'às' HH:mm", { locale: ptBR });
  };

  const getResetInfo = () => {
    if (profile.plan === 'FREE') {
      const resetDate = new Date(profile.credit_reset_at);
      return `Seus créditos serão renovados ${format(resetDate, "d 'de' MMMM", { locale: ptBR })}`;
    } else {
      const cycleEnd = profile.pro_cycle_end ? new Date(profile.pro_cycle_end) : null;
      return cycleEnd
        ? `Ciclo atual termina em ${format(cycleEnd, "d 'de' MMMM", { locale: ptBR })}`
        : 'Ciclo mensal';
    }
  };

  return (
    <Layout>
      <div className="container py-8">
        <div className="mb-8">
          <h1 className="text-3xl font-bold">Minha Conta</h1>
          <p className="text-muted-foreground">Gerencie sua conta e veja seu histórico</p>
        </div>

        <div className="grid gap-6 lg:grid-cols-3">
          {/* Main Content */}
          <div className="space-y-6 lg:col-span-2">
            {/* Profile Card */}
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <User className="h-5 w-5" />
                  Perfil
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="flex items-center gap-4">
                  <div className="flex h-16 w-16 items-center justify-center rounded-full bg-primary text-2xl font-bold text-primary-foreground">
                    {profile.name?.charAt(0).toUpperCase() || user.email?.charAt(0).toUpperCase()}
                  </div>
                  <div>
                    <h3 className="text-lg font-semibold">{profile.name || 'Usuário'}</h3>
                    <p className="text-sm text-muted-foreground">{user.email}</p>
                  </div>
                </div>
              </CardContent>
            </Card>

            {/* Plan Card */}
            <Card id="planos">
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Crown className="h-5 w-5" />
                  Plano Atual
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="flex items-center justify-between">
                  <div>
                    <div className="flex items-center gap-2">
                      <span className="text-2xl font-bold">{profile.plan}</span>
                      <Badge
                        variant={profile.plan === 'PRO' ? 'default' : 'secondary'}
                        className={profile.plan === 'PRO' ? 'bg-gradient-to-r from-primary to-purple-600' : ''}
                      >
                        {profile.plan === 'PRO' ? 'Ativo' : 'Gratuito'}
                      </Badge>
                    </div>
                    <p className="mt-1 text-sm text-muted-foreground">{getResetInfo()}</p>
                  </div>
                  <div className="text-right">
                    <div className="flex items-center gap-1 text-2xl font-bold">
                      <CreditCard className="h-6 w-6 text-primary" />
                      {profile.credits_remaining}
                    </div>
                    <p className="text-sm text-muted-foreground">créditos restantes</p>
                  </div>
                </div>

                {profile.plan === 'FREE' && (
                  <>
                    <Separator className="my-6" />
                    <div className="rounded-xl border-2 border-primary/20 bg-primary/5 p-6">
                      <div className="flex items-center gap-2">
                        <Zap className="h-5 w-5 text-primary" />
                        <h4 className="font-semibold">Upgrade para PRO</h4>
                      </div>
                      <p className="mt-2 text-sm text-muted-foreground">
                        Desbloqueie mais recursos e créditos com o plano PRO
                      </p>
                      <ul className="mt-4 space-y-2">
                        <li className="flex items-center gap-2 text-sm">
                          <Check className="h-4 w-4 text-success" />
                          1000 créditos por mês
                        </li>
                        <li className="flex items-center gap-2 text-sm">
                          <Check className="h-4 w-4 text-success" />
                          Alertas via WhatsApp
                        </li>
                        <li className="flex items-center gap-2 text-sm">
                          <Check className="h-4 w-4 text-success" />
                          Histórico completo
                        </li>
                        <li className="flex items-center gap-2 text-sm">
                          <Check className="h-4 w-4 text-success" />
                          Suporte prioritário
                        </li>
                      </ul>
                      <Button className="mt-4 w-full gap-2">
                        Fazer Upgrade
                        <ArrowRight className="h-4 w-4" />
                      </Button>
                    </div>
                  </>
                )}
              </CardContent>
            </Card>

            {/* Search History */}
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <History className="h-5 w-5" />
                  Histórico de Buscas
                </CardTitle>
                <CardDescription>Suas últimas 10 buscas</CardDescription>
              </CardHeader>
              <CardContent>
                {searchHistory.length === 0 ? (
                  <div className="flex flex-col items-center justify-center py-8 text-center">
                    <Search className="mb-4 h-12 w-12 text-muted-foreground/30" />
                    <p className="text-muted-foreground">Você ainda não fez nenhuma busca</p>
                    <Button asChild className="mt-4" variant="outline">
                      <Link to="/buscar">Fazer primeira busca</Link>
                    </Button>
                  </div>
                ) : (
                  <div className="space-y-3">
                    {searchHistory.map((query) => (
                      <Link
                        key={query.id}
                        to={`/buscar?q=${encodeURIComponent(query.term)}`}
                        className="flex items-center justify-between rounded-lg border border-border p-3 transition-colors hover:bg-secondary/50"
                      >
                        <div className="flex items-center gap-3">
                          <Search className="h-4 w-4 text-muted-foreground" />
                          <div>
                            <p className="font-medium">{query.term}</p>
                            <p className="text-xs text-muted-foreground">
                              {query.results_count} resultados • {formatDate(query.created_at)}
                            </p>
                          </div>
                        </div>
                        <ArrowRight className="h-4 w-4 text-muted-foreground" />
                      </Link>
                    ))}
                  </div>
                )}
              </CardContent>
            </Card>
          </div>

          {/* Sidebar */}
          <div className="space-y-6">
            {/* Quick Actions */}
            <Card>
              <CardHeader>
                <CardTitle>Ações Rápidas</CardTitle>
              </CardHeader>
              <CardContent className="space-y-2">
                <Button asChild variant="outline" className="w-full justify-start gap-2">
                  <Link to="/buscar">
                    <Search className="h-4 w-4" />
                    Nova Busca
                  </Link>
                </Button>
                <Button asChild variant="outline" className="w-full justify-start gap-2">
                  <Link to="/alertas">
                    <Bell className="h-4 w-4" />
                    Gerenciar Alertas
                  </Link>
                </Button>
              </CardContent>
            </Card>

            {/* Plan Comparison */}
            <Card>
              <CardHeader>
                <CardTitle>Comparação de Planos</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-4">
                  <div className="rounded-lg border border-border p-4">
                    <h4 className="font-semibold">FREE</h4>
                    <ul className="mt-2 space-y-1 text-sm text-muted-foreground">
                      <li>• 10 créditos/dia</li>
                      <li>• Alertas por e-mail</li>
                      <li>• Histórico de 7 dias</li>
                    </ul>
                  </div>
                  <div className="rounded-lg border-2 border-primary bg-primary/5 p-4">
                    <div className="flex items-center gap-2">
                      <h4 className="font-semibold">PRO</h4>
                      <Badge className="bg-gradient-to-r from-primary to-purple-600">
                        Recomendado
                      </Badge>
                    </div>
                    <ul className="mt-2 space-y-1 text-sm text-muted-foreground">
                      <li>• 1000 créditos/mês</li>
                      <li>• Alertas via WhatsApp</li>
                      <li>• Histórico ilimitado</li>
                      <li>• Suporte prioritário</li>
                    </ul>
                  </div>
                </div>
              </CardContent>
            </Card>
          </div>
        </div>
      </div>
    </Layout>
  );
}
