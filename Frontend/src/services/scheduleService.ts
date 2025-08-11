import api from './api';

export interface ScheduledRestart {
  restartTimes: string[];
  enabled: boolean;
  lastRestart: string | null;
  nextRestart: string | null;
  lastNotification: string | null;
}

export interface ScheduleResponse {
  success: boolean;
  schedules?: ScheduledRestart;
  restartTimes?: string[];
  enabled?: boolean;
}

class ScheduleService {
  private baseUrl = '/server/schedules';

  // Buscar horários configurados
  async getSchedules(): Promise<ScheduleResponse> {
    try {
      console.log('🔍 Fazendo requisição para:', this.baseUrl);
      const response = await api.get(this.baseUrl);
      console.log('📡 Resposta completa do backend:', response);
      console.log('📡 Dados da resposta:', response.data);
      return response.data;
    } catch (error) {
      console.error('❌ Erro ao buscar horários:', error);
      throw error;
    }
  }

  // Adicionar novo horário
  async addTime(time: string): Promise<ScheduleResponse> {
    try {
      const response = await api.post(this.baseUrl, { time });
      return response.data;
    } catch (error) {
      console.error('Erro ao adicionar horário:', error);
      throw error;
    }
  }

  // Remover horário
  async removeTime(time: string): Promise<ScheduleResponse> {
    try {
      const response = await api.delete(this.baseUrl, { data: { time } });
      return response.data;
    } catch (error) {
      console.error('Erro ao remover horário:', error);
      throw error;
    }
  }

  // Ativar/Desativar sistema
  async toggleSystem(enabled: boolean): Promise<ScheduleResponse> {
    try {
      const response = await api.put(this.baseUrl, { enabled });
      return response.data;
    } catch (error) {
      console.error('Erro ao alterar status:', error);
      throw error;
    }
  }

  // Gerar opções de horário (00:00 a 23:00)
  getTimeOptions(): string[] {
    return Array.from({ length: 24 }, (_, i) =>
      `${i.toString().padStart(2, '0')}:00`
    );
  }

  // Formatar horário para exibição (HH:00 HHh)
  formatTimeForDisplay(time: string): string {
    return time.replace(':00', '');
  }

  // Formatar horário para API (HHh -> HH:00)
  formatTimeForAPI(time: string): string {
    return time.replace('h', '0');
  }
}

export const scheduleService = new ScheduleService(); 