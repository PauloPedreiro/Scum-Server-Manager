import React, { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { FileText, RefreshCw, AlertCircle, CheckCircle, Clock } from 'lucide-react';
import authService, { AuthLog } from '../services/authService';
import { useLanguage } from '../contexts/LanguageContext';
import { toast } from 'react-toastify';

const AuthLogsView: React.FC = () => {
  const [logs, setLogs] = useState<AuthLog[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [refreshing, setRefreshing] = useState(false);
  const { t } = useLanguage();

  useEffect(() => {
    fetchLogs();
  }, []);

  const fetchLogs = async () => {
    try {
      setLoading(true);
      setError(null);
      
      const result = await authService.getLogs();
      
      if (result.success && result.data) {
        setLogs(result.data.logs);
      } else {
        setError(result.message || 'Erro ao carregar logs');
        toast.error(result.message || 'Erro ao carregar logs');
      }
    } catch (error) {
      const errorMessage = 'Erro de conexão ao carregar logs';
      setError(errorMessage);
      toast.error(errorMessage);
      console.error('[LOGS] Erro ao carregar logs:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleRefresh = async () => {
    setRefreshing(true);
    await fetchLogs();
    setRefreshing(false);
  };

  const formatDate = (timestamp: string) => {
    try {
      return new Date(timestamp).toLocaleString('pt-BR', {
        day: '2-digit',
        month: '2-digit',
        year: 'numeric',
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit'
      });
    } catch {
      return timestamp;
    }
  };

  const getActionIcon = (action: string) => {
    if (action.toLowerCase().includes('login')) return <CheckCircle size={16} className="text-green-400" />;
    if (action.toLowerCase().includes('logout')) return <Clock size={16} className="text-blue-400" />;
    if (action.toLowerCase().includes('failed') || action.toLowerCase().includes('error')) return <AlertCircle size={16} className="text-red-400" />;
    return <FileText size={16} className="text-gray-400" />;
  };

  const getActionColor = (action: string) => {
    if (action.toLowerCase().includes('login')) return 'text-green-400';
    if (action.toLowerCase().includes('logout')) return 'text-blue-400';
    if (action.toLowerCase().includes('failed') || action.toLowerCase().includes('error')) return 'text-red-400';
    return 'text-gray-400';
  };

  if (loading) {
    return (
      <div className="bg-scum-dark/60 backdrop-blur-sm rounded-lg border border-scum-accent/20 p-6">
        <div className="flex items-center justify-center py-12">
          <div className="w-8 h-8 border-2 border-scum-accent border-t-transparent rounded-full animate-spin"></div>
          <span className="ml-3 text-scum-light">Carregando logs...</span>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-scum-dark/60 backdrop-blur-sm rounded-lg border border-scum-accent/20 p-6">
        <div className="text-center py-12">
          <div className="text-red-400 text-4xl mb-4">⚠️</div>
          <h3 className="text-lg font-bold text-scum-light mb-2">Erro ao carregar logs</h3>
          <p className="text-scum-muted mb-4">{error}</p>
          <button
            onClick={fetchLogs}
            className="px-4 py-2 bg-scum-accent/20 hover:bg-scum-accent/30 border border-scum-accent/50 rounded text-scum-accent transition-colors"
          >
            Tentar novamente
          </button>
        </div>
      </div>
    );
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      className="bg-scum-dark/60 backdrop-blur-sm rounded-lg border border-scum-accent/20 p-6"
    >
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-3">
          <FileText size={24} className="text-scum-accent" />
          <h2 className="text-xl font-bold text-scum-light">Logs de Acesso</h2>
        </div>
        
        <motion.button
          whileHover={{ scale: 1.05 }}
          whileTap={{ scale: 0.95 }}
          onClick={handleRefresh}
          disabled={refreshing}
          className={`
            flex items-center gap-2 px-3 py-2 rounded-lg border transition-all duration-200
            ${refreshing
              ? 'bg-scum-gray/30 border-scum-gray/50 text-scum-muted cursor-not-allowed'
              : 'bg-scum-secondary/30 border-scum-accent/30 text-scum-light hover:bg-scum-secondary/50 hover:border-scum-accent/50'
            }
          `}
          title="Atualizar logs"
        >
          <div className={`${refreshing ? 'animate-spin' : ''}`}>
            <RefreshCw size={16} />
          </div>
          <span className="text-sm font-medium">Atualizar</span>
        </motion.button>
      </div>

      {/* Logs Table */}
      <div className="overflow-x-auto">
        <table className="min-w-full divide-y divide-scum-accent/20">
          <thead className="bg-scum-gray/30">
            <tr>
              <th className="px-4 py-3 text-left text-xs font-medium text-scum-muted uppercase tracking-wider">
                Data/Hora
              </th>
              <th className="px-4 py-3 text-left text-xs font-medium text-scum-muted uppercase tracking-wider">
                Usuário
              </th>
              <th className="px-4 py-3 text-left text-xs font-medium text-scum-muted uppercase tracking-wider">
                Ação
              </th>
              <th className="px-4 py-3 text-left text-xs font-medium text-scum-muted uppercase tracking-wider">
                IP
              </th>
              <th className="px-4 py-3 text-left text-xs font-medium text-scum-muted uppercase tracking-wider">
                Status
              </th>
            </tr>
          </thead>
          <tbody className="bg-scum-dark/20 divide-y divide-scum-accent/10">
            {logs.length === 0 ? (
              <tr>
                <td colSpan={5} className="px-4 py-8 text-center text-scum-muted">
                  Nenhum log encontrado
                </td>
              </tr>
            ) : (
              logs.map((log) => (
                <motion.tr
                  key={log.id}
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  className="hover:bg-scum-gray/20 transition-colors"
                >
                  <td className="px-4 py-3 whitespace-nowrap text-sm text-scum-light font-mono">
                    {formatDate(log.timestamp)}
                  </td>
                  <td className="px-4 py-3 whitespace-nowrap text-sm text-scum-light">
                    {log.username}
                  </td>
                  <td className="px-4 py-3 whitespace-nowrap">
                    <div className="flex items-center gap-2">
                      {getActionIcon(log.action)}
                      <span className={`text-sm ${getActionColor(log.action)}`}>
                        {log.action}
                      </span>
                    </div>
                  </td>
                  <td className="px-4 py-3 whitespace-nowrap text-sm text-scum-muted font-mono">
                    {log.ip}
                  </td>
                  <td className="px-4 py-3 whitespace-nowrap">
                    <span className={`inline-flex items-center px-2 py-1 rounded-full text-xs font-semibold ${
                      log.success 
                        ? 'bg-green-400/20 text-green-400 border border-green-400/30' 
                        : 'bg-red-400/20 text-red-400 border border-red-400/30'
                    }`}>
                      {log.success ? 'Sucesso' : 'Falha'}
                    </span>
                  </td>
                </motion.tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {/* Footer */}
      <div className="mt-6 pt-4 border-t border-scum-accent/20">
        <div className="flex items-center justify-between text-sm text-scum-muted">
          <span>Total de logs: {logs.length}</span>
          <span className="text-xs">Última atualização: {new Date().toLocaleTimeString('pt-BR')}</span>
        </div>
      </div>
    </motion.div>
  );
};

export default AuthLogsView; 