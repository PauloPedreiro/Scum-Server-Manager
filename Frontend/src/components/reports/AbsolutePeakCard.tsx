import React from 'react';
import { useTranslation } from 'react-i18next';
import { Target, Loader2 } from 'lucide-react';
import type { AbsolutePeak } from '@/services/reports';

interface AbsolutePeakCardProps {
  absolutePeak: AbsolutePeak | null;
  loading?: boolean;
}

export function AbsolutePeakCard({ 
  absolutePeak, 
  loading = false 
}: AbsolutePeakCardProps) {
  const { t, i18n } = useTranslation();

  if (loading) {
    return (
      <div className="p-4 sm:p-6 rounded-xl bg-gradient-to-br from-purple-600/20 to-blue-600/20 border border-purple-500/30 shadow-lg">
        <div className="flex items-center gap-2 text-white/70">
          <Loader2 className="animate-spin h-4 w-4" />
          <span className="text-sm">{t('players.analyses.absolutePeak.loading')}</span>
        </div>
      </div>
    );
  }

  if (!absolutePeak) {
    return null; // Não exibir se não houver dados
  }

  // Formatar data conforme locale
  const date = new Date(absolutePeak.timestamp);
  const formattedDate = date.toLocaleDateString(i18n.language, {
    day: 'numeric',
    month: 'long',
    year: 'numeric'
  });
  const formattedTime = date.toLocaleTimeString(i18n.language, {
    hour: '2-digit',
    minute: '2-digit'
  });

  // Determinar preposição baseada no idioma
  const timePreposition = i18n.language === 'pt-BR' ? 'às' : 'at';

  return (
    <div className="p-4 sm:p-6 rounded-xl bg-gradient-to-br from-purple-600/20 to-blue-600/20 border border-purple-500/30 shadow-lg">
      <div className="flex items-center gap-2 mb-3">
        <Target className="text-purple-400" size={20} />
        <h3 className="text-lg font-semibold text-white">
          {t('players.analyses.absolutePeak.title')}
        </h3>
      </div>
      
      <div className="space-y-2">
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-1">
          <span className="text-xs sm:text-sm text-white/70">{t('players.analyses.absolutePeak.date')}:</span>
          <span className="text-sm sm:text-base text-white font-medium">
            {formattedDate} {timePreposition} {formattedTime}
          </span>
        </div>
        
        <div className="flex items-center justify-between gap-2 pt-2 border-t border-white/10 flex-nowrap">
          <span className="text-xs sm:text-sm text-white/70 whitespace-nowrap">{t('players.analyses.absolutePeak.players')}:</span>
          <div className="flex items-center gap-2 flex-shrink-0">
            <span className="text-2xl sm:text-3xl font-bold text-purple-300">
              {absolutePeak.players_count}
            </span>
            <span className="text-xs sm:text-sm text-white/70 whitespace-nowrap">
              {t('players.analyses.players')}
            </span>
          </div>
        </div>
      </div>
    </div>
  );
}
