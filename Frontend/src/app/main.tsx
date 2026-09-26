import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import { RouterProvider } from 'react-router-dom';
import { AnimatePresence } from 'framer-motion';
import { Toaster as HotToaster } from 'react-hot-toast';
import { ToastContainer } from 'react-toastify';
import 'react-toastify/dist/ReactToastify.css';
import './styles/index.css';
import { router } from './routes';
import '@/i18n';

// Suprimir avisos de violação de performance em produção
if (import.meta.env.PROD) {
  // Desabilitar avisos de violação do Chrome em produção
  const originalWarn = console.warn;
  console.warn = (...args: any[]) => {
    const message = args[0]?.toString() || '';
    // Ignorar avisos de violação de performance
    if (message.includes('[Violation]') || message.includes('handler took')) {
      return;
    }
    originalWarn.apply(console, args);
  };
}

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <AnimatePresence mode="wait">
      <RouterProvider router={router} />
    </AnimatePresence>
    <HotToaster position="top-right" />
    <ToastContainer position="bottom-right" theme="dark" />
  </StrictMode>
);


