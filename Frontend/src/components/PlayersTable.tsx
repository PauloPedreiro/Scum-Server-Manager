import React, { useState, useMemo } from 'react';
import { Player } from '../services/playerService';
import { useLanguage } from '../contexts/LanguageContext';
import { AdminService } from '../services/adminService';
import { toast } from 'react-toastify';
import 'react-toastify/dist/ReactToastify.css';
import { ToastContainer } from 'react-toastify';
import { WhitelistService } from '../services/whitelistService';
import { BanService } from '../services/banService';
import { ExclusiveService } from '../services/exclusiveService';
import { SilenceService } from '../services/silenceService';
import { AdminUsersService } from '../services/adminUsersService';
import { ServerSettingsAdminUsersService } from '../services/serverSettingsAdminUsersService';

interface PlayersTableProps {
  players: Player[];
  hideSteamIds?: boolean;
  admins?: string[];
  serverSettingsAdmins?: string[];
  whitelistedUsers?: string[];
  bannedUsers?: string[];
  exclusiveUsers?: string[];
  silencedUsers?: string[];
  onAdminAdded?: () => void;
  onServerSettingsAdminAdded?: () => void;
  onWhitelistUpdated?: () => void;
  onBanListUpdated?: () => void;
  onExclusiveListUpdated?: () => void;
  onSilenceListUpdated?: () => void;
}

const formatPlayTime = (ms: number) => {
  const totalSeconds = Math.floor(ms / 1000);
  const hours = Math.floor(totalSeconds / 3600);
  const minutes = Math.floor((totalSeconds % 3600) / 60);
  return `${hours}h ${minutes}min`;
};

const uniqueTags = (players: Player[]) => {
  const tagsSet = new Set<string>();
  players.forEach(p => p.tags?.forEach(tag => tagsSet.add(tag)));
  return Array.from(tagsSet);
};

