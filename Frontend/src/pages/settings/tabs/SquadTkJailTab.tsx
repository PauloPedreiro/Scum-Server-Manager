import { useState, useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import { Loader2, Save, RefreshCw, AlertTriangle, Scale, Lock, Info } from 'lucide-react';
import Swal from 'sweetalert2';
import { getConfig, updateConfigSection } from '@/services/config';

interface SquadTkJailTabProps {
  searchQuery?: string;
  onSearchChange?: (query: string) => void;
}

interface SquadTkJailConfig {
  enabled: boolean;
  jail_coordinates: string;
  jail_radius_meters: number;
  jail_duration_minutes: number;
  warning_color: string;
  use_colors: boolean;
  announcement_message: string;
  escape_message: string;
  release_message: string;
}

const COLOR_PRESETS = [
  { value: '7', hex: '#EF4444', nameKey: 'settings.rconRoutines.colors.red',    nameDefault: 'Vermelho' },
  { value: '6', hex: '#F97316', nameKey: 'settings.rconRoutines.colors.orange', nameDefault: 'Laranja'  },
  { value: '4', hex: '#EAB308', nameKey: 'settings.rconRoutines.colors.yellow', nameDefault: 'Amarelo'  },
  { value: '3', hex: '#22C55E', nameKey: 'settings.rconRoutines.colors.green',  nameDefault: 'Verde'    },
  { value: '2', hex: '#38BDF8', nameKey: 'settings.rconRoutines.colors.blue',   nameDefault: 'Azul'     },
  { value: '0', hex: '#F1F5F9', nameKey: 'settings.rconRoutines.colors.white',  nameDefault: 'Branco'   },
];

function cleanScumCoordinates(input: string): string {
  const trimmed = input.trim();
  if (!trimmed) return '';
  
  // Regex to match X, Y, Z coordinates from SCUM teleport/telemetry format:
  // e.g. {X=-271417.281 Y=314246.875 Z=84056.023|P=...}
  // or X=-271417.281 Y=314246.875 Z=84056.023
  const regex = /X\s*=\s*([-+]?\d+\.?\d*)\s*Y\s*=\s*([-+]?\d+\.?\d*)\s*Z\s*=\s*([-+]?\d+\.?\d*)/i;
  const match = trimmed.match(regex);
  if (match) {
    const x = parseFloat(match[1]);
    const y = parseFloat(match[2]);
    const z = parseFloat(match[3]);
    return `${x} ${y} ${z}`;
  }
  
  // Also match comma or space separated numbers: -271417.281, 314246.875, 84056.023
  const numbersRegex = /^\s*([-+]?\d+\.?\d*)[,\s]+([-+]?\d+\.?\d*)[,\s]+([-+]?\d+\.?\d*)\s*$/;
  const numbersMatch = trimmed.match(numbersRegex);
  if (numbersMatch) {
    const x = parseFloat(numbersMatch[1]);
    const y = parseFloat(numbersMatch[2]);
    const z = parseFloat(numbersMatch[3]);
    return `${x} ${y} ${z}`;
  }
  
  return trimmed;
}

export default function SquadTkJailTab({ searchQuery = '' }: SquadTkJailTabProps) {
  const { t } = useTranslation();
  const [configData, setConfigData] = useState<SquadTkJailConfig>({
    enabled: false,
    jail_coordinates: '-271417.281 314246.875 84056.023',
    jail_radius_meters: 20.0,
    jail_duration_minutes: 30,
    warning_color: '2',
    use_colors: true,
    announcement_message: '{killer} matou o companheiro de squad {victim} e foi enviado para a prisão por {minutes} minutos!',
    escape_message: '{player}, você tentou escapar! Retornando para a cela.',
    release_message: '{player} cumpriu sua pena e foi libertado!',
  });
  const [originalConfigData, setOriginalConfigData] = useState<SquadTkJailConfig>({
    enabled: false,
    jail_coordinates: '-271417.281 314246.875 84056.023',
    jail_radius_meters: 20.0,
    jail_duration_minutes: 30,
    warning_color: '2',
    use_colors: true,
    announcement_message: '{killer} matou o companheiro de squad {victim} e foi enviado para a prisão por {minutes} minutos!',
    escape_message: '{player}, você tentou escapar! Retornando para a cela.',
    release_message: '{player} cumpriu sua pena e foi libertado!',
  });
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const loadData = async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await getConfig('squad_tk_jail');
      if (response.success && response.data) {
        // Safe mapping
        const data = response.data;
        const loadedConfig = {
          enabled: data.enabled === true,
          jail_coordinates: String(data.jail_coordinates ?? '-271417.281 314246.875 84056.023'),
          jail_radius_meters: Number(data.jail_radius_meters ?? 20.0),
          jail_duration_minutes: Number(data.jail_duration_minutes ?? 30),
          warning_color: String(data.warning_color ?? '2'),
          use_colors: data.use_colors !== false,
          announcement_message: String(data.announcement_message ?? '{killer} matou o companheiro de squad {victim} e foi enviado para a prisão por {minutes} minutos!'),
          escape_message: String(data.escape_message ?? '{player}, você tentou escapar! Retornando para a cela.'),
          release_message: String(data.release_message ?? '{player} cumpriu sua pena e foi libertado!'),
        };
        setConfigData(loadedConfig);
        setOriginalConfigData(loadedConfig);
      } else {
        setError(response.error || t('settings.squadTkJail.error_loading', 'Erro ao carregar dados'));
      }
    } catch (err: any) {
      setError(err.message || t('settings.squadTkJail.error_loading', 'Erro ao carregar dados'));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const handleToggle = (key: 'enabled' | 'use_colors') => {
    setConfigData((prev) => ({
      ...prev,
      [key]: !prev[key],
    }));
  };

  const handleSave = async () => {
    const cleanedCoords = cleanScumCoordinates(configData.jail_coordinates);

    // Validate bounds
    if (configData.jail_radius_meters < 1) {
      await Swal.fire({
        icon: 'warning',
        title: t('common.warning', 'Aviso'),
        text: t('settings.squadTkJail.validation.radius_min', 'O raio mínimo da cela é de 1 metro.'),
        confirmButtonColor: '#f97316',
      });
      return;
    }
    if (configData.jail_duration_minutes < 1) {
      await Swal.fire({
        icon: 'warning',
        title: t('common.warning', 'Aviso'),
        text: t('settings.squadTkJail.validation.duration_min', 'A duração mínima da prisão é de 1 minuto.'),
        confirmButtonColor: '#f97316',
      });
      return;
    }
    if (!cleanedCoords) {
      await Swal.fire({
        icon: 'warning',
        title: t('common.warning', 'Aviso'),
        text: t('settings.squadTkJail.validation.coords_required', 'As coordenadas da cela são obrigatórias.'),
        confirmButtonColor: '#f97316',
      });
      return;
    }

    const updatedConfig = {
      ...configData,
      jail_coordinates: cleanedCoords,
    };
    setConfigData(updatedConfig);

    setSaving(true);
    try {
      const response = await updateConfigSection('squad_tk_jail', updatedConfig, true);
      if (response.success) {
        setOriginalConfigData(updatedConfig);
        await Swal.fire({
          icon: 'success',
          title: t('settings.squadTkJail.save_success', 'Configurações salvas!'),
          text: t('settings.discord.save.backup', 'Configurações atualizadas e backup criado com sucesso.'),
          confirmButtonColor: '#f97316',
        });
      } else {
        throw new Error(response.error || response.message || t('settings.squadTkJail.save_error', 'Erro ao salvar as configurações'));
      }
    } catch (err: any) {
      const errorMsg = err.response?.data?.error || err.message || t('settings.squadTkJail.save_error', 'Erro ao salvar as configurações');
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
    configData.enabled !== originalConfigData.enabled ||
    configData.jail_coordinates !== originalConfigData.jail_coordinates ||
    configData.jail_radius_meters !== originalConfigData.jail_radius_meters ||
    configData.jail_duration_minutes !== originalConfigData.jail_duration_minutes ||
    configData.warning_color !== originalConfigData.warning_color ||
    configData.use_colors !== originalConfigData.use_colors ||
    configData.announcement_message !== originalConfigData.announcement_message ||
    configData.escape_message !== originalConfigData.escape_message ||
    configData.release_message !== originalConfigData.release_message;

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
            <h3 className="font-semibold">{t('settings.squadTkJail.error_loading', 'Erro ao carregar dados')}</h3>
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
  const matchesSearch = (text: string) => !query || text.toLowerCase().includes(query);

  const showGeneral = matchesSearch(t('settings.squadTkJail.general.title', 'Configurações Gerais')) ||
    matchesSearch('jail_coordinates') || matchesSearch('jail_radius_meters') || matchesSearch('jail_duration_minutes');
  
  const showMessages = matchesSearch(t('settings.squadTkJail.messages.title', 'Mensagens Customizáveis')) ||
    matchesSearch('announcement_message') || matchesSearch('escape_message') || matchesSearch('release_message');

  return (
    <div className="space-y-6">
      <div className="card p-4 sm:p-6 space-y-6">
        <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
          <div>
            <h2 className="text-lg font-bold text-white flex items-center gap-2">
              <Scale className="text-scum-orange w-5 h-5" />
              {t('settings.squadTkJail.title', 'Punição por Team Kill (Squad TK Jail)')}
            </h2>
            <p className="text-sm text-white/60 mt-1">
              {t(
                'settings.squadTkJail.description',
                'Configure o sistema de aprisionamento automático para jogadores que eliminam companheiros do próprio esquadrão.'
              )}
            </p>
          </div>
          <label className="relative inline-flex items-center cursor-pointer flex-shrink-0">
            <input
              type="checkbox"
              checked={configData.enabled}
              onChange={() => handleToggle('enabled')}
              className="sr-only peer"
              disabled={saving}
            />
            <div className="w-11 h-6 bg-white/10 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-scum-orange"></div>
          </label>
        </div>

        <div className="space-y-6">
          {showGeneral && (
            <div className="bg-white/5 border border-white/10 rounded-xl p-4 sm:p-5 space-y-5">
              <h3 className="text-sm font-semibold text-white flex items-center gap-2 border-b border-white/5 pb-3">
                <Lock size={16} className="text-scum-orange" />
                {t('settings.squadTkJail.general.title', 'Configurações de Prisão')}
              </h3>

              <div className="flex flex-col md:flex-row gap-4 items-start">
                {/* Coordenadas */}
                <div className="flex-1 w-full space-y-1.5">
                  <label htmlFor="jail_coordinates" className="text-xs font-medium text-white/70 block h-5 flex items-center">
                    {t('settings.squadTkJail.coords', 'Coordenadas da Cela')}
                  </label>
                  <input
                    id="jail_coordinates"
                    type="text"
                    value={configData.jail_coordinates}
                    onChange={(e) => setConfigData(prev => ({ ...prev, jail_coordinates: e.target.value }))}
                    onBlur={(e) => setConfigData(prev => ({ ...prev, jail_coordinates: cleanScumCoordinates(e.target.value) }))}
                    className="w-full px-3 py-1.5 bg-white/5 border border-white/10 rounded-lg text-white text-sm focus:outline-none focus:ring-2 focus:ring-scum-orange focus:border-transparent font-mono"
                    placeholder="-271417.281 314246.875 84056.023"
                    disabled={saving}
                  />
                </div>

                {/* Raio Máximo */}
                <div className="space-y-1.5 w-full md:w-36 flex-shrink-0">
                  <label htmlFor="jail_radius_meters" className="text-xs font-medium text-white/70 block md:whitespace-nowrap h-5 flex items-center">
                    {t('settings.squadTkJail.radius', 'Raio Limite (metros)')}
                  </label>
                  <div className="flex items-center gap-1.5">
                    <input
                      id="jail_radius_meters"
                      type="number"
                      min="1"
                      max="9999"
                      value={configData.jail_radius_meters}
                      onChange={(e) => setConfigData(prev => ({ ...prev, jail_radius_meters: Math.max(1, Number(e.target.value)) }))}
                      className="w-full px-3 py-1.5 bg-white/5 border border-white/10 rounded-lg text-white text-sm focus:outline-none focus:ring-2 focus:ring-scum-orange focus:border-transparent text-center"
                      disabled={saving}
                    />
                    <span className="text-xs text-white/40">m</span>
                  </div>
                </div>

                {/* Duração */}
                <div className="space-y-1.5 w-full md:w-36 flex-shrink-0">
                  <label htmlFor="jail_duration_minutes" className="text-xs font-medium text-white/70 block md:whitespace-nowrap h-5 flex items-center">
                    {t('settings.squadTkJail.duration', 'Duração (minutos)')}
                  </label>
                  <div className="flex items-center gap-1.5">
                    <input
                      id="jail_duration_minutes"
                      type="number"
                      min="1"
                      max="9999"
                      value={configData.jail_duration_minutes}
                      onChange={(e) => setConfigData(prev => ({ ...prev, jail_duration_minutes: Math.max(1, Number(e.target.value)) }))}
                      className="w-full px-3 py-1.5 bg-white/5 border border-white/10 rounded-lg text-white text-sm focus:outline-none focus:ring-2 focus:ring-scum-orange focus:border-transparent text-center"
                      disabled={saving}
                    />
                    <span className="text-xs text-white/40">min</span>
                  </div>
                </div>
              </div>

              {/* Canal de cores */}
              <div className="pt-4 border-t border-white/5 space-y-4">
                <div className="flex items-center justify-between">
                  <div>
                    <span className="text-xs font-semibold text-white block">
                      {t('settings.squadTkJail.use_colors', 'Usar Cores Customizadas no Chat')}
                    </span>
                    <span className="text-[10px] text-white/40">
                      {t('settings.squadTkJail.use_colors_help', 'Envia avisos com a cor predefinida em vez do anúncio comum.')}
                    </span>
                  </div>
                  <label className="relative inline-flex items-center cursor-pointer">
                    <input
                      type="checkbox"
                      checked={configData.use_colors}
                      onChange={() => handleToggle('use_colors')}
                      className="sr-only peer"
                      disabled={saving}
                    />
                    <div className="w-11 h-6 bg-white/10 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-scum-orange"></div>
                  </label>
                </div>

                {configData.use_colors && (
                  <div className="space-y-2 pt-2 animate-fadeIn">
                    <label className="text-xs font-semibold text-white/70 block">
                      {t('settings.squadTkJail.warning_color', 'Cor do Aviso')}
                    </label>
                    <div className="flex flex-wrap gap-1.5">
                      {COLOR_PRESETS.map(c => (
                        <button
                          key={c.value}
                          type="button"
                          onClick={() => setConfigData(prev => ({ ...prev, warning_color: c.value }))}
                          disabled={saving}
                          className={`px-2.5 py-1 rounded-lg border text-[11px] transition-colors flex items-center gap-1.5 ${
                            configData.warning_color === c.value
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
                )}
              </div>
            </div>
          )}

          {showMessages && (
            <div className="bg-white/5 border border-white/10 rounded-xl p-4 sm:p-5 space-y-4">
              <h3 className="text-sm font-semibold text-white flex items-center gap-2 border-b border-white/5 pb-3">
                <Info size={16} className="text-scum-orange" />
                {t('settings.squadTkJail.messages.title', 'Mensagens do Servidor')}
              </h3>

              {/* Mensagem de Preso */}
              <div className="space-y-1.5">
                <div className="flex justify-between items-center">
                  <label htmlFor="announcement_message" className="text-xs font-medium text-white/70">
                    {t('settings.squadTkJail.messages.announcement', 'Mensagem de Anúncio de Prisão')}
                  </label>
                  <span className="text-[10px] text-white/40">Tags: {"{killer}"}, {"{victim}"}, {"{minutes}"}</span>
                </div>
                <input
                  id="announcement_message"
                  type="text"
                  value={configData.announcement_message}
                  onChange={(e) => setConfigData(prev => ({ ...prev, announcement_message: e.target.value }))}
                  className="w-full px-3 py-2 bg-white/5 border border-white/10 rounded-lg text-white text-sm focus:outline-none focus:ring-2 focus:ring-scum-orange focus:border-transparent"
                  disabled={saving}
                />
              </div>

              {/* Mensagem de Fuga */}
              <div className="space-y-1.5">
                <div className="flex justify-between items-center">
                  <label htmlFor="escape_message" className="text-xs font-medium text-white/70">
                    {t('settings.squadTkJail.messages.escape', 'Mensagem ao Tentar Escapar')}
                  </label>
                  <span className="text-[10px] text-white/40">Tags: {"{player}"}</span>
                </div>
                <input
                  id="escape_message"
                  type="text"
                  value={configData.escape_message}
                  onChange={(e) => setConfigData(prev => ({ ...prev, escape_message: e.target.value }))}
                  className="w-full px-3 py-2 bg-white/5 border border-white/10 rounded-lg text-white text-sm focus:outline-none focus:ring-2 focus:ring-scum-orange focus:border-transparent"
                  disabled={saving}
                />
              </div>

              {/* Mensagem de Solto */}
              <div className="space-y-1.5">
                <div className="flex justify-between items-center">
                  <label htmlFor="release_message" className="text-xs font-medium text-white/70">
                    {t('settings.squadTkJail.messages.release', 'Mensagem ao ser Libertado')}
                  </label>
                  <span className="text-[10px] text-white/40">Tags: {"{player}"}</span>
                </div>
                <input
                  id="release_message"
                  type="text"
                  value={configData.release_message}
                  onChange={(e) => setConfigData(prev => ({ ...prev, release_message: e.target.value }))}
                  className="w-full px-3 py-2 bg-white/5 border border-white/10 rounded-lg text-white text-sm focus:outline-none focus:ring-2 focus:ring-scum-orange focus:border-transparent"
                  disabled={saving}
                />
              </div>
            </div>
          )}
        </div>

        {/* Rodapé de Ações */}
        <div className="flex flex-col sm:flex-row gap-4 items-center justify-between pt-4 border-t border-white/10">
          <div className="flex items-center gap-2 text-white/50 text-xs">
            <AlertTriangle size={14} className="text-scum-orange animate-pulse flex-shrink-0" />
            <span>{t('settings.squadTkJail.footer_warning', 'As mudanças nas configurações se aplicam imediatamente nos próximos eventos do servidor.')}</span>
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
