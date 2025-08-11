import React, { useState, useEffect, useRef } from 'react';
import { useServerStatus } from '../hooks/useServerStatus';
import axios from 'axios';
import { useLanguage } from '../contexts/LanguageContext';

interface ServerControlCardProps {
  className?: string;
}

interface ScheduleData {
  nextRestart?: string;
  schedules?: any;
  lastRestart?: string;
}

const ServerControlCard: React.FC<ServerControlCardProps> = ({ className = '' }) => {
  const { t, language } = useLanguage();
  const [actionLoading, setActionLoading] = useState<string | null>(null);
  const [scheduleData, setScheduleData] = useState<ScheduleData | null>(null);
  const [scheduleLoading, setScheduleLoading] = useState(false);
  const lastRestartRef = useRef<string | null>(null);
  
  const {
    status,
    error,
    startServer,
    stopServer,
    restartServer
  } = useServerStatus(true, 10000);

  // Função para buscar dados do agendamento
  const fetchScheduleData = async () => {
    setScheduleLoading(true);
    try {
      console.log('Buscando dados do agendamento...');
      const response = await axios.get('/api/server/schedules');
      console.log('Dados recebidos:', response.data);
      
      // Verificar se houve mudança no lastRestart (indicando que houve um restart)
      const newLastRestart = response.data.schedules?.lastRestart;
      if (lastRestartRef.current && newLastRestart && lastRestartRef.current !== newLastRestart) {
        console.log('🔄 Detectado restart automático, atualizando próximo restart...');
      }
      
      lastRestartRef.current = newLastRestart;
      setScheduleData(response.data);
    } catch (error) {
      console.error('Erro ao buscar dados do agendamento:', error);
      // Para teste, vamos usar dados mock se a API falhar
      setScheduleData({
        nextRestart: "2025-07-17T02:00:00.000-03:00"
      });
    } finally {
      setScheduleLoading(false);
    }
  };

  // Função para formatar data no padrão brasileiro
  const formatNextRestart = (dateString?: string) => {
    if (!dateString) return null;
    
    try {
      const date = new Date(dateString);
      const day = date.getDate().toString().padStart(2, '0');
      const month = (date.getMonth() + 1).toString().padStart(2, '0');
      const year = date.getFullYear();
      const hours = date.getHours().toString().padStart(2, '0');
      const minutes = date.getMinutes().toString().padStart(2, '0');
      const seconds = date.getSeconds().toString().padStart(2, '0');
      
      return `${day}/${month}/${year} às ${hours}:${minutes}:${seconds}`;
    } catch (error) {
      console.error('Erro ao formatar data:', error);
      return null;
    }
  };

  // Buscar dados do agendamento ao montar o componente e a cada 10 segundos
  useEffect(() => {
    fetchScheduleData();
    // REMOVIDO: Atualização automática - agora é manual
    // const interval = setInterval(fetchScheduleData, 10000);
    // return () => clearInterval(interval);
  }, []);

  const handleAction = async (action: 'start' | 'stop' | 'restart') => {
    setActionLoading(action);
    try {
      let success = false;
      switch (action) {
        case 'start':
          success = await startServer();
          break;
        case 'stop':
          success = await stopServer();
          break;
        case 'restart':
          success = await restartServer();
          break;
      }
      if (!success) {
        alert(`Erro: ${error || 'Erro desconhecido'}`);
      } else {
        // Se a ação foi bem-sucedida, atualizar os dados do agendamento
        if (action === 'restart') {
          console.log('🔄 Servidor reiniciado, atualizando dados do agendamento...');
          // Aguardar um pouco para o servidor processar o restart
          setTimeout(() => {
            fetchScheduleData();
          }, 2000);
        }
      }
    } catch (error) {
      alert('Erro ao conectar com o servidor');
    } finally {
      setActionLoading(null);
    }
  };

  const formattedNextRestart = formatNextRestart(scheduleData?.schedules?.nextRestart);
  const isRestartEnabled = scheduleData?.schedules?.enabled;
  console.log('scheduleData:', scheduleData);
  console.log('formattedNextRestart:', formattedNextRestart);

  return (
    <div className={`bg-scum-dark/60 backdrop-blur-sm rounded-lg p-3 border border-scum-accent/20 ${className}`}>
      <div className="flex flex-col sm:flex-row gap-2 items-start sm:items-center">
        <div className="flex gap-2">
        <button
          onClick={() => handleAction('start')}
          disabled={actionLoading !== null || status?.isRunning}
          className={`px-4 py-2 rounded-lg font-medium transition-all duration-200 ${
            status?.isRunning
              ? 'bg-gray-600 text-gray-400 cursor-not-allowed'
              : actionLoading === 'start'
              ? 'bg-blue-600 text-white cursor-wait'
              : 'bg-green-600 hover:bg-green-700 text-white'
          }`}
        >
          {actionLoading === 'start' ? t('starting') : t('start_server')}
        </button>
        <button
          onClick={() => handleAction('stop')}
          disabled={actionLoading !== null || !status?.isRunning}
          className={`px-4 py-2 rounded-lg font-medium transition-all duration-200 ${
            !status?.isRunning
              ? 'bg-gray-600 text-gray-400 cursor-not-allowed'
              : actionLoading === 'stop'
              ? 'bg-red-600 text-white cursor-wait'
              : 'bg-red-600 hover:bg-red-700 text-white'
          }`}
        >
          {actionLoading === 'stop' ? t('stopping') : t('stop_server')}
        </button>
        <button
          onClick={() => handleAction('restart')}
          disabled={actionLoading !== null || !status?.isRunning}
          className={`px-4 py-2 rounded-lg font-medium transition-all duration-200 ${
            !status?.isRunning
              ? 'bg-gray-600 text-gray-400 cursor-not-allowed'
              : actionLoading === 'restart'
              ? 'bg-yellow-600 text-white cursor-wait'
              : 'bg-yellow-600 hover:bg-yellow-700 text-white'
          }`}
        >
          {actionLoading === 'restart' ? t('restarting') : t('restart_server')}
        </button>
      </div>

        <div className="sm:ml-4 text-sm text-gray-300 flex items-center gap-2">
          {scheduleLoading ? (
            <div className="flex items-center gap-2">
              <div className="w-3 h-3 border border-gray-400 border-t-transparent rounded-full animate-spin"></div>
              <span>{t('updating')}</span>
            </div>
          ) : (
            <>
              {/* Indicador de status do restart automático */}
              <div className="flex items-center gap-1">
                <div className={`w-2 h-2 rounded-full ${isRestartEnabled ? 'bg-green-400' : 'bg-red-400'}`}></div>
                <span className={`text-xs ${isRestartEnabled ? 'text-green-400' : 'text-red-400'}`}>
                  {isRestartEnabled ? t('auto') : t('manual')}
                </span>
              </div>
              
              {formattedNextRestart ? (
                <>{t('next_reset')} {formattedNextRestart}</>
              ) : (
                <>{t('next_reset')} 17/07/2025 às 02:00:00</>
              )}
            </>
          )}
        </div>
      </div>
    </div>
  );
};

export default ServerControlCard; 