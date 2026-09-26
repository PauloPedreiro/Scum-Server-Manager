import api from './server';

export interface NotificationsCooldownsInfo {
  cooldowns: Record<string, number>;
  last_sent: Record<string, string | null>;
}

export interface NotificationsStatusData {
  enabled: boolean;
  is_running: boolean;
  check_interval: number;
  restart_protection_window: number;
  last_restart_notifications: string | null;
  cooldowns: NotificationsCooldownsInfo;
  scum_notifier: {
    enabled: boolean;
    notifications_file_exists: boolean;
    current_notifications_count: number;
    highest_priority: number;
  };
}

export interface NotificationsStatusResponse {
  success: boolean;
  data?: NotificationsStatusData;
  error?: string;
  timestamp?: number;
}

export interface SendNotificationRequest {
  message: string;
  duration: number;
  color: string;
}

export interface NotificationSendData {
  message: string;
  color: string;
  duration: number;
  time: string;
  path: string;
}

export interface SendNotificationResponse {
  success: boolean;
  message?: string;
  data?: NotificationSendData;
  error?: string;
}

export interface AdminNotificationRequest {
  type: string;
  message?: string;
  granted_by?: string;
  notes?: string;
}

export interface AdminNotificationResponse {
  success: boolean;
  message?: string;
  data?: {
    message: string;
    color?: string;
    duration?: number;
    time?: string;
    path?: string;
    ini_file_updated?: boolean;
  };
  error?: string;
}

export interface AdminTemplate {
  type: string;
  description: string;
  color: string;
  duration: number;
  examples?: string[];
}

export interface AdminTemplatesData {
  name: string;
  description: string;
  version: string;
  admin_message_types: AdminTemplate[];
}

export interface AdminTemplatesResponse {
  success: boolean;
  data?: AdminTemplatesData;
  error?: string;
}

export interface ClearNotificationsResponse {
  success: boolean;
  error?: string;
}

export interface ResetCooldownsResponse {
  success: boolean;
  message?: string;
  cooldowns?: NotificationsCooldownsInfo;
  error?: string;
}

export interface RestartNotificationRequest {
  restart_time: string;
  restart_date?: string;
}

export interface RestartNotificationResponse {
  success: boolean;
  count?: number;
  priority?: number;
  path?: string;
  message?: string;
  error?: string;
}

export async function getNotificationsStatus(): Promise<NotificationsStatusResponse> {
  const { data } = await api.get<NotificationsStatusResponse>('/notifications/status');
  return data;
}

export async function sendNotification(
  payload: SendNotificationRequest
): Promise<SendNotificationResponse> {
  const { data } = await api.post<SendNotificationResponse>('/notifications/send', payload);
  return data;
}

export async function sendAdminNotification(
  payload: AdminNotificationRequest
): Promise<AdminNotificationResponse> {
  const { data } = await api.post<AdminNotificationResponse>('/notifications/admin/send', payload);
  return data;
}

export async function getAdminNotificationTemplates(): Promise<AdminTemplatesResponse> {
  const { data } = await api.get<AdminTemplatesResponse>('/notifications/admin/templates');
  return data;
}

export async function clearNotifications(): Promise<ClearNotificationsResponse> {
  const { data } = await api.post<ClearNotificationsResponse>('/notifications/clear');
  return data;
}

export async function resetNotificationCooldowns(): Promise<ResetCooldownsResponse> {
  const { data } = await api.post<ResetCooldownsResponse>('/notifications/cooldowns/reset');
  return data;
}

export async function createRestartNotifications(
  payload: RestartNotificationRequest
): Promise<RestartNotificationResponse> {
  const { data } = await api.post<RestartNotificationResponse>('/notifications/restart/create', payload);
  return data;
}

