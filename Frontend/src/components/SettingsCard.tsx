import React, { useState, useEffect } from 'react';
import { ChevronDown, ChevronRight, Settings, Clock, Shield, Database, Eye, Server, Bot, MessageCircle, Car, Wrench } from 'lucide-react';
import { scheduleService, ScheduledRestart } from '../services/scheduleService';
import { useLanguage } from '../contexts/LanguageContext';

interface SettingsCardProps {
  className?: string;
  hideSteamIds?: boolean;
  onHideSteamIdsChange?: (hide: boolean) => void;
}

interface SettingSection {
  id: string;
  title: string;
  icon: React.ComponentType<any>;
  component: React.ReactNode;
}

interface ServerConfig {
  serverPath?: string;
  steamCMDPath?: string;
  installPath?: string;
  batPath?: string;
  port?: number;
  maxPlayers?: number;
  useBattleye?: boolean;
  autoRestart?: boolean;
  restartInterval?: number;
  logLevel?: string;
  checkInterval?: number;
  discord_bot?: {
    enabled?: boolean;
    token?: string;
    guild_id?: string;
    webhook_key?: string;
    channels?: {
      vehicle_registration?: string;
      vehicle_mount_registration?: string;
      vehicle_denunciation?: string;
    };
    features?: {
      vehicle_registration?: {
        enabled?: boolean;
        command_prefix?: string;
        auto_register?: boolean;
        cooldown_seconds?: number;
        embed_color?: string;
      };
      vehicle_mount_registration?: {
        enabled?: boolean;
        command_prefix?: string;
        auto_register?: boolean;
        cooldown_seconds?: number;
        embed_color?: string;
      };
      vehicle_mount_complete?: {
        enabled?: boolean;
        command_prefix?: string;
        auto_register?: boolean;
        cooldown_seconds?: number;
        embed_color?: string;
      };
      vehicle_denunciation?: {
        enabled?: boolean;
        command_prefix?: string;
        cooldown_seconds?: number;
        required_roles?: string[];
        embed_color?: string;
      };
      user_linking?: {
        enabled?: boolean;
        expiration_hours?: number;
        max_linked_users?: number;
      };

    };
  };
}

