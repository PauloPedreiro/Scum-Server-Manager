import { useState, useEffect } from 'react';

export const useBunkersCountdown = () => {
  // Inicializa o contador com valor do localStorage ou padrão
  const [countdown, setCountdown] = useState(() => {
    const saved = localStorage.getItem('bunkersCountdown');
    if (saved) {
      const savedTime = parseInt(saved);
      const now = Date.now();
      const elapsed = Math.floor((now - savedTime) / 1000);
      const remaining = Math.max(0, 1800 - elapsed); // 30 minutos = 1800 segundos
      return remaining;
    }
    return 1800; // 30 minutos em segundos
  });

  // Função para resetar o contador (chamada quando dados são atualizados)
  const resetCountdown = () => {
    setCountdown(1800);
    localStorage.setItem('bunkersCountdown', Date.now().toString());
  };

  // Função para formatar o contador
  const formatCountdown = (seconds: number) => {
    const hours = Math.floor(seconds / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    const secs = seconds % 60;
    return `${hours.toString().padStart(2, '0')}:${minutes.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
  };

  // Countdown timer - REMOVIDO: Agora é manual
  // useEffect(() => {
  //   const countdownInterval = setInterval(() => {
  //     setCountdown(prev => {
  //       if (prev <= 1) {
  //         return 1800; // Reset to 30 minutes
  //       }
  //       return prev - 1;
  //     });
  //   }, 1000);

  //   return () => clearInterval(countdownInterval);
  // }, []);

  // Salva o contador no localStorage sempre que ele mudar
  useEffect(() => {
    if (countdown > 0 && countdown < 1800) {
      const now = Date.now();
      const elapsed = Math.floor((now - parseInt(localStorage.getItem('bunkersCountdown') || '0')) / 1000);
      const remaining = Math.max(0, 1800 - elapsed);
      if (Math.abs(remaining - countdown) <= 1) { // Tolerância de 1 segundo
        localStorage.setItem('bunkersCountdown', (now - (1800 - countdown) * 1000).toString());
      }
    }
  }, [countdown]);

  return {
    countdown,
    resetCountdown,
    formatCountdown
  };
}; 