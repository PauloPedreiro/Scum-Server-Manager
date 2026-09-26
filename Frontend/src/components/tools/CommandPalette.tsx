import { useEffect, useMemo, useRef, useState } from 'react';
import { AnimatePresence, motion } from 'framer-motion';
import { useNavigate } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { Search, Star } from 'lucide-react';
import {
  TOOLS,
  findTools,
  getFavoriteSlugs,
  getRecentSlugs,
  toggleFavoriteSlug,
  type ToolDefinition,
} from '@/tools/registry';

type Props = {
  open: boolean;
  onClose: () => void;
};

function scoreTool(tool: ToolDefinition, favorites: Set<string>, recents: string[]) {
  const fav = favorites.has(tool.slug) ? 1000 : 0;
  const recentIndex = recents.indexOf(tool.slug);
  const recentScore = recentIndex >= 0 ? 500 - recentIndex : 0;
  const active = tool.status === 'active' ? 50 : 0;
  return fav + recentScore + active;
}

export function CommandPalette({ open, onClose }: Props) {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const [query, setQuery] = useState('');
  const [favorites, setFavorites] = useState<Set<string>>(() => getFavoriteSlugs());
  const inputRef = useRef<HTMLInputElement | null>(null);

  const getToolTitle = (tool: ToolDefinition) =>
    t(`tools.registry.${tool.slug}.title`, {
      defaultValue: tool.title,
    });

  const getToolDescription = (tool: ToolDefinition) =>
    t(`tools.registry.${tool.slug}.description`, {
      defaultValue: tool.description,
    });

  const getCategoryLabel = (value: string) =>
    t(`tools.categories.${value}`, {
      defaultValue: value,
    });

  const getTypeLabel = (value: string) =>
    t(`tools.types.${value}`, {
      defaultValue: value,
    });

  const getStatusLabel = (value: string) =>
    t(`tools.status.${value}`, {
      defaultValue: value,
    });

  const recents = useMemo(() => getRecentSlugs(), [open]);

  const results = useMemo(() => {
    const base = query.trim() ? findTools(query) : TOOLS;
    const scored = base
      .map((t) => ({ t, score: scoreTool(t, favorites, recents) }))
      .sort((a, b) => b.score - a.score || a.t.title.localeCompare(b.t.title));
    return scored.map((x) => x.t).slice(0, 30);
  }, [favorites, query, recents]);

  useEffect(() => {
    if (!open) return;
    setQuery('');
    setFavorites(getFavoriteSlugs());
    const t = window.setTimeout(() => {
      inputRef.current?.focus();
    }, 0);
    return () => window.clearTimeout(t);
  }, [open]);

  useEffect(() => {
    if (!open) return;
    const onKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        e.preventDefault();
        onClose();
      }
    };
    window.addEventListener('keydown', onKeyDown);
    return () => window.removeEventListener('keydown', onKeyDown);
  }, [onClose, open]);

  return (
    <AnimatePresence>
      {open && (
        <>
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={onClose}
            className="fixed inset-0 bg-black/60 backdrop-blur-sm z-50"
          />
          <motion.div
            initial={{ opacity: 0, scale: 0.98, y: 12 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.98, y: 12 }}
            className="fixed inset-0 z-50 flex items-start justify-center p-4 sm:p-6"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="w-full max-w-2xl bg-black rounded-xl border border-white/10 shadow-2xl overflow-hidden">
              <div className="p-3 border-b border-white/10 flex items-center gap-2">
                <Search size={18} className="text-white/40" />
                <input
                  ref={inputRef}
                  value={query}
                  onChange={(e) => setQuery(e.target.value)}
                  placeholder={t('tools.search.placeholder', { defaultValue: 'Search tools...' })}
                  className="w-full bg-transparent outline-none text-white placeholder-white/40 text-sm sm:text-base"
                />
                <div className="text-xs text-white/40 border border-white/10 rounded px-2 py-1">Esc</div>
              </div>

              <div className="max-h-[60vh] overflow-y-auto">
                {results.length === 0 ? (
                  <div className="p-4 text-sm text-white/60">
                    {t('tools.search.noResults', { defaultValue: 'No results' })}
                  </div>
                ) : (
                  <div className="divide-y divide-white/10">
                    {results.map((tool) => (
                      <div
                        key={tool.slug}
                        role="button"
                        tabIndex={0}
                        onClick={() => {
                          onClose();
                          navigate(tool.route);
                        }}
                        onKeyDown={(e) => {
                          if (e.key === 'Enter' || e.key === ' ') {
                            e.preventDefault();
                            onClose();
                            navigate(tool.route);
                          }
                        }}
                        className="w-full text-left p-3 hover:bg-white/5 transition-colors flex items-center gap-3 cursor-pointer"
                      >
                        <div className="min-w-0 flex-1">
                          <div className="flex items-center gap-2">
                            <div className="font-medium text-white truncate">{getToolTitle(tool)}</div>
                            <div className="text-[11px] px-2 py-0.5 rounded border border-white/10 text-white/60">
                              {getCategoryLabel(tool.category)}
                            </div>
                            <div className="text-[11px] px-2 py-0.5 rounded border border-white/10 text-white/60">
                              {getTypeLabel(tool.type)}
                            </div>
                            {tool.status !== 'active' && (
                              <div className="text-[11px] px-2 py-0.5 rounded border border-white/10 text-white/60">
                                {getStatusLabel(tool.status)}
                              </div>
                            )}
                          </div>
                          <div className="text-xs text-white/50 truncate">{getToolDescription(tool)}</div>
                        </div>

                        <button
                          onClick={(e) => {
                            e.preventDefault();
                            e.stopPropagation();
                            const next = toggleFavoriteSlug(tool.slug);
                            setFavorites(new Set(next));
                          }}
                          className="p-2 rounded hover:bg-white/5 text-white/60 hover:text-white"
                          aria-label={t('tools.favorites.toggle', { defaultValue: 'Toggle favorite' })}
                        >
                          <Star size={16} className={favorites.has(tool.slug) ? 'fill-scum-orange text-scum-orange' : ''} />
                        </button>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  );
}
