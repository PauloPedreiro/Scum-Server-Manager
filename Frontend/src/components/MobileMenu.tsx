import React from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { X, Menu } from 'lucide-react';
import { useLanguage } from '../contexts/LanguageContext';

interface MobileMenuProps {
  isOpen: boolean;
  onToggle: () => void;
  children: React.ReactNode;
}

const MobileMenu: React.FC<MobileMenuProps> = ({ isOpen, onToggle, children }) => {
  const { t } = useLanguage();

  return (
    <>
      {/* Botão de menu mobile */}
      <button
        onClick={onToggle}
        className="mobile-menu-button mobile-only"
        aria-label={t('menu')}
      >
        <Menu size={24} />
      </button>

      {/* Overlay */}
      <AnimatePresence>
        {isOpen && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.2 }}
            className="mobile-overlay"
            onClick={onToggle}
          />
        )}
      </AnimatePresence>

      {/* Sidebar mobile */}
      <AnimatePresence>
        {isOpen && (
          <motion.aside
            initial={{ x: '-100%' }}
            animate={{ x: 0 }}
            exit={{ x: '-100%' }}
            transition={{ type: 'spring', damping: 25, stiffness: 200 }}
            className="sidebar-mobile"
          >
            {/* Header do menu mobile */}
            <div className="flex items-center justify-between p-4 border-b border-scum-primary">
              <h2 className="text-scum-light font-bold military-text">
                {t('menu')}
              </h2>
              <button
                onClick={onToggle}
                className="p-2 text-scum-light hover:text-scum-accent transition-colors"
                aria-label={t('close')}
              >
                <X size={24} />
              </button>
            </div>

            {/* Conteúdo do menu */}
            <div className="flex-1 overflow-y-auto">
              {children}
            </div>
          </motion.aside>
        )}
      </AnimatePresence>
    </>
  );
};

export default MobileMenu; 