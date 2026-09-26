import { useState, useEffect, useMemo } from 'react';
import { useTranslation } from 'react-i18next';
import { Loader2, CheckCircle2, Edit2, X, Send, Save, ChevronDown, ChevronUp } from 'lucide-react';
import Swal from 'sweetalert2';
import {
  getWebhooks,
  getWebhookNames,
  updateWebhook,
  testWebhook,
  testWebhookByUrl,
} from '@/services/webhooks';

interface DiscordTabProps {
  searchQuery?: string;
  onSearchChange?: (query: string) => void;
}

/**
 * Obtém o nome traduzido de um webhook
 */
function getWebhookDisplayName(webhookName: string, t: any): string {
  const normalizedName = webhookName.replace(/-/g, '_').toLowerCase();
  const translationKey = `settings.discord.webhooks.${normalizedName}`;
  const translated = t(translationKey);
  
  if (translated && translated !== translationKey) {
    return translated;
  }
  
  const words = normalizedName.split('_');
  return words
    .map(word => {
      if (word === 'serverstatus') {
        return t('settings.discord.webhooks.serverstatus');
      }
      return word.charAt(0).toUpperCase() + word.slice(1).toLowerCase();
    })
    .join(' ');
}

/**
 * Valida se uma URL é um webhook válido do Discord
 * Aceita tanto discord.com quanto discordapp.com
 */
function isValidDiscordWebhook(url: string): boolean {
  if (!url.trim()) return true; // URL vazia é válida (para limpar)
  
  try {
    const urlObj = new URL(url);
    const isValidHostname = 
      urlObj.hostname === 'discord.com' || 
      urlObj.hostname === 'discordapp.com';
    
    return (
      urlObj.protocol === 'https:' &&
      isValidHostname &&
      urlObj.pathname.startsWith('/api/webhooks/')
    );
  } catch {
    return false;
  }
}

