import api from './server';

export interface GpsSyncStatus {
  enabled: boolean;
  is_running: boolean;
  sync_interval: string;
  last_sync: {
    timestamp: string; // ISO 8601
    status: 'success' | 'error' | 'warning';
    details: {
      players_synced?: number;
      players_updated?: number;
      players_created?: number;
      elapsed_seconds?: number;
      message?: string;
      error?: string;
    };
  };
}

export interface GpsSyncResponse {
  success: boolean;
  message?: string;
  status?: 'started' | 'stopped' | 'already_running' | 'not_running' | 'disabled';
  sync_interval?: string;
  error?: string;
}

export interface GpsSyncManualResponse {
  success: boolean;
  players_synced: number;
  players_updated?: number;
  players_created?: number;
  elapsed_seconds?: number;
  message?: string;
  errors?: Array<{
    steam_id: string;
    error: string;
  }>;
  error_count?: number;
  error?: string;
}

export interface GpsCoordinates {
  x: number;
  y: number;
  z: number;
}

export interface GpsSpawnData {
  prisoner_id: number;
  location_x: number;
  location_y: number;
  location_z: number;
  rotation_yaw: number; // Direção horizontal (0-360 graus)
  velocity_x: number;
  velocity_y: number;
  velocity_z: number;
  type: number;
  updated_at: string; // ISO 8601
}

export interface PlayerGpsData {
  steam_id: string;
  player_name: string;
  last_activity: string; // ISO 8601
  ssm_coordinates: GpsCoordinates;
  gps_data: {
    spawns: GpsSpawnData[];
  };
}

export interface OnlinePlayersGpsResponse {
  success: boolean;
  data: {
    players: PlayerGpsData[];
    count: number;
  };
  timestamp: number;
  error?: string;
}

// Obter dados de GPS dos jogadores online
export async function getOnlinePlayersGps(): Promise<OnlinePlayersGpsResponse> {
  const { data } = await api.get<OnlinePlayersGpsResponse>('/gps/online');
  return data;
}

// Obter status do serviço de sincronização
export async function getGpsSyncStatus(): Promise<GpsSyncStatus> {
  const { data } = await api.get<GpsSyncStatus>('/gps/sync/status');
  return data;
}

// Iniciar serviço de polling
export async function startGpsSync(): Promise<GpsSyncResponse> {
  const { data } = await api.post<GpsSyncResponse>('/gps/sync/start');
  return data;
}

// Parar serviço de polling
export async function stopGpsSync(): Promise<GpsSyncResponse> {
  const { data } = await api.post<GpsSyncResponse>('/gps/sync/stop');
  return data;
}

// Sincronização manual instantânea
export async function runGpsSyncNow(): Promise<GpsSyncManualResponse> {
  const { data } = await api.post<GpsSyncManualResponse>('/gps/sync/run-now');
  return data;
}
