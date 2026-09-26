import axios from 'axios';
import { authService } from './auth';
import { getApiBaseURL, getBackendTimeout } from './configLoader';

// Variável para armazenar a URL da API após carregar
let apiBaseURL: string = '/api';
let apiInstance: ReturnType<typeof axios.create> | null = null;
let lastNetworkErrorLoggedAt = 0;

// Função para inicializar a instância do axios após carregar o config
async function initializeApi() {
  if (apiInstance) return apiInstance;

  apiBaseURL = await getApiBaseURL();
  const timeout = await getBackendTimeout();
  
  // Log apenas em desenvolvimento, sem expor URL completa
  if (import.meta.env.DEV) {
    console.log('[API] ✅ Base URL configurada');
    console.log('[API] Timeout configurado:', timeout, 'ms');
  }

  apiInstance = axios.create({
    baseURL: apiBaseURL,
    timeout: timeout,
    headers: {
      'Content-Type': 'application/json'
    }
  });

  // Configurar interceptors
  setupInterceptors(apiInstance);

  return apiInstance;
}

// Função para configurar interceptors
function setupInterceptors(instance: ReturnType<typeof axios.create>) {
  // Interceptor de request: adicionar token automaticamente
  instance.interceptors.request.use(
    (config) => {
      const token = authService.getToken();
      if (token) {
        config.headers.Authorization = `Bearer ${token}`;
      }
      return config;
    },
    (error) => {
      return Promise.reject(error);
    }
  );

  // Interceptor de response: tratar erros de autenticação
  instance.interceptors.response.use(
    (r) => r,
    (e) => {
      // Tratamento de erros melhorado
      if (e.code === 'ERR_NETWORK' || 
          e.code === 'ERR_CONNECTION_TIMED_OUT' ||
          e.message?.includes('ERR_CONNECTION_REFUSED') ||
          e.message?.includes('ERR_CONNECTION_TIMED_OUT') ||
          e.message?.includes('timeout')) {
        const errorMsg =
          'Não foi possível conectar ao servidor backend. Verifique se o backend está rodando e acessível.';
        // Log de erro sanitizado (sem expor URLs ou dados sensíveis)
        const now = Date.now();
        const shouldLog = now - lastNetworkErrorLoggedAt > 10000;
        if (shouldLog) {
          lastNetworkErrorLoggedAt = now;
          if (import.meta.env.DEV) {
            console.error('[API Error]', errorMsg);
          } else {
            console.error('[API Error]', errorMsg);
          }
        }
        return Promise.reject(new Error(errorMsg));
      }
    
    // Tratar bloqueio de admin por vinculação Discord (403)
    if (e.response?.status === 403) {
      const errorCode = e.response.data?.code;
      const isAuthEndpoint = e.config?.url?.includes('/auth/');

      if (!isAuthEndpoint && errorCode === 'DISCORD_LINK_REQUIRED') {
        if (window.location.pathname !== '/activate-discord') {
          window.location.href = '/activate-discord';
        }
      }
    }

    // Tratar erros de autenticação (401)
    if (e.response?.status === 401) {
      const errorCode = e.response.data?.code;
      const isAuthEndpoint = e.config?.url?.includes('/auth/');
      
      // Não redirecionar se for endpoint de autenticação (evitar loop)
      if (!isAuthEndpoint && (errorCode === 'INVALID_TOKEN' || errorCode === 'AUTH_REQUIRED')) {
        // Limpar token e redirecionar para login
        authService.logout();
        
        // Verificar se não está já na página de login
        if (window.location.pathname !== '/login' && window.location.pathname !== '/change-password') {
          window.location.href = '/login';
        }
      }
    }
    
    // Para endpoint de veículos, transformar 404 em resposta válida (player sem veículos é situação normal)
    if (e.response?.status === 404 && e.config?.url?.includes('/vehicles/player/')) {
      // Transformar em resposta válida para evitar erro no console
      return Promise.resolve({
        status: 404,
        statusText: 'Not Found',
        headers: {},
        config: e.config,
        data: {
          success: false,
          error: 'Player not found or has no vehicles',
          data: undefined
        }
      });
    }

    // Para endpoints de permissões, alguns backends retornam 400 em casos idempotentes (já ativa/já inativa).
    // Para UX de toggle, tratamos como resposta válida para evitar rejeição/stacktrace no console.
    if (
      e.response?.status === 400 &&
      typeof e.config?.url === 'string' &&
      e.config.url.includes('/permissions/') &&
      (e.config.url.includes('/activate') || e.config.url.includes('/deactivate'))
    ) {
      return Promise.resolve(e.response);
    }
    
      return Promise.reject(e);
    }
  );
}

