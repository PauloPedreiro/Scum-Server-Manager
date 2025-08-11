import { buildApiUrl } from '../config/api';
import { FameResponse, FamePlayer, FameStats } from '../types/fame';

export class FameService {
  static async getFamePoints(): Promise<FameResponse> {
    try {
      const response = await fetch(buildApiUrl('/api/famepoints'), {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
        },
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const data = await response.json();
      return data;
    } catch (error) {
      console.error('Erro ao buscar dados de fama:', error);
      throw error;
    }
  }

  static calculateStats(players: FamePlayer[]): FameStats {
    if (players.length === 0) {
      return {
        totalPlayers: 0,
        averageFame: 0,
        highestFame: null,
        lowestFame: null,
        topPlayers: [],
      };
    }

    // Ordena por fama (maior primeiro)
    const sortedPlayers = [...players].sort((a, b) => b.totalFame - a.totalFame);
    
    const totalFame = players.reduce((sum, player) => sum + player.totalFame, 0);
    const averageFame = totalFame / players.length;
    
    return {
      totalPlayers: players.length,
      averageFame: Math.round(averageFame * 100) / 100, // Arredonda para 2 casas decimais
      highestFame: sortedPlayers[0],
      lowestFame: sortedPlayers[sortedPlayers.length - 1],
      topPlayers: sortedPlayers.slice(0, 3), // Top 3
    };
  }

  static getFameLevel(fame: number): 'high' | 'medium' | 'low' {
    if (fame >= 800) return 'high';
    if (fame >= 400) return 'medium';
    return 'low';
  }

  static getFameLevelColor(level: 'high' | 'medium' | 'low'): string {
    switch (level) {
      case 'high': return 'text-green-400';
      case 'medium': return 'text-yellow-400';
      case 'low': return 'text-red-400';
      default: return 'text-scum-muted';
    }
  }

  static getFameLevelBgColor(level: 'high' | 'medium' | 'low'): string {
    switch (level) {
      case 'high': return 'bg-green-400/10 border-green-400/30';
      case 'medium': return 'bg-yellow-400/10 border-yellow-400/30';
      case 'low': return 'bg-red-400/10 border-red-400/30';
      default: return 'bg-scum-gray/10 border-scum-gray/30';
    }
  }

  static formatFamePoints(fame: number): string {
    return fame.toFixed(2);
  }

  static formatTimestamp(timestamp: string): string {
    const date = new Date(timestamp);
    return date.toLocaleString('pt-BR', {
      day: '2-digit',
      month: '2-digit',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  }

  static getMedalIcon(position: number): string {
    switch (position) {
      case 1: return '🥇';
      case 2: return '🥈';
      case 3: return '🥉';
      default: return '🏅';
    }
  }
} 