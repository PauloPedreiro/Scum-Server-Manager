import { useTranslation } from 'react-i18next';

export default function NotFound() {
  const { t } = useTranslation();
  return (
    <div className="min-h-[40vh] grid place-items-center">
      <div className="text-center">
        <div className="text-6xl font-black tracking-tight accent">404</div>
        <p className="text-white/60">{t('errors.notFound.title')}</p>
      </div>
    </div>
  );
}


