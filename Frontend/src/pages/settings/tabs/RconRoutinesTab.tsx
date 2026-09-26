import { useState, useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import { Loader2, Plus, Trash2, Edit2, Play, Check, X, Clock, AlertTriangle, ChevronDown, ChevronUp, Sparkles, Terminal } from 'lucide-react';
import Swal from 'sweetalert2';
import {
  getRoutines,
  createRoutine,
  updateRoutine,
  deleteRoutine,
  testRoutine,
  RconRoutine,
  RoutineTestResult
} from '@/services/rconRoutines';

interface RconRoutinesTabProps {
  searchQuery?: string;
  onSearchChange?: (query: string) => void;
}

// SCUM SendChat numeric color codes (v2 API — breaking change from HEX)
const COLOR_PRESETS = [
  { value: '7', hex: '#EF4444', nameKey: 'settings.rconRoutines.colors.red',    nameDefault: 'Vermelho' },
  { value: '6', hex: '#F97316', nameKey: 'settings.rconRoutines.colors.orange', nameDefault: 'Laranja'  },
  { value: '4', hex: '#EAB308', nameKey: 'settings.rconRoutines.colors.yellow', nameDefault: 'Amarelo'  },
  { value: '3', hex: '#22C55E', nameKey: 'settings.rconRoutines.colors.green',  nameDefault: 'Verde'    },
  { value: '2', hex: '#38BDF8', nameKey: 'settings.rconRoutines.colors.blue',   nameDefault: 'Azul'     },
  { value: '0', hex: '#F1F5F9', nameKey: 'settings.rconRoutines.colors.white',  nameDefault: 'Branco'   },
];

// Map numeric warning_color value → display hex (for card badge rendering)
const COLOR_HEX_MAP: Record<string, string> = Object.fromEntries(
  COLOR_PRESETS.map(c => [c.value, c.hex])
);

// Resolve a legacy hex or numeric value to a valid numeric string
const resolveWarningColor = (color: string | undefined | null): string => {
  if (!color || color.startsWith('#')) return '7'; // legacy HEX → default red
  return COLOR_PRESETS.some(c => c.value === color) ? color : '7';
};

export default function RconRoutinesTab({ searchQuery = '' }: RconRoutinesTabProps) {
  const { t } = useTranslation();
  const [routines, setRoutines] = useState<RconRoutine[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Form Modal States
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [editingRoutine, setEditingRoutine] = useState<RconRoutine | null>(null);
  const [formName, setFormName] = useState('');
  const [formInterval, setFormInterval] = useState<number>(30);
  const [formEnabled, setFormEnabled] = useState(true);
  const [formCommands, setFormCommands] = useState<string[]>(['']);
  const [formWarningEnabled, setFormWarningEnabled] = useState(false);
  const [formWarningMessage, setFormWarningMessage] = useState('');
  const [formWarningColor, setFormWarningColor] = useState('7'); // numeric SCUM color code
  const [formWarningMinutes, setFormWarningMinutes] = useState<number>(5);
  const [formSubmitting, setFormSubmitting] = useState(false);

  // Warning Section Expand State
  const [isWarningSectionExpanded, setIsWarningSectionExpanded] = useState(false);

  // Test Console Modal States
  const [isConsoleOpen, setIsConsoleOpen] = useState(false);
  const [consoleRoutineName, setConsoleRoutineName] = useState('');
  const [consoleLoading, setConsoleLoading] = useState(false);
  const [consoleResults, setConsoleResults] = useState<RoutineTestResult[]>([]);
  const [consoleError, setConsoleError] = useState<string | null>(null);

  const loadRoutines = async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await getRoutines();
      if (response.success && response.data) {
        setRoutines(response.data);
      } else {
        setError(response.error || t('settings.rconRoutines.error_loading', 'Erro ao carregar as rotinas RCON'));
      }
    } catch (err: any) {
      setError(err.message || t('settings.rconRoutines.error_loading', 'Erro ao carregar as rotinas RCON'));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadRoutines();
  }, []);

  const handleToggleRoutine = async (routine: RconRoutine) => {
    const originalStatus = routine.enabled;
    // Otimista
    setRoutines(prev =>
      prev.map(r => (r.id === routine.id ? { ...r, enabled: !r.enabled } : r))
    );

    try {
      const response = await updateRoutine(routine.id, { enabled: !originalStatus });
      if (!response.success) {
        throw new Error(response.error);
      }
    } catch (err: any) {
      // Reverter
      setRoutines(prev =>
        prev.map(r => (r.id === routine.id ? { ...r, enabled: originalStatus } : r))
      );
      Swal.fire({
        icon: 'error',
        title: t('common.error', 'Erro'),
        text: err.message || t('settings.rconRoutines.toggle_failed', 'Erro ao atualizar status da rotina.'),
        confirmButtonColor: '#f97316'
      });
    }
  };

  const handleOpenCreateModal = () => {
    setEditingRoutine(null);
    setFormName('');
    setFormInterval(30);
    setFormEnabled(true);
    setFormCommands(['']);
    setFormWarningEnabled(false);
    setFormWarningMessage('');
    setFormWarningColor('7');
    setFormWarningMinutes(5);
    setIsWarningSectionExpanded(false);
    setIsModalOpen(true);
  };

  const handleOpenEditModal = (routine: RconRoutine) => {
    setEditingRoutine(routine);
    setFormName(routine.name);
    setFormInterval(routine.interval_minutes);
    setFormEnabled(routine.enabled);
    setFormCommands(routine.commands.length > 0 ? [...routine.commands] : ['']);
    setFormWarningEnabled(routine.warning_enabled);
    setFormWarningMessage(routine.warning_message || '');
    setFormWarningColor(resolveWarningColor(routine.warning_color));
    setFormWarningMinutes(routine.warning_minutes_before || 5);
    setIsWarningSectionExpanded(routine.warning_enabled);
    setIsModalOpen(true);
  };

  const handleAddCommandField = () => {
    setFormCommands(prev => [...prev, '']);
  };

  const handleCommandChange = (index: number, val: string) => {
    setFormCommands(prev => {
      const copy = [...prev];
      copy[index] = val;
      return copy;
    });
  };

  const handleRemoveCommandField = (index: number) => {
    if (formCommands.length === 1) {
      setFormCommands(['']);
      return;
    }
    setFormCommands(prev => prev.filter((_, idx) => idx !== index));
  };

  const handleMoveCommandUp = (index: number) => {
    if (index === 0) return;
    setFormCommands(prev => {
      const copy = [...prev];
      const temp = copy[index - 1];
      copy[index - 1] = copy[index];
      copy[index] = temp;
      return copy;
    });
  };

  const handleMoveCommandDown = (index: number) => {
    if (index === formCommands.length - 1) return;
    setFormCommands(prev => {
      const copy = [...prev];
      const temp = copy[index + 1];
      copy[index + 1] = copy[index];
      copy[index] = temp;
      return copy;
    });
  };

  const handleFormSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const name = formName.trim();
    if (!name) {
      Swal.fire({
        icon: 'warning',
        title: t('common.warning', 'Aviso'),
        text: t('settings.rconRoutines.validation.name_required', 'O nome da rotina é obrigatório.'),
        confirmButtonColor: '#f97316'
      });
      return;
    }

    if (formInterval < 1) {
      Swal.fire({
        icon: 'warning',
        title: t('common.warning', 'Aviso'),
        text: t('settings.rconRoutines.validation.interval_min', 'O intervalo mínimo é de 1 minuto.'),
        confirmButtonColor: '#f97316'
      });
      return;
    }

    const validCommands = formCommands.map(c => c.trim()).filter(c => c !== '');
    if (validCommands.length === 0) {
      Swal.fire({
        icon: 'warning',
        title: t('common.warning', 'Aviso'),
        text: t('settings.rconRoutines.validation.command_required', 'Adicione pelo menos um comando válido.'),
        confirmButtonColor: '#f97316'
      });
      return;
    }

    if (formWarningEnabled) {
      if (formWarningMinutes < 1) {
        Swal.fire({
          icon: 'warning',
          title: t('common.warning', 'Aviso'),
          text: t('settings.rconRoutines.validation.warning_minutes_min', 'O aviso prévio deve ser de pelo menos 1 minuto.'),
          confirmButtonColor: '#f97316'
        });
        return;
      }
      if (formWarningMinutes >= formInterval) {
        Swal.fire({
          icon: 'warning',
          title: t('common.warning', 'Aviso'),
          text: t('settings.rconRoutines.validation.warning_minutes_limit', 'O tempo do aviso prévio deve ser menor que o intervalo da rotina.'),
          confirmButtonColor: '#f97316'
        });
        return;
      }
      if (!formWarningMessage.trim()) {
        Swal.fire({
          icon: 'warning',
          title: t('common.warning', 'Aviso'),
          text: t('settings.rconRoutines.validation.warning_message_required', 'Digite o texto da mensagem do aviso prévio.'),
          confirmButtonColor: '#f97316'
        });
        return;
      }
    }

    const payload = {
      name,
      interval_minutes: formInterval,
      enabled: formEnabled,
      commands: validCommands,
      warning_enabled: formWarningEnabled,
      warning_message: formWarningEnabled ? formWarningMessage : '',
      warning_color: formWarningEnabled ? formWarningColor : '7',
      warning_minutes_before: formWarningEnabled ? formWarningMinutes : 5
    };

    setFormSubmitting(true);
    try {
      if (editingRoutine) {
        const res = await updateRoutine(editingRoutine.id, payload);
        if (res.success && res.data) {
          setRoutines(prev => prev.map(r => (r.id === editingRoutine.id ? res.data! : r)));
          setIsModalOpen(false);
          Swal.fire({
            icon: 'success',
            title: t('settings.rconRoutines.save_success', 'Rotina salva com sucesso!'),
            confirmButtonColor: '#f97316',
            timer: 1500
          });
        } else {
          throw new Error(res.error);
        }
      } else {
        const res = await createRoutine(payload);
        if (res.success && res.data) {
          setRoutines(prev => [...prev, res.data!]);
          setIsModalOpen(false);
          Swal.fire({
            icon: 'success',
            title: t('settings.rconRoutines.create_success', 'Rotina criada com sucesso!'),
            confirmButtonColor: '#f97316',
            timer: 1500
          });
        } else {
          throw new Error(res.error);
        }
      }
    } catch (err: any) {
      Swal.fire({
        icon: 'error',
        title: t('common.error', 'Erro'),
        text: err.message || t('settings.rconRoutines.save_failed', 'Erro ao salvar a rotina.'),
        confirmButtonColor: '#f97316'
      });
    } finally {
      setFormSubmitting(false);
    }
  };

  const handleDeleteRoutine = async (routine: RconRoutine) => {
    const result = await Swal.fire({
      title: t('settings.rconRoutines.delete_confirm_title', 'Excluir rotina?'),
      text: t('settings.rconRoutines.delete_confirm_text', 'Tem certeza que deseja excluir esta rotina periódica? Esta ação não pode ser desfeita.'),
      icon: 'warning',
      showCancelButton: true,
      confirmButtonText: t('common.delete', 'Excluir'),
      cancelButtonText: t('common.cancel', 'Cancelar'),
      confirmButtonColor: '#d33',
      cancelButtonColor: '#3085d6'
    });

    if (result.isConfirmed) {
      try {
        const res = await deleteRoutine(routine.id);
        if (res.success) {
          setRoutines(prev => prev.filter(r => r.id !== routine.id));
          Swal.fire({
            icon: 'success',
            title: t('settings.rconRoutines.delete_success', 'Rotina excluída com sucesso!'),
            confirmButtonColor: '#f97316',
            timer: 1500
          });
        } else {
          throw new Error(res.error);
        }
      } catch (err: any) {
        Swal.fire({
          icon: 'error',
          title: t('common.error', 'Erro'),
          text: err.message || t('settings.rconRoutines.delete_failed', 'Erro ao excluir a rotina.'),
          confirmButtonColor: '#f97316'
        });
      }
    }
  };

  const handleTestRoutine = async (routine: RconRoutine) => {
    setConsoleRoutineName(routine.name);
    setConsoleResults([]);
    setConsoleError(null);
    setConsoleLoading(true);
    setIsConsoleOpen(true);

    try {
      const response = await testRoutine(routine.id);
      if (response.success && response.results) {
        setConsoleResults(response.results);
      } else {
        setConsoleError(response.error || t('settings.rconRoutines.test_failed_msg', 'Erro desconhecido durante o teste de rotina.'));
      }
    } catch (err: any) {
      setConsoleError(err.message || t('settings.rconRoutines.test_failed_msg', 'Erro ao se conectar ao backend para realizar o teste.'));
    } finally {
      setConsoleLoading(false);
      // Recarregar rotinas para atualizar last_run se aplicável
      loadRoutines();
    }
  };

  const formatLastRun = (timestamp: number | null) => {
    if (!timestamp) return t('settings.rconRoutines.never_run', 'Nunca executada');
    const date = new Date(timestamp * 1000);
    return date.toLocaleString(navigator.language, {
      day: '2-digit',
      month: '2-digit',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit'
    });
  };

  const query = searchQuery.toLowerCase().trim();
  const filteredRoutines = routines.filter(
    r =>
      r.name.toLowerCase().includes(query) ||
      r.commands.some(c => c.toLowerCase().includes(query))
  );

  return (
    <div className="space-y-6">
      {/* Top action header */}
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 bg-white/5 border border-white/10 rounded-xl p-4">
        <div>
          <h2 className="text-lg font-bold text-white flex items-center gap-2">
            <Clock className="text-scum-orange w-5 h-5" />
            {t('settings.rconRoutines.title', 'Agendador de Rotinas RCON')}
          </h2>
          <p className="text-xs text-white/60 mt-1">
            {t('settings.rconRoutines.description', 'Gerencie comandos RCON periódicos que serão executados automaticamente no servidor.')}
          </p>
        </div>
        <button
          onClick={handleOpenCreateModal}
          className="w-full sm:w-auto px-4 py-2 bg-scum-orange hover:bg-scum-orange/90 text-white rounded-lg text-sm font-semibold transition-colors flex items-center justify-center gap-2 shadow-lg shadow-scum-orange/20"
        >
          <Plus size={16} />
          {t('settings.rconRoutines.new_button', 'Nova Rotina')}
        </button>
      </div>

      {loading ? (
        <div className="flex items-center justify-center py-12">
          <Loader2 className="w-8 h-8 animate-spin text-scum-orange" />
        </div>
      ) : error ? (
        <div className="card p-6 text-center space-y-4">
          <div className="text-red-400 font-semibold">{error}</div>
          <button
            onClick={loadRoutines}
            className="px-4 py-2 bg-white/5 hover:bg-white/10 border border-white/10 rounded-lg text-sm text-white inline-flex items-center gap-2 transition-colors"
          >
            <Clock size={16} />
            {t('common.retry', 'Tentar novamente')}
          </button>
        </div>
      ) : filteredRoutines.length === 0 ? (
        <div className="text-center py-16 text-white/50 card border-dashed border-white/5 bg-black/10">
          <Clock size={40} className="mx-auto text-white/20 mb-3" />
          <p className="text-sm">
            {query
              ? t('settings.rconRoutines.no_results', 'Nenhuma rotina corresponde à busca.')
              : t('settings.rconRoutines.empty_list', 'Nenhuma rotina agendada ainda. Adicione uma rotina acima.')}
          </p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {filteredRoutines.map(routine => (
            <div
              key={routine.id}
              className={`card flex flex-col justify-between border transition-all ${
                routine.enabled ? 'border-white/10 hover:border-scum-orange/40' : 'border-white/5 bg-black/20 opacity-70'
              }`}
            >
              <div className="p-4 sm:p-5 space-y-4">
                <div className="flex items-start justify-between gap-3">
                  <div>
                    <h3 className="font-bold text-white text-sm line-clamp-1" title={routine.name}>
                      {routine.name}
                    </h3>
                    <div className="flex items-center gap-1.5 text-xs text-white/50 mt-1">
                      <Clock size={12} className="text-scum-orange" />
                      <span>
                        {t('settings.rconRoutines.every_interval', 'A cada {{minutes}} minutos', {
                          minutes: routine.interval_minutes
                        })}
                      </span>
                    </div>
                  </div>
                  <label className="relative inline-flex items-center cursor-pointer flex-shrink-0">
                    <input
                      type="checkbox"
                      checked={routine.enabled}
                      onChange={() => handleToggleRoutine(routine)}
                      className="sr-only peer"
                    />
                    <div className="w-9 h-5 bg-white/10 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-4 after:w-4 after:transition-all peer-checked:bg-scum-orange"></div>
                  </label>
                </div>

                <div className="space-y-1.5 bg-black/30 rounded-lg p-3 font-mono text-[10px] text-white/60 border border-white/5 h-24 overflow-y-auto custom-scrollbar">
                  {routine.commands.map((cmd, idx) => (
                    <div key={idx} className="truncate select-all leading-normal" title={cmd}>
                      <span className="text-scum-orange/70 mr-1">$</span>
                      {cmd}
                    </div>
                  ))}
                </div>

                {routine.warning_enabled && (() => {
                  const badgeHex = COLOR_HEX_MAP[resolveWarningColor(routine.warning_color)] ?? '#EF4444';
                  return (
                    <div
                      className="flex items-center gap-2 px-2.5 py-1.5 rounded-md border text-[10px] leading-tight"
                      style={{
                        borderColor: `${badgeHex}30`,
                        backgroundColor: `${badgeHex}0D`,
                        color: badgeHex
                      }}
                    >
                      <AlertTriangle size={12} className="flex-shrink-0" />
                      <span className="truncate">
                        {t('settings.rconRoutines.warning_active_badge', 'Aviso ({{minutes}}m): "{{message}}"', {
                          minutes: routine.warning_minutes_before,
                          message: routine.warning_message
                        })}
                      </span>
                    </div>
                  );
                })()}

                <div className="flex flex-col gap-1 border-t border-white/5 pt-3 text-[10px] text-white/40 leading-normal">
                  <div className="flex justify-between">
                    <span>{t('settings.rconRoutines.last_run_label', 'Última Execução:')}</span>
                    <span className="font-semibold text-white/60">{formatLastRun(routine.last_run)}</span>
                  </div>
                  {routine.warning_enabled && (
                    <div className="flex justify-between">
                      <span>{t('settings.rconRoutines.last_warning_label', 'Último Aviso:')}</span>
                      <span className="font-semibold text-white/60">{formatLastRun(routine.last_warning_run)}</span>
                    </div>
                  )}
                </div>
              </div>

              <div className="bg-white/5 border-t border-white/5 p-3 flex gap-2">
                <button
                  onClick={() => handleTestRoutine(routine)}
                  className="flex-1 px-2.5 py-1.5 bg-green-500/10 hover:bg-green-500/20 border border-green-500/25 rounded-md text-xs font-semibold text-green-400 transition-colors flex items-center justify-center gap-1.5"
                  title="Testar comando(s) no console agora"
                >
                  <Play size={12} fill="currentColor" />
                  {t('settings.rconRoutines.test_now', 'Testar')}
                </button>
                <button
                  onClick={() => handleOpenEditModal(routine)}
                  className="px-2.5 py-1.5 bg-white/5 hover:bg-white/10 border border-white/10 rounded-md text-xs font-semibold text-white transition-colors flex items-center justify-center"
                  title="Editar rotina"
                >
                  <Edit2 size={12} />
                </button>
                <button
                  onClick={() => handleDeleteRoutine(routine)}
                  className="px-2.5 py-1.5 bg-red-500/5 hover:bg-red-500/15 border border-red-500/20 rounded-md text-xs font-semibold text-red-400 transition-colors flex items-center justify-center"
                  title="Excluir rotina"
                >
                  <Trash2 size={12} />
                </button>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Routine Creation/Edit Modal */}
      {isModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm animate-fadeIn">
          <div className="w-full max-w-2xl bg-scum-panel border border-white/10 rounded-2xl shadow-2xl flex flex-col max-h-[90vh]">
            <div className="flex items-center justify-between p-4 border-b border-white/10">
              <h3 className="text-base font-bold text-white flex items-center gap-2">
                <Sparkles className="text-scum-orange w-4 h-4" />
                {editingRoutine
                  ? t('settings.rconRoutines.edit_modal_title', 'Editar Rotina RCON')
                  : t('settings.rconRoutines.create_modal_title', 'Nova Rotina RCON')}
              </h3>
              <button
                onClick={() => setIsModalOpen(false)}
                className="text-white/40 hover:text-white/80 transition-colors"
              >
                <X size={18} />
              </button>
            </div>

            <form onSubmit={handleFormSubmit} className="flex-1 overflow-y-auto p-5 space-y-5 custom-scrollbar">
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                <div className="sm:col-span-2">
                  <label htmlFor="routine_name" className="text-xs font-semibold text-white/70 block mb-1">
                    {t('settings.rconRoutines.form_name', 'Nome da Rotina')}
                  </label>
                  <input
                    id="routine_name"
                    type="text"
                    value={formName}
                    onChange={e => setFormName(e.target.value)}
                    placeholder={t('settings.rconRoutines.form_name_placeholder', 'Ex: Limpeza de itens no chão')}
                    className="w-full px-3 py-2 bg-white/5 border border-white/10 rounded-lg text-white text-sm focus:outline-none focus:ring-2 focus:ring-scum-orange focus:border-transparent"
                    required
                  />
                </div>
                <div>
                  <label htmlFor="routine_interval" className="text-xs font-semibold text-white/70 block mb-1">
                    {t('settings.rconRoutines.form_interval', 'Intervalo (Minutos)')}
                  </label>
                  <input
                    id="routine_interval"
                    type="number"
                    min="1"
                    value={formInterval}
                    onChange={e => setFormInterval(Number(e.target.value))}
                    className="w-full px-3 py-2 bg-white/5 border border-white/10 rounded-lg text-white text-sm focus:outline-none focus:ring-2 focus:ring-scum-orange focus:border-transparent"
                    required
                  />
                </div>
              </div>

              <div className="flex items-center justify-between bg-white/5 p-3 rounded-lg border border-white/5">
                <div>
                  <span className="text-xs font-semibold text-white block">
                    {t('settings.rconRoutines.form_enabled', 'Ativar Rotina')}
                  </span>
                  <span className="text-[10px] text-white/40">
                    {t('settings.rconRoutines.form_enabled_help', 'Determina se os comandos serão executados periodicamente.')}
                  </span>
                </div>
                <label className="relative inline-flex items-center cursor-pointer">
                  <input
                    type="checkbox"
                    checked={formEnabled}
                    onChange={() => setFormEnabled(!formEnabled)}
                    className="sr-only peer"
                  />
                  <div className="w-11 h-6 bg-white/10 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-scum-orange"></div>
                </label>
              </div>

              {/* RCON Commands List */}
              <div className="space-y-2">
                <div className="flex justify-between items-center">
                  <label className="text-xs font-semibold text-white/70">
                    {t('settings.rconRoutines.form_commands', 'Comandos RCON (em sequência)')}
                  </label>
                  <button
                    type="button"
                    onClick={handleAddCommandField}
                    className="px-2 py-1 bg-white/5 hover:bg-white/10 border border-white/10 rounded text-[10px] text-scum-orange transition-colors flex items-center gap-1"
                  >
                    <Plus size={12} />
                    {t('settings.rconRoutines.add_command_btn', 'Novo Comando')}
                  </button>
                </div>

                <div className="space-y-2 max-h-[160px] overflow-y-auto custom-scrollbar pr-1">
                  {formCommands.map((command, index) => (
                    <div key={index} className="flex gap-1.5 items-center">
                      <span className="text-[10px] font-mono text-white/30 w-5 text-right">{index + 1}.</span>
                      <input
                        type="text"
                        value={command}
                        onChange={e => handleCommandChange(index, e.target.value)}
                        placeholder="#say Mensagem ou #DestroyAllItemsWithinRadius..."
                        className="flex-1 px-3 py-1.5 bg-black/40 border border-white/10 rounded-lg text-white text-xs font-mono focus:outline-none focus:ring-1 focus:ring-scum-orange"
                      />
                      <div className="flex flex-shrink-0 gap-0.5">
                        <button
                          type="button"
                          onClick={() => handleMoveCommandUp(index)}
                          disabled={index === 0}
                          className="p-1.5 bg-white/5 hover:bg-white/10 rounded disabled:opacity-30 disabled:hover:bg-white/5 text-white/60 transition-colors"
                        >
                          <ChevronUp size={12} />
                        </button>
                        <button
                          type="button"
                          onClick={() => handleMoveCommandDown(index)}
                          disabled={index === formCommands.length - 1}
                          className="p-1.5 bg-white/5 hover:bg-white/10 rounded disabled:opacity-30 disabled:hover:bg-white/5 text-white/60 transition-colors"
                        >
                          <ChevronDown size={12} />
                        </button>
                        <button
                          type="button"
                          onClick={() => handleRemoveCommandField(index)}
                          className="p-1.5 bg-red-500/10 hover:bg-red-500/20 text-red-400 rounded transition-colors"
                        >
                          <Trash2 size={12} />
                        </button>
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              {/* Warning/Antecedencia Section (Accordion Style) */}
              <div className="bg-white/5 border border-white/10 rounded-xl overflow-hidden">
                <button
                  type="button"
                  onClick={() => setIsWarningSectionExpanded(!isWarningSectionExpanded)}
                  className="w-full flex items-center justify-between p-4 hover:bg-white/5 transition-colors text-left"
                >
                  <div className="flex items-center gap-2">
                    <AlertTriangle className="text-scum-orange w-4 h-4 flex-shrink-0" />
                    <div>
                      <span className="text-xs font-semibold text-white block">
                        {t('settings.rconRoutines.warning_section_title', 'Aviso Prévio no Chat do Jogo')}
                      </span>
                      <span className="text-[10px] text-white/40">
                        {t('settings.rconRoutines.warning_section_desc', 'Configurar mensagem para alertar os jogadores antes do envio dos comandos.')}
                      </span>
                    </div>
                  </div>
                  {isWarningSectionExpanded ? <ChevronUp size={16} className="text-white/40" /> : <ChevronDown size={16} className="text-white/40" />}
                </button>

                {isWarningSectionExpanded && (
                  <div className="p-4 border-t border-white/5 bg-black/10 space-y-4">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <span className="text-xs font-semibold text-white">
                          {t('settings.rconRoutines.warning_enabled', 'Enviar Aviso Prévio')}
                        </span>
                        {formWarningEnabled && (
                          <div className="flex items-center gap-1.5 ml-2 animate-fadeIn">
                            <input
                              id="warning_minutes"
                              type="number"
                              min="1"
                              max={formInterval - 1}
                              value={formWarningMinutes}
                              onChange={e => setFormWarningMinutes(Number(e.target.value))}
                              className="w-14 px-1.5 py-0.5 bg-black/40 border border-white/15 rounded text-white text-xs text-center font-bold focus:outline-none focus:ring-1 focus:ring-scum-orange"
                              required
                            />
                            <span className="text-[10px] text-white/50">
                              {t('settings.rconRoutines.warning_minutes_suffix', 'minutos antes')}
                            </span>
                            <span className="text-[9px] text-white/35 ml-1" title={t('settings.rconRoutines.warning_minutes_hint', 'Deve ser menor que o intervalo da rotina ({{interval}}m).', { interval: formInterval })}>
                              ({t('settings.rconRoutines.warning_max', 'máx. {{max}}m', { max: formInterval - 1 })})
                            </span>
                          </div>
                        )}
                      </div>
                      <label className="relative inline-flex items-center cursor-pointer">
                        <input
                          type="checkbox"
                          checked={formWarningEnabled}
                          onChange={() => setFormWarningEnabled(!formWarningEnabled)}
                          className="sr-only peer"
                        />
                        <div className="w-11 h-6 bg-white/10 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-scum-orange"></div>
                      </label>
                    </div>

                    {formWarningEnabled && (
                      <div className="space-y-4 animate-fadeIn">
                        {/* Cores sugeridas */}
                        <div className="space-y-2">
                          <label className="text-xs font-semibold text-white/70 block">
                            {t('settings.rconRoutines.warning_color', 'Cor do Aviso')}
                          </label>
                          <div className="flex flex-wrap gap-1.5">
                            {COLOR_PRESETS.map(c => (
                              <button
                                key={c.value}
                                type="button"
                                onClick={() => setFormWarningColor(c.value)}
                                className={`px-2.5 py-1 rounded-lg border text-[11px] transition-colors flex items-center gap-1.5 ${
                                  formWarningColor === c.value
                                    ? 'border-scum-orange bg-scum-orange/10 text-white font-semibold'
                                    : 'border-white/5 bg-white/5 text-white/60 hover:bg-white/10 hover:text-white'
                                }`}
                              >
                                <div className="w-2.5 h-2.5 rounded-full border border-white/20" style={{ backgroundColor: c.hex }} />
                                {t(c.nameKey, c.nameDefault)}
                              </button>
                            ))}
                          </div>
                        </div>

                        {/* Mensagem do aviso */}
                        <div className="space-y-1">
                          <label htmlFor="warning_message" className="text-xs font-semibold text-white/70 block mb-1">
                            {t('settings.rconRoutines.warning_message', 'Mensagem do Aviso')}
                          </label>
                          <input
                            id="warning_message"
                            type="text"
                            value={formWarningMessage}
                            onChange={e => setFormWarningMessage(e.target.value)}
                            placeholder="AVISO: O servidor executará a rotina em {minutes} minutos."
                            className="w-full px-3 py-2 bg-white/5 border border-white/10 rounded-lg text-white text-sm focus:outline-none focus:ring-2 focus:ring-scum-orange focus:border-transparent"
                            required={formWarningEnabled}
                          />
                          <span className="text-[10px] text-white/40 mt-1 block leading-normal">
                            💡 {t('settings.rconRoutines.warning_message_hint', 'Dica: Use {minutes} para que o tempo restante seja substituído dinamicamente.')}
                          </span>
                        </div>
                      </div>
                    )}
                  </div>
                )}
              </div>
            </form>

            <div className="flex gap-3 justify-end p-4 border-t border-white/10">
              <button
                type="button"
                onClick={() => setIsModalOpen(false)}
                className="px-4 py-2 bg-white/5 hover:bg-white/10 border border-white/10 rounded-lg text-xs font-medium text-white transition-colors"
                disabled={formSubmitting}
              >
                {t('common.cancel', 'Cancelar')}
              </button>
              <button
                type="button"
                onClick={handleFormSubmit}
                disabled={formSubmitting}
                className="px-5 py-2 bg-scum-orange hover:bg-scum-orange/90 disabled:bg-scum-orange/50 text-white rounded-lg text-xs font-semibold transition-colors flex items-center gap-1.5 shadow-lg shadow-scum-orange/10"
              >
                {formSubmitting ? (
                  <>
                    <Loader2 size={14} className="animate-spin" />
                    {t('common.saving', 'Salvando...')}
                  </>
                ) : (
                  t('common.save', 'Salvar Alterações')
                )}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Terminal/Console Test Modal */}
      {isConsoleOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70 backdrop-blur-sm animate-fadeIn">
          <div className="w-full max-w-xl bg-scum-panel border border-white/10 rounded-2xl shadow-2xl overflow-hidden flex flex-col max-h-[80vh]">
            <div className="flex items-center justify-between p-4 border-b border-white/10 bg-black/20">
              <div className="flex items-center gap-2">
                <Terminal className="text-green-500 w-4 h-4" />
                <h3 className="text-xs font-bold text-white font-mono uppercase tracking-wide">
                  Console RCON: {consoleRoutineName}
                </h3>
              </div>
              <button
                onClick={() => setIsConsoleOpen(false)}
                className="text-white/40 hover:text-white/80 transition-colors"
                disabled={consoleLoading}
              >
                <X size={18} />
              </button>
            </div>

            <div className="flex-1 bg-black/95 p-4 overflow-y-auto font-mono text-xs text-white/90 space-y-3 min-h-[300px] custom-scrollbar">
              <div className="text-white/40 select-none">
                # ssm-routine-executor --routine="{consoleRoutineName}" --verbose
              </div>
              <div className="text-sky-400">
                [*] {t('settings.rconRoutines.console_starting', 'Iniciando execução da rotina... Aguardando resposta RCON.')}
              </div>

              {consoleLoading && (
                <div className="flex items-center gap-2 text-white/50 pt-2 select-none">
                  <Loader2 size={13} className="animate-spin text-green-500" />
                  <span>{t('settings.rconRoutines.console_executing', 'Executando comandos. Isso pode levar até 25 segundos...')}</span>
                </div>
              )}

              {consoleError && (
                <div className="text-red-500 bg-red-500/10 border border-red-500/20 p-2.5 rounded-lg">
                  [FALHA] {consoleError}
                </div>
              )}

              {consoleResults.length > 0 && (
                <div className="space-y-3 pt-1">
                  {consoleResults.map((res, idx) => (
                    <div
                      key={idx}
                      className={`p-2.5 rounded border leading-relaxed ${
                        res.success
                          ? 'bg-green-500/5 border-green-500/15 text-green-400'
                          : 'bg-red-500/5 border-red-500/15 text-red-400'
                      }`}
                    >
                      <div className="font-semibold flex items-center gap-1.5">
                        <span>{res.success ? '✔ [OK]' : '✘ [FALHA]'}</span>
                        <span className="text-white/80 select-all">${res.command}</span>
                      </div>
                      <div className="mt-1 pl-4 opacity-85 select-all whitespace-pre-wrap">
                        {res.response || t('settings.rconRoutines.console_no_response', '(Sem resposta do console)')}
                      </div>
                    </div>
                  ))}
                  <div className="text-green-500 select-none pt-2 border-t border-white/5">
                    ✔ {t('settings.rconRoutines.console_finished', 'Rotina executada completamente.')}
                  </div>
                </div>
              )}
            </div>

            <div className="flex justify-end p-4 border-t border-white/10 bg-black/20">
              <button
                type="button"
                onClick={() => setIsConsoleOpen(false)}
                className="px-5 py-1.5 bg-white/5 hover:bg-white/10 border border-white/10 rounded-lg text-xs font-semibold text-white transition-colors"
                disabled={consoleLoading}
              >
                {t('common.close', 'Fechar')}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
