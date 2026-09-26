import { useState, useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import { Loader2, Save, RefreshCw, AlertTriangle, ShieldAlert, Coins, MapPin, Info } from 'lucide-react';
import Swal from 'sweetalert2';
import { getConfig, updateConfigSection } from '@/services/config';

interface MinePunishmentTabProps {
  searchQuery?: string;
  onSearchChange?: (query: string) => void;
}

interface MinePunishmentConfig {
  teleport_punishment_enabled: boolean;
  teleport_punishment_delay_seconds: number;
  wallet_fine_enabled: boolean;
  wallet_fine_amount: number;
  flag_radius_units: number;
  flag_radius_tolerance_units: number;
  teleport_message: string;
}

export default function MinePunishmentTab({ searchQuery = '' }: MinePunishmentTabProps) {
  const { t } = useTranslation();
  const [configData, setConfigData] = useState<MinePunishmentConfig>({
    teleport_punishment_enabled: false,
    teleport_punishment_delay_seconds: 5.0,
    wallet_fine_enabled: false,
    wallet_fine_amount: 1000,
    flag_radius_units: 10000,
    flag_radius_tolerance_units: 600,
    teleport_message: 'ATENCAO: Voce foi teleportado por implantar mina fora da flag!',
  });
  const [originalConfigData, setOriginalConfigData] = useState<MinePunishmentConfig>({
    teleport_punishment_enabled: false,
    teleport_punishment_delay_seconds: 5.0,
    wallet_fine_enabled: false,
    wallet_fine_amount: 1000,
    flag_radius_units: 10000,
    flag_radius_tolerance_units: 600,
    teleport_message: 'ATENCAO: Voce foi teleportado por implantar mina fora da flag!',
  });
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const loadData = async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await getConfig('mines_alerts');
      if (response.success && response.data) {
        const data = response.data;
        const loadedConfig = {
          teleport_punishment_enabled: data.teleport_punishment_enabled === true,
          teleport_punishment_delay_seconds: Number(data.teleport_punishment_delay_seconds ?? 5.0),
          wallet_fine_enabled: data.wallet_fine_enabled === true,
          wallet_fine_amount: Number(data.wallet_fine_amount ?? 1000),
          flag_radius_units: Number(data.flag_radius_units ?? 10000),
          flag_radius_tolerance_units: Number(data.flag_radius_tolerance_units ?? 600),
          teleport_message: String(data.teleport_message ?? 'ATENCAO: Voce foi teleportado por implantar mina fora da flag!'),
        };
        setConfigData(loadedConfig);
        setOriginalConfigData(loadedConfig);
      } else {
        setError(response.error || t('settings.minePunishment.error_loading', 'Erro ao carregar dados'));
      }
    } catch (err: any) {
      setError(err.message || t('settings.minePunishment.error_loading', 'Erro ao carregar dados'));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const handleToggle = (key: keyof MinePunishmentConfig) => {
    setConfigData((prev) => ({
      ...prev,
      [key]: !prev[key],
    }));
  };

  const handleNumberChange = (key: keyof MinePunishmentConfig, value: number) => {
    setConfigData((prev) => ({
      ...prev,
      [key]: value,
    }));
  };

  const handleSave = async () => {
    setSaving(true);
    try {
      const response = await updateConfigSection('mines_alerts', configData, true);
      if (response.success) {
        setOriginalConfigData(configData);
        await Swal.fire({
          icon: 'success',
          title: t('settings.minePunishment.save_success', 'Configurações salvas!'),
          text: t('settings.discord.save.backup', 'Configurações atualizadas e backup criado com sucesso.'),
          confirmButtonColor: '#f97316',
        });
      } else {
        throw new Error(response.error || response.message || t('settings.minePunishment.save_error', 'Erro ao salvar as configurações'));
      }
    } catch (err: any) {
      const errorMsg = err.response?.data?.error || err.message || t('settings.minePunishment.save_error', 'Erro ao salvar as configurações');
      await Swal.fire({
        icon: 'error',
        title: t('settings.errors.saveFailed', 'Erro ao salvar'),
        text: errorMsg,
        confirmButtonColor: '#f97316',
      });
    } finally {
      setSaving(false);
    }
  };

  const hasChanges =
    configData.teleport_punishment_enabled !== originalConfigData.teleport_punishment_enabled ||
    configData.teleport_punishment_delay_seconds !== originalConfigData.teleport_punishment_delay_seconds ||
    configData.wallet_fine_enabled !== originalConfigData.wallet_fine_enabled ||
    configData.wallet_fine_amount !== originalConfigData.wallet_fine_amount ||
    configData.flag_radius_units !== originalConfigData.flag_radius_units ||
    configData.flag_radius_tolerance_units !== originalConfigData.flag_radius_tolerance_units ||
    configData.teleport_message !== originalConfigData.teleport_message;

  if (loading) {
    return (
      <div className="flex items-center justify-center py-12">
        <Loader2 className="w-8 h-8 animate-spin text-scum-orange" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="card p-6">
        <div className="flex items-center gap-3 text-red-400">
          <div>
            <h3 className="font-semibold">{t('settings.minePunishment.error_loading', 'Erro ao carregar dados')}</h3>
            <p className="text-sm text-white/70 mt-1">{error}</p>
            <button
              onClick={loadData}
              className="mt-4 px-4 py-2 bg-white/5 hover:bg-white/10 border border-white/10 rounded-lg text-sm text-white flex items-center gap-2 transition-colors"
            >
              <RefreshCw size={16} />
              {t('common.retry', 'Tentar novamente')}
            </button>
          </div>
        </div>
      </div>
    );
  }

  const query = searchQuery.toLowerCase().trim();
  const showTeleport =
    !query ||
    t('settings.minePunishment.teleport.title', 'Teleporte (Death Carousel)').toLowerCase().includes(query) ||
    t('settings.minePunishment.teleport.description', 'Teleporta o jogador que implantou a mina ilegal diretamente para cima dela.').toLowerCase().includes(query) ||
    'teleport_punishment_enabled'.includes(query) ||
    t('settings.minePunishment.teleport.delay', 'Atraso').toLowerCase().includes(query) ||
    t('settings.minePunishment.teleport.message', 'Mensagem').toLowerCase().includes(query);
  const showWallet =
    !query ||
    t('settings.minePunishment.wallet.title', 'Multa Financeira').toLowerCase().includes(query) ||
    t('settings.minePunishment.wallet.description', 'Aplica um débito na carteira do jogador imediatamente após a implantação.').toLowerCase().includes(query) ||
    'wallet_fine_enabled'.includes(query) ||
    t('settings.minePunishment.wallet.amount', 'Valor da Multa').toLowerCase().includes(query);
  const showRadius =
    !query ||
    t('settings.minePunishment.radius.title', 'Raio de Proteção').toLowerCase().includes(query) ||
    t('settings.minePunishment.radius.description', 'Define os limites de distância das minas em relação às flags dos jogadores.').toLowerCase().includes(query) ||
    'flag_radius_units'.includes(query) ||
    t('settings.minePunishment.radius.default_radius', 'Raio Padrão da Flag').toLowerCase().includes(query) ||
    t('settings.minePunishment.radius.tolerance', 'Tolerância de Raio').toLowerCase().includes(query);

  return (
    <div className="space-y-6">
      <div className="card p-4 sm:p-6 space-y-6">
        <div>
          <h2 className="text-lg font-bold text-white flex items-center gap-2">
            <ShieldAlert className="text-scum-orange w-5 h-5" />
            {t('settings.minePunishment.title', 'Punição de Minas Fora de Bandeira')}
          </h2>
          <p className="text-sm text-white/60 mt-1">
            {t(
              'settings.minePunishment.description',
              'Configure o sistema de monitoramento automático e punição para jogadores que implantam minas/armadilhas fora do raio de proteção de suas bandeiras.'
            )}
          </p>
        </div>

        <div className="space-y-4">
          {/* Grid de Configurações (Todos os 3 Lado a Lado no Desktop) */}
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-4 items-stretch">
            
            {/* Coluna 1: Punição de Teleporte */}
            {showTeleport && (
              <div className="bg-white/5 border border-white/10 rounded-xl p-4 sm:p-5 flex flex-col justify-between space-y-4">
                <div className="flex items-start justify-between gap-4">
                  <div>
                    <h3 className="text-sm font-semibold text-white">
                      {t('settings.minePunishment.teleport.title', 'Teleporte (Death Carousel)')}
                    </h3>
                    <p className="text-xs text-white/50 mt-1">
                      {t('settings.minePunishment.teleport.description', 'Teleporta o jogador que implantou a mina ilegal diretamente para cima dela.')}
                    </p>
                  </div>
                  <label className="relative inline-flex items-center cursor-pointer flex-shrink-0 mt-0.5">
                    <input
                      type="checkbox"
                      checked={configData.teleport_punishment_enabled}
                      onChange={() => handleToggle('teleport_punishment_enabled')}
                      className="sr-only peer"
                      disabled={saving}
                    />
                    <div className="w-11 h-6 bg-white/10 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-scum-orange"></div>
                  </label>
                </div>

                {configData.teleport_punishment_enabled && (
                  <div className="space-y-3 pt-3 border-t border-white/5">
                    {/* Atraso */}
                    <div className="flex items-center justify-between gap-2">
                      <div className="flex items-center gap-1.5">
                        <label htmlFor="teleport_punishment_delay_seconds" className="text-xs font-medium text-white/70">
                          {t('settings.minePunishment.teleport.delay', 'Atraso')}
                        </label>
                        <div className="group relative inline-block">
                          <Info className="w-3.5 h-3.5 text-white/40 hover:text-white/80 cursor-pointer" />
                          <div className="pointer-events-none absolute bottom-full left-1/2 z-50 mb-2 w-48 -translate-x-1/2 rounded bg-black/95 px-2.5 py-1.5 text-[11px] font-normal text-white/90 opacity-0 transition-opacity group-hover:opacity-100 shadow-xl border border-white/10 text-center whitespace-normal normal-case leading-normal">
                            {t('settings.minePunishment.teleport.delay_tooltip', 'Tempo em segundos antes de executar o teleporte do infrator. Recomendado: 5 segundos.')}
                          </div>
                        </div>
                      </div>
                      <div className="flex items-center gap-1.5">
                        <input
                          id="teleport_punishment_delay_seconds"
                          type="number"
                          min="1"
                          max="300"
                          step="0.5"
                          value={configData.teleport_punishment_delay_seconds}
                          onChange={(e) => handleNumberChange('teleport_punishment_delay_seconds', Number(e.target.value))}
                          className="w-16 px-2 py-1 bg-white/5 border border-white/10 rounded-lg text-white text-sm focus:outline-none focus:ring-2 focus:ring-scum-orange focus:border-transparent text-center"
                          disabled={saving}
                        />
                        <span className="text-xs text-white/40">s</span>
                      </div>
                    </div>

                    {/* Mensagem */}
                    <div className="space-y-1.5">
                      <div className="flex items-center gap-1.5">
                        <label htmlFor="teleport_message" className="text-xs font-medium text-white/70">
                          {t('settings.minePunishment.teleport.message', 'Mensagem do Teleporte')}
                        </label>
                        <div className="group relative inline-block">
                          <Info className="w-3.5 h-3.5 text-white/40 hover:text-white/80 cursor-pointer" />
                          <div className="pointer-events-none absolute bottom-full left-1/2 z-50 mb-2 w-48 -translate-x-1/2 rounded bg-black/95 px-2.5 py-1.5 text-[11px] font-normal text-white/90 opacity-0 transition-opacity group-hover:opacity-100 shadow-xl border border-white/10 text-center whitespace-normal normal-case leading-normal">
                            {t('settings.minePunishment.teleport.message_tooltip', 'Aviso enviado por notificação ao jogador ao ser punido.')}
                          </div>
                        </div>
                      </div>
                      <input
                        id="teleport_message"
                        type="text"
                        value={configData.teleport_message}
                        onChange={(e) => setConfigData(prev => ({ ...prev, teleport_message: e.target.value }))}
                        className="w-full px-3 py-1 bg-white/5 border border-white/10 rounded-lg text-white text-sm placeholder-white/30 focus:outline-none focus:ring-2 focus:ring-scum-orange focus:border-transparent"
                        placeholder={t('settings.minePunishment.teleport.message_placeholder', 'Mensagem exibida na tela')}
                        disabled={saving}
                      />
                    </div>
                  </div>
                )}
              </div>
            )}

            {/* Coluna 2: Punição Financeira */}
            {showWallet && (
              <div className="bg-white/5 border border-white/10 rounded-xl p-4 sm:p-5 flex flex-col justify-between space-y-4">
                <div className="flex items-start justify-between gap-4">
                  <div>
                    <h3 className="text-sm font-semibold text-white">
                      {t('settings.minePunishment.wallet.title', 'Multa Financeira')}
                    </h3>
                    <p className="text-xs text-white/50 mt-1">
                      {t('settings.minePunishment.wallet.description', 'Aplica um débito na carteira do jogador imediatamente após a implantação.')}
                    </p>
                  </div>
                  <label className="relative inline-flex items-center cursor-pointer flex-shrink-0 mt-0.5">
                    <input
                      type="checkbox"
                      checked={configData.wallet_fine_enabled}
                      onChange={() => handleToggle('wallet_fine_enabled')}
                      className="sr-only peer"
                      disabled={saving}
                    />
                    <div className="w-11 h-6 bg-white/10 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-scum-orange"></div>
                  </label>
                </div>

                {/* Mostra o campo de valor sempre para manter a estabilidade do layout */}
                <div className="pt-3 border-t border-white/5">
                  <div className={`flex items-center justify-between gap-2 transition-opacity duration-200 ${configData.wallet_fine_enabled ? 'opacity-100' : 'opacity-35'}`}>
                    <div className="flex items-center gap-1.5">
                      <label htmlFor="wallet_fine_amount" className="text-xs font-medium text-white/70">
                        {t('settings.minePunishment.wallet.amount', 'Valor da Multa')}
                      </label>
                      <div className="group relative inline-block">
                        <Info className="w-3.5 h-3.5 text-white/40 hover:text-white/80 cursor-pointer" />
                        <div className="pointer-events-none absolute bottom-full left-1/2 z-50 mb-2 w-48 -translate-x-1/2 rounded bg-black/95 px-2.5 py-1.5 text-[11px] font-normal text-white/90 opacity-0 transition-opacity group-hover:opacity-100 shadow-xl border border-white/10 text-center whitespace-normal normal-case leading-normal">
                          {t('settings.minePunishment.wallet.amount_tooltip', 'Aplica um débito na carteira do jogador. O saldo é deduzido mesmo se ficar negativo.')}
                        </div>
                      </div>
                    </div>
                    <div className="relative flex items-center">
                      <span className="absolute left-2.5 text-xs text-white/40 font-mono">$</span>
                      <input
                        id="wallet_fine_amount"
                        type="number"
                        min="0"
                        value={configData.wallet_fine_amount}
                        onChange={(e) => handleNumberChange('wallet_fine_amount', Math.max(0, Number(e.target.value)))}
                        className="w-24 pl-6 pr-2 py-1 bg-white/5 border border-white/10 rounded-lg text-white text-sm focus:outline-none focus:ring-2 focus:ring-scum-orange focus:border-transparent text-center"
                        disabled={saving || !configData.wallet_fine_enabled}
                      />
                    </div>
                  </div>
                </div>
              </div>
            )}

            {/* Coluna 3: Raio e Tolerância */}
            {showRadius && (
              <div className="bg-white/5 border border-white/10 rounded-xl p-4 sm:p-5 flex flex-col justify-between space-y-4">
                <div className="flex items-start justify-between gap-4">
                  <div>
                    <h3 className="text-sm font-semibold text-white">
                      {t('settings.minePunishment.radius.title', 'Raio de Proteção')}
                    </h3>
                    <p className="text-xs text-white/50 mt-1">
                      {t('settings.minePunishment.radius.description', 'Define os limites de distância das minas em relação às flags dos jogadores.')}
                    </p>
                  </div>
                  <div className="group relative inline-block mt-0.5">
                    <Info className="w-3.5 h-3.5 text-white/40 hover:text-white/80 cursor-pointer" />
                    <div className="pointer-events-none absolute bottom-full right-0 z-50 mb-2 w-48 rounded bg-black/95 px-2.5 py-1.5 text-[11px] font-normal text-white/90 opacity-0 transition-opacity group-hover:opacity-100 shadow-xl border border-white/10 text-center whitespace-normal normal-case leading-normal">
                      {t('settings.minePunishment.radius.tooltip', 'Configurações de distância para legalidade das minas em relação às bandeiras dos jogadores.')}
                    </div>
                  </div>
                </div>

                <div className="space-y-3 pt-3 border-t border-white/5">
                  {/* Raio Padrão */}
                  <div className="flex items-center justify-between gap-2">
                    <div className="flex items-center gap-1.5">
                      <label htmlFor="flag_radius_units" className="text-xs font-medium text-white/70">
                        {t('settings.minePunishment.radius.default_radius', 'Raio Padrão da Flag')}
                      </label>
                      <div className="group relative inline-block">
                        <Info className="w-3.5 h-3.5 text-white/40 hover:text-white/80 cursor-pointer" />
                        <div className="pointer-events-none absolute bottom-full left-1/2 z-50 mb-2 w-48 -translate-x-1/2 rounded bg-black/95 px-2.5 py-1.5 text-[11px] font-normal text-white/90 opacity-0 transition-opacity group-hover:opacity-100 shadow-xl border border-white/10 text-center whitespace-normal normal-case leading-normal">
                          {t('settings.minePunishment.radius.default_radius_tooltip', 'Geralmente 10000 units correspondem ao raio padrão do círculo da bandeira.')}
                        </div>
                      </div>
                    </div>
                    <div className="flex items-center gap-1.5">
                      <input
                        id="flag_radius_units"
                        type="number"
                        min="1"
                        value={configData.flag_radius_units}
                        onChange={(e) => handleNumberChange('flag_radius_units', Math.max(1, Number(e.target.value)))}
                        className="w-24 px-2 py-1 bg-white/5 border border-white/10 rounded-lg text-white text-sm focus:outline-none focus:ring-2 focus:ring-scum-orange focus:border-transparent text-center"
                        disabled={saving}
                      />
                      <span className="text-xs text-white/40 whitespace-nowrap">units</span>
                    </div>
                  </div>

                  {/* Tolerância */}
                  <div className="flex items-center justify-between gap-2">
                    <div className="flex items-center gap-1.5">
                      <label htmlFor="flag_radius_tolerance_units" className="text-xs font-medium text-white/70">
                        {t('settings.minePunishment.radius.tolerance', 'Tolerância de Raio')}
                      </label>
                      <div className="group relative inline-block">
                        <Info className="w-3.5 h-3.5 text-white/40 hover:text-white/80 cursor-pointer" />
                        <div className="pointer-events-none absolute bottom-full left-1/2 z-50 mb-2 w-48 -translate-x-1/2 rounded bg-black/95 px-2.5 py-1.5 text-[11px] font-normal text-white/90 opacity-0 transition-opacity group-hover:opacity-100 shadow-xl border border-white/10 text-center whitespace-normal normal-case leading-normal">
                          {t('settings.minePunishment.radius.tolerance_tooltip', 'Margem de erro tolerada para além do círculo da bandeira (padrão 600 units).')}
                        </div>
                      </div>
                    </div>
                    <div className="flex items-center gap-1.5">
                      <input
                        id="flag_radius_tolerance_units"
                        type="number"
                        min="0"
                        value={configData.flag_radius_tolerance_units}
                        onChange={(e) => handleNumberChange('flag_radius_tolerance_units', Math.max(0, Number(e.target.value)))}
                        className="w-20 px-2 py-1 bg-white/5 border border-white/10 rounded-lg text-white text-sm focus:outline-none focus:ring-2 focus:ring-scum-orange focus:border-transparent text-center"
                        disabled={saving}
                      />
                      <span className="text-xs text-white/40 whitespace-nowrap">units</span>
                    </div>
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Rodapé e Ações */}
        <div className="flex flex-col sm:flex-row gap-4 items-center justify-between pt-4 border-t border-white/10">
          <div className="flex items-center gap-2 text-white/50 text-xs">
            <AlertTriangle size={14} className="text-scum-orange animate-pulse flex-shrink-0" />
            <span>{t('settings.minePunishment.footer_warning', 'As mudanças nas configurações se aplicam em tempo real nos próximos logs processados.')}</span>
          </div>

          <div className="flex gap-3 w-full sm:w-auto">
            <button
              onClick={loadData}
              disabled={loading || saving}
              className="flex-1 sm:flex-none px-4 py-2 bg-white/5 hover:bg-white/10 border border-white/10 rounded-lg text-sm font-medium text-white transition-colors flex items-center justify-center gap-2"
            >
              <RefreshCw size={16} />
              {t('common.revert', 'Descartar')}
            </button>
            <button
              onClick={handleSave}
              disabled={saving || !hasChanges}
              className={`flex-1 sm:flex-none px-5 py-2 rounded-lg text-sm font-medium transition-all flex items-center justify-center gap-2 ${
                hasChanges && !saving
                  ? 'bg-scum-orange hover:bg-scum-orange/90 text-white shadow-lg shadow-scum-orange/20'
                  : 'bg-white/5 text-white/40 border border-white/5 cursor-not-allowed'
              }`}
            >
              {saving ? <Loader2 size={16} className="animate-spin" /> : <Save size={16} />}
              {t('common.save', 'Salvar alterações')}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
