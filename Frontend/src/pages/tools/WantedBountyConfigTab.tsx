import { useEffect, useState, useMemo } from 'react';
import { useTranslation } from 'react-i18next';
import Swal from 'sweetalert2';
import {
  Sliders,
  MessageSquare,
  Plus,
  Trash2,
  Skull,
  RefreshCw,
  Save,
  RotateCcw,
  AlertTriangle,
  Info,
  Search,
} from 'lucide-react';
import {
  getBountyConfig,
  updateBountyConfig,
  getActiveBountyPlayers,
  triggerManualBounty,
  resetManualBounty,
  type BountyConfig,
  type ActiveBountyPlayer,
} from '@/services/bounty';
import { getAllPlayers, type AllPlayer } from '@/services/server';

const DEFAULT_CONFIG: BountyConfig = {
  enabled: false,
  killstreak_trigger: 5,
  base_bounty: 500,
  increment_bounty: 100,
  cooldown_hours: 12,
  squad_leave_cooldown_hours: 24,
  discord: {
    top_killers_message_id: '',
    shame_rank_message_id: '',
  },
  notifications: {
    in_game_chat_color: '2',
    activation_template: '⚠️ WANTED: {player} reached a {streak} killstreak and is now WANTED! Bounty: {points} points!',
    increment_template: '🔥 DANGER: Wanted player {player} got another kill (Streak {streak})! Bounty increased to {points} points!',
    claimed_template: '🎯 BOUNTY CLAIMED: {killer} killed wanted player {victim} (Streak {streak}) and won {points} points!',
  },
};

