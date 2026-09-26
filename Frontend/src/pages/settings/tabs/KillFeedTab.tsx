import { useState, useEffect, useRef } from 'react';
import { useTranslation } from 'react-i18next';
import { Loader2, Save, RefreshCw, AlertTriangle, ShieldAlert, Info, Plus, Trash2, Edit2, Check, X } from 'lucide-react';
import Swal from 'sweetalert2';
import { getConfig, updateConfigSection, getKillFeedPhrases, updateKillFeedPhrases } from '@/services/config';

interface KillFeedTabProps {
  searchQuery?: string;
  onSearchChange?: (query: string) => void;
}

interface KillFeedConfig {
  enabled: boolean;
  mode: string;
  chat_type: number;
  message_template: string;
  priority: number;
  phrases_path?: string;
}

const CHAT_TYPES = [
  { id: 2, nameKey: 'settings.killFeed.channels.global.name', nameDefault: 'Chat Global', colorBg: 'bg-sky-500', colorText: 'text-sky-400', descKey: 'settings.killFeed.channels.global.desc', descDefault: 'Canal padrão exibido para todos' },
  { id: 4, nameKey: 'settings.killFeed.channels.admin.name', nameDefault: 'Admin / Anúncio', colorBg: 'bg-yellow-500', colorText: 'text-yellow-400', descKey: 'settings.killFeed.channels.admin.desc', descDefault: 'Destaque amarelo para avisos rápidos' },
  { id: 6, nameKey: 'settings.killFeed.channels.server.name', nameDefault: 'Mensagem do Servidor', colorBg: 'bg-orange-500', colorText: 'text-orange-400', descKey: 'settings.killFeed.channels.server.desc', descDefault: 'Mensagem cinza/laranja do sistema' },
  { id: 7, nameKey: 'settings.killFeed.channels.alert.name', nameDefault: 'Alerta / Erro', colorBg: 'bg-red-500', colorText: 'text-red-400', descKey: 'settings.killFeed.channels.alert.desc', descDefault: 'Canal de alerta vermelho chamativo' },
  { id: 0, nameKey: 'settings.killFeed.channels.local.name', nameDefault: 'Chat Local / Padrão', colorBg: 'bg-white', colorText: 'text-white/90', descKey: 'settings.killFeed.channels.local.desc', descDefault: 'Branco padrão do jogo' },
  { id: 3, nameKey: 'settings.killFeed.channels.squad.name', nameDefault: 'Chat de Squad', colorBg: 'bg-green-500', colorText: 'text-green-400', descKey: 'settings.killFeed.channels.squad.desc', descDefault: 'Visível apenas para membros do grupo' },
];

