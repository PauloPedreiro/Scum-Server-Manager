import { useEffect, useState, useMemo, Fragment, useCallback, useRef } from 'react';
import { useTranslation } from 'react-i18next';
import {
  Users,
  Users2,
  Circle,
  Search,
  Car,
  RefreshCw,
  ArrowDown,
  ArrowUp,
  FileText,
  Loader2,
  Boxes,
  Activity,
  Trophy,
  BarChart3,
  Settings,
  X,
  CheckSquare,
  Square,
} from 'lucide-react';
import vehicleMapping from '@/assets/vehicle-log/mapping.json';
import { authService } from '@/services/auth';

// Carregar todas as imagens de veículos (PNG e WebP)
const vehicleImagesPng = import.meta.glob('/src/assets/vehicle-log/*.png', {
  eager: true,
  query: '?url',
  import: 'default',
});
const vehicleImagesWebp = import.meta.glob('/src/assets/vehicle-log/*.webp', {
  eager: true,
  query: '?url',
  import: 'default',
});
const vehicleImages = { ...vehicleImagesPng, ...vehicleImagesWebp };

// Função helper para obter o caminho da imagem do veículo
const getVehicleImagePath = (vehicleClassDisplay: string): string | null => {
  // Verificar se existe no mapping
  const mappedFileName = (vehicleMapping as Record<string, string>)[vehicleClassDisplay];
  const fileName = mappedFileName || `${vehicleClassDisplay}_ES.png`;
  
  // Procurar a imagem no glob carregado
  // O glob retorna paths absolutos do sistema de arquivos, precisamos procurar pelo nome do arquivo
  for (const [path, url] of Object.entries(vehicleImages)) {
    if (path.includes(fileName)) {
      return url as string;
    }
  }
  
  return null;
};
import { 
  getPlayersOnlineList, 
  getAllPlayers, 
  getPlayersVehicleSummary,
  updatePlayerPermissao,
  getPlayerPermissions,
  activatePermission,
  deactivatePermission,
  getPlayerVehiclesByStatus,
  getAdminLogsRecent,
  getAdminLogsStats,
  markElevatedUser,
  getElevatedUsersList,
  type PlayersOnlineListResponse, 
  type AllPlayersResponse, 
  type AllPlayer,
  type PermissionType,
  type PlayerPermissionsData,
  type PlayerVehiclesData,
  type PlayerVehicleSummaryItem,
  type Vehicle,
  type AdminCommand,
  type AdminLogsRecentResponse,
  type AdminLogsStatsResponse,
  type ElevatedUser
} from '@/services/server';
import { getSquads, getSquadMembers, type Squad, type SquadMember } from '@/services/squads';
import { getChests, isValidChestLocation, type ChestSnapshot } from '@/services/chests';
import { getSurvivalPlayer, type SurvivalPlayerDetailResponse } from '@/services/survival';
import { getRankingsList, type PlayerRanking, type RankingsListResponse } from '@/services/rankings';
import { getBankAccountsCurrent, type BankAccountCurrentItem } from '@/services/bank';
import { 
  getPlayersChartData, 
  getPlayersHourlyAverage,
  getPlayersDailyAverage,
  type PlayersChartDataResponse,
  type AbsolutePeak
} from '@/services/reports';
import { PlayersChart } from '@/components/reports/PlayersChart';
import { StatCard } from '@/components/reports/StatCard';
import { AbsolutePeakCard } from '@/components/reports/AbsolutePeakCard';
import { getChestThumbnail } from '@/utils/chestAssets';
import Swal from 'sweetalert2';

interface PlayerListItem extends AllPlayer {
  isOnline: boolean;
  permissions?: Map<string, boolean | number>; // Map<permission_type, is_active>
}

// Lista de tipos de permissão a serem exibidos na tabela
// 'exclusive' está temporariamente oculto - pode ser reativado adicionando de volta ao array
const PERMISSION_TYPES: PermissionType[] = ['admin', 'banned', 'server_admin', 'silenced', 'whitelisted'];
// Para reativar 'exclusive': ['admin', 'banned', 'exclusive', 'server_admin', 'silenced', 'whitelisted']

const SQUAD_MEMBERS_PAGE_SIZE = 25;
const SQUAD_MEMBERS_INITIAL_RENDER = 8;
const SQUAD_MEMBERS_RENDER_BATCH = 25;

interface SquadMembersState {
  members: SquadMember[];
  total: number;
  limit: number;
  offset: number;
  loading: boolean;
  error: string | null;
  hasMore: boolean;
}

