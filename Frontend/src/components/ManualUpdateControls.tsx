import React, { useState } from 'react';
import { motion } from 'framer-motion';
import { RefreshCw, Users, MessageSquare, Car, Trophy, Shield, FileText } from 'lucide-react';
import { useLanguage } from '../contexts/LanguageContext';
import { toast } from 'react-toastify';

interface ManualUpdateControlsProps {
  onPlayersUpdate?: () => void;
  onChatUpdate?: () => void;
  onVehiclesUpdate?: () => void;
  onFameUpdate?: () => void;
  onBunkersUpdate?: () => void;
  onAdminLogUpdate?: () => void;
}

interface UpdateButtonProps {
  icon: React.ReactNode;
  label: string;
  onClick: () => Promise<void>;
  loading: boolean;
}

const UpdateButton: React.FC<UpdateButtonProps> = ({ icon, label, onClick, loading }) => {
  return (
    <motion.button
      whileHover={{ scale: 1.02 }}
      whileTap={{ scale: 0.98 }}
      onClick={onClick}
      disabled={loading}
      className={`
        flex items-center gap-2 px-3 py-2 rounded-lg border transition-all duration-200 text-sm
        ${loading 
          ? 'bg-scum-gray/30 border-scum-gray/50 text-scum-muted cursor-not-allowed' 
          : 'bg-scum-secondary/30 border-scum-accent/30 text-scum-light hover:bg-scum-secondary/50 hover:border-scum-accent/50'
        }
      `}
      title={loading ? 'Atualizando...' : `Atualizar ${label}`}
    >
      <div className={`${loading ? 'animate-spin' : ''}`}>
        {loading ? <RefreshCw size={14} className="sm:w-4 sm:h-4" /> : icon}
      </div>
      <span className="text-xs sm:text-sm font-medium">{label}</span>
    </motion.button>
  );
};

const ManualUpdateControls: React.FC<ManualUpdateControlsProps> = ({
  onPlayersUpdate,
  onChatUpdate,
  onVehiclesUpdate,
  onFameUpdate,
  onBunkersUpdate,
  onAdminLogUpdate
}) => {
  const { t } = useLanguage();
  const [loadingStates, setLoadingStates] = useState({
    players: false,
    chat: false,
    vehicles: false,
    fame: false,
    bunkers: false,
    adminLog: false
  });

  const handleUpdate = async (
    type: keyof typeof loadingStates,
    updateFunction: (() => void) | undefined,
    apiEndpoint: string
  ) => {
    if (loadingStates[type]) return;

    setLoadingStates(prev => ({ ...prev, [type]: true }));

    try {
      // Simular chamada da API
      await new Promise(resolve => setTimeout(resolve, 1000));
      
      // Chamar função de atualização se fornecida
      if (updateFunction) {
        updateFunction();
      }

      toast.success(`${t('updated_successfully')} ${t(type)}`);
    } catch (error) {
      toast.error(`${t('update_error')} ${t(type)}`);
      console.error(`Erro ao atualizar ${type}:`, error);
    } finally {
      setLoadingStates(prev => ({ ...prev, [type]: false }));
    }
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      className="bg-scum-card/50 backdrop-blur-sm border border-scum-accent/20 rounded-lg p-4 mb-6"
    >
      <div className="flex items-center gap-2 mb-4">
        <RefreshCw size={18} className="sm:w-5 sm:h-5 text-scum-accent" />
        <h3 className="text-base sm:text-lg font-semibold text-scum-light">
          {t('manual_updates')}
        </h3>
      </div>
      
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-2 sm:gap-3">
        <UpdateButton
          icon={<Users size={14} className="sm:w-4 sm:h-4" />}
          label={t('players')}
          onClick={() => handleUpdate('players', onPlayersUpdate, '/api/players/painelplayers')}
          loading={loadingStates.players}
        />
        
        <UpdateButton
          icon={<MessageSquare size={14} className="sm:w-4 sm:h-4" />}
          label={t('chat')}
          onClick={() => handleUpdate('chat', onChatUpdate, '/api/chat_in_game')}
          loading={loadingStates.chat}
        />
        
        <UpdateButton
          icon={<Car size={14} className="sm:w-4 sm:h-4" />}
          label={t('vehicles')}
          onClick={() => handleUpdate('vehicles', onVehiclesUpdate, '/api/LogVeiculos')}
          loading={loadingStates.vehicles}
        />
        
        <UpdateButton
          icon={<Trophy size={14} className="sm:w-4 sm:h-4" />}
          label={t('fama')}
          onClick={() => handleUpdate('fame', onFameUpdate, '/api/famepoints')}
          loading={loadingStates.fame}
        />
        
        <UpdateButton
          icon={<Shield size={14} className="sm:w-4 sm:h-4" />}
          label={t('bunkers')}
          onClick={() => handleUpdate('bunkers', onBunkersUpdate, '/api/bunkers/status')}
          loading={loadingStates.bunkers}
        />
        
        <UpdateButton
          icon={<FileText size={14} className="sm:w-4 sm:h-4" />}
          label={t('admin_log')}
          onClick={() => handleUpdate('adminLog', onAdminLogUpdate, '/api/adminlog')}
          loading={loadingStates.adminLog}
        />
      </div>
    </motion.div>
  );
};

export default ManualUpdateControls; 