// Inicializar API imediatamente (carrega config.json em runtime)
initializeApi().catch((error) => {
  // Log de erro sanitizado
  if (import.meta.env.DEV) {
    console.error('[API] Erro ao inicializar API:', error);
  } else {
    console.error('[API] Erro ao inicializar API');
  }
});

// Exportar função para obter instância do api (inicializa se necessário)
export async function getApi() {
  return await initializeApi();
}

// Exportar api como proxy que garante inicialização antes de qualquer chamada
// Isso resolve o problema de race condition onde serviços usam api antes da inicialização completar
const api = new Proxy({} as ReturnType<typeof axios.create>, {
  get: (target, prop) => {
    // Se apiInstance já existe, usar diretamente
    if (apiInstance) {
      const value = (apiInstance as any)[prop];
      // Se for função, retornar bound
      if (typeof value === 'function') {
        return value.bind(apiInstance);
      }
      return value;
    }
    
    // Se for um método HTTP (get, post, put, delete, patch), aguardar inicialização
    if (typeof prop === 'string' && ['get', 'post', 'put', 'delete', 'patch'].includes(prop)) {
      return async (...args: any[]) => {
        const instance = await initializeApi();
        return (instance as any)[prop](...args);
      };
    }
    
    // Para interceptors, aguardar inicialização e retornar proxy
    if (prop === 'interceptors') {
      return {
        request: {
          use: async (...args: any[]) => {
            const instance = await initializeApi();
            return instance.interceptors.request.use(...args);
          }
        },
        response: {
          use: async (...args: any[]) => {
            const instance = await initializeApi();
            return instance.interceptors.response.use(...args);
          }
        }
      };
    }
    
    // Para outras propriedades, aguardar inicialização
    return async (...args: any[]) => {
      const instance = await initializeApi();
      const value = (instance as any)[prop];
      if (typeof value === 'function') {
        return value.bind(instance);
      }
      return value;
    };
  }
}) as ReturnType<typeof axios.create>;

// Status do servidor SCUM (endpoint /api/server/status)
export interface ServerStatusData {
  install_path: string;
  is_running: boolean;
  last_check: number;
  max_players: number;
  nssm_path: string;
  port: number;
  server_path: string;
  service_info: {
    AGUARDAR_DICA?: string;
    CÓDIGO_DE_SAÍDA_DO_SERVIÇO?: string;
    CÓDIGO_DE_SAÍDA_DO_WIN32?: string;
    ESTADO?: string;
    NOME_DO_SERVIÇO?: string;
    PONTO_DE_VERIFICAÇÃO?: string;
    TIPO?: string;
    [key: string]: string | undefined;
  };
  service_name: string;
  steamcmd_path: string;
  use_battleye: boolean;
}

export interface ServerStatusResponse {
  success: boolean;
  data?: ServerStatusData;
  timestamp?: number;
  error?: string;
}

// Função para buscar o status do servidor
export async function getServerStatus(): Promise<ServerStatusResponse> {
  const instance = await initializeApi();
  const { data } = await instance.get<ServerStatusResponse>('/server/status');
  return data;
}

// Interface legada para status do jogo (usado na Home - será outro endpoint no futuro)
export interface ServerGameStatus {
  time: string;
  weather: string;
  moon: string;
  players: number;
}

