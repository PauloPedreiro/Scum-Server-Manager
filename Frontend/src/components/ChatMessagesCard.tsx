import React from 'react';
import { CheckSquare, Square, MessageCircle, Users, Globe, MapPin } from 'lucide-react';
import { useLanguage } from '../contexts/LanguageContext';

interface ChatMessage {
  timestamp: string;
  steamId: string;
  playerName: string;
  chatType: string;
  message: string;
}

interface ChatMessagesCardProps {
  messages: ChatMessage[];
  ativo: boolean;
  onToggle: () => void;
  hideSteamIds?: boolean;
}

const getEmoji = (type: string) => {
  switch (type) {
    case 'Local': return '🎯';
    case 'Global': return '🌐';
    case 'Squad': return '👥';
    default: return '';
  }
};

const getIcon = (type: string) => {
  switch (type) {
    case 'Local': return MapPin;
    case 'Global': return Globe;
    case 'Squad': return Users;
    default: return MessageCircle;
  }
};

const formatTime = (timestamp: string) => {
  try {
    const date = new Date(timestamp);
    const time = date.toLocaleTimeString('pt-BR', {
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit'
    });
    // Se for inválido, retorna vazio
    if (time === 'Invalid Date' || isNaN(date.getTime())) return '';
    return time;
  } catch {
    return '';
  }
};

const ChatMessagesCard: React.FC<ChatMessagesCardProps> = ({ messages, ativo, onToggle, hideSteamIds = false }) => {
  const { t, language } = useLanguage();
  const lastMessages = messages.slice(-50).reverse(); // Últimas 50 mensagens, mais recente primeiro

  if (!ativo) {
    return (
      <div className="w-full bg-scum-dark/50 border border-scum-gray/30 rounded-lg p-4 shadow-lg">
        <div className="flex items-center justify-between mb-3">
          <div className="flex items-center gap-2">
            <div className="w-7 h-7 bg-scum-secondary/50 rounded-lg flex items-center justify-center">
              <MessageCircle size={16} className="text-scum-muted" />
            </div>
            <div>
                          <h3 className="text-scum-light font-semibold text-base">{t('chat_in_game')}</h3>
            <p className="text-scum-muted text-xs">{t('disabled')}</p>
            </div>
          </div>
          <label className="flex items-center gap-1 cursor-pointer select-none">
            <input
              type="checkbox"
              checked={ativo}
              onChange={onToggle}
              className="hidden"
            />
            {ativo ? (
              <CheckSquare size={16} className="text-green-400" />
            ) : (
              <Square size={16} className="text-scum-muted" />
            )}
            <span className="text-scum-light text-xs">{t('activate')}</span>
          </label>
        </div>
        <div className="text-center py-6">
          <MessageCircle size={32} className="text-scum-muted mx-auto mb-2" />
          <p className="text-scum-muted text-sm">{t('chat_in_game_disabled')}</p>
        </div>
      </div>
    );
  }

  return (
    <div className="w-full bg-scum-dark/50 border border-scum-gray/30 rounded-lg p-4 shadow-lg">
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <div className="w-7 h-7 bg-scum-secondary/50 rounded-lg flex items-center justify-center">
            <MessageCircle size={16} className="text-scum-accent" />
          </div>
          <div>
            <h3 className="text-scum-light font-semibold text-base">{t('chat_in_game')}</h3>
            <p className="text-scum-muted text-xs">
              {lastMessages.length} {t('recent_message')}{lastMessages.length !== 1 ? 's' : ''}
            </p>
          </div>
        </div>
        <label className="flex items-center gap-1 cursor-pointer select-none">
          <input
            type="checkbox"
            checked={ativo}
            onChange={onToggle}
            className="hidden"
          />
          {ativo ? (
            <CheckSquare size={16} className="text-green-400" />
          ) : (
            <Square size={16} className="text-scum-muted" />
          )}
                      <span className="text-scum-light text-xs">{t('activate')}</span>
        </label>
      </div>

      <div className="space-y-1.5 max-h-64 overflow-y-auto" style={{
        scrollbarWidth: 'thin',
        scrollbarColor: 'rgba(210, 105, 30, 0.3) transparent'
      }}>
        {lastMessages.length === 0 ? (
          <div className="text-center py-8 flex-1 flex flex-col items-center justify-center">
            <MessageCircle size={32} className="text-scum-muted mx-auto mb-2" />
            <p className="text-scum-muted text-sm">{t('no_chat_messages')}</p>
          </div>
        ) : (
          lastMessages.map((msg, idx) => {
            const IconComponent = getIcon(msg.chatType);
            return (
              <div key={`${msg.timestamp}-${msg.steamId}-${idx}`} className="bg-scum-dark/40 rounded-lg p-2 border border-scum-accent/10 hover:border-scum-accent/30 transition-colors">
                <div className="flex items-start gap-2">
                  <div className="flex-shrink-0 w-6 h-6 bg-scum-secondary/30 rounded-full flex items-center justify-center">
                    <IconComponent size={11} className="text-scum-accent" />
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-1 mb-0.5">
                      <span className="text-sm">{getEmoji(msg.chatType)}</span>
                      <span className="font-semibold text-scum-accent text-xs truncate">
                        {msg.playerName}
                      </span>
                      <span className="text-scum-muted text-[9px]">
                        {formatTime(msg.timestamp)}
                      </span>
                    </div>
                    <p className="text-scum-light text-xs break-words">
                      {msg.message}
                    </p>
                    <div className="flex items-center gap-1 mt-0.5">
                      <span className="text-[9px] text-scum-muted bg-scum-dark/50 px-1 py-0.5 rounded">
                        {msg.chatType}
                      </span>
                      {!hideSteamIds && (
                        <span className="text-[9px] text-scum-muted">
                          Steam ID: {msg.steamId}
                        </span>
                      )}
                    </div>
                  </div>
                </div>
              </div>
            );
          })
        )}
      </div>
    </div>
  );
};

export default ChatMessagesCard;