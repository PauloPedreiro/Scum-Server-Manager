import { useEffect, useMemo, useState } from 'react';
import { useTranslation } from 'react-i18next';
import {
  Bell,
  CalendarClock,
  CheckCircle2,
  FileText,
  Loader2,
  Pencil,
  Plus,
  RefreshCw,
  Save,
  Trash2,
  X,
} from 'lucide-react';
import { alert as showAlert } from '@/lib/alert';
import {
  compileNotifications,
  createScheduledNotification,
  deleteScheduledNotification,
  listScheduledNotifications,
  updateScheduledNotification,
  validateScheduledNotification,
  type CompileResult,
  type Schedule,
  type ScheduledNotification,
  type UpsertScheduledNotificationRequest,
  type ValidateScheduledNotificationResponse,
} from '@/services/scheduledNotifications';

type ScheduleType = Schedule['type'];

type FormState = {
  enabled: boolean;
  title: string;
  message: string;
  color: string;
  duration: number;
  scheduleType: ScheduleType;
  onceDatetime: string;
  dailyTime: string;
  offsetMinutes: number;
};

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

function rgbDashToHexKnown(value: string): string {
  const match = COLOR_SWATCHES.find((x) => x.rgbDash === value);
  return match?.hex || '#ffffff';
}

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

function buildSchedulePayload(form: FormState): Schedule {
  if (form.scheduleType === 'once') {
    return {
      type: 'once',
      datetime: form.onceDatetime,
    };
  }
  if (form.scheduleType === 'daily') {
    return {
      type: 'daily',
      time: form.dailyTime,
    };
  }
  return {
    type: 'relative_to_restart',
    offset_minutes: form.offsetMinutes,
  };
}

function scheduleToLabel(t: (key: string, opts?: any) => string, schedule: Schedule): string {
  if (schedule.type === 'once') {
    return t('server.scheduledNotifications.scheduleLabels.once', {
      defaultValue: 'Uma vez: {{value}}',
      value: schedule.datetime,
    });
  }
  if (schedule.type === 'daily') {
    return t('server.scheduledNotifications.scheduleLabels.daily', {
      defaultValue: 'Diario: {{value}}',
      value: schedule.time,
    });
  }
  const v = schedule.offset_minutes;
  const sign = v >= 0 ? '+' : '';
  return t('server.scheduledNotifications.scheduleLabels.relativeToRestart', {
    defaultValue: 'Restart {{value}} min',
    value: `${sign}${v}`,
  });
}

function formatCompileSummary(t: (key: string, opts?: any) => string, compile?: CompileResult): string {
  if (!compile) {
    return t('server.scheduledNotifications.compile.noInfo', {
      defaultValue: 'Nenhuma informacao de compilacao foi retornada.',
    });
  }
  if (!compile.success) {
    return (
      compile.error ||
      t('server.scheduledNotifications.compile.failed', {
        defaultValue: 'Falha ao compilar.',
      })
    );
  }
  const total = compile.count ?? '-';
  const restart = compile.restart_count ?? '-';
  const custom = compile.custom_count ?? '-';
  const path = compile.path ?? '';
  return `${t('server.scheduledNotifications.compile.ok', {
    defaultValue: 'Compilado com sucesso.',
  })}\n${t('server.scheduledNotifications.compile.summary', {
    defaultValue: 'Total: {{total}} | Restart: {{restart}} | Custom: {{custom}}',
    total,
    restart,
    custom,
  })}${path ? `\n${path}` : ''}`;
}

function getConflictText(
  t: (key: string, opts?: any) => string,
  res: ValidateScheduledNotificationResponse
): string | null {
  if ((res as any)?.error_code === 'SCHEDULE_TIME_RESERVED_BY_RESTART') {
    const r = res as any;
    const d = r.details;
    return [
      r.message,
      '',
      t('server.scheduledNotifications.validate.conflictRequested', {
        defaultValue: 'Solicitado: {{value}}',
        value: d?.requested_time ?? '',
      }),
      t('server.scheduledNotifications.validate.conflictRestart', {
        defaultValue: 'Restart: {{value}}',
        value: d?.conflicting_restart_time ?? '',
      }),
      t('server.scheduledNotifications.validate.conflictWindow', {
        defaultValue: 'Janela reservada: {{start}} -> {{end}}',
        start: d?.reserved_window_start ?? '',
        end: d?.reserved_window_end ?? '',
      }),
    ]
      .filter(Boolean)
      .join('\n');
  }
  return null;
}