// Tempo do servidor (endpoint /api/weather/time)
export interface ServerTimeData {
  air_temperature?: number;
  cumulonimbus_causes_fog?: boolean;
  fog_density?: number;
  is_running: boolean;
  last_sync: string;
  map_id?: number;
  moon_rotation?: number;
  next_sync: string;
  server_time: string;
  sync_interval_minutes: number;
  time_of_day: number;
  user_profile_id?: number | null;
  water_temperature?: number;
}

export interface ServerTimeResponse {
  success: boolean;
  data?: ServerTimeData;
  timestamp?: number;
  error?: string;
}

// Função para buscar o tempo do servidor
export async function getServerTime(): Promise<ServerTimeResponse> {
  const { data } = await api.get<ServerTimeResponse>('/weather/time');
  return data;
}

// Estatísticas de jogadores online (endpoint /api/players/online/stats)
export interface PlayersOnlineStatsData {
  last_update: string;
  offline_count: number;
  online_count: number;
  total_tracked: number;
}

export interface PlayersOnlineStatsResponse {
  success: boolean;
  data?: PlayersOnlineStatsData;
  error?: string;
}

// Função para buscar estatísticas de jogadores online
export async function getPlayersOnlineStats(): Promise<PlayersOnlineStatsResponse> {
  const { data } = await api.get<PlayersOnlineStatsResponse>('/players/online/stats');
  return data;
}

// Tipos para lista de jogadores (endpoint /api/logs/players)
export interface ActiveSession {
  duration: number;
  login_time: string;
  player_id: number;
  player_name: string;
  steam_id: string;
}

export interface TopPlayer {
  player_name: string;
  total_playtime: number;
  total_sessions: number;
}

export interface PlayersLogsData {
  active_players: number;
  active_sessions: ActiveSession[];
  new_players: number;
  online_now: number;
  top_players: TopPlayer[];
  total_players: number;
}

export interface PlayersLogsResponse {
  success: boolean;
  data?: PlayersLogsData;
  error?: string;
}

// Função para buscar lista de jogadores
export async function getPlayersLogs(limit: number = 100, offset: number = 0): Promise<PlayersLogsResponse> {
  const { data } = await api.get<PlayersLogsResponse>('/logs/players', {
    params: { limit, offset }
  });
  return data;
}

// Tipos para lista de jogadores online (endpoint /api/players/online/list)
export interface SteamInfo {
  avatar_full_url: string;
  avatar_medium_url: string;
  avatar_url: string;
  community_visibility: number;
  country_code: string;
  last_logoff: number;
  persona_name: string;
  persona_state: number;
  profile_url: string;
  real_name: string;
  steam_id: string;
  time_created: number;
}

export interface Coordinates {
  x: number;
  y: number;
  z: number;
}

export interface OnlinePlayer {
  activity_types: string[];
  coordinates: Coordinates;
  last_activity: string;
  player_id: number;
  player_name: string;
  steam_id: string;
  steam_info: SteamInfo;
  total_activities: number;
}

export interface PlayersOnlineListData {
  count: number;
  players: OnlinePlayer[];
  timestamp: string;
}

export interface PlayersOnlineListResponse {
  success: boolean;
  data?: PlayersOnlineListData;
  error?: string;
}

// Função para buscar lista de jogadores online
export async function getPlayersOnlineList(): Promise<PlayersOnlineListResponse> {
  const { data } = await api.get<PlayersOnlineListResponse>('/players/online/list');
  return data;
}

// Tipos para lista completa de jogadores (endpoint /api/players)
export interface AllPlayer {
  created_at: string;
  first_seen: string;
  is_new_player: boolean;
  last_seen: string;
  notification_sent: boolean;
  permissao: number;
  player_id: number;
  player_name: string;
  steam_id: string;
  total_playtime: number;
  total_sessions: number;
  balance?: number;
}

export interface AllPlayersData {
  count: number;
  limit: number | null;
  offset: number;
  players: AllPlayer[];
  total: number;
}

export interface AllPlayersResponse {
  success: boolean;
  data?: AllPlayersData;
  error?: string;
}

