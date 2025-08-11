import { buildApiUrl } from '../config/api';

export interface Player {
  playerName: string;
  steamId: string;
  totalPlayTime: number;
  lastLogin: string;
  lastLogout: string;
  isOnline: boolean;
  tags: string[];
}

export interface PlayerApiResponse {
  success: boolean;
  message: string;
  data: Player[];
}

export class PlayerService {
  static async getPainelPlayers(): Promise<Player[]> {
    const response = await fetch(buildApiUrl('/api/players/painelplayers'));
    if (!response.ok) {
      throw new Error('Erro ao buscar jogadores do painelplayers');
    }
    const data: PlayerApiResponse = await response.json();
    if (!data.success) {
      throw new Error(data.message || 'Erro desconhecido');
    }
    return data.data;
  }
} 