import React, { useState, useEffect, useCallback } from 'react';
import { motion } from 'framer-motion';
import { Trophy, TrendingUp } from 'lucide-react';
import { FameService } from '../services/fameService';
import { FamePlayer } from '../types/fame';
import { useBunkersCountdown } from '../hooks/useBunkersCountdown';
import { useLanguage } from '../contexts/LanguageContext';

interface FameTop3CardProps {
  className?: string;
}

const FameTop3Card: React.FC<FameTop3CardProps> = ({ className = '' }) => {
  const { t, language } = useLanguage();
  const [top3Players, setTop3Players] = useState<FamePlayer[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [lastUpdate, setLastUpdate] = useState<string>('');
  const { countdown, resetCountdown } = useBunkersCountdown();
  const hasLoadedRef = React.useRef(false);

  const fetchTop3Data = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const response = await FameService.getFamePoints();
      
      if (response.success && response.data) {
        // Ordena por pontuação (maior para menor) e pega os top 3
        const sortedPlayers = response.data.sort((a, b) => b.totalFame - a.totalFame);
        const top3 = sortedPlayers.slice(0, 3);
        
        setTop3Players(top3);
        setLastUpdate(new Date().toLocaleTimeString(language));
        
        // Salva no localStorage
        localStorage.setItem('fameTop3Data', JSON.stringify(top3));
        localStorage.setItem('fameTop3LastUpdate', new Date().toLocaleTimeString(language));
        
        resetCountdown(); // Reset countdown using global hook
      } else {
        setError('Erro ao carregar dados de fama');
      }
    } catch (err) {
      setError('Erro ao conectar com o servidor');
      console.error('Erro ao buscar dados de fama:', err);
    } finally {
      setLoading(false);
    }
  }, [resetCountdown]);

  // Carrega dados apenas se não há dados salvos
  useEffect(() => {
    const saved = localStorage.getItem('fameTop3Data');
    const savedUpdate = localStorage.getItem('fameTop3LastUpdate');
    
    if (saved && !hasLoadedRef.current) {
      try {
        const parsedData = JSON.parse(saved);
        setTop3Players(parsedData);
        setLastUpdate(savedUpdate || '');
        hasLoadedRef.current = true;
        setLoading(false);
      } catch {
        hasLoadedRef.current = true;
        fetchTop3Data();
      }
    } else if (!saved && !hasLoadedRef.current) {
      hasLoadedRef.current = true;
      fetchTop3Data();
    }
  }, [fetchTop3Data]);

  // Trigger update when countdown reaches 0
  useEffect(() => {
    if (countdown <= 1 && hasLoadedRef.current) {
      const updateData = async () => {
        try {
          setLoading(true);
          setError(null);
          const response = await FameService.getFamePoints();
          
          if (response.success && response.data) {
            const sortedPlayers = response.data.sort((a, b) => b.totalFame - a.totalFame);
            const top3 = sortedPlayers.slice(0, 3);
            
            setTop3Players(top3);
            setLastUpdate(new Date().toLocaleTimeString(language));
            
            localStorage.setItem('fameTop3Data', JSON.stringify(top3));
            localStorage.setItem('fameTop3LastUpdate', new Date().toLocaleTimeString(language));
            
            resetCountdown();
          } else {
            setError('Erro ao carregar dados de fama');
          }
        } catch (err) {
          setError('Erro ao conectar com o servidor');
          console.error('Erro ao buscar dados de fama:', err);
        } finally {
          setLoading(false);
        }
      };
      updateData();
    }
  }, [countdown, resetCountdown]);

  const getMaxFame = () => {
    if (top3Players.length === 0) return 1000;
    return Math.max(...top3Players.map(p => p.totalFame));
  };

  const getProgressPercentage = (fame: number) => {
    const maxFame = getMaxFame();
    return (fame / maxFame) * 100;
  };

  if (loading) {
    return (
      <div className={`bg-scum-dark/60 rounded-lg border border-scum-accent/20 shadow-lg p-6 ${className}`}>
        <div className="flex items-center justify-center py-12">
          <div className="w-8 h-8 border-2 border-scum-accent border-t-transparent rounded-full animate-spin"></div>
          <span className="ml-3 text-scum-light">{t('loading_top3')}</span>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className={`bg-scum-dark/60 rounded-lg border border-scum-accent/20 shadow-lg p-6 ${className}`}>
        <div className="text-center py-12">
          <div className="text-red-400 text-4xl mb-4">⚠️</div>
          <h3 className="text-lg font-bold text-scum-light mb-2">{t('error_loading_data')}</h3>
          <p className="text-scum-muted">{error}</p>
          <button
            onClick={fetchTop3Data}
            className="mt-4 px-4 py-2 bg-scum-accent/20 hover:bg-scum-accent/30 border border-scum-accent/50 rounded text-scum-accent transition-colors"
          >
            {t('try_again')}
          </button>
        </div>
      </div>
    );
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      className={`bg-scum-dark/60 rounded-lg border border-scum-accent/20 shadow-lg p-6 ${className}`}
    >
      {/* Header */}
      <div className="flex flex-col items-center justify-center mb-3 border-b border-scum-accent/30 pb-2 gap-1">
        <div className="flex flex-col sm:flex-row items-center justify-center gap-2 w-full">
                      <h3 className="text-base font-bold text-scum-light flex items-center justify-center">
              <span className="text-xl mr-2">🏆</span>
              {t('top3_fame')}
            </h3>
        </div>
      </div>

      {/* Top 3 Players */}
      <div className="space-y-2">
        {top3Players.length === 0 ? (
          <div className="text-center py-6 text-scum-muted">
            <Trophy size={32} className="mx-auto mb-2 text-scum-muted/50" />
            <p className="text-xs">{t('no_players_found')}</p>
          </div>
        ) : (
          top3Players.map((player, index) => {
            const level = FameService.getFameLevel(player.totalFame);
            const levelColor = FameService.getFameLevelColor(level);
            const progressPercentage = getProgressPercentage(player.totalFame);
            const isTop3 = index < 3;
            
            return (
              <motion.div
                key={player.steamId}
                initial={{ opacity: 0, x: -20 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: index * 0.1 }}
                className={`p-2 rounded-lg border ${
                  index === 0 ? 'bg-yellow-400/10 border-yellow-400/30' :
                  index === 1 ? 'bg-gray-400/10 border-gray-400/30' :
                  'bg-orange-400/10 border-orange-400/30'
                } ${isTop3 ? 'shadow-md' : ''}`}
              >
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2 flex-1">
                    {/* Posição e Medalha */}
                    <div className="flex items-center gap-1.5 min-w-[50px]">
                      <span className="text-sm">{FameService.getMedalIcon(index + 1)}</span>
                      <span className={`font-bold text-xs ${
                        index === 0 ? 'text-yellow-400' :
                        index === 1 ? 'text-gray-400' :
                        'text-orange-400'
                      }`}>
                        #{index + 1}
                      </span>
                    </div>

                    {/* Nome do jogador */}
                    <div className="flex-1">
                      <h4 className="font-bold text-scum-light text-xs">{player.playerName}</h4>
                      <p className="text-xs text-scum-muted font-mono">{player.steamId}</p>
                    </div>

                    {/* Pontos de fama */}
                    <div className="text-right min-w-[80px]">
                      <div className={`text-xs font-bold ${levelColor}`}>
                        {FameService.formatFamePoints(player.totalFame)}
                      </div>
                      <div className="text-xs text-scum-muted font-medium">pts</div>
                    </div>
                  </div>

                  {/* Barra de progresso */}
                  <div className="ml-2 w-16">
                    <div className="w-full bg-scum-dark/60 rounded-full h-1">
                      <motion.div
                        className={`h-1 rounded-full ${
                          level === 'high' ? 'bg-green-400' :
                          level === 'medium' ? 'bg-yellow-400' : 'bg-red-400'
                        }`}
                        initial={{ width: 0 }}
                        animate={{ width: `${progressPercentage}%` }}
                        transition={{ duration: 1, delay: index * 0.2 }}
                      />
                    </div>
                    <div className="text-xs text-scum-muted mt-0.5 text-center font-medium">
                      {progressPercentage.toFixed(0)}%
                    </div>
                  </div>
                </div>

                {/* Última atualização */}
                <div className="mt-1 text-xs text-scum-muted font-medium">
                  Atualizado: {FameService.formatTimestamp(player.timestamp)}
                </div>
              </motion.div>
            );
          })
        )}
      </div>

      {/* Last Update */}
      {lastUpdate && (
        <div className="text-xs text-scum-muted text-center pt-2 border-t border-scum-accent/30 font-mono">
          <span className="text-scum-accent font-semibold">ÚLTIMA ATUALIZAÇÃO:</span> {lastUpdate}
        </div>
      )}

      {/* Manual Update Button */}
      <div className="mt-3 flex justify-center">
        <button
          onClick={fetchTop3Data}
          className="px-3 py-1.5 bg-scum-accent/10 hover:bg-scum-accent/20 border border-scum-accent/30 rounded text-scum-accent transition-colors text-xs flex items-center gap-1.5"
        >
          <TrendingUp size={12} />
          Atualizar
        </button>
      </div>
    </motion.div>
  );
};

export default FameTop3Card; 