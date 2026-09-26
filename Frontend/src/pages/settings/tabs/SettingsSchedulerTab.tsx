import { useState, useEffect, useMemo, useRef } from 'react';
import { useTranslation } from 'react-i18next';
import { Loader2, Plus, Trash2, Edit2, Upload, X, Clock, AlertTriangle, Calendar, Settings, Sparkles, FileText } from 'lucide-react';
import Swal from 'sweetalert2';
import { getSchedulerConfig, updateSchedulerConfig, getRoutines, saveRoutineUnified, deleteRoutine, SettingsRoutine } from '@/services/settingsScheduler';

interface Props { searchQuery?: string; }

export default function SettingsSchedulerTab({ searchQuery = '' }: Props) {
  const { t } = useTranslation();
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Days abbreviations — driven by translation keys (reuse events.day_N pattern)
  const DAYS_ABBR = [
    t('tools.events.day_1'), // Seg
    t('tools.events.day_2'), // Ter
    t('tools.events.day_3'), // Qua
    t('tools.events.day_4'), // Qui
    t('tools.events.day_5'), // Sex
    t('tools.events.day_6'), // Sáb
    t('tools.events.day_0'), // Dom
  ];

  const [globalEnabled, setGlobalEnabled] = useState(false);
  const [activeRoutineId, setActiveRoutineId] = useState<string | null>(null);
  const [routines, setRoutines] = useState<SettingsRoutine[]>([]);
  const [loading, setLoading] = useState(true);
  const [actionLoading, setActionLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Inline form state
  const [editingId, setEditingId] = useState<string | null>(null); // null=closed, 'new'=creating, uuid=editing
  const [formName, setFormName] = useState('');
  const [formEnabled, setFormEnabled] = useState(true);
  const [formDays, setFormDays] = useState<number[]>([]);
  const [formStart, setFormStart] = useState('12:00');
  const [formEnd, setFormEnd] = useState('18:00');
  const [formFile, setFormFile] = useState<File | null>(null);
  const [formExistingFile, setFormExistingFile] = useState('');
  const [formSubmitting, setFormSubmitting] = useState(false);

  const loadAll = async () => {
    setLoading(true);
    setError(null);
    try {
      const [configRes, routinesRes] = await Promise.all([getSchedulerConfig(), getRoutines()]);
      if (configRes.success) { setGlobalEnabled(configRes.enabled); setActiveRoutineId(configRes.active_routine_id); }
      else throw new Error(configRes.error || t('settings.settingsScheduler.error.initTitle'));
      if (routinesRes.success) setRoutines(routinesRes.routines);
      else throw new Error(routinesRes.error || t('settings.settingsScheduler.error.initTitle'));
    } catch (err: any) {
      setError(err.message || t('settings.settingsScheduler.error.initTitle'));
    } finally { setLoading(false); }
  };

  useEffect(() => { loadAll(); }, []);

  const handleToggleGlobal = async () => {
    setActionLoading(true);
    const target = !globalEnabled;
    try {
      const res = await updateSchedulerConfig(target);
      if (res.success) { setGlobalEnabled(res.enabled); setActiveRoutineId(res.active_routine_id); }
      else throw new Error(res.error);
    } catch (err: any) {
      Swal.fire({ icon: 'error', title: t('settings.settingsScheduler.alerts.error'), text: err.message, confirmButtonColor: '#f97316' });
    } finally { setActionLoading(false); }
  };

  const openCreateForm = () => {
    setEditingId('new');
    setFormName(''); setFormEnabled(true); setFormDays([]); setFormStart('12:00'); setFormEnd('18:00');
    setFormFile(null); setFormExistingFile('');
  };

  const openEditForm = (r: SettingsRoutine) => {
    setEditingId(r.id);
    setFormName(r.name); setFormEnabled(r.enabled); setFormDays([...r.days_of_week]);
    setFormStart(r.start_time); setFormEnd(r.end_time);
    setFormFile(null); setFormExistingFile(r.preset_file);
  };

  const closeForm = () => { setEditingId(null); setFormFile(null); };

  const handleToggleDay = (idx: number) => {
    setFormDays(prev => prev.includes(idx) ? prev.filter(d => d !== idx) : [...prev, idx].sort((a, b) => a - b));
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const f = e.target.files?.[0];
    if (f && !f.name.endsWith('.ini')) {
      Swal.fire({ icon: 'error', title: t('settings.settingsScheduler.validation.invalidFormat'), text: t('settings.settingsScheduler.validation.iniOnly'), confirmButtonColor: '#f97316' });
      if (fileInputRef.current) fileInputRef.current.value = '';
      return;
    }
    setFormFile(f || null);
  };

  const handleSubmit = async () => {
    if (!formName.trim()) { Swal.fire({ icon: 'warning', title: t('settings.settingsScheduler.alerts.warning'), text: t('settings.settingsScheduler.validation.nameRequired'), confirmButtonColor: '#f97316' }); return; }
    if (formDays.length === 0) { Swal.fire({ icon: 'warning', title: t('settings.settingsScheduler.alerts.warning'), text: t('settings.settingsScheduler.validation.dayRequired'), confirmButtonColor: '#f97316' }); return; }

    const [sH, sM] = formStart.split(':').map(Number);
    const [eH, eM] = formEnd.split(':').map(Number);
    if (eH * 60 + eM <= sH * 60 + sM) { Swal.fire({ icon: 'warning', title: t('settings.settingsScheduler.alerts.warning'), text: t('settings.settingsScheduler.validation.timeOrder'), confirmButtonColor: '#f97316' }); return; }

    const isNew = editingId === 'new';
    if (isNew && !formFile) { Swal.fire({ icon: 'warning', title: t('settings.settingsScheduler.alerts.warning'), text: t('settings.settingsScheduler.validation.fileRequired'), confirmButtonColor: '#f97316' }); return; }

    setFormSubmitting(true);
    try {
      const res = await saveRoutineUnified({
        id: isNew ? undefined : editingId!,
        name: formName.trim(),
        enabled: formEnabled,
        days_of_week: formDays,
        start_time: formStart,
        end_time: formEnd,
        file: formFile,
      });
      if (res.success && res.routines) {
        setRoutines(res.routines);
        closeForm();
        const cfgRes = await getSchedulerConfig();
        if (cfgRes.success) { setGlobalEnabled(cfgRes.enabled); setActiveRoutineId(cfgRes.active_routine_id); }
        Swal.fire({ icon: 'success', title: isNew ? t('settings.settingsScheduler.alerts.created') : t('settings.settingsScheduler.alerts.updated'), confirmButtonColor: '#f97316', timer: 1500 });
      } else throw new Error(res.error || t('settings.settingsScheduler.alerts.error'));
    } catch (err: any) {
      Swal.fire({ icon: 'error', title: t('settings.settingsScheduler.alerts.error'), text: err.message, confirmButtonColor: '#f97316' });
    } finally { setFormSubmitting(false); }
  };

  const handleDelete = async (r: SettingsRoutine) => {
    const confirm = await Swal.fire({
      title: t('settings.settingsScheduler.alerts.deleteTitle'),
      text: t('settings.settingsScheduler.alerts.deleteText', { name: r.name }),
      icon: 'warning',
      showCancelButton: true,
      confirmButtonText: t('settings.settingsScheduler.alerts.deleteBtn'),
      cancelButtonText: t('settings.settingsScheduler.alerts.deleteCancel'),
      confirmButtonColor: '#ef4444',
      cancelButtonColor: '#3b82f6',
    });
    if (!confirm.isConfirmed) return;
    setActionLoading(true);
    try {
      const res = await deleteRoutine(r.id);
      if (res.success && res.routines) { setRoutines(res.routines); Swal.fire({ icon: 'success', title: t('settings.settingsScheduler.alerts.deleted'), confirmButtonColor: '#f97316', timer: 1500 }); }
      else throw new Error(res.error || t('settings.settingsScheduler.alerts.error'));
    } catch (err: any) {
      Swal.fire({ icon: 'error', title: t('settings.settingsScheduler.alerts.error'), text: err.message, confirmButtonColor: '#f97316' });
    } finally { setActionLoading(false); }
  };

  const handleToggleRoutine = async (r: SettingsRoutine) => {
    const prev = r.enabled;
    setRoutines(rs => rs.map(x => x.id === r.id ? { ...x, enabled: !x.enabled } : x));
    try {
      const res = await saveRoutineUnified({ id: r.id, name: r.name, enabled: !prev, days_of_week: r.days_of_week, start_time: r.start_time, end_time: r.end_time });
      if (res.success && res.routines) { setRoutines(res.routines); const c = await getSchedulerConfig(); if (c.success) { setGlobalEnabled(c.enabled); setActiveRoutineId(c.active_routine_id); } }
      else throw new Error(res.error);
    } catch (err: any) {
      setRoutines(rs => rs.map(x => x.id === r.id ? { ...x, enabled: prev } : x));
      Swal.fire({ icon: 'error', title: t('settings.settingsScheduler.alerts.error'), text: err.message, confirmButtonColor: '#f97316' });
    }
  };

  const filtered = useMemo(() => {
    const q = searchQuery.toLowerCase().trim();
    if (!q) return routines;
    return routines.filter(r => r.name.toLowerCase().includes(q) || r.preset_file.toLowerCase().includes(q));
  }, [routines, searchQuery]);

  const activeRoutine = useMemo(() => {
    if (!activeRoutineId || !globalEnabled) return null;
    return routines.find(r => r.id === activeRoutineId) || null;
  }, [activeRoutineId, globalEnabled, routines]);

  // --- INLINE FORM COMPONENT ---
  const renderInlineForm = () => (
    <div className="col-span-1 md:col-span-2 card border-2 border-scum-orange/40 bg-scum-orange/5 p-5 space-y-4 animate-fadeIn">
      <div className="flex items-center justify-between">
        <h4 className="text-sm font-bold text-white flex items-center gap-2">
          <Sparkles className="text-scum-orange w-4 h-4" />
          {editingId === 'new' ? t('settings.settingsScheduler.form.newTitle') : t('settings.settingsScheduler.form.editTitle')}
        </h4>
        <button onClick={closeForm} className="text-white/40 hover:text-white/80 transition-colors"><X size={18} /></button>
      </div>

      {/* Nome + Toggle */}
      <div className="grid grid-cols-1 sm:grid-cols-[1fr_auto] gap-4 items-end">
        <div>
          <label className="text-[11px] font-semibold text-white/70 block mb-1">{t('settings.settingsScheduler.form.eventName')}</label>
          <input type="text" value={formName} onChange={e => setFormName(e.target.value)} placeholder={t('settings.settingsScheduler.form.eventNamePlaceholder')}
            className="w-full px-3 py-2 bg-white/5 border border-white/10 rounded-lg text-white text-xs focus:outline-none focus:ring-2 focus:ring-scum-orange focus:border-transparent" />
        </div>
        <div className="flex items-center gap-3 bg-white/5 px-3 py-2 rounded-lg border border-white/5 h-[36px]">
          <span className="text-xs font-semibold text-white whitespace-nowrap">{t('settings.settingsScheduler.form.activate')}</span>
          <button type="button" onClick={() => setFormEnabled(!formEnabled)}
            className={`relative inline-flex h-5 w-9 flex-shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors duration-200 ${formEnabled ? 'bg-scum-orange' : 'bg-white/10'}`}>
            <span className={`pointer-events-none inline-block h-4 w-4 transform rounded-full bg-white shadow transition duration-200 ${formEnabled ? 'translate-x-4' : 'translate-x-0'}`} />
          </button>
        </div>
      </div>

      {/* Dias + Horário + Upload + Actions — tudo em uma linha */}
      <div className="flex items-center gap-1.5 flex-wrap sm:flex-nowrap">
        {DAYS_ABBR.map((day, idx) => (
          <button key={idx} type="button" onClick={() => handleToggleDay(idx)}
            className={`w-8 h-8 rounded-md text-[10px] font-bold transition-all flex-shrink-0 ${formDays.includes(idx) ? 'bg-scum-orange text-white shadow-sm' : 'bg-white/5 border border-white/5 text-white/40 hover:bg-white/10'}`}>
            {day.charAt(0)}
          </button>
        ))}

        <div className="w-px h-6 bg-white/10 mx-0.5 flex-shrink-0 hidden sm:block" />

        <input type="time" value={formStart} onChange={e => setFormStart(e.target.value)}
          className="w-[80px] px-1.5 py-1.5 bg-white/5 border border-white/10 rounded-lg text-white text-[11px] focus:outline-none focus:ring-2 focus:ring-scum-orange font-mono text-center flex-shrink-0" />
        <span className="text-[9px] text-white/30 font-semibold flex-shrink-0">–</span>
        <input type="time" value={formEnd} onChange={e => setFormEnd(e.target.value)}
          className="w-[80px] px-1.5 py-1.5 bg-white/5 border border-white/10 rounded-lg text-white text-[11px] focus:outline-none focus:ring-2 focus:ring-scum-orange font-mono text-center flex-shrink-0" />

        <input ref={fileInputRef} type="file" accept=".ini" onChange={handleFileChange} className="hidden" />
        <button type="button" onClick={() => fileInputRef.current?.click()}
          className={`min-w-0 flex-1 px-2.5 py-1.5 border rounded-lg text-[11px] font-semibold transition-all flex items-center justify-center gap-1.5 truncate ${
            formFile
              ? 'border-emerald-500/40 bg-emerald-500/10 text-emerald-400'
              : formExistingFile
              ? 'border-scum-orange/30 bg-scum-orange/10 text-scum-orange'
              : 'border-white/10 bg-white/5 text-white/50 hover:border-scum-orange/30'
          }`}>
          {formFile ? <FileText size={12} className="flex-shrink-0" /> : <Upload size={12} className="flex-shrink-0" />}
          <span className="truncate">{formFile ? formFile.name : formExistingFile || '.ini'}</span>
        </button>

        <button onClick={closeForm} disabled={formSubmitting}
          className="px-2.5 py-1.5 bg-white/5 hover:bg-white/10 border border-white/10 rounded-lg text-[11px] font-semibold text-white transition-colors flex-shrink-0">
          {t('settings.settingsScheduler.form.cancel')}
        </button>
        <button onClick={handleSubmit} disabled={formSubmitting}
          className="px-3 py-1.5 bg-scum-orange hover:bg-scum-orange/90 disabled:bg-scum-orange/50 text-white rounded-lg text-[11px] font-bold transition-colors flex items-center gap-1 shadow-lg shadow-scum-orange/15 flex-shrink-0">
          {formSubmitting ? <Loader2 size={12} className="animate-spin" /> : t('settings.settingsScheduler.form.save')}
        </button>
      </div>
    </div>
  );

  // --- LOADING / ERROR ---
  if (loading) return (
    <div className="flex items-center justify-center py-24 card bg-black/10">
      <div className="text-center space-y-3">
        <Loader2 className="w-10 h-10 animate-spin text-scum-orange mx-auto" />
        <p className="text-white/60 text-sm">{t('settings.settingsScheduler.loading')}</p>
      </div>
    </div>
  );

  if (error) return (
    <div className="card p-8 text-center space-y-4 border border-red-500/20 bg-red-500/5">
      <AlertTriangle className="w-12 h-12 text-red-400 mx-auto" />
      <div className="text-red-400 font-bold text-lg">{t('settings.settingsScheduler.error.initTitle')}</div>
      <p className="text-white/60 text-sm max-w-md mx-auto">{error}</p>
      <button onClick={loadAll} className="px-5 py-2 bg-white/5 hover:bg-white/10 border border-white/10 rounded-lg text-sm text-white inline-flex items-center gap-2 transition-all">{t('settings.settingsScheduler.error.retry')}</button>
    </div>
  );

  return (
    <div className="space-y-6">
      {/* Header + Toggle Global */}
      <div className="flex flex-col lg:flex-row justify-between items-start lg:items-center gap-4 bg-white/5 border border-white/10 rounded-xl p-5 backdrop-blur-sm relative overflow-hidden">
        <div className="absolute top-0 right-0 p-4 opacity-5 pointer-events-none"><Settings size={120} className="text-white" /></div>
        <div className="space-y-1 z-10">
          <h2 className="text-lg font-bold text-white flex items-center gap-2">
            <Clock className="text-scum-orange w-5 h-5 animate-pulse" />
            {t('settings.settingsScheduler.title')}
          </h2>
          <p className="text-xs text-white/60 max-w-2xl leading-relaxed">
            {t('settings.settingsScheduler.descriptionPre')}<code className="text-xs bg-white/5 px-1 py-0.5 rounded text-scum-orange">ServerSettings.ini</code>{t('settings.settingsScheduler.descriptionPost')}
          </p>
          {activeRoutine && (
            <div className="inline-flex items-center gap-2 px-2.5 py-1 mt-2 rounded-full border border-emerald-500/20 bg-emerald-500/5 text-emerald-400 text-xs">
              <span className="relative flex h-2 w-2"><span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span><span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-500"></span></span>
              {t('settings.settingsScheduler.runningNow')} <strong>{activeRoutine.name}</strong> ({activeRoutine.preset_file})
            </div>
          )}
        </div>
        <div className="flex items-center gap-3 bg-black/30 border border-white/5 px-4 py-3 rounded-lg z-10 w-full lg:w-auto justify-between lg:justify-start">
          <div className="text-left">
            <span className="text-xs font-semibold text-white block">{t('settings.settingsScheduler.globalStatus.label')}</span>
            <span className="text-[10px] text-white/40 block">{globalEnabled ? t('settings.settingsScheduler.globalStatus.monitoring') : t('settings.settingsScheduler.globalStatus.inactive')}</span>
          </div>
          <button onClick={handleToggleGlobal} disabled={actionLoading}
            className={`relative inline-flex h-6 w-11 flex-shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors duration-200 ${globalEnabled ? 'bg-scum-orange' : 'bg-white/10'}`}>
            <span className={`pointer-events-none inline-block h-5 w-5 transform rounded-full bg-white shadow transition duration-200 ${globalEnabled ? 'translate-x-5' : 'translate-x-0'}`} />
          </button>
        </div>
      </div>

      {/* Toolbar */}
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-3 bg-white/5 border border-white/10 rounded-xl p-4">
        <div className="text-left">
          <h3 className="font-bold text-white text-sm flex items-center gap-1.5"><Calendar className="text-scum-orange w-4.5 h-4.5" /> {t('settings.settingsScheduler.scheduledEvents.title')}</h3>
          <p className="text-[10px] text-white/50 mt-0.5">{t('settings.settingsScheduler.scheduledEvents.description')}</p>
        </div>
        <button onClick={openCreateForm} disabled={actionLoading || editingId !== null}
          className="w-full sm:w-auto px-3.5 py-1.5 bg-scum-orange hover:bg-scum-orange/90 disabled:bg-scum-orange/40 text-white rounded-lg text-xs font-semibold transition-all flex items-center justify-center gap-1.5 shadow-lg shadow-scum-orange/10">
          <Plus size={14} /> {t('settings.settingsScheduler.newEvent')}
        </button>
      </div>

      {/* Grid de Eventos */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {/* Inline form (top of grid) */}
        {editingId === 'new' && renderInlineForm()}

        {filtered.map(routine => {
          const isActive = routine.id === activeRoutineId && globalEnabled;

          // If editing this routine, render inline form instead of card
          if (editingId === routine.id) return <div key={routine.id} className="col-span-1 md:col-span-2">{renderInlineForm()}</div>;

          return (
            <div key={routine.id} className={`card flex flex-col justify-between border transition-all ${isActive ? 'border-emerald-500 bg-emerald-500/5 ring-1 ring-emerald-500/30' : routine.enabled ? 'border-white/10 hover:border-scum-orange/45' : 'border-white/5 bg-black/25 opacity-60'}`}>
              <div className="p-4 space-y-3.5">
                <div className="flex items-start justify-between gap-3">
                  <div className="text-left truncate">
                    <h4 className="font-bold text-white text-xs leading-tight truncate" title={routine.name}>{routine.name}</h4>
                    <span className="inline-flex items-center gap-1 text-[10px] text-white/40 mt-1 font-mono"><FileText size={11} />{routine.preset_file}</span>
                  </div>
                  <label className="relative inline-flex items-center cursor-pointer flex-shrink-0">
                    <input type="checkbox" checked={routine.enabled} onChange={() => handleToggleRoutine(routine)} className="sr-only peer" />
                    <div className="w-8 h-4.5 bg-white/10 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-3.5 after:w-3.5 after:transition-all peer-checked:bg-scum-orange"></div>
                  </label>
                </div>
                <div className="flex gap-1 justify-between bg-black/25 p-2 rounded-lg border border-white/5">
                  {DAYS_ABBR.map((day, idx) => (
                    <span key={idx} className={`text-[8px] font-bold w-6 h-6 rounded-md flex items-center justify-center transition-all ${routine.days_of_week.includes(idx) ? 'bg-scum-orange text-white shadow-sm' : 'text-white/20 bg-white/5'}`}>{day.charAt(0)}</span>
                  ))}
                </div>
                <div className="flex items-center justify-between text-[10px] border-t border-white/5 pt-2.5">
                  <div className="flex items-center gap-1.5 text-white/60"><Clock size={11} className="text-scum-orange" /><span className="font-semibold">{routine.start_time} - {routine.end_time}</span></div>
                  {isActive ? (
                    <span className="flex items-center gap-1 px-1.5 py-0.5 rounded bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 font-bold text-[9px] uppercase tracking-wide">
                      <span className="relative flex h-1.5 w-1.5"><span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span><span className="relative inline-flex rounded-full h-1.5 w-1.5 bg-emerald-500"></span></span>{t('settings.settingsScheduler.card.active')}
                    </span>
                  ) : routine.enabled ? <span className="text-white/40 text-[9px]">{t('settings.settingsScheduler.card.scheduled')}</span> : <span className="text-white/20 text-[9px] line-through">{t('settings.settingsScheduler.card.inactive')}</span>}
                </div>
              </div>
              <div className="bg-white/5 border-t border-white/5 p-2 flex gap-1.5">
                <button onClick={() => openEditForm(routine)} disabled={editingId !== null}
                  className="flex-1 px-2.5 py-1.5 bg-white/5 hover:bg-white/10 border border-white/10 rounded-md text-[10px] font-semibold text-white transition-all flex items-center justify-center gap-1 disabled:opacity-40">
                  <Edit2 size={11} /> {t('settings.settingsScheduler.card.edit')}
                </button>
                <button onClick={() => handleDelete(routine)} disabled={editingId !== null}
                  className="px-2.5 py-1.5 bg-red-500/5 hover:bg-red-500/15 border border-red-500/20 rounded-md text-[10px] font-semibold text-red-400 transition-all flex items-center justify-center disabled:opacity-40">
                  <Trash2 size={11} />
                </button>
              </div>
            </div>
          );
        })}
      </div>

      {/* Empty state */}
      {filtered.length === 0 && editingId === null && (
        <div className="text-center py-16 text-white/50 card border-dashed border-white/5 bg-black/10">
          <Calendar size={40} className="mx-auto text-white/20 mb-3" />
          <p className="text-xs">{searchQuery ? t('settings.settingsScheduler.empty.noResults') : t('settings.settingsScheduler.empty.noEvents')}</p>
        </div>
      )}
    </div>
  );
}
