import api from './server';

export interface SettingsPreset {
  name: string;
  size_bytes: number;
  modified_at: string;
}

export interface SettingsRoutine {
  id: string;
  name: string;
  enabled: boolean;
  days_of_week: number[]; // 0: Segunda, ..., 6: Domingo
  start_time: string;     // "HH:MM"
  end_time: string;       // "HH:MM"
  preset_file: string;
}

export interface SchedulerConfigResponse {
  success: boolean;
  enabled: boolean;
  active_routine_id: string | null;
  timestamp?: number;
  error?: string;
}

export interface RoutinesListResponse {
  success: boolean;
  routines: SettingsRoutine[];
  error?: string;
}

export interface DeleteResponse {
  success: boolean;
  error?: string;
  routines?: SettingsRoutine[];
}

/**
 * Obter configuração/status global do agendador de configurações
 */
export async function getSchedulerConfig(): Promise<SchedulerConfigResponse> {
  const { data } = await api.get<SchedulerConfigResponse>('/scheduler/settings/config');
  return data;
}

/**
 * Habilitar ou desabilitar o agendador globalmente
 */
export async function updateSchedulerConfig(enabled: boolean): Promise<SchedulerConfigResponse> {
  const { data } = await api.post<SchedulerConfigResponse>('/scheduler/settings/config', { enabled });
  return data;
}

/**
 * Listar rotinas agendadas
 */
export async function getRoutines(): Promise<RoutinesListResponse> {
  const { data } = await api.get<RoutinesListResponse>('/scheduler/settings/routines');
  return data;
}

/**
 * Endpoint unificado: Criar ou editar uma rotina com arquivo .ini
 * Envia tudo via multipart/form-data em uma única requisição.
 * - Na criação (sem id): o arquivo .ini é obrigatório.
 * - Na edição (com id): o arquivo .ini é opcional (mantém o existente).
 */
export async function saveRoutineUnified(params: {
  id?: string;
  name: string;
  enabled: boolean;
  days_of_week: number[];
  start_time: string;
  end_time: string;
  file?: File | null;
}): Promise<RoutinesListResponse> {
  const formData = new FormData();

  if (params.id) {
    formData.append('id', params.id);
  }

  formData.append('name', params.name);
  formData.append('enabled', String(params.enabled));
  formData.append('days_of_week', JSON.stringify(params.days_of_week));
  formData.append('start_time', params.start_time);
  formData.append('end_time', params.end_time);

  if (params.file) {
    formData.append('file', params.file);
  }

  const { data } = await api.post<RoutinesListResponse>(
    '/scheduler/settings/routines/save',
    formData,
    {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    }
  );
  return data;
}

/**
 * Excluir uma rotina agendada específica
 */
export async function deleteRoutine(id: string): Promise<RoutinesListResponse> {
  const { data } = await api.delete<RoutinesListResponse>(`/scheduler/settings/routines/${id}`);
  return data;
}
