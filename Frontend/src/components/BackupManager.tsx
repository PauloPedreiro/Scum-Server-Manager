import React, { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { Download, Upload, Trash2, Clock, FileText, AlertTriangle } from 'lucide-react';
import { ServerConfigService, BackupInfo } from '../services/serverConfigService';

interface BackupManagerProps {
  onBackupRestored?: () => void;
}

const BackupManager: React.FC<BackupManagerProps> = ({ onBackupRestored }) => {
  const [backups, setBackups] = useState<BackupInfo[]>([]);
  const [loading, setLoading] = useState(false);
  const [restoring, setRestoring] = useState<string | null>(null);

  useEffect(() => {
    loadBackups();
  }, []);

  const loadBackups = async () => {
    setLoading(true);
    try {
      const response = await ServerConfigService.getBackups();
      if (response.success && response.backups) {
        setBackups(response.backups);
      } else {
        console.error('Erro ao carregar backups:', response.error);
      }
    } catch (error) {
      console.error('Erro ao carregar backups:', error);
    } finally {
      setLoading(false);
    }
  };

  const restoreBackup = async (filename: string) => {
    setRestoring(filename);
    try {
      const response = await ServerConfigService.restoreBackup(filename);
      if (response.success) {
        console.log('Backup restaurado com sucesso');
        onBackupRestored?.();
        // Recarregar lista de backups
        await loadBackups();
      } else {
        console.error('Erro ao restaurar backup:', response.error);
      }
    } catch (error) {
      console.error('Erro ao restaurar backup:', error);
    } finally {
      setRestoring(null);
    }
  };

  const formatFileSize = (bytes: number): string => {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  };

  const formatDate = (dateString: string): string => {
    const date = new Date(dateString);
    return date.toLocaleString('pt-BR', {
      day: '2-digit',
      month: '2-digit',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center py-8">
        <div className="text-center">
          <div className="w-6 h-6 border-2 border-scum-accent border-t-transparent rounded-full animate-spin mx-auto mb-2"></div>
          <p className="text-scum-muted text-sm">Carregando backups...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <FileText className="text-scum-accent" size={20} />
          <h3 className="text-lg font-semibold text-scum-light">Gerenciador de Backups</h3>
        </div>
        <button
          onClick={loadBackups}
          className="text-sm text-scum-accent hover:text-scum-accent/80 transition-colors"
        >
          Atualizar
        </button>
      </div>

      {backups.length === 0 ? (
        <div className="text-center py-8">
          <AlertTriangle className="text-scum-muted mx-auto mb-2" size={24} />
          <p className="text-scum-muted text-sm">Nenhum backup encontrado</p>
        </div>
      ) : (
        <div className="space-y-2">
          {backups.map((backup) => (
            <motion.div
              key={backup.filename}
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              className="scum-card p-4"
            >
              <div className="flex items-center justify-between">
                <div className="flex-1">
                  <div className="flex items-center gap-2 mb-1">
                    <FileText className="text-scum-accent" size={16} />
                    <span className="text-sm font-medium text-scum-light">{backup.filename}</span>
                  </div>
                  <div className="flex items-center gap-4 text-xs text-scum-muted">
                    <div className="flex items-center gap-1">
                      <Clock size={12} />
                      <span>{formatDate(backup.created)}</span>
                    </div>
                    <span>{formatFileSize(backup.size)}</span>
                    <span>Arquivo: {backup.originalFile}</span>
                  </div>
                </div>
                
                <div className="flex items-center gap-2">
                  <button
                    onClick={() => restoreBackup(backup.filename)}
                    disabled={restoring === backup.filename}
                    className="flex items-center gap-1 px-3 py-1 bg-scum-accent hover:bg-scum-accent/80 disabled:bg-scum-muted text-scum-dark text-xs font-medium rounded transition-colors"
                  >
                    {restoring === backup.filename ? (
                      <>
                        <div className="w-3 h-3 border border-scum-dark border-t-transparent rounded-full animate-spin"></div>
                        Restaurando...
                      </>
                    ) : (
                      <>
                        <Upload size={12} />
                        Restaurar
                      </>
                    )}
                  </button>
                </div>
              </div>
            </motion.div>
          ))}
        </div>
      )}

      <div className="text-xs text-scum-muted text-center">
        <p>Backups são criados automaticamente antes de cada modificação</p>
        <p>Os backups são salvos em: src/data/configserver/backups/</p>
      </div>
    </div>
  );
};

export default BackupManager; 