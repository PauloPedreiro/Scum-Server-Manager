import React from 'react';
import { motion } from 'framer-motion';
import { 
  Shield, 
  Users, 
  Server, 
  Activity, 
  Zap, 
  Target, 
  MapPin, 
  Clock,
  Wifi,
  Battery,
  Signal,
  AlertTriangle
} from 'lucide-react';

interface ScumIconProps {
  type: 'server' | 'players' | 'activity' | 'status' | 'location' | 'time' | 'signal' | 'battery' | 'warning';
  size?: number;
  className?: string;
  animated?: boolean;
}

const ScumIcon: React.FC<ScumIconProps> = ({ type, size = 24, className = '', animated = false }) => {
  const iconMap = {
    server: Server,
    players: Users,
    activity: Activity,
    status: Shield,
    location: MapPin,
    time: Clock,
    signal: Signal,
    battery: Battery,
    warning: AlertTriangle,
  };

  const IconComponent = iconMap[type];

  if (animated) {
    return (
      <motion.div
        whileHover={{ scale: 1.1 }}
        whileTap={{ scale: 0.9 }}
        className={className}
      >
        <IconComponent size={size} />
      </motion.div>
    );
  }

  return <IconComponent size={size} className={className} />;
};

// Componente de status do servidor
export const ServerStatus: React.FC<{ status: 'online' | 'offline' | 'warning' }> = ({ status }) => {
  const statusConfig = {
    online: {
      color: 'text-green-500',
      bgColor: 'bg-green-500',
      text: 'ONLINE',
      icon: 'status' as const,
    },
    offline: {
      color: 'text-red-500',
      bgColor: 'bg-red-500',
      text: 'OFFLINE',
      icon: 'warning' as const,
    },
    warning: {
      color: 'text-yellow-500',
      bgColor: 'bg-yellow-500',
      text: 'WARNING',
      icon: 'warning' as const,
    },
  };

  const config = statusConfig[status];

  return (
    <div className="flex items-center gap-2">
      <div className={`w-2 h-2 ${config.bgColor} rounded-full animate-pulse`}></div>
      <ScumIcon type={config.icon} size={16} className={config.color} />
      <span className="text-xs text-scum-muted digital-text">{config.text}</span>
    </div>
  );
};

// Componente de estatísticas
export const StatCard: React.FC<{
  title: string;
  value: string | number;
  icon: ScumIconProps['type'];
  color?: string;
}> = ({ title, value, icon, color = 'text-scum-accent' }) => {
  return (
    <motion.div
      whileHover={{ scale: 1.02 }}
      className="scum-card p-4 backdrop-blur-sm bg-scum-gray/60"
    >
      <div className="flex items-center justify-between">
        <div>
          <p className="text-xs text-scum-muted military-text">{title}</p>
          <p className={`text-lg font-bold ${color}`}>{value}</p>
        </div>
        <ScumIcon type={icon} size={24} className={color} />
      </div>
    </motion.div>
  );
};

// Componente de barra de progresso temática
export const ScumProgressBar: React.FC<{
  value: number;
  max: number;
  label: string;
  color?: 'green' | 'orange' | 'red' | 'blue';
}> = ({ value, max, label, color = 'green' }) => {
  const percentage = (value / max) * 100;
  
  const colorConfig = {
    green: 'bg-scum-secondary',
    orange: 'bg-scum-accent',
    red: 'bg-scum-danger',
    blue: 'bg-blue-500',
  };

  return (
    <div className="space-y-2">
      <div className="flex justify-between text-xs text-scum-muted">
        <span className="digital-text">{label}</span>
        <span className="digital-text">{value}/{max}</span>
      </div>
      <div className="w-full bg-scum-gray rounded-full h-2">
        <motion.div
          className={`h-2 rounded-full ${colorConfig[color]}`}
          initial={{ width: 0 }}
          animate={{ width: `${percentage}%` }}
          transition={{ duration: 1, ease: "easeOut" }}
        />
      </div>
    </div>
  );
};

export default ScumIcon; 