export default function WantedBountyConfigTab() {
  const { t } = useTranslation();

  const [config, setConfig] = useState<BountyConfig>(DEFAULT_CONFIG);
  const [initialConfig, setInitialConfig] = useState<BountyConfig>(DEFAULT_CONFIG);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Active Bounties
  const [activeBounties, setActiveBounties] = useState<ActiveBountyPlayer[]>([]);
  const [loadingBounties, setLoadingBounties] = useState(false);

  // Manual Trigger Modal
  const [modalOpen, setModalOpen] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [players, setPlayers] = useState<AllPlayer[]>([]);
  const [loadingPlayers, setLoadingPlayers] = useState(false);
  const [selectedPlayer, setSelectedPlayer] = useState<AllPlayer | null>(null);
  const [manualBountyValue, setManualBountyValue] = useState<number>(500);

  const isDirty = useMemo(() => {
    return JSON.stringify(config) !== JSON.stringify(initialConfig);
  }, [config, initialConfig]);

  const loadConfig = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await getBountyConfig();
      if (res.success && res.config) {
        const merged: BountyConfig = {
          ...DEFAULT_CONFIG,
          ...res.config,
          discord: {
            ...DEFAULT_CONFIG.discord,
            ...(res.config.discord || {}),
          },
          notifications: {
            ...DEFAULT_CONFIG.notifications,
            ...(res.config.notifications || {}),
          },
        };
        setConfig(merged);
        setInitialConfig(merged);
      }
    } catch (err: any) {
      console.error('[WantedBountyConfigTab] error loading config:', err);
      setError(err?.response?.data?.error || err?.message || 'Erro ao carregar configurações.');
    } finally {
      setLoading(false);
    }
  };

  const loadActiveBounties = async () => {
    setLoadingBounties(true);
    try {
      const res = await getActiveBountyPlayers();
      if (res.success && res.data) {
        setActiveBounties(res.data);
      }
    } catch (err) {
      console.error('[WantedBountyConfigTab] error loading active bounties:', err);
    } finally {
      setLoadingBounties(false);
    }
  };

  useEffect(() => {
    void loadConfig();
    void loadActiveBounties();
  }, []);

  // Player search logic for modal
  useEffect(() => {
    if (!modalOpen) return;
    const handler = setTimeout(async () => {
      setLoadingPlayers(true);
      try {
        const res = await getAllPlayers(20, 0, { q: searchQuery });
        if (res.success && res.data?.players) {
          setPlayers(res.data.players);
        } else {
          setPlayers([]);
        }
      } catch (err) {
        console.error(err);
        setPlayers([]);
      } finally {
        setLoadingPlayers(false);
      }
    }, 300);

    return () => clearTimeout(handler);
  }, [searchQuery, modalOpen]);

  const handleSaveConfig = async () => {
    if (config.killstreak_trigger < 1) {
      void Swal.fire({
        icon: 'error',
        title: t('common.error', { defaultValue: 'Erro' }),
        text: t('tools.shopDeliveries.wantedBounty.validation.triggerMin', {
          defaultValue: 'O gatilho de Killstreak deve ser no mínimo 1.',
        }),
        confirmButtonColor: '#f97316',
      });
      return;
    }

    setSaving(true);
    try {
      const res = await updateBountyConfig(config);
      if (res.success) {
        setInitialConfig(config);
        void Swal.fire({
          icon: 'success',
          title: t('common.saved', { defaultValue: 'Salvo com sucesso' }),
          text: t('tools.shopDeliveries.wantedBounty.saveSuccess', {
            defaultValue: 'Configurações de procurados atualizadas com sucesso.',
          }),
          timer: 1500,
          showConfirmButton: false,
          toast: true,
          position: 'top-end',
        });
      }
    } catch (err: any) {
      console.error(err);
      void Swal.fire({
        icon: 'error',
        title: t('common.error', { defaultValue: 'Erro' }),
        text: err?.response?.data?.error || err?.message || 'Erro ao salvar configurações.',
        confirmButtonColor: '#f97316',
      });
    } finally {
      setSaving(false);
    }
  };

  const handleResetAll = async () => {
    const confirm = await Swal.fire({
      title: t('tools.shopDeliveries.wantedBounty.resetAll.confirmTitle', {
        defaultValue: 'Tem certeza?',
      }),
      text: t('tools.shopDeliveries.wantedBounty.resetAll.confirmText', {
        defaultValue: 'Isso irá limpar o status de PROCURADO de todos os jogadores ativos!',
      }),
      icon: 'warning',
      showCancelButton: true,
      confirmButtonColor: '#ef4444',
      cancelButtonColor: '#6b7280',
      confirmButtonText: t('tools.shopDeliveries.wantedBounty.resetAll.confirmButton', {
        defaultValue: 'Sim, resetar todos!',
      }),
      cancelButtonText: t('common.cancel', { defaultValue: 'Cancelar' }),
    });

    if (!confirm.isConfirmed) return;

    try {
      const res = await resetManualBounty();
      if (res.success) {
        void loadActiveBounties();
        void Swal.fire({
          icon: 'success',
          title: t('common.success', { defaultValue: 'Sucesso' }),
          text: t('tools.shopDeliveries.wantedBounty.resetAll.successText', {
            defaultValue: 'Todos os procurados foram resetados.',
          }),
          timer: 1500,
          showConfirmButton: false,
          toast: true,
          position: 'top-end',
        });
      }
    } catch (err: any) {
      console.error(err);
      void Swal.fire({
        icon: 'error',
        title: t('common.error', { defaultValue: 'Erro' }),
        text: err?.response?.data?.error || err?.message || 'Erro ao resetar procurados.',
        confirmButtonColor: '#f97316',
      });
    }
  };

  const handleResetPlayer = async (steamId: string, playerName: string) => {
    const confirm = await Swal.fire({
      title: t('tools.shopDeliveries.wantedBounty.resetPlayer.confirmTitle', {
        defaultValue: 'Resetar Procurado?',
      }),
      text: t('tools.shopDeliveries.wantedBounty.resetPlayer.confirmText', {
        defaultValue: 'Deseja remover o status de procurado de {{name}}?',
        name: playerName,
      }),
      icon: 'question',
      showCancelButton: true,
      confirmButtonColor: '#ef4444',
      cancelButtonColor: '#6b7280',
      confirmButtonText: t('tools.shopDeliveries.wantedBounty.resetPlayer.confirmButton', {
        defaultValue: 'Sim, resetar',
      }),
      cancelButtonText: t('common.cancel', { defaultValue: 'Cancelar' }),
    });

    if (!confirm.isConfirmed) return;

    try {
      const res = await resetManualBounty(steamId);
      if (res.success) {
        void loadActiveBounties();
        void Swal.fire({
          icon: 'success',
          title: t('common.success', { defaultValue: 'Sucesso' }),
          text: t('tools.shopDeliveries.wantedBounty.resetPlayer.successText', {
            defaultValue: 'Status de procurado de {{name}} resetado.',
            name: playerName,
          }),
          timer: 1500,
          showConfirmButton: false,
          toast: true,
          position: 'top-end',
        });
      }
    } catch (err: any) {
      console.error(err);
      void Swal.fire({
        icon: 'error',
        title: t('common.error', { defaultValue: 'Erro' }),
        text: err?.response?.data?.error || err?.message || 'Erro ao resetar jogador.',
        confirmButtonColor: '#f97316',
      });
    }
  };

  const handleTriggerManual = async () => {
    if (!selectedPlayer) return;

    try {
      const res = await triggerManualBounty(
        selectedPlayer.steam_id,
        selectedPlayer.player_name || 'Desconhecido',
        manualBountyValue
      );

      if (res.success) {
        setModalOpen(false);
        setSelectedPlayer(null);
        setSearchQuery('');
        void loadActiveBounties();
        void Swal.fire({
          icon: 'success',
          title: t('common.success', { defaultValue: 'Sucesso' }),
          text: t('tools.shopDeliveries.wantedBounty.manualTrigger.successText', {
            defaultValue: 'Jogador {{name}} marcado como procurado manualmente.',
            name: selectedPlayer.player_name,
          }),
          timer: 1500,
          showConfirmButton: false,
          toast: true,
          position: 'top-end',
        });
      }
    } catch (err: any) {
      console.error(err);
      void Swal.fire({
        icon: 'error',
        title: t('common.error', { defaultValue: 'Erro' }),
        text: err?.response?.data?.error || err?.message || 'Erro ao acionar recompensa.',
        confirmButtonColor: '#f97316',
      });
    }
  };

  if (loading) {
    return (
      <div className="flex h-64 items-center justify-center">
        <RefreshCw className="h-8 w-8 animate-spin text-scum-orange" />
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {error && (
        <div className="flex items-center gap-2 rounded-lg border border-red-500/20 bg-red-500/10 p-3 text-sm text-red-400">
          <AlertTriangle size={16} />
          <span>{error}</span>
        </div>
      )}

      {/* Top 2 Columns layout */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {/* Left Column: System Variables */}
        <div className="card p-4 space-y-4">
          <div className="flex items-center gap-2 pb-2 border-b border-white/10">
            <Sliders className="text-scum-orange h-5 w-5" />
            <h3 className="text-sm font-semibold text-white">
              {t('tools.shopDeliveries.wantedBounty.tabs.variables', { defaultValue: 'Variáveis do Sistema' })}
            </h3>
          </div>

          <div className="space-y-4">
            {/* Status Toggle */}
            <div className="flex items-center justify-between p-3 rounded-lg bg-white/5 border border-white/5">
              <div>
                <div className="text-sm font-medium text-white">
                  {t('tools.shopDeliveries.wantedBounty.fields.enabled', { defaultValue: 'Ativar Sistema' })}
                </div>
                <div className="text-xs text-white/50">
                  {t('tools.shopDeliveries.wantedBounty.fields.enabledDesc', {
                    defaultValue: 'Ativa ou desativa o sistema de recompensas por killstreak',
                  })}
                </div>
              </div>
              <label className="relative inline-flex items-center cursor-pointer select-none">
                <input
                  type="checkbox"
                  checked={config.enabled}
                  onChange={(e) => setConfig((prev) => ({ ...prev, enabled: e.target.checked }))}
                  className="sr-only peer"
                />
                <div className="w-11 h-6 bg-white/10 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-scum-orange"></div>
              </label>
            </div>

            {/* Numerical Fields Row-by-Row List */}
            <div className="divide-y divide-white/5 bg-[#0b1220]/40 border border-white/10 rounded-lg overflow-hidden">
              {/* Killstreak Trigger */}
              <div className="flex items-center justify-between p-3 hover:bg-white/[0.01] transition-colors">
                <div className="flex flex-col pr-4">
                  <span className="text-sm font-medium text-white/90">
                    {t('tools.shopDeliveries.wantedBounty.fields.killstreakTrigger', {
                      defaultValue: 'Gatilho de Killstreak (Mín. Kills)',
                    })}
                  </span>
                  <span className="text-xs text-white/40 mt-0.5">
                    Número mínimo de kills consecutivas para marcar o jogador como procurado
                  </span>
                </div>
                <input
                  type="number"
                  min="1"
                  max="99"
                  value={config.killstreak_trigger}
                  onChange={(e) => {
                    const val = Math.max(1, parseInt(e.target.value) || 1);
                    setConfig((prev) => ({
                      ...prev,
                      killstreak_trigger: val > 99 ? 99 : val,
                    }));
                  }}
                  className="w-20 px-3 py-1.5 rounded-lg bg-[#0b1220] border border-white/10 text-white text-sm text-center font-semibold focus:outline-none focus:ring-2 focus:ring-scum-orange"
                />
              </div>

              {/* Base Bounty */}
              <div className="flex items-center justify-between p-3 hover:bg-white/[0.01] transition-colors">
                <div className="flex flex-col pr-4">
                  <span className="text-sm font-medium text-white/90">
                    {t('tools.shopDeliveries.wantedBounty.fields.baseBounty', { defaultValue: 'Recompensa Base' })}
                  </span>
                  <span className="text-xs text-white/40 mt-0.5">
                    Recompensa inicial em pontos concedida ao entrar na lista
                  </span>
                </div>
                <input
                  type="number"
                  min="0"
                  max="9999999999"
                  value={config.base_bounty}
                  onChange={(e) => {
                    const val = Math.max(0, parseInt(e.target.value) || 0);
                    setConfig((prev) => ({
                      ...prev,
                      base_bounty: val > 9999999999 ? 9999999999 : val,
                    }));
                  }}
                  className="w-32 px-3 py-1.5 rounded-lg bg-[#0b1220] border border-white/10 text-white text-sm text-right font-semibold focus:outline-none focus:ring-2 focus:ring-scum-orange"
                />
              </div>

              {/* Increment Bounty */}
              <div className="flex items-center justify-between p-3 hover:bg-white/[0.01] transition-colors">
                <div className="flex flex-col pr-4">
                  <span className="text-sm font-medium text-white/90">
                    {t('tools.shopDeliveries.wantedBounty.fields.incrementBounty', {
                      defaultValue: 'Incremento por Kill',
                    })}
                  </span>
                  <span className="text-xs text-white/40 mt-0.5">
                    Adicional somado ao valor da recompensa por cada kill consecutiva extra
                  </span>
                </div>
                <input
                  type="number"
                  min="0"
                  max="9999999999"
                  value={config.increment_bounty}
                  onChange={(e) => {
                    const val = Math.max(0, parseInt(e.target.value) || 0);
                    setConfig((prev) => ({
                      ...prev,
                      increment_bounty: val > 9999999999 ? 9999999999 : val,
                    }));
                  }}
                  className="w-32 px-3 py-1.5 rounded-lg bg-[#0b1220] border border-white/10 text-white text-sm text-right font-semibold focus:outline-none focus:ring-2 focus:ring-scum-orange"
                />
              </div>

              {/* Cooldown (Hours) */}
              <div className="flex items-center justify-between p-3 hover:bg-white/[0.01] transition-colors">
                <div className="flex flex-col pr-4">
                  <span className="text-sm font-medium text-white/90">
                    {t('tools.shopDeliveries.wantedBounty.fields.cooldown', { defaultValue: 'Cooldown (Horas)' })}
                  </span>
                  <span className="text-xs text-white/40 mt-0.5">
                    Tempo de carência (em horas) para o caçador resgatar outra recompensa do mesmo alvo
                  </span>
                </div>
                <input
                  type="number"
                  min="0"
                  max="9999"
                  value={config.cooldown_hours}
                  onChange={(e) => {
                    const val = Math.max(0, parseInt(e.target.value) || 0);
                    setConfig((prev) => ({
                      ...prev,
                      cooldown_hours: val > 9999 ? 9999 : val,
                    }));
                  }}
                  className="w-24 px-3 py-1.5 rounded-lg bg-[#0b1220] border border-white/10 text-white text-sm text-center font-semibold focus:outline-none focus:ring-2 focus:ring-scum-orange"
                />
              </div>

              {/* Squad Leave Cooldown */}
              <div className="flex items-center justify-between p-3 hover:bg-white/[0.01] transition-colors">
                <div className="flex flex-col pr-4">
                  <span className="text-sm font-medium text-white/90">
                    {t('tools.shopDeliveries.wantedBounty.fields.squadCooldown', {
                      defaultValue: 'Cooldown Saída de Squad (Horas)',
                    })}
                  </span>
                  <span className="text-xs text-white/40 mt-0.5">
                    Tempo de restrição ao sair de um squad para impossibilitar abusos de TK
                  </span>
                </div>
                <input
                  type="number"
                  min="0"
                  max="9999"
                  value={config.squad_leave_cooldown_hours}
                  onChange={(e) => {
                    const val = Math.max(0, parseInt(e.target.value) || 0);
                    setConfig((prev) => ({
                      ...prev,
                      squad_leave_cooldown_hours: val > 9999 ? 9999 : val,
                    }));
                  }}
                  className="w-24 px-3 py-1.5 rounded-lg bg-[#0b1220] border border-white/10 text-white text-sm text-center font-semibold focus:outline-none focus:ring-2 focus:ring-scum-orange"
                />
              </div>
            </div>
          </div>
        </div>

        {/* Right Column: In-game Alerts & Discord Tracking */}
        <div className="card p-4 space-y-4">
          <div className="flex items-center gap-2 pb-2 border-b border-white/10">
            <MessageSquare className="text-scum-orange h-5 w-5" />
            <h3 className="text-sm font-semibold text-white">
              {t('tools.shopDeliveries.wantedBounty.tabs.alerts', { defaultValue: 'Alertas e Integração Discord' })}
            </h3>
          </div>

          <div className="space-y-3">
            {/* In-game Chat Color */}
            <div className="space-y-2">
              <label className="block text-xs font-semibold text-white/60 uppercase tracking-wider">
                {t('tools.shopDeliveries.wantedBounty.fields.chatColor', { defaultValue: 'Cor do Chat In-game' })}
              </label>
              <div className="grid grid-cols-2 sm:grid-cols-3 gap-2">
                {[
                  { value: '0', color: 'bg-white border-white/20', label: 'Branco', glow: 'shadow-[0_0_8px_rgba(255,255,255,0.15)]' },
                  { value: '2', color: 'bg-blue-500 border-blue-500/20', label: 'Azul', glow: 'shadow-[0_0_8px_rgba(59,130,246,0.15)]' },
                  { value: '3', color: 'bg-emerald-500 border-emerald-500/20', label: 'Verde', glow: 'shadow-[0_0_8px_rgba(16,185,129,0.15)]' },
                  { value: '4', color: 'bg-yellow-500 border-yellow-500/20', label: 'Amarelo', glow: 'shadow-[0_0_8px_rgba(234,179,8,0.15)]' },
                  { value: '6', color: 'bg-orange-500 border-orange-500/20', label: 'Laranja', glow: 'shadow-[0_0_8px_rgba(249,115,22,0.15)]' },
                  { value: '7', color: 'bg-red-500 border-red-500/20', label: 'Vermelho', glow: 'shadow-[0_0_8px_rgba(239,68,68,0.15)]' },
                ].map((opt) => {
                  const isSelected = config.notifications.in_game_chat_color === opt.value;
                  return (
                    <button
                      key={opt.value}
                      type="button"
                      onClick={() =>
                        setConfig((prev) => ({
                          ...prev,
                          notifications: { ...prev.notifications, in_game_chat_color: opt.value },
                        }))
                      }
                      className={`flex items-center justify-center gap-1.5 px-3 py-2 rounded-lg border text-xs font-semibold transition-all ${
                        isSelected
                          ? `border-scum-orange bg-scum-orange/15 text-white ${opt.glow}`
                          : 'border-white/10 bg-white/5 text-white/60 hover:bg-white/10 hover:text-white/80'
                      }`}
                    >
                      <span className={`w-2 h-2 rounded-full ${opt.color}`} />
                      {opt.label}
                    </button>
                  );
                })}
              </div>
            </div>

            {/* Message templates */}
            <div>
              <label className="block text-xs text-white/60 mb-1">
                {t('tools.shopDeliveries.wantedBounty.fields.activationTemplate', {
                  defaultValue: 'Template de Ativação',
                })}
              </label>
              <textarea
                value={config.notifications.activation_template}
                onChange={(e) =>
                  setConfig((prev) => ({
                    ...prev,
                    notifications: { ...prev.notifications, activation_template: e.target.value },
                  }))
                }
                rows={2}
                className="w-full px-3 py-2 rounded-lg bg-[#0b1220] border border-white/10 text-white text-xs focus:outline-none focus:ring-2 focus:ring-scum-orange"
              />
            </div>

            <div>
              <label className="block text-xs text-white/60 mb-1">
                {t('tools.shopDeliveries.wantedBounty.fields.incrementTemplate', {
                  defaultValue: 'Template de Incremento (Nova Kill)',
                })}
              </label>
              <textarea
                value={config.notifications.increment_template}
                onChange={(e) =>
                  setConfig((prev) => ({
                    ...prev,
                    notifications: { ...prev.notifications, increment_template: e.target.value },
                  }))
                }
                rows={2}
                className="w-full px-3 py-2 rounded-lg bg-[#0b1220] border border-white/10 text-white text-xs focus:outline-none focus:ring-2 focus:ring-scum-orange"
              />
            </div>

            <div>
              <label className="block text-xs text-white/60 mb-1">
                {t('tools.shopDeliveries.wantedBounty.fields.claimedTemplate', {
                  defaultValue: 'Template de Reivindicação (Recompensa Paga)',
                })}
              </label>
              <textarea
                value={config.notifications.claimed_template}
                onChange={(e) =>
                  setConfig((prev) => ({
                    ...prev,
                    notifications: { ...prev.notifications, claimed_template: e.target.value },
                  }))
                }
                rows={2}
                className="w-full px-3 py-2 rounded-lg bg-[#0b1220] border border-white/10 text-white text-xs focus:outline-none focus:ring-2 focus:ring-scum-orange"
              />
            </div>

            {/* Template placeholder details */}
            <div className="rounded-lg bg-white/5 border border-white/5 p-2 text-[10px] text-white/40 space-y-1">
              <div className="font-semibold text-white/60 uppercase">
                {t('tools.shopDeliveries.wantedBounty.fields.placeholdersTitle', { defaultValue: 'Placeholders Dinâmicos:' })}
              </div>
              <div className="grid grid-cols-2 gap-x-2">
                <div><code>{'{player}'}</code>: {t('tools.shopDeliveries.wantedBounty.placeholders.player', { defaultValue: 'Nome do procurado' })}</div>
                <div><code>{'{killer}'}</code>: {t('tools.shopDeliveries.wantedBounty.placeholders.killer', { defaultValue: 'Nome do caçador' })}</div>
                <div><code>{'{victim}'}</code>: {t('tools.shopDeliveries.wantedBounty.placeholders.victim', { defaultValue: 'Nome da vítima' })}</div>
                <div><code>{'{streak}'}</code>: {t('tools.shopDeliveries.wantedBounty.placeholders.streak', { defaultValue: 'Killstreak atual' })}</div>
                <div><code>{'{points}'}</code>: {t('tools.shopDeliveries.wantedBounty.placeholders.points', { defaultValue: 'Valor da recompensa' })}</div>
              </div>
            </div>

            {/* Discord message IDs */}
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 pt-2">
              <div>
                <div className="flex items-center gap-1 mb-1">
                  <label className="text-xs text-white/60">
                    {t('tools.shopDeliveries.wantedBounty.fields.topKillersMsgId', {
                      defaultValue: 'ID da Mensagem Top Killers',
                    })}
                  </label>
                  <div
                    className="cursor-pointer text-white/30 hover:text-white/60"
                    title={t('tools.shopDeliveries.wantedBounty.tooltips.msgId', {
                      defaultValue:
                        'Preenchido automaticamente pelo backend. Apague se quiser forçar o bot a postar uma nova mensagem.',
                    })}
                  >
                    <Info size={12} />
                  </div>
                </div>
                <input
                  type="text"
                  placeholder="—"
                  value={config.discord.top_killers_message_id}
                  onChange={(e) =>
                    setConfig((prev) => ({
                      ...prev,
                      discord: { ...prev.discord, top_killers_message_id: e.target.value.trim() },
                    }))
                  }
                  className="w-full px-3 py-2 rounded-lg bg-[#0b1220] border border-white/10 text-white text-xs focus:outline-none focus:ring-2 focus:ring-scum-orange"
                />
              </div>

              <div>
                <div className="flex items-center gap-1 mb-1">
                  <label className="text-xs text-white/60">
                    {t('tools.shopDeliveries.wantedBounty.fields.shameRankMsgId', {
                      defaultValue: 'ID da Mensagem Shame Rank',
                    })}
                  </label>
                  <div
                    className="cursor-pointer text-white/30 hover:text-white/60"
                    title={t('tools.shopDeliveries.wantedBounty.tooltips.msgId', {
                      defaultValue:
                        'Preenchido automaticamente pelo backend. Apague se quiser forçar o bot a postar uma nova mensagem.',
                    })}
                  >
                    <Info size={12} />
                  </div>
                </div>
                <input
                  type="text"
                  placeholder="—"
                  value={config.discord.shame_rank_message_id}
                  onChange={(e) =>
                    setConfig((prev) => ({
                      ...prev,
                      discord: { ...prev.discord, shame_rank_message_id: e.target.value.trim() },
                    }))
                  }
                  className="w-full px-3 py-2 rounded-lg bg-[#0b1220] border border-white/10 text-white text-xs focus:outline-none focus:ring-2 focus:ring-scum-orange"
                />
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Save & Reset buttons panel */}
      <div className="flex flex-col sm:flex-row gap-2 justify-end">
        <button
          type="button"
          disabled={!isDirty || saving}
          onClick={() => setConfig(initialConfig)}
          className="px-4 py-2 rounded-lg border border-white/10 bg-white/5 text-sm font-semibold text-white/60 hover:bg-white/10 hover:text-white/90 disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
        >
          <RotateCcw size={16} />
          {t('common.revert', { defaultValue: 'Reverter' })}
        </button>

        <button
          type="button"
          disabled={!isDirty || saving}
          onClick={handleSaveConfig}
          className="px-4 py-2 rounded-lg border border-scum-orange bg-scum-orange/20 text-sm font-semibold text-scum-orange hover:bg-scum-orange hover:text-white disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2 transition-colors"
        >
          {saving ? <RefreshCw className="h-4 w-4 animate-spin" /> : <Save size={16} />}
          {saving ? t('common.saving', { defaultValue: 'Salvando...' }) : t('common.save', { defaultValue: 'Salvar' })}
        </button>
      </div>

      {/* Live Monitoring - Active Bounties */}
      <div className="card p-4 space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 border-b border-white/10 pb-3">
          <div className="flex items-center gap-2">
            <Skull className="text-amber-500 h-5 w-5 animate-pulse" />
            <div>
              <h3 className="text-sm font-semibold text-white">
                {t('tools.shopDeliveries.wantedBounty.monitoring.title', { defaultValue: 'Procurados Ativos' })}
              </h3>
              <p className="text-xs text-white/50">
                {t('tools.shopDeliveries.wantedBounty.monitoring.desc', {
                  defaultValue: 'Lista em tempo real de jogadores marcados como procurados',
                })}
              </p>
            </div>
          </div>

          <div className="flex flex-wrap gap-2">
            <button
              type="button"
              disabled={loadingBounties}
              onClick={loadActiveBounties}
              className="px-3 py-1.5 rounded-lg border border-white/10 bg-white/5 text-xs text-white/70 hover:bg-white/10 flex items-center gap-1.5"
            >
              <RefreshCw size={14} className={loadingBounties ? 'animate-spin' : ''} />
              {t('common.refresh', { defaultValue: 'Atualizar' })}
            </button>

            <button
              type="button"
              disabled={activeBounties.length === 0}
              onClick={handleResetAll}
              className="px-3 py-1.5 rounded-lg border border-red-500/30 bg-red-500/10 text-xs text-red-400 hover:bg-red-500/20 disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-1.5 transition-colors"
            >
              <Trash2 size={14} />
              {t('tools.shopDeliveries.wantedBounty.actions.resetAll', { defaultValue: 'Resetar Todos' })}
            </button>

            <button
              type="button"
              onClick={() => setModalOpen(true)}
              className="px-3 py-1.5 rounded-lg border border-scum-orange bg-scum-orange/10 text-xs text-scum-orange hover:bg-scum-orange hover:text-white flex items-center gap-1.5 transition-colors"
            >
              <Plus size={14} />
              {t('tools.shopDeliveries.wantedBounty.actions.triggerManual', {
                defaultValue: 'Definir Procurado Manual',
              })}
            </button>
          </div>
        </div>

        {/* Table */}
        <div className="overflow-x-auto border border-white/10 rounded-lg">
          <table className="min-w-full text-sm">
            <thead className="bg-white/5 text-white/70">
              <tr>
                <th className="text-left px-4 py-2">
                  {t('tools.shopDeliveries.wantedBounty.table.status', { defaultValue: 'Status' })}
                </th>
                <th className="text-left px-4 py-2">
                  {t('tools.shopDeliveries.wantedBounty.table.player', { defaultValue: 'Jogador' })}
                </th>
                <th className="text-left px-4 py-2">
                  {t('tools.shopDeliveries.wantedBounty.table.steamId', { defaultValue: 'Steam ID' })}
                </th>
                <th className="text-center px-4 py-2 font-mono">
                  {t('tools.shopDeliveries.wantedBounty.table.streak', { defaultValue: 'Killstreak' })}
                </th>
                <th className="text-right px-4 py-2">
                  {t('tools.shopDeliveries.wantedBounty.table.bounty', { defaultValue: 'Valor da Recompensa' })}
                </th>
                <th className="text-center px-4 py-2">
                  {t('tools.shopDeliveries.wantedBounty.table.actions', { defaultValue: 'Ações' })}
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-white/5">
              {activeBounties.map((item) => (
                <tr key={item.steam_id} className="hover:bg-white/5 transition-colors">
                  <td className="px-4 py-3">
                    {item.is_online === 1 ? (
                      <span className="inline-flex items-center gap-1 text-xs text-emerald-400 font-semibold bg-emerald-500/10 px-2 py-0.5 rounded-full border border-emerald-500/25">
                        <span className="w-1.5 h-1.5 bg-emerald-400 rounded-full animate-pulse" />
                        ONLINE
                      </span>
                    ) : (
                      <span className="inline-flex items-center gap-1 text-xs text-red-400 font-semibold bg-red-500/10 px-2 py-0.5 rounded-full border border-red-500/25">
                        <span className="w-1.5 h-1.5 bg-red-500 rounded-full" />
                        OFFLINE
                      </span>
                    )}
                  </td>
                  <td className="px-4 py-3 font-semibold text-white/90">{item.player_name}</td>
                  <td className="px-4 py-3 text-xs text-white/60 font-mono">{item.steam_id}</td>
                  <td className="px-4 py-3 text-center text-white/80 tabular-nums">{item.current_streak}</td>
                  <td className="px-4 py-3 text-right">
                    <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-lg border border-amber-500/30 bg-amber-500/10 text-xs font-semibold text-amber-500 select-none shadow-[0_0_8px_rgba(245,158,11,0.08)]">
                      <Skull size={13} className="text-amber-500 animate-spin-slow" />
                      {item.bounty_value.toLocaleString()} {t('common.points', { defaultValue: 'Pts' })}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-center">
                    <button
                      type="button"
                      onClick={() => handleResetPlayer(item.steam_id, item.player_name)}
                      className="p-1 px-2.5 rounded-lg border border-red-500/25 bg-red-500/5 text-xs text-red-400 hover:bg-red-500/15 transition-colors"
                      title={t('tools.shopDeliveries.wantedBounty.actions.resetPlayer', {
                        defaultValue: 'Resetar recompensa deste jogador',
                      })}
                    >
                      {t('tools.shopDeliveries.wantedBounty.actions.resetBtn', { defaultValue: 'Resetar' })}
                    </button>
                  </td>
                </tr>
              ))}

              {activeBounties.length === 0 && !loadingBounties && (
                <tr>
                  <td colSpan={6} className="px-4 py-8 text-center text-white/40">
                    <div className="flex flex-col items-center justify-center gap-2">
                      <Skull size={24} className="text-white/20" />
                      <div>
                        {t('tools.shopDeliveries.wantedBounty.monitoring.empty', {
                          defaultValue: 'Nenhum jogador procurado no momento.',
                        })}
                      </div>
                    </div>
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Manual Trigger Dialog Modal */}
      {modalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4">
          <div className="card w-full max-w-md p-4 space-y-4 border border-white/10 shadow-2xl relative animate-in fade-in-50 zoom-in-95 duration-150">
            <div className="flex items-center justify-between pb-2 border-b border-white/10">
              <h3 className="text-sm font-semibold text-white flex items-center gap-2">
                <Skull size={18} className="text-scum-orange" />
                {t('tools.shopDeliveries.wantedBounty.manualTrigger.title', {
                  defaultValue: 'Definir Procurado Manualmente',
                })}
              </h3>
              <button
                type="button"
                onClick={() => {
                  setModalOpen(false);
                  setSelectedPlayer(null);
                  setSearchQuery('');
                }}
                className="text-white/40 hover:text-white/80 text-sm focus:outline-none"
              >
                ✕
              </button>
            </div>

            <div className="space-y-3">
              {/* Search Player Input */}
              {!selectedPlayer ? (
                <div>
                  <label className="block text-xs text-white/60 mb-1">
                    {t('tools.shopDeliveries.wantedBounty.manualTrigger.searchLabel', { defaultValue: 'Buscar Jogador' })}
                  </label>
                  <div className="relative">
                    <Search className="absolute left-3 top-2.5 h-4 w-4 text-white/30" />
                    <input
                      type="text"
                      placeholder={t('tools.shopDeliveries.wantedBounty.manualTrigger.searchPlaceholder', {
                        defaultValue: 'Nome ou Steam ID...',
                      })}
                      value={searchQuery}
                      onChange={(e) => setSearchQuery(e.target.value)}
                      className="w-full pl-9 pr-3 py-2 rounded-lg bg-[#0b1220] border border-white/10 text-white text-sm focus:outline-none focus:ring-2 focus:ring-scum-orange"
                    />
                  </div>

                  {/* List of found players */}
                  <div className="mt-2 max-h-40 overflow-y-auto border border-white/10 rounded-lg divide-y divide-white/5 bg-black/10">
                    {loadingPlayers ? (
                      <div className="p-3 text-center text-xs text-white/50 flex items-center justify-center gap-1">
                        <RefreshCw className="h-3 w-3 animate-spin text-scum-orange" />
                        {t('common.loading', { defaultValue: 'Carregando...' })}
                      </div>
                    ) : players.length === 0 ? (
                      <div className="p-3 text-center text-xs text-white/40">
                        {searchQuery
                          ? t('tools.shopDeliveries.wantedBounty.manualTrigger.noPlayers', {
                              defaultValue: 'Nenhum jogador encontrado.',
                            })
                          : t('tools.shopDeliveries.wantedBounty.manualTrigger.startSearch', {
                              defaultValue: 'Digite para buscar...',
                            })}
                      </div>
                    ) : (
                      players.map((p) => (
                        <div
                          key={p.steam_id}
                          onClick={() => setSelectedPlayer(p)}
                          className="p-2.5 hover:bg-white/5 cursor-pointer flex justify-between items-center text-xs transition-colors"
                        >
                          <div>
                            <div className="font-semibold text-white/90">{p.player_name}</div>
                            <div className="text-white/40 font-mono text-[10px]">{p.steam_id}</div>
                          </div>
                          <span className="text-[10px] text-scum-orange font-semibold bg-scum-orange/10 border border-scum-orange/20 px-2 py-0.5 rounded-full">
                            {t('tools.shopDeliveries.wantedBounty.manualTrigger.select', { defaultValue: 'Selecionar' })}
                          </span>
                        </div>
                      ))
                    )}
                  </div>
                </div>
              ) : (
                /* Chosen Player Details */
                <div className="p-3 rounded-lg border border-scum-orange/20 bg-scum-orange/5 space-y-2">
                  <div className="flex justify-between items-start">
                    <div>
                      <div className="text-xs text-white/40 uppercase font-semibold">
                        {t('tools.shopDeliveries.wantedBounty.manualTrigger.selectedPlayer', {
                          defaultValue: 'Jogador Selecionado',
                        })}
                      </div>
                      <div className="font-semibold text-white text-sm">{selectedPlayer.player_name}</div>
                      <div className="text-xs text-white/50 font-mono">{selectedPlayer.steam_id}</div>
                    </div>
                    <button
                      type="button"
                      onClick={() => setSelectedPlayer(null)}
                      className="text-xs text-scum-orange hover:underline focus:outline-none"
                    >
                      {t('common.change', { defaultValue: 'Alterar' })}
                    </button>
                  </div>
                </div>
              )}

              {/* Bounty Reward Input */}
              <div>
                <label className="block text-xs text-white/60 mb-1">
                  {t('tools.shopDeliveries.wantedBounty.manualTrigger.valueLabel', {
                    defaultValue: 'Valor da Recompensa (Pontos)',
                  })}
                </label>
                <input
                  type="number"
                  min="0"
                  value={manualBountyValue}
                  onChange={(e) => setManualBountyValue(Math.max(0, parseInt(e.target.value) || 0))}
                  className="w-full px-3 py-2 rounded-lg bg-[#0b1220] border border-white/10 text-white text-sm focus:outline-none focus:ring-2 focus:ring-scum-orange"
                />
              </div>
            </div>

            {/* Modal Actions */}
            <div className="flex gap-2 justify-end pt-2">
              <button
                type="button"
                onClick={() => {
                  setModalOpen(false);
                  setSelectedPlayer(null);
                  setSearchQuery('');
                }}
                className="px-4 py-2 rounded-lg border border-white/15 bg-white/8 text-xs font-semibold text-white/80 hover:text-white hover:bg-white/12"
              >
                {t('common.cancel', { defaultValue: 'Cancelar' })}
              </button>

              <button
                type="button"
                disabled={!selectedPlayer}
                onClick={handleTriggerManual}
                className="px-4 py-2 rounded-lg border border-scum-orange bg-scum-orange/20 text-xs font-semibold text-scum-orange hover:bg-scum-orange hover:text-white disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
              >
                {t('tools.shopDeliveries.wantedBounty.manualTrigger.submit', { defaultValue: 'Tornar Procurado' })}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
