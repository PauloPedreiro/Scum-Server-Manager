import { useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import SearchBar from '@/components/ui/SearchBar';
import {
  TOOLS,
  findTools,
  getFavoriteSlugs,
  getRecentSlugs,
  toggleFavoriteSlug,
  type ToolCategory,
  type ToolDefinition,
  type ToolType,
} from '@/tools/registry';
import { Star } from 'lucide-react';

export default function Tools() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const [query, setQuery] = useState('');
  const [category, setCategory] = useState<ToolCategory | 'All'>('All');
  const [type, setType] = useState<ToolType | 'All'>('All');
  const [favorites, setFavorites] = useState<Set<string>>(() => getFavoriteSlugs());

  const recents = useMemo(() => getRecentSlugs(), []);

  const categories = useMemo(() => {
    const set = new Set<ToolCategory>();
    for (const tool of TOOLS) set.add(tool.category);
    return Array.from(set).sort((a, b) => a.localeCompare(b));
  }, []);

  const filtered = useMemo(() => {
    const base = query.trim() ? findTools(query) : TOOLS;
    return base.filter((tool) => {
      if (category !== 'All' && tool.category !== category) return false;
      if (type !== 'All' && tool.type !== type) return false;
      return true;
    });
  }, [category, query, type]);

  const getToolTitle = (tool: ToolDefinition) =>
    t(`tools.registry.${tool.slug}.title`, {
      defaultValue: tool.title,
    });

  const getToolDescription = (tool: ToolDefinition) =>
    t(`tools.registry.${tool.slug}.description`, {
      defaultValue: tool.description,
    });

  const getCategoryLabel = (value: ToolCategory) =>
    t(`tools.categories.${value}`, {
      defaultValue: value,
    });

  const getTypeLabel = (value: ToolType) =>
    t(`tools.types.${value}`, {
      defaultValue: value,
    });

  const getStatusLabel = (value: string) =>
    t(`tools.status.${value}`, {
      defaultValue: value,
    });

  const favoritesList = useMemo(() => {
    const favs = TOOLS.filter((t) => favorites.has(t.slug) && t.status !== 'coming_soon');
    return favs.sort((a, b) => getToolTitle(a).localeCompare(getToolTitle(b)));
  }, [favorites, t]);

  const recentsList = useMemo(() => {
    const map = new Map(TOOLS.map((t) => [t.slug, t] as const));
    return recents
      .map((slug) => map.get(slug))
      .filter((x): x is ToolDefinition => Boolean(x));
  }, [recents]);

  const openTool = (tool: ToolDefinition) => {
    navigate(tool.route);
  };

  return (
    <div className="space-y-4">
      <div className="card p-4">
        <div className="text-lg font-semibold">
          {t('tools.title', { defaultValue: 'Tools' })}
        </div>
        <div className="text-sm text-white/60">
          {t('tools.subtitle', { defaultValue: 'Administrative tools and routines.' })}
        </div>
      </div>

      <div className="card p-4 space-y-3">
        <SearchBar
          value={query}
          onChange={setQuery}
          placeholder={t('tools.search.placeholder', { defaultValue: 'Search tools...' })}
        />

        <div className="flex flex-wrap items-center gap-2">
          <div className="text-xs uppercase text-white/40">
            {t('tools.filters.title', { defaultValue: 'Filters' })}
          </div>

          <select
            value={category}
            onChange={(e) => setCategory(e.target.value as ToolCategory | 'All')}
            style={{ colorScheme: 'dark' }}
            className="px-3 py-2 rounded-lg bg-[#0b1220] border border-white/10 text-white text-sm focus:outline-none focus:ring-2 focus:ring-scum-orange"
          >
            <option value="All" style={{ backgroundColor: '#0b1220', color: '#fff' }}>
              {t('tools.filters.allCategories', { defaultValue: 'All categories' })}
            </option>
            {categories.map((c) => (
              <option key={c} value={c}>
                {getCategoryLabel(c)}
              </option>
            ))}
          </select>

          <select
            value={type}
            onChange={(e) => setType(e.target.value as ToolType | 'All')}
            style={{ colorScheme: 'dark' }}
            className="px-3 py-2 rounded-lg bg-[#0b1220] border border-white/10 text-white text-sm focus:outline-none focus:ring-2 focus:ring-scum-orange"
          >
            <option value="All" style={{ backgroundColor: '#0b1220', color: '#fff' }}>
              {t('tools.filters.allTypes', { defaultValue: 'All types' })}
            </option>
            <option value="module" style={{ backgroundColor: '#0b1220', color: '#fff' }}>
              {t('tools.filters.modules', { defaultValue: 'Modules' })}
            </option>
            <option value="action" style={{ backgroundColor: '#0b1220', color: '#fff' }}>
              {t('tools.filters.actions', { defaultValue: 'Quick actions' })}
            </option>
          </select>
        </div>
      </div>

      {favoritesList.length > 0 && (
        <div className="space-y-2">
          <div className="text-xs uppercase text-white/40 px-1">
            {t('tools.sections.favorites', { defaultValue: 'Favorites' })}
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
            {favoritesList.map((tool) => (
              <div
                key={tool.slug}
                role="button"
                tabIndex={0}
                onClick={() => openTool(tool)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter' || e.key === ' ') {
                    e.preventDefault();
                    openTool(tool);
                  }
                }}
                className="card p-4 text-left hover:bg-white/5 transition-colors cursor-pointer"
              >
                <div className="flex items-start gap-3">
                  <div className="min-w-0 flex-1">
                    <div className="font-semibold truncate">{getToolTitle(tool)}</div>
                    <div className="text-sm text-white/60 line-clamp-2">{getToolDescription(tool)}</div>
                    <div className="mt-2 flex items-center gap-2 text-xs text-white/50">
                      <span className="px-2 py-0.5 rounded border border-white/10">
                        {getCategoryLabel(tool.category)}
                      </span>
                      <span className="px-2 py-0.5 rounded border border-white/10">{getTypeLabel(tool.type)}</span>
                    </div>
                  </div>
                  <button
                    onClick={(e) => {
                      e.preventDefault();
                      e.stopPropagation();
                      const next = toggleFavoriteSlug(tool.slug);
                      setFavorites(new Set(next));
                    }}
                    className="p-2 rounded hover:bg-white/5 text-white/60 hover:text-white"
                    aria-label="Toggle favorite"
                  >
                    <Star size={16} className={favorites.has(tool.slug) ? 'fill-scum-orange text-scum-orange' : ''} />
                  </button>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {recentsList.length > 0 && (
        <div className="space-y-2">
          <div className="text-xs uppercase text-white/40 px-1">
            {t('tools.sections.recents', { defaultValue: 'Recent' })}
          </div>
          <div className="flex flex-wrap gap-2">
            {recentsList.slice(0, 8).map((tool) => (
              <button
                key={tool.slug}
                onClick={() => openTool(tool)}
                className="px-3 py-2 rounded-lg border border-white/10 bg-white/5 text-sm text-white/80 hover:text-white hover:bg-white/10"
              >
                {getToolTitle(tool)}
              </button>
            ))}
          </div>
        </div>
      )}

      <div className="space-y-2">
        <div className="flex items-center justify-between px-1">
          <div className="text-xs uppercase text-white/40">
            {t('tools.sections.allTools', { defaultValue: 'All tools' })}
          </div>
          <div className="text-xs text-white/40">{filtered.length}</div>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
          {filtered.map((tool) => (
            <div
              key={tool.slug}
              role="button"
              tabIndex={0}
              onClick={() => openTool(tool)}
              onKeyDown={(e) => {
                if (e.key === 'Enter' || e.key === ' ') {
                  e.preventDefault();
                  openTool(tool);
                }
              }}
              className="card p-4 text-left hover:bg-white/5 transition-colors cursor-pointer"
            >
              <div className="flex items-start gap-3">
                <div className="min-w-0 flex-1">
                  <div className="flex items-center gap-2">
                    <div className="font-semibold truncate">{getToolTitle(tool)}</div>
                    {tool.status !== 'active' && (
                      <span className="text-[11px] px-2 py-0.5 rounded border border-white/10 text-white/60">
                        {getStatusLabel(tool.status)}
                      </span>
                    )}
                  </div>
                  <div className="text-sm text-white/60 line-clamp-2">{getToolDescription(tool)}</div>
                  <div className="mt-2 flex items-center gap-2 text-xs text-white/50">
                    <span className="px-2 py-0.5 rounded border border-white/10">
                      {getCategoryLabel(tool.category)}
                    </span>
                    <span className="px-2 py-0.5 rounded border border-white/10">{getTypeLabel(tool.type)}</span>
                  </div>
                </div>

                <button
                  onClick={(e) => {
                    e.preventDefault();
                    e.stopPropagation();
                    const next = toggleFavoriteSlug(tool.slug);
                    setFavorites(new Set(next));
                  }}
                  className="p-2 rounded hover:bg-white/5 text-white/60 hover:text-white"
                  aria-label="Toggle favorite"
                >
                  <Star size={16} className={favorites.has(tool.slug) ? 'fill-scum-orange text-scum-orange' : ''} />
                </button>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
