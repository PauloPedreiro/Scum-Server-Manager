import { lazy, Suspense, useEffect, useMemo, type ComponentType, type LazyExoticComponent } from 'react';
import { useParams } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { TOOLS, addRecentSlug } from '@/tools/registry';

const PAGE_CACHE = new Map<string, LazyExoticComponent<ComponentType>>();

function getToolPage(slug: string, pageLoader?: () => Promise<{ default: ComponentType<any> }>) {
  if (!pageLoader) return undefined;
  const cached = PAGE_CACHE.get(slug);
  if (cached) return cached;
  const Page = lazy(pageLoader);
  PAGE_CACHE.set(slug, Page);
  return Page;
}

export default function ToolRouter() {
  const { t } = useTranslation();
  const params = useParams();
  const slug = params.tool;

  const tool = useMemo(() => TOOLS.find((t) => t.slug === slug), [slug]);

  useEffect(() => {
    if (tool?.slug) {
      addRecentSlug(tool.slug);
    }
  }, [tool?.slug]);

  if (!tool || !slug) {
    return (
      <div className="card p-4">
        <div className="text-lg font-semibold">
          {t('tools.router.notFoundTitle', { defaultValue: 'Tool not found' })}
        </div>
        <div className="text-sm text-white/60">
          {t('tools.router.notFoundText', { defaultValue: 'The requested tool does not exist.' })}
        </div>
      </div>
    );
  }

  if (tool.status !== 'active') {
    const toolTitle = t(`tools.registry.${tool.slug}.title`, { defaultValue: tool.title });
    const toolDescription = t(`tools.registry.${tool.slug}.description`, { defaultValue: tool.description });
    return (
      <div className="card p-4">
        <div className="text-lg font-semibold">{toolTitle}</div>
        <div className="text-sm text-white/60">{toolDescription}</div>
        <div className="mt-3 text-sm text-white/60">
          {t('tools.router.comingSoon', { defaultValue: 'Coming soon' })}{' '}
          <span className="text-white/40">
            ({t(`tools.status.${tool.status}`, { defaultValue: tool.status })})
          </span>
        </div>
      </div>
    );
  }

  const Page = getToolPage(tool.slug, tool.pageLoader);
  if (!Page) {
    const toolTitle = t(`tools.registry.${tool.slug}.title`, { defaultValue: tool.title });
    const toolDescription = t(`tools.registry.${tool.slug}.description`, { defaultValue: tool.description });
    return (
      <div className="card p-4">
        <div className="text-lg font-semibold">{toolTitle}</div>
        <div className="text-sm text-white/60">{toolDescription}</div>
        <div className="mt-3 text-sm text-white/60">
          {t('tools.router.pageNotImplemented', { defaultValue: 'Tool page not implemented' })}
        </div>
      </div>
    );
  }

  return (
    <Suspense>
      <Page />
    </Suspense>
  );
}
