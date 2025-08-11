export interface VehicleEvent {
  timestamp: string;
  event: string;
  vehicleType: string;
  vehicleId: string;
  ownerSteamId: string;
  ownerPlayerId: string;
  ownerName: string;
  location: {
    x: number;
    y: number;
    z: number;
  };
  processedAt: string;
}

export interface VehicleStats {
  totalEvents: number;
  eventsByType: Record<string, number>;
  topOwners: Array<{ steamId: string; name: string; count: number }>;
  topVehicleTypes: Array<{ type: string; count: number }>;
}

import { buildApiUrl } from '../config/api';

export const VehicleService = {
  async processLog() {
    const response = await fetch(buildApiUrl('/api/LogVeiculos'));
    return await response.json();
  },
  async getHistory() {
    const response = await fetch(buildApiUrl('/api/vehicles/history'));
    return await response.json();
  },
  async getByOwner(steamId: string) {
    const response = await fetch(buildApiUrl(`/api/vehicles/owner/${steamId}`));
    return await response.json();
  },
  async getStats() {
    const response = await fetch(buildApiUrl('/api/vehicles/stats'));
    return await response.json();
  }
}; 