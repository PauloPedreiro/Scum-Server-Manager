import { useEffect, useMemo, useRef, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Image as ImageIcon, X } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';

// Carrega todas as imagens da pasta backgrounds como URLs estáticas
const files = import.meta.glob('/src/assets/backgrounds/*.{png,jpg,jpeg,webp}', {
  eager: true,
  query: '?url',
  import: 'default',
});

type BgItem = { key: string; url: string; name: string };

function useBackground() {
  const [current, setCurrent] = useState<string | null>(null);

  useEffect(() => {
    try {
      const saved = localStorage.getItem('bg');
      if (saved) setCurrent(saved);
    } catch {}
  }, []);

  useEffect(() => {
    const root = document.documentElement as HTMLElement;
    if (!current) {
      root.style.setProperty('--app-bg-url', 'none');
      return;
    }
    root.style.setProperty('--app-bg-url', `url(${current})`);
  }, [current]);

  const set = (url: string | null) => {
    setCurrent(url);
    try {
      if (url) localStorage.setItem('bg', url);
      else localStorage.removeItem('bg');
    } catch {}
  };

  return { current, set };
}

type Props = { variant?: 'button' | 'menu'; iconOnly?: boolean };

export function BackgroundSelector({ variant = 'button', iconOnly = false }: Props) {
  const { t } = useTranslation();
  const { current, set } = useBackground();
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement | null>(null);

  const items: BgItem[] = useMemo(() =>
    Object.entries(files).map(([key, url]) => ({
      key,
      url: url as string,
      name: key.split('/').pop()!.replace(/\.[^.]+$/, ''),
    })), []);

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

  if (variant === 'menu') {
    return (
      <div className="space-y-2">
        <div className="text-xs uppercase text-white/40 px-1">{t('background.title')}</div>
        <button
          onClick={() => set(null)}
          className={`w-full text-left px-2 py-1 rounded text-sm inline-flex items-center gap-2 ${
            !current ? 'bg-scum-panel text-white' : 'text-white/80 hover:text-white hover:bg-white/5'
          }`}
        >
          <X size={14} /> {t('background.none')}
        </button>
        <div className="grid grid-cols-2 sm:grid-cols-3 gap-2">
          {items.map((item) => (
            <button
              key={item.key}
              onClick={() => set(item.url)}
              title={item.name}
              className={`relative rounded overflow-hidden border ${
                current === item.url ? 'border-scum-accent' : 'border-white/10 hover:border-white/20'
              }`}
            >
              <img src={item.url} alt={item.name} className="w-full h-16 object-cover" />
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
        className={`${iconOnly ? 'px-2 py-2' : 'px-4 py-2.5'} rounded-lg text-white/80 hover:text-white inline-flex items-center gap-2 border border-white/10 bg-black/30`}
        aria-haspopup="menu"
        aria-expanded={open}
        aria-label={iconOnly ? t('background.title') : undefined}
      >
        <ImageIcon size={16} />
        {!iconOnly && t('background.title')}
      </button>
      <AnimatePresence>
        {open && (
          <motion.div
            initial={{ opacity: 0, y: -4 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -4 }}
            transition={{ duration: 0.12 }}
            className="absolute right-0 mt-2 w-64 card p-2 space-y-2 max-h-80 overflow-auto z-[9999] shadow-xl"
            role="menu"
          >
            <button
              onClick={() => set(null)}
              className={`w-full text-left px-2 py-1 rounded text-sm inline-flex items-center gap-2 ${
                !current ? 'bg-scum-panel text-white' : 'text-white/80 hover:text-white hover:bg-white/5'
              }`}
            >
              <X size={14} /> {t('background.none')}
            </button>
            <div className="grid grid-cols-2 gap-2">
              {items.map((item) => (
                <button
                  key={item.key}
                  onClick={() => set(item.url)}
                  title={item.name}
                  className={`relative rounded overflow-hidden border ${
                    current === item.url ? 'border-scum-accent' : 'border-white/10 hover:border-white/20'
                  }`}
                >
                  <img src={item.url} alt={item.name} className="w-full h-20 object-cover" />
                </button>
              ))}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

export default BackgroundSelector;


