import api from './server';

export interface SurvivalLeaderboardPlayer {
  position: number;
  steam_id: string | null;
  player_name: string | null;
  user_profile_id: number | null;
  value: number;
  kills: number;
  deaths: number;
  kdr: number;
  animals_killed: number;
  puppets_killed: number;
  longest_kill_distance: number | null;
  shots_fired: number;
  shots_hit: number;
  accuracy_percent: number | null;
  headshots: number;
  snapshot_at: string | null;
}

export interface SurvivalLeaderboardResponse {
  success: true;
  data: {
    metric: string;
    available_metrics: string[];
    players: SurvivalLeaderboardPlayer[];
    total: number;
    limit: number;
    offset: number;
    count: number;
  };
  timestamp: number;
}

export interface SurvivalPlayerDetailResponse {
  success: true;
  data: {
    steam_id: string | null;
    player_name: string | null;
    user_profile_id: number | null;
    snapshot_at: string | null;
    metrics: Record<string, number>;
    derived: {
      kdr: number;
      accuracy_percent: number | null;
    };
  };
  timestamp: number;
}

export async function getSurvivalPlayer(identifier: string): Promise<SurvivalPlayerDetailResponse> {
  const { data } = await api.get<SurvivalPlayerDetailResponse>(`/survival/player/${identifier}`);
  return data;
}

export async function getSurvivalLeaderboard(params?: {
  metric?: string;
  limit?: number;
  offset?: number;
}): Promise<SurvivalLeaderboardResponse> {
  const { data } = await api.get<SurvivalLeaderboardResponse>('/survival/leaderboard', {
    params,
  });
  return data;
}


