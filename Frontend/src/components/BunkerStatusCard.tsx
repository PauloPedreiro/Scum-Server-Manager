import React, { useState, useEffect, useRef } from 'react';
import { motion } from 'framer-motion';
import { RefreshCw } from 'lucide-react';
import { useBunkersCountdown } from '../hooks/useBunkersCountdown';
import { useLanguage } from '../contexts/LanguageContext';
import { toast } from 'react-toastify';

interface BunkerCoordinates {
  x: number;
  y: number;
  z: number;
}

interface Bunker {
  name: string;
  status: 'active' | 'locked';
  activated?: string;
  nextActivation?: string;
  coordinates: BunkerCoordinates | null;
  lastUpdate: string;
  activationTime?: string;
  activationMethod?: string;
}

interface BunkerData {
  active: Bunker[];
  locked: Bunker[];
  lastUpdate: string;
}

interface BunkerStatusCardProps {
  hideSteamIds?: boolean;
  onManualUpdate?: () => void;
}

const BunkerStatusCard: React.FC<BunkerStatusCardProps> = ({ hideSteamIds = false, onManualUpdate }) => {
  const { t, language } = useLanguage();
  const [bunkerData, setBunkerData] = useState<BunkerData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [lastUpdate, setLastUpdate] = useState<string | null>(null);
  const { countdown, resetCountdown } = useBunkersCountdown();
  const hasLoadedRef = useRef(false);
  const [manualUpdateLoading, setManualUpdateLoading] = useState(false);

  const fetchBunkerStatus = async () => {
    try {
      setLoading(true);
      const response = await fetch('/api/bunkers/status');
      const data = await response.json();

      if (data.success) {
        setBunkerData(data.data);
        setLastUpdate(new Date().toLocaleTimeString(language));
        setError(null);
        resetCountdown(); // Reset countdown using global hook
        hasLoadedRef.current = true;
      } else {
        setError(data.message || t('error_loading_bunkers'));
      }
    } catch (err) {
      setError(t('connection_error'));
      console.error('Erro ao buscar status dos bunkers:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleManualUpdate = async () => {
    if (manualUpdateLoading) return;
    
    setManualUpdateLoading(true);
    try {
      await fetchBunkerStatus();
      toast.success(t('updated_successfully'));
      if (onManualUpdate) {
        onManualUpdate();
      }
    } catch (err) {
      toast.error(t('update_error'));
    } finally {
      setManualUpdateLoading(false);
    }
  };

  useEffect(() => {
    fetchBunkerStatus();
  }, []);

  // Trigger update when countdown reaches 0
  useEffect(() => {
    if (countdown <= 1 && hasLoadedRef.current) {
      fetchBunkerStatus();
    }
  }, [countdown]);

  const formatCoordinates = (coordinates: BunkerCoordinates | null) => {
    if (!coordinates) return 'N/A';
    return `X: ${coordinates.x.toFixed(0)}, Y: ${coordinates.y.toFixed(0)}, Z: ${coordinates.z.toFixed(0)}`;
  };

  const getStatusIcon = (status: string) => {
    return status === 'active' ? '🟢' : '🔴';
  };

  const getStatusText = (status: string) => {
    return status === 'active' ? t('active') : t('blocked');
  };

  if (loading && !bunkerData) {
    return (
      <div className="bg-scum-dark/60 backdrop-blur-sm rounded-lg p-3 border border-scum-accent/20">
        <div className="flex items-center justify-center">
          <div className="w-4 h-4 border-2 border-scum-accent border-t-transparent rounded-full animate-spin mr-2"></div>
          <span className="text-sm text-gray-300">{t('loading_bunkers')}</span>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-scum-dark/60 backdrop-blur-sm rounded-lg p-3 border border-scum-accent/20">
        <div className="text-scum-danger text-sm text-center">{error}</div>
      </div>
    );
  }

  if (!bunkerData) {
    return (
      <div className="bg-scum-dark/60 backdrop-blur-sm rounded-lg p-3 border border-scum-accent/20">
        <div className="text-scum-muted text-sm text-center">{t('no_data_available')}</div>
      </div>
    );
  }

  const activeBunkers = bunkerData.active;
  const activeCount = activeBunkers.length;

  return (
    <div className="bg-scum-dark/60 backdrop-blur-sm rounded-lg p-3 border border-scum-accent/20">
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <h3 className="text-sm font-semibold text-scum-light">{t('bunker_status')}</h3>
          {lastUpdate && (
            <span className="text-xs text-scum-muted">
              {t('last_update')}: {lastUpdate}
            </span>
          )}
        </div>
        
        <motion.button
          whileHover={{ scale: 1.05 }}
          whileTap={{ scale: 0.95 }}
          onClick={handleManualUpdate}
          disabled={manualUpdateLoading}
          className={`
            flex items-center gap-1 px-2 py-1 rounded text-xs transition-all duration-200
            ${manualUpdateLoading 
              ? 'bg-scum-gray/30 text-scum-muted cursor-not-allowed' 
              : 'bg-scum-accent/20 text-scum-accent hover:bg-scum-accent/30'
            }
          `}
          title={manualUpdateLoading ? 'Atualizando...' : 'Atualizar Bunkers'}
        >
          <div className={`${manualUpdateLoading ? 'animate-spin' : ''}`}>
            <RefreshCw size={12} />
          </div>
          <span className="text-xs">Atualizar</span>
        </motion.button>
      </div>

      <div className="flex gap-2 items-center">
        <div className="flex gap-2">
          {activeBunkers.map((bunker) => (
            <div key={bunker.name} className="px-3 py-2 bg-green-400/10 border border-green-400/30 rounded-lg text-xs font-mono">
              <span className="text-green-400 font-bold">🛡️ {bunker.name}</span>
            </div>
          ))}
        </div>
        
        {activeCount === 0 && (
          <div className="text-sm text-gray-400">
            {t('no_active_bunkers')}
          </div>
        )}
        
        {activeCount > 0 && (
          <div className="ml-4 text-sm text-gray-300">
            {activeCount} {t('bunker')}{activeCount > 1 ? 's' : ''} {t('active')}
          </div>
        )}
      </div>
    </div>
  );
};

export default BunkerStatusCard; 