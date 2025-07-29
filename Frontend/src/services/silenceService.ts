import { buildApiUrl } from '../config/api';

export interface SilencedUser {
  steamId: string;
  playerName: string;
}

export interface SilenceListResponse {
  success: boolean;
  silencedUsers: SilencedUser[];
  stats: {
    size: number;
    modified: string;
    created: string;
  };
  error?: string;
}

export interface SilenceAddResponse {
  success: boolean;
  message: string;
  backupCreated: string;
  error?: string;
}

export interface SilenceRemoveResponse {
  success: boolean;
  message: string;
  backupCreated: string;
  error?: string;
}

export interface SilenceReplaceResponse {
  success: boolean;
  message: string;
  backupCreated: string;
  linesCount: number;
  error?: string;
}

export const SilenceService = {
  async listSilencedUsers(): Promise<SilenceListResponse> {
    const response = await fetch(buildApiUrl('/api/configserver/SilencedUsers.ini'));
    return await response.json();
  },

  async addSilencedUser(steamId: string): Promise<SilenceAddResponse> {
    const response = await fetch(buildApiUrl('/api/configserver/SilencedUsers.ini'), {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ steamId })
    });
    return await response.json();
  },

  async removeSilencedUser(steamId: string): Promise<SilenceRemoveResponse> {
    const response = await fetch(buildApiUrl('/api/configserver/SilencedUsers.ini'), {
      method: 'DELETE',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ steamId })
    });
    return await response.json();
  },

  async replaceSilencedUsers(content: string[]): Promise<SilenceReplaceResponse> {
    const response = await fetch(buildApiUrl('/api/configserver/SilencedUsers.ini'), {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ content })
    });
    return await response.json();
  }
}; 