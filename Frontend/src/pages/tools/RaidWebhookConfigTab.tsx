import { useEffect, useState, useMemo } from 'react';
import { useTranslation } from 'react-i18next';
import Swal from 'sweetalert2';
import {
  Clock,
  Info,
  Save,
  RotateCcw,
  RefreshCw,
  Sliders,
  MessageSquare,
  Search,
  ShieldCheck,
  ToggleLeft,
  ToggleRight,
  ShieldAlert,
} from 'lucide-react';
import { getConfig, updateConfigSection } from '@/services/config';
import {
  getAllPlayers,
  getPlayerPermissions,
  activatePermission,
  deactivatePermission,
  type AllPlayer,
  type PlayerPermissionsData,
} from '@/services/server';

interface PersonalWebhooksConfig {
  enabled: boolean;
  price_points: number;
  duration_days: number;
  messages: {
    system_disabled: string;
    usage_help: string;
    no_permission: string;
    insufficient_funds: string;
    disabled_success: string;
    disabled_success_lifetime: string;
    registered_success: string;
    registered_success_lifetime: string;
    updated_success: string;
    updated_success_lifetime: string;
    renewed_success: string;
    status_info: string;
    status_expired: string;
    status_no_subscription: string;
    invalid_webhook: string;
    database_error: string;
    auto_renew_success: string;
    auto_renew_failed: string;
    expiry_warning_3_days: string;
    expiry_warning_1_day: string;
  };
}

const DEFAULT_CONFIG: PersonalWebhooksConfig = {
  enabled: true,
  price_points: 500,
  duration_days: 30,
  messages: {
    system_disabled: '[SSM] O sistema de webhook pessoal de raid esta desativado neste servidor.',
    usage_help: '[SSM] Uso correto: /rd <url> ou /rd off. Para ver detalhes digite: /rd info',
    no_permission: '[SSM] Voce nao tem permissao para gerenciar webhook pessoal.',
    insufficient_funds: '[SSM] Saldo insuficiente. Para cadastrar o webhook sao necessarios {price} pontos. Seu saldo: {balance}.',
    disabled_success: '[SSM] Webhook desativado. Sua assinatura continua valida ate {expires_at}.',
    disabled_success_lifetime: '[SSM] Webhook pessoal desativado com sucesso.',
    registered_success: '[SSM] Webhook cadastrado por {days} dias! Validade: {expires_at}. Descontado {price} pontos.',
    registered_success_lifetime: '[SSM] Webhook pessoal cadastrado com sucesso (Plano Vitalicio)!',
    updated_success: '[SSM] Webhook atualizado com sucesso! Validade: {expires_at}.',
    updated_success_lifetime: '[SSM] Webhook pessoal atualizado com sucesso!',
    renewed_success: '[SSM] Assinatura estendida por mais {days} dias! Nova validade: {expires_at}. Descontado {price} pontos.',
    status_info: '[SSM] Webhook: {url} | Validade da assinatura: {expires_at} {remaining}.',
    status_expired: '[SSM] Webhook: {url} | Assinatura EXPIRADA em: {expires_at}.',
    status_no_subscription: '[SSM] Voce nao possui uma assinatura de webhook pessoal activa.',
    invalid_webhook: '[SSM] URL de webhook invalida. Use uma URL do Discord valida.',
    database_error: '[SSM] Erro interno ao salvar as configuracoes do webhook.',
    auto_renew_success: '🔄 [SSM] Sua assinatura do webhook de raid foi renovada automaticamente por mais {days} dias! Validade: {expires_at}. Descontado {price} pontos.',
    auto_renew_failed: '⚠️ [SSM] Sua assinatura do webhook de raid expirou e nao pôde ser renovada automaticamente por falta de saldo (Preço: {price} pontos | Seu saldo: {balance}). Adicione pontos para reativar.',
    expiry_warning_3_days: '📅 [SSM] Lembrete: Sua assinatura do webhook de raid expira em 3 dias ({expires_at}). Caso tenha saldo suficiente, ela será renovada automaticamente.',
    expiry_warning_1_day: '🚨 [SSM] Atenção: Sua assinatura do webhook de raid expira amanhã ({expires_at}). Verifique se possui saldo suficiente para a renovação automática.',
  },
};

type MessageKey = keyof PersonalWebhooksConfig['messages'];

