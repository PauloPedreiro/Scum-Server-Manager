import { Loader2 } from 'lucide-react';
import { useTranslation } from 'react-i18next';

interface LoadingStateProps {
  message?: string;
}

export default function LoadingState({ message }: LoadingStateProps) {
  const { t } = useTranslation();

  return (
    <div className="flex items-center justify-center py-12">
      <Loader2 size={32} className="animate-spin text-scum-orange" />
      <span className="ml-3 text-white/70">{message || t('settings.loading')}</span>
    </div>
  );
}

