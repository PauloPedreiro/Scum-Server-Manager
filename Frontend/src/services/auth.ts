import axios from 'axios';
import { getApiBaseURL } from './configLoader';

// Função helper para obter a URL base da API (sempre atualizada)
async function getApiBaseURLAsync(): Promise<string> {
  return await getApiBaseURL();
}

// Interfaces
export interface LoginResponse {
  success: boolean;
  data?: {
    token?: string;
    username?: string;
    role?: string;
    must_link_discord?: boolean;
    expires_in?: number;
    must_change_password?: boolean;
    message?: string;
  };
  error?: string;
}

export interface User {
  id: number;
  username: string;
  role: string;
  password_changed: boolean;
  discord_user_id?: string | null;
  must_link_discord?: boolean;
  is_active?: boolean;
  steam_id?: string | null;
  player_name?: string | null;
  player_id?: number | null;
  last_login?: string | null;
  created_at?: string;
}

export interface DiscordLinkCodeResponse {
  success: boolean;
  data?: {
    code: string;
    expires_in_minutes: number;
    command: string;
  };
  error?: string;
  code?: string;
}

export interface CreateUserResponse {
  success: boolean;
  data?: {
    id?: number;
    username: string;
    role: string;
    is_active?: boolean;
    password_changed?: boolean;
    steam_id?: string | null;
    player_name?: string | null;
    created_at?: string;
    message?: string;
  };
  error?: string;
}

export interface ListUsersResponse {
  success: boolean;
  data?: {
    users?: User[];
    total?: number;
  };
  users?: User[];
  error?: string;
}

export interface UpdateUserResponse {
  success: boolean;
  data?: User;
  error?: string;
}

export interface Player {
  steam_id: string;
  name: string;
  id: number;
}

export interface SearchPlayersResponse {
  success: boolean;
  data?: {
    players: Player[];
    total: number;
  };
  error?: string;
}

export interface ChangePasswordResponse {
  success: boolean;
  data?: {
    token?: string;
    message?: string;
    password_changed?: boolean;
    role?: string;
    must_link_discord?: boolean;
    expires_in?: number;
  };
  error?: string;
}

export interface RequestPasswordResetResponse {
  success: boolean;
  message: string;
}

export interface ResetPasswordResponse {
  success: boolean;
  message?: string;
  error?: string;
}

export interface MeResponse {
  success: boolean;
  data?: User;
  error?: string;
  code?: string;
}

class AuthService {
  private tokenKey = 'ssm_auth_token';
  private userKey = 'ssm_user';
  private rememberMeKey = 'ssm_remember_me';

  private requiresDiscordLink(user: Pick<User, 'role' | 'discord_user_id' | 'must_link_discord'>): boolean {
    if (user.must_link_discord === true) return true;
    if (user.must_link_discord === false) return false;
    if (user.role === 'admin_pending') return true;
    if (user.role === 'admin' && !user.discord_user_id) return true;
    return false;
  }
  
  // Determinar qual storage usar baseado em "Lembrar-me"
  private getStorage(): Storage {
    const rememberMe = localStorage.getItem(this.rememberMeKey) === 'true';
    return rememberMe ? localStorage : sessionStorage;
  }
  
  // Limpar de ambos storages
  private clearFromAllStorages(key: string): void {
    localStorage.removeItem(key);
    sessionStorage.removeItem(key);
  }

  // Login
  async login(username: string, password: string, rememberMe: boolean = false): Promise<LoginResponse> {
    try {
      const baseURL = await getApiBaseURLAsync();
      const response = await axios.post<LoginResponse>(
        `${baseURL}/auth/login`,
        { username, password },
        {
          headers: {
            'Content-Type': 'application/json',
          },
        }
      );

      const data = response.data;

      if (data.success && data.data?.token) {
        const storage = rememberMe ? localStorage : sessionStorage;
        
        // Armazenar preferência "Lembrar-me"
        if (rememberMe) {
          localStorage.setItem(this.rememberMeKey, 'true');
        } else {
          localStorage.removeItem(this.rememberMeKey);
        }
        
        // Armazenar token no storage apropriado
        storage.setItem(this.tokenKey, data.data.token);
        
        // Armazenar dados do usuário
        if (data.data.username && data.data.role) {
          storage.setItem(this.userKey, JSON.stringify({
            username: data.data.username,
            role: data.data.role,
          }));
        }
      }

      return data;
    } catch (error: any) {
      if (error.response?.data) {
        return error.response.data;
      }
      return {
        success: false,
        error: error.message || 'Erro ao fazer login',
      };
    }
  }