export default function RaidWebhookConfigTab() {
  const { t } = useTranslation();
  const [config, setConfig] = useState<PersonalWebhooksConfig>(DEFAULT_CONFIG);
  const [initialConfig, setInitialConfig] = useState<PersonalWebhooksConfig>(DEFAULT_CONFIG);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Message group selection for better tab UX
  const [selectedGroup, setSelectedGroup] = useState<'commandUsage' | 'registration' | 'autoRenewal' | 'errors'>('commandUsage');

  // Player Access Control list states
  const [players, setPlayers] = useState<AllPlayer[]>([]);
  const [playersBusy, setPlayersBusy] = useState(false);
  const [playerQuery, setPlayerQuery] = useState('');
  const [playersPage, setPlayersPage] = useState(1);
  const [playersTotal, setPlayersTotal] = useState(0);
  const playersLimit = 5;

  const [permissionsMap, setPermissionsMap] = useState<Map<string, PlayerPermissionsData>>(new Map());
  const [updatingPermissions, setUpdatingPermissions] = useState<Set<string>>(new Set());

  // Config loading
  const loadConfig = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await getConfig('personal_webhooks');
      if (res.success && res.data) {
        // Merge with defaults to ensure all keys exist
        const merged: PersonalWebhooksConfig = {
          ...DEFAULT_CONFIG,
          ...res.data,
          messages: {
            ...DEFAULT_CONFIG.messages,
            ...(res.data.messages || {}),
          },
        };
        setConfig(merged);
        setInitialConfig(merged);
      } else {
        setError(res.error || t('tools.shopDeliveries.raidWebhooks.saveError', { defaultValue: 'Falha ao carregar as configurações do webhook de raid.' }));
      }
    } catch (err: any) {
      console.error('[RaidWebhookConfigTab] error loading config:', err);
      setError(err?.response?.data?.error || err?.message || 'Erro ao carregar configurações.');
    } finally {
      setLoading(false);
    }
  };

  // Players loading with their permissions
  const loadPlayersPage = async (page: number, queryStr = playerQuery) => {
    const safePage = Math.max(1, page);
    const offset = (safePage - 1) * playersLimit;
    setPlayersBusy(true);
    try {
      const res = await getAllPlayers(playersLimit, offset, { q: queryStr });
      if (res.success && res.data?.players) {
        const loadedPlayers = res.data.players;
        setPlayers(loadedPlayers);
        setPlayersTotal(res.data.total ?? 0);
        setPlayersPage(safePage);

        // Batch fetch permissions for loaded players
        const permPromises = loadedPlayers.map(async (player) => {
          try {
            const pRes = await getPlayerPermissions(player.steam_id, false);
            if (pRes.success && pRes.data) {
              return { steamId: player.steam_id, data: pRes.data };
            }
          } catch (e) {
            console.error(`Error loading permission for ${player.steam_id}:`, e);
          }
          return { steamId: player.steam_id, data: null };
        });

        const permResults = await Promise.all(permPromises);
        setPermissionsMap((prev) => {
          const next = new Map(prev);
          permResults.forEach((item) => {
            if (item.data) {
              next.set(item.steamId, item.data);
            }
          });
          return next;
        });
      } else {
        setPlayers([]);
        setPlayersTotal(0);
      }
    } catch (e) {
      console.error(e);
      setPlayers([]);
      setPlayersTotal(0);
    } finally {
      setPlayersBusy(false);
    }
  };

  useEffect(() => {
    void loadConfig();
    void loadPlayersPage(1);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Debounced query change
  useEffect(() => {
    const handler = setTimeout(() => {
      void loadPlayersPage(1, playerQuery);
    }, 400);
    return () => clearTimeout(handler);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [playerQuery]);

  const handleTogglePermission = async (player: AllPlayer) => {
    const steamId = player.steam_id;
    const playerPerms = permissionsMap.get(steamId);
    
    // A player is blocked ONLY if they have a permission entry with is_active = 0 or false
    const isBlocked = playerPerms?.permissions.some(
      (p) => p.permission_type === 'raid_webhook_manage' && (p.is_active === false || p.is_active === 0)
    ) || false;

    setUpdatingPermissions((prev) => new Set(prev).add(steamId));
    try {
      // Toggle logic: If currently blocked (isBlocked = true), we activate (unblock).
      // If currently allowed (isBlocked = false), we deactivate (block).
      const response = isBlocked
        ? await activatePermission(steamId, 'raid_webhook_manage')
        : await deactivatePermission(steamId, 'raid_webhook_manage');

      if (response.success) {
        // Reload permissions for this player
        const permsData = await getPlayerPermissions(steamId, false);
        if (permsData.data) {
          setPermissionsMap((prev) => new Map(prev).set(steamId, permsData.data!));
        }

        await Swal.fire({
          icon: 'success',
          title: t('players.permissions.updated', { defaultValue: 'Permissão atualizada' }),
          text: isBlocked
            ? t('players.permissions.messages.raid_webhook_manageActivated', {
                defaultValue: 'Permissão de webhook de raid ativada com sucesso',
              })
            : t('players.permissions.messages.raid_webhook_manageDeactivated', {
                defaultValue: 'Permissão de webhook de raid desativada com sucesso',
              }),
          timer: 1500,
          showConfirmButton: false,
          toast: true,
          position: 'top-end',
        });
      }
    } catch (error: any) {
      console.error(error);
      await Swal.fire({
        icon: 'error',
        title: t('common.error', { defaultValue: 'Erro' }),
        text: error?.response?.data?.error || error?.message || 'Erro ao atualizar permissão',
        confirmButtonColor: '#f97316',
      });
    } finally {
      setUpdatingPermissions((prev) => {
        const next = new Set(prev);
        next.delete(steamId);
        return next;
      });
    }
  };

  const hasChanges = () => {
    return JSON.stringify(config) !== JSON.stringify(initialConfig);
  };

  const handleRevert = () => {
    setConfig(initialConfig);
  };

  const handleSave = async () => {
    if (config.price_points < 0 || !Number.isInteger(Number(config.price_points))) {
      await Swal.fire({
        icon: 'error',
        title: t('common.error', { defaultValue: 'Erro' }),
        text: t('tools.shopDeliveries.raidWebhooks.validationPriceError', {
          defaultValue: 'O preço da assinatura deve ser um número inteiro igual ou superior a 0.',
        }),
        confirmButtonColor: '#f97316',
      });
      return;
    }

    if (config.duration_days < 0 || !Number.isInteger(Number(config.duration_days))) {
      await Swal.fire({
        icon: 'error',
        title: t('common.error', { defaultValue: 'Erro' }),
        text: t('tools.shopDeliveries.raidWebhooks.validationDurationError', {
          defaultValue: 'A duração da assinatura deve ser um número inteiro igual ou superior a 0.',
        }),
        confirmButtonColor: '#f97316',
      });
      return;
    }

    setSaving(true);
    try {
      const res = await updateConfigSection('personal_webhooks', config, true);
      if (res.success) {
        setInitialConfig(config);
        await Swal.fire({
          icon: 'success',
          title: t('common.success', { defaultValue: 'Sucesso' }),
          text: t('tools.shopDeliveries.raidWebhooks.saveSuccess', {
            defaultValue: 'Configurações de Webhook de Raid salvas com sucesso!',
          }),
          confirmButtonColor: '#f97316',
        });
      } else {
        await Swal.fire({
          icon: 'error',
          title: t('common.error', { defaultValue: 'Erro' }),
          text: res.error || t('tools.shopDeliveries.raidWebhooks.saveError', { defaultValue: 'Falha ao salvar as configurações.' }),
          confirmButtonColor: '#f97316',
        });
      }
    } catch (err: any) {
      console.error('[RaidWebhookConfigTab] error saving config:', err);
      const msg = err?.response?.data?.error || err?.message || 'Erro ao salvar as configurações.';
      await Swal.fire({
        icon: 'error',
        title: t('common.error', { defaultValue: 'Erro' }),
        text: msg,
        confirmButtonColor: '#f97316',
      });
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return (
      <div className="card p-8 flex flex-col items-center justify-center space-y-4">
        <RefreshCw className="animate-spin text-scum-orange" size={36} />
        <span className="text-white/60 text-sm">
          {t('common.loading', { defaultValue: 'Carregando configurações...' })}
        </span>
      </div>
    );
  }

  // Placeholder description for custom messages
  const messageMetadata: Record<MessageKey, { labelKey: string; defaultLabel: string; placeholders: string[] }> = {
    system_disabled: {
      labelKey: 'tools.shopDeliveries.raidWebhooks.labels.system_disabled',
      defaultLabel: 'Sistema Desativado',
      placeholders: [],
    },
    usage_help: {
      labelKey: 'tools.shopDeliveries.raidWebhooks.labels.usage_help',
      defaultLabel: 'Ajuda de Uso',
      placeholders: [],
    },
    no_permission: {
      labelKey: 'tools.shopDeliveries.raidWebhooks.labels.no_permission',
      defaultLabel: 'Sem Permissão',
      placeholders: [],
    },
    insufficient_funds: {
      labelKey: 'tools.shopDeliveries.raidWebhooks.labels.insufficient_funds',
      defaultLabel: 'Saldo Insuficiente',
      placeholders: ['{price}', '{balance}'],
    },
    disabled_success: {
      labelKey: 'tools.shopDeliveries.raidWebhooks.labels.disabled_success',
      defaultLabel: 'Assinatura Desativada (Com crédito)',
      placeholders: ['{expires_at}'],
    },
    disabled_success_lifetime: {
      labelKey: 'tools.shopDeliveries.raidWebhooks.labels.disabled_success_lifetime',
      defaultLabel: 'Assinatura Desativada (Vitalícia)',
      placeholders: [],
    },
    registered_success: {
      labelKey: 'tools.shopDeliveries.raidWebhooks.labels.registered_success',
      defaultLabel: 'Cadastro Realizado (Com crédito)',
      placeholders: ['{days}', '{expires_at}', '{price}'],
    },
    registered_success_lifetime: {
      labelKey: 'tools.shopDeliveries.raidWebhooks.labels.registered_success_lifetime',
      defaultLabel: 'Cadastro Realizado (Vitalício)',
      placeholders: [],
    },
    updated_success: {
      labelKey: 'tools.shopDeliveries.raidWebhooks.labels.updated_success',
      defaultLabel: 'Webhook Atualizado (Com crédito)',
      placeholders: ['{expires_at}'],
    },
    updated_success_lifetime: {
      labelKey: 'tools.shopDeliveries.raidWebhooks.labels.updated_success_lifetime',
      defaultLabel: 'Webhook Atualizado (Vitalício)',
      placeholders: [],
    },
    renewed_success: {
      labelKey: 'tools.shopDeliveries.raidWebhooks.labels.renewed_success',
      defaultLabel: 'Assinatura Estendida',
      placeholders: ['{days}', '{expires_at}', '{price}'],
    },
    status_info: {
      labelKey: 'tools.shopDeliveries.raidWebhooks.labels.status_info',
      defaultLabel: 'Status da Assinatura',
      placeholders: ['{url}', '{expires_at}', '{remaining}'],
    },
    status_expired: {
      labelKey: 'tools.shopDeliveries.raidWebhooks.labels.status_expired',
      defaultLabel: 'Status Expirado',
      placeholders: ['{url}', '{expires_at}'],
    },
    status_no_subscription: {
      labelKey: 'tools.shopDeliveries.raidWebhooks.labels.status_no_subscription',
      defaultLabel: 'Sem Assinatura Ativa',
      placeholders: [],
    },
    invalid_webhook: {
      labelKey: 'tools.shopDeliveries.raidWebhooks.labels.invalid_webhook',
      defaultLabel: 'Webhook Inválido',
      placeholders: [],
    },
    database_error: {
      labelKey: 'tools.shopDeliveries.raidWebhooks.labels.database_error',
      defaultLabel: 'Erro no Banco de Dados',
      placeholders: [],
    },
    auto_renew_success: {
      labelKey: 'tools.shopDeliveries.raidWebhooks.labels.auto_renew_success',
      defaultLabel: 'Renovação Automática com Sucesso',
      placeholders: ['{days}', '{expires_at}', '{price}'],
    },
    auto_renew_failed: {
      labelKey: 'tools.shopDeliveries.raidWebhooks.labels.auto_renew_failed',
      defaultLabel: 'Falha na Renovação Automática',
      placeholders: ['{price}', '{balance}'],
    },
    expiry_warning_3_days: {
      labelKey: 'tools.shopDeliveries.raidWebhooks.labels.expiry_warning_3_days',
      defaultLabel: 'Lembrete de Expiração (3 dias)',
      placeholders: ['{expires_at}'],
    },
    expiry_warning_1_day: {
      labelKey: 'tools.shopDeliveries.raidWebhooks.labels.expiry_warning_1_day',
      defaultLabel: 'Aviso Urgente de Expiração (1 dia)',
      placeholders: ['{expires_at}'],
    },
  };

  const messageGroups = [
    {
      id: 'commandUsage' as const,
      title: t('tools.shopDeliveries.raidWebhooks.groups.commandUsage', { defaultValue: 'Comandos & Status' }),
      keys: ['usage_help', 'status_info', 'status_expired', 'status_no_subscription'] as MessageKey[],
    },
    {
      id: 'registration' as const,
      title: t('tools.shopDeliveries.raidWebhooks.groups.registration', { defaultValue: 'Registro & Renovação Manual' }),
      keys: [
        'registered_success',
        'registered_success_lifetime',
        'updated_success',
        'updated_success_lifetime',
        'renewed_success',
        'disabled_success',
        'disabled_success_lifetime',
      ] as MessageKey[],
    },
    {
      id: 'autoRenewal' as const,
      title: t('tools.shopDeliveries.raidWebhooks.groups.autoRenewal', { defaultValue: 'Renovação Automática & Alertas' }),
      keys: ['auto_renew_success', 'auto_renew_failed', 'expiry_warning_3_days', 'expiry_warning_1_day'] as MessageKey[],
    },
    {
      id: 'errors' as const,
      title: t('tools.shopDeliveries.raidWebhooks.groups.errors', { defaultValue: 'Erros & Restrições' }),
      keys: ['system_disabled', 'no_permission', 'insufficient_funds', 'invalid_webhook', 'database_error'] as MessageKey[],
    },
  ];

  const activeGroupKeys = messageGroups.find((g) => g.id === selectedGroup)?.keys || [];

  const totalPages = Math.ceil(playersTotal / playersLimit) || 1;

  return (
    <div className="space-y-6">
      {error && (
        <div className="p-3 text-sm text-red-400 rounded-lg border border-red-500/20 bg-red-500/5 animate-pulse">
          {error}
        </div>
      )}

      {/* Help Panel */}
      <div className="card p-5 border border-blue-500/20 bg-gradient-to-br from-blue-500/10 to-transparent rounded-xl space-y-3 relative overflow-hidden">
        <div className="absolute top-0 right-0 p-4 opacity-5 pointer-events-none">
          <Info size={120} />
        </div>
        <div className="flex items-center gap-2 text-blue-400 font-bold text-sm">
          <Info size={18} />
          <span>{t('tools.shopDeliveries.raidWebhooks.infoTitle', { defaultValue: 'Webhook Pessoal de Raid (/rd)' })}</span>
        </div>
        <p className="text-xs text-white/80 leading-relaxed max-w-4xl">
          {t(
            'tools.shopDeliveries.raidWebhooks.infoDesc',
            { defaultValue: 'Esta ferramenta permite que os jogadores cadastrem seus próprios webhooks do Discord para receber notificações de invasão em tempo real. Para usar o comando /rd, os jogadores precisam ter a permissão raid_webhook_manage e pontos suficientes na carteira.' }
          )}
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left Column: General Config & Access Control */}
        <div className="lg:col-span-1 space-y-6">
          {/* General Config Card */}
          <div className="card p-5 border border-white/10 bg-gradient-to-br from-white/5 to-transparent rounded-xl space-y-4">
            <div className="flex items-center gap-2 text-white font-bold text-base">
              <Sliders className="text-scum-orange animate-pulse" size={20} />
              <span>{t('tools.shopDeliveries.raidWebhooks.generalConfig', { defaultValue: 'Configurações Gerais' })}</span>
            </div>

            {/* Enable/Disable Toggle */}
            <div className="flex items-center justify-between py-2 border-b border-white/5">
              <span className="text-sm font-medium text-white/90">{t('tools.shopDeliveries.raidWebhooks.enableFeature', { defaultValue: 'Ativar Recurso' })}</span>
              <button
                type="button"
                onClick={() => setConfig((prev) => ({ ...prev, enabled: !prev.enabled }))}
                className="focus:outline-none transition-transform hover:scale-105 duration-200"
              >
                {config.enabled ? (
                  <ToggleRight className="text-scum-orange" size={38} />
                ) : (
                  <ToggleLeft className="text-white/30" size={38} />
                )}
              </button>
            </div>

            {/* Price Points */}
            <div className="space-y-1">
              <label htmlFor="price_points" className="text-xs text-white/60 font-medium block">
                {t('tools.shopDeliveries.raidWebhooks.costLabel', { defaultValue: 'Custo de Ativação / Renovação' })}
              </label>
              <div className="relative flex items-center">
                <input
                  id="price_points"
                  type="number"
                  disabled={!config.enabled}
                  value={config.price_points}
                  onChange={(e) => {
                    const val = parseInt(e.target.value, 10);
                    setConfig((prev) => ({ ...prev, price_points: isNaN(val) ? 0 : val }));
                  }}
                  className="w-full pl-3 pr-16 py-2 rounded-lg bg-white/5 border border-white/10 text-white text-sm focus:outline-none focus:ring-2 focus:ring-scum-orange disabled:opacity-50 transition-all duration-200"
                  min="0"
                />
                <span className="absolute right-3 text-xs text-white/40 select-none">
                  {t('tools.shopDeliveries.raidWebhooks.costSuffix', { defaultValue: 'pontos' })}
                </span>
              </div>
            </div>

            {/* Duration Days */}
            <div className="space-y-1">
              <label htmlFor="duration_days" className="text-xs text-white/60 font-medium block">
                {t('tools.shopDeliveries.raidWebhooks.durationLabel', { defaultValue: 'Duração da Assinatura' })}
              </label>
              <div className="relative flex items-center">
                <input
                  id="duration_days"
                  type="number"
                  disabled={!config.enabled}
                  value={config.duration_days}
                  onChange={(e) => {
                    const val = parseInt(e.target.value, 10);
                    setConfig((prev) => ({ ...prev, duration_days: isNaN(val) ? 0 : val }));
                  }}
                  className="w-full pl-3 pr-16 py-2 rounded-lg bg-white/5 border border-white/10 text-white text-sm focus:outline-none focus:ring-2 focus:ring-scum-orange disabled:opacity-50 transition-all duration-200"
                  min="0"
                />
                <span className="absolute right-3 text-xs text-white/40 select-none">
                  {t('tools.shopDeliveries.raidWebhooks.durationSuffix', { defaultValue: 'dias' })}
                </span>
              </div>
              
              {/* Lifetime Plan Info box */}
              <div className="mt-2.5 p-2.5 rounded-lg border border-amber-500/10 bg-amber-500/5 text-[10px] text-white/70 leading-normal space-y-1">
                <div className="flex items-center gap-1.5 font-bold text-amber-400">
                  <Info size={12} className="shrink-0 animate-pulse" />
                  <span>{t('tools.shopDeliveries.raidWebhooks.lifetimePlan.title', { defaultValue: 'Plano Vitalício (Lifetime)' })}</span>
                </div>
                <p className="text-[10px] leading-relaxed text-white/60">
                  {t('tools.shopDeliveries.raidWebhooks.lifetimePlan.desc', { 
                    defaultValue: 'Defina como 0 para habilitar o plano vitalício. A expiração do jogador será salva como vazia (NULL), o webhook nunca expirará e o agendador de background não tentará cobrar ou desativá-lo por tempo.' 
                  })}
                </p>
              </div>
            </div>
          </div>

          {/* Access Control Card */}
          <div className="card p-5 border border-white/10 bg-gradient-to-br from-white/5 to-transparent rounded-xl space-y-4">
            <div className="flex items-center gap-2 text-white font-bold text-base">
              <ShieldCheck className="text-scum-orange" size={20} />
              <span>{t('tools.shopDeliveries.raidWebhooks.accessControlTitle', { defaultValue: 'Controle de Acesso (/rd)' })}</span>
            </div>

            <p className="text-xs text-white/60 leading-relaxed">
              {t('tools.shopDeliveries.raidWebhooks.accessControlDesc', { defaultValue: 'Ative ou desative o acesso ao comando /rd para jogadores específicos:' })}
            </p>

            <div className="relative">
              <input
                value={playerQuery}
                onChange={(e) => setPlayerQuery(e.target.value)}
                placeholder={t('tools.shopDeliveries.raidWebhooks.searchPlaceholder', { defaultValue: 'Buscar jogador (nome ou Steam ID)...' })}
                className="w-full pl-9 pr-3 py-2 rounded-lg bg-white/5 border border-white/10 text-white text-sm focus:outline-none focus:ring-2 focus:ring-scum-orange transition-all"
              />
              <Search className="absolute left-3 top-2.5 text-white/40" size={16} />
            </div>

            {/* Players Access List */}
            <div className="space-y-2 max-h-[340px] overflow-y-auto pr-1">
              {playersBusy && players.length === 0 ? (
                <div className="text-center py-4 text-xs text-white/55 flex justify-center items-center gap-2">
                  <RefreshCw className="animate-spin text-scum-orange" size={14} />
                  <span>{t('tools.shopDeliveries.raidWebhooks.loadingPlayers', { defaultValue: 'Carregando jogadores...' })}</span>
                </div>
              ) : players.length === 0 ? (
                <div className="text-center py-4 text-xs text-white/45">
                  {t('tools.shopDeliveries.raidWebhooks.noPlayersFound', { defaultValue: 'Nenhum jogador encontrado.' })}
                </div>
              ) : (
                players.map((player) => {
                  const steamId = player.steam_id;
                  const isUpdating = updatingPermissions.has(steamId);
                  const playerPerms = permissionsMap.get(steamId);
                  
                  // Blacklist by Default logic: player is blocked ONLY if is_active is explicitly 0 or false
                  const isBlocked = playerPerms?.permissions.some(
                    (p) => p.permission_type === 'raid_webhook_manage' && (p.is_active === false || p.is_active === 0)
                  ) || false;

                  return (
                    <div
                      key={steamId}
                      className="flex items-center justify-between p-2.5 rounded-lg border border-white/5 bg-white/5 hover:bg-white/8 transition-colors duration-150"
                    >
                      <div className="min-w-0 pr-2">
                        <div className="text-xs font-semibold text-white truncate" title={player.player_name}>
                          {player.player_name || 'Sem Nome'}
                        </div>
                        <div className="text-[10px] font-mono text-white/50 truncate">
                          {steamId}
                        </div>
                      </div>

                      <div className="flex items-center gap-2">
                        {/* Status badge */}
                        <span className={`px-2 py-0.5 rounded-full text-[9px] font-semibold border ${
                          isBlocked
                            ? 'bg-red-500/10 text-red-400 border-red-500/20'
                            : 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20'
                        }`}>
                          {isBlocked 
                            ? t('tools.shopDeliveries.raidWebhooks.blocked', { defaultValue: 'Bloqueado' })
                            : t('tools.shopDeliveries.raidWebhooks.allowed', { defaultValue: 'Permitido' })
                          }
                        </span>

                        <button
                          type="button"
                          disabled={isUpdating}
                          onClick={() => void handleTogglePermission(player)}
                          className={`flex items-center gap-1 px-2.5 py-1 rounded-lg text-[11px] font-bold border transition-all duration-200 ${
                            isBlocked
                              ? 'border-emerald-500/30 bg-emerald-500/5 text-emerald-400 hover:bg-emerald-500/20 hover:border-emerald-500/50'
                              : 'border-red-500/30 bg-red-500/5 text-red-400 hover:bg-red-500/20 hover:border-red-500/50'
                          } disabled:opacity-50`}
                        >
                          {isUpdating ? (
                            <RefreshCw className="animate-spin" size={12} />
                          ) : isBlocked ? (
                            <>
                              <ShieldCheck size={12} />
                              <span>{t('tools.shopDeliveries.raidWebhooks.allowBtn', { defaultValue: 'Permitir' })}</span>
                            </>
                          ) : (
                            <>
                              <ShieldAlert size={12} />
                              <span>{t('tools.shopDeliveries.raidWebhooks.blockBtn', { defaultValue: 'Bloquear' })}</span>
                            </>
                          )}
                        </button>
                      </div>
                    </div>
                  );
                })
              )}
            </div>

            {/* Pagination Controls */}
            {totalPages > 1 && (
              <div className="flex items-center justify-between pt-2 border-t border-white/5">
                <span className="text-[10px] text-white/40">
                  {t('tools.shopDeliveries.raidWebhooks.pageIndicator', { 
                    defaultValue: 'Pág. {{page}} / {{totalPages}}',
                    page: playersPage,
                    totalPages: totalPages
                  })}
                </span>
                <div className="flex items-center gap-1">
                  <button
                    type="button"
                    disabled={playersBusy || playersPage <= 1}
                    onClick={() => void loadPlayersPage(playersPage - 1)}
                    className="px-2 py-1 rounded bg-white/5 hover:bg-white/10 text-white/90 text-xs disabled:opacity-50 transition-colors"
                  >
                    {t('tools.shopDeliveries.raidWebhooks.prevPage', { defaultValue: 'Anterior' })}
                  </button>
                  <button
                    type="button"
                    disabled={playersBusy || playersPage >= totalPages}
                    onClick={() => void loadPlayersPage(playersPage + 1)}
                    className="px-2 py-1 rounded bg-white/5 hover:bg-white/10 text-white/90 text-xs disabled:opacity-50 transition-colors"
                  >
                    {t('tools.shopDeliveries.raidWebhooks.nextPage', { defaultValue: 'Próxima' })}
                  </button>
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Right Column: Custom Messages */}
        <div className="lg:col-span-2 space-y-4">
          <div className="card p-5 border border-white/10 bg-gradient-to-br from-white/5 to-transparent rounded-xl space-y-4">
            <div className="flex items-center gap-2 text-white font-bold text-base">
              <MessageSquare className="text-scum-orange" size={20} />
              <span>{t('tools.shopDeliveries.raidWebhooks.chatMessagesTitle', { defaultValue: 'Mensagens do Chat RCON' })}</span>
            </div>

            <p className="text-xs text-white/60 leading-relaxed">
              {t(
                'tools.shopDeliveries.raidWebhooks.chatMessagesDesc',
                { defaultValue: 'Personalize as respostas enviadas aos jogadores no chat in-game ao interagir com o comando /rd. Use os marcadores indicados para inserir dados dinâmicos.' }
              )}
            </p>

            {/* Premium Pill tabs to filter message keys */}
            <div className="flex flex-wrap gap-1.5 p-1 bg-white/5 rounded-xl border border-white/5">
              {messageGroups.map((grp) => (
                <button
                  key={grp.id}
                  type="button"
                  onClick={() => setSelectedGroup(grp.id)}
                  className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition-all duration-200 ${
                    selectedGroup === grp.id
                      ? 'bg-scum-orange text-white shadow-lg shadow-scum-orange/20'
                      : 'text-white/60 hover:text-white hover:bg-white/5'
                  }`}
                >
                  {grp.title}
                </button>
              ))}
            </div>

            <div className="space-y-4 pt-2">
              {activeGroupKeys.map((key) => {
                const meta = messageMetadata[key];
                const value = config.messages[key] || '';
                const label = meta ? t(meta.labelKey, { defaultValue: meta.defaultLabel }) : key;

                return (
                  <div key={key} className="space-y-1.5 p-3.5 rounded-lg border border-white/5 bg-white/5 hover:border-white/10 transition-all duration-150">
                    <div className="flex items-center justify-between">
                      <span className="text-xs font-bold text-white/80">
                        {label}
                      </span>
                      <span className="text-[10px] font-mono text-white/40 select-all bg-black/30 px-1.5 py-0.5 rounded">
                        {key}
                      </span>
                    </div>

                    <input
                      type="text"
                      disabled={!config.enabled}
                      value={value}
                      onChange={(e) => {
                        const nextVal = e.target.value;
                        setConfig((prev) => ({
                          ...prev,
                          messages: {
                            ...prev.messages,
                            [key]: nextVal,
                          },
                        }));
                      }}
                      className="w-full px-3 py-2 rounded-lg bg-black/20 border border-white/10 text-white text-sm focus:outline-none focus:ring-2 focus:ring-scum-orange disabled:opacity-50 transition-all"
                    />

                    {meta?.placeholders && meta.placeholders.length > 0 && (
                      <div className="flex items-center gap-1.5 pt-1.5">
                        <span className="text-[10px] text-white/40 font-medium">Parâmetros disponíveis:</span>
                        <div className="flex flex-wrap gap-1">
                          {meta.placeholders.map((p) => (
                            <span
                              key={p}
                              className="px-1.5 py-0.5 rounded bg-scum-orange/15 text-scum-orange font-mono text-[9px] border border-scum-orange/20"
                            >
                              {p}
                            </span>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          </div>
        </div>
      </div>

      {/* Sticky Save Bar */}
      <div className="card p-4 flex items-center justify-between border border-white/10 bg-[#0b1220]/80 backdrop-blur-md sticky bottom-4 z-30 rounded-xl">
        <div className="text-xs text-white/50">
          {hasChanges() ? (
            <span className="text-amber-400 font-medium">
              {t('tools.shopDeliveries.raidWebhooks.unsavedChanges', { defaultValue: 'Você possui alterações não salvas neste painel.' })}
            </span>
          ) : (
            <span>{t('tools.shopDeliveries.raidWebhooks.noChanges', { defaultValue: 'Sem alterações pendentes.' })}</span>
          )}
        </div>

        <div className="flex gap-2">
          <button
            type="button"
            disabled={!hasChanges() || saving}
            onClick={handleRevert}
            className="px-4 py-2 rounded-lg border border-white/15 bg-white/8 text-sm font-medium text-white/90 hover:bg-white/12 hover:border-white/25 disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-1.5 transition-all duration-200"
          >
            <RotateCcw size={16} />
            <span>{t('tools.shopDeliveries.raidWebhooks.revertBtn', { defaultValue: 'Reverter' })}</span>
          </button>
          <button
            type="button"
            disabled={!hasChanges() || saving}
            onClick={handleSave}
            className="px-4 py-2 rounded-lg border border-scum-orange/60 bg-scum-orange/10 text-sm font-semibold text-scum-orange hover:bg-scum-orange/20 hover:border-scum-orange/80 focus:outline-none focus:ring-2 focus:ring-scum-orange/70 disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-1.5 transition-all duration-200"
          >
            {saving ? (
              <>
                <RefreshCw size={16} className="animate-spin" />
                <span>{t('tools.shopDeliveries.raidWebhooks.savingBtn', { defaultValue: 'Salvando...' })}</span>
              </>
            ) : (
              <>
                <Save size={16} />
                <span>{t('tools.shopDeliveries.raidWebhooks.saveBtn', { defaultValue: 'Salvar' })}</span>
              </>
            )}
          </button>
        </div>
      </div>
    </div>
  );
}
