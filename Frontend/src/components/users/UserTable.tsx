import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Edit2, Trash2, Power, PowerOff, CheckCircle2, XCircle, Loader2 } from 'lucide-react';
import { User } from '@/services/auth';
import { authService } from '@/services/auth';
import Swal from 'sweetalert2';
import PlayerSearch from './PlayerSearch';

interface UserTableProps {
  users: User[];
  onUpdate: () => void;
}

export default function UserTable({ users, onUpdate }: UserTableProps) {
  const { t } = useTranslation();
  const [editingUserId, setEditingUserId] = useState<number | null>(null);
  const [editData, setEditData] = useState<{
    is_active?: boolean;
    role?: 'admin' | 'moderator';
    steam_id?: string | null;
  }>({});
  const [updating, setUpdating] = useState<number | null>(null);
  const [deleting, setDeleting] = useState<number | null>(null);

  const handleToggleActive = async (user: User) => {
    setUpdating(user.id);
    try {
      const response = await authService.updateUser(user.id, {
        is_active: !user.is_active,
      });

      if (response.success) {
        await Swal.fire({
          icon: 'success',
          title: t('settings.users.updateSuccess.title'),
          text: t('settings.users.updateSuccess.text'),
          confirmButtonColor: '#f97316',
        });
        onUpdate();
      } else {
        await Swal.fire({
          icon: 'error',
          title: t('settings.users.errors.updateFailed'),
          text: response.error || t('settings.users.errors.updateFailed'),
          confirmButtonColor: '#f97316',
        });
      }
    } catch (error: any) {
      await Swal.fire({
        icon: 'error',
        title: t('settings.users.errors.updateFailed'),
        text: error.message || t('settings.users.errors.updateFailed'),
        confirmButtonColor: '#f97316',
      });
    } finally {
      setUpdating(null);
    }
  };

  const handleEdit = (user: User) => {
    console.log('UserTable - Editando usuário:', user);
    setEditingUserId(user.id);
    setEditData({
      is_active: user.is_active,
      role: user.role as 'admin' | 'moderator',
      steam_id: user.steam_id || null,
    });
    console.log('UserTable - editData inicializado:', {
      is_active: user.is_active,
      role: user.role,
      steam_id: user.steam_id || null,
    });
  };

  const handleSaveEdit = async (userId: number) => {
    console.log('UserTable - Salvando edição:', { userId, editData });
    setUpdating(userId);
    try {
      const response = await authService.updateUser(userId, editData);
      console.log('UserTable - Resposta do update:', response);

      if (response.success) {
        await Swal.fire({
          icon: 'success',
          title: t('settings.users.updateSuccess.title'),
          text: t('settings.users.updateSuccess.text'),
          confirmButtonColor: '#f97316',
        });
        setEditingUserId(null);
        setEditData({});
        onUpdate();
      } else {
        const errorMsg = response.error || t('settings.users.errors.updateFailed');
        console.error('UserTable - Erro na atualização:', errorMsg);
        await Swal.fire({
          icon: 'error',
          title: t('settings.users.errors.updateFailed'),
          text: errorMsg,
          confirmButtonColor: '#f97316',
        });
      }
    } catch (error: any) {
      console.error('UserTable - Erro completo:', error);
      console.error('UserTable - Erro response:', error.response?.data);
      const errorMsg = error.response?.data?.error || error.message || t('settings.users.errors.updateFailed');
      await Swal.fire({
        icon: 'error',
        title: t('settings.users.errors.updateFailed'),
        text: errorMsg,
        confirmButtonColor: '#f97316',
      });
    } finally {
      setUpdating(null);
    }
  };

  const handleCancelEdit = () => {
    setEditingUserId(null);
    setEditData({});
  };

  const handleDelete = async (user: User) => {
    const result = await Swal.fire({
      icon: 'warning',
      title: t('settings.users.delete.confirmTitle'),
      text: t('settings.users.delete.confirmText', { username: user.username }),
      showCancelButton: true,
      confirmButtonColor: '#f97316',
      cancelButtonColor: '#6b7280',
      confirmButtonText: t('settings.users.delete.confirm'),
      cancelButtonText: t('settings.users.delete.cancel'),
    });

    if (result.isConfirmed) {
      setDeleting(user.id);
      try {
        const response = await authService.deleteUser(user.id);

        if (response.success) {
          await Swal.fire({
            icon: 'success',
            title: t('settings.users.delete.success'),
            text: t('settings.users.delete.successText', { username: user.username }),
            confirmButtonColor: '#f97316',
          });
          onUpdate();
        } else {
          await Swal.fire({
            icon: 'error',
            title: t('settings.users.errors.deleteFailed'),
            text: response.error || t('settings.users.errors.deleteFailed'),
            confirmButtonColor: '#f97316',
          });
        }
      } catch (error: any) {
        await Swal.fire({
          icon: 'error',
          title: t('settings.users.errors.deleteFailed'),
          text: error.message || t('settings.users.errors.deleteFailed'),
          confirmButtonColor: '#f97316',
        });
      } finally {
        setDeleting(null);
      }
    }
  };

  const formatDate = (dateString: string | null | undefined): string => {
    if (!dateString) return t('settings.users.table.never');
    try {
      return new Date(dateString).toLocaleString();
    } catch {
      return t('settings.users.table.never');
    }
  };

  if (users.length === 0) {
    return (
      <div className="card p-8 text-center">
        <p className="text-white/60">{t('settings.users.empty')}</p>
      </div>
    );
  }

  return (
    <>
      {/* Desktop: Tabela */}
      <div className="hidden md:block card overflow-x-auto">
        <table className="w-full">
          <thead>
            <tr className="border-b border-white/10">
              <th className="px-4 py-3 text-left text-sm font-medium text-white/80">{t('settings.users.table.id')}</th>
              <th className="px-4 py-3 text-left text-sm font-medium text-white/80">{t('settings.users.table.username')}</th>
              <th className="px-4 py-3 text-left text-sm font-medium text-white/80">{t('settings.users.table.role')}</th>
              <th className="px-4 py-3 text-left text-sm font-medium text-white/80">{t('settings.users.table.status')}</th>
              <th className="px-4 py-3 text-left text-sm font-medium text-white/80">{t('settings.users.table.passwordChanged')}</th>
              <th className="px-4 py-3 text-left text-sm font-medium text-white/80">{t('settings.users.table.linkedPlayer')}</th>
              <th className="px-4 py-3 text-left text-sm font-medium text-white/80">{t('settings.users.table.lastLogin')}</th>
              <th className="px-4 py-3 text-left text-sm font-medium text-white/80">{t('settings.users.table.createdAt')}</th>
              <th className="px-4 py-3 text-left text-sm font-medium text-white/80">{t('settings.users.table.actions')}</th>
            </tr>
          </thead>
          <tbody>
            {users.map((user) => (
              <tr key={user.id} className="border-b border-white/5 hover:bg-white/5">
                {editingUserId === user.id ? (
                  <>
                    <td className="px-4 py-3 text-white/80">{user.id}</td>
                    <td className="px-4 py-3 text-white/80">{user.username}</td>
                    <td className="px-4 py-3">
                      <select
                        value={editData.role}
                        onChange={(e) => setEditData({ ...editData, role: e.target.value as 'admin' | 'moderator' })}
                        className="px-3 py-1 bg-white/5 border border-white/10 rounded text-white text-sm focus:outline-none focus:ring-2 focus:ring-scum-orange"
                      >
                        <option value="moderator">{t('settings.users.roles.moderator')}</option>
                        <option value="admin">{t('settings.users.roles.admin')}</option>
                      </select>
                    </td>
                    <td className="px-4 py-3">
                      <label className="flex items-center gap-2 cursor-pointer">
                        <input
                          type="checkbox"
                          checked={editData.is_active}
                          onChange={(e) => setEditData({ ...editData, is_active: e.target.checked })}
                          className="w-4 h-4 rounded bg-white/5 border-white/10 text-scum-orange focus:ring-scum-orange"
                        />
                        <span className="text-white/80 text-sm">
                          {editData.is_active ? t('settings.users.table.active') : t('settings.users.table.inactive')}
                        </span>
                      </label>
                    </td>
                    <td className="px-4 py-3">
                      {user.password_changed ? (
                        <CheckCircle2 className="text-green-400" size={20} />
                      ) : (
                        <XCircle className="text-red-400" size={20} />
                      )}
                    </td>
                    <td className="px-4 py-3">
                      <div className="w-64">
                        <PlayerSearch
                          value={editData.steam_id || undefined}
                          onChange={(id) => {
                            console.log('UserTable - Steam ID mudou:', id);
                            setEditData({ ...editData, steam_id: id || null });
                          }}
                        />
                      </div>
                    </td>
                    <td className="px-4 py-3 text-white/60 text-sm">{formatDate(user.last_login)}</td>
                    <td className="px-4 py-3 text-white/60 text-sm">{formatDate(user.created_at)}</td>
                    <td className="px-4 py-3">
                      <div className="flex gap-2">
                        <button
                          onClick={() => handleSaveEdit(user.id)}
                          disabled={updating === user.id}
                          className="px-3 py-1 bg-scum-orange text-white rounded text-sm hover:bg-scum-orange/90 disabled:opacity-50 flex items-center gap-1"
                        >
                          {updating === user.id ? (
                            <Loader2 size={14} className="animate-spin" />
                          ) : (
                            'Salvar'
                          )}
                        </button>
                        <button
                          onClick={handleCancelEdit}
                          className="px-3 py-1 bg-white/5 text-white rounded text-sm hover:bg-white/10"
                        >
                          Cancelar
                        </button>
                      </div>
                    </td>
                  </>
                ) : (
                  <>
                    <td className="px-4 py-3 text-white/80">{user.id}</td>
                    <td className="px-4 py-3 text-white font-medium">{user.username}</td>
                    <td className="px-4 py-3">
                      <span
                        className={`px-2 py-1 rounded text-xs font-medium ${
                          user.role === 'admin'
                            ? 'bg-red-500/20 text-red-400'
                            : 'bg-blue-500/20 text-blue-400'
                        }`}
                      >
                        {user.role === 'admin' ? t('settings.users.roles.admin') : t('settings.users.roles.moderator')}
                      </span>
                    </td>
                    <td className="px-4 py-3">
                      <span
                        className={`px-2 py-1 rounded text-xs font-medium ${
                          user.is_active
                            ? 'bg-green-500/20 text-green-400'
                            : 'bg-gray-500/20 text-gray-400'
                        }`}
                      >
                        {user.is_active ? t('settings.users.table.active') : t('settings.users.table.inactive')}
                      </span>
                    </td>
                    <td className="px-4 py-3">
                      {user.password_changed ? (
                        <CheckCircle2 className="text-green-400" size={20} />
                      ) : (
                        <XCircle className="text-red-400" size={20} />
                      )}
                    </td>
                    <td className="px-4 py-3 text-white/80">
                      {user.steam_id ? (
                        <span className="flex items-center gap-1">
                          {user.player_name ? (
                            <>
                              <span>{user.player_name}</span>
                              <span className="text-white/40">({user.steam_id})</span>
                            </>
                          ) : (
                            <span>{user.steam_id}</span>
                          )}
                        </span>
                      ) : (
                        <span className="text-white/40">{t('settings.users.table.notLinked')}</span>
                      )}
                    </td>
                    <td className="px-4 py-3 text-white/60 text-sm">{formatDate(user.last_login)}</td>
                    <td className="px-4 py-3 text-white/60 text-sm">{formatDate(user.created_at)}</td>
                    <td className="px-4 py-3">
                      <div className="flex gap-2">
                        <button
                          onClick={() => handleToggleActive(user)}
                          disabled={updating === user.id}
                          className="p-2 text-white/70 hover:text-white transition-colors disabled:opacity-50"
                          title={user.is_active ? t('settings.users.actions.deactivate') : t('settings.users.actions.activate')}
                        >
                          {updating === user.id ? (
                            <Loader2 size={16} className="animate-spin" />
                          ) : user.is_active ? (
                            <PowerOff size={16} />
                          ) : (
                            <Power size={16} />
                          )}
                        </button>
                        <button
                          onClick={() => handleEdit(user)}
                          className="p-2 text-white/70 hover:text-white transition-colors"
                          title={t('settings.users.actions.edit')}
                        >
                          <Edit2 size={16} />
                        </button>
                        {user.role !== 'admin' && (
                          <button
                            onClick={() => handleDelete(user)}
                            disabled={deleting === user.id}
                            className="p-2 text-red-400/70 hover:text-red-400 transition-colors disabled:opacity-50"
                            title={t('settings.users.actions.delete')}
                          >
                            {deleting === user.id ? (
                              <Loader2 size={16} className="animate-spin" />
                            ) : (
                              <Trash2 size={16} />
                            )}
                          </button>
                        )}
                      </div>
                    </td>
                  </>
                )}
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Mobile: Cards */}
      <div className="md:hidden space-y-3">
        {users.map((user) => (
          <div key={user.id} className="card p-4">
            {editingUserId === user.id ? (
              <div className="space-y-4">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-white/60 text-xs">ID</p>
                    <p className="text-white font-medium">{user.id}</p>
                  </div>
                  <div>
                    <p className="text-white/60 text-xs">{t('settings.users.table.username')}</p>
                    <p className="text-white font-medium">{user.username}</p>
                  </div>
                </div>

                <div>
                  <label className="block text-white/60 text-xs mb-1">{t('settings.users.table.role')}</label>
                  <select
                    value={editData.role}
                    onChange={(e) => setEditData({ ...editData, role: e.target.value as 'admin' | 'moderator' })}
                    className="w-full px-3 py-2 bg-white/5 border border-white/10 rounded text-white text-sm focus:outline-none focus:ring-2 focus:ring-scum-orange"
                  >
                    <option value="moderator">{t('settings.users.roles.moderator')}</option>
                    <option value="admin">{t('settings.users.roles.admin')}</option>
                  </select>
                </div>

                <div>
                  <label className="flex items-center gap-2 cursor-pointer">
                    <input
                      type="checkbox"
                      checked={editData.is_active}
                      onChange={(e) => setEditData({ ...editData, is_active: e.target.checked })}
                      className="w-4 h-4 rounded bg-white/5 border-white/10 text-scum-orange focus:ring-scum-orange"
                    />
                    <span className="text-white/80 text-sm">
                      {editData.is_active ? t('settings.users.table.active') : t('settings.users.table.inactive')}
                    </span>
                  </label>
                </div>

                <div>
                  <label className="block text-white/60 text-xs mb-1">{t('settings.users.table.linkedPlayer')}</label>
                  <PlayerSearch
                    value={editData.steam_id || undefined}
                    onChange={(id) => {
                      console.log('UserTable - Steam ID mudou:', id);
                      setEditData({ ...editData, steam_id: id || null });
                    }}
                  />
                </div>

                <div className="flex gap-2 pt-2">
                  <button
                    onClick={() => handleSaveEdit(user.id)}
                    disabled={updating === user.id}
                    className="flex-1 px-3 py-2 bg-scum-orange text-white rounded text-sm hover:bg-scum-orange/90 disabled:opacity-50 flex items-center justify-center gap-1"
                  >
                    {updating === user.id ? (
                      <Loader2 size={14} className="animate-spin" />
                    ) : (
                      'Salvar'
                    )}
                  </button>
                  <button
                    onClick={handleCancelEdit}
                    className="px-4 py-2 bg-white/5 text-white rounded text-sm hover:bg-white/10"
                  >
                    Cancelar
                  </button>
                </div>
              </div>
            ) : (
              <div className="space-y-3">
                <div className="flex items-center justify-between gap-2 flex-wrap">
                  <p className="text-white font-semibold text-base">{user.username}</p>
                  <div className="flex items-center gap-2 flex-shrink-0">
                    <span
                      className={`px-2 py-1 rounded text-xs font-medium ${
                        user.role === 'admin'
                          ? 'bg-red-500/20 text-red-400'
                          : 'bg-blue-500/20 text-blue-400'
                      }`}
                    >
                      {user.role === 'admin' ? t('settings.users.roles.admin') : t('settings.users.roles.moderator')}
                    </span>
                    <span
                      className={`px-2 py-1 rounded text-xs font-medium ${
                        user.is_active
                          ? 'bg-green-500/20 text-green-400'
                          : 'bg-gray-500/20 text-gray-400'
                      }`}
                    >
                      {user.is_active ? t('settings.users.table.active') : t('settings.users.table.inactive')}
                    </span>
                  </div>
                </div>

                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <p className="text-white/60 text-xs mb-1">
                      <span className="sm:hidden">{t('settings.users.table.passwordChangedShort')}</span>
                      <span className="hidden sm:inline">{t('settings.users.table.passwordChanged')}</span>
                    </p>
                    <div className="flex items-center gap-2">
                      {user.password_changed ? (
                        <CheckCircle2 className="text-green-400" size={18} />
                      ) : (
                        <XCircle className="text-red-400" size={18} />
                      )}
                    </div>
                  </div>
                  <div>
                    <p className="text-white/60 text-xs mb-1">{t('settings.users.table.linkedPlayer')}</p>
                    {user.steam_id ? (
                      <p className="text-white/80 text-xs truncate">
                        {user.player_name ? (
                          <>
                            {user.player_name} <span className="text-white/40">({user.steam_id})</span>
                          </>
                        ) : (
                          user.steam_id
                        )}
                      </p>
                    ) : (
                      <p className="text-white/40 text-xs">{t('settings.users.table.notLinked')}</p>
                    )}
                  </div>
                </div>

                <div className="grid grid-cols-2 gap-3 text-xs">
                  <div>
                    <p className="text-white/60 mb-1">{t('settings.users.table.lastLogin')}</p>
                    <p className="text-white/80">{formatDate(user.last_login)}</p>
                  </div>
                  <div>
                    <p className="text-white/60 mb-1">{t('settings.users.table.createdAt')}</p>
                    <p className="text-white/80">{formatDate(user.created_at)}</p>
                  </div>
                </div>

                <div className="flex gap-2 pt-2 border-t border-white/10">
                  <button
                    onClick={() => handleToggleActive(user)}
                    disabled={updating === user.id}
                    className="px-3 py-2 bg-white/5 text-white rounded text-sm hover:bg-white/10 transition-colors disabled:opacity-50 flex items-center justify-center gap-2 flex-shrink-0"
                  >
                    {updating === user.id ? (
                      <Loader2 size={16} className="animate-spin" />
                    ) : user.is_active ? (
                      <>
                        <PowerOff size={16} />
                        <span className="hidden sm:inline">{t('settings.users.actions.deactivate')}</span>
                      </>
                    ) : (
                      <>
                        <Power size={16} />
                        <span className="hidden sm:inline">{t('settings.users.actions.activate')}</span>
                      </>
                    )}
                  </button>
                  <button
                    onClick={() => handleEdit(user)}
                    className="px-3 py-2 bg-white/5 text-white rounded text-sm hover:bg-white/10 transition-colors flex items-center justify-center gap-2 flex-shrink-0"
                  >
                    <Edit2 size={16} />
                    <span className="hidden sm:inline">{t('settings.users.actions.edit')}</span>
                  </button>
                  {user.role !== 'admin' && (
                    <button
                      onClick={() => handleDelete(user)}
                      disabled={deleting === user.id}
                      className="px-3 py-2 bg-red-500/20 text-red-400 rounded text-sm hover:bg-red-500/30 transition-colors disabled:opacity-50 flex items-center justify-center flex-shrink-0"
                    >
                      {deleting === user.id ? (
                        <Loader2 size={16} className="animate-spin" />
                      ) : (
                        <Trash2 size={16} />
                      )}
                    </button>
                  )}
                </div>
              </div>
            )}
          </div>
        ))}
      </div>
    </>
  );
}

