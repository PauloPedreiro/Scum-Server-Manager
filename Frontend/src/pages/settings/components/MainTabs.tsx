import { useState, useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import { authService } from '@/services/auth';

export type MainTab = 'serverSettings' | 'settingsScheduler' | 'discord' | 'shopNotifications' | 'minePunishment' | 'squadTkJail' | 'killFeed' | 'rconRoutines' | 'users';

interface MainTabsProps {
  activeTab: MainTab;
  onTabChange: (tab: MainTab) => void;
}

export default function MainTabs({ activeTab, onTabChange }: MainTabsProps) {
  const { t } = useTranslation();
  const [isAdmin, setIsAdmin] = useState(false);

  useEffect(() => {
    // Verificar status de admin
    const checkAdmin = () => {
      const adminStatus = authService.isAdmin();
      setIsAdmin(adminStatus);
    };

    checkAdmin();

    // Verificar quando o storage mudar (evento customizado ou polling)
    const handleStorageChange = () => {
      checkAdmin();
    };

    // Verificar periodicamente (a cada 2 segundos) para atualizar se o status mudar
    const interval = setInterval(checkAdmin, 2000);

    // Escutar mudanças no localStorage
    window.addEventListener('storage', handleStorageChange);

    return () => {
      clearInterval(interval);
      window.removeEventListener('storage', handleStorageChange);
    };
  }, []);

  const tabs: { id: MainTab; label: string }[] = [
    { id: 'serverSettings', label: t('settings.tabs.serverSettings') },
    { id: 'settingsScheduler', label: t('settings.tabs.settingsScheduler', 'Agendador de Configs') },
    { id: 'discord', label: t('settings.tabs.discord') },
    { id: 'shopNotifications', label: t('settings.tabs.shopNotifications') },
    { id: 'minePunishment', label: t('settings.tabs.minePunishment', 'Punição de Minas') },
    { id: 'squadTkJail', label: t('settings.tabs.squadTkJail', 'Squad TK Jail') },
    { id: 'killFeed', label: t('settings.tabs.killFeed', 'Kill Feed') },
    { id: 'rconRoutines', label: t('settings.tabs.rconRoutines', 'Rotinas RCON') },
    ...(isAdmin ? [{ id: 'users' as MainTab, label: t('settings.tabs.users') }] : []),
  ];

  return (
    <div className="card p-2 sm:p-4">
      <div className="flex flex-wrap gap-2">
        {tabs.map((tab) => (
          <button
            key={tab.id}
            onClick={() => onTabChange(tab.id)}
            className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
              activeTab === tab.id
                ? 'bg-scum-orange text-white'
                : 'bg-white/5 text-white/70 hover:bg-white/10 hover:text-white'
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>
    </div>
  );
}

