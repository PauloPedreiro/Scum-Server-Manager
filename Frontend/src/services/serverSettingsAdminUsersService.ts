import { buildApiUrl, API_CONFIG } from '../config/api';

export interface ServerSettingsAdminUser {
  steamId: string;
  name?: string;
  level?: string;
}

export interface ServerSettingsAdminUsersResponse {
  success: boolean;
  message?: string;
  admins?: ServerSettingsAdminUser[];
  admin?: ServerSettingsAdminUser;
  backupCreated?: string;
}

export class ServerSettingsAdminUsersService {
  // Buscar todos os administradores de configuração
  static async getServerSettingsAdminUsers(): Promise<ServerSettingsAdminUsersResponse> {
    try {
      const response = await fetch(buildApiUrl(API_CONFIG.ENDPOINTS.SERVER_SETTINGS_ADMIN_USERS));
      const data = await response.json();
      
      // Mapear a resposta do backend para o formato esperado
      if (data.success && data.adminUsers) {
        console.log('Mapping adminUsers response:', data.adminUsers);
        const mappedAdmins = data.adminUsers.map((admin: any) => ({
          steamId: admin.steamId,
          name: admin.playerName || admin.name,
          level: admin.level
        }));
        console.log('Mapped admins:', mappedAdmins);
        return {
          success: true,
          admins: mappedAdmins
        };
      }
      
      return data;
    } catch (error) {
      return {
        success: false,
        message: 'Erro de conexão'
      };
    }
  }

  // Adicionar administrador de configuração
  static async addServerSettingsAdminUser(steamId: string): Promise<ServerSettingsAdminUsersResponse> {
    try {
      const response = await fetch(buildApiUrl(API_CONFIG.ENDPOINTS.SERVER_SETTINGS_ADMIN_USERS), {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ steamId })
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

  // Remover administrador de configuração
  static async removeServerSettingsAdminUser(steamId: string): Promise<ServerSettingsAdminUsersResponse> {
    try {
      const response = await fetch(buildApiUrl(API_CONFIG.ENDPOINTS.SERVER_SETTINGS_ADMIN_USERS), {
        method: 'DELETE',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ steamId })
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

  // Atualizar administrador de configuração
  static async updateServerSettingsAdminUser(steamId: string, admin: ServerSettingsAdminUser): Promise<ServerSettingsAdminUsersResponse> {
    try {
      const response = await fetch(buildApiUrl(API_CONFIG.ENDPOINTS.SERVER_SETTINGS_ADMIN_USERS), {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ steamId, ...admin })
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
  static async updateServerSettingsAdminUsersBulk(admins: ServerSettingsAdminUser[]): Promise<ServerSettingsAdminUsersResponse> {
    try {
      const response = await fetch(buildApiUrl(API_CONFIG.ENDPOINTS.SERVER_SETTINGS_ADMIN_USERS), {
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