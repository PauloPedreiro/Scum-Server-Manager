import api from './server';

// Interfaces baseadas na documentação do backend
export interface LongestShot {
  distance: number;
  weapon: string | null;
  timestamp: string | null;
}

export interface LockpickStats {
  success: number;
  fails: number;
  total: number;
  rate: number;
}

export interface LockpickingStats {
  basic: LockpickStats;
  medium: LockpickStats;
  advanced: LockpickStats;
  veryeasy: LockpickStats;
  diallock: LockpickStats;
  other: LockpickStats;
}

export interface PlayerRanking {
  rank: number;
  steam_id: string;
  player_name: string;
  
  // Combat Stats
  kills: number;
  deaths: number;
  kdr: number;
  longest_shot: LongestShot;
  suicides: number;
  headshots: number;
  
  // Lockpicking Stats
  lockpicking: LockpickingStats;
  
  // Survival Stats
  vehicles_destroyed: number;
  highest_defecation: number;
  animals_killed: number;
  players_knocked_out: number;
  minutes_survived: number;
  overdoses: number;
  highest_weight_carried: number;
  total_fame: number;
  
  // Metadata
  last_updated: string;
}

export interface RankingsPagination {
  total: number;
  limit: number;
  offset: number;
  count: number;
  has_more: boolean;
}

export interface RankingsSorting {
  sort_by: string;
  sort_order: 'asc' | 'desc';
  order_column: string;
}

export interface RankingsListData {
  players: PlayerRanking[];
  pagination: RankingsPagination;
  sorting: RankingsSorting;
  search: string | null;
}

export interface RankingsListResponse {
  success: boolean;
  data?: RankingsListData;
  timestamp?: number;
  error?: string;
}

export interface RankingsListParams {
  limit?: number;
  offset?: number;
  sort_by?: string;
  sort_order?: 'asc' | 'desc';
  search?: string;
}

/**
 * Busca lista completa de rankings
 */
export async function getRankingsList(
  params?: RankingsListParams
): Promise<RankingsListResponse> {
  const queryParams: Record<string, any> = {};
  
  if (params?.limit !== undefined) {
    queryParams.limit = params.limit;
  }
  if (params?.offset !== undefined) {
    queryParams.offset = params.offset;
  }
  if (params?.sort_by) {
    queryParams.sort_by = params.sort_by;
  }
  if (params?.sort_order) {
    queryParams.sort_order = params.sort_order;
  }
  if (params?.search) {
    queryParams.search = params.search;
  }
  
  const { data } = await api.get<RankingsListResponse>('/rankings/list', {
    params: queryParams,
  });
  return data;
}

