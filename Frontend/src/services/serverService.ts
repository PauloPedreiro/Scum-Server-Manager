import api from './api';
import { 
  ApiResponse,
  ServerStatusResponse
} from '../types/server';

// Classe para gerenciar o servidor SCUM
class ServerManager {
  private baseUrl = '/server';

  // Obter status do servidor
  async getStatus(): Promise<ServerStatusResponse> {
    try {
      const response = await api.get(`${this.baseUrl}/status`);
      return response.data;
    } catch (error: any) {
      console.error('Erro na requisição:', error);
      return {
        success: false,
        error: 'Erro ao conectar com o servidor',
        status: null as any,
        config: null as any
      };
    }
  }

  // Iniciar servidor
  async startServer(): Promise<ApiResponse<{message: string}>> {
    try {
      const response = await api.post(`${this.baseUrl}/start`, {});
      return response.data;
    } catch (error: any) {
      return {
        success: false,
        error: 'Erro ao conectar com o servidor'
      };
    }
  }

  // Parar servidor
  async stopServer(): Promise<ApiResponse<{message: string}>> {
    try {
      const response = await api.post(`${this.baseUrl}/stop`, {});
      return response.data;
    } catch (error: any) {
      return {
        success: false,
        error: 'Erro ao conectar com o servidor'
      };
    }
  }

  // Reiniciar servidor
  async restartServer(): Promise<ApiResponse<{message: string}>> {
    try {
      const response = await api.post(`${this.baseUrl}/restart`, {});
      return response.data;
    } catch (error: any) {
      return {
        success: false,
        error: 'Erro ao conectar com o servidor'
      };
    }
  }
}

// Instância única do gerenciador de servidor
export const serverService = new ServerManager(); 