// Função para buscar lista completa de jogadores
export async function getAllPlayers(
  limit?: number | null,
  offset: number = 0,
  options?: {
    sortBy?: string;
    sortOrder?: 'asc' | 'desc';
    q?: string;
  }
): Promise<AllPlayersResponse> {
  const params: Record<string, any> = { offset };
  if (limit !== undefined && limit !== null) {
    params.limit = limit;
  }
  if (options?.sortBy) {
    params.sort_by = options.sortBy;
  }
  if (options?.sortOrder) {
    params.sort_order = options.sortOrder;
  }
  if (options?.q) {
    params.q = options.q;
  }

  const { data } = await api.get<AllPlayersResponse>('/players', {
    params,
  });
  return data;
}

// Tipos para atualização de permissão do comando /tm
export interface UpdatePermissaoRequest {
  permissao: 0 | 1;
}

export interface UpdatePermissaoResponse {
  success: boolean;
  message: string;
  data?: AllPlayer;
  error?: string;
}

// Função para atualizar permissão do comando /tm para um jogador
export async function updatePlayerPermissao(steamId: string, permissao: 0 | 1): Promise<UpdatePermissaoResponse> {
  const { data } = await api.put<UpdatePermissaoResponse>(`/players/${steamId}/permissao`, {
    permissao
  });
  return data;
}

// Tipos para sistema de permissões avançadas (player_permissions)
export interface PlayerPermission {
  id: number;
  permission_type: string;
  is_active: boolean | number; // Pode ser true/false ou 1/0
  granted_by: string | null;
  granted_at: string | null;
  revoked_by: string | null;
  revoked_at: string | null;
  notes: string | null;
}

export interface PlayerPermissionsData {
  steam_id: string;
  player_name: string;
  permissions: PlayerPermission[];
  total_permissions: number;
  active_permissions: number;
  inactive_permissions: number;
}

export interface PlayerPermissionsResponse {
  success: boolean;
  data?: PlayerPermissionsData;
  error?: string;
}

export interface ActivatePermissionResponse {
  success: boolean;
  message: string;
  data?: {
    permission_id: number;
    steam_id: string;
    permission_type: string;
    is_active: boolean;
    granted_by: string;
    granted_at: string;
    notes: string | null;
    ini_file_updated: boolean | null;
    ini_file_path: string | null;
  };
  error?: string;
}

// Tipos de permissão disponíveis
export type PermissionType = 'admin' | 'banned' | 'exclusive' | 'server_admin' | 'silenced' | 'whitelisted' | 'raid_webhook_manage';

// Função para buscar permissões de um jogador
export async function getPlayerPermissions(steamId: string, includeInactive: boolean = false): Promise<PlayerPermissionsResponse> {
  const { data } = await api.get<PlayerPermissionsResponse>(`/players/${steamId}/permissions`, {
    params: { include_inactive: includeInactive }
  });
  return data;
}

// Função para ativar uma permissão
export async function activatePermission(
  steamId: string,
  permissionType: PermissionType,
  grantedBy?: string,
  notes?: string
): Promise<ActivatePermissionResponse> {
  const { data } = await api.post<ActivatePermissionResponse>(
    `/players/${steamId}/permissions/${permissionType}/activate`,
    {
      granted_by: grantedBy || 'system',
      notes: notes || null
    },
    {
      validateStatus: (status) => status < 500
    }
  );
  return data;
}

// Função para desativar uma permissão
export async function deactivatePermission(
  steamId: string,
  permissionType: PermissionType,
  revokedBy?: string,
  notes?: string
): Promise<ActivatePermissionResponse> {
  const { data } = await api.post<ActivatePermissionResponse>(
    `/players/${steamId}/permissions/${permissionType}/deactivate`,
    {
      revoked_by: revokedBy || 'system',
      notes: notes || null
    },
    {
      validateStatus: (status) => status < 500
    }
  );
  return data;
}

// Hook stub para uso na Home (atualizar quando tiver endpoint de status do jogo)
export const getServerStatus_legacy = {
  async queryFn() {
    return {
      time: '--:--',
      weather: '—',
      moon: '—',
      players: 0,
    } as ServerGameStatus;
  },
  useQuery() {
    return {
      data: undefined as ServerGameStatus | undefined,
      isLoading: false,
    };
  },
};

