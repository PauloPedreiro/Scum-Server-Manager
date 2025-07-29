import React from 'react';
import { CheckSquare, Square } from 'lucide-react';

interface ChatMessage {
  timestamp: string;
  steamId: string;
  playerName: string;
  chatType: string;
  message: string;
}

interface ChatTickerBarProps {
  messages: ChatMessage[];
  ativo: boolean;
  onToggle: () => void;
}

const getEmoji = (type: string) => {
  switch (type) {
    case 'Local': return '🎯';
    case 'Global': return '🌐';
    case 'Squad': return '👥';
    default: return '';
  }
};

const ChatTickerBar: React.FC<ChatTickerBarProps> = ({ messages, ativo, onToggle }) => {
  // Duplicar as mensagens para efeito de loop
  const tickerMessages = messages.length > 0 ? [...messages, ...messages] : [];
  const duration = Math.max(10, messages.length * 4); // duração baseada na quantidade de mensagens

  if (!ativo) {
    return (
      <div className="w-full bg-scum-dark/80 border-b border-scum-accent/30 overflow-hidden flex-shrink-0 flex items-center justify-between" style={{ height: '36px', maxHeight: '36px', minHeight: '36px', width: '100%', maxWidth: '100%' }}>
        <span className="text-scum-muted text-xs px-4">Chat In Game desativado</span>
        <label className="flex items-center gap-2 cursor-pointer select-none px-4">
          <input
            type="checkbox"
            checked={ativo}
            onChange={onToggle}
            className="hidden"
          />
          {ativo ? (
            <CheckSquare size={20} className="text-green-400" />
          ) : (
            <Square size={20} className="text-scum-muted" />
          )}
          <span className="text-scum-light text-xs">Ativar</span>
        </label>
      </div>
    );
  }

  return (
    <div 
      className="w-full bg-scum-dark/80 border-b border-scum-accent/30 overflow-hidden flex-shrink-0 flex items-center justify-between" 
      style={{ 
        height: '36px',
        maxHeight: '36px',
        minHeight: '36px',
        width: '100%',
        maxWidth: '100%'
      }}
    >
      <style>{`
        @keyframes ticker {
          0% { transform: translateX(0); }
          100% { transform: translateX(-50%); }
        }
        .ticker-anim {
          display: flex;
          gap: 2rem;
          white-space: nowrap;
          animation: ticker ${duration}s linear infinite;
          align-items: center;
          height: 100%;
          padding: 8px 16px;
          width: max-content;
        }
        .ticker-anim:hover {
          animation-play-state: paused;
        }
        .ticker-container {
          height: 100%;
          display: flex;
          align-items: center;
          overflow: hidden;
          width: 100%;
          max-width: 100%;
        }
        .ticker-message {
          display: flex;
          align-items: center;
          gap: 4px;
          padding: 0 8px;
          font-size: 12px;
          max-width: 250px;
          white-space: nowrap;
          overflow: hidden;
          text-overflow: ellipsis;
          flex-shrink: 0;
        }
      `}</style>
      <div className="ticker-container flex-1">
        <div
          className={messages.length > 0 ? 'ticker-anim' : ''}
        >
          {tickerMessages.length === 0 ? (
            <span className="text-scum-muted text-xs px-4">Nenhuma mensagem do chat in game.</span>
          ) : (
            tickerMessages.map((msg, idx) => (
              <span key={idx} className="ticker-message">
                <span>{getEmoji(msg.chatType)}</span>
                <span className="font-bold text-scum-accent truncate">{msg.playerName}:</span>
                <span className="text-scum-light truncate">{msg.message}</span>
              </span>
            ))
          )}
        </div>
      </div>
      <label className="flex items-center gap-2 cursor-pointer select-none px-4">
        <input
          type="checkbox"
          checked={ativo}
          onChange={onToggle}
          className="hidden"
        />
        {ativo ? (
          <CheckSquare size={20} className="text-green-400" />
        ) : (
          <Square size={20} className="text-scum-muted" />
        )}
        <span className="text-scum-light text-xs">Ativar</span>
      </label>
    </div>
  );
};

export default ChatTickerBar; 