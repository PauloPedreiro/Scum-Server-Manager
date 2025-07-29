export interface FamePlayer {
  playerName: string;
  steamId: string;
  totalFame: number;
  timestamp: string;
}

export interface FameResponse {
  success: boolean;
  message: string;
  data: FamePlayer[];
}

export interface FameStats {
  totalPlayers: number;
  averageFame: number;
  highestFame: FamePlayer | null;
  lowestFame: FamePlayer | null;
  topPlayers: FamePlayer[];
}

export type FameLevel = 'high' | 'medium' | 'low';

export interface FameFilters {
  searchTerm: string;
  dateFilter: string;
  rankingFilter: string;
  levelFilter: FameLevel | 'all';
} 