import axios from 'axios';
import { LoginRequest, LoginResponse } from '../types/auth';

// Configuração da API com proxy do Vite
const api = axios.create({
  baseURL: '/api',
  headers: {
    'Content-Type': 'application/json',
  },
});

// Interceptor para adicionar token em todas as requisições
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Interceptor para tratar erros de autenticação
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('token');
      localStorage.removeItem('user');
      window.location.href = '/login';
    }
    return Promise.reject(error);
  }
);

// Serviço de autenticação MOCKADO
export const authService = {
  login: async (credentials: LoginRequest): Promise<LoginResponse> => {
    // Simular delay de rede
    await new Promise(resolve => setTimeout(resolve, 1000));
    
    // Credenciais mockadas
    if (credentials.username === 'admin' && credentials.password === '123456') {
      const mockToken = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VySWQiOiIxIiwidXNlcm5hbWUiOiJhZG1pbiIsInJvbGUiOiJhZG1pbiIsInBlcm1pc3Npb25zIjpbInJlYWRfbG9ncyIsIndyaXRlX2xvZ3MiLCJyZWFkX3BsYXllcnMiLCJ3cml0ZV9wbGF5ZXJzIiwibWFuYWdlX3VzZXJzIiwibWFuYWdlX3dlYmhvb2tzIiwibWFuYWdlX2NvbmZpZyIsImV4ZWN1dGVfY29tbWFuZHMiLCJ2aWV3X2FuYWx5dGljcyIsIm1hbmFnZV9iYWNrdXBzIl0sImlzRmlyc3RMb2dpbiI6ZmFsc2UsInJlcXVpcmVzUGFzc3dvcmRDaGFuZ2UiOmZhbHNlLCJpYXQiOjE3NTIyOTM3NjksImV4cCI6MTc1MjM4MDE2OX0.sjczQWW2TcDlumn-LWwdJLzvgudzJXQhjGikexDWZY0';
      
      const mockUser = {
        id: '1',
        username: 'admin',
        steamId: null,
        role: 'admin',
        permissions: [
          'read_logs',
          'write_logs',
          'read_players',
          'write_players',
          'manage_users',
          'manage_webhooks',
          'manage_config',
          'execute_commands',
          'view_analytics',
          'manage_backups'
        ],
        profile: {
          firstName: 'Admin',
          lastName: 'User',
          avatar: null,
          timezone: 'America/Sao_Paulo',
          language: 'pt-BR'
        },
        isFirstLogin: false,
        requiresPasswordChange: false
      };

      // Salvar no localStorage
      localStorage.setItem('token', mockToken);
      localStorage.setItem('user', JSON.stringify(mockUser));

      return {
        success: true,
        message: 'Login realizado com sucesso',
        data: {
          token: mockToken,
          user: mockUser
        }
      };
    } else {
      // Simular erro de credenciais inválidas
      throw new Error('Credenciais inválidas');
    }
  },

  verify: async (): Promise<{ success: boolean; user: any }> => {
    // Simular delay
    await new Promise(resolve => setTimeout(resolve, 500));
    
    const token = localStorage.getItem('token');
    const user = localStorage.getItem('user');
    
    if (token && user) {
      return {
        success: true,
        user: JSON.parse(user)
      };
    } else {
      return {
        success: false,
        user: null
      };
    }
  },

  logout: async (): Promise<void> => {
    // Simular delay
    await new Promise(resolve => setTimeout(resolve, 500));
    
    // Limpar localStorage
    localStorage.removeItem('token');
    localStorage.removeItem('user');
  },
};

// Serviço básico para dados do dashboard (MOCKADO)
export const dashboardService = {
  getServerStatus: async (): Promise<{ status: string }> => {
    // Simular delay
    await new Promise(resolve => setTimeout(resolve, 800));
    
    return {
      status: 'online'
    };
  },

  getOnlinePlayers: async (): Promise<{ totalOnline: number }> => {
    // Simular delay
    await new Promise(resolve => setTimeout(resolve, 600));
    
    return {
      totalOnline: Math.floor(Math.random() * 20) + 5 // Número aleatório entre 5-25
    };
  },
};

export default api; 