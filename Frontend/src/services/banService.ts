import { buildApiUrl } from '../config/api';

export interface BannedUser {
  steamId: string;
  playerName: string;
}

export interface BanListResponse {
  success: boolean;
  bannedUsers: BannedUser[];
  stats: {
    size: number;
    modified: string;
    created: string;
  };
  error?: string;
}

export interface BanAddResponse {
  success: boolean;
  message: string;
  backupCreated: string;
  error?: string;
}

export interface BanRemoveResponse {
  success: boolean;
  message: string;
  backupCreated: string;
  error?: string;
}

export interface BanReplaceResponse {
  success: boolean;
  message: string;
  backupCreated: string;
  linesCount: number;
  error?: string;
}

export const BanService = {
  async listBannedUsers(): Promise<BanListResponse> {
    const response = await fetch(buildApiUrl('/api/configserver/BannedUsers.ini'));
    return await response.json();
  },

  async addBannedUser(steamId: string): Promise<BanAddResponse> {
    const response = await fetch(buildApiUrl('/api/configserver/BannedUsers.ini'), {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ steamId })
    });
    return await response.json();
  },

  async removeBannedUser(steamId: string): Promise<BanRemoveResponse> {
    const response = await fetch(buildApiUrl('/api/configserver/BannedUsers.ini'), {
      method: 'DELETE',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ steamId })
    });
    return await response.json();
  },

  async replaceBannedUsers(content: string[]): Promise<BanReplaceResponse> {
    const response = await fetch(buildApiUrl('/api/configserver/BannedUsers.ini'), {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ content })
    });
    return await response.json();
  }
}; 