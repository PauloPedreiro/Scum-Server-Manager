import { FileText, Plus } from 'lucide-react';
import { useTranslation } from 'react-i18next';

interface EmptyStateProps {
  message: string;
  showAddButton?: boolean;
  onAdd?: () => void;
}

export default function EmptyState({ message, showAddButton = false, onAdd }: EmptyStateProps) {
  const { t } = useTranslation();

  return (
    <div className="flex flex-col items-center justify-center py-12 text-center">
      <FileText size={48} className="text-white/30 mb-4" />
      <p className="text-white/70 mb-2">{message}</p>
      {showAddButton && onAdd && (
        <button
          onClick={onAdd}
          className="mt-4 px-4 py-2 bg-scum-orange hover:bg-scum-orange/90 text-white rounded-lg text-sm font-medium transition-colors flex items-center gap-2"
        >
          <Plus size={16} />
          {t('settings.actions.addField')}
        </button>
      )}
    </div>
  );
}

