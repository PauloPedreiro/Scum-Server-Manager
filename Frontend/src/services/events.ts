import api from './server';
import type { ApiResponse } from './shopAdmin';

export type EventConfig = {
  event_id: number;
  name: string;
  description: string;
  webhook_url: string | null;
  duration_minutes: number;
  recurrence_interval_minutes: number | null;
  schedule_type: 'manual' | 'daily' | 'interval';
  schedule_value: string | null;
  status: 'inactive' | 'active';
  last_start_time: string | null;
  last_recurrence_time: string | null;
  created_at: string;
};

export type EventCoordinate = {
  coord_id: number;
  event_id: number;
  name: string;
  x: number;
  y: number;
  z: number;
};

export type EventStartupCommand = {
  startup_id: number;
  event_id: number;
  command_string: string;
  order_index: number;
  recurrence_interval_minutes: number | null;
  last_execution_time: string | null;
};

export type TestedCommand = {
  command_id: number;
  command_string: string;
  tested_at: string;
  status: 'success' | 'failed';
  requires_coordinates: number;
};

export async function listEvents(): Promise<ApiResponse<EventConfig[]>> {
  const { data } = await api.get<ApiResponse<EventConfig[]>>('/events');
  return data;
}

export async function createEvent(payload: Omit<EventConfig, 'event_id' | 'status' | 'last_start_time' | 'last_recurrence_time' | 'created_at'>): Promise<ApiResponse<{ event_id: number }>> {
  const { data } = await api.post<ApiResponse<{ event_id: number }>>('/events', payload);
  return data;
}

export async function getEventDetails(eventId: number): Promise<ApiResponse<EventConfig & { coordinates: EventCoordinate[]; commands: EventStartupCommand[] }>> {
  const { data } = await api.get<ApiResponse<EventConfig & { coordinates: EventCoordinate[]; commands: EventStartupCommand[] }>>(`/events/${eventId}`);
  return data;
}

export async function updateEvent(eventId: number, payload: Omit<EventConfig, 'event_id' | 'status' | 'last_start_time' | 'last_recurrence_time' | 'created_at'>): Promise<ApiResponse<boolean>> {
  const { data } = await api.put<ApiResponse<boolean>>(`/events/${eventId}`, payload);
  return data;
}

export async function deleteEvent(eventId: number): Promise<ApiResponse<boolean>> {
  const { data } = await api.delete<ApiResponse<boolean>>(`/events/${eventId}`);
  return data;
}

export async function startEvent(eventId: number): Promise<ApiResponse<boolean>> {
  const { data } = await api.post<ApiResponse<boolean>>(`/events/${eventId}/start`);
  return data;
}

export async function stopEvent(eventId: number): Promise<ApiResponse<boolean>> {
  const { data } = await api.post<ApiResponse<boolean>>(`/events/${eventId}/stop`);
  return data;
}

export async function addCoordinate(eventId: number, payload: { name: string; x: number; y: number; z: number }): Promise<ApiResponse<{ coord_id: number }>> {
  const { data } = await api.post<ApiResponse<{ coord_id: number }>>(`/events/${eventId}/coordinates`, payload);
  return data;
}

export async function removeCoordinate(coordId: number): Promise<ApiResponse<boolean>> {
  const { data } = await api.delete<ApiResponse<boolean>>(`/events/coordinates/${coordId}`);
  return data;
}

export async function addStartupCommand(eventId: number, payload: { command_string: string; order_index: number; recurrence_interval_minutes?: number | null }): Promise<ApiResponse<{ startup_id: number }>> {
  const { data } = await api.post<ApiResponse<{ startup_id: number }>>(`/events/${eventId}/commands`, payload);
  return data;
}

export async function removeStartupCommand(startupId: number): Promise<ApiResponse<boolean>> {
  const { data } = await api.delete<ApiResponse<boolean>>(`/events/commands/${startupId}`);
  return data;
}

export async function updateStartupCommand(startupId: number, payload: { recurrence_interval_minutes: number | null }): Promise<ApiResponse<boolean>> {
  const { data } = await api.put<ApiResponse<boolean>>(`/events/commands/${startupId}`, payload);
  return data;
}

export async function testCommand(command: string): Promise<ApiResponse<{ response: string }>> {
  const { data } = await api.post<ApiResponse<{ response: string }>>('/events/test-command', { command });
  return data;
}

export async function listTestedCommands(): Promise<ApiResponse<TestedCommand[]>> {
  const { data } = await api.get<ApiResponse<TestedCommand[]>>('/events/tested-commands');
  return data;
}

export async function registerTestedCommand(payload: { command: string; requires_coordinates: number }): Promise<ApiResponse<void>> {
  const { data } = await api.post<ApiResponse<void>>('/events/tested-commands', payload);
  return data;
}

export async function syncStartupCommands(eventId: number, commands: Array<{ command_string: string; recurrence_interval_minutes: number | null }>): Promise<ApiResponse<void>> {
  const { data } = await api.put<ApiResponse<void>>(`/events/${eventId}/commands/sync`, { commands });
  return data;
}

export async function syncCoordinates(eventId: number, coordinates: Array<{ name: string; x: number; y: number; z: number }>): Promise<ApiResponse<void>> {
  const { data } = await api.put<ApiResponse<void>>(`/events/${eventId}/coordinates/sync`, { coordinates });
  return data;
}