// Tipos para controle do servidor
export interface ServerRequest {
  force?: boolean;
  wait_timeout?: number;
}

export interface ServerResponse {
  success: boolean;
  message?: string;
  status?: 'started' | 'stopped' | 'restarted' | 'already_running' | 'not_running';
  data?: {
    service_name?: string;
    pid?: number;
    uptime?: number;
  };
  final_status?: {
    is_running: boolean;
    service_name?: string;
  };
  error?: string;
}

// Funções de controle do servidor
export async function startServer(params: ServerRequest = {}): Promise<ServerResponse> {
  const { data } = await api.post<ServerResponse>('/server/start', {
    force: params.force ?? false,
    wait_timeout: params.wait_timeout ?? 30,
  });
  return data;
}

export async function stopServer(params: ServerRequest = {}): Promise<ServerResponse> {
  const { data } = await api.post<ServerResponse>('/server/stop', {
    force: params.force ?? false,
    wait_timeout: params.wait_timeout ?? 30,
  });
  return data;
}

export async function restartServer(params: ServerRequest = {}): Promise<ServerResponse> {
  const { data } = await api.post<ServerResponse>('/server/restart', {
    force: params.force ?? false,
    wait_timeout: params.wait_timeout ?? 0, // Padrão 0 para execução assíncrona
  });
  return data;
}

// Tipos para sistema de veículos
export interface Vehicle {
  entity_id: number;
  vehicle_entity_id: number;
  vehicle_class: string;
  vehicle_class_display: string;
  status: number;
  status_text: string;
  location_x: number;
  location_y: number;
  location_z: number;
  last_ownership_change: string;
  is_vehicle_functional: number;
  container_class?: string;
  vehicle_asset_id?: string;
  notification_sent?: boolean;
  updated_at?: string;
}

export interface PlayerVehiclesSummary {
  total_vehicles: number;
  by_status?: {
    [status: string]: number;
  };
  filtered_status?: number[];
  count?: number;
}

export interface PlayerVehiclesData {
  steam_id: string;
  player_name: string;
  player_id: number;
  summary: PlayerVehiclesSummary;
  vehicles?: Vehicle[];
  vehicles_by_status?: {
    [status: string]: Vehicle[];
  };
}

export interface PlayerVehicleSummaryItem {
  steam_id: string;
  player_id?: number;
  total: number;
  by_status?: Record<string, number>;
  updated_at?: string | null;
}

export interface PlayersVehicleSummaryData {
  count: number;
  limit: number;
  offset: number;
  total: number;
  sort_by?: string;
  sort_order?: 'asc' | 'desc';
  summaries: PlayerVehicleSummaryItem[];
}

export interface PlayersVehicleSummaryResponse {
  success: boolean;
  data?: PlayersVehicleSummaryData;
  error?: string;
}

export interface PlayerVehiclesResponse {
  success: boolean;
  data?: PlayerVehiclesData;
  error?: string;
  timestamp?: number;
}

// Função para buscar veículos de um player por status
export async function getPlayerVehiclesByStatus(
  steamId: string,
  status?: string
): Promise<PlayerVehiclesResponse> {
  const params = status ? { status } : {};
  
  // O interceptor transforma 404 em resposta válida automaticamente
  const response = await api.get<PlayerVehiclesResponse>(
    `/vehicles/player/${steamId}/by-status`,
    { 
      params,
      // Validar que 200 e 404 são status válidos (404 será transformado pelo interceptor)
      validateStatus: (status) => status === 200 || status === 404
    }
  );
  
  // Se for 404, retornar resposta vazia (já transformada pelo interceptor)
  if (response.status === 404 || (response.data && !response.data.success)) {
    return {
      success: false,
      error: 'Player not found or has no vehicles',
      data: undefined
    };
  }
  
  return response.data;
}

