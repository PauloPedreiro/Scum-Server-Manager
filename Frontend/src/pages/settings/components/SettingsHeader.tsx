import { Settings as SettingsIcon } from 'lucide-react';
import { useTranslation } from 'react-i18next';

export default function SettingsHeader() {
  const { t } = useTranslation();

  return (
    <div className="card p-4 sm:p-6">
      <div className="flex items-center gap-2 mb-4">
        <SettingsIcon size={20} className="text-scum-orange" />
        <h1 className="text-xl sm:text-2xl font-semibold">{t('settings.title')}</h1>
      </div>
      <p className="text-white/70 text-sm">{t('settings.description')}</p>
    </div>
  );
}

