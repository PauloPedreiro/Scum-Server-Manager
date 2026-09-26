import { AlertCircle } from 'lucide-react';
import { useTranslation } from 'react-i18next';

interface ErrorStateProps {
  message: string;
  onRetry?: () => void;
}

export default function ErrorState({ message, onRetry }: ErrorStateProps) {
  const { t } = useTranslation();

  return (
    <div className="flex flex-col items-center justify-center py-12 text-center">
      <AlertCircle size={48} className="text-red-400 mb-4" />
      <p className="text-red-400 mb-4">{message}</p>
      {onRetry && (
        <button
          onClick={onRetry}
          className="px-4 py-2 bg-scum-orange hover:bg-scum-orange/90 text-white rounded-lg text-sm font-medium transition-colors"
        >
          {t('settings.errors.tryAgain')}
        </button>
      )}
    </div>
  );
}