  // Mudar senha
  async changePassword(
    currentPassword: string,
    newPassword: string,
    username?: string
  ): Promise<ChangePasswordResponse> {
    try {
      const token = this.getToken();
      const headers: Record<string, string> = {
        'Content-Type': 'application/json',
      };

      if (token) {
        headers['Authorization'] = `Bearer ${token}`;
      }

      const body: any = {
        current_password: currentPassword,
        new_password: newPassword,
      };

      if (username) {
        body.username = username;
      }

      const baseURL = await getApiBaseURLAsync();
      const response = await axios.post<ChangePasswordResponse>(
        `${baseURL}/auth/change-password`,
        body,
        { headers }
      );

      const data = response.data;

      if (data.success && data.data?.token) {
        // Atualizar token
        const storage = this.getStorage();
        storage.setItem(this.tokenKey, data.data.token);

        // Atualizar role em cache, se backend retornar (mantém UI consistente)
        if (data.data.role) {
          const current = this.getUserFromStorage();
          if (current?.username) {
            storage.setItem(
              this.userKey,
              JSON.stringify({
                username: current.username,
                role: data.data.role,
              })
            );
          }
        }
      }

      return data;
    } catch (error: any) {
      if (error.response?.data) {
        return error.response.data;
      }
      return {
        success: false,
        error: error.message || 'Erro ao alterar senha',
      };
    }
  }

  // Obter usuário atual
  async getCurrentUser(): Promise<User | null> {
    const token = this.getToken();
    if (!token) return null;

    try {
      const baseURL = await getApiBaseURLAsync();
      const response = await axios.get<MeResponse>(
        `${baseURL}/auth/me`,
        {
          headers: {
            'Authorization': `Bearer ${token}`,
          },
        }
      );

      if (response.status === 401) {
        // Token inválido/expirado
        this.logout();
        return null;
      }

      const data = response.data;
      if (data.success && data.data) {
        // Atualizar cache básico do usuário (role/username) para manter UI consistente
        try {
          const storage = this.getStorage();
          storage.setItem(
            this.userKey,
            JSON.stringify({
              username: data.data.username,
              role: data.data.role,
            })
          );
        } catch {
          // ignore
        }
        return data.data;
      }
    } catch (error: any) {
      if (error.response?.status === 401) {
        // Token inválido/expirado
        this.logout();
        return null;
      }
      if (import.meta.env.DEV) {
        console.error('Erro ao obter usuário:', error);
      } else {
        console.error('Erro ao obter usuário');
      }
    }

    return null;
  }

  // Logout
  async logout(): Promise<void> {
    const token = this.getToken();
    
    if (token) {
      try {
        const baseURL = await getApiBaseURLAsync();
        await axios.post(
          `${baseURL}/auth/logout`,
          {},
          {
            headers: {
              'Authorization': `Bearer ${token}`,
            },
          }
        );
      } catch (error) {
        if (import.meta.env.DEV) {
          console.error('Erro no logout:', error);
        } else {
          console.error('Erro no logout');
        }
      }
    }

    // Remover token e dados do usuário de ambos storages
    this.clearFromAllStorages(this.tokenKey);
    this.clearFromAllStorages(this.userKey);
    localStorage.removeItem(this.rememberMeKey);
  }

  // Verificar se está autenticado (verifica token e validade)
  isAuthenticated(): boolean {
    const token = this.getToken();
    if (!token) return false;
    
    // Verificar se token é válido (não expirado)
    try {
      // Verificar se é um JWT válido (formato: header.payload.signature)
      const parts = token.split('.');
      if (parts.length !== 3) {
        // Não é um JWT válido, mas pode ser outro formato de token
        // Retornar true e deixar backend validar
        return true;
      }
      
      // Decodificar payload do JWT para verificar expiração
      const payload = JSON.parse(atob(parts[1]));
      const exp = payload.exp;
      
      // Se tem campo exp e está expirado, limpar token
      if (exp && typeof exp === 'number' && exp * 1000 < Date.now()) {
        // Token expirado, limpar
        this.logout();
        return false;
      }
      
      return true;
    } catch (error) {
      // Se não conseguir decodificar, pode ser token em outro formato
      // Retornar true e deixar backend validar na próxima requisição
      // Não fazer logout aqui para evitar loops
      return true;
    }
  }

