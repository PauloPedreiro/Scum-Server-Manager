import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import { Shield, Eye, EyeOff, AlertCircle, Users } from 'lucide-react';
import { useAuth } from '../hooks/useAuth';
import ScumBackground from '../components/ScumBackground';
import { ServerStatus } from '../components/ScumIcons';

const Login: React.FC = () => {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState('');
  
  const { login, isAuthenticated, isLoading: authLoading } = useAuth();
  const navigate = useNavigate();

  console.log('[LOGIN COMPONENT] Renderizando, isAuthenticated:', isAuthenticated);

  // Se já está autenticado, redirecionar para dashboard
  useEffect(() => {
    if (isAuthenticated && !authLoading) {
      console.log('[LOGIN COMPONENT] Usuário já autenticado, redirecionando para dashboard');
      navigate('/dashboard');
    }
  }, [isAuthenticated, authLoading]);

  // Se está carregando ou já autenticado, mostrar loading
  if (authLoading || isAuthenticated) {
    return (
      <ScumBackground imageIndex={0}>
        <div className="flex items-center justify-center min-h-screen p-4">
          <div className="text-scum-light text-center">
            <div className="w-8 h-8 border-2 border-scum-accent border-t-transparent rounded-full animate-spin mx-auto mb-4"></div>
            <p className="text-sm">Verificando autenticação...</p>
          </div>
        </div>
      </ScumBackground>
    );
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    if (!username || !password) {
      setError('Preencha todos os campos');
      return;
    }

    try {
      setIsLoading(true);
      setError('');
      console.log('[LOGIN] Iniciando login...');
      await login(username, password);
      console.log('[LOGIN] Login bem-sucedido, navegando para dashboard...');
      navigate('/dashboard');
    } catch (err: any) {
      console.error('[LOGIN] Erro no login:', err);
      setError(err.message || 'Erro ao fazer login');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <ScumBackground imageIndex={0}>
      <div className="flex items-center justify-center min-h-screen p-4">
        <motion.div
          initial={{ opacity: 0, y: 50 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.8, ease: "easeOut" }}
          className="w-full max-w-md"
        >
          {/* Header com logo SCUM */}
          <div className="text-center mb-8">
            <motion.div
              initial={{ scale: 0 }}
              animate={{ scale: 1 }}
              transition={{ delay: 0.2, type: "spring", stiffness: 200 }}
              className="inline-flex items-center justify-center w-16 h-16 sm:w-20 sm:h-20 bg-scum-secondary/80 backdrop-blur-sm rounded-full mb-6 glow border-2 border-scum-accent/50"
            >
              <Shield className="w-8 h-8 sm:w-10 sm:h-10 text-scum-light" />
            </motion.div>
            
            <motion.h1
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ delay: 0.4 }}
              className="text-3xl sm:text-4xl font-bold text-scum-light mb-2 military-text text-shadow"
            >
              SCUM SERVER
            </motion.h1>
            
            <motion.p
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ delay: 0.6 }}
              className="text-scum-muted text-xs sm:text-sm digital-text tracking-wider"
            >
              ADMINISTRATION PANEL
            </motion.p>
          </div>

          {/* Formulário de Login */}
          <motion.form
            initial={{ opacity: 0, y: 30 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.8, duration: 0.6 }}
            onSubmit={handleSubmit}
            className="space-y-6"
          >
            {/* Campo Username */}
            <div className="space-y-2">
              <label htmlFor="username" className="block text-sm font-medium text-scum-light">
                Usuário
              </label>
              <div className="relative">
                <input
                  id="username"
                  type="text"
                  value={username}
                  onChange={(e) => setUsername(e.target.value)}
                  className="scum-input-mobile w-full"
                  placeholder="Digite seu usuário"
                  disabled={isLoading}
                />
                <Users className="absolute right-3 top-1/2 transform -translate-y-1/2 text-scum-muted w-5 h-5" />
              </div>
            </div>

            {/* Campo Password */}
            <div className="space-y-2">
              <label htmlFor="password" className="block text-sm font-medium text-scum-light">
                Senha
              </label>
              <div className="relative">
                <input
                  id="password"
                  type={showPassword ? 'text' : 'password'}
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className="scum-input-mobile w-full pr-12"
                  placeholder="Digite sua senha"
                  disabled={isLoading}
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute right-3 top-1/2 transform -translate-y-1/2 text-scum-muted hover:text-scum-light transition-colors"
                >
                  {showPassword ? <EyeOff className="w-5 h-5" /> : <Eye className="w-5 h-5" />}
                </button>
              </div>
            </div>

            {/* Mensagem de Erro */}
            {error && (
              <motion.div
                initial={{ opacity: 0, scale: 0.95 }}
                animate={{ opacity: 1, scale: 1 }}
                className="flex items-center gap-2 p-3 bg-scum-danger/20 border border-scum-danger/50 rounded-lg text-scum-light text-sm"
              >
                <AlertCircle className="w-5 h-5 text-scum-danger flex-shrink-0" />
                <span>{error}</span>
              </motion.div>
            )}

            {/* Botão de Login */}
            <motion.button
              type="submit"
              disabled={isLoading}
              whileHover={{ scale: 1.02 }}
              whileTap={{ scale: 0.98 }}
              className="w-full scum-button-mobile disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {isLoading ? (
                <div className="flex items-center justify-center gap-2">
                  <div className="w-4 h-4 border-2 border-scum-light border-t-transparent rounded-full animate-spin"></div>
                  <span>Entrando...</span>
                </div>
              ) : (
                <span>Entrar</span>
              )}
            </motion.button>
          </motion.form>

          {/* Footer */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 1.2 }}
            className="mt-8 text-center"
          >
            <p className="text-xs text-scum-muted digital-text">
              Sistema de Administração SCUM Server
            </p>
            <p className="text-xs text-scum-muted mt-1">
              Acesso restrito a administradores
            </p>
          </motion.div>
        </motion.div>
      </div>
    </ScumBackground>
  );
};

export default Login; 