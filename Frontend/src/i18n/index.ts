import i18n from 'i18next';
import { initReactI18next } from 'react-i18next';

import ptBR from './locales/pt-BR/translation.json';
import en from './locales/en/translation.json';
import de from './locales/de/translation.json';
import fr from './locales/fr/translation.json';
import es from './locales/es/translation.json';
import ar from './locales/ar/translation.json';
import ru from './locales/ru/translation.json';
import zhCN from './locales/zh-CN/translation.json';
import nl from './locales/nl/translation.json';

const resources = {
  'pt-BR': { translation: ptBR },
  en: { translation: en },
  de: { translation: de },
  fr: { translation: fr },
  es: { translation: es },
  ar: { translation: ar },
  ru: { translation: ru },
  'zh-CN': { translation: zhCN },
  nl: { translation: nl },
} as const;

const saved = (() => {
  try {
    return localStorage.getItem('lng');
  } catch {
    return null;
  }
})();

const browser = typeof navigator !== 'undefined' ? navigator.language : 'pt-BR';
const initialLng = saved || (browser.startsWith('pt') ? 'pt-BR' : 'en');

void i18n
  .use(initReactI18next)
  .init({
    resources,
    lng: initialLng,
    fallbackLng: 'en',
    interpolation: { escapeValue: false },
    returnNull: false,
  });

export default i18n;