  // Obter token (verifica ambos storages)
  getToken(): string | null {
    // Verificar sessionStorage primeiro (mais seguro)
    const sessionToken = sessionStorage.getItem(this.tokenKey);
    if (sessionToken) return sessionToken;
    
    // Verificar localStorage se "Lembrar-me" estiver ativo
    const rememberMe = localStorage.getItem(this.rememberMeKey) === 'true';
    if (rememberMe) {
      return localStorage.getItem(this.tokenKey);
    }
    
    return null;
  }

  // Obter dados do usuário do storage apropriado
  getUserFromStorage(): { username: string; role: string } | null {
    const storage = this.getStorage();
    const userStr = storage.getItem(this.userKey);
    if (userStr) {
      try {
        return JSON.parse(userStr);
      } catch {
        return null;
      }
    }
    return null;
  }

  // Verificar se é admin
  isAdmin(): boolean {
    const user = this.getUserFromStorage();
    return user?.role === 'admin' || user?.role === 'admin_pending';
  }

  mustLinkDiscordFromUser(user: Pick<User, 'role' | 'discord_user_id' | 'must_link_discord'>): boolean {
    return this.requiresDiscordLink(user);
  }

  // Gerar código de vinculação Discord (Admin)
  async generateDiscordLinkCode(): Promise<DiscordLinkCodeResponse> {
    const token = this.getToken();
    if (!token) {
      return {
        success: false,
        error: 'Not authenticated',
      };
    }

    try {
      const baseURL = await getApiBaseURLAsync();
      const response = await axios.post<DiscordLinkCodeResponse>(
        `${baseURL}/auth/discord-link-code`,
        {},
        {
          headers: {
            Authorization: `Bearer ${token}`,
          },
        }
      );
      return response.data;
    } catch (error: any) {
      if (error.response?.data) {
        return error.response.data;
      }
      return {
        success: false,
        error: error.message || 'Erro ao gerar código de vinculação',
      };
    }
  }

  // ========== GERENCIAMENTO DE USUÁRIOS (ADMIN APENAS) ==========

