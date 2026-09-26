import { useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import Swal from 'sweetalert2';
import { Dumbbell, Heart, Zap, Brain, Save, RotateCcw, RefreshCw, Info, Clock } from 'lucide-react';
import { getAttributePrices, updateAttributePrices } from '@/services/attributes';

type AttributePrices = {
  strength: Record<number, number>;
  constitution: Record<number, number>;
  dexterity: Record<number, number>;
  intelligence: Record<number, number>;
};

const DEFAULT_PRICES: AttributePrices = {
  strength: {
    1: 100,
    2: 200,
    3: 300,
    4: 400,
    5: 500,
    6: 1000,
    7: 2000,
    8: 4000,
  },
  constitution: {
    1: 100,
    2: 200,
    3: 300,
    4: 400,
    5: 800,
  },
  dexterity: {
    1: 100,
    2: 200,
    3: 300,
    4: 400,
    5: 800,
  },
  intelligence: {
    1: 100,
    2: 200,
    3: 300,
    4: 400,
    5: 800,
  },
};

export default function AttributesConfigTab() {
  const { t } = useTranslation();
  const [prices, setPrices] = useState<AttributePrices>(DEFAULT_PRICES);
  const [initialPrices, setInitialPrices] = useState<AttributePrices>(DEFAULT_PRICES);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [expirationEnabled, setExpirationEnabled] = useState(false);
  const [initialExpirationEnabled, setInitialExpirationEnabled] = useState(false);
  const [expirationDurationDays, setExpirationDurationDays] = useState(30);
  const [initialExpirationDurationDays, setInitialExpirationDurationDays] = useState(30);

  const loadPrices = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await getAttributePrices();
      if (res.success && res.data) {
        const rawPrices = res.data.prices;
        const isExpEnabled = res.data.expiration_enabled === 1;
        const expDays = res.data.expiration_duration_days ?? 30;

        const mergedPrices: AttributePrices = {
          strength: { ...DEFAULT_PRICES.strength, ...rawPrices?.strength },
          constitution: { ...DEFAULT_PRICES.constitution, ...rawPrices?.constitution },
          dexterity: { ...DEFAULT_PRICES.dexterity, ...rawPrices?.dexterity },
          intelligence: { ...DEFAULT_PRICES.intelligence, ...rawPrices?.intelligence },
        };
        
        setPrices(mergedPrices);
        setInitialPrices(mergedPrices);
        setExpirationEnabled(isExpEnabled);
        setInitialExpirationEnabled(isExpEnabled);
        setExpirationDurationDays(expDays);
        setInitialExpirationDurationDays(expDays);
      } else {
        setError(res.error || 'Falha ao carregar as configurações.');
      }
    } catch (err: any) {
      console.error('[AttributesConfigTab] error loading config:', err);
      setError(err?.response?.data?.error || err?.message || 'Erro ao carregar as configurações.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void loadPrices();
  }, []);

  const handlePriceChange = (attribute: keyof AttributePrices, level: number, value: string) => {
    // Sanitize input to only non-negative integers
    const sanitized = value.replace(/[^0-9]/g, '');
    const numValue = sanitized === '' ? 0 : parseInt(sanitized, 10);
    
    setPrices((prev) => ({
      ...prev,
      [attribute]: {
        ...prev[attribute],
        [level]: numValue,
      },
    }));
  };

  const hasChanges = () => {
    return (
      JSON.stringify(prices) !== JSON.stringify(initialPrices) ||
      expirationEnabled !== initialExpirationEnabled ||
      expirationDurationDays !== initialExpirationDurationDays
    );
  };

  const handleRevert = () => {
    setPrices(initialPrices);
    setExpirationEnabled(initialExpirationEnabled);
    setExpirationDurationDays(initialExpirationDurationDays);
  };

  const handleSave = async () => {
    if (expirationEnabled) {
      if (isNaN(expirationDurationDays) || expirationDurationDays < 1 || !Number.isInteger(Number(expirationDurationDays))) {
        await Swal.fire({
          icon: 'error',
          title: t('common.error', { defaultValue: 'Erro' }),
          text: t('tools.shopDeliveries.attributes.invalidDays', { 
            defaultValue: 'A duração da validade deve ser um número inteiro igual ou superior a 1 dia.' 
          }),
          confirmButtonColor: '#f97316',
        });
        return;
      }
    }

    setSaving(true);
    try {
      const res = await updateAttributePrices({
        prices,
        expiration_enabled: expirationEnabled,
        expiration_duration_days: Number(expirationDurationDays),
      });
      if (res.success) {
        setInitialPrices(prices);
        setInitialExpirationEnabled(expirationEnabled);
        setInitialExpirationDurationDays(expirationDurationDays);
        await Swal.fire({
          icon: 'success',
          title: t('common.success', { defaultValue: 'Sucesso' }),
          text: t('tools.shopDeliveries.attributes.saveSuccess', { defaultValue: 'Configurações salvas com sucesso!' }),
          confirmButtonColor: '#f97316',
        });
      } else {
        await Swal.fire({
          icon: 'error',
          title: t('common.error', { defaultValue: 'Erro' }),
          text: res.error || 'Falha ao salvar as configurações.',
          confirmButtonColor: '#f97316',
        });
      }
    } catch (err: any) {
      console.error('[AttributesConfigTab] error saving config:', err);
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

  const attributesList = [
    {
      key: 'strength' as const,
      label: t('tools.attributes.fields.strength', { defaultValue: 'Força' }),
      icon: <Dumbbell className="text-red-400" size={20} />,
      levels: [1, 2, 3, 4, 5, 6, 7, 8],
      bgGrad: 'from-red-500/10 to-transparent',
      borderHover: 'hover:border-red-500/30',
    },
    {
      key: 'constitution' as const,
      label: t('tools.attributes.fields.constitution', { defaultValue: 'Constituição' }),
      icon: <Heart className="text-emerald-400" size={20} />,
      levels: [1, 2, 3, 4, 5],
      bgGrad: 'from-emerald-500/10 to-transparent',
      borderHover: 'hover:border-emerald-500/30',
    },
    {
      key: 'dexterity' as const,
      label: t('tools.attributes.fields.dexterity', { defaultValue: 'Destreza' }),
      icon: <Zap className="text-amber-400" size={20} />,
      levels: [1, 2, 3, 4, 5],
      bgGrad: 'from-amber-500/10 to-transparent',
      borderHover: 'hover:border-amber-500/30',
    },
    {
      key: 'intelligence' as const,
      label: t('tools.attributes.fields.intelligence', { defaultValue: 'Inteligência' }),
      icon: <Brain className="text-blue-400" size={20} />,
      levels: [1, 2, 3, 4, 5],
      bgGrad: 'from-blue-500/10 to-transparent',
      borderHover: 'hover:border-blue-500/30',
    },
  ];

  return (
    <div className="space-y-4">
      {error && (
        <div className="p-3 text-sm text-red-400 rounded-lg border border-red-500/20 bg-red-500/5">
          {error}
        </div>
      )}

      {/* Help Panel for clear visual explanation (ideal for ADHD/TDH readability) */}
      <div className="card p-4 border border-blue-500/20 bg-blue-500/5 rounded-xl space-y-3">
        <div className="flex items-center gap-2 text-blue-400 font-semibold text-sm">
          <Info size={18} />
          <span>{t('tools.shopDeliveries.attributes.help.title', { defaultValue: 'Como funciona a configuração de preços?' })}</span>
        </div>
        <p className="text-xs text-white/80 leading-relaxed">
          {t('tools.shopDeliveries.attributes.help.description', { 
            defaultValue: 'Os jogadores compram os níveis de atributos diretamente no chat do jogo usando comandos de RCON (como /f5, /c3).' 
          })}
        </p>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3 pt-1 text-[11px] text-white/60">
          <div className="p-2.5 rounded-lg bg-white/5 border border-white/5 space-y-1">
            <span className="font-semibold text-white/80 block">
              {t('tools.shopDeliveries.attributes.help.fieldsTitle', { defaultValue: '📌 O que significa cada campo?' })}
            </span>
            <span>
              {t('tools.shopDeliveries.attributes.help.fieldsDesc', { 
                defaultValue: 'O valor configurado em cada Nível é o custo em créditos para que o jogador atinja aquele nível exato de atributo.' 
              })}
            </span>
          </div>
          <div className="p-2.5 rounded-lg bg-white/5 border border-white/5 space-y-1">
            <span className="font-semibold text-white/80 block">
              {t('tools.shopDeliveries.attributes.help.exampleTitle', { defaultValue: '💡 Exemplo Prático:' })}
            </span>
            <span>
              {t('tools.shopDeliveries.attributes.help.exampleDesc', { 
                defaultValue: 'Se o campo Nível 5 da Força estiver configurado como 500, o jogador pagará 500 créditos ao digitar /f5 para obter Força 5.' 
              })}
            </span>
          </div>
        </div>
      </div>

      {/* Configuração de Validade Temporária */}
      <div className="card p-5 border border-white/10 bg-gradient-to-br from-white/5 to-transparent rounded-xl space-y-4">
        <div className="flex items-center gap-2 text-white font-semibold text-base">
          <Clock className="text-scum-orange" size={20} />
          <span>{t('tools.shopDeliveries.attributes.expiration.title', { defaultValue: 'Regras de Validade dos Atributos' })}</span>
        </div>
        
        <p className="text-xs text-white/60 leading-relaxed max-w-2xl">
          {t('tools.shopDeliveries.attributes.expiration.description', { 
            defaultValue: 'Ao ativar a validade temporária, os níveis de atributos adquiridos pelos jogadores voltarão aos valores base pré-compra após o período selecionado expirar.' 
          })}
        </p>

        <div className="flex flex-col md:flex-row md:items-center gap-6 pt-2">
          {/* Switch Toggle */}
          <label className="relative inline-flex items-center cursor-pointer select-none">
            <input
              type="checkbox"
              checked={expirationEnabled}
              onChange={(e) => setExpirationEnabled(e.target.checked)}
              className="sr-only peer"
            />
            <div className="w-11 h-6 bg-white/10 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-scum-orange"></div>
            <span className="ml-3 text-sm font-medium text-white/90">
              {t('tools.shopDeliveries.attributes.expiration.enableLabel', { defaultValue: 'Habilitar expiração temporária dos atributos' })}
            </span>
          </label>

          {/* Duração da validade */}
          {expirationEnabled && (
            <div className="flex items-center gap-3">
              <label htmlFor="expirationDuration" className="text-sm font-medium text-white/70">
                {t('tools.shopDeliveries.attributes.expiration.durationLabel', { defaultValue: 'Duração da validade:' })}
              </label>
              <div className="relative flex items-center max-w-[120px]">
                <input
                  id="expirationDuration"
                  type="text"
                  inputMode="numeric"
                  value={expirationDurationDays}
                  onChange={(e) => {
                    const val = e.target.value.replace(/[^0-9]/g, '');
                    setExpirationDurationDays(val === '' ? 0 : parseInt(val, 10));
                  }}
                  className="w-full pl-3 pr-12 py-1.5 rounded-lg bg-white/5 border border-white/10 text-white text-sm focus:outline-none focus:ring-2 focus:ring-scum-orange"
                  min="1"
                />
                <span className="absolute right-3 text-xs text-white/40 select-none">
                  dias
                </span>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Attributes cards grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {attributesList.map((attr) => (
          <div
            key={attr.key}
            className={`card p-5 border border-white/10 bg-gradient-to-br ${attr.bgGrad} ${attr.borderHover} transition-all duration-200`}
          >
            <div className="flex items-center gap-2 mb-4">
              <div className="p-2 rounded-lg bg-white/5 border border-white/10">
                {attr.icon}
              </div>
              <span className="font-semibold text-white text-base">{attr.label}</span>
            </div>

            <div className="grid grid-cols-2 sm:grid-cols-5 gap-3">
              {attr.levels.map((level) => (
                <div key={level} className="space-y-1">
                  <div className="text-xs text-white/50 font-medium">
                    {t('tools.shopDeliveries.attributes.level', {
                      defaultValue: 'Nível {{level}}',
                      level,
                    })}
                  </div>
                  <div className="relative flex items-center">
                    <input
                      type="text"
                      inputMode="numeric"
                      value={prices[attr.key][level] ?? ''}
                      onChange={(e) => handlePriceChange(attr.key, level, e.target.value)}
                      className="w-full pl-3 pr-8 py-1.5 rounded-lg bg-white/5 border border-white/10 text-white text-sm focus:outline-none focus:ring-2 focus:ring-scum-orange disabled:opacity-60"
                      placeholder="0"
                    />
                    <span className="absolute right-3 text-xs text-white/40 select-none">
                      $
                    </span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        ))}
      </div>

      {/* Sticky Action Bar */}
      <div className="card p-4 flex items-center justify-between border border-white/10 bg-[#0b1220]/80 backdrop-blur-md sticky bottom-4 z-30">
        <div className="text-xs text-white/50">
          {hasChanges() ? (
            <span className="text-amber-400">
              {t('tools.attributes.pending', { defaultValue: 'Você tem alterações não salvas.' })}
            </span>
          ) : (
            <span>{t('tools.shopDeliveries.attributes.noChanges', { defaultValue: 'Sem alterações.' })}</span>
          )}
        </div>

        <div className="flex gap-2">
          <button
            type="button"
            disabled={!hasChanges() || saving}
            onClick={handleRevert}
            className="px-4 py-2 rounded-lg border border-white/15 bg-white/8 text-sm font-medium text-white/90 hover:bg-white/12 hover:border-white/25 disabled:opacity-60 disabled:cursor-not-allowed flex items-center gap-1.5"
          >
            <RotateCcw size={16} />
            {t('tools.shopDeliveries.wallet.removeConfirmTitle', { defaultValue: 'Reverter' })}
          </button>
          <button
            type="button"
            disabled={!hasChanges() || saving}
            onClick={handleSave}
            className="px-4 py-2 rounded-lg border border-scum-orange/60 bg-scum-orange/10 text-sm font-semibold text-scum-orange hover:bg-scum-orange/20 hover:border-scum-orange/80 focus:outline-none focus:ring-2 focus:ring-scum-orange/70 disabled:opacity-60 disabled:cursor-not-allowed flex items-center gap-1.5"
          >
            {saving ? (
              <>
                <RefreshCw size={16} className="animate-spin" />
                {t('common.saving', { defaultValue: 'Salvando...' })}
              </>
            ) : (
              <>
                <Save size={16} />
                {t('common.save', { defaultValue: 'Salvar' })}
              </>
            )}
          </button>
        </div>
      </div>
    </div>
  );
}
