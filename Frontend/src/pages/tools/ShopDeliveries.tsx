import { useEffect, useMemo, useRef, useState } from 'react';
import { useTranslation } from 'react-i18next';
import Swal from 'sweetalert2';
import { Download, Info, RotateCcw, RefreshCw, Save, Upload, List, PlusCircle, X } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { ModuleToolPage } from '@/components/tools/ModuleToolPage';
import SearchBar from '@/components/ui/SearchBar';
import Kits from './Kits';
import ShopNotificationsTab from '@/pages/settings/tabs/ShopNotificationsTab';
import AttributesConfigTab from './AttributesConfigTab';
import RaidWebhookConfigTab from './RaidWebhookConfigTab';
import WantedBountyConfigTab from './WantedBountyConfigTab';
import { getAllPlayers, type AllPlayer } from '@/services/server';
import {
  dryRunBaseMaterialUpgrade,
  getAdminFlagsOwners,
  scheduleBaseMaterialUpgrade,
  type AdminFlagOwnerItem,
  type BaseMaterialDryRunResponse,
} from '@/services/baseUpgradesAdmin';
import {
  getVehiclesAdminCatalog,
  patchVehicleAdminCatalogItem,
  resetVehicleAdminTemplates,
  syncVehicleAdminTemplates,
  uploadVehicleAdminCatalogImage,
  type AdminVehicleTemplatesResetRequest,
  type AdminVehicleTemplatesSyncResponse,
  type PatchVehicleAdminCatalogRequest,
  type VehicleAdminCatalogItem,
} from '@/services/vehicles';
import {
  adjustShopAdminWallet,
  clearShopAdminCatalog,
  getShopAdminCatalog,
  getShopAdminRewardsPlaytimeRules,
  getShopAdminRewardsPlaytimeRuleTargets,
  getShopAdminWalletTransactions,
  getShopAdminRewardsPlaytimeConfig,
  getRegisteredPlayers,
  getShopWalletBalance,
  importShopAdminCatalog,
  patchShopAdminRewardsPlaytimeRule,
  patchShopAdminCatalogItem,
  postShopAdminCatalog,
  postShopAdminRewardsPlaytimeRule,
  postShopAdminRewardsPlaytimeRuleTarget,
  setShopAdminScannerChest,
  syncShopAdminScanner,
  deleteShopAdminRewardsPlaytimeRuleTarget,
  type PatchShopAdminCatalogRequest,
  type ShopAdminCatalogItem,
  type ShopAdminRewardsPlaytimeConfig,
  type ShopAdminRewardsPlaytimeRule,
  type RegisteredPlayerItem,
  type WalletTxItem,
} from '@/services/shopAdmin';

function getApiErrorMessage(res: { success: boolean; message?: string } & Record<string, any>): string | null {
  const anyRes: any = res;
  const fromData = anyRes?.data?.error || anyRes?.data?.message;
  const base = anyRes?.error || anyRes?.message || fromData;
  const code = anyRes?.code || anyRes?.data?.code;
  const details = anyRes?.details || anyRes?.data?.details;

  const baseText = typeof base === 'string' ? base : undefined;
  const codeText = typeof code === 'string' ? code : undefined;

  if (baseText && codeText) return `${codeText}: ${baseText}`;
  if (baseText) return baseText;
  if (codeText) return codeText;
  if (details && typeof details === 'string') return details;
  return null;
}

function toNumOrNull(raw: string): number | null {
  const v = raw.trim();
  if (v === '') return null;
  const n = Number(v);
  return Number.isFinite(n) ? n : null;
}

function toNum(raw: string): number {
  const n = Number(raw);
  return Number.isFinite(n) ? n : 0;
}

type DraftRow = {
  display_name: string;
  catalog_enabled: boolean;
  offer_enabled: boolean;
  price: string;
  qty: string;
  max_per_order: string;
  max_per_day: string;
};

type DraftVehicleRow = {
  display_name: string;
  enabled: boolean;
  price: string;
};

type CatalogSnapshotV1 = {
  schema: 'shop_catalog_snapshot_v1';
  exportedAt: string;
  items: Array<{
    code: number;
    display_name: string;
    setup: string;
    catalog_enabled: boolean;
    offer_enabled: boolean;
    price: number;
    qty: number;
    max_per_order: number | null;
    max_per_day: number | null;
  }>;
};

function clampDecimal(raw: string, decimals: number) {
  const cleaned = raw.replace(/[^0-9.]/g, '');
  const [intPart, fracPartRaw] = cleaned.split('.', 2);
  const fracPart = fracPartRaw ? fracPartRaw.slice(0, decimals) : undefined;
  if (fracPart === undefined) return intPart;
  return `${intPart}.${fracPart}`;
}

function clampInt(raw: string) {
  return raw.replace(/[^0-9]/g, '');
}

function parseIdList(raw: string): number[] {
  const parts = raw
    .split(/[\s,;]+/)
    .map((x) => x.trim())
    .filter(Boolean);
  const ids: number[] = [];
  for (const p of parts) {
    const n = Number(p);
    if (Number.isFinite(n) && Number.isInteger(n) && n >= 0) ids.push(n);
  }
  return Array.from(new Set(ids));
}

function safeJsonParse(raw: string) {
  try {
    return { ok: true as const, value: JSON.parse(raw) };
  } catch (e: any) {
    return { ok: false as const, error: e?.message || 'Invalid JSON' };
  }
}

