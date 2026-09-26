import api from './server';

export interface Squad {
  snapshot_id: number;
  squad_id: number;
  name: string;
  message: string | null;
  information: string | null;
  emblem: string | null;
  score: number | null;
  member_limit: number | null;
  member_count: number;
  squad_total_vehicles?: number;
  flag_count: number | null;
  flag_ids: string | null;
  last_member_login_time: string | null;
  last_member_logout_time: string | null;
  rank_position: number | null;
  snapshot_at: string;
}

export interface SquadsApiResponse {
  success: boolean;
  data?: {
    squads: Squad[];
    total: number;
  };
  error?: string;
}

export async function getSquads(): Promise<SquadsApiResponse> {
  const { data } = await api.get<SquadsApiResponse>('/squads');
  return data;
}

export interface SquadMember {
  snapshot_member_id: number;
  squad_member_id: number;
  user_profile_id: number | null;
  steam_id: string | null;
  name: string | null;
  rank: number | null;
  fame_points: number | null;
  last_login_time: string | null;
  last_logout_time: string | null;
  play_time: number | null;
  vehicle_count?: number;
}

export interface SquadMembersResponse {
  success: boolean;
  data?: {
    squad_id: number;
    squad_name: string;
    members: SquadMember[];
    squad_total_vehicles?: number;
    total: number;
    limit: number;
    offset: number;
    count: number;
  };
  error?: string;
}

export async function getSquadMembers(
  squadId: number,
  limit: number = 50,
  offset: number = 0
): Promise<SquadMembersResponse> {
  const { data } = await api.get<SquadMembersResponse>(`/squads/${squadId}/members`, {
    params: { limit, offset },
  });
  return data;
}

