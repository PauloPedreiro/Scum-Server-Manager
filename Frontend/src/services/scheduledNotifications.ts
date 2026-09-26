import api from './server';

export type ScheduleOnce = {
  type: 'once';
  datetime: string;
};

export type ScheduleDaily = {
  type: 'daily';
  time: string;
};

export type ScheduleRelativeToRestart = {
  type: 'relative_to_restart';
  offset_minutes: number;
};

export type Schedule = ScheduleOnce | ScheduleDaily | ScheduleRelativeToRestart;

export type ScheduledNotification = {
  id: string;
  enabled: boolean;
  title: string;
  message: string;
  color: string;
  duration: number;
  schedule: Schedule;
  created_at?: string;
  updated_at?: string;
};

export type CompileResult = {
  success: boolean;
  count?: number;
  restart_count?: number;
  custom_count?: number;
  path?: string;
  error?: string;
};

export type ReservedWindowConflict = {
  success: false;
  error_code: 'SCHEDULE_TIME_RESERVED_BY_RESTART';
  message: string;
  details: {
    requested_time: string;
    conflicting_restart_time: string;
    reserved_window_start: string;
    reserved_window_end: string;
    reserved_before_minutes: number;
    reserved_after_minutes: number;
  };
};

export type ListScheduledNotificationsResponse = {
  success: boolean;
  items?: ScheduledNotification[];
  error?: string;
  timestamp?: number;
};

export type GetScheduledNotificationResponse = {
  success: boolean;
  item?: ScheduledNotification;
  error?: string;
  timestamp?: number;
};

export type ValidateScheduledNotificationResponse =
  | { success: true; timestamp?: number }
  | ReservedWindowConflict
  | { success: false; error?: string; message?: string; timestamp?: number };

export type UpsertScheduledNotificationRequest = {
  enabled?: boolean;
  title?: string;
  message?: string;
  color?: string;
  duration?: number;
  schedule?: Schedule;
};

export type UpsertScheduledNotificationResponse = {
  success: boolean;
  item?: ScheduledNotification;
  compile?: CompileResult;
  error?: string;
  message?: string;
  timestamp?: number;
};

export type DeleteScheduledNotificationResponse = {
  success: boolean;
  deleted?: boolean;
  compile?: CompileResult;
  error?: string;
  timestamp?: number;
};

export type CompileNotificationsResponse = CompileResult & {
  success: boolean;
};

export async function listScheduledNotifications(): Promise<ListScheduledNotificationsResponse> {
  const { data } = await api.get<ListScheduledNotificationsResponse>('/notifications/scheduled');
  return data;
}

export async function getScheduledNotificationById(itemId: string): Promise<GetScheduledNotificationResponse> {
  const { data } = await api.get<GetScheduledNotificationResponse>(`/notifications/scheduled/${itemId}`);
  return data;
}

export async function validateScheduledNotification(
  payload: UpsertScheduledNotificationRequest
): Promise<ValidateScheduledNotificationResponse> {
  const { data } = await api.post<ValidateScheduledNotificationResponse>('/notifications/scheduled/validate', payload, {
    validateStatus: (status) => status < 500,
  });
  return data;
}

export async function createScheduledNotification(
  payload: UpsertScheduledNotificationRequest
): Promise<UpsertScheduledNotificationResponse> {
  const { data } = await api.post<UpsertScheduledNotificationResponse>('/notifications/scheduled', payload, {
    validateStatus: (status) => status < 500,
  });
  return data;
}

export async function updateScheduledNotification(
  itemId: string,
  payload: UpsertScheduledNotificationRequest
): Promise<UpsertScheduledNotificationResponse> {
  const { data } = await api.put<UpsertScheduledNotificationResponse>(`/notifications/scheduled/${itemId}`, payload, {
    validateStatus: (status) => status < 500,
  });
  return data;
}

export async function deleteScheduledNotification(itemId: string): Promise<DeleteScheduledNotificationResponse> {
  const { data } = await api.delete<DeleteScheduledNotificationResponse>(`/notifications/scheduled/${itemId}`, {
    validateStatus: (status) => status < 500,
  });
  return data;
}

export async function compileNotifications(): Promise<CompileNotificationsResponse> {
  const { data } = await api.post<CompileNotificationsResponse>('/notifications/compile');
  return data;
}
