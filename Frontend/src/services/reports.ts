import api from './server';

// ==================== Relatórios de Jogadores Online ====================

/**
 * Interface para o campo absolute_peak (pico absoluto)
 */
export interface AbsolutePeak {
  timestamp: string;        // ISO 8601: "2025-12-23T01:35:10.180745"
  date: string;            // Data (YYYY-MM-DD): "2025-12-23"
  hour: number;            // Hora (0-23)
  minute: number;          // Minuto (0-59)
  players_count: number;   // Número de jogadores
  formatted: string;        // Formato legível: "2025-12-23 01:35"
}

/**
 * Interface para resposta do endpoint chart-data
 */
export interface PlayersChartDataResponse {
  success: boolean;
  data?: {
    period: {
      start: string;
      end: string;
      days: number;
    };
    granularity: 'hour' | 'day';
    labels: string[];
    datasets: [
      {
        label: string;
        data: number[];
        average: number;
        peak: number;
        lowest: number;
      }
    ];
  };
  error?: string;
}

/**
 * Interface para resposta do endpoint hourly-average
 */
export interface PlayersHourlyAverageResponse {
  success: boolean;
  data?: {
    period: {
      start: string;
      end: string;
      days: number;
    };
    by_hour: Array<{
      hour: number;
      average: number;
      min: number;
      max: number;
      samples: number;
    }>;
    overall_average: number;
    peak_hour: number;
    peak_hour_average: number;
    lowest_hour: number;
    lowest_hour_average: number;
    absolute_peak: AbsolutePeak | null;  // ⭐ NOVO: Pico absoluto (timestamp exato)
  };
  error?: string;
}

/**
 * Interface para resposta do endpoint daily-average
 */
export interface PlayersDailyAverageResponse {
  success: boolean;
  data?: {
    period: {
      start: string;
      end: string;
      days: number;
    };
    interval_minutes: number;
    by_day: Array<{
      date: string;
      average: number;
      min: number;
      max: number;
      peak: number;
      lowest: number;
      samples: number;
    }>;
    overall_average: number;
    peak_day: string;
    peak_day_count: number;
    lowest_day: string;
    lowest_day_count: number;
    absolute_peak: AbsolutePeak | null;  // ⭐ NOVO: Pico absoluto (timestamp exato)
  };
  error?: string;
}

/**
 * Busca dados formatados para gráfico de jogadores online
 * 
 * @param days Número de dias para analisar (1-365, padrão: 7)
 * @param granularity Tipo de granularidade: 'hour' (0-23) ou 'day' (por dia)
 * @returns Dados formatados prontos para uso em gráficos
 */
export async function getPlayersChartData(
  days: number = 7,
  granularity: 'hour' | 'day' = 'hour'
): Promise<PlayersChartDataResponse> {
  const { data } = await api.get<PlayersChartDataResponse>('/reports/players/chart-data', {
    params: {
      days,
      granularity,
    },
  });
  return data;
}

/**
 * Busca média de jogadores online por hora do dia (0-23)
 * 
 * @param days Número de dias para analisar (1-365, padrão: 7)
 * @returns Média de jogadores por hora do dia
 */
export async function getPlayersHourlyAverage(
  days: number = 7
): Promise<PlayersHourlyAverageResponse> {
  const { data } = await api.get<PlayersHourlyAverageResponse>('/reports/players/hourly-average', {
    params: {
      days,
    },
  });
  return data;
}

/**
 * Busca média de jogadores online por dia no período
 * 
 * @param days Número de dias para analisar (1-365, padrão: 7)
 * @param interval_minutes Intervalo entre snapshots em minutos (5-60, padrão: 15)
 * @returns Média de jogadores por dia
 */
export async function getPlayersDailyAverage(
  days: number = 7,
  interval_minutes: number = 15
): Promise<PlayersDailyAverageResponse> {
  const { data } = await api.get<PlayersDailyAverageResponse>('/reports/players/daily-average', {
    params: {
      days,
      interval_minutes,
    },
  });
  return data;
}
