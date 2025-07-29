// Tipos para o servidor SCUM
export interface ServerStatus {
  isRunning: boolean;
  pid: string | null;
  startTime: string | null;
  lastCheck: string | null;
  uptime: number;
  restartCount: number;
  lastError: string | null;
  version: string | null;
}

export interface ServerConfig {
  port: number;
  maxPlayers: number;
  useBattleye: boolean;
  serverPath: string;
}

export interface ServerStatusResponse {
  success: boolean;
  status: ServerStatus;
  config: ServerConfig;
  error?: string;
  details?: string;
}

export interface ServerActionResponse {
  success: boolean;
  message?: string;
  error?: string;
  details?: string;
}

export interface ApiResponse<T> {
  success: boolean;
  data?: T;
  error?: string;
  details?: string;
  message?: string;
} 