const DEFAULT_FORM: FormState = {
  enabled: true,
  title: '',
  message: '',
  color: '255-255-255',
  duration: 15,
  scheduleType: 'daily',
  onceDatetime: '',
  dailyTime: '00:20',
  offsetMinutes: -30,
};

export default function ScheduledNotifications() {
  const { t } = useTranslation();

  const [items, setItems] = useState<ScheduledNotification[]>([]);
  const [loading, setLoading] = useState(false);
  const [busyAction, setBusyAction] = useState<
    null | 'refresh' | 'validate' | 'save' | 'delete' | 'compile'
  >(null);

  const [showForm, setShowForm] = useState(false);
  const [editingItem, setEditingItem] = useState<ScheduledNotification | null>(null);
  const [form, setForm] = useState<FormState>(DEFAULT_FORM);

  const [validatedOk, setValidatedOk] = useState(false);
  const [validatedAt, setValidatedAt] = useState<string | null>(null);

  const canSave = useMemo(() => {
    if (busyAction) return false;
    if (!validatedOk) return false;
    if (!form.message.trim()) return false;
    if (form.duration <= 0) return false;
    if (!form.color.trim()) return false;

    if (form.scheduleType === 'once') return Boolean(form.onceDatetime.trim());
    if (form.scheduleType === 'daily') return Boolean(form.dailyTime.trim());
    return Number.isFinite(form.offsetMinutes);
  }, [busyAction, form, validatedOk]);

  const refresh = async () => {
    setLoading(true);
    setBusyAction('refresh');
    try {
      const res = await listScheduledNotifications();
      if (res.success) {
        setItems(res.items || []);
      } else {
        await showAlert({
          icon: 'error',
          title: t('common.error', { defaultValue: 'Error' }),
          text: res.error || 'Failed to load scheduled notifications.',
        });
      }
    } catch (e: any) {
      await showAlert({
        icon: 'error',
        title: t('common.error', { defaultValue: 'Error' }),
        text: e?.message || 'Failed to load scheduled notifications.',
      });
    } finally {
      setBusyAction(null);
      setLoading(false);
    }
  };

  useEffect(() => {
    void refresh();
  }, []);

  const openCreate = () => {
    setEditingItem(null);
    setForm(DEFAULT_FORM);
    setValidatedOk(false);
    setValidatedAt(null);
    setShowForm(true);
  };

  const openEdit = (item: ScheduledNotification) => {
    setEditingItem(item);
    setForm({
      enabled: item.enabled,
      title: item.title || '',
      message: item.message || '',
      color: item.color || '255-255-255',
      duration: item.duration ?? 15,
      scheduleType: item.schedule.type,
      onceDatetime: item.schedule.type === 'once' ? item.schedule.datetime : '',
      dailyTime: item.schedule.type === 'daily' ? item.schedule.time : '00:20',
      offsetMinutes: item.schedule.type === 'relative_to_restart' ? item.schedule.offset_minutes : -30,
    });
    setValidatedOk(false);
    setValidatedAt(null);
    setShowForm(true);
  };

  const closeForm = () => {
    setShowForm(false);
    setEditingItem(null);
    setForm(DEFAULT_FORM);
    setValidatedOk(false);
    setValidatedAt(null);
  };

  const updateForm = (patch: Partial<FormState>) => {
    setForm((prev) => ({ ...prev, ...patch }));
    setValidatedOk(false);
    setValidatedAt(null);
  };

  const onValidate = async () => {
    setBusyAction('validate');
    try {
      const payload: UpsertScheduledNotificationRequest = {
        enabled: form.enabled,
        title: form.title,
        message: form.message,
        color: form.color,
        duration: form.duration,
        schedule: buildSchedulePayload(form),
      };

      const res = await validateScheduledNotification(payload);
      if ((res as any)?.success === true) {
        setValidatedOk(true);
        const stamp = new Date().toISOString();
        setValidatedAt(stamp);
        await showAlert({
          icon: 'success',
          title: t('common.success', { defaultValue: 'Sucesso' }),
          text: t('server.scheduledNotifications.validate.ok', {
            defaultValue: 'Validacao OK. Agora voce pode salvar.',
          }),
        });
        return;
      }

      const conflictText = getConflictText(t, res);
      if (conflictText) {
        setValidatedOk(false);
        await showAlert({
          icon: 'warning',
          title: t('server.scheduledNotifications.validate.conflictTitle', {
            defaultValue: 'Horario reservado pelo restart',
          }),
          text: conflictText,
        });
        return;
      }

      setValidatedOk(false);
      await showAlert({
        icon: 'error',
        title: t('common.error', { defaultValue: 'Erro' }),
        text: (res as any)?.error || (res as any)?.message || t('server.scheduledNotifications.validate.failed', { defaultValue: 'Falha ao validar.' }),
      });
    } catch (e: any) {
      const status = e?.response?.status;
      if (status === 409) {
        const msg =
          e?.response?.data?.message ||
          e?.response?.data?.error ||
          e?.message ||
          t('server.scheduledNotifications.validate.conflictTitle', {
            defaultValue: 'Horário reservado pelo restart',
          });
        await showAlert({
          icon: 'warning',
          title: t('server.scheduledNotifications.validate.conflictTitle', {
            defaultValue: 'Horario reservado pelo restart',
          }),
          text: msg,
        });
      } else {
        await showAlert({
          icon: 'error',
          title: t('common.error', { defaultValue: 'Erro' }),
          text: e?.message || t('server.scheduledNotifications.validate.failed', { defaultValue: 'Falha ao validar.' }),
        });
      }
    } finally {
      setBusyAction(null);
    }
  };

  const onSave = async () => {
    setBusyAction('save');
    try {
      const payload: UpsertScheduledNotificationRequest = {
        enabled: form.enabled,
        title: form.title,
        message: form.message,
        color: form.color,
        duration: form.duration,
        schedule: buildSchedulePayload(form),
      };

      const res = editingItem
        ? await updateScheduledNotification(editingItem.id, payload)
        : await createScheduledNotification(payload);

      if (!res.success) {
        const errorText = res.error || res.message || t('server.scheduledNotifications.save.failed', { defaultValue: 'Falha ao salvar.' });
        await showAlert({
          icon: 'error',
          title: t('common.error', { defaultValue: 'Erro' }),
          text: errorText,
        });
        return;
      }

      await showAlert({
        icon: 'success',
        title: t('common.success', { defaultValue: 'Sucesso' }),
        text: formatCompileSummary(t, res.compile),
      });

      closeForm();
      await refresh();
    } catch (e: any) {
      const status = e?.response?.status;
      if (status === 409) {
        const msg =
          e?.response?.data?.message ||
          e?.response?.data?.error ||
          e?.message ||
          t('server.scheduledNotifications.validate.conflictTitle', {
            defaultValue: 'Horário reservado pelo restart',
          });
        await showAlert({
          icon: 'warning',
          title: t('server.scheduledNotifications.validate.conflictTitle', {
            defaultValue: 'Horario reservado pelo restart',
          }),
          text: msg,
        });
      } else {
        await showAlert({
          icon: 'error',
          title: t('common.error', { defaultValue: 'Erro' }),
          text: e?.message || t('server.scheduledNotifications.save.failed', { defaultValue: 'Falha ao salvar.' }),
        });
      }
    } finally {
      setBusyAction(null);
    }
  };

  const onDelete = async (item: ScheduledNotification) => {
    const confirm = await showAlert({
      icon: 'warning',
      title: t('server.scheduledNotifications.delete.confirmTitle', { defaultValue: 'Deletar notificação?' }),
      text: t('server.scheduledNotifications.delete.confirmText', {
        defaultValue: 'Isso vai deletar a notificação programada e recompilar o Notifications.json.',
      }),
      showCancelButton: true,
      confirmButtonText: t('common.delete', { defaultValue: 'Deletar' }),
      cancelButtonText: t('common.cancel', { defaultValue: 'Cancelar' }),
    });

    if (!confirm.isConfirmed) return;

    setBusyAction('delete');
    try {
      const res = await deleteScheduledNotification(item.id);
      if (!res.success) {
        await showAlert({
          icon: 'error',
          title: t('common.error', { defaultValue: 'Erro' }),
          text:
            res.error ||
            t('server.scheduledNotifications.delete.failed', {
              defaultValue: 'Falha ao deletar.',
            }),
        });
        return;
      }

      await showAlert({
        icon: 'success',
        title: t('common.success', { defaultValue: 'Sucesso' }),
        text: formatCompileSummary(t, res.compile),
      });

      await refresh();
    } catch (e: any) {
      await showAlert({
        icon: 'error',
        title: t('common.error', { defaultValue: 'Erro' }),
        text:
          e?.message ||
          t('server.scheduledNotifications.delete.failed', {
            defaultValue: 'Falha ao deletar.',
          }),
      });
    } finally {
      setBusyAction(null);
    }
  };

  const onCompile = async () => {
    setBusyAction('compile');
    try {
      const res = await compileNotifications();
      if (!res.success) {
        await showAlert({
          icon: 'error',
          title: t('common.error', { defaultValue: 'Erro' }),
          text: res.error || t('server.scheduledNotifications.compile.failed', { defaultValue: 'Falha ao compilar.' }),
        });
        return;
      }

      await showAlert({
        icon: 'success',
        title: t('common.success', { defaultValue: 'Sucesso' }),
        text: formatCompileSummary(t, res),
      });
    } catch (e: any) {
      await showAlert({
        icon: 'error',
        title: t('common.error', { defaultValue: 'Erro' }),
        text: e?.message || t('server.scheduledNotifications.compile.failed', { defaultValue: 'Falha ao compilar.' }),
      });
    } finally {
      setBusyAction(null);
    }
  };

  return (
    <div className="space-y-4">
      <div className="card p-3 sm:p-4">
        <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3">
          <div className="min-w-0">
            <h1 className="text-lg sm:text-xl font-semibold text-white flex items-center gap-2">
              <CalendarClock size={20} className="flex-shrink-0" />
              <span className="truncate">
                {t('server.scheduledNotifications.title', { defaultValue: 'Notificações Programadas' })}
              </span>
            </h1>
            <p className="text-white/60 text-xs sm:text-sm mt-1">
              {t('server.scheduledNotifications.description', {
                defaultValue:
                  'Crie, valide e compile notificações customizadas para o Notifications.json do SCUM.',
              })}
            </p>
          </div>

          <div className="flex gap-2 w-full sm:w-auto">
            <button
              onClick={refresh}
              disabled={busyAction === 'refresh'}
              className="flex-1 sm:flex-none px-3 sm:px-4 py-2 bg-white/5 text-white rounded-lg font-medium hover:bg-white/10 transition-colors disabled:opacity-50 flex items-center justify-center gap-2 text-sm"
            >
              <RefreshCw size={16} className={busyAction === 'refresh' ? 'animate-spin' : ''} />
              <span className="hidden sm:inline">
                {t('common.refresh', { defaultValue: 'Atualizar' })}
              </span>
            </button>

            <button
              onClick={onCompile}
              disabled={busyAction === 'compile'}
              className="flex-1 sm:flex-none px-3 sm:px-4 py-2 bg-blue-500/20 hover:bg-blue-500/30 border border-blue-500/30 text-white rounded-lg font-medium transition-colors disabled:opacity-50 flex items-center justify-center gap-2 text-sm"
            >
              {busyAction === 'compile' ? (
                <Loader2 size={16} className="animate-spin" />
              ) : (
                <FileText size={16} />
              )}
              <span className="hidden sm:inline">
                {t('server.scheduledNotifications.actions.compile', { defaultValue: 'Compilar' })}
              </span>
            </button>

            <button
              onClick={openCreate}
              className="flex-1 sm:flex-none px-3 sm:px-4 py-2 bg-scum-orange text-white rounded-lg font-medium hover:bg-scum-orange/90 transition-colors flex items-center justify-center gap-2 text-sm"
            >
              <Plus size={16} />
              <span className="hidden sm:inline">
                {t('server.scheduledNotifications.actions.create', { defaultValue: 'Criar' })}
              </span>
            </button>
          </div>
        </div>
      </div>

      {showForm && (
        <div className="card p-4">
          <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 mb-4">
            <div className="min-w-0">
              <div className="text-white font-semibold flex items-center gap-2">
                <Bell size={18} />
                <span className="truncate">
                  {editingItem
                    ? t('server.scheduledNotifications.form.editTitle', { defaultValue: 'Editar notificacao programada' })
                    : t('server.scheduledNotifications.form.createTitle', { defaultValue: 'Criar notificacao programada' })}
                </span>
              </div>
              <div className="text-xs text-white/50 mt-1">
                {validatedOk
                  ? t('server.scheduledNotifications.form.validated', {
                      defaultValue: 'Validado',
                    })
                  : t('server.scheduledNotifications.form.notValidated', {
                      defaultValue: 'Nao validado',
                    })}
                {validatedOk && validatedAt ? ` (${validatedAt})` : ''}
              </div>
            </div>
            <button
              onClick={closeForm}
              className="px-3 py-2 rounded-lg bg-white/5 hover:bg-white/10 border border-white/10 text-white/80 text-sm transition-colors flex items-center gap-2"
              type="button"
            >
              <X size={16} />
              {t('common.cancel', { defaultValue: 'Cancelar' })}
            </button>
          </div>

          <div className="p-4 rounded-lg bg-white/5 border border-white/10 space-y-3">
            <div className="flex items-center justify-between">
              <label className="text-sm font-semibold text-white">
                {t('server.scheduledNotifications.fields.enabled', { defaultValue: 'Ativo' })}
              </label>
              <button
                onClick={() => updateForm({ enabled: !form.enabled })}
                className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${
                  form.enabled ? 'bg-green-500' : 'bg-gray-600'
                }`}
                type="button"
              >
                <span
                  className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
                    form.enabled ? 'translate-x-6' : 'translate-x-1'
                  }`}
                />
              </button>
            </div>

            <label className="text-xs text-white/60">
              {t('server.scheduledNotifications.fields.title', { defaultValue: 'Titulo' })}
              <input
                type="text"
                value={form.title}
                onChange={(e) => updateForm({ title: e.target.value })}
                className="mt-1 w-full px-3 py-2 bg-black/50 border border-white/10 rounded-lg text-white text-sm focus:outline-none focus:ring-2 focus:ring-scum-panel"
                placeholder={t('server.scheduledNotifications.fields.titlePlaceholder', { defaultValue: '(opcional)' })}
              />
            </label>

            <label className="text-xs text-white/60">
              {t('server.scheduledNotifications.fields.message', { defaultValue: 'Mensagem' })} *
              <textarea
                value={form.message}
                onChange={(e) => updateForm({ message: e.target.value })}
                className="mt-1 w-full min-h-[96px] px-3 py-2 bg-black/50 border border-white/10 rounded-lg text-white text-sm focus:outline-none focus:ring-2 focus:ring-scum-panel"
                placeholder={t('server.scheduledNotifications.fields.messagePlaceholder', { defaultValue: 'Mensagem' })}
              />
            </label>

            <div className="grid sm:grid-cols-2 gap-3">
              <label className="text-xs text-white/60">
                {t('server.scheduledNotifications.fields.duration', { defaultValue: 'Duracao (minutos)' })}
                <input
                  type="number"
                  min={1}
                  value={form.duration}
                  onChange={(e) => updateForm({ duration: Number(e.target.value) })}
                  className="mt-1 w-full px-3 py-2 bg-black/50 border border-white/10 rounded-lg text-white text-sm focus:outline-none focus:ring-2 focus:ring-scum-panel"
                />
              </label>

              <label className="text-xs text-white/60">
                {t('server.scheduledNotifications.fields.color', { defaultValue: 'Cor (R-G-B)' })}
                <div className="mt-1 flex flex-wrap items-center gap-2">
                  {COLOR_SWATCHES.map((sw) => {
                    const selected = form.color === sw.rgbDash;
                    return (
                      <button
                        key={sw.key}
                        type="button"
                        onClick={() => updateForm({ color: sw.rgbDash })}
                        className={`h-8 w-8 rounded border transition-colors ${
                          selected
                            ? 'border-scum-orange ring-2 ring-scum-orange/60'
                            : 'border-white/15 hover:border-white/30'
                        }`}
                        style={{ backgroundColor: sw.hex }}
                        title={t(`server.scheduledNotifications.colors.${sw.key}`, {
                          defaultValue: sw.key,
                        })}
                        aria-label={t(`server.scheduledNotifications.colors.${sw.key}`, {
                          defaultValue: sw.key,
                        })}
                      />
                    );
                  })}
                  <div className="ml-1 inline-flex items-center gap-2 text-xs text-white/50">
                    <span
                      className="inline-block h-4 w-4 rounded border border-white/20"
                      style={{ backgroundColor: rgbDashToCssColor(form.color) }}
                      aria-label={t('server.scheduledNotifications.fields.color', { defaultValue: 'Cor (R-G-B)' })}
                      title={form.color}
                    />
                    <span>{form.color}</span>
                  </div>
                </div>
              </label>
            </div>
          </div>

          <div className="p-4 rounded-lg bg-white/5 border border-white/10 space-y-3 mt-4">
            <div className="text-sm font-semibold text-white">
              {t('server.scheduledNotifications.fields.schedule', { defaultValue: 'Agenda' })}
            </div>

            <div className="grid sm:grid-cols-2 gap-3">
              <label className="text-xs text-white/60">
                {t('server.scheduledNotifications.fields.scheduleType', { defaultValue: 'Tipo' })}
                <select
                  value={form.scheduleType}
                  onChange={(e) => updateForm({ scheduleType: e.target.value as ScheduleType })}
                  className="mt-1 w-full px-3 py-2 bg-black/50 border border-white/10 rounded-lg text-white text-sm focus:outline-none focus:ring-2 focus:ring-scum-panel"
                >
                  <option value="once">
                    {t('server.scheduledNotifications.scheduleTypes.once', { defaultValue: 'Uma vez' })}
                  </option>
                  <option value="daily">
                    {t('server.scheduledNotifications.scheduleTypes.daily', { defaultValue: 'Diario' })}
                  </option>
                  <option value="relative_to_restart">
                    {t('server.scheduledNotifications.scheduleTypes.relativeToRestart', {
                      defaultValue: 'Relativo ao restart',
                    })}
                  </option>
                </select>
              </label>

              {form.scheduleType === 'daily' && (
                <label className="text-xs text-white/60">
                  {t('server.scheduledNotifications.fields.dailyTime', { defaultValue: 'Horario (HH:MM)' })}
                  <input
                    type="text"
                    value={form.dailyTime}
                    onChange={(e) => updateForm({ dailyTime: e.target.value })}
                    className="mt-1 w-full px-3 py-2 bg-black/50 border border-white/10 rounded-lg text-white text-sm focus:outline-none focus:ring-2 focus:ring-scum-panel"
                    placeholder="00:20"
                  />
                </label>
              )}

              {form.scheduleType === 'once' && (
                <label className="text-xs text-white/60 sm:col-span-1">
                  {t('server.scheduledNotifications.fields.onceDatetime', { defaultValue: 'Datetime (ISO)' })}
                  <input
                    type="text"
                    value={form.onceDatetime}
                    onChange={(e) => updateForm({ onceDatetime: e.target.value })}
                    className="mt-1 w-full px-3 py-2 bg-black/50 border border-white/10 rounded-lg text-white text-sm focus:outline-none focus:ring-2 focus:ring-scum-panel"
                    placeholder="2026-03-08T00:20:00"
                  />
                </label>
              )}

              {form.scheduleType === 'relative_to_restart' && (
                <label className="text-xs text-white/60">
                  {t('server.scheduledNotifications.fields.offsetMinutes', { defaultValue: 'Offset (minutos)' })}
                  <input
                    type="number"
                    value={form.offsetMinutes}
                    onChange={(e) => updateForm({ offsetMinutes: Number(e.target.value) })}
                    className="mt-1 w-full px-3 py-2 bg-black/50 border border-white/10 rounded-lg text-white text-sm focus:outline-none focus:ring-2 focus:ring-scum-panel"
                  />
                </label>
              )}
            </div>

            <div className="text-xs text-white/50">
              {t('server.scheduledNotifications.fields.schedulePreview', { defaultValue: 'Agenda gerada:' })}{' '}
              <span className="text-white/70">
                {scheduleToLabel(t, buildSchedulePayload(form))}
              </span>
            </div>
          </div>

          <div className="grid sm:grid-cols-2 gap-3 mt-4">
            <button
              type="button"
              onClick={onValidate}
              disabled={busyAction === 'validate'}
              className="w-full px-4 py-3 bg-blue-500/20 hover:bg-blue-500/30 border border-blue-500/30 rounded-lg transition-colors flex items-center justify-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {busyAction === 'validate' ? (
                <Loader2 size={18} className="animate-spin" />
              ) : (
                <CheckCircle2 size={18} />
              )}
              {t('server.scheduledNotifications.actions.validate', { defaultValue: 'Validar' })}
            </button>

            <button
              type="button"
              onClick={onSave}
              disabled={!canSave}
              className="w-full px-4 py-3 bg-green-500/20 hover:bg-green-500/30 border border-green-500/30 rounded-lg transition-colors flex items-center justify-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {busyAction === 'save' ? (
                <Loader2 size={18} className="animate-spin" />
              ) : (
                <Save size={18} />
              )}
              {t('common.save', { defaultValue: 'Salvar' })}
            </button>
          </div>

          {!validatedOk && (
            <div className="text-xs text-yellow-200 bg-yellow-500/10 border border-yellow-500/20 rounded-lg p-3 mt-4">
              {t('server.scheduledNotifications.hints.validateRequired', {
                defaultValue: 'Voce precisa clicar em Validar antes de salvar.',
              })}
            </div>
          )}
        </div>
      )}

      <div className="card p-4">
        {loading && items.length === 0 ? (
          <div className="text-center py-8 text-white/50">
            <Loader2 size={24} className="animate-spin mx-auto mb-2" />
            <div>{t('common.loading', { defaultValue: 'Carregando...' })}</div>
          </div>
        ) : items.length === 0 ? (
          <div className="text-center py-8 text-white/50">
            {t('server.scheduledNotifications.empty', { defaultValue: 'Nenhuma notificação programada.' })}
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-white/10">
                  <th className="text-left py-2 px-2 text-white/70 font-medium">
                    {t('server.scheduledNotifications.table.enabled', { defaultValue: 'Ativo' })}
                  </th>
                  <th className="text-left py-2 px-2 text-white/70 font-medium">
                    {t('server.scheduledNotifications.table.title', { defaultValue: 'Titulo' })}
                  </th>
                  <th className="text-left py-2 px-2 text-white/70 font-medium">
                    {t('server.scheduledNotifications.table.message', { defaultValue: 'Mensagem' })}
                  </th>
                  <th className="text-left py-2 px-2 text-white/70 font-medium">
                    {t('server.scheduledNotifications.table.schedule', { defaultValue: 'Agenda' })}
                  </th>
                  <th className="text-left py-2 px-2 text-white/70 font-medium">
                    {t('server.scheduledNotifications.table.duration', { defaultValue: 'Duracao' })}
                  </th>
                  <th className="text-left py-2 px-2 text-white/70 font-medium">
                    {t('server.scheduledNotifications.table.color', { defaultValue: 'Cor' })}
                  </th>
                  <th className="text-right py-2 px-2 text-white/70 font-medium">
                    {t('server.scheduledNotifications.table.actions', { defaultValue: 'Acoes' })}
                  </th>
                </tr>
              </thead>
              <tbody>
                {items.map((item) => (
                  <tr key={item.id} className="border-b border-white/5">
                    <td className="py-2 px-2 text-white/70">
                      {item.enabled ? (
                        <CheckCircle2 size={16} className="text-green-300" />
                      ) : (
                        <X size={16} className="text-white/40" />
                      )}
                    </td>
                    <td className="py-2 px-2 text-white/80">{item.title || '-'}</td>
                    <td className="py-2 px-2 text-white/70">{item.message}</td>
                    <td className="py-2 px-2 text-white/70">{scheduleToLabel(t, item.schedule)}</td>
                    <td className="py-2 px-2 text-white/70">
                      {t('server.scheduledNotifications.table.durationValue', {
                        defaultValue: '{{value}} min',
                        value: item.duration,
                      })}
                    </td>
                    <td className="py-2 px-2 text-white/70">
                      <div className="inline-flex items-center gap-2">
                        <span
                          className="inline-block h-4 w-4 rounded border border-white/20"
                          style={{ backgroundColor: rgbDashToCssColor(item.color) }}
                          title={item.color}
                          aria-label={t('server.scheduledNotifications.table.color', { defaultValue: 'Cor' })}
                        />
                        <span>{item.color}</span>
                      </div>
                    </td>
                    <td className="py-2 px-2 text-right">
                      <div className="inline-flex items-center gap-2">
                        <button
                          onClick={() => openEdit(item)}
                          className="p-2 rounded bg-white/5 hover:bg-white/10 text-white/80 transition-colors"
                          title={t('server.scheduledNotifications.actions.edit', { defaultValue: 'Editar' })}
                        >
                          <Pencil size={16} />
                        </button>
                        <button
                          onClick={() => onDelete(item)}
                          disabled={busyAction === 'delete'}
                          className="p-2 rounded bg-red-500/10 hover:bg-red-500/20 text-red-200 transition-colors disabled:opacity-50"
                          title={t('common.delete', { defaultValue: 'Deletar' })}
                        >
                          <Trash2 size={16} />
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
