import React, { useState, useMemo } from 'react';
import { VehicleEvent } from '../services/vehicleService';
import { useLanguage } from '../contexts/LanguageContext';

interface VehiclesTableProps {
  vehicles: VehicleEvent[];
}

const eventIcons: Record<string, string> = {
  Destroyed: '💥',
  Disappeared: '👻',
  VehicleInactiveTimerReached: '⏰',
};

function formatVehicleDate(dateStr: string) {
  // Esperado: 2025.07.14-04.17.26
  if (!dateStr) return '';
  const match = dateStr.match(/(\d{4})\.(\d{2})\.(\d{2})-(\d{2})\.(\d{2})\.(\d{2})/);
  if (!match) return dateStr;
  const [, year, month, day, hour, min, sec] = match;
  return `${day}/${month}/${year} às ${hour}:${min}:${sec}`;
}

const VehiclesTable: React.FC<VehiclesTableProps> = ({ vehicles }) => {
  const { t, language } = useLanguage();
  const [ownerFilter, setOwnerFilter] = useState('');
  const [typeFilter, setTypeFilter] = useState('');
  const [eventFilter, setEventFilter] = useState('');

  const eventLabels: Record<string, string> = {
    Destroyed: t('destroyed'),
    Disappeared: t('disappeared'),
    VehicleInactiveTimerReached: t('vehicle_inactive_timer_reached'),
  };

  const filteredVehicles = useMemo(() => {
    return vehicles.filter(event => {
      const ownerMatch = (event.ownerName ?? '').toLowerCase().includes(ownerFilter.toLowerCase());
      const typeMatch = (event.vehicleType ?? '').toLowerCase().includes(typeFilter.toLowerCase());
      const eventMatch = eventFilter === '' || event.event === eventFilter;
      return ownerMatch && typeMatch && eventMatch;
    }).slice().reverse();
  }, [vehicles, ownerFilter, typeFilter, eventFilter]);

  const uniqueTypes = useMemo(() => Array.from(new Set(vehicles.map(v => v.vehicleType))), [vehicles]);
  const uniqueEvents = useMemo(() => Array.from(new Set(vehicles.map(v => v.event))), [vehicles]);

  return (
    <div className="overflow-x-auto bg-scum-dark/60 rounded-lg border border-scum-accent/20 shadow">
      <table className="min-w-full text-sm text-scum-light">
        <thead>
          <tr className="bg-scum-secondary/40">
            <th className="px-4 py-3 text-left">{t('event')}</th>
            <th className="px-4 py-3 text-left">{t('type')}</th>
            <th className="px-4 py-3 text-left">{t('owner')}</th>
            <th className="px-4 py-3 text-left">{t('vehicle_id')}</th>
            <th className="px-4 py-3 text-left">{t('location')}</th>
            <th className="px-4 py-3 text-left">{t('date_time')}</th>
          </tr>
          <tr className="bg-scum-secondary/20">
            <th className="px-2 py-2">
              <select
                value={eventFilter}
                onChange={e => setEventFilter(e.target.value)}
                className="w-full px-2 py-1 rounded bg-scum-gray/40 text-scum-light border border-scum-gray focus:border-scum-accent outline-none text-xs"
              >
                <option value="">{t('all')}</option>
                {uniqueEvents.map(ev => (
                  <option key={ev} value={ev}>{eventLabels[ev] || ev}</option>
                ))}
              </select>
            </th>
            <th className="px-2 py-2">
              <select
                value={typeFilter}
                onChange={e => setTypeFilter(e.target.value)}
                className="w-full px-2 py-1 rounded bg-scum-gray/40 text-scum-light border border-scum-gray focus:border-scum-accent outline-none text-xs"
              >
                <option value="">{t('all')}</option>
                {uniqueTypes.map(type => (
                  <option key={type} value={type}>{type}</option>
                ))}
              </select>
            </th>
            <th className="px-2 py-2">
              <input
                type="text"
                value={ownerFilter}
                onChange={e => setOwnerFilter(e.target.value)}
                placeholder={t('filter_owner')}
                className="w-full px-2 py-1 rounded bg-scum-gray/40 text-scum-light placeholder-scum-muted border border-scum-gray focus:border-scum-accent outline-none text-xs"
              />
            </th>
            <th></th>
            <th></th>
            <th></th>
          </tr>
        </thead>
        <tbody>
          {filteredVehicles.length === 0 && (
            <tr>
              <td colSpan={6} className="text-center py-6 text-scum-muted">{t('no_events_found')}</td>
            </tr>
          )}
          {filteredVehicles.map((event, idx) => (
            <tr key={event.vehicleId + event.timestamp + idx} className="border-b border-scum-gray/30 hover:bg-scum-gray/20 transition-colors">
              <td className="px-4 py-2 font-bold">
                <span className="mr-1">{eventIcons[event.event] || '❓'}</span>
                {eventLabels[event.event] || event.event}
              </td>
              <td className="px-4 py-2">{event.vehicleType}</td>
              <td className="px-4 py-2">
                {event.ownerName && event.ownerName.trim() !== '' ? (
                  event.ownerName
                ) : (
                  <span className="text-red-500 font-semibold">{t('no_owner')}</span>
                )}
              </td>
              <td className="px-4 py-2 font-mono text-xs">{event.vehicleId}</td>
              <td className="px-4 py-2 text-xs">
                X: {event.location.x.toFixed(0)}<br />
                Y: {event.location.y.toFixed(0)}<br />
                Z: {event.location.z.toFixed(0)}
              </td>
              <td className="px-4 py-2 text-xs">{formatVehicleDate(event.timestamp)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
};

export default VehiclesTable; 