import { useState, useEffect, useCallback } from 'react';
import { serverService } from '../services/serverService';
import { ServerStatus, ServerConfig, ServerStatusResponse } from '../types/server';

interface UseServerStatusReturn {
  status: ServerStatus | null;
  config: ServerConfig | null;
  loading: boolean;
  error: string | null;
  lastUpdate: Date | null;
  refreshStatus: () => Promise<void>;
  startServer: () => Promise<boolean>;
  stopServer: () => Promise<boolean>;
  restartServer: () => Promise<boolean>;
}

export const useServerStatus = (autoRefresh: boolean = true, refreshInterval: number = 10000): UseServerStatusReturn => {
  const [status, setStatus] = useState<ServerStatus | null>(null);
  const [config, setConfig] = useState<ServerConfig | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [lastUpdate, setLastUpdate] = useState<Date | null>(null);

  const refreshStatus = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      
      const response = await serverService.getStatus();
      
      if (response.success && response.status) {
        setStatus(response.status);
        setConfig(response.config);
        setLastUpdate(new Date());
      } else {
        setError(response.error || 'Erro ao buscar status do servidor');
      }
    } catch (err) {
      console.error('Erro ao buscar status:', err);
      setError('Erro de conexão com o servidor');
    } finally {
      setLoading(false);
    }
  }, []);

  const startServer = useCallback(async (): Promise<boolean> => {
    try {
      setLoading(true);
      setError(null);
      
      const response = await serverService.startServer();
      
      if (response.success) {
        // Aguardar um pouco antes de atualizar o status
        setTimeout(() => {
          refreshStatus();
        }, 2000);
        return true;
      } else {
        setError(response.error || 'Erro ao iniciar servidor');
        return false;
      }
    } catch (err) {
      setError('Erro de conexão com o servidor');
      console.error('Erro ao iniciar servidor:', err);
      return false;
    } finally {
      setLoading(false);
    }
  }, [refreshStatus]);

  const stopServer = useCallback(async (): Promise<boolean> => {
    try {
      setLoading(true);
      setError(null);
      
      const response = await serverService.stopServer();
      
      if (response.success) {
        // Aguardar um pouco antes de atualizar o status
        setTimeout(() => {
          refreshStatus();
        }, 2000);
        return true;
      } else {
        setError(response.error || 'Erro ao parar servidor');
        return false;
      }
    } catch (err) {
      setError('Erro de conexão com o servidor');
      console.error('Erro ao parar servidor:', err);
      return false;
    } finally {
      setLoading(false);
    }
  }, [refreshStatus]);

  const restartServer = useCallback(async (): Promise<boolean> => {
    try {
      setLoading(true);
      setError(null);
      
      const response = await serverService.restartServer();
      
      if (response.success) {
        // Aguardar um pouco antes de atualizar o status
        setTimeout(() => {
          refreshStatus();
        }, 3000);
        return true;
      } else {
        setError(response.error || 'Erro ao reiniciar servidor');
        return false;
      }
    } catch (err) {
      setError('Erro de conexão com o servidor');
      console.error('Erro ao reiniciar servidor:', err);
      return false;
    } finally {
      setLoading(false);
    }
  }, [refreshStatus]);

  // Auto-refresh do status
  useEffect(() => {
    if (autoRefresh) {
      refreshStatus();
      // REMOVIDO: Atualização automática - agora é manual
      // const interval = setInterval(refreshStatus, refreshInterval);
      // return () => clearInterval(interval);
    }
  }, [autoRefresh, refreshInterval, refreshStatus]);

  return {
    status,
    config,
    loading,
    error,
    lastUpdate,
    refreshStatus,
    startServer,
    stopServer,
    restartServer
  };
}; 