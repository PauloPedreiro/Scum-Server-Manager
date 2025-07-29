import React, { useState, useEffect, useCallback, useRef } from 'react';
import { motion } from 'framer-motion';
import { BunkerService, BunkersData, ActiveBunker, LockedBunker } from '../services/bunkerService';
import { useBunkersCountdown } from '../hooks/useBunkersCountdown';

interface BunkersCardProps {
  className?: string;
}

const BunkersCard: React.FC<BunkersCardProps> = ({ className = '' }) => {
  const [bunkersData, setBunkersData] = useState<BunkersData | null>(() => {
    // Tenta carregar dados do localStorage
    const saved = localStorage.getItem('bunkersData');
    if (saved) {
      try {
        return JSON.parse(saved);
      } catch {
        return null;
      }
    }
    return null;
  });
  const [loading, setLoading] = useState(() => {
    // Só mostra loading se não há dados salvos
    const saved = localStorage.getItem('bunkersData');
    return !saved;
  });
  const [error, setError] = useState<string | null>(null);
  const [lastUpdate, setLastUpdate] = useState<string>(() => {
    const saved = localStorage.getItem('bunkersLastUpdate');
    return saved || '';
  });
  const { countdown, resetCountdown, formatCountdown } = useBunkersCountdown();
  const hasLoadedRef = useRef(false);

  const fetchBunkersData = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const response = await BunkerService.getBunkersStatus();
      if (response.success && response.data) {
        setBunkersData(response.data);
        setLastUpdate(response.data.lastUpdate);
        // Salva no localStorage
        localStorage.setItem('bunkersData', JSON.stringify(response.data));
        localStorage.setItem('bunkersLastUpdate', response.data.lastUpdate);
        resetCountdown(); // Reset countdown using global hook
      } else {
        setError('Erro ao carregar dados dos bunkers');
      }
    } catch (err) {
      setError('Erro ao conectar com o servidor');
      console.error('Erro ao buscar bunkers:', err);
    } finally {
      setLoading(false);
    }
  }, [resetCountdown]);

  // Carrega dados apenas se não há dados salvos
  useEffect(() => {
    if (!bunkersData && !hasLoadedRef.current) {
      hasLoadedRef.current = true;
      fetchBunkersData();
    } else if (bunkersData) {
      // Se já tem dados, não precisa carregar
      hasLoadedRef.current = true;
      setLoading(false);
    }
  }, []);

  // Trigger update when countdown reaches 0
  useEffect(() => {
    if (countdown <= 1 && hasLoadedRef.current) {
      // Chama diretamente sem usar useCallback para evitar loops
      const updateData = async () => {
        try {
          setLoading(true);
          setError(null);
          const response = await BunkerService.getBunkersStatus();
          if (response.success && response.data) {
            setBunkersData(response.data);
            setLastUpdate(response.data.lastUpdate);
            localStorage.setItem('bunkersData', JSON.stringify(response.data));
            localStorage.setItem('bunkersLastUpdate', response.data.lastUpdate);
            resetCountdown();
          } else {
            setError('Erro ao carregar dados dos bunkers');
          }
        } catch (err) {
          setError('Erro ao conectar com o servidor');
          console.error('Erro ao buscar bunkers:', err);
        } finally {
          setLoading(false);
        }
      };
      updateData();
    }
  }, [countdown, resetCountdown]);

  const formatTime = (timeStr: string) => {
    return timeStr.replace('h', 'h ').replace('m', 'm ').replace('s', 's');
  };

  const formatCoordinates = (coords: { x: number; y: number; z: number } | null) => {
    if (!coords) return 'N/A';
    return `X: ${Math.round(coords.x)}, Y: ${Math.round(coords.y)}, Z: ${Math.round(coords.z)}`;
  };

  if (loading) {
    return (
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className={`bg-scum-dark/60 backdrop-blur-sm rounded-lg p-3 border border-scum-accent/20 ${className}`}
      >
        <div className="flex items-center justify-center">
          <div className="w-4 h-4 border-2 border-scum-accent border-t-transparent rounded-full animate-spin mr-2"></div>
          <span className="text-sm text-gray-300">Carregando bunkers...</span>
        </div>
      </motion.div>
    );
  }

  if (error) {
    return (
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className={`bg-scum-dark/60 backdrop-blur-sm rounded-lg p-3 border border-scum-accent/20 ${className}`}
      >
        <div className="text-scum-danger text-sm text-center">{error}</div>
      </motion.div>
    );
  }

  if (!bunkersData) {
    return (
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className={`bg-scum-dark/60 backdrop-blur-sm rounded-lg p-3 border border-scum-accent/20 ${className}`}
      >
        <div className="text-scum-muted text-sm text-center">Nenhum dado disponível</div>
      </motion.div>
    );
  }

  // Função para deduplicar bunkers por nome, mantendo apenas o mais recente
  const deduplicateBunkers = (bunkers: ActiveBunker[] | LockedBunker[]) => {
    const uniqueBunkers = new Map();
    
    bunkers.forEach(bunker => {
      const existing = uniqueBunkers.get(bunker.name);
      if (!existing) {
        uniqueBunkers.set(bunker.name, bunker);
      } else {
        // Prioriza bunkers com coordenadas (mais completos)
        const existingHasCoords = 'coordinates' in existing && existing.coordinates;
        const currentHasCoords = 'coordinates' in bunker && bunker.coordinates;
        
        if (currentHasCoords && !existingHasCoords) {
          // Atual tem coordenadas, existente não tem - substitui
          uniqueBunkers.set(bunker.name, bunker);
        } else if (!currentHasCoords && existingHasCoords) {
          // Existente tem coordenadas, atual não tem - mantém existente
          // Não faz nada
        } else {
          // Ambos têm ou ambos não têm coordenadas - compara tempos
          const existingTime = 'activated' in existing ? existing.activated : existing.nextActivation;
          const currentTime = 'activated' in bunker ? bunker.activated : bunker.nextActivation;
          
          // Para bunkers ativos: tempo menor = mais recente
          // Para bunkers bloqueados: tempo maior = mais recente (mais tempo restante)
          const isActive = 'activated' in bunker;
          
          if (isActive) {
            // Bunker ativo: mantém o com menor tempo (mais recente)
            if (currentTime < existingTime) {
              uniqueBunkers.set(bunker.name, bunker);
            }
          } else {
            // Bunker bloqueado: mantém o com maior tempo (mais tempo restante)
            if (currentTime > existingTime) {
              uniqueBunkers.set(bunker.name, bunker);
            }
          }
        }
      }
    });
    
    return Array.from(uniqueBunkers.values());
  };

  const uniqueActiveBunkers = deduplicateBunkers(bunkersData.active) as ActiveBunker[];
  const activeCount = uniqueActiveBunkers.length;

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      className={`bg-scum-dark/60 backdrop-blur-sm rounded-lg p-3 border border-scum-accent/20 ${className}`}
    >
      <div className="flex gap-2 items-center">
        <div className="flex gap-2">
          {uniqueActiveBunkers.map((bunker, index) => (
            <div key={`${bunker.name}-${index}`} className="px-3 py-2 bg-green-400/10 border border-green-400/30 rounded-lg text-xs font-mono">
              <span className="text-green-400 font-bold">🛡️ {bunker.name}</span>
            </div>
          ))}
        </div>
        
        {activeCount === 0 && (
          <div className="text-sm text-gray-400">
            Nenhum bunker ativo
          </div>
        )}
        
        {activeCount > 0 && (
          <div className="ml-4 text-sm text-gray-300">
            {activeCount} bunker{activeCount > 1 ? 's' : ''} ativo{activeCount > 1 ? 's' : ''}
          </div>
        )}
      </div>
    </motion.div>
  );
};

export default BunkersCard; 