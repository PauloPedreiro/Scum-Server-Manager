import { motion } from 'framer-motion';
import { useState, useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import { Lock, Loader2, AlertCircle, CheckCircle2, Eye, EyeOff } from 'lucide-react';
import { useNavigate, useLocation } from 'react-router-dom';
import SsmLogo from '@/assets/logo/SSMlogo1.png';
import { authService } from '@/services/auth';
import Swal from 'sweetalert2';
import backgroundImage from '@/assets/backgrounds/2421905-1920x1200-desktop-hd-scum-game-wallpaper-photo.jpg';

export default function ChangePassword() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const location = useLocation();
  const [currentPassword, setCurrentPassword] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const [username, setUsername] = useState<string | null>(null);
  const [showCurrentPassword, setShowCurrentPassword] = useState(false);
  const [showNewPassword, setShowNewPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);

  // Se veio do primeiro login, usar dados do state
  useEffect(() => {
    if (location.state?.username && location.state?.currentPassword) {
      setUsername(location.state.username);
      setCurrentPassword(location.state.currentPassword);
    }
  }, [location]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');

    // Validações
    if (!currentPassword.trim() || !newPassword.trim() || !confirmPassword.trim()) {
      setError(t('auth.changePassword.errors.required'));
      return;
    }

    if (newPassword.length < 8) {
      setError(t('auth.changePassword.errors.minLength'));
      return;
    }

    if (newPassword !== confirmPassword) {
      setError(t('auth.changePassword.errors.mismatch'));
      return;
    }

    setLoading(true);

    try {
      const response = await authService.changePassword(
        currentPassword,
        newPassword,
        username || undefined
      );

      if (response.success) {
        // Senha alterada com sucesso
        await Swal.fire({
          icon: 'success',
          title: t('auth.changePassword.success'),
          text: t('auth.changePassword.success'),
          confirmButtonColor: '#f97316',
        });

        // Redirecionar para home
        navigate('/');
      } else {
        setError(response.error || t('auth.changePassword.errors.currentIncorrect'));
      }
    } catch (err: any) {
      setError(t('auth.changePassword.errors.networkError'));
      console.error('Erro ao alterar senha:', err);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center p-4 relative overflow-hidden">
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

      {/* Card de Mudança de Senha */}
      <motion.div
        initial={{ opacity: 0, y: 20, scale: 0.95 }}
        animate={{ opacity: 1, y: 0, scale: 1 }}
        transition={{ duration: 0.4, ease: 'easeOut' }}
        className="relative z-10 w-full max-w-md"
      >
        <div className="card p-8 md:p-10">
          {/* Logo e Título */}
          <div className="text-center mb-8">
            <motion.img
              src={SsmLogo}
              alt="SSM"
              className="h-40 w-40 md:h-48 md:w-48 mx-auto mb-6 rounded-sm"
              initial={{ opacity: 0, scale: 0.9 }}
              animate={{ opacity: 1, scale: 1 }}
              transition={{ duration: 0.5, ease: 'easeOut' }}
            />
            <h1 className="text-2xl font-bold text-white mb-2">
              {t('auth.changePassword.title')}
            </h1>
            <p className="text-white/60 text-sm md:text-base">
              {t('auth.changePassword.subtitle')}
            </p>
          </div>

          {/* Formulário */}
          <form onSubmit={handleSubmit} className="space-y-4">
            {/* Senha Atual */}
            <div>
              <label className="block text-sm font-medium text-white/80 mb-2">
                {t('auth.changePassword.currentPassword')}
              </label>
              <div className="relative">
                <Lock className="absolute left-3 top-1/2 -translate-y-1/2 text-white/40" size={20} />
                <input
                  type={showCurrentPassword ? 'text' : 'password'}
                  value={currentPassword}
                  onChange={(e) => setCurrentPassword(e.target.value)}
                  className="w-full pl-10 pr-12 py-3 bg-black/30 border border-white/10 rounded-lg text-white placeholder-white/40 focus:outline-none focus:ring-2 focus:ring-scum-orange focus:border-scum-orange transition-all duration-200"
                  placeholder={t('auth.changePassword.currentPasswordPlaceholder')}
                  required
                  disabled={loading}
                  autoComplete="current-password"
                />
                <button
                  type="button"
                  onClick={() => setShowCurrentPassword(!showCurrentPassword)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-white/40 hover:text-white/80 transition-colors"
                  tabIndex={-1}
                >
                  {showCurrentPassword ? <EyeOff size={20} /> : <Eye size={20} />}
                </button>
              </div>
            </div>

            {/* Nova Senha */}
            <div>
              <label className="block text-sm font-medium text-white/80 mb-2">
                {t('auth.changePassword.newPassword')}
              </label>
              <div className="relative">
                <Lock className="absolute left-3 top-1/2 -translate-y-1/2 text-white/40" size={20} />
                <input
                  type={showNewPassword ? 'text' : 'password'}
                  value={newPassword}
                  onChange={(e) => setNewPassword(e.target.value)}
                  className="w-full pl-10 pr-12 py-3 bg-black/30 border border-white/10 rounded-lg text-white placeholder-white/40 focus:outline-none focus:ring-2 focus:ring-scum-orange focus:border-scum-orange transition-all duration-200"
                  placeholder={t('auth.changePassword.newPasswordPlaceholder')}
                  required
                  minLength={8}
                  disabled={loading}
                  autoComplete="new-password"
                />
                <button
                  type="button"
                  onClick={() => setShowNewPassword(!showNewPassword)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-white/40 hover:text-white/80 transition-colors"
                  tabIndex={-1}
                >
                  {showNewPassword ? <EyeOff size={20} /> : <Eye size={20} />}
                </button>
              </div>
              {newPassword.length > 0 && newPassword.length < 8 && (
                <p className="text-xs text-yellow-400 mt-1">
                  {t('auth.changePassword.errors.minLength')}
                </p>
              )}
            </div>

            {/* Confirmar Nova Senha */}
            <div>
              <label className="block text-sm font-medium text-white/80 mb-2">
                {t('auth.changePassword.confirmPassword')}
              </label>
              <div className="relative">
                <Lock className="absolute left-3 top-1/2 -translate-y-1/2 text-white/40" size={20} />
                <input
                  type={showConfirmPassword ? 'text' : 'password'}
                  value={confirmPassword}
                  onChange={(e) => setConfirmPassword(e.target.value)}
                  className="w-full pl-10 pr-12 py-3 bg-black/30 border border-white/10 rounded-lg text-white placeholder-white/40 focus:outline-none focus:ring-2 focus:ring-scum-orange focus:border-scum-orange transition-all duration-200"
                  placeholder={t('auth.changePassword.confirmPasswordPlaceholder')}
                  required
                  minLength={8}
                  disabled={loading}
                  autoComplete="new-password"
                />
                <button
                  type="button"
                  onClick={() => setShowConfirmPassword(!showConfirmPassword)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-white/40 hover:text-white/80 transition-colors"
                  tabIndex={-1}
                >
                  {showConfirmPassword ? <EyeOff size={20} /> : <Eye size={20} />}
                </button>
              </div>
              {confirmPassword.length > 0 && newPassword !== confirmPassword && (
                <p className="text-xs text-red-400 mt-1">
                  {t('auth.changePassword.errors.mismatch')}
                </p>
              )}
              {confirmPassword.length > 0 && newPassword === confirmPassword && newPassword.length >= 8 && (
                <p className="text-xs text-green-400 mt-1 flex items-center gap-1">
                  <CheckCircle2 size={12} />
                  Senhas coincidem
                </p>
              )}
            </div>

            {/* Mensagem de Erro */}
            {error && (
              <motion.div
                initial={{ opacity: 0, y: -10 }}
                animate={{ opacity: 1, y: 0 }}
                className="flex items-center gap-2 p-3 bg-red-500/10 border border-red-500/20 rounded-lg text-red-400 text-sm"
              >
                <AlertCircle size={16} />
                <span>{error}</span>
              </motion.div>
            )}

            {/* Botão */}
            <button
              type="submit"
              disabled={loading || newPassword.length < 8 || newPassword !== confirmPassword}
              className="w-full py-3 bg-scum-orange hover:bg-scum-orange/90 text-white font-semibold rounded-lg transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2 mt-6"
            >
              {loading ? (
                <>
                  <Loader2 className="animate-spin" size={20} />
                  <span>{t('auth.changePassword.loading')}</span>
                </>
              ) : (
                <span>{t('auth.changePassword.submit')}</span>
              )}
            </button>
          </form>
        </div>
      </motion.div>
    </div>
  );
}

