import React, { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { Bot, Save, TestTube, Link, ChevronDown, ChevronUp } from 'lucide-react';
import { WebhookService } from '../services/webhookService';

interface DiscordWebhookCardProps {
  webhookName: string;
  webhookUrl: string;
  webhookType: string;
  onSave: (url: string, webhookType: string) => Promise<any>;
  onTest: (url: string, webhookType: string) => Promise<any>;
}

const DiscordWebhookCard: React.FC<DiscordWebhookCardProps> = ({
  webhookName,
  webhookUrl,
  webhookType,
  onSave,
  onTest
}) => {
  const [url, setUrl] = useState(webhookUrl);
  const [isLoading, setIsLoading] = useState(false);
  const [isExpanded, setIsExpanded] = useState(false);
  const [testResult, setTestResult] = useState<{
    success: boolean;
    message: string;
  } | null>(null);

  // Sincronizar o estado interno com a prop webhookUrl
  useEffect(() => {
    console.log(`🔄 Atualizando ${webhookName}:`, webhookUrl);
    setUrl(webhookUrl);
  }, [webhookUrl, webhookName]);

  const handleSave = async () => {
    if (!url.trim()) {
      setTestResult({
        success: false,
        message: 'Por favor, insira um endereço de webhook válido'
      });
      return;
    }

    setIsLoading(true);
    try {
      const result = await onSave(url.trim(), webhookType);
      setTestResult({
        success: true,
        message: result?.message || 'Webhook salvo com sucesso!'
      });
    } catch (error) {
      setTestResult({
        success: false,
        message: error instanceof Error ? error.message : 'Erro ao salvar webhook'
      });
    } finally {
      setIsLoading(false);
    }
  };

  const handleTest = async () => {
    if (!url.trim()) {
      setTestResult({
        success: false,
        message: 'Por favor, insira um endereço de webhook válido'
      });
      return;
    }

    setIsLoading(true);
    try {
      const result = await onTest(url.trim(), webhookType);
      setTestResult({
        success: true,
        message: result?.message || 'Teste realizado com sucesso! Webhook funcionando.'
      });
    } catch (error) {
      setTestResult({
        success: false,
        message: error instanceof Error ? error.message : 'Erro ao testar webhook. Verifique o endereço.'
      });
    } finally {
      setIsLoading(false);
    }
  };

  const validarWebhookUrl = (url: string): boolean => {
    const webhookRegex = /^https:\/\/discord\.com\/api\/webhooks\/\d+\/[a-zA-Z0-9_-]+$/;
    return webhookRegex.test(url);
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      className="scum-card overflow-hidden"
    >
      {/* Cabeçalho clicável */}
      <motion.button
        onClick={() => setIsExpanded(!isExpanded)}
        className="w-full p-6 flex items-center justify-between hover:bg-scum-gray/20 transition-colors"
      >
        <div className="flex items-center gap-3">
          <div className="p-2 bg-scum-accent/20 rounded-lg">
            <Bot size={20} className="text-scum-accent" />
          </div>
          <h3 className="text-lg font-bold text-scum-light military-text">
            {webhookName}
          </h3>
        </div>
        <motion.div
          animate={{ rotate: isExpanded ? 180 : 0 }}
          transition={{ duration: 0.2 }}
        >
          {isExpanded ? (
            <ChevronUp size={20} className="text-scum-muted" />
          ) : (
            <ChevronDown size={20} className="text-scum-muted" />
          )}
        </motion.div>
      </motion.button>

      {/* Conteúdo colapsável */}
      <motion.div
        initial={false}
        animate={{
          height: isExpanded ? "auto" : 0,
          opacity: isExpanded ? 1 : 0
        }}
        transition={{ duration: 0.3, ease: "easeInOut" }}
        className="overflow-hidden"
      >
        <div className="px-6 pb-6 space-y-4">
        {/* Campo de URL */}
        <div>
          <label className="block text-sm text-scum-muted mb-2 military-text">
            ENDEREÇO DO WEBHOOK
          </label>
          <div className="relative">
            <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
              <Link size={16} className="text-scum-muted" />
            </div>
            <input
              type="url"
              value={url}
              onChange={(e) => setUrl(e.target.value)}
              placeholder="https://discord.com/api/webhooks/..."
              className="w-full pl-10 pr-4 py-3 bg-scum-dark/50 border border-scum-gray rounded-lg text-scum-light placeholder-scum-muted focus:border-scum-accent focus:outline-none transition-colors"
            />
          </div>
        </div>

        {/* Botões */}
        <div className="flex gap-3">
          <motion.button
            whileHover={{ scale: 1.02 }}
            whileTap={{ scale: 0.98 }}
            onClick={handleSave}
            disabled={isLoading}
            className="flex-1 flex items-center justify-center gap-2 py-3 px-4 bg-scum-accent hover:bg-scum-accent/80 disabled:opacity-50 rounded-lg text-scum-dark font-bold military-text transition-colors"
          >
            <Save size={16} />
            {isLoading ? 'SALVANDO...' : 'SALVAR'}
          </motion.button>

          <motion.button
            whileHover={{ scale: 1.02 }}
            whileTap={{ scale: 0.98 }}
            onClick={handleTest}
            disabled={isLoading}
            className="flex-1 flex items-center justify-center gap-2 py-3 px-4 bg-scum-secondary hover:bg-scum-secondary/80 disabled:opacity-50 rounded-lg text-scum-light font-bold military-text transition-colors"
          >
            <TestTube size={16} />
            {isLoading ? 'TESTANDO...' : 'TESTE'}
          </motion.button>
        </div>

        {/* Resultado do teste */}
        {testResult && (
          <motion.div
            initial={{ opacity: 0, y: -10 }}
            animate={{ opacity: 1, y: 0 }}
            className={`p-3 rounded-lg border ${
              testResult.success
                ? 'bg-green-500/10 border-green-500/30 text-green-400'
                : 'bg-red-500/10 border-red-500/30 text-red-400'
            }`}
          >
            <p className="text-sm military-text">{testResult.message}</p>
          </motion.div>
        )}
        </div>
      </motion.div>
    </motion.div>
  );
};

export default DiscordWebhookCard; 