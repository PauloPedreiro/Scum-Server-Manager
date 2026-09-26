import { Save, RefreshCw, Plus, Loader2, AlertCircle } from 'lucide-react';
import { useTranslation } from 'react-i18next';

interface ActionButtonsProps {
  onRefresh: () => void;
  onAdd?: () => void;
  onSave: () => void;
  loading?: boolean;
  saving?: boolean;
  hasChanges?: boolean;
  disabled?: boolean;
}

export default function ActionButtons({
  onRefresh,
  onAdd,
  onSave,
  loading = false,
  saving = false,
  hasChanges = false,
  disabled = false,
}: ActionButtonsProps) {
  const { t } = useTranslation();

  return (
    <div className="card p-4">
      <div className="flex flex-col sm:flex-row gap-3 sm:items-center">
        <div className="flex gap-2">
          <button
            onClick={onRefresh}
            disabled={loading || disabled}
            className="px-4 py-2 bg-white/5 hover:bg-white/10 border border-white/10 rounded-lg text-white text-sm font-medium transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
          >
            <RefreshCw size={16} className={loading ? 'animate-spin' : ''} />
            <span className="hidden sm:inline">{t('settings.actions.refresh')}</span>
          </button>
          {onAdd && (
            <button
              onClick={onAdd}
              disabled={disabled}
              className="px-4 py-2 bg-white/5 hover:bg-white/10 border border-white/10 rounded-lg text-white text-sm font-medium transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
            >
              <Plus size={16} />
              <span className="hidden sm:inline">{t('settings.actions.addField')}</span>
            </button>
          )}
          <button
            onClick={onSave}
            disabled={!hasChanges || saving || disabled}
            className="px-4 py-2 bg-scum-orange hover:bg-scum-orange/90 text-white rounded-lg text-sm font-medium transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
          >
            {saving ? (
              <>
                <Loader2 size={16} className="animate-spin" />
                <span className="hidden sm:inline">{t('settings.actions.saving')}</span>
              </>
            ) : (
              <>
                <Save size={16} />
                <span className="hidden sm:inline">{t('settings.actions.save')}</span>
              </>
            )}
          </button>
        </div>

        {hasChanges && (
          <div className="flex items-center gap-2 text-amber-400 text-sm">
            <AlertCircle size={16} />
            <span>{t('settings.unsavedChanges')}</span>
          </div>
        )}
      </div>
    </div>
  );
}