const PlayersTable: React.FC<PlayersTableProps> = ({ 
  players, 
  hideSteamIds = false, 
  admins = [], 
  serverSettingsAdmins = [], 
  whitelistedUsers = [], 
  bannedUsers = [], 
  exclusiveUsers = [], 
  silencedUsers = [], 
  onAdminAdded, 
  onServerSettingsAdminAdded, 
  onWhitelistUpdated, 
  onBanListUpdated, 
  onExclusiveListUpdated, 
  onSilenceListUpdated 
}) => {
  console.log('PlayersTable rendered with serverSettingsAdmins:', serverSettingsAdmins);
  console.log('PlayersTable serverSettingsAdmins length:', serverSettingsAdmins.length);
  const { t, language } = useLanguage();
  const [nameFilter, setNameFilter] = useState('');
  const [steamIdFilter, setSteamIdFilter] = useState('');
  const [statusFilter, setStatusFilter] = useState('');
  const [tagFilter, setTagFilter] = useState('');

  const tagsList = useMemo(() => uniqueTags(players), [players]);

  const filteredPlayers = useMemo(() => {
    return players.filter(player => {
      const nameMatch = player.playerName.toLowerCase().includes(nameFilter.toLowerCase());
      const steamIdMatch = hideSteamIds ? true : player.steamId.includes(steamIdFilter);
      const statusMatch = statusFilter === '' || (statusFilter === 'online' && player.isOnline) || (statusFilter === 'offline' && !player.isOnline);
      const tagMatch = tagFilter === '' || (player.tags && player.tags.includes(tagFilter));
      return nameMatch && steamIdMatch && statusMatch && tagMatch;
    });
  }, [players, nameFilter, steamIdFilter, statusFilter, tagFilter, hideSteamIds]);

  return (
    <div className="overflow-x-auto bg-scum-dark/60 rounded-lg border border-scum-accent/20 shadow">
      <div className="min-w-full">
        <table className="w-full text-xs sm:text-sm text-scum-light">
          <thead>
            <tr className="bg-scum-secondary/40">
              <th className="px-2 sm:px-4 py-2 sm:py-3 text-left whitespace-nowrap">{t('name')}</th>
              {!hideSteamIds && <th className="px-2 sm:px-4 py-2 sm:py-3 text-left whitespace-nowrap">SteamID</th>}
              <th className="px-2 sm:px-4 py-2 sm:py-3 text-left whitespace-nowrap">{t('playtime')}</th>
              <th className="px-2 sm:px-4 py-2 sm:py-3 text-left whitespace-nowrap">{t('last_login')}</th>
              <th className="px-2 sm:px-4 py-2 sm:py-3 text-left whitespace-nowrap">{t('status')}</th>
              <th className="px-2 sm:px-4 py-2 sm:py-3 text-left whitespace-nowrap">{t('tags')}</th>
              <th className="px-2 sm:px-4 py-2 sm:py-3 text-left whitespace-nowrap">Admin</th>
              <th className="px-2 sm:px-4 py-2 sm:py-3 text-left whitespace-nowrap">Admin Config</th>
              <th className="px-2 sm:px-4 py-2 sm:py-3 text-left whitespace-nowrap">Whitelist</th>
              <th className="px-2 sm:px-4 py-2 sm:py-3 text-left whitespace-nowrap">Ban</th>
              <th className="px-2 sm:px-4 py-2 sm:py-3 text-left whitespace-nowrap">VIP</th>
              <th className="px-2 sm:px-4 py-2 sm:py-3 text-left whitespace-nowrap">Mute</th>
            </tr>
            <tr className="bg-scum-secondary/20">
              <th className="px-2 py-2">
                <input
                  type="text"
                  value={nameFilter}
                  onChange={e => setNameFilter(e.target.value)}
                  placeholder={t('filter_name')}
                  className="w-full px-2 py-1 rounded bg-scum-gray/40 text-scum-light placeholder-scum-muted border border-scum-gray focus:border-scum-accent outline-none text-xs"
                />
              </th>
              {!hideSteamIds && (
                <th className="px-2 py-2">
                  <input
                    type="text"
                    value={steamIdFilter}
                    onChange={e => setSteamIdFilter(e.target.value)}
                    placeholder={t('filter_steamid')}
                    className="w-full px-2 py-1 rounded bg-scum-gray/40 text-scum-light placeholder-scum-muted border border-scum-gray focus:border-scum-accent outline-none text-xs"
                  />
                </th>
              )}
              <th></th>
              <th></th>
              <th className="px-2 py-2">
                <select
                  value={statusFilter}
                  onChange={e => setStatusFilter(e.target.value)}
                  className="w-full px-2 py-1 rounded bg-scum-gray/40 text-scum-light border border-scum-gray focus:border-scum-accent outline-none text-xs"
                >
                  <option value="">{t('all')}</option>
                  <option value="online">{t('online')}</option>
                  <option value="offline">{t('offline')}</option>
                </select>
              </th>
              <th className="px-2 py-2">
                <select
                  value={tagFilter}
                  onChange={e => setTagFilter(e.target.value)}
                  className="w-full px-2 py-1 rounded bg-scum-gray/40 text-scum-light border border-scum-gray focus:border-scum-accent outline-none text-xs"
                >
                  <option value="">{t('all_tags')}</option>
                  {tagsList.map(tag => (
                    <option key={tag} value={tag}>{tag}</option>
                  ))}
                </select>
              </th>
              <th></th>
              <th></th>
              <th></th>
              <th></th>
              <th></th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {filteredPlayers.length === 0 && (
              <tr>
                <td colSpan={hideSteamIds ? 12 : 13} className="text-center py-6 text-scum-muted">{t('no_players_found')}</td>
              </tr>
            )}
            {filteredPlayers.map((player) => {
                    const isAdmin = admins.includes(player.steamId);
      const isServerSettingsAdmin = serverSettingsAdmins.includes(player.steamId);
      const isWhitelisted = whitelistedUsers.includes(player.steamId);
      const isBanned = bannedUsers.includes(player.steamId);
      const isExclusive = exclusiveUsers.includes(player.steamId);
      const isSilenced = silencedUsers.includes(player.steamId);
      
      // Debug log para verificar o estado
      if (player.steamId === '76561198012345678') {
        console.log('Player steamId:', player.steamId);
        console.log('Server settings admins:', serverSettingsAdmins);
        console.log('Is server settings admin:', isServerSettingsAdmin);
      }
            
              return (
                <tr key={player.steamId} className="border-b border-scum-gray/30 hover:bg-scum-gray/20 transition-colors">
                  <td className="px-2 sm:px-4 py-2 font-bold">{player.playerName}</td>
                  {!hideSteamIds && <td className="px-2 sm:px-4 py-2 font-mono text-xs">{player.steamId}</td>}
                  <td className="px-2 sm:px-4 py-2">{formatPlayTime(player.totalPlayTime)}</td>
                  <td className="px-2 sm:px-4 py-2">{player.lastLogin ? new Date(player.lastLogin).toLocaleString(language) : '-'}</td>
                  <td className="px-2 sm:px-4 py-2">
                    {player.isOnline ? (
                      <span className="text-green-400 font-bold">Online</span>
                    ) : (
                      <span className="text-scum-muted">Offline</span>
                    )}
                  </td>
                  <td className="px-2 sm:px-4 py-2">
                    {player.tags && player.tags.length > 0 ? (
                      <span className="bg-scum-accent/20 text-scum-accent px-2 py-1 rounded text-xs font-mono">{player.tags[0]}</span>
                    ) : (
                      <span className="text-scum-muted">-</span>
                    )}
                  </td>
                  <td className="px-2 sm:px-4 py-2 text-center">
                    {isAdmin ? (
                      <div className="flex items-center justify-center gap-1">
                        <span className="bg-yellow-500 text-black px-2 py-1 rounded text-xs font-bold">Adm</span>
                        <button
                          className="px-1 py-1 bg-red-600 hover:bg-red-700 text-white rounded text-xs transition-colors"
                          onClick={async () => {
                            try {
                              const res = await AdminService.removeAdmin(player.steamId);
                              if (res.success) {
                                toast.success('Admin removido com sucesso!');
                                if (onAdminAdded) onAdminAdded();
                              } else {
                                toast.error(res.error || 'Erro ao remover admin.');
                              }
                            } catch (err) {
                              toast.error('Erro ao conectar ao servidor.');
                            }
                          }}
                          title="Remover Admin"
                        >
                          ✕
                        </button>
                      </div>
                    ) : (
                      <button
                        className="px-2 py-1 bg-green-700 hover:bg-green-800 text-white rounded text-xs transition-colors"
                        onClick={async () => {
                          try {
                            const res = await AdminService.addAdmin(player.steamId);
                            if (res.success) {
                              toast.success('Admin adicionado com sucesso!');
                              if (onAdminAdded) onAdminAdded();
                            } else {
                              toast.error(res.error || 'Erro ao adicionar admin.');
                            }
                          } catch (err) {
                            toast.error('Erro ao conectar ao servidor.');
                          }
                        }}
                        title="Tornar Admin"
                      >
                        Admin
                      </button>
                    )}
                  </td>
                  <td className="px-2 sm:px-4 py-2 text-center">
                    {isServerSettingsAdmin ? (
                      <div className="flex items-center justify-center gap-1">
                        <span className="bg-blue-600 text-white px-2 py-1 rounded text-xs font-bold">Config</span>
                        <button
                          className="px-1 py-1 bg-red-600 hover:bg-red-700 text-white rounded text-xs transition-colors"
                          onClick={async () => {
                            try {
                              const res = await ServerSettingsAdminUsersService.removeServerSettingsAdminUser(player.steamId);
                              if (res.success) {
                                toast.success('Configuração de admin removida com sucesso!');
                                if (onServerSettingsAdminAdded) onServerSettingsAdminAdded();
                              } else {
                                toast.error(res.message || 'Erro ao remover configuração.');
                              }
                            } catch (err) {
                              toast.error('Erro ao conectar ao servidor.');
                            }
                          }}
                          title="Remover Config Admin"
                        >
                          ✕
                        </button>
                      </div>
                    ) : (
                      <button
                        className="px-2 py-1 bg-blue-700 hover:bg-blue-800 text-white rounded text-xs transition-colors"
                        onClick={async () => {
                          try {
                            console.log('Adding server settings admin for:', player.steamId);
                            const res = await ServerSettingsAdminUsersService.addServerSettingsAdminUser(player.steamId);
                            console.log('Add server settings admin response:', res);
                            if (res.success) {
                              toast.success('Configuração de admin adicionada com sucesso!');
                              console.log('Calling onServerSettingsAdminAdded callback...');
                              if (onServerSettingsAdminAdded) onServerSettingsAdminAdded();
                            } else {
                              toast.error(res.message || 'Erro ao adicionar configuração.');
                            }
                          } catch (err) {
                            console.error('Error adding server settings admin:', err);
                            toast.error('Erro ao conectar ao servidor.');
                          }
                        }}
                        title="Adicionar Config Admin"
                      >
                        Config
                      </button>
                    )}
                  </td>
                  <td className="px-2 sm:px-4 py-2 text-center">
                    {isWhitelisted ? (
                      <div className="flex items-center justify-center gap-1">
                        <span className="bg-blue-500 text-white px-2 py-1 rounded text-xs font-bold">WL</span>
                        <button
                          className="px-1 py-1 bg-red-600 hover:bg-red-700 text-white rounded text-xs transition-colors"
                          onClick={async () => {
                            try {
                              const res = await WhitelistService.removeWhitelistedUser(player.steamId);
                              if (res.success) {
                                toast.success('Usuário removido da whitelist com sucesso!');
                                if (onWhitelistUpdated) onWhitelistUpdated();
                              } else {
                                toast.error(res.error || 'Erro ao remover da whitelist.');
                              }
                            } catch (err) {
                              toast.error('Erro ao conectar ao servidor.');
                            }
                          }}
                          title="Remover da Whitelist"
                        >
                          ✕
                        </button>
                      </div>
                    ) : (
                      <button
                        className="px-2 py-1 bg-blue-700 hover:bg-blue-800 text-white rounded text-xs transition-colors"
                        onClick={async () => {
                          try {
                            const res = await WhitelistService.addWhitelistedUser(player.steamId);
                            if (res.success) {
                              toast.success('Usuário adicionado à whitelist com sucesso!');
                              if (onWhitelistUpdated) onWhitelistUpdated();
                            } else {
                              toast.error(res.error || 'Erro ao adicionar à whitelist.');
                            }
                          } catch (err) {
                            toast.error('Erro ao conectar ao servidor.');
                          }
                        }}
                        title="Adicionar à Whitelist"
                      >
                        Whitelist
                      </button>
                    )}
                  </td>
                  <td className="px-2 sm:px-4 py-2 text-center">
                    {isBanned ? (
                      <div className="flex items-center justify-center gap-1">
                        <span className="bg-red-500 text-white px-2 py-1 rounded text-xs font-bold">BAN</span>
                        <button
                          className="px-1 py-1 bg-green-600 hover:bg-green-700 text-white rounded text-xs transition-colors"
                          onClick={async () => {
                            try {
                              const res = await BanService.removeBannedUser(player.steamId);
                              if (res.success) {
                                toast.success('Usuário desbanido com sucesso!');
                                if (onBanListUpdated) onBanListUpdated();
                              } else {
                                toast.error(res.error || 'Erro ao desbanir usuário.');
                              }
                            } catch (err) {
                              toast.error('Erro ao conectar ao servidor.');
                            }
                          }}
                          title="Desbanir Usuário"
                        >
                          ✓
                        </button>
                      </div>
                    ) : (
                      <button
                        className="px-2 py-1 bg-red-700 hover:bg-red-800 text-white rounded text-xs transition-colors"
                        onClick={async () => {
                          try {
                            const res = await BanService.addBannedUser(player.steamId);
                            if (res.success) {
                              toast.success('Usuário banido com sucesso!');
                              if (onBanListUpdated) onBanListUpdated();
                            } else {
                              toast.error(res.error || 'Erro ao banir usuário.');
                            }
                          } catch (err) {
                            toast.error('Erro ao conectar ao servidor.');
                          }
                        }}
                        title="Banir Usuário"
                      >
                        Ban
                      </button>
                    )}
                  </td>
                  <td className="px-2 sm:px-4 py-2 text-center">
                    {isExclusive ? (
                      <div className="flex items-center justify-center gap-1">
                        <span className="bg-purple-600 text-white px-2 py-1 rounded text-xs font-bold">VIP</span>
                        <button
                          className="px-1 py-1 bg-red-600 hover:bg-red-700 text-white rounded text-xs transition-colors"
                          onClick={async () => {
                            try {
                              const res = await ExclusiveService.removeExclusiveUser(player.steamId);
                              if (res.success) {
                                toast.success('Usuário removido da lista VIP com sucesso!');
                                if (onExclusiveListUpdated) onExclusiveListUpdated();
                              } else {
                                toast.error(res.error || 'Erro ao remover da lista VIP.');
                              }
                            } catch (err) {
                              toast.error('Erro ao conectar ao servidor.');
                            }
                          }}
                          title="Remover VIP"
                        >
                          ✕
                        </button>
                      </div>
                    ) : (
                      <button
                        className="px-2 py-1 bg-purple-700 hover:bg-purple-800 text-white rounded text-xs transition-colors"
                        onClick={async () => {
                          try {
                            const res = await ExclusiveService.addExclusiveUser(player.steamId);
                            if (res.success) {
                              toast.success('Usuário adicionado à lista VIP com sucesso!');
                              if (onExclusiveListUpdated) onExclusiveListUpdated();
                            } else {
                              toast.error(res.error || 'Erro ao adicionar à lista VIP.');
                            }
                          } catch (err) {
                            toast.error('Erro ao conectar ao servidor.');
                          }
                        }}
                        title="Adicionar VIP"
                      >
                        VIP
                      </button>
                    )}
                  </td>
                  <td className="px-2 sm:px-4 py-2 text-center">
                    {isSilenced ? (
                      <div className="flex items-center justify-center gap-1">
                        <span className="bg-gray-600 text-white px-2 py-1 rounded text-xs font-bold">Mute</span>
                        <button
                          className="px-1 py-1 bg-green-600 hover:bg-green-700 text-white rounded text-xs transition-colors"
                          onClick={async () => {
                            try {
                              const res = await SilenceService.removeSilencedUser(player.steamId);
                              if (res.success) {
                                toast.success('Usuário removido da lista de silenciados com sucesso!');
                                if (onSilenceListUpdated) onSilenceListUpdated();
                              } else {
                                toast.error(res.error || 'Erro ao remover da lista de silenciados.');
                              }
                            } catch (err) {
                              toast.error('Erro ao conectar ao servidor.');
                            }
                          }}
                          title="Remover Mute"
                        >
                          ✓
                        </button>
                      </div>
                    ) : (
                      <button
                        className="px-2 py-1 bg-gray-700 hover:bg-gray-800 text-white rounded text-xs transition-colors"
                        onClick={async () => {
                          try {
                            const res = await SilenceService.addSilencedUser(player.steamId);
                            if (res.success) {
                              toast.success('Usuário silenciado com sucesso!');
                              if (onSilenceListUpdated) onSilenceListUpdated();
                            } else {
                              toast.error(res.error || 'Erro ao silenciar usuário.');
                            }
                          } catch (err) {
                            toast.error('Erro ao conectar ao servidor.');
                          }
                        }}
                        title="Silenciar Usuário"
                      >
                        Mute
                      </button>
                    )}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
        <ToastContainer position="top-right" autoClose={3000} hideProgressBar newestOnTop closeOnClick pauseOnFocusLoss draggable pauseOnHover />
      </div>
    </div>
  );
};

export default PlayersTable; 