import { buildApiUrl } from '../config/api';

export interface WhitelistedUser {
  steamId: string;
  playerName: string;
}

export interface WhitelistListResponse {
  success: boolean;
  whitelistedUsers: WhitelistedUser[];
  stats: {
    size: number;
    modified: string;
    created: string;
  };
  error?: string;
}

export interface WhitelistAddResponse {
  success: boolean;
  message: string;
  backupCreated: string;
  error?: string;
}

export interface WhitelistRemoveResponse {
  success: boolean;
  message: string;
  backupCreated: string;
  error?: string;
}

export interface WhitelistReplaceResponse {
  success: boolean;
  message: string;
  backupCreated: string;
  linesCount: number;
  error?: string;
}

export const WhitelistService = {
  async listWhitelistedUsers(): Promise<WhitelistListResponse> {
    const response = await fetch(buildApiUrl('/api/configserver/WhitelistedUsers.ini'));
    return await response.json();
  },

  async addWhitelistedUser(steamId: string): Promise<WhitelistAddResponse> {
    const response = await fetch(buildApiUrl('/api/configserver/WhitelistedUsers.ini'), {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ steamId })
    });
    return await response.json();
  },

  async removeWhitelistedUser(steamId: string): Promise<WhitelistRemoveResponse> {
    const response = await fetch(buildApiUrl('/api/configserver/WhitelistedUsers.ini'), {
      method: 'DELETE',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ steamId })
    });
    return await response.json();
  },

  async replaceWhitelistedUsers(content: string[]): Promise<WhitelistReplaceResponse> {
    const response = await fetch(buildApiUrl('/api/configserver/WhitelistedUsers.ini'), {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ content })
    });
    return await response.json();
  }
}; 