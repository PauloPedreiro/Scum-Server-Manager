import { useMemo, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { ChevronDown, Loader2 } from 'lucide-react';

export interface MapFilterOption {
  id: string;
  label: string;
  description?: string;
  active: boolean;
  disabled?: boolean;
  loading?: boolean;
  count?: number;
}

interface MapFiltersPanelProps {
  title?: string;
  options: MapFilterOption[];
  onToggle: (id: string) => void;
}

export function MapFiltersPanel({ title, options, onToggle }: MapFiltersPanelProps) {
  const { t } = useTranslation();
  const [search, setSearch] = useState('');

  const safeTitle = title ?? t('map.filters.title', 'Filtros');

  const filteredOptions = useMemo(() => {
    const query = search.trim().toLowerCase();
    if (!query) return options;

    return options.filter((option) => option.label.toLowerCase().includes(query));
  }, [options, search]);

  return (
    <aside className="card p-3 sm:p-4 bg-black/40 border border-white/10 rounded-xl text-white flex flex-col gap-3">
      <div>
        <h2 className="text-base font-semibold uppercase tracking-wide text-white/80">
          {safeTitle}
        </h2>
        <input
          type="text"
          value={search}
          onChange={(event) => setSearch(event.target.value)}
          placeholder={t('map.filters.searchPlaceholder', 'Buscar filtro...')}
          className="mt-3 w-full rounded-lg bg-black/40 border border-white/10 px-3 py-2 text-sm text-white placeholder:text-white/40 focus:outline-none focus:ring-2 focus:ring-scum-accent/60"
        />
      </div>

      <div className="flex flex-col gap-2 overflow-y-auto pr-1">
        {filteredOptions.map((option) => {
          const { id, label, description, active, disabled, loading, count } = option;
          return (
            <button
              key={id}
              type="button"
              onClick={() => !disabled && onToggle(id)}
              className={`group relative flex items-center gap-3 rounded-lg border px-3 py-2 text-left transition-colors ${
                active
                  ? 'border-scum-accent/40 bg-scum-accent/15'
                  : 'border-white/10 bg-black/30 hover:border-scum-accent/30 hover:bg-scum-accent/10'
              } ${disabled ? 'opacity-40 cursor-not-allowed' : 'cursor-pointer'}`}
            >
              <input
                type="checkbox"
                checked={active}
                readOnly
                disabled={disabled}
                className="h-4 w-4 rounded border border-white/30 bg-black/60 accent-scum-accent/80"
              />
              <div className="flex flex-1 flex-col">
                <span className="text-sm font-medium text-white">{label}</span>
                {description ? (
                  <span className="text-xs text-white/50">{description}</span>
                ) : null}
                {typeof count === 'number' ? (
                  <span className="mt-1 inline-flex w-fit items-center gap-1 rounded-full bg-white/10 px-2 py-0.5 text-[11px] font-semibold text-white/80">
                    {t('map.filters.itemsCount', { count })}
                  </span>
                ) : null}
              </div>
              {loading ? (
                <Loader2 className="h-4 w-4 animate-spin text-scum-accent" />
              ) : (
                <ChevronDown
                  className={`h-4 w-4 transition-transform ${
                    active ? 'rotate-180 text-scum-accent' : 'text-white/40 group-hover:text-white/70'
                  }`}
                />
              )}
            </button>
          );
        })}

        {!filteredOptions.length && (
          <div className="rounded-lg border border-white/10 bg-black/30 px-3 py-4 text-center text-sm text-white/40">
            {t('map.filters.empty', 'Nenhum filtro compatível')}
          </div>
        )}
      </div>
    </aside>
  );
}

export default MapFiltersPanel;


