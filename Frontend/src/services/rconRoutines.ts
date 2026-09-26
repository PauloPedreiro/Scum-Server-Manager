import api from './server';

export interface RconRoutine {
  id: string;
  name: string;
  interval_minutes: number;
  enabled: boolean;
  commands: string[];
  last_run: number | null;
  warning_enabled: boolean;
  warning_message: string;
  warning_color: string;
  warning_minutes_before: number;
  last_warning_run: number | null;
}

export interface RoutineTestResult {
  command: string;
  success: boolean;
  response: string;
}

export interface RoutineTestResponse {
  success: boolean;
  routine_name: string;
  results: RoutineTestResult[];
  error?: string;
}

export interface GenericApiResponse<T> {
  success: boolean;
  data?: T;
  message?: string;
  error?: string;
}

// Obter todas as rotinas
export async function getRoutines(): Promise<GenericApiResponse<RconRoutine[]>> {
  const { data } = await api.get<GenericApiResponse<RconRoutine[]>>('/rcon-routines');
  return data;
}

// Criar nova rotina
export async function createRoutine(
  routineData: Omit<RconRoutine, 'id' | 'last_run' | 'last_warning_run'>
): Promise<GenericApiResponse<RconRoutine>> {
  const { data } = await api.post<GenericApiResponse<RconRoutine>>('/rcon-routines', routineData);
  return data;
}

// Editar rotina
export async function updateRoutine(
  id: string,
  routineData: Partial<RconRoutine>
): Promise<GenericApiResponse<RconRoutine>> {
  const { data } = await api.put<GenericApiResponse<RconRoutine>>(`/rcon-routines/${id}`, routineData);
  return data;
}

// Excluir rotina
export async function deleteRoutine(id: string): Promise<GenericApiResponse<null>> {
  const { data } = await api.delete<GenericApiResponse<null>>(`/rcon-routines/${id}`);
  return data;
}

// Testar rotina de forma síncrona
export async function testRoutine(id: string): Promise<RoutineTestResponse> {
  const { data } = await api.post<RoutineTestResponse>(`/rcon-routines/${id}/test`);
  return data;
}
