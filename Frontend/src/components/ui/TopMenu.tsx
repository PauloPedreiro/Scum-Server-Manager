import { useRef, useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Menu } from 'lucide-react';
import { LanguageSwitcher } from '@/components/ui/LanguageSwitcher';
import { BackgroundSelector } from '@/components/ui/BackgroundSelector';
import { useTranslation } from 'react-i18next';

export function TopMenu() {
  const { t } = useTranslation();
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    const onClick = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    };
    window.addEventListener('click', onClick);
    return () => window.removeEventListener('click', onClick);
  }, []);

  return (
    <div className="relative" ref={ref}>
      <button
        onClick={() => setOpen((v) => !v)}
        className="px-3 py-2.5 rounded-lg text-white/80 hover:text-white inline-flex items-center gap-2 border border-white/10 bg-black/30"
        aria-haspopup="menu"
        aria-expanded={open}
      >
        <Menu size={16} /> {t('menu.title', { defaultValue: 'Menu' })}
      </button>
      <AnimatePresence>
        {open && (
          <motion.div
            initial={{ opacity: 0, y: -4 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -4 }}
            transition={{ duration: 0.12 }}
            className="absolute right-0 mt-2 w-72 sm:w-80 card p-3 space-y-3"
            role="menu"
          >
            <LanguageSwitcher variant="menu" />
            <div className="h-px w-full bg-white/10" />
            <BackgroundSelector variant="menu" />
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

export default TopMenu;


