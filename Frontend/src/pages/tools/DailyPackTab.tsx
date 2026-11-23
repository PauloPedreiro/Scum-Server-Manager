import { useEffect, useMemo, useRef, useState } from 'react';
import Swal from 'sweetalert2';
import {
  Gift,
  MessageSquare,
  Package,
  RefreshCw,
  RotateCcw,
  Save,
  Send,
  Users,
  History,
  CheckCircle2,
  Clock,
} from 'lucide-react';
import {
  getShopAdminDailyPackConfig,
  getShopAdminDailyPackHistory,
  getShopAdminDailyPackPlayers,
  patchShopAdminDailyPackConfig,
  resetShopAdminDailyPackPlayer,
  testShopAdminDailyPackReminder,
  type DailyPackConfigPayload,
  type DailyPackHistoryItem,
  type DailyPackKitDetails,
  type DailyPackPlayerItem,
} from '@/services/shopAdmin';

function formatCooldownRemaining(seconds: number): string {
  const s = Math.max(0, Math.floor(seconds));
  const h = Math.floor(s / 3600);
  const m = Math.floor((s % 3600) / 60);
  return `${String(h).padStart(2, '0')}h ${String(m).padStart(2, '0')}m`;
}

function formatDateTimePtBr(raw: string | null | undefined): string {
  if (!raw) return '—';
  const trimmed = String(raw).trim();
  if (!trimmed) return '—';
  let normalized = trimmed.includes('T') ? trimmed : trimmed.replace(' ', 'T');
  if (!/(Z|[+-]\d{2}:?\d{2})$/i.test(normalized)) {
    normalized += 'Z';
  }
  const d = new Date(normalized);
  if (Number.isNaN(d.getTime())) {
    return trimmed;
  }
  return d.toLocaleString('pt-BR');
}

const CHAT_COLOR_OPTIONS = [
  { value: 0, label: '0 - Padrão / Branco' },
  { value: 1, label: '1 - Cinza' },
  { value: 2, label: '2 - Amarelo / Dourado' },
  { value: 3, label: '3 - Azul Claro' },
  { value: 4, label: '4 - Azul Escuro' },
  { value: 5, label: '5 - Roxo' },
  { value: 6, label: '6 - Verde (Destaque positivo)' },
  { value: 7, label: '7 - Vermelho (Aviso)' },
  { value: 8, label: '8 - Laranja' },
  { value: 9, label: '9 - Rosa' },
];