export async function getPlayersVehicleSummary(
  limit?: number,
  offset?: number,
  steamId?: string,
  options?: {
    sortBy?: string;
    sortOrder?: 'asc' | 'desc';
  }
): Promise<PlayersVehicleSummaryResponse> {
  const params: Record<string, any> = {};
  if (typeof limit === 'number') params.limit = limit;
  if (typeof offset === 'number') params.offset = offset;
  if (steamId) params.steam_id = steamId;
  if (options?.sortBy) params.sort_by = options.sortBy;
  if (options?.sortOrder) params.sort_order = options.sortOrder;

  const { data } = await api.get<PlayersVehicleSummaryResponse>('/players/vehicles/summary', {
    params,
  });
  return data;
}

export interface AllPlayersVehiclesData {
  total_players: number;
  total_vehicles: number;
  count?: number;
  limit?: number;
  offset?: number;
  filtered_status?: number[];
  players: Array<{
    steam_id: string;
    player_name: string;
    player_id: number;
    vehicles_count: number;
    vehicles?: Vehicle[];
    vehicles_by_status?: {
      [status: string]: Vehicle[];
    };
    summary?: {
      total: number;
      by_status: {
        [status: string]: number;
      };
    };
  }>;
}

export interface AllPlayersVehiclesResponse {
  success: boolean;
  data?: AllPlayersVehiclesData;
  error?: string;
  timestamp?: number;
}

// Função para buscar todos os players com seus veículos
export async function getAllPlayersVehicles(
  status?: string,
  groupByStatus: boolean = false,
  limit: number = 1000,
  offset: number = 0
): Promise<AllPlayersVehiclesResponse> {
  const params: any = { limit, offset };
  if (status) params.status = status;
  if (groupByStatus) params.group_by_status = 'true';
  
  const { data } = await api.get<AllPlayersVehiclesResponse>('/vehicles/players', { params });
  return data;
}

// ==================== Sistema de Agendamento ====================

// Interfaces para o sistema de agendamento
export interface SchedulerStatus {
  enabled: boolean;
  is_running: boolean;
  restart_times: string[]; // Formato "HH:MM"
  next_restart: string | null; // ISO 8601
  notification_minutes: number[];
  scheduled_jobs: number;
  logs_count: number;
}

export interface SchedulerConfig {
  enabled: boolean;
  auto_start: boolean;
  restart_times: string[]; // Formato "HH:MM"
  notification_minutes: number[];
  timezone: string; // Ex: "America/Sao_Paulo"
}

export interface SchedulerLog {
  timestamp: string; // ISO 8601
  event_type: string;
  message: string;
  data: Record<string, any>;
}

export interface SchedulerLogResponse {
  logs: SchedulerLog[];
  count: number;
  limit: number;
}

export interface SchedulerApiResponse<T> {
  success: boolean;
  data?: T;
  message?: string;
  status?: string;
  error?: string;
  timestamp?: number;
  restart_result?: {
    success: boolean;
    message: string;
    status: string;
  };
}

export interface ForceRestartResponse {
  success: boolean;
  message: string;
  status: string;
  data?: {
    service_name: string;
    pid: number;
    uptime: number;
  };
}

// Funções de API para o sistema de agendamento
export async function getSchedulerStatus(): Promise<SchedulerApiResponse<SchedulerStatus>> {
  const { data } = await api.get<SchedulerApiResponse<SchedulerStatus>>('/scheduler/status');
  return data;
}

export async function startScheduler(): Promise<SchedulerApiResponse<any>> {
  const { data } = await api.post<SchedulerApiResponse<any>>('/scheduler/start');
  return data;
}

export async function stopScheduler(): Promise<SchedulerApiResponse<any>> {
  const { data } = await api.post<SchedulerApiResponse<any>>('/scheduler/stop');
  return data;
}

export async function restartScheduler(): Promise<SchedulerApiResponse<any>> {
  const { data } = await api.post<SchedulerApiResponse<any>>('/scheduler/restart');
  return data;
}

export async function getSchedulerLogs(limit: number = 50): Promise<SchedulerApiResponse<SchedulerLogResponse>> {
  const { data } = await api.get<SchedulerApiResponse<SchedulerLogResponse>>('/scheduler/logs', {
    params: { limit },
  });
  return data;
}

