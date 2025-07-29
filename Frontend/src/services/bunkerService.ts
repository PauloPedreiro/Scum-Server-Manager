import { buildApiUrl } from '../config/api';

export interface BunkerCoordinates {
  x: number;
  y: number;
  z: number;
}

export interface ActiveBunker {
  name: string;
  activated: string;
  coordinates: BunkerCoordinates | null;
}

export interface LockedBunker {
  name: string;
  nextActivation: string;
  coordinates: BunkerCoordinates | null;
}

export interface BunkersData {
  active: ActiveBunker[];
  locked: LockedBunker[];
  lastUpdate: string;
}

export interface BunkersResponse {
  success: boolean;
  message: string;
  data: BunkersData;
  logFile?: string;
}

export const BunkerService = {
  async getBunkersStatus(): Promise<BunkersResponse> {
    try {
      const response = await fetch(buildApiUrl('/api/bunkers/status'));
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      const data = await response.json();
      return data;
    } catch (error) {
      console.error('Erro ao buscar status dos bunkers:', error);
      throw new Error('Erro ao conectar com o servidor. Verifique se o backend está rodando.');
    }
  }
}; 