export default function DiscordTab({ searchQuery = '' }: DiscordTabProps) {
  const { t } = useTranslation();

  // Estados
  const [webhooks, setWebhooks] = useState<Record<string, string>>({});
  const [webhookNames, setWebhookNames] = useState<string[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [editingUrls, setEditingUrls] = useState<Record<string, string>>({});
  const [saving, setSaving] = useState<Record<string, boolean>>({});
  const [testing, setTesting] = useState<Record<string, boolean>>({});
  const [expandedCards, setExpandedCards] = useState<Record<string, boolean>>({});

  // Carregar dados
  useEffect(() => {
    const loadData = async () => {
      setLoading(true);
      setError(null);
      
      try {
        // Carregar nomes de webhooks disponíveis
        const namesResponse = await getWebhookNames();
        if (namesResponse.success && namesResponse.data) {
          setWebhookNames(namesResponse.data.webhooks || []);
        } else {
          setError(namesResponse.error || t('settings.discord.errors.loadFailed'));
          return;
        }

        // Carregar webhooks configurados
        const webhooksResponse = await getWebhooks();
        if (webhooksResponse.success && webhooksResponse.data) {
          setWebhooks(webhooksResponse.data);
        } else {
          setError(webhooksResponse.error || t('settings.discord.errors.loadFailed'));
        }
      } catch (err: any) {
        setError(err.message || t('settings.discord.errors.loadFailed'));
      } finally {
        setLoading(false);
      }
    };

    loadData();
  }, []);

  // Filtrar webhooks por busca
  const filteredWebhookNames = useMemo(() => {
    if (!searchQuery.trim()) {
      return webhookNames;
    }

    const query = searchQuery.toLowerCase();
    return webhookNames.filter(name => {
      const displayName = getWebhookDisplayName(name, t).toLowerCase();
      const url = editingUrls[name] || webhooks[name] || '';
      return (
        name.toLowerCase().includes(query) ||
        displayName.includes(query) ||
        url.toLowerCase().includes(query)
      );
    });
  }, [webhookNames, editingUrls, webhooks, searchQuery, t]);

  // Iniciar edição
  const handleStartEdit = (webhookName: string) => {
    setEditingUrls({
      ...editingUrls,
      [webhookName]: webhooks[webhookName] || '',
    });
  };

  // Cancelar edição
  const handleCancelEdit = (webhookName: string) => {
    const updated = { ...editingUrls };
    delete updated[webhookName];
    setEditingUrls(updated);
  };

  // Atualizar URL durante edição
  const handleUrlChange = (webhookName: string, url: string) => {
    setEditingUrls({
      ...editingUrls,
      [webhookName]: url,
    });
  };

  // Testar webhook configurado
  const handleTestWebhook = async (webhookName: string) => {
    setTesting({ ...testing, [webhookName]: true });
    
    try {
      const result = await testWebhook(webhookName);
      
      if (result.success) {
        await Swal.fire({
          icon: 'success',
          title: t('settings.discord.test.success'),
          text: `${t('settings.discord.test.successText')} (Status: ${result.data.status_code})`,
          confirmButtonColor: '#f97316',
        });
      } else {
        throw new Error(result.error || result.message || t('settings.discord.test.error'));
      }
    } catch (err: any) {
      const errorMsg = err.response?.data?.error || err.message || t('settings.discord.test.error');
      await Swal.fire({
        icon: 'error',
        title: t('settings.discord.test.error'),
        text: errorMsg,
        confirmButtonColor: '#f97316',
      });
    } finally {
      setTesting({ ...testing, [webhookName]: false });
    }
  };

  // Testar URL antes de salvar
  const handleTestUrl = async (webhookName: string, url: string) => {
    if (!url.trim()) {
      await Swal.fire({
        icon: 'warning',
        title: t('settings.discord.test.invalidUrl'),
        text: t('settings.discord.test.emptyUrl'),
        confirmButtonColor: '#f97316',
      });
      return;
    }

    if (!isValidDiscordWebhook(url)) {
      await Swal.fire({
        icon: 'error',
        title: t('settings.discord.errors.validationFailed'),
        text: t('settings.discord.errors.invalidUrl'),
        confirmButtonColor: '#f97316',
      });
      return;
    }

    setTesting({ ...testing, [`${webhookName}_url`]: true });
    
    try {
      const result = await testWebhookByUrl({ url });
      
      if (result.success) {
        await Swal.fire({
          icon: 'success',
          title: t('settings.discord.test.success'),
          text: `${t('settings.discord.test.successText')} (Status: ${result.data.status_code})`,
          confirmButtonColor: '#f97316',
        });
      } else {
        throw new Error(result.error || result.message || t('settings.discord.test.error'));
      }
    } catch (err: any) {
      const errorMsg = err.response?.data?.error || err.message || t('settings.discord.test.error');
      await Swal.fire({
        icon: 'error',
        title: t('settings.discord.test.error'),
        text: errorMsg,
        confirmButtonColor: '#f97316',
      });
    } finally {
      setTesting({ ...testing, [`${webhookName}_url`]: false });
    }
  };

  // Salvar webhook
  const handleSave = async (webhookName: string) => {
    const url = editingUrls[webhookName] || '';

    // Validar URL
    if (url.trim() && !isValidDiscordWebhook(url)) {
      await Swal.fire({
        icon: 'error',
        title: t('settings.discord.errors.validationFailed'),
        text: t('settings.discord.errors.invalidUrl'),
        confirmButtonColor: '#f97316',
      });
      return;
    }

    setSaving({ ...saving, [webhookName]: true });
    
    try {
      await updateWebhook(webhookName, url.trim(), true);
      
      await Swal.fire({
        icon: 'success',
        title: t('settings.discord.save.success'),
        text: t('settings.discord.save.backup'),
        confirmButtonColor: '#f97316',
      });

      // Atualizar estado local
      setWebhooks({
        ...webhooks,
        [webhookName]: url.trim(),
      });

      // Sair do modo de edição
      handleCancelEdit(webhookName);
    } catch (err: any) {
      const errorMsg = err.response?.data?.error || err.message || t('settings.discord.errors.saveFailed');
      await Swal.fire({
        icon: 'error',
        title: t('settings.discord.errors.saveFailed'),
        text: errorMsg,
        confirmButtonColor: '#f97316',
      });
    } finally {
      setSaving({ ...saving, [webhookName]: false });
    }
  };

  // Verificar se está editando
  const isEditing = (webhookName: string) => {
    return webhookName in editingUrls;
  };

  // Alternar estado de expansão do card
  const toggleCard = (webhookName: string) => {
    setExpandedCards({
      ...expandedCards,
      [webhookName]: !expandedCards[webhookName],
    });
  };

  // Verificar se o card está expandido
  const isExpanded = (webhookName: string) => {
    return expandedCards[webhookName] === true; // Por padrão, os cards começam fechados
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
            <h3 className="font-semibold">{t('settings.discord.errors.loadFailed')}</h3>
            <p className="text-sm text-white/70 mt-1">{error}</p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {filteredWebhookNames.length === 0 ? (
        <div className="card p-6 text-center text-white/60">
          <p>{searchQuery ? t('settings.discord.search.noResults') : t('settings.discord.empty')}</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
          {filteredWebhookNames.map((name) => {
            const currentUrl = webhooks[name] || '';
            const editingUrl = editingUrls[name] ?? currentUrl;
            const editing = isEditing(name);
            const isSaving = saving[name] || false;
            const isTesting = testing[name] || false;
            const isTestingUrl = testing[`${name}_url`] || false;
            const hasChanges = editingUrl !== currentUrl;

            const expanded = isExpanded(name);

            return (
              <div key={name} className="card p-4">
                <div className="space-y-3">
                  {/* Título com botão de colapsar */}
                  <div className="flex items-center justify-between cursor-pointer" onClick={() => toggleCard(name)}>
                    <h3 className="text-sm font-semibold text-white">
                      {getWebhookDisplayName(name, t)}
                    </h3>
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        toggleCard(name);
                      }}
                      className="p-1 hover:bg-white/10 rounded transition-colors"
                      title={
                        expanded
                          ? t('settings.discord.actions.collapse')
                          : t('settings.discord.actions.expand')
                      }
                    >
                      {expanded ? (
                        <ChevronUp size={18} className="text-white/70" />
                      ) : (
                        <ChevronDown size={18} className="text-white/70" />
                      )}
                    </button>
                  </div>

                  {/* Conteúdo */}
                  {expanded && (
                  <div className="space-y-2">
                    {editing ? (
                      <input
                        type="url"
                        value={editingUrl}
                        onChange={(e) => handleUrlChange(name, e.target.value)}
                        placeholder={t('settings.discord.urlPlaceholder')}
                        className="w-full px-3 py-2 bg-white/5 border border-white/10 rounded-lg text-white text-sm placeholder-white/40 focus:outline-none focus:ring-2 focus:ring-scum-orange focus:border-transparent"
                        disabled={isSaving || isTestingUrl}
                      />
                    ) : (
                      <div className="px-3 py-2 bg-white/5 border border-white/10 rounded-lg text-white/80 text-sm font-mono break-all min-h-[40px] flex items-center">
                        {currentUrl || t('settings.discord.urlPlaceholder')}
                      </div>
                    )}
                    <div className="flex gap-2 items-center justify-end">
                      {editing ? (
                        <>
                          <button
                            onClick={() => handleTestUrl(name, editingUrl)}
                            disabled={isTestingUrl || !editingUrl.trim()}
                            className="px-3 py-1.5 bg-blue-500/20 hover:bg-blue-500/30 border border-blue-500/30 rounded text-blue-400 text-sm font-medium transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center"
                            title={t('settings.discord.test.testUrl')}
                          >
                            {isTestingUrl ? (
                              <Loader2 size={16} className="animate-spin" />
                            ) : (
                              <Send size={16} />
                            )}
                          </button>
                          <button
                            onClick={() => handleCancelEdit(name)}
                            disabled={isSaving || isTestingUrl}
                            className="px-3 py-1.5 bg-white/5 hover:bg-white/10 border border-white/10 rounded text-white text-sm font-medium transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center"
                            title={t('common.cancel')}
                          >
                            <X size={16} />
                          </button>
                        </>
                      ) : (
                        currentUrl && (
                          <button
                            onClick={() => handleTestWebhook(name)}
                            disabled={isTesting}
                            className="px-3 py-1.5 bg-blue-500/20 hover:bg-blue-500/30 border border-blue-500/30 rounded text-blue-400 text-sm font-medium transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center"
                            title={t('settings.discord.test.testWebhook')}
                          >
                            {isTesting ? (
                              <Loader2 size={16} className="animate-spin" />
                            ) : (
                              <Send size={16} />
                            )}
                          </button>
                        )
                      )}
                      <button
                        onClick={() => handleStartEdit(name)}
                        disabled={editing || isSaving}
                        className="px-3 py-1.5 bg-white/5 hover:bg-white/10 border border-white/10 rounded text-white text-sm font-medium transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center"
                        title={t('settings.discord.edit')}
                      >
                        <Edit2 size={16} />
                      </button>
                      <button
                        onClick={() => handleSave(name)}
                        disabled={!editing || isSaving || !hasChanges}
                        className={`px-3 py-1.5 rounded text-sm font-medium transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center ${
                          editing && hasChanges
                            ? 'bg-scum-orange hover:bg-scum-orange/90 text-white'
                            : 'bg-white/5 hover:bg-white/10 border border-white/10 text-white'
                        }`}
                        title={t('settings.discord.actions.save')}
                      >
                        {isSaving ? (
                          <Loader2 size={16} className="animate-spin" />
                        ) : (
                          <Save size={16} />
                        )}
                      </button>
                    </div>
                  </div>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