export default function KillFeedTab({ searchQuery = '' }: KillFeedTabProps) {
  const { t } = useTranslation();
  const inputRef = useRef<HTMLInputElement>(null);

  const [configData, setConfigData] = useState<KillFeedConfig>({
    enabled: false,
    mode: 'chat',
    chat_type: 2,
    message_template: '{killer} matou {victim} ({weapon} - {distance}m) | {phrase}',
    priority: 15,
  });

  const [originalConfigData, setOriginalConfigData] = useState<KillFeedConfig>({
    enabled: false,
    mode: 'chat',
    chat_type: 2,
    message_template: '{killer} matou {victim} ({weapon} - {distance}m) | {phrase}',
    priority: 15,
  });

  const [phrases, setPhrases] = useState<string[]>([]);
  const [originalPhrases, setOriginalPhrases] = useState<string[]>([]);
  const [newPhrase, setNewPhrase] = useState('');
  const [editingIndex, setEditingIndex] = useState<number | null>(null);
  const [editingValue, setEditingValue] = useState('');

  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [showRestartWarning, setShowRestartWarning] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const loadData = async () => {
    setLoading(true);
    setError(null);
    try {
      const configRes = await getConfig('kill_feed');
      const phrasesRes = await getKillFeedPhrases();

      if (configRes.success && configRes.data?.kill_feed) {
        const data = configRes.data.kill_feed;
        const loadedConfig: KillFeedConfig = {
          enabled: data.enabled === true,
          mode: String(data.mode ?? 'chat'),
          chat_type: Number(data.chat_type ?? 2),
          message_template: String(data.message_template ?? '{killer} matou {victim} ({weapon} - {distance}m) | {phrase}'),
          priority: Number(data.priority ?? 15),
          phrases_path: data.phrases_path,
        };
        setConfigData(loadedConfig);
        setOriginalConfigData(loadedConfig);
      } else {
        throw new Error(configRes.error || 'Erro ao carregar configurações do Kill Feed');
      }

      if (phrasesRes.success && Array.isArray(phrasesRes.data)) {
        setPhrases(phrasesRes.data);
        setOriginalPhrases(phrasesRes.data);
      } else {
        throw new Error(phrasesRes.error || 'Erro ao carregar a lista de frases');
      }
    } catch (err: any) {
      setError(err.message || 'Erro ao carregar dados do Kill Feed');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const handleToggleEnabled = () => {
    setConfigData(prev => ({ ...prev, enabled: !prev.enabled }));
  };

  const handleChatTypeSelect = (id: number) => {
    setConfigData(prev => ({ ...prev, chat_type: id }));
  };

  const insertTag = (tag: string) => {
    const input = inputRef.current;
    if (!input) return;
    const start = input.selectionStart ?? 0;
    const end = input.selectionEnd ?? 0;
    const text = configData.message_template;
    const before = text.substring(0, start);
    const after = text.substring(end, text.length);
    const newText = before + tag + after;

    setConfigData(prev => ({
      ...prev,
      message_template: newText,
    }));

    setTimeout(() => {
      input.focus();
      const newCursorPos = start + tag.length;
      input.setSelectionRange(newCursorPos, newCursorPos);
    }, 0);
  };

  const handleAddPhrase = () => {
    const trimmed = newPhrase.trim();
    if (!trimmed) return;
    if (phrases.includes(trimmed)) {
      Swal.fire({
        icon: 'warning',
        title: t('settings.killFeed.phrases.duplicate_title', 'Duplicate Phrase'),
        text: t('settings.killFeed.phrases.duplicate_text', 'This phrase already exists in the list.'),
        confirmButtonColor: '#f97316',
      });
      return;
    }
    setPhrases(prev => [...prev, trimmed]);
    setNewPhrase('');
  };

  const handleDeletePhrase = (index: number) => {
    setPhrases(prev => prev.filter((_, idx) => idx !== index));
  };

  const handleStartEdit = (index: number) => {
    setEditingIndex(index);
    setEditingValue(phrases[index]);
  };

  const handleSaveEdit = () => {
    const trimmed = editingValue.trim();
    if (!trimmed) return;
    if (phrases.includes(trimmed) && phrases[editingIndex!] !== trimmed) {
      Swal.fire({
        icon: 'warning',
        title: t('settings.killFeed.phrases.duplicate_title', 'Duplicate Phrase'),
        text: t('settings.killFeed.phrases.duplicate_text', 'This phrase already exists in the list.'),
        confirmButtonColor: '#f97316',
      });
      return;
    }
    setPhrases(prev => prev.map((p, idx) => (idx === editingIndex ? trimmed : p)));
    setEditingIndex(null);
    setEditingValue('');
  };

  const handleSave = async () => {
    setSaving(true);
    try {
      const configPayload = {
        enabled: configData.enabled,
        mode: configData.mode,
        chat_type: configData.chat_type,
        message_template: configData.message_template,
        priority: configData.priority,
      };
      
      const configRes = await updateConfigSection('kill_feed', configPayload, true);
      if (!configRes.success) {
        throw new Error(configRes.error || 'Falha ao salvar configurações do Kill Feed');
      }

      const phrasesRes = await updateKillFeedPhrases(phrases);
      if (!phrasesRes.success) {
        throw new Error(phrasesRes.error || 'Falha ao salvar lista de frases');
      }

      setOriginalConfigData(configData);
      setOriginalPhrases(phrases);
      setShowRestartWarning(true);

      await Swal.fire({
        icon: 'success',
        title: t('settings.killFeed.save_success', 'Kill Feed settings saved successfully!'),
        text: t('settings.killFeed.save_success_details', 'Kill Feed settings and phrases list have been successfully saved.'),
        confirmButtonColor: '#f97316',
      });
    } catch (err: any) {
      Swal.fire({
        icon: 'error',
        title: t('settings.errors.saveFailed', 'Save failed'),
        text: err.message || 'Error occurred while saving.',
        confirmButtonColor: '#f97316',
      });
    } finally {
      setSaving(false);
    }
  };



  const hasChanges =
    configData.enabled !== originalConfigData.enabled ||
    configData.mode !== originalConfigData.mode ||
    configData.chat_type !== originalConfigData.chat_type ||
    configData.message_template !== originalConfigData.message_template ||
    configData.priority !== originalConfigData.priority ||
    JSON.stringify(phrases) !== JSON.stringify(originalPhrases);

  const getChatColorClass = (type: number) => {
    switch (type) {
      case 0:
      case 1:
        return 'text-white';
      case 2:
        return 'text-sky-400';
      case 3:
        return 'text-green-400';
      case 4:
        return 'text-yellow-400 font-semibold';
      case 6:
        return 'text-orange-400';
      case 7:
        return 'text-red-500 font-semibold';
      default:
        return 'text-white';
    }
  };

  const generatePreview = () => {
    const randomPhrase = phrases.length > 0 ? phrases[0] : 'foi de arrasta pra cima!';
    return configData.message_template
      .replace(/{killer}/g, 'Pedreiro')
      .replace(/{victim}/g, 'Gemini')
      .replace(/{weapon}/g, 'AK-47')
      .replace(/{distance}/g, '124')
      .replace(/{phrase}/g, randomPhrase);
  };

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
            <h3 className="font-semibold">{t('settings.killFeed.error_loading', 'Error loading Kill Feed settings')}</h3>
            <p className="text-sm text-white/70 mt-1">{error}</p>
            <button
              onClick={loadData}
              className="mt-4 px-4 py-2 bg-white/5 hover:bg-white/10 border border-white/10 rounded-lg text-sm text-white flex items-center gap-2 transition-colors"
            >
              <RefreshCw size={16} />
              {t('common.retry', 'Retry')}
            </button>
          </div>
        </div>
      </div>
    );
  }

  const query = searchQuery.toLowerCase().trim();
  const matchesSearch =
    !query ||
    t('settings.killFeed.title', 'Kill Feed Settings').toLowerCase().includes(query) ||
    t('settings.killFeed.description', 'Manage real-time in-game chat broadcast of kills with dynamic phrases.').toLowerCase().includes(query) ||
    configData.message_template.toLowerCase().includes(query) ||
    phrases.some(p => p.toLowerCase().includes(query));

  if (!matchesSearch) {
    return (
      <div className="text-center py-12 text-white/50 card">
        Nenhum item do Kill Feed corresponde à sua busca.
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {showRestartWarning && (
        <div className="bg-orange-500/10 border border-orange-500/30 rounded-xl p-4 flex items-start gap-3">
          <AlertTriangle className="text-orange-500 w-5 h-5 flex-shrink-0 mt-0.5" />
          <div>
            <h4 className="text-sm font-semibold text-white">
              {t('settings.killFeed.restart_warning_title', 'Restart Required')}
            </h4>
            <p className="text-xs text-white/75 mt-1 leading-relaxed">
              {t('settings.killFeed.restart_warning', 'Changes to RCON settings require the SSM Backend to be restarted manually to take effect. Stop the service, close the backend, open it again, and click Start.')}
            </p>
          </div>
        </div>
      )}

      <div className="card p-4 sm:p-6 space-y-6">
        <div>
          <h2 className="text-lg font-bold text-white flex items-center gap-2">
            <ShieldAlert className="text-scum-orange w-5 h-5" />
            {t('settings.killFeed.title', 'Kill Feed Settings')}
          </h2>
          <p className="text-sm text-white/60 mt-1">
            {t('settings.killFeed.description', 'Manage real-time in-game chat broadcast of PvP kills with templates and dynamic phrases.')}
          </p>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <div className="space-y-6">
            <div className="bg-white/5 border border-white/10 rounded-xl p-4 space-y-4">
              <div className="flex items-center justify-between">
                <div>
                  <h3 className="text-sm font-semibold text-white">
                    {t('settings.killFeed.enabled', 'Enable Kill Feed')}
                  </h3>
                  <p className="text-xs text-white/50 mt-0.5">
                    {t('settings.killFeed.enabled_help', 'If enabled, sends kill notifications to the in-game chat.')}
                  </p>
                </div>
                <label className="relative inline-flex items-center cursor-pointer flex-shrink-0">
                  <input
                    type="checkbox"
                    checked={configData.enabled}
                    onChange={handleToggleEnabled}
                    className="sr-only peer"
                    disabled={saving}
                  />
                  <div className="w-11 h-6 bg-white/10 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-scum-orange"></div>
                </label>
              </div>

              <div className="grid grid-cols-2 gap-4 pt-3 border-t border-white/5">
                <div>
                  <label htmlFor="mode" className="text-xs font-semibold text-white/70 block mb-1">
                    {t('settings.killFeed.mode', 'Display Mode')}
                  </label>
                  <select
                    id="mode"
                    value={configData.mode}
                    onChange={(e) => setConfigData(prev => ({ ...prev, mode: e.target.value }))}
                    className="w-full px-3 py-2 bg-white/5 border border-white/10 rounded-lg text-white text-sm focus:outline-none focus:ring-2 focus:ring-scum-orange focus:border-transparent"
                    disabled={saving}
                  >
                    <option value="chat" className="bg-scum-panel">{t('settings.killFeed.modes.chat', 'Chat')}</option>
                    <option value="hidden" className="bg-scum-panel">{t('settings.killFeed.modes.hidden', 'Hidden')}</option>
                  </select>
                </div>

                <div>
                  <div className="flex items-center gap-1 mb-1">
                    <label htmlFor="priority" className="text-xs font-semibold text-white/70">
                      {t('settings.killFeed.priority', 'RCON Priority')}
                    </label>
                    <div className="group relative inline-block">
                      <Info className="w-3.5 h-3.5 text-white/40 hover:text-white/80 cursor-pointer" />
                      <div className="pointer-events-none absolute bottom-full left-1/2 z-50 mb-2 w-48 -translate-x-1/2 rounded bg-black/95 px-2.5 py-1.5 text-[11px] font-normal text-white/90 opacity-0 transition-opacity group-hover:opacity-100 shadow-xl border border-white/10 text-center whitespace-normal normal-case leading-normal">
                        {t('settings.killFeed.priority_help', 'Priority order in RCON command queue (default: 15).')}
                      </div>
                    </div>
                  </div>
                  <input
                    id="priority"
                    type="number"
                    min="1"
                    max="100"
                    value={configData.priority}
                    onChange={(e) => setConfigData(prev => ({ ...prev, priority: Number(e.target.value) }))}
                    className="w-full px-3 py-2 bg-white/5 border border-white/10 rounded-lg text-white text-sm focus:outline-none focus:ring-2 focus:ring-scum-orange focus:border-transparent"
                    disabled={saving}
                  />
                </div>
              </div>
            </div>

            <div className="bg-white/5 border border-white/10 rounded-xl p-4 space-y-3">
              <div>
                <h3 className="text-sm font-semibold text-white">
                  {t('settings.killFeed.chat_type', 'Chat Channel (Color)')}
                </h3>
                <p className="text-xs text-white/50 mt-0.5">
                  {t('settings.killFeed.chat_type_help', 'Select the SCUM channel where kill messages will be broadcast.')}
                </p>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                {CHAT_TYPES.map((type) => {
                  const isSelected = configData.chat_type === type.id;
                  return (
                    <button
                      key={type.id}
                      onClick={() => handleChatTypeSelect(type.id)}
                      className={`p-2.5 rounded-lg border text-left flex items-start gap-2.5 transition-all ${
                        isSelected
                          ? 'bg-scum-orange/10 border-scum-orange shadow-lg'
                          : 'bg-white/5 border-white/10 hover:bg-white/10'
                      }`}
                      disabled={saving}
                    >
                      <div className={`w-3.5 h-3.5 rounded-full mt-0.5 flex-shrink-0 ${type.colorBg} border border-white/10`} />
                      <div>
                        <div className={`text-xs font-semibold ${isSelected ? 'text-scum-orange' : 'text-white'}`}>
                          {t(type.nameKey, type.nameDefault)}
                        </div>
                        <div className="text-[10px] text-white/45 leading-tight mt-0.5">
                          {t(type.descKey, type.descDefault)}
                        </div>
                      </div>
                    </button>
                  );
                })}
              </div>
            </div>

            <div className="bg-white/5 border border-white/10 rounded-xl p-4 space-y-4">
              <div>
                <h3 className="text-sm font-semibold text-white">
                  {t('settings.killFeed.template', 'Message Template')}
                </h3>
                <p className="text-xs text-white/50 mt-0.5">
                  {t('settings.killFeed.template_description', 'Define the text template for kills. Use the quick tags below to populate data.')}
                </p>
              </div>

              <div className="space-y-2">
                <input
                  ref={inputRef}
                  type="text"
                  value={configData.message_template}
                  onChange={(e) => setConfigData(prev => ({ ...prev, message_template: e.target.value }))}
                  className="w-full px-3 py-2 bg-white/5 border border-white/10 rounded-lg text-white text-sm focus:outline-none focus:ring-2 focus:ring-scum-orange focus:border-transparent font-mono text-xs"
                  placeholder="{killer} matou {victim} ({weapon} - {distance}m)"
                  disabled={saving}
                />

                <div className="flex flex-wrap gap-1.5 pt-1">
                  {['{killer}', '{victim}', '{weapon}', '{distance}', '{phrase}'].map((tag) => (
                    <button
                      key={tag}
                      onClick={() => insertTag(tag)}
                      className="px-2 py-1 bg-white/5 hover:bg-white/10 border border-white/10 rounded text-[10px] font-mono text-scum-orange transition-colors"
                      disabled={saving}
                      title={`Insert ${tag} at cursor`}
                    >
                      {tag}
                    </button>
                  ))}
                </div>
              </div>

              <div className="space-y-2 pt-3 border-t border-white/5">
                <span className="text-xs font-semibold text-white/70">
                  {t('settings.killFeed.preview', 'In-Game View (Simulation)')}
                </span>
                
                <div className="bg-black/85 rounded-xl border border-white/5 p-3.5 font-mono text-xs space-y-1.5 shadow-inner min-h-[50px] flex items-center">
                  <div className="flex items-center gap-1.5 w-full leading-normal">
                    <span className="text-[10px] text-white/30 font-sans">[13:07:34]</span>
                    <span className={getChatColorClass(configData.chat_type)}>
                      {generatePreview()}
                    </span>
                  </div>
                </div>
              </div>

            </div>

          </div>

          <div className="space-y-4">
            <div className="bg-white/5 border border-white/10 rounded-xl p-4 flex flex-col h-full space-y-4 min-h-[500px]">
              <div>
                <h3 className="text-sm font-semibold text-white">
                  {t('settings.killFeed.phrases_title', 'Random Kill Phrases ({phrase})')}
                </h3>
                <p className="text-xs text-white/50 mt-0.5">
                  {t('settings.killFeed.phrases_description', 'Phrases that randomly replace the {phrase} tag in kill messages.')}
                </p>
              </div>

              <div className="flex gap-2">
                <input
                  type="text"
                  value={newPhrase}
                  onChange={(e) => setNewPhrase(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter') {
                      e.preventDefault();
                      handleAddPhrase();
                    }
                  }}
                  placeholder={t('settings.killFeed.add_phrase_placeholder', 'Type a kill phrase...')}
                  className="flex-1 px-3 py-2 bg-white/5 border border-white/10 rounded-lg text-white text-sm focus:outline-none focus:ring-2 focus:ring-scum-orange focus:border-transparent"
                  disabled={saving}
                />
                <button
                  onClick={handleAddPhrase}
                  disabled={saving || !newPhrase.trim()}
                  className="px-3 py-2 bg-scum-orange hover:bg-scum-orange/90 text-white rounded-lg text-sm font-semibold transition-colors flex items-center gap-1"
                >
                  <Plus size={16} />
                  {t('settings.killFeed.add_button', 'Add')}
                </button>
              </div>

              <div className="flex-1 overflow-y-auto border border-white/5 rounded-lg bg-black/20 p-2.5 max-h-[360px] space-y-1.5 custom-scrollbar">
                {phrases.length === 0 ? (
                  <div className="text-center py-12 text-white/30 text-xs">
                    {t('settings.killFeed.phrases.empty', 'No phrases registered. Add phrases above to populate the kill feed.')}
                  </div>
                ) : (
                  phrases.map((phrase, index) => {
                    const isEditing = editingIndex === index;
                    return (
                      <div
                        key={index}
                        className={`flex items-center justify-between p-2 rounded-lg text-xs transition-colors group ${
                          isEditing
                            ? 'bg-scum-orange/10 border border-scum-orange/30'
                            : 'bg-white/5 hover:bg-white/10 border border-transparent'
                        }`}
                      >
                        {isEditing ? (
                          <input
                            type="text"
                            value={editingValue}
                            onChange={(e) => setEditingValue(e.target.value)}
                            onKeyDown={(e) => {
                              if (e.key === 'Enter') {
                                e.preventDefault();
                                handleSaveEdit();
                              } else if (e.key === 'Escape') {
                                setEditingIndex(null);
                              }
                            }}
                            className="flex-1 px-2.5 py-1 bg-black/40 border border-white/20 rounded text-white text-xs focus:outline-none focus:ring-1 focus:ring-scum-orange"
                            autoFocus
                          />
                        ) : (
                          <span className="text-white/80 font-mono pl-1">
                            {phrase}
                          </span>
                        )}

                        <div className="flex gap-1.5 ml-2">
                          {isEditing ? (
                            <>
                              <button
                                onClick={handleSaveEdit}
                                className="p-1 hover:text-green-400 text-white/50 transition-colors"
                                title="Save"
                              >
                                <Check size={14} />
                              </button>
                              <button
                                onClick={() => setEditingIndex(null)}
                                className="p-1 hover:text-red-400 text-white/50 transition-colors"
                                title="Cancel"
                              >
                                <X size={14} />
                              </button>
                            </>
                          ) : (
                            <>
                              <button
                                onClick={() => handleStartEdit(index)}
                                className="p-1 hover:text-sky-400 text-white/40 group-hover:text-white/80 transition-colors"
                                title="Edit"
                                disabled={saving}
                              >
                                <Edit2 size={13} />
                              </button>
                              <button
                                onClick={() => handleDeletePhrase(index)}
                                className="p-1 hover:text-red-400 text-white/40 group-hover:text-white/80 transition-colors"
                                title="Delete"
                                disabled={saving}
                              >
                                <Trash2 size={13} />
                              </button>
                            </>
                          )}
                        </div>
                      </div>
                    );
                  })
                )}
              </div>

              <div className="text-[10px] text-white/40 flex justify-between px-1">
                <span>{t('settings.killFeed.phrases.total', 'Total: {{count}} phrases', { count: phrases.length })}</span>
                <span>{t('settings.killFeed.phrases.tag_hint', 'Usable tag in template: {phrase}')}</span>
              </div>
            </div>
          </div>
        </div>

        <div className="flex flex-col sm:flex-row gap-4 items-center justify-between pt-4 border-t border-white/10">
          <div className="flex items-center gap-2 text-white/50 text-xs">
            <AlertTriangle size={14} className="text-scum-orange animate-pulse flex-shrink-0" />
            <span>{t('settings.killFeed.footer_warning', 'Changes to the phrases list take effect after saving. Channel and priority changes require restart.')}</span>
          </div>

          <div className="flex gap-3 w-full sm:w-auto">
            <button
              onClick={loadData}
              disabled={loading || saving}
              className="flex-1 sm:flex-none px-4 py-2 bg-white/5 hover:bg-white/10 border border-white/10 rounded-lg text-sm font-medium text-white transition-colors flex items-center justify-center gap-2"
            >
              <RefreshCw size={16} />
              {t('common.revert', 'Revert')}
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
              {t('common.save', 'Save alterations')}
            </button>
          </div>
        </div>

      </div>
    </div>
  );
}
