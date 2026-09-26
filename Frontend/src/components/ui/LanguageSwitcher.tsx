import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Globe } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';

const LANGS = [
  { code: 'pt-BR', short: 'PT' },
  { code: 'en', short: 'EN' },
  { code: 'de', short: 'DE' },
  { code: 'fr', short: 'FR' },
  { code: 'es', short: 'ES' },
  { code: 'nl', short: 'NL' },
];

type Props = {
  variant?: 'button' | 'menu';
  iconOnly?: boolean;
};

export function LanguageSwitcher({ variant = 'button', iconOnly = false }: Props) {
  const { i18n, t } = useTranslation();
  const current = i18n.language;
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement | null>(null);

  const normalizeLng = useCallback((lng: string) => {
    const raw = (lng || '').trim();
    if (!raw) return 'pt-BR';
    if (raw.toLowerCase() === 'pt' || raw.toLowerCase().startsWith('pt-')) return 'pt-BR';
    if (raw.toLowerCase().startsWith('zh-')) return 'zh-CN';
    return raw.split('-')[0];
  }, []);

  const normalizedCurrent = useMemo(() => normalizeLng(current), [current, normalizeLng]);

  const applyDocumentDir = useCallback((lng: string) => {
    if (typeof document === 'undefined') return;
    const isRtl = normalizeLng(lng).toLowerCase().startsWith('ar');
    document.documentElement.dir = isRtl ? 'rtl' : 'ltr';
  }, [normalizeLng]);

  const change = useCallback(async (lng: string) => {
    const next = normalizeLng(lng);
    await i18n.changeLanguage(next);
    try {
      localStorage.setItem('lng', next);
    } catch {}
    applyDocumentDir(next);
    setOpen(false);
  }, [applyDocumentDir, i18n, normalizeLng]);

  useEffect(() => {
    applyDocumentDir(normalizedCurrent);
  }, [applyDocumentDir, normalizedCurrent]);

  useEffect(() => {
    if (!open) return;
    const onClick = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) {
        setOpen(false);
      }
    };
    document.addEventListener('click', onClick);
    return () => document.removeEventListener('click', onClick);
  }, [open]);

  const currentLabel = LANGS.find((l) => l.code === normalizedCurrent)?.short ?? 'PT';

  if (variant === 'menu') {
    return (
      <div className="space-y-1">
        <div className="text-xs uppercase text-white/40 px-1">{t('i18nMenu.language') ?? 'Language'}</div>
        <div className="flex items-center gap-2">
          {LANGS.map((l) => (
            <button
              key={l.code}
              onClick={() => change(l.code)}
              className={`px-2 py-1 rounded text-xs border ${normalizedCurrent === l.code ? 'bg-scum-panel text-white border-white/10' : 'text-white/80 hover:text-white border-white/10/0'}`}
              aria-pressed={normalizedCurrent === l.code}
            >
              {l.short}
            </button>
          ))}
        </div>
      </div>
    );
  }

  return (
    <div className="relative z-[150]" ref={ref}>
      <button
        onClick={(e) => {
          e.stopPropagation();
          setOpen((v) => !v);
        }}
        className={`${iconOnly ? 'px-2 py-2' : 'px-2.5 py-2'} rounded-lg text-white/80 hover:text-white inline-flex items-center gap-1.5 border border-white/10 bg-black/30`}
        aria-haspopup="menu"
        aria-expanded={open}
        aria-label={iconOnly ? t('i18nMenu.language') ?? 'Language' : undefined}
      >
        <Globe size={16} />
        {!iconOnly && currentLabel}
      </button>
      <AnimatePresence>
        {open && (
          <motion.div
            initial={{ opacity: 0, y: -4 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -4 }}
            transition={{ duration: 0.12 }}
            className="absolute right-0 mt-2 w-16 card p-1 z-[9999] shadow-xl"
            role="menu"
          >
            <div className="flex flex-col gap-1">
              {LANGS.map((l) => (
                <button
                  key={l.code}
                  onClick={() => change(l.code)}
                  role="menuitemradio"
                  aria-checked={normalizedCurrent === l.code}
                  className={`w-full text-center px-2 py-1.5 rounded-md text-sm transition-colors ${
                    normalizedCurrent === l.code
                      ? 'bg-scum-panel text-white'
                      : 'text-white/80 hover:text-white hover:bg-white/5'
                  }`}
                >
                  {l.short}
                </button>
              ))}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

export default LanguageSwitcher;


