import { useState, useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import { Users, UserPlus, RefreshCw, Loader2, ShieldAlert } from 'lucide-react';
import { authService, User } from '@/services/auth';
import UserTable from '@/components/users/UserTable';
import CreateUserForm from '@/components/users/CreateUserForm';
import SearchBar from '@/components/ui/SearchBar';
import Swal from 'sweetalert2';

interface UsersTabProps {
  searchQuery?: string;
  onSearchChange?: (query: string) => void;
}

export default function UsersTab({ searchQuery = '', onSearchChange }: UsersTabProps) {
  const { t } = useTranslation();
  const [users, setUsers] = useState<User[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [showCreateForm, setShowCreateForm] = useState(false);
  const [filteredUsers, setFilteredUsers] = useState<User[]>([]);

  // Verificar se é admin
  const isAdmin = authService.isAdmin();

  // Carregar usuários
  const loadUsers = async () => {
    if (!isAdmin) {
      setError(t('settings.users.errors.adminRequired'));
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const usersList = await authService.listUsers();
      console.log('UsersTab - Usuários recebidos:', usersList);
      console.log('UsersTab - Quantidade:', usersList?.length || 0);
      
      if (usersList && Array.isArray(usersList)) {
        setUsers(usersList);
        setError(null);
      } else {
        console.warn('UsersTab - usersList não é um array válido:', usersList);
        setUsers([]);
        setError('Formato de resposta inválido do servidor');
      }
    } catch (err: any) {
      console.error('Erro ao carregar usuários:', err);
      console.error('Erro completo:', err.response?.data || err);
      
      const errorMessage = err.message || t('settings.users.errors.loadFailed');
      setError(errorMessage);
      setUsers([]); // Garantir que users está vazio em caso de erro
      
      // Se o erro é sobre coluna não encontrada, é problema do backend
      if (errorMessage.includes('no such column') || errorMessage.includes('p.name')) {
        await Swal.fire({
          icon: 'warning',
          title: t('settings.users.errors.loadFailed'),
          text: 'Erro no backend: coluna não encontrada. Verifique os logs do backend.',
          confirmButtonColor: '#f97316',
        });
      } else if (err.message === 'Not authenticated') {
        await Swal.fire({
          icon: 'error',
          title: t('settings.users.errors.adminRequired'),
          text: t('settings.users.errors.adminRequired'),
          confirmButtonColor: '#f97316',
        });
      } else {
        // Mostrar erro genérico
        console.error('Erro desconhecido ao carregar usuários:', err);
      }
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadUsers();
  }, []);

  // Filtrar usuários baseado na busca
  useEffect(() => {
    console.log('UsersTab - Filtrar usuários:', { 
      usersCount: users.length, 
      searchQuery, 
      users: users.map(u => ({ id: u.id, username: u.username }))
    });
    
    if (!searchQuery.trim()) {
      console.log('UsersTab - Sem busca, usando todos os usuários');
      setFilteredUsers(users);
      return;
    }

    const query = searchQuery.toLowerCase();
    const filtered = users.filter(
      (user) =>
        user.username.toLowerCase().includes(query) ||
        user.role.toLowerCase().includes(query) ||
        (user.player_name && user.player_name.toLowerCase().includes(query)) ||
        (user.steam_id && user.steam_id.includes(query))
    );

    console.log('UsersTab - Usuários filtrados:', filtered.length);
    setFilteredUsers(filtered);
  }, [searchQuery, users]);

  const handleCreateSuccess = () => {
    setShowCreateForm(false);
    loadUsers();
  };

  const handleUpdate = () => {
    loadUsers();
  };

  // Se não for admin, mostrar mensagem de acesso negado
  if (!isAdmin) {
    return (
      <div className="card p-8 text-center">
        <ShieldAlert className="mx-auto mb-4 text-red-400" size={48} />
        <h3 className="text-xl font-semibold text-white mb-2">{t('settings.users.errors.adminRequired')}</h3>
        <p className="text-white/60">{t('settings.users.errors.adminRequired')}</p>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="card p-3 sm:p-4">
        <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 sm:gap-4">
          <div className="flex-1 min-w-0">
            <h2 className="text-lg sm:text-xl font-semibold text-white flex items-center gap-2">
              <Users size={20} className="sm:w-6 sm:h-6 flex-shrink-0" />
              <span className="truncate">{t('settings.users.title')}</span>
            </h2>
            <p className="text-white/60 text-xs sm:text-sm mt-1">{t('settings.users.description')}</p>
          </div>
          <div className="flex gap-2 w-full sm:w-auto">
            <button
              onClick={loadUsers}
              disabled={loading}
              className="flex-1 sm:flex-none px-3 sm:px-4 py-2 bg-white/5 text-white rounded-lg font-medium hover:bg-white/10 transition-colors disabled:opacity-50 flex items-center justify-center gap-2 text-sm"
            >
              <RefreshCw size={16} className={loading ? 'animate-spin' : ''} />
              <span className="hidden sm:inline">{t('settings.users.actions.refresh')}</span>
              <span className="sm:hidden">{t('settings.users.actions.refresh')}</span>
            </button>
            {!showCreateForm && (
              <button
                onClick={() => setShowCreateForm(true)}
                className="flex-1 sm:flex-none px-3 sm:px-4 py-2 bg-scum-orange text-white rounded-lg font-medium hover:bg-scum-orange/90 transition-colors flex items-center justify-center gap-2 text-sm"
              >
                <UserPlus size={16} />
                <span className="hidden sm:inline">{t('settings.users.actions.create')}</span>
                <span className="sm:hidden">{t('settings.users.actions.create')}</span>
              </button>
            )}
          </div>
        </div>
      </div>

      {/* Busca */}
      {!showCreateForm && (
        <div className="card p-3 sm:p-4">
          <SearchBar
            value={searchQuery}
            onChange={(value) => onSearchChange?.(value)}
            placeholder={t('settings.users.search.placeholder')}
          />
        </div>
      )}

      {/* Formulário de Criação */}
      {showCreateForm && (
        <CreateUserForm onSuccess={handleCreateSuccess} onCancel={() => setShowCreateForm(false)} />
      )}

      {/* Lista de Usuários */}
      {!showCreateForm && (
        <>
          {loading && users.length === 0 ? (
            <div className="card p-8 text-center">
              <Loader2 className="mx-auto mb-4 text-scum-orange animate-spin" size={32} />
              <p className="text-white/60">{t('settings.users.loading')}</p>
            </div>
          ) : error ? (
            <div className="card p-6">
              <div className="bg-red-500/20 border border-red-500/50 rounded-lg p-4">
                <p className="text-red-400">{error}</p>
                <button
                  onClick={loadUsers}
                  className="mt-4 px-4 py-2 bg-red-500/20 text-red-400 rounded-lg hover:bg-red-500/30 transition-colors"
                >
                  {t('settings.users.actions.refresh')}
                </button>
              </div>
            </div>
          ) : (
            <>
              {filteredUsers.length === 0 && searchQuery ? (
                <div className="card p-8 text-center">
                  <p className="text-white/60">{t('settings.users.search.noResults')}</p>
                </div>
              ) : filteredUsers.length === 0 && !searchQuery ? (
                <div className="card p-8 text-center">
                  <p className="text-white/60">{t('settings.users.empty')}</p>
                  <button
                    onClick={loadUsers}
                    className="mt-4 px-4 py-2 bg-scum-orange text-white rounded-lg hover:bg-scum-orange/90 transition-colors"
                  >
                    {t('settings.users.actions.refresh')}
                  </button>
                </div>
              ) : (
                <UserTable users={filteredUsers} onUpdate={handleUpdate} />
              )}
            </>
          )}
        </>
      )}
    </div>
  );
}

