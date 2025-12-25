import { Link, useNavigate } from 'react-router-dom';
import { Button } from '@/components/ui/button';
import { 
  DropdownMenu, 
  DropdownMenuContent, 
  DropdownMenuItem, 
  DropdownMenuSeparator, 
  DropdownMenuTrigger 
} from '@/components/ui/dropdown-menu';
import { Avatar, AvatarFallback } from '@/components/ui/avatar';
import { useAuth } from '@/contexts/AuthContext';
import { 
  Search, 
  Bell, 
  User, 
  LogOut, 
  Settings, 
  CreditCard,
  Shield,
  Menu,
  X
} from 'lucide-react';
import { useState } from 'react';

export function Header() {
  const { user, profile, isAdmin, signOut } = useAuth();
  const navigate = useNavigate();
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  const handleSignOut = async () => {
    await signOut();
    navigate('/');
  };

  const getInitials = (name: string | null, email: string | undefined) => {
    if (name) {
      return name.split(' ').map(n => n[0]).join('').toUpperCase().slice(0, 2);
    }
    return email?.slice(0, 2).toUpperCase() || 'U';
  };

  return (
    <header className="sticky top-0 z-50 w-full border-b border-border bg-card/95 backdrop-blur supports-[backdrop-filter]:bg-card/80">
      <div className="container flex h-16 items-center justify-between overflow-visible">
        {/* Logo */}
        <Link to="/" className="flex items-center gap-2 overflow-visible">
          <img
            src="https://jlrgspohnhtxbxdhvtpk.supabase.co/storage/v1/object/public/ImagensBarateiro/ChatGPT_Image_22_de_dez._de_2025__18_07_23-removebg-preview.png"
            alt="Achei Barato"
            className="h-[182px] w-auto object-contain"
          />
        </Link>

        {/* Desktop Navigation */}
        <nav className="hidden items-center gap-1 md:flex">
          <Link to="/" className="nav-link">
            Início
          </Link>
          <Link to="/buscar" className="nav-link">
            Buscar
          </Link>
          {user && (
            <Link to="/alertas" className="nav-link">
              Alertas
            </Link>
          )}
        </nav>

        {/* Actions */}
        <div className="flex items-center gap-2">
          {user ? (
            <>
              {/* Credits Badge */}
              {profile && (
                <div className="hidden items-center gap-2 sm:flex">
                  <span className="credit-badge">
                    <CreditCard className="h-3 w-3" />
                    {profile.credits_remaining} créditos
                  </span>
                  <span className={profile.plan === 'PRO' ? 'plan-badge-pro' : 'plan-badge-free'}>
                    {profile.plan}
                  </span>
                </div>
              )}

              {/* Notifications */}
              <Button variant="ghost" size="icon" className="relative" asChild>
                <Link to="/alertas">
                  <Bell className="h-5 w-5" />
                </Link>
              </Button>

              {/* User Menu */}
              <DropdownMenu>
                <DropdownMenuTrigger asChild>
                  <Button variant="ghost" size="icon" className="rounded-full">
                    <Avatar className="h-8 w-8">
                      <AvatarFallback className="bg-primary text-primary-foreground text-sm">
                        {getInitials(profile?.name, user.email)}
                      </AvatarFallback>
                    </Avatar>
                  </Button>
                </DropdownMenuTrigger>
                <DropdownMenuContent align="end" className="w-56">
                  <div className="px-2 py-1.5">
                    <p className="text-sm font-medium">{profile?.name || user.email}</p>
                    <p className="text-xs text-muted-foreground">{user.email}</p>
                  </div>
                  <DropdownMenuSeparator />
                  <DropdownMenuItem asChild>
                    <Link to="/conta" className="cursor-pointer">
                      <User className="mr-2 h-4 w-4" />
                      Minha Conta
                    </Link>
                  </DropdownMenuItem>
                  <DropdownMenuItem asChild>
                    <Link to="/alertas" className="cursor-pointer">
                      <Bell className="mr-2 h-4 w-4" />
                      Meus Alertas
                    </Link>
                  </DropdownMenuItem>
                  {isAdmin && (
                    <>
                      <DropdownMenuSeparator />
                      <DropdownMenuItem asChild>
                        <Link to="/admin" className="cursor-pointer">
                          <Shield className="mr-2 h-4 w-4" />
                          Painel Admin
                        </Link>
                      </DropdownMenuItem>
                    </>
                  )}
                  <DropdownMenuSeparator />
                  <DropdownMenuItem onClick={handleSignOut} className="cursor-pointer text-destructive">
                    <LogOut className="mr-2 h-4 w-4" />
                    Sair
                  </DropdownMenuItem>
                </DropdownMenuContent>
              </DropdownMenu>
            </>
          ) : (
            <>
              <Button variant="ghost" asChild className="hidden sm:inline-flex">
                <Link to="/auth">Entrar</Link>
              </Button>
              <Button asChild>
                <Link to="/auth?tab=signup">Criar Conta</Link>
              </Button>
            </>
          )}

          {/* Mobile Menu Toggle */}
          <Button
            variant="ghost"
            size="icon"
            className="md:hidden"
            onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
          >
            {mobileMenuOpen ? <X className="h-5 w-5" /> : <Menu className="h-5 w-5" />}
          </Button>
        </div>
      </div>

      {/* Mobile Menu */}
      {mobileMenuOpen && (
        <div className="border-t border-border bg-card md:hidden">
          <nav className="container flex flex-col gap-1 py-4">
            <Link
              to="/"
              className="rounded-lg px-4 py-2 text-sm font-medium hover:bg-secondary"
              onClick={() => setMobileMenuOpen(false)}
            >
              Início
            </Link>
            <Link
              to="/buscar"
              className="rounded-lg px-4 py-2 text-sm font-medium hover:bg-secondary"
              onClick={() => setMobileMenuOpen(false)}
            >
              Buscar
            </Link>
            {user && (
              <Link
                to="/alertas"
                className="rounded-lg px-4 py-2 text-sm font-medium hover:bg-secondary"
                onClick={() => setMobileMenuOpen(false)}
              >
                Alertas
              </Link>
            )}
            {!user && (
              <Link
                to="/auth"
                className="rounded-lg px-4 py-2 text-sm font-medium hover:bg-secondary"
                onClick={() => setMobileMenuOpen(false)}
              >
                Entrar
              </Link>
            )}
          </nav>
        </div>
      )}
    </header>
  );
}
