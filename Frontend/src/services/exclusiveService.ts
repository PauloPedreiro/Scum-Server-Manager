import { buildApiUrl } from '../config/api';

export interface ExclusiveUser {
  steamId: string;
  playerName: string;
}

export interface ExclusiveListResponse {
  success: boolean;
  exclusiveUsers: ExclusiveUser[];
  stats: {
    size: number;
    modified: string;
    created: string;
  };
  error?: string;
}

export interface ExclusiveAddResponse {
  success: boolean;
  message: string;
  backupCreated: string;
  error?: string;
}

export interface ExclusiveRemoveResponse {
  success: boolean;
  message: string;
  backupCreated: string;
  error?: string;
}

export interface ExclusiveReplaceResponse {
  success: boolean;
  message: string;
  backupCreated: string;
  linesCount: number;
  error?: string;
}

export const ExclusiveService = {
  async listExclusiveUsers(): Promise<ExclusiveListResponse> {
    const response = await fetch(buildApiUrl('/api/configserver/ExclusiveUsers.ini'));
    return await response.json();
  },

  async addExclusiveUser(steamId: string): Promise<ExclusiveAddResponse> {
    const response = await fetch(buildApiUrl('/api/configserver/ExclusiveUsers.ini'), {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ steamId })
    });
    return await response.json();
  },

  async removeExclusiveUser(steamId: string): Promise<ExclusiveRemoveResponse> {
    const response = await fetch(buildApiUrl('/api/configserver/ExclusiveUsers.ini'), {
      method: 'DELETE',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ steamId })
    });
    return await response.json();
  },

  async replaceExclusiveUsers(content: string[]): Promise<ExclusiveReplaceResponse> {
    const response = await fetch(buildApiUrl('/api/configserver/ExclusiveUsers.ini'), {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ content })
    });
    return await response.json();
  }
}; 