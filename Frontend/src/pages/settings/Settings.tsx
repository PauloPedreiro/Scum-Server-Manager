import { useState, useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import type { MainTab } from './components/MainTabs';
import SettingsHeader from './components/SettingsHeader';
import MainTabs from './components/MainTabs';
import SearchBar from '@/components/ui/SearchBar';
import ServerSettingsTab from './tabs/ServerSettingsTab';
import SettingsSchedulerTab from './tabs/SettingsSchedulerTab';
import DiscordTab from './tabs/DiscordTab';
import ShopNotificationsTab from './tabs/ShopNotificationsTab';
import MinePunishmentTab from './tabs/MinePunishmentTab';
import SquadTkJailTab from './tabs/SquadTkJailTab';
import UsersTab from './tabs/UsersTab';
import KillFeedTab from './tabs/KillFeedTab';
import RconRoutinesTab from './tabs/RconRoutinesTab';
import { authService } from '@/services/auth';

type SectionName = 'General' | 'World' | 'Respawn' | 'Vehicles' | 'Damage' | 'Features';

export default function Settings() {
  const { t } = useTranslation();
  const [activeMainTab, setActiveMainTab] = useState<MainTab>('serverSettings');
  const [isAdmin, setIsAdmin] = useState(false);
  const [activeSection, setActiveSection] = useState<SectionName>('General');
  const [searchQuery, setSearchQuery] = useState('');

  // Verificar status de admin ao montar e quando necessário
  useEffect(() => {
    const checkAdmin = () => {
      const adminStatus = authService.isAdmin();
      setIsAdmin(adminStatus);
    };

    checkAdmin();

    // Verificar periodicamente
    const interval = setInterval(checkAdmin, 2000);

    return () => clearInterval(interval);
  }, []);

  // Se não for admin e estiver na aba users, redirecionar para serverSettings
  useEffect(() => {
    if (activeMainTab === 'users' && !isAdmin) {
      setActiveMainTab('serverSettings');
    }
  }, [activeMainTab, isAdmin]);

  // Obter placeholder da busca baseado na tab ativa
  const getSearchPlaceholder = () => {
    if (activeMainTab === 'discord') {
      return t('settings.discord.search.placeholder');
    }
    if (activeMainTab === 'users') {
      return t('settings.users.search.placeholder');
    }
    if (activeMainTab === 'minePunishment') {
      return t('settings.minePunishment.search.placeholder', 'Buscar configuração de punição...');
    }
    if (activeMainTab === 'squadTkJail') {
      return t('settings.squadTkJail.search.placeholder', 'Buscar configuração de prisão...');
    }
    if (activeMainTab === 'killFeed') {
      return t('settings.killFeed.search.placeholder', 'Buscar configuração de kill feed...');
    }
    if (activeMainTab === 'rconRoutines') {
      return t('settings.rconRoutines.search.placeholder', 'Buscar rotinas RCON...');
    }
    if (activeMainTab === 'settingsScheduler') {
      return t('settings.settingsScheduler.search.placeholder', 'Buscar rotinas de configuração...');
    }
    return t('settings.search.placeholder');
  };

  return (
    <div className="space-y-4">
      <SettingsHeader />

      <MainTabs activeTab={activeMainTab} onTabChange={setActiveMainTab} />

      {/* Campo de Busca (compartilhado) */}
      <div className="card p-4">
        <SearchBar
          value={searchQuery}
          onChange={setSearchQuery}
          placeholder={getSearchPlaceholder()}
        />
      </div>

      {/* Conteúdo baseado na tab principal */}
      {activeMainTab === 'serverSettings' && (
        <ServerSettingsTab
          searchQuery={searchQuery}
          onSearchChange={setSearchQuery}
          activeSection={activeSection}
          onSectionChange={setActiveSection}
        />
      )}

      {activeMainTab === 'settingsScheduler' && (
        <SettingsSchedulerTab searchQuery={searchQuery} />
      )}

      {activeMainTab === 'discord' && (
        <DiscordTab searchQuery={searchQuery} onSearchChange={setSearchQuery} />
      )}

      {activeMainTab === 'shopNotifications' && (
        <ShopNotificationsTab searchQuery={searchQuery} onSearchChange={setSearchQuery} />
      )}

      {activeMainTab === 'minePunishment' && (
        <MinePunishmentTab searchQuery={searchQuery} onSearchChange={setSearchQuery} />
      )}

      {activeMainTab === 'squadTkJail' && (
        <SquadTkJailTab searchQuery={searchQuery} onSearchChange={setSearchQuery} />
      )}

      {activeMainTab === 'killFeed' && (
        <KillFeedTab searchQuery={searchQuery} onSearchChange={setSearchQuery} />
      )}

      {activeMainTab === 'rconRoutines' && (
        <RconRoutinesTab searchQuery={searchQuery} onSearchChange={setSearchQuery} />
      )}

      {activeMainTab === 'users' && (
        <UsersTab searchQuery={searchQuery} onSearchChange={setSearchQuery} />
      )}
    </div>
  );
}