export default function Players() {
  const { t, i18n } = useTranslation();
  const [onlinePlayersData, setOnlinePlayersData] = useState<PlayersOnlineListResponse | null>(null);
  const [allPlayersData, setAllPlayersData] = useState<AllPlayersResponse | null>(null);
  const [permissionsMap, setPermissionsMap] = useState<Map<string, PlayerPermissionsData>>(new Map());
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [updatingIds, setUpdatingIds] = useState<Set<string>>(new Set());
  const [updatingPermissions, setUpdatingPermissions] = useState<Set<string>>(new Set());
  const [expanded, setExpanded] = useState<Set<string>>(new Set());
  const [searchTerm, setSearchTerm] = useState<string>('');
  const [filterPermissions, setFilterPermissions] = useState<Set<string>>(new Set());
  const [playersPage, setPlayersPage] = useState(1);
  const [playersPageSize, setPlayersPageSize] = useState(10);
  const [playersTotal, setPlayersTotal] = useState(0);

  const survivalDateFormatter = useMemo(() => {
    return new Intl.DateTimeFormat(i18n.language, {
      dateStyle: 'short',
      timeStyle: 'short',
    });
  }, [i18n.language]);

  const metricFormatter0 = useMemo(() => {
    return new Intl.NumberFormat(i18n.language, {
      maximumFractionDigits: 0,
    });
  }, [i18n.language]);

  const metricFormatter2 = useMemo(() => {
    return new Intl.NumberFormat(i18n.language, {
      maximumFractionDigits: 2,
    });
  }, [i18n.language]);
  
  // Estado para abas (qual aba está ativa para cada player)
  const [activeTab, setActiveTab] = useState<Map<string, 'permissions' | 'vehicles' | 'chests' | 'survival'>>(new Map());
  
  // Estado para veículos de cada player
  const [vehiclesData, setVehiclesData] = useState<Map<string, PlayerVehiclesData>>(new Map());
  const [vehiclesLoading, setVehiclesLoading] = useState<Set<string>>(new Set());
  const [vehiclesError, setVehiclesError] = useState<Map<string, string>>(new Map());
  
  // Estado para filtro de veículos por status (para cada player)
  const [vehicleStatusFilter, setVehicleStatusFilter] = useState<Map<string, string | null>>(new Map());

  interface PlayerChestData {
    chests: ChestSnapshot[];
    totalCount: number;
    limit: number;
  }

  const [chestsData, setChestsData] = useState<Map<string, PlayerChestData>>(new Map());
  const [chestsLoading, setChestsLoading] = useState<Set<string>>(new Set());
  const [chestsError, setChestsError] = useState<Map<string, string>>(new Map());

  // Estado para Elevated Users
  const [elevatedUsers, setElevatedUsers] = useState<Set<string>>(new Set()); // Set<steam_id>
  const [updatingElevatedUsers, setUpdatingElevatedUsers] = useState<Set<string>>(new Set());

interface PlayerSurvivalData {
  metrics: Record<string, number>;
  derived: {
    kdr: number;
    accuracy_percent: number | null;
  };
  snapshotAt: string | null;
  steamId?: string | null;
  playerName?: string | null;
}

const [survivalData, setSurvivalData] = useState<Map<string, PlayerSurvivalData>>(new Map());
const [survivalLoading, setSurvivalLoading] = useState<Set<string>>(new Set());
const [survivalError, setSurvivalError] = useState<Map<string, string>>(new Map());

  const formatMetricValue = useCallback(
    (value: number | null | undefined): string => {
      if (value === null || value === undefined || Number.isNaN(value)) {
        return '—';
      }

      const absValue = Math.abs(value);
      return (absValue >= 100 ? metricFormatter0 : metricFormatter2).format(value);
    },
    [metricFormatter0, metricFormatter2]
  );

  const formatSurvivalDate = useCallback(
    (value: string | null | undefined): string => {
      if (!value) {
        return '—';
      }

      try {
        const date = new Date(value);
        return survivalDateFormatter.format(date);
      } catch {
        return value;
      }
    },
    [survivalDateFormatter]
  );
  const formatPlayTime = useCallback((seconds: number | null | undefined): string => {
    if (!seconds || Number.isNaN(seconds) || seconds <= 0) {
      return '—';
    }

    const totalMinutes = Math.floor(seconds / 60);
    const hours = Math.floor(totalMinutes / 60);
    const minutes = totalMinutes % 60;

    if (hours <= 0) {
      return `${minutes} min`;
    }

    return `${hours}h ${minutes.toString().padStart(2, '0')}m`;
  }, []);
  
  // Estado para contagem de veículos ativos por player (para a tabela principal)
  const [activeVehiclesCount, setActiveVehiclesCount] = useState<Map<string, number>>(new Map());
  
  // Estado para ordenação por veículos
  const [sortByVehicles, setSortByVehicles] = useState<boolean>(false);

  // Estado para tab principal (Players, Squads, Admin Log, Ranking ou Análises)
  const [mainTab, setMainTab] = useState<'players' | 'squads' | 'admin-logs' | 'ranking' | 'analyses' | 'bank'>('players');

  const isAdmin = authService.isAdmin();

  // Estado para Admin Logs
  const [adminLogs, setAdminLogs] = useState<AdminCommand[]>([]);
  const [adminLogsLoading, setAdminLogsLoading] = useState(false);
  const [adminLogsError, setAdminLogsError] = useState<string | null>(null);
  const [adminLogsTotal, setAdminLogsTotal] = useState<number | null>(null);
  const [adminLogsLimit, setAdminLogsLimit] = useState(10);
  const [adminLogsCategoryFilter, setAdminLogsCategoryFilter] = useState<string>('all');
  const [adminLogsSearch, setAdminLogsSearch] = useState('');
  const [adminLogsStats, setAdminLogsStats] = useState<AdminLogsStatsResponse['data'] | null>(null);
  const [adminLogsStatsLoading, setAdminLogsStatsLoading] = useState(false);

  // Estado para Squads
  const [squads, setSquads] = useState<Squad[]>([]);
  const [squadsTotal, setSquadsTotal] = useState<number>(0);
  const [squadsLoading, setSquadsLoading] = useState(false);
  const [squadsError, setSquadsError] = useState<string | null>(null);
  const [squadsSnapshotAt, setSquadsSnapshotAt] = useState<string | null>(null);
  const [squadsLastFetch, setSquadsLastFetch] = useState<number | null>(null);
  const [squadsPage, setSquadsPage] = useState(1);
  const [squadsPageSize, setSquadsPageSize] = useState(25);
  const [expandedSquads, setExpandedSquads] = useState<Set<number>>(new Set());
  const [squadMembersState, setSquadMembersState] = useState<Map<number, SquadMembersState>>(new Map());
  const [squadMembersRenderLimit, setSquadMembersRenderLimit] = useState<Map<number, number>>(new Map());
  const squadMembersRenderTimersRef = useRef<Map<number, number>>(new Map());
  const squadMembersRenderRafRef = useRef<Map<number, number>>(new Map());

  const squadsMaxPage = useMemo(() => {
    const total = squads.length;
    return total <= 0 ? 1 : Math.max(1, Math.ceil(total / squadsPageSize));
  }, [squads.length, squadsPageSize]);

  const squadsPageClamped = useMemo(() => {
    return Math.min(Math.max(1, squadsPage), squadsMaxPage);
  }, [squadsMaxPage, squadsPage]);

  const paginatedSquads = useMemo(() => {
    const startIndex = (squadsPageClamped - 1) * squadsPageSize;
    return squads.slice(startIndex, startIndex + squadsPageSize);
  }, [squads, squadsPageClamped, squadsPageSize]);

  const squadsRangeStart = useMemo(() => {
    return squads.length === 0 ? 0 : (squadsPageClamped - 1) * squadsPageSize + 1;
  }, [squads.length, squadsPageClamped, squadsPageSize]);

  const squadsRangeEnd = useMemo(() => {
    return squads.length === 0 ? 0 : Math.min(squadsPageClamped * squadsPageSize, squads.length);
  }, [squads.length, squadsPageClamped, squadsPageSize]);

  useEffect(() => {
    if (squadsPage !== squadsPageClamped) {
      setSquadsPage(squadsPageClamped);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [squadsPageClamped]);

  useEffect(() => {
    // Ao mudar pagina/tamanho, colapsar squads expandidos para evitar inconsistência visual
    setExpandedSquads(new Set());
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [squadsPageClamped, squadsPageSize]);

  // Estado para Rankings
  const [rankingsData, setRankingsData] = useState<PlayerRanking[]>([]);
  const [rankingsLoading, setRankingsLoading] = useState(false);
  const [rankingsError, setRankingsError] = useState<string | null>(null);
  const [rankingsPage, setRankingsPage] = useState(1);
  const [rankingsPageSize, setRankingsPageSize] = useState(50);
  const [rankingsTotal, setRankingsTotal] = useState(0);
  const [rankingsSortBy, setRankingsSortBy] = useState<string>('kills');
  const [rankingsSortOrder, setRankingsSortOrder] = useState<'asc' | 'desc'>('desc');
  const [rankingsSearch, setRankingsSearch] = useState<string>('');

  // Estado para tab Análises
  const [chartDays, setChartDays] = useState<number>(7);
  const [chartGranularity, setChartGranularity] = useState<'hour' | 'day'>('hour');
  const [chartData, setChartData] = useState<PlayersChartDataResponse | null>(null);
  const [chartLoading, setChartLoading] = useState(false);
  const [chartError, setChartError] = useState<string | null>(null);
  
  // Estado para Pico Absoluto
  const [absolutePeak, setAbsolutePeak] = useState<AbsolutePeak | null>(null);
  const [absolutePeakLoading, setAbsolutePeakLoading] = useState(false);

  // ==================== Bank (Admin) ====================
  const [bankItems, setBankItems] = useState<BankAccountCurrentItem[]>([]);
  const [bankLoading, setBankLoading] = useState(false);
  const [bankError, setBankError] = useState<string | null>(null);
  const [bankLimit] = useState(50);
  const [bankOffset, setBankOffset] = useState(0);
  const [bankTotal, setBankTotal] = useState(0);
  const [bankHasMore, setBankHasMore] = useState(false);
  const [bankSearch, setBankSearch] = useState('');
  const bankFetchInFlightRef = useRef(false);
  const bankRequestSeqRef = useRef(0);
  const fetchBankAccountsRef = useRef<(() => Promise<void>) | null>(null);
  const [bankSortKey, setBankSortKey] = useState<'money' | 'gold' | null>(null);
  const [bankSortDir, setBankSortDir] = useState<'asc' | 'desc'>('desc');

  const sortedBankItems = useMemo(() => {
    if (!bankSortKey) return bankItems;

    const getValue = (it: BankAccountCurrentItem): number => {
      if (bankSortKey === 'gold') return Number(it.balances?.gold ?? 0);
      return Number(it.balances?.money_total ?? 0);
    };

    const next = [...bankItems].sort((a, b) => {
      const va = getValue(a);
      const vb = getValue(b);
      return bankSortDir === 'asc' ? va - vb : vb - va;
    });

    return next;
  }, [bankItems, bankSortDir, bankSortKey]);

  const handleBankSort = useCallback((key: 'money' | 'gold') => {
    setBankSortKey((prevKey) => {
      if (prevKey !== key) {
        setBankSortDir('desc');
        return key;
      }
      setBankSortDir((prevDir) => (prevDir === 'desc' ? 'asc' : 'desc'));
      return prevKey;
    });
  }, []);

  // Configuração de colunas disponíveis
  const RANKING_COLUMNS = {
    fixed: [
      { key: 'rank', label: 'rank', sortable: false },
      { key: 'player', label: 'player', sortable: false },
    ],
    main: [
      { key: 'kills', label: 'kills', sortable: true },
      { key: 'deaths', label: 'deaths', sortable: true },
      { key: 'kdr', label: 'kdr', sortable: true },
      { key: 'total_fame', label: 'fame', sortable: true },
      { key: 'minutes_survived', label: 'minutesSurvived', sortable: true },
      { key: 'longest_shot', label: 'topSniper', sortable: true },
    ],
    combat: [
      { key: 'headshots', label: 'headshots', sortable: true },
      { key: 'suicides', label: 'suicides', sortable: true },
    ],
    survival: [
      { key: 'vehicles_destroyed', label: 'vehiclesDestroyed', sortable: true },
      { key: 'animals_killed', label: 'animalsKilled', sortable: true },
      { key: 'players_knocked_out', label: 'playersKnockedOut', sortable: true },
      { key: 'overdoses', label: 'overdoses', sortable: true },
      { key: 'highest_weight_carried', label: 'highestWeight', sortable: true },
      { key: 'highest_defecation', label: 'highestDefecation', sortable: true },
    ],
    lockpicking: [
      { key: 'lockpick_basic_rate', label: 'lockpickBasic', sortable: true },
      { key: 'lockpick_medium_rate', label: 'lockpickMedium', sortable: true },
      { key: 'lockpick_advanced_rate', label: 'lockpickAdvanced', sortable: true },
      { key: 'lockpick_veryeasy_rate', label: 'lockpickVeryEasy', sortable: true },
      { key: 'lockpick_diallock_rate', label: 'lockpickDiallock', sortable: true },
    ],
  };

  // Estado para colunas visíveis (com persistência no localStorage)
  const getDefaultVisibleColumns = (): Set<string> => {
    if (typeof window === 'undefined') {
      return new Set(['rank', 'player', 'kills', 'deaths', 'kdr', 'total_fame', 'minutes_survived', 'longest_shot']);
    }
    const saved = localStorage.getItem('rankings_visible_columns');
    if (saved) {
      try {
        return new Set(JSON.parse(saved));
      } catch {
        return new Set(['rank', 'player', 'kills', 'deaths', 'kdr', 'total_fame', 'minutes_survived', 'longest_shot']);
      }
    }
    return new Set(['rank', 'player', 'kills', 'deaths', 'kdr', 'total_fame', 'minutes_survived', 'longest_shot']);
  };

  const [visibleColumns, setVisibleColumns] = useState<Set<string>>(getDefaultVisibleColumns);
  const [showColumnSelector, setShowColumnSelector] = useState(false);

  // Salvar colunas visíveis no localStorage
  const updateVisibleColumns = useCallback((newColumns: Set<string>) => {
    setVisibleColumns(newColumns);
    if (typeof window !== 'undefined') {
      localStorage.setItem('rankings_visible_columns', JSON.stringify(Array.from(newColumns)));
    }
  }, []);

  // Função para buscar Rankings
  const fetchRankings = useCallback(async () => {
    setRankingsLoading(true);
    setRankingsError(null);
    try {
      const offset = (rankingsPage - 1) * rankingsPageSize;
      const response = await getRankingsList({
        limit: rankingsPageSize,
        offset,
        sort_by: rankingsSortBy,
        sort_order: rankingsSortOrder,
        search: rankingsSearch.trim() || undefined,
      });
      
      if (response.success && response.data) {
        setRankingsData(response.data.players);
        setRankingsTotal(response.data.pagination.total);
      } else {
        setRankingsError(response.error || 'Erro ao carregar rankings');
      }
    } catch (err: any) {
      const errorMsg = err.response?.data?.error || err.message || 'Erro ao carregar rankings';
      setRankingsError(errorMsg);
    } finally {
      setRankingsLoading(false);
    }
  }, [rankingsPage, rankingsPageSize, rankingsSortBy, rankingsSortOrder, rankingsSearch]);

  const fetchBankAccounts = useCallback(async () => {
    if (!isAdmin) return;
    if (bankFetchInFlightRef.current) return;

    bankFetchInFlightRef.current = true;
    const seq = ++bankRequestSeqRef.current;

    setBankLoading(true);
    setBankError(null);

    try {
      const response = await getBankAccountsCurrent({
        limit: bankLimit,
        offset: bankOffset,
        q: bankSearch.trim() || undefined,
      });

      if (seq !== bankRequestSeqRef.current) {
        return;
      }

      if (response.success && response.data) {
        setBankItems(response.data.items);
        setBankTotal(response.data.total);
        setBankHasMore(response.data.has_more);
      } else {
        setBankItems([]);
        setBankTotal(0);
        setBankHasMore(false);
        setBankError(response.error || t('players.bank.errors.loadFailed'));
      }
    } catch (err: any) {
      if (seq !== bankRequestSeqRef.current) {
        return;
      }
      const msg = err?.response?.data?.error || err?.message || t('players.bank.errors.loadFailed');
      setBankError(msg);
      setBankItems([]);
      setBankTotal(0);
      setBankHasMore(false);
    } finally {
      if (seq === bankRequestSeqRef.current) {
        setBankLoading(false);
      }
      bankFetchInFlightRef.current = false;
    }
  }, [isAdmin, bankLimit, bankOffset, bankSearch, t]);

  useEffect(() => {
    fetchBankAccountsRef.current = fetchBankAccounts;
  }, [fetchBankAccounts]);

  // Função para buscar dados do gráfico
  const fetchChartData = useCallback(async () => {
    setChartLoading(true);
    setChartError(null);
    try {
      if (import.meta.env.DEV) {
        console.log('[Analyses] Buscando dados do gráfico...', { chartDays, chartGranularity });
      }
      const response = await getPlayersChartData(chartDays, chartGranularity);
      if (import.meta.env.DEV) {
        console.log('[Analyses] Resposta recebida:', response);
      }
      if (response.success && response.data) {
        setChartData(response);
        if (import.meta.env.DEV) {
          console.log('[Analyses] Dados salvos no estado:', response.data);
        }
      } else {
        const errorMsg = response.error || 'Erro ao carregar dados do gráfico';
        setChartError(errorMsg);
        if (import.meta.env.DEV) {
          console.error('[Analyses] Erro na resposta:', errorMsg);
        }
      }
    } catch (err: any) {
      const errorMsg = err.response?.data?.error || err.message || 'Erro ao carregar dados do gráfico';
      setChartError(errorMsg);
      if (import.meta.env.DEV) {
        console.error('[Analyses] Erro na requisição:', err);
      }
    } finally {
      setChartLoading(false);
    }
  }, [chartDays, chartGranularity]);

  // Função para buscar Pico Absoluto
  const fetchAbsolutePeak = useCallback(async () => {
    setAbsolutePeakLoading(true);
    try {
      if (import.meta.env.DEV) {
        console.log('[Analyses] Buscando pico absoluto...', { chartDays, chartGranularity });
      }
      
      let response;
      if (chartGranularity === 'hour') {
        response = await getPlayersHourlyAverage(chartDays);
      } else {
        response = await getPlayersDailyAverage(chartDays);
      }
      
      if (response.success && response.data?.absolute_peak) {
        setAbsolutePeak(response.data.absolute_peak);
        if (import.meta.env.DEV) {
          console.log('[Analyses] Pico absoluto recebido:', response.data.absolute_peak);
        }
      } else {
        setAbsolutePeak(null);
        if (import.meta.env.DEV) {
          console.log('[Analyses] Nenhum pico absoluto disponível');
        }
      }
    } catch (err: any) {
      console.error('[Analyses] Erro ao buscar pico absoluto:', err);
      setAbsolutePeak(null);
    } finally {
      setAbsolutePeakLoading(false);
    }
  }, [chartDays, chartGranularity]);

  // Função para buscar Admin Logs
  const fetchAdminLogs = useCallback(
    async (override?: { category?: string; q?: string; limit?: number }) => {
      setAdminLogsLoading(true);
      setAdminLogsError(null);
      try {
        const effectiveCategory = override?.category ?? adminLogsCategoryFilter;
        const effectiveQ = override?.q ?? adminLogsSearch;
        const effectiveLimit = override?.limit ?? adminLogsLimit;

        const response = await getAdminLogsRecent({
          limit: effectiveLimit,
          include_total: true,
          category: effectiveCategory !== 'all' ? effectiveCategory : undefined,
          q: effectiveQ.trim() ? effectiveQ.trim() : undefined,
        });

        if (response.success && response.data) {
          setAdminLogs(response.data.commands);
          setAdminLogsTotal(response.data.total ?? null);
        } else {
          setAdminLogsError(response.error || t('adminLogs.errors.loadFailed'));
        }
      } catch (err: any) {
        const errorMsg = err.response?.data?.error || err.message || t('adminLogs.errors.loadFailed');
        setAdminLogsError(errorMsg);
      } finally {
        setAdminLogsLoading(false);
      }
    },
    [adminLogsCategoryFilter, adminLogsLimit, adminLogsSearch, t]
  );

  const fetchAdminLogsStats = useCallback(async () => {
    setAdminLogsStatsLoading(true);
    try {
      const response = await getAdminLogsStats();
      if (response.success && response.data) {
        setAdminLogsStats(response.data);
      }
    } catch {
      // Silencioso (stats é apenas auxiliar)
    } finally {
      setAdminLogsStatsLoading(false);
    }
  }, []);

  const fetchSquads = useCallback(
    async (forceReload: boolean = false) => {
      if (squadsLoading) {
        return;
      }

      const now = Date.now();
      if (!forceReload && squadsLastFetch && now - squadsLastFetch < 60000) {
        return;
      }

      setSquadsLoading(true);
      setSquadsError(null);

      try {
        const response = await getSquads();
        if (response.success && response.data) {
          const { squads: squadList, total } = response.data;
          setSquads(squadList);
          setSquadsTotal(total);
          setSquadsSnapshotAt(squadList.length > 0 ? squadList[0].snapshot_at : null);
        } else {
          setSquads([]);
          setSquadsTotal(0);
          setSquadsSnapshotAt(null);
          setSquadsError(response.error || t('players.squads.errors.loadFailed'));
        }
      } catch (err: any) {
        const errorMessage =
          err?.response?.data?.error || err?.message || t('players.squads.errors.loadFailed');
        setSquadsError(errorMessage);
        setSquads([]);
        setSquadsTotal(0);
        setSquadsSnapshotAt(null);
      } finally {
        setSquadsLoading(false);
        setSquadsLastFetch(Date.now());
      }
    },
    [squadsLoading, squadsLastFetch, t]
  );

  const loadSquadMembers = useCallback(
    async (squadId: number, append: boolean = false) => {
      const existingEntry = squadMembersState.get(squadId);
      const offsetToUse = append && existingEntry ? existingEntry.offset : 0;

      const existingTimer = squadMembersRenderTimersRef.current.get(squadId);
      if (existingTimer) {
        clearTimeout(existingTimer);
        squadMembersRenderTimersRef.current.delete(squadId);
      }

      const existingRaf = squadMembersRenderRafRef.current.get(squadId);
      if (existingRaf) {
        cancelAnimationFrame(existingRaf);
        squadMembersRenderRafRef.current.delete(squadId);
      }

      setSquadMembersState(prev => {
        const next = new Map(prev);
        const prevEntry = next.get(squadId);
        next.set(squadId, {
          members: prevEntry?.members ?? [],
          total: prevEntry?.total ?? 0,
          limit: prevEntry?.limit ?? SQUAD_MEMBERS_PAGE_SIZE,
          offset: prevEntry?.offset ?? 0,
          hasMore: prevEntry?.hasMore ?? false,
          loading: true,
          error: null,
        });
        return next;
      });

      try {
        const response = await getSquadMembers(squadId, SQUAD_MEMBERS_PAGE_SIZE, offsetToUse);
        if (response.success && response.data) {
          const { members, total, limit, offset, count } = response.data;
          setSquadMembersState(prev => {
            const next = new Map(prev);
            const prevEntry = next.get(squadId);
            const combinedMembers =
              append && prevEntry ? [...prevEntry.members, ...members] : members;

            next.set(squadId, {
              members: combinedMembers,
              total,
              limit,
              offset: offset + count,
              hasMore: offset + count < total,
              loading: false,
              error: null,
            });
            return next;
          });

          setSquadMembersRenderLimit(prev => {
            const next = new Map(prev);
            const currentTotal = (append && existingEntry ? existingEntry.members.length : 0) + members.length;
            next.set(squadId, Math.min(SQUAD_MEMBERS_INITIAL_RENDER, currentTotal));
            return next;
          });

          const totalMembers = (append && existingEntry ? existingEntry.members.length : 0) + members.length;
          if (totalMembers > SQUAD_MEMBERS_INITIAL_RENDER) {
            let rendered = SQUAD_MEMBERS_INITIAL_RENDER;
            const step = () => {
              rendered = Math.min(rendered + SQUAD_MEMBERS_RENDER_BATCH, totalMembers);
              setSquadMembersRenderLimit(prev => {
                const next = new Map(prev);
                next.set(squadId, rendered);
                return next;
              });

              if (rendered < totalMembers) {
                const rafId = requestAnimationFrame(step);
                squadMembersRenderRafRef.current.set(squadId, rafId);
              } else {
                squadMembersRenderRafRef.current.delete(squadId);
              }
            };

            const rafId = requestAnimationFrame(step);
            squadMembersRenderRafRef.current.set(squadId, rafId);
          }
        } else {
          const errorMessage = response.error || t('players.squads.members.errorLoad');
          setSquadMembersState(prev => {
            const next = new Map(prev);
            const prevEntry = next.get(squadId);
            next.set(squadId, {
              members: prevEntry?.members ?? [],
              total: prevEntry?.total ?? 0,
              limit: prevEntry?.limit ?? SQUAD_MEMBERS_PAGE_SIZE,
              offset: prevEntry?.offset ?? 0,
              hasMore: false,
              loading: false,
              error: errorMessage,
            });
            return next;
          });

          setSquadMembersRenderLimit(prev => {
            const next = new Map(prev);
            next.delete(squadId);
            return next;
          });
        }
      } catch (err: any) {
        const errorMessage =
          err?.response?.status === 404
            ? t('players.squads.members.notFound')
            : err?.response?.data?.error || err?.message || t('players.squads.members.errorLoad');
        setSquadMembersState(prev => {
          const next = new Map(prev);
          const prevEntry = next.get(squadId);
          next.set(squadId, {
            members: prevEntry?.members ?? [],
            total: prevEntry?.total ?? 0,
            limit: prevEntry?.limit ?? SQUAD_MEMBERS_PAGE_SIZE,
            offset: prevEntry?.offset ?? 0,
            hasMore: false,
            loading: false,
            error: errorMessage,
          });
          return next;
        });

        setSquadMembersRenderLimit(prev => {
          const next = new Map(prev);
          next.delete(squadId);
          return next;
        });
      }
    },
    [squadMembersState, t]
  );

  const handleSquadToggle = useCallback(
    (squad: Squad) => {
      const isCurrentlyExpanded = expandedSquads.has(squad.squad_id);

      if (isCurrentlyExpanded) {
        const existingTimer = squadMembersRenderTimersRef.current.get(squad.squad_id);
        if (existingTimer) {
          clearTimeout(existingTimer);
          squadMembersRenderTimersRef.current.delete(squad.squad_id);
        }

        const existingRaf = squadMembersRenderRafRef.current.get(squad.squad_id);
        if (existingRaf) {
          cancelAnimationFrame(existingRaf);
          squadMembersRenderRafRef.current.delete(squad.squad_id);
        }
        setSquadMembersRenderLimit(prev => {
          const next = new Map(prev);
          next.delete(squad.squad_id);
          return next;
        });
      }

      setExpandedSquads(prev => {
        const next = new Set(prev);
        if (isCurrentlyExpanded) {
          next.delete(squad.squad_id);
        } else {
          next.add(squad.squad_id);
        }
        return next;
      });

      if (!isCurrentlyExpanded && !squadMembersState.has(squad.squad_id)) {
        loadSquadMembers(squad.squad_id);
      } else if (!isCurrentlyExpanded && squadMembersState.has(squad.squad_id)) {
        setSquadMembersRenderLimit(prev => {
          const next = new Map(prev);
          next.set(squad.squad_id, SQUAD_MEMBERS_INITIAL_RENDER);
          return next;
        });

        const existingRaf = squadMembersRenderRafRef.current.get(squad.squad_id);
        if (existingRaf) {
          cancelAnimationFrame(existingRaf);
          squadMembersRenderRafRef.current.delete(squad.squad_id);
        }

        const entry = squadMembersState.get(squad.squad_id);
        const totalMembers = entry?.members.length ?? 0;
        if (totalMembers > SQUAD_MEMBERS_INITIAL_RENDER) {
          let rendered = SQUAD_MEMBERS_INITIAL_RENDER;
          const step = () => {
            rendered = Math.min(rendered + SQUAD_MEMBERS_RENDER_BATCH, totalMembers);
            setSquadMembersRenderLimit(prev => {
              const next = new Map(prev);
              next.set(squad.squad_id, rendered);
              return next;
            });

            if (rendered < totalMembers) {
              const rafId = requestAnimationFrame(step);
              squadMembersRenderRafRef.current.set(squad.squad_id, rafId);
            } else {
              squadMembersRenderRafRef.current.delete(squad.squad_id);
            }
          };

          const rafId = requestAnimationFrame(step);
          squadMembersRenderRafRef.current.set(squad.squad_id, rafId);
        }
      }
    },
    [expandedSquads, loadSquadMembers, squadMembersState, squadMembersRenderLimit]
  );

  const handleLoadMoreSquadMembers = useCallback(
    (squadId: number) => {
      const entry = squadMembersState.get(squadId);
      if (!entry || entry.loading || !entry.hasMore) {
        return;
      }
      loadSquadMembers(squadId, true);
    },
    [loadSquadMembers, squadMembersState]
  );

  useEffect(() => {
    if (mainTab === 'squads' && squads.length === 0 && !squadsLoading && !squadsError) {
      // Evitar loop infinito: só buscar se não houve tentativa recente (últimos 5 segundos)
      const now = Date.now();
      if (!squadsLastFetch || now - squadsLastFetch > 5000) {
        fetchSquads(true);
      }
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [mainTab, squads.length, squadsLoading, squadsLastFetch, squadsError]);

  // Buscar rankings quando a tab estiver ativa
  useEffect(() => {
    if (mainTab === 'ranking') {
      fetchRankings();
      // Atualizar a cada 60 segundos quando a tab estiver ativa
      const interval = setInterval(fetchRankings, 60000);
      return () => clearInterval(interval);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [mainTab, rankingsPage, rankingsPageSize, rankingsSortBy, rankingsSortOrder, rankingsSearch, fetchRankings]);

  // Buscar Bank quando a tab estiver ativa
  useEffect(() => {
    if (mainTab !== 'bank') return;
    fetchBankAccountsRef.current?.();
  }, [mainTab, bankOffset, bankLimit, isAdmin]);

  // Debounce para busca no Bank
  useEffect(() => {
    if (mainTab !== 'bank') return;
    const handle = setTimeout(() => {
      fetchBankAccountsRef.current?.();
    }, 400);
    return () => clearTimeout(handle);
  }, [bankSearch, mainTab]);

  // Buscar dados do gráfico quando tab Análises estiver ativa ou quando filtros mudarem
  useEffect(() => {
    if (mainTab === 'analyses') {
      fetchChartData();
      fetchAbsolutePeak();
    }
  }, [mainTab, chartDays, chartGranularity, fetchChartData, fetchAbsolutePeak]);

  // Formatar timestamp
  const formatDateTime = (timestamp: string): string => {
    try {
      const date = new Date(timestamp);
      return date.toLocaleString('pt-BR', {
        day: '2-digit',
        month: '2-digit',
        year: 'numeric',
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit'
      });
    } catch {
      return timestamp;
    }
  };

  const adminLogsCategoryCounts = useMemo(() => {
    const base: Record<string, number> = {};
    const categories = adminLogsStats?.categories;
    if (!categories) return base;
    for (const [key, info] of Object.entries(categories)) {
      base[key] = info?.count ?? 0;
    }
    return base;
  }, [adminLogsStats]);

  // Buscar logs quando tab ativa e quando filtros mudarem (server-side)
  useEffect(() => {
    if (mainTab !== 'admin-logs') return;

    fetchAdminLogs();
    fetchAdminLogsStats();

    const interval = setInterval(() => {
      fetchAdminLogs();
      fetchAdminLogsStats();
    }, 60000);

    return () => clearInterval(interval);
  }, [mainTab, fetchAdminLogs, fetchAdminLogsStats]);

  // Debounce para busca
  useEffect(() => {
    if (mainTab !== 'admin-logs') return;
    const handle = setTimeout(() => {
      fetchAdminLogs({ q: adminLogsSearch, category: adminLogsCategoryFilter, limit: adminLogsLimit });
    }, 350);
    return () => clearTimeout(handle);
  }, [adminLogsSearch, adminLogsCategoryFilter, adminLogsLimit, mainTab, fetchAdminLogs]);

  // Função para buscar dados dos players (reutilizável)
  const fetchPlayers = async (
    isInitialLoad: boolean = false,
    page: number = playersPage,
    pageSize: number = playersPageSize,
    sortVehiclesOverride: boolean = sortByVehicles
  ) => {
    try {
      if (isInitialLoad) {
        setLoading(true);
      } else {
        setRefreshing(true);
      }
      
      const offset = (page - 1) * pageSize;
      const searchTermTrimmed = searchTerm.trim();
      const searchActive = searchTermTrimmed.length > 0;
      const DEFAULT_SEARCH_LIMIT = 500;
      const totalKnown = playersTotal > 0 ? playersTotal : DEFAULT_SEARCH_LIMIT;
      const limitForFetch = searchActive ? Math.min(DEFAULT_SEARCH_LIMIT, totalKnown) : pageSize;
      const offsetForFetch = searchActive ? 0 : offset;
      const sortOptions = sortVehiclesOverride
        ? {
            sortBy: 'vehicles_total',
            sortOrder: 'desc' as const,
          }
        : undefined;

      const [onlineData, allData, vehiclesSummary] = await Promise.all([
        getPlayersOnlineList(),
        getAllPlayers(limitForFetch, offsetForFetch, sortOptions),
        getPlayersVehicleSummary(limitForFetch, offsetForFetch, undefined, sortOptions),
      ]);
      setOnlinePlayersData(onlineData);

      let normalizedAllData = allData;
      if (
        sortVehiclesOverride &&
        allData?.data?.players &&
        vehiclesSummary?.data?.summaries &&
        vehiclesSummary.data.summaries.length > 0
      ) {
        const playersBySteam = new Map(allData.data.players.map(player => [player.steam_id, player]));
        const orderedPlayers: AllPlayer[] = [];

        vehiclesSummary.data.summaries.forEach(summary => {
          const player = playersBySteam.get(summary.steam_id);
          if (player) {
            orderedPlayers.push(player);
            playersBySteam.delete(summary.steam_id);
          }
        });

        // Append any players not covered in the summary (fallback)
        if (playersBySteam.size > 0) {
          orderedPlayers.push(...playersBySteam.values());
        }

        normalizedAllData = {
          ...allData,
          data: allData.data
            ? {
                ...allData.data,
                players: orderedPlayers,
              }
            : allData.data,
        };
      }

      setAllPlayersData(normalizedAllData);

      const totalFromApi =
        normalizedAllData?.data?.total ??
        normalizedAllData?.data?.count ??
        playersTotal;
      setPlayersTotal(totalFromApi ?? 0);

      if (totalFromApi > 0) {
        const maxPage = Math.max(1, Math.ceil(totalFromApi / pageSize));
        if (page > maxPage) {
          setPlayersPage(maxPage);
        }
      }

      setPermissionsMap(new Map());
      setVehiclesData(new Map());

      const vehiclesCountMap = new Map<string, number>();
      if (vehiclesSummary?.success && vehiclesSummary.data?.summaries) {
        vehiclesSummary.data.summaries.forEach((summary: PlayerVehicleSummaryItem) => {
          // Usar apenas veículos com status "0" (ativos) ao invés do total
          const activeVehicles = summary.by_status?.["0"] ?? 0;
          vehiclesCountMap.set(summary.steam_id, activeVehicles);
        });
      }
      if (allData?.data?.players) {
        allData.data.players.forEach(player => {
          if (!vehiclesCountMap.has(player.steam_id)) {
            vehiclesCountMap.set(player.steam_id, 0);
          }
        });
      }
      setActiveVehiclesCount(vehiclesCountMap);
    } catch (err) {
      console.error('Erro ao buscar dados de jogadores:', err);
    } finally {
      if (isInitialLoad) {
        setLoading(false);
      } else {
        setRefreshing(false);
      }
    }
  };

  // Função para carregar lista de elevated users
  const loadElevatedUsers = useCallback(async () => {
    try {
      const response = await getElevatedUsersList();
      if (response.success && response.data) {
        const elevatedSet = new Set<string>();
        response.data.elevated_users.forEach((user: ElevatedUser) => {
          elevatedSet.add(user.steam_id);
        });
        setElevatedUsers(elevatedSet);
      }
    } catch (err) {
      console.error('Erro ao carregar elevated users:', err);
    }
  }, []);

  // Carregar dados ao entrar na página (apenas uma vez)
  useEffect(() => {
    fetchPlayers(true, playersPage, playersPageSize);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [playersPage, playersPageSize]);

  // Carregar elevated users quando o componente montar
  useEffect(() => {
    loadElevatedUsers();
  }, [loadElevatedUsers]);

  const searchFetchInitializedRef = useRef(false);
  const searchTriggeredPageChangeRef = useRef(false);
  useEffect(() => {
    if (!searchFetchInitializedRef.current) {
      searchFetchInitializedRef.current = true;
      return;
    }

    if (searchTriggeredPageChangeRef.current) {
      searchTriggeredPageChangeRef.current = false;
      return;
    }

    const handler = setTimeout(() => {
      if (playersPage === 1) {
        fetchPlayers(false, 1, playersPageSize);
      }
    }, 300);

    return () => clearTimeout(handler);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [searchTerm, playersPageSize]);

  useEffect(() => {
    setPlayersPage(prev => {
      if (prev !== 1) {
        searchTriggeredPageChangeRef.current = true;
        return 1;
      }
      searchTriggeredPageChangeRef.current = false;
      return prev;
    });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [searchTerm, filterPermissions]);

  // Função para atualizar manualmente conforme a aba atual
  const handleMainRefresh = () => {
    if (mainTab === 'players') {
      fetchPlayers(false, playersPage, playersPageSize);
    } else if (mainTab === 'squads') {
      fetchSquads(true);
    } else if (mainTab === 'ranking') {
      fetchRankings();
    } else if (mainTab === 'bank') {
      fetchBankAccounts();
    } else {
      fetchAdminLogs();
      fetchAdminLogsStats();
    }
  };

  // Função para verificar se uma permissão está ativa
  const isPermissionActive = (player: PlayerListItem, permissionType: PermissionType): boolean => {
    const permValue = player.permissions?.get(permissionType);
    // Aceitar tanto boolean true quanto number 1 como ativo
    return permValue === true || permValue === 1;
  };

  // Função para carregar veículos de um player
  const loadPlayerVehicles = async (steamId: string, statusFilter?: string | null) => {
    // Se já está carregando, não fazer nada
    if (vehiclesLoading.has(steamId)) return;
    
    setVehiclesLoading(prev => new Set(prev).add(steamId));
    setVehiclesError(prev => {
      const next = new Map(prev);
      next.delete(steamId);
      return next;
    });

    try {
      const response = await getPlayerVehiclesByStatus(steamId, statusFilter || undefined);
      if (response.success && response.data) {
        setVehiclesData(prev => {
          const next = new Map(prev);
          next.set(steamId, response.data!);
          return next;
        });
      } else {
        // Se não tem veículos, tratar como situação normal (sem erro)
        const playerName = allPlayersData?.data?.players.find(p => p.steam_id === steamId)?.player_name || '';
        const playerId = allPlayersData?.data?.players.find(p => p.steam_id === steamId)?.player_id || 0;
        setVehiclesData(prev => {
          const next = new Map(prev);
          // Criar um objeto vazio para indicar que o player não tem veículos
          next.set(steamId, {
            steam_id: steamId,
            player_name: playerName,
            player_id: playerId,
            summary: {
              total_vehicles: 0,
              by_status: {}
            },
            vehicles: [],
            vehicles_by_status: {}
          });
          return next;
        });
      }
    } catch (err: any) {
      // Tratar 404 como "sem veículos" ao invés de erro
      if (err?.response?.status === 404) {
        // 404 significa que o player não tem veículos - situação normal, não logar erro
        const playerName = allPlayersData?.data?.players.find(p => p.steam_id === steamId)?.player_name || '';
        const playerId = allPlayersData?.data?.players.find(p => p.steam_id === steamId)?.player_id || 0;
        setVehiclesData(prev => {
          const next = new Map(prev);
          next.set(steamId, {
            steam_id: steamId,
            player_name: playerName,
            player_id: playerId,
            summary: {
              total_vehicles: 0,
              by_status: {}
            },
            vehicles: [],
            vehicles_by_status: {}
          });
          return next;
        });
      } else {
        // Para outros erros, mostrar mensagem de erro
        console.error(`Erro ao carregar veículos de ${steamId}:`, err);
        setVehiclesError(prev => {
          const next = new Map(prev);
          next.set(steamId, err.message || (t('players.vehicles.error.loadError') ?? 'Error loading vehicles'));
          return next;
        });
      }
    } finally {
      setVehiclesLoading(prev => {
        const next = new Set(prev);
        next.delete(steamId);
        return next;
      });
    }
  };

  const CHESTS_LIMIT = 1000;

  const loadPlayerChests = async (steamId: string) => {
    if (chestsLoading.has(steamId)) return;

    setChestsLoading((prev) => new Set(prev).add(steamId));
    setChestsError((prev) => {
      const next = new Map(prev);
      next.delete(steamId);
      return next;
    });

    try {
      const response = await getChests({
        steamId,
        limit: CHESTS_LIMIT,
        offset: 0,
      });

      if (response.success && response.data) {
        setChestsData((prev) => {
          const next = new Map(prev);
          next.set(steamId, {
            chests: response.data.chests,
            totalCount: response.data.total ?? response.data.count ?? response.data.chests.length,
            limit: response.data.limit ?? CHESTS_LIMIT,
          });
          return next;
        });
      } else {
        setChestsError((prev) => {
          const next = new Map(prev);
          next.set(steamId, response.data ? t('players.chests.loadError') ?? 'Erro ao carregar baús' : t('players.chests.loadError') ?? 'Erro ao carregar baús');
          return next;
        });
      }
    } catch (err: any) {
      console.error(`Erro ao carregar baús de ${steamId}:`, err);
      setChestsError((prev) => {
        const next = new Map(prev);
        next.set(steamId, err?.message || t('players.chests.loadError') || 'Erro ao carregar baús');
        return next;
      });
    } finally {
      setChestsLoading((prev) => {
        const next = new Set(prev);
        next.delete(steamId);
        return next;
      });
    }
  };

  const loadPlayerSurvival = async (steamId: string) => {
    if (!steamId) {
      return;
    }

    if (survivalLoading.has(steamId)) {
      return;
    }

    setSurvivalLoading(prev => new Set(prev).add(steamId));
    setSurvivalError(prev => {
      const next = new Map(prev);
      next.delete(steamId);
      return next;
    });

    try {
      const response = await getSurvivalPlayer(steamId);
      if (response.success && response.data) {
        setSurvivalData(prev => {
          const next = new Map(prev);
          next.set(steamId, {
            metrics: response.data.metrics ?? {},
            derived: response.data.derived,
            snapshotAt: response.data.snapshot_at,
            steamId: response.data.steam_id ?? undefined,
            playerName: response.data.player_name ?? undefined,
          });
          return next;
        });
      } else {
        setSurvivalError(prev => {
          const next = new Map(prev);
          next.set(steamId, t('players.survival.error') ?? 'Erro ao carregar estatísticas');
          return next;
        });
      }
    } catch (err: any) {
      setSurvivalError(prev => {
        const next = new Map(prev);
        next.set(
          steamId,
          err?.message || t('players.survival.error') || 'Erro ao carregar estatísticas'
        );
        return next;
      });
    } finally {
      setSurvivalLoading(prev => {
        const next = new Set(prev);
        next.delete(steamId);
        return next;
      });
    }
  };

  // Função para mudar de aba
  const handleTabChange = (
    steamId: string | null,
    tab: 'permissions' | 'vehicles' | 'chests' | 'survival'
  ) => {
    if (!steamId) {
      return;
    }

    setActiveTab(prev => {
      const next = new Map(prev);
      next.set(steamId, tab);
      return next;
    });

    // Se mudou para a aba de Veículos, carregar os veículos se ainda não foram carregados
    if (tab === 'vehicles' && !vehiclesData.has(steamId) && !vehiclesLoading.has(steamId)) {
      const currentFilter = vehicleStatusFilter.get(steamId);
      loadPlayerVehicles(steamId, currentFilter || null);
    }

    if (tab === 'chests' && !chestsData.has(steamId) && !chestsLoading.has(steamId)) {
      loadPlayerChests(steamId);
    }

    if (tab === 'survival') {
      const key = steamId;
      if (!survivalData.has(key) && !survivalLoading.has(key)) {
        loadPlayerSurvival(steamId);
      }
    }
  };

  // Função para mudar filtro de status de veículos
  const handleVehicleStatusFilterChange = (steamId: string, status: string | null) => {
    setVehicleStatusFilter(prev => {
      const next = new Map(prev);
      next.set(steamId, status);
      return next;
    });
    loadPlayerVehicles(steamId, status);
  };

  // Combinar e ordenar players: online primeiro, depois offline
  const { visiblePlayers, totalFilteredPlayers } = useMemo(() => {
    const onlinePlayers = onlinePlayersData?.data?.players || [];
    const allPlayersList = allPlayersData?.data?.players || [];

    if (allPlayersList.length === 0) {
      return {
        visiblePlayers: [] as PlayerListItem[],
        totalFilteredPlayers: 0,
      };
    }
    
    // Criar um mapa de players online por steam_id para verificação rápida
    const onlineMap = new Map<string, boolean>();
    onlinePlayers.forEach(player => {
      onlineMap.set(player.steam_id, true);
    });

    // Criar lista combinada marcando players como online/offline e adicionar permissões
    let playersList: PlayerListItem[] = allPlayersList.map(player => {
      const playerPerms = permissionsMap.get(player.steam_id);
      const permsMap = new Map<string, boolean>();
      
      if (playerPerms) {
        playerPerms.permissions.forEach(perm => {
          // Aceitar tanto boolean true quanto number 1 como ativo
          const isActive = perm.is_active === true || perm.is_active === 1;
          permsMap.set(perm.permission_type, isActive);
        });
        
        // Debug para ARKANJO
        if (player.player_name === 'ARKANJO') {
          console.log(`[DEBUG] ARKANJO - PlayerPerms:`, playerPerms);
          console.log(`[DEBUG] ARKANJO - PermsMap criado:`, Array.from(permsMap.entries()));
        }
      }

      return {
        ...player,
        isOnline: onlineMap.has(player.steam_id),
        permissions: permsMap
      };
    });

    // Aplicar filtro de pesquisa se houver termo
    if (searchTerm.trim()) {
      const searchLower = searchTerm.toLowerCase().trim();
      playersList = playersList.filter(player => 
        player.player_name.toLowerCase().includes(searchLower) ||
        player.steam_id.includes(searchTerm.trim())
      );
    }

    // Aplicar filtros de permissão
    if (filterPermissions.size > 0) {
      playersList = playersList.filter(player => {
        // Verificar se o player atende a pelo menos um filtro (OR logic)
        // Cada filtro mostra apenas players com a permissão ATIVA
        return Array.from(filterPermissions).some(filterKey => {
          // Verificar Timer (permissao na tabela players) - somente ativos
          if (filterKey === 'timer-active') {
            return player.permissao === 1;
          }
          
          // Verificar Elevated User
          if (filterKey === 'elevated-user') {
            return elevatedUsers.has(player.steam_id);
          }
          
          // Verificar outras permissões (só ativas)
          if (PERMISSION_TYPES.includes(filterKey as PermissionType)) {
            return isPermissionActive(player, filterKey as PermissionType);
          }
          
          return false;
        });
      });
    }

    // Ordenar conforme seleção
    if (sortByVehicles) {
      // Ordenar por quantidade de veículos (maior para menor) e depois online/offline e alfabético
      playersList.sort((a, b) => {
        const vehiclesA = activeVehiclesCount.get(a.steam_id) ?? 0;
        const vehiclesB = activeVehiclesCount.get(b.steam_id) ?? 0;
        
        // Primeiro por quantidade de veículos (descendente)
        if (vehiclesA !== vehiclesB) {
          return vehiclesB - vehiclesA; // Maior para menor
        }
        
        // Se mesma quantidade, online primeiro
        if (a.isOnline !== b.isOnline) {
          return a.isOnline ? -1 : 1;
        }
        
        // Se mesmo status online, ordenar alfabeticamente
        return a.player_name.localeCompare(b.player_name);
      });
    } else {
      // Ordenar: online primeiro, depois offline, e dentro de cada grupo, alfabeticamente por nome
      playersList.sort((a, b) => {
        if (a.isOnline !== b.isOnline) {
          return a.isOnline ? -1 : 1; // Online primeiro
        }
        return a.player_name.localeCompare(b.player_name);
      });
    }

    const totalFilteredPlayers = playersList.length;
    let visiblePlayers: PlayerListItem[];

    if (searchTerm.trim()) {
      const startIndex = (playersPage - 1) * playersPageSize;
      const endIndex = startIndex + playersPageSize;
      visiblePlayers = playersList.slice(startIndex, endIndex);
    } else {
      visiblePlayers = playersList;
    }
    
    return {
      visiblePlayers,
      totalFilteredPlayers,
    };
  }, [
    onlinePlayersData,
    allPlayersData,
    permissionsMap,
    searchTerm,
    filterPermissions,
    sortByVehicles,
    activeVehiclesCount,
    playersPage,
    playersPageSize,
    elevatedUsers,
  ]);

  // Função para recarregar permissões de um player específico
  const reloadPlayerPermissions = async (steamId: string) => {
    try {
      const permsData = await getPlayerPermissions(steamId, false);
      if (permsData.data) {
        setPermissionsMap(prev => new Map(prev).set(steamId, permsData.data!));
      }
    } catch (err) {
      console.error(`Erro ao recarregar permissões de ${steamId}:`, err);
    }
  };

  // Função para atualizar permissão avançada
  const handleTogglePermission = async (player: PlayerListItem, permissionType: PermissionType) => {
    const isActive = isPermissionActive(player, permissionType);
    const actionKey = `${player.steam_id}-${permissionType}`;

    setUpdatingPermissions(prev => new Set(prev).add(actionKey));

    try {
      const response = isActive
        ? await deactivatePermission(player.steam_id, permissionType)
        : await activatePermission(player.steam_id, permissionType);

      if (response.success && response.data) {
        const playerPerms = permissionsMap.get(player.steam_id);
        if (playerPerms) {
          const updatedPermissions = playerPerms.permissions.map(perm =>
            perm.permission_type === permissionType
              ? { ...perm, is_active: response.data!.is_active }
              : perm
          );

          if (!playerPerms.permissions.find(p => p.permission_type === permissionType)) {
            updatedPermissions.push({
              id: response.data.permission_id,
              permission_type: permissionType,
              is_active: response.data.is_active,
              granted_by: response.data.granted_by || 'system',
              granted_at: response.data.granted_at,
              revoked_by: null,
              revoked_at: null,
              notes: null
            });
          }

          const updatedData: PlayerPermissionsData = {
            ...playerPerms,
            permissions: updatedPermissions,
            active_permissions: updatedPermissions.filter(p => p.is_active === true || p.is_active === 1).length
          };
          setPermissionsMap(prev => new Map(prev).set(player.steam_id, updatedData));
        }

        await reloadPlayerPermissions(player.steam_id);

        const wasActivated = !isActive;
        const permissionKeyMap: Record<string, string> = {
          admin: 'admin',
          banned: 'banned',
          server_admin: 'config',
          silenced: 'silenced',
          whitelisted: 'whitelisted',
          raid_webhook_manage: 'raid_webhook_manage',
          elevatedUser: 'elevatedUser',
          timer: 'timer'
        };

        const permissionKey = permissionKeyMap[permissionType] || permissionType;
        const actionSuffix = wasActivated ? 'Activated' : 'Deactivated';
        const messageKey = `players.permissions.messages.${permissionKey}${actionSuffix}`;
        const translatedMessage = t(messageKey);
        const finalMessage = translatedMessage === messageKey
          ? (t('players.permissions.updateSuccess') ?? 'Permission updated successfully')
          : translatedMessage;

        await Swal.fire({
          icon: 'success',
          title: t('players.permissions.updated') ?? 'Permission updated',
          text: finalMessage,
          timer: 1500,
          showConfirmButton: false,
          toast: true,
          position: 'top-end'
        });
      }
    } catch (error: any) {
      const errorText =
        error?.response?.data?.error ||
        error?.response?.data?.message ||
        error?.message ||
        '';
      const normalized = typeof errorText === 'string' ? errorText.toLowerCase() : '';
      const statusCode = error?.response?.status;
      const isAlreadyInState =
        normalized.includes('already active') ||
        normalized.includes('already inactive') ||
        normalized.includes('permission_already') ||
        normalized.includes('já está ativa') ||
        normalized.includes('ja está ativa') ||
        normalized.includes('ja esta ativa') ||
        normalized.includes('já esta ativa') ||
        normalized.includes('já está inativa') ||
        normalized.includes('ja está inativa') ||
        normalized.includes('ja esta inativa') ||
        normalized.includes('já esta inativa');

      if (isAlreadyInState) {
        await reloadPlayerPermissions(player.steam_id);
        await Swal.fire({
          icon: 'info',
          title: t('players.permissions.synchronized') ?? 'Permission synchronized',
          text: errorText || (t('players.permissions.alreadyInState') ?? 'Permission already in the requested state'),
          timer: 2000,
          showConfirmButton: false,
          toast: true,
          position: 'top-end'
        });
      } else if (statusCode === 400) {
        // Alguns backends retornam 400 para "já está ativa/inativa" ou outras validações idempotentes.
        // Para UX de toggle, sincronizamos o estado real e mostramos uma mensagem informativa.
        await reloadPlayerPermissions(player.steam_id);
        await Swal.fire({
          icon: 'info',
          title: t('players.permissions.synchronized') ?? 'Permission synchronized',
          text: errorText || (t('players.permissions.alreadyInState') ?? 'Permission already in the requested state'),
          timer: 2500,
          showConfirmButton: false,
          toast: true,
          position: 'top-end'
        });
      } else if (statusCode === 404) {
        const errorMessage = errorText || (t('players.permissions.updateError') ?? 'Error updating permission');
        await Swal.fire({
          icon: 'error',
          title: t('players.permissions.error') ?? 'Error',
          text: errorMessage,
          timer: 3500,
          toast: true,
          position: 'top-end'
        });
      } else {
        const errorMessage = errorText || (t('players.permissions.updateError') ?? 'Error updating permission');
        await Swal.fire({
          icon: 'error',
          title: t('players.permissions.error') ?? 'Error',
          text: errorMessage,
          timer: 3000,
          toast: true,
          position: 'top-end'
        });
      }
    } finally {
      setUpdatingPermissions(prev => {
        const next = new Set(prev);
        next.delete(actionKey);
        return next;
      });
    }
  };

  // Função para alternar Elevated User
  const handleToggleElevatedUser = async (player: PlayerListItem) => {
    const isElevated = elevatedUsers.has(player.steam_id);
    const newElevated: 0 | 1 = isElevated ? 0 : 1;

    setUpdatingElevatedUsers(prev => new Set(prev).add(player.steam_id));

    try {
      const response = await markElevatedUser(
        player.steam_id,
        newElevated,
        newElevated ? 'Promovido a Elevated User' : 'Removido de Elevated User'
      );

      if (response.success && response.data) {
        setElevatedUsers(prev => {
          const next = new Set(prev);
          if (newElevated === 1) {
            next.add(player.steam_id);
          } else {
            next.delete(player.steam_id);
          }
          return next;
        });

        await loadElevatedUsers();

        let message = response.data.message;
        let icon: 'success' | 'info' = 'success';

        if (response.data.action === 'scheduled') {
          message = t('players.elevatedUser.scheduled') || 'Elevated user agendado. Será sincronizado quando o servidor parar.';
          icon = 'info';
        } else if (response.data.action === 'added' || response.data.action === 'removed') {
          message = t('players.elevatedUser.updated') || 'Elevated user atualizado com sucesso!';
        }

        await Swal.fire({
          icon,
          title: icon === 'success'
            ? (t('players.elevatedUser.success') || 'Sucesso')
            : (t('players.elevatedUser.info') || 'Informação'),
          text: message,
          timer: 3000,
          showConfirmButton: false,
          toast: true,
          position: 'top-end'
        });
      }
    } catch (error: any) {
      const errorMessage = error?.response?.data?.error || error?.message || t('players.elevatedUser.updateError') || 'Erro ao atualizar elevated user';
      await Swal.fire({
        icon: 'error',
        title: t('players.elevatedUser.error') || 'Erro',
        text: errorMessage,
        timer: 3000,
        toast: true,
        position: 'top-end'
      });
    } finally {
      setUpdatingElevatedUsers(prev => {
        const next = new Set(prev);
        next.delete(player.steam_id);
        return next;
      });
    }
  };

  // Função para atualizar permissão do timer
  const handleToggleTimer = async (player: PlayerListItem) => {
    const newPermissao: 0 | 1 = player.permissao === 1 ? 0 : 1;

    setUpdatingIds(prev => new Set(prev).add(player.steam_id));

    try {
      const response = await updatePlayerPermissao(player.steam_id, newPermissao);

      if (response.success && response.data) {
        if (allPlayersData?.data) {
          const updatedPlayers = allPlayersData.data.players.map(p =>
            p.steam_id === player.steam_id ? { ...p, permissao: newPermissao } : p
          );
          setAllPlayersData({
            ...allPlayersData,
            data: {
              ...allPlayersData.data,
              players: updatedPlayers
            }
          });
        }

        await Swal.fire({
          icon: 'success',
          title: t('players.timer.updated'),
          text: response.message || t('players.timer.updateSuccess'),
          timer: 2000,
          showConfirmButton: false,
          toast: true,
          position: 'top-end'
        });
      }
    } catch (error: any) {
      const errorMessage = error?.response?.data?.error || error?.message || t('players.timer.updateError');
      await Swal.fire({
        icon: 'error',
        title: t('players.timer.error'),
        text: errorMessage,
        timer: 3000,
        toast: true,
        position: 'top-end'
      });
    } finally {
      setUpdatingIds(prev => {
        const next = new Set(prev);
        next.delete(player.steam_id);
        return next;
      });
    }
  };

  const handlePlayersPageSizeChange = (value: number) => {
    setPlayersPageSize(value);
    setPlayersPage(1);
  };

  const searchActive = searchTerm.trim().length > 0;
  const effectiveTotal = searchActive ? totalFilteredPlayers : playersTotal;
  const playersMaxPage = Math.max(1, Math.ceil(effectiveTotal / playersPageSize) || 1);
  const playersRangeStart = effectiveTotal === 0 ? 0 : (playersPage - 1) * playersPageSize + 1;
  const playersRangeEnd = effectiveTotal === 0 ? 0 : Math.min(playersPage * playersPageSize, effectiveTotal);

  useEffect(() => {
    if (playersPage > playersMaxPage) {
      setPlayersPage(playersMaxPage);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [playersMaxPage]);

  if (loading) {
    return (
      <div className="card p-4">
        <div className="flex items-center justify-center py-8">
          <div className="text-white/70">{t('players.loading')}</div>
        </div>
      </div>
    );
  }

  const isCurrentTabRefreshing =
    mainTab === 'players'
      ? refreshing || loading
      : mainTab === 'admin-logs'
      ? adminLogsLoading
      : mainTab === 'ranking'
      ? rankingsLoading
      : mainTab === 'bank'
      ? bankLoading
      : squadsLoading;

  const refreshLabel =
    mainTab === 'players'
      ? t('players.refresh') ?? 'Atualizar'
      : mainTab === 'admin-logs'
      ? t('adminLogs.refresh') ?? 'Atualizar'
      : mainTab === 'ranking'
      ? t('players.rankings.refresh') ?? 'Atualizar'
      : mainTab === 'bank'
      ? t('players.bank.refresh') ?? 'Atualizar'
      : t('players.squads.refresh') ?? 'Atualizar';

  return (
    <div className="card p-4">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <Users size={20} />
          <h1 className="text-xl font-semibold">{t('players.title')}</h1>
          {mainTab === 'players' && (
            <span className="text-sm text-white/60">({playersTotal})</span>
          )}
        </div>
        <button
          onClick={handleMainRefresh}
          disabled={isCurrentTabRefreshing}
          className={`flex items-center gap-2 px-3 py-1.5 rounded-lg border transition-colors ${
            isCurrentTabRefreshing
              ? 'bg-black/30 border-white/10 text-white/40 cursor-not-allowed'
              : 'bg-black/30 border-white/10 text-white/70 hover:bg-white/10 hover:text-white hover:border-white/20'
          }`}
          title={refreshLabel}
        >
          <RefreshCw size={16} className={isCurrentTabRefreshing ? 'animate-spin' : ''} />
          <span className="text-sm hidden sm:inline">{refreshLabel}</span>
        </button>
      </div>

      {/* Tabs Principais */}
      <div className="mb-4 border-b border-white/10">
        <div className="flex flex-wrap gap-2">
          <button
            onClick={() => setMainTab('players')}
            className={`px-2 sm:px-4 py-2 text-xs sm:text-sm font-medium transition-colors flex items-center gap-1.5 sm:gap-2 ${
              mainTab === 'players'
                ? 'text-white border-b-2 border-scum-panel'
                : 'text-white/60 hover:text-white/80'
            }`}
          >
            <Users size={14} className="sm:w-4 sm:h-4" />
            <span className="whitespace-nowrap">{t('players.tabs.players')}</span>
          </button>
          <button
            onClick={() => setMainTab('squads')}
            className={`px-2 sm:px-4 py-2 text-xs sm:text-sm font-medium transition-colors flex items-center gap-1.5 sm:gap-2 ${
              mainTab === 'squads'
                ? 'text-white border-b-2 border-scum-panel'
                : 'text-white/60 hover:text-white/80'
            }`}
          >
            <Users2 size={14} className="sm:w-4 sm:h-4" />
            <span className="whitespace-nowrap">{t('players.tabs.squads')}</span>
            {mainTab === 'squads' && squadsTotal > 0 && (
              <span className="text-xs text-white/60">({squadsTotal})</span>
            )}
          </button>
          <button
            onClick={() => setMainTab('admin-logs')}
            className={`px-2 sm:px-4 py-2 text-xs sm:text-sm font-medium transition-colors flex items-center gap-1.5 sm:gap-2 ${
              mainTab === 'admin-logs'
                ? 'text-white border-b-2 border-scum-panel'
                : 'text-white/60 hover:text-white/80'
            }`}
          >
            <FileText size={14} className="sm:w-4 sm:h-4" />
            <span className="whitespace-nowrap">{t('players.tabs.adminLog')}</span>
          </button>
          <button
            onClick={() => setMainTab('ranking')}
            className={`px-2 sm:px-4 py-2 text-xs sm:text-sm font-medium transition-colors flex items-center gap-1.5 sm:gap-2 ${
              mainTab === 'ranking'
                ? 'text-white border-b-2 border-scum-panel'
                : 'text-white/60 hover:text-white/80'
            }`}
          >
            <Trophy size={14} className="sm:w-4 sm:h-4" />
            <span className="whitespace-nowrap">{t('players.tabs.ranking')}</span>
            {mainTab === 'ranking' && rankingsTotal > 0 && (
              <span className="text-xs text-white/60">({rankingsTotal})</span>
            )}
          </button>
          <button
            onClick={() => setMainTab('analyses')}
            className={`px-2 sm:px-4 py-2 text-xs sm:text-sm font-medium transition-colors flex items-center gap-1.5 sm:gap-2 ${
              mainTab === 'analyses'
                ? 'text-white border-b-2 border-scum-panel'
                : 'text-white/60 hover:text-white/80'
            }`}
          >
            <BarChart3 size={14} className="sm:w-4 sm:h-4" />
            <span className="whitespace-nowrap">{t('players.tabs.analyses')}</span>
          </button>

          {isAdmin && (
            <button
              onClick={() => {
                setMainTab('bank');
                setBankOffset(0);
              }}
              className={`px-2 sm:px-4 py-2 text-xs sm:text-sm font-medium transition-colors flex items-center gap-1.5 sm:gap-2 ${
                mainTab === 'bank'
                  ? 'text-white border-b-2 border-scum-panel'
                  : 'text-white/60 hover:text-white/80'
              }`}
            >
              <Boxes size={14} className="sm:w-4 sm:h-4" />
              <span className="whitespace-nowrap">{t('players.tabs.bank')}</span>
              {mainTab === 'bank' && bankTotal > 0 && (
                <span className="text-xs text-white/60">({bankTotal})</span>
              )}
            </button>
          )}
        </div>
      </div>
      
      {/* Conteúdo condicional baseado na tab */}
      {mainTab === 'players' && (
        <>
          {/* Campo de pesquisa */}
          <div className="mb-4">
            <div className="relative">
              <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-white/40" size={18} />
              <input
                type="text"
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                placeholder={t('players.search.placeholder') ?? 'Search by player name or Steam ID...'}
                className="w-full pl-10 pr-4 py-2 bg-black/30 border border-white/10 rounded-lg text-white placeholder-white/40 focus:outline-none focus:ring-2 focus:ring-scum-panel focus:border-transparent"
              />
            </div>
          </div>

          {/* Filtros de Permissão */}
          <div className="mb-4">
        <div className="text-xs text-white/60 mb-2">{t('players.filters.title') ?? 'Filter by permissions:'}</div>
        <div className="flex flex-wrap gap-2">
          {/* Timer - somente ativos */}
          <button
            onClick={() => {
              setFilterPermissions(prev => {
                const next = new Set(prev);
                if (next.has('timer-active')) {
                  next.delete('timer-active');
                } else {
                  next.add('timer-active');
                  next.delete('timer-inactive'); // Remove o oposto se existir
                }
                return next;
              });
            }}
            className={`px-3 py-1.5 text-xs rounded-lg border transition-colors ${
              filterPermissions.has('timer-active')
                ? 'bg-green-500/20 border-green-500 text-green-400'
                : 'bg-black/30 border-white/10 text-white/70 hover:border-white/20'
            }`}
          >
            {t('players.table.timer')}
          </button>

          {/* Outras Permissões */}
          {PERMISSION_TYPES.map(permType => (
            <button
              key={permType}
              onClick={() => {
                setFilterPermissions(prev => {
                  const next = new Set(prev);
                  if (next.has(permType)) {
                    next.delete(permType);
                  } else {
                    next.add(permType);
                  }
                  return next;
                });
              }}
              className={`px-3 py-1.5 text-xs rounded-lg border transition-colors ${
                filterPermissions.has(permType)
                  ? 'bg-green-500/20 border-green-500 text-green-400'
                  : 'bg-black/30 border-white/10 text-white/70 hover:border-white/20'
              }`}
            >
              {t(`players.permissions.${permType}`)}
            </button>
          ))}

          {/* Elevated User */}
          <button
            onClick={() => {
              setFilterPermissions(prev => {
                const next = new Set(prev);
                if (next.has('elevated-user')) {
                  next.delete('elevated-user');
                } else {
                  next.add('elevated-user');
                }
                return next;
              });
            }}
            className={`px-3 py-1.5 text-xs rounded-lg border transition-colors ${
              filterPermissions.has('elevated-user')
                ? 'bg-green-500/20 border-green-500 text-green-400'
                : 'bg-black/30 border-white/10 text-white/70 hover:border-white/20'
            }`}
          >
            {t('players.permissions.elevatedUser')}
          </button>

          {/* Botão limpar filtros */}
          {filterPermissions.size > 0 && (
            <button
              onClick={() => setFilterPermissions(new Set())}
              className="px-3 py-1.5 text-xs rounded-lg border bg-black/30 border-white/10 text-white/70 hover:border-white/20 transition-colors"
            >
              {t('players.filters.clear') ?? 'Clear filters'}
            </button>
          )}
        </div>
      </div>

          {visiblePlayers.length > 0 ? (
        <div className="overflow-x-auto -mx-4 px-4 sm:mx-0 sm:px-0" style={{ WebkitOverflowScrolling: 'touch' }}>
          <div className="inline-block min-w-full align-middle">
            <table className="min-w-full text-sm">
              <thead>
                <tr className="border-b border-white/10">
                  <th className="text-left py-2 px-1 sm:px-2 text-white/70 font-medium whitespace-nowrap sticky left-0 bg-black/40 z-10">{t('players.table.playerName')}</th>
                  <th className="text-left py-2 px-1 sm:px-2 text-white/70 font-medium whitespace-nowrap hidden sm:table-cell">{t('players.table.steamId')}</th>
                  <th className="text-left py-2 px-1 sm:px-2 text-white/70 font-medium whitespace-nowrap">{t('players.table.status')}</th>
                  <th 
                    className="text-left py-2 px-1 sm:px-2 text-white/70 font-medium whitespace-nowrap cursor-pointer hover:text-white transition-colors select-none"
                    onClick={() => {
                      const nextSortState = !sortByVehicles;
                      setSortByVehicles(nextSortState);
                      if (playersPage !== 1) {
                        setPlayersPage(1);
                      } else {
                        fetchPlayers(false, 1, playersPageSize, nextSortState);
                      }
                    }}
                    title={t('players.table.sortByVehicles') ?? 'Ordenar por quantidade de veículos'}
                  >
                    <div className="flex items-center gap-1.5">
                      {t('players.table.vehicles')}
                      {sortByVehicles && <ArrowDown size={14} className="text-green-400" />}
                    </div>
                  </th>
                </tr>
              </thead>
              <tbody>
                {visiblePlayers.map((player) => (
                  <Fragment key={player.steam_id}>
                    <tr key={`${player.steam_id}-main`} className="border-b border-white/5 hover:bg-white/5">
                      <td className="py-2 px-1 sm:px-2 sticky left-0 bg-black/30 z-10 whitespace-nowrap font-medium">
                        <button
                          className="text-left w-full hover:text-white/90"
                          onClick={() => {
                            const isCurrentlyExpanded = expanded.has(player.steam_id);
                            setExpanded(prev => {
                              const next = new Set(prev);
                              if (isCurrentlyExpanded) {
                                next.delete(player.steam_id);
                              } else {
                                next.add(player.steam_id);
                                // Carregar permissões quando expandir pela primeira vez
                                if (!permissionsMap.has(player.steam_id)) {
                                  reloadPlayerPermissions(player.steam_id);
                                }
                              }
                              return next;
                            });
                          }}
                          aria-expanded={expanded.has(player.steam_id)}
                        >
                          {player.player_name}
                        </button>
                      </td>
                      <td className="py-2 px-1 sm:px-2 text-white/70 text-xs font-mono hidden sm:table-cell">{player.steam_id}</td>
                      <td className="py-2 px-1 sm:px-2 whitespace-nowrap">
                        <div className="flex items-center gap-1.5 sm:gap-2">
                          <Circle 
                            size={8} 
                            className={`flex-shrink-0 ${player.isOnline ? 'fill-current text-green-400' : 'fill-current text-red-400'}`}
                          />
                          <span className={`text-xs sm:text-sm ${player.isOnline ? 'text-green-400' : 'text-red-400'}`}>
                            {player.isOnline ? t('players.status.online') : t('players.status.offline')}
                          </span>
                        </div>
                      </td>
                      <td className="py-2 px-1 sm:px-2 whitespace-nowrap">
                        <span className={`text-sm font-semibold ${(activeVehiclesCount.get(player.steam_id) || 0) > 0 ? 'text-green-400' : 'text-red-400'}`}>
                          {activeVehiclesCount.get(player.steam_id) ?? 0}
                        </span>
                      </td>
                    </tr>
                    {expanded.has(player.steam_id) && (() => {
                      const currentTab = activeTab.get(player.steam_id) || 'permissions';
                      const playerVehiclesData = vehiclesData.get(player.steam_id);
                      const playerVehiclesLoading = vehiclesLoading.has(player.steam_id);
                      const playerVehiclesError = vehiclesError.get(player.steam_id);
                      const currentVehicleFilter = vehicleStatusFilter.get(player.steam_id) || null;
                      const playerChestData = chestsData.get(player.steam_id);
                      const playerChestLoading = chestsLoading.has(player.steam_id);
                      const playerChestError = chestsError.get(player.steam_id);
                      const playerSurvivalData = player.steam_id ? survivalData.get(player.steam_id) : undefined;
                      const playerSurvivalLoading = player.steam_id ? survivalLoading.has(player.steam_id) : false;
                      const playerSurvivalError = player.steam_id ? survivalError.get(player.steam_id) : undefined;

                      return (
                        <tr key={`${player.steam_id}-panel`} className="border-b border-white/10 bg-black/20">
                          <td colSpan={4} className="py-3 px-2">
                            {/* Abas */}
                            <div className="flex flex-wrap gap-2 mb-3 border-b border-white/10">
                              <button
                                onClick={() => handleTabChange(player.steam_id, 'permissions')}
                                className={`px-3 py-2 text-xs sm:text-sm font-medium transition-colors ${
                                  currentTab === 'permissions'
                                    ? 'text-white border-b-2 border-scum-panel'
                                    : 'text-white/60 hover:text-white/80'
                                }`}
                              >
                                {t('players.tabs.permissions')}
                              </button>
                              <button
                                onClick={() => handleTabChange(player.steam_id, 'vehicles')}
                                className={`px-4 py-2 text-xs sm:text-sm font-medium transition-colors flex items-center gap-1.5 ${
                                  currentTab === 'vehicles'
                                    ? 'text-white border-b-2 border-scum-panel'
                                    : 'text-white/60 hover:text-white/80'
                                }`}
                              >
                                <Car size={16} />
                                {t('players.tabs.vehicles')}
                              </button>
                              <button
                                onClick={() => handleTabChange(player.steam_id, 'chests')}
                                className={`px-4 py-2 text-xs sm:text-sm font-medium transition-colors flex items-center gap-1.5 ${
                                  currentTab === 'chests'
                                    ? 'text-white border-b-2 border-scum-panel'
                                    : 'text-white/60 hover:text-white/80'
                                }`}
                              >
                                <Boxes size={16} />
                                {t('players.tabs.chests')}
                              </button>
                              <button
                                onClick={() => {
                                  if (player.steam_id) {
                                    handleTabChange(player.steam_id, 'survival');
                                  }
                                }}
                                className={`px-4 py-2 text-xs sm:text-sm font-medium transition-colors flex items-center gap-1.5 ${
                                  currentTab === 'survival'
                                    ? 'text-white border-b-2 border-scum-panel'
                                    : 'text-white/60 hover:text-white/80'
                                } ${player.steam_id ? '' : 'cursor-not-allowed opacity-50'}`}
                                disabled={!player.steam_id}
                              >
                                <Activity size={16} />
                                {t('players.tabs.survival')}
                              </button>
                            </div>

                            {/* Conteúdo das Abas */}
                            {currentTab === 'permissions' ? (
                              <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-6 gap-3">
                                {/* Timer */}
                                <div className="flex items-center justify-between gap-2 p-2 rounded-lg bg-white/5">
                                  <span className="text-xs text-white/80">{t('players.table.timer')}</span>
                                  <button
                                    onClick={() => handleToggleTimer(player)}
                                    disabled={updatingIds.has(player.steam_id)}
                                    className={`relative inline-flex h-5 w-9 sm:h-6 sm:w-11 items-center rounded-full transition-colors focus:outline-none focus:ring-2 focus:ring-scum-panel ${
                                      player.permissao === 1 ? 'bg-green-500' : 'bg-gray-600'
                                    } ${updatingIds.has(player.steam_id) ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer'}`}
                                    title={player.permissao === 1 ? t('players.timer.disable') : t('players.timer.enable')}
                                  >
                                    <span
                                      className={`inline-block h-3 w-3 sm:h-4 sm:w-4 transform rounded-full bg-white transition-transform ${
                                        player.permissao === 1 ? 'translate-x-5 sm:translate-x-6' : 'translate-x-0.5 sm:translate-x-1'
                                      }`}
                                    />
                                    {updatingIds.has(player.steam_id) && (
                                      <div className="absolute inset-0 flex items-center justify-center">
                                        <div className="h-2 w-2 sm:h-3 sm:w-3 animate-spin rounded-full border-2 border-white border-t-transparent" />
                                      </div>
                                    )}
                                  </button>
                                </div>
                                {/* Elevated User */}
                                <div className="flex items-center justify-between gap-2 p-2 rounded-lg bg-white/5">
                                  <span className="text-xs text-white/80">{t('players.permissions.elevatedUser')}</span>
                                  <button
                                    onClick={() => handleToggleElevatedUser(player)}
                                    disabled={updatingElevatedUsers.has(player.steam_id)}
                                    className={`relative inline-flex h-5 w-9 sm:h-6 sm:w-11 items-center rounded-full transition-colors focus:outline-none focus:ring-2 focus:ring-scum-panel ${
                                      elevatedUsers.has(player.steam_id) ? 'bg-green-500' : 'bg-gray-600'
                                    } ${updatingElevatedUsers.has(player.steam_id) ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer'}`}
                                    title={elevatedUsers.has(player.steam_id) ? t('players.elevatedUser.disable') : t('players.elevatedUser.enable')}
                                  >
                                    <span
                                      className={`inline-block h-3 w-3 sm:h-4 sm:w-4 transform rounded-full bg-white transition-transform ${
                                        elevatedUsers.has(player.steam_id) ? 'translate-x-5 sm:translate-x-6' : 'translate-x-0.5 sm:translate-x-1'
                                      }`}
                                    />
                                    {updatingElevatedUsers.has(player.steam_id) && (
                                      <div className="absolute inset-0 flex items-center justify-center">
                                        <div className="h-2 w-2 sm:h-3 sm:w-3 animate-spin rounded-full border-2 border-white border-t-transparent" />
                                      </div>
                                    )}
                                  </button>
                                </div>
                                {/* Outras Permissões */}
                                {PERMISSION_TYPES.map(permType => {
                                  const isActive = isPermissionActive(player, permType);
                                  const actionKey = `${player.steam_id}-${permType}`;
                                  const isUpdating = updatingPermissions.has(actionKey);
                                  return (
                                    <div key={permType} className="flex items-center justify-between gap-2 p-2 rounded-lg bg-white/5">
                                      <span className="text-xs text-white/80">{t(`players.permissions.${permType}`)}</span>
                                      <button
                                        onClick={() => handleTogglePermission(player, permType)}
                                        disabled={isUpdating}
                                        className={`relative inline-flex h-5 w-9 sm:h-6 sm:w-11 items-center rounded-full transition-colors focus:outline-none focus:ring-2 focus:ring-scum-panel ${
                                          isActive ? 'bg-green-500' : 'bg-gray-600'
                                        } ${isUpdating ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer'}`}
                                      >
                                        <span
                                          className={`inline-block h-3 w-3 sm:h-4 sm:w-4 transform rounded-full bg-white transition-transform ${
                                            isActive ? 'translate-x-5 sm:translate-x-6' : 'translate-x-0.5 sm:translate-x-1'
                                          }`}
                                        />
                                        {isUpdating && (
                                          <div className="absolute inset-0 flex items-center justify-center">
                                            <div className="h-2 w-2 sm:h-3 sm:w-3 animate-spin rounded-full border-2 border-white border-t-transparent" />
                                          </div>
                                        )}
                                      </button>
                                    </div>
                                  );
                                })}
                              </div>
                            ) : currentTab === 'vehicles' ? (
                              // Aba de Veículos
                              <div>
                                {playerVehiclesLoading ? (
                                  <div className="flex items-center justify-center py-8">
                                    <div className="text-white/70">{t('players.vehicles.loading')}</div>
                                  </div>
                                ) : playerVehiclesError ? (
                                  <div className="text-red-400 text-sm py-4 text-center">{playerVehiclesError}</div>
                                ) : playerVehiclesData ? (
                                  <div>
                                    {/* Resumo */}
                                    {playerVehiclesData.summary && (
                                      <div className="mb-4 p-3 rounded-lg bg-white/5">
                                        <div className="text-sm font-medium text-white/90 mb-2">
                                          {t('players.vehicles.total', { count: playerVehiclesData.summary.total_vehicles })}
                                        </div>
                                        {playerVehiclesData.summary.by_status && (
                                          <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 text-xs">
                                            <div className="flex items-center gap-1.5">
                                              <div className="w-2 h-2 rounded-full bg-green-500" />
                                              <span className="text-white/70">{t('players.vehicles.summary.active')}: {playerVehiclesData.summary.by_status['0'] || 0}</span>
                                            </div>
                                            <div className="flex items-center gap-1.5">
                                              <div className="w-2 h-2 rounded-full bg-yellow-500" />
                                              <span className="text-white/70">{t('players.vehicles.summary.inactive')}: {playerVehiclesData.summary.by_status['1'] || 0}</span>
                                            </div>
                                            <div className="flex items-center gap-1.5">
                                              <div className="w-2 h-2 rounded-full bg-orange-500" />
                                              <span className="text-white/70">{t('players.vehicles.summary.disappeared')}: {playerVehiclesData.summary.by_status['2'] || 0}</span>
                                            </div>
                                            <div className="flex items-center gap-1.5">
                                              <div className="w-2 h-2 rounded-full bg-red-500" />
                                              <span className="text-white/70">{t('players.vehicles.summary.destroyed')}: {playerVehiclesData.summary.by_status['3'] || 0}</span>
                                            </div>
                                          </div>
                                        )}
                                      </div>
                                    )}

                                    {/* Filtros de Status */}
                                    <div className="mb-4">
                                      <div className="flex flex-wrap gap-2">
                                        <button
                                          onClick={() => handleVehicleStatusFilterChange(player.steam_id, null)}
                                          className={`px-3 py-1.5 text-xs rounded-lg border transition-colors ${
                                            currentVehicleFilter === null
                                              ? 'bg-scum-panel/30 border-scum-panel text-white'
                                              : 'bg-black/30 border-white/10 text-white/70 hover:border-white/20'
                                          }`}
                                        >
                                          {t('players.vehicles.filters.all')}
                                        </button>
                                        <button
                                          onClick={() => handleVehicleStatusFilterChange(player.steam_id, '0')}
                                          className={`px-3 py-1.5 text-xs rounded-lg border transition-colors ${
                                            currentVehicleFilter === '0'
                                              ? 'bg-green-500/20 border-green-500 text-green-400'
                                              : 'bg-black/30 border-white/10 text-white/70 hover:border-white/20'
                                          }`}
                                        >
                                          {t('players.vehicles.filters.active')}
                                        </button>
                                        <button
                                          onClick={() => handleVehicleStatusFilterChange(player.steam_id, '1')}
                                          className={`px-3 py-1.5 text-xs rounded-lg border transition-colors ${
                                            currentVehicleFilter === '1'
                                              ? 'bg-yellow-500/20 border-yellow-500 text-yellow-400'
                                              : 'bg-black/30 border-white/10 text-white/70 hover:border-white/20'
                                          }`}
                                        >
                                          {t('players.vehicles.filters.inactive')}
                                        </button>
                                        <button
                                          onClick={() => handleVehicleStatusFilterChange(player.steam_id, '2')}
                                          className={`px-3 py-1.5 text-xs rounded-lg border transition-colors ${
                                            currentVehicleFilter === '2'
                                              ? 'bg-orange-500/20 border-orange-500 text-orange-400'
                                              : 'bg-black/30 border-white/10 text-white/70 hover:border-white/20'
                                          }`}
                                        >
                                          {t('players.vehicles.filters.disappeared')}
                                        </button>
                                        <button
                                          onClick={() => handleVehicleStatusFilterChange(player.steam_id, '3')}
                                          className={`px-3 py-1.5 text-xs rounded-lg border transition-colors ${
                                            currentVehicleFilter === '3'
                                              ? 'bg-red-500/20 border-red-500 text-red-400'
                                              : 'bg-black/30 border-white/10 text-white/70 hover:border-white/20'
                                          }`}
                                        >
                                          {t('players.vehicles.filters.destroyed')}
                                        </button>
                                      </div>
                                    </div>

                                    {/* Lista de Veículos */}
                                    {(() => {
                                      // Se há filtro, usar vehicles array; senão, usar vehicles_by_status
                                      const vehiclesToShow: Vehicle[] = currentVehicleFilter !== null
                                        ? (playerVehiclesData.vehicles || [])
                                        : Object.values(playerVehiclesData.vehicles_by_status || {}).flat();

                                      if (vehiclesToShow.length === 0) {
                                        return (
                                          <div className="text-white/70 text-sm py-4 text-center">
                                            {t('players.vehicles.noVehicles')}
                                          </div>
                                        );
                                      }

                                      // Agrupar por status se não há filtro
                                      const groupedByStatus = currentVehicleFilter === null
                                        ? playerVehiclesData.vehicles_by_status || {}
                                        : { [currentVehicleFilter]: vehiclesToShow };

                                      // Função para agrupar veículos em pares (chunks de 2)
                                      const chunkVehicles = <T,>(array: T[], size: number): T[][] => {
                                        const chunks: T[][] = [];
                                        for (let i = 0; i < array.length; i += size) {
                                          chunks.push(array.slice(i, i + size));
                                        }
                                        return chunks;
                                      };

                                      // Função para obter cor do status
                                      const getStatusColor = (status: string): string => {
                                        const statusColors: Record<string, string> = {
                                          '0': 'bg-green-500/10 border-green-500/30',
                                          '1': 'bg-yellow-500/10 border-yellow-500/30',
                                          '2': 'bg-orange-500/10 border-orange-500/30',
                                          '3': 'bg-red-500/10 border-red-500/30'
                                        };
                                        return statusColors[status] || 'bg-white/5 border-white/10';
                                      };

                                      // Agrupar todos os veículos em pares, independente do status
                                      const allVehiclesPairs = chunkVehicles(vehiclesToShow, 2);

                                      return (
                                        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 items-start">
                                          {allVehiclesPairs.map((vehiclePair, pairIndex) => {
                                            // Determinar cor do card baseado no status do primeiro veículo
                                            // Sempre usa a cor do primeiro veículo para manter consistência visual
                                            const firstStatus = vehiclePair[0]?.status?.toString() || '0';
                                            const cardColor = getStatusColor(firstStatus);

                                            return (
                                              <div key={pairIndex} className={`border rounded-lg p-3 ${cardColor} flex flex-col`}>
                                                <div className={`grid gap-3 ${vehiclePair.length === 1 ? 'grid-cols-1' : 'grid-cols-1 md:grid-cols-2'}`}>
                                                  {vehiclePair.map((vehicle) => {
                                                    const vehicleImage = getVehicleImagePath(vehicle.vehicle_class_display);
                                                    return (
                                                      <div key={vehicle.entity_id} className="p-2 rounded bg-black/20 border border-white/5">
                                                        <div className="flex items-center gap-2 mb-1">
                                                          {vehicleImage ? (
                                                            <img 
                                                              src={vehicleImage} 
                                                              alt={vehicle.vehicle_class_display}
                                                              className="w-10 h-10 object-contain flex-shrink-0"
                                                              onError={(e) => {
                                                                // Fallback: esconder imagem se não carregar
                                                                e.currentTarget.style.display = 'none';
                                                              }}
                                                            />
                                                          ) : (
                                                            <div className="w-10 h-10 bg-white/5 rounded flex items-center justify-center flex-shrink-0">
                                                              <Car size={20} className="text-white/40" />
                                                            </div>
                                                          )}
                                                          <span className="text-sm font-medium text-white/90 truncate">
                                                            {vehicle.vehicle_class_display}
                                                          </span>
                                                        </div>
                                                        <div className="space-y-1 text-xs text-white/60">
                                                          <div className="whitespace-nowrap">
                                                            <span className="text-white/40">{t('players.vehicles.details.vehicleEntityId')}: </span>
                                                            <span className="font-mono">{vehicle.vehicle_entity_id}</span>
                                                          </div>
                                                          <div className="whitespace-nowrap">
                                                            <span className="text-white/40">{t('players.vehicles.details.entityId')}: </span>
                                                            <span className="font-mono">{vehicle.entity_id}</span>
                                                          </div>
                                                          <div className="whitespace-nowrap">
                                                            <span className="text-white/40">{t('players.vehicles.details.location')}: </span>
                                                            {Number.isFinite(vehicle.location_x) && Number.isFinite(vehicle.location_y) ? (
                                                              <a
                                                                href={`https://scum-map.com/en/shared/scum/island/${vehicle.location_x.toFixed(4)},${vehicle.location_y.toFixed(4)},4`}
                                                                target="_blank"
                                                                rel="noopener noreferrer"
                                                                className="font-mono text-white hover:text-green-300 hover:underline"
                                                                title={t('players.vehicles.details.openMap') ?? undefined}
                                                              >
                                                                ({vehicle.location_x.toFixed(0)}, {vehicle.location_y.toFixed(0)}, {vehicle.location_z.toFixed(0)})
                                                              </a>
                                                            ) : (
                                                              <span className="font-mono">
                                                                ({vehicle.location_x.toFixed(0)}, {vehicle.location_y.toFixed(0)}, {vehicle.location_z.toFixed(0)})
                                                              </span>
                                                            )}
                                                          </div>
                                                          <div className="whitespace-nowrap">
                                                            <span className="text-white/40">{t('players.vehicles.details.lastChange')}: </span>
                                                            <span>{new Date(vehicle.last_ownership_change).toLocaleString()}</span>
                                                          </div>
                                                          <div className="whitespace-nowrap">
                                                            <span className="text-white/40">{t('players.vehicles.details.status')}: </span>
                                                            <span>{vehicle.status_text}</span>
                                                            {vehicle.is_vehicle_functional !== undefined && (
                                                              <>
                                                                {' • '}
                                                                <span>{vehicle.is_vehicle_functional === 1 
                                                                  ? t('players.vehicles.details.functional')
                                                                  : t('players.vehicles.details.nonFunctional')
                                                                }</span>
                                                              </>
                                                            )}
                                                          </div>
                                                        </div>
                                                      </div>
                                                    );
                                                  })}
                                                </div>
                                              </div>
                                            );
                                          })}
                                        </div>
                                      );
                                    })()}
                                  </div>
                                ) : (
                                  <div className="text-white/70 text-sm py-4 text-center">
                                    {t('players.vehicles.noVehicles')}
                                  </div>
                                )}
                              </div>
                            ) : currentTab === 'chests' ? (
                              <div>
                                {playerChestLoading ? (
                                  <div className="flex items-center justify-center py-8">
                                    <div className="text-white/70">{t('players.chests.loading')}</div>
                                  </div>
                                ) : playerChestError ? (
                                  <div className="flex flex-col items-center gap-2 py-6 text-sm text-red-400">
                                    <span>{playerChestError}</span>
                                    <button
                                      type="button"
                                      onClick={() => loadPlayerChests(player.steam_id)}
                                      className="rounded-lg border border-red-400/40 bg-red-500/10 px-3 py-1.5 text-xs text-red-200 hover:bg-red-500/20 transition"
                                    >
                                      {t('players.chests.retry')}
                                    </button>
                                  </div>
                                ) : playerChestData ? (
                                  <div className="space-y-4">
                                    <div className="rounded-lg border border-white/10 bg-white/5 p-3 text-sm text-white/80">
                                      <div className="flex flex-wrap items-center justify-between gap-2">
                                          <div className="flex flex-col gap-1">
                                          <span className="font-semibold text-white">
                                            {t('players.chests.summary.total', {
                                              count: playerChestData.totalCount,
                                            })}
                                          </span>
                                          {playerChestData.totalCount > playerChestData.chests.length && (
                                            <span className="text-xs text-yellow-300/80">
                                              {t('players.chests.summary.limitWarning', {
                                                limit: playerChestData.limit,
                                              })}
                                            </span>
                                          )}
                                        </div>
                                        <button
                                          type="button"
                                          onClick={() => loadPlayerChests(player.steam_id)}
                                          className={`inline-flex items-center gap-2 rounded-lg border border-white/10 px-3 py-1.5 text-xs font-semibold transition ${
                                            chestsLoading.has(player.steam_id)
                                              ? 'cursor-wait opacity-60'
                                              : 'hover:border-scum-panel/40 hover:bg-scum-panel/10'
                                          }`}
                                        >
                                          <RefreshCw
                                            size={14}
                                            className={chestsLoading.has(player.steam_id) ? 'animate-spin text-scum-panel' : 'text-white/70'}
                                          />
                                          {t('players.chests.refresh')}
                                        </button>
                                      </div>
                                      {(() => {
                                        const totalWithCoords = playerChestData.chests.filter((c) => isValidChestLocation(c.location)).length;
                                        const totalWithoutCoords = playerChestData.chests.length - totalWithCoords;
                                        const typeCounts = playerChestData.chests.reduce<Record<string, number>>((acc, chest) => {
                                          const key = chest.chest_type || t('players.chests.unknownType');
                                          acc[key] = (acc[key] || 0) + 1;
                                          return acc;
                                        }, {});

                                        return (
                                          <div className="mt-3 grid grid-cols-1 gap-2 text-xs text-white/70 sm:grid-cols-3">
                                            <span>
                                              <strong className="text-white/80">
                                                {t('players.chests.summary.withCoords')}:
                                              </strong>{' '}
                                              {totalWithCoords}
                                            </span>
                                            <span>
                                              <strong className="text-white/80">
                                                {t('players.chests.summary.withoutCoords')}:
                                              </strong>{' '}
                                              {totalWithoutCoords}
                                            </span>
                                            <span>
                                              <strong className="text-white/80">
                                                {t('players.chests.summary.types')}:
                                              </strong>{' '}
                                              {Object.entries(typeCounts)
                                                .map(([type, count]) => `${type} (${count})`)
                                                .join(', ')}
                                            </span>
                                          </div>
                                        );
                                      })()}
                                    </div>

                                    {playerChestData.chests.length === 0 ? (
                                      <div className="py-6 text-center text-sm text-white/60">
                                        {t('players.chests.empty')}
                                      </div>
                                    ) : (
                                      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
                                        {playerChestData.chests.map((chest) => {
                                          const hasLocation = isValidChestLocation(chest.location);
                                          const coordinates = hasLocation
                                            ? `(${(chest.location.x ?? 0).toFixed(0)}, ${(chest.location.y ?? 0).toFixed(0)}, ${(chest.location.z ?? 0).toFixed(0)})`
                                            : t('players.chests.noCoordinates');
                                          const scumMapUrl =
                                            hasLocation && chest.location
                                              ? `https://scum-map.com/en/shared/scum/island/${(chest.location.x ?? 0).toFixed(4)},${(chest.location.y ?? 0).toFixed(4)},4`
                                              : null;
                                          const thumbnail = getChestThumbnail(chest.chest_class, chest.chest_type);

                                          return (
                                            <div
                                              key={chest.entity_id}
                                              className="rounded-lg border border-white/10 bg-black/20 p-3 text-xs text-white/70 flex flex-col gap-2"
                                              style={{ minHeight: '160px' }}
                                            >
                                              <div className="mb-2 flex items-center justify-between gap-2">
                                                <div className="flex items-center gap-2">
                                                  {thumbnail ? (
                                                    <img
                                                      src={thumbnail}
                                                      alt={chest.chest_type || chest.chest_class || 'Chest'}
                                                      className="h-10 w-10 rounded-md border border-white/10 object-cover"
                                                      onError={(e) => {
                                                        e.currentTarget.style.display = 'none';
                                                      }}
                                                    />
                                                  ) : (
                                                    <div className="h-10 w-10 rounded-md border border-white/10 bg-white/5 flex items-center justify-center text-white/40">
                                                      <Boxes size={18} />
                                                    </div>
                                                  )}
                                                  <div className="font-semibold text-white">
                                                    {chest.custom_name || chest.player_name || chest.fake_name || t('players.chests.unknownName')}
                                                  </div>
                                                </div>
                                                <span className="rounded-full border border-white/10 bg-white/5 px-2 py-0.5 text-[11px] text-white/60">
                                                  {chest.chest_type}
                                                </span>
                                              </div>
                                              <div className="space-y-1">
                                                <div className="flex flex-wrap items-center gap-1">
                                                  <span className="text-white/40">
                                                    {t('players.chests.fields.location')}:
                                                  </span>{' '}
                                                  {hasLocation && scumMapUrl ? (
                                                    <a
                                                      href={scumMapUrl}
                                                      target="_blank"
                                                      rel="noopener noreferrer"
                                                      className="text-white hover:text-green-300 hover:underline"
                                                      title={t('players.chests.fields.openMap') ?? undefined}
                                                    >
                                                      {coordinates}
                                                    </a>
                                                  ) : (
                                                    coordinates
                                                  )}
                                                </div>
                                                <div>
                                                  <span className="text-white/40">
                                                    {t('players.chests.fields.lastSeen')}:
                                                  </span>{' '}
                                                  {new Date(chest.last_seen_at).toLocaleString()}
                                                </div>
                                                {chest.has_vehicle && chest.vehicle ? (
                                                  <div>
                                                    <span className="text-white/40">
                                                      {t('players.chests.fields.vehicle')}:
                                                    </span>{' '}
                                                    {chest.vehicle.class || t('players.chests.unknownVehicle')}
                                                  </div>
                                                ) : null}
                                              </div>
                                            </div>
                                          );
                                        })}
                                      </div>
                                    )}
                                  </div>
                                ) : (
                                  <div className="text-white/70 py-6 text-center text-sm">
                                    {t('players.chests.empty')}
                                  </div>
                                )}
                              </div>
                            ) : (
                              <div>
                                {!player.steam_id ? (
                                  <div className="text-white/70 text-sm py-4 text-center">
                                    {t('players.survival.noData')}
                                  </div>
                                ) : playerSurvivalLoading ? (
                                  <div className="flex items-center justify-center py-8">
                                    <div className="text-white/70">{t('players.survival.loading')}</div>
                                  </div>
                                ) : playerSurvivalError ? (
                                  <div className="flex flex-col items-center gap-2 py-6 text-sm text-red-400">
                                    <span>{playerSurvivalError}</span>
                                    <button
                                      type="button"
                                      onClick={() => loadPlayerSurvival(player.steam_id!)}
                                      className="rounded-lg border border-red-400/40 bg-red-500/10 px-3 py-1.5 text-xs text-red-200 hover:bg-red-500/20 transition"
                                    >
                                      {t('players.survival.retry')}
                                    </button>
                                  </div>
                                ) : playerSurvivalData ? (
                                  <div className="space-y-4">
                                    <div className="flex flex-wrap items-center justify-between gap-3 rounded-lg border border-white/10 bg-white/5 px-3 py-3 text-xs sm:text-sm text-white/70">
                                      <div className="flex flex-col gap-1">
                                        <span className="font-semibold text-white">
                                          {t('players.survival.snapshot', {
                                            date: formatSurvivalDate(playerSurvivalData.snapshotAt),
                                          })}
                                        </span>
                                      </div>
                                      <button
                                        type="button"
                                        onClick={() => loadPlayerSurvival(player.steam_id!)}
                                        className={`inline-flex items-center gap-2 rounded-lg border border-white/10 px-3 py-1.5 text-xs font-semibold transition ${
                                          survivalLoading.has(player.steam_id!)
                                            ? 'cursor-wait opacity-60'
                                            : 'hover:border-scum-panel/40 hover:bg-scum-panel/10'
                                        }`}
                                      >
                                        <RefreshCw
                                          size={14}
                                          className={
                                            survivalLoading.has(player.steam_id!)
                                              ? 'animate-spin text-scum-panel'
                                              : 'text-white/70'
                                          }
                                        />
                                        {t('players.survival.retry')}
                                      </button>
                                    </div>

                                    {(() => {
                                      const sections = [
                                        {
                                          title: t('players.survival.sections.combat'),
                                          keys: [
                                            'kills',
                                            'deaths',
                                            'deaths_by_prisoners',
                                            'players_knocked_out',
                                            'prisoner_kills',
                                            'shots_fired',
                                            'shots_hit',
                                            'accuracy_percent',
                                            'kdr',
                                            'headshots',
                                            'firearm_kills',
                                            'archery_kills',
                                            'bare_handed_kills',
                                            'melee_kills',
                                            'melee_weapon_hits',
                                            'melee_weapon_swings',
                                            'drone_kills',
                                            'sentry_kills',
                                            'longest_kill_distance',
                                            'longest_animal_kill_distance',
                                            'highest_damage_taken',
                                          ],
                                        },
                                        {
                                          title: t('players.survival.sections.hunting'),
                                          keys: [
                                            'animals_killed',
                                            'animals_skinned',
                                            'puppets_killed',
                                            'puppets_knocked_out',
                                            'bears_killed',
                                            'wolves_killed',
                                            'boars_killed',
                                            'goats_killed',
                                            'horses_killed',
                                            'donkeys_killed',
                                            'rabbits_killed',
                                            'chickens_killed',
                                            'crows_killed',
                                            'seagulls_killed',
                                            'deers_killed',
                                          ],
                                        },
                                        {
                                          title: t('players.survival.sections.survival'),
                                          keys: [
                                            'minutes_survived',
                                            'food_eaten',
                                            'liquid_drank',
                                            'alcohol_drank',
                                            'total_calories_intake',
                                            'mushrooms_eaten',
                                            'wounds_patched',
                                            'heart_attacks',
                                            'overdose',
                                            'teeth_lost',
                                            'diarrheas',
                                            'starvation',
                                            'vomits',
                                            'total_defecations',
                                            'total_urinations',
                                            'times_mauled_by_bear',
                                            'times_caught_by_shark',
                                            'times_escaped_shark_bite',
                                          ],
                                        },
                                        {
                                          title: t('players.survival.sections.mobility'),
                                          keys: [
                                            'distance_travelled_by_foot',
                                            'distance_travelled_in_vehicle',
                                            'distance_travelled_swimming',
                                            'distance_travel_by_boat',
                                            'distance_sailed',
                                          ],
                                        },
                                        {
                                          title: t('players.survival.sections.crafting'),
                                          keys: [
                                            'locks_picked',
                                            'arrows_crafted',
                                            'bullets_crafted',
                                            'guns_crafted',
                                            'melee_weapons_crafted',
                                            'clothing_crafted',
                                            'foliage_cut',
                                            'containers_looted',
                                            'items_picked_up',
                                            'items_put_into_containers',
                                            'doors_claimed',
                                            'lights_fired',
                                          ],
                                        },
                                        {
                                          title: t('players.survival.sections.progress'),
                                          keys: [
                                            'highest_positive_fame_points',
                                            'lowest_negative_fame_points',
                                            'highest_weight_carried',
                                            'highest_fat',
                                            'highest_muscle_mass',
                                            'last_fame_point_award_consecutive_days',
                                          ],
                                        },
                                      ];

                                      const getMetricValue = (key: string): number | null => {
                                        if (!playerSurvivalData) {
                                          return null;
                                        }
                                        if (key === 'kdr') {
                                          return playerSurvivalData.derived?.kdr ?? null;
                                        }
                                        if (key === 'accuracy_percent') {
                                          return playerSurvivalData.derived?.accuracy_percent ?? null;
                                        }
                                        return playerSurvivalData.metrics?.[key] ?? null;
                                      };

                                      const cards = sections
                                        .map(section => {
                                          const metricItems = section.keys
                                            .map(key => ({
                                              key,
                                              label: t(`players.survival.fields.${key}`),
                                              value: getMetricValue(key),
                                            }))
                                            .filter(item => item.value !== null && item.value !== undefined);
                                          return { ...section, metricItems };
                                        })
                                        .filter(section => section.metricItems.length > 0);

                                      if (!cards.length) {
                                        return (
                                          <div className="text-white/70 text-sm py-6 text-center">
                                            {t('players.survival.noData')}
                                          </div>
                                        );
                                      }

                                      return (
                                        <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
                                          {cards.map(section => (
                                            <div
                                              key={section.title}
                                              className="rounded-lg border border-white/10 bg-black/25 p-3 text-xs text-white/70"
                                            >
                                              <div className="mb-2 text-sm font-semibold text-white">
                                                {section.title}
                                              </div>
                                              <div className="divide-y divide-white/10">
                                                {section.metricItems.map(item => (
                                                  <div
                                                    key={item.key}
                                                    className="flex items-center justify-between gap-2 py-1"
                                                  >
                                                    <span className="text-white/50">{item.label}</span>
                                                    <span className="font-mono text-white/90">
                                                      {formatMetricValue(item.value)}
                                                    </span>
                                                  </div>
                                                ))}
                                              </div>
                                            </div>
                                          ))}
                                        </div>
                                      );
                                    })()}
                                  </div>
                                ) : (
                                  <div className="text-white/70 text-sm py-6 text-center">
                                    {t('players.survival.noData')}
                                  </div>
                                )}
                              </div>
                            )}
                          </td>
                        </tr>
                      );
                    })()}
                  </Fragment>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      ) : (
        <div className="text-white/70 text-sm py-4 text-center">
          {searchTerm.trim() 
            ? (t('players.search.noResults') ?? `No players found matching "${searchTerm}"`)
            : t('players.noPlayers')
          }
      </div>
      )}
        </>
      )}

      {mainTab === 'squads' && (
        <div className="space-y-4">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div className="text-sm text-white/70">
              {t('players.squads.total', { count: squadsTotal })}
            </div>
            <div className="text-xs text-white/50">
              {squadsSnapshotAt
                ? t('players.squads.syncedAt', { date: formatSurvivalDate(squadsSnapshotAt) })
                : t('players.squads.syncedUnknown')}
            </div>
          </div>

          {squadsLoading ? (
            <div className="grid gap-3">
              {Array.from({ length: 4 }).map((_, index) => (
                <div
                  key={index}
                  className="h-20 rounded-lg border border-white/10 bg-white/5 animate-pulse"
                />
              ))}
            </div>
          ) : squadsError ? (
            <div className="p-4 rounded-lg bg-red-500/10 border border-red-500/40 text-red-300 text-sm space-y-3">
              <div>{squadsError}</div>
              <button
                onClick={() => fetchSquads(true)}
                className="inline-flex items-center gap-2 px-3 py-1.5 text-xs rounded-md border border-red-500/60 text-red-200 hover:bg-red-500/20 transition-colors"
              >
                <RefreshCw size={14} />
                {t('players.squads.tryAgain')}
              </button>
            </div>
          ) : squads.length === 0 ? (
            <div className="text-center py-8 text-white/60">
              {t('players.squads.empty')}
            </div>
          ) : (
            <>
              {/* Tabela para telas médias e maiores */}
              <div className="hidden md:block overflow-x-auto -mx-4 px-4 sm:mx-0 sm:px-0">
                <div className="inline-block min-w-full align-middle">
                  <table className="min-w-full text-sm">
                    <thead>
                      <tr className="border-b border-white/10">
                        <th className="text-left py-2 px-2 text-white/60 font-medium whitespace-nowrap">
                          {t('players.squads.columns.rank')}
                        </th>
                        <th className="text-left py-2 px-2 text-white/60 font-medium whitespace-nowrap">
                          {t('players.squads.columns.squad')}
                        </th>
                        <th className="text-left py-2 px-2 text-white/60 font-medium whitespace-nowrap">
                          {t('players.squads.columns.score')}
                        </th>
                        <th className="text-left py-2 px-2 text-white/60 font-medium whitespace-nowrap">
                          {t('players.squads.columns.members')}
                        </th>
                        <th className="text-left py-2 px-2 text-white/60 font-medium whitespace-nowrap">
                          {t('players.squads.columns.vehicles')}
                        </th>
                        <th className="text-left py-2 px-2 text-white/60 font-medium whitespace-nowrap">
                          {t('players.squads.columns.flags')}
                        </th>
                      </tr>
                    </thead>
                    <tbody>
                      {paginatedSquads.map((squad) => {
                        const message = squad.message?.trim() || '';
                        const information = squad.information?.trim() || '';
                        const messageText = message || t('players.squads.placeholders.noMessage');
                        const isExpanded = expandedSquads.has(squad.squad_id);
                        const memberState = squadMembersState.get(squad.squad_id);
                        const members = memberState?.members ?? [];
                        const membersTotal = memberState?.total ?? 0;
                        const membersLoading = memberState?.loading ?? false;
                        const membersError = memberState?.error ?? null;
                        const membersHasMore = memberState?.hasMore ?? false;
                        const renderLimit = squadMembersRenderLimit.get(squad.squad_id) ?? Number.POSITIVE_INFINITY;
                        const activityText = squad.last_member_login_time
                          ? t('players.squads.activity.lastLogin', {
                              date: formatSurvivalDate(squad.last_member_login_time),
                            })
                          : squad.last_member_logout_time
                          ? t('players.squads.activity.lastLogout', {
                              date: formatSurvivalDate(squad.last_member_logout_time),
                            })
                          : t('players.squads.activity.noActivity');
                        const membersLabel = squad.member_limit
                          ? t('players.squads.memberCountLimited', {
                              count: squad.member_count,
                              limit: squad.member_limit,
                            })
                          : t('players.squads.memberCount', {
                              count: squad.member_count,
                            });
                        return (
                          <Fragment key={squad.squad_id}>
                            <tr className="border-b border-white/5 hover:bg-white/5">
                              <td className="py-3 px-2 text-white/70 font-mono">
                                {squad.rank_position ?? '—'}
                              </td>
                              <td className="py-3 px-2">
                                <button
                                  type="button"
                                  onClick={() => handleSquadToggle(squad)}
                                  aria-expanded={isExpanded}
                                  className="w-full rounded-md border border-transparent bg-transparent px-0 py-1 text-left text-sm font-semibold text-white transition hover:border-white/10 hover:bg-white/5 focus:outline-none focus-visible:ring-2 focus-visible:ring-scum-panel"
                                >
                                  {squad.name}
                                </button>
                              </td>
                              <td className="py-3 px-2 text-white/80">
                                {formatMetricValue(squad.score)}
                              </td>
                              <td className="py-3 px-2 text-white/80">
                                {membersLabel}
                              </td>
                              <td className="py-3 px-2 text-white/80">
                                {squad.squad_total_vehicles ?? 0}
                              </td>
                              <td className="py-3 px-2 text-white/80">
                                {squad.flag_count ?? 0}
                              </td>
                            </tr>
                            {isExpanded && (
                              <tr className="border-b border-white/10 bg-black/20">
                                <td colSpan={6} className="px-3 py-4">
                                  <div className="space-y-4">
                                    <div className="space-y-2">
                                      <div className="text-xs uppercase text-white/50">
                                        {t('players.squads.columns.message')}
                                      </div>
                                      <div className="text-sm text-white/80 whitespace-pre-wrap break-words">
                                        {messageText}
                                      </div>
                                      {information && (
                                        <div className="text-xs text-white/50 whitespace-pre-wrap break-words">
                                          {information}
                                        </div>
                                      )}
                                    </div>

                                    {squad.flag_ids && (
                                      <div className="space-y-2">
                                        <div className="text-xs uppercase text-white/50">
                                          {t('players.squads.flags.title')}
                                        </div>
                                        <div className="flex flex-wrap gap-2">
                                          {squad.flag_ids
                                            .split(',')
                                            .map((id) => id.trim())
                                            .filter((id) => id.length > 0)
                                            .map((flagId) => (
                                              <span
                                                key={flagId}
                                                className="inline-flex items-center rounded-md border border-white/20 bg-white/5 px-2.5 py-1 text-xs font-mono text-white/80"
                                              >
                                                {flagId}
                                              </span>
                                            ))}
                                        </div>
                                        {squad.flag_count !== null && (
                                          <div className="text-xs text-white/60">
                                            {t('players.squads.flags.total', { count: squad.flag_count })}
                                          </div>
                                        )}
                                      </div>
                                    )}

                                    <div className="space-y-3">
                                      <div className="flex items-center justify-between text-xs text-white/60">
                                        <span>
                                          {membersTotal > 0
                                            ? t('players.squads.members.summary', { count: membersTotal })
                                            : t('players.squads.members.summaryZero')}
                                        </span>
                                        {membersLoading && <Loader2 size={16} className="animate-spin" />}
                                      </div>

                                      {membersLoading && members.length === 0 ? (
                                        <div className="flex items-center justify-center gap-2 rounded-md border border-white/10 bg-black/30 p-4 text-sm text-white/60">
                                          <Loader2 size={16} className="animate-spin" />
                                          <span>{t('players.squads.members.loading')}</span>
                                        </div>
                                      ) : membersError ? (
                                        <div className="rounded-md border border-red-500/30 bg-red-500/10 p-3 text-sm text-red-200">
                                          {membersError}
                                        </div>
                                      ) : members.length === 0 ? (
                                        <div className="rounded-md border border-white/10 bg-black/30 p-3 text-sm text-white/60">
                                          {t('players.squads.members.empty')}
                                        </div>
                                      ) : (
                                        <div className="space-y-2">
                                          {members.slice(0, renderLimit).map((member) => (
                                            <div
                                              key={member.snapshot_member_id}
                                              className="rounded-lg border border-white/10 bg-black/30 p-3 text-xs text-white/70"
                                            >
                                              <div className="flex flex-wrap items-center justify-between gap-2">
                                                <div>
                                                  <div className="text-sm font-semibold text-white">
                                                    {member.name || t('players.squads.members.nameUnknown')}
                                                  </div>
                                                  <div className="text-white/40">
                                                    {member.steam_id || t('players.squads.members.steamUnknown')}
                                                  </div>
                                                </div>
                                                <div className="rounded-full border border-white/15 px-3 py-1 text-white/70">
                                                  {member.rank !== null && member.rank !== undefined
                                                    ? member.rank
                                                    : t('players.squads.members.rankUnknown')}
                                                </div>
                                              </div>

                                              <div className="mt-3 grid gap-2 text-white/60 sm:grid-cols-2">
                                                <div>
                                                  <span className="text-white/40">
                                                    {t('players.squads.members.fame')}:{' '}
                                                  </span>
                                                  <span>{formatMetricValue(member.fame_points)}</span>
                                                </div>
                                                <div>
                                                  <span className="text-white/40">
                                                    {t('players.squads.members.playtime')}:{' '}
                                                  </span>
                                                  <span>{formatPlayTime(member.play_time)}</span>
                                                </div>
                                                <div>
                                                  <span className="text-white/40">
                                                    {t('players.squads.members.lastLogin')}:{' '}
                                                  </span>
                                                  <span>{formatSurvivalDate(member.last_login_time)}</span>
                                                </div>
                                                <div>
                                                  <span className="text-white/40">
                                                    {t('players.squads.members.lastLogout')}:{' '}
                                                  </span>
                                                  <span>{formatSurvivalDate(member.last_logout_time)}</span>
                                                </div>
                                              </div>
                                            </div>
                                          ))}

                                          {membersHasMore && (
                                            <button
                                              type="button"
                                              onClick={() => handleLoadMoreSquadMembers(squad.squad_id)}
                                              disabled={membersLoading}
                                              className="flex w-full items-center justify-center gap-2 rounded-lg border border-white/20 px-4 py-2 text-sm font-medium text-white transition hover:border-white/40 hover:bg-white/10 disabled:cursor-not-allowed disabled:opacity-60"
                                            >
                                              {membersLoading && <Loader2 size={16} className="animate-spin" />}
                                              <span>{t('players.squads.members.loadMore')}</span>
                                            </button>
                                          )}
                                        </div>
                                      )}
                                    </div>
                                  </div>
                                </td>
                              </tr>
                            )}
                          </Fragment>
                        );
                      })}
                    </tbody>
                  </table>
                </div>
              </div>

              {/* Cards empilhados para mobile */}
              <div className="grid gap-3 md:hidden">
                {paginatedSquads.map((squad) => {
                  const message = squad.message?.trim() || '';
                  const information = squad.information?.trim() || '';
                  const messageText = message || t('players.squads.placeholders.noMessage');
                  const isExpanded = expandedSquads.has(squad.squad_id);
                  const memberState = squadMembersState.get(squad.squad_id);
                  const members = memberState?.members ?? [];
                  const membersTotal = memberState?.total ?? 0;
                  const membersLoading = memberState?.loading ?? false;
                  const membersError = memberState?.error ?? null;
                  const membersHasMore = memberState?.hasMore ?? false;
                  const renderLimit = squadMembersRenderLimit.get(squad.squad_id) ?? Number.POSITIVE_INFINITY;
                  const membersLabel = squad.member_limit
                    ? t('players.squads.memberCountLimited', {
                        count: squad.member_count,
                        limit: squad.member_limit,
                      })
                    : t('players.squads.memberCount', {
                        count: squad.member_count,
                      });
                  const vehiclesLabel = t('players.squads.columns.vehicles');
                  const flagsLabel = t('players.squads.columns.flags');

                  return (
                    <div
                      key={`card-${squad.squad_id}`}
                      className="rounded-lg border border-white/10 bg-black/30 p-3 text-sm text-white/80"
                    >
                      <button
                        type="button"
                        onClick={() => handleSquadToggle(squad)}
                        aria-expanded={isExpanded}
                        className="w-full text-left text-base font-semibold text-white transition hover:text-white/90 focus:outline-none focus-visible:ring-2 focus-visible:ring-scum-panel"
                      >
                        {squad.name}
                      </button>

                      <div className="mt-1 text-xs text-white/60">
                        <span>{membersLabel}</span>
                        <span className="mx-2 text-white/40">•</span>
                        <span>{vehiclesLabel}: {squad.squad_total_vehicles ?? 0}</span>
                        <span className="mx-2 text-white/40">•</span>
                        <span>{flagsLabel}: {squad.flag_count ?? 0}</span>
                      </div>

                      {isExpanded && (
                        <div className="mt-3 space-y-3 text-xs">
                          <div>
                            <div className="text-white/50 uppercase">
                              {t('players.squads.columns.message')}
                            </div>
                            <div className="text-white/80 whitespace-pre-wrap break-words">
                              {messageText}
                            </div>
                          </div>

                          {information && (
                            <div>
                              <div className="text-white/50 uppercase">
                                {t('players.squads.columns.information')}
                              </div>
                              <div className="text-white/60 whitespace-pre-wrap break-words">
                                {information}
                              </div>
                            </div>
                          )}

                          {squad.flag_ids && (
                            <div>
                              <div className="text-white/50 uppercase">
                                {t('players.squads.flags.title')}
                              </div>
                              <div className="mt-2 flex flex-wrap gap-2">
                                {squad.flag_ids
                                  .split(',')
                                  .map((id) => id.trim())
                                  .filter((id) => id.length > 0)
                                  .map((flagId) => (
                                    <span
                                      key={flagId}
                                      className="inline-flex items-center rounded-md border border-white/20 bg-white/5 px-2 py-1 text-xs font-mono text-white/80"
                                    >
                                      {flagId}
                                    </span>
                                  ))}
                              </div>
                              {squad.flag_count !== null && (
                                <div className="mt-1 text-xs text-white/60">
                                  {t('players.squads.flags.total', { count: squad.flag_count })}
                                </div>
                              )}
                            </div>
                          )}

                          <div className="flex items-center justify-between text-white/60">
                            <span>
                              {membersTotal > 0
                                ? t('players.squads.members.summary', { count: membersTotal })
                                : t('players.squads.members.summaryZero')}
                            </span>
                            {membersLoading && <Loader2 size={14} className="animate-spin" />}
                          </div>

                          {membersLoading && members.length === 0 ? (
                            <div className="flex items-center justify-center gap-2 rounded-md border border-white/10 bg-black/40 p-3 text-white/60">
                              <Loader2 size={14} className="animate-spin" />
                              <span>{t('players.squads.members.loading')}</span>
                            </div>
                          ) : membersError ? (
                            <div className="rounded-md border border-red-500/40 bg-red-500/10 p-3 text-red-200">
                              {membersError}
                            </div>
                          ) : members.length === 0 ? (
                            <div className="rounded-md border border-white/10 bg-black/40 p-3 text-white/60">
                              {t('players.squads.members.empty')}
                            </div>
                          ) : (
                            <div className="space-y-2">
                              {members.slice(0, renderLimit).map((member) => (
                                <div
                                  key={member.snapshot_member_id}
                                  className="rounded-lg border border-white/10 bg-black/40 p-3 text-white/70"
                                >
                                  <div className="font-semibold text-white">
                                    {member.name || t('players.squads.members.nameUnknown')}
                                  </div>
                                  <div className="text-white/40">
                                    {member.steam_id || t('players.squads.members.steamUnknown')}
                                  </div>

                                  <div className="mt-2 grid gap-2">
                                    <div>
                                      <span className="text-white/40">
                                        {t('players.squads.members.rank')}:{' '}
                                      </span>
                                      <span>
                                        {member.rank !== null && member.rank !== undefined
                                          ? member.rank
                                          : t('players.squads.members.rankUnknown')}
                                      </span>
                                    </div>
                                    <div>
                                      <span className="text-white/40">
                                        {t('players.squads.members.fame')}:{' '}
                                      </span>
                                      <span>{formatMetricValue(member.fame_points)}</span>
                                    </div>
                                    <div>
                                      <span className="text-white/40">
                                        {t('players.squads.members.playtime')}:{' '}
                                      </span>
                                      <span>{formatPlayTime(member.play_time)}</span>
                                    </div>
                                    <div>
                                      <span className="text-white/40">
                                        {t('players.squads.members.lastLogin')}:{' '}
                                      </span>
                                      <span>{formatSurvivalDate(member.last_login_time)}</span>
                                    </div>
                                    <div>
                                      <span className="text-white/40">
                                        {t('players.squads.members.lastLogout')}:{' '}
                                      </span>
                                      <span>{formatSurvivalDate(member.last_logout_time)}</span>
                                    </div>
                                  </div>
                                </div>
                              ))}

                              {membersHasMore && (
                                <button
                                  type="button"
                                  onClick={() => handleLoadMoreSquadMembers(squad.squad_id)}
                                  disabled={membersLoading}
                                  className="flex w-full items-center justify-center gap-2 rounded-lg border border-white/20 px-4 py-2 text-sm font-medium text-white transition hover:border-white/35 hover:bg-white/10 disabled:cursor-not-allowed disabled:opacity-60"
                                >
                                  {membersLoading && <Loader2 size={16} className="animate-spin" />}
                                  <span>{t('players.squads.members.loadMore')}</span>
                                </button>
                              )}
                            </div>
                          )}
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>

              {/* Paginação Squads */}
              <div className="mt-4 flex flex-wrap items-center justify-between gap-3 border-t border-white/10 pt-3 text-xs text-white/60">
                <div>
                  {t('players.pagination.showing', {
                    start: squadsRangeStart,
                    end: squadsRangeEnd,
                    total: squads.length,
                  })}
                </div>
                <div className="flex items-center gap-2">
                  <button
                    type="button"
                    onClick={() => setSquadsPage((prev) => Math.max(1, prev - 1))}
                    disabled={squads.length === 0 || squadsPageClamped === 1}
                    className="rounded-md border border-white/20 px-3 py-1 text-white/70 transition hover:border-white/40 hover:text-white disabled:cursor-not-allowed disabled:opacity-50"
                  >
                    {t('players.pagination.prev')}
                  </button>
                  <div className="text-white/60">
                    {t('players.pagination.page', { page: squads.length === 0 ? 0 : squadsPageClamped })}
                  </div>
                  <button
                    type="button"
                    onClick={() => setSquadsPage((prev) => Math.min(squadsMaxPage, prev + 1))}
                    disabled={squads.length === 0 || squadsPageClamped >= squadsMaxPage}
                    className="rounded-md border border-white/20 px-3 py-1 text-white/70 transition hover:border-white/40 hover:text-white disabled:cursor-not-allowed disabled:opacity-50"
                  >
                    {t('players.pagination.next')}
                  </button>
                  <select
                    value={squadsPageSize}
                    onChange={(e) => {
                      const nextSize = Number(e.target.value);
                      setSquadsPageSize(nextSize);
                      setSquadsPage(1);
                    }}
                    className="rounded-md border border-white/20 bg-black/40 px-2 py-1 text-white/70 focus:outline-none focus:ring-2 focus:ring-scum-panel"
                    disabled={squads.length === 0}
                  >
                    {[10, 25, 50, 100].map((size) => (
                      <option key={size} value={size}>
                        {t('players.pagination.perPage', { count: size })}
                      </option>
                    ))}
                  </select>
                </div>
              </div>
            </>
          )}
        </div>
      )}

      {mainTab === 'admin-logs' && (
        /* Tab: Admin Logs */
        <div className="space-y-4">
          {/* Header com controles */}
          <div className="flex flex-wrap items-center justify-between gap-4">
            <div className="text-sm text-white/60">
              {t('adminLogs.total')}: <span className="text-white font-semibold">{adminLogsTotal ?? '-'}</span>
            </div>
            <div className="flex flex-wrap items-center gap-3">
              <div className="relative">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-white/40" size={16} />
                <input
                  type="text"
                  value={adminLogsSearch}
                  onChange={(e) => setAdminLogsSearch(e.target.value)}
                  placeholder={t('adminLogs.searchPlaceholder') ?? 'Filtrar por comando, admin ou Steam ID'}
                  className="pl-9 pr-3 py-1.5 bg-black/30 border border-white/10 rounded-lg text-sm text-white placeholder:text-white/40 focus:outline-none focus:ring-2 focus:ring-scum-panel focus:border-transparent"
                />
              </div>
              <div className="flex items-center gap-2">
                <label className="text-sm text-white/70">{t('adminLogs.limit')}:</label>
                <select
                  value={adminLogsLimit}
                  onChange={(e) => {
                    const newLimit = parseInt(e.target.value);
                    if (newLimit > 0 && newLimit <= 100) {
                      setAdminLogsLimit(newLimit);
                    }
                  }}
                  className="px-3 py-1.5 bg-black/50 border border-white/10 rounded-lg text-white text-sm focus:outline-none focus:ring-2 focus:ring-scum-panel"
                >
                  <option value={10}>10</option>
                  <option value={20}>20</option>
                  <option value={50}>50</option>
                  <option value={100}>100</option>
                </select>
              </div>
            </div>
          </div>

          {/* Filtros por categoria */}
          <div className="flex flex-wrap gap-2">
            <button
              onClick={() => setAdminLogsCategoryFilter('all')}
              className={`px-3 py-1.5 text-xs rounded-lg border transition-colors ${
                adminLogsCategoryFilter === 'all'
                  ? 'bg-scum-panel border-scum-panel text-white'
                  : 'bg-black/30 border-white/10 text-white/70 hover:border-white/20'
              }`}
            >
              {t('adminLogs.filters.all')}
            </button>
            <button
              onClick={() => setAdminLogsCategoryFilter('teleport')}
              className={`px-3 py-1.5 text-xs rounded-lg border transition-colors ${
                adminLogsCategoryFilter === 'teleport'
                  ? 'bg-purple-500/20 border-purple-500 text-white'
                  : 'bg-black/30 border-white/10 text-white/70 hover:border-white/20'
              }`}
            >
              🚀 {t('adminLogs.filters.teleport')} ({adminLogsCategoryCounts.teleport ?? 0})
            </button>
            <button
              onClick={() => setAdminLogsCategoryFilter('spawn')}
              className={`px-3 py-1.5 text-xs rounded-lg border transition-colors ${
                adminLogsCategoryFilter === 'spawn'
                  ? 'bg-yellow-500/20 border-yellow-500 text-white'
                  : 'bg-black/30 border-white/10 text-white/70 hover:border-white/20'
              }`}
            >
              🎁 {t('adminLogs.filters.spawnItem')} ({adminLogsCategoryCounts.spawn ?? 0})
            </button>
            <button
              onClick={() => setAdminLogsCategoryFilter('godmode')}
              className={`px-3 py-1.5 text-xs rounded-lg border transition-colors ${
                adminLogsCategoryFilter === 'godmode'
                  ? 'bg-red-500/20 border-red-500 text-white'
                  : 'bg-black/30 border-white/10 text-white/70 hover:border-white/20'
              }`}
            >
              🛡️ {t('adminLogs.filters.godMode')} ({adminLogsCategoryCounts.godmode ?? 0})
            </button>
            <button
              onClick={() => setAdminLogsCategoryFilter('info')}
              className={`px-3 py-1.5 text-xs rounded-lg border transition-colors ${
                adminLogsCategoryFilter === 'info'
                  ? 'bg-blue-500/20 border-blue-500 text-white'
                  : 'bg-black/30 border-white/10 text-white/70 hover:border-white/20'
              }`}
            >
              👁️ {t('adminLogs.filters.playerInfo')} ({adminLogsCategoryCounts.info ?? 0})
            </button>
            <button
              onClick={() => setAdminLogsCategoryFilter('punishments')}
              className={`px-3 py-1.5 text-xs rounded-lg border transition-colors ${
                adminLogsCategoryFilter === 'punishments'
                  ? 'bg-orange-500/20 border-orange-500 text-white'
                  : 'bg-black/30 border-white/10 text-white/70 hover:border-white/20'
              }`}
              style={adminLogsStatsLoading ? { opacity: 0.85 } : undefined}
            >
              🔨 {t('adminLogs.filters.punishments') ?? 'Punishments'} ({adminLogsCategoryCounts.punishments ?? 0})
            </button>
            <button
              onClick={() => setAdminLogsCategoryFilter('other')}
              className={`px-3 py-1.5 text-xs rounded-lg border transition-colors ${
                adminLogsCategoryFilter === 'other'
                  ? 'bg-gray-500/20 border-gray-500 text-white'
                  : 'bg-black/30 border-white/10 text-white/70 hover:border-white/20'
              }`}
              style={adminLogsStatsLoading ? { opacity: 0.85 } : undefined}
            >
              📋 {t('adminLogs.filters.others') ?? 'Other'} ({adminLogsCategoryCounts.other ?? 0})
            </button>
          </div>

          {/* Loading */}
          {adminLogsLoading && adminLogs.length === 0 ? (
            <div className="text-center py-8 text-white/50">
              <Loader2 size={24} className="animate-spin mx-auto mb-2" />
              <div>{t('adminLogs.loading')}</div>
            </div>
          ) : adminLogsError ? (
            <div className="text-center py-8 text-red-400">
              {adminLogsError}
            </div>
          ) : adminLogs.length > 0 ? (
            /* Lista de comandos */
            <div className="space-y-3">
              {adminLogs.map((cmd) => (
                <div
                  key={cmd.command_id}
                  className="p-4 rounded-lg bg-black/30 border border-white/5 hover:bg-black/40 transition-colors"
                  style={{ borderLeftColor: cmd.category.color, borderLeftWidth: '4px' }}
                >
                  <div className="flex items-start justify-between mb-3">
                    <div className="flex items-center gap-2">
                      <span className="text-xl">{cmd.category.emoji}</span>
                      <span className="font-semibold text-white">{cmd.category.name}</span>
                    </div>
                    <span className="text-xs text-white/50">{formatDateTime(cmd.timestamp)}</span>
                  </div>
                  <div className="space-y-1">
                    <div className="text-sm">
                      <span className="text-white/60">{t('adminLogs.admin')}: </span>
                      <span className="text-white font-medium">{cmd.player_name}</span>
                      <span className="text-white/40 text-xs ml-2">({cmd.steam_id})</span>
                    </div>
                    <div className="text-sm">
                      <span className="text-white/60">{t('adminLogs.command')}: </span>
                      <span className="font-mono text-white/90 bg-black/50 px-2 py-1 rounded">{cmd.action}</span>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="text-center py-8 text-white/50">
              {t('adminLogs.empty')}
            </div>
          )}
        </div>
      )}

      {mainTab === 'ranking' && (
        <div className="space-y-4">
          {/* Busca e Controles */}
          <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
            <div className="relative flex-1 w-full sm:min-w-[200px]">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-white/40" size={16} />
              <input
                type="text"
                value={rankingsSearch}
                onChange={(e) => {
                  setRankingsSearch(e.target.value);
                  setRankingsPage(1);
                }}
                onKeyDown={(e) => {
                  if (e.key === 'Enter') {
                    fetchRankings();
                  }
                }}
                placeholder={t('players.rankings.searchPlaceholder') ?? 'Buscar por nome do jogador...'}
                className="w-full pl-9 pr-3 py-2 bg-black/30 border border-white/10 rounded-lg text-sm text-white placeholder:text-white/40 focus:outline-none focus:ring-2 focus:ring-scum-panel focus:border-transparent"
              />
            </div>
            <div className="flex items-center gap-2 flex-shrink-0 flex-wrap">
              {/* Botão de Colunas */}
              <div className="relative">
                <button
                  onClick={() => setShowColumnSelector(!showColumnSelector)}
                  className="flex items-center gap-1.5 px-2 sm:px-3 py-1.5 bg-black/50 border border-white/10 rounded-lg text-white text-xs sm:text-sm hover:bg-white/10 transition-colors"
                >
                  <Settings size={14} />
                  <span className="hidden sm:inline">{t('players.rankings.columnsLabel') ?? 'Colunas'}</span>
                  <span className="sm:hidden">{t('players.rankings.columnsShort') ?? 'Col.'}</span>
                  {visibleColumns.size > 8 && (
                    <span className="px-1.5 py-0.5 bg-scum-panel text-white text-xs rounded-full">
                      {visibleColumns.size}
                    </span>
                  )}
                </button>

                {/* Painel de Seleção de Colunas */}
                {showColumnSelector && (
                  <>
                    {/* Overlay para fechar ao clicar fora */}
                    <div
                      className="fixed inset-0 z-40 bg-black/50 sm:bg-transparent"
                      onClick={() => setShowColumnSelector(false)}
                    />
                    {/* Painel - Mobile: drawer da direita, Desktop: dropdown */}
                    <div className="fixed sm:absolute right-0 top-0 sm:top-full sm:mt-2 z-50 w-full sm:w-80 md:w-96 h-auto max-h-[85vh] sm:max-h-[70vh] bg-black/95 sm:bg-black/95 border-0 sm:border sm:border-white/20 rounded-none sm:rounded-lg shadow-xl flex flex-col">
                      {/* Header fixo */}
                      <div className="flex items-center justify-between p-4 pb-4 border-b border-white/10 flex-shrink-0">
                        <h3 className="text-base sm:text-sm font-semibold text-white">
                          {t('players.rankings.selectColumns') ?? 'Selecionar Colunas'}
                        </h3>
                        <button
                          onClick={() => setShowColumnSelector(false)}
                          className="p-1 text-white/60 hover:text-white hover:bg-white/10 rounded transition-colors"
                        >
                          <X size={20} />
                        </button>
                      </div>
                      
                      {/* Conteúdo scrollável */}
                      <div className="flex-1 overflow-y-auto p-4 pt-4 min-h-0">

                      {/* Colunas Fixas (sempre visíveis) */}
                      <div className="mb-4">
                        <div className="text-xs text-white/50 mb-2 uppercase">
                          {t('players.rankings.categories.fixed') ?? 'Fixas'}
                        </div>
                        <div className="space-y-1">
                          {RANKING_COLUMNS.fixed.map(col => (
                            <label key={col.key} className="flex items-center gap-2 text-sm text-white/80 cursor-pointer hover:text-white">
                              <CheckSquare size={16} className="text-green-400" />
                              <span>{t(`players.rankings.columns.${col.label}`) ?? col.label}</span>
                            </label>
                          ))}
                        </div>
                      </div>

                      {/* Colunas Principais */}
                      <div className="mb-4">
                        <div className="flex items-center justify-between mb-2">
                          <div className="text-xs text-white/50 uppercase">
                            {t('players.rankings.categories.main') ?? 'Principais'}
                          </div>
                          <button
                            onClick={() => {
                              const allMain = RANKING_COLUMNS.main.every(c => visibleColumns.has(c.key));
                              const newCols = new Set(visibleColumns);
                              if (allMain) {
                                RANKING_COLUMNS.main.forEach(c => newCols.delete(c.key));
                              } else {
                                RANKING_COLUMNS.main.forEach(c => newCols.add(c.key));
                              }
                              updateVisibleColumns(newCols);
                            }}
                            className="text-xs text-white/60 hover:text-white"
                          >
                            {t('players.rankings.toggleAll') ?? 'Todos'}
                          </button>
                        </div>
                        <div className="space-y-1">
                          {RANKING_COLUMNS.main.map(col => (
                            <label key={col.key} className="flex items-center gap-2 text-sm text-white/80 cursor-pointer hover:text-white">
                              <input
                                type="checkbox"
                                checked={visibleColumns.has(col.key)}
                                onChange={(e) => {
                                  const newCols = new Set(visibleColumns);
                                  if (e.target.checked) {
                                    newCols.add(col.key);
                                  } else {
                                    newCols.delete(col.key);
                                  }
                                  updateVisibleColumns(newCols);
                                }}
                                className="sr-only"
                              />
                              {visibleColumns.has(col.key) ? (
                                <CheckSquare size={16} className="text-green-400" />
                              ) : (
                                <Square size={16} className="text-white/40" />
                              )}
                              <span>{t(`players.rankings.columns.${col.label}`) ?? col.label}</span>
                            </label>
                          ))}
                        </div>
                      </div>

                      {/* Combat Stats */}
                      <div className="mb-4">
                        <div className="flex items-center justify-between mb-2">
                          <div className="text-xs text-white/50 uppercase">
                            {t('players.rankings.categories.combat') ?? 'Combat'}
                          </div>
                          <button
                            onClick={() => {
                              const allCombat = RANKING_COLUMNS.combat.every(c => visibleColumns.has(c.key));
                              const newCols = new Set(visibleColumns);
                              if (allCombat) {
                                RANKING_COLUMNS.combat.forEach(c => newCols.delete(c.key));
                              } else {
                                RANKING_COLUMNS.combat.forEach(c => newCols.add(c.key));
                              }
                              updateVisibleColumns(newCols);
                            }}
                            className="text-xs text-white/60 hover:text-white"
                          >
                            {t('players.rankings.toggleAll') ?? 'Todos'}
                          </button>
                        </div>
                        <div className="space-y-1">
                          {RANKING_COLUMNS.combat.map(col => (
                            <label key={col.key} className="flex items-center gap-2 text-sm text-white/80 cursor-pointer hover:text-white">
                              <input
                                type="checkbox"
                                checked={visibleColumns.has(col.key)}
                                onChange={(e) => {
                                  const newCols = new Set(visibleColumns);
                                  if (e.target.checked) {
                                    newCols.add(col.key);
                                  } else {
                                    newCols.delete(col.key);
                                  }
                                  updateVisibleColumns(newCols);
                                }}
                                className="sr-only"
                              />
                              {visibleColumns.has(col.key) ? (
                                <CheckSquare size={16} className="text-green-400" />
                              ) : (
                                <Square size={16} className="text-white/40" />
                              )}
                              <span>{t(`players.rankings.columns.${col.label}`) ?? col.label}</span>
                            </label>
                          ))}
                        </div>
                      </div>

                      {/* Survival Stats */}
                      <div className="mb-4">
                        <div className="flex items-center justify-between mb-2">
                          <div className="text-xs text-white/50 uppercase">
                            {t('players.rankings.categories.survival') ?? 'Survival'}
                          </div>
                          <button
                            onClick={() => {
                              const allSurvival = RANKING_COLUMNS.survival.every(c => visibleColumns.has(c.key));
                              const newCols = new Set(visibleColumns);
                              if (allSurvival) {
                                RANKING_COLUMNS.survival.forEach(c => newCols.delete(c.key));
                              } else {
                                RANKING_COLUMNS.survival.forEach(c => newCols.add(c.key));
                              }
                              updateVisibleColumns(newCols);
                            }}
                            className="text-xs text-white/60 hover:text-white"
                          >
                            {t('players.rankings.toggleAll') ?? 'Todos'}
                          </button>
                        </div>
                        <div className="space-y-1">
                          {RANKING_COLUMNS.survival.map(col => (
                            <label key={col.key} className="flex items-center gap-2 text-sm text-white/80 cursor-pointer hover:text-white">
                              <input
                                type="checkbox"
                                checked={visibleColumns.has(col.key)}
                                onChange={(e) => {
                                  const newCols = new Set(visibleColumns);
                                  if (e.target.checked) {
                                    newCols.add(col.key);
                                  } else {
                                    newCols.delete(col.key);
                                  }
                                  updateVisibleColumns(newCols);
                                }}
                                className="sr-only"
                              />
                              {visibleColumns.has(col.key) ? (
                                <CheckSquare size={16} className="text-green-400" />
                              ) : (
                                <Square size={16} className="text-white/40" />
                              )}
                              <span>{t(`players.rankings.columns.${col.label}`) ?? col.label}</span>
                            </label>
                          ))}
                        </div>
                      </div>

                      {/* Lockpicking Stats */}
                      <div className="mb-4">
                        <div className="flex items-center justify-between mb-2">
                          <div className="text-xs text-white/50 uppercase">
                            {t('players.rankings.categories.lockpicking') ?? 'Lockpicking'}
                          </div>
                          <button
                            onClick={() => {
                              const allLockpicking = RANKING_COLUMNS.lockpicking.every(c => visibleColumns.has(c.key));
                              const newCols = new Set(visibleColumns);
                              if (allLockpicking) {
                                RANKING_COLUMNS.lockpicking.forEach(c => newCols.delete(c.key));
                              } else {
                                RANKING_COLUMNS.lockpicking.forEach(c => newCols.add(c.key));
                              }
                              updateVisibleColumns(newCols);
                            }}
                            className="text-xs text-white/60 hover:text-white"
                          >
                            {t('players.rankings.toggleAll') ?? 'Todos'}
                          </button>
                        </div>
                        <div className="space-y-1">
                          {RANKING_COLUMNS.lockpicking.map(col => (
                            <label key={col.key} className="flex items-center gap-2 text-sm text-white/80 cursor-pointer hover:text-white">
                              <input
                                type="checkbox"
                                checked={visibleColumns.has(col.key)}
                                onChange={(e) => {
                                  const newCols = new Set(visibleColumns);
                                  if (e.target.checked) {
                                    newCols.add(col.key);
                                  } else {
                                    newCols.delete(col.key);
                                  }
                                  updateVisibleColumns(newCols);
                                }}
                                className="sr-only"
                              />
                              {visibleColumns.has(col.key) ? (
                                <CheckSquare size={16} className="text-green-400" />
                              ) : (
                                <Square size={16} className="text-white/40" />
                              )}
                              <span>{t(`players.rankings.columns.${col.label}`) ?? col.label}</span>
                            </label>
                          ))}
                        </div>
                      </div>

                      </div>
                      
                      {/* Botões de ação fixos no final */}
                      <div className="flex gap-2 p-4 pt-3 border-t border-white/10 flex-shrink-0">
                        <button
                          onClick={() => {
                            const allCols = new Set<string>();
                            Object.values(RANKING_COLUMNS).flat().forEach(col => allCols.add(col.key));
                            updateVisibleColumns(allCols);
                          }}
                          className="flex-1 px-3 py-1.5 text-xs bg-white/10 border border-white/20 rounded text-white hover:bg-white/20 transition-colors"
                        >
                          {t('players.rankings.selectAll') ?? 'Selecionar Tudo'}
                        </button>
                        <button
                          onClick={() => {
                            const defaultCols = new Set(['rank', 'player', 'kills', 'deaths', 'kdr', 'total_fame', 'minutes_survived', 'longest_shot']);
                            updateVisibleColumns(defaultCols);
                          }}
                          className="flex-1 px-3 py-1.5 text-xs bg-white/10 border border-white/20 rounded text-white hover:bg-white/20 transition-colors"
                        >
                          {t('players.rankings.reset') ?? 'Resetar'}
                        </button>
                      </div>
                    </div>
                  </>
                )}
              </div>

              <div className="flex items-center gap-2 flex-shrink-0">
                <label className="text-xs sm:text-sm text-white/70 whitespace-nowrap">{t('players.rankings.itemsPerPage') ?? 'Itens por página'}:</label>
                <select
                  value={rankingsPageSize}
                  onChange={(e) => {
                    setRankingsPageSize(Number(e.target.value));
                    setRankingsPage(1);
                  }}
                  className="px-2 sm:px-3 py-1.5 bg-black/50 border border-white/10 rounded-lg text-white text-xs sm:text-sm focus:outline-none focus:ring-2 focus:ring-scum-panel"
                >
                  <option value={25}>25</option>
                  <option value={50}>50</option>
                  <option value={100}>100</option>
                  <option value={200}>200</option>
                </select>
              </div>
            </div>
          </div>

          {/* Loading */}
          {rankingsLoading && rankingsData.length === 0 ? (
            <div className="text-center py-8 text-white/50">
              <Loader2 size={24} className="animate-spin mx-auto mb-2" />
              <div>{t('players.rankings.loading') ?? 'Carregando rankings...'}</div>
            </div>
          ) : rankingsError ? (
            <div className="p-4 rounded-lg bg-red-500/10 border border-red-500/40 text-red-300 text-sm space-y-3">
              <div>{rankingsError}</div>
              <button
                onClick={fetchRankings}
                className="inline-flex items-center gap-2 px-3 py-1.5 text-xs rounded-md border border-red-500/60 text-red-200 hover:bg-red-500/20 transition-colors"
              >
                <RefreshCw size={14} />
                {t('players.rankings.tryAgain') ?? 'Tentar novamente'}
              </button>
            </div>
          ) : rankingsData.length === 0 ? (
            <div className="text-center py-8 text-white/60">
              {t('players.rankings.empty') ?? 'Nenhum ranking encontrado'}
            </div>
          ) : (
            <>
              {/* Tabela de Rankings para desktop */}
              <div className="hidden md:block overflow-x-auto -mx-4 px-4 sm:mx-0 sm:px-0" style={{ WebkitOverflowScrolling: 'touch' }}>
                <div className="inline-block min-w-full align-middle">
                  <table className="min-w-full text-sm">
                    <thead>
                      <tr className="border-b border-white/10">
                        {/* Renderizar colunas fixas */}
                        {visibleColumns.has('rank') && (
                          <th className="text-left py-2 px-2 text-white/70 font-medium whitespace-nowrap">
                            {t('players.rankings.columns.rank') ?? 'Rank'}
                          </th>
                        )}
                        {visibleColumns.has('player') && (
                          <th className="text-left py-2 px-2 text-white/70 font-medium whitespace-nowrap">
                            {t('players.rankings.columns.player') ?? 'Player'}
                          </th>
                        )}
                        
                        {/* Renderizar colunas principais e adicionais dinamicamente */}
                        {[...RANKING_COLUMNS.main, ...RANKING_COLUMNS.combat, ...RANKING_COLUMNS.survival, ...RANKING_COLUMNS.lockpicking].map(col => {
                          if (!visibleColumns.has(col.key)) return null;
                          
                          const isActive = rankingsSortBy === col.key || 
                            (col.key === 'total_fame' && rankingsSortBy === 'fame') ||
                            (col.key === 'minutes_survived' && rankingsSortBy === 'survival_time') ||
                            (col.key === 'longest_shot' && rankingsSortBy === 'longest_shot_distance');
                          
                          return (
                            <th
                              key={col.key}
                              className={`text-left py-2 px-2 text-white/70 font-medium whitespace-nowrap ${col.sortable ? 'cursor-pointer hover:text-white transition-colors select-none' : ''}`}
                              onClick={col.sortable ? () => {
                                if (isActive) {
                                  setRankingsSortOrder(rankingsSortOrder === 'desc' ? 'asc' : 'desc');
                                } else {
                                  setRankingsSortBy(col.key);
                                  setRankingsSortOrder('desc');
                                }
                                setRankingsPage(1);
                              } : undefined}
                            >
                              <div className="flex items-center gap-1.5">
                                {t(`players.rankings.columns.${col.label}`) ?? col.label}
                                {col.sortable && isActive && (
                                  rankingsSortOrder === 'desc' ? <ArrowDown size={14} className="text-green-400" /> : <ArrowUp size={14} className="text-green-400" />
                                )}
                              </div>
                            </th>
                          );
                        })}
                      </tr>
                    </thead>
                    <tbody>
                      {rankingsData.map((player) => {
                        const longestShotDistance = player.longest_shot?.distance ?? 0;
                        const minutesSurvived = Math.floor(player.minutes_survived ?? 0);
                        const hours = Math.floor(minutesSurvived / 60);
                        const minutes = minutesSurvived % 60;
                        const playtimeFormatted = hours > 0 ? `${hours}h ${minutes}m` : `${minutes}m`;

                        // Função helper para obter valor da coluna
                        const getColumnValue = (key: string): string | number => {
                          switch (key) {
                            case 'rank': return player.rank;
                            case 'player': return player.player_name;
                            case 'kills': return player.kills ?? 0;
                            case 'deaths': return player.deaths ?? 0;
                            case 'kdr': return formatMetricValue(player.kdr ?? 0);
                            case 'total_fame': return formatMetricValue(player.total_fame ?? 0);
                            case 'minutes_survived': return playtimeFormatted;
                            case 'longest_shot': return longestShotDistance > 0 ? `${formatMetricValue(longestShotDistance)}m` : '—';
                            case 'headshots': return player.headshots ?? 0;
                            case 'suicides': return player.suicides ?? 0;
                            case 'vehicles_destroyed': return player.vehicles_destroyed ?? 0;
                            case 'animals_killed': return player.animals_killed ?? 0;
                            case 'players_knocked_out': return player.players_knocked_out ?? 0;
                            case 'overdoses': return player.overdoses ?? 0;
                            case 'highest_weight_carried': return formatMetricValue(player.highest_weight_carried ?? 0);
                            case 'highest_defecation': return player.highest_defecation ?? 0;
                            case 'lockpick_basic_rate': return player.lockpicking?.basic?.rate ? `${formatMetricValue(player.lockpicking.basic.rate)}%` : '—';
                            case 'lockpick_medium_rate': return player.lockpicking?.medium?.rate ? `${formatMetricValue(player.lockpicking.medium.rate)}%` : '—';
                            case 'lockpick_advanced_rate': return player.lockpicking?.advanced?.rate ? `${formatMetricValue(player.lockpicking.advanced.rate)}%` : '—';
                            case 'lockpick_veryeasy_rate': return player.lockpicking?.veryeasy?.rate ? `${formatMetricValue(player.lockpicking.veryeasy.rate)}%` : '—';
                            case 'lockpick_diallock_rate': return player.lockpicking?.diallock?.rate ? `${formatMetricValue(player.lockpicking.diallock.rate)}%` : '—';
                            default: return '—';
                          }
                        };

                        return (
                          <tr key={player.steam_id} className="border-b border-white/5 hover:bg-white/5">
                            {/* Renderizar colunas fixas */}
                            {visibleColumns.has('rank') && (
                              <td className="py-2 px-2 text-white/70 font-mono">
                                {player.rank}
                              </td>
                            )}
                            {visibleColumns.has('player') && (
                              <td className="py-2 px-2 font-medium text-white">
                                {player.player_name}
                              </td>
                            )}
                            
                            {/* Renderizar colunas dinamicamente */}
                            {[...RANKING_COLUMNS.main, ...RANKING_COLUMNS.combat, ...RANKING_COLUMNS.survival, ...RANKING_COLUMNS.lockpicking].map(col => {
                              if (!visibleColumns.has(col.key)) return null;
                              
                              const value = getColumnValue(col.key);
                              const isNumeric = typeof value === 'number' || (typeof value === 'string' && value !== '—' && !value.includes('h') && !value.includes('m') && !value.includes('%'));
                              
                              return (
                                <td key={col.key} className={`py-2 px-2 text-white/80 ${col.key === 'minutes_survived' ? 'text-xs' : ''}`}>
                                  {value}
                                </td>
                              );
                            })}
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>
              </div>

              {/* Seletor de Ordenação para Mobile */}
              <div className="md:hidden mb-3">
                <div className="flex items-center gap-2">
                  <label className="text-xs text-white/70 whitespace-nowrap">
                    {t('players.rankings.sortBy') ?? 'Ordenar por'}:
                  </label>
                  <select
                    value={rankingsSortBy}
                    onChange={(e) => {
                      setRankingsSortBy(e.target.value);
                      setRankingsPage(1);
                    }}
                    className="flex-1 px-2 py-1.5 bg-black/50 border border-white/10 rounded-lg text-white text-xs focus:outline-none focus:ring-2 focus:ring-scum-panel"
                  >
                    {[...RANKING_COLUMNS.main, ...RANKING_COLUMNS.combat, ...RANKING_COLUMNS.survival, ...RANKING_COLUMNS.lockpicking]
                      .filter(col => col.sortable)
                      .map(col => (
                        <option key={col.key} value={col.key}>
                          {t(`players.rankings.columns.${col.label}`) ?? col.label}
                        </option>
                      ))}
                  </select>
                  <button
                    onClick={() => {
                      setRankingsSortOrder(rankingsSortOrder === 'desc' ? 'asc' : 'desc');
                      setRankingsPage(1);
                    }}
                    className="px-2 py-1.5 bg-black/50 border border-white/10 rounded-lg text-white hover:bg-white/10 transition-colors flex items-center gap-1"
                    title={rankingsSortOrder === 'desc' ? t('players.rankings.sortDesc') ?? 'Ordenar decrescente' : t('players.rankings.sortAsc') ?? 'Ordenar crescente'}
                  >
                    {rankingsSortOrder === 'desc' ? <ArrowDown size={14} /> : <ArrowUp size={14} />}
                  </button>
                </div>
              </div>

              {/* Cards empilhados para mobile */}
              <div className="grid gap-3 md:hidden">
                {rankingsData.map((player) => {
                  const longestShotDistance = player.longest_shot?.distance ?? 0;
                  const minutesSurvived = Math.floor(player.minutes_survived ?? 0);
                  const hours = Math.floor(minutesSurvived / 60);
                  const minutes = minutesSurvived % 60;
                  const playtimeFormatted = hours > 0 ? `${hours}h ${minutes}m` : `${minutes}m`;

                  return (
                    <div
                      key={`card-${player.steam_id}`}
                      className="rounded-lg border border-white/10 bg-black/30 p-3 text-sm text-white/80"
                    >
                      {/* Header do Card */}
                      <div className="flex items-center justify-between mb-2">
                        <div className="flex items-center gap-2">
                          <span className="text-xs font-mono text-white/60">#{player.rank}</span>
                          <span className="font-semibold text-white">{player.player_name}</span>
                        </div>
                      </div>

                      {/* Estatísticas principais em grid - apenas colunas visíveis */}
                      <div className="grid grid-cols-2 gap-2 mt-3 text-xs">
                        {[...RANKING_COLUMNS.main, ...RANKING_COLUMNS.combat, ...RANKING_COLUMNS.survival, ...RANKING_COLUMNS.lockpicking].map(col => {
                          if (!visibleColumns.has(col.key)) return null;
                          
                          const getValue = () => {
                            switch (col.key) {
                              case 'kills': return player.kills ?? 0;
                              case 'deaths': return player.deaths ?? 0;
                              case 'kdr': return formatMetricValue(player.kdr ?? 0);
                              case 'total_fame': return formatMetricValue(player.total_fame ?? 0);
                              case 'minutes_survived': return playtimeFormatted;
                              case 'longest_shot': return longestShotDistance > 0 ? `${formatMetricValue(longestShotDistance)}m` : '—';
                              case 'headshots': return player.headshots ?? 0;
                              case 'suicides': return player.suicides ?? 0;
                              case 'vehicles_destroyed': return player.vehicles_destroyed ?? 0;
                              case 'animals_killed': return player.animals_killed ?? 0;
                              case 'players_knocked_out': return player.players_knocked_out ?? 0;
                              case 'overdoses': return player.overdoses ?? 0;
                              case 'highest_weight_carried': return formatMetricValue(player.highest_weight_carried ?? 0);
                              case 'highest_defecation': return player.highest_defecation ?? 0;
                              case 'lockpick_basic_rate': return player.lockpicking?.basic?.rate ? `${formatMetricValue(player.lockpicking.basic.rate)}%` : '—';
                              case 'lockpick_medium_rate': return player.lockpicking?.medium?.rate ? `${formatMetricValue(player.lockpicking.medium.rate)}%` : '—';
                              case 'lockpick_advanced_rate': return player.lockpicking?.advanced?.rate ? `${formatMetricValue(player.lockpicking.advanced.rate)}%` : '—';
                              case 'lockpick_veryeasy_rate': return player.lockpicking?.veryeasy?.rate ? `${formatMetricValue(player.lockpicking.veryeasy.rate)}%` : '—';
                              case 'lockpick_diallock_rate': return player.lockpicking?.diallock?.rate ? `${formatMetricValue(player.lockpicking.diallock.rate)}%` : '—';
                              default: return '—';
                            }
                          };
                          
                          return (
                            <div key={col.key} className="flex items-center justify-between py-1 border-b border-white/5">
                              <span className="text-white/50">{t(`players.rankings.columns.${col.label}`) ?? col.label}:</span>
                              <span className={`font-medium text-white ${col.key === 'minutes_survived' ? 'text-xs' : ''}`}>
                                {getValue()}
                              </span>
                            </div>
                          );
                        })}
                      </div>
                    </div>
                  );
                })}
              </div>

              {/* Paginação */}
              <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 border-t border-white/10 pt-3 text-xs text-white/60">
                <div className="text-center sm:text-left">
                  {t('players.rankings.showing', {
                    start: (rankingsPage - 1) * rankingsPageSize + 1,
                    end: Math.min(rankingsPage * rankingsPageSize, rankingsTotal),
                    total: rankingsTotal,
                  }) ?? `Mostrando ${(rankingsPage - 1) * rankingsPageSize + 1}-${Math.min(rankingsPage * rankingsPageSize, rankingsTotal)} de ${rankingsTotal}`}
                </div>
                <div className="flex items-center justify-center gap-2">
                  <button
                    type="button"
                    onClick={() => setRankingsPage(prev => Math.max(1, prev - 1))}
                    disabled={rankingsPage === 1 || rankingsLoading}
                    className="rounded-md border border-white/20 px-2 sm:px-3 py-1 text-white/70 transition hover:border-white/40 hover:text-white disabled:cursor-not-allowed disabled:opacity-50 text-xs sm:text-sm"
                  >
                    {t('players.pagination.prev') ?? 'Anterior'}
                  </button>
                  <div className="text-white/60 px-2">
                    {t('players.pagination.page', { page: rankingsPage }) ?? `Página ${rankingsPage}`}
                  </div>
                  <button
                    type="button"
                    onClick={() => setRankingsPage(prev => prev + 1)}
                    disabled={rankingsPage * rankingsPageSize >= rankingsTotal || rankingsLoading}
                    className="rounded-md border border-white/20 px-2 sm:px-3 py-1 text-white/70 transition hover:border-white/40 hover:text-white disabled:cursor-not-allowed disabled:opacity-50 text-xs sm:text-sm"
                  >
                    {t('players.pagination.next') ?? 'Próxima'}
                  </button>
                </div>
              </div>
            </>
          )}
        </div>
      )}

      {mainTab === 'bank' && isAdmin && (
        <div className="space-y-4">
          <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
            <div className="relative flex-1 w-full sm:min-w-[200px]">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-white/40" size={16} />
              <input
                type="text"
                value={bankSearch}
                onChange={(e) => {
                  setBankSearch(e.target.value);
                  setBankOffset(0);
                }}
                placeholder={t('players.bank.searchPlaceholder') ?? 'Search by player name or Steam ID...'}
                className="w-full pl-9 pr-3 py-2 bg-black/30 border border-white/10 rounded-lg text-sm text-white placeholder:text-white/40 focus:outline-none focus:ring-2 focus:ring-scum-panel focus:border-transparent"
              />
            </div>
          </div>

          {bankLoading && bankItems.length === 0 ? (
            <div className="text-center py-8 text-white/50">
              <Loader2 size={24} className="animate-spin mx-auto mb-2" />
              <div>{t('players.bank.loading') ?? 'Loading...'}</div>
            </div>
          ) : bankError ? (
            <div className="text-center py-8 text-red-400">{bankError}</div>
          ) : bankItems.length > 0 ? (
            <>
              <div className="flex items-center justify-between gap-2 sm:hidden">
                <div className="text-xs text-white/60">{t('players.rankings.sortBy') ?? 'Sort by:'}</div>
                <div className="flex items-center gap-2">
                  <button
                    type="button"
                    onClick={() => handleBankSort('money')}
                    className={`rounded-md border px-2 py-1 text-xs transition-colors ${
                      bankSortKey === 'money'
                        ? 'border-white/40 text-white'
                        : 'border-white/20 text-white/70 hover:border-white/40 hover:text-white'
                    }`}
                  >
                    {t('players.bank.columns.money') ?? 'Money'}
                    {bankSortKey === 'money' && (
                      <span className="ml-1 inline-flex align-middle">
                        {bankSortDir === 'asc' ? <ArrowUp size={12} /> : <ArrowDown size={12} />}
                      </span>
                    )}
                  </button>
                  <button
                    type="button"
                    onClick={() => handleBankSort('gold')}
                    className={`rounded-md border px-2 py-1 text-xs transition-colors ${
                      bankSortKey === 'gold'
                        ? 'border-white/40 text-white'
                        : 'border-white/20 text-white/70 hover:border-white/40 hover:text-white'
                    }`}
                  >
                    {t('players.bank.columns.gold') ?? 'Gold'}
                    {bankSortKey === 'gold' && (
                      <span className="ml-1 inline-flex align-middle">
                        {bankSortDir === 'asc' ? <ArrowUp size={12} /> : <ArrowDown size={12} />}
                      </span>
                    )}
                  </button>
                </div>
              </div>

              <div className="space-y-2 sm:hidden">
                {sortedBankItems.map((it) => (
                  <div key={it.steam_id} className="rounded-lg border border-white/10 bg-black/20 p-3">
                    <div className="flex items-start justify-between gap-2">
                      <div className="min-w-0">
                        <div className="text-white font-medium truncate">{it.player_name || '—'}</div>
                        <div className="text-white/60 text-xs font-mono truncate">{it.steam_id}</div>
                        <div className="text-white/60 text-xs font-mono truncate">{it.account_number}</div>
                      </div>
                      <div className="shrink-0 text-right">
                        <div className="text-white text-sm">
                          {t('players.bank.columns.money') ?? 'Money'}: {it.balances?.money_total ?? 0}
                        </div>
                        <div className="text-white text-sm">
                          {t('players.bank.columns.gold') ?? 'Gold'}: {it.balances?.gold ?? 0}
                        </div>
                      </div>
                    </div>
                  </div>
                ))}
              </div>

              <div className="hidden sm:block overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="text-left text-white/70 border-b border-white/10">
                      <th className="py-2 px-2">{t('players.bank.columns.playerName') ?? 'Name'}</th>
                      <th className="py-2 px-2">{t('players.bank.columns.steamId') ?? 'Steam ID'}</th>
                      <th className="py-2 px-2">{t('players.bank.columns.accountNumber') ?? 'Account'}</th>
                      <th className="py-2 px-2 text-right">
                        <button
                          type="button"
                          onClick={() => handleBankSort('money')}
                          className="inline-flex items-center justify-end gap-1 w-full hover:text-white transition-colors"
                        >
                          <span>{t('players.bank.columns.money') ?? 'Money'}</span>
                          {bankSortKey === 'money' && (bankSortDir === 'asc' ? <ArrowUp size={12} /> : <ArrowDown size={12} />)}
                        </button>
                      </th>
                      <th className="py-2 px-2 text-right">
                        <button
                          type="button"
                          onClick={() => handleBankSort('gold')}
                          className="inline-flex items-center justify-end gap-1 w-full hover:text-white transition-colors"
                        >
                          <span>{t('players.bank.columns.gold') ?? 'Gold'}</span>
                          {bankSortKey === 'gold' && (bankSortDir === 'asc' ? <ArrowUp size={12} /> : <ArrowDown size={12} />)}
                        </button>
                      </th>
                    </tr>
                  </thead>
                  <tbody>
                    {sortedBankItems.map((it) => (
                      <tr key={it.steam_id} className="border-b border-white/5 hover:bg-white/5">
                        <td className="py-2 px-2 text-white">{it.player_name || '—'}</td>
                        <td className="py-2 px-2 text-white/80 font-mono">{it.steam_id}</td>
                        <td className="py-2 px-2 text-white/80 font-mono">{it.account_number}</td>
                        <td className="py-2 px-2 text-right text-white">{it.balances?.money_total ?? 0}</td>
                        <td className="py-2 px-2 text-right text-white">{it.balances?.gold ?? 0}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </>
          ) : (
            <div className="text-center py-8 text-white/50">
              {t('players.bank.empty') ?? 'No items.'}
            </div>
          )}

          <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 border-t border-white/10 pt-3 text-xs text-white/60">
            <div className="text-center sm:text-left">
              {t('players.bank.showing', {
                start: bankTotal === 0 ? 0 : bankOffset + 1,
                end: Math.min(bankOffset + bankLimit, bankTotal),
                total: bankTotal,
              })}
            </div>
            <div className="flex items-center justify-center gap-2">
              <button
                type="button"
                onClick={() => setBankOffset((prev) => Math.max(0, prev - bankLimit))}
                disabled={bankOffset === 0 || bankLoading}
                className="rounded-md border border-white/20 px-2 sm:px-3 py-1 text-white/70 transition hover:border-white/40 hover:text-white disabled:cursor-not-allowed disabled:opacity-50 text-xs sm:text-sm"
              >
                {t('players.pagination.prev') ?? 'Previous'}
              </button>
              <button
                type="button"
                onClick={() => setBankOffset((prev) => prev + bankLimit)}
                disabled={!bankHasMore || bankLoading}
                className="rounded-md border border-white/20 px-2 sm:px-3 py-1 text-white/70 transition hover:border-white/40 hover:text-white disabled:cursor-not-allowed disabled:opacity-50 text-xs sm:text-sm"
              >
                {t('players.pagination.next') ?? 'Next'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Tab Análises */}
      {mainTab === 'analyses' && (
        <div className="space-y-4">
              {/* Header com filtros */}
              <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
                <h3 className="text-lg font-semibold flex items-center gap-2">
                  <BarChart3 size={20} />
                  {t('players.analyses.title')}
                </h3>
                
                <div className="flex items-center gap-3">
                  {/* Seletor de período */}
                  <select
                    value={chartDays}
                    onChange={(e) => setChartDays(Number(e.target.value))}
                    className="px-3 py-2 bg-black/50 border border-white/10 rounded-lg text-white text-sm focus:outline-none focus:ring-2 focus:ring-scum-panel"
                  >
                    <option value={7}>{t('players.analyses.period.7days')}</option>
                    <option value={30}>{t('players.analyses.period.30days')}</option>
                    <option value={90}>{t('players.analyses.period.90days')}</option>
                  </select>
                  
                  {/* Toggle granularidade */}
                  <div className="flex items-center gap-2 bg-black/30 rounded-lg p-1 border border-white/10">
                    <button
                      onClick={() => setChartGranularity('hour')}
                      className={`px-3 py-1.5 text-xs rounded transition-colors ${
                        chartGranularity === 'hour'
                          ? 'bg-scum-panel text-white'
                          : 'text-white/60 hover:text-white/80'
                      }`}
                    >
                      {t('players.analyses.granularity.hour')}
                    </button>
                    <button
                      onClick={() => setChartGranularity('day')}
                      className={`px-3 py-1.5 text-xs rounded transition-colors ${
                        chartGranularity === 'day'
                          ? 'bg-scum-panel text-white'
                          : 'text-white/60 hover:text-white/80'
                      }`}
                    >
                      {t('players.analyses.granularity.day')}
                    </button>
                  </div>
                </div>
              </div>

              {/* 🎯 Card de Pico Absoluto */}
              <AbsolutePeakCard
                absolutePeak={absolutePeak}
                loading={absolutePeakLoading}
              />

              {/* Cards de estatísticas */}
              {chartData?.data?.datasets?.[0] && (
                <div className="grid grid-cols-3 gap-3">
                  <StatCard
                    label={t('players.analyses.average')}
                    value={chartData.data.datasets[0].average.toFixed(1)}
                    unit={t('players.analyses.players')}
                    color="text-blue-400"
                  />
                  <StatCard
                    label={t('players.analyses.peak')}
                    value={chartData.data.datasets[0].peak}
                    unit={t('players.analyses.players')}
                    color="text-green-400"
                  />
                  <StatCard
                    label={t('players.analyses.lowest')}
                    value={chartData.data.datasets[0].lowest}
                    unit={t('players.analyses.players')}
                    color="text-red-400"
                  />
                </div>
              )}

              {/* Gráfico */}
              <div className="card p-4">
                {chartLoading ? (
                  <div className="flex items-center justify-center h-[400px]">
                    <Loader2 className="animate-spin text-scum-panel" size={32} />
                    <span className="ml-3 text-white/70">{t('players.analyses.loading')}</span>
                  </div>
                ) : chartError ? (
                  <div className="flex items-center justify-center h-[400px] text-red-400">
                    {chartError}
                  </div>
                ) : chartData?.data ? (
                  <PlayersChart data={chartData.data} />
                ) : (
                  <div className="flex items-center justify-center h-[400px] text-white/60">
                    {t('players.analyses.noData')}
                  </div>
                )}
              </div>
            </div>
          )}

      {mainTab === 'players' && (
        <div className="mt-4 flex flex-wrap items-center justify-between gap-3 border-t border-white/10 pt-3 text-xs text-white/60">
          <div>
            {t('players.pagination.showing', {
              start: playersRangeStart,
              end: playersRangeEnd,
              total: effectiveTotal,
            })}
          </div>
          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={() => setPlayersPage(prev => Math.max(1, prev - 1))}
              disabled={playersPage === 1 || loading || refreshing || effectiveTotal === 0}
              className="rounded-md border border-white/20 px-3 py-1 text-white/70 transition hover:border-white/40 hover:text-white disabled:cursor-not-allowed disabled:opacity-50"
            >
              {t('players.pagination.prev')}
            </button>
            <div className="text-white/60">
              {t('players.pagination.page', { page: effectiveTotal === 0 ? 0 : playersPage })}
            </div>
            <button
              type="button"
              onClick={() => setPlayersPage(prev => Math.min(playersMaxPage, prev + 1))}
              disabled={effectiveTotal === 0 || playersPage >= playersMaxPage || loading || refreshing}
              className="rounded-md border border-white/20 px-3 py-1 text-white/70 transition hover:border-white/40 hover:text-white disabled:cursor-not-allowed disabled:opacity-50"
            >
              {t('players.pagination.next')}
            </button>
            <select
              value={playersPageSize}
              onChange={(e) => handlePlayersPageSizeChange(Number(e.target.value))}
              className="rounded-md border border-white/20 bg-black/40 px-2 py-1 text-white/70 focus:outline-none focus:ring-2 focus:ring-scum-panel"
              disabled={effectiveTotal === 0}
            >
              {[10, 25, 50, 100].map(size => (
                <option key={size} value={size}>
                  {t('players.pagination.perPage', { count: size })}
                </option>
              ))}
            </select>
          </div>
        </div>
      )}
    </div>
  );
}


