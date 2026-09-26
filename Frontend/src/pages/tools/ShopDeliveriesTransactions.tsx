import { useCallback, useEffect, useMemo, useState } from 'react';
import { useParams } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { ModuleToolPage } from '@/components/tools/ModuleToolPage';
import { getShopAdminWalletTransactions, type WalletTxItem } from '@/services/shopAdmin';

export default function ShopDeliveriesTransactions() {
  const { t, i18n } = useTranslation();
  const params = useParams();
  const steamId = (params as any).steamId as string | undefined;

  const [limit, setLimit] = useState(100);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [items, setItems] = useState<WalletTxItem[]>([]);
  const [count, setCount] = useState<number | null>(null);
  const [hoveredMetaTxId, setHoveredMetaTxId] = useState<string | null>(null);

  const fmtNumber = useMemo(() => {
    try {
      return new Intl.NumberFormat(i18n.language);
    } catch {
      return new Intl.NumberFormat('en');
    }
  }, [i18n.language]);

  const fmtDateTime = useMemo(() => {
    try {
      return new Intl.DateTimeFormat(i18n.language, {
        year: 'numeric',
        month: '2-digit',
        day: '2-digit',
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit',
      });
    } catch {
      return new Intl.DateTimeFormat('en', {
        year: 'numeric',
        month: '2-digit',
        day: '2-digit',
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit',
      });
    }
  }, [i18n.language]);

  const formatCreatedAt = useCallback(
    (raw: string) => {
      const d = new Date(raw);
      if (!Number.isNaN(d.getTime())) return fmtDateTime.format(d);
      return raw;
    },
    [fmtDateTime]
  );

  const formatDelta = useCallback(
    (raw: number) => {
      const v = Number(raw);
      if (!Number.isFinite(v)) return String(raw);
      const abs = fmtNumber.format(Math.abs(v));
      return `${v >= 0 ? '+' : '-'}${abs}`;
    },
    [fmtNumber]
  );

  const getReasonLabel = useCallback(
    (reason: string) => {
      const key = `tools.shopDeliveries.transactions.reasons.${reason}`;
      const translated = t(key);
      return translated && translated !== key ? translated : reason;
    },
    [t]
  );

  const getRefTypeLabel = useCallback(
    (refType: string | null) => {
      if (!refType) return '';
      const key = `tools.shopDeliveries.transactions.refTypes.${refType}`;
      const translated = t(key);
      return translated && translated !== key ? translated : refType;
    },
    [t]
  );

  const shortId = useCallback((raw: string, max = 12) => {
    const v = (raw || '').trim();
    if (!v) return '';
    if (v.length <= max) return v;
    return `${v.slice(0, Math.max(6, max - 3))}...`;
  }, []);

  const getMetaKeyLabel = useCallback(
    (k: string) => {
      const key = `tools.shopDeliveries.transactions.metaKeys.${k}`;
      const translated = t(key);
      return translated && translated !== key ? translated : k;
    },
    [t]
  );

  const formatMetaValueShort = useCallback(
    (v: any) => {
      if (v == null) return '';
      if (typeof v === 'number') return fmtNumber.format(v);
      if (typeof v === 'boolean') return v ? 'true' : 'false';
      const s = typeof v === 'string' ? v : JSON.stringify(v);
      return s.length > 18 ? shortId(s, 18) : s;
    },
    [fmtNumber, shortId]
  );

  const formatMetaValueFull = useCallback(
    (v: any) => {
      if (v == null) return '';
      if (typeof v === 'number') return fmtNumber.format(v);
      if (typeof v === 'boolean') return v ? 'true' : 'false';
      if (typeof v === 'string') return v;
      try {
        return JSON.stringify(v, null, 2);
      } catch {
        return String(v);
      }
    },
    [fmtNumber]
  );

  const formatMetaSummary = useCallback(
    (meta: Record<string, any> | null) => {
      if (!meta || typeof meta !== 'object') return '';
      const entries = Object.entries(meta).slice(0, 6);
      return entries
        .map(([k, v]) => `${k}=${typeof v === 'string' ? v : JSON.stringify(v)}`)
        .join(' | ');
    },
    []
  );

  const formatMetaFull = useCallback((meta: Record<string, any> | null) => {
    if (!meta) return '';
    try {
      return JSON.stringify(meta, null, 2);
    } catch {
      return String(meta);
    }
  }, []);

  const getMetaOrderedEntries = useCallback((meta: Record<string, any>) => {
    const priorityKeys = [
      'order_id',
      'code',
      'template_vehicle_entity_id',
      'hours_to_pay',
      'hours_total',
      'last_paid_hours',
      'points_per_hour',
      'rule_id',
    ];

    const entries = Object.entries(meta);
    const pri: [string, any][] = [];
    const rest: [string, any][] = [];

    for (const [k, v] of entries) {
      if (priorityKeys.includes(k)) pri.push([k, v]);
      else rest.push([k, v]);
    }

    return [...pri, ...rest];
  }, []);

  const getMetaChips = useCallback((meta: Record<string, any> | null) => {
    if (!meta || typeof meta !== 'object') return [] as { k: string; v: string }[];

    const priorityKeys = [
      'order_id',
      'code',
      'template_vehicle_entity_id',
      'hours_to_pay',
      'hours_total',
      'last_paid_hours',
      'points_per_hour',
      'rule_id',
    ];

    const chips: { k: string; v: string }[] = [];
    const pushChip = (k: string, v: any) => {
      if (chips.length >= 4) return;
      if (v == null) return;
      const s = typeof v === 'string' ? v : JSON.stringify(v);
      chips.push({ k, v: s });
    };

    for (const k of priorityKeys) {
      if (k in meta) pushChip(k, (meta as any)[k]);
    }

    if (chips.length < 4) {
      for (const [k, v] of Object.entries(meta)) {
        if (priorityKeys.includes(k)) continue;
        pushChip(k, v);
      }
    }

    return chips;
  }, []);

  const canLoadMore = useMemo(() => {
    if (count == null) return true;
    return items.length < count;
  }, [count, items.length]);

  useEffect(() => {
    if (!steamId) return;
    let cancelled = false;
    setBusy(true);
    setError(null);
    void (async () => {
      try {
        const res = await getShopAdminWalletTransactions(steamId, limit);
        if (cancelled) return;
        if (!res.success) {
          setError(res.message || res.error || t('tools.shopDeliveries.transactions.errors.requestFailed'));
          setItems([]);
          setCount(null);
          return;
        }
        setItems(res.data.items || []);
        setCount(res.data.count ?? null);
      } catch (e: any) {
        if (cancelled) return;
        setError(e?.message || t('tools.shopDeliveries.transactions.errors.requestFailed'));
      } finally {
        if (!cancelled) setBusy(false);
      }
    })();

    return () => {
      cancelled = true;
    };
  }, [steamId, limit]);

  return (
    <ModuleToolPage title={t('tools.shopDeliveries.transactions.title', { defaultValue: 'Wallet statement' })}>
      <div className="card p-4 space-y-3">
        <div className="text-xs text-white/60">
          {steamId ? (
            <div>
              {t('tools.shopDeliveries.transactions.steamId', {
                defaultValue: 'Steam ID: {{steam_id}}',
                steam_id: steamId,
              })}
            </div>
          ) : (
            <div>{t('tools.shopDeliveries.transactions.missingSteamId', { defaultValue: 'Missing Steam ID.' })}</div>
          )}
        </div>

        {error && <div className="text-sm text-red-400">{error}</div>}

        <div className="rounded-lg border border-white/10 overflow-auto">
          <div className="min-w-[920px]">
            <div className="grid grid-cols-[200px_120px_200px_120px_1fr] gap-2 px-3 py-2 text-xs uppercase text-white/40 border-b border-white/10">
              <div>{t('tools.shopDeliveries.transactions.table.createdAt', { defaultValue: 'Created at' })}</div>
              <div>{t('tools.shopDeliveries.transactions.table.delta', { defaultValue: 'Delta' })}</div>
              <div>{t('tools.shopDeliveries.transactions.table.reason', { defaultValue: 'Reason' })}</div>
              <div>{t('tools.shopDeliveries.transactions.table.ref', { defaultValue: 'Ref' })}</div>
              <div>{t('tools.shopDeliveries.transactions.table.meta', { defaultValue: 'Meta' })}</div>
            </div>

            {busy ? (
              <div className="p-3 text-sm text-white/60">{t('common.loading', { defaultValue: 'Loading...' })}</div>
            ) : items.length === 0 ? (
              <div className="p-3 text-sm text-white/60">
                {t('tools.shopDeliveries.transactions.empty', { defaultValue: 'No transactions.' })}
              </div>
            ) : (
              <div className="divide-y divide-white/10">
                {items.map((tx) => {
                  const delta = Number(tx.delta);
                  const deltaColor = delta >= 0 ? 'text-emerald-400' : 'text-red-400';
                  const refTypeLabel = getRefTypeLabel(tx.ref_type);
                  const refIdRaw = tx.ref_id || '';
                  const refIdShort = shortId(refIdRaw, 14);
                  const refFull = [tx.ref_type, tx.ref_id].filter(Boolean).join(':');
                  const metaSummary = formatMetaSummary(tx.meta);
                  const metaFull = formatMetaFull(tx.meta);
                  const metaChips = getMetaChips(tx.meta);
                  const metaKeysCount = tx.meta && typeof tx.meta === 'object' ? Object.keys(tx.meta).length : 0;
                  const createdAt = formatCreatedAt(tx.created_at);
                  const deltaLabel = formatDelta(delta);
                  const reasonLabel = getReasonLabel(tx.reason);

                  return (
                    <div
                      key={tx.tx_id}
                      className="grid grid-cols-[200px_120px_200px_120px_1fr] gap-2 px-3 py-2 text-sm"
                    >
                      <div className="text-white/70 tabular-nums" title={tx.created_at}>
                        {createdAt}
                      </div>
                      <div className={deltaColor + ' tabular-nums'} title={String(delta)}>
                        {deltaLabel}
                      </div>
                      <div className="text-white/80 truncate" title={tx.reason}>
                        {reasonLabel}
                      </div>
                      <div className="text-white/60" title={refFull}>
                        {refFull ? (
                          <div className="flex flex-col leading-tight min-w-0">
                            <div className="text-[10px] uppercase tracking-wide text-white/40 truncate">
                              {refTypeLabel || tx.ref_type || '—'}
                            </div>
                            <div className="text-xs text-white/70 font-mono truncate">{refIdShort || '—'}</div>
                          </div>
                        ) : (
                          '—'
                        )}
                      </div>
                      <div
                        className="text-white/50 text-xs relative"
                        onMouseEnter={() => setHoveredMetaTxId(tx.tx_id)}
                        onMouseLeave={() => setHoveredMetaTxId((prev) => (prev === tx.tx_id ? null : prev))}
                      >
                        {metaKeysCount === 0 ? (
                          <span className="truncate">—</span>
                        ) : (
                          <div className="flex flex-wrap gap-1 items-center">
                            {metaChips.map((c) => (
                              <span
                                key={`${tx.tx_id}_${c.k}`}
                                className="px-1.5 py-0.5 rounded-md border border-white/10 bg-white/5 text-white/70 max-w-[180px] truncate"
                              >
                                {getMetaKeyLabel(c.k)}={formatMetaValueShort(c.v)}
                              </span>
                            ))}
                            {metaKeysCount > metaChips.length && (
                              <span className="text-white/40">
                                {t('tools.shopDeliveries.transactions.meta.more', {
                                  defaultValue: '+{{count}} more',
                                  count: metaKeysCount - metaChips.length,
                                })}
                              </span>
                            )}
                          </div>
                        )}

                        {hoveredMetaTxId === tx.tx_id && tx.meta && typeof tx.meta === 'object' && (
                          <div
                            className="absolute right-0 top-full mt-2 w-[420px] max-w-[80vw] rounded-lg bg-black/90 px-3 py-2 text-xs text-white shadow-lg border border-white/20 z-50"
                            style={{ filter: 'drop-shadow(0 4px 6px rgba(0,0,0,0.5))' }}
                          >
                            <div className="max-h-64 overflow-auto space-y-1">
                              {getMetaOrderedEntries(tx.meta).map(([k, v]) => (
                                <div key={k} className="grid grid-cols-[170px_1fr] gap-2">
                                  <div className="text-white/70 truncate" title={k}>
                                    {getMetaKeyLabel(k)}
                                    <span className="ml-1 text-white/30">({k})</span>
                                  </div>
                                  <div className="text-white/90 font-mono whitespace-pre-wrap break-words">
                                    {formatMetaValueFull(v)}
                                  </div>
                                </div>
                              ))}
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
        </div>

        <div className="flex items-center justify-between gap-2">
          <div className="text-xs text-white/50">
            {count != null
              ? t('tools.shopDeliveries.transactions.count', {
                  defaultValue: 'Showing {{shown}} of {{count}}',
                  shown: items.length,
                  count,
                })
              : t('tools.shopDeliveries.transactions.countUnknown', {
                  defaultValue: 'Showing {{shown}}',
                  shown: items.length,
                })}
          </div>

          <button
            type="button"
            disabled={!steamId || busy || !canLoadMore}
            onClick={() => setLimit((v) => v + 100)}
            className="px-3 py-2 rounded-lg border border-white/15 bg-white/8 text-sm font-medium text-white/90 shadow-sm hover:text-white hover:bg-white/12 hover:border-white/25 focus:outline-none focus:ring-2 focus:ring-scum-orange/70 disabled:opacity-70 disabled:cursor-not-allowed"
          >
            {t('tools.shopDeliveries.transactions.loadMore', { defaultValue: 'Load more' })}
          </button>
        </div>
      </div>
    </ModuleToolPage>
  );
}
