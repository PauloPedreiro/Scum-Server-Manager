import api from './server';

export interface ChestLocation {
  x: number | null;
  y: number | null;
  z: number | null;
}

export interface ChestRotation {
  x: number | null;
  y: number | null;
  z: number | null;
}

export interface ChestVehicleInfo {
  entity_id: number | null;
  class: string | null;
  container_class: string | null;
  owner_name: string | null;
  owner_steam_id: string | null;
  owner_player_id: number | null;
  registered_at: string | null;
}

export interface ChestSnapshot {
  entity_id: number;
  container_entity_id: number | null;
  owner_profile_id: number | null;
  steam_id: string | null;
  player_name: string | null;
  fake_name: string | null;
  custom_name: string | null;
  chest_class: string | null;
  chest_type: string;
  location: ChestLocation;
  rotation: ChestRotation;
  vehicle_owner_mismatch: boolean;
  vehicle: ChestVehicleInfo | null;
  last_seen_at: string;
  created_at: string;
  has_vehicle: boolean;
}

export interface ChestPlayerSummary {
  steam_id: string | null;
  count: number;
  player_name: string | null;
  fake_name: string | null;
}

export interface ChestListPayload {
  count: number;
  chests: ChestSnapshot[];
  players?: ChestPlayerSummary[];
  limit?: number;
  offset?: number;
  total?: number;
}

export interface ChestListResponse {
  success: boolean;
  data: ChestListPayload;
  timestamp: number;
}

export interface GetChestsParams {
  steamId?: string;
  limit?: number;
  offset?: number;
  minimal?: boolean;
  disableSummary?: boolean;
}

export async function getChests(params: GetChestsParams = {}): Promise<ChestListResponse> {
  const { steamId, limit, offset, minimal, disableSummary } = params;

  const response = await api.get<ChestListResponse>('/chests', {
    params: {
      steam_id: steamId,
      limit,
      offset,
      minimal,
      disable_summary: disableSummary,
    },
  });

  return response.data;
}

export function isValidChestLocation(location: ChestLocation | null | undefined): location is ChestLocation {
  if (!location) return false;

  const { x, y, z } = location;
  if (x === null || y === null || z === null) {
    return false;
  }

  const isZeroPosition = x === 0 && y === 0 && z === 0;
  if (isZeroPosition) {
    return false;
  }

  return Number.isFinite(x) && Number.isFinite(y);
}

export interface SplitChestResult {
  mappable: ChestSnapshot[];
  vehicleStored: ChestSnapshot[];
  withoutLocation: ChestSnapshot[];
}

export function splitChestsByLocation(chests: ChestSnapshot[]): SplitChestResult {
  const result: SplitChestResult = {
    mappable: [],
    vehicleStored: [],
    withoutLocation: [],
  };

  chests.forEach((chest) => {
    if (isValidChestLocation(chest.location)) {
      result.mappable.push(chest);
      return;
    }

    if (chest.has_vehicle || chest.vehicle) {
      result.vehicleStored.push(chest);
      return;
    }

    result.withoutLocation.push(chest);
  });

  return result;
}


