import { Outlet, NavLink, useLocation, useNavigate } from 'react-router-dom';
import { useEffect, useState } from 'react';
import SsmLogo from '@/assets/logo/logoSSM.gif';
import { LanguageSwitcher } from '@/components/ui/LanguageSwitcher';
import { BackgroundSelector } from '@/components/ui/BackgroundSelector';
import { NavigationLoadingProvider } from '@/components/ui/NavigationLoader';
import { Server, Map as MapIcon, Users, Settings as SettingsIcon, LayoutDashboard, LogOut, Wrench, X } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { authService } from '@/services/auth';
import { CommandPalette } from '@/components/tools/CommandPalette';
import Swal from 'sweetalert2';
// Removed LanguageSwitcher and BackgroundSelector from header; moved to Settings page

function AppShellContent() {
  const { t } = useTranslation();
  const location = useLocation();
  const navigate = useNavigate();
  const isHome = location.pathname === '/';
  const user = authService.getUserFromStorage();
  const isAuthenticated = authService.isAuthenticated(); // Verificar se está autenticado pelo token
  const isAdmin = authService.isAdmin();
  const [isCommandPaletteOpen, setIsCommandPaletteOpen] = useState(false);
  const [showAbout, setShowAbout] = useState(false);

  useEffect(() => {
    if (!isAdmin) return;
    const onKeyDown = (e: KeyboardEvent) => {
      const key = e.key.toLowerCase();
      if ((e.ctrlKey || e.metaKey) && key === 'k') {
        e.preventDefault();
        setIsCommandPaletteOpen(true);
      }
    };
    window.addEventListener('keydown', onKeyDown);
    return () => window.removeEventListener('keydown', onKeyDown);
  }, [isAdmin]);

  const handleLogout = async () => {
    const result = await Swal.fire({
      icon: 'question',
      title: t('auth.logout.confirmTitle'),
      text: t('auth.logout.confirmMessage'),
      showCancelButton: true,
      confirmButtonColor: '#f97316',
      cancelButtonColor: '#6b7280',
      confirmButtonText: t('auth.logout.button'),
      cancelButtonText: t('common.cancel'),
    });

    if (result.isConfirmed) {
      await authService.logout();
      navigate('/login');
      await Swal.fire({
        icon: 'success',
        title: t('auth.logout.success'),
        confirmButtonColor: '#f97316',
      });
    }
  };
  
  return (
    <div className="min-h-dvh grid grid-rows-[auto_1fr]">
      <header className="sticky top-0 z-[120] border-b border-white/10 bg-black/40 backdrop-blur">
        <div className="mx-auto max-w-7xl px-3 sm:px-4 py-2 sm:py-3 flex items-center gap-2 sm:gap-4">
          {/* Logo Container - Clicável com hover */}
          <button
            type="button"
            onClick={() => setShowAbout(true)}
            className={`flex items-center px-2 sm:px-3 py-1.5 sm:py-2 rounded-lg border transition-all duration-200 focus:outline-none focus-visible:ring-2 focus-visible:ring-scum-orange/70 bg-white/[0.02] border-white/10 text-white/80 hover:bg-white/5 hover:border-white/20 hover:text-white ${
              isHome ? 'shadow-[0_0_0_1px_rgba(255,255,255,0.06)]' : ''
            }`}
            aria-label="About"
            title="About"
          >
            <img 
              src={SsmLogo} 
              alt="SSM" 
              className="h-8 w-8 sm:h-9 sm:w-9 rounded-sm object-contain transition-transform duration-200 hover:scale-105" 
            />
          </button>

          <div className="ml-auto flex items-center gap-2">
            <nav className="flex items-center gap-1.5 sm:gap-3 text-xs sm:text-sm overflow-x-auto whitespace-nowrap [-webkit-overflow-scrolling:touch]">
            <NavLink to="/" className={({ isActive }) => `px-3 py-2 sm:px-4 sm:py-2.5 rounded-lg inline-flex items-center gap-2 ${isActive ? 'bg-scum-panel text-white' : 'text-white/80 hover:text-white'}`}>
              <LayoutDashboard size={16} />
              <span className="hidden md:inline">{t('app.nav.overview')}</span>
            </NavLink>
            <NavLink to="/map" className={({ isActive }) => `px-3 py-2 sm:px-4 sm:py-2.5 rounded-lg inline-flex items-center gap-2 ${isActive ? 'bg-scum-panel text-white' : 'text-white/80 hover:text-white'}`}>
              <MapIcon size={16} /> <span className="hidden md:inline">{t('app.nav.map')}</span>
            </NavLink>
            <NavLink to="/server" className={({ isActive }) => `px-3 py-2 sm:px-4 sm:py-2.5 rounded-lg inline-flex items-center gap-2 ${isActive ? 'bg-scum-panel text-white' : 'text-white/80 hover:text-white'}`}>
              <Server size={16} /> <span className="hidden md:inline">{t('app.nav.server')}</span>
            </NavLink>
            <NavLink to="/players" className={({ isActive }) => `px-3 py-2 sm:px-4 sm:py-2.5 rounded-lg inline-flex items-center gap-2 ${isActive ? 'bg-scum-panel text-white' : 'text-white/80 hover:text-white'}`}>
              <Users size={16} /> <span className="hidden md:inline">{t('app.sidebar.players')}</span>
            </NavLink>
            {isAdmin && (
              <NavLink to="/tools" className={({ isActive }) => `px-3 py-2 sm:px-4 sm:py-2.5 rounded-lg inline-flex items-center gap-2 ${isActive ? 'bg-scum-panel text-white' : 'text-white/80 hover:text-white'}`}>
                <Wrench size={16} /> <span className="hidden md:inline">{t('tools.title', { defaultValue: 'Tools' })}</span>
              </NavLink>
            )}
            <NavLink to="/settings" className={({ isActive }) => `px-3 py-2 sm:px-4 sm:py-2.5 rounded-lg inline-flex items-center gap-2 ${isActive ? 'bg-scum-panel text-white' : 'text-white/80 hover:text-white'}`}>
              <SettingsIcon size={16} /> <span className="hidden md:inline">{t('app.sidebar.settings')}</span>
            </NavLink>
          </nav>
          {/* Controles de idioma/fundo fora do nav com overflow */}
          <div className="h-5 w-px bg-white/10 mx-1 flex-shrink-0" />
          {/* Usuário e Logout */}
          {isAuthenticated && (
            <>
              {user && (
                <div className="hidden md:flex items-center gap-2 px-3 py-1.5 rounded-lg bg-white/5 text-white/80 text-sm">
                  <span className="font-medium">{user.username}</span>
                  <span className="text-white/40">•</span>
                  <span className="text-xs uppercase">{user.role}</span>
                </div>
              )}
              <button
                onClick={handleLogout}
                className="flex items-center gap-2 px-3 py-2 rounded-lg text-white/80 hover:text-white hover:bg-white/5 transition-all duration-200"
                title={t('auth.logout.button')}
                aria-label={t('auth.logout.button')}
              >
                <LogOut size={16} />
              </button>
            </>
          )}
          {/* Ícones compactos no mobile */}
          <div className="md:hidden flex items-center gap-1.5 flex-shrink-0">
            <LanguageSwitcher iconOnly />
            <BackgroundSelector iconOnly />
          </div>
          {/* Controles completos em md+ */}
          <div className="hidden md:block flex-shrink-0"><LanguageSwitcher /></div>
          <div className="hidden md:block flex-shrink-0"><BackgroundSelector /></div>
          </div>
        </div>
      </header>
      <main className="mx-auto max-w-7xl w-full p-3 sm:p-4">
        <Outlet />
      </main>
      {isAdmin && (
        <CommandPalette open={isCommandPaletteOpen} onClose={() => setIsCommandPaletteOpen(false)} />
      )}
      {showAbout && (
        <div className="fixed inset-0 z-[200]">
          <button
            type="button"
            className="absolute inset-0 bg-black/70 backdrop-blur-sm"
            onClick={() => setShowAbout(false)}
            aria-label="Close"
          />
          <div className="absolute inset-0 flex items-start justify-center p-4 sm:p-6" onClick={(e) => e.stopPropagation()}>
            <div className="w-full max-w-md bg-black rounded-xl border border-white/10 shadow-2xl overflow-hidden">
              <div className="p-3 border-b border-white/10 flex items-center justify-between">
                <div className="text-sm font-semibold text-white">Scum Server Manager</div>
                <button
                  type="button"
                  onClick={() => setShowAbout(false)}
                  className="p-2 rounded-lg hover:bg-white/5 text-white/70 hover:text-white transition-colors"
                  aria-label="Close"
                >
                  <X size={16} />
                </button>
              </div>
              <div className="p-6 flex flex-col items-center gap-4">
                <img src={SsmLogo} alt="SSM" className="h-40 w-40 rounded-sm object-contain" />
                <div className="text-white font-semibold">Scum Server Manager</div>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export function AppShell() {
  return (
    <NavigationLoadingProvider>
      <AppShellContent />
    </NavigationLoadingProvider>
  );
}

export default AppShell;


