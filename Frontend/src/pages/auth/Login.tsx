import { motion, AnimatePresence } from 'framer-motion';
import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { User, Lock, Loader2, AlertCircle, Eye, EyeOff, X, Info } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import SsmLogo from '@/assets/logo/SSMlogo1.png';
import { authService } from '@/services/auth';
import { LanguageSwitcher } from '@/components/ui/LanguageSwitcher';
import backgroundImage from '@/assets/backgrounds/2421905-1920x1200-desktop-hd-scum-game-wallpaper-photo.jpg';

export default function Login() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const [showPassword, setShowPassword] = useState(false);
  const [rememberMe, setRememberMe] = useState(false);

  // Password reset states
  const [showRequestResetModal, setShowRequestResetModal] = useState(false);
  const [showResetPasswordModal, setShowResetPasswordModal] = useState(false);
  const [resetUsername, setResetUsername] = useState('');
  const [resetToken, setResetToken] = useState('');
  const [resetNewPassword, setResetNewPassword] = useState('');
  const [resetConfirmPassword, setResetConfirmPassword] = useState('');
  const [resetShowPassword, setResetShowPassword] = useState(false);
  const [resetShowConfirmPassword, setResetShowConfirmPassword] = useState(false);
  const [resetLoading, setResetLoading] = useState(false);
  const [resetError, setResetError] = useState('');
  const [resetSuccess, setResetSuccess] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');

    // Validação básica
    if (!username.trim() || !password.trim()) {
      setError(t('auth.login.errors.required'));
      return;
    }

    setLoading(true);

    try {
      const response = await authService.login(username.trim(), password, rememberMe);

      if (response.success) {
        if (response.data?.must_change_password) {
          // Redirecionar para mudança de senha
          navigate('/change-password', {
            state: { username: username.trim(), currentPassword: password }
          });
        } else {
          // Login bem-sucedido
          navigate('/');
        }
      } else {
        setError(response.error || t('auth.login.errors.invalidCredentials'));
      }
    } catch (err: any) {
      setError(t('auth.login.errors.networkError'));
      console.error('Erro ao fazer login:', err);
    } finally {
      setLoading(false);
    }
  };

  // Handle request password reset
  const handleRequestReset = async (e: React.FormEvent) => {
    e.preventDefault();
    setResetError('');

    if (!resetUsername.trim()) {
      setResetError(t('auth.passwordReset.requestReset.errors.networkError'));
      return;
    }

    setResetLoading(true);

    try {
      const response = await authService.requestPasswordReset(resetUsername.trim());
      
      if (response.success) {
        setResetSuccess(true);
        // Fechar modal após 3 segundos e abrir modal de reset
        setTimeout(() => {
          setShowRequestResetModal(false);
          setShowResetPasswordModal(true);
          setResetSuccess(false);
        }, 3000);
      } else {
        setResetError(response.message || t('auth.passwordReset.requestReset.errors.networkError'));
      }
    } catch (err: any) {
      setResetError(t('auth.passwordReset.requestReset.errors.networkError'));
      console.error('Erro ao solicitar reset:', err);
    } finally {
      setResetLoading(false);
    }
  };

  // Handle reset password
  const handleResetPassword = async (e: React.FormEvent) => {
    e.preventDefault();
    setResetError('');

    // Validações client-side
    if (!resetToken.trim() || !resetNewPassword.trim() || !resetConfirmPassword.trim()) {
      setResetError(t('auth.passwordReset.resetPassword.errors.required'));
      return;
    }

    if (resetNewPassword.length < 8) {
      setResetError(t('auth.passwordReset.resetPassword.errors.passwordMinLength'));
      return;
    }

    if (resetNewPassword !== resetConfirmPassword) {
      setResetError(t('auth.passwordReset.resetPassword.errors.passwordMismatch'));
      return;
    }

    setResetLoading(true);

    try {
      const response = await authService.resetPassword(resetToken.trim(), resetNewPassword);

      if (response.success) {
        setResetSuccess(true);
        // Fechar modal e limpar formulário após 2 segundos
        setTimeout(() => {
          closeResetPasswordModal();
          // Mostrar mensagem de sucesso no login
          setError('');
        }, 2000);
      } else {
        setResetError(response.error || t('auth.passwordReset.resetPassword.errors.tokenInvalid'));
      }
    } catch (err: any) {
      setResetError(t('auth.passwordReset.resetPassword.errors.networkError'));
      console.error('Erro ao resetar senha:', err);
    } finally {
      setResetLoading(false);
    }
  };

  // Reset modal states
  const closeRequestResetModal = () => {
    setShowRequestResetModal(false);
    setResetUsername('');
    setResetError('');
    setResetSuccess(false);
  };

  const closeResetPasswordModal = () => {
    setShowResetPasswordModal(false);
    setResetToken('');
    setResetNewPassword('');
    setResetConfirmPassword('');
    setResetError('');
    setResetSuccess(false);
  };

  return (
    <div className="min-h-screen flex items-center justify-center p-4 relative overflow-hidden">
      {/* Seletor de Idioma - Canto Superior Direito da Página */}
      <div className="absolute top-4 right-4 z-50">
        <LanguageSwitcher iconOnly={false} />
      </div>

      {/* Background Layers */}
      <div className="absolute inset-0 bg-scum-bg">
        {/* Layer 1: Background Image */}
        <motion.div
          initial={{ opacity: 0, scale: 1.1 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ duration: 1.5, ease: 'easeOut' }}
          className="absolute inset-0"
        >
          <img
            src={backgroundImage}
            alt=""
            className="w-full h-full object-cover md:object-center object-left"
            style={{ filter: 'blur(2px)' }}
          />
        </motion.div>
        
        {/* Layer 2: Dark Gradient Overlay */}
        <div className="absolute inset-0 bg-gradient-to-b from-black/60 via-black/50 to-black/60" />
        
        {/* Layer 3: Grid Pattern */}
        <div
          className="absolute inset-0 opacity-10"
          style={{
            backgroundImage: `
              linear-gradient(rgba(255,255,255,0.05) 1px, transparent 1px),
              linear-gradient(90deg, rgba(255,255,255,0.05) 1px, transparent 1px)
            `,
            backgroundSize: '50px 50px',
          }}
        />
        
        {/* Layer 4: Final Overlay (Contraste mais suave) */}
        <div className="absolute inset-0 bg-black/30" />
      </div>

      {/* Card de Login */}
      <motion.div
        initial={{ opacity: 0, y: 20, scale: 0.95 }}
        animate={{ opacity: 1, y: 0, scale: 1 }}
        transition={{ duration: 0.4, ease: 'easeOut' }}
        className="relative z-10 w-full max-w-md"
      >
        <div className="p-8 md:p-10 relative overflow-hidden min-h-[600px] md:min-h-[650px] flex items-center bg-black rounded-xl border border-white/5 shadow-lg">
          {/* Logo de Fundo */}
          <div className="absolute inset-0 flex items-center justify-center pointer-events-none">
            <motion.img
              src={SsmLogo}
              alt="SSM"
              className="object-contain opacity-15"
              initial={{ opacity: 0, scale: 1.05 }}
              animate={{ opacity: 0.15, scale: 1 }}
              transition={{ duration: 0.8, ease: 'easeOut' }}
              style={{ 
                width: '95%',
                height: '95%',
                maxWidth: '95%',
                maxHeight: '95%',
                objectFit: 'contain'
              }}
            />
          </div>

          {/* Formulário */}
          <form onSubmit={handleSubmit} className="space-y-4 relative z-10 w-full">
            {/* Username */}
            <div>
              <label className="block text-sm font-medium text-white/80 mb-2">
                {t('auth.login.username')}
              </label>
              <div className="relative">
                <div className="absolute left-3 top-1/2 -translate-y-1/2 z-20" style={{ filter: 'none', backdropFilter: 'none' }}>
                  <User className="text-white" size={20} style={{ opacity: 1 }} />
                </div>
                <input
                  type="text"
                  value={username}
                  onChange={(e) => setUsername(e.target.value)}
                  className="w-full pl-10 pr-4 py-3 bg-black/70 backdrop-blur-sm border border-white/20 rounded-lg text-white placeholder-white/40 focus:outline-none focus:ring-2 focus:ring-scum-orange focus:border-scum-orange transition-all duration-200"
                  placeholder={t('auth.login.usernamePlaceholder')}
                  required
                  disabled={loading}
                  autoComplete="username"
                />
              </div>
            </div>

            {/* Password */}
            <div>
              <label className="block text-sm font-medium text-white/80 mb-2">
                {t('auth.login.password')}
              </label>
              <div className="relative">
                <div className="absolute left-3 top-1/2 -translate-y-1/2 z-20" style={{ filter: 'none', backdropFilter: 'none' }}>
                  <Lock className="text-white" size={20} style={{ opacity: 1 }} />
                </div>
                <input
                  type={showPassword ? 'text' : 'password'}
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className="w-full pl-10 pr-12 py-3 bg-black/70 backdrop-blur-sm border border-white/20 rounded-lg text-white placeholder-white/40 focus:outline-none focus:ring-2 focus:ring-scum-orange focus:border-scum-orange transition-all duration-200"
                  placeholder={t('auth.login.passwordPlaceholder')}
                  required
                  disabled={loading}
                  autoComplete="current-password"
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-white/40 hover:text-white/80 transition-colors"
                  tabIndex={-1}
                >
                  {showPassword ? <EyeOff size={20} /> : <Eye size={20} />}
                </button>
              </div>
            </div>

            {/* Lembrar-me */}
            <div className="flex items-center">
              <input
                type="checkbox"
                id="rememberMe"
                checked={rememberMe}
                onChange={(e) => setRememberMe(e.target.checked)}
                className="w-4 h-4 rounded border-white/20 bg-black/70 text-scum-orange focus:ring-2 focus:ring-scum-orange focus:ring-offset-0 cursor-pointer"
                disabled={loading}
              />
              <label htmlFor="rememberMe" className="ml-2 text-sm text-white/80 cursor-pointer select-none">
                {t('auth.login.rememberMe')}
              </label>
            </div>

            {/* Mensagem de Erro */}
            {error && (
              <motion.div
                initial={{ opacity: 0, y: -10 }}
                animate={{ opacity: 1, y: 0 }}
                className="flex items-center gap-2 p-3 bg-red-500/20 backdrop-blur-sm border border-red-500/30 rounded-lg text-red-400 text-sm relative z-10"
              >
                <AlertCircle size={16} />
                <span>{error}</span>
              </motion.div>
            )}

            {/* Botão */}
            <button
              type="submit"
              disabled={loading}
              className="w-full py-3 bg-scum-orange hover:bg-scum-orange/90 text-white font-semibold rounded-lg transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2 mt-6 relative z-10"
            >
              {loading ? (
                <>
                  <Loader2 className="animate-spin" size={20} />
                  <span>{t('auth.login.loading')}</span>
                </>
              ) : (
                <span>{t('auth.login.submit')}</span>
              )}
            </button>

            {/* Link Esqueci minha senha */}
            <div className="text-center mt-4 relative z-10">
              <button
                type="button"
                onClick={() => setShowRequestResetModal(true)}
                className="text-sm text-scum-orange hover:text-scum-orange/80 transition-colors underline"
                disabled={loading}
              >
                {t('auth.passwordReset.forgotPassword')}
              </button>
            </div>
          </form>
        </div>
      </motion.div>

      {/* Modal: Solicitar Reset */}
      <AnimatePresence>
        {showRequestResetModal && (
          <>
            {/* Backdrop */}
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              onClick={closeRequestResetModal}
              className="fixed inset-0 bg-black/60 backdrop-blur-sm z-50"
            />
            
            {/* Modal */}
            <motion.div
              initial={{ opacity: 0, scale: 0.95, y: 20 }}
              animate={{ opacity: 1, scale: 1, y: 0 }}
              exit={{ opacity: 0, scale: 0.95, y: 20 }}
              className="fixed inset-0 z-50 flex items-center justify-center p-4"
              onClick={(e) => e.stopPropagation()}
            >
              <div className="bg-black rounded-xl border border-white/10 shadow-2xl w-full max-w-md p-6 md:p-8 relative">
                {/* Close button */}
                <button
                  onClick={closeRequestResetModal}
                  className="absolute top-4 right-4 text-white/40 hover:text-white transition-colors"
                >
                  <X size={24} />
                </button>

                {/* Header */}
                <div className="mb-6">
                  <h2 className="text-2xl font-bold text-white mb-2">
                    {t('auth.passwordReset.requestReset.title')}
                  </h2>
                  <p className="text-white/60 text-sm">
                    {t('auth.passwordReset.requestReset.subtitle')}
                  </p>
                </div>

                {/* Form */}
                <form onSubmit={handleRequestReset} className="space-y-4">
                  {/* Username */}
                  <div>
                    <label className="block text-sm font-medium text-white/80 mb-2">
                      {t('auth.passwordReset.requestReset.username')}
                    </label>
                    <div className="relative">
                      <div className="absolute left-3 top-1/2 -translate-y-1/2 z-20" style={{ filter: 'none', backdropFilter: 'none' }}>
                        <User className="text-white" size={20} style={{ opacity: 1 }} />
                      </div>
                      <input
                        type="text"
                        value={resetUsername}
                        onChange={(e) => setResetUsername(e.target.value)}
                        className="w-full pl-10 pr-4 py-3 bg-black/70 backdrop-blur-sm border border-white/20 rounded-lg text-white placeholder-white/40 focus:outline-none focus:ring-2 focus:ring-scum-orange focus:border-scum-orange transition-all duration-200"
                        placeholder={t('auth.passwordReset.requestReset.usernamePlaceholder')}
                        required
                        disabled={resetLoading}
                        autoComplete="username"
                      />
                    </div>
                  </div>

                  {/* Info message */}
                  <div className="flex items-start gap-2 p-3 bg-blue-500/20 backdrop-blur-sm border border-blue-500/30 rounded-lg text-blue-400 text-sm">
                    <Info size={16} className="mt-0.5 flex-shrink-0" />
                    <span>{t('auth.passwordReset.requestReset.info')}</span>
                  </div>

                  {/* Success message */}
                  {resetSuccess && (
                    <motion.div
                      initial={{ opacity: 0, y: -10 }}
                      animate={{ opacity: 1, y: 0 }}
                      className="flex items-center gap-2 p-3 bg-green-500/20 backdrop-blur-sm border border-green-500/30 rounded-lg text-green-400 text-sm"
                    >
                      <AlertCircle size={16} />
                      <span>{t('auth.passwordReset.requestReset.success')}</span>
                    </motion.div>
                  )}

                  {/* Error message */}
                  {resetError && !resetSuccess && (
                    <motion.div
                      initial={{ opacity: 0, y: -10 }}
                      animate={{ opacity: 1, y: 0 }}
                      className="flex items-center gap-2 p-3 bg-red-500/20 backdrop-blur-sm border border-red-500/30 rounded-lg text-red-400 text-sm"
                    >
                      <AlertCircle size={16} />
                      <span>{resetError}</span>
                    </motion.div>
                  )}

                  {/* Buttons */}
                  <div className="flex gap-3 mt-6">
                    <button
                      type="button"
                      onClick={closeRequestResetModal}
                      disabled={resetLoading}
                      className="flex-1 py-3 bg-white/10 hover:bg-white/20 text-white font-semibold rounded-lg transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed"
                    >
                      Cancelar
                    </button>
                    <button
                      type="submit"
                      disabled={resetLoading}
                      className="flex-1 py-3 bg-scum-orange hover:bg-scum-orange/90 text-white font-semibold rounded-lg transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
                    >
                      {resetLoading ? (
                        <>
                          <Loader2 className="animate-spin" size={20} />
                          <span>{t('auth.passwordReset.requestReset.loading')}</span>
                        </>
                      ) : (
                        <span>{t('auth.passwordReset.requestReset.submit')}</span>
                      )}
                    </button>
                  </div>
                </form>
              </div>
            </motion.div>
          </>
        )}
      </AnimatePresence>

      {/* Modal: Resetar Senha */}
      <AnimatePresence>
        {showResetPasswordModal && (
          <>
            {/* Backdrop */}
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              onClick={closeResetPasswordModal}
              className="fixed inset-0 bg-black/60 backdrop-blur-sm z-50"
            />
            
            {/* Modal */}
            <motion.div
              initial={{ opacity: 0, scale: 0.95, y: 20 }}
              animate={{ opacity: 1, scale: 1, y: 0 }}
              exit={{ opacity: 0, scale: 0.95, y: 20 }}
              className="fixed inset-0 z-50 flex items-center justify-center p-4"
              onClick={(e) => e.stopPropagation()}
            >
              <div className="bg-black rounded-xl border border-white/10 shadow-2xl w-full max-w-md p-6 md:p-8 relative max-h-[90vh] overflow-y-auto">
                {/* Close button */}
                <button
                  onClick={closeResetPasswordModal}
                  className="absolute top-4 right-4 text-white/40 hover:text-white transition-colors"
                >
                  <X size={24} />
                </button>

                {/* Header */}
                <div className="mb-6">
                  <h2 className="text-2xl font-bold text-white mb-2">
                    {t('auth.passwordReset.resetPassword.title')}
                  </h2>
                  <p className="text-white/60 text-sm">
                    {t('auth.passwordReset.resetPassword.subtitle')}
                  </p>
                </div>

                {/* Form */}
                <form onSubmit={handleResetPassword} className="space-y-4">
                  {/* Token */}
                  <div>
                    <label className="block text-sm font-medium text-white/80 mb-2">
                      {t('auth.passwordReset.resetPassword.token')}
                    </label>
                    <input
                      type="text"
                      value={resetToken}
                      onChange={(e) => setResetToken(e.target.value)}
                      className="w-full px-4 py-3 bg-black/70 backdrop-blur-sm border border-white/20 rounded-lg text-white placeholder-white/40 focus:outline-none focus:ring-2 focus:ring-scum-orange focus:border-scum-orange transition-all duration-200"
                      placeholder={t('auth.passwordReset.resetPassword.tokenPlaceholder')}
                      required
                      disabled={resetLoading}
                    />
                  </div>

                  {/* New Password */}
                  <div>
                    <label className="block text-sm font-medium text-white/80 mb-2">
                      {t('auth.passwordReset.resetPassword.newPassword')}
                    </label>
                    <div className="relative">
                      <div className="absolute left-3 top-1/2 -translate-y-1/2 z-20" style={{ filter: 'none', backdropFilter: 'none' }}>
                        <Lock className="text-white" size={20} style={{ opacity: 1 }} />
                      </div>
                      <input
                        type={resetShowPassword ? 'text' : 'password'}
                        value={resetNewPassword}
                        onChange={(e) => setResetNewPassword(e.target.value)}
                        className="w-full pl-10 pr-12 py-3 bg-black/70 backdrop-blur-sm border border-white/20 rounded-lg text-white placeholder-white/40 focus:outline-none focus:ring-2 focus:ring-scum-orange focus:border-scum-orange transition-all duration-200"
                        placeholder={t('auth.passwordReset.resetPassword.newPasswordPlaceholder')}
                        required
                        disabled={resetLoading}
                        minLength={8}
                        autoComplete="new-password"
                      />
                      <button
                        type="button"
                        onClick={() => setResetShowPassword(!resetShowPassword)}
                        className="absolute right-3 top-1/2 -translate-y-1/2 text-white/40 hover:text-white/80 transition-colors"
                        tabIndex={-1}
                      >
                        {resetShowPassword ? <EyeOff size={20} /> : <Eye size={20} />}
                      </button>
                    </div>
                  </div>

                  {/* Confirm Password */}
                  <div>
                    <label className="block text-sm font-medium text-white/80 mb-2">
                      {t('auth.passwordReset.resetPassword.confirmPassword')}
                    </label>
                    <div className="relative">
                      <div className="absolute left-3 top-1/2 -translate-y-1/2 z-20" style={{ filter: 'none', backdropFilter: 'none' }}>
                        <Lock className="text-white" size={20} style={{ opacity: 1 }} />
                      </div>
                      <input
                        type={resetShowConfirmPassword ? 'text' : 'password'}
                        value={resetConfirmPassword}
                        onChange={(e) => setResetConfirmPassword(e.target.value)}
                        className="w-full pl-10 pr-12 py-3 bg-black/70 backdrop-blur-sm border border-white/20 rounded-lg text-white placeholder-white/40 focus:outline-none focus:ring-2 focus:ring-scum-orange focus:border-scum-orange transition-all duration-200"
                        placeholder={t('auth.passwordReset.resetPassword.confirmPasswordPlaceholder')}
                        required
                        disabled={resetLoading}
                        minLength={8}
                        autoComplete="new-password"
                      />
                      <button
                        type="button"
                        onClick={() => setResetShowConfirmPassword(!resetShowConfirmPassword)}
                        className="absolute right-3 top-1/2 -translate-y-1/2 text-white/40 hover:text-white/80 transition-colors"
                        tabIndex={-1}
                      >
                        {resetShowConfirmPassword ? <EyeOff size={20} /> : <Eye size={20} />}
                      </button>
                    </div>
                  </div>

                  {/* Success message */}
                  {resetSuccess && (
                    <motion.div
                      initial={{ opacity: 0, y: -10 }}
                      animate={{ opacity: 1, y: 0 }}
                      className="flex items-center gap-2 p-3 bg-green-500/20 backdrop-blur-sm border border-green-500/30 rounded-lg text-green-400 text-sm"
                    >
                      <AlertCircle size={16} />
                      <span>{t('auth.passwordReset.resetPassword.success')}</span>
                    </motion.div>
                  )}

                  {/* Error message */}
                  {resetError && !resetSuccess && (
                    <motion.div
                      initial={{ opacity: 0, y: -10 }}
                      animate={{ opacity: 1, y: 0 }}
                      className="flex items-center gap-2 p-3 bg-red-500/20 backdrop-blur-sm border border-red-500/30 rounded-lg text-red-400 text-sm"
                    >
                      <AlertCircle size={16} />
                      <span>{resetError}</span>
                    </motion.div>
                  )}

                  {/* Buttons */}
                  <div className="flex gap-3 mt-6">
                    <button
                      type="button"
                      onClick={closeResetPasswordModal}
                      disabled={resetLoading}
                      className="flex-1 py-3 bg-white/10 hover:bg-white/20 text-white font-semibold rounded-lg transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed"
                    >
                      Cancelar
                    </button>
                    <button
                      type="submit"
                      disabled={resetLoading}
                      className="flex-1 py-3 bg-scum-orange hover:bg-scum-orange/90 text-white font-semibold rounded-lg transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
                    >
                      {resetLoading ? (
                        <>
                          <Loader2 className="animate-spin" size={20} />
                          <span>{t('auth.passwordReset.resetPassword.loading')}</span>
                        </>
                      ) : (
                        <span>{t('auth.passwordReset.resetPassword.submit')}</span>
                      )}
                    </button>
                  </div>
                </form>
              </div>
            </motion.div>
          </>
        )}
      </AnimatePresence>
    </div>
  );
}

