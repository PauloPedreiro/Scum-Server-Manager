import { useEffect, useMemo, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { ModuleToolPage } from '@/components/tools/ModuleToolPage';
import SearchBar from '@/components/ui/SearchBar';
import Swal from 'sweetalert2';
import {
  getPlayerAttributes,
  patchPlayerAttributes,
  type AttributesValues,
} from '@/services/attributes';
import { getAllPlayers, getPlayersOnlineList, type AllPlayer } from '@/services/server';

type AttrKey = keyof AttributesValues;

const RANGES: Record<AttrKey, { min: number; max: number }> = {
  strength: { min: 1.0, max: 8.0 },
  constitution: { min: 1.0, max: 5.0 },
  dexterity: { min: 1.0, max: 5.0 },
  intelligence: { min: 1.0, max: 5.0 },
};

function clamp(n: number, min: number, max: number) {
  if (Number.isNaN(n)) return min;
  return Math.min(max, Math.max(min, n));
}

function round1(n: number) {
  return Math.round(n * 10) / 10;
}

function normalizeAttributes(a: AttributesValues): AttributesValues {
  return {
    strength: round1(a.strength),
    constitution: round1(a.constitution),
    dexterity: round1(a.dexterity),
    intelligence: round1(a.intelligence),
  };
}

function isSameAttributes(a?: AttributesValues | null, b?: AttributesValues | null) {
  if (!a || !b) return false;
  const keys: AttrKey[] = ['strength', 'constitution', 'dexterity', 'intelligence'];
  return keys.every((k) => Math.abs(a[k] - b[k]) < 0.0001);
}

function validate(attrs: AttributesValues) {
  const keys: AttrKey[] = ['strength', 'constitution', 'dexterity', 'intelligence'];
  const errors: Partial<Record<AttrKey, string>> = {};
  for (const k of keys) {
    const { min, max } = RANGES[k];
    const v = attrs[k];
    if (Number.isNaN(v)) {
      errors[k] = 'Invalid number';
      continue;
    }
    if (v < min || v > max) {
      errors[k] = `Must be between ${min} and ${max}`;
    }
  }
  return errors;
}

export default function ToolsAttributes() {
  const { t } = useTranslation();

  const [query, setQuery] = useState('');
  const [loadingPrisoners, setLoadingPrisoners] = useState(false);
  const [players, setPlayers] = useState<AllPlayer[]>([]);
  const [selected, setSelected] = useState<AllPlayer | null>(null);

  const [loadingPlayer, setLoadingPlayer] = useState(false);
  const [playerError, setPlayerError] = useState<string | null>(null);
  const [playerInfo, setPlayerInfo] = useState<string | null>(null);

  const [original, setOriginal] = useState<AttributesValues | null>(null);
  const [draft, setDraft] = useState<AttributesValues | null>(null);
  const [saving, setSaving] = useState(false);

  const pending = useMemo(() => !isSameAttributes(original, draft), [original, draft]);
  const errors = useMemo(() => (draft ? validate(draft) : {}), [draft]);
  const hasErrors = useMemo(() => Object.keys(errors).length > 0, [errors]);

  const filteredPlayers = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (!q) return players;
    return players.filter((p) => {
      const name = String(p.player_name || '').toLowerCase();
      const steam = String(p.steam_id || '');
      const id = String(p.player_id || '');
      return name.includes(q) || steam.includes(q) || id.includes(q);
    });
  }, [players, query]);

  useEffect(() => {
    const run = async () => {
      setLoadingPrisoners(true);
      try {
        const res = await getAllPlayers(null, 0);
        if (res.success && res.data?.players) {
          setPlayers(res.data.players);
        } else {
          setPlayers([]);
        }
      } catch {
        setPlayers([]);
      } finally {
        setLoadingPrisoners(false);
      }
    };

    void run();
  }, []);

  const loadPlayer = async (p: AllPlayer) => {
    setSelected(p);
    setPlayerError(null);
    setPlayerInfo(null);
    setLoadingPlayer(true);
    setOriginal(null);
    setDraft(null);
    try {
      const res = await getPlayerAttributes(p.steam_id);
      if (res.success && res.data?.attributes) {
        const normalized = normalizeAttributes(res.data.attributes);
        setOriginal(normalized);
        setDraft(normalized);
      } else {
        const raw = String(res.error || '').toLowerCase();
        if (raw.includes('not found') || raw.includes('não encontrado') || raw.includes('nao encontrado') || raw.includes('404')) {
          setPlayerInfo(
            t('tools.attributes.noAttributesYet', {
              defaultValue:
                'Este jogador ainda não tem atributos disponíveis (provavelmente nunca logou no servidor).',
            })
          );
        } else {
          setPlayerError(res.error || 'Failed to load player attributes');
        }
      }
    } catch (e: any) {
      const status = e?.response?.status;
      if (status === 404) {
        setPlayerInfo(
          t('tools.attributes.noAttributesYet', {
            defaultValue:
              'Este jogador ainda não tem atributos disponíveis (provavelmente nunca logou no servidor).',
          })
        );
      } else {
        setPlayerError(e?.response?.data?.error || e?.message || 'Failed to load player attributes');
      }
    } finally {
      setLoadingPlayer(false);
    }
  };

  const setAttr = (key: AttrKey, raw: string) => {
    if (!draft) return;
    const parsed = raw === '' ? Number.NaN : Number(raw);
    setDraft({ ...draft, [key]: parsed });
  };

  const clampAttr = (key: AttrKey) => {
    if (!draft) return;
    const { min, max } = RANGES[key];
    const v = round1(clamp(draft[key], min, max));
    setDraft({ ...draft, [key]: v });
  };

  const onRevert = () => {
    if (!original) return;
    setDraft(original);
  };

  const onSave = async () => {
    if (!selected || !draft || !original) return;
    if (hasErrors) return;
    setSaving(true);
    try {
      try {
        const online = await getPlayersOnlineList();
        const onlinePlayers = online?.data?.players;
        const isOnline =
          Array.isArray(onlinePlayers) &&
          onlinePlayers.some((p: any) =>
            String(p?.steam_id || p?.steamId || p?.steamID || p?.id || '').includes(String(selected.steam_id))
          );
        if (isOnline) {
          await Swal.fire({
            icon: 'warning',
            title: t('tools.attributes.playerOnlineTitle', { defaultValue: 'Player online' }),
            text: t('tools.attributes.playerOnlineText', {
              defaultValue:
                'Player is online. To update attributes while the server is running, the player must be offline.',
            }),
            confirmButtonColor: '#f97316',
          });
          return;
        }
      } catch {
        // If pre-check fails, continue and rely on backend 409.
      }

      const payload = normalizeAttributes(draft);
      const res = await patchPlayerAttributes(selected.steam_id, payload);
      if (res.success && res.data?.after) {
        const normalized = normalizeAttributes(res.data.after);
        setOriginal(normalized);
        setDraft(normalized);
        await Swal.fire({
          icon: 'success',
          title: t('common.success', { defaultValue: 'Success' }),
          text: res.message || t('tools.attributes.saveSuccess', { defaultValue: 'Attributes updated successfully.' }),
          confirmButtonColor: '#f97316',
        });
      } else {
        await Swal.fire({
          icon: 'error',
          title: t('common.error', { defaultValue: 'Error' }),
          text: res.error || t('tools.attributes.saveError', { defaultValue: 'Failed to update attributes.' }),
          confirmButtonColor: '#f97316',
        });
      }
    } catch (e: any) {
      const status = e?.response?.status;
      const msg = e?.response?.data?.error || e?.message || 'Failed to update attributes';
      if (status === 409) {
        await Swal.fire({
          icon: 'warning',
          title: t('tools.attributes.playerOnlineTitle', { defaultValue: 'Player online' }),
          text:
            msg ||
            t('tools.attributes.playerOnlineText', {
              defaultValue: 'Player is online. To update attributes while the server is running, the player must be offline.',
            }),
          confirmButtonColor: '#f97316',
        });
      } else if (status === 403) {
        await Swal.fire({
          icon: 'error',
          title: t('errors.unauthorized.title', { defaultValue: 'Unauthorized' }),
          text: msg,
          confirmButtonColor: '#f97316',
        });
      } else {
        await Swal.fire({
          icon: 'error',
          title: t('common.error', { defaultValue: 'Error' }),
          text: msg,
          confirmButtonColor: '#f97316',
        });
      }
    } finally {
      setSaving(false);
    }
  };

  return (
    <ModuleToolPage
      title={t('tools.attributes.title', { defaultValue: 'Attributes' })}
      subtitle={t('tools.attributes.subtitle', { defaultValue: 'Edit player attributes (Strength/Constitution/Dexterity/Intelligence).' })}
    >
      <div className="grid grid-cols-1 lg:grid-cols-[360px_1fr] gap-4">
        <div className="space-y-3">
          <div className="card p-4 space-y-3">
            <SearchBar
              value={query}
              onChange={setQuery}
              placeholder={t('tools.attributes.searchPlayers', { defaultValue: 'Search player (name, steam id, prisoner id)...' })}
            />
            <div className="text-xs text-white/50">
              {loadingPrisoners
                ? t('common.loading', { defaultValue: 'Loading...' })
                : t('tools.attributes.resultsCount', {
                    defaultValue: 'Results: {{count}}',
                    count: filteredPlayers.length,
                  })}
            </div>
          </div>

          <div className="card p-2 max-h-[60vh] overflow-auto">
            {filteredPlayers.length === 0 ? (
              <div className="p-3 text-sm text-white/60">
                {t('tools.attributes.noPlayers', { defaultValue: 'No players found.' })}
              </div>
            ) : (
              <div className="divide-y divide-white/10">
                {filteredPlayers.map((p) => {
                  const active = selected?.steam_id === p.steam_id;
                  return (
                    <div
                      key={p.steam_id}
                      role="button"
                      tabIndex={0}
                      onClick={() => loadPlayer(p)}
                      onKeyDown={(e) => {
                        if (e.key === 'Enter' || e.key === ' ') {
                          e.preventDefault();
                          loadPlayer(p);
                        }
                      }}
                      className={`p-3 rounded-lg cursor-pointer transition-colors ${
                        active ? 'bg-scum-panel/40' : 'hover:bg-white/5'
                      }`}
                    >
                      <div className="flex items-center justify-between gap-2">
                        <div className="min-w-0">
                          <div className="font-medium text-white truncate">{p.player_name}</div>
                          <div className="text-xs text-white/50 truncate">{p.steam_id}</div>
                        </div>
                        <div className="text-xs text-white/40">#{p.player_id}</div>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        </div>

        <div className="space-y-3">
          <div className="card p-4">
            <div className="flex items-start gap-3">
              <div className="min-w-0">
                <div className="text-sm text-white/60">{t('tools.attributes.selected', { defaultValue: 'Selected player' })}</div>
                <div className="text-lg font-semibold truncate">
                  {selected ? selected.player_name : t('tools.attributes.noneSelected', { defaultValue: 'None' })}
                </div>
                {selected && <div className="text-xs text-white/50 truncate">{selected.steam_id}</div>}
              </div>
              <div className="ml-auto flex items-center gap-2">
                <button
                  onClick={onRevert}
                  disabled={!pending || saving || loadingPlayer}
                  className="px-3 py-2 rounded-lg border border-white/15 bg-white/8 text-sm font-medium text-white/90 shadow-sm hover:text-white hover:bg-white/12 hover:border-white/25 focus:outline-none focus:ring-2 focus:ring-scum-orange/70 disabled:opacity-70 disabled:cursor-not-allowed"
                >
                  {t('common.revert', { defaultValue: 'Revert' })}
                </button>
                <button
                  onClick={onSave}
                  disabled={!pending || hasErrors || saving || loadingPlayer}
                  className="px-3 py-2 rounded-lg border border-scum-orange/60 bg-scum-orange/10 text-sm font-semibold text-scum-orange shadow-sm hover:bg-scum-orange/20 hover:border-scum-orange/80 focus:outline-none focus:ring-2 focus:ring-scum-orange/70 disabled:opacity-70 disabled:cursor-not-allowed"
                >
                  {saving ? t('common.saving', { defaultValue: 'Saving...' }) : t('common.save', { defaultValue: 'Save' })}
                </button>
              </div>
            </div>

            {pending && (
              <div className="mt-3 text-xs text-white/60">
                {t('tools.attributes.pending', { defaultValue: 'You have unsaved changes.' })}
              </div>
            )}

            {hasErrors && (
              <div className="mt-3 text-xs text-red-400">
                {t('tools.attributes.validationError', { defaultValue: 'Please fix validation errors before saving.' })}
              </div>
            )}
          </div>

          <div className="card p-4">
            {loadingPlayer && (
              <div className="text-sm text-white/60">{t('common.loading', { defaultValue: 'Loading...' })}</div>
            )}

            {!loadingPlayer && playerError && <div className="text-sm text-red-400">{playerError}</div>}

            {!loadingPlayer && !playerError && playerInfo && <div className="text-sm text-amber-300">{playerInfo}</div>}

            {!loadingPlayer && !playerError && !playerInfo && !draft && (
              <div className="text-sm text-white/60">
                {t('tools.attributes.selectPrompt', { defaultValue: 'Select a player to load attributes.' })}
              </div>
            )}

            {!loadingPlayer && !playerError && draft && (
              <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
                {(
                  [
                    ['strength', t('tools.attributes.fields.strength', { defaultValue: 'Strength' })],
                    ['constitution', t('tools.attributes.fields.constitution', { defaultValue: 'Constitution' })],
                    ['dexterity', t('tools.attributes.fields.dexterity', { defaultValue: 'Dexterity' })],
                    ['intelligence', t('tools.attributes.fields.intelligence', { defaultValue: 'Intelligence' })],
                  ] as Array<[AttrKey, string]>
                ).map(([key, label]) => {
                  const range = RANGES[key];
                  const err = (errors as any)[key] as string | undefined;
                  return (
                    <div key={key} className="flex flex-col h-full gap-2">
                      <div className="grid grid-cols-[1fr_auto] items-center gap-3 min-h-6">
                        <div className="text-sm font-medium text-white truncate">{label}</div>
                        <div className="text-xs text-white/50 text-right whitespace-nowrap">
                          {range.min} - {range.max}
                        </div>
                      </div>

                      <div className="grid grid-cols-[1fr_auto] items-center gap-3">
                        <input
                          type="number"
                          step={0.1}
                          min={range.min}
                          max={range.max}
                          value={Number.isNaN(draft[key]) ? '' : draft[key]}
                          onChange={(e) => setAttr(key, e.target.value)}
                          onBlur={() => clampAttr(key)}
                          className={`w-16 sm:w-20 h-8 px-2 py-1 rounded-lg bg-white/5 border text-white text-sm text-right tabular-nums leading-none focus:outline-none focus:ring-2 focus:ring-scum-orange ${
                            err ? 'border-red-500/60' : 'border-white/10'
                          }`}
                        />
                        <div />
                      </div>

                      {err && <div className="text-xs text-red-400">{err}</div>}

                      {original && (
                        <div className="mt-auto text-xs text-white/50">
                          {t('tools.attributes.original', { defaultValue: 'Original:' })}{' '}
                          {original[key].toFixed(1)}
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        </div>
      </div>
    </ModuleToolPage>
  );
}