const SettingsCard: React.FC<SettingsCardProps> = ({ className = '', hideSteamIds = false, onHideSteamIdsChange }) => {
  const { t } = useLanguage();
  const [expandedSections, setExpandedSections] = useState<string[]>(['restart']);
  const [schedules, setSchedules] = useState<ScheduledRestart | null>(null);
  const [selectedTime, setSelectedTime] = useState<string>('00:00');
  const [loading, setLoading] = useState(false);
  const [initialLoading, setInitialLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Estados para configuração do servidor
  const [serverConfig, setServerConfig] = useState<ServerConfig>({});
  const [configLoading, setConfigLoading] = useState(false);
  const [configSaving, setConfigSaving] = useState(false);
  const [configError, setConfigError] = useState<string | null>(null);

  // Buscar configuração do servidor
  const fetchServerConfig = async () => {
    setConfigLoading(true);
    try {
      const response = await fetch('/api/server/config');
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      const data = await response.json();
      if (data.success && data.config) {
        setServerConfig(data.config);
      }
    } catch (error) {
      console.error('Erro ao buscar configuração:', error);
      setConfigError('Erro ao carregar configurações do servidor');
    } finally {
      setConfigLoading(false);
    }
  };

  // Salvar configuração do servidor
  const saveServerConfig = async (newConfig: Partial<ServerConfig>) => {
    setConfigSaving(true);
    try {
      const response = await fetch('/api/server/config', {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(newConfig),
      });
      
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      
      const data = await response.json();
      if (data.success) {
        await fetchServerConfig(); // Recarregar configuração
        setConfigError(null);
      } else {
        setConfigError(data.message || 'Erro ao salvar configuração');
      }
    } catch (error) {
      console.error('Erro ao salvar configuração:', error);
      setConfigError('Erro ao salvar configurações do servidor');
    } finally {
      setConfigSaving(false);
    }
  };

  // Buscar horários configurados
  const fetchSchedules = async () => {
    try {
      setError(null);
      console.log('🔄 Iniciando busca de horários...');
      const response = await scheduleService.getSchedules();
      console.log('📡 Resposta do serviço:', response);
      
      if (response.success && response.schedules) {
        console.log('✅ Dados válidos recebidos:', response.schedules);
        setSchedules(response.schedules);
      } else {
        console.error('❌ Resposta inválida:', response);
        setError('Resposta inválida do servidor');
      }
    } catch (error) {
      console.error('❌ Erro ao buscar horários:', error);
      setError('Erro ao carregar configurações de restart');
    } finally {
      setInitialLoading(false);
    }
  };

  // Adicionar novo horário
  const addTime = async () => {
    if (schedules?.restartTimes.includes(selectedTime)) return;
    setLoading(true);
    try {
      const response = await scheduleService.addTime(selectedTime);
      if (response.success) {
        await fetchSchedules();
        setSelectedTime('00:00');
      }
    } catch (error) {
      setError('Erro ao adicionar horário');
    } finally {
      setLoading(false);
    }
  };

  // Remover horário
  const removeTime = async (time: string) => {
    try {
      const response = await scheduleService.removeTime(time);
      if (response.success) {
        await fetchSchedules();
      }
    } catch (error) {
      setError('Erro ao remover horário');
    }
  };

  // Ativar/Desativar sistema
  const toggleSystem = async (enabled: boolean) => {
    try {
      const response = await scheduleService.toggleSystem(enabled);
      if (response.success) {
        await fetchSchedules();
      }
    } catch (error) {
      setError('Erro ao alterar status do sistema');
    }
  };

  useEffect(() => {
    fetchSchedules();
    fetchServerConfig();
  }, []);

  const toggleSection = (sectionId: string) => {
    setExpandedSections(prev => 
      prev.includes(sectionId) 
        ? prev.filter(id => id !== sectionId)
        : [...prev, sectionId]
    );
  };

  const sections: SettingSection[] = [
    {
      id: 'restart',
              title: t('scheduled_restart'),
      icon: Clock,
      component: (
        <div className="p-4 bg-scum-dark/40 rounded border border-scum-accent/20">
          {initialLoading ? (
            <div className="text-center py-8">
              <div className="w-8 h-8 border-2 border-scum-accent border-t-transparent rounded-full animate-spin mx-auto mb-4"></div>
              <p className="text-scum-light">{t('loading_settings')}</p>
            </div>
          ) : error ? (
            <div className="text-scum-danger text-sm text-center">{error}</div>
          ) : (
            <div className="space-y-4">
              {/* Status do Sistema */}
              <div className="grid grid-cols-2 text-sm gap-4">
                <div>
                  <span className="text-scum-muted">{t('status')}:</span>
                  <span className={`ml-2 font-medium ${schedules?.enabled ? 'text-green-400' : 'text-red-400'}`}>
                    {schedules?.enabled ? t('system_active') : t('system_inactive')}
                  </span>
                </div>
                <div>
                  <span className="text-scum-muted">{t('configured_times')}:</span>
                  <span className="ml-2 font-medium text-scum-light">
                    {schedules?.restartTimes.length || 0}
                  </span>
                </div>
              </div>

              {/* Lista de Horários */}
              <div>
                <h4 className="text-sm font-semibold text-scum-accent mb-2">{t('configured_times')}</h4>
                <div className="flex flex-wrap gap-2">
                  {schedules?.restartTimes.length === 0 ? (
                    <span className="text-scum-muted text-sm">{t('no_time_configured')}</span>
                  ) : (
                    schedules?.restartTimes.map((time) => (
                      <div key={time} className="flex items-center gap-1 bg-scum-dark/40 px-2 py-1 rounded border border-scum-accent/20">
                        <span className="text-scum-light text-sm">{scheduleService.formatTimeForDisplay(time)}</span>
                        <button
                          onClick={() => removeTime(time)}
                          className="text-xs text-red-400 hover:text-red-600 focus:outline-none"
                          title={`Remover ${scheduleService.formatTimeForDisplay(time)}`}
                        >
                          ×
                        </button>
                      </div>
                    ))
                  )}
                </div>
              </div>

              {/* Controles */}
              <div className="space-y-3">
                <div className="flex items-center gap-3">
                  <div className="flex-1">
                    <label className="text-xs text-scum-muted block mb-1">{t('add_time')}</label>
                    <select
                      value={selectedTime}
                      onChange={(e) => setSelectedTime(e.target.value)}
                      className="w-full px-3 py-2 bg-scum-dark/50 border border-scum-accent/20 rounded text-scum-light focus:border-scum-accent focus:outline-none"
                    >
                      {scheduleService.getTimeOptions().map(time => (
                        <option key={time} value={time}>
                          {scheduleService.formatTimeForDisplay(time)}
                        </option>
                      ))}
                    </select>
                  </div>
                  
                  <button
                    onClick={addTime}
                    disabled={loading || schedules?.restartTimes.includes(selectedTime)}
                    className={`px-4 py-2 rounded font-medium transition-colors ${loading || schedules?.restartTimes.includes(selectedTime) ? 'bg-gray-600 text-gray-400 cursor-not-allowed' : 'bg-orange-500 hover:bg-orange-600 text-white'}`}
                    title={t('add_time')}
                  >
                    {loading ? t('adding') : t('add')}
                  </button>
                </div>

                {/* Toggle do Sistema */}
                <div className="flex items-center justify-between p-3 bg-scum-dark/40 rounded border border-scum-accent/20">
                  <div>
                    <span className="text-scum-light font-medium">{t('automatic_restart_system')}</span>
                    <p className="text-scum-muted text-xs">{t('activates_deactivates_scheduled_restart_system')}</p>
                  </div>
                  <button
                    onClick={() => toggleSystem(!schedules?.enabled)}
                    className={`px-4 py-2 rounded font-medium transition-colors ${schedules?.enabled ? 'bg-red-500 text-white' : 'bg-green-500 hover:bg-green-600 text-white'}`}
                  >
                    {schedules?.enabled ? t('deactivate') : t('activate')}
                  </button>
                </div>
              </div>
            </div>
          )}
        </div>
      )
    },
    {
      id: 'privacy',
              title: t('privacy'),
      icon: Eye,
      component: (
        <div className="p-4 bg-scum-dark/40 rounded border border-scum-accent/20">
          <div className="space-y-4">
            <div className="flex items-center justify-between p-3 bg-scum-dark/40 rounded border border-scum-accent/20">
              <div>
                <span className="text-scum-light font-medium">{t('hide_steam_ids')}</span>
                <p className="text-scum-muted text-xs">{t('hides_steam_ids_all_sections_videos_screenshots')}</p>
              </div>
              <label className="flex items-center gap-2 cursor-pointer">
                <input
                  type="checkbox"
                  checked={hideSteamIds}
                  onChange={(e) => onHideSteamIdsChange?.(e.target.checked)}
                  className="w-4 h-4 text-scum-accent bg-scum-dark border-scum-gray rounded focus:ring-scum-accent focus:ring-2"
                />
                <span className="text-sm text-scum-light">
                  🎥 {t('hide_steam_ids_for_videos')}
                </span>
              </label>
            </div>
          </div>
        </div>
      )
    },
    {
      id: 'security',
              title: t('scum_server_manager_configuration'),
      icon: Shield,
      component: (
        <div className="p-4 bg-scum-dark/40 rounded border border-scum-accent/20">
          {configLoading ? (
            <div className="text-center py-8">
              <div className="w-8 h-8 border-2 border-scum-accent border-t-transparent rounded-full animate-spin mx-auto mb-4"></div>
              <p className="text-scum-light">{t('loading_server_settings')}</p>
            </div>
          ) : configError ? (
            <div className="text-red-400 text-sm text-center mb-4">{configError}</div>
          ) : (
            <div className="space-y-6">
              {/* Configurações do Servidor */}
              <div>
                <h4 className="text-sm font-semibold text-scum-accent mb-3 flex items-center gap-2">
                  <Server className="w-4 h-4" />
                  {t('server_settings')}
                </h4>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div>
                    <label className="text-xs text-scum-muted block mb-1">{t('server_port')}</label>
                    <input
                      type="number"
                      value={serverConfig.port || ''}
                      onChange={(e) => setServerConfig(prev => ({ ...prev, port: parseInt(e.target.value) || 0 }))}
                      className="w-full px-3 py-2 bg-scum-dark/50 border border-scum-accent/20 rounded text-scum-light focus:border-scum-accent focus:outline-none"
                      placeholder="8900"
                      min="1"
                      max="65535"
                    />
                  </div>
                  <div>
                    <label className="text-xs text-scum-muted block mb-1">{t('max_players')}</label>
                    <input
                      type="number"
                      value={serverConfig.maxPlayers || ''}
                      onChange={(e) => setServerConfig(prev => ({ ...prev, maxPlayers: parseInt(e.target.value) || 0 }))}
                      className="w-full px-3 py-2 bg-scum-dark/50 border border-scum-accent/20 rounded text-scum-light focus:border-scum-accent focus:outline-none"
                      placeholder="64"
                      min="1"
                      max="100"
                    />
                  </div>
                  <div className="md:col-span-2">
                    <label className="flex items-center gap-2 cursor-pointer">
                      <input
                        type="checkbox"
                        checked={serverConfig.useBattleye || false}
                        onChange={(e) => setServerConfig(prev => ({ ...prev, useBattleye: e.target.checked }))}
                        className="w-4 h-4 text-scum-accent bg-scum-dark border-scum-gray rounded focus:ring-scum-accent focus:ring-2"
                      />
                      <span className="text-sm text-scum-light">{t('use_battleye')}</span>
                    </label>
                  </div>
                </div>
              </div>

              {/* Configurações do Bot Discord */}
              <div>
                <h4 className="text-sm font-semibold text-scum-accent mb-3 flex items-center gap-2">
                  <Bot className="w-4 h-4" />
                  {t('discord_bot')}
                </h4>
                <div className="space-y-4">
                  <div className="flex items-center justify-between p-3 bg-scum-dark/40 rounded border border-scum-accent/20">
                    <div>
                                          <span className="text-scum-light font-medium">{t('discord_bot')}</span>
                    <p className="text-scum-muted text-xs">{t('activates_deactivates_discord_bot')}</p>
                    </div>
                    <label className="flex items-center gap-2 cursor-pointer">
                      <input
                        type="checkbox"
                        checked={serverConfig.discord_bot?.enabled || false}
                        onChange={(e) => setServerConfig(prev => ({
                          ...prev,
                          discord_bot: { ...prev.discord_bot, enabled: e.target.checked }
                        }))}
                        className="w-4 h-4 text-scum-accent bg-scum-dark border-scum-gray rounded focus:ring-scum-accent focus:ring-2"
                      />
                                              <span className="text-sm text-scum-light">{t('active')}</span>
                    </label>
                  </div>

                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div>
                      <label className="text-xs text-scum-muted block mb-1">{t('bot_token')}</label>
                      <input
                        type="password"
                        value={serverConfig.discord_bot?.token || ''}
                        onChange={(e) => setServerConfig(prev => ({
                          ...prev,
                          discord_bot: { ...prev.discord_bot, token: e.target.value }
                        }))}
                        className="w-full px-3 py-2 bg-scum-dark/50 border border-scum-accent/20 rounded text-scum-light focus:border-scum-accent focus:outline-none"
                        placeholder="Token do bot Discord"
                      />
                    </div>
                    <div>
                      <label className="text-xs text-scum-muted block mb-1">{t('discord_server_id')}</label>
                      <input
                        type="text"
                        value={serverConfig.discord_bot?.guild_id || ''}
                        onChange={(e) => setServerConfig(prev => ({
                          ...prev,
                          discord_bot: { ...prev.discord_bot, guild_id: e.target.value }
                        }))}
                        className="w-full px-3 py-2 bg-scum-dark/50 border border-scum-accent/20 rounded text-scum-light focus:border-scum-accent focus:outline-none"
                        placeholder="ID do servidor Discord"
                      />
                    </div>
                  </div>

                  {/* Canais do Discord */}
                  <div>
                    <h5 className="text-xs font-semibold text-scum-accent mb-2 flex items-center gap-2">
                      <MessageCircle className="w-3 h-3" />
                      {t('discord_channels')}
                    </h5>
                    <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                      <div>
                        <label className="text-xs text-scum-muted block mb-1">{t('vehicle_channel')}</label>
                        <input
                          type="text"
                          value={serverConfig.discord_bot?.channels?.vehicle_registration || ''}
                          onChange={(e) => setServerConfig(prev => ({
                            ...prev,
                            discord_bot: {
                              ...prev.discord_bot,
                              channels: { ...prev.discord_bot?.channels, vehicle_registration: e.target.value }
                            }
                          }))}
                          className="w-full px-3 py-2 bg-scum-dark/50 border border-scum-accent/20 rounded text-scum-light focus:border-scum-accent focus:outline-none"
                          placeholder="ID do canal de veículos"
                        />
                      </div>
                      <div>
                        <label className="text-xs text-scum-muted block mb-1">{t('mount_channel')}</label>
                        <input
                          type="text"
                          value={serverConfig.discord_bot?.channels?.vehicle_mount_registration || ''}
                          onChange={(e) => setServerConfig(prev => ({
                            ...prev,
                            discord_bot: {
                              ...prev.discord_bot,
                              channels: { ...prev.discord_bot?.channels, vehicle_mount_registration: e.target.value }
                            }
                          }))}
                          className="w-full px-3 py-2 bg-scum-dark/50 border border-scum-accent/20 rounded text-scum-light focus:border-scum-accent focus:outline-none"
                          placeholder="ID do canal de montagem"
                        />
                      </div>
                      <div>
                        <label className="text-xs text-scum-muted block mb-1">{t('denunciation_channel')}</label>
                        <input
                          type="text"
                          value={serverConfig.discord_bot?.channels?.vehicle_denunciation || ''}
                          onChange={(e) => setServerConfig(prev => ({
                            ...prev,
                            discord_bot: {
                              ...prev.discord_bot,
                              channels: { ...prev.discord_bot?.channels, vehicle_denunciation: e.target.value }
                            }
                          }))}
                          className="w-full px-3 py-2 bg-scum-dark/50 border border-scum-accent/20 rounded text-scum-light focus:border-scum-accent focus:outline-none"
                          placeholder="ID do canal de denúncias"
                        />
                      </div>
                    </div>
                  </div>

                  {/* Comandos do Discord */}
                  <div>
                    <h5 className="text-xs font-semibold text-scum-accent mb-2 flex items-center gap-2">
                      <Wrench className="w-3 h-3" />
                      {t('discord_commands')}
                    </h5>
                    <div className="space-y-3">
                      {/* Comando /rv */}
                      <div className="p-3 bg-scum-dark/40 rounded border border-scum-accent/20">
                        <div className="flex items-center justify-between mb-2">
                          <span className="text-sm font-medium text-scum-light">{t('vehicle_registration')}</span>
                          <label className="flex items-center gap-2 cursor-pointer">
                            <input
                              type="checkbox"
                              checked={serverConfig.discord_bot?.features?.vehicle_registration?.enabled || false}
                              onChange={(e) => setServerConfig(prev => ({
                                ...prev,
                                discord_bot: {
                                  ...prev.discord_bot,
                                  features: {
                                    ...prev.discord_bot?.features,
                                    vehicle_registration: {
                                      ...prev.discord_bot?.features?.vehicle_registration,
                                      enabled: e.target.checked
                                    }
                                  }
                                }
                              }))}
                              className="w-4 h-4 text-scum-accent bg-scum-dark border-scum-gray rounded focus:ring-scum-accent focus:ring-2"
                            />
                            <span className="text-xs text-scum-light">Ativo</span>
                          </label>
                        </div>
                        <div className="grid grid-cols-2 gap-2">
                          <div>
                            <label className="text-xs text-scum-muted block mb-1">Cooldown (segundos)</label>
                            <input
                              type="number"
                              value={serverConfig.discord_bot?.features?.vehicle_registration?.cooldown_seconds || 30}
                              onChange={(e) => setServerConfig(prev => ({
                                ...prev,
                                discord_bot: {
                                  ...prev.discord_bot,
                                  features: {
                                    ...prev.discord_bot?.features,
                                    vehicle_registration: {
                                      ...prev.discord_bot?.features?.vehicle_registration,
                                      cooldown_seconds: parseInt(e.target.value) || 30
                                    }
                                  }
                                }
                              }))}
                              className="w-full px-2 py-1 bg-scum-dark/50 border border-scum-accent/20 rounded text-scum-light focus:border-scum-accent focus:outline-none text-xs"
                              min="1"
                              max="300"
                            />
                          </div>
                          <div>
                            <label className="text-xs text-scum-muted block mb-1">Cor do Embed</label>
                            <input
                              type="color"
                              value={serverConfig.discord_bot?.features?.vehicle_registration?.embed_color || '#00ff00'}
                              onChange={(e) => setServerConfig(prev => ({
                                ...prev,
                                discord_bot: {
                                  ...prev.discord_bot,
                                  features: {
                                    ...prev.discord_bot?.features,
                                    vehicle_registration: {
                                      ...prev.discord_bot?.features?.vehicle_registration,
                                      embed_color: e.target.value
                                    }
                                  }
                                }
                              }))}
                              className="w-full h-8 bg-scum-dark/50 border border-scum-accent/20 rounded focus:border-scum-accent focus:outline-none"
                            />
                          </div>
                        </div>
                      </div>

                      {/* Comando /rm */}
                      <div className="p-3 bg-scum-dark/40 rounded border border-scum-accent/20">
                        <div className="flex items-center justify-between mb-2">
                          <span className="text-sm font-medium text-scum-light">{t('mount_registration')}</span>
                          <label className="flex items-center gap-2 cursor-pointer">
                            <input
                              type="checkbox"
                              checked={serverConfig.discord_bot?.features?.vehicle_mount_registration?.enabled || false}
                              onChange={(e) => setServerConfig(prev => ({
                                ...prev,
                                discord_bot: {
                                  ...prev.discord_bot,
                                  features: {
                                    ...prev.discord_bot?.features,
                                    vehicle_mount_registration: {
                                      ...prev.discord_bot?.features?.vehicle_mount_registration,
                                      enabled: e.target.checked
                                    }
                                  }
                                }
                              }))}
                              className="w-4 h-4 text-scum-accent bg-scum-dark border-scum-gray rounded focus:ring-scum-accent focus:ring-2"
                            />
                            <span className="text-xs text-scum-light">Ativo</span>
                          </label>
                        </div>
                        <div className="grid grid-cols-2 gap-2">
                          <div>
                            <label className="text-xs text-scum-muted block mb-1">Cooldown (segundos)</label>
                            <input
                              type="number"
                              value={serverConfig.discord_bot?.features?.vehicle_mount_registration?.cooldown_seconds || 30}
                              onChange={(e) => setServerConfig(prev => ({
                                ...prev,
                                discord_bot: {
                                  ...prev.discord_bot,
                                  features: {
                                    ...prev.discord_bot?.features,
                                    vehicle_mount_registration: {
                                      ...prev.discord_bot?.features?.vehicle_mount_registration,
                                      cooldown_seconds: parseInt(e.target.value) || 30
                                    }
                                  }
                                }
                              }))}
                              className="w-full px-2 py-1 bg-scum-dark/50 border border-scum-accent/20 rounded text-scum-light focus:border-scum-accent focus:outline-none text-xs"
                              min="1"
                              max="300"
                            />
                          </div>
                          <div>
                            <label className="text-xs text-scum-muted block mb-1">Cor do Embed</label>
                            <input
                              type="color"
                              value={serverConfig.discord_bot?.features?.vehicle_mount_registration?.embed_color || '#ff8800'}
                              onChange={(e) => setServerConfig(prev => ({
                                ...prev,
                                discord_bot: {
                                  ...prev.discord_bot,
                                  features: {
                                    ...prev.discord_bot?.features,
                                    vehicle_mount_registration: {
                                      ...prev.discord_bot?.features?.vehicle_mount_registration,
                                      embed_color: e.target.value
                                    }
                                  }
                                }
                              }))}
                              className="w-full h-8 bg-scum-dark/50 border border-scum-accent/20 rounded focus:border-scum-accent focus:outline-none"
                            />
                          </div>
                        </div>
                      </div>

                      {/* Comando /mc */}
                      <div className="p-3 bg-scum-dark/40 rounded border border-scum-accent/20">
                        <div className="flex items-center justify-between mb-2">
                          <span className="text-sm font-medium text-scum-light">{t('mount_complete')}</span>
                          <label className="flex items-center gap-2 cursor-pointer">
                            <input
                              type="checkbox"
                              checked={serverConfig.discord_bot?.features?.vehicle_mount_complete?.enabled || false}
                              onChange={(e) => setServerConfig(prev => ({
                                ...prev,
                                discord_bot: {
                                  ...prev.discord_bot,
                                  features: {
                                    ...prev.discord_bot?.features,
                                    vehicle_mount_complete: {
                                      ...prev.discord_bot?.features?.vehicle_mount_complete,
                                      enabled: e.target.checked
                                    }
                                  }
                                }
                              }))}
                              className="w-4 h-4 text-scum-accent bg-scum-dark border-scum-gray rounded focus:ring-scum-accent focus:ring-2"
                            />
                            <span className="text-xs text-scum-light">Ativo</span>
                          </label>
                        </div>
                        <div className="grid grid-cols-2 gap-2">
                          <div>
                            <label className="text-xs text-scum-muted block mb-1">Cooldown (segundos)</label>
                            <input
                              type="number"
                              value={serverConfig.discord_bot?.features?.vehicle_mount_complete?.cooldown_seconds || 30}
                              onChange={(e) => setServerConfig(prev => ({
                                ...prev,
                                discord_bot: {
                                  ...prev.discord_bot,
                                  features: {
                                    ...prev.discord_bot?.features,
                                    vehicle_mount_complete: {
                                      ...prev.discord_bot?.features?.vehicle_mount_complete,
                                      cooldown_seconds: parseInt(e.target.value) || 30
                                    }
                                  }
                                }
                              }))}
                              className="w-full px-2 py-1 bg-scum-dark/50 border border-scum-accent/20 rounded text-scum-light focus:border-scum-accent focus:outline-none text-xs"
                              min="1"
                              max="300"
                            />
                          </div>
                          <div>
                            <label className="text-xs text-scum-muted block mb-1">Cor do Embed</label>
                            <input
                              type="color"
                              value={serverConfig.discord_bot?.features?.vehicle_mount_complete?.embed_color || '#00ff88'}
                              onChange={(e) => setServerConfig(prev => ({
                                ...prev,
                                discord_bot: {
                                  ...prev.discord_bot,
                                  features: {
                                    ...prev.discord_bot?.features,
                                    vehicle_mount_complete: {
                                      ...prev.discord_bot?.features?.vehicle_mount_complete,
                                      embed_color: e.target.value
                                    }
                                  }
                                }
                              }))}
                              className="w-full h-8 bg-scum-dark/50 border border-scum-accent/20 rounded focus:border-scum-accent focus:outline-none"
                            />
                          </div>
                        </div>
                      </div>

                      {/* Comando /dv */}
                      <div className="p-3 bg-scum-dark/40 rounded border border-scum-accent/20">
                        <div className="flex items-center justify-between mb-2">
                          <span className="text-sm font-medium text-scum-light">{t('vehicle_denunciation')}</span>
                          <label className="flex items-center gap-2 cursor-pointer">
                            <input
                              type="checkbox"
                              checked={serverConfig.discord_bot?.features?.vehicle_denunciation?.enabled || false}
                              onChange={(e) => setServerConfig(prev => ({
                                ...prev,
                                discord_bot: {
                                  ...prev.discord_bot,
                                  features: {
                                    ...prev.discord_bot?.features,
                                    vehicle_denunciation: {
                                      ...prev.discord_bot?.features?.vehicle_denunciation,
                                      enabled: e.target.checked
                                    }
                                  }
                                }
                              }))}
                              className="w-4 h-4 text-scum-accent bg-scum-dark border-scum-gray rounded focus:ring-scum-accent focus:ring-2"
                            />
                            <span className="text-xs text-scum-light">Ativo</span>
                          </label>
                        </div>
                        <div className="grid grid-cols-2 gap-2">
                          <div>
                            <label className="text-xs text-scum-muted block mb-1">Cooldown (segundos)</label>
                            <input
                              type="number"
                              value={serverConfig.discord_bot?.features?.vehicle_denunciation?.cooldown_seconds || 60}
                              onChange={(e) => setServerConfig(prev => ({
                                ...prev,
                                discord_bot: {
                                  ...prev.discord_bot,
                                  features: {
                                    ...prev.discord_bot?.features,
                                    vehicle_denunciation: {
                                      ...prev.discord_bot?.features?.vehicle_denunciation,
                                      cooldown_seconds: parseInt(e.target.value) || 60
                                    }
                                  }
                                }
                              }))}
                              className="w-full px-2 py-1 bg-scum-dark/50 border border-scum-accent/20 rounded text-scum-light focus:border-scum-accent focus:outline-none text-xs"
                              min="1"
                              max="300"
                            />
                          </div>
                          <div>
                            <label className="text-xs text-scum-muted block mb-1">Cor do Embed</label>
                            <input
                              type="color"
                              value={serverConfig.discord_bot?.features?.vehicle_denunciation?.embed_color || '#ff0000'}
                              onChange={(e) => setServerConfig(prev => ({
                                ...prev,
                                discord_bot: {
                                  ...prev.discord_bot,
                                  features: {
                                    ...prev.discord_bot?.features,
                                    vehicle_denunciation: {
                                      ...prev.discord_bot?.features?.vehicle_denunciation,
                                      embed_color: e.target.value
                                    }
                                  }
                                }
                              }))}
                              className="w-full h-8 bg-scum-dark/50 border border-scum-accent/20 rounded focus:border-scum-accent focus:outline-none"
                            />
                          </div>
                        </div>
                        <div className="mt-2">
                          <label className="text-xs text-scum-muted block mb-1">Cargos Necessários (separados por vírgula)</label>
                          <input
                            type="text"
                            value={serverConfig.discord_bot?.features?.vehicle_denunciation?.required_roles?.join(', ') || ''}
                            onChange={(e) => setServerConfig(prev => ({
                              ...prev,
                              discord_bot: {
                                ...prev.discord_bot,
                                features: {
                                  ...prev.discord_bot?.features,
                                  vehicle_denunciation: {
                                    ...prev.discord_bot?.features?.vehicle_denunciation,
                                    required_roles: e.target.value.split(',').map(role => role.trim()).filter(role => role)
                                  }
                                }
                              }
                            }))}
                            className="w-full px-2 py-1 bg-scum-dark/50 border border-scum-accent/20 rounded text-scum-light focus:border-scum-accent focus:outline-none text-xs"
                            placeholder="Staff, Adm, Moderador"
                          />
                        </div>
                      </div>
                    </div>

                    {/* Configurações de Vinculação */}
                    <div>
                      <h5 className="text-xs font-semibold text-scum-accent mb-2 flex items-center gap-2">
                        <Shield className="w-3 h-3" />
                        {t('user_linking')}
                      </h5>
                      <div className="p-3 bg-scum-dark/40 rounded border border-scum-accent/20">
                        <div className="flex items-center justify-between mb-2">
                          <span className="text-sm font-medium text-scum-light">Sistema de Vinculação</span>
                          <label className="flex items-center gap-2 cursor-pointer">
                            <input
                              type="checkbox"
                              checked={serverConfig.discord_bot?.features?.user_linking?.enabled || false}
                              onChange={(e) => setServerConfig(prev => ({
                                ...prev,
                                discord_bot: {
                                  ...prev.discord_bot,
                                  features: {
                                    ...prev.discord_bot?.features,
                                    user_linking: {
                                      ...prev.discord_bot?.features?.user_linking,
                                      enabled: e.target.checked
                                    }
                                  }
                                }
                              }))}
                              className="w-4 h-4 text-scum-accent bg-scum-dark border-scum-gray rounded focus:ring-scum-accent focus:ring-2"
                            />
                            <span className="text-xs text-scum-light">Ativo</span>
                          </label>
                        </div>
                        <div className="grid grid-cols-2 gap-2">
                          <div>
                            <label className="text-xs text-scum-muted block mb-1">{t('expiration_hours')}</label>
                            <input
                              type="number"
                              value={serverConfig.discord_bot?.features?.user_linking?.expiration_hours || 24}
                              onChange={(e) => setServerConfig(prev => ({
                                ...prev,
                                discord_bot: {
                                  ...prev.discord_bot,
                                  features: {
                                    ...prev.discord_bot?.features,
                                    user_linking: {
                                      ...prev.discord_bot?.features?.user_linking,
                                      expiration_hours: parseInt(e.target.value) || 24
                                    }
                                  }
                                }
                              }))}
                              className="w-full px-2 py-1 bg-scum-dark/50 border border-scum-accent/20 rounded text-scum-light focus:border-scum-accent focus:outline-none text-xs"
                              min="1"
                              max="168"
                            />
                          </div>
                          <div>
                            <label className="text-xs text-scum-muted block mb-1">{t('max_linked_users')}</label>
                            <input
                              type="number"
                              value={serverConfig.discord_bot?.features?.user_linking?.max_linked_users || 100}
                              onChange={(e) => setServerConfig(prev => ({
                                ...prev,
                                discord_bot: {
                                  ...prev.discord_bot,
                                  features: {
                                    ...prev.discord_bot?.features,
                                    user_linking: {
                                      ...prev.discord_bot?.features?.user_linking,
                                      max_linked_users: parseInt(e.target.value) || 100
                                    }
                                  }
                                }
                              }))}
                              className="w-full px-2 py-1 bg-scum-dark/50 border border-scum-accent/20 rounded text-scum-light focus:border-scum-accent focus:outline-none text-xs"
                              min="1"
                              max="1000"
                            />
                          </div>
                        </div>
                      </div>
                    </div>


                  </div>
                </div>
              </div>

              {/* Botões de Ação */}
              <div className="flex gap-3 pt-4 border-t border-scum-accent/20">
                <button
                  onClick={() => saveServerConfig(serverConfig)}
                  disabled={configSaving}
                  className={`flex-1 px-4 py-2 rounded font-medium transition-colors ${
                    configSaving 
                      ? 'bg-gray-600 text-gray-400 cursor-not-allowed' 
                      : 'bg-green-600 hover:bg-green-700 text-white'
                  }`}
                >
                                      {configSaving ? t('saving') : t('save_settings')}
                </button>
                <button
                  onClick={fetchServerConfig}
                  disabled={configLoading}
                  className={`px-4 py-2 rounded font-medium transition-colors ${
                    configLoading 
                      ? 'bg-gray-600 text-gray-400 cursor-not-allowed' 
                      : 'bg-blue-600 hover:bg-blue-700 text-white'
                  }`}
                >
                                      {configLoading ? t('loading') : t('reload')}
                </button>
              </div>
            </div>
          )}
        </div>
      )
    },
    {
      id: 'database',
              title: t('database'),
      icon: Database,
      component: (
        <div className="p-4 bg-scum-dark/40 rounded border border-scum-accent/20">
          <p className="text-scum-muted text-sm">Configurações de banco de dados em desenvolvimento...</p>
        </div>
      )
    }
  ];

  return (
    <div className={`bg-scum-dark/60 rounded-lg border border-scum-accent/20 p-6 ${className}`}>
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <h3 className="text-lg font-bold text-scum-light flex items-center">
          <Settings className="w-5 h-5 mr-3 text-scum-accent" />
          {t('system_settings')}
        </h3>
      </div>

      {/* Seções Colapsáveis */}
      <div className="space-y-3">
        {sections.map((section) => {
          const IconComponent = section.icon;
          const isExpanded = expandedSections.includes(section.id);
          
          return (
            <div key={section.id} className="border border-scum-accent/20 rounded-lg overflow-hidden">
              {/* Cabeçalho da Seção */}
              <button
                onClick={() => toggleSection(section.id)}
                className="w-full flex items-center justify-between p-4 bg-scum-dark/40 hover:bg-scum-dark/60 transition-colors"
              >
                <div className="flex items-center gap-3">
                  <IconComponent className="w-5 h-5 text-scum-accent" />
                  <span className="text-scum-light font-medium">{section.title}</span>
                </div>
                {isExpanded ? (
                  <ChevronDown className="w-5 h-5 text-scum-accent" />
                ) : (
                  <ChevronRight className="w-5 h-5 text-scum-accent" />
                )}
              </button>

              {/* Conteúdo da Seção */}
              {isExpanded && (
                <div className="border-t border-scum-accent/20">
                  {section.component}
                </div>
              )}
            </div>
          );
        })}
      </div>

      {/* Informações Gerais */}
      <div className="mt-6 p-4 bg-scum-dark/40 rounded border border-scum-accent/20">
        <h5 className="text-sm font-semibold text-scum-accent mb-2">Informações</h5>
        <ul className="text-xs text-scum-muted space-y-1">
          <li>• Clique nas seções para expandir/colapsar</li>
          <li>• As configurações são salvas automaticamente</li>
          <li>• Algumas alterações podem requerer reinicialização</li>
        </ul>
      </div>
    </div>
  );
};

export default SettingsCard; 