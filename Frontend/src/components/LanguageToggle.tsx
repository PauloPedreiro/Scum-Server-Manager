import React, { useState, useRef, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { ChevronDown } from 'lucide-react';
import { useLanguage } from '../contexts/LanguageContext';

// Interface para idiomas suportados
interface Language {
  code: string;
  name: string;
  nativeName: string;
  sigla: string;
  country: string;
}

// Lista de idiomas suportados
const SUPPORTED_LANGUAGES: Language[] = [
  {
    code: 'pt-BR',
    name: 'Portuguese',
    nativeName: 'Português',
    sigla: 'BR',
    country: 'Brazil'
  },
  {
    code: 'en-US',
    name: 'English',
    nativeName: 'English',
    sigla: 'US',
    country: 'United States'
  },
  // Futuros idiomas podem ser adicionados aqui
  // {
  //   code: 'es-ES',
  //   name: 'Spanish',
  //   nativeName: 'Español',
  //   sigla: 'ES',
  //   country: 'Spain'
  // },
  // {
  //   code: 'fr-FR',
  //   name: 'French',
  //   nativeName: 'Français',
  //   sigla: 'FR',
  //   country: 'France'
  // }
];

const LanguageToggle: React.FC = () => {
  const { language, setLanguage, t } = useLanguage();
  const [isOpen, setIsOpen] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);

  // Fechar dropdown quando clicar fora
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setIsOpen(false);
      }
    };

    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  // Obter idioma atual
  const currentLanguage = SUPPORTED_LANGUAGES.find(lang => lang.code === language) || SUPPORTED_LANGUAGES[0];

  const handleLanguageChange = (languageCode: string) => {
    setLanguage(languageCode as 'pt-BR' | 'en-US');
    setIsOpen(false);
  };

  return (
    <div className="relative flex-shrink-0" ref={dropdownRef}>
      {/* Botão principal */}
      <motion.button
        whileHover={{ scale: 1.02 }}
        whileTap={{ scale: 0.98 }}
        onClick={() => setIsOpen(!isOpen)}
        className="scum-button-mobile flex items-center gap-1 sm:gap-2"
        title={`${t('select_language')} - ${currentLanguage.nativeName}`}
      >
        <div className="flex items-center gap-1">
          <div className="flex-shrink-0">
            <span className="text-xs font-bold text-scum-light">
              {currentLanguage.sigla}
            </span>
          </div>
          <motion.div
            animate={{ rotate: isOpen ? 180 : 0 }}
            transition={{ duration: 0.2 }}
          >
            <ChevronDown className="w-3 h-3 text-scum-light/60" />
          </motion.div>
        </div>
      </motion.button>

      {/* Menu dropdown */}
      <AnimatePresence>
        {isOpen && (
          <motion.div
            initial={{ opacity: 0, y: -10, scale: 0.95 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: -10, scale: 0.95 }}
            transition={{ duration: 0.2 }}
            className="absolute top-full right-0 mt-1 w-48 bg-scum-dark/95 border border-scum-accent/20 rounded-lg shadow-lg backdrop-blur-sm z-[9999]"
          >
            <div className="py-1">
              {SUPPORTED_LANGUAGES.map((lang) => (
                <motion.button
                  key={lang.code}
                  whileHover={{ backgroundColor: 'rgba(255, 255, 255, 0.1)' }}
                  onClick={() => handleLanguageChange(lang.code)}
                  className={`w-full flex items-center gap-3 px-4 py-2 text-left transition-colors ${
                    language === lang.code
                      ? 'bg-scum-accent/20 text-scum-secondary'
                      : 'text-scum-light hover:text-scum-secondary'
                  }`}
                >
                  <div className="flex-shrink-0">
                    <span className="text-xs font-bold text-scum-light">
                      {lang.sigla}
                    </span>
                  </div>
                  <div className="flex flex-col">
                    <span className="text-xs font-medium">{lang.nativeName}</span>
                    <span className="text-xs text-scum-light/60">{lang.name}</span>
                  </div>
                  {language === lang.code && (
                    <div className="ml-auto">
                      <div className="w-2 h-2 bg-scum-secondary rounded-full"></div>
                    </div>
                  )}
                </motion.button>
              ))}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
};

export default LanguageToggle; 