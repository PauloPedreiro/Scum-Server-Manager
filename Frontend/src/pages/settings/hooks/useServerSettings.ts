import { useState, useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import {
  getServerSettings,
  updateSection,
  type ServerSettingsResponse,
} from '@/services/settings';

type SectionName = 'General' | 'World' | 'Respawn' | 'Vehicles' | 'Damage' | 'Features';

export function useServerSettings(section: SectionName) {
  const { t } = useTranslation();
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [settingsData, setSettingsData] = useState<ServerSettingsResponse | null>(null);
  const [editingSettings, setEditingSettings] = useState<Record<string, string>>({});
  const [hasChanges, setHasChanges] = useState(false);

  // Carregar configurações
  const fetchSettings = async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await getServerSettings(section);
      if (response.success && response.data) {
        setSettingsData(response);
        const sectionData = response.data[section] || {};
        setEditingSettings({ ...sectionData });
        setHasChanges(false);
      } else {
        setError(response.error || t('settings.errors.loadFailed'));
      }
    } catch (err: any) {
      const errorMsg = err.response?.data?.error || err.message || t('settings.errors.loadFailed');
      setError(errorMsg);
    } finally {
      setLoading(false);
    }
  };

  // Carregar ao mudar de seção
  useEffect(() => {
    fetchSettings();
  }, [section]);

  // Detectar mudanças
  useEffect(() => {
    if (!settingsData?.data?.[section]) return;
    const original = settingsData.data[section];
    const edited = editingSettings;
    const hasDiff = Object.keys(original).some(
      (key) => original[key] !== edited[key]
    ) || Object.keys(edited).some(
      (key) => original[key] !== edited[key]
    );
    setHasChanges(hasDiff);
  }, [editingSettings, settingsData, section]);

  // Atualizar campo
  const handleFieldChange = (key: string, value: string) => {
    setEditingSettings((prev) => ({ ...prev, [key]: value }));
  };

  // Salvar
  const handleSave = async () => {
    if (!hasChanges) return;
    setSaving(true);
    try {
      const response = await updateSection(section, editingSettings);
      if (response.success) {
        await fetchSettings();
        return { success: true, message: response.message, backup: response.data?.backup };
      } else {
        throw new Error(response.error || response.message || t('settings.errors.saveFailed'));
      }
    } catch (err: any) {
      const errorMsg = err.response?.data?.error || err.message || t('settings.errors.saveFailed');
      return { success: false, error: errorMsg };
    } finally {
      setSaving(false);
    }
  };

  return {
    loading,
    saving,
    error,
    settingsData,
    editingSettings,
    hasChanges,
    fetchSettings,
    handleFieldChange,
    handleSave,
  };
}