export async function getSchedulerConfig(): Promise<SchedulerApiResponse<SchedulerConfig>> {
  const { data } = await api.get<SchedulerApiResponse<SchedulerConfig>>('/scheduler/config');
  return data;
}

export async function updateSchedulerConfig(
  config: Partial<SchedulerConfig>
): Promise<SchedulerApiResponse<any>> {
  const { data } = await api.post<SchedulerApiResponse<any>>('/scheduler/config', config);
  return data;
}

export async function forceRestart(): Promise<SchedulerApiResponse<ForceRestartResponse>> {
  const { data } = await api.post<SchedulerApiResponse<ForceRestartResponse>>('/scheduler/force-restart');
  return data;
}

// ==================== Admin Logs ====================

// Interfaces para Admin Logs
export interface CommandCategory {
  key: string;
  name: string;
  emoji: string;
  color: string; // Hex color com #
}

export interface AdminCommand {
  command_id: string;
  timestamp: string; // ISO 8601
  steam_id: string;
  player_name: string;
  action: string;
  event_type: string | null;
  category: CommandCategory;
}

export interface AdminLogsRecentResponse {
  success: boolean;
  data?: {
    commands: AdminCommand[];
    total: number | null;
    limit: number;
  };
  timestamp?: number;
  error?: string;
}

// Função de API para buscar logs de admin recentes
export interface AdminLogsRecentParams {
  limit?: number;
  include_total?: boolean;
  category?: string | string[];
  steam_id?: string;
  player_name?: string;
  q?: string;
}

export async function getAdminLogsRecent(
  params: AdminLogsRecentParams = {}
): Promise<AdminLogsRecentResponse> {
  const { data } = await api.get<AdminLogsRecentResponse>('/admin-logs/recent', {
    params,
  });
  return data;
}

export interface AdminLogStatsCategory {
  name: string;
  emoji: string;
  color: string;
  count: number;
  percentage: number;
}

export interface AdminLogTopAdmin {
  steam_id: string;
  name: string;
  commands_count: number;
  percentage: number;
}

export interface AdminLogsStatsResponse {
  success: boolean;
  data?: {
    total_commands: number;
    commands_today: number;
    commands_this_week: number;
    commands_this_month: number;
    categories: Record<string, AdminLogStatsCategory>;
    top_admins: AdminLogTopAdmin[];
  };
  timestamp?: number;
  error?: string;
}

export async function getAdminLogsStats(): Promise<AdminLogsStatsResponse> {
  const { data } = await api.get<AdminLogsStatsResponse>('/admin-logs/stats');
  return data;
}

// ==================== Elevated Users ====================

// Interfaces para Elevated Users
export interface MarkElevatedUserRequest {
  elevated_user: 0 | 1;
  reason?: string;
}

export interface MarkElevatedUserResponse {
  success: boolean;
  data?: {
    steam_id: string;
    player_name: string;
    elevated_user: 0 | 1;
    action: 'added' | 'removed' | 'scheduled' | 'synced' | 'no_change';
    synced: boolean;
    message: string;
    backup_created?: string;
    pending_sync?: boolean;
  };
  timestamp?: string;
  error?: string;
}

export interface ElevatedUser {
  steam_id: string;
  player_name: string;
  is_synced: boolean;
  created_at: string;
  synced_at: string | null;
}

export interface ElevatedUserListResponse {
  success: boolean;
  data?: {
    elevated_users: ElevatedUser[];
    total: number;
  };
  timestamp?: string;
  error?: string;
}

// Função para marcar/desmarcar elevated user
export async function markElevatedUser(
  steamId: string,
  elevated: 0 | 1,
  reason?: string
): Promise<MarkElevatedUserResponse> {
  const { data } = await api.post<MarkElevatedUserResponse>(
    `/players/${steamId}/elevated-user`,
    {
      elevated_user: elevated,
      reason: reason || undefined
    }
  );
  return data;
}

// Função para listar todos os elevated users
export async function getElevatedUsersList(): Promise<ElevatedUserListResponse> {
  const { data } = await api.get<ElevatedUserListResponse>('/elevated-users/list');
  return data;
}

export default api;


