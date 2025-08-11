import { buildApiUrl, API_CONFIG } from '../config/api';

export interface AdminUser {
  steamId: string;
  name?: string;
  level?: string;
}

export interface AdminUsersResponse {
  success: boolean;
  message?: string;
  admins?: AdminUser[];
  admin?: AdminUser;
}

export class AdminUsersService {
  // Buscar todos os administradores
  static async getAdminUsers(): Promise<AdminUsersResponse> {
    try {
      const response = await fetch(buildApiUrl(API_CONFIG.ENDPOINTS.ADMIN_USERS));
      const data = await response.json();
      return data;
    } catch (error) {
      return {
        success: false,
        message: 'Erro de conexão'
      };
    }
  }

  // Adicionar administrador (apenas steamId)
  static async addAdminUser(steamId: string | { steamId: string }): Promise<AdminUsersResponse> {
    try {
      const steamIdValue = typeof steamId === 'string' ? steamId : steamId.steamId;
      
      const response = await fetch(buildApiUrl(API_CONFIG.ENDPOINTS.ADMIN_USERS), {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ steamId: steamIdValue })
      });
      const data = await response.json();
      return data;
    } catch (error) {
      return {
        success: false,
        message: 'Erro de conexão'
      };
    }
  }

  // Atualizar administrador
  static async updateAdminUser(steamId: string, admin: AdminUser): Promise<AdminUsersResponse> {
    try {
      const response = await fetch(buildApiUrl(`${API_CONFIG.ENDPOINTS.ADMIN_USERS}/${steamId}`), {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(admin)
      });
      const data = await response.json();
      return data;
    } catch (error) {
      return {
        success: false,
        message: 'Erro de conexão'
      };
    }
  }

  // Remover administrador
  static async removeAdminUser(steamId: string): Promise<AdminUsersResponse> {
    try {
      const response = await fetch(buildApiUrl(`${API_CONFIG.ENDPOINTS.ADMIN_USERS}/${steamId}`), {
        method: 'DELETE'
      });
      const data = await response.json();
      return data;
    } catch (error) {
      return {
        success: false,
        message: 'Erro de conexão'
      };
    }
  }

  // Atualizar em massa
  static async updateAdminUsersBulk(admins: AdminUser[]): Promise<AdminUsersResponse> {
    try {
      const response = await fetch(buildApiUrl(API_CONFIG.ENDPOINTS.ADMIN_USERS), {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ admins })
      });
      const data = await response.json();
      return data;
    } catch (error) {
      return {
        success: false,
        message: 'Erro de conexão'
      };
    }
  }
} 