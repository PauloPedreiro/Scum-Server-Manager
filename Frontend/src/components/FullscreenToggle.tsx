import React, { useState, useEffect } from 'react';
import { Maximize2, Minimize2 } from 'lucide-react';
import { useLanguage } from '../contexts/LanguageContext';

const FullscreenToggle: React.FC = () => {
  const { t } = useLanguage();
  const [isFullscreen, setIsFullscreen] = useState(false);

  useEffect(() => {
    // Verificar se já está em fullscreen ao carregar
    const checkFullscreen = () => {
      setIsFullscreen(!!document.fullscreenElement);
    };

    checkFullscreen();

    // Adicionar listener para mudanças de fullscreen
    document.addEventListener('fullscreenchange', checkFullscreen);
    
    return () => {
      document.removeEventListener('fullscreenchange', checkFullscreen);
    };
  }, []);

  const toggleFullscreen = async () => {
    try {
      if (!document.fullscreenElement) {
        // Entrar em fullscreen
        await document.documentElement.requestFullscreen();
        setIsFullscreen(true);
      } else {
        // Sair do fullscreen
        await document.exitFullscreen();
        setIsFullscreen(false);
      }
    } catch (error) {
      console.error('Erro ao alternar fullscreen:', error);
    }
  };

  return (
    <button
      onClick={toggleFullscreen}
      className="mobile-only fixed top-4 right-4 z-50 bg-scum-accent/90 hover:bg-scum-accent text-scum-dark rounded-full p-2 sm:p-3 shadow-lg backdrop-blur-sm border border-scum-accent/30 transition-all duration-200 hover:scale-105 active:scale-95"
      title={isFullscreen ? t('fullscreen_exit') : t('fullscreen_enter')}
      aria-label={isFullscreen ? t('fullscreen_exit') : t('fullscreen_enter')}
    >
      {isFullscreen ? (
        <Minimize2 size={18} className="sm:w-5 sm:h-5" />
      ) : (
        <Maximize2 size={18} className="sm:w-5 sm:h-5" />
      )}
    </button>
  );
};

export default FullscreenToggle;