import React, { useState, useEffect } from 'react';
import { Download, Smartphone } from 'lucide-react';

interface BeforeInstallPromptEvent extends Event {
  prompt(): Promise<void>;
  userChoice: Promise<{ outcome: 'accepted' | 'dismissed' }>;
}

const PWAInstallButton: React.FC = () => {
  const [deferredPrompt, setDeferredPrompt] = useState<BeforeInstallPromptEvent | null>(null);
  const [showInstallButton, setShowInstallButton] = useState(false);

  useEffect(() => {
    const handleBeforeInstallPrompt = (e: Event) => {
      e.preventDefault();
      setDeferredPrompt(e as BeforeInstallPromptEvent);
      setShowInstallButton(true);
    };

    const handleAppInstalled = () => {
      setShowInstallButton(false);
      setDeferredPrompt(null);
    };

    window.addEventListener('beforeinstallprompt', handleBeforeInstallPrompt);
    window.addEventListener('appinstalled', handleAppInstalled);

    return () => {
      window.removeEventListener('beforeinstallprompt', handleBeforeInstallPrompt);
      window.removeEventListener('appinstalled', handleAppInstalled);
    };
  }, []);

  const handleInstallClick = async () => {
    if (!deferredPrompt) return;

    deferredPrompt.prompt();
    const { outcome } = await deferredPrompt.userChoice;
    
    if (outcome === 'accepted') {
      console.log('PWA instalado com sucesso!');
    }
    
    setDeferredPrompt(null);
    setShowInstallButton(false);
  };

  const handleManualInstall = () => {
    // Instruções para instalação manual
    const instructions = `
📱 Para instalar o SCUM Server Manager como app:

1. Abra o menu do navegador (⋮)
2. Clique em "Instalar aplicativo" ou "Adicionar à tela inicial"
3. Confirme a instalação

Ou use as DevTools:
1. Pressione F12
2. Vá na aba "Application" → "Manifest"
3. Clique em "Install"
    `;
    
    alert(instructions);
  };

  if (!showInstallButton) {
    return (
      <button
        onClick={handleManualInstall}
        className="flex items-center gap-2 px-4 py-2 bg-green-600 hover:bg-green-700 text-white rounded-lg transition-colors"
        title="Instalar como app"
      >
        <Smartphone size={20} />
        <span>Instalar App</span>
      </button>
    );
  }

  return (
    <button
      onClick={handleInstallClick}
      className="flex items-center gap-2 px-4 py-2 bg-green-600 hover:bg-green-700 text-white rounded-lg transition-colors animate-pulse"
      title="Instalar PWA"
    >
      <Download size={20} />
      <span>Instalar PWA</span>
    </button>
  );
};

export default PWAInstallButton;