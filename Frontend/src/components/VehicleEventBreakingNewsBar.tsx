import React from 'react';

interface VehicleEvent {
  event: string;
  vehicleType: string;
  ownerName?: string | null;
  timestamp: string;
}

const eventIcons: Record<string, string> = {
  Destroyed: '💥',
  Disappeared: '👻',
  VehicleInactiveTimerReached: '⏰',
};

const eventLabels: Record<string, string> = {
  Destroyed: 'Destruído',
  Disappeared: 'Desaparecido',
  VehicleInactiveTimerReached: 'Temporizador de veículo inativo atingido',
};

interface VehicleEventBreakingNewsBarProps {
  event: VehicleEvent | null;
}

const VehicleEventBreakingNewsBar: React.FC<VehicleEventBreakingNewsBarProps> = ({ event }) => {
  if (!event) return null;
  return (
    <div className="w-full bg-scum-dark/90 border-b-2 border-scum-accent/60 flex items-center gap-4 px-6 py-2 shadow-lg">
      <div className="flex items-center gap-2 mr-4">
        <span className="text-xl">{eventIcons[event.event] || '❓'}</span>
        <span className="font-bold text-scum-accent text-base">{eventLabels[event.event] || event.event}</span>
      </div>
      
      <div className="flex items-center gap-4 flex-1">
        <span className="text-scum-light text-sm">{event.vehicleType}</span>
        <span className="text-scum-light text-sm">— Proprietário: {event.ownerName && event.ownerName.trim() !== '' ? (
          <span className="font-bold">{event.ownerName}</span>
        ) : (
          <span className="text-red-500">Sem Proprietário</span>
        )}</span>
      </div>

      <span className="text-scum-muted text-xs">{event.timestamp}</span>
    </div>
  );
};

export default VehicleEventBreakingNewsBar; 