export default function DailyPackTab() {
  const [leftTab, setLeftTab] = useState<'kit' | 'reminder'>('kit');
  const [rightTab, setRightTab] = useState<'players' | 'history'>('players');

  // Config + kits state
  const [configPayload, setConfigPayload] = useState<DailyPackConfigPayload | null>(null);
  const [configLoading, setConfigLoading] = useState(false);
  const [configSaving, setConfigSaving] = useState(false);
  const [configError, setConfigError] = useState<string | null>(null);
  const [testingReminder, setTestingReminder] = useState(false);

  // Editable draft fields
  const [enabled, setEnabled] = useState(true);
  const [selectedKitCode, setSelectedKitCode] = useState<string>('');
  const [cooldownHours, setCooldownHours] = useState<string>('24');
  const [bonusCoins, setBonusCoins] = useState<string>('50');
  const [discordInviteUrl, setDiscordInviteUrl] = useState<string>('');
  const [reminderEnabled, setReminderEnabled] = useState<boolean>(false);
  const [reminderIntervalMinutes, setReminderIntervalMinutes] = useState<string>('30');
  const [reminderChatColor, setReminderChatColor] = useState<number>(6);
  const [reminderMessage, setReminderMessage] = useState<string>('');

  // Registered players table state
  const [players, setPlayers] = useState<DailyPackPlayerItem[]>([]);
  const [playersTotal, setPlayersTotal] = useState(0);
  const [playersSummary, setPlayersSummary] = useState({
    total_registered: 0,
    claimed_in_cycle: 0,
    available_now: 0,
    never_claimed: 0,
  });
  const [playersPage, setPlayersPage] = useState(1);
  const [playersLimit] = useState(50);
  const [playersQuery, setPlayersQuery] = useState('');
  const [playersStatusFilter, setPlayersStatusFilter] = useState<'all' | 'claimed' | 'available' | 'never'>('all');
  const [playersSortBy, setPlayersSortBy] = useState<string>('last_command_at');
  const [playersSortOrder, setPlayersSortOrder] = useState<'asc' | 'desc'>('desc');
  const [playersBusy, setPlayersBusy] = useState(false);
  const [playersError, setPlayersError] = useState<string | null>(null);
  const [resettingSteamId, setResettingSteamId] = useState<string | null>(null);

  // History table state
  const [historyItems, setHistoryItems] = useState<DailyPackHistoryItem[]>([]);
  const [historyTotal, setHistoryTotal] = useState(0);
  const [historyPage, setHistoryPage] = useState(1);
  const [historyLimit] = useState(50);
  const [historyQuery, setHistoryQuery] = useState('');
  const [historyBusy, setHistoryBusy] = useState(false);
  const [historyError, setHistoryError] = useState<string | null>(null);

  const syncFormFromPayload = (data: DailyPackConfigPayload) => {
    setConfigPayload(data);
    const cfg = data.config;
    setEnabled(Boolean(cfg.enabled));
    const effectiveCode = data.active_kit?.code ?? cfg.kit_code;
    setSelectedKitCode(effectiveCode != null ? String(effectiveCode) : '');
    const hrs = Math.max(1, Math.round((Number(cfg.cooldown_seconds || 86400) / 3600) * 100) / 100);
    setCooldownHours(String(hrs));
    setBonusCoins(String(cfg.bonus_coins ?? 0));
    setDiscordInviteUrl(cfg.discord_invite_url || '');
    setReminderEnabled(Boolean(cfg.reminder_enabled));
    setReminderIntervalMinutes(String(cfg.reminder_interval_minutes ?? 30));
    setReminderChatColor(Number(cfg.reminder_chat_color ?? 6));
    setReminderMessage(cfg.reminder_message || '');
  };

  const loadConfig = async () => {
    setConfigLoading(true);
    setConfigError(null);
    try {
      const res = await getShopAdminDailyPackConfig();
      if (res.success && res.data) {
        syncFormFromPayload(res.data);
      } else {
        setConfigError((res as any).error || (res as any).message || 'Erro ao carregar configuração do DailyPack');
      }
    } catch (err: any) {
      setConfigError(err?.response?.data?.error || err?.message || 'Erro ao carregar configuração do DailyPack');
    } finally {
      setConfigLoading(false);
    }
  };

  const loadPlayers = async (
    page = playersPage,
    q = playersQuery,
    status = playersStatusFilter,
    sortBy = playersSortBy,
    sortOrder = playersSortOrder
  ) => {
    setPlayersBusy(true);
    setPlayersError(null);
    try {
      const offset = Math.max(0, (page - 1) * playersLimit);
      const res = await getShopAdminDailyPackPlayers({
        limit: playersLimit,
        offset,
        q: q.trim() || undefined,
        status,
        sort_by: sortBy,
        sort_order: sortOrder,
      });
      if (res.success && res.data) {
        setPlayers(res.data.items || []);
        setPlayersTotal(Number(res.data.total || 0));
        if (res.data.summary) {
          setPlayersSummary(res.data.summary);
        }
        setPlayersPage(page);
      } else {
        setPlayersError((res as any).error || 'Erro ao carregar jogadores registrados');
      }
    } catch (err: any) {
      setPlayersError(err?.response?.data?.error || err?.message || 'Erro ao carregar jogadores registrados');
    } finally {
      setPlayersBusy(false);
    }
  };

  const loadHistory = async (page = historyPage, q = historyQuery) => {
    setHistoryBusy(true);
    setHistoryError(null);
    try {
      const offset = Math.max(0, (page - 1) * historyLimit);
      const res = await getShopAdminDailyPackHistory({
        limit: historyLimit,
        offset,
        q: q.trim() || undefined,
      });
      if (res.success && res.data) {
        setHistoryItems(res.data.items || []);
        setHistoryTotal(Number(res.data.total || 0));
        setHistoryPage(page);
      } else {
        setHistoryError((res as any).error || 'Erro ao carregar histórico do DailyPack');
      }
    } catch (err: any) {
      setHistoryError(err?.response?.data?.error || err?.message || 'Erro ao carregar histórico do DailyPack');
    } finally {
      setHistoryBusy(false);
    }
  };

  const playersMountedRef = useRef(false);

  useEffect(() => {
    void loadConfig();
    void loadPlayers(1, '', 'all', 'last_command_at', 'desc');
  }, []);

  useEffect(() => {
    if (!playersMountedRef.current) {
      playersMountedRef.current = true;
      return;
    }
    const tmr = setTimeout(() => {
      void loadPlayers(1, playersQuery, playersStatusFilter, playersSortBy, playersSortOrder);
    }, 250);
    return () => clearTimeout(tmr);
  }, [playersQuery, playersStatusFilter, playersSortBy, playersSortOrder]);

  useEffect(() => {
    if (rightTab !== 'history') return;
    const tmr = setTimeout(() => {
      void loadHistory(1, historyQuery);
    }, 250);
    return () => clearTimeout(tmr);
  }, [rightTab, historyQuery]);

  // Preview instantâneo do kit selecionado no dropdown
  const previewKit: DailyPackKitDetails | null = useMemo(() => {
    if (!configPayload) return null;
    if (!selectedKitCode) return null;
    const num = Number(selectedKitCode);
    const found = (configPayload.available_kits || []).find((k) => Number(k.code) === num);
    if (found) return found;
    if (configPayload.active_kit && Number(configPayload.active_kit.code) === num) {
      return configPayload.active_kit;
    }
    return null;
  }, [configPayload, selectedKitCode]);

  const handleSaveConfig = async () => {
    const hrsNum = Number(cooldownHours);
    if (Number.isNaN(hrsNum) || hrsNum <= 0) {
      await Swal.fire({
        icon: 'warning',
        title: 'Cooldown inválido',
        text: 'Informe um cooldown em horas maior que zero.',
        confirmButtonColor: '#f97316',
      });
      return;
    }

    const coinsNum = Number(bonusCoins);
    if (Number.isNaN(coinsNum) || coinsNum < 0) {
      await Swal.fire({
        icon: 'warning',
        title: 'Coins inválidos',
        text: 'O bônus em coins não pode ser negativo.',
        confirmButtonColor: '#f97316',
      });
      return;
    }

    const intervalNum = Number(reminderIntervalMinutes);
    if (Number.isNaN(intervalNum) || intervalNum < 1) {
      await Swal.fire({
        icon: 'warning',
        title: 'Intervalo inválido',
        text: 'O cooldown do aviso no chat deve ser de pelo menos 1 minuto.',
        confirmButtonColor: '#f97316',
      });
      return;
    }

    setConfigSaving(true);
    try {
      const selectedObj = previewKit;
      const res = await patchShopAdminDailyPackConfig({
        enabled,
        kit_code: selectedKitCode ? Number(selectedKitCode) : null,
        kit_id: selectedObj ? selectedObj.kit_id : null,
        cooldown_hours: hrsNum,
        bonus_coins: Math.floor(coinsNum),
        discord_invite_url: discordInviteUrl.trim(),
        reminder_enabled: reminderEnabled,
        reminder_interval_minutes: Math.floor(intervalNum),
        reminder_chat_color: reminderChatColor,
        reminder_message: reminderMessage,
      });

      if (res.success && res.data) {
        syncFormFromPayload(res.data);
        await loadPlayers(playersPage, playersQuery, playersStatusFilter, playersSortBy, playersSortOrder);
        await Swal.fire({
          icon: 'success',
          title: 'DailyPack salvo!',
          text: 'Configurações do comando /daily, kit, aviso e Discord foram atualizadas.',
          confirmButtonColor: '#f97316',
        });
      } else {
        throw new Error((res as any).error || 'Erro ao salvar configuração');
      }
    } catch (err: any) {
      await Swal.fire({
        icon: 'error',
        title: 'Erro ao salvar',
        text: err?.response?.data?.error || err?.message || 'Não foi possível salvar.',
        confirmButtonColor: '#f97316',
      });
    } finally {
      setConfigSaving(false);
    }
  };

  const handleTestReminder = async () => {
    setTestingReminder(true);
    try {
      const res = await testShopAdminDailyPackReminder({
        reminder_message: reminderMessage,
        reminder_chat_color: reminderChatColor,
        discord_invite_url: discordInviteUrl.trim(),
      });
      if (res.success && res.data) {
        const d = res.data;
        if (d.sent) {
          await Swal.fire({
            icon: 'success',
            title: 'Aviso enviado ao chat!',
            text: `Enviado para ${d.players_notified} jogador(es) online (${d.online_unregistered} não registrado(s)).`,
            confirmButtonColor: '#f97316',
          });
          void loadConfig();
        } else {
          const reasonMap: Record<string, string> = {
            no_players_online: 'Nenhum jogador online encontrado na tabela players_online no momento.',
            rcon_disabled: 'O RCON está desativado nas configurações do servidor.',
            empty_message: 'A mensagem configurada está vazia.',
          };
          await Swal.fire({
            icon: 'info',
            title: 'Envio não realizado',
            text: reasonMap[String(d.reason || '')] || `Motivo: ${d.reason || 'indisponível'}`,
            confirmButtonColor: '#f97316',
          });
        }
      } else {
        throw new Error((res as any).error || 'Falha ao testar aviso');
      }
    } catch (err: any) {
      await Swal.fire({
        icon: 'error',
        title: 'Erro ao testar aviso',
        text: err?.response?.data?.error || err?.message || 'Erro desconhecido.',
        confirmButtonColor: '#f97316',
      });
    } finally {
      setTestingReminder(false);
    }
  };

  const handleResetPlayer = async (player: DailyPackPlayerItem) => {
    const confirm = await Swal.fire({
      icon: 'warning',
      title: 'Resetar cooldown do /daily?',
      text: `Isso liberará imediatamente o /daily para ${player.player_name || player.steam_id}. O histórico antigo continuará salvo.`,
      showCancelButton: true,
      confirmButtonColor: '#f97316',
      cancelButtonColor: '#374151',
      confirmButtonText: 'Sim, resetar',
      cancelButtonText: 'Cancelar',
    });
    if (!confirm.isConfirmed) return;

    setResettingSteamId(player.steam_id);
    try {
      const res = await resetShopAdminDailyPackPlayer(player.steam_id);
      if (res.success) {
        await loadPlayers(playersPage, playersQuery, playersStatusFilter, playersSortBy, playersSortOrder);
      } else {
        throw new Error((res as any).error || 'Erro ao resetar jogador');
      }
    } catch (err: any) {
      await Swal.fire({
        icon: 'error',
        title: 'Erro ao resetar',
        text: err?.response?.data?.error || err?.message || 'Não foi possível resetar.',
        confirmButtonColor: '#f97316',
      });
    } finally {
      setResettingSteamId(null);
    }
  };

  const toggleSort = (col: string) => {
    if (playersSortBy === col) {
      setPlayersSortOrder((prev) => (prev === 'asc' ? 'desc' : 'asc'));
    } else {
      setPlayersSortBy(col);
      setPlayersSortOrder(col === 'player_name' ? 'asc' : 'desc');
    }
  };

  const playersTotalPages = Math.max(1, Math.ceil(playersTotal / playersLimit));
  const historyTotalPages = Math.max(1, Math.ceil(historyTotal / historyLimit));

  const renderSortButton = (label: string, col: string, alignRight = false) => {
    const active = playersSortBy === col;
    return (
      <button
        type="button"
        onClick={() => toggleSort(col)}
        className={`flex items-center gap-1 hover:text-white/80 transition-colors ${alignRight ? 'justify-end w-full' : ''}`}
      >
        <span>{label}</span>
        {active && <span className="text-scum-orange">{playersSortOrder === 'asc' ? '▲' : '▼'}</span>}
      </button>
    );
  };

  return (
    <div className="grid grid-cols-1 xl:grid-cols-[440px_1fr] gap-4">
      {/* COLUNA ESQUERDA — Configuração do Kit + Caixa de Mensagem + Link Discord */}
      <div className="card p-4 space-y-4">
        <div className="flex items-center justify-between gap-2">
          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={() => setLeftTab('kit')}
              className={
                leftTab === 'kit'
                  ? 'px-2.5 py-1 rounded-lg border border-scum-orange/60 bg-scum-orange/10 text-xs font-semibold text-scum-orange flex items-center gap-1.5'
                  : 'px-2.5 py-1 rounded-lg border border-white/15 bg-white/8 text-xs font-medium text-white/90 hover:bg-white/12 hover:border-white/25 flex items-center gap-1.5'
              }
            >
              <Gift size={13} />
              <span>Configuração & Kit</span>
            </button>
            <button
              type="button"
              onClick={() => setLeftTab('reminder')}
              className={
                leftTab === 'reminder'
                  ? 'px-2.5 py-1 rounded-lg border border-scum-orange/60 bg-scum-orange/10 text-xs font-semibold text-scum-orange flex items-center gap-1.5'
                  : 'px-2.5 py-1 rounded-lg border border-white/15 bg-white/8 text-xs font-medium text-white/90 hover:bg-white/12 hover:border-white/25 flex items-center gap-1.5'
              }
            >
              <MessageSquare size={13} />
              <span>Aviso & Discord</span>
            </button>
          </div>
          <button
            type="button"
            disabled={configLoading}
            onClick={() => void loadConfig()}
            className="p-1.5 rounded-lg border border-white/15 bg-white/5 text-white/70 hover:text-white hover:bg-white/10 disabled:opacity-60"
            title="Recarregar configuração"
          >
            <RefreshCw size={14} className={configLoading ? 'animate-spin' : ''} />
          </button>
        </div>

        {configError && (
          <div className="rounded-lg border border-red-500/30 bg-red-500/10 px-3 py-2 text-xs text-red-300">
            {configError}
          </div>
        )}

        {leftTab === 'kit' ? (
          <div className="space-y-3">
            {/* Ativar comando /daily */}
            <label className="flex items-center justify-between gap-3 rounded-lg border border-white/10 bg-white/5 px-3 py-2.5 cursor-pointer">
              <div>
                <div className="text-sm font-semibold text-white">Comando /daily</div>
                <div className="text-xs text-white/55">
                  Somente jogadores registrados no Discord conseguem resgatar.
                </div>
              </div>
              <input
                type="checkbox"
                checked={enabled}
                onChange={(e) => setEnabled(e.target.checked)}
                className="h-4 w-4 accent-scum-orange"
              />
            </label>

            {/* Seletor de Kit */}
            <div>
              <label className="block text-xs text-white/60 mb-1">Kit vinculado ao DailyPack</label>
              <select
                value={selectedKitCode}
                onChange={(e) => setSelectedKitCode(e.target.value)}
                className="w-full px-3 py-2 rounded-lg bg-[#0b1220] border border-white/10 text-white text-sm focus:outline-none focus:ring-2 focus:ring-scum-orange"
              >
                <option value="" style={{ backgroundColor: '#0b1220', color: '#ffffff' }}>
                  Nenhum kit (entregar somente coins)
                </option>
                {(configPayload?.available_kits || []).map((k) => (
                  <option
                    key={k.kit_id}
                    value={String(k.code)}
                    style={{ backgroundColor: '#0b1220', color: '#ffffff' }}
                  >
                    Kit #{k.code} — {k.name} ({k.items.length} {k.items.length === 1 ? 'item' : 'itens'})
                  </option>
                ))}
              </select>
            </div>

            {/* Cooldown (horas) & Bônus Coins */}
            <div className="grid grid-cols-2 gap-2">
              <div>
                <label className="block text-xs text-white/60 mb-1">Cooldown (/daily) em horas</label>
                <input
                  type="number"
                  min={1}
                  step={1}
                  value={cooldownHours}
                  onChange={(e) => setCooldownHours(e.target.value)}
                  className="w-full px-3 py-2 rounded-lg bg-white/5 border border-white/10 text-white text-sm focus:outline-none focus:ring-2 focus:ring-scum-orange"
                />
              </div>
              <div>
                <label className="block text-xs text-white/60 mb-1">Bônus em Coins</label>
                <input
                  type="number"
                  min={0}
                  step={1}
                  value={bonusCoins}
                  onChange={(e) => setBonusCoins(e.target.value)}
                  className="w-full px-3 py-2 rounded-lg bg-white/5 border border-white/10 text-white text-sm focus:outline-none focus:ring-2 focus:ring-scum-orange"
                />
              </div>
            </div>

            <button
              type="button"
              disabled={configSaving}
              onClick={() => void handleSaveConfig()}
              className="w-full px-3 py-2 rounded-lg border border-scum-orange/60 bg-scum-orange/10 text-sm font-semibold text-scum-orange hover:bg-scum-orange/20 hover:border-scum-orange/80 focus:outline-none focus:ring-2 focus:ring-scum-orange/70 disabled:opacity-70 flex items-center justify-center gap-2"
            >
              <Save size={15} />
              <span>{configSaving ? 'Salvando...' : 'Salvar configurações'}</span>
            </button>

            {/* Preview do Kit em uso no DailyPack */}
            <div className="pt-2 border-t border-white/10 space-y-2">
              <div className="flex items-center justify-between">
                <div className="text-xs font-semibold uppercase tracking-wide text-white/60 flex items-center gap-1.5">
                  <Package size={13} className="text-scum-orange" />
                  <span>Kit em uso no DailyPack</span>
                </div>
                {previewKit && (
                  <span className="inline-flex items-center px-2 py-0.5 rounded bg-scum-orange/15 border border-scum-orange/30 text-xs font-bold text-scum-orange font-mono">
                    Kit #{previewKit.code}
                  </span>
                )}
              </div>

              {previewKit ? (
                <div className="rounded-lg border border-white/10 bg-white/5 p-3 space-y-2.5">
                  <div className="flex items-start justify-between gap-2">
                    <div>
                      <div className="text-sm font-semibold text-white">{previewKit.name}</div>
                      <div className="text-xs text-white/50">
                        Número do Kit: <span className="text-white/80 font-mono">#{previewKit.code}</span> • ID:{' '}
                        <span className="font-mono">{previewKit.kit_id}</span>
                      </div>
                    </div>
                    <span
                      className={
                        previewKit.enabled
                          ? 'px-2 py-0.5 rounded-full bg-emerald-500/15 border border-emerald-500/30 text-[11px] font-semibold text-emerald-300'
                          : 'px-2 py-0.5 rounded-full bg-white/10 border border-white/15 text-[11px] text-white/60'
                      }
                    >
                      {previewKit.enabled ? 'Ativo' : 'Oculto do /kit'}
                    </span>
                  </div>

                  <div className="text-xs font-medium text-white/70">
                    O que o jogador ganha ({previewKit.items.length}{' '}
                    {previewKit.items.length === 1 ? 'item' : 'itens'}
                    {Number(bonusCoins || 0) > 0 ? ` + ${Number(bonusCoins)} coins` : ''}):
                  </div>

                  {previewKit.items.length === 0 ? (
                    <div className="text-xs text-amber-300/80">Este kit ainda não possui itens cadastrados.</div>
                  ) : (
                    <div className="max-h-[260px] overflow-auto divide-y divide-white/5 rounded border border-white/10 bg-[#0b1220]/70">
                      {previewKit.items.map((item, idx) => (
                        <div
                          key={`${item.setup}-${idx}`}
                          className="flex items-center justify-between gap-2 px-2.5 py-1.5 text-xs"
                        >
                          <div className="min-w-0">
                            <div className="text-white/90 font-medium truncate">
                              {item.display_name || item.setup}
                            </div>
                            {item.display_name && item.display_name !== item.setup && (
                              <div className="text-[11px] text-white/45 font-mono truncate">{item.setup}</div>
                            )}
                          </div>
                          <span className="shrink-0 font-mono font-semibold text-scum-orange tabular-nums">
                            x{item.qty}
                          </span>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              ) : (
                <div className="rounded-lg border border-white/10 bg-white/5 p-3 text-xs text-white/60">
                  Nenhum kit selecionado no momento.
                  {Number(bonusCoins || 0) > 0
                    ? ` Jogadores registrados receberão apenas ${Number(bonusCoins)} coins ao digitar /daily.`
                    : ' Selecione um kit ou defina um bônus em coins acima.'}
                </div>
              )}
            </div>
          </div>
        ) : (
          <div className="space-y-3">
            {/* Link do Discord */}
            <div>
              <label className="block text-xs font-semibold text-white/80 mb-1">
                Link do Discord (enviado no /daily para não registrados)
              </label>
              <input
                type="url"
                value={discordInviteUrl}
                onChange={(e) => setDiscordInviteUrl(e.target.value)}
                placeholder="https://discord.gg/seu-servidor"
                className="w-full px-3 py-2 rounded-lg bg-white/5 border border-white/10 text-white text-sm focus:outline-none focus:ring-2 focus:ring-scum-orange"
              />
              <div className="text-[11px] text-white/50 mt-1">
                Se um jogador não registrado digitar <span className="font-mono text-white/80">/daily</span>, receberá
                este link no chat pedindo para se registrar com <span className="font-mono text-white/80">!register</span>.
              </div>
            </div>

            {/* Ativar aviso automático */}
            <label className="flex items-center justify-between gap-3 rounded-lg border border-white/10 bg-white/5 px-3 py-2.5 cursor-pointer">
              <div>
                <div className="text-sm font-semibold text-white">Aviso automático no chat do jogo</div>
                <div className="text-xs text-white/55">
                  Envia apenas se houver pelo menos 1 jogador online não registrado.
                </div>
              </div>
              <input
                type="checkbox"
                checked={reminderEnabled}
                onChange={(e) => setReminderEnabled(e.target.checked)}
                className="h-4 w-4 accent-scum-orange"
              />
            </label>

            {/* Caixa de texto ajustável */}
            <div>
              <div className="flex items-center justify-between mb-1">
                <label className="text-xs font-semibold text-white/80">
                  Mensagem para o chat do jogo (ajustável)
                </label>
                <span className="text-[11px] text-white/45">Variável opcional: {'{discord}'}</span>
              </div>
              <textarea
                rows={4}
                value={reminderMessage}
                onChange={(e) => setReminderMessage(e.target.value)}
                placeholder="Atenção jogadores, seu Presente diário pode estar disponível! use /daily em seu chat para conferir"
                className="w-full px-3 py-2 rounded-lg bg-white/5 border border-white/10 text-white text-sm resize-y min-h-[110px] focus:outline-none focus:ring-2 focus:ring-scum-orange"
              />
              <div className="text-[11px] text-white/45 mt-1">
                Você pode redimensionar a altura da caixa acima. Cada quebra de linha envia uma linha via SendChat.
              </div>
            </div>

            {/* Cooldown em minutos + Cor */}
            <div className="grid grid-cols-2 gap-2">
              <div>
                <label className="block text-xs text-white/60 mb-1">Cooldown do aviso (minutos)</label>
                <input
                  type="number"
                  min={1}
                  step={1}
                  value={reminderIntervalMinutes}
                  onChange={(e) => setReminderIntervalMinutes(e.target.value)}
                  className="w-full px-3 py-2 rounded-lg bg-white/5 border border-white/10 text-white text-sm focus:outline-none focus:ring-2 focus:ring-scum-orange"
                />
              </div>
              <div>
                <label className="block text-xs text-white/60 mb-1">Cor no chat (SendChat)</label>
                <select
                  value={reminderChatColor}
                  onChange={(e) => setReminderChatColor(Number(e.target.value))}
                  className="w-full px-3 py-2 rounded-lg bg-[#0b1220] border border-white/10 text-white text-sm focus:outline-none focus:ring-2 focus:ring-scum-orange"
                >
                  {CHAT_COLOR_OPTIONS.map((opt) => (
                    <option
                      key={opt.value}
                      value={opt.value}
                      style={{ backgroundColor: '#0b1220', color: '#ffffff' }}
                    >
                      {opt.label}
                    </option>
                  ))}
                </select>
              </div>
            </div>

            {/* Status online / agendador */}
            <div className="rounded-lg border border-white/10 bg-white/5 px-3 py-2 text-xs text-white/70 space-y-1">
              <div className="flex items-center justify-between">
                <span>Jogadores online agora:</span>
                <span className="font-semibold text-white tabular-nums">
                  {configPayload?.online_stats?.online_total ?? 0} total (
                  <span className="text-amber-300">
                    {configPayload?.online_stats?.online_unregistered ?? 0} não registrado(s)
                  </span>
                  )
                </span>
              </div>
              <div className="flex items-center justify-between">
                <span>Último envio do aviso:</span>
                <span className="text-white/80 tabular-nums">
                  {configPayload?.reminder_status?.last_sent_at
                    ? formatDateTimePtBr(configPayload.reminder_status.last_sent_at)
                    : 'Ainda não enviado'}
                </span>
              </div>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
              <button
                type="button"
                disabled={configSaving}
                onClick={() => void handleSaveConfig()}
                className="px-3 py-2 rounded-lg border border-scum-orange/60 bg-scum-orange/10 text-sm font-semibold text-scum-orange hover:bg-scum-orange/20 hover:border-scum-orange/80 disabled:opacity-70 flex items-center justify-center gap-2"
              >
                <Save size={15} />
                <span>{configSaving ? 'Salvando...' : 'Salvar'}</span>
              </button>
              <button
                type="button"
                disabled={testingReminder}
                onClick={() => void handleTestReminder()}
                className="px-3 py-2 rounded-lg border border-white/15 bg-white/8 text-sm font-medium text-white/90 hover:bg-white/12 hover:border-white/25 disabled:opacity-70 flex items-center justify-center gap-2"
              >
                <Send size={14} />
                <span>{testingReminder ? 'Enviando...' : 'Enviar teste agora'}</span>
              </button>
            </div>
          </div>
        )}
      </div>

      {/* COLUNA DIREITA — Jogadores Registrados & Histórico (/daily) */}
      <div className="card p-4 space-y-3">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={() => setRightTab('players')}
              className={
                rightTab === 'players'
                  ? 'px-2.5 py-1 rounded-lg border border-scum-orange/60 bg-scum-orange/10 text-xs font-semibold text-scum-orange flex items-center gap-1.5'
                  : 'px-2.5 py-1 rounded-lg border border-white/15 bg-white/8 text-xs font-medium text-white/90 hover:bg-white/12 hover:border-white/25 flex items-center gap-1.5'
              }
            >
              <Users size={13} />
              <span>Jogadores Registrados</span>
            </button>
            <button
              type="button"
              onClick={() => setRightTab('history')}
              className={
                rightTab === 'history'
                  ? 'px-2.5 py-1 rounded-lg border border-scum-orange/60 bg-scum-orange/10 text-xs font-semibold text-scum-orange flex items-center gap-1.5'
                  : 'px-2.5 py-1 rounded-lg border border-white/15 bg-white/8 text-xs font-medium text-white/90 hover:bg-white/12 hover:border-white/25 flex items-center gap-1.5'
              }
            >
              <History size={13} />
              <span>Histórico de Resgates</span>
            </button>
          </div>

          <div className="flex flex-wrap items-center gap-2 text-xs text-white/60">
            <span>
              Registrados: <strong className="text-white tabular-nums">{playersSummary.total_registered}</strong>
            </span>
            <span>•</span>
            <span>
              Em cooldown: <strong className="text-amber-300 tabular-nums">{playersSummary.claimed_in_cycle}</strong>
            </span>
            <span>•</span>
            <span>
              Disponíveis: <strong className="text-emerald-300 tabular-nums">{playersSummary.available_now}</strong>
            </span>
            <button
              type="button"
              onClick={() =>
                rightTab === 'players'
                  ? void loadPlayers(playersPage, playersQuery, playersStatusFilter, playersSortBy, playersSortOrder)
                  : void loadHistory(historyPage, historyQuery)
              }
              className="p-1.5 rounded-lg border border-white/15 bg-white/5 text-white/70 hover:text-white hover:bg-white/10"
              title="Atualizar lista"
            >
              <RefreshCw size={13} className={(rightTab === 'players' ? playersBusy : historyBusy) ? 'animate-spin' : ''} />
            </button>
          </div>
        </div>

        {rightTab === 'players' ? (
          <>
            <div className="grid grid-cols-1 sm:grid-cols-[1fr_220px] gap-2">
              <input
                value={playersQuery}
                onChange={(e) => setPlayersQuery(e.target.value)}
                placeholder="Buscar jogador registrado (nome ou Steam ID)..."
                className="w-full px-3 py-2 rounded-lg bg-white/5 border border-white/10 text-white text-sm focus:outline-none focus:ring-2 focus:ring-scum-orange"
              />
              <select
                value={playersStatusFilter}
                onChange={(e) => setPlayersStatusFilter(e.target.value as any)}
                className="w-full px-3 py-2 rounded-lg bg-[#0b1220] border border-white/10 text-white text-sm focus:outline-none focus:ring-2 focus:ring-scum-orange"
              >
                <option value="all" style={{ backgroundColor: '#0b1220', color: '#ffffff' }}>
                  Todos os registrados
                </option>
                <option value="claimed" style={{ backgroundColor: '#0b1220', color: '#ffffff' }}>
                  Já retiraram (em cooldown)
                </option>
                <option value="available" style={{ backgroundColor: '#0b1220', color: '#ffffff' }}>
                  Disponíveis para retirar
                </option>
                <option value="never" style={{ backgroundColor: '#0b1220', color: '#ffffff' }}>
                  Nunca retiraram
                </option>
              </select>
            </div>

            {playersError && (
              <div className="rounded-lg border border-red-500/30 bg-red-500/10 px-3 py-2 text-xs text-red-300">
                {playersError}
              </div>
            )}

            <div className="rounded-lg border border-white/10 overflow-auto">
              <div className="min-w-[820px]">
                <div className="grid grid-cols-[1.2fr_170px_165px_175px_70px_90px] gap-2 px-3 py-2 text-xs uppercase text-white/45 border-b border-white/10">
                  {renderSortButton('Jogador', 'player_name')}
                  {renderSortButton('Steam ID', 'steam_id')}
                  <div>Status (/daily)</div>
                  {renderSortButton('Data / Hora (/daily)', 'last_command_at')}
                  {renderSortButton('Total', 'total_claims', true)}
                  <div className="text-right">Ação</div>
                </div>

                <div className="max-h-[520px] overflow-auto divide-y divide-white/5">
                  {players.map((p) => {
                    const cmdDate = p.last_command_at || p.last_claimed_at;
                    return (
                      <div
                        key={p.steam_id}
                        className="grid grid-cols-[1.2fr_170px_165px_175px_70px_90px] gap-2 px-3 py-2.5 items-center hover:bg-white/5 text-sm"
                      >
                        <div className="min-w-0">
                          <div className="font-medium text-white/95 truncate">{p.player_name || 'Sem nome'}</div>
                          {p.last_kit_code != null && (
                            <div className="text-[11px] text-white/45 truncate">
                              Último: Kit #{p.last_kit_code}
                              {p.last_kit_name ? ` (${p.last_kit_name})` : ''}
                            </div>
                          )}
                        </div>

                        <div className="text-xs font-mono text-white/65 truncate">{p.steam_id}</div>

                        <div>
                          {p.claim_status === 'claimed' ? (
                            <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full bg-amber-500/15 border border-amber-500/35 text-xs font-semibold text-amber-300">
                              <Clock size={11} />
                              <span>{formatCooldownRemaining(p.remaining_seconds)}</span>
                            </span>
                          ) : p.claim_status === 'available' ? (
                            <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full bg-emerald-500/15 border border-emerald-500/35 text-xs font-semibold text-emerald-300">
                              <CheckCircle2 size={11} />
                              <span>Disponível</span>
                            </span>
                          ) : (
                            <span className="inline-flex items-center px-2 py-0.5 rounded-full bg-white/5 border border-white/15 text-xs text-white/55">
                              Nunca resgatou
                            </span>
                          )}
                        </div>

                        <div className="text-xs text-white/80 tabular-nums">
                          {cmdDate ? formatDateTimePtBr(cmdDate) : '—'}
                        </div>

                        <div className="text-xs font-semibold text-white/80 text-right tabular-nums">
                          {p.total_claims || 0}
                        </div>

                        <div className="flex justify-end">
                          <button
                            type="button"
                            disabled={!p.last_claimed_ts || resettingSteamId === p.steam_id}
                            onClick={() => void handleResetPlayer(p)}
                            className="px-2 py-1 rounded border border-white/15 bg-white/5 text-xs text-white/85 hover:bg-white/12 hover:border-white/25 disabled:opacity-40 disabled:cursor-not-allowed flex items-center gap-1"
                            title="Resetar cooldown deste jogador"
                          >
                            <RotateCcw size={11} />
                            <span>Resetar</span>
                          </button>
                        </div>
                      </div>
                    );
                  })}

                  {!playersBusy && players.length === 0 && (
                    <div className="p-4 text-sm text-white/55 text-center">
                      Nenhum jogador registrado encontrado para este filtro.
                    </div>
                  )}
                </div>
              </div>
            </div>

            {playersTotal > 0 && (
              <div className="flex items-center justify-between gap-2 pt-1">
                <div className="text-xs text-white/50">
                  Página {playersPage} / {playersTotalPages} ({playersTotal} registros)
                </div>
                <div className="flex items-center gap-1">
                  <button
                    type="button"
                    disabled={playersBusy || playersPage <= 1}
                    onClick={() =>
                      void loadPlayers(
                        playersPage - 1,
                        playersQuery,
                        playersStatusFilter,
                        playersSortBy,
                        playersSortOrder
                      )
                    }
                    className="px-2.5 py-1 rounded-lg border border-white/15 bg-white/8 text-xs font-medium text-white/90 hover:bg-white/12 disabled:opacity-50"
                  >
                    Anterior
                  </button>
                  <button
                    type="button"
                    disabled={playersBusy || playersPage >= playersTotalPages}
                    onClick={() =>
                      void loadPlayers(
                        playersPage + 1,
                        playersQuery,
                        playersStatusFilter,
                        playersSortBy,
                        playersSortOrder
                      )
                    }
                    className="px-2.5 py-1 rounded-lg border border-white/15 bg-white/8 text-xs font-medium text-white/90 hover:bg-white/12 disabled:opacity-50"
                  >
                    Próxima
                  </button>
                </div>
              </div>
            )}
          </>
        ) : (
          <>
            <input
              value={historyQuery}
              onChange={(e) => setHistoryQuery(e.target.value)}
              placeholder="Buscar no histórico (jogador, Steam ID ou kit)..."
              className="w-full px-3 py-2 rounded-lg bg-white/5 border border-white/10 text-white text-sm focus:outline-none focus:ring-2 focus:ring-scum-orange"
            />

            {historyError && (
              <div className="rounded-lg border border-red-500/30 bg-red-500/10 px-3 py-2 text-xs text-red-300">
                {historyError}
              </div>
            )}

            <div className="rounded-lg border border-white/10 overflow-auto">
              <div className="min-w-[760px]">
                <div className="grid grid-cols-[175px_1fr_175px_170px_80px] gap-2 px-3 py-2 text-xs uppercase text-white/45 border-b border-white/10">
                  <div>Data / Hora (/daily)</div>
                  <div>Jogador</div>
                  <div>Steam ID</div>
                  <div>Kit Entregue</div>
                  <div className="text-right">Coins</div>
                </div>

                <div className="max-h-[520px] overflow-auto divide-y divide-white/5">
                  {historyItems.map((h) => (
                    <div
                      key={h.id}
                      className="grid grid-cols-[175px_1fr_175px_170px_80px] gap-2 px-3 py-2.5 items-center hover:bg-white/5 text-sm"
                    >
                      <div className="text-xs text-white/80 tabular-nums">{formatDateTimePtBr(h.command_at)}</div>
                      <div className="font-medium text-white/95 truncate">{h.player_name || 'Sem nome'}</div>
                      <div className="text-xs font-mono text-white/65 truncate">{h.steam_id}</div>
                      <div className="text-xs text-white/80 truncate">
                        {h.kit_code != null
                          ? `Kit #${h.kit_code}${h.kit_name ? ` — ${h.kit_name}` : ''}`
                          : 'Somente coins'}
                      </div>
                      <div className="text-xs font-semibold text-emerald-300 text-right tabular-nums">
                        +{h.bonus_coins || 0}
                      </div>
                    </div>
                  ))}

                  {!historyBusy && historyItems.length === 0 && (
                    <div className="p-4 text-sm text-white/55 text-center">
                      Nenhum resgate registrado no histórico ainda.
                    </div>
                  )}
                </div>
              </div>
            </div>

            {historyTotal > 0 && (
              <div className="flex items-center justify-between gap-2 pt-1">
                <div className="text-xs text-white/50">
                  Página {historyPage} / {historyTotalPages} ({historyTotal} registros)
                </div>
                <div className="flex items-center gap-1">
                  <button
                    type="button"
                    disabled={historyBusy || historyPage <= 1}
                    onClick={() => void loadHistory(historyPage - 1, historyQuery)}
                    className="px-2.5 py-1 rounded-lg border border-white/15 bg-white/8 text-xs font-medium text-white/90 hover:bg-white/12 disabled:opacity-50"
                  >
                    Anterior
                  </button>
                  <button
                    type="button"
                    disabled={historyBusy || historyPage >= historyTotalPages}
                    onClick={() => void loadHistory(historyPage + 1, historyQuery)}
                    className="px-2.5 py-1 rounded-lg border border-white/15 bg-white/8 text-xs font-medium text-white/90 hover:bg-white/12 disabled:opacity-50"
                  >
                    Próxima
                  </button>
                </div>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
}
