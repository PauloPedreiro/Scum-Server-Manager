import type { ComponentType } from 'react';

export type ToolType = 'action' | 'module';

export type ToolCategory =
  | 'Player'
  | 'World'
  | 'Economy'
  | 'Server'
  | 'RCON'
  | 'Mods'
  | 'Logs'
  | 'Other';

export type ToolStatus = 'active' | 'coming_soon' | 'beta';

export type ToolPageModule = { default: ComponentType<any> };
export type ToolPageLoader = () => Promise<ToolPageModule>;

export type ToolDefinition = {
  slug: string;
  title: string;
  description: string;
  category: ToolCategory;
  type: ToolType;
  tags: string[];
  route: string;
  status: ToolStatus;
  pageLoader?: ToolPageLoader;
};

export const TOOLS: ToolDefinition[] = [
  {
    slug: 'shop-deliveries',
    title: 'Shop & Deliveries',
    description: 'Admin catalog management (scanner, enable/disable, pricing, limits).',
    category: 'Economy',
    type: 'module',
    tags: ['shop', 'economy', 'catalog', 'offers', 'scanner', 'delivery'],
    route: '/tools/shop-deliveries',
    status: 'active',
    pageLoader: () => import('../pages/tools/ShopDeliveries'),
  },

  {
    slug: 'integrations',
    title: 'Integrações',
    description: 'Manage public integrations (API keys) for external bots/systems.',
    category: 'Other',
    type: 'module',
    tags: ['integrations', 'discord', 'api', 'keys'],
    route: '/tools/integrations',
    status: 'active',
    pageLoader: () => import('../pages/tools/Integrations'),
  },

  {
    slug: 'events',
    title: 'Agendador de Eventos',
    description: 'Crie e agende eventos, execute múltiplos comandos sequenciais e homologue novos comandos.',
    category: 'World',
    type: 'module',
    tags: ['events', 'scheduler', 'rcon', 'commands', 'homologation', 'coordinates'],
    route: '/tools/events',
    status: 'active',
    pageLoader: () => import('../pages/tools/Events'),
  },
];

const FAVORITES_KEY = 'tools:favorites';
const RECENTS_KEY = 'tools:recents';
const RECENTS_MAX = 12;

export function getFavoriteSlugs(): Set<string> {
  try {
    const raw = localStorage.getItem(FAVORITES_KEY);
    if (!raw) return new Set();
    const arr = JSON.parse(raw);
    if (!Array.isArray(arr)) return new Set();
    return new Set(arr.filter((x) => typeof x === 'string'));
  } catch {
    return new Set();
  }
}

export function setFavoriteSlugs(slugs: Set<string>) {
  try {
    localStorage.setItem(FAVORITES_KEY, JSON.stringify(Array.from(slugs)));
  } catch {}
}

export function toggleFavoriteSlug(slug: string): Set<string> {
  const next = getFavoriteSlugs();
  if (next.has(slug)) next.delete(slug);
  else next.add(slug);
  setFavoriteSlugs(next);
  return next;
}

export function getRecentSlugs(): string[] {
  try {
    const raw = localStorage.getItem(RECENTS_KEY);
    if (!raw) return [];
    const arr = JSON.parse(raw);
    if (!Array.isArray(arr)) return [];
    return arr.filter((x) => typeof x === 'string');
  } catch {
    return [];
  }
}

export function addRecentSlug(slug: string) {
  try {
    const current = getRecentSlugs();
    const next = [slug, ...current.filter((s) => s !== slug)].slice(0, RECENTS_MAX);
    localStorage.setItem(RECENTS_KEY, JSON.stringify(next));
  } catch {}
}

export function findTools(query: string): ToolDefinition[] {
  const q = query.trim().toLowerCase();
  if (!q) return TOOLS;
  return TOOLS.filter((t) => {
    const haystack = [t.slug, t.title, t.description, t.category, t.type, ...t.tags]
      .join(' ')
      .toLowerCase();
    return haystack.includes(q);
  });
}
