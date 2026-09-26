import { useTranslation } from 'react-i18next';

export default function Unauthorized() {
  const { t } = useTranslation();

  return (
    <div className="min-h-[40vh] grid place-items-center">
      <div className="text-center">
        <div className="text-6xl font-black tracking-tight accent">403</div>
        <p className="text-white/60">
          {t('errors.unauthorized.title', { defaultValue: 'Unauthorized' })}
        </p>
      </div>
    </div>
  );
}
