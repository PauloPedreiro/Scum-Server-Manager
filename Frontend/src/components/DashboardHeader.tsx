import React, { useState } from 'react';
import { motion } from 'framer-motion';
import { LogOut, Shield, Wifi, FileText, Lock } from 'lucide-react';
import { useAuth } from '../hooks/useAuth';
// REMOVIDO: Contador de bunkers - agora é manual
// import { useBunkersCountdown } from '../hooks/useBunkersCountdown';
import LanguageToggle from './LanguageToggle';
import { useLanguage } from '../contexts/LanguageContext';
import { useNavigate } from 'react-router-dom';
import ChangePasswordModal from './ChangePasswordModal';

interface DashboardHeaderProps {
  serverStatus: 'online' | 'offline' | 'warning';
  playerCount: number;
  maxPlayers: number;
  vehicleLogCountdown?: number;
}

const DashboardHeader: React.FC<DashboardHeaderProps> = ({ 
  serverStatus, 
  playerCount, 
  maxPlayers,
  vehicleLogCountdown
}) => {
  const { logout, isAdmin } = useAuth();
  // REMOVIDO: Contador de bunkers - agora é manual
  // const { countdown: bunkersCountdown, formatCountdown } = useBunkersCountdown();
  const { t, language } = useLanguage();
  const navigate = useNavigate();
  const [showChangePassword, setShowChangePassword] = useState(false);

  const statusConfig = {
    online: { color: 'text-green-400', bgColor: 'bg-green-500', icon: Shield },
    offline: { color: 'text-red-400', bgColor: 'bg-red-500', icon: Shield },
    warning: { color: 'text-yellow-400', bgColor: 'bg-yellow-500', icon: Shield },
  };

  const config = statusConfig[serverStatus];
  const StatusIcon = config.icon;

  const handleLogout = async () => {
    await logout();
    navigate('/login');
  };

  return (
    <>
      <motion.header 
        initial={{ y: -20, opacity: 0 }}
        animate={{ y: 0, opacity: 1 }}
        className="flex flex-col gap-4 p-4 sm:p-6 scum-card backdrop-blur-md bg-scum-gray/40 border-b border-scum-primary"
      >
        {/* Primeira linha: Logo, Título e Status */}
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
          {/* Logo e Título */}
          <div className="flex items-center gap-3 sm:gap-4">
            <div className="relative">
              <motion.div
                whileHover={{ scale: 1.05 }}
                className="w-10 h-10 sm:w-12 sm:h-12 bg-scum-secondary rounded-lg flex items-center justify-center"
              >
                <Wifi size={20} className="sm:w-6 sm:h-6 text-scum-light" />
              </motion.div>
              <div className="absolute -top-1 -right-1 w-2 h-2 sm:w-3 sm:h-3 bg-scum-accent rounded-full animate-pulse"></div>
            </div>
            
            <div>
              <h1 className="text-lg sm:text-2xl font-bold text-scum-light military-text tracking-wider">
                SCUM SERVER MANAGER
              </h1>
              <p className="text-xs text-scum-muted digital-text">
                {t('survival_control_system')}
              </p>
            </div>
          </div>

          {/* Status do Servidor */}
          <div className="flex items-center gap-2 sm:gap-3">
            <div className={`w-2 h-2 sm:w-3 sm:h-3 ${config.bgColor} rounded-full animate-pulse`}></div>
            <StatusIcon size={16} className={`sm:w-5 sm:h-5 ${config.color}`} />
            <div className="text-right">
              <p className="text-xs sm:text-sm text-scum-light military-text">
                {t('server')} {serverStatus.toUpperCase()}
              </p>
              <p className="text-xs text-scum-muted digital-text">
                {playerCount}/{maxPlayers} {t('players')}
              </p>
              {/* REMOVIDO: Contador de bunkers - agora é manual */}
              {/* <span className="text-xs text-scum-accent digital-text block mt-1 select-none font-mono" title={t('next_bunker_check')}>
                🛡️ {formatCountdown(bunkersCountdown)}
              </span> */}
            </div>
          </div>
        </div>

        {/* Segunda linha: Botões de Ação */}
        <div className="flex items-center justify-end gap-2 flex-wrap">
          {isAdmin && (
            <motion.button
              whileHover={{ scale: 1.05 }}
              whileTap={{ scale: 0.95 }}
              onClick={() => setShowChangePassword(true)}
              className="scum-button-mobile text-xs sm:text-sm flex items-center gap-1 sm:gap-2"
            >
              <Lock size={14} className="sm:w-4 sm:h-4" />
              <span className="hidden sm:inline">{t('change_password')}</span>
              <span className="sm:hidden">Senha</span>
            </motion.button>
          )}
          
          <motion.button
            whileHover={{ scale: 1.05 }}
            whileTap={{ scale: 0.95 }}
            onClick={() => navigate('/logs')}
            className="scum-button-mobile text-xs sm:text-sm flex items-center gap-1 sm:gap-2"
          >
            <FileText size={14} className="sm:w-4 sm:h-4" />
            <span className="hidden sm:inline">{t('logs')}</span>
            <span className="sm:hidden">Logs</span>
          </motion.button>

          <LanguageToggle />

          <motion.button
            whileHover={{ scale: 1.05 }}
            whileTap={{ scale: 0.95 }}
            onClick={handleLogout}
            className="scum-button-mobile text-xs sm:text-sm flex items-center gap-1 sm:gap-2 bg-scum-danger/20 hover:bg-scum-danger/30 border-scum-danger/50"
          >
            <LogOut size={14} className="sm:w-4 sm:h-4" />
            <span className="hidden sm:inline">{t('logout')}</span>
            <span className="sm:hidden">Sair</span>
          </motion.button>
        </div>
      </motion.header>

      {/* Modal de Alteração de Senha */}
      {showChangePassword && (
        <ChangePasswordModal
          isOpen={showChangePassword}
          onClose={() => setShowChangePassword(false)}
        />
      )}
    </>
  );
};

export default DashboardHeader; 