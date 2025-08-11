import { buildApiUrl, API_CONFIG } from '../config/api';

export interface LoginRequest {
  username: string;
  password: string;
}

export interface LoginResponse {
  success: boolean;
  message?: string;
  data?: {
    token: string;
    user: User;
  };
}

export interface User {
  id: string;
  username: string;
  steamId?: string | null;
  role: string;
  permissions: string[];
  profile: {
    firstName: string;
    lastName: string;
    avatar?: string | null;
    timezone: string;
    language: string;
  };
  isFirstLogin: boolean;
  requiresPasswordChange: boolean;
}

export interface AuthLog {
  id: string;
  timestamp: string;
  username: string;
  action: string;
  ip: string;
  success: boolean;
}

export interface ChangePasswordRequest {
  currentPassword: string;
  newPassword: string;
}

export interface ChangePasswordResponse {
  success: boolean;
  message?: string;
}

export interface LogsResponse {
  success: boolean;
  message?: string;
  data?: {
    logs: AuthLog[];
  };
}

class AuthService {
  private baseURL: string;
  private tokenKey: string;
  private userKey: string;

  constructor() {
    this.baseURL = '/api/auth';
    this.tokenKey = 'scum_auth_token';
    this.userKey = 'scum_user_data';
  }

  // Login
  async login(username: string, password: string): Promise<LoginResponse> {
    try {
      console.log('[AUTH] Tentando login:', { username });
      
      const response = await fetch(`${this.baseURL}/login`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ username, password })
      });

      const data = await response.json();
      console.log('[AUTH] Resposta do login:', data);

      if (data.success) {
        // Salvar token e dados do usuário
        localStorage.setItem(this.tokenKey, data.data.token);
        localStorage.setItem(this.userKey, JSON.stringify(data.data.user));
        
        console.log('[AUTH] Dados salvos no localStorage:', {
          token: data.data.token,
          user: data.data.user
        });
        
        return {
          success: true,
          message: data.message,
          data: {
            token: data.data.token,
            user: data.data.user
          }
        };
      } else {
        return {
          success: false,
          message: data.message || 'Credenciais inválidas'
        };
      }
    } catch (error) {
      console.error('[AUTH] Erro no login:', error);
      return {
        success: false,
        message: 'Erro de conexão com o servidor'
      };
    }
  }

  // Logout
  async logout(): Promise<void> {
    try {
      const token = this.getToken();
      
      if (token) {
        await fetch(`${this.baseURL}/logout`, {
          method: 'POST',
          headers: {
            'Authorization': `Bearer ${token}`
          }
        });
      }
    } catch (error) {
      console.error('[AUTH] Erro no logout:', error);
    } finally {
      // Limpar dados locais
      localStorage.removeItem(this.tokenKey);
      localStorage.removeItem(this.userKey);
    }
  }

  // Verificar dados do usuário
  async getMe(): Promise<{ success: boolean; message?: string; data?: User }> {
    try {
      const token = this.getToken();
      
      if (!token) {
        return { success: false, message: 'Não autenticado' };
      }

      const response = await fetch(`${this.baseURL}/me`, {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });

      const data = await response.json();
      return data;
    } catch (error) {
      console.error('[AUTH] Erro ao verificar usuário:', error);
      return { success: false, message: 'Erro de conexão' };
    }
  }

  // Buscar logs (apenas admin)
  async getLogs(): Promise<LogsResponse> {
    try {
      const token = this.getToken();
      
      if (!token) {
        return { success: false, message: 'Não autenticado' };
      }

      const response = await fetch(`${this.baseURL}/logs`, {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });

      const data = await response.json();
      return data;
    } catch (error) {
      console.error('[AUTH] Erro ao buscar logs:', error);
      return { success: false, message: 'Erro de conexão' };
    }
  }

  // Alterar senha
  async changePassword(currentPassword: string, newPassword: string): Promise<ChangePasswordResponse> {
    try {
      const token = this.getToken();
      
      if (!token) {
        return { success: false, message: 'Não autenticado' };
      }

      const response = await fetch(`${this.baseURL}/change-password`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({ currentPassword, newPassword })
      });

      const data = await response.json();
      return data;
    } catch (error) {
      console.error('[AUTH] Erro ao alterar senha:', error);
      return { success: false, message: 'Erro de conexão' };
    }
  }

  // Utilitários
  getToken(): string | null {
    return localStorage.getItem(this.tokenKey);
  }

  getUser(): User | null {
    const userData = localStorage.getItem(this.userKey);
    return userData ? JSON.parse(userData) : null;
  }

  isAuthenticated(): boolean {
    return !!this.getToken();
  }

  isAdmin(): boolean {
    const user = this.getUser();
    return user && user.role === 'admin';
  }

  // Verificar se o token ainda é válido
  async verify(): Promise<{ success: boolean; user?: User }> {
    try {
      const token = this.getToken();
      console.log('[AUTH] Verificando token:', !!token);
      
      if (!token) {
        console.log('[AUTH] Nenhum token encontrado');
        return { success: false };
      }

      const result = await this.getMe();
      console.log('[AUTH] Resultado da verificação:', result);
      
      if (result.success && result.data) {
        return { success: true, user: result.data };
      } else {
        // Token inválido, limpar dados
        console.log('[AUTH] Token inválido, limpando dados');
        localStorage.removeItem(this.tokenKey);
        localStorage.removeItem(this.userKey);
        return { success: false };
      }
    } catch (error) {
      console.error('[AUTH] Erro ao verificar token:', error);
      return { success: false };
    }
  }
}

export default new AuthService(); 