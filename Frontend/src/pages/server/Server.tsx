import { useState, useEffect, useMemo, useRef, FormEvent } from 'react';
import { useTranslation } from 'react-i18next';
import { Link } from 'react-router-dom';
import AtivadoIcon from '@/assets/logo/Ativado.webp';
import ParadoIcon from '@/assets/logo/Parado.webp';
import { 
  Server as ServerIcon, 
  Play, 
  Square, 
  RotateCw, 
  Loader2, 
  CheckCircle2, 
  XCircle, 
  AlertCircle, 
  RefreshCw,
  Clock,
  Settings,
  FileText,
  Power,
  Plus,
  Trash2,
  Save,
  Bell,
  Send,
  Megaphone,
  AlarmClock,
  ListChecks,
  Wrench
} from 'lucide-react';
import { 
  startServer, 
  stopServer, 
  restartServer, 
  getServerStatus, 
  type ServerResponse, 
  type ServerStatusResponse,
  // Scheduler functions
  getSchedulerStatus,
  startScheduler,
  stopScheduler,
  restartScheduler,
  getSchedulerLogs,
  getSchedulerConfig,
  updateSchedulerConfig,
  forceRestart,
  type SchedulerStatus,
  type SchedulerConfig,
  type SchedulerLog
} from '@/services/server';
import {
  getNotificationsStatus,
  sendNotification,
  sendAdminNotification,
  getAdminNotificationTemplates,
  clearNotifications,
  resetNotificationCooldowns,
  createRestartNotifications,
  type NotificationsStatusData,
  type AdminTemplate
} from '@/services/notifications';
import { alert as showAlert } from '@/lib/alert';
import { authService } from '@/services/auth';

type SchedulerTab = 'status' | 'config' | 'logs';

type ColorSwatch = {
  key: 'white' | 'red' | 'yellow' | 'green' | 'blue' | 'purple' | 'orange';
  rgbDash: string;
  hex: string;
};

const COLOR_SWATCHES: ColorSwatch[] = [
  { key: 'white', rgbDash: '255-255-255', hex: '#ffffff' },
  { key: 'red', rgbDash: '255-0-0', hex: '#ff0000' },
  { key: 'yellow', rgbDash: '255-255-0', hex: '#ffff00' },
  { key: 'green', rgbDash: '0-255-0', hex: '#00ff00' },
  { key: 'blue', rgbDash: '0-0-255', hex: '#0000ff' },
  { key: 'purple', rgbDash: '128-0-128', hex: '#800080' },
  { key: 'orange', rgbDash: '255-165-0', hex: '#ffa500' },
];

function rgbDashToCssColor(value: string): string {
  const known = COLOR_SWATCHES.find((x) => x.rgbDash === value);
  if (known) return known.hex;
  const parts = value
    .split('-')
    .map((x) => Number(x.trim()))
    .filter((n) => Number.isFinite(n));
  if (parts.length === 3) {
    const clamp = (n: number) => Math.max(0, Math.min(255, Math.round(n)));
    const [r, g, b] = parts;
    return `rgb(${clamp(r)}, ${clamp(g)}, ${clamp(b)})`;
  }
  return '#ffffff';
}

