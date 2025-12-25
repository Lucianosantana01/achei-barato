import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Layout } from '@/components/layout/Layout';
import { useAuth } from '@/contexts/AuthContext';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Switch } from '@/components/ui/switch';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from '@/components/ui/dialog';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { supabase } from '@/integrations/supabase/client';
import { PriceAlert } from '@/types';
import { toast } from 'sonner';
import { Bell, Plus, Trash2, Edit, BellOff } from 'lucide-react';

export default function AlertsPage() {
  const { user, profile, loading } = useAuth();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [isDialogOpen, setIsDialogOpen] = useState(false);
  const [term, setTerm] = useState('');
  const [targetPrice, setTargetPrice] = useState('');

  useEffect(() => {
    if (!loading && !user) {
      navigate('/auth');
    }
  }, [user, loading, navigate]);

  const { data: alerts = [] } = useQuery({
    queryKey: ['alerts', user?.id],
    queryFn: async () => {
      const { data } = await supabase
        .from('price_alerts')
        .select('*')
        .eq('user_id', user!.id)
        .order('created_at', { ascending: false });
      return (data || []) as PriceAlert[];
    },
    enabled: !!user,
  });

  const createAlert = useMutation({
    mutationFn: async () => {
      const { error } = await supabase.from('price_alerts').insert([{
        user_id: user!.id,
        term,
        target_price: parseFloat(targetPrice),
        active: true,
      }]);
      if (error) throw error;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['alerts'] });
      toast.success('Alerta criado com sucesso!');
      setIsDialogOpen(false);
      setTerm('');
      setTargetPrice('');
    },
    onError: () => toast.error('Erro ao criar alerta'),
  });

  const toggleAlert = useMutation({
    mutationFn: async ({ id, active }: { id: string; active: boolean }) => {
      await supabase.from('price_alerts').update({ active }).eq('id', id);
    },
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['alerts'] }),
  });

  const deleteAlert = useMutation({
    mutationFn: async (id: string) => {
      await supabase.from('price_alerts').delete().eq('id', id);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['alerts'] });
      toast.success('Alerta removido');
    },
  });

  if (loading || !user) return null;

  const formatPrice = (price: number) =>
    new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' }).format(price);

  return (
    <Layout>
      <div className="container py-8">
        <div className="mb-8 flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold">Alertas de Preço</h1>
            <p className="text-muted-foreground">Seja notificado quando o preço cair</p>
          </div>
          <Dialog open={isDialogOpen} onOpenChange={setIsDialogOpen}>
            <DialogTrigger asChild>
              <Button className="gap-2">
                <Plus className="h-4 w-4" />
                Novo Alerta
              </Button>
            </DialogTrigger>
            <DialogContent>
              <DialogHeader>
                <DialogTitle>Criar Alerta de Preço</DialogTitle>
              </DialogHeader>
              <div className="space-y-4">
                <div className="space-y-2">
                  <Label>Produto</Label>
                  <Input placeholder="Ex: iPhone 15" value={term} onChange={(e) => setTerm(e.target.value)} />
                </div>
                <div className="space-y-2">
                  <Label>Preço Alvo (R$)</Label>
                  <Input type="number" placeholder="Ex: 4500" value={targetPrice} onChange={(e) => setTargetPrice(e.target.value)} />
                </div>
                <Button onClick={() => createAlert.mutate()} className="w-full" disabled={!term || !targetPrice}>
                  Criar Alerta
                </Button>
              </div>
            </DialogContent>
          </Dialog>
        </div>

        {alerts.length === 0 ? (
          <Card className="flex flex-col items-center justify-center py-16 text-center">
            <Bell className="mb-4 h-16 w-16 text-muted-foreground/30" />
            <h3 className="text-xl font-semibold">Nenhum alerta criado</h3>
            <p className="mt-2 text-muted-foreground">Crie alertas para ser notificado quando o preço cair</p>
          </Card>
        ) : (
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {alerts.map((alert) => (
              <Card key={alert.id} className={!alert.active ? 'opacity-60' : ''}>
                <CardHeader className="flex flex-row items-center justify-between pb-2">
                  <CardTitle className="text-base">{alert.term}</CardTitle>
                  <Switch checked={alert.active} onCheckedChange={(active) => toggleAlert.mutate({ id: alert.id, active })} />
                </CardHeader>
                <CardContent>
                  <p className="text-2xl font-bold text-success">{formatPrice(alert.target_price)}</p>
                  <p className="mt-1 text-sm text-muted-foreground">
                    {alert.active ? 'Notificar quando atingir' : 'Alerta pausado'}
                  </p>
                  <Button variant="ghost" size="sm" className="mt-4 text-destructive" onClick={() => deleteAlert.mutate(alert.id)}>
                    <Trash2 className="mr-2 h-4 w-4" />
                    Remover
                  </Button>
                </CardContent>
              </Card>
            ))}
          </div>
        )}
      </div>
    </Layout>
  );
}
