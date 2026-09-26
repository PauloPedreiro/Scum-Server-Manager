import api from './server';

export interface FlagLocation {
  x: number;
  y: number;
  z: number;
}

export interface BaseLocation {
  x: number;
  y: number;
}

export interface Base {
  id: number;
  name: string;
  location: BaseLocation | null;
}

export interface Flag {
  element_id: number;
  location: FlagLocation;
  base: Base | null;
  owner: string; // String formatada ou "no owner"
  owner_profile_id: number | null;
  owner_steam_id: string | null;
  owner_name: string | null;
  squad_id: number | null;
  squad_name: string | null;
  overtake_end_time: number | null;
  overtaker_user_profile_id: number | null;
}

export interface FlagsResponse {
  success: boolean;
  data?: {
    flags: Flag[];
    total: number;
    with_owner: number;
    no_owner: number;
  };
  error?: string;
}

export async function getFlags(): Promise<FlagsResponse> {
  const { data } = await api.get<FlagsResponse>('/flags');
  return data;
}

