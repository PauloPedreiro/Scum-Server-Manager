import React, { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { Search, TrendingUp } from 'lucide-react';
import { FameService } from '../services/fameService';
import { FamePlayer, FameStats, FameFilters, FameLevel } from '../types/fame';
import { useLanguage } from '../contexts/LanguageContext';

interface FamePlayersListProps {
  className?: string;
  hideSteamIds?: boolean;
}

const FamePlayersList: React.FC<FamePlayersListProps> = ({ className = '', hideSteamIds = false }) => {
  const { t, language } = useLanguage();
  const [players, setPlayers] = useState<FamePlayer[]>([]);
  const [filteredPlayers, setFilteredPlayers] = useState<FamePlayer[]>([]);
  const [stats, setStats] = useState<FameStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [lastUpdate, setLastUpdate] = useState<Date | null>(null);
  const [filters, setFilters] = useState<FameFilters>({
    searchTerm: '',
    dateFilter: 'all',
    rankingFilter: 'all',
    levelFilter: 'all',
  });

  const fetchFameData = async () => {
    try {
      setLoading(true);
      setError(null);
      const response = await FameService.getFamePoints();
      
      if (response.success && response.data) {
        setPlayers(response.data);
        setFilteredPlayers(response.data);
        setStats(FameService.calculateStats(response.data));
        setLastUpdate(new Date());
      } else {
        setError(t('error_loading_fame'));
      }
    } catch (err) {
              setError(t('connection_error'));
      console.error('Erro ao buscar dados de fama:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchFameData();
    
    // REMOVIDO: Atualização automática - agora é manual
    // Atualiza automaticamente a cada 30 segundos
    // const interval = setInterval(fetchFameData, 30000);
    
    // return () => clearInterval(interval);
  }, []);

  // Aplica filtros
  useEffect(() => {
    let filtered = [...players];

    // Ordena por pontuação (maior para menor)
    filtered = filtered.sort((a, b) => b.totalFame - a.totalFame);

    // Filtro por busca
    if (filters.searchTerm) {
      filtered = filtered.filter(player =>
        player.playerName.toLowerCase().includes(filters.searchTerm.toLowerCase())
      );
    }

    // Filtro por ranking
    if (filters.rankingFilter !== 'all') {
      const limit = parseInt(filters.rankingFilter);
      filtered = filtered.slice(0, limit);
    }

    // Filtro por nível de fama
    if (filters.levelFilter !== 'all') {
      filtered = filtered.filter(player => {
        const level = FameService.getFameLevel(player.totalFame);
        return level === filters.levelFilter;
      });
    }

    setFilteredPlayers(filtered);
  }, [players, filters]);

  const handleFilterChange = (key: keyof FameFilters, value: string) => {
    setFilters(prev => ({ ...prev, [key]: value }));
  };

  const getMaxFame = () => {
    if (players.length === 0) return 1000;
    return Math.max(...players.map(p => p.totalFame));
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
          <span className="ml-3 text-scum-light">{t('loading_fame_data')}</span>
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
            onClick={fetchFameData}
            className="mt-4 px-4 py-2 bg-scum-accent/20 hover:bg-scum-accent/30 border border-scum-accent/50 rounded text-scum-accent transition-colors"
          >
            {t('try_again')}
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className={`space-y-3 ${className}`}>
      {/* Filtros */}
      <div className="bg-scum-dark/40 backdrop-blur-sm rounded-lg border border-scum-accent/20 p-3">
        <div className="grid grid-cols-1 md:grid-cols-4 gap-2">
          {/* Busca por nome */}
          <div className="relative">
            <Search className="absolute left-2 top-1/2 transform -translate-y-1/2 text-scum-muted" size={14} />
            <input
              type="text"
              placeholder={t('search_player')}
              value={filters.searchTerm}
              onChange={(e) => handleFilterChange('searchTerm', e.target.value)}
              className="w-full pl-8 pr-3 py-1.5 bg-scum-dark/60 text-scum-light placeholder-scum-muted border border-scum-accent/20 rounded focus:border-scum-accent/50 outline-none text-sm transition-colors"
            />
          </div>

          {/* Filtro por ranking */}
          <select
            value={filters.rankingFilter}
            onChange={(e) => handleFilterChange('rankingFilter', e.target.value)}
            className="px-3 py-1.5 bg-scum-dark/60 text-scum-light border border-scum-accent/20 rounded focus:border-scum-accent/50 outline-none text-sm transition-colors"
          >
            <option value="all">{t('all_players')}</option>
            <option value="3">{t('top3')}</option>
            <option value="5">{t('top5')}</option>
            <option value="10">{t('top10')}</option>
          </select>

          {/* Filtro por nível */}
          <select
            value={filters.levelFilter}
            onChange={(e) => handleFilterChange('levelFilter', e.target.value)}
            className="px-3 py-1.5 bg-scum-dark/60 text-scum-light border border-scum-accent/20 rounded focus:border-scum-accent/50 outline-none text-sm transition-colors"
          >
            <option value="all">{t('all_levels')}</option>
            <option value="high">{t('high_fame')} (800+)</option>
            <option value="medium">{t('medium_fame')} (400-799)</option>
            <option value="low">{t('low_fame')} (0-399)</option>
          </select>

          {/* Botão de refresh */}
          <button
            onClick={fetchFameData}
            className="px-3 py-1.5 bg-scum-accent/10 hover:bg-scum-accent/20 border border-scum-accent/30 rounded text-scum-accent transition-colors text-sm flex items-center justify-center"
          >
            <TrendingUp size={14} className="mr-1.5" />
            {t('update')}
          </button>
        </div>
      </div>

      {/* Lista de Jogadores */}
      <div className="bg-scum-dark/40 backdrop-blur-sm rounded-lg border border-scum-accent/20 overflow-hidden">
        <div className="p-3 border-b border-scum-accent/20 bg-scum-dark/60">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-semibold text-scum-light">
              {t('fame_ranking')} ({filteredPlayers.length} {t('players')})
            </h3>
            {lastUpdate && (
              <div className="text-xs text-scum-muted">
                {t('last_update')}: {lastUpdate.toLocaleTimeString(language)}
              </div>
            )}
          </div>
        </div>
        
        <div className="max-h-[70vh] overflow-y-auto">
          {filteredPlayers.length === 0 ? (
            <div className="text-center py-6 text-scum-muted">
              Nenhum jogador encontrado com os filtros aplicados.
            </div>
          ) : (
            <div className="divide-y divide-scum-accent/10">
              {filteredPlayers.map((player, index) => {
                const level = FameService.getFameLevel(player.totalFame);
                const levelColor = FameService.getFameLevelColor(level);
                const progressPercentage = getProgressPercentage(player.totalFame);
                const isTop3 = index < 3;
                
                return (
                  <motion.div
                    key={player.steamId}
                    initial={{ opacity: 0, x: -20 }}
                    animate={{ opacity: 1, x: 0 }}
                    transition={{ delay: index * 0.05 }}
                    className={`p-3 hover:bg-scum-accent/5 transition-colors ${isTop3 ? 'bg-scum-accent/10' : ''}`}
                  >
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-3 flex-1">
                        {/* Posição e Medalha */}
                        <div className="flex items-center gap-1.5 min-w-[50px]">
                          <span className="text-sm">{FameService.getMedalIcon(index + 1)}</span>
                          <span className={`font-bold text-xs ${isTop3 ? 'text-scum-accent' : 'text-scum-muted'}`}>
                            #{index + 1}
                          </span>
                        </div>

                        {/* Nome do jogador */}
                        <div className="flex-1">
                          <h4 className="font-bold text-scum-light text-sm">{player.playerName}</h4>
                          {!hideSteamIds && <p className="text-xs text-scum-muted font-mono">{player.steamId}</p>}
                        </div>

                        {/* Pontos de fama */}
                        <div className="text-right min-w-[100px]">
                          <div className={`text-sm font-bold ${levelColor}`}>
                            {FameService.formatFamePoints(player.totalFame)}
                          </div>
                          <div className="text-xs text-scum-muted font-medium">pts</div>
                        </div>
                      </div>

                      {/* Barra de progresso */}
                      <div className="ml-3 w-24">
                        <div className="w-full bg-scum-dark/60 rounded-full h-1.5">
                          <motion.div
                            className={`h-1.5 rounded-full ${
                              level === 'high' ? 'bg-green-400' :
                              level === 'medium' ? 'bg-yellow-400' : 'bg-red-400'
                            }`}
                            initial={{ width: 0 }}
                            animate={{ width: `${progressPercentage}%` }}
                            transition={{ duration: 1, delay: index * 0.1 }}
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
              })}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default FamePlayersList; 