import React, { useState, useMemo } from 'react';
import { AdminLogEvent } from '../services/adminLogService';
import { useLanguage } from '../contexts/LanguageContext';

interface AdminLogTableProps {
  events: AdminLogEvent[];
  hideSteamIds?: boolean;
}

function formatLogDate(dateStr: string) {
  if (!dateStr) return '';
  const match = dateStr.match(/(\d{4})\.(\d{2})\.(\d{2})-(\d{2})\.(\d{2})\.(\d{2})/);
  if (!match) return dateStr;
  const [, year, month, day, hour, min, sec] = match;
  return `${day}/${month}/${year} às ${hour}:${min}:${sec}`;
}

const AdminLogTable: React.FC<AdminLogTableProps> = ({ events, hideSteamIds = false }) => {
  const { t, language } = useLanguage();
  const [nameFilter, setNameFilter] = useState('');
  const [steamIdFilter, setSteamIdFilter] = useState('');
  const [commandFilter, setCommandFilter] = useState('');
  const [paramFilter, setParamFilter] = useState('');

  const uniqueCommands = useMemo(() => {
    const set = new Set(events.map(e => e.command).filter(Boolean));
    return Array.from(set) as string[];
  }, [events]);

  const filteredEvents = useMemo(() => {
    return events.filter(e =>
      (!nameFilter || (e.name || '').toLowerCase().includes(nameFilter.toLowerCase())) &&
      (hideSteamIds || !steamIdFilter || (e.steamId || '').includes(steamIdFilter)) &&
      (!commandFilter || (e.command || '').toLowerCase().includes(commandFilter.toLowerCase())) &&
      (!paramFilter || (e.param || e.message || '').toLowerCase().includes(paramFilter.toLowerCase()))
    );
  }, [events, nameFilter, steamIdFilter, commandFilter, paramFilter, hideSteamIds]);

  return (
    <div className="overflow-x-auto bg-scum-dark/60 rounded-lg border border-scum-accent/20 shadow">
      <table className="min-w-full text-sm text-scum-light">
        <thead>
          <tr className="bg-scum-secondary/40">
            <th className="px-4 py-3 text-left">{t('date_time')}</th>
            <th className="px-4 py-3 text-left">{t('name')}</th>
            {!hideSteamIds && <th className="px-4 py-3 text-left">SteamID</th>}
            <th className="px-4 py-3 text-left">{t('command')}</th>
            <th className="px-4 py-3 text-left">{t('parameter_message')}</th>
          </tr>
          <tr className="bg-scum-secondary/20">
            <th></th>
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
            <th className="px-2 py-2">
              <input
                type="text"
                value={commandFilter}
                onChange={e => setCommandFilter(e.target.value)}
                placeholder={t('filter_command')}
                className="w-full px-2 py-1 rounded bg-scum-gray/40 text-scum-light placeholder-scum-muted border border-scum-gray focus:border-scum-accent outline-none text-xs"
              />
            </th>
            <th className="px-2 py-2">
              <input
                type="text"
                value={paramFilter}
                onChange={e => setParamFilter(e.target.value)}
                placeholder={t('filter_parameter_message')}
                className="w-full px-2 py-1 rounded bg-scum-gray/40 text-scum-light placeholder-scum-muted border border-scum-gray focus:border-scum-accent outline-none text-xs"
              />
            </th>
          </tr>
        </thead>
        <tbody>
          {filteredEvents.length === 0 && (
            <tr>
              <td colSpan={hideSteamIds ? 4 : 5} className="text-center py-6 text-scum-muted">{t('no_events_found')}</td>
            </tr>
          )}
          {filteredEvents.map((event, idx) => (
            <tr key={event.timestamp + (event.name || '') + (event.command || '') + idx} className="border-b border-scum-gray/30 hover:bg-scum-gray/20 transition-colors">
              <td className="px-4 py-2 text-xs font-mono">{formatLogDate(event.timestamp)}</td>
              <td className="px-4 py-2">{event.name || '-'}</td>
              {!hideSteamIds && <td className="px-4 py-2 font-mono text-xs">{event.steamId || '-'}</td>}
              <td className="px-4 py-2">{event.command || '-'}</td>
              <td className="px-4 py-2">
                {event.param ? event.param : event.message}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
};

export default AdminLogTable; 