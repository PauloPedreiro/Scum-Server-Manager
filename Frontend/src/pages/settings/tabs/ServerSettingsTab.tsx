import { useMemo } from 'react';
import { useTranslation } from 'react-i18next';
import { getFieldDisplayName } from '@/utils/settingsFormatter';
import { validateFieldValue } from '@/utils/fieldTypeDetector';
import { getFieldType } from '@/utils/fieldTypeDetector';
import { validateFieldConstraints } from '@/utils/fieldConstraints';
import Swal from 'sweetalert2';
import { useServerSettings } from '../hooks/useServerSettings';
import SectionTabs from '../components/SectionTabs';
import ActionButtons from '../components/ActionButtons';
import FieldCard from '../components/FieldCard';
import LoadingState from '../components/LoadingState';
import ErrorState from '../components/ErrorState';
import EmptyState from '../components/EmptyState';

type SectionName = 'General' | 'World' | 'Respawn' | 'Vehicles' | 'Damage' | 'Features';

const SECTIONS: SectionName[] = ['General', 'World', 'Respawn', 'Vehicles', 'Damage', 'Features'];

interface ServerSettingsTabProps {
  searchQuery: string;
  onSearchChange: (query: string) => void;
  activeSection: SectionName;
  onSectionChange: (section: SectionName) => void;
}

export default function ServerSettingsTab({
  searchQuery,
  onSearchChange,
  activeSection,
  onSectionChange,
}: ServerSettingsTabProps) {
  const { t } = useTranslation();
  const {
    loading,
    saving,
    error,
    editingSettings,
    hasChanges,
    fetchSettings,
    handleFieldChange,
    handleSave,
  } = useServerSettings(activeSection);

  // Filtrar campos por busca
  const filteredSettings = useMemo(() => {
    if (!searchQuery.trim()) {
      return editingSettings;
    }

    const query = searchQuery.toLowerCase();
    const filtered: Record<string, string> = {};

    Object.entries(editingSettings).forEach(([key, value]) => {
      const translatedName = getFieldDisplayName(key, activeSection, t).toLowerCase();
      if (
        key.toLowerCase().includes(query) ||
        value.toLowerCase().includes(query) ||
        translatedName.includes(query)
      ) {
        filtered[key] = value;
      }
    });

    return filtered;
  }, [editingSettings, searchQuery, activeSection, t]);

  const sortedSettings = useMemo(() => {
    return Object.entries(filteredSettings);
  }, [filteredSettings]);

  // Salvar com validação
  const handleSaveWithValidation = async () => {
    // Validar todos os campos antes de salvar
    const validationErrors: string[] = [];
    
    Object.entries(editingSettings).forEach(([key, value]) => {
      const fieldType = getFieldType(key, value);
      const typeValidation = validateFieldValue(fieldType, value);
      if (!typeValidation.valid) {
        const fieldName = getFieldDisplayName(key, activeSection, t);
        validationErrors.push(`${fieldName}: ${typeValidation.error}`);
        return;
      }
      
      const constraintsValidation = validateFieldConstraints(key, value);
      if (!constraintsValidation.valid) {
        const fieldName = getFieldDisplayName(key, activeSection, t);
        validationErrors.push(`${fieldName}: ${constraintsValidation.error}`);
      }
    });

    if (validationErrors.length > 0) {
      await Swal.fire({
        icon: 'error',
        title: t('settings.errors.validationFailed'),
        html: `
          <p class="text-sm mb-2">${t('settings.errors.validationErrors')}:</p>
          <ul class="text-sm text-left list-disc list-inside max-h-60 overflow-y-auto">
            ${validationErrors.map(err => `<li>${err}</li>`).join('')}
          </ul>
        `,
        confirmButtonColor: '#f97316',
      });
      return;
    }

    const result = await handleSave();
    if (!result) {
      await Swal.fire({
        icon: 'info',
        title: t('common.info'),
        text: t('common.noChanges'),
        confirmButtonColor: '#f97316',
      });
      return;
    }

    if (result.success) {
      await Swal.fire({
        icon: 'success',
        title: t('settings.save.success'),
        html: `
          <p>${result.message}</p>
          ${result.backup ? `<p class="text-sm mt-2 text-gray-400">${t('settings.save.backup')}: <code class="text-xs">${result.backup}</code></p>` : ''}
        `,
        confirmButtonColor: '#f97316',
      });
    } else {
      await Swal.fire({
        icon: 'error',
        title: t('settings.errors.saveFailed'),
        text: result.error,
        confirmButtonColor: '#f97316',
      });
    }
  };

  return (
    <div className="space-y-4">
      {/* Tabs de Seções */}
      <SectionTabs
        sections={SECTIONS}
        activeSection={activeSection}
        onSectionChange={onSectionChange}
        formatLabel={(section) => {
          const key = `settings.sections.${section}`;
          const translated = t(key);
          return `[${translated && translated !== key ? translated : section}]`;
        }}
      />

      <ActionButtons
        onRefresh={fetchSettings}
        onSave={handleSaveWithValidation}
        loading={loading}
        saving={saving}
        hasChanges={hasChanges}
        disabled={loading}
      />

      {/* Conteúdo Principal */}
      <div className="card p-4 sm:p-6">
        {loading ? (
          <LoadingState />
        ) : error ? (
          <ErrorState message={error} onRetry={fetchSettings} />
        ) : sortedSettings.length === 0 ? (
          <EmptyState
            message={searchQuery ? t('settings.search.noResults') : t('settings.empty')}
            showAddButton={false}
          />
        ) : (
          <div className="space-y-4">
            <div className="grid grid-cols-1 lg:grid-cols-2 xl:grid-cols-3 gap-4">
              {sortedSettings.map(([key, value]) => (
                <FieldCard
                  key={key}
                  keyName={key}
                  value={value}
                  displayName={getFieldDisplayName(key, activeSection, t)}
                  onChange={(newValue) => handleFieldChange(key, String(newValue))}
                />
              ))}
            </div>

            <div className="text-sm text-white/50 text-center pt-4 border-t border-white/10">
              {t('settings.fieldsCount', {
                count: sortedSettings.length,
                total: Object.keys(editingSettings).length,
              })}
              {searchQuery && (
                <span className="ml-2">({t('settings.search.filtered')})</span>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

