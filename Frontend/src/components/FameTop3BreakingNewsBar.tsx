import React from 'react';
import { motion } from 'framer-motion';
import { Trophy } from 'lucide-react';
import { FamePlayer } from '../types/fame';
import { FameService } from '../services/fameService';

interface FameTop3BreakingNewsBarProps {
  top3Players: FamePlayer[];
}

const FameTop3BreakingNewsBar: React.FC<FameTop3BreakingNewsBarProps> = ({ top3Players }) => {
  if (!top3Players || top3Players.length === 0) return null;



  return (
    <motion.div 
      initial={{ y: -20, opacity: 0 }}
      animate={{ y: 0, opacity: 1 }}
      className="w-full bg-scum-dark/90 border-b-2 border-yellow-400/60 flex items-center gap-4 px-6 py-2 shadow-lg"
    >
      <div className="flex items-center gap-2 mr-4">
        <Trophy size={20} className="text-yellow-400" />
        <span className="font-bold text-yellow-400 text-base">🏆 TOP 3 FAMA</span>
      </div>
      
      <div className="flex items-center gap-4 flex-1">
        {top3Players.map((player, index) => {
          return (
            <motion.div
              key={player.steamId}
              initial={{ scale: 0.8, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              transition={{ delay: index * 0.1 }}
              className="flex items-center gap-2"
            >
              {/* Posição e Medalha */}
              <div className="flex items-center gap-1">
                <span className="text-lg">{FameService.getMedalIcon(index + 1)}</span>
                <span className={`font-bold text-sm ${
                  index === 0 ? 'text-yellow-400' :
                  index === 1 ? 'text-gray-400' :
                  'text-orange-400'
                }`}>
                  #{index + 1}
                </span>
              </div>

              {/* Nome do jogador */}
              <div className="flex flex-col">
                <span className="font-bold text-scum-light text-sm">{player.playerName}</span>
              </div>

              {/* Pontos de fama */}
              <div className="text-right">
                <div className="text-sm font-bold text-scum-accent">
                  {FameService.formatFamePoints(player.totalFame)}
                </div>
              </div>
            </motion.div>
          );
        })}
      </div>

      {/* Última atualização */}
      {top3Players.length > 0 && (
        <div className="text-xs text-scum-muted font-mono ml-auto">
          Atualizado: {FameService.formatTimestamp(top3Players[0].timestamp)}
        </div>
      )}
    </motion.div>
  );
};

export default FameTop3BreakingNewsBar; 