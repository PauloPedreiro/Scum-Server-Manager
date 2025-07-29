import React from 'react';
import { motion } from 'framer-motion';
import { 
  BarChart3, 
  Users, 
  Bot, 
  FileText, 
  Settings, 
  HardDrive, 
  Activity,
  Shield,
  Zap,
  Star,
  Server
} from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { useLanguage } from '../contexts/LanguageContext';

interface DashboardSidebarProps {
  activeSection: string;
  onSectionChange: (section: string) => void;
  onDonationClick?: () => void;
  isMobile?: boolean;
  onMobileClose?: () => void;
}

interface MenuItem {
  id: string;
  label: string;
  icon: React.ComponentType<any>;
  active?: boolean;
  badge?: number;
}

const DashboardSidebar: React.FC<DashboardSidebarProps> = ({ 
  activeSection, 
  onSectionChange,
  onDonationClick,
  isMobile = false,
  onMobileClose
}) => {
  const navigate = useNavigate();
  const { t } = useLanguage();
  
  const menuItems: MenuItem[] = [
    {
      id: 'dashboard',
      label: t('dashboard'),
      icon: BarChart3,
      active: activeSection === 'dashboard'
    },
    {
      id: 'players',
      label: t('players'),
      icon: Users,
      active: activeSection === 'players',
      badge: 24
    },
    {
      id: 'fama',
      label: t('fama'),
      icon: Star,
      active: activeSection === 'fama'
    },
    {
      id: 'discord',
      label: t('discord'),
      icon: Bot,
      active: activeSection === 'discord',
      badge: 3
    },
    {
      id: 'admin',
      label: t('administration'),
      icon: Shield,
      active: activeSection === 'admin'
    },
    {
      id: 'veiculos',
      label: t('vehicles'),
      icon: FileText,
      active: activeSection === 'veiculos'
    },
    {
      id: 'settings',
      label: t('settings'),
      icon: Settings,
      active: activeSection === 'settings'
    },
    {
      id: 'server_config',
      label: t('server_configuration'),
      icon: Server,
      active: activeSection === 'server_config'
    },
    {
      id: 'backups',
      label: t('backups'),
      icon: HardDrive,
      active: activeSection === 'backups'
    },
    {
      id: 'analytics',
      label: t('analytics'),
      icon: Activity,
      active: activeSection === 'analytics'
    }
  ];

  const handleSectionChange = (sectionId: string) => {
    onSectionChange(sectionId);
    if (isMobile && onMobileClose) {
      onMobileClose();
    }
  };

  return (
    <motion.aside 
      initial={{ x: -20, opacity: 0 }}
      animate={{ x: 0, opacity: 1 }}
      className={`${isMobile ? 'w-full' : 'w-64'} bg-scum-gray/30 backdrop-blur-md border-r border-scum-primary p-4 space-y-2`}
    >
      {/* Botão de Doação */}
      <div className="mb-6 p-4">
        <motion.button
          whileHover={{ scale: 1.05 }}
          whileTap={{ scale: 0.95 }}
          onClick={onDonationClick}
          className="w-full text-white font-bold py-3 px-4 rounded-lg shadow-lg transition-all duration-200 flex items-center justify-center space-x-2 animate-gradient rgb-glow"
          style={{
            background: 'linear-gradient(-45deg, #6b8e23, #8b4513, #d2691e, #a0522d, #556b2f, #b8860b, #daa520, #cd853f)',
            backgroundSize: '400% 400%',
            animation: 'gradient 3s ease infinite, heartbeat 2s ease-in-out infinite'
          }}
        >
          <svg className="w-5 h-5 text-red-500" fill="currentColor" viewBox="0 0 20 20">
            <path d="M9.654 17.836l-.468-.299C4.776 15.298 2 12.092 2 8.5 2 5.462 4.462 3 7.5 3c1.548 0 2.973.801 3.787 2.107C12.027 3.801 13.452 3 15 3c3.038 0 5.5 2.462 5.5 5.5 0 3.592-2.776 6.798-7.186 11.037l-.468.299-.468-.299z" />
          </svg>
          <span className="text-sm">{t('support_project')}</span>
        </motion.button>
      </div>

      {/* Menu Items */}
      <nav className="space-y-1">
        {menuItems.map((item) => {
          const IconComponent = item.icon;
          return (
            <motion.button
              key={item.id}
              whileHover={{ scale: 1.02, x: 4 }}
              whileTap={{ scale: 0.98 }}
              onClick={() => handleSectionChange(item.id)}
              className={`w-full flex items-center justify-between p-3 rounded-lg transition-all duration-200 group ${
                item.active 
                  ? 'bg-scum-secondary/50 border border-scum-accent text-scum-light' 
                  : 'text-scum-muted hover:text-scum-light hover:bg-scum-gray/50'
              }`}
            >
              <div className="flex items-center gap-3">
                <div className={`p-2 rounded-lg ${
                  item.active 
                    ? 'bg-scum-accent/20' 
                    : 'bg-scum-gray/50 group-hover:bg-scum-gray/70'
                }`}>
                  <IconComponent 
                    size={18} 
                    className={item.active ? 'text-scum-accent' : 'text-scum-muted group-hover:text-scum-light'} 
                  />
                </div>
                <span className="text-xs military-text tracking-wide">
                  {item.label}
                </span>
              </div>
              
              {item.badge && (
                <div className="flex items-center gap-2">
                  <span className="text-xs text-scum-accent digital-text">
                    {item.badge}
                  </span>
                  <div className="w-2 h-2 bg-scum-accent rounded-full animate-pulse"></div>
                </div>
              )}
            </motion.button>
          );
        })}
      </nav>

      {/* Status do Sistema - Oculto em mobile para economizar espaço */}
      {!isMobile && (
        <div className="mt-8 p-4 scum-card">
          <div className="flex items-center gap-2 mb-3">
            <Zap size={14} className="text-scum-accent" />
            <span className="text-xs text-scum-muted military-text">{t('system_status')}</span>
          </div>
          
          <div className="space-y-2">
            <div className="flex items-center justify-between text-xs">
              <span className="text-scum-muted digital-text">CPU</span>
              <span className="text-scum-accent digital-text">45%</span>
            </div>
            <div className="w-full bg-scum-gray rounded-full h-1">
              <motion.div 
                className="h-1 bg-scum-accent rounded-full"
                initial={{ width: 0 }}
                animate={{ width: '45%' }}
                transition={{ duration: 1 }}
              />
            </div>
            
            <div className="flex items-center justify-between text-xs">
              <span className="text-scum-muted digital-text">RAM</span>
              <span className="text-scum-accent digital-text">67%</span>
            </div>
            <div className="w-full bg-scum-gray rounded-full h-1">
              <motion.div 
                className="h-1 bg-scum-secondary rounded-full"
                initial={{ width: 0 }}
                animate={{ width: '67%' }}
                transition={{ duration: 1, delay: 0.2 }}
              />
            </div>
          </div>
        </div>
      )}
    </motion.aside>
  );
};

export default DashboardSidebar; 