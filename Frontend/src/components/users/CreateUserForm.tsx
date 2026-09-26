import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { UserPlus, Loader2, X } from 'lucide-react';
import { authService } from '@/services/auth';
import PlayerSearch from './PlayerSearch';
import Swal from 'sweetalert2';

interface CreateUserFormProps {
  onSuccess: () => void;
  onCancel: () => void;
}

export default function CreateUserForm({ onSuccess, onCancel }: CreateUserFormProps) {
  const { t } = useTranslation();
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [role, setRole] = useState<'admin' | 'moderator'>('moderator');
  const [steamId, setSteamId] = useState<string | undefined>();
  const [loading, setLoading] = useState(false);
  const [errors, setErrors] = useState<Record<string, string>>({});

  const validate = (): boolean => {
    const newErrors: Record<string, string> = {};

    if (!username.trim()) {
      newErrors.username = t('settings.users.errors.usernameExists');
    } else if (username.length < 3) {
      newErrors.username = 'Username deve ter pelo menos 3 caracteres';
    }

    if (!password) {
      newErrors.password = t('settings.users.errors.invalidPassword');
    } else if (password.length < 8) {
      newErrors.password = t('settings.users.errors.invalidPassword');
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    if (!validate()) {
      return;
    }

    setLoading(true);
    setErrors({});

    try {
      const response = await authService.createUser(username, password, role, steamId);

      // Log para debug
      console.log('CreateUser response:', response);

      if (response.success) {
        await Swal.fire({
          icon: 'success',
          title: t('settings.users.createSuccess.title'),
          text: t('settings.users.createSuccess.text', { username }),
          confirmButtonColor: '#f97316',
        });

        // Limpar formulário
        setUsername('');
        setPassword('');
        setRole('moderator');
        setSteamId(undefined);
        setErrors({});

        onSuccess();
      } else {
        // Se não tem success mas também não tem erro definido, pode ter sido criado mesmo assim
        const errorMessage = response.error || t('settings.users.errors.createFailed');
        setErrors({ submit: errorMessage });
        
        await Swal.fire({
          icon: 'warning',
          title: t('settings.users.errors.createFailed'),
          text: errorMessage,
          confirmButtonColor: '#f97316',
        });
        
        // Mesmo com erro, tentar recarregar a lista (pode ter sido criado)
        setTimeout(() => {
          onSuccess();
        }, 1000);
      }
    } catch (error: any) {
      console.error('Erro ao criar usuário:', error);
      const errorMessage = error.message || t('settings.users.errors.createFailed');
      setErrors({ submit: errorMessage });
      
      await Swal.fire({
        icon: 'error',
        title: t('settings.users.errors.createFailed'),
        text: errorMessage,
        confirmButtonColor: '#f97316',
      });
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="card p-4 sm:p-6">
      <div className="flex items-center justify-between mb-4 sm:mb-6">
        <h3 className="text-lg sm:text-xl font-semibold text-white flex items-center gap-2">
          <UserPlus size={20} className="sm:w-6 sm:h-6 flex-shrink-0" />
          <span className="truncate">{t('settings.users.create.title')}</span>
        </h3>
        <button
          onClick={onCancel}
          className="text-white/50 hover:text-white transition-colors flex-shrink-0"
          type="button"
        >
          <X size={20} />
        </button>
      </div>

      <form onSubmit={handleSubmit} className="space-y-4">
        <div>
          <label className="block text-sm font-medium text-white/80 mb-2">
            {t('settings.users.create.username')} *
          </label>
          <input
            type="text"
            value={username}
            onChange={(e) => {
              setUsername(e.target.value);
              if (errors.username) setErrors({ ...errors, username: '' });
            }}
            className={`w-full px-4 py-2 bg-white/5 border rounded-lg text-white placeholder-white/50 focus:outline-none focus:ring-2 focus:ring-scum-orange ${
              errors.username ? 'border-red-500' : 'border-white/10'
            }`}
            placeholder={t('settings.users.create.username')}
            required
          />
          {errors.username && (
            <p className="mt-1 text-sm text-red-400">{errors.username}</p>
          )}
        </div>

        <div>
          <label className="block text-sm font-medium text-white/80 mb-2">
            {t('settings.users.create.password')} *
          </label>
          <input
            type="password"
            value={password}
            onChange={(e) => {
              setPassword(e.target.value);
              if (errors.password) setErrors({ ...errors, password: '' });
            }}
            className={`w-full px-4 py-2 bg-white/5 border rounded-lg text-white placeholder-white/50 focus:outline-none focus:ring-2 focus:ring-scum-orange ${
              errors.password ? 'border-red-500' : 'border-white/10'
            }`}
            placeholder={t('settings.users.create.passwordHint')}
            required
            minLength={8}
          />
          {errors.password && (
            <p className="mt-1 text-sm text-red-400">{errors.password}</p>
          )}
          <p className="mt-1 text-xs text-white/50">{t('settings.users.create.passwordHint')}</p>
        </div>

        <div>
          <label className="block text-sm font-medium text-white/80 mb-2">
            {t('settings.users.create.role')} *
          </label>
          <select
            value={role}
            onChange={(e) => setRole(e.target.value as 'admin' | 'moderator')}
            className="w-full px-4 py-2 bg-white/5 border border-white/10 rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-scum-orange"
          >
            <option value="moderator">{t('settings.users.roles.moderator')}</option>
            <option value="admin">{t('settings.users.roles.admin')}</option>
          </select>
        </div>

        <div>
          <label className="block text-sm font-medium text-white/80 mb-2">
            {t('settings.users.create.steamId')}
          </label>
          <PlayerSearch
            value={steamId}
            onChange={(id) => setSteamId(id)}
          />
        </div>

        {errors.submit && (
          <div className="p-3 bg-red-500/20 border border-red-500/50 rounded-lg">
            <p className="text-sm text-red-400">{errors.submit}</p>
          </div>
        )}

        <div className="flex flex-col sm:flex-row gap-3 pt-4">
          <button
            type="submit"
            disabled={loading}
            className="flex-1 px-4 py-2 bg-scum-orange text-white rounded-lg font-medium hover:bg-scum-orange/90 transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2 text-sm sm:text-base"
          >
            {loading ? (
              <>
                <Loader2 size={16} className="sm:w-[18px] sm:h-[18px] animate-spin" />
                <span>{t('settings.users.create.submit')}...</span>
              </>
            ) : (
              t('settings.users.create.submit')
            )}
          </button>
          <button
            type="button"
            onClick={onCancel}
            className="px-4 py-2 bg-white/5 text-white rounded-lg font-medium hover:bg-white/10 transition-colors text-sm sm:text-base"
          >
            {t('settings.users.create.cancel')}
          </button>
        </div>
      </form>
    </div>
  );
}

