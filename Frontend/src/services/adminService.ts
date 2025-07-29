import { buildApiUrl } from '../config/api';

export interface Admin {
  steamId: string;
  playerName: string;
}

export interface AdminListResponse {
  success: boolean;
  admins: Admin[];
  stats: {
    size: number;
    modified: string;
    created: string;
  };
  error?: string;
}

export interface AdminAddResponse {
  success: boolean;
  message: string;
  backupCreated: string;
  error?: string;
}

export interface AdminReplaceResponse {
  success: boolean;
  message: string;
  backupCreated: string;
  linesCount: number;
  error?: string;
}

export interface AdminRemoveResponse {
  success: boolean;
  message: string;
  backupCreated: string;
  error?: string;
}

export const AdminService = {
  async listAdmins(): Promise<AdminListResponse> {
    const response = await fetch(buildApiUrl('/api/configserver/AdminUsers.ini'));
    return await response.json();
  },

  async addAdmin(steamId: string): Promise<AdminAddResponse> {
    const response = await fetch(buildApiUrl('/api/configserver/AdminUsers.ini'), {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ steamId })
    });
    return await response.json();
  },

  async removeAdmin(steamId: string): Promise<AdminRemoveResponse> {
    const response = await fetch(buildApiUrl('/api/configserver/AdminUsers.ini'), {
      method: 'DELETE',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ steamId })
    });
    return await response.json();
  },

  async replaceAdmins(content: string[]): Promise<AdminReplaceResponse> {
    const response = await fetch(buildApiUrl('/api/configserver/AdminUsers.ini'), {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ content })
    });
    return await response.json();
  }
}; 