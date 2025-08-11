import React, { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import ScumBackground from '../components/ScumBackground';
import { useLanguage } from '../contexts/LanguageContext';
import DashboardHeader from '../components/DashboardHeader';
import DashboardSidebar from '../components/DashboardSidebar';
import MobileMenu from '../components/MobileMenu';
import DiscordWebhookCard from '../components/DiscordWebhookCard';
import { WebhookService } from '../services/webhookService';
import { PlayerService, Player } from '../services/playerService';
import PlayersTable from '../components/PlayersTable';

import ChatMessagesCard from '../components/ChatMessagesCard';
import VehiclesTable from '../components/VehiclesTable';
import { VehicleService, VehicleEvent } from '../services/vehicleService';
import VehicleEventBreakingNewsBar from '../components/VehicleEventBreakingNewsBar';
import { AdminLogService, AdminLogEvent } from '../services/adminLogService';
import AdminLogTable from '../components/AdminLogTable';
import BunkerStatusCard from '../components/BunkerStatusCard';
import FamePlayersList from '../components/FamePlayersList';

import FameTop3BreakingNewsBar from '../components/FameTop3BreakingNewsBar';
import { FamePlayer } from '../types/fame';
import { FameService } from '../services/fameService';
import ServerControlCard from '../components/ServerControlCard';
import SettingsCard from '../components/SettingsCard';
import ServerConfigurationCard from '../components/ServerConfigurationCard';
import DonationModal from '../components/DonationModal';
import { AdminService } from '../services/adminService';
import { ServerSettingsAdminUsersService } from '../services/serverSettingsAdminUsersService';
import { WhitelistService } from '../services/whitelistService';
import { BanService } from '../services/banService';
import { ExclusiveService } from '../services/exclusiveService';
import { SilenceService } from '../services/silenceService';
import ManualUpdateControls from '../components/ManualUpdateControls';
import FullscreenToggle from '../components/FullscreenToggle';

interface ChatMessage {
  timestamp: string;
  steamId: string;
  playerName: string;
  chatType: string;
  message: string;
}



const Dashboard: React.FC = () => {
  const { t } = useLanguage();
  const [activeSection, setActiveSection] = useState('dashboard');
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);
  

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [painelPlayersWebhook, setPainelPlayersWebhook] = useState('');
  const [veiculosWebhook, setVeiculosWebhook] = useState('');
  const [adminLogWebhook, setAdminLogWebhook] = useState('');
  const [chatInGameWebhook, setChatInGameWebhook] = useState('');
  const [bunkersWebhook, setBunkersWebhook] = useState('');
  const [famaWebhook, setFamaWebhook] = useState('');
  const [serverStatusWebhook, setServerStatusWebhook] = useState('');
  const [funnyStatisticWebhook, setFunnyStatisticWebhook] = useState('');
  const [playerCount, setPlayerCount] = useState(0);
  const [players, setPlayers] = useState<Player[]>([]);

  const [chatInGameAtivo, setChatInGameAtivo] = useState(() => {
    const saved = localStorage.getItem('chatInGameAtivo');
    return saved === null ? true : saved === 'true';
  });
  const [chatMessages, setChatMessages] = useState<ChatMessage[]>([]);

  const [vehicles, setVehicles] = useState<VehicleEvent[]>([]);



  const [adminLogEvents, setAdminLogEvents] = useState<AdminLogEvent[]>([]);
  const [loadingAdminLog] = useState(false);
  const [top3FamePlayers, setTop3FamePlayers] = useState<FamePlayer[]>([]);

  // Estado para ocultar Steam IDs (para vídeos)
  const [hideSteamIds, setHideSteamIds] = useState(() => {
    const saved = localStorage.getItem('hideSteamIds');
    return saved === null ? false : saved === 'true';
  });

  // Estado para controlar o modal de doação
  const [isDonationModalOpen, setIsDonationModalOpen] = useState(false);

  const [adminSteamIds, setAdminSteamIds] = useState<string[]>([]);
  const [serverSettingsAdminSteamIds, setServerSettingsAdminSteamIds] = useState<string[]>([]);
  
  // Debug effect para monitorar mudanças no estado
  useEffect(() => {
    console.log('Server settings admin steam IDs changed:', serverSettingsAdminSteamIds);
    console.log('Length:', serverSettingsAdminSteamIds.length);
  }, [serverSettingsAdminSteamIds]);
  const [whitelistedSteamIds, setWhitelistedSteamIds] = useState<string[]>([]);
  const [bannedSteamIds, setBannedSteamIds] = useState<string[]>([]);
  const [exclusiveSteamIds, setExclusiveSteamIds] = useState<string[]>([]);
  const [silencedSteamIds, setSilencedSteamIds] = useState<string[]>([]);

  // Carregar dados iniciais do dashboard
  useEffect(() => {
    const loadDashboardData = async () => {
      try {
        setLoading(true);
        setError(null);
        
        console.log('Iniciando carregamento de dados do dashboard...');
        
        // Simular delay de carregamento
        await new Promise(resolve => setTimeout(resolve, 1000));
        
        console.log('Dados carregados com sucesso');
      } catch (err) {
        console.error('Erro ao carregar dados do dashboard:', err);
        setError('Erro ao carregar dados do servidor.');
      } finally {
        setLoading(false);
      }
    };

    loadDashboardData();
  }, []);

  // Carregar dados iniciais (apenas uma vez)
  useEffect(() => {
    const loadInitialData = async () => {
      try {
        // Carregar jogadores iniciais
        const players = await PlayerService.getPainelPlayers();
        setPlayers(players);
        const online = players.filter(p => p.isOnline).length;
        setPlayerCount(online);
      } catch (err) {
        setPlayers([]);
        setPlayerCount(0);
      }

      try {
        // Carregar top 3 fama inicial
        const response = await FameService.getFamePoints();
        if (response.success && response.data) {
          const sortedPlayers = response.data.sort((a, b) => b.totalFame - a.totalFame);
          const top3 = sortedPlayers.slice(0, 3);
          setTop3FamePlayers(top3);
        } else {
          setTop3FamePlayers([]);
        }
      } catch (err) {
        setTop3FamePlayers([]);
      }
    };

    loadInitialData();
  }, []);

  // Buscar os webhooks salvos ao abrir a tela
  useEffect(() => {
    const fetchWebhooks = async () => {
      console.log('🔍 Iniciando busca dos webhooks...');
      try {
        // Painel Players
        try {
          console.log('📡 Buscando webhook Painel Players...');
          const painelPlayersResult = await WebhookService.getPainelPlayersWebhook();
          console.log('📡 Resultado Painel Players:', painelPlayersResult);
          if (painelPlayersResult.success && painelPlayersResult.url) {
            setPainelPlayersWebhook(painelPlayersResult.url);
          } else {
            setPainelPlayersWebhook('');
          }
        } catch (err) {
          console.error('❌ Erro ao buscar Painel Players:', err);
          setPainelPlayersWebhook('');
        }
        
        // Chat in Game
        try {
          console.log('📡 Buscando webhook Chat in Game...');
          const chatInGameResult = await WebhookService.getChatInGameWebhook();
          console.log('📡 Resultado Chat in Game:', chatInGameResult);
          if (chatInGameResult.success && chatInGameResult.url) {
            setChatInGameWebhook(chatInGameResult.url);
          } else {
            setChatInGameWebhook('');
          }
        } catch (err) {
          console.error('❌ Erro ao buscar Chat in Game:', err);
          setChatInGameWebhook('');
        }
        
        // Veículos
        try {
          console.log('📡 Buscando webhook Veículos...');
          const veiculosResult = await WebhookService.getLogVeiculosWebhook();
          console.log('📡 Resultado Veículos:', veiculosResult);
          if (veiculosResult.success && veiculosResult.url) {
            setVeiculosWebhook(veiculosResult.url);
          } else if (veiculosResult.success && veiculosResult.data && veiculosResult.data.url) {
            setVeiculosWebhook(veiculosResult.data.url);
          } else {
            setVeiculosWebhook('');
          }
        } catch (err) {
          console.error('❌ Erro ao buscar Veículos:', err);
          setVeiculosWebhook('');
        }
        
        // Admin Log
        try {
          console.log('📡 Buscando webhook Admin Log...');
          const adminLogResult = await WebhookService.getAdminLogWebhook();
          console.log('📡 Resultado Admin Log:', adminLogResult);
          if (adminLogResult.success && adminLogResult.url) {
            setAdminLogWebhook(adminLogResult.url);
          } else {
            setAdminLogWebhook('');
          }
        } catch (err) {
          console.error('❌ Erro ao buscar Admin Log:', err);
          setAdminLogWebhook('');
        }
        
        // Bunkers
        try {
          console.log('📡 Buscando webhook Bunkers...');
          const bunkersResult = await WebhookService.getBunkersWebhook();
          console.log('📡 Resultado Bunkers:', bunkersResult);
          if (bunkersResult.success && bunkersResult.url) {
            setBunkersWebhook(bunkersResult.url);
          } else {
            setBunkersWebhook('');
          }
        } catch (err) {
          console.error('❌ Erro ao buscar Bunkers:', err);
          setBunkersWebhook('');
        }
        
        // Fama
        try {
          console.log('📡 Buscando webhook Fama...');
          const famaResult = await WebhookService.getFamaWebhook();
          console.log('📡 Resultado Fama:', famaResult);
          if (famaResult.success && famaResult.url) {
            setFamaWebhook(famaResult.url);
          } else {
            setFamaWebhook('');
          }
        } catch (err) {
          console.error('❌ Erro ao buscar Fama:', err);
          setFamaWebhook('');
        }
        
        // Server Status
        try {
          console.log('📡 Buscando webhook Server Status...');
          const serverStatusResult = await WebhookService.getServerStatusWebhook();
          console.log('📡 Resultado Server Status:', serverStatusResult);
          if (serverStatusResult.success && serverStatusResult.url) {
            setServerStatusWebhook(serverStatusResult.url);
          } else {
            setServerStatusWebhook('');
          }
        } catch (err) {
          console.error('❌ Erro ao buscar Server Status:', err);
          setServerStatusWebhook('');
        }
        
        // Funny Statistic
        try {
          console.log('📡 Buscando webhook Funny Statistic...');
          const funnyStatisticResult = await WebhookService.getFunnyStatisticWebhook();
          console.log('📡 Resultado Funny Statistic:', funnyStatisticResult);
          if (funnyStatisticResult.success && funnyStatisticResult.url) {
            setFunnyStatisticWebhook(funnyStatisticResult.url);
          } else {
            setFunnyStatisticWebhook('');
          }
        } catch (err) {
          console.error('❌ Erro ao buscar Funny Statistic:', err);
          setFunnyStatisticWebhook('');
        }
        
        console.log('✅ Busca dos webhooks concluída!');
      } catch (err) {
        console.error('❌ Erro geral ao buscar webhooks:', err);
      }
    };
    fetchWebhooks();
  }, []);

  // Atualiza localStorage ao mudar o estado do chat
  useEffect(() => {
    localStorage.setItem('chatInGameAtivo', chatInGameAtivo.toString());
  }, [chatInGameAtivo]);

  // Atualiza localStorage ao mudar o estado de ocultar Steam IDs
  useEffect(() => {
    localStorage.setItem('hideSteamIds', hideSteamIds.toString());
  }, [hideSteamIds]);

  // Consulta Chat In Game após Painel Players se estiver ativo
  useEffect(() => {
    if (!chatInGameAtivo) return;
    // Consulta após fetchPlayers (Painel Players)
    const fetchChatInGame = async () => {
      try {
        await WebhookService.getChatInGameWebhook();
        // Aqui pode adicionar lógica futura de atualização de dados do chat
      } catch (err) {
        // Tratar erro se necessário
      }
    };
    fetchChatInGame();
  }, [chatInGameAtivo]); // Removido 'players' da dependência

  // Carregar dados iniciais de chat e veículos (apenas uma vez)
  useEffect(() => {
    const loadInitialChatAndVehicles = async () => {
      // Carregar chat inicial
      if (chatInGameAtivo) {
        try {
          const result = await WebhookService.getChatInGameMessages();
          if (result.success && Array.isArray(result.data) && result.data.length > 0) {
            setChatMessages(result.data.map((msg: any) => ({
              timestamp: msg.timestamp,
              steamId: msg.steamId,
              playerName: msg.playerName,
              chatType: msg.chatType,
              message: msg.message
            })));
          }
        } catch (err) {
          console.error('Erro ao carregar chat inicial:', err);
        }
      }

      // Carregar veículos iniciais
      try {
        const res = await VehicleService.getHistory();
        if (res.success && Array.isArray(res.data)) {
          setVehicles(res.data);
        }
      } catch (err) {
        console.error('Erro ao carregar veículos iniciais:', err);
      }
    };

    loadInitialChatAndVehicles();
  }, [chatInGameAtivo]);

  // Carregar admin log inicial (apenas uma vez)
  useEffect(() => {
    const loadInitialAdminLog = async () => {
      try {
        const res = await AdminLogService.getAdminLog();
        if (res.success && res.data) {
          let lines: string[] = [];
          if (Array.isArray(res.data)) lines = res.data;
          else if (typeof res.data === 'string') lines = res.data.split('\n').filter(l => l.trim() !== '');
          setAdminLogEvents(AdminLogService.parseLogLines(lines).reverse());
        }
      } catch (err) {
        console.error('Erro ao carregar admin log inicial:', err);
      }
    };

    loadInitialAdminLog();
  }, []);

  // Buscar admins ao abrir a tela e atualizar quando necessário
  useEffect(() => {
    const fetchAdmins = async () => {
      try {
        const res = await AdminService.listAdmins();
        if (res.success && Array.isArray(res.admins)) {
          setAdminSteamIds(res.admins.map(a => a.steamId.replace('[setgodmode]', '')));
        } else {
          setAdminSteamIds([]);
        }
      } catch {
        setAdminSteamIds([]);
      }
    };
    fetchAdmins();
  }, []);

  // Buscar admins de configuração ao abrir a tela e atualizar quando necessário
  useEffect(() => {
    const fetchServerSettingsAdmins = async () => {
      try {
        console.log('Fetching server settings admins on mount...');
        const res = await ServerSettingsAdminUsersService.getServerSettingsAdminUsers();
        console.log('Initial server settings admins response:', res);
        if (res.success && Array.isArray(res.admins)) {
          const steamIds = res.admins.map(a => a.steamId);
          console.log('Initial server settings admin steam IDs:', steamIds);
          console.log('Initial steam IDs length:', steamIds.length);
          setServerSettingsAdminSteamIds(steamIds);
        } else {
          console.log('No initial admins found, setting empty array');
          console.log('Initial response:', res);
          setServerSettingsAdminSteamIds([]);
        }
      } catch (error) {
        console.error('Error fetching initial server settings admins:', error);
        setServerSettingsAdminSteamIds([]);
      }
    };
    fetchServerSettingsAdmins();
  }, []);

  // Buscar whitelist ao abrir a tela e atualizar quando necessário
  useEffect(() => {
    const fetchWhitelist = async () => {
      try {
        const res = await WhitelistService.listWhitelistedUsers();
        if (res.success && Array.isArray(res.whitelistedUsers)) {
          setWhitelistedSteamIds(res.whitelistedUsers.map(u => u.steamId));
        } else {
          setWhitelistedSteamIds([]);
        }
      } catch {
        setWhitelistedSteamIds([]);
      }
    };
    fetchWhitelist();
  }, []);

  // Buscar lista de banidos ao abrir a tela e atualizar quando necessário
  useEffect(() => {
    const fetchBanList = async () => {
      try {
        const res = await BanService.listBannedUsers();
        if (res.success && Array.isArray(res.bannedUsers)) {
          setBannedSteamIds(res.bannedUsers.map(u => u.steamId));
        } else {
          setBannedSteamIds([]);
        }
      } catch {
        setBannedSteamIds([]);
      }
    };
    fetchBanList();
  }, []);

  // Buscar lista de exclusivos ao abrir a tela e atualizar quando necessário
  useEffect(() => {
    const fetchExclusiveList = async () => {
      try {
        const res = await ExclusiveService.listExclusiveUsers();
        if (res.success && Array.isArray(res.exclusiveUsers)) {
          setExclusiveSteamIds(res.exclusiveUsers.map(u => u.steamId));
        } else {
          setExclusiveSteamIds([]);
        }
      } catch {
        setExclusiveSteamIds([]);
      }
    };
    fetchExclusiveList();
  }, []);

  // Buscar lista de silenciados ao abrir a tela e atualizar quando necessário
  useEffect(() => {
    const fetchSilenceList = async () => {
      try {
        const res = await SilenceService.listSilencedUsers();
        if (res.success && Array.isArray(res.silencedUsers)) {
          setSilencedSteamIds(res.silencedUsers.map(u => u.steamId));
        } else {
          setSilencedSteamIds([]);
        }
      } catch {
        setSilencedSteamIds([]);
      }
    };
    fetchSilenceList();
  }, []);

  // Funções para gerenciar webhooks
  const handleSaveWebhook = async (url: string, webhookType: string) => {
    console.log('Salvando webhook:', webhookType, url);
    try {
      switch (webhookType) {
        case 'painelPlayers': {
          const response = await WebhookService.savePainelPlayersWebhook(url);
          if (response.success) {
            setPainelPlayersWebhook(url);
            return response;
          } else {
            throw new Error(response.message);
          }
        }
        case 'veiculos': {
          const response = await WebhookService.saveLogVeiculosWebhook(url);
          if (response.success && (response.url || (response.data && response.data.url))) {
            setVeiculosWebhook(response.url || response.data.url);
            return response;
          } else {
            throw new Error(response.message || 'Erro ao salvar webhook Veiculos');
          }
        }
        case 'adminLog': {
          const response = await WebhookService.saveAdminLogWebhook(url);
          if (response.success) {
            setAdminLogWebhook(url);
            return response;
          } else {
            throw new Error(response.message);
          }
        }
        case 'chatInGame': {
          const response = await WebhookService.saveChatInGameWebhook(url);
          if (response.success) {
            setChatInGameWebhook(url);
            return response;
          } else {
            throw new Error(response.message);
          }
        }
        case 'bunkers': {
          const response = await WebhookService.saveBunkersWebhook(url);
          if (response.success) {
            setBunkersWebhook(url);
            return response;
          } else {
            throw new Error(response.message);
          }
        }
        case 'fama': {
          const response = await WebhookService.saveFamaWebhook(url);
          if (response.success) {
            setFamaWebhook(url);
            return response;
          } else {
            throw new Error(response.message);
          }
        }
        case 'serverStatus': {
          const response = await WebhookService.saveServerStatusWebhook(url);
          if (response.success) {
            setServerStatusWebhook(url);
            return response;
          } else {
            throw new Error(response.message);
          }
        }
        case 'funnyStatistic': {
          const response = await WebhookService.saveFunnyStatisticWebhook(url);
          if (response.success) {
            setFunnyStatisticWebhook(url);
            return response;
          } else {
            throw new Error(response.message);
          }
        }
      }
    } catch (error) {
      console.error('Erro ao salvar webhook:', error);
      throw error;
    }
  };

  const handleTestWebhook = async (url: string, webhookType: string) => {
    console.log('Testando webhook:', webhookType, url);
    try {
      switch (webhookType) {
        case 'painelPlayers':
          return await WebhookService.testWebhook(url);
        case 'veiculos':
          return await WebhookService.testWebhook(url);
        case 'adminLog':
          return await WebhookService.testWebhook(url);
        case 'chatInGame':
          return await WebhookService.testWebhook(url);
        case 'bunkers':
          return await WebhookService.testWebhook(url);
        case 'fama':
          return await WebhookService.testWebhook(url);
        case 'serverStatus':
          return await WebhookService.testWebhook(url);
        case 'funnyStatistic':
          return await WebhookService.testWebhook(url);
      }
    } catch (error) {
      console.error('Erro ao testar webhook:', error);
      throw error;
    }
  };

  // Função para atualizar admins após adicionar
  const refreshAdmins = async () => {
    try {
      const res = await AdminService.listAdmins();
      if (res.success && Array.isArray(res.admins)) {
        setAdminSteamIds(res.admins.map(a => a.steamId.replace('[setgodmode]', '')));
      } else {
        setAdminSteamIds([]);
      }
    } catch {
      setAdminSteamIds([]);
    }
  };

  const refreshServerSettingsAdmins = async () => {
    try {
      console.log('Refreshing server settings admins...');
      const res = await ServerSettingsAdminUsersService.getServerSettingsAdminUsers();
      console.log('Server settings admins response:', res);
              if (res.success && Array.isArray(res.admins)) {
          const steamIds = res.admins.map(a => a.steamId);
          console.log('Setting server settings admin steam IDs:', steamIds);
          console.log('Steam IDs length:', steamIds.length);
          setServerSettingsAdminSteamIds(steamIds);
        } else {
          console.log('No admins found or error, setting empty array');
          console.log('Response:', res);
          setServerSettingsAdminSteamIds([]);
        }
    } catch (error) {
      console.error('Error refreshing server settings admins:', error);
      setServerSettingsAdminSteamIds([]);
    }
  };

  // Função para atualizar whitelist após adicionar/remover
  const refreshWhitelist = async () => {
    try {
      const res = await WhitelistService.listWhitelistedUsers();
      if (res.success && Array.isArray(res.whitelistedUsers)) {
        setWhitelistedSteamIds(res.whitelistedUsers.map(u => u.steamId));
      } else {
        setWhitelistedSteamIds([]);
      }
    } catch {
      setWhitelistedSteamIds([]);
    }
  };

  // Função para atualizar lista de banidos após adicionar/remover
  const refreshBanList = async () => {
    try {
      const res = await BanService.listBannedUsers();
      if (res.success && Array.isArray(res.bannedUsers)) {
        setBannedSteamIds(res.bannedUsers.map(u => u.steamId));
      } else {
        setBannedSteamIds([]);
      }
    } catch {
      setBannedSteamIds([]);
    }
  };

  // Função para atualizar lista de exclusivos após adicionar/remover
  const refreshExclusiveList = async () => {
    try {
      const res = await ExclusiveService.listExclusiveUsers();
      if (res.success && Array.isArray(res.exclusiveUsers)) {
        setExclusiveSteamIds(res.exclusiveUsers.map(u => u.steamId));
      } else {
        setExclusiveSteamIds([]);
      }
    } catch {
      setExclusiveSteamIds([]);
    }
  };

  // Função para atualizar lista de silenciados após adicionar/remover
  const refreshSilenceList = async () => {
    try {
      const res = await SilenceService.listSilencedUsers();
      if (res.success && Array.isArray(res.silencedUsers)) {
        setSilencedSteamIds(res.silencedUsers.map(u => u.steamId));
      } else {
        setSilencedSteamIds([]);
      }
    } catch {
      setSilencedSteamIds([]);
    }
  };

  // Funções de atualização manual
  const handlePlayersUpdate = async () => {
    try {
      const players = await PlayerService.getPainelPlayers();
      setPlayers(players);
      const online = players.filter(p => p.isOnline).length;
      setPlayerCount(online);
    } catch (err) {
      console.error('Erro ao atualizar jogadores:', err);
    }
  };

  const handleChatUpdate = async () => {
    try {
      const result = await WebhookService.getChatInGameMessages();
      if (result.success && result.data) {
        setChatMessages(result.data);
      }
    } catch (err) {
      console.error('Erro ao atualizar chat:', err);
    }
  };

  const handleVehiclesUpdate = async () => {
    try {
      await VehicleService.processLog();
      const res = await VehicleService.getHistory();
      if (res.success && Array.isArray(res.data)) {
        setVehicles(res.data);
      }
    } catch (err) {
      console.error('Erro ao atualizar veículos:', err);
    }
  };

  const handleFameUpdate = async () => {
    try {
      const response = await FameService.getFamePoints();
      if (response.success && response.data) {
        const sortedPlayers = response.data.sort((a, b) => b.totalFame - a.totalFame);
        const top3 = sortedPlayers.slice(0, 3);
        setTop3FamePlayers(top3);
      }
    } catch (err) {
      console.error('Erro ao atualizar fama:', err);
    }
  };

  const handleBunkersUpdate = async () => {
    // Esta função será chamada pelo BunkerStatusCard
    // O componente já tem sua própria lógica de atualização
  };

  const handleAdminLogUpdate = async () => {
    try {
      const res = await AdminLogService.getAdminLog();
      if (res.success && res.data) {
        let lines: string[] = [];
        if (Array.isArray(res.data)) lines = res.data;
        else if (typeof res.data === 'string') lines = res.data.split('\n').filter(l => l.trim() !== '');
        setAdminLogEvents(AdminLogService.parseLogLines(lines).reverse());
      }
    } catch (err) {
      console.error('Erro ao atualizar admin log:', err);
    }
  };

  if (loading) {
    return (
      <ScumBackground>
        <div className="flex h-screen items-center justify-center">
          <div className="text-center">
            <div className="w-8 h-8 border-2 border-scum-accent border-t-transparent rounded-full animate-spin mx-auto mb-4"></div>
            <p className="text-scum-light military-text">CARREGANDO DASHBOARD...</p>
          </div>
        </div>
      </ScumBackground>
    );
  }

  if (error) {
    return (
      <ScumBackground>
        <div className="flex h-screen items-center justify-center">
          <div className="text-center">
            <p className="text-scum-danger military-text mb-4">{error}</p>
            <button 
              onClick={() => window.location.reload()}
              className="scum-button"
            >
              TENTAR NOVAMENTE
            </button>
          </div>
        </div>
      </ScumBackground>
    );
  }

  return (
    <ScumBackground>
      <FullscreenToggle />
      <div className="flex h-screen overflow-hidden">
        {/* Sidebar Desktop */}
        <div className="hidden md:block">
          <DashboardSidebar 
            activeSection={activeSection}
            onSectionChange={setActiveSection}
            onDonationClick={() => setIsDonationModalOpen(true)}
          />
        </div>

        {/* Menu Mobile */}
        <MobileMenu 
          isOpen={isMobileMenuOpen}
          onToggle={() => setIsMobileMenuOpen(!isMobileMenuOpen)}
        >
          <DashboardSidebar 
            activeSection={activeSection}
            onSectionChange={setActiveSection}
            onDonationClick={() => setIsDonationModalOpen(true)}
            isMobile={true}
            onMobileClose={() => setIsMobileMenuOpen(false)}
          />
        </MobileMenu>

        {/* Main Content */}
        <div className="flex-1 flex flex-col min-h-0 overflow-hidden">
          {/* Header - Oculto em todas as seções exceto dashboard */}
          {activeSection === 'dashboard' && (
            <DashboardHeader 
              serverStatus="online"
              playerCount={playerCount}
              maxPlayers={64}
            />
          )}
          {activeSection === 'dashboard' && vehicles.length > 0 && (
            <div className="desktop-only">
              <VehicleEventBreakingNewsBar event={vehicles[vehicles.length - 1]} />
            </div>
          )}
          {activeSection === 'dashboard' && top3FamePlayers.length > 0 && (
            <div className="desktop-only">
              <FameTop3BreakingNewsBar top3Players={top3FamePlayers} />
            </div>
          )}

          {/* Dashboard Content */}
          <main className={`flex-1 overflow-y-auto min-h-0 overflow-x-hidden ${
            activeSection === 'dashboard' ? 'p-4 sm:p-6' : 'p-4'
          }`}>
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              className="space-y-6"
            >
              {/* Conteúdo baseado na seção ativa */}
              {activeSection === 'dashboard' && (
                <>
                  {/* Controle do Servidor - Nova linha no topo */}
                  <div className="max-w-6xl mx-auto mb-6">
                    <ServerControlCard />
                  </div>
                  
                  {/* Controles de Atualização Manual */}
                  <div className="max-w-6xl mx-auto mb-6">
                    <ManualUpdateControls
                      onPlayersUpdate={handlePlayersUpdate}
                      onChatUpdate={handleChatUpdate}
                      onVehiclesUpdate={handleVehiclesUpdate}
                      onFameUpdate={handleFameUpdate}
                      onBunkersUpdate={handleBunkersUpdate}
                      onAdminLogUpdate={handleAdminLogUpdate}
                    />
                  </div>
                  
                  {/* Cards existentes */}
                  <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 sm:gap-6 max-w-6xl mx-auto mb-8 items-start">
                    <ChatMessagesCard messages={chatMessages} ativo={chatInGameAtivo} onToggle={() => setChatInGameAtivo(v => !v)} hideSteamIds={hideSteamIds} />
                    <BunkerStatusCard hideSteamIds={hideSteamIds} onManualUpdate={handleBunkersUpdate} />
                  </div>
                </>
              )}

              {/* Seção Discord */}
              {activeSection === 'discord' && (
                <div className="h-full">
                  <div className="text-center mb-8">
                    <h1 className="text-2xl sm:text-3xl font-bold text-scum-light mb-4">
                      {t('discord_settings')}
                    </h1>
                    <p className="text-scum-light/80 text-base sm:text-lg">
                      {t('manage_discord_webhooks_notifications')}
                    </p>
                  </div>
                  <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 sm:gap-6 max-w-6xl mx-auto">
                    <DiscordWebhookCard
                      webhookName="WebHook Painel Players"
                      webhookUrl={painelPlayersWebhook}
                      webhookType="painelPlayers"
                      onSave={handleSaveWebhook}
                      onTest={handleTestWebhook}
                    />
                    
                    <DiscordWebhookCard
                      webhookName="WebHook Veiculos"
                      webhookUrl={veiculosWebhook}
                      webhookType="veiculos"
                      onSave={handleSaveWebhook}
                      onTest={handleTestWebhook}
                    />
                    
                    <DiscordWebhookCard
                      webhookName="WebHook Admin Log"
                      webhookUrl={adminLogWebhook}
                      webhookType="adminLog"
                      onSave={handleSaveWebhook}
                      onTest={handleTestWebhook}
                    />
                    
                    <DiscordWebhookCard
                      webhookName="Chat in Game"
                      webhookUrl={chatInGameWebhook}
                      webhookType="chatInGame"
                      onSave={handleSaveWebhook}
                      onTest={handleTestWebhook}
                    />
                    
                    <DiscordWebhookCard
                      webhookName="WebHook Bunkers"
                      webhookUrl={bunkersWebhook}
                      webhookType="bunkers"
                      onSave={handleSaveWebhook}
                      onTest={handleTestWebhook}
                    />
                    
                    <DiscordWebhookCard
                      webhookName="WebHook Fama"
                      webhookUrl={famaWebhook}
                      webhookType="fama"
                      onSave={handleSaveWebhook}
                      onTest={handleTestWebhook}
                    />
                    
                    <DiscordWebhookCard
                      webhookName="WebHook Server Status"
                      webhookUrl={serverStatusWebhook}
                      webhookType="serverStatus"
                      onSave={handleSaveWebhook}
                      onTest={handleTestWebhook}
                    />
                    
                    <DiscordWebhookCard
                      webhookName="🎭 Estatísticas Divertidas"
                      webhookUrl={funnyStatisticWebhook}
                      webhookType="funnyStatistic"
                      onSave={handleSaveWebhook}
                      onTest={handleTestWebhook}
                    />
                  </div>
                </div>
              )}

              {/* Seção Jogadores */}
              {activeSection === 'players' && (
                <div className="h-full">
                  <div className="text-center mb-8">
                    <h1 className="text-3xl font-bold text-scum-light mb-4">
                      {t('online_players_statistics')}
                    </h1>
                    <p className="text-scum-light/80 text-lg">
                      {t('view_all_players_status_playtime_ranking')}
                    </p>
                  </div>
                  {/* Resumo de jogadores */}
                  <div className="flex flex-wrap justify-center gap-6 mb-6">
                    <div className="bg-scum-secondary/30 border border-scum-accent/30 rounded-lg px-6 py-4 text-center">
                      <div className="text-2xl font-bold text-scum-accent">{players.length}</div>
                      <div className="text-xs text-scum-light/80 mt-1">Total</div>
                    </div>
                    <div className="bg-green-900/30 border border-green-500/30 rounded-lg px-6 py-4 text-center">
                      <div className="text-2xl font-bold text-green-400">{players.filter(p => p.isOnline).length}</div>
                      <div className="text-xs text-green-300 mt-1">Online</div>
                    </div>
                    <div className="bg-scum-dark/30 border border-scum-gray/30 rounded-lg px-6 py-4 text-center">
                      <div className="text-2xl font-bold text-scum-muted">{players.filter(p => !p.isOnline).length}</div>
                      <div className="text-xs text-scum-muted mt-1">Offline</div>
                    </div>
                  </div>
                  <PlayersTable 
                    players={players} 
                    hideSteamIds={hideSteamIds} 
                    admins={adminSteamIds} 
                    serverSettingsAdmins={serverSettingsAdminSteamIds}
                    whitelistedUsers={whitelistedSteamIds}
                    bannedUsers={bannedSteamIds}
                    exclusiveUsers={exclusiveSteamIds}
                    silencedUsers={silencedSteamIds}
                    onAdminAdded={refreshAdmins} 
                    onServerSettingsAdminAdded={refreshServerSettingsAdmins}
                    onWhitelistUpdated={refreshWhitelist}
                    onBanListUpdated={refreshBanList}
                    onExclusiveListUpdated={refreshExclusiveList}
                    onSilenceListUpdated={refreshSilenceList}
                  />
                  {/* Debug info */}
                  <div className="text-xs text-scum-muted mt-2">
                    Debug - Server Settings Admins: {JSON.stringify(serverSettingsAdminSteamIds)}
                  </div>
                </div>
              )}

              {/* Seção FAMA */}
              {activeSection === 'fama' && (
                <div className="h-full">
                  <div className="text-center mb-8">
                    <h1 className="text-3xl font-bold text-scum-light mb-4">
                      {t('fame_system')}
                    </h1>
                    <p className="text-scum-light/80 text-lg">
                      {t('manage_player_reputation_fame_system')}
                    </p>
                  </div>
                  <FamePlayersList hideSteamIds={hideSteamIds} />
                </div>
              )}

              {/* Seção Veículos */}
              {activeSection === 'veiculos' && (
                <div className="h-full">
                  <div className="text-center mb-8">
                    <h1 className="text-3xl font-bold text-scum-light mb-4">
                      {t('vehicle_history_events')}
                    </h1>
                    <p className="text-scum-light/80 text-lg">
                      {t('view_all_vehicle_events_processed_system')}
                    </p>
                  </div>
                  <VehiclesTable vehicles={vehicles} />
                </div>
              )}

              {/* Seção Administração */}
              {activeSection === 'admin' && (
                <div className="h-full">
                  <div className="text-center mb-8">
                    <h1 className="text-3xl font-bold text-scum-light mb-4">
                      {t('administration')}
                    </h1>
                    <p className="text-scum-light/80 text-lg">
                      {t('manage_administrative_functions_scum_server')}
                    </p>
                  </div>
                  <div>
                    <h2 className="text-xl font-bold text-scum-accent mb-4">{t('admin_log')}</h2>
                    {loadingAdminLog ? (
                      <div className="text-center text-scum-muted py-8">{t('loading_admin_log')}</div>
                    ) : (
                      <AdminLogTable events={adminLogEvents} hideSteamIds={hideSteamIds} />
                    )}
                  </div>
                </div>
              )}

              {/* Seção Configurações */}
              {activeSection === 'settings' && (
                <div className="h-full">
                  <div className="text-center mb-8">
                    <h1 className="text-3xl font-bold text-scum-light mb-4">
                      {t('system_settings')}
                    </h1>
                    <p className="text-scum-light/80 text-lg">
                      {t('manage_advanced_scum_server_settings')}
                    </p>
                  </div>
                  <div className="max-w-4xl mx-auto">
                    <SettingsCard 
                      hideSteamIds={hideSteamIds}
                      onHideSteamIdsChange={setHideSteamIds}
                    />
                  </div>
                </div>
              )}

              {/* Seção Configurações do Servidor */}
              {activeSection === 'server_config' && (
                <div className="h-full">
                  <div className="text-center mb-8">
                    <h1 className="text-3xl font-bold text-scum-light mb-4">
                      {t('server_configuration')}
                    </h1>
                    <p className="text-scum-light/80 text-lg">
                      {t('manage_server_configuration_settings')}
                    </p>
                  </div>
                  <ServerConfigurationCard />
                </div>
              )}

              {/* Outras seções */}
              {activeSection !== 'dashboard' && activeSection !== 'discord' && activeSection !== 'players' && activeSection !== 'fama' && activeSection !== 'veiculos' && activeSection !== 'admin' && activeSection !== 'settings' && activeSection !== 'server_config' && (
                <div className="h-full flex items-center justify-center">
                  <div className="text-center">
                    <h1 className="text-3xl font-bold text-scum-light mb-4">
                      {activeSection.charAt(0).toUpperCase() + activeSection.slice(1)}
                    </h1>
                    <p className="text-scum-light/80 text-lg">
                      Seção em desenvolvimento
                    </p>
                  </div>
                </div>
              )}
            </motion.div>
          </main>
        </div>
        
        {/* Modal de Doação */}
        <DonationModal 
          isOpen={isDonationModalOpen}
          onClose={() => setIsDonationModalOpen(false)}
        />
      </div>
    </ScumBackground>
  );
};

export default Dashboard; 