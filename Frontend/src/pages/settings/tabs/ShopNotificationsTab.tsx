import { useState, useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import { Loader2, Save, RefreshCw, Info } from 'lucide-react';
import Swal from 'sweetalert2';
import { getConfig, updateConfigSection } from '@/services/config';

interface ShopNotificationsTabProps {
  searchQuery?: string;
  onSearchChange?: (query: string) => void;
}

interface NotificationMessages {
  welcome_kit_delivered: string;
  items_delivered: string;
  insufficient_funds: string;
}

export default function ShopNotificationsTab({ searchQuery = '' }: ShopNotificationsTabProps) {
  const { t } = useTranslation();
  const [messages, setMessages] = useState<NotificationMessages>({
    welcome_kit_delivered: '',
    items_delivered: '',
    insufficient_funds: '',
  });
  const [originalMessages, setOriginalMessages] = useState<NotificationMessages>({
    welcome_kit_delivered: '',
    items_delivered: '',
    insufficient_funds: '',
  });
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const loadData = async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await getConfig('shop_notifications');
      if (response.success && response.data) {
        const data = response.data;
        const loadedMessages = {
          welcome_kit_delivered: data.welcome_kit_delivered || 'Seu kit foi entregue com sucesso!',
          items_delivered: data.items_delivered || 'Seus itens foram entregues com sucesso!',
          insufficient_funds: data.insufficient_funds || 'Saldo insuficiente! Seu saldo atual: R$ {balance}',
        };
        setMessages(loadedMessages);
        setOriginalMessages(loadedMessages);
      } else {
        setError(response.error || 'Erro ao carregar configurações');
      }
    } catch (err: any) {
      setError(err.message || 'Erro ao carregar configurações');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const handleChange = (key: keyof NotificationMessages, value: string) => {
    setMessages((prev) => ({
      ...prev,
      [key]: value,
    }));
  };

  const handleSave = async () => {
    setSaving(true);
    try {
      const response = await updateConfigSection('shop_notifications', messages, true);
      if (response.success) {
        setOriginalMessages(messages);
        await Swal.fire({
          icon: 'success',
          title: t('settings.shopNotifications.save_success', 'Configurações salvas!'),
          text: t('settings.discord.save.backup', 'Configurações atualizadas e backup criado com sucesso.'),
          confirmButtonColor: '#f97316',
        });
      } else {
        throw new Error(response.error || response.message || 'Erro ao salvar configurações');
      }
    } catch (err: any) {
      const errorMsg = err.response?.data?.error || err.message || 'Erro ao salvar configurações';
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
    messages.welcome_kit_delivered !== originalMessages.welcome_kit_delivered ||
    messages.items_delivered !== originalMessages.items_delivered ||
    messages.insufficient_funds !== originalMessages.insufficient_funds;

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
            <h3 className="font-semibold">Erro ao carregar dados</h3>
            <p className="text-sm text-white/70 mt-1">{error}</p>
            <button
              onClick={loadData}
              className="mt-4 px-4 py-2 bg-white/5 hover:bg-white/10 border border-white/10 rounded-lg text-sm text-white flex items-center gap-2 transition-colors"
            >
              <RefreshCw size={16} />
              Tentar novamente
            </button>
          </div>
        </div>
      </div>
    );
  }

  // Filtrar campos se o usuário estiver buscando algo específico no input de busca
  const query = searchQuery.toLowerCase().trim();
  const fields = [
    {
      key: 'welcome_kit_delivered' as const,
      label: t('settings.shopNotifications.welcome_kit_delivered', 'Entrega de Kit de Boas-vindas / Kits'),
      help: t('settings.shopNotifications.welcome_kit_delivered_help', 'Mensagem enviada quando um kit é entregue com sucesso.'),
      placeholder: 'Seu kit foi entregue com sucesso!',
      variables: [],
    },
    {
      key: 'items_delivered' as const,
      label: t('settings.shopNotifications.items_delivered', 'Entrega de Itens'),
      help: t('settings.shopNotifications.items_delivered_help', 'Mensagem enviada quando itens avulsos são entregues com sucesso.'),
      placeholder: 'Seus itens foram entregues com sucesso!',
      variables: [],
    },
    {
      key: 'insufficient_funds' as const,
      label: t('settings.shopNotifications.insufficient_funds', 'Saldo Insuficiente'),
      help: t('settings.shopNotifications.insufficient_funds_help', 'Mensagem enviada quando o jogador tenta comprar mas não tem saldo suficiente.'),
      placeholder: 'Saldo insuficiente! Seu saldo atual: R$ {balance}',
      variables: ['{balance}'],
    },
  ];

  const filteredFields = fields.filter(
    (field) =>
      field.label.toLowerCase().includes(query) ||
      field.help.toLowerCase().includes(query) ||
      messages[field.key].toLowerCase().includes(query)
  );

  return (
    <div className="space-y-6">
      <div className="card p-4 sm:p-6 space-y-6">
        <div>
          <h2 className="text-lg font-bold text-white">
            {t('settings.shopNotifications.title', 'Notificações RCON da Loja')}
          </h2>
          <p className="text-sm text-white/60 mt-1">
            {t('settings.shopNotifications.description', 'Personalize as mensagens que os jogadores recebem in-game via RCON.')}
          </p>
        </div>

        <div className="space-y-6">
          {filteredFields.length === 0 ? (
            <div className="text-center py-6 text-white/55">
              Nenhum campo de notificação corresponde à sua busca.
            </div>
          ) : (
            filteredFields.map((field) => (
              <div key={field.key} className="space-y-2 border-b border-white/5 pb-6 last:border-0 last:pb-0">
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-1">
                  <label htmlFor={field.key} className="text-sm font-semibold text-white">
                    {field.label}
                  </label>
                  {field.variables.length > 0 && (
                    <div className="flex gap-2">
                      {field.variables.map((v) => (
                        <span
                          key={v}
                          className="px-2 py-0.5 bg-white/5 border border-white/10 rounded text-xs font-mono text-scum-orange cursor-pointer hover:bg-white/10"
                          onClick={() => {
                            if (!messages[field.key].includes(v)) {
                              handleChange(field.key, messages[field.key] + ' ' + v);
                            }
                          }}
                          title="Clique para adicionar ao final da mensagem"
                        >
                          {v}
                        </span>
                      ))}
                    </div>
                  )}
                </div>
                <p className="text-xs text-white/45">{field.help}</p>
                <div className="relative">
                  <textarea
                    id={field.key}
                    value={messages[field.key]}
                    onChange={(e) => handleChange(field.key, e.target.value)}
                    placeholder={field.placeholder}
                    className="w-full px-3 py-2.5 bg-white/5 border border-white/10 rounded-lg text-white text-sm placeholder-white/30 focus:outline-none focus:ring-2 focus:ring-scum-orange focus:border-transparent min-h-[80px]"
                    disabled={saving}
                  />
                </div>
              </div>
            ))
          )}
        </div>

        <div className="flex flex-col sm:flex-row gap-4 items-center justify-between pt-4 border-t border-white/10">
          <div className="flex items-center gap-2 text-white/50 text-xs">
            <Info size={14} className="text-scum-orange" />
            <span>As mensagens usam a combinação HUD + Toast com delay de 0.2s</span>
          </div>

          <div className="flex gap-3 w-full sm:w-auto">
            <button
              onClick={loadData}
              disabled={loading || saving}
              className="flex-1 sm:flex-none px-4 py-2 bg-white/5 hover:bg-white/10 border border-white/10 rounded-lg text-sm font-medium text-white transition-colors flex items-center justify-center gap-2"
            >
              <RefreshCw size={16} />
              Descartar
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
              Salvar alterações
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