function downloadJson(filename: string, obj: any) {
  const blob = new Blob([JSON.stringify(obj, null, 2)], { type: 'application/json;charset=utf-8' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(url);
}

function isSnapshotV1(x: any): x is CatalogSnapshotV1 {
  if (!x || typeof x !== 'object') return false;
  if (x.schema !== 'shop_catalog_snapshot_v1') return false;
  if (!Array.isArray(x.items)) return false;
  return true;
}

function buildDraft(item: ShopAdminCatalogItem): DraftRow {
  // Backend pode retornar display_name ou name — preferir display_name quando válido
  const rawDisplay = (item as any).display_name;
  const displayName = rawDisplay != null && rawDisplay !== 'None' && rawDisplay !== ''
    ? String(rawDisplay)
    : (item.name ?? '');
  return {
    display_name: displayName,
    catalog_enabled: Boolean(item.catalog_enabled),
    offer_enabled: Boolean(item.offer_enabled),
    price: String(item.price ?? 0),
    qty: String(item.qty ?? 1),
    max_per_order: item.max_per_order == null ? '' : String(item.max_per_order),
    max_per_day: item.max_per_day == null ? '' : String(item.max_per_day),
  };
}

function diffPayload(original: ShopAdminCatalogItem, draft: DraftRow): PatchShopAdminCatalogRequest {
  const payload: PatchShopAdminCatalogRequest = {};

  // Usar display_name se disponível, senão name
  const rawDisplay = (original as any).display_name;
  const originalName = rawDisplay != null && rawDisplay !== 'None' && rawDisplay !== ''
    ? String(rawDisplay)
    : (original.name ?? '');
  if (originalName !== draft.display_name) payload.display_name = draft.display_name;

  if (Boolean(original.catalog_enabled) !== draft.catalog_enabled) payload.catalog_enabled = draft.catalog_enabled;
  if (Boolean(original.offer_enabled) !== draft.offer_enabled) payload.offer_enabled = draft.offer_enabled;

  const price = toNum(draft.price);
  if ((original.price ?? 0) !== price) payload.price = price;

  const qty = toNum(draft.qty);
  if ((original.qty ?? 0) !== qty) payload.qty = qty;

  const mpo = toNumOrNull(draft.max_per_order);
  if ((original.max_per_order ?? null) !== mpo) payload.max_per_order = mpo;

  const mpd = toNumOrNull(draft.max_per_day);
  if ((original.max_per_day ?? null) !== mpd) payload.max_per_day = mpd;

  return payload;
}

function hasChanges(payload: PatchShopAdminCatalogRequest) {
  return Object.keys(payload).length > 0;
}

function computeTriState(total: number, checkedCount: number) {
  const all = total > 0 && checkedCount === total;
  const none = checkedCount === 0;
  return {
    checked: all,
    indeterminate: !all && !none,
  };
}

export default function ShopDeliveries() {
  const { t } = useTranslation();
  const navigate = useNavigate();

  const [pendingImport, setPendingImport] = useState<CatalogSnapshotV1 | null>(null);

  const exportCatalog = () => {
    const now = new Date();
    const stamp = now.toISOString().slice(0, 19).replace(/[:T]/g, '-');
    const snapshot: CatalogSnapshotV1 = {
      schema: 'shop_catalog_snapshot_v1',
      exportedAt: now.toISOString(),
      items: items.map((it) => {
        const d = drafts[it.code] || buildDraft(it);
        return {
          code: it.code,
          display_name: d.display_name,
          setup: it.setup,
          catalog_enabled: d.catalog_enabled,
          offer_enabled: d.offer_enabled,
          price: toNum(d.price),
          qty: toNum(d.qty),
          max_per_order: toNumOrNull(d.max_per_order),
          max_per_day: toNumOrNull(d.max_per_day),
        };
      }),
    };
    downloadJson(`shop-catalog-${stamp}.json`, snapshot);
  };

  const buildDraftFromSnapshotRow = (row: CatalogSnapshotV1['items'][number]): DraftRow => {
    return {
      display_name: row.display_name ?? '',
      catalog_enabled: Boolean(row.catalog_enabled),
      offer_enabled: Boolean(row.offer_enabled),
      price: String(row.price ?? 0),
      qty: String(row.qty ?? 1),
      max_per_order: row.max_per_order == null ? '' : String(row.max_per_order),
      max_per_day: row.max_per_day == null ? '' : String(row.max_per_day),
    };
  };

  const runBackendImport = async (snapshot: CatalogSnapshotV1) => {
    const res = await importShopAdminCatalog({
      schema: snapshot.schema,
      exportedAt: snapshot.exportedAt,
      mode: 'merge',
      dry_run: false,
      items: snapshot.items.map((it) => ({
        code: it.code,
        display_name: it.display_name,
        setup: it.setup,
        catalog_enabled: Boolean(it.catalog_enabled),
        offer_enabled: Boolean(it.offer_enabled),
        price: Number(it.price ?? 0),
        qty: Number(it.qty ?? 1),
        max_per_order: it.max_per_order ?? null,
        max_per_day: it.max_per_day ?? null,
      })),
    });

    if (!res.success) {
      throw new Error(getApiErrorMessage(res as any) || 'Import failed');
    }

    const data: any = (res as any).data;
    const created = Number(data?.created ?? 0);
    const updated = Number(data?.updated ?? 0);
    const ignored = Number(data?.ignored ?? 0);
    const errors = Array.isArray(data?.errors) ? data.errors : [];

    const topErrors = errors
      .slice(0, 5)
      .map((e: any) => `${e?.code ?? '?'}: ${e?.reason ?? 'ERROR'}`)
      .join(', ');
    const more = errors.length > 5 ? ` (+${errors.length - 5})` : '';

    await Swal.fire({
      icon: errors.length > 0 ? 'warning' : 'success',
      title: t('common.success', { defaultValue: 'Success' }),
      text:
        `Created: ${created} | Updated: ${updated} | Ignored: ${ignored}` +
        (errors.length > 0 ? ` | Errors: ${topErrors}${more}` : ''),
      confirmButtonColor: '#f97316',
    });

    await load();
  };

  const applyImportSnapshot = async (snapshot: CatalogSnapshotV1) => {
    const byCode = new Map<number, ShopAdminCatalogItem>();
    for (const it of items) byCode.set(it.code, it);

    const changedCodes: number[] = [];
    const ignoredCodes: number[] = [];
    const toApply: Array<{ code: number; draft: DraftRow }> = [];

    for (const row of snapshot.items) {
      const code = Number((row as any)?.code);
      if (!Number.isFinite(code)) continue;
      const current = byCode.get(code);
      if (!current) {
        ignoredCodes.push(code);
        continue;
      }

      const nextDraft = buildDraftFromSnapshotRow(row);
      const payload = diffPayload(current, nextDraft);
      if (hasChanges(payload)) {
        changedCodes.push(code);
        toApply.push({ code, draft: nextDraft });
      }
    }

    const changedCount = changedCodes.length;
    const ignoredCount = ignoredCodes.length;
    const sample = changedCodes.slice(0, 12).map((c) => `#${c}`).join(', ');
    const more = changedCount > 12 ? ` +${changedCount - 12}` : '';

    const confirm = await Swal.fire({
      icon: 'question',
      title: t('tools.shopDeliveries.import.previewTitle', { defaultValue: 'Preview import' }),
      text: t('tools.shopDeliveries.import.previewText', {
        defaultValue: 'Changes: {{changed}} | Ignored (missing codes): {{ignored}}',
        changed: changedCount,
        ignored: ignoredCount,
      }),
      footer:
        changedCount > 0
          ? t('tools.shopDeliveries.import.previewList', {
              defaultValue: 'Sample changed codes: {{codes}}',
              codes: sample + more,
            })
          : undefined,
      showCancelButton: true,
      confirmButtonColor: '#f97316',
      cancelButtonColor: '#6b7280',
      confirmButtonText: t('tools.shopDeliveries.import.apply', { defaultValue: 'Apply to draft' }),
      cancelButtonText: t('common.cancel', { defaultValue: 'Cancel' }),
      showDenyButton: true,
      denyButtonColor: '#16a34a',
      denyButtonText: t('tools.shopDeliveries.import.applyAndSave', { defaultValue: 'Apply & save' }),
    });
    if (!confirm.isConfirmed && !confirm.isDenied) return;

    setDrafts((prev) => {
      const next = { ...prev };
      for (const x of toApply) {
        next[x.code] = x.draft;
      }
      return next;
    });

    setPendingImport(null);

    if (confirm.isDenied) {
      void Swal.fire({
        title: t('common.loading', { defaultValue: 'Loading...' }),
        allowOutsideClick: false,
        allowEscapeKey: false,
        didOpen: () => {
          Swal.showLoading();
        },
      });

      try {
        await runBackendImport(snapshot);
      } catch (e: any) {
        await Swal.fire({
          icon: 'error',
          title: t('common.error', { defaultValue: 'Error' }),
          text: e?.message || t('tools.shopDeliveries.import.loadError', { defaultValue: 'Failed to load catalog for import.' }),
          confirmButtonColor: '#f97316',
        });
      } finally {
        Swal.close();
      }
      return;
    }

    await Swal.fire({
      icon: 'success',
      title: t('common.success', { defaultValue: 'Success' }),
      text: t('tools.shopDeliveries.import.applied', { defaultValue: 'Imported changes applied to draft. Review and click Save.' }),
      confirmButtonColor: '#f97316',
    });
  };

  const importCatalog = async () => {
    const picked = await Swal.fire({
      title: t('tools.shopDeliveries.import.title', { defaultValue: 'Import catalog' }),
      text: t('tools.shopDeliveries.import.pickFile', { defaultValue: 'Choose a .json file to import.' }),
      input: 'file',
      inputAttributes: {
        accept: 'application/json,.json',
      },
      showCancelButton: true,
      confirmButtonColor: '#f97316',
      cancelButtonColor: '#6b7280',
      confirmButtonText: t('tools.shopDeliveries.import.confirm', { defaultValue: 'Import' }),
      cancelButtonText: t('common.cancel', { defaultValue: 'Cancel' }),
    });
    if (!picked.isConfirmed) return;
    const file = picked.value as File | null;
    if (!file) return;

    const raw = await file.text();
    const parsed = safeJsonParse(raw);
    if (!parsed.ok) {
      await Swal.fire({
        icon: 'error',
        title: t('common.error', { defaultValue: 'Error' }),
        text: parsed.error,
        confirmButtonColor: '#f97316',
      });
      return;
    }

    const data = parsed.value;
    if (!isSnapshotV1(data)) {
      await Swal.fire({
        icon: 'error',
        title: t('common.error', { defaultValue: 'Error' }),
        text: t('tools.shopDeliveries.import.invalidSchema', {
          defaultValue: 'Invalid schema. Expected shop_catalog_snapshot_v1.',
        }),
        confirmButtonColor: '#f97316',
      });
      return;
    }

    setPendingImport(data);

    if (items.length === 0) {
      void Swal.fire({
        title: t('common.loading', { defaultValue: 'Loading...' }),
        text: t('tools.shopDeliveries.import.loadingCatalog', { defaultValue: 'Loading current catalog to apply import...' }),
        allowOutsideClick: false,
        allowEscapeKey: false,
        didOpen: () => {
          Swal.showLoading();
        },
      });

      try {
        await runBackendImport(data);
      } catch (e: any) {
        await Swal.fire({
          icon: 'error',
          title: t('common.error', { defaultValue: 'Error' }),
          text: e?.message || t('tools.shopDeliveries.import.loadError', { defaultValue: 'Failed to load catalog for import.' }),
          confirmButtonColor: '#f97316',
        });
      } finally {
        Swal.close();
      }

      return;
    }

    await applyImportSnapshot(data);
  };

  const HeaderWithHelp = ({ labelKey, labelDefault, helpKey, helpDefault }: any) => (
    <div className="min-w-0 flex items-center gap-1">
      <span className="truncate">{t(labelKey, { defaultValue: labelDefault })}</span>
      <span className="text-white/30" title={t(helpKey, { defaultValue: helpDefault })}>
        <Info size={14} />
      </span>
    </div>
  );

  const [query, setQuery] = useState('');
  const [loading, setLoading] = useState(false);
  const [items, setItems] = useState<ShopAdminCatalogItem[]>([]);
  const [error, setError] = useState<string | null>(null);

  const [drafts, setDrafts] = useState<Record<number, DraftRow>>({});
  const [savingCode, setSavingCode] = useState<number | null>(null);

  const [bulkBusy, setBulkBusy] = useState(false);
  const [bulkDone, setBulkDone] = useState(0);
  const [bulkTotal, setBulkTotal] = useState(0);

  const [scannerChestId, setScannerChestId] = useState('');
  const [scannerBusy, setScannerBusy] = useState(false);

  const [section, setSection] = useState<'catalog' | 'vehicles' | 'wallet' | 'base_upgrades' | 'kits' | 'shop_notifications' | 'attributes' | 'raid_webhooks' | 'wanted_bounty'>('catalog');

  const [ownersQuery, setOwnersQuery] = useState('');
  const [ownersBusy, setOwnersBusy] = useState(false);
  const [ownersError, setOwnersError] = useState<string | null>(null);
  const [ownersPage, setOwnersPage] = useState(1);
  const [ownersPageSize, setOwnersPageSize] = useState(50);
  const [ownersTotal, setOwnersTotal] = useState(0);
  const [ownersItems, setOwnersItems] = useState<AdminFlagOwnerItem[]>([]);
  const [selectedFlagId, setSelectedFlagId] = useState<number | null>(null);

  const [upgradeTargetLevel, setUpgradeTargetLevel] = useState(5);
  const [upgradeFallbackLowest, setUpgradeFallbackLowest] = useState(true);
  const [upgradeRunNowIfOffline, setUpgradeRunNowIfOffline] = useState(true);
  const [upgradeAutoEnrichWhitelist, setUpgradeAutoEnrichWhitelist] = useState(true);

  const [dryRunBusy, setDryRunBusy] = useState(false);
  const [dryRunError, setDryRunError] = useState<string | null>(null);
  const [dryRunResult, setDryRunResult] = useState<BaseMaterialDryRunResponse | null>(null);
  const [scheduleBusy, setScheduleBusy] = useState(false);

  const [templatesLastError, setTemplatesLastError] = useState<string | null>(null);
  const [templatesIdsRaw, setTemplatesIdsRaw] = useState('');
  const [templatesBusy, setTemplatesBusy] = useState(false);
  const [templatesLastSync, setTemplatesLastSync] = useState<AdminVehicleTemplatesSyncResponse | null>(null);

  const loadOwners = async (page = ownersPage, pageSize = ownersPageSize) => {
    setOwnersBusy(true);
    setOwnersError(null);
    try {
      const res = await getAdminFlagsOwners(page, pageSize);
      if (res.success && res.data) {
        setOwnersItems(res.data.flags || []);
        setOwnersTotal(Number(res.data.total ?? 0));
        setOwnersPage(Number(res.data.page ?? page));
        setOwnersPageSize(Number(res.data.page_size ?? pageSize));
      } else {
        setOwnersItems([]);
        setOwnersTotal(0);
        setOwnersError(getApiErrorMessage(res as any) || 'Failed to load flags');
      }
    } catch (e: any) {
      setOwnersItems([]);
      setOwnersTotal(0);
      setOwnersError(e?.response?.data?.error || e?.response?.data?.message || e?.message || 'Failed to load flags');
    } finally {
      setOwnersBusy(false);
    }
  };

  const ownersFiltered = useMemo(() => {
    const q = ownersQuery.trim().toLowerCase();
    if (!q) return ownersItems;
    return ownersItems.filter((it) => {
      const hay = [it.flag_id, it.owner, it.owner_type, it.elements, it.last_seen_at].join(' ').toLowerCase();
      return hay.includes(q);
    });
  }, [ownersItems, ownersQuery]);

  const ownersTotalPages = useMemo(() => {
    const ps = Math.max(1, Number(ownersPageSize) || 50);
    return Math.max(1, Math.ceil((ownersTotal || 0) / ps));
  }, [ownersTotal, ownersPageSize]);

  const runDryRun = async () => {
    if (!selectedFlagId) return;
    if (!Number.isFinite(upgradeTargetLevel) || upgradeTargetLevel < 1 || upgradeTargetLevel > 5) {
      await Swal.fire({
        icon: 'error',
        title: t('common.error', { defaultValue: 'Error' }),
        text: t('tools.shopDeliveries.baseUpgrades.validation.level', { defaultValue: 'Target level must be between 1 and 5.' }),
        confirmButtonColor: '#f97316',
      });
      return;
    }

    setDryRunBusy(true);
    setDryRunError(null);
    try {
      const res = await dryRunBaseMaterialUpgrade({
        flag_id: selectedFlagId,
        target_level: upgradeTargetLevel,
        fallback_lowest: upgradeFallbackLowest,
        auto_enrich_whitelist: upgradeAutoEnrichWhitelist,
      });
      setDryRunResult(res);
      if (!res.success) {
        setDryRunError(getApiErrorMessage(res as any) || 'Dry-run failed');
      }
    } catch (e: any) {
      setDryRunResult(null);
      setDryRunError(e?.response?.data?.error || e?.response?.data?.message || e?.message || 'Dry-run failed');
    } finally {
      setDryRunBusy(false);
    }
  };

  const runSchedule = async () => {
    if (!selectedFlagId) return;
    if (!dryRunResult?.success || !dryRunResult.data) {
      await Swal.fire({
        icon: 'info',
        title: t('common.info', { defaultValue: 'Info' }),
        text: t('tools.shopDeliveries.baseUpgrades.validation.previewFirst', { defaultValue: 'Run the dry-run preview before scheduling.' }),
        confirmButtonColor: '#f97316',
      });
      return;
    }

    const stats = dryRunResult.data.stats;
    const confirm = await Swal.fire({
      icon: 'warning',
      title: t('tools.shopDeliveries.baseUpgrades.schedule.confirmTitle', { defaultValue: 'Schedule base upgrade?' }),
      text:
        t('tools.shopDeliveries.baseUpgrades.schedule.confirmText', {
          defaultValue:
            'This will NOT restart the server. It will apply on the next automatic restart. To change: {{toChange}} | Already target: {{already}} | No mapping: {{noMapping}}',
          toChange: Number(stats?.to_change ?? 0),
          already: Number(stats?.already_target ?? 0),
          noMapping: Number(stats?.no_mapping ?? 0),
        }) as any,
      showCancelButton: true,
      confirmButtonColor: '#f97316',
      cancelButtonColor: '#6b7280',
      confirmButtonText: t('tools.shopDeliveries.baseUpgrades.schedule.confirmBtn', { defaultValue: 'Schedule' }),
      cancelButtonText: t('common.cancel', { defaultValue: 'Cancel' }),
    });
    if (!confirm.isConfirmed) return;

    setScheduleBusy(true);
    try {
      const res = await scheduleBaseMaterialUpgrade({
        flag_id: selectedFlagId,
        target_level: upgradeTargetLevel,
        fallback_lowest: upgradeFallbackLowest,
        run_now_if_offline: upgradeRunNowIfOffline,
      });

      if (!res.success || !res.data) {
        await Swal.fire({
          icon: 'error',
          title: t('common.error', { defaultValue: 'Error' }),
          text: getApiErrorMessage(res as any) || 'Failed to schedule',
          confirmButtonColor: '#f97316',
        });
        return;
      }

      const executedNow = Boolean(res.data.executed_now);
      if (!executedNow) {
        const dedup = Boolean((res.data as any).deduplicated);
        await Swal.fire({
          icon: 'success',
          title: t('common.success', { defaultValue: 'Success' }),
          text: t('tools.shopDeliveries.baseUpgrades.schedule.scheduled', {
            defaultValue: 'Scheduled. It will apply on the next automatic restart. Job: {{job}}',
            job: res.data.job_id,
          }) + (dedup ? ` (${t('tools.shopDeliveries.baseUpgrades.schedule.deduplicated', { defaultValue: 'deduplicated' })})` : ''),
          confirmButtonColor: '#f97316',
        });
      } else {
        const rr = res.data.run_result;
        await Swal.fire({
          icon: rr && Number(rr.failed ?? 0) > 0 ? 'warning' : 'success',
          title: t('common.success', { defaultValue: 'Success' }),
          text: t('tools.shopDeliveries.baseUpgrades.schedule.executedNow', {
            defaultValue: 'Executed now (server offline). Updated: {{u}} | Failed: {{f}} | No changes: {{n}}',
            u: Number(rr?.updated ?? 0),
            f: Number(rr?.failed ?? 0),
            n: Number(rr?.no_changes ?? 0),
          }),
          confirmButtonColor: '#f97316',
        });
      }
    } catch (e: any) {
      await Swal.fire({
        icon: 'error',
        title: t('common.error', { defaultValue: 'Error' }),
        text: e?.response?.data?.error || e?.response?.data?.message || e?.message || 'Failed to schedule',
        confirmButtonColor: '#f97316',
      });
    } finally {
      setScheduleBusy(false);
    }
  };

  const [vehicleQuery, setVehicleQuery] = useState('');
  const [vehicleLoading, setVehicleLoading] = useState(false);
  const [vehicleError, setVehicleError] = useState<string | null>(null);
  const [vehicleItems, setVehicleItems] = useState<VehicleAdminCatalogItem[]>([]);
  const [vehicleDrafts, setVehicleDrafts] = useState<Record<number, DraftVehicleRow>>({});

  const [vehicleBulkBusy, setVehicleBulkBusy] = useState(false);
  const [vehicleBulkDone, setVehicleBulkDone] = useState(0);
  const [vehicleBulkTotal, setVehicleBulkTotal] = useState(0);

  const vehicleImageInputRefs = useRef<Record<number, HTMLInputElement | null>>({});
  const [vehicleImageBusyByCode, setVehicleImageBusyByCode] = useState<Record<number, boolean>>({});

  const buildVehicleDraft = (it: VehicleAdminCatalogItem): DraftVehicleRow => {
    const setupRaw = String((it as any).setup ?? '');
    const displayRaw = String((it as any).display_name ?? '');
    const nameRaw = String((it as any).name ?? '');
    const displayName = displayRaw && displayRaw !== setupRaw ? displayRaw : nameRaw || displayRaw;
    return {
      display_name: displayName,
      enabled: Boolean(it.enabled),
      price: String(it.price ?? 0),
    };
  };

  const setVehicleDraft = (code: number, patch: Partial<DraftVehicleRow>) => {
    setVehicleDrafts((prev) => ({
      ...prev,
      [code]: {
        ...(prev[code] || { display_name: '', enabled: false, price: '0' }),
        ...patch,
      },
    }));
  };

  const diffVehiclePayload = (original: VehicleAdminCatalogItem, draft: DraftVehicleRow): PatchVehicleAdminCatalogRequest => {
    const payload: PatchVehicleAdminCatalogRequest = {};

    const originalDisplay = String((original as any).display_name ?? '');
    const nextDisplay = String(draft.display_name ?? '');
    if (originalDisplay !== nextDisplay) payload.display_name = nextDisplay;

    const price = Number(draft.price);
    const safePrice = Number.isFinite(price) ? price : 0;
    if (Number(original.price ?? 0) !== safePrice) payload.price = safePrice;
    if (Boolean(original.enabled) !== Boolean(draft.enabled)) payload.enabled = Boolean(draft.enabled);
    return payload;
  };

  const loadVehicles = async () => {
    setVehicleLoading(true);
    setVehicleError(null);
    try {
      const res = await getVehiclesAdminCatalog();
      if (res.success && res.data?.items) {
        setVehicleItems(res.data.items);
        const nextDrafts: Record<number, DraftVehicleRow> = {};
        for (const it of res.data.items) nextDrafts[it.code] = buildVehicleDraft(it);
        setVehicleDrafts(nextDrafts);
      } else {
        setVehicleItems([]);
        setVehicleDrafts({});
        setVehicleError(getApiErrorMessage(res as any) || 'Failed to load vehicles catalog');
      }
    } catch (e: any) {
      setVehicleItems([]);
      setVehicleDrafts({});
      setVehicleError(e?.response?.data?.error || e?.message || 'Failed to load vehicles catalog');
    } finally {
      setVehicleLoading(false);
    }
  };

  const onUploadVehicleImage = async (code: number, file: File) => {
    if (vehicleImageBusyByCode[code]) return;

    setVehicleImageBusyByCode((prev) => ({ ...prev, [code]: true }));
    try {
      const res = await uploadVehicleAdminCatalogImage(code, file);
      if (res.success && res.data?.image_url) {
        setVehicleItems((prev) => prev.map((x) => (x.code === code ? { ...x, image_url: res.data.image_url } : x)));
      } else {
        await Swal.fire({
          icon: 'error',
          title: t('common.error', { defaultValue: 'Error' }),
          text: getApiErrorMessage(res as any) || 'Failed to upload image',
          confirmButtonColor: '#f97316',
        });
      }
    } catch (e: any) {
      await Swal.fire({
        icon: 'error',
        title: t('common.error', { defaultValue: 'Error' }),
        text: e?.response?.data?.error || e?.response?.data?.message || e?.message || 'Failed to upload image',
        confirmButtonColor: '#f97316',
      });
    } finally {
      setVehicleImageBusyByCode((prev) => ({ ...prev, [code]: false }));
      const input = vehicleImageInputRefs.current[code];
      if (input) input.value = '';
    }
  };

  const onResetVehicleTemplates = async () => {
    if (templatesBusy) return;
    setTemplatesLastError(null);

    const confirm = await Swal.fire({
      icon: 'warning',
      title: t('common.confirm', { defaultValue: 'Confirm' }),
      text: t('tools.shopDeliveries.vehicleTemplates.resetConfirm', {
        defaultValue:
          'This will reset SCUM_TEMPLATES.db and can optionally clear vehicle catalog/orders. Continue?',
      }),
      showCancelButton: true,
      confirmButtonColor: '#ef4444',
      cancelButtonColor: '#6b7280',
      confirmButtonText: t('common.continue', { defaultValue: 'Continue' }),
      cancelButtonText: t('common.cancel', { defaultValue: 'Cancel' }),
    });
    if (!confirm.isConfirmed) return;

    const payload: AdminVehicleTemplatesResetRequest = {
      force: true,
      make_backup: true,
      reset_catalog: true,
      reset_orders: true,
    };

    setTemplatesBusy(true);
    try {
      const res = await resetVehicleAdminTemplates(payload);
      if (res.success) {
        setTemplatesLastSync(null);
        await Swal.fire({
          icon: 'success',
          title: t('common.success', { defaultValue: 'Success' }),
          text: t('tools.shopDeliveries.vehicleTemplates.resetDone', {
            defaultValue: 'Templates reset completed.',
          }),
          confirmButtonColor: '#f97316',
        });
        await loadVehicles();
      } else {
        const msg = getApiErrorMessage(res as any) || 'Reset failed';
        setTemplatesLastError(msg);
        await Swal.fire({
          icon: 'error',
          title: t('common.error', { defaultValue: 'Error' }),
          text: msg,
          confirmButtonColor: '#f97316',
        });
      }
    } catch (e: any) {
      const msg = e?.response?.data?.error || e?.message || 'Reset failed';
      setTemplatesLastError(String(msg));
      await Swal.fire({
        icon: 'error',
        title: t('common.error', { defaultValue: 'Error' }),
        text: String(msg),
        confirmButtonColor: '#f97316',
      });
    } finally {
      setTemplatesBusy(false);
    }
  };

  const onSyncVehicleTemplates = async () => {
    if (templatesBusy) return;
    setTemplatesLastError(null);

    const ids = parseIdList(templatesIdsRaw);
    if (ids.length === 0) {
      await Swal.fire({
        icon: 'info',
        title: t('common.info', { defaultValue: 'Info' }),
        text: t('tools.shopDeliveries.vehicleTemplates.idsRequired', {
          defaultValue: 'Enter at least one template vehicle entity id.',
        }),
        confirmButtonColor: '#f97316',
      });
      return;
    }

    const confirm = await Swal.fire({
      icon: 'question',
      title: t('common.confirm', { defaultValue: 'Confirm' }),
      text: t('tools.shopDeliveries.vehicleTemplates.syncConfirm', {
        defaultValue:
          'This will merge templates from an offline SCUM.db into SCUM_TEMPLATES.db and upsert into vehicle catalog. Continue?',
      }),
      showCancelButton: true,
      confirmButtonColor: '#f97316',
      cancelButtonColor: '#6b7280',
      confirmButtonText: t('common.continue', { defaultValue: 'Continue' }),
      cancelButtonText: t('common.cancel', { defaultValue: 'Cancel' }),
    });
    if (!confirm.isConfirmed) return;

    setTemplatesBusy(true);
    try {
      const res = await syncVehicleAdminTemplates({
        source_scum_db: '@config',
        ids,
        force: false,
      });
      setTemplatesLastSync(res);
      if (res.success) {
        const report = res.data?.report;
        const usedSnapshot = Boolean(res.data?.diagnostics?.used_snapshot);
        const diagText = usedSnapshot ? 'Running: using safe SCUM.db snapshot' : 'Stopped: reading SCUM.db directly';
        await Swal.fire({
          icon: 'success',
          title: t('common.success', { defaultValue: 'Success' }),
          text: t('tools.shopDeliveries.vehicleTemplates.syncDone', {
            defaultValue: 'Sync completed. Synced: {{synced}} | Missing: {{missing}}',
            synced: report?.counts?.synced ?? 0,
            missing: report?.counts?.missing ?? 0,
          }) + `\n${diagText}`,
          confirmButtonColor: '#f97316',
        });
        await loadVehicles();
      } else {
        const msg = getApiErrorMessage(res as any) || 'Sync failed';
        setTemplatesLastError(msg);
        await Swal.fire({
          icon: 'error',
          title: t('common.error', { defaultValue: 'Error' }),
          text: msg,
          confirmButtonColor: '#f97316',
        });
      }
    } catch (e: any) {
      const code = e?.response?.data?.code;
      const details = e?.response?.data?.details;
      const msg = e?.response?.data?.error || e?.response?.data?.message || e?.message || 'Sync failed';

      if (code === 'SCUMDB_SNAPSHOT_FAILED') {
        const text = 'Failed to create SCUM.db snapshot. Try again. If it persists, stop the server and retry.';
        setTemplatesLastError(text);
        await Swal.fire({
          icon: 'error',
          title: t('common.error', { defaultValue: 'Error' }),
          text: text + (details ? `\n${String(details)}` : ''),
          confirmButtonColor: '#f97316',
        });
      } else {
        setTemplatesLastError(String(msg));
        await Swal.fire({
          icon: 'error',
          title: t('common.error', { defaultValue: 'Error' }),
          text: String(msg),
          confirmButtonColor: '#f97316',
        });
      }
    } finally {
      setTemplatesBusy(false);
    }
  };

  const vehicleFiltered = useMemo(() => {
    const q = vehicleQuery.trim().toLowerCase();
    if (!q) return vehicleItems;
    return vehicleItems.filter((it) => {
      const name = (it.name || '').toLowerCase();
      const setup = String((it as any).setup || '').toLowerCase();
      const display = String((it as any).display_name || '').toLowerCase();
      const code = String(it.code);
      return name.includes(q) || setup.includes(q) || display.includes(q) || code.includes(q);
    });
  }, [vehicleItems, vehicleQuery]);

  const dirtyVehicleCodes = useMemo(() => {
    const next: number[] = [];
    for (const it of vehicleItems) {
      const d = vehicleDrafts[it.code];
      if (!d) continue;
      const payload = diffVehiclePayload(it, d);
      if (Object.keys(payload).length > 0) next.push(it.code);
    }
    return next;
  }, [vehicleItems, vehicleDrafts]);

  const onSaveAllVehicles = async () => {
    if (vehicleBulkBusy) return;

    const dirty = vehicleItems
      .map((it) => ({ it, draft: vehicleDrafts[it.code] }))
      .filter((x) => x.draft)
      .map((x) => ({ it: x.it, draft: x.draft as DraftVehicleRow }))
      .map(({ it, draft }) => ({ it, payload: diffVehiclePayload(it, draft) }))
      .filter(({ payload }) => Object.keys(payload).length > 0);

    if (dirty.length === 0) {
      await Swal.fire({
        icon: 'info',
        title: t('common.info', { defaultValue: 'Info' }),
        text: t('common.noChanges', { defaultValue: 'No changes to save.' }),
        confirmButtonColor: '#f97316',
      });
      return;
    }

    const invalid = dirty.find((x) => (x.payload.price != null ? Number(x.payload.price) < 0 : false));
    if (invalid) {
      await Swal.fire({
        icon: 'error',
        title: t('common.error', { defaultValue: 'Error' }),
        text: t('tools.shopDeliveries.vehicles.invalidPrice', { defaultValue: 'Price must be >= 0.' }),
        confirmButtonColor: '#f97316',
      });
      return;
    }

    const confirm = await Swal.fire({
      icon: 'question',
      title: t('tools.shopDeliveries.vehicles.saveConfirmTitle', { defaultValue: 'Save vehicle changes?' }),
      text: t('tools.shopDeliveries.vehicles.saveConfirmText', {
        defaultValue: 'This will save changes for {{count}} vehicles.',
        count: dirty.length,
      }),
      showCancelButton: true,
      confirmButtonColor: '#f97316',
      cancelButtonColor: '#6b7280',
      confirmButtonText: t('common.save', { defaultValue: 'Save' }),
      cancelButtonText: t('common.cancel', { defaultValue: 'Cancel' }),
    });
    if (!confirm.isConfirmed) return;

    const concurrency = 6;
    let idx = 0;
    const failures: Array<{ code: number; message: string }> = [];

    setVehicleBulkBusy(true);
    setVehicleBulkDone(0);
    setVehicleBulkTotal(dirty.length);

    const worker = async () => {
      while (idx < dirty.length) {
        const current = dirty[idx];
        idx += 1;
        try {
          const res = await patchVehicleAdminCatalogItem(current.it.code, current.payload);
          if (res.success && res.data?.item) {
            const updated = res.data.item;
            setVehicleItems((prev) => prev.map((x) => (x.code === updated.code ? updated : x)));
            setVehicleDrafts((prev) => ({ ...prev, [updated.code]: buildVehicleDraft(updated) }));
          } else {
            failures.push({
              code: current.it.code,
              message: getApiErrorMessage(res as any) || t('common.saveError', { defaultValue: 'Failed to save.' }),
            });
          }
        } catch (e: any) {
          const msg = e?.response?.data?.error || e?.message || 'Failed to save';
          failures.push({ code: current.it.code, message: String(msg) });
        } finally {
          setVehicleBulkDone((d) => d + 1);
        }
      }
    };

    try {
      await Promise.all(Array.from({ length: Math.min(concurrency, dirty.length) }, () => worker()));
    } finally {
      setVehicleBulkBusy(false);
    }

    if (failures.length > 0) {
      const sample = failures
        .slice(0, 8)
        .map((f) => `${f.code}: ${f.message}`)
        .join('\n');
      const more = failures.length > 8 ? `\n(+${failures.length - 8} more)` : '';
      await Swal.fire({
        icon: 'warning',
        title: t('tools.shopDeliveries.bulk.partialTitle', { defaultValue: 'Some items failed to save' }),
        text: sample + more,
        confirmButtonColor: '#f97316',
      });
    } else {
      await Swal.fire({
        icon: 'success',
        title: t('common.success', { defaultValue: 'Success' }),
        text: t('tools.shopDeliveries.bulk.savedAll', { defaultValue: 'All changes saved.' }),
        confirmButtonColor: '#f97316',
      });
    }
  };

  const [walletTab, setWalletTab] = useState<'wallet' | 'rewards'>('wallet');

  const [walletSteamId, setWalletSteamId] = useState('');
  const [walletBalance, setWalletBalance] = useState<number | null>(null);
  const [walletBalanceSteamId, setWalletBalanceSteamId] = useState<string | null>(null);
  const [walletBusy, setWalletBusy] = useState(false);
  const [walletTxBusy, setWalletTxBusy] = useState(false);
  const [walletTxError, setWalletTxError] = useState<string | null>(null);
  const [walletTxItems, setWalletTxItems] = useState<WalletTxItem[]>([]);

  const [playtimeBusy, setPlaytimeBusy] = useState(false);
  const [playtimeError, setPlaytimeError] = useState<string | null>(null);
  const [playtimeConfig, setPlaytimeConfig] = useState<ShopAdminRewardsPlaytimeConfig | null>(null);

  const [rulesBusy, setRulesBusy] = useState(false);
  const [rulesError, setRulesError] = useState<string | null>(null);
  const [rulesItems, setRulesItems] = useState<ShopAdminRewardsPlaytimeRule[]>([]);
  const [rulesQuickKind, setRulesQuickKind] = useState<'default' | 'vip'>('default');
  const [rulesQuickPoints, setRulesQuickPoints] = useState('');

  const [vipEditOpen, setVipEditOpen] = useState(false);
  const [vipTargetsBusy, setVipTargetsBusy] = useState(false);
  const [vipTargetsError, setVipTargetsError] = useState<string | null>(null);
  const [vipTargets, setVipTargets] = useState<string[]>([]);
  const [vipSelected, setVipSelected] = useState<Record<string, boolean>>({});
  const [vipOnly, setVipOnly] = useState(false);
  const [vipSaved, setVipSaved] = useState(false);

  const [walletOp, setWalletOp] = useState<'add' | 'remove'>('add');
  const [walletAmount, setWalletAmount] = useState('');
  const [walletNote, setWalletNote] = useState('');

  const [walletPlayers, setWalletPlayers] = useState<AllPlayer[]>([]);
  const [walletPlayersBusy, setWalletPlayersBusy] = useState(false);
  const [walletPlayerQuery, setWalletPlayerQuery] = useState('');
  const [walletPage, setWalletPage] = useState(1);
  const [walletLimit, setWalletLimit] = useState(100);
  const [walletTotal, setWalletTotal] = useState(0);

  const [walletSortBy, setWalletSortBy] = useState<string>('last_seen');
  const [walletSortOrder, setWalletSortOrder] = useState<'asc' | 'desc'>('desc');

  const [mailboxItems, setMailboxItems] = useState<RegisteredPlayerItem[]>([]);
  const [mailboxBusy, setMailboxBusy] = useState(false);
  const [mailboxError, setMailboxError] = useState<string | null>(null);
  const [mailboxTotal, setMailboxTotal] = useState(0);
  const [mailboxLimit, setMailboxLimit] = useState(100);
  const [mailboxPage, setMailboxPage] = useState(1);

  const [mailboxSortBy, setMailboxSortBy] = useState<string>('discord_linked_at');
  const [mailboxSortOrder, setMailboxSortOrder] = useState<'asc' | 'desc'>('desc');

  const [walletBalances, setWalletBalances] = useState<Record<string, number>>({});
  const [walletBalancesBusy, setWalletBalancesBusy] = useState<Record<string, boolean>>({});
  const [walletBulkBusy, setWalletBulkBusy] = useState(false);
  const [walletBulkDone, setWalletBulkDone] = useState(0);
  const [walletBulkTotal, setWalletBulkTotal] = useState(0);
  const walletBulkLoadedRef = useRef(false);

  const [clearBusy, setClearBusy] = useState(false);
  const [catalogDangerOpen, setCatalogDangerOpen] = useState(false);

  // Add catalog item form
  const [addCatalogOpen, setAddCatalogOpen] = useState(false);
  const [addCatalogBusy, setAddCatalogBusy] = useState(false);
  const [addSetup, setAddSetup] = useState('');
  const [addDisplayName, setAddDisplayName] = useState('');
  const [addPrice, setAddPrice] = useState('0');
  const [addQty, setAddQty] = useState('1');
  const [addEnabled, setAddEnabled] = useState(true);
  const [addCatalogError, setAddCatalogError] = useState<string | null>(null);



  const load = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await getShopAdminCatalog();
      if (res.success && res.data?.items) {
        setItems(res.data.items);
        const nextDrafts: Record<number, DraftRow> = {};
        for (const it of res.data.items) nextDrafts[it.code] = buildDraft(it);
        setDrafts(nextDrafts);
      } else {
        setItems([]);
        setDrafts({});
        setError(getApiErrorMessage(res as any) || 'Failed to load catalog');
      }
    } catch (e: any) {
      setItems([]);
      setDrafts({});
      setError(e?.response?.data?.error || e?.message || 'Failed to load catalog');
    } finally {
      setLoading(false);
    }
  };

  const onSaveAll = async () => {
    if (bulkBusy) return;
    const dirty = items
      .map((it) => ({ it, draft: drafts[it.code] }))
      .filter((x) => x.draft)
      .map((x) => ({ it: x.it, draft: x.draft as DraftRow }))
      .map(({ it, draft }) => ({ it, payload: diffPayload(it, draft) }))
      .filter(({ payload }) => hasChanges(payload));

    if (dirty.length === 0) {
      await Swal.fire({
        icon: 'info',
        title: t('common.info', { defaultValue: 'Info' }),
        text: t('common.noChanges', { defaultValue: 'No changes to save.' }),
        confirmButtonColor: '#f97316',
      });
      return;
    }

    const confirm = await Swal.fire({
      icon: 'question',
      title: t('tools.shopDeliveries.bulk.confirmTitle', { defaultValue: 'Save all changes?' }),
      text: t('tools.shopDeliveries.bulk.confirmText', {
        defaultValue: 'This will save changes for {{count}} items.',
        count: dirty.length,
      }),
      showCancelButton: true,
      confirmButtonColor: '#f97316',
      cancelButtonColor: '#6b7280',
      confirmButtonText: t('common.save', { defaultValue: 'Save' }),
      cancelButtonText: t('common.cancel', { defaultValue: 'Cancel' }),
    });
    if (!confirm.isConfirmed) return;

    const concurrency = 6;
    let idx = 0;
    const failures: Array<{ code: number; message: string }> = [];

    setBulkBusy(true);
    setBulkDone(0);
    setBulkTotal(dirty.length);

    const worker = async () => {
      while (idx < dirty.length) {
        const current = dirty[idx];
        idx += 1;
        try {
          const res = await patchShopAdminCatalogItem(current.it.code, current.payload);
          if (res.success && res.data?.item) {
            const updated = res.data.item;
            setItems((prev) => prev.map((x) => (x.code === updated.code ? updated : x)));
            setDrafts((prev) => ({ ...prev, [updated.code]: buildDraft(updated) }));
          } else {
            failures.push({
              code: current.it.code,
              message: getApiErrorMessage(res as any) || t('common.saveError', { defaultValue: 'Failed to save.' }),
            });
          }
        } catch (e: any) {
          const msg = e?.response?.data?.error || e?.message || 'Failed to save';
          failures.push({ code: current.it.code, message: String(msg) });
        } finally {
          setBulkDone((d) => d + 1);
        }
      }
    };

    try {
      await Promise.all(Array.from({ length: Math.min(concurrency, dirty.length) }, () => worker()));
    } finally {
      setBulkBusy(false);
    }

    if (failures.length === 0) {
      await Swal.fire({
        icon: 'success',
        title: t('common.success', { defaultValue: 'Success' }),
        text: t('tools.shopDeliveries.bulk.savedAll', { defaultValue: 'All changes saved.' }),
        confirmButtonColor: '#f97316',
      });
      return;
    }

    const preview = failures
      .slice(0, 10)
      .map((f) => `#${f.code}: ${f.message}`)
      .join('\n');
    const more = failures.length > 10 ? `\n... (+${failures.length - 10})` : '';

    await Swal.fire({
      icon: 'warning',
      title: t('tools.shopDeliveries.bulk.partialTitle', { defaultValue: 'Some items failed' }),
      text: `${t('tools.shopDeliveries.bulk.partialText', {
        defaultValue: 'Saved: {{ok}} | Failed: {{fail}}',
        ok: dirty.length - failures.length,
        fail: failures.length,
      })}\n\n${preview}${more}`,
      confirmButtonColor: '#f97316',
    });
  };

  const fetchAllWalletBalances = async (players: AllPlayer[]) => {
    if (walletBulkBusy) return;
    const ids = players.map((p) => p.steam_id).filter(Boolean);
    if (ids.length === 0) return;

    const concurrency = 6;
    let idx = 0;

    setWalletBulkBusy(true);
    setWalletBulkDone(0);
    setWalletBulkTotal(ids.length);

    const worker = async () => {
      while (idx < ids.length) {
        const current = ids[idx];
        idx += 1;
        try {
          await fetchWalletBalanceFor(current);
        } catch {
          // ignore
        } finally {
          setWalletBulkDone((d) => d + 1);
        }
      }
    };

    try {
      await Promise.all(Array.from({ length: Math.min(concurrency, ids.length) }, () => worker()));
    } finally {
      setWalletBulkBusy(false);
    }
  };

  const fetchWalletBalanceFor = async (steamId: string) => {
    const sid = steamId.trim();
    if (!sid) return;

    setWalletBalancesBusy((prev) => ({ ...prev, [sid]: true }));
    try {
      const res = await getShopWalletBalance(sid);
      if (res.success && res.data) {
        setWalletBalances((prev) => ({ ...prev, [sid]: res.data.balance }));
        setWalletBalance(res.data.balance);
        setWalletBalanceSteamId(res.data.steam_id);
      }
    } finally {
      setWalletBalancesBusy((prev) => ({ ...prev, [sid]: false }));
    }
  };

  useEffect(() => {
    void load();
  }, []);

  useEffect(() => {
    if (section !== 'base_upgrades') return;
    if (ownersItems.length > 0) return;
    void loadOwners(1, ownersPageSize);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [section]);

  useEffect(() => {
    setDryRunResult(null);
    setDryRunError(null);
  }, [selectedFlagId, upgradeTargetLevel]);

  useEffect(() => {
    if (section !== 'vehicles') return;
    if (vehicleItems.length > 0) return;
    void loadVehicles();
  }, [section, vehicleItems.length]);



  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (!q) return items;
    return items.filter((it) => {
      const hay = [it.code, it.name, it.setup].join(' ').toLowerCase();
      return hay.includes(q);
    });
  }, [items, query]);

  const dirtyCodes = useMemo(() => {
    const next: number[] = [];
    for (const it of items) {
      const d = drafts[it.code];
      if (!d) continue;
      const payload = diffPayload(it, d);
      if (hasChanges(payload)) next.push(it.code);
    }
    return next;
  }, [items, drafts]);

  const filteredCatalogCheckedCount = useMemo(() => {
    let count = 0;
    for (const it of items) {
      const d = drafts[it.code] || buildDraft(it);
      if (d.catalog_enabled) count += 1;
    }
    return count;
  }, [items, drafts]);

  const filteredOfferCheckedCount = useMemo(() => {
    let count = 0;
    for (const it of items) {
      const d = drafts[it.code] || buildDraft(it);
      if (d.offer_enabled) count += 1;
    }
    return count;
  }, [items, drafts]);

  const catalogTri = useMemo(
    () => computeTriState(items.length, filteredCatalogCheckedCount),
    [items.length, filteredCatalogCheckedCount]
  );
  const offerTri = useMemo(
    () => computeTriState(items.length, filteredOfferCheckedCount),
    [items.length, filteredOfferCheckedCount]
  );

  const catalogHeaderRef = useRef<HTMLInputElement | null>(null);
  const offerHeaderRef = useRef<HTMLInputElement | null>(null);

  useEffect(() => {
    if (catalogHeaderRef.current) catalogHeaderRef.current.indeterminate = catalogTri.indeterminate;
  }, [catalogTri.indeterminate]);

  useEffect(() => {
    if (offerHeaderRef.current) offerHeaderRef.current.indeterminate = offerTri.indeterminate;
  }, [offerTri.indeterminate]);

  const applyBulkToggle = (field: 'catalog_enabled' | 'offer_enabled', value: boolean) => {
    setDrafts((prev) => {
      const next: Record<number, DraftRow> = { ...prev };
      for (const it of items) {
        next[it.code] = {
          ...(prev[it.code] || buildDraft(it)),
          [field]: value,
        } as DraftRow;
      }
      return next;
    });
  };

  const onToggleAllInHeader = (field: 'catalog_enabled' | 'offer_enabled') => {
    const tri = field === 'catalog_enabled' ? catalogTri : offerTri;
    const nextValue = !tri.checked;
    applyBulkToggle(field, nextValue);
  };

  const filteredPlayers = useMemo(() => {
    const q = walletPlayerQuery.trim().toLowerCase();
    if (!q) return walletPlayers;
    return walletPlayers.filter((p) => {
      const name = (p.player_name || '').toLowerCase();
      const sid = (p.steam_id || '').toLowerCase();
      return name.includes(q) || sid.includes(q);
    });
  }, [walletPlayers, walletPlayerQuery]);

  const rewardsMailboxMode = walletTab === 'rewards';
  const vipSelectMode = rewardsMailboxMode && vipEditOpen;

  const mailboxTotalPages = useMemo(() => {
    return Math.max(1, Math.ceil(mailboxTotal / mailboxLimit));
  }, [mailboxLimit, mailboxTotal]);

  const mailboxPageButtons = useMemo(() => {
    const totalPages = mailboxTotalPages;
    const maxButtons = 7;
    const half = Math.floor(maxButtons / 2);
    let start = Math.max(1, mailboxPage - half);
    let end = Math.min(totalPages, start + maxButtons - 1);
    start = Math.max(1, end - maxButtons + 1);
    const pages: number[] = [];
    for (let p = start; p <= end; p += 1) pages.push(p);
    return pages;
  }, [mailboxPage, mailboxTotalPages]);

  const walletTotalPages = useMemo(() => {
    return Math.max(1, Math.ceil(walletTotal / walletLimit));
  }, [walletLimit, walletTotal]);

  const walletPageButtons = useMemo(() => {
    const totalPages = walletTotalPages;
    const maxButtons = 7;
    const half = Math.floor(maxButtons / 2);
    let start = Math.max(1, walletPage - half);
    let end = Math.min(totalPages, start + maxButtons - 1);
    start = Math.max(1, end - maxButtons + 1);
    const pages: number[] = [];
    for (let p = start; p <= end; p += 1) pages.push(p);
    return pages;
  }, [walletPage, walletTotalPages]);

  const mailboxFiltered = useMemo(() => {
    const q = walletPlayerQuery.trim().toLowerCase();
    let base = mailboxItems;
    if (q) {
      base = base.filter((it) => {
        const name = (it.player_name || '').toLowerCase();
        const sid = (it.steam_id || '').toLowerCase();
        return name.includes(q) || sid.includes(q);
      });
    }
    if (vipOnly) {
      base = base.filter((it) => Boolean(vipSelected[it.steam_id]));
    }
    return base;
  }, [mailboxItems, vipOnly, vipSelected, walletPlayerQuery]);

  const filteredPlayersForView = useMemo(() => {
    if (rewardsMailboxMode) return [] as AllPlayer[];
    if (!vipOnly) return filteredPlayers;
    return filteredPlayers.filter((p) => Boolean(vipSelected[p.steam_id]));
  }, [filteredPlayers, rewardsMailboxMode, vipOnly, vipSelected]);

  const renderSortableHeader = (
    label: string,
    field: string,
    isMailbox: boolean,
    className = ''
  ) => {
    const currentField = isMailbox ? mailboxSortBy : walletSortBy;
    const currentOrder = isMailbox ? mailboxSortOrder : walletSortOrder;
    const isActive = currentField === field;

    const handleSort = () => {
      if (isMailbox) {
        const nextOrder = isActive && currentOrder === 'desc' ? 'asc' : 'desc';
        setMailboxSortBy(field);
        setMailboxSortOrder(nextOrder);
        void loadMailboxPage(1, walletPlayerQuery, field, nextOrder);
      } else {
        const nextOrder = isActive && currentOrder === 'desc' ? 'asc' : 'desc';
        setWalletSortBy(field);
        setWalletSortOrder(nextOrder);
        void loadWalletPage(1, walletPlayerQuery, field, nextOrder);
      }
    };

    return (
      <div
        onClick={handleSort}
        className={`flex items-center gap-1 cursor-pointer select-none hover:text-white/80 transition-colors ${className}`}
      >
        <span>{label}</span>
        <span className="text-[10px] opacity-70">
          {isActive ? (currentOrder === 'desc' ? '▼' : '▲') : '↕'}
        </span>
      </div>
    );
  };

  const loadMailboxPage = async (
    page: number,
    searchQuery = walletPlayerQuery,
    sortBy = mailboxSortBy,
    sortOrder = mailboxSortOrder
  ) => {
    const safePage = Math.max(1, page);
    const offset = (safePage - 1) * mailboxLimit;
    setMailboxBusy(true);
    setMailboxError(null);
    try {
      const res = await getRegisteredPlayers(
        mailboxLimit,
        offset,
        searchQuery,
        sortBy,
        sortOrder
      );
      if (!res.success) {
        setMailboxItems([]);
        setMailboxTotal(0);
        setMailboxError(getApiErrorMessage(res as any));
        return;
      }
      setMailboxItems(res.data.items || []);
      setMailboxTotal(Number(res.data.total ?? 0));
      setMailboxPage(safePage);
    } catch (e: any) {
      setMailboxItems([]);
      setMailboxTotal(0);
      setMailboxError(e?.response?.data?.error || e?.response?.data?.message || e?.message || 'Request failed');
    } finally {
      setMailboxBusy(false);
    }
  };

  const loadWalletPage = async (
    page: number,
    searchQuery = walletPlayerQuery,
    sortBy = walletSortBy,
    sortOrder = walletSortOrder
  ) => {
    const safePage = Math.max(1, page);
    const offset = (safePage - 1) * walletLimit;
    setWalletPlayersBusy(true);
    try {
      const res = await getAllPlayers(walletLimit, offset, {
        q: searchQuery,
        sortBy,
        sortOrder,
      });
      if (res.success && res.data?.players) {
        setWalletPlayers(res.data.players);
        setWalletTotal(res.data.total ?? 0);
        setWalletPage(safePage);
      } else {
        setWalletPlayers([]);
        setWalletTotal(0);
      }
    } catch (e) {
      console.error(e);
      setWalletPlayers([]);
      setWalletTotal(0);
    } finally {
      setWalletPlayersBusy(false);
    }
  };

  // Initial load when tab/limit/section/sort changes
  useEffect(() => {
    if (section !== 'wallet') return;
    if (rewardsMailboxMode) {
      void loadMailboxPage(1, walletPlayerQuery, mailboxSortBy, mailboxSortOrder);
    } else {
      void loadWalletPage(1, walletPlayerQuery, walletSortBy, walletSortOrder);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [
    section,
    rewardsMailboxMode,
    mailboxLimit,
    walletLimit,
    walletSortBy,
    walletSortOrder,
    mailboxSortBy,
    mailboxSortOrder,
  ]);

  // Debounced search trigger
  useEffect(() => {
    if (section !== 'wallet') return;
    const handler = setTimeout(() => {
      if (rewardsMailboxMode) {
        void loadMailboxPage(1, walletPlayerQuery, mailboxSortBy, mailboxSortOrder);
      } else {
        void loadWalletPage(1, walletPlayerQuery, walletSortBy, walletSortOrder);
      }
    }, 400);

    return () => clearTimeout(handler);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [walletPlayerQuery, rewardsMailboxMode, section]);

  // Balance fetching for mailbox items
  useEffect(() => {
    if (!rewardsMailboxMode) return;
    if (mailboxItems.length === 0) return;
    const ids = mailboxItems.map((it) => it.steam_id).filter(Boolean);
    if (ids.length === 0) return;

    const concurrency = 6;
    let idx = 0;
    void Promise.all(
      Array.from({ length: Math.min(concurrency, ids.length) }, async () => {
        while (idx < ids.length) {
          const sid = ids[idx];
          idx += 1;
          if (walletBalancesBusy[sid]) continue;
          if (walletBalances[sid] != null) continue;
          await fetchWalletBalanceFor(sid);
        }
      })
    );
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [rewardsMailboxMode, mailboxItems]);

  // Balance fetching for wallet players
  useEffect(() => {
    if (section !== 'wallet' || rewardsMailboxMode) return;
    if (walletPlayers.length === 0) return;
    const ids = walletPlayers.map((p) => p.steam_id).filter(Boolean);
    if (ids.length === 0) return;

    const concurrency = 6;
    let idx = 0;
    void Promise.all(
      Array.from({ length: Math.min(concurrency, ids.length) }, async () => {
        while (idx < ids.length) {
          const sid = ids[idx];
          idx += 1;
          if (walletBalancesBusy[sid]) continue;
          if (walletBalances[sid] != null) continue;
          await fetchWalletBalanceFor(sid);
        }
      })
    );
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [section, rewardsMailboxMode, walletPlayers]);

  const setDraft = (code: number, patch: Partial<DraftRow>) => {
    setDrafts((prev) => ({
      ...prev,
      [code]: {
        ...(prev[code] || ({} as DraftRow)),
        ...patch,
      },
    }));
  };

  const onSaveRow = async (item: ShopAdminCatalogItem) => {
    const draft = drafts[item.code];
    if (!draft) return;

    const payload = diffPayload(item, draft);
    if (!hasChanges(payload)) {
      await Swal.fire({
        icon: 'info',
        title: t('common.info', { defaultValue: 'Info' }),
        text: t('common.noChanges', { defaultValue: 'No changes to save.' }),
        confirmButtonColor: '#f97316',
      });
      return;
    }

    setSavingCode(item.code);
    try {
      const res = await patchShopAdminCatalogItem(item.code, payload);
      if (res.success && res.data?.item) {
        const updated = res.data.item;
        setItems((prev) => prev.map((x) => (x.code === updated.code ? updated : x)));
        setDrafts((prev) => ({ ...prev, [updated.code]: buildDraft(updated) }));
        await Swal.fire({
          icon: 'success',
          title: t('common.success', { defaultValue: 'Success' }),
          text: t('common.saved', { defaultValue: 'Saved.' }),
          confirmButtonColor: '#f97316',
        });
      } else {
        await Swal.fire({
          icon: 'error',
          title: t('common.error', { defaultValue: 'Error' }),
          text: getApiErrorMessage(res as any) || t('common.saveError', { defaultValue: 'Failed to save.' }),
          confirmButtonColor: '#f97316',
        });
      }
    } catch (e: any) {
      const msg = e?.response?.data?.error || e?.message || 'Failed to save';
      await Swal.fire({
        icon: 'error',
        title: t('common.error', { defaultValue: 'Error' }),
        text: msg,
        confirmButtonColor: '#f97316',
      });
    } finally {
      setSavingCode(null);
    }
  };

  const onSetScannerChest = async () => {
    const chestId = Number(scannerChestId);
    if (!Number.isFinite(chestId) || chestId <= 0) {
      await Swal.fire({
        icon: 'error',
        title: t('common.error', { defaultValue: 'Error' }),
        text: t('tools.shopDeliveries.invalidChestId', { defaultValue: 'Invalid chest id.' }),
        confirmButtonColor: '#f97316',
      });
      return;
    }

    setScannerBusy(true);
    try {
      const res = await setShopAdminScannerChest(chestId);
      if (res.success) {
        await Swal.fire({
          icon: 'success',
          title: t('common.success', { defaultValue: 'Success' }),
          text: t('tools.shopDeliveries.scannerSet', { defaultValue: 'Scanner chest updated.' }),
          confirmButtonColor: '#f97316',
        });
      } else {
        await Swal.fire({
          icon: 'error',
          title: t('common.error', { defaultValue: 'Error' }),
          text:
            getApiErrorMessage(res as any) ||
            t('tools.shopDeliveries.scannerSetError', { defaultValue: 'Failed to set scanner chest.' }),
          confirmButtonColor: '#f97316',
        });
      }
    } catch (e: any) {
      const msg = e?.response?.data?.error || e?.message || 'Failed to set scanner chest';
      await Swal.fire({
        icon: 'error',
        title: t('common.error', { defaultValue: 'Error' }),
        text: msg,
        confirmButtonColor: '#f97316',
      });
    } finally {
      setScannerBusy(false);
    }
  };

  const onWalletBalance = async () => {
    setWalletBusy(true);
    try {
      const sid = walletSteamId.trim() || undefined;
      const res = await getShopWalletBalance(sid);
      if (res.success && res.data) {
        setWalletBalance(res.data.balance);
        setWalletBalanceSteamId(res.data.steam_id);
      } else {
        setWalletBalance(null);
        setWalletBalanceSteamId(null);
        await Swal.fire({
          icon: 'error',
          title: t('common.error', { defaultValue: 'Error' }),
          text: getApiErrorMessage(res as any) || t('tools.shopDeliveries.wallet.balanceError', { defaultValue: 'Failed to fetch balance.' }),
          confirmButtonColor: '#f97316',
        });
      }
    } catch (e: any) {
      const msg = e?.response?.data?.error || e?.message || 'Failed to fetch balance';
      await Swal.fire({
        icon: 'error',
        title: t('common.error', { defaultValue: 'Error' }),
        text: msg,
        confirmButtonColor: '#f97316',
      });
    } finally {
      setWalletBusy(false);
    }
  };

  useEffect(() => {
    const steamId = walletSteamId.trim();
    if (!steamId) {
      setWalletTxError(null);
      setWalletTxItems([]);
      return;
    }

    let cancelled = false;
    setWalletTxBusy(true);
    setWalletTxError(null);
    void (async () => {
      try {
        const txRes = await getShopAdminWalletTransactions(steamId, 10);
        if (cancelled) return;
        if (!txRes.success) {
          setWalletTxError(getApiErrorMessage(txRes as any));
          setWalletTxItems([]);
        } else {
          setWalletTxItems(txRes.data.items || []);
        }
      } catch (e: any) {
        if (cancelled) return;
        setWalletTxError(e?.message || 'Request failed');
        setWalletTxItems([]);
      } finally {
        if (!cancelled) setWalletTxBusy(false);
      }
    })();

    return () => {
      cancelled = true;
    };
  }, [walletSteamId]);

  const loadPlaytimeConfig = async () => {
    setPlaytimeBusy(true);
    setPlaytimeError(null);
    try {
      const res = await getShopAdminRewardsPlaytimeConfig();
      if (!res.success) {
        setPlaytimeConfig(null);
        setPlaytimeError(getApiErrorMessage(res as any));
        return;
      }
      setPlaytimeConfig(res.data);
    } catch (e: any) {
      setPlaytimeConfig(null);
      setPlaytimeError(e?.message || 'Request failed');
    } finally {
      setPlaytimeBusy(false);
    }
  };

  const findDefaultRule = (items: ShopAdminRewardsPlaytimeRule[]) => items.find((r) => r.name === 'Padrão') || null;
  const findVipRule = (items: ShopAdminRewardsPlaytimeRule[]) => items.find((r) => r.name === 'VIP') || null;

  const loadPlaytimeRules = async () => {
    setRulesBusy(true);
    setRulesError(null);
    try {
      const res = await getShopAdminRewardsPlaytimeRules();
      if (!res.success) {
        setRulesItems([]);
        setRulesError(getApiErrorMessage(res as any));
        return;
      }
      setRulesItems(res.data.items || []);
    } catch (e: any) {
      setRulesItems([]);
      setRulesError(e?.message || 'Request failed');
    } finally {
      setRulesBusy(false);
    }
  };

  const ensureRule = async (kind: 'default' | 'vip', pointsPerHour: number) => {
    const items = rulesItems;
    const existing = kind === 'default' ? findDefaultRule(items) : findVipRule(items);
    if (existing) return existing;

    const maxHours = playtimeConfig?.max_hours_per_run ?? 0;
    const payload = {
      name: kind === 'default' ? 'Padrão' : 'VIP',
      enabled: 1 as const,
      exclusive: kind === 'default' ? (0 as const) : (1 as const),
      points_per_hour: pointsPerHour,
      max_hours_per_run: maxHours,
      audience_type: 'list' as const,
    };
    const res = await postShopAdminRewardsPlaytimeRule(payload);
    if (!res.success) throw new Error(getApiErrorMessage(res as any) || 'Request failed');

    // Reload and return the new rule
    const nextRes = await getShopAdminRewardsPlaytimeRules();
    if (nextRes.success) setRulesItems(nextRes.data.items || []);
    const nextItems = nextRes.success ? nextRes.data.items || [] : rulesItems;
    return kind === 'default' ? findDefaultRule(nextItems) : findVipRule(nextItems);
  };

  const saveQuickRulePoints = async () => {
    const raw = rulesQuickPoints.trim();
    const validFormat = raw !== '' && /^\d+$/.test(raw);
    const points = Number(raw);
    if (!validFormat || !Number.isFinite(points) || points < 0) {
      await Swal.fire({
        icon: 'error',
        title: t('common.error', { defaultValue: 'Error' }),
        text: t('tools.shopDeliveries.playtimeRules.validation.points', {
          defaultValue: 'Points per hour must be an integer >= 0.',
        }),
        confirmButtonColor: '#f97316',
      });
      return;
    }

    setRulesBusy(true);
    setRulesError(null);
    try {
      const rule = await ensureRule(rulesQuickKind, points);
      if (!rule) throw new Error('RULE_NOT_FOUND');
      const patch = await patchShopAdminRewardsPlaytimeRule(rule.rule_id, { points_per_hour: points });
      if (!patch.success) throw new Error(getApiErrorMessage(patch as any) || 'Request failed');
      await loadPlaytimeRules();
    } catch (e: any) {
      setRulesError(e?.message || 'Request failed');
    } finally {
      setRulesBusy(false);
    }
  };

  const toggleRuleEnabled = async (rule: ShopAdminRewardsPlaytimeRule, enabled: boolean) => {
    setRulesBusy(true);
    setRulesError(null);
    try {
      const res = await patchShopAdminRewardsPlaytimeRule(rule.rule_id, { enabled: enabled ? 1 : 0 });
      if (!res.success) throw new Error(getApiErrorMessage(res as any) || 'Request failed');
      await loadPlaytimeRules();
    } catch (e: any) {
      setRulesError(e?.message || 'Request failed');
    } finally {
      setRulesBusy(false);
    }
  };

  const loadVipTargets = async (ruleId: string) => {
    setVipTargetsBusy(true);
    setVipTargetsError(null);
    try {
      const res = await getShopAdminRewardsPlaytimeRuleTargets(ruleId);
      if (!res.success) {
        setVipTargets([]);
        setVipTargetsError(getApiErrorMessage(res as any));
        return;
      }
      const items = res.data.items || [];
      setVipTargets(items);
      const next: Record<string, boolean> = {};
      for (const sid of items) next[sid] = true;
      setVipSelected(next);
    } catch (e: any) {
      setVipTargets([]);
      setVipTargetsError(e?.message || 'Request failed');
    } finally {
      setVipTargetsBusy(false);
    }
  };

  const saveVipTargetsFromSelection = async (ruleId: string) => {
    const desired = new Set(Object.keys(vipSelected).filter((k) => vipSelected[k]));
    const current = new Set(vipTargets);
    const toAdd = Array.from(desired).filter((sid) => !current.has(sid));
    const toRemove = Array.from(current).filter((sid) => !desired.has(sid));

    if (toAdd.length === 0 && toRemove.length === 0) return;

    setVipTargetsBusy(true);
    setVipTargetsError(null);

    const showVipRuleError = async (msg: string) => {
      if (msg !== 'DEFAULT_RULE_NOT_FOUND' && msg !== 'NOT_IN_DEFAULT_RULE') return false;

      await Swal.fire({
        icon: 'error',
        title: t('common.error', { defaultValue: 'Error' }),
        text:
          msg === 'DEFAULT_RULE_NOT_FOUND'
            ? t('tools.shopDeliveries.playtimeRules.errors.defaultRuleNotFound', {
                defaultValue: 'Default rule (Padrão) not found. Create it first.',
              })
            : t('tools.shopDeliveries.playtimeRules.errors.notInDefaultRule', {
                defaultValue: 'Player must be registered before becoming VIP.',
              }),
        confirmButtonColor: '#f97316',
      });
      return true;
    };

    const extractErrorCode = (e: any) => {
      const status = e?.response?.status;
      const data = e?.response?.data;
      const code = data?.error || data?.message;
      if (code) return code;

      if (status) {
        let body = '';
        try {
          if (typeof data === 'string') body = data;
          else if (data != null) body = JSON.stringify(data);
        } catch {
          body = '';
        }

        const snippet = body ? ` | ${body.slice(0, 220)}` : '';
        return `HTTP_${status}${snippet}`;
      }

      return e?.message || 'Request failed';
    };

    try {
      for (const sid of toAdd) {
        let res: any;
        try {
          res = await postShopAdminRewardsPlaytimeRuleTarget(ruleId, { steam_id: sid });
        } catch (e: any) {
          const code = extractErrorCode(e);
          if (await showVipRuleError(code)) return;
          throw e;
        }

        if (!res.success) {
          const msg = getApiErrorMessage(res as any) || 'Request failed';
          if (await showVipRuleError(msg)) return;
          throw new Error(msg);
        }
      }
      for (const sid of toRemove) {
        let res: any;
        try {
          res = await deleteShopAdminRewardsPlaytimeRuleTarget(ruleId, sid);
        } catch (e: any) {
          const code = extractErrorCode(e);
          if (await showVipRuleError(code)) return;
          throw e;
        }
        if (!res.success) {
          const msg = getApiErrorMessage(res as any) || 'Request failed';
          if (await showVipRuleError(msg)) return;
          throw new Error(msg);
        }
      }
      await loadVipTargets(ruleId);

      setVipSaved(true);
      window.setTimeout(() => setVipSaved(false), 2500);
    } catch (e: any) {
      const code = extractErrorCode(e);
      if (await showVipRuleError(code)) return;
      if (String(code).startsWith('HTTP_500')) {
        await Swal.fire({
          icon: 'error',
          title: t('common.error', { defaultValue: 'Error' }),
          text: t('tools.shopDeliveries.playtimeRules.errors.internalServerError', {
            defaultValue:
              'Backend returned HTTP 500 while saving VIPs. Open DevTools > Network and check the Response body for details.',
          }),
          confirmButtonColor: '#f97316',
        });
      }
      setVipTargetsError(code);
    } finally {
      setVipTargetsBusy(false);
    }
  };

  useEffect(() => {
    if (walletTab !== 'rewards') return;
    if (playtimeBusy) return;
    setPlaytimeError(null);
    void loadPlaytimeConfig();
    void loadPlaytimeRules();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [walletTab]);

  const onWalletAdjust = async () => {
    const steamId = walletSteamId.trim();
    const amount = Number(walletAmount);
    if (!steamId) {
      await Swal.fire({
        icon: 'error',
        title: t('common.error', { defaultValue: 'Error' }),
        text: t('tools.shopDeliveries.wallet.validationSteamId', { defaultValue: 'Steam ID is required.' }),
        confirmButtonColor: '#f97316',
      });
      return;
    }
    if (!Number.isFinite(amount) || amount <= 0) {
      await Swal.fire({
        icon: 'error',
        title: t('common.error', { defaultValue: 'Error' }),
        text: t('tools.shopDeliveries.wallet.validationAmount', { defaultValue: 'Amount must be greater than zero.' }),
        confirmButtonColor: '#f97316',
      });
      return;
    }

    let currentBalance: number | null = null;
    try {
      const res = await getShopWalletBalance(steamId);
      if (res.success && res.data) {
        currentBalance = res.data.balance;
        setWalletBalance(res.data.balance);
        setWalletBalanceSteamId(res.data.steam_id);
        setWalletBalances((prev) => ({ ...prev, [steamId]: res.data.balance }));
      }
    } catch {
      // ignore
    }

    if (currentBalance == null) {
      await Swal.fire({
        icon: 'error',
        title: t('common.error', { defaultValue: 'Error' }),
        text: t('tools.shopDeliveries.wallet.balanceRequired', {
          defaultValue: 'Please fetch the current balance before applying an adjustment.',
        }),
        confirmButtonColor: '#f97316',
      });
      return;
    }

    if (walletOp === 'remove') {
      const confirm = await Swal.fire({
        icon: 'warning',
        title: t('tools.shopDeliveries.wallet.removeConfirmTitle', { defaultValue: 'Confirm removal' }),
        text: t('tools.shopDeliveries.wallet.removeConfirmText', {
          defaultValue: 'Remove {{amount}} credits from {{steam_id}}?',
          amount,
          steam_id: steamId,
        }),
        showCancelButton: true,
        confirmButtonColor: '#f97316',
        cancelButtonColor: '#6b7280',
        confirmButtonText: t('tools.shopDeliveries.wallet.confirm', { defaultValue: 'Confirm' }),
        cancelButtonText: t('common.cancel', { defaultValue: 'Cancel' }),
      });
      if (!confirm.isConfirmed) return;
    }

    const delta = walletOp === 'add' ? amount : -amount;
    const projected = currentBalance + delta;
    if (!Number.isFinite(projected) || projected < 0) {
      await Swal.fire({
        icon: 'error',
        title: t('common.error', { defaultValue: 'Error' }),
        text: t('tools.shopDeliveries.wallet.insufficientFunds', { defaultValue: 'Insufficient funds.' }),
        confirmButtonColor: '#f97316',
      });
      return;
    }
    const payload = {
      external_id: `ADMIN_ADJ_${Date.now()}_${steamId}`,
      steam_id: steamId,
      delta,
      reason: 'admin_adjust',
      meta: walletNote.trim() ? { note: walletNote.trim() } : undefined,
    };

    setWalletBusy(true);
    try {
      const res = await adjustShopAdminWallet(payload);
      if (res.success && res.data) {
        const text = res.data.already_applied
          ? t('tools.shopDeliveries.wallet.alreadyApplied', { defaultValue: 'Already applied (idempotent).' })
          : t('tools.shopDeliveries.wallet.adjusted', {
              defaultValue: 'Adjusted. New balance: {{balance}}',
              balance: res.data.balance,
            });
        await Swal.fire({
          icon: 'success',
          title: t('common.success', { defaultValue: 'Success' }),
          text,
          confirmButtonColor: '#f97316',
        });
        setWalletBalance(res.data.balance);
        setWalletBalanceSteamId(res.data.steam_id);
        setWalletBalances((prev) => ({ ...prev, [res.data.steam_id]: res.data.balance }));
        setWalletAmount('');
        setWalletNote('');
      } else {
        console.error('[wallet.adjust] unexpected response', res);
        const msg =
          getApiErrorMessage(res as any) ||
          ((res as any)?.success
            ? t('tools.shopDeliveries.wallet.adjustMissingData', {
                defaultValue: 'Request succeeded but no data was returned.',
              })
            : t('tools.shopDeliveries.wallet.adjustError', { defaultValue: 'Failed to adjust wallet.' }));
        await Swal.fire({
          icon: 'error',
          title: t('common.error', { defaultValue: 'Error' }),
          text: msg,
          confirmButtonColor: '#f97316',
        });
      }
    } catch (e: any) {
      const status = e?.response?.status;
      if (status === 409) {
        await Swal.fire({
          icon: 'error',
          title: t('common.error', { defaultValue: 'Error' }),
          text: t('tools.shopDeliveries.wallet.insufficientFunds', { defaultValue: 'Insufficient funds.' }),
          confirmButtonColor: '#f97316',
        });
      } else {
        const msg = e?.response?.data?.error || e?.message || 'Failed to adjust wallet';
        await Swal.fire({
          icon: 'error',
          title: t('common.error', { defaultValue: 'Error' }),
          text: msg,
          confirmButtonColor: '#f97316',
        });
      }
    } finally {
      setWalletBusy(false);
    }
  };

  const onClearCatalog = async () => {
    const confirmText = 'DELETE_ALL_CATALOG';

    const result = await Swal.fire({
      icon: 'warning',
      title: t('tools.shopDeliveries.clear.title', { defaultValue: 'Clear catalog' }),
      html: `<div style="text-align:left;">
        <div>${t('tools.shopDeliveries.clear.desc', {
          defaultValue:
            'This will hard-clear the catalog (shop_offer + shop_catalog). Orders history will remain. To confirm, type:',
        })}</div>
        <div style="margin-top:8px;"><b>${confirmText}</b></div>
      </div>`,
      input: 'text',
      inputPlaceholder: confirmText,
      showCancelButton: true,
      confirmButtonColor: '#f97316',
      cancelButtonColor: '#6b7280',
      confirmButtonText: t('tools.shopDeliveries.clear.confirm', { defaultValue: 'Clear' }),
      cancelButtonText: t('common.cancel', { defaultValue: 'Cancel' }),
      preConfirm: (value) => {
        if (String(value || '').trim() !== confirmText) {
          Swal.showValidationMessage(
            t('tools.shopDeliveries.clear.validation', {
              defaultValue: 'Confirmation text does not match.',
            })
          );
          return false as any;
        }
        return true;
      },
    });

    if (!result.isConfirmed) return;

    setClearBusy(true);
    try {
      const res = await clearShopAdminCatalog();
      if (res.success && res.data?.deleted) {
        await Swal.fire({
          icon: 'success',
          title: t('common.success', { defaultValue: 'Success' }),
          text: t('tools.shopDeliveries.clear.success', {
            defaultValue: 'Cleared. Offers: {{offers}} | Catalog: {{catalog}}',
            offers: res.data.deleted.shop_offer,
            catalog: res.data.deleted.shop_catalog,
          }),
          confirmButtonColor: '#f97316',
        });
        await load();
      } else {
        await Swal.fire({
          icon: 'error',
          title: t('common.error', { defaultValue: 'Error' }),
          text:
            getApiErrorMessage(res as any) ||
            t('tools.shopDeliveries.clear.error', { defaultValue: 'Failed to clear catalog.' }),
          confirmButtonColor: '#f97316',
        });
      }
    } catch (e: any) {
      const msg = e?.response?.data?.error || e?.message || 'Failed to clear catalog';
      await Swal.fire({
        icon: 'error',
        title: t('common.error', { defaultValue: 'Error' }),
        text: msg,
        confirmButtonColor: '#f97316',
      });
    } finally {
      setClearBusy(false);
    }
  };

  const onSyncScanner = async () => {
    setScannerBusy(true);
    try {
      const res = await syncShopAdminScanner();
      if (res.success && res.data) {
        await Swal.fire({
          icon: 'success',
          title: t('common.success', { defaultValue: 'Success' }),
          text: t('tools.shopDeliveries.scannerSyncResult', {
            defaultValue: 'Discovered: {{d}} | Created: {{c}}',
            d: res.data.discovered_setups,
            c: res.data.created_catalog,
          }),
          confirmButtonColor: '#f97316',
        });
        await load();
      } else {
        await Swal.fire({
          icon: 'error',
          title: t('common.error', { defaultValue: 'Error' }),
          text:
            getApiErrorMessage(res as any) ||
            t('tools.shopDeliveries.scannerSyncError', { defaultValue: 'Failed to sync scanner.' }),
          confirmButtonColor: '#f97316',
        });
      }
    } catch (e: any) {
      const msg = e?.response?.data?.error || e?.message || 'Failed to sync scanner';
      await Swal.fire({
        icon: 'error',
        title: t('common.error', { defaultValue: 'Error' }),
        text: msg,
        confirmButtonColor: '#f97316',
      });
    } finally {
      setScannerBusy(false);
    }
  };



  const onAddCatalogItem = async () => {
    const setup = addSetup.trim();
    if (!setup) {
      setAddCatalogError(t('tools.shopDeliveries.addCatalog.errorSetupRequired', { defaultValue: 'O campo Blueprint / Setup é obrigatório.' }));
      return;
    }
    const price = Number(addPrice);
    if (!Number.isFinite(price) || price < 0) {
      setAddCatalogError(t('tools.shopDeliveries.addCatalog.errorPrice', { defaultValue: 'O preço deve ser um número inteiro positivo.' }));
      return;
    }
    const qty = Number(addQty);
    if (!Number.isFinite(qty) || qty < 1) {
      setAddCatalogError(t('tools.shopDeliveries.addCatalog.errorQty', { defaultValue: 'A quantidade deve ser pelo menos 1.' }));
      return;
    }

    setAddCatalogError(null);
    setAddCatalogBusy(true);
    try {
      const res = await postShopAdminCatalog({
        setup,
        display_name: addDisplayName.trim() || undefined,
        price,
        qty,
        enabled: addEnabled,
      });

      if (res.success) {
        await Swal.fire({
          icon: 'success',
          title: t('common.success', { defaultValue: 'Success' }),
          text: t('tools.shopDeliveries.addCatalog.success', { defaultValue: '✅ Item adicionado com sucesso ao catálogo!' }),
          confirmButtonColor: '#f97316',
        });
        setAddSetup('');
        setAddDisplayName('');
        setAddPrice('0');
        setAddQty('1');
        setAddEnabled(true);
        setAddCatalogOpen(false);
        await load();
      } else {
        const msg = getApiErrorMessage(res as any);
        const friendlyMsg = msg?.includes('already exists')
          ? t('tools.shopDeliveries.addCatalog.errorDuplicate', { defaultValue: '⚠️ Este blueprint já existe no catálogo.' })
          : msg || t('tools.shopDeliveries.addCatalog.errorGeneric', { defaultValue: '❌ Erro ao adicionar item. Tente novamente.' });
        setAddCatalogError(friendlyMsg);
      }
    } catch (e: any) {
      const msg = e?.response?.data?.error || e?.message || 'Failed to add item';
      setAddCatalogError(msg);
    } finally {
      setAddCatalogBusy(false);
    }
  };

  return (
    <ModuleToolPage
      title={t('tools.shopDeliveries.title', { defaultValue: 'Shop & Deliveries' })}
      subtitle={t('tools.shopDeliveries.subtitle', {
        defaultValue: 'Admin catalog management (scanner, enable/disable, pricing, limits).',
      })}
    >
      <div className="flex gap-2 mb-4">
        <button
          type="button"
          onClick={() => setSection('catalog')}
          className={
            section === 'catalog'
              ? 'px-3 py-2 rounded-lg border border-scum-orange/60 bg-scum-orange/10 text-sm font-semibold text-scum-orange'
              : 'px-3 py-2 rounded-lg border border-white/15 bg-white/8 text-sm font-medium text-white/90 hover:bg-white/12 hover:border-white/25'
          }
        >
          {t('tools.shopDeliveries.sections.catalog', { defaultValue: 'Catalog' })}
        </button>
        <button
          type="button"
          onClick={() => setSection('wallet')}
          className={
            section === 'wallet'
              ? 'px-3 py-2 rounded-lg border border-scum-orange/60 bg-scum-orange/10 text-sm font-semibold text-scum-orange'
              : 'px-3 py-2 rounded-lg border border-white/15 bg-white/8 text-sm font-medium text-white/90 hover:bg-white/12 hover:border-white/25'
          }
        >
          {t('tools.shopDeliveries.sections.wallet', { defaultValue: 'Wallet' })}
        </button>
        <button
          type="button"
          onClick={() => setSection('base_upgrades')}
          className={
            section === 'base_upgrades'
              ? 'px-3 py-2 rounded-lg border border-scum-orange/60 bg-scum-orange/10 text-sm font-semibold text-scum-orange'
              : 'px-3 py-2 rounded-lg border border-white/15 bg-white/8 text-sm font-medium text-white/90 hover:bg-white/12 hover:border-white/25'
          }
        >
          {t('tools.shopDeliveries.sections.baseUpgrades', { defaultValue: 'Base Upgrades' })}
        </button>
        <button
          type="button"
          onClick={() => setSection('kits')}
          className={
            section === 'kits'
              ? 'px-3 py-2 rounded-lg border border-scum-orange/60 bg-scum-orange/10 text-sm font-semibold text-scum-orange'
              : 'px-3 py-2 rounded-lg border border-white/15 bg-white/8 text-sm font-medium text-white/90 hover:bg-white/12 hover:border-white/25'
          }
        >
          {t('tools.shopDeliveries.sections.kits', { defaultValue: 'Kits' })}
        </button>
        <button
          type="button"
          onClick={() => setSection('shop_notifications')}
          className={
            section === 'shop_notifications'
              ? 'px-3 py-2 rounded-lg border border-scum-orange/60 bg-scum-orange/10 text-sm font-semibold text-scum-orange'
              : 'px-3 py-2 rounded-lg border border-white/15 bg-white/8 text-sm font-medium text-white/90 hover:bg-white/12 hover:border-white/25'
          }
        >
          {t('tools.shopDeliveries.sections.shopNotifications', { defaultValue: 'RCON Notifications' })}
        </button>
        <button
          type="button"
          onClick={() => setSection('attributes')}
          className={
            section === 'attributes'
              ? 'px-3 py-2 rounded-lg border border-scum-orange/60 bg-scum-orange/10 text-sm font-semibold text-scum-orange'
              : 'px-3 py-2 rounded-lg border border-white/15 bg-white/8 text-sm font-medium text-white/90 hover:bg-white/12 hover:border-white/25'
          }
        >
          {t('tools.shopDeliveries.sections.attributes', { defaultValue: 'Atributos' })}
        </button>
        <button
          type="button"
          onClick={() => setSection('raid_webhooks')}
          className={
            section === 'raid_webhooks'
              ? 'px-3 py-2 rounded-lg border border-scum-orange/60 bg-scum-orange/10 text-sm font-semibold text-scum-orange'
              : 'px-3 py-2 rounded-lg border border-white/15 bg-white/8 text-sm font-medium text-white/90 hover:bg-white/12 hover:border-white/25'
          }
        >
          {t('tools.shopDeliveries.sections.raidWebhooks', { defaultValue: 'Webhook Raid (/rd)' })}
        </button>
        <button
          type="button"
          onClick={() => setSection('wanted_bounty')}
          className={
            section === 'wanted_bounty'
              ? 'px-3 py-2 rounded-lg border border-scum-orange/60 bg-scum-orange/10 text-sm font-semibold text-scum-orange'
              : 'px-3 py-2 rounded-lg border border-white/15 bg-white/8 text-sm font-medium text-white/90 hover:bg-white/12 hover:border-white/25'
          }
        >
          {t('tools.shopDeliveries.sections.wantedBounty', { defaultValue: 'Sistema de Procurados' })}
        </button>
      </div>

      {section === 'catalog' ? (
        <div className="space-y-3">
          <div className="card p-3 relative z-20">
            <div className="flex flex-col xl:flex-row xl:items-end gap-2">
              <div className="flex-1 grid grid-cols-1 md:grid-cols-[260px_auto_auto_minmax(0,1fr)_auto_auto_auto_auto] gap-2 items-end">
                <div>
                  <div className="text-xs text-white/60 mb-1">
                    {t('tools.shopDeliveries.scanner.chestId', { defaultValue: 'Scanner Chest ID' })}
                  </div>
                  <input
                    value={scannerChestId}
                    onChange={(e) => setScannerChestId(e.target.value)}
                    placeholder="60008"
                    className="w-full px-3 py-2 rounded-lg bg-white/5 border border-white/10 text-white text-sm focus:outline-none focus:ring-2 focus:ring-scum-orange"
                  />
                </div>

                <button
                  disabled={scannerBusy}
                  onClick={onSetScannerChest}
                  className="px-3 py-2 rounded-lg border border-white/15 bg-white/8 text-sm font-medium text-white/90 shadow-sm hover:text-white hover:bg-white/12 hover:border-white/25 focus:outline-none focus:ring-2 focus:ring-scum-orange/70 disabled:opacity-70 disabled:cursor-not-allowed"
                >
                  {scannerBusy
                    ? t('common.loading', { defaultValue: 'Loading...' })
                    : t('tools.shopDeliveries.scanner.set', { defaultValue: 'Set' })}
                </button>

                <button
                  disabled={scannerBusy}
                  onClick={onSyncScanner}
                  className="px-3 py-2 rounded-lg border border-scum-orange/60 bg-scum-orange/10 text-sm font-semibold text-scum-orange shadow-sm hover:bg-scum-orange/20 hover:border-scum-orange/80 focus:outline-none focus:ring-2 focus:ring-scum-orange/70 disabled:opacity-70 disabled:cursor-not-allowed"
                >
                  {scannerBusy
                    ? t('common.loading', { defaultValue: 'Loading...' })
                    : t('tools.shopDeliveries.scanner.sync', { defaultValue: 'Scanner' })}
                </button>

                <div className="min-w-0">
                  <SearchBar
                    value={query}
                    onChange={setQuery}
                    placeholder={t('tools.shopDeliveries.search', { defaultValue: 'Search catalog (name, setup, code)...' })}
                  />
                </div>

                <button
                  type="button"
                  disabled={loading}
                  onClick={load}
                  className="p-2 rounded-lg border border-white/15 bg-white/8 text-white/90 shadow-sm hover:text-white hover:bg-white/12 hover:border-white/25 focus:outline-none focus:ring-2 focus:ring-scum-orange/70 disabled:opacity-70 disabled:cursor-not-allowed"
                  title={t('common.refresh', { defaultValue: 'Refresh' })}
                  aria-label={t('common.refresh', { defaultValue: 'Refresh' })}
                >
                  <RefreshCw size={16} />
                </button>

                <button
                  type="button"
                  disabled={loading || items.length === 0}
                  onClick={exportCatalog}
                  className="p-2 rounded-lg border border-white/15 bg-white/8 text-white/90 shadow-sm hover:text-white hover:bg-white/12 hover:border-white/25 focus:outline-none focus:ring-2 focus:ring-scum-orange/70 disabled:opacity-70 disabled:cursor-not-allowed"
                  title={t('tools.shopDeliveries.export.title', { defaultValue: 'Export catalog' })}
                  aria-label={t('tools.shopDeliveries.export.title', { defaultValue: 'Export catalog' })}
                >
                  <Download size={16} />
                </button>

                <button
                  type="button"
                  disabled={loading}
                  onClick={() => void importCatalog()}
                  className="p-2 rounded-lg border border-white/15 bg-white/8 text-white/90 shadow-sm hover:text-white hover:bg-white/12 hover:border-white/25 focus:outline-none focus:ring-2 focus:ring-scum-orange/70 disabled:opacity-70 disabled:cursor-not-allowed"
                  title={t('tools.shopDeliveries.import.title', { defaultValue: 'Import catalog' })}
                  aria-label={t('tools.shopDeliveries.import.title', { defaultValue: 'Import catalog' })}
                >
                  <Upload size={16} />
                </button>



                <button
                  type="button"
                  onClick={() => { setAddCatalogOpen((v) => !v); setAddCatalogError(null); }}
                  className={
                    'p-2 rounded-lg border text-sm font-semibold shadow-sm focus:outline-none focus:ring-2 focus:ring-scum-orange/70 ' +
                    (addCatalogOpen
                      ? 'border-scum-orange/60 bg-scum-orange/10 text-scum-orange'
                      : 'border-white/15 bg-white/8 text-white/90 hover:text-white hover:bg-white/12 hover:border-white/25')
                  }
                  title={t('tools.shopDeliveries.addCatalog.toggleBtn', { defaultValue: 'Adicionar item ao catálogo' })}
                  aria-label={t('tools.shopDeliveries.addCatalog.toggleBtn', { defaultValue: 'Adicionar item ao catálogo' })}
                >
                  {addCatalogOpen ? <X size={16} /> : <PlusCircle size={16} />}
                </button>
              </div>

              <div className="flex items-center justify-between xl:justify-end gap-2">
                <div className="text-xs text-white/50">
                  {loading
                    ? t('common.loading', { defaultValue: 'Loading...' })
                    : t('tools.shopDeliveries.resultsCount', {
                        defaultValue: 'Results: {{count}}',
                        count: filtered.length,
                      })}
                </div>

                <div className="relative">
                  <button
                    type="button"
                    onClick={() => setCatalogDangerOpen((v) => !v)}
                    className="px-3 py-2 rounded-lg border border-red-500/40 bg-red-500/10 text-sm font-semibold text-red-300 shadow-sm hover:bg-red-500/20 hover:border-red-500/70 focus:outline-none focus:ring-2 focus:ring-red-500/30"
                  >
                    {t('tools.shopDeliveries.clear.section', { defaultValue: 'Danger zone' })}
                  </button>

                  {catalogDangerOpen && (
                    <div className="absolute right-0 mt-2 w-[320px] rounded-lg border border-red-500/30 bg-[#0b1220] p-3 shadow-lg z-[100]">
                      <div className="text-xs text-white/60">
                        {t('tools.shopDeliveries.clear.hint', {
                          defaultValue: 'Use this to hard-clear the catalog before re-running the scanner from scratch.',
                        })}
                      </div>
                      <button
                        disabled={clearBusy}
                        onClick={onClearCatalog}
                        className="mt-3 w-full px-3 py-2 rounded-lg border border-red-500/40 bg-red-500/10 text-sm font-semibold text-red-300 shadow-sm hover:bg-red-500/20 hover:border-red-500/70 focus:outline-none focus:ring-2 focus:ring-red-500/30 disabled:opacity-70 disabled:cursor-not-allowed"
                      >
                        {clearBusy
                          ? t('common.loading', { defaultValue: 'Loading...' })
                          : t('tools.shopDeliveries.clear.button', { defaultValue: 'Clear catalog' })}
                      </button>
                    </div>
                  )}
                </div>
              </div>
            </div>

            {error && <div className="mt-2 text-sm text-red-400">{error}</div>}
          </div>

          {addCatalogOpen && (
            <div className="card p-4 border border-scum-orange/30 bg-scum-orange/5 animate-in fade-in slide-in-from-top-2 duration-200">
              <div className="flex items-center justify-between mb-3">
                <div className="flex items-center gap-2">
                  <PlusCircle size={16} className="text-scum-orange" />
                  <span className="text-sm font-semibold text-white/90">
                    {t('tools.shopDeliveries.addCatalog.title', { defaultValue: 'Adicionar ao Catálogo da Loja' })}
                  </span>
                </div>
                <button
                  type="button"
                  onClick={() => { setAddCatalogOpen(false); setAddCatalogError(null); }}
                  className="p-1 rounded text-white/40 hover:text-white/80"
                >
                  <X size={16} />
                </button>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-[1fr_1fr_120px_80px_auto] gap-3 items-start">
                <div>
                  <div className="text-xs text-white/60 mb-1">
                    {t('tools.shopDeliveries.addCatalog.setup', { defaultValue: 'Blueprint / Setup *' })}
                  </div>
                  <input
                    id="add-catalog-setup"
                    value={addSetup}
                    onChange={(e) => setAddSetup(e.target.value)}
                    placeholder="BPC_SidecarBike"
                    disabled={addCatalogBusy}
                    className="w-full px-3 py-2 rounded-lg bg-white/5 border border-white/10 text-white text-sm focus:outline-none focus:ring-2 focus:ring-scum-orange disabled:opacity-60"
                  />
                  <div className="text-[11px] text-white/35 mt-1">
                    {t('tools.shopDeliveries.addCatalog.setupHint', { defaultValue: 'Ex: BPC_SidecarBike — copie do jogo' })}
                  </div>
                </div>

                <div>
                  <div className="text-xs text-white/60 mb-1">
                    {t('tools.shopDeliveries.addCatalog.displayName', { defaultValue: 'Nome de Exibição' })}
                  </div>
                  <input
                    id="add-catalog-display-name"
                    value={addDisplayName}
                    onChange={(e) => setAddDisplayName(e.target.value)}
                    placeholder="Sidecar Bike"
                    disabled={addCatalogBusy}
                    className="w-full px-3 py-2 rounded-lg bg-white/5 border border-white/10 text-white text-sm focus:outline-none focus:ring-2 focus:ring-scum-orange disabled:opacity-60"
                  />
                </div>

                <div>
                  <div className="text-xs text-white/60 mb-1">
                    {t('tools.shopDeliveries.addCatalog.price', { defaultValue: 'Preço (coins)' })}
                  </div>
                  <input
                    id="add-catalog-price"
                    value={addPrice}
                    onChange={(e) => setAddPrice(e.target.value.replace(/[^0-9]/g, ''))}
                    inputMode="numeric"
                    placeholder="0"
                    disabled={addCatalogBusy}
                    className="w-full px-3 py-2 rounded-lg bg-white/5 border border-white/10 text-white text-sm text-right tabular-nums focus:outline-none focus:ring-2 focus:ring-scum-orange disabled:opacity-60"
                  />
                </div>

                <div>
                  <div className="text-xs text-white/60 mb-1">
                    {t('tools.shopDeliveries.addCatalog.qty', { defaultValue: 'Qtd' })}
                  </div>
                  <input
                    id="add-catalog-qty"
                    value={addQty}
                    onChange={(e) => setAddQty(e.target.value.replace(/[^0-9]/g, ''))}
                    inputMode="numeric"
                    placeholder="1"
                    disabled={addCatalogBusy}
                    className="w-full px-3 py-2 rounded-lg bg-white/5 border border-white/10 text-white text-sm text-right tabular-nums focus:outline-none focus:ring-2 focus:ring-scum-orange disabled:opacity-60"
                  />
                </div>

                <div className="flex flex-col items-center pb-1">
                  <div className="text-xs mb-1 select-none pointer-events-none opacity-0 hidden md:block" aria-hidden="true">
                    Placeholder
                  </div>
                  <div className="flex items-center h-[38px]">
                    <label className="flex items-center gap-1.5 text-xs text-white/70 select-none cursor-pointer whitespace-nowrap">
                      <input
                        type="checkbox"
                        checked={addEnabled}
                        onChange={(e) => setAddEnabled(e.target.checked)}
                        disabled={addCatalogBusy}
                        className="accent-scum-orange"
                      />
                      {t('tools.shopDeliveries.addCatalog.enabled', { defaultValue: 'Ativo' })}
                    </label>
                  </div>
                </div>
              </div>

              {addCatalogError && (
                <div className="mt-3 text-sm text-red-400 rounded-lg border border-red-500/20 bg-red-500/5 px-3 py-2">
                  {addCatalogError}
                </div>
              )}

              <div className="flex items-center justify-end gap-2 mt-4">
                <button
                  type="button"
                  disabled={addCatalogBusy}
                  onClick={() => { setAddCatalogOpen(false); setAddCatalogError(null); }}
                  className="px-4 py-2 rounded-lg border border-white/15 bg-white/8 text-sm font-medium text-white/90 hover:bg-white/12 hover:border-white/25 disabled:opacity-60 disabled:cursor-not-allowed"
                >
                  {t('common.cancel', { defaultValue: 'Cancelar' })}
                </button>
                <button
                  type="button"
                  disabled={addCatalogBusy || !addSetup.trim()}
                  onClick={() => void onAddCatalogItem()}
                  className="px-4 py-2 rounded-lg border border-scum-orange/60 bg-scum-orange/10 text-sm font-semibold text-scum-orange hover:bg-scum-orange/20 hover:border-scum-orange/80 focus:outline-none focus:ring-2 focus:ring-scum-orange/70 disabled:opacity-60 disabled:cursor-not-allowed flex items-center gap-2"
                >
                  {addCatalogBusy ? (
                    t('common.loading', { defaultValue: 'Salvando...' })
                  ) : (
                    <>
                      <PlusCircle size={14} />
                      {t('tools.shopDeliveries.addCatalog.submitBtn', { defaultValue: 'Adicionar ✓' })}
                    </>
                  )}
                </button>
              </div>
            </div>
          )}

          <div className="card p-2 overflow-x-hidden overflow-y-auto">
            <div className="grid grid-cols-[56px_minmax(0,1.4fr)_minmax(0,1.8fr)_84px_76px_80px_64px_84px_84px_140px] items-center gap-2 p-3 pr-4 text-xs uppercase text-white/40 border-b border-white/10">
              <div>
                <HeaderWithHelp
                  labelKey="tools.shopDeliveries.table.code"
                  labelDefault="Code"
                  helpKey="tools.shopDeliveries.tableHelp.code"
                  helpDefault="Unique item identifier (used to update this item)."
                />
              </div>
              <div>
                <HeaderWithHelp
                  labelKey="tools.shopDeliveries.table.name"
                  labelDefault="Name"
                  helpKey="tools.shopDeliveries.tableHelp.name"
                  helpDefault="Display name shown to players."
                />
              </div>
              <div>
                <HeaderWithHelp
                  labelKey="tools.shopDeliveries.table.setup"
                  labelDefault="Setup"
                  helpKey="tools.shopDeliveries.tableHelp.setup"
                  helpDefault="Scanner setup/group this item belongs to (used to organize the catalog)."
                />
              </div>
              <div className="text-center">
                <div className="relative flex items-center justify-center">
                  <input
                    ref={catalogHeaderRef}
                    type="checkbox"
                    checked={catalogTri.checked}
                    disabled={bulkBusy || filtered.length === 0}
                    onChange={() => onToggleAllInHeader('catalog_enabled')}
                    className="h-4 w-4"
                    title={t('tools.shopDeliveries.bulk.toggleAllCatalog', { defaultValue: 'Toggle all (filtered) catalog enabled' })}
                  />
                  <span
                    className="absolute right-0 text-white/30"
                    title={t('tools.shopDeliveries.tableHelp.catalog', {
                      defaultValue: 'If disabled, the item is hidden/disabled in the catalog.',
                    })}
                  >
                    <Info size={14} />
                  </span>
                </div>
              </div>
              <div className="text-center">
                <div className="relative flex items-center justify-center">
                  <input
                    ref={offerHeaderRef}
                    type="checkbox"
                    checked={offerTri.checked}
                    disabled={bulkBusy || filtered.length === 0}
                    onChange={() => onToggleAllInHeader('offer_enabled')}
                    className="h-4 w-4"
                    title={t('tools.shopDeliveries.bulk.toggleAllOffer', { defaultValue: 'Toggle all (filtered) offer enabled' })}
                  />
                  <span
                    className="absolute right-0 text-white/30"
                    title={t('tools.shopDeliveries.tableHelp.offer', {
                      defaultValue: 'If disabled, the item cannot be purchased as an offer.',
                    })}
                  >
                    <Info size={14} />
                  </span>
                </div>
              </div>
              <div>
                <div className="flex justify-end">
                  <HeaderWithHelp
                    labelKey="tools.shopDeliveries.table.price"
                    labelDefault="Price"
                    helpKey="tools.shopDeliveries.tableHelp.price"
                    helpDefault="Price for the offer (in your server currency)."
                  />
                </div>
              </div>
              <div>
                <div className="flex justify-end">
                  <HeaderWithHelp
                    labelKey="tools.shopDeliveries.table.qty"
                    labelDefault="Qty"
                    helpKey="tools.shopDeliveries.tableHelp.qty"
                    helpDefault="Quantity delivered per purchase."
                  />
                </div>
              </div>
              <div>
                <div className="flex justify-end">
                  <HeaderWithHelp
                    labelKey="tools.shopDeliveries.table.maxOrder"
                    labelDefault="Max/Order"
                    helpKey="tools.shopDeliveries.tableHelp.maxOrder"
                    helpDefault="Maximum quantity allowed per purchase/order."
                  />
                </div>
              </div>
              <div>
                <div className="flex justify-end">
                  <HeaderWithHelp
                    labelKey="tools.shopDeliveries.table.maxDay"
                    labelDefault="Max/Day"
                    helpKey="tools.shopDeliveries.tableHelp.maxDay"
                    helpDefault="Maximum quantity allowed per day (per player)."
                  />
                </div>
              </div>
              <div className="flex items-center justify-end pr-1">
                <button
                  type="button"
                  disabled={bulkBusy || dirtyCodes.length === 0}
                  onClick={() => void onSaveAll()}
                  className={
                    "px-3 py-2 rounded-lg border text-sm font-semibold shadow-sm focus:outline-none focus:ring-2 focus:ring-scum-orange/70 disabled:opacity-70 disabled:cursor-not-allowed " +
                    (bulkBusy || dirtyCodes.length === 0
                      ? 'border-white/15 bg-white/5 text-white/40'
                      : 'border-white/30 bg-white/10 text-white hover:bg-white/15 hover:border-white/40')
                  }
                  title={
                    bulkBusy
                      ? t('tools.shopDeliveries.bulk.savingProgress', {
                          defaultValue: 'Saving {{done}}/{{total}}',
                          done: bulkDone,
                          total: bulkTotal,
                        })
                      : t('tools.shopDeliveries.bulk.saveAll', {
                          defaultValue: 'Save ({{count}})',
                          count: dirtyCodes.length,
                        })
                  }
                  aria-label={t('tools.shopDeliveries.bulk.saveAll', {
                    defaultValue: 'Save ({{count}})',
                    count: dirtyCodes.length,
                  })}
                >
                  {bulkBusy
                    ? t('tools.shopDeliveries.bulk.savingProgress', {
                        defaultValue: 'Saving {{done}}/{{total}}',
                        done: bulkDone,
                        total: bulkTotal,
                      })
                    : t('tools.shopDeliveries.bulk.saveAll', {
                        defaultValue: 'Save ({{count}})',
                        count: dirtyCodes.length,
                      })}
                </button>
              </div>
            </div>

            {filtered.length === 0 && !loading ? (
              <div className="p-4 text-sm text-white/60">{t('tools.shopDeliveries.empty', { defaultValue: 'No items.' })}</div>
            ) : (
              <div className="divide-y divide-white/10">
                {filtered.map((it) => {
                  const d = drafts[it.code] || buildDraft(it);
                  const payload = diffPayload(it, d);
                  const dirty = hasChanges(payload);
                  const saving = savingCode === it.code;

                  return (
                    <div
                      key={it.code}
                      className="grid grid-cols-[56px_minmax(0,1.4fr)_minmax(0,1.8fr)_84px_76px_80px_64px_84px_84px_140px] gap-2 p-3 pr-4 items-center"
                    >
                      <div className="text-sm text-white/80 tabular-nums">{it.code}</div>

                      <input
                        value={d.display_name}
                        onChange={(e) => setDraft(it.code, { display_name: e.target.value })}
                        className="min-w-0 px-2 py-1 rounded bg-white/5 border border-white/10 text-white text-sm focus:outline-none focus:ring-2 focus:ring-scum-orange"
                      />

                      <div className="text-xs text-white/60 truncate" title={it.setup}>
                        {it.setup}
                      </div>

                      <div className="flex justify-center">
                        <input
                          type="checkbox"
                          checked={d.catalog_enabled}
                          onChange={(e) => setDraft(it.code, { catalog_enabled: e.target.checked })}
                          className="h-4 w-4"
                        />
                      </div>

                      <div className="flex justify-center">
                        <input
                          type="checkbox"
                          checked={d.offer_enabled}
                          onChange={(e) => setDraft(it.code, { offer_enabled: e.target.checked })}
                          className="h-4 w-4"
                        />
                      </div>

                      <input
                        value={d.price}
                        inputMode="decimal"
                        onChange={(e) => setDraft(it.code, { price: clampDecimal(e.target.value, 3) })}
                        className="min-w-0 w-full px-2 py-1 rounded bg-white/5 border border-white/10 text-white text-sm text-right tabular-nums focus:outline-none focus:ring-2 focus:ring-scum-orange"
                      />

                      <input
                        value={d.qty}
                        onChange={(e) => setDraft(it.code, { qty: e.target.value })}
                        inputMode="numeric"
                        className="min-w-0 w-full px-2 py-1 rounded bg-white/5 border border-white/10 text-white text-sm text-right tabular-nums focus:outline-none focus:ring-2 focus:ring-scum-orange"
                      />

                      <input
                        value={d.max_per_order}
                        onChange={(e) => setDraft(it.code, { max_per_order: e.target.value })}
                        inputMode="numeric"
                        className="min-w-0 w-full px-2 py-1 rounded bg-white/5 border border-white/10 text-white text-sm text-right tabular-nums focus:outline-none focus:ring-2 focus:ring-scum-orange"
                      />

                      <input
                        value={d.max_per_day}
                        onChange={(e) => setDraft(it.code, { max_per_day: e.target.value })}
                        inputMode="numeric"
                        className="min-w-0 w-full px-2 py-1 rounded bg-white/5 border border-white/10 text-white text-sm text-right tabular-nums focus:outline-none focus:ring-2 focus:ring-scum-orange"
                      />

                      <div className="flex justify-end gap-2 pr-1">
                        <button
                          disabled={!dirty || saving}
                          title={t('tools.shopDeliveries.actions.revertHelp', {
                            defaultValue:
                              'Revert unsaved changes for this row. Enabled only when you have edits not saved yet.',
                          })}
                          onClick={() => {
                            setDrafts((prev) => ({ ...prev, [it.code]: buildDraft(it) }));
                          }}
                          className="p-2 rounded-lg border border-white/15 bg-white/8 text-white/90 shadow-sm hover:text-white hover:bg-white/12 hover:border-white/25 focus:outline-none focus:ring-2 focus:ring-scum-orange/70 disabled:opacity-70 disabled:cursor-not-allowed"
                        >
                          <RotateCcw size={14} />
                        </button>
                        <button
                          disabled={!dirty || saving}
                          title={t('tools.shopDeliveries.actions.saveHelp', {
                            defaultValue:
                              'Save changes for this row to the server. After saving, there is nothing to revert unless you edit again.',
                          })}
                          onClick={() => onSaveRow(it)}
                          className="p-2 rounded-lg border border-scum-orange/60 bg-scum-orange/10 text-scum-orange shadow-sm hover:bg-scum-orange/20 hover:border-scum-orange/80 focus:outline-none focus:ring-2 focus:ring-scum-orange/70 disabled:opacity-70 disabled:cursor-not-allowed"
                        >
                          {saving ? <span className="text-xs">{t('common.saving', { defaultValue: 'Saving...' })}</span> : <Save size={14} />}
                        </button>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        </div>
      ) : section === 'base_upgrades' ? (
        <div className="space-y-3">
          <div className="card p-3">
            <div className="flex flex-col lg:flex-row lg:items-end gap-2">
              <div className="min-w-0 flex-1">
                <SearchBar
                  value={ownersQuery}
                  onChange={setOwnersQuery}
                  placeholder={t('tools.shopDeliveries.baseUpgrades.search', { defaultValue: 'Search flags (owner, id)...' })}
                />
              </div>

              <div className="flex items-end gap-2 flex-wrap">
                <div>
                  <div className="text-xs text-white/60 mb-1">
                    {t('tools.shopDeliveries.baseUpgrades.pageSize', { defaultValue: 'Page size' })}
                  </div>
                  <select
                    value={ownersPageSize}
                    onChange={(e) => {
                      const next = Number(e.target.value);
                      setOwnersPageSize(next);
                      setOwnersPage(1);
                      void loadOwners(1, next);
                    }}
                    className="px-3 py-2 rounded-lg bg-white/5 border border-white/10 text-white text-sm focus:outline-none focus:ring-2 focus:ring-scum-orange"
                  >
                    {[25, 50, 100].map((n) => (
                      <option key={n} value={n} className="bg-black">
                        {n}
                      </option>
                    ))}
                  </select>
                </div>

                <button
                  type="button"
                  disabled={ownersBusy}
                  onClick={() => void loadOwners(ownersPage, ownersPageSize)}
                  className="p-2 rounded-lg border border-white/15 bg-white/8 text-white/90 shadow-sm hover:text-white hover:bg-white/12 hover:border-white/25 focus:outline-none focus:ring-2 focus:ring-scum-orange/70 disabled:opacity-70 disabled:cursor-not-allowed"
                  title={t('common.refresh', { defaultValue: 'Refresh' })}
                  aria-label={t('common.refresh', { defaultValue: 'Refresh' })}
                >
                  <RefreshCw size={16} />
                </button>
              </div>
            </div>

            {ownersError && <div className="mt-2 text-sm text-red-400">{ownersError}</div>}
          </div>

          <div className="grid grid-cols-1 xl:grid-cols-[minmax(0,1fr)_360px] gap-3">
            <div className="card p-3">
              <div className="flex items-center justify-between mb-2">
                <div className="text-sm font-semibold text-white/90">
                  {t('tools.shopDeliveries.baseUpgrades.flagsTitle', { defaultValue: 'Flags / Bases' })}
                </div>
                <div className="text-xs text-white/50">
                  {t('tools.shopDeliveries.resultsCount', { defaultValue: 'Results: {{count}}', count: ownersFiltered.length })}
                </div>
              </div>

              <div className="overflow-auto border border-white/10 rounded-lg">
                <table className="min-w-full text-sm">
                  <thead className="bg-white/5 text-white/70">
                    <tr>
                      <th className="text-left px-3 py-2">
                        {t('tools.shopDeliveries.baseUpgrades.columns.flagId', { defaultValue: 'Flag ID' })}
                      </th>
                      <th className="text-left px-3 py-2">
                        {t('tools.shopDeliveries.baseUpgrades.columns.owner', { defaultValue: 'Owner' })}
                      </th>
                      <th className="text-left px-3 py-2">
                        {t('tools.shopDeliveries.baseUpgrades.columns.type', { defaultValue: 'Type' })}
                      </th>
                      <th className="text-right px-3 py-2">
                        {t('tools.shopDeliveries.baseUpgrades.columns.elements', { defaultValue: 'Elements' })}
                      </th>
                      <th className="text-left px-3 py-2">
                        {t('tools.shopDeliveries.baseUpgrades.columns.lastSeen', { defaultValue: 'Last seen' })}
                      </th>
                    </tr>
                  </thead>
                  <tbody>
                    {ownersFiltered.map((it) => {
                      const selected = Number(selectedFlagId) === Number(it.flag_id);
                      return (
                        <tr
                          key={it.flag_id}
                          onClick={() => setSelectedFlagId(it.flag_id)}
                          className={
                            'cursor-pointer border-t border-white/5 hover:bg-white/5 ' +
                            (selected ? 'bg-scum-orange/10' : '')
                          }
                        >
                          <td className="px-3 py-2 font-mono text-white/90">{it.flag_id}</td>
                          <td className="px-3 py-2 text-white/90">{it.owner || '—'}</td>
                          <td className="px-3 py-2 text-white/70">{it.owner_type || 'unknown'}</td>
                          <td className="px-3 py-2 text-right text-white/70">{Number(it.elements ?? 0)}</td>
                          <td className="px-3 py-2 text-white/60">{it.last_seen_at || '—'}</td>
                        </tr>
                      );
                    })}
                    {ownersFiltered.length === 0 && (
                      <tr>
                        <td className="px-3 py-6 text-center text-white/50" colSpan={5}>
                          {ownersBusy
                            ? t('common.loading', { defaultValue: 'Loading...' })
                            : t('tools.shopDeliveries.baseUpgrades.empty', { defaultValue: 'No flags found.' })}
                        </td>
                      </tr>
                    )}
                  </tbody>
                </table>
              </div>

              <div className="flex items-center justify-between mt-3">
                <div className="text-xs text-white/50">
                  {t('tools.shopDeliveries.baseUpgrades.pagination', {
                    defaultValue: 'Page {{p}} / {{tp}} (total {{total}})',
                    p: ownersPage,
                    tp: ownersTotalPages,
                    total: ownersTotal,
                  })}
                </div>
                <div className="flex items-center gap-2">
                  <button
                    disabled={ownersBusy || ownersPage <= 1}
                    onClick={() => {
                      const next = Math.max(1, ownersPage - 1);
                      void loadOwners(next, ownersPageSize);
                    }}
                    className="px-3 py-2 rounded-lg border border-white/15 bg-white/8 text-sm font-medium text-white/90 hover:bg-white/12 hover:border-white/25 disabled:opacity-70 disabled:cursor-not-allowed"
                  >
                    {t('common.prev', { defaultValue: 'Prev' })}
                  </button>
                  <button
                    disabled={ownersBusy || ownersPage >= ownersTotalPages}
                    onClick={() => {
                      const next = Math.min(ownersTotalPages, ownersPage + 1);
                      void loadOwners(next, ownersPageSize);
                    }}
                    className="px-3 py-2 rounded-lg border border-white/15 bg-white/8 text-sm font-medium text-white/90 hover:bg-white/12 hover:border-white/25 disabled:opacity-70 disabled:cursor-not-allowed"
                  >
                    {t('common.next', { defaultValue: 'Next' })}
                  </button>
                </div>
              </div>
            </div>

            <div className="card p-3">
              <div className="text-sm font-semibold text-white/90 mb-2">
                {t('tools.shopDeliveries.baseUpgrades.configTitle', { defaultValue: 'Upgrade config' })}
              </div>

              <div className="space-y-2">
                <div className="text-xs text-white/60">
                  {t('tools.shopDeliveries.baseUpgrades.selectedFlag', { defaultValue: 'Selected flag' })}
                </div>
                <div className="px-3 py-2 rounded-lg bg-white/5 border border-white/10 text-white/90 font-mono text-sm">
                  {selectedFlagId ? `#${selectedFlagId}` : '—'}
                </div>

                <div>
                  <div className="text-xs text-white/60 mb-1">
                    {t('tools.shopDeliveries.baseUpgrades.targetLevel', { defaultValue: 'Target level (1..5)' })}
                  </div>
                  <select
                    value={upgradeTargetLevel}
                    onChange={(e) => setUpgradeTargetLevel(Number(e.target.value))}
                    className="w-full px-3 py-2 rounded-lg bg-white/5 border border-white/10 text-white text-sm focus:outline-none focus:ring-2 focus:ring-scum-orange"
                  >
                    {[1, 2, 3, 4, 5].map((n) => (
                      <option key={n} value={n} className="bg-black">
                        {n}
                      </option>
                    ))}
                  </select>
                </div>

                <input type="hidden" value={upgradeFallbackLowest ? '1' : '0'} readOnly />

                <label className="flex items-center gap-2 text-sm text-white/80 select-none">
                  <input
                    type="checkbox"
                    checked={upgradeRunNowIfOffline}
                    onChange={(e) => setUpgradeRunNowIfOffline(e.target.checked)}
                    className="accent-scum-orange"
                  />
                  {t('tools.shopDeliveries.baseUpgrades.runNowIfOffline', {
                    defaultValue: 'Run now if server is offline',
                  })}
                </label>

                <label className="flex items-center gap-2 text-sm text-white/80 select-none">
                  <input
                    type="checkbox"
                    checked={upgradeAutoEnrichWhitelist}
                    onChange={(e) => setUpgradeAutoEnrichWhitelist(e.target.checked)}
                    className="accent-scum-orange"
                  />
                  {t('tools.shopDeliveries.baseUpgrades.autoEnrichWhitelist.label', {
                    defaultValue: 'Auto-enrich whitelist on dry-run',
                  })}
                </label>

                <div className="flex gap-2 pt-1">
                  <button
                    type="button"
                    disabled={!selectedFlagId || dryRunBusy || ownersBusy}
                    onClick={() => void runDryRun()}
                    className="flex-1 px-3 py-2 rounded-lg border border-white/15 bg-white/8 text-sm font-medium text-white/90 shadow-sm hover:text-white hover:bg-white/12 hover:border-white/25 focus:outline-none focus:ring-2 focus:ring-scum-orange/70 disabled:opacity-70 disabled:cursor-not-allowed"
                  >
                    {dryRunBusy
                      ? t('common.loading', { defaultValue: 'Loading...' })
                      : t('tools.shopDeliveries.baseUpgrades.dryRun', { defaultValue: 'Dry-run' })}
                  </button>
                  <button
                    type="button"
                    disabled={!selectedFlagId || scheduleBusy || !dryRunResult?.success || dryRunBusy}
                    onClick={() => void runSchedule()}
                    className="flex-1 px-3 py-2 rounded-lg border border-scum-orange/60 bg-scum-orange/10 text-sm font-semibold text-scum-orange shadow-sm hover:bg-scum-orange/20 hover:border-scum-orange/80 focus:outline-none focus:ring-2 focus:ring-scum-orange/70 disabled:opacity-70 disabled:cursor-not-allowed"
                  >
                    {scheduleBusy
                      ? t('common.loading', { defaultValue: 'Loading...' })
                      : t('tools.shopDeliveries.baseUpgrades.scheduleBtn', { defaultValue: 'Schedule' })}
                  </button>
                </div>

                {dryRunError && <div className="text-sm text-red-400">{dryRunError}</div>}

                {dryRunResult?.success && dryRunResult.data && (
                  <div className="mt-2 rounded-lg border border-white/10 bg-white/5 p-3 space-y-2">
                    <div className="text-sm font-semibold text-white/90">
                      {t('tools.shopDeliveries.baseUpgrades.previewTitle', { defaultValue: 'Preview' })}
                    </div>
                    <div className="grid grid-cols-2 gap-2 text-xs">
                      <div className="rounded-lg border border-white/10 bg-black/20 p-2">
                        <div className="text-white/50">to_change</div>
                        <div className="text-white/90 text-sm font-semibold">
                          {Number(dryRunResult.data.stats?.to_change ?? 0)}
                        </div>
                      </div>
                      <div className="rounded-lg border border-white/10 bg-black/20 p-2">
                        <div className="text-white/50">already_target</div>
                        <div className="text-white/90 text-sm font-semibold">
                          {Number(dryRunResult.data.stats?.already_target ?? 0)}
                        </div>
                      </div>
                      <div className="rounded-lg border border-white/10 bg-black/20 p-2">
                        <div className="text-white/50">no_mapping</div>
                        <div className="text-white/90 text-sm font-semibold">
                          {Number(dryRunResult.data.stats?.no_mapping ?? 0)}
                        </div>
                      </div>
                      <div className="rounded-lg border border-white/10 bg-black/20 p-2">
                        <div className="text-white/50">not_whitelisted</div>
                        <div className="text-white/90 text-sm font-semibold">
                          {Number(dryRunResult.data.stats?.not_whitelisted ?? 0)}
                        </div>
                      </div>
                    </div>

                    {((dryRunResult.data as any).debug?.auto_whitelisted || 0) > 0 && (
                      <div className="text-xs text-white/70">
                        {t('tools.shopDeliveries.baseUpgrades.autoEnrichWhitelist.debugAutoWhitelisted', {
                          defaultValue: 'Auto-whitelisted: {{count}}',
                          count: Number((dryRunResult.data as any).debug?.auto_whitelisted ?? 0),
                        })}
                      </div>
                    )}

                    {Array.isArray((dryRunResult.data as any).debug?.auto_whitelisted_assets) &&
                      ((dryRunResult.data as any).debug?.auto_whitelisted_assets || []).length > 0 && (
                        <div className="text-xs text-white/60">
                          {t('tools.shopDeliveries.baseUpgrades.autoEnrichWhitelist.debugAssetsSample', {
                            defaultValue: 'Auto-whitelisted assets (sample):',
                          })}{' '}
                          {String(((dryRunResult.data as any).debug?.auto_whitelisted_assets || []).join(', '))}
                        </div>
                      )}

                    <div className="text-xs text-white/60">
                      {t('tools.shopDeliveries.baseUpgrades.sample', { defaultValue: 'Sample changes' })}
                      {dryRunResult.data.changes_sample_truncated ? ' (truncated)' : ''}
                    </div>
                    <div className="max-h-56 overflow-auto border border-white/10 rounded-lg">
                      <table className="min-w-full text-xs">
                        <thead className="bg-white/5 text-white/70">
                          <tr>
                            <th className="text-left px-2 py-1">element_id</th>
                            <th className="text-left px-2 py-1">from</th>
                            <th className="text-left px-2 py-1">to</th>
                            <th className="text-left px-2 py-1">family</th>
                          </tr>
                        </thead>
                        <tbody>
                          {(dryRunResult.data.changes_sample || []).map((c) => (
                            <tr key={c.element_id} className="border-t border-white/5">
                              <td className="px-2 py-1 font-mono text-white/80">{c.element_id}</td>
                              <td className="px-2 py-1 text-white/80">{(c as any).from_asset ?? (c as any).old_asset ?? '—'}</td>
                              <td className="px-2 py-1 text-white/80">{(c as any).to_asset ?? (c as any).new_asset ?? '—'}</td>
                              <td className="px-2 py-1 text-white/60">{c.family_key}</td>
                            </tr>
                          ))}
                          {(dryRunResult.data.changes_sample || []).length === 0 && (
                            <tr>
                              <td className="px-2 py-4 text-center text-white/50" colSpan={4}>
                                {t('tools.shopDeliveries.baseUpgrades.noSample', { defaultValue: 'No sample returned.' })}
                              </td>
                            </tr>
                          )}
                        </tbody>
                      </table>
                    </div>
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>
      ) : section === 'kits' ? (
        <Kits isTab={true} />
      ) : section === 'shop_notifications' ? (
        <ShopNotificationsTab />
      ) : section === 'attributes' ? (
        <AttributesConfigTab />
      ) : section === 'raid_webhooks' ? (
        <RaidWebhookConfigTab />
      ) : section === 'wanted_bounty' ? (
        <WantedBountyConfigTab />
      ) : (
        <div className="grid grid-cols-1 xl:grid-cols-[420px_1fr] gap-4">
          <div className="card p-4 space-y-3">
            <div className="flex items-center gap-2">
              <div className="flex items-center gap-2">
                <button
                  type="button"
                  onClick={() => setWalletTab('wallet')}
                  className={
                    walletTab === 'wallet'
                      ? 'px-2 py-1 rounded-lg border border-scum-orange/60 bg-scum-orange/10 text-xs font-semibold text-scum-orange'
                      : 'px-2 py-1 rounded-lg border border-white/15 bg-white/8 text-xs font-medium text-white/90 hover:bg-white/12 hover:border-white/25'
                  }
                >
                  {t('tools.shopDeliveries.walletTabs.wallet', { defaultValue: 'Wallet' })}
                </button>
                <button
                  type="button"
                  onClick={() => {
                    setWalletTab('rewards');
                    setPlaytimeError(null);
                  }}
                  className={
                    walletTab === 'rewards'
                      ? 'px-2 py-1 rounded-lg border border-scum-orange/60 bg-scum-orange/10 text-xs font-semibold text-scum-orange'
                      : 'px-2 py-1 rounded-lg border border-white/15 bg-white/8 text-xs font-medium text-white/90 hover:bg-white/12 hover:border-white/25'
                  }
                >
                  {t('tools.shopDeliveries.walletTabs.rewards', { defaultValue: 'Rewards' })}
                </button>
              </div>
            </div>

            {walletTab === 'wallet' ? (
              <>
                <div className="text-xs text-white/60">
                  {walletSteamId ? (
                    <div>
                      {t('tools.shopDeliveries.wallet.selected', {
                        defaultValue: 'Selected: {{steam_id}}',
                        steam_id: walletSteamId,
                      })}
                    </div>
                  ) : (
                    <div>{t('tools.shopDeliveries.wallet.selectPlayerHint', { defaultValue: 'Select a player on the left.' })}</div>
                  )}
                </div>

            <div className="grid grid-cols-1 sm:grid-cols-[1fr_auto] gap-2 items-end">
              <div className="text-xs text-white/60">
                {walletBalance != null && walletBalanceSteamId ? (
                  <div>
                    {t('tools.shopDeliveries.wallet.balanceLabel', {
                      defaultValue: 'Balance ({{steam_id}}): {{balance}}',
                      steam_id: walletBalanceSteamId,
                      balance: walletBalance,
                    })}
                  </div>
                ) : (
                  <div>{t('tools.shopDeliveries.wallet.balanceEmpty', { defaultValue: 'No balance loaded.' })}</div>
                )}
              </div>
              <button
                disabled={Boolean((walletSteamId && walletBalancesBusy[walletSteamId]) || !walletSteamId)}
                onClick={() => void fetchWalletBalanceFor(walletSteamId)}
                className="px-3 py-2 rounded-lg border border-white/15 bg-white/8 text-sm font-medium text-white/90 shadow-sm hover:text-white hover:bg-white/12 hover:border-white/25 focus:outline-none focus:ring-2 focus:ring-scum-orange/70 disabled:opacity-70 disabled:cursor-not-allowed"
              >
                {walletSteamId && walletBalancesBusy[walletSteamId]
                  ? t('common.loading', { defaultValue: 'Loading...' })
                  : t('tools.shopDeliveries.wallet.fetchBalance', { defaultValue: 'Fetch balance' })}
              </button>
            </div>

                <div className="grid grid-cols-1 sm:grid-cols-[140px_1fr] gap-2">
              <div>
                <div className="text-xs text-white/60 mb-1">
                  {t('tools.shopDeliveries.wallet.operation', { defaultValue: 'Operation' })}
                </div>
                <select
                  value={walletOp}
                  onChange={(e) => setWalletOp(e.target.value as any)}
                  className="w-full px-3 py-2 rounded-lg bg-[#0b1220] border border-white/10 text-white text-sm focus:outline-none focus:ring-2 focus:ring-scum-orange"
                >
                  <option value="add" style={{ backgroundColor: '#0b1220', color: '#ffffff' }}>
                    {t('tools.shopDeliveries.wallet.add', { defaultValue: 'Add' })}
                  </option>
                  <option value="remove" style={{ backgroundColor: '#0b1220', color: '#ffffff' }}>
                    {t('tools.shopDeliveries.wallet.remove', { defaultValue: 'Remove' })}
                  </option>
                </select>
              </div>
              <div>
                <div className="text-xs text-white/60 mb-1">
                  {t('tools.shopDeliveries.wallet.amount', { defaultValue: 'Amount' })}
                </div>
                <input
                  value={walletAmount}
                  onChange={(e) => setWalletAmount(e.target.value)}
                  inputMode="numeric"
                  placeholder="100"
                  className="w-full px-3 py-2 rounded-lg bg-white/5 border border-white/10 text-white text-sm focus:outline-none focus:ring-2 focus:ring-scum-orange"
                />
              </div>
            </div>

            <div>
              <div className="text-xs text-white/60 mb-1">
                {t('tools.shopDeliveries.wallet.note', { defaultValue: 'Note (optional)' })}
              </div>
              <input
                value={walletNote}
                onChange={(e) => setWalletNote(e.target.value.toUpperCase())}
                className="w-full px-3 py-2 rounded-lg bg-white/5 border border-white/10 text-white text-sm uppercase focus:outline-none focus:ring-2 focus:ring-scum-orange"
              />
            </div>

            <button
              disabled={walletBusy || !walletSteamId}
              onClick={onWalletAdjust}
              className="w-full px-3 py-2 rounded-lg border border-scum-orange/60 bg-scum-orange/10 text-sm font-semibold text-scum-orange shadow-sm hover:bg-scum-orange/20 hover:border-scum-orange/80 focus:outline-none focus:ring-2 focus:ring-scum-orange/70 disabled:opacity-70 disabled:cursor-not-allowed"
            >
              {walletBusy
                ? t('common.loading', { defaultValue: 'Loading...' })
                : t('tools.shopDeliveries.wallet.apply', { defaultValue: 'Apply' })}
            </button>

                {walletSteamId && (
              <button
                type="button"
                onClick={() => navigate(`/tools/shop-deliveries/transactions/${walletSteamId}`)}
                className="w-full px-3 py-2 rounded-lg border border-white/15 bg-white/8 text-sm font-medium text-white/90 shadow-sm hover:text-white hover:bg-white/12 hover:border-white/25 focus:outline-none focus:ring-2 focus:ring-scum-orange/70"
              >
                {t('tools.shopDeliveries.wallet.statement', { defaultValue: 'Full statement' })}
              </button>
            )}

            {walletSteamId && (
              <div className="pt-2">
                <div className="text-xs uppercase text-white/40 mb-2">
                  {t('tools.shopDeliveries.wallet.recentTx', { defaultValue: 'Recent transactions' })}
                </div>
                {walletTxError && <div className="text-xs text-red-400 mb-2">{walletTxError}</div>}
                {walletTxBusy ? (
                  <div className="text-sm text-white/60">{t('common.loading', { defaultValue: 'Loading...' })}</div>
                ) : walletTxItems.length === 0 ? (
                  <div className="text-sm text-white/60">
                    {t('tools.shopDeliveries.wallet.noTx', { defaultValue: 'No transactions.' })}
                  </div>
                ) : (
                  <div className="space-y-1">
                    {walletTxItems.slice(0, 10).map((tx) => {
                      const delta = Number(tx.delta);
                      const deltaColor = delta >= 0 ? 'text-emerald-400' : 'text-red-400';
                      const ref = [tx.ref_type, tx.ref_id].filter(Boolean).join(':');
                      return (
                        <div
                          key={tx.tx_id}
                          className="rounded-lg border border-white/10 bg-white/5 px-3 py-2"
                        >
                          <div className="flex items-center justify-between gap-2">
                            <div className="text-xs text-white/60 tabular-nums">{tx.created_at}</div>
                            <div className={"text-sm font-semibold tabular-nums " + deltaColor}>{delta}</div>
                          </div>
                          <div className="text-xs text-white/80 truncate" title={tx.reason}>
                            {tx.reason}
                          </div>
                          <div className="text-[11px] text-white/50 truncate" title={ref}>
                            {ref || '—'}
                          </div>
                        </div>
                      );
                    })}
                  </div>
                )}
              </div>
                )}
              </>
            ) : (
              <>
                {playtimeError && <div className="text-sm text-red-400">{playtimeError}</div>}

                {playtimeConfig ? (
                  <div className="space-y-3">
                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                      <div className="text-xs text-white/60">
                        {t('tools.shopDeliveries.playtime.enabled', { defaultValue: 'Enabled' })}:{' '}
                        {playtimeConfig.enabled ? 'ON' : 'OFF'}
                      </div>
                      <div className="text-xs text-white/60">
                        {t('tools.shopDeliveries.playtime.maxHoursPerRun', { defaultValue: 'Max hours/run' })}:{' '}
                        {playtimeConfig.max_hours_per_run}
                      </div>
                    </div>

                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                      <div className="text-xs text-white/60">
                        {t('tools.shopDeliveries.playtime.interval', {
                          defaultValue: 'Interval (min): {{v}}',
                          v: playtimeConfig.interval_minutes,
                        })}
                      </div>
                      <div className="text-xs text-white/60">
                        {t('tools.shopDeliveries.playtime.baseline', {
                          defaultValue: 'Baseline: {{v}}',
                          v: playtimeConfig.baseline_mode,
                        })}
                      </div>
                    </div>

                    <div className="pt-3 border-t border-white/10" />
                    <div className="text-xs text-white/60">
                      {t('tools.shopDeliveries.playtimeRules.exclusiveNote', {
                        defaultValue:
                          'VIP is substitution: if a player matches any exclusive rule, non-exclusive rules (Default) do not apply.',
                      })}
                    </div>

                    <div className="grid grid-cols-1 md:grid-cols-[minmax(0,1fr)_180px_auto] gap-2 items-end">
                      <div className="min-w-0">
                        <div className="text-xs text-white/60 mb-1">
                          {t('tools.shopDeliveries.playtimeRules.pointsPerHour', { defaultValue: 'Points/hour' })}
                        </div>
                        <input
                          value={rulesQuickPoints}
                          onChange={(e) => setRulesQuickPoints(clampInt(e.target.value))}
                          inputMode="numeric"
                          className="w-full px-3 py-2 rounded-lg bg-white/5 border border-white/10 text-white text-sm focus:outline-none focus:ring-2 focus:ring-scum-orange"
                        />
                      </div>
                      <div>
                        <div className="text-xs text-white/60 mb-1">
                          {t('tools.shopDeliveries.playtimeRules.applyTo', { defaultValue: 'Apply to' })}
                        </div>
                        <select
                          value={rulesQuickKind}
                          onChange={(e) => setRulesQuickKind(e.target.value as any)}
                          className="w-full px-3 py-2 rounded-lg bg-[#0b1220] border border-white/10 text-white text-sm focus:outline-none focus:ring-2 focus:ring-scum-orange"
                        >
                          <option value="default" style={{ backgroundColor: '#0b1220', color: '#ffffff' }}>
                            {t('tools.shopDeliveries.playtimeRules.default', { defaultValue: 'Default' })}
                          </option>
                          <option value="vip" style={{ backgroundColor: '#0b1220', color: '#ffffff' }}>
                            {t('tools.shopDeliveries.playtimeRules.vip', { defaultValue: 'VIP' })}
                          </option>
                        </select>
                      </div>
                      <button
                        type="button"
                        disabled={rulesBusy || (walletTab === 'rewards' && vipEditOpen)}
                        onClick={() => void saveQuickRulePoints()}
                        className="w-full md:w-auto px-4 py-2 rounded-lg border border-scum-orange/60 bg-scum-orange/10 text-sm font-semibold text-scum-orange shadow-sm hover:bg-scum-orange/20 hover:border-scum-orange/80 focus:outline-none focus:ring-2 focus:ring-scum-orange/70 disabled:opacity-70 disabled:cursor-not-allowed"
                      >
                        {rulesBusy ? t('common.saving', { defaultValue: 'Saving...' }) : t('common.save', { defaultValue: 'Save' })}
                      </button>
                    </div>

                    {rulesError && <div className="text-xs text-red-400">{rulesError}</div>}

                    <div className="space-y-2">
                      {(() => {
                        const def = findDefaultRule(rulesItems);
                        const vip = findVipRule(rulesItems);
                        const entries = [
                          def
                            ? { kind: 'default' as const, rule: def }
                            : { kind: 'default' as const, rule: null as any },
                          vip ? { kind: 'vip' as const, rule: vip } : { kind: 'vip' as const, rule: null as any },
                        ];
                        return entries.map(({ kind, rule }) => {
                          const title =
                            kind === 'default'
                              ? t('tools.shopDeliveries.playtimeRules.default', { defaultValue: 'Default' })
                              : t('tools.shopDeliveries.playtimeRules.vip', { defaultValue: 'VIP' });
                          const subtitle =
                            kind === 'default'
                              ? t('tools.shopDeliveries.playtimeRules.defaultHint', {
                                  defaultValue: 'Applies to registered players (Padrão list, non-exclusive).',
                                })
                              : t('tools.shopDeliveries.playtimeRules.vipHint', {
                                  defaultValue: 'Applies only to listed players (exclusive substitution).',
                                });
                          const enabled = rule ? Boolean(rule.enabled) : false;
                          const points = rule ? rule.points_per_hour : null;
                          const canEditVip = kind === 'vip';

                          return (
                            <div
                              key={kind}
                              className={
                                "rounded-lg border border-white/10 bg-white/5 px-3 py-2" +
                                (canEditVip && rule ? " cursor-pointer hover:bg-white/7" : "")
                              }
                              onClick={() => {
                                if (!canEditVip || !rule) return;
                                const next = !vipEditOpen;
                                setVipEditOpen(next);
                                if (next) void loadVipTargets(rule.rule_id);
                              }}
                            >
                              <div className="flex items-start justify-between gap-2">
                                <div className="min-w-0">
                                  <div className="text-sm font-semibold text-white/90">{title}</div>
                                  <div className="text-xs text-white/50 truncate">{subtitle}</div>
                                </div>
                                <div className="flex items-center gap-2">
                                  <label className="flex items-center gap-2 text-xs text-white/60">
                                    <span>{t('tools.shopDeliveries.playtimeRules.enabled', { defaultValue: 'Enabled' })}</span>
                                    <input
                                      type="checkbox"
                                      disabled={rulesBusy || !rule}
                                      checked={enabled}
                                      onChange={(e) => rule && void toggleRuleEnabled(rule, e.target.checked)}
                                      onClick={(e) => e.stopPropagation()}
                                      className="h-4 w-4"
                                    />
                                  </label>
                                </div>
                              </div>

                              <div className="mt-2 flex items-center justify-between gap-2">
                                <div className="text-xs text-white/60">
                                  {t('tools.shopDeliveries.playtimeRules.pointsLabel', {
                                    defaultValue: 'Points/hour: {{v}}',
                                    v: points == null ? '—' : points,
                                  })}
                                </div>
                                <div className="text-[11px] text-white/40">
                                  {rule
                                    ? `${rule.audience_type}${rule.exclusive ? ' | exclusive' : ''}`
                                    : t('tools.shopDeliveries.playtimeRules.missing', { defaultValue: 'Not created yet.' })}
                                </div>
                              </div>

                              {kind === 'vip' && vipEditOpen && rule && (
                                <div className="mt-3 border-t border-white/10 pt-3 space-y-2">
                                  <div className="flex items-center justify-between gap-2">
                                    <div className="text-xs uppercase text-white/40">
                                      {t('tools.shopDeliveries.playtimeRules.vipTargets', { defaultValue: 'VIPs (targets)' })}
                                    </div>
                                    <div className="text-xs text-white/50 tabular-nums">
                                      {t('tools.shopDeliveries.playtimeRules.vipCount', {
                                        defaultValue: 'Count: {{count}}',
                                        count: vipTargets.length,
                                      })}
                                    </div>
                                  </div>

                                  <div className="text-xs text-white/60">
                                    {t('tools.shopDeliveries.playtimeRules.vipSelectHint', {
                                      defaultValue: 'Select VIPs using the players list on the right, then click Save VIPs.',
                                    })}
                                  </div>

                                  {vipTargetsError && <div className="text-xs text-red-400">{vipTargetsError}</div>}

                                  <button
                                    type="button"
                                    disabled={vipTargetsBusy}
                                    onClick={() => void saveVipTargetsFromSelection(rule.rule_id)}
                                    className="w-full px-3 py-2 rounded-lg border border-scum-orange/60 bg-scum-orange/10 text-sm font-semibold text-scum-orange shadow-sm hover:bg-scum-orange/20 hover:border-scum-orange/80 focus:outline-none focus:ring-2 focus:ring-scum-orange/70 disabled:opacity-70 disabled:cursor-not-allowed"
                                  >
                                    {vipTargetsBusy
                                      ? t('common.saving', { defaultValue: 'Saving...' })
                                      : t('tools.shopDeliveries.playtimeRules.saveVips', { defaultValue: 'Save VIPs' })}
                                  </button>

                                  {vipSaved && !vipTargetsBusy && !vipTargetsError && (
                                    <div className="text-xs text-emerald-400">
                                      {t('tools.shopDeliveries.playtimeRules.savedVips', { defaultValue: 'VIPs saved.' })}
                                    </div>
                                  )}
                                </div>
                              )}
                            </div>
                          );
                        });
                      })()}
                    </div>

                  </div>
                ) : (
                  <div className="text-sm text-white/60">
                    {playtimeBusy
                      ? t('tools.shopDeliveries.playtime.loading', { defaultValue: 'Loading configuration...' })
                      : t('tools.shopDeliveries.playtime.hint', {
                          defaultValue: 'Configuration will load automatically when you open this tab.',
                        })}
                  </div>
                )}
              </>
            )}
          </div>

          <div className="card p-4 space-y-3">
            <div className="flex items-center justify-between gap-2">
              <div className="text-sm font-semibold text-white">
                {t('tools.shopDeliveries.wallet.playersTitle', { defaultValue: 'Players' })}
              </div>
              <div className="flex items-center gap-2">
                {vipSelectMode && (
                  <label className="flex items-center gap-2 text-xs text-white/70 select-none">
                    <input
                      type="checkbox"
                      checked={vipOnly}
                      onChange={(e) => setVipOnly(e.target.checked)}
                      className="h-4 w-4"
                    />
                    <span>
                      {t('tools.shopDeliveries.playtimeRules.vipOnly', { defaultValue: 'VIPs only' })}
                    </span>
                  </label>
                )}
                <div className="text-xs text-white/50">
                  {rewardsMailboxMode ? (
                    mailboxBusy
                      ? t('common.loading', { defaultValue: 'Loading...' })
                      : t('tools.shopDeliveries.playtimeRules.registeredCount', {
                          defaultValue: 'Registered: {{count}}',
                          count: mailboxTotal,
                        })
                  ) : walletPlayersBusy
                    ? t('common.loading', { defaultValue: 'Loading...' })
                    : t('tools.shopDeliveries.wallet.playersCount', {
                        defaultValue: 'Players: {{count}}',
                        count: walletTotal,
                      })}
                </div>
                {walletTab === 'wallet' && (
                  <button
                    type="button"
                    disabled={walletPlayersBusy || walletBulkBusy || walletPlayers.length === 0}
                    onClick={() => {
                      void fetchAllWalletBalances(walletPlayers);
                    }}
                    className="px-2 py-1 rounded-lg border border-white/15 bg-white/8 text-xs font-medium text-white/90 hover:bg-white/12 hover:border-white/25 disabled:opacity-70 disabled:cursor-not-allowed"
                    title={t('tools.shopDeliveries.wallet.fetchAllHelp', { defaultValue: 'Fetch balances for all loaded players.' })}
                  >
                    {walletBulkBusy
                      ? t('tools.shopDeliveries.wallet.fetchAllProgress', {
                          defaultValue: 'Balances {{done}}/{{total}}',
                          done: walletBulkDone,
                          total: walletBulkTotal,
                        })
                      : t('tools.shopDeliveries.wallet.fetchAll', { defaultValue: 'Fetch balances' })}
                  </button>
                )}
              </div>
            </div>

            <input
              value={walletPlayerQuery}
              onChange={(e) => setWalletPlayerQuery(e.target.value)}
              placeholder={t('tools.shopDeliveries.wallet.playersSearch', { defaultValue: 'Search players (name or Steam ID)...' })}
              className="w-full px-3 py-2 rounded-lg bg-white/5 border border-white/10 text-white text-sm focus:outline-none focus:ring-2 focus:ring-scum-orange"
            />

            <div className="rounded-lg border border-white/10 overflow-auto">
              <div className={rewardsMailboxMode ? (vipSelectMode ? 'min-w-[940px]' : 'min-w-[900px]') : 'min-w-[720px]'}>
                <div
                  className={
                    rewardsMailboxMode
                      ? vipSelectMode
                        ? 'grid grid-cols-[40px_1fr_240px_120px_120px] gap-2 px-3 py-2 text-xs uppercase text-white/40 border-b border-white/10'
                        : 'grid grid-cols-[1fr_240px_120px_120px] gap-2 px-3 py-2 text-xs uppercase text-white/40 border-b border-white/10'
                      : 'grid grid-cols-[1fr_240px_120px] gap-2 px-3 py-2 text-xs uppercase text-white/40 border-b border-white/10'
                  }
                >
                  {rewardsMailboxMode ? (
                    <>
                      {vipSelectMode && (
                        <div className="text-center">{t('tools.shopDeliveries.playtimeRules.vip', { defaultValue: 'VIP' })}</div>
                      )}
                      {renderSortableHeader(t('tools.shopDeliveries.wallet.table.name', { defaultValue: 'Name' }), 'player_name', true)}
                      {renderSortableHeader(t('tools.shopDeliveries.wallet.table.steamId', { defaultValue: 'Steam ID' }), 'steam_id', true)}
                      {renderSortableHeader(t('tools.shopDeliveries.playtimeRules.registeredColumn', { defaultValue: 'Registered' }), 'discord_linked_at', true, 'justify-end')}
                      {renderSortableHeader(t('tools.shopDeliveries.wallet.table.balance', { defaultValue: 'Balance' }), 'balance', true, 'justify-end')}
                    </>
                  ) : (
                    <>
                      {renderSortableHeader(t('tools.shopDeliveries.wallet.table.name', { defaultValue: 'Name' }), 'player_name', false)}
                      {renderSortableHeader(t('tools.shopDeliveries.wallet.table.steamId', { defaultValue: 'Steam ID' }), 'steam_id', false)}
                      {renderSortableHeader(t('tools.shopDeliveries.wallet.table.balance', { defaultValue: 'Balance' }), 'balance', false, 'justify-end')}
                    </>
                  )}
                </div>

                <div className="max-h-[560px] overflow-auto">
                  {rewardsMailboxMode
                    ? mailboxFiltered.map((it) => {
                        const checked = Boolean(vipSelected[it.steam_id]);
                        const balBusy = Boolean(walletBalancesBusy[it.steam_id]);
                        const bal = walletBalances[it.steam_id] !== undefined ? walletBalances[it.steam_id] : it.balance;
                        return (
                          <button
                            key={it.steam_id}
                            type="button"
                            onClick={() => {
                              if (!vipSelectMode) return;
                              setVipSelected((prev) => ({ ...prev, [it.steam_id]: !Boolean(prev[it.steam_id]) }));
                            }}
                            className={
                              'w-full grid gap-2 px-3 py-2 text-left border-b border-white/5 last:border-b-0 hover:bg-white/5 ' +
                              (vipSelectMode
                                ? 'grid-cols-[40px_1fr_240px_120px_120px]'
                                : 'grid-cols-[1fr_240px_120px_120px]')
                            }
                          >
                            {vipSelectMode && (
                              <div className="flex items-center justify-center">
                                <input
                                  type="checkbox"
                                  checked={checked}
                                  onChange={() =>
                                    setVipSelected((prev) => ({ ...prev, [it.steam_id]: !Boolean(prev[it.steam_id]) }))
                                  }
                                  onClick={(e) => e.stopPropagation()}
                                  className="h-4 w-4"
                                />
                              </div>
                            )}
                            <div className="text-white/90 text-sm font-medium truncate">{it.player_name || 'Sem nome'}</div>
                            <div className="text-white/60 text-xs sm:text-sm truncate">{it.steam_id}</div>
                            <div className="text-white/60 text-xs tabular-nums text-right">
                              {it.discord_linked_at
                                ? new Date(it.discord_linked_at).toLocaleDateString()
                                : '—'}
                            </div>
                            <div className="text-white/80 text-sm tabular-nums text-right">
                              {balBusy
                                ? t('tools.shopDeliveries.wallet.balanceLoading', { defaultValue: 'Loading...' })
                                : bal == null
                                  ? t('tools.shopDeliveries.wallet.balanceUnknown', { defaultValue: '—' })
                                  : bal}
                            </div>
                          </button>
                        );
                      })
                    : filteredPlayersForView.map((p) => {
                    const active = walletSteamId && p.steam_id === walletSteamId;
                    const balBusy = Boolean(walletBalancesBusy[p.steam_id]);
                    const bal = walletBalances[p.steam_id] !== undefined ? walletBalances[p.steam_id] : p.balance;

                    const checked = Boolean(vipSelected[p.steam_id]);

                    return (
                      <button
                        key={p.steam_id}
                        type="button"
                        onClick={() => {
                          if (vipSelectMode) {
                            setVipSelected((prev) => ({ ...prev, [p.steam_id]: !Boolean(prev[p.steam_id]) }));
                            return;
                          }
                          setWalletSteamId(p.steam_id);
                          setWalletBalance(null);
                          setWalletBalanceSteamId(null);
                          void fetchWalletBalanceFor(p.steam_id);
                        }}
                        className={
                          'w-full grid ' +
                          'grid-cols-[1fr_240px_120px]' +
                          ' gap-2 px-3 py-2 text-left border-b border-white/5 last:border-b-0 hover:bg-white/5 ' +
                          (active ? 'bg-white/5' : '')
                        }
                      >
                        <div className="text-white/90 text-sm font-medium truncate">{p.player_name || 'Sem nome'}</div>
                        <div className="text-white/60 text-xs sm:text-sm truncate">{p.steam_id}</div>
                        <div className="text-white/80 text-sm tabular-nums text-right">
                          {balBusy
                            ? t('tools.shopDeliveries.wallet.balanceLoading', { defaultValue: 'Loading...' })
                            : bal == null
                              ? t('tools.shopDeliveries.wallet.balanceUnknown', { defaultValue: '—' })
                              : bal}
                        </div>
                      </button>
                    );
                  })}

                  {rewardsMailboxMode ? (
                    <>
                      {mailboxError && <div className="p-3 text-sm text-red-400">{mailboxError}</div>}
                      {!mailboxBusy && !mailboxError && mailboxFiltered.length === 0 && (
                        <div className="p-3 text-sm text-white/60">
                          {vipOnly
                            ? t('tools.shopDeliveries.playtimeRules.vipOnlyEmpty', { defaultValue: 'No VIPs selected.' })
                            : t('tools.shopDeliveries.playtimeRules.registeredEmpty', { defaultValue: 'No registered players.' })}
                        </div>
                      )}
                    </>
                  ) : (
                    <>
                      {!walletPlayersBusy && filteredPlayers.length === 0 && (
                        <div className="p-3 text-sm text-white/60">
                          {t('tools.shopDeliveries.wallet.playersEmpty', { defaultValue: 'No players.' })}
                        </div>
                      )}

                      {!walletPlayersBusy && filteredPlayers.length > 0 && filteredPlayersForView.length === 0 && (
                        <div className="p-3 text-sm text-white/60">
                          {t('tools.shopDeliveries.playtimeRules.vipOnlyEmpty', { defaultValue: 'No VIPs selected.' })}
                        </div>
                      )}
                    </>
                  )}
                </div>
              </div>
            </div>

            {rewardsMailboxMode ? (
              mailboxTotal > 0 && (
                <div className="flex items-center justify-between gap-2 pt-2">
                  <div className="text-xs text-white/50">
                    {t('tools.shopDeliveries.playtimeRules.pageInfo', {
                      defaultValue: 'Page {{page}} / {{pages}}',
                      page: mailboxPage,
                      pages: mailboxTotalPages,
                    })}
                  </div>

                  <div className="flex items-center gap-1">
                    <button
                      type="button"
                      disabled={mailboxBusy || mailboxPage <= 1}
                      onClick={() => void loadMailboxPage(mailboxPage - 1)}
                      className="px-2 py-1 rounded-lg border border-white/15 bg-white/8 text-xs font-medium text-white/90 hover:bg-white/12 hover:border-white/25 disabled:opacity-60 disabled:cursor-not-allowed"
                    >
                      {t('common.prev', { defaultValue: 'Prev' })}
                    </button>

                    {mailboxPageButtons.map((p) => (
                      <button
                        key={p}
                        type="button"
                        disabled={mailboxBusy}
                        onClick={() => void loadMailboxPage(p)}
                        className={
                          'px-2 py-1 rounded-lg border text-xs font-medium ' +
                          (p === mailboxPage
                            ? 'border-scum-orange/70 bg-scum-orange/15 text-scum-orange'
                            : 'border-white/15 bg-white/8 text-white/90 hover:bg-white/12 hover:border-white/25') +
                          ' disabled:opacity-60 disabled:cursor-not-allowed'
                        }
                      >
                        {p}
                      </button>
                    ))}

                    <button
                      type="button"
                      disabled={mailboxBusy || mailboxPage >= mailboxTotalPages}
                      onClick={() => void loadMailboxPage(mailboxPage + 1)}
                      className="px-2 py-1 rounded-lg border border-white/15 bg-white/8 text-xs font-medium text-white/90 hover:bg-white/12 hover:border-white/25 disabled:opacity-60 disabled:cursor-not-allowed"
                    >
                      {t('common.next', { defaultValue: 'Next' })}
                    </button>
                  </div>
                </div>
              )
            ) : (
              walletTotal > 0 && (
                <div className="flex items-center justify-between gap-2 pt-2">
                  <div className="text-xs text-white/50">
                    {t('tools.shopDeliveries.playtimeRules.pageInfo', {
                      defaultValue: 'Page {{page}} / {{pages}}',
                      page: walletPage,
                      pages: walletTotalPages,
                    })}
                  </div>

                  <div className="flex items-center gap-1">
                    <button
                      type="button"
                      disabled={walletPlayersBusy || walletPage <= 1}
                      onClick={() => void loadWalletPage(walletPage - 1)}
                      className="px-2 py-1 rounded-lg border border-white/15 bg-white/8 text-xs font-medium text-white/90 hover:bg-white/12 hover:border-white/25 disabled:opacity-60 disabled:cursor-not-allowed"
                    >
                      {t('common.prev', { defaultValue: 'Prev' })}
                    </button>

                    {walletPageButtons.map((p) => (
                      <button
                        key={p}
                        type="button"
                        disabled={walletPlayersBusy}
                        onClick={() => void loadWalletPage(p)}
                        className={
                          'px-2 py-1 rounded-lg border text-xs font-medium ' +
                          (p === walletPage
                            ? 'border-scum-orange/70 bg-scum-orange/15 text-scum-orange'
                            : 'border-white/15 bg-white/8 text-white/90 hover:bg-white/12 hover:border-white/25') +
                          ' disabled:opacity-60 disabled:cursor-not-allowed'
                        }
                      >
                        {p}
                      </button>
                    ))}

                    <button
                      type="button"
                      disabled={walletPlayersBusy || walletPage >= walletTotalPages}
                      onClick={() => void loadWalletPage(walletPage + 1)}
                      className="px-2 py-1 rounded-lg border border-white/15 bg-white/8 text-xs font-medium text-white/90 hover:bg-white/12 hover:border-white/25 disabled:opacity-60 disabled:cursor-not-allowed"
                    >
                      {t('common.next', { defaultValue: 'Next' })}
                    </button>
                  </div>
                </div>
              )
            )}
          </div>
        </div>
      )}


    </ModuleToolPage>
  );
}