  // Criar usuário
  async createUser(
    username: string,
    password: string,
    role: 'admin' | 'moderator' = 'moderator',
    steamId?: string
  ): Promise<CreateUserResponse> {
    const token = this.getToken();
    if (!token) {
      return {
        success: false,
        error: 'Not authenticated',
      };
    }

    try {
      const response = await axios.post<CreateUserResponse>(
        `${await getApiBaseURLAsync()}/auth/users`,
        {
          username,
          password,
          role,
          steam_id: steamId,
        },
        {
          headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${token}`,
          },
        }
      );

      // Se o status HTTP é 201 (Created), considerar sucesso mesmo se success=false
      if (response.status === 201 || response.status === 200) {
        // Se a resposta tem success: true, retornar normalmente
        if (response.data && response.data.success) {
          return response.data;
        }

        // Se o status é 201 mas success=false, pode ter sido criado mas com algum problema secundário
        // (ex: erro ao buscar player vinculado, mas usuário foi criado)
        if (response.status === 201) {
          if (import.meta.env.DEV) {
            console.warn('Usuário criado (201) mas resposta indica erro');
          }
          return {
            success: true,
            data: response.data?.data || {
              username,
              role,
              steam_id: steamId || null,
            },
          };
        }

        // Se a resposta tem success: false mas tem estrutura válida, retornar
        if (response.data && typeof response.data.success === 'boolean') {
          return response.data;
        }

        // Se chegou aqui, a resposta não tem a estrutura esperada mas status é OK
        if (import.meta.env.DEV) {
          console.warn('Resposta do backend não tem estrutura esperada');
        }
        return {
          success: true,
          data: response.data as any,
        };
      }

      // Se chegou aqui, status não é 201/200
      return response.data || {
        success: false,
        error: 'Resposta inesperada do servidor',
      };
    } catch (error: any) {
      if (import.meta.env.DEV) {
        console.error('Erro completo ao criar usuário:', error);
      } else {
        console.error('Erro ao criar usuário');
      }
      
      // Se o erro tem response.data, usar ele
      if (error.response?.data) {
        const errorData = error.response.data;
        const errorMessage = errorData.error || errorData.message || 'Erro desconhecido';
        
        // Se o status é 201 (Created), mesmo com erro na resposta, foi criado
        if (error.response.status === 201) {
          if (import.meta.env.DEV) {
            console.warn('Status 201 mas resposta indica erro');
          }
          return {
            success: true,
            data: errorData.data || {
              username,
              role,
              steam_id: steamId || null,
            },
          };
        }
        
        // Se o erro é 500 mas a mensagem indica problema no logger (não crítico)
        // e o usuário pode ter sido criado mesmo assim
        if (error.response.status === 500 && 
            (errorMessage.includes('exc_info') || errorMessage.includes('StructuredLogger'))) {
          if (import.meta.env.DEV) {
            console.warn('Erro 500 no logger, mas usuário pode ter sido criado');
          }
          // Retornar como sucesso parcial - o usuário provavelmente foi criado
          return {
            success: true,
            data: {
              username,
              role,
              steam_id: steamId || null,
            },
          };
        }
        
        return {
          success: false,
          error: errorMessage,
        };
      }
      
      // Se o erro é de rede ou outro tipo
      return {
        success: false,
        error: error.message || 'Erro ao criar usuário',
      };
    }
  }

  // Listar usuários
  async listUsers(): Promise<User[]> {
    const token = this.getToken();
    if (!token) {
      throw new Error('Not authenticated');
    }

    try {
      const response = await axios.get<ListUsersResponse>(
        `${await getApiBaseURLAsync()}/auth/users`,
        {
          headers: {
            'Authorization': `Bearer ${token}`,
          },
        }
      );

      // Log apenas em desenvolvimento
      if (import.meta.env.DEV) {
        console.log('ListUsers - Response status:', response.status);
      }

      if (response.status === 401) {
        this.logout();
        throw new Error('Not authenticated');
      }

      const data = response.data;
      // Log apenas em desenvolvimento, sem dados sensíveis
      if (import.meta.env.DEV) {
        console.log('ListUsers - Resposta recebida');
      }

      // Se não tem success ou data, verificar se há erro
      if (!data.success) {
        const errorMsg = data.error || 'Erro ao listar usuários';
        if (import.meta.env.DEV) {
          console.error('ListUsers - Erro na resposta:', errorMsg);
        } else {
          console.error('ListUsers - Erro na resposta');
        }
        throw new Error(errorMsg);
      }

      // Verificar se data existe
      if (!data.data) {
        if (import.meta.env.DEV) {
          console.warn('ListUsers - Resposta sem data');
        }
        // Se success é true mas não tem data, pode ser que o backend retornou estrutura diferente
        // Tentar acessar diretamente data.users ou retornar array vazio
        if (data.users && Array.isArray(data.users)) {
          if (import.meta.env.DEV) {
            console.log('ListUsers - Usuários encontrados:', data.users.length);
          }
          return data.users;
        }
        if (import.meta.env.DEV) {
          console.warn('ListUsers - Retornando array vazio (sem dados)');
        }
        return [];
      }

      // Verificar se data.data é um objeto vazio
      if (Object.keys(data.data).length === 0) {
        if (import.meta.env.DEV) {
          console.warn('ListUsers - data.data está vazio');
        }
        return [];
      }

      // Verificar se users existe e é um array
      if (!data.data.users || !Array.isArray(data.data.users)) {
        if (import.meta.env.DEV) {
          console.warn('ListUsers - users não é um array');
        }
        // Tentar acessar diretamente em data.users (fallback)
        if (data.users && Array.isArray(data.users)) {
          if (import.meta.env.DEV) {
            console.log('ListUsers - Usuários encontrados (fallback):', data.users.length);
          }
          return data.users;
        }
        // Se não tem users mas tem sucesso, retornar array vazio
        if (import.meta.env.DEV) {
          console.warn('ListUsers - Retornando array vazio (users não encontrado)');
        }
        return [];
      }

      if (import.meta.env.DEV) {
        console.log('ListUsers - Usuários retornados:', data.data.users.length);
      }
      return data.data.users;
    } catch (error: any) {
      if (import.meta.env.DEV) {
        console.error('ListUsers - Erro completo:', error);
        if (error.response?.data) {
          console.error('ListUsers - Erro do backend');
        }
      } else {
        console.error('ListUsers - Erro ao listar usuários');
      }
      
      if (error.response?.status === 401) {
        this.logout();
        throw new Error('Not authenticated');
      }
      
      throw error;
    }
  }

  // Atualizar usuário
  async updateUser(
    userId: number,
    updates: {
      is_active?: boolean;
      role?: 'admin' | 'moderator';
      steam_id?: string | null;
    }
  ): Promise<UpdateUserResponse> {
    const token = this.getToken();
    if (!token) {
      return {
        success: false,
        error: 'Not authenticated',
      };
    }

    try {
      // Preparar o body - garantir que steam_id seja string ou null (não undefined)
      const body: any = {};
      if (updates.is_active !== undefined) {
        body.is_active = updates.is_active;
      }
      if (updates.role !== undefined) {
        body.role = updates.role;
      }
      if (updates.steam_id !== undefined) {
        // Se steam_id é string vazia, converter para null
        body.steam_id = updates.steam_id === '' ? null : updates.steam_id;
      }

      console.log('UpdateUser - Enviando:', { userId, body });

      const response = await axios.put<UpdateUserResponse>(
        `${await getApiBaseURLAsync()}/auth/users/${userId}`,
        body,
        {
          headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${token}`,
          },
        }
      );

      if (import.meta.env.DEV) {
        console.log('UpdateUser - Usuário atualizado');
      }
      return response.data;
    } catch (error: any) {
      if (import.meta.env.DEV) {
        console.error('UpdateUser - Erro completo:', error);
      } else {
        console.error('UpdateUser - Erro ao atualizar usuário');
      }
      
      if (error.response?.data) {
        return error.response.data;
      }
      return {
        success: false,
        error: error.message || 'Erro ao atualizar usuário',
      };
    }
  }

  // Deletar usuário
  async deleteUser(userId: number): Promise<{ success: boolean; message?: string; error?: string }> {
    const token = this.getToken();
    if (!token) {
      return {
        success: false,
        error: 'Not authenticated',
      };
    }

    try {
      const response = await axios.delete<{ success: boolean; message?: string; error?: string }>(
        `${await getApiBaseURLAsync()}/auth/users/${userId}`,
        {
          headers: {
            'Authorization': `Bearer ${token}`,
          },
        }
      );

      return response.data;
    } catch (error: any) {
      if (error.response?.data) {
        return error.response.data;
      }
      return {
        success: false,
        error: error.message || 'Erro ao deletar usuário',
      };
    }
  }

  // Buscar players
  async searchPlayers(query: string, limit: number = 20): Promise<Player[]> {
    const token = this.getToken();
    if (!token) {
      throw new Error('Not authenticated');
    }

    try {
      const response = await axios.get<SearchPlayersResponse>(
        `${await getApiBaseURLAsync()}/auth/users/search-players`,
        {
          params: {
            q: query,
            limit,
          },
          headers: {
            'Authorization': `Bearer ${token}`,
          },
        }
      );

      if (response.status === 401) {
        this.logout();
        throw new Error('Not authenticated');
      }

      const data = response.data;

      if (!data.success || !data.data) {
        throw new Error(data.error || 'Erro ao buscar players');
      }

      return data.data.players;
    } catch (error: any) {
      if (error.response?.status === 401) {
        this.logout();
        throw new Error('Not authenticated');
      }
      throw error;
    }
  }

  // Request password reset
  async requestPasswordReset(username: string): Promise<RequestPasswordResetResponse> {
    try {
      const response = await axios.post<RequestPasswordResetResponse>(
        `${await getApiBaseURLAsync()}/auth/request-password-reset`,
        { username },
        {
          headers: {
            'Content-Type': 'application/json',
          },
        }
      );
      return response.data;
    } catch (error: any) {
      if (error.response?.data) {
        return error.response.data;
      }
      return {
        success: false,
        message: error.message || 'Erro ao solicitar reset de senha',
      };
    }
  }

  // Reset password with token
  async resetPassword(token: string, newPassword: string): Promise<ResetPasswordResponse> {
    try {
      const response = await axios.post<ResetPasswordResponse>(
        `${await getApiBaseURLAsync()}/auth/reset-password`,
        {
          token,
          new_password: newPassword,
        },
        {
          headers: {
            'Content-Type': 'application/json',
          },
        }
      );
      return response.data;
    } catch (error: any) {
      if (error.response?.data) {
        return error.response.data;
      }
      return {
        success: false,
        error: error.message || 'Erro ao resetar senha',
      };
    }
  }
}

export const authService = new AuthService();

