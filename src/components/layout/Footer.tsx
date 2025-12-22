import { Link } from 'react-router-dom';
import { Search } from 'lucide-react';

export function Footer() {
  return (
    <footer className="border-t border-border bg-card">
      <div className="container py-8 md:py-12">
        <div className="grid gap-8 md:grid-cols-4">
          {/* Brand */}
          <div className="md:col-span-2">
            <Link to="/" className="flex items-center gap-2">
              <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-primary">
                <Search className="h-5 w-5 text-primary-foreground" />
              </div>
              <span className="font-display text-xl font-bold">Comparador</span>
            </Link>
            <p className="mt-4 max-w-md text-sm text-muted-foreground">
              Compare preços de milhares de produtos em diversas lojas e encontre as melhores ofertas. 
              Economize tempo e dinheiro com nossa plataforma inteligente.
            </p>
          </div>

          {/* Links */}
          <div>
            <h4 className="mb-3 text-sm font-semibold">Navegação</h4>
            <ul className="space-y-2 text-sm text-muted-foreground">
              <li>
                <Link to="/" className="hover:text-foreground transition-colors">
                  Início
                </Link>
              </li>
              <li>
                <Link to="/buscar" className="hover:text-foreground transition-colors">
                  Buscar Produtos
                </Link>
              </li>
              <li>
                <Link to="/alertas" className="hover:text-foreground transition-colors">
                  Alertas de Preço
                </Link>
              </li>
            </ul>
          </div>

          {/* Account */}
          <div>
            <h4 className="mb-3 text-sm font-semibold">Conta</h4>
            <ul className="space-y-2 text-sm text-muted-foreground">
              <li>
                <Link to="/auth" className="hover:text-foreground transition-colors">
                  Entrar / Cadastrar
                </Link>
              </li>
              <li>
                <Link to="/conta" className="hover:text-foreground transition-colors">
                  Minha Conta
                </Link>
              </li>
              <li>
                <Link to="/conta#planos" className="hover:text-foreground transition-colors">
                  Planos e Preços
                </Link>
              </li>
            </ul>
          </div>
        </div>

        <div className="mt-8 flex flex-col items-center justify-between gap-4 border-t border-border pt-8 text-center text-sm text-muted-foreground md:flex-row md:text-left">
          <p>© {new Date().getFullYear()} Comparador de Preços. Todos os direitos reservados.</p>
          <p className="text-xs">
            Preços e disponibilidade sujeitos a alteração sem aviso prévio.
          </p>
        </div>
      </div>
    </footer>
  );
}