export default function Server() {
  const { t, i18n } = useTranslation();
  const isAdmin = authService.isAdmin();
  const isEnglishUi = (i18n.language || '').toLowerCase().startsWith('en');

  const translateBackendMessage = (message: string): string => {
    if (!isEnglishUi) return message;

    const m = (message || '').toLowerCase();
    if (m.includes('nssm') && (m.includes('falha ao iniciar') || m.includes('falhou ao iniciar'))) {
      return t('server.errors.nssmStartFailed');
    }

    return message;
  };
  
  // Server control states
  const [loading, setLoading] = useState<{ action: 'start' | 'stop' | 'restart' | null }>({ action: null });
  const [error, setError] = useState<string | null>(null);
  const [lastResponse, setLastResponse] = useState<ServerResponse | null>(null);
  const [lastAction, setLastAction] = useState<'start' | 'stop' | 'restart' | null>(null);
  const [serverStatus, setServerStatus] = useState<ServerStatusResponse | null>(null);
  const [statusLoading, setStatusLoading] = useState(false);
  
  // Restart assíncrono states
  const [isRestarting, setIsRestarting] = useState(false);
  const [restartStatus, setRestartStatus] = useState<'idle' | 'starting' | 'in_progress' | 'completed' | 'timeout' | 'error'>('idle');
  const restartCheckIntervalRef = useRef<NodeJS.Timeout | null>(null);
  const restartTimeoutRef = useRef<NodeJS.Timeout | null>(null);

  // Scheduler states
  const [schedulerTab, setSchedulerTab] = useState<SchedulerTab>('status');
  const [schedulerStatus, setSchedulerStatus] = useState<SchedulerStatus | null>(null);
  const [schedulerConfig, setSchedulerConfig] = useState<SchedulerConfig | null>(null);
  const [schedulerLogs, setSchedulerLogs] = useState<SchedulerLog[]>([]);
  const [schedulerLoading, setSchedulerLoading] = useState({
    status: false,
    config: false,
    logs: false,
    action: null as 'start' | 'stop' | 'restart' | 'force' | 'save' | null
  });
  const [schedulerError, setSchedulerError] = useState<string | null>(null);
  const [logsLimit, setLogsLimit] = useState(50);
  const [logsFilter, setLogsFilter] = useState<string>('all');
  
  // Notifications states
  const [notificationsStatus, setNotificationsStatus] = useState<NotificationsStatusData | null>(null);
  const [notificationTemplates, setNotificationTemplates] = useState<AdminTemplate[]>([]);
  const [notificationsLoading, setNotificationsLoading] = useState({
    status: false,
    templates: false,
    custom: false,
    admin: false,
    clear: false,
    reset: false,
    restart: false,
  });
  const [notificationTab, setNotificationTab] = useState<'custom'>(
    'custom'
  );
  const [notificationsError, setNotificationsError] = useState<string | null>(null);
  const [customNotificationForm, setCustomNotificationForm] = useState({
    message: '',
    duration: 15,
    color: '255-255-255',
  });
  const [adminNotificationForm, setAdminNotificationForm] = useState({
    type: '',
    message: '',
    granted_by: '',
    notes: '',
  });
  const [restartNotificationForm, setRestartNotificationForm] = useState({
    restart_time: '',
    restart_date: '',
  });

  // Config form states
  const [configForm, setConfigForm] = useState<Partial<SchedulerConfig>>({
    enabled: true,
    auto_start: false,
    restart_times: [],
    notification_minutes: [],
    timezone: 'America/Sao_Paulo'
  });
  const [selectedHour, setSelectedHour] = useState<string>('00');
  const [selectedMinute, setSelectedMinute] = useState<string>('00');
  const [notificationMinutesInput, setNotificationMinutesInput] = useState('');

  // Buscar status do servidor
  const fetchStatus = async () => {
    setStatusLoading(true);
    try {
      const status = await getServerStatus();
      setServerStatus(status);
    } catch (err: any) {
      console.error('Erro ao buscar status:', err);
    } finally {
      setStatusLoading(false);
    }
  };

  // Buscar status do agendador
  const fetchSchedulerStatus = async () => {
    setSchedulerLoading(prev => ({ ...prev, status: true }));
    setSchedulerError(null);
    try {
      const response = await getSchedulerStatus();
      if (response.success && response.data) {
        setSchedulerStatus(response.data);
      } else {
        setSchedulerError(response.error || t('server.scheduler.errors.loadStatus'));
      }
    } catch (err: any) {
      const errorMsg = err.response?.data?.error || err.message || t('server.scheduler.errors.loadStatus');
      setSchedulerError(errorMsg);
    } finally {
      setSchedulerLoading(prev => ({ ...prev, status: false }));
    }
  };

  // Buscar configuração do agendador
  const fetchSchedulerConfig = async () => {
    setSchedulerLoading(prev => ({ ...prev, config: true }));
    try {
      const response = await getSchedulerConfig();
      if (response.success && response.data) {
        setSchedulerConfig(response.data);
        setConfigForm({
          enabled: response.data.enabled,
          auto_start: response.data.auto_start,
          restart_times: [...response.data.restart_times],
          notification_minutes: [...response.data.notification_minutes],
          timezone: response.data.timezone
        });
        setNotificationMinutesInput(response.data.notification_minutes.join(', '));
      }
    } catch (err: any) {
      console.error('Erro ao buscar configuração:', err);
    } finally {
      setSchedulerLoading(prev => ({ ...prev, config: false }));
    }
  };

  // Buscar logs do agendador
  const fetchSchedulerLogs = async () => {
    setSchedulerLoading(prev => ({ ...prev, logs: true }));
    try {
      const response = await getSchedulerLogs(logsLimit);
      if (response.success && response.data) {
        setSchedulerLogs(response.data.logs || []);
      }
    } catch (err: any) {
      console.error('Erro ao buscar logs:', err);
    } finally {
      setSchedulerLoading(prev => ({ ...prev, logs: false }));
    }
  };

  // Notifications helpers
  const refreshNotificationsStatus = async () => {
    setNotificationsLoading(prev => ({ ...prev, status: true }));
    setNotificationsError(null);
    try {
      const response = await getNotificationsStatus();
      if (response.success && response.data) {
        setNotificationsStatus(response.data);
      } else {
        const errorMsg = response.error || t('server.notifications.errors.loadStatus');
        setNotificationsError(errorMsg);
      }
    } catch (err: any) {
      const errorMsg = err.response?.data?.error || err.message || t('server.notifications.errors.loadStatus');
      setNotificationsError(errorMsg);
    } finally {
      setNotificationsLoading(prev => ({ ...prev, status: false }));
    }
  };

  const loadNotificationTemplates = async () => {
    setNotificationsLoading(prev => ({ ...prev, templates: true }));
    try {
      const response = await getAdminNotificationTemplates();
      if (response.success && response.data) {
        setNotificationTemplates(response.data.admin_message_types || []);
      }
    } catch (err) {
      console.error('Erro ao carregar templates de notificações:', err);
    } finally {
      setNotificationsLoading(prev => ({ ...prev, templates: false }));
    }
  };

  const getCooldownDuration = (type: string): number =>
    notificationsStatus?.cooldowns?.cooldowns?.[type] ?? 0;

  const getCooldownRemaining = (type: string): number => {
    const duration = getCooldownDuration(type);
    if (!duration) return 0;

    const lastSentValue = notificationsStatus?.cooldowns?.last_sent?.[type];
    if (!lastSentValue) return 0;

    const lastSentDate = new Date(lastSentValue);
    if (Number.isNaN(lastSentDate.getTime())) return 0;

    const elapsed = Math.floor((Date.now() - lastSentDate.getTime()) / 1000);
    return Math.max(0, duration - elapsed);
  };

  const isCooldownActive = (type: string): boolean => getCooldownRemaining(type) > 0;

  const formatCooldown = (seconds: number): string => {
    if (!seconds || seconds <= 0) return t('server.notifications.cooldowns.ready');
    const minutes = Math.floor(seconds / 60);
    const remainingSeconds = seconds % 60;
    if (minutes > 0) {
      return `${minutes}m ${remainingSeconds.toString().padStart(2, '0')}s`;
    }
    return `${remainingSeconds}s`;
  };

  const formatNotificationDate = (value: string): string => {
    try {
      const date = new Date(value);
      return new Intl.DateTimeFormat(i18n.language, {
        day: '2-digit',
        month: '2-digit',
        year: 'numeric',
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit',
      }).format(date);
    } catch {
      return value;
    }
  };

  const getLastSentLabel = (type: string): string => {
    const lastValue = notificationsStatus?.cooldowns?.last_sent?.[type];
    if (!lastValue) {
      return t('server.notifications.lastSent.never');
    }
    return formatNotificationDate(lastValue);
  };

  const handleSendCustomNotification = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!customNotificationForm.message.trim()) {
      showAlert({
        title: t('server.actions.error'),
        text: t('server.notifications.validation.messageRequired'),
        icon: 'error',
      });
      return;
    }

    if (!Number.isInteger(customNotificationForm.duration) || customNotificationForm.duration <= 0) {
      showAlert({
        title: t('server.actions.error'),
        text: t('server.notifications.validation.durationInvalid'),
        icon: 'error',
      });
      return;
    }

    const colorMatch = customNotificationForm.color.match(/^(\d{1,3})-(\d{1,3})-(\d{1,3})$/);
    if (!colorMatch) {
      showAlert({
        title: t('server.actions.error'),
        text: t('server.notifications.validation.colorInvalid'),
        icon: 'error',
      });
      return;
    }

    const colorValid = colorMatch.slice(1).every(value => {
      const num = Number(value);
      return num >= 0 && num <= 255;
    });

    if (!colorValid) {
      showAlert({
        title: t('server.actions.error'),
        text: t('server.notifications.validation.colorInvalid'),
        icon: 'error',
      });
      return;
    }

    setNotificationsLoading(prev => ({ ...prev, custom: true }));

    try {
      const response = await sendNotification({
        message: customNotificationForm.message.trim(),
        duration: customNotificationForm.duration,
        color: customNotificationForm.color,
      });

      if (response.success) {
        showAlert({
          title: t('server.notifications.success.sent'),
          text: response.message || t('server.notifications.success.customSent'),
          icon: 'success',
        });
        setCustomNotificationForm(prev => ({ ...prev, message: '' }));
        await refreshNotificationsStatus();
      } else {
        const errorMsg = response.message || response.error || t('server.notifications.errors.sendFailed');
        showAlert({
          title: t('server.actions.error'),
          text: errorMsg,
          icon: 'error',
        });
      }
    } catch (err: any) {
      const errorMsg = err.response?.data?.error || err.message || t('server.notifications.errors.sendFailed');
      showAlert({
        title: t('server.actions.error'),
        text: errorMsg,
        icon: 'error',
      });
    } finally {
      setNotificationsLoading(prev => ({ ...prev, custom: false }));
    }
  };

  const handleSendAdminNotification = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!adminNotificationForm.type) {
      showAlert({
        title: t('server.actions.error'),
        text: t('server.notifications.validation.templateRequired'),
        icon: 'error',
      });
      return;
    }

    setNotificationsLoading(prev => ({ ...prev, admin: true }));

    try {
      const response = await sendAdminNotification({
        type: adminNotificationForm.type,
        message: adminNotificationForm.message?.trim() || undefined,
        granted_by: adminNotificationForm.granted_by?.trim() || undefined,
        notes: adminNotificationForm.notes?.trim() || undefined,
      });

      if (response.success) {
        showAlert({
          title: t('server.notifications.success.sent'),
          text: response.message || t('server.notifications.success.adminSent'),
          icon: 'success',
        });
        setAdminNotificationForm(prev => ({
          ...prev,
          message: '',
          granted_by: '',
          notes: '',
        }));
        await refreshNotificationsStatus();
      } else {
        const errorMsg = response.message || response.error || t('server.notifications.errors.sendFailed');
        showAlert({
          title: t('server.actions.error'),
          text: errorMsg,
          icon: 'error',
        });
      }
    } catch (err: any) {
      const errorMsg = err.response?.data?.error || err.message || t('server.notifications.errors.sendFailed');
      showAlert({
        title: t('server.actions.error'),
        text: errorMsg,
        icon: 'error',
      });
    } finally {
      setNotificationsLoading(prev => ({ ...prev, admin: false }));
    }
  };

  const handleClearNotifications = async () => {
    const confirmation = await showAlert({
      title: t('server.notifications.actions.clear.confirmTitle'),
      text: t('server.notifications.actions.clear.confirmMessage'),
      icon: 'warning',
      showCancelButton: true,
      confirmButtonText: t('server.notifications.actions.clear.confirmButton'),
      cancelButtonText: t('server.notifications.actions.cancel'),
    });

    if (!confirmation.isConfirmed) return;

    setNotificationsLoading(prev => ({ ...prev, clear: true }));
    try {
      const response = await clearNotifications();
      if (response.success) {
        showAlert({
          title: t('server.notifications.success.cleared'),
          icon: 'success',
        });
        await refreshNotificationsStatus();
      } else {
        const errorMsg = response.error || t('server.notifications.errors.clearFailed');
        showAlert({
          title: t('server.actions.error'),
          text: errorMsg,
          icon: 'error',
        });
      }
    } catch (err: any) {
      const errorMsg = err.response?.data?.error || err.message || t('server.notifications.errors.clearFailed');
      showAlert({
        title: t('server.actions.error'),
        text: errorMsg,
        icon: 'error',
      });
    } finally {
      setNotificationsLoading(prev => ({ ...prev, clear: false }));
    }
  };

  const handleResetCooldowns = async () => {
    const confirmation = await showAlert({
      title: t('server.notifications.actions.resetCooldowns.confirmTitle'),
      text: t('server.notifications.actions.resetCooldowns.confirmMessage'),
      icon: 'warning',
      showCancelButton: true,
      confirmButtonText: t('server.notifications.actions.resetCooldowns.confirmButton'),
      cancelButtonText: t('server.notifications.actions.cancel'),
    });

    if (!confirmation.isConfirmed) return;

    setNotificationsLoading(prev => ({ ...prev, reset: true }));
    try {
      const response = await resetNotificationCooldowns();
      if (response.success) {
        showAlert({
          title: t('server.notifications.success.cooldownsReset'),
          text: response.message,
          icon: 'success',
        });
        await refreshNotificationsStatus();
      } else {
        const errorMsg = response.error || response.message || t('server.notifications.errors.resetCooldownsFailed');
        showAlert({
          title: t('server.actions.error'),
          text: errorMsg,
          icon: 'error',
        });
      }
    } catch (err: any) {
      const errorMsg = err.response?.data?.error || err.message || t('server.notifications.errors.resetCooldownsFailed');
      showAlert({
        title: t('server.actions.error'),
        text: errorMsg,
        icon: 'error',
      });
    } finally {
      setNotificationsLoading(prev => ({ ...prev, reset: false }));
    }
  };

  const handleCreateRestartNotifications = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const time = restartNotificationForm.restart_time;
    const date = restartNotificationForm.restart_date;

    const timeRegex = /^([0-1]\d|2[0-3]):[0-5]\d$/;
    if (!timeRegex.test(time)) {
      showAlert({
        title: t('server.actions.error'),
        text: t('server.notifications.validation.restartTimeInvalid'),
        icon: 'error',
      });
      return;
    }

    if (date && !/^\d{4}-\d{2}-\d{2}$/.test(date)) {
      showAlert({
        title: t('server.actions.error'),
        text: t('server.notifications.validation.restartDateInvalid'),
        icon: 'error',
      });
      return;
    }

    const confirmation = await showAlert({
      title: t('server.notifications.actions.restart.confirmTitle'),
      text: t('server.notifications.actions.restart.confirmMessage', { time, date: date || t('server.notifications.actions.restart.today') }),
      icon: 'warning',
      showCancelButton: true,
      confirmButtonText: t('server.notifications.actions.restart.confirmButton'),
      cancelButtonText: t('server.notifications.actions.cancel'),
    });

    if (!confirmation.isConfirmed) return;

    setNotificationsLoading(prev => ({ ...prev, restart: true }));

    try {
      const response = await createRestartNotifications({
        restart_time: time,
        restart_date: date || undefined,
      });

      if (response.success) {
        showAlert({
          title: t('server.notifications.success.restartCreated'),
          text: t('server.notifications.success.restartCreatedDetails', {
            count: response.count ?? 0,
            priority: response.priority ?? 0,
          }),
          icon: 'success',
        });
        setRestartNotificationForm({ restart_time: '', restart_date: '' });
        await refreshNotificationsStatus();
      } else {
        const errorMsg = response.error || response.message || t('server.notifications.errors.restartCreateFailed');
        showAlert({
          title: t('server.actions.error'),
          text: errorMsg,
          icon: 'error',
        });
      }
    } catch (err: any) {
      const errorMsg = err.response?.data?.error || err.message || t('server.notifications.errors.restartCreateFailed');
      showAlert({
        title: t('server.actions.error'),
        text: errorMsg,
        icon: 'error',
      });
    } finally {
      setNotificationsLoading(prev => ({ ...prev, restart: false }));
    }
  };

  // Função auxiliar para calcular contagem regressiva
  const getCountdown = (nextRestart: string | null): string => {
    if (!nextRestart) return t('server.scheduler.status.noRestartScheduled') || 'N/A';
    
    const now = new Date();
    const restart = new Date(nextRestart);
    const diff = restart.getTime() - now.getTime();
    
    if (diff < 0) return t('server.scheduler.countdown.passed');
    
    const hours = Math.floor(diff / (1000 * 60 * 60));
    const minutes = Math.floor((diff % (1000 * 60 * 60)) / (1000 * 60));
    const seconds = Math.floor((diff % (1000 * 60)) / 1000);
    
    if (hours > 0) {
      return `${hours}${t('server.scheduler.countdown.hours')} ${minutes}${t('server.scheduler.countdown.minutes')}`;
    } else if (minutes > 0) {
      return `${minutes}${t('server.scheduler.countdown.minutes')} ${seconds}${t('server.scheduler.countdown.seconds')}`;
    } else {
      return `${seconds}${t('server.scheduler.countdown.seconds')}`;
    }
  };

  // Atualizar contagem regressiva a cada segundo
  useEffect(() => {
    if (schedulerStatus?.next_restart) {
      const interval = setInterval(() => {
        // Force re-render para atualizar contagem regressiva
        setSchedulerStatus(prev => prev ? { ...prev } : null);
      }, 1000);
      return () => clearInterval(interval);
    }
  }, [schedulerStatus?.next_restart]);

  // Carregar dados iniciais
  useEffect(() => {
    fetchStatus();
    fetchSchedulerStatus();
    
    // Atualizar status do servidor a cada 30 segundos
    const serverInterval = setInterval(fetchStatus, 30000);
    
    // Atualizar status do agendador a cada 30 segundos (ou 60 se parado)
    const schedulerInterval = setInterval(() => {
      fetchSchedulerStatus();
    }, schedulerStatus?.is_running ? 30000 : 60000);
    
    return () => {
      clearInterval(serverInterval);
      clearInterval(schedulerInterval);
    };
  }, []);

  useEffect(() => {
    let isCancelled = false;
    let timeoutId: number | null = null;
    let currentDelayMs = 5000;

    loadNotificationTemplates();

    const scheduleNext = (delayMs: number) => {
      if (timeoutId) {
        window.clearTimeout(timeoutId);
      }
      timeoutId = window.setTimeout(run, delayMs);
    };

    const run = async () => {
      if (isCancelled) return;
      try {
        await refreshNotificationsStatus();
        currentDelayMs = 5000;
      } catch {
        currentDelayMs = Math.min(currentDelayMs * 2, 60000);
      } finally {
        scheduleNext(currentDelayMs);
      }
    };

    run();

    return () => {
      isCancelled = true;
      if (timeoutId) {
        window.clearTimeout(timeoutId);
      }
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Carregar dados quando muda de tab
  useEffect(() => {
    if (schedulerTab === 'config' && !schedulerConfig) {
      fetchSchedulerConfig();
    } else if (schedulerTab === 'logs') {
      fetchSchedulerLogs();
    }
  }, [schedulerTab]);

  const handleAction = async (action: 'start' | 'stop' | 'restart') => {
    // Se for restart, usar lógica assíncrona
    if (action === 'restart') {
      return handleRestartAsync();
    }

    // Para start e stop, manter comportamento síncrono
    setLastAction(action);
    setLoading({ action });
    setError(null);
    setLastResponse(null);

    try {
      let response: ServerResponse;
      
      switch (action) {
        case 'start':
          response = await startServer({ force: false, wait_timeout: 30 });
          break;
        case 'stop':
          response = await stopServer({ force: false, wait_timeout: 30 });
          break;
        default:
          return;
      }

      setLastResponse(response);

      if (response.success) {
        const actionText = action === 'start' ? t('server.actions.started') : t('server.actions.stopped');
        showAlert({
          title: t('server.actions.success'),
          text: isEnglishUi ? `${actionText} ${t('server.actions.withSuccess')}` : (response.message || `${actionText} ${t('server.actions.withSuccess')}`),
          icon: 'success',
        });
      } else {
        const rawErrorMsg = response.message || response.error || t('server.actions.unknownError');
        const errorMsg = translateBackendMessage(rawErrorMsg);
        setError(errorMsg);
        showAlert({
          title: t('server.actions.error'),
          text: errorMsg,
          icon: 'error',
        });
      }
    } catch (err: any) {
      const rawErrorMsg = err.response?.data?.error || err.response?.data?.message || err.message || t('server.actions.requestError');
      const errorMsg = translateBackendMessage(rawErrorMsg);
      setError(errorMsg);
      showAlert({
        title: t('server.actions.error'),
        text: errorMsg,
        icon: 'error',
      });
    } finally {
      setLoading({ action: null });
      setTimeout(() => fetchStatus(), 2000);
    }
  };

  // Limpar intervalos quando componente desmontar
  useEffect(() => {
    return () => {
      if (restartCheckIntervalRef.current) {
        clearInterval(restartCheckIntervalRef.current);
      }
      if (restartTimeoutRef.current) {
        clearTimeout(restartTimeoutRef.current);
      }
    };
  }, []);

  // Handler específico para restart assíncrono
  const handleRestartAsync = async () => {
    // Limpar intervalos anteriores se existirem
    if (restartCheckIntervalRef.current) {
      clearInterval(restartCheckIntervalRef.current);
      restartCheckIntervalRef.current = null;
    }
    if (restartTimeoutRef.current) {
      clearTimeout(restartTimeoutRef.current);
      restartTimeoutRef.current = null;
    }

    setLoading({ action: 'restart' });
    setLastAction('restart');
    setIsRestarting(true);
    setRestartStatus('starting');
    setError(null);
    setLastResponse(null);

    try {
      // Iniciar restart (wait_timeout: 0 para execução assíncrona)
      const response = await restartServer({ force: false, wait_timeout: 0 });
      
      setLastResponse(response);

      if (response.success) {
        setRestartStatus('in_progress');
        
        // Mostrar mensagem informativa
        showAlert({
          title: t('server.actions.restart.initiated'),
          text: isEnglishUi ? t('server.actions.restart.message') : (response.message || t('server.actions.restart.message')),
          icon: 'info',
        });

        // Verificar status periodicamente (a cada 5 segundos)
        restartCheckIntervalRef.current = setInterval(async () => {
          try {
            const statusResponse = await getServerStatus();
            const status = statusResponse.data;

            // Verificar se o servidor está rodando novamente
            if (status?.is_running) {
              // Servidor está rodando novamente - restart completo
              setRestartStatus('completed');
              setIsRestarting(false);
              
              if (restartCheckIntervalRef.current) {
                clearInterval(restartCheckIntervalRef.current);
                restartCheckIntervalRef.current = null;
              }
              if (restartTimeoutRef.current) {
                clearTimeout(restartTimeoutRef.current);
                restartTimeoutRef.current = null;
              }
              
              showAlert({
                title: t('server.actions.success'),
                text: t('server.actions.restarted') + ' ' + t('server.actions.withSuccess'),
                icon: 'success',
              });
              
              // Atualizar status
              setServerStatus(statusResponse);
              setLoading({ action: null });
            }
          } catch (error) {
            console.error('Erro ao verificar status durante restart:', error);
            // Não interromper o polling por erros temporários
          }
        }, 5000);

        // Timeout de segurança (10 minutos)
        restartTimeoutRef.current = setTimeout(() => {
          if (restartCheckIntervalRef.current) {
            clearInterval(restartCheckIntervalRef.current);
            restartCheckIntervalRef.current = null;
          }
          
          setIsRestarting((current) => {
            if (current) {
              setRestartStatus('timeout');
              showAlert({
                title: t('server.actions.restart.timeout'),
                text: t('server.actions.restart.timeoutMessage'),
                icon: 'warning',
              });
              setLoading({ action: null });
              return false;
            }
            return current;
          });
        }, 600000); // 10 minutos
      } else {
        const errorMsg = response.message || response.error || t('server.actions.unknownError');
        setError(errorMsg);
        setRestartStatus('error');
        setIsRestarting(false);
        setLoading({ action: null });
        showAlert({
          title: t('server.actions.error'),
          text: errorMsg,
          icon: 'error',
        });
      }
    } catch (err: any) {
      const errorMsg = err.response?.data?.error || err.response?.data?.message || err.message || t('server.actions.requestError');
      setError(errorMsg);
      setRestartStatus('error');
      setIsRestarting(false);
      setLoading({ action: null });
      showAlert({
        title: t('server.actions.error'),
        text: errorMsg,
        icon: 'error',
      });
    } finally {
      // Continuar verificando status mesmo após iniciar o restart
      setTimeout(() => fetchStatus(), 2000);
    }
  };

  // Handlers do agendador
  const handleSchedulerAction = async (action: 'start' | 'stop' | 'restart') => {
    setSchedulerLoading(prev => ({ ...prev, action }));
    setSchedulerError(null);
    
    try {
      let response;
      switch (action) {
        case 'start':
          response = await startScheduler();
          break;
        case 'stop':
          response = await stopScheduler();
          break;
        case 'restart':
          response = await restartScheduler();
          break;
      }
      
      if (response.success) {
        showAlert({
          title: t('server.scheduler.success.' + (action === 'start' ? 'started' : action === 'stop' ? 'stopped' : 'restarted')),
          icon: 'success',
        });
        await fetchSchedulerStatus();
      } else {
        const errorMsg = response.error || response.message || t(`server.scheduler.errors.${action}Failed`);
        setSchedulerError(errorMsg);
        showAlert({
          title: t('server.actions.error'),
          text: errorMsg,
          icon: 'error',
        });
      }
    } catch (err: any) {
      const errorMsg = err.response?.data?.error || err.message || t(`server.scheduler.errors.${action}Failed`);
      setSchedulerError(errorMsg);
      showAlert({
        title: t('server.actions.error'),
        text: errorMsg,
        icon: 'error',
      });
    } finally {
      setSchedulerLoading(prev => ({ ...prev, action: null }));
    }
  };

  const handleForceRestart = async () => {
    const result = await showAlert({
      title: t('server.scheduler.controls.forceRestart.confirm.title'),
      text: t('server.scheduler.controls.forceRestart.confirm.message'),
      icon: 'warning',
      showCancelButton: true,
      confirmButtonText: t('server.scheduler.controls.forceRestart.confirm.confirmButton'),
      cancelButtonText: t('server.scheduler.controls.forceRestart.confirm.cancelButton'),
    });

    if (!result.isConfirmed) return;

    setSchedulerLoading(prev => ({ ...prev, action: 'force' }));
    setSchedulerError(null);
    
    try {
      const response = await forceRestart();
      if (response.success) {
        showAlert({
          title: t('server.scheduler.success.forceRestart'),
          icon: 'success',
        });
        await fetchStatus();
      } else {
        const errorMsg = response.error || response.message || t('server.scheduler.errors.forceRestartFailed');
        setSchedulerError(errorMsg);
        showAlert({
          title: t('server.actions.error'),
          text: errorMsg,
          icon: 'error',
        });
      }
    } catch (err: any) {
      const errorMsg = err.response?.data?.error || err.message || t('server.scheduler.errors.forceRestartFailed');
      setSchedulerError(errorMsg);
      showAlert({
        title: t('server.actions.error'),
        text: errorMsg,
        icon: 'error',
      });
    } finally {
      setSchedulerLoading(prev => ({ ...prev, action: null }));
    }
  };

  const handleAddTime = () => {
    const newTime = `${selectedHour}:${selectedMinute}`;

    const currentTimes = configForm.restart_times || [];
    if (currentTimes.includes(newTime)) {
      showAlert({
        title: t('server.actions.error'),
        text: 'Este horário já está configurado',
        icon: 'error',
      });
      return;
    }

    setConfigForm(prev => ({
      ...prev,
      restart_times: [...(prev.restart_times || []), newTime].sort()
    }));
    // Reset para valores padrão após adicionar
    setSelectedHour('00');
    setSelectedMinute('00');
  };

  const handleRemoveTime = (time: string) => {
    setConfigForm(prev => ({
      ...prev,
      restart_times: (prev.restart_times || []).filter(t => t !== time)
    }));
  };

  const handleSaveConfig = async () => {
    setSchedulerLoading(prev => ({ ...prev, action: 'save' }));
    setSchedulerError(null);
    
    try {
      // Parse notification minutes
      const notificationMinutes = notificationMinutesInput
        .split(',')
        .map(m => parseInt(m.trim()))
        .filter(m => !isNaN(m) && m > 0);

      const config: Partial<SchedulerConfig> = {
        ...configForm,
        notification_minutes: notificationMinutes
      };

      const response = await updateSchedulerConfig(config);
      
      if (response.success) {
        showAlert({
          title: t('server.scheduler.config.save.success'),
          icon: 'success',
        });
        await fetchSchedulerConfig();
        await fetchSchedulerStatus();
      } else {
        const errorMsg = response.error || response.message || t('server.scheduler.config.save.error');
        setSchedulerError(errorMsg);
        showAlert({
          title: t('server.actions.error'),
          text: errorMsg,
          icon: 'error',
        });
      }
    } catch (err: any) {
      const errorMsg = err.response?.data?.error || err.message || t('server.scheduler.config.save.error');
      setSchedulerError(errorMsg);
      showAlert({
        title: t('server.actions.error'),
        text: errorMsg,
        icon: 'error',
      });
    } finally {
      setSchedulerLoading(prev => ({ ...prev, action: null }));
    }
  };

  // Filtrar logs
  const filteredLogs = useMemo(() => {
    if (logsFilter === 'all') return schedulerLogs;
    return schedulerLogs.filter(log => log.event_type === logsFilter);
  }, [schedulerLogs, logsFilter]);

  // Formatar data
  const formatDateTime = (dateString: string): string => {
    try {
      const date = new Date(dateString);
      return date.toLocaleString('pt-BR', {
        day: '2-digit',
        month: '2-digit',
        year: 'numeric',
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit'
      });
    } catch {
      return dateString;
    }
  };

  const isLoading = loading.action !== null;
  const checkIsRunning = () => {
    if (serverStatus?.data?.is_running) return true;
    if (lastResponse?.final_status?.is_running) return true;
    const estado = serverStatus?.data?.service_info?.ESTADO;
    if (estado && (estado.includes('RUNNING') || estado.includes('4'))) return true;
    return false;
  };
  const checkIsStopped = () => {
    if (!serverStatus?.data?.is_running && !lastResponse?.final_status?.is_running) {
      const estado = serverStatus?.data?.service_info?.ESTADO;
      if (estado && (estado.includes('STOPPED') || estado.includes('1'))) return true;
      if (!serverStatus?.data && !lastResponse?.final_status?.is_running) return true;
    }
    return false;
  };
  const isRunning = checkIsRunning();
  const isStopped = checkIsStopped();

  return (
    <div className="grid gap-4">
      {/* Card: Controle do Servidor */}
      <div className="card p-4">
        <div className="flex items-center gap-2 mb-4">
          <ServerIcon size={20} />
          <h1 className="text-xl font-semibold">{t('server.title')}</h1>
        </div>
        <p className="text-white/70 text-sm mb-6">
          {t('server.description')}
        </p>

        {/* Status atual do servidor */}
        <div className={`mb-6 p-4 rounded-lg border ${
          isRunning 
            ? 'bg-green-500/10 border-green-500/20' 
            : 'bg-gray-500/10 border-gray-500/20'
        }`}>
          <div className="flex items-center justify-between mb-3">
            <div className="flex items-center gap-2">
              <img
                src={isRunning ? AtivadoIcon : ParadoIcon}
                alt={isRunning ? t('server.status.running') : t('server.status.stopped')}
                className="w-5 h-5"
              />
              <span className={`font-semibold ${isRunning ? 'text-green-400' : 'text-gray-400'}`}>
                {t('server.status.label')}: {isRunning ? t('server.status.running') : t('server.status.stopped')}
              </span>
            </div>
            <button
              onClick={fetchStatus}
              disabled={statusLoading}
              className="p-2 rounded-lg bg-black/30 hover:bg-black/50 border border-white/10 disabled:opacity-50 transition-colors"
              title={t('server.refreshStatus')}
            >
              <RefreshCw size={16} className={statusLoading ? 'animate-spin' : ''} />
            </button>
          </div>
          
          {statusLoading && !serverStatus && (
            <div className="text-xs text-white/50">{t('server.loadingStatus')}</div>
          )}
        </div>

        {/* Status da última ação */}
        {lastResponse && (
          <div className={`mb-6 p-4 rounded-lg border ${
            lastResponse.success 
              ? 'bg-green-500/10 border-green-500/20' 
              : 'bg-red-500/10 border-red-500/20'
          }`}>
            <div className="flex items-center gap-2 mb-2">
              {lastResponse.success ? (
                <CheckCircle2 size={20} className="text-green-400" />
              ) : (
                <XCircle size={20} className="text-red-400" />
              )}
              <span className={`font-semibold ${lastResponse.success ? 'text-green-400' : 'text-red-400'}`}>
                {lastResponse.success ? t('server.actions.success') : t('server.actions.error')}
              </span>
            </div>
            {(() => {
              const message = (() => {
                if (!lastResponse.success) {
                  return lastResponse.message ? translateBackendMessage(lastResponse.message) : lastResponse.message;
                }
                if (!isEnglishUi) return lastResponse.message;
                if (lastAction === 'restart') return t('server.actions.restart.message');
                if (lastAction === 'start') {
                  return `${t('server.actions.started')} ${t('server.actions.withSuccess')}`;
                }
                if (lastAction === 'stop') {
                  return `${t('server.actions.stopped')} ${t('server.actions.withSuccess')}`;
                }
                return lastResponse.message;
              })();

              if (!message) return null;
              return <p className="text-sm text-white/80">{message}</p>;
            })()}
            {lastResponse.final_status && (
              <div className="mt-2 text-xs text-white/60">
                {t('server.status.label')}: {lastResponse.final_status.is_running ? t('server.status.running') : t('server.status.stopped')}
              </div>
            )}
          </div>
        )}

        {/* Mensagem de erro */}
        {error && (
          <div className="mb-6 p-4 rounded-lg bg-red-500/10 border border-red-500/20">
            <div className="flex items-center gap-2 mb-2">
              <AlertCircle size={20} className="text-red-400" />
              <span className="font-semibold text-red-400">{t('server.actions.error')}</span>
            </div>
            <p className="text-sm text-white/80">{error}</p>
          </div>
        )}

        {/* Botões de controle */}
        <div className="flex gap-3">
          <button
            onClick={() => handleAction('start')}
            disabled={isLoading || isRunning}
            className="flex-1 p-3 sm:p-4 rounded-lg bg-green-500/20 hover:bg-green-500/30 border border-green-500/30 disabled:opacity-50 disabled:cursor-not-allowed transition-colors flex items-center justify-center gap-2"
            title={isRunning ? t('server.buttons.start.tooltip') : t('server.buttons.start.label')}
          >
            {loading.action === 'start' ? (
              <Loader2 size={20} className="animate-spin" />
            ) : (
              <Play size={20} />
            )}
            <span className="font-semibold hidden sm:inline">
              {loading.action === 'start' ? t('server.buttons.start.loading') : t('server.buttons.start.label')}
            </span>
          </button>

          <button
            onClick={() => handleAction('stop')}
            disabled={isLoading || isStopped}
            className="flex-1 p-3 sm:p-4 rounded-lg bg-red-500/20 hover:bg-red-500/30 border border-red-500/30 disabled:opacity-50 disabled:cursor-not-allowed transition-colors flex items-center justify-center gap-2"
            title={isStopped ? t('server.buttons.stop.tooltip') : t('server.buttons.stop.label')}
          >
            {loading.action === 'stop' ? (
              <Loader2 size={20} className="animate-spin" />
            ) : (
              <Square size={20} />
            )}
            <span className="font-semibold hidden sm:inline">
              {loading.action === 'stop' ? t('server.buttons.stop.loading') : t('server.buttons.stop.label')}
            </span>
          </button>

          <button
            onClick={() => handleAction('restart')}
            disabled={isLoading || isStopped || isRestarting}
            className="flex-1 p-3 sm:p-4 rounded-lg bg-blue-500/20 hover:bg-blue-500/30 border border-blue-500/30 disabled:opacity-50 disabled:cursor-not-allowed transition-colors flex items-center justify-center gap-2"
            title={
              isStopped
                ? t('server.buttons.restart.tooltip')
                : isRestarting
                  ? t('server.buttons.restart.restarting')
                  : t('server.buttons.restart.label')
            }
          >
            {(loading.action === 'restart' || isRestarting) ? (
              <Loader2 size={20} className="animate-spin" />
            ) : (
              <RotateCw size={20} />
            )}
            <span className="font-semibold hidden sm:inline">
              {isRestarting 
                ? t('server.buttons.restart.restarting')
                : loading.action === 'restart' 
                  ? t('server.buttons.restart.loading') 
                  : t('server.buttons.restart.label')}
            </span>
          </button>
        </div>

        {/* Feedback visual do restart assíncrono */}
        {isRestarting && (
          <div className="mt-4 p-4 rounded-lg bg-blue-500/10 border border-blue-500/20">
            <div className="flex items-center gap-2 mb-2">
              <Loader2 size={18} className="animate-spin text-blue-400" />
              <span className="font-semibold text-blue-400">
                {t('server.actions.restart.inProgress')}
              </span>
            </div>
            <p className="text-sm text-white/70">
              {t('server.actions.restart.message')}
            </p>
            {restartStatus === 'in_progress' && (
              <div className="mt-3 flex items-center gap-2 text-xs text-white/60">
                <RefreshCw size={14} className="animate-spin" />
                <span>{t('server.actions.restart.checking')}</span>
              </div>
            )}
          </div>
        )}

        {/* Informações adicionais */}
        {lastResponse?.data && (
          <div className="mt-6 p-4 rounded-lg bg-black/30 border border-white/5">
            <h3 className="text-sm font-semibold mb-2">{t('server.serverInfo.title')}</h3>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 text-xs text-white/70">
              {lastResponse.data.service_name && (
                <div>
                  <span className="text-white/50">{t('server.serverInfo.service')}:</span> {lastResponse.data.service_name}
                </div>
              )}
              {lastResponse.data.pid !== undefined && (
                <div>
                  <span className="text-white/50">{t('server.serverInfo.pid')}:</span> {lastResponse.data.pid}
                </div>
              )}
              {lastResponse.data.uptime !== undefined && (
                <div>
                  <span className="text-white/50">{t('server.serverInfo.uptime')}:</span> {lastResponse.data.uptime}s
                </div>
              )}
            </div>
          </div>
        )}
      </div>

      {/* Card: Sistema de Agendamento */}
      <div className="card p-4">
        <div className="flex items-center gap-2 mb-4">
          <Clock size={20} />
          <h1 className="text-xl font-semibold">{t('server.scheduler.title')}</h1>
        </div>
        <p className="text-white/70 text-sm mb-6">
          {t('server.scheduler.description')}
        </p>


        {/* Mensagem de erro do agendador */}
        {schedulerError && (
          <div className="mb-6 p-4 rounded-lg bg-red-500/10 border border-red-500/20">
            <div className="flex items-center gap-2 mb-2">
              <AlertCircle size={20} className="text-red-400" />
              <span className="font-semibold text-red-400">{t('server.actions.error')}</span>
            </div>
            <p className="text-sm text-white/80">{schedulerError}</p>
          </div>
        )}

        {/* Tabs */}
        <div className="mb-4 border-b border-white/10">
          <div className="flex gap-2">
            <button
              onClick={() => setSchedulerTab('status')}
              className={`px-4 py-2 text-sm font-medium transition-colors flex items-center gap-2 ${
                schedulerTab === 'status'
                  ? 'text-white border-b-2 border-scum-panel'
                  : 'text-white/60 hover:text-white/80'
              }`}
            >
              <Clock size={16} />
              {t('server.scheduler.tabs.status')}
            </button>
            <button
              onClick={() => setSchedulerTab('config')}
              className={`px-4 py-2 text-sm font-medium transition-colors flex items-center gap-2 ${
                schedulerTab === 'config'
                  ? 'text-white border-b-2 border-scum-panel'
                  : 'text-white/60 hover:text-white/80'
              }`}
            >
              <Settings size={16} />
              {t('server.scheduler.tabs.config')}
            </button>
            <button
              onClick={() => setSchedulerTab('logs')}
              className={`px-4 py-2 text-sm font-medium transition-colors flex items-center gap-2 ${
                schedulerTab === 'logs'
                  ? 'text-white border-b-2 border-scum-panel'
                  : 'text-white/60 hover:text-white/80'
              }`}
            >
              <FileText size={16} />
              {t('server.scheduler.tabs.logs')}
            </button>
          </div>
        </div>

        {/* Tab: Status */}
        {schedulerTab === 'status' && (
          <div className="space-y-4">
            {schedulerLoading.status && !schedulerStatus ? (
              <div className="text-center py-8 text-white/50">
                <Loader2 size={24} className="animate-spin mx-auto mb-2" />
                <div>{t('server.scheduler.logs.loading')}</div>
              </div>
            ) : schedulerStatus ? (
              <>
                <div className="grid grid-cols-2 gap-4">
                  <div className="p-4 rounded-lg bg-black/30 border border-white/5">
                    <div className="text-xs text-white/60 mb-1">{t('server.scheduler.status.nextRestart')}</div>
                    <div className="text-lg font-semibold">
                      {schedulerStatus.next_restart 
                        ? getCountdown(schedulerStatus.next_restart)
                        : t('server.scheduler.status.noRestartScheduled')}
                    </div>
                  </div>

                  <div className="p-4 rounded-lg bg-black/30 border border-white/5">
                    <div className="text-sm font-semibold mb-3">{t('server.scheduler.status.restartTimes')}</div>
                    {schedulerStatus.restart_times.length > 0 ? (
                      <div className="flex flex-wrap gap-2">
                        {schedulerStatus.restart_times.map((time, idx) => (
                          <span key={idx} className="px-3 py-1 bg-white/10 rounded-lg text-sm">
                            {time}
                          </span>
                        ))}
                      </div>
                    ) : (
                      <div className="text-white/50 text-sm">{t('server.scheduler.config.restartTimes.empty')}</div>
                    )}
                  </div>
                </div>
              </>
            ) : (
              <div className="text-center py-8 text-white/50">
                {t('server.scheduler.errors.loadStatus')}
              </div>
            )}
          </div>
        )}

        {/* Tab: Configuração */}
        {schedulerTab === 'config' && (
          <div className="space-y-6">
            {schedulerLoading.config && !schedulerConfig ? (
              <div className="text-center py-8 text-white/50">
                <Loader2 size={24} className="animate-spin mx-auto mb-2" />
                <div>{t('server.scheduler.logs.loading')}</div>
              </div>
            ) : (
              <>
                <div className="p-4 rounded-lg bg-black/30 border border-white/5">
                  <div className="flex items-center justify-between mb-4">
                    <label className="text-sm font-semibold">{t('server.scheduler.config.enabled')}</label>
                    <button
                      onClick={() => setConfigForm(prev => ({ ...prev, enabled: !prev.enabled }))}
                      className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${
                        configForm.enabled ? 'bg-green-500' : 'bg-gray-600'
                      }`}
                    >
                      <span
                        className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
                          configForm.enabled ? 'translate-x-6' : 'translate-x-1'
                        }`}
                      />
                    </button>
                  </div>

                  <div className="flex items-center justify-between">
                    <label className="text-sm font-semibold">{t('server.scheduler.config.autoStart')}</label>
                    <button
                      onClick={() => setConfigForm(prev => ({ ...prev, auto_start: !prev.auto_start }))}
                      className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${
                        configForm.auto_start ? 'bg-green-500' : 'bg-gray-600'
                      }`}
                    >
                      <span
                        className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
                          configForm.auto_start ? 'translate-x-6' : 'translate-x-1'
                        }`}
                      />
                    </button>
                  </div>
                </div>

                <div className="p-4 rounded-lg bg-black/30 border border-white/5">
                  <div className="text-sm font-semibold mb-3">{t('server.scheduler.config.restartTimes.label')}</div>
                  <div className="flex gap-2 mb-3">
                    <select
                      value={selectedHour}
                      onChange={(e) => setSelectedHour(e.target.value)}
                      className="px-3 py-2 bg-black/50 border border-white/10 rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-scum-panel"
                    >
                      {Array.from({ length: 24 }, (_, i) => {
                        const hour = i.toString().padStart(2, '0');
                        return (
                          <option key={hour} value={hour}>
                            {hour}
                          </option>
                        );
                      })}
                    </select>
                    <span className="px-2 py-2 text-white/70">:</span>
                    <select
                      value={selectedMinute}
                      onChange={(e) => setSelectedMinute(e.target.value)}
                      className="px-3 py-2 bg-black/50 border border-white/10 rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-scum-panel"
                    >
                      {Array.from({ length: 60 }, (_, i) => {
                        const minute = i.toString().padStart(2, '0');
                        return (
                          <option key={minute} value={minute}>
                            {minute}
                          </option>
                        );
                      })}
                    </select>
                    <button
                      onClick={handleAddTime}
                      className="px-4 py-2 bg-green-500/20 hover:bg-green-500/30 border border-green-500/30 rounded-lg transition-colors flex items-center gap-2"
                      title={t('server.scheduler.config.restartTimes.add')}
                    >
                      <Plus size={16} />
                      <span className="hidden sm:inline">{t('server.scheduler.config.restartTimes.add')}</span>
                    </button>
                    <button
                      onClick={handleSaveConfig}
                      disabled={schedulerLoading.action === 'save'}
                      className="px-4 py-2 bg-blue-500/20 hover:bg-blue-500/30 border border-blue-500/30 rounded-lg transition-colors flex items-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed"
                      title={t('server.scheduler.config.save.label')}
                    >
                      {schedulerLoading.action === 'save' ? (
                        <Loader2 size={16} className="animate-spin" />
                      ) : (
                        <Save size={16} />
                      )}
                      <span className="hidden sm:inline">{t('server.scheduler.config.save.label')}</span>
                    </button>
                  </div>
                  {configForm.restart_times && configForm.restart_times.length > 0 ? (
                    <div className="flex flex-wrap gap-2">
                      {configForm.restart_times.map((time, idx) => (
                        <span key={idx} className="px-3 py-1 bg-white/10 rounded-lg text-sm flex items-center gap-2">
                          {time}
                          <button
                            onClick={() => handleRemoveTime(time)}
                            className="text-red-400 hover:text-red-300"
                          >
                            <Trash2 size={14} />
                          </button>
                        </span>
                      ))}
                    </div>
                  ) : (
                    <div className="text-white/50 text-sm">{t('server.scheduler.config.restartTimes.empty')}</div>
                  )}
                </div>

                <button
                  onClick={handleSaveConfig}
                  disabled={schedulerLoading.action === 'save'}
                  className="w-full px-4 py-3 bg-green-500/20 hover:bg-green-500/30 border border-green-500/30 rounded-lg transition-colors flex items-center justify-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {schedulerLoading.action === 'save' ? (
                    <Loader2 size={20} className="animate-spin" />
                  ) : (
                    <Save size={20} />
                  )}
                  {schedulerLoading.action === 'save' 
                    ? t('server.scheduler.config.save.loading') 
                    : t('server.scheduler.config.save.label')}
                </button>
              </>
            )}
          </div>
        )}

        {/* Tab: Logs */}
        {schedulerTab === 'logs' && (
          <div className="space-y-4">
            <div className="flex flex-wrap items-center justify-between gap-4">
              <div className="flex items-center gap-2">
                <label className="text-sm text-white/70">{t('server.scheduler.logs.filter.label')}:</label>
                <select
                  value={logsFilter}
                  onChange={(e) => setLogsFilter(e.target.value)}
                  className="px-3 py-1.5 bg-black/50 border border-white/10 rounded-lg text-white text-sm focus:outline-none focus:ring-2 focus:ring-scum-panel"
                >
                  <option value="all">{t('server.scheduler.logs.filter.all')}</option>
                  <option value="notification">{t('server.scheduler.logs.filter.notification')}</option>
                  <option value="restart">{t('server.scheduler.logs.filter.restart')}</option>
                  <option value="scheduler_started">{t('server.scheduler.logs.filter.scheduler_started')}</option>
                  <option value="scheduler_stopped">{t('server.scheduler.logs.filter.scheduler_stopped')}</option>
                  <option value="config_updated">{t('server.scheduler.logs.filter.config_updated')}</option>
                  <option value="restart_scheduled">{t('server.scheduler.logs.filter.restart_scheduled')}</option>
                  <option value="notification_scheduled">{t('server.scheduler.logs.filter.notification_scheduled')}</option>
                  <option value="restart_started">{t('server.scheduler.logs.filter.restart_started')}</option>
                  <option value="restart_success">{t('server.scheduler.logs.filter.restart_success')}</option>
                  <option value="restart_failed">{t('server.scheduler.logs.filter.restart_failed')}</option>
                  <option value="force_restart">{t('server.scheduler.logs.filter.force_restart')}</option>
                </select>
              </div>
              
              <div className="flex items-center gap-2">
                <label className="text-sm text-white/70">{t('server.scheduler.logs.limit')}:</label>
                <input
                  type="number"
                  value={logsLimit}
                  onChange={(e) => {
                    const val = parseInt(e.target.value);
                    if (val > 0 && val <= 500) {
                      setLogsLimit(val);
                      fetchSchedulerLogs();
                    }
                  }}
                  className="w-20 px-3 py-1.5 bg-black/50 border border-white/10 rounded-lg text-white text-sm focus:outline-none focus:ring-2 focus:ring-scum-panel"
                  min={1}
                  max={500}
                />
                <button
                  onClick={fetchSchedulerLogs}
                  disabled={schedulerLoading.logs}
                  className="px-4 py-1.5 bg-black/30 hover:bg-black/50 border border-white/10 rounded-lg transition-colors flex items-center gap-2 disabled:opacity-50"
                >
                  <RefreshCw size={16} className={schedulerLoading.logs ? 'animate-spin' : ''} />
                  {t('server.scheduler.logs.refresh')}
                </button>
              </div>
            </div>

            {schedulerLoading.logs && schedulerLogs.length === 0 ? (
              <div className="text-center py-8 text-white/50">
                <Loader2 size={24} className="animate-spin mx-auto mb-2" />
                <div>{t('server.scheduler.logs.loading')}</div>
              </div>
            ) : filteredLogs.length > 0 ? (
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b border-white/10">
                      <th className="text-left py-2 px-2 text-white/70 font-medium">{t('server.scheduler.logs.columns.timestamp')}</th>
                      <th className="text-left py-2 px-2 text-white/70 font-medium">{t('server.scheduler.logs.columns.eventType')}</th>
                      <th className="text-left py-2 px-2 text-white/70 font-medium">{t('server.scheduler.logs.columns.message')}</th>
                    </tr>
                  </thead>
                  <tbody>
                    {filteredLogs.map((log, idx) => (
                      <tr key={idx} className="border-b border-white/5 hover:bg-white/5">
                        <td className="py-2 px-2 text-white/70 text-xs">{formatDateTime(log.timestamp)}</td>
                        <td className="py-2 px-2">
                          <span className="px-2 py-1 bg-white/10 rounded text-xs">
                            {log.event_type}
                          </span>
                        </td>
                        <td className="py-2 px-2 text-white/80">{log.message}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : (
              <div className="text-center py-8 text-white/50">
                {t('server.scheduler.logs.empty')}
              </div>
            )}
          </div>
        )}
      </div>
      {/* Card: Sistema de Notificações */}
      <div className="card p-4">
        <div className="flex items-center justify-between gap-3 mb-4">
          <div className="flex items-center gap-2">
            <Bell size={20} />
            <h1 className="text-xl font-semibold">{t('server.notifications.title')}</h1>
          </div>
          {isAdmin && (
            <Link
              to="/server/notifications/scheduled"
              className="px-3 py-2 rounded-lg bg-white/5 hover:bg-white/10 border border-white/10 text-white/80 text-sm transition-colors"
            >
              {t('server.notifications.scheduledLink', { defaultValue: 'Scheduled' })}
            </Link>
          )}
        </div>
        <p className="text-white/70 text-sm mb-6">
          {t('server.notifications.description')}
        </p>

        {notificationsError && (
          <div className="mb-4 p-4 rounded-lg bg-red-500/10 border border-red-500/20">
            <div className="flex items-center gap-2 mb-2">
              <AlertCircle size={20} className="text-red-400" />
              <span className="font-semibold text-red-400">{t('server.actions.error')}</span>
            </div>
            <p className="text-sm text-white/80">{notificationsError}</p>
          </div>
        )}


        {notificationsLoading.status && !notificationsStatus && (
          <div className="text-sm text-white/60 mb-4">
            <Loader2 size={16} className="inline mr-2 animate-spin" />
            {t('server.notifications.loading')}
          </div>
        )}

        {notificationTab === 'custom' && (
          <div>
            <form
              onSubmit={handleSendCustomNotification}
              className="p-4 rounded-lg bg-black/30 border border-white/5 space-y-3"
            >
              <div className="flex items-center gap-2">
                <Send size={16} />
                <span className="text-sm font-semibold text-white">
                  {t('server.notifications.forms.custom.title')}
                </span>
              </div>
              <label className="text-xs text-white/60">
                {t('server.notifications.forms.custom.message')}
                <textarea
                  className="mt-1 w-full min-h-[96px] px-3 py-2 bg-black/50 border border-white/10 rounded-lg text-white text-sm focus:outline-none focus:ring-2 focus:ring-scum-panel"
                  value={customNotificationForm.message}
                  onChange={(e) =>
                    setCustomNotificationForm(prev => ({ ...prev, message: e.target.value }))
                  }
                  placeholder={t('server.notifications.forms.custom.placeholder') ?? ''}
                />
              </label>
              <div className="grid sm:grid-cols-2 gap-3">
                <label className="text-xs text-white/60">
                  {t('server.notifications.forms.custom.duration')}
                  <input
                    type="number"
                    min={1}
                    className="mt-1 w-full px-3 py-2 bg-black/50 border border-white/10 rounded-lg text-white text-sm focus:outline-none focus:ring-2 focus:ring-scum-panel"
                    value={customNotificationForm.duration}
                    onChange={(e) =>
                      setCustomNotificationForm(prev => ({
                        ...prev,
                        duration: Number(e.target.value),
                      }))
                    }
                  />
                </label>
                <label className="text-xs text-white/60">
                  {t('server.notifications.forms.custom.color')}
                  <div className="mt-1 flex flex-wrap items-center gap-2">
                    {COLOR_SWATCHES.map((sw) => {
                      const selected = customNotificationForm.color === sw.rgbDash;
                      return (
                        <button
                          key={sw.key}
                          type="button"
                          onClick={() =>
                            setCustomNotificationForm((prev) => ({ ...prev, color: sw.rgbDash }))
                          }
                          className={
                            selected
                              ? 'h-7 w-7 rounded border-2 border-scum-orange shadow'
                              : 'h-7 w-7 rounded border border-white/15 hover:border-white/30'
                          }
                          style={{ backgroundColor: sw.hex }}
                          title={sw.rgbDash}
                          aria-label={t('server.notifications.forms.custom.color')}
                        />
                      );
                    })}
                    <div className="ml-1 inline-flex items-center gap-2 text-xs text-white/50">
                      <span
                        className="inline-block h-4 w-4 rounded border border-white/20"
                        style={{ backgroundColor: rgbDashToCssColor(customNotificationForm.color) }}
                        aria-label={t('server.notifications.forms.custom.color')}
                        title={customNotificationForm.color}
                      />
                      <span className="tabular-nums">{customNotificationForm.color}</span>
                    </div>
                  </div>
                  <input
                    type="text"
                    className="mt-2 w-full px-3 py-2 bg-black/50 border border-white/10 rounded-lg text-white text-sm focus:outline-none focus:ring-2 focus:ring-scum-panel"
                    value={customNotificationForm.color}
                    onChange={(e) =>
                      setCustomNotificationForm((prev) => ({ ...prev, color: e.target.value }))
                    }
                    placeholder="255-255-255"
                  />
                </label>
              </div>
              {isCooldownActive('custom') && (
                <div className="text-xs text-yellow-300 bg-yellow-500/10 border border-yellow-500/20 rounded-lg p-2">
                  {t('server.notifications.cooldowns.blocked', {
                  time: formatCooldown(getCooldownRemaining('custom')),
                  })}
                </div>
              )}
              {!notificationsStatus?.enabled && (
                <div className="text-xs text-red-300 bg-red-500/10 border border-red-500/20 rounded-lg p-2">
                  {t('server.notifications.status.disabledHint')}
                </div>
              )}
              <button
                type="submit"
                disabled={
                  notificationsLoading.custom ||
                  !notificationsStatus?.enabled ||
                  isCooldownActive('custom')
                }
                className="w-full px-4 py-2 bg-green-500/20 hover:bg-green-500/30 border border-green-500/30 rounded-lg transition-colors flex items-center justify-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {notificationsLoading.custom ? (
                  <Loader2 size={18} className="animate-spin" />
                ) : (
                  <Send size={18} />
                )}
                {t('server.notifications.forms.custom.submit')}
              </button>
            </form>
          </div>
        )}
      </div>
    </div>
  );
}
