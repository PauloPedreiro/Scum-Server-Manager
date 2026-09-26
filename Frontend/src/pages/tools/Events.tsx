import { useEffect, useState, useMemo, useRef } from 'react';
import { useTranslation } from 'react-i18next';
import { 
  Plus, Trash2, Play, Square, Terminal, CheckCircle2, XCircle, 
  MapPin, Clock, Calendar, ArrowRight, Settings, Sparkles, RefreshCw
} from 'lucide-react';
import { ModuleToolPage } from '@/components/tools/ModuleToolPage';
import { alert } from '@/lib/alert';
import { 
  listEvents, createEvent, getEventDetails, updateEvent, deleteEvent,
  startEvent, stopEvent, addCoordinate, removeCoordinate, addStartupCommand,
  removeStartupCommand, updateStartupCommand, testCommand, listTestedCommands,
  registerTestedCommand, syncStartupCommands, syncCoordinates,
  type EventConfig, type EventCoordinate, type EventStartupCommand, type TestedCommand
} from '@/services/events';

const calculateDurationMinutes = (start: string, end: string): number => {
  const [startH, startM] = start.split(':').map(Number);
  const [endH, endM] = end.split(':').map(Number);
  
  let startMinutes = startH * 60 + startM;
  let endMinutes = endH * 60 + endM;
  
  if (endMinutes < startMinutes) {
    // Caso vire o dia (ex: 23:00 até 02:00)
    endMinutes += 24 * 60;
  }
  
  return endMinutes - startMinutes;
};

const formatDuration = (minutes: number): string => {
  const hrs = Math.floor(minutes / 60);
  const mins = minutes % 60;
  return hrs > 0 ? `${hrs}h${mins > 0 ? `${mins}min` : ''}` : `${minutes}min`;
};

const getEndTimeString = (startTime: string | null, durationMinutes: number): string => {
  if (!startTime) return '';
  const timeOnly = startTime.includes('|') ? startTime.split('|')[0] : startTime;
  const [h, m] = timeOnly.split(':').map(Number);
  const totalMinutes = h * 60 + m + durationMinutes;
  const endH = Math.floor(totalMinutes / 60) % 24;
  const endM = totalMinutes % 60;
  return `${String(endH).padStart(2, '0')}:${String(endM).padStart(2, '0')}`;
};

const parseRawCoordinates = (coordStr: string): { x: number; y: number; z: number } | null => {
  if (!coordStr) return null;
  const str = coordStr.trim();
  
  // Format 1: {X=-195909.000 Y=-33639.000 Z=35788.141|P=...}
  const matchScum = str.match(/X=([\d.-]+)[,\s]+Y=([\d.-]+)[,\s]+Z=([\d.-]+)/i);
  if (matchScum) {
    return { x: parseFloat(matchScum[1]), y: parseFloat(matchScum[2]), z: parseFloat(matchScum[3]) };
  }
  
  // Format 2: #ScheduleWorldEvent BP_CargoDropEvent X Y Z
  const matchCmd = str.match(/#ScheduleWorldEvent\s+\S+\s+([\d.-]+)\s+([\d.-]+)\s+([\d.-]+)/i);
  if (matchCmd) {
    return { x: parseFloat(matchCmd[1]), y: parseFloat(matchCmd[2]), z: parseFloat(matchCmd[3]) };
  }
  
  // Format 3: General fallback of numbers
  const cleaned = str.replace(/,/g, ' ').replace(/{/g, ' ').replace(/}/g, ' ').replace(/\|/g, ' ');
  const parts = cleaned.split(/\s+/).map(p => {
    const pClean = p.replace(/[^\d.-]/g, '');
    return pClean ? parseFloat(pClean) : null;
  }).filter((v): v is number => v !== null && !isNaN(v));
  
  if (parts.length >= 3) {
    return { x: parts[0], y: parts[1], z: parts[2] };
  }
  
  return null;
};

const formatScheduleValue = (scheduleValue: string | null, durationMinutes: number, t: any): string => {
  if (!scheduleValue) return t('tools.events.scheduleManual', { defaultValue: 'Manual' });
  const timeOnly = scheduleValue.includes('|') ? scheduleValue.split('|')[0] : scheduleValue;
  const endTime = getEndTimeString(timeOnly, durationMinutes);
  
  let result = `${timeOnly} - ${endTime}`;
  
  if (scheduleValue.includes('|')) {
    const daysPart = scheduleValue.split('|')[1];
    if (daysPart) {
      const dayIndexes = daysPart.split(',').map(Number);
      const selectedNames = dayIndexes.map(idx => t(`tools.events.day_${idx}`)).filter(Boolean);
      if (selectedNames.length > 0) {
        result += ` (${selectedNames.join(', ')})`;
      }
    }
  }
  return result;
};

const combineCommandAndCoordinates = (base: string, qty: string, coord: string): string => {
  const cleanBase = base.trim();
  const cleanCoord = coord.trim();
  if (!cleanCoord) {
    if (cleanBase.startsWith('#SpawnItem') && qty.trim()) {
      if (!/\s+\d+(\s+|$)/.test(cleanBase)) {
        return `${cleanBase} ${qty.trim()}`;
      }
    }
    return cleanBase;
  }
  
  if (cleanBase.startsWith('#SpawnItem')) {
    if (cleanBase.toLowerCase().includes('location')) {
      return `${cleanBase} "${cleanCoord}"`;
    }
    const cleanQty = qty.trim() || '1';
    return `${cleanBase} ${cleanQty} Location "${cleanCoord}"`;
  }
  
  return `${cleanBase} ${cleanCoord}`;
};

export default function Events() {
  const { t } = useTranslation();

  // Estados gerais
  const [events, setEvents] = useState<EventConfig[]>([]);
  const [selectedEventId, setSelectedEventId] = useState<number | null>(null);
  const [selectedEventDetails, setSelectedEventDetails] = useState<
    (EventConfig & { coordinates: EventCoordinate[]; commands: EventStartupCommand[] }) | null
  >(null);
  const [testedCommands, setTestedCommands] = useState<TestedCommand[]>([]);

  // Estados de loading
  const [loadingEvents, setLoadingEvents] = useState(false);
  const [loadingDetails, setLoadingDetails] = useState(false);
  const [loadingTested, setLoadingTested] = useState(false);
  const [testingCommand, setTestingCommand] = useState(false);

  // Formulário de evento
  const [showCreateForm, setShowCreateForm] = useState(false);
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [startTime, setStartTime] = useState('14:30');
  const [endTime, setEndTime] = useState('16:00');
  const [repeatEvent, setRepeatEvent] = useState(false);
  const [selectedWeekdays, setSelectedWeekdays] = useState<number[]>([]);

  // Estados de edição de evento diretamente no card
  const [editingEventId, setEditingEventId] = useState<number | null>(null);
  const [editName, setEditName] = useState('');
  const [editDescription, setEditDescription] = useState('');
  const [editStartTime, setEditStartTime] = useState('14:30');
  const [editEndTime, setEditEndTime] = useState('16:00');
  const [editIsRepeating, setEditIsRepeating] = useState(false);
  const [editWeekdays, setEditWeekdays] = useState<number[]>([]);

  // Formulários de sub-ítens do evento selecionado
  const [newCoordName, setNewCoordName] = useState('');
  const [newRawCoord, setNewRawCoord] = useState('');

  const [newCommandString, setNewCommandString] = useState('');
  const [searchTerm, setSearchTerm] = useState('');
  const [isOpen, setIsOpen] = useState(false);
  const [showHomologation, setShowHomologation] = useState(false);

  // Coordenadas na criação de eventos
  const [creationCoordInput, setCreationCoordInput] = useState('');
  const [creationCoords, setCreationCoords] = useState<Array<{ raw: string; parsed: { x: number; y: number; z: number } }>>([]);

  // Edição em memória de comandos do evento selecionado
  const [editableCommands, setEditableCommands] = useState<EventStartupCommand[]>([]);
  const [editableCoordinates, setEditableCoordinates] = useState<EventCoordinate[]>([]);
  const [savingCommands, setSavingCommands] = useState(false);

  // Painel de teste de RCON
  const [testBaseCmd, setTestBaseCmd] = useState('');
  const [testQty, setTestQty] = useState('1');
  const [testCoord, setTestCoord] = useState('');
  const [testResponse, setTestResponse] = useState<string | null>(null);
  const [testSuccess, setTestSuccess] = useState<boolean | null>(null);

  const dropdownRef = useRef<HTMLDivElement>(null);

  // Fechar dropdown ao clicar fora
  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setIsOpen(false);
      }
    }
    document.addEventListener('mousedown', handleClickOutside);
    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
    };
  }, []);

  // Sincronizar os comandos e coordenadas editáveis em memória com os detalhes do evento carregado do backend
  useEffect(() => {
    if (selectedEventDetails) {
      setEditableCommands(selectedEventDetails.commands || []);
      setEditableCoordinates(selectedEventDetails.coordinates || []);
    } else {
      setEditableCommands([]);
      setEditableCoordinates([]);
    }
  }, [selectedEventDetails]);

  // Carregar eventos e lista de testados no início
  useEffect(() => {
    loadEvents();
    loadTestedCommands();
  }, []);

  // Recarregar detalhes quando o evento selecionado mudar
  useEffect(() => {
    if (selectedEventId !== null) {
      loadEventDetails(selectedEventId);
    } else {
      setSelectedEventDetails(null);
    }
  }, [selectedEventId]);

  const loadEvents = async () => {
    setLoadingEvents(true);
    try {
      const res = await listEvents();
      if (res.success) {
        setEvents(res.data || []);
      } else {
        await alert({
          icon: 'error',
          title: t('tools.events.loadEventsError', { defaultValue: 'Erro ao carregar eventos' }),
          text: res.message || res.error
        });
      }
    } catch (err: any) {
      console.error(err);
    } finally {
      setLoadingEvents(false);
    }
  };

  const loadTestedCommands = async () => {
    setLoadingTested(true);
    try {
      const res = await listTestedCommands();
      if (res.success) {
        setTestedCommands(res.data || []);
      }
    } catch (err: any) {
      console.error(err);
    } finally {
      setLoadingTested(false);
    }
  };

  const loadEventDetails = async (id: number) => {
    setLoadingDetails(true);
    try {
      const res = await getEventDetails(id);
      if (res.success) {
        setSelectedEventDetails(res.data);
      } else {
        await alert({
          icon: 'error',
          title: t('tools.events.loadDetailsError', { defaultValue: 'Erro ao carregar detalhes' }),
          text: res.message || res.error
        });
      }
    } catch (err: any) {
      console.error(err);
    } finally {
      setLoadingDetails(false);
    }
  };

  const startEditing = (ev: EventConfig) => {
    setEditingEventId(ev.event_id);
    setEditName(ev.name);
    setEditDescription(ev.description || '');
    const timeOnly = ev.schedule_value ? (ev.schedule_value.includes('|') ? ev.schedule_value.split('|')[0] : ev.schedule_value) : '14:30';
    setEditStartTime(timeOnly);
    setEditEndTime(getEndTimeString(timeOnly, ev.duration_minutes));
    setEditIsRepeating(ev.schedule_value ? ev.schedule_value.includes('|') : false);
    const currentDays = ev.schedule_value && ev.schedule_value.includes('|') 
      ? ev.schedule_value.split('|')[1].split(',').filter(x => x !== '').map(Number) 
      : [];
    setEditWeekdays(currentDays);
  };

  const handleSaveEdit = async (ev: EventConfig) => {
    if (!editName.trim()) return;
    const calculatedDuration = calculateDurationMinutes(editStartTime, editEndTime);
    let scheduleValue = editStartTime;
    if (editIsRepeating) {
      scheduleValue = `${editStartTime}|${editWeekdays.join(',')}`;
    }

    try {
      const res = await updateEvent(ev.event_id, {
        name: editName,
        description: editDescription,
        webhook_url: ev.webhook_url || null,
        duration_minutes: calculatedDuration,
        recurrence_interval_minutes: ev.recurrence_interval_minutes || null,
        schedule_type: 'daily',
        schedule_value: scheduleValue
      });

      if (res.success) {
        setEditingEventId(null);
        await alert({
          icon: 'success',
          title: t('tools.events.successTitle', { defaultValue: 'Sucesso' }),
          text: t('tools.events.allSaved', { defaultValue: 'Alterações salvas com sucesso!' })
        });
        loadEvents();
        if (selectedEventId === ev.event_id) {
          loadEventDetails(ev.event_id);
        }
      } else {
        await alert({
          icon: 'error',
          title: t('tools.events.updateErrorTitle', { defaultValue: 'Erro ao atualizar' }),
          text: res.message || res.error
        });
      }
    } catch (err: any) {
      console.error(err);
    }
  };

  // Handlers de Ações em Eventos
  const handleCreateEvent = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!name.trim()) return;

    try {
      const calculatedDuration = calculateDurationMinutes(startTime, endTime);
      const scheduleValue = startTime;

      const res = await createEvent({
        name,
        description,
        webhook_url: null,
        duration_minutes: calculatedDuration,
        recurrence_interval_minutes: null,
        schedule_type: 'daily',
        schedule_value: scheduleValue
      });

      if (res.success) {
        const eventId = res.data.event_id;

        // Adicionar cada coordenada cadastrada no formulário de criação
        for (let i = 0; i < creationCoords.length; i++) {
          const coord = creationCoords[i];
          try {
            await addCoordinate(eventId, {
              name: t('tools.events.pointLabel', { num: i + 1, defaultValue: `Ponto ${i + 1}` }),
              x: coord.parsed.x,
              y: coord.parsed.y,
              z: coord.parsed.z
            });
          } catch (coordErr) {
            console.error('Erro ao adicionar coordenada durante a criação:', coordErr);
          }
        }

        await alert({
          icon: 'success',
          title: t('tools.events.successTitle', { defaultValue: 'Sucesso' }),
          text: t('tools.events.successCreated', { defaultValue: 'Evento criado com sucesso!' })
        });
        setName('');
        setDescription('');
        setStartTime('14:30');
        setEndTime('16:00');
        setCreationCoords([]);
        setCreationCoordInput('');
        setShowCreateForm(false);
        loadEvents();
      } else {
        await alert({
          icon: 'error',
          title: t('tools.events.createEventError', { defaultValue: 'Erro ao criar evento' }),
          text: res.message || res.error
        });
      }
    } catch (err: any) {
      console.error(err);
    }
  };

  const handleUpdateEventSchedule = async (ev: EventConfig, newScheduleValue: string) => {
    try {
      const res = await updateEvent(ev.event_id, {
        name: ev.name,
        description: ev.description || '',
        webhook_url: ev.webhook_url || null,
        duration_minutes: ev.duration_minutes,
        recurrence_interval_minutes: ev.recurrence_interval_minutes || null,
        schedule_type: 'daily',
        schedule_value: newScheduleValue
      });
      if (res.success) {
        loadEvents();
        // Se este evento estiver selecionado e exibindo detalhes, atualize os detalhes selecionados
        if (selectedEventId === ev.event_id) {
          loadEventDetails(ev.event_id);
        }
      } else {
        await alert({
          icon: 'error',
          title: t('tools.events.updateScheduleError', { defaultValue: 'Erro ao atualizar agendamento' }),
          text: res.message || res.error
        });
      }
    } catch (err: any) {
      console.error(err);
    }
  };

  const handleDeleteEvent = async (id: number) => {
    const ev = events.find(e => e.event_id === id);
    const evName = ev ? ev.name : '';
    const confirm = await alert({
      icon: 'warning',
      title: t('tools.events.confirmDeleteTitle', { defaultValue: 'Deletar evento?' }),
      text: t('tools.events.confirmDeleteText', { name: evName, defaultValue: 'Tem certeza que deseja deletar este evento? Todas as coordenadas e comandos associados serão excluídos permanentemente.' }),
      showCancelButton: true,
      confirmButtonText: t('tools.events.confirmDeleteBtn', { defaultValue: 'Deletar' }),
      cancelButtonText: t('tools.events.cancel', { defaultValue: 'Cancelar' })
    });

    if (!confirm.isConfirmed) return;

    try {
      const res = await deleteEvent(id);
      if (res.success) {
        if (selectedEventId === id) setSelectedEventId(null);
        await alert({
          icon: 'success',
          title: t('tools.events.successTitle', { defaultValue: 'Sucesso' }),
          text: t('tools.events.deletedSuccess', { defaultValue: 'Evento deletado!' })
        });
        loadEvents();
      } else {
        await alert({
          icon: 'error',
          title: t('tools.events.deleteErrorTitle', { defaultValue: 'Erro ao deletar' }),
          text: res.message || res.error
        });
      }
    } catch (err: any) {
      console.error(err);
    }
  };

  const handleStartEvent = async (id: number) => {
    try {
      const res = await startEvent(id);
      if (res.success) {
        await alert({
          icon: 'success',
          title: t('tools.events.eventStartedTitle', { defaultValue: 'Evento Iniciado' }),
          text: t('tools.events.eventStartedText', { defaultValue: 'O evento foi ativado e seus comandos iniciais foram enviados para a fila RCON.' })
        });
        loadEvents();
        if (selectedEventId === id) loadEventDetails(id);
      } else {
        await alert({
          icon: 'error',
          title: t('tools.events.startEventErrorTitle', { defaultValue: 'Erro ao iniciar evento' }),
          text: res.message || res.error
        });
      }
    } catch (err: any) {
      console.error(err);
    }
  };

  const handleStopEvent = async (id: number) => {
    try {
      const res = await stopEvent(id);
      if (res.success) {
        await alert({
          icon: 'success',
          title: t('tools.events.eventStoppedTitle', { defaultValue: 'Evento Finalizado' }),
          text: t('tools.events.eventStoppedText', { defaultValue: 'O evento foi definido como inativo.' })
        });
        loadEvents();
        if (selectedEventId === id) loadEventDetails(id);
      } else {
        await alert({
          icon: 'error',
          title: t('tools.events.stopEventErrorTitle', { defaultValue: 'Erro ao finalizar evento' }),
          text: res.message || res.error
        });
      }
    } catch (err: any) {
      console.error(err);
    }
  };

  // Coordenadas
  const handleAddCoordinate = (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedEventId || !newCoordName.trim() || !newRawCoord.trim()) return;

    const parsed = parseRawCoordinates(newRawCoord);
    if (!parsed) {
      alert({
        icon: 'error',
        title: t('tools.events.invalidFormat', { defaultValue: 'Formato Inválido' }),
        text: t('tools.events.invalidCoords', { defaultValue: 'Não foi possível extrair as coordenadas. Cole a localização bruta (ex: {X=... Y=... Z=...}) ou números separados por espaço.' })
      });
      return;
    }

    const newCoord: EventCoordinate = {
      coord_id: -Date.now(),
      event_id: selectedEventId,
      name: newCoordName.trim(),
      x: parsed.x,
      y: parsed.y,
      z: parsed.z
    };

    setEditableCoordinates(prev => [...prev, newCoord]);
    setNewCoordName('');
    setNewRawCoord('');
  };

  const handleRemoveCoordinate = (coordId: number) => {
    setEditableCoordinates(prev => prev.filter(c => c.coord_id !== coordId));
  };

  // Comandos Iniciais (Edição em Memória)
  const hasUnsavedChanges = useMemo(() => {
    if (!selectedEventDetails) return false;

    // Comandos
    const dbCmds = selectedEventDetails.commands || [];
    if (editableCommands.length !== dbCmds.length) return true;
    for (let i = 0; i < editableCommands.length; i++) {
      const ec = editableCommands[i];
      const dc = dbCmds[i];
      if (ec.command_string !== dc.command_string) return true;
      if (ec.recurrence_interval_minutes !== dc.recurrence_interval_minutes) return true;
    }

    // Coordenadas
    const dbCoords = selectedEventDetails.coordinates || [];
    if (editableCoordinates.length !== dbCoords.length) return true;
    for (let i = 0; i < editableCoordinates.length; i++) {
      const ec = editableCoordinates[i];
      const dc = dbCoords[i];
      if (ec.name !== dc.name) return true;
      if (ec.x !== dc.x) return true;
      if (ec.y !== dc.y) return true;
      if (ec.z !== dc.z) return true;
    }

    return false;
  }, [editableCommands, editableCoordinates, selectedEventDetails]);

  const handleAddStartupCommand = (e: React.FormEvent) => {
    e.preventDefault();
    const cmdToAdd = newCommandString.trim() || searchTerm.trim();
    if (!selectedEventId || !cmdToAdd) return;

    const newCmd: EventStartupCommand = {
      startup_id: -Date.now(),
      event_id: selectedEventId,
      command_string: cmdToAdd,
      order_index: editableCommands.length,
      recurrence_interval_minutes: null,
      last_execution_time: null
    };

    setEditableCommands(prev => [...prev, newCmd]);
    setNewCommandString('');
    setSearchTerm('');
  };

  const handleToggleCommandRecurrence = (cmd: EventStartupCommand, active: boolean) => {
    setEditableCommands(prev => prev.map(c => {
      if (c.startup_id === cmd.startup_id) {
        return { ...c, recurrence_interval_minutes: active ? 20 : null };
      }
      return c;
    }));
  };

  const handleUpdateCommandRecurrenceInterval = (cmd: EventStartupCommand, interval: number | null) => {
    if (interval !== null && (isNaN(interval) || interval <= 0)) return;
    setEditableCommands(prev => prev.map(c => {
      if (c.startup_id === cmd.startup_id) {
        return { ...c, recurrence_interval_minutes: interval };
      }
      return c;
    }));
  };

  const handleRemoveStartupCommand = (startupId: number) => {
    setEditableCommands(prev => prev.filter(c => c.startup_id !== startupId));
  };

  const handleSaveStartupCommands = async () => {
    if (!selectedEventId) return;
    setSavingCommands(true);
    try {
      // 1. Salvar Comandos
      const cmdPayload = editableCommands.map(cmd => ({
        command_string: cmd.command_string,
        recurrence_interval_minutes: cmd.recurrence_interval_minutes
      }));
      const resCmd = await syncStartupCommands(selectedEventId, cmdPayload);
      if (!resCmd.success) {
        throw new Error(resCmd.message || resCmd.error || t('tools.events.saveErrorTitle', { defaultValue: 'Erro ao salvar' }));
      }

      // 2. Salvar Coordenadas
      const coordPayload = editableCoordinates.map(c => ({
        name: c.name,
        x: c.x,
        y: c.y,
        z: c.z
      }));
      const resCoord = await syncCoordinates(selectedEventId, coordPayload);
      if (!resCoord.success) {
        throw new Error(resCoord.message || resCoord.error || t('tools.events.saveErrorTitle', { defaultValue: 'Erro ao salvar' }));
      }

      await alert({
        icon: 'success',
        title: t('tools.events.successTitle', { defaultValue: 'Sucesso' }),
        text: t('tools.events.allSaved', { defaultValue: 'Alterações salvas com sucesso!' })
      });
      loadEventDetails(selectedEventId);
    } catch (err: any) {
      console.error(err);
      await alert({
        icon: 'error',
        title: t('tools.events.saveErrorTitle', { defaultValue: 'Erro ao salvar' }),
        text: err.message || t('tools.events.saveErrorTitle', { defaultValue: 'Erro ao salvar' })
      });
    } finally {
      setSavingCommands(false);
    }
  };

  // Teste de Comando RCON (Homologação)
  const handleTestCommand = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!testBaseCmd.trim() || testingCommand) return;

    setTestingCommand(true);
    setTestResponse(null);
    setTestSuccess(null);

    try {
      const combined = combineCommandAndCoordinates(testBaseCmd, testQty, testCoord);
      const res = await testCommand(combined);
      if (res.success) {
        setTestSuccess(true);
        setTestResponse(res.data.response || t('tools.events.testSuccessText', { defaultValue: 'Comando executado com sucesso, mas sem resposta.' }));
      } else {
        setTestSuccess(false);
        setTestResponse(res.error || res.message || t('tools.events.testFailText', { defaultValue: 'Falha ao executar o comando.' }));
      }
    } catch (err: any) {
      setTestSuccess(false);
      setTestResponse(err.message || t('tools.events.testErrorText', { defaultValue: 'Erro inesperado.' }));
    } finally {
      setTestingCommand(false);
    }
  };

  const handleRegisterCommand = async () => {
    if (!testBaseCmd.trim()) return;

    const requiresCoords = testCoord.trim() !== '' ? 1 : 0;
    
    let commandToRegister = testBaseCmd.trim();
    if (commandToRegister.startsWith('#SpawnItem')) {
      if (!commandToRegister.toLowerCase().includes('location')) {
        const cleanQty = testQty.trim() || '1';
        commandToRegister = `${commandToRegister} ${cleanQty} Location`;
      }
    }

    try {
      const res = await registerTestedCommand({
        command: commandToRegister,
        requires_coordinates: requiresCoords
      });
      if (res.success) {
        await alert({
          icon: 'success',
          title: t('tools.events.successTitle', { defaultValue: 'Sucesso' }),
          text: t('tools.events.registerSuccessText', { defaultValue: 'Comando registrado no catálogo!' })
        });
        loadTestedCommands();
      } else {
        await alert({
          icon: 'error',
          title: t('tools.events.errorTitle', { defaultValue: 'Erro' }),
          text: res.message || res.error
        });
      }
    } catch (err: any) {
      console.error(err);
      await alert({
        icon: 'error',
        title: t('tools.events.errorTitle', { defaultValue: 'Erro' }),
        text: t('tools.events.registerErrorText', { defaultValue: 'Erro ao registrar comando.' })
      });
    }
  };

  const filteredCommands = useMemo(() => {
    if (!searchTerm.trim()) return testedCommands;
    return testedCommands.filter((tc) =>
      tc.command_string.toLowerCase().includes(searchTerm.toLowerCase())
    );
  }, [testedCommands, searchTerm]);

  const handleSelectTestedCommand = async (tc: TestedCommand) => {
    if (!selectedEventId) return;

    let finalCommand = tc.command_string;

    if (tc.requires_coordinates === 1) {
      const confirm = await alert({
        title: t('tools.events.coordsNeededTitle', { defaultValue: 'Coordenadas Necessárias' }),
        text: t('tools.events.coordsNeededText', { defaultValue: 'Este comando exige coordenadas. Cole la localización del SCUM (ex: {X=... Y=... Z=...}):' }),
        input: 'text',
        inputPlaceholder: t('tools.events.telemetryPlaceholder', { defaultValue: 'Cole aqui a telemetria do jogo...' }),
        showCancelButton: true,
        confirmButtonText: t('tools.events.confirmBtn', { defaultValue: 'Confirmar' }),
        cancelButtonText: t('tools.events.cancel', { defaultValue: 'Cancelar' })
      });

      if (confirm.isConfirmed && confirm.value) {
        finalCommand = combineCommandAndCoordinates(tc.command_string, '', confirm.value);
      } else {
        return;
      }
    }

    const newCmd: EventStartupCommand = {
      startup_id: -Date.now(),
      event_id: selectedEventId,
      command_string: finalCommand,
      order_index: editableCommands.length,
      recurrence_interval_minutes: null,
      last_execution_time: null
    };

    setEditableCommands(prev => [...prev, newCmd]);
    setNewCommandString('');
    setSearchTerm('');
    setIsOpen(false);
  };

  return (
    <ModuleToolPage
      title={t('tools.events.title', { defaultValue: 'Agendador de Eventos & Homologação' })}
      subtitle={t('tools.events.subtitle', {
        defaultValue: 'Gerencie eventos personalizados com execução múltipla de comandos e fila RCON segura.',
      })}
    >
      <div className="space-y-6">
        
        {/* HOMOLOGAÇÃO DE COMANDOS RCON (Colapsável) */}
        <div className="card p-4 space-y-3 border border-white/5 bg-white/[0.02]">
          <button
            type="button"
            onClick={() => setShowHomologation(!showHomologation)}
            className="w-full flex items-center justify-between text-left text-sm font-bold text-white hover:text-scum-orange transition-colors"
          >
            <div className="flex items-center gap-2">
              <Sparkles className="text-scum-orange" size={16} />
              <span>{t('tools.events.homologationTitle', { defaultValue: 'Homologação de Comandos RCON' })}</span>
            </div>
            <span className="text-xs text-white/40 font-mono">
              {showHomologation 
                ? t('tools.events.hidePanel', { defaultValue: 'Ocultar painel ▲' }) 
                : t('tools.events.showPanel', { defaultValue: 'Mostrar painel ▼' })}
            </span>
          </button>

          {showHomologation && (
            <div className="pt-3 border-t border-white/5 grid grid-cols-1 md:grid-cols-2 gap-6 items-start">
              <div className="space-y-3">
                <p className="text-xs text-white/60 leading-relaxed">
                  {t('tools.events.homologationDesc', { defaultValue: 'Teste comandos RCON em tempo real contra o servidor SCUM ativo. Comandos testados com sucesso são homologados e salvos para que você possa utilizá-los na criação dos eventos.' })}
                </p>
                <form onSubmit={handleTestCommand} className="space-y-3">
                  <div className="grid grid-cols-12 gap-3 items-end">
                    <div className={testBaseCmd.trim().startsWith('#SpawnItem') ? "col-span-12 sm:col-span-8 space-y-1" : "col-span-12 space-y-1"}>
                      <label className="block text-[10px] uppercase font-bold text-white/40 mb-1">{t('tools.events.commandBaseLabel', { defaultValue: 'Comando Base (Sem Coordenadas)' })}</label>
                      <input
                        id="test-base-cmd-input"
                        type="text"
                        required
                        placeholder={t('tools.events.commandBasePlaceholder', { defaultValue: 'Ex: #SpawnItem 2H_Katana1' })}
                        value={testBaseCmd}
                        onChange={(e) => setTestBaseCmd(e.target.value)}
                        className="w-full px-3 py-2 rounded-lg bg-[#0b0e13] border border-white/10 text-white text-xs focus:outline-none focus:ring-1 focus:ring-scum-orange font-mono"
                      />
                    </div>
                    {testBaseCmd.trim().startsWith('#SpawnItem') && (
                      <div className="col-span-12 sm:col-span-4 space-y-1">
                        <label className="block text-[10px] uppercase font-bold text-white/40 mb-1">{t('tools.events.quantityLabel', { defaultValue: 'Quantidade' })}</label>
                        <input
                          id="test-qty-input"
                          type="text"
                          required
                          placeholder={t('tools.events.quantityPlaceholder', { defaultValue: 'Ex: 1' })}
                          value={testQty}
                          onChange={(e) => setTestQty(e.target.value)}
                          className="w-full px-3 py-2 rounded-lg bg-[#0b0e13] border border-white/10 text-white text-xs focus:outline-none focus:ring-1 focus:ring-scum-orange font-mono"
                        />
                      </div>
                    )}
                  </div>
                  <div className="space-y-1">
                    <label className="block text-[10px] uppercase font-bold text-white/40 mb-1">{t('tools.events.referenceCoordLabel', { defaultValue: 'Coordenada de Referência (Opcional)' })}</label>
                    <input
                      id="test-coord-input"
                      type="text"
                      placeholder={t('tools.events.coordinatesPlaceholder', { defaultValue: 'Cole a telemetria SCUM (ex: {X=... Y=... Z=...})' })}
                      value={testCoord}
                      onChange={(e) => setTestCoord(e.target.value)}
                      className="w-full px-3 py-2 rounded-lg bg-[#0b0e13] border border-white/10 text-white text-xs focus:outline-none focus:ring-1 focus:ring-scum-orange font-mono"
                    />
                  </div>
                  <button
                    type="submit"
                    disabled={testingCommand}
                    className="w-full flex items-center justify-center gap-2 px-3 py-2 rounded-lg bg-scum-orange hover:bg-scum-orange-hover disabled:bg-scum-orange/50 text-white text-xs font-semibold transition-colors"
                  >
                    {testingCommand ? (
                      <>
                        <RefreshCw size={14} className="animate-spin" />
                        {t('tools.events.testingCommand', { defaultValue: 'Executando teste...' })}
                      </>
                    ) : (
                      <>
                        <Terminal size={14} />
                        {t('tools.events.testCommandBtn', { defaultValue: 'Testar Comando' })}
                      </>
                    )}
                  </button>
                </form>
              </div>

              {/* PAINEL DE RESPOSTA DO TERMINAL */}
              {testResponse ? (
                <div className="space-y-2 text-left">
                  <div className="flex items-center justify-between text-[10px] uppercase">
                    <span className="text-white/40">{t('tools.events.serverResponseLabel', { defaultValue: 'Resposta do Servidor' })}</span>
                    <span className={testSuccess ? 'text-green-400 font-bold' : 'text-red-400 font-bold'}>
                      {testSuccess ? t('tools.events.successTitle', { defaultValue: 'Sucesso' }) : t('tools.events.failTitle', { defaultValue: 'Falha' })}
                    </span>
                  </div>
                  <pre className={`p-3 rounded-lg border font-mono text-xs overflow-x-auto max-h-[140px] ${
                    testSuccess 
                      ? 'bg-green-950/20 border-green-500/20 text-green-300' 
                      : 'bg-red-950/20 border-red-500/20 text-red-300'
                  }`}>
                    {testResponse}
                  </pre>
                  {testSuccess && (
                    <button
                      type="button"
                      onClick={handleRegisterCommand}
                      className="w-full flex items-center justify-center gap-2 px-3 py-2 rounded-lg bg-green-600 hover:bg-green-700 text-white text-xs font-semibold transition-colors mt-2"
                    >
                      <CheckCircle2 size={14} />
                      {t('tools.events.registerCommandBtn', { defaultValue: 'Registrar no Catálogo de Homologados' })}
                    </button>
                  )}
                </div>
              ) : (
                <div className="flex items-center justify-center border border-dashed border-white/10 rounded-lg p-6 text-xs text-white/30 h-full min-h-[100px]">
                  {t('tools.events.waitingTest', { defaultValue: 'Aguardando a execução do teste...' })}
                </div>
              )}
            </div>
          )}
        </div>

        {/* AGENDADOR DE EVENTOS */}
        <div className="card p-6 space-y-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Calendar className="text-scum-orange" size={20} />
                <h2 className="text-lg font-bold text-white">{t('tools.events.customEvents', { defaultValue: 'Eventos Personalizados' })}</h2>
              </div>
              <div className="flex items-center gap-2">
                <button
                  type="button"
                  onClick={loadEvents}
                  disabled={loadingEvents}
                  className="p-2 rounded-lg border border-white/10 bg-white/5 text-white/80 hover:bg-white/10 hover:text-white"
                  title={t('tools.events.refreshList', { defaultValue: 'Atualizar lista' })}
                >
                  <RefreshCw size={16} className={loadingEvents ? 'animate-spin' : ''} />
                </button>
                <button
                  type="button"
                  onClick={() => setShowCreateForm(!showCreateForm)}
                  className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-scum-orange bg-scum-orange/15 text-scum-orange text-sm font-semibold hover:bg-scum-orange/25 transition-colors"
                >
                  <Plus size={16} />
                  {t('tools.events.newEvent', { defaultValue: 'Novo Evento' })}
                </button>
              </div>
            </div>

             {/* FORMULÁRIO DE CRIAÇÃO */}
             {showCreateForm && (
               <form onSubmit={handleCreateEvent} className="p-4 rounded-lg bg-black/30 border border-white/10 space-y-3">
                 <div className="grid grid-cols-1 md:grid-cols-12 gap-3">
                   
                   {/* Nome do Evento */}
                   <div className="col-span-12 md:col-span-6 space-y-1">
                     <label className="text-[10px] uppercase text-white/50 block">{t('tools.events.eventName', { defaultValue: 'Nome do Evento' })}</label>
                     <input
                       type="text"
                       required
                       placeholder={t('tools.events.eventNamePlaceholder', { defaultValue: 'Ex: Drop de Cargo Drop' })}
                       value={name}
                       onChange={(e) => setName(e.target.value)}
                       className="w-full px-3 py-1.5 rounded-lg bg-white/5 border border-white/10 text-white text-xs focus:outline-none focus:ring-1 focus:ring-scum-orange"
                     />
                   </div>

                   {/* Descrição */}
                   <div className="col-span-12 md:col-span-6 space-y-1">
                     <label className="text-[10px] uppercase text-white/50 block">{t('tools.events.description', { defaultValue: 'Descrição' })}</label>
                     <input
                       type="text"
                       placeholder={t('tools.events.descriptionPlaceholder', { defaultValue: 'Descrição opcional do evento...' })}
                       value={description}
                       onChange={(e) => setDescription(e.target.value)}
                       className="w-full px-3 py-1.5 rounded-lg bg-white/5 border border-white/10 text-white text-xs focus:outline-none focus:ring-1 focus:ring-scum-orange"
                     />
                   </div>

                    {/* Horários e Duração Compactos */}
                    <div className="col-span-12 flex flex-wrap gap-3">
                      <div className="w-24 space-y-1">
                        <label className="text-[10px] uppercase text-white/50 block">{t('tools.events.startTime', { defaultValue: 'Hora Inicial' })}</label>
                        <input
                          type="time"
                          required
                          value={startTime}
                          onChange={(e) => setStartTime(e.target.value)}
                          className="w-full px-2 py-1 bg-[#0b0e13] border border-white/10 text-white text-xs rounded focus:outline-none focus:ring-1 focus:ring-scum-orange font-mono text-center"
                        />
                      </div>

                      <div className="w-24 space-y-1">
                        <label className="text-[10px] uppercase text-white/50 block">{t('tools.events.endTime', { defaultValue: 'Hora Final' })}</label>
                        <input
                          type="time"
                          required
                          value={endTime}
                          onChange={(e) => setEndTime(e.target.value)}
                          className="w-full px-2 py-1 bg-[#0b0e13] border border-white/10 text-white text-xs rounded focus:outline-none focus:ring-1 focus:ring-scum-orange font-mono text-center"
                        />
                      </div>

                      <div className="w-24 space-y-1">
                        <label className="text-[10px] uppercase text-white/50 block">{t('tools.events.duration', { defaultValue: 'Duração' })}</label>
                        <div className="w-full h-[26px] bg-white/5 border border-white/5 text-white/90 text-xs font-semibold flex items-center justify-center rounded font-mono">
                          {formatDuration(calculateDurationMinutes(startTime, endTime))}
                        </div>
                      </div>
                    </div>

                    {/* Coordenadas de Teleporte (Spawn) */}
                    <div className="col-span-12 space-y-1">
                      <label className="text-[10px] uppercase text-white/50 block">{t('tools.events.coordinatesLabel', { defaultValue: 'Coordenadas de Teleporte (Spawn)' })}</label>
                      <div className="flex gap-2">
                        <input
                          type="text"
                          placeholder={t('tools.events.coordinatesPlaceholder', { defaultValue: 'Cole a coordenada do jogo (ex: {X=... Y=... Z=...})' })}
                          value={creationCoordInput}
                          onChange={(e) => setCreationCoordInput(e.target.value)}
                          className="flex-1 px-3 py-1.5 rounded-lg bg-white/5 border border-white/10 text-white text-xs focus:outline-none focus:ring-1 focus:ring-scum-orange"
                        />
                        <button
                          type="button"
                          onClick={() => {
                            const parsed = parseRawCoordinates(creationCoordInput);
                            if (parsed) {
                              setCreationCoords([...creationCoords, { raw: creationCoordInput, parsed }]);
                              setCreationCoordInput('');
                            } else {
                              alert({
                                icon: 'warning',
                                title: t('tools.events.invalidFormat', { defaultValue: 'Formato Inválido' }),
                                text: t('tools.events.invalidCoords', { defaultValue: 'Por favor, cole coordenadas válidas no formato do jogo (ex: contendo X, Y e Z).' })
                              });
                            }
                          }}
                          className="px-3 py-1.5 rounded-lg bg-scum-orange/20 border border-scum-orange/45 text-scum-orange hover:bg-scum-orange/30 text-xs font-semibold flex items-center gap-1 transition-all"
                        >
                          <Plus size={14} />
                          {t('tools.events.add', { defaultValue: 'Adicionar' })}
                        </button>
                      </div>

                      {/* Lista de coordenadas já adicionadas */}
                      {creationCoords.length > 0 && (
                        <div className="flex flex-wrap gap-2 pt-2">
                          {creationCoords.map((coord, idx) => (
                            <div
                              key={idx}
                              className="flex items-center gap-1.5 px-2 py-1 rounded bg-[#0b0e13] border border-white/10 text-[10px] text-white/80"
                            >
                              <MapPin size={10} className="text-scum-orange" />
                              <span className="font-mono">{t('tools.events.pointNum', { num: idx + 1, defaultValue: `Ponto ${idx + 1}:` })}</span>
                              <span className="font-mono text-white/60">
                                {coord.parsed.x.toFixed(1)}, {coord.parsed.y.toFixed(1)}, {coord.parsed.z.toFixed(1)}
                              </span>
                              <button
                                type="button"
                                onClick={() => setCreationCoords(creationCoords.filter((_, i) => i !== idx))}
                                className="text-white/40 hover:text-red-400 font-bold shrink-0 ml-1.5"
                                title={t('tools.events.removeCoordinate', { defaultValue: 'Remover coordenada' })}
                              >
                                &times;
                              </button>
                            </div>
                          ))}
                        </div>
                      )}
                    </div>

                   {/* Repetir Evento */}
                   <div className="hidden">
                     <label className="text-[10px] uppercase text-white/50 block">{t('tools.events.repeatEvent', { defaultValue: 'Repetir Evento?' })}</label>
                     <div className="flex items-center gap-3 h-[30px]">
                       <label className="relative inline-flex items-center cursor-pointer">
                         <input 
                           type="checkbox" 
                           checked={repeatEvent} 
                           onChange={(e) => {
                             setRepeatEvent(e.target.checked);
                             if (!e.target.checked) setSelectedWeekdays([]);
                           }}
                           className="sr-only peer" 
                         />
                         <div className="w-9 h-5 bg-white/10 peer-focus:outline-none rounded-full peer-checked:after:translate-x-full after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-4 after:w-4 after:transition-all peer-checked:bg-scum-orange"></div>
                         <span className="ml-2 text-xs text-white/70">{t('tools.events.activate', { defaultValue: 'Ativar' })}</span>
                       </label>

                       {repeatEvent && (
                         <div className="flex items-center gap-1">
                           {['D', 'S', 'T', 'Q', 'Q', 'S', 'S'].map((day, idx) => {
                             const isSelected = selectedWeekdays.includes(idx);
                             return (
                               <button
                                 key={idx}
                                 type="button"
                                 onClick={() => {
                                   if (isSelected) {
                                     setSelectedWeekdays(selectedWeekdays.filter(d => d !== idx));
                                   } else {
                                     setSelectedWeekdays([...selectedWeekdays, idx]);
                                   }
                                 }}
                                 title={t(`tools.events.dayLong_${idx}`)}
                                 className={`w-6 h-6 rounded-full text-[10px] font-bold transition-all flex items-center justify-center border ${
                                   isSelected 
                                     ? 'bg-scum-orange border-scum-orange text-white' 
                                     : 'bg-white/5 border-white/10 text-white/60 hover:bg-white/10 hover:text-white'
                                 }`}
                                >
                                  {t(`tools.events.dayLetter_${idx}`)}
                               </button>
                             );
                           })}
                         </div>
                       )}
                     </div>
                   </div>

                 </div>

                 <div className="flex justify-end gap-2 pt-1.5">
                   <button
                     type="button"
                     onClick={() => setShowCreateForm(false)}
                     className="px-3 py-1.5 rounded-lg border border-white/10 text-white/80 hover:bg-white/5 text-xs"
                   >
                     {t('tools.events.cancel', { defaultValue: 'Cancelar' })}
                   </button>
                   <button
                     type="submit"
                     className="px-3 py-1.5 rounded-lg bg-scum-orange hover:bg-scum-orange-hover text-white text-xs font-semibold"
                   >
                     {t('tools.events.saveEvent', { defaultValue: 'Salvar Evento' })}
                   </button>
                 </div>
               </form>
             )}

            {/* LISTAGEM DE EVENTOS */}
            {events.length === 0 ? (
              <div className="text-center py-6 text-white/40 text-sm">
                {t('tools.events.noEvents', { defaultValue: 'Nenhum evento cadastrado. Clique em "Novo Evento" para começar.' })}
              </div>
            ) : (
              <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 xl:grid-cols-4 gap-3 mb-6">
                {events.map((ev) => {
                  const isRepeating = ev.schedule_value ? ev.schedule_value.includes('|') : false;
                  const timePart = ev.schedule_value ? (ev.schedule_value.includes('|') ? ev.schedule_value.split('|')[0] : ev.schedule_value) : '14:30';
                  const currentDays = ev.schedule_value && ev.schedule_value.includes('|') 
                    ? ev.schedule_value.split('|')[1].split(',').filter(x => x !== '').map(Number) 
                    : [];

                  if (editingEventId === ev.event_id) {
                    return (
                      <div
                        key={ev.event_id}
                        className="p-3 rounded-lg border border-scum-orange bg-scum-orange/5 text-left flex flex-col justify-between"
                        onClick={(e) => e.stopPropagation()}
                      >
                        <div className="space-y-2">
                          <div>
                            <label className="text-[9px] uppercase text-white/40 block mb-0.5">{t('tools.events.eventName', { defaultValue: 'Nome do Evento' })}</label>
                            <input
                              type="text"
                              required
                              value={editName}
                              onChange={(e) => setEditName(e.target.value)}
                              className="w-full px-2 py-1 rounded bg-[#0b0e13] border border-white/10 text-white text-xs focus:outline-none focus:ring-1 focus:ring-scum-orange"
                            />
                          </div>

                          <div>
                            <label className="text-[9px] uppercase text-white/40 block mb-0.5">{t('tools.events.description', { defaultValue: 'Descrição' })}</label>
                            <input
                              type="text"
                              value={editDescription}
                              onChange={(e) => setEditDescription(e.target.value)}
                              className="w-full px-2 py-1 rounded bg-[#0b0e13] border border-white/10 text-white text-xs focus:outline-none focus:ring-1 focus:ring-scum-orange"
                            />
                          </div>

                          <div className="flex gap-2">
                            <div className="flex-1">
                              <label className="text-[9px] uppercase text-white/40 block mb-0.5">{t('tools.events.startTime', { defaultValue: 'Hora Inicial' })}</label>
                              <input
                                type="time"
                                required
                                value={editStartTime}
                                onChange={(e) => setEditStartTime(e.target.value)}
                                className="w-full px-2 py-1 bg-[#0b0e13] border border-white/10 text-white text-xs rounded focus:outline-none focus:ring-1 focus:ring-scum-orange font-mono text-center"
                              />
                            </div>
                            <div className="flex-1">
                              <label className="text-[9px] uppercase text-white/40 block mb-0.5">{t('tools.events.endTime', { defaultValue: 'Hora Final' })}</label>
                              <input
                                type="time"
                                required
                                value={editEndTime}
                                onChange={(e) => setEditEndTime(e.target.value)}
                                className="w-full px-2 py-1 bg-[#0b0e13] border border-white/10 text-white text-xs rounded focus:outline-none focus:ring-1 focus:ring-scum-orange font-mono text-center"
                              />
                            </div>
                          </div>

                          <div className="pt-2 border-t border-white/5 space-y-1">
                            <div className="flex items-center justify-between">
                              <span className="text-[9px] text-white/40 uppercase font-semibold">{t('tools.events.chooseDays', { defaultValue: 'escolher dias' })}</span>
                              <label className="relative inline-flex items-center cursor-pointer">
                                <input 
                                  type="checkbox" 
                                  checked={editIsRepeating} 
                                  onChange={(e) => {
                                    setEditIsRepeating(e.target.checked);
                                    if (!e.target.checked) setEditWeekdays([]);
                                  }}
                                  className="sr-only peer" 
                                />
                                <div className="w-9 h-5 bg-white/10 peer-focus:outline-none rounded-full peer-checked:after:translate-x-full after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-4 after:w-4 after:transition-all peer-checked:bg-scum-orange"></div>
                              </label>
                            </div>

                            {editIsRepeating && (
                              <div className="flex items-center justify-between gap-0.5 mt-1">
                                {['D', 'S', 'T', 'Q', 'Q', 'S', 'S'].map((day, idx) => {
                                  const isSelected = editWeekdays.includes(idx);
                                  return (
                                    <button
                                      key={idx}
                                      type="button"
                                      onClick={() => {
                                        if (isSelected) {
                                          setEditWeekdays(editWeekdays.filter(d => d !== idx));
                                        } else {
                                          setEditWeekdays([...editWeekdays, idx].sort((a, b) => a - b));
                                        }
                                      }}
                                      title={t(`tools.events.dayLong_${idx}`)}
                                      className={`w-5 h-5 rounded-full text-[9px] font-bold transition-all flex items-center justify-center border ${
                                        isSelected 
                                          ? 'bg-scum-orange border-scum-orange text-white' 
                                          : 'bg-white/5 border-white/10 text-white/50 hover:bg-white/10'
                                      }`}
                                    >
                                      {t(`tools.events.dayLetter_${idx}`)}
                                    </button>
                                  );
                                })}
                              </div>
                            )}
                          </div>
                        </div>

                        <div className="flex items-center justify-between gap-2 mt-4 pt-2 border-t border-white/5">
                          <button
                            type="button"
                            onClick={() => setEditingEventId(null)}
                            className="px-2 py-1 rounded border border-white/10 text-white/70 hover:bg-white/5 text-[10px]"
                          >
                            {t('tools.events.cancel', { defaultValue: 'Cancelar' })}
                          </button>
                          <button
                            type="button"
                            onClick={() => handleSaveEdit(ev)}
                            className="px-2.5 py-1 rounded bg-green-600 hover:bg-green-700 text-white text-[10px] font-semibold"
                          >
                            {t('tools.events.saveChanges', { defaultValue: 'Gravar' })}
                          </button>
                        </div>
                      </div>
                    );
                  }

                  return (
                    <div
                      key={ev.event_id}
                      onClick={() => setSelectedEventId(selectedEventId === ev.event_id ? null : ev.event_id)}
                      className={`p-3 rounded-lg border text-left cursor-pointer transition-all flex flex-col justify-between ${
                        selectedEventId === ev.event_id 
                          ? 'border-scum-orange bg-scum-orange/5 shadow-lg shadow-scum-orange/5' 
                          : 'border-white/10 bg-white/5 hover:bg-white/8 hover:border-white/15'
                      }`}
                    >
                      <div>
                        <div className="flex items-start justify-between gap-1.5">
                          <h3 className="font-bold text-white text-xs truncate flex-1" title={ev.name}>{ev.name}</h3>
                          <span className={`inline-flex items-center gap-1 text-[9px] px-1.5 py-0.5 rounded-full font-bold uppercase tracking-wider shrink-0 ${
                            ev.status === 'active' 
                              ? 'bg-green-500/20 text-green-400 border border-green-500/30 animate-pulse' 
                              : 'bg-white/10 text-white/40'
                          }`}>
                            {ev.status === 'active' 
                              ? t('tools.events.activeStatus', { defaultValue: 'Ativo' }) 
                              : t('tools.events.inactiveStatus', { defaultValue: 'Inativo' })}
                          </span>
                        </div>
                        <p className="text-[11px] text-white/50 line-clamp-1 mt-1">{ev.description || t('tools.events.noDescription', { defaultValue: 'Sem descrição' })}</p>
                      </div>

                      <div>
                        <div className="flex flex-wrap items-center gap-x-2 gap-y-1 mt-3 text-[10px] text-white/60">
                          <span className="flex items-center gap-0.5 shrink-0">
                            <Clock size={11} className="text-scum-orange" />
                            {formatDuration(ev.duration_minutes)}
                          </span>
                          <span className="flex items-center gap-0.5 border-l border-white/10 pl-2 shrink-0">
                            <Calendar size={11} className="text-scum-orange" />
                            {formatScheduleValue(ev.schedule_value, ev.duration_minutes, t)}
                          </span>
                        </div>

                        <div className="flex items-center justify-between mt-3 pt-2 border-t border-white/5">
                          <div className="flex items-center gap-1.5">
                            <button
                              type="button"
                              onClick={(e) => {
                                e.stopPropagation();
                                handleDeleteEvent(ev.event_id);
                              }}
                              className="p-1 rounded hover:bg-red-500/10 text-white/40 hover:text-red-400 transition-colors"
                              title={t('tools.events.deleteEventTooltip', { defaultValue: 'Deletar evento' })}
                            >
                              <Trash2 size={13} />
                            </button>
                            <button
                              type="button"
                              onClick={(e) => {
                                e.stopPropagation();
                                startEditing(ev);
                              }}
                              className="p-1 rounded hover:bg-white/10 text-white/40 hover:text-white transition-colors"
                              title={t('tools.events.editEventTooltip', { defaultValue: 'Editar evento' })}
                            >
                              <Settings size={13} />
                            </button>
                          </div>
                          {ev.status === 'active' ? (
                            <button
                              type="button"
                              onClick={(e) => {
                                e.stopPropagation();
                                handleStopEvent(ev.event_id);
                              }}
                              className="flex items-center gap-1 px-2 py-0.5 rounded bg-red-500/25 text-red-300 border border-red-500/30 text-[10px] font-semibold hover:bg-red-500/35 transition-colors"
                            >
                              <Square size={10} />
                              {t('tools.events.stop', { defaultValue: 'Finalizar' })}
                            </button>
                          ) : (
                            <button
                              type="button"
                              disabled={isRepeating && currentDays.length === 0}
                              onClick={(e) => {
                                e.stopPropagation();
                                handleStartEvent(ev.event_id);
                              }}
                              className={`flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-semibold transition-colors ${
                                isRepeating && currentDays.length === 0
                                  ? 'bg-white/5 text-white/30 border border-white/10 cursor-not-allowed'
                                  : 'bg-green-500/25 text-green-300 border border-green-500/30 hover:bg-green-500/35'
                              }`}
                              title={isRepeating && currentDays.length === 0 ? t('tools.events.startDaysWarning', { defaultValue: 'Selecione pelo menos um dia da semana para iniciar' }) : t('tools.events.start', { defaultValue: 'Iniciar' })}
                            >
                              <Play size={10} />
                              {t('tools.events.start', { defaultValue: 'Iniciar' })}
                            </button>
                          )}
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>

          {/* DETALHES DO EVENTO SELECIONADO */}
          {selectedEventId && (
            <div className="mt-6 space-y-6">
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                {/* CONFIGURAÇÃO DE COMANDOS INICIAIS */}
                <div className="card p-6 space-y-4">
                  <div className="flex items-center gap-2">
                    <Terminal className="text-scum-orange" size={18} />
                    <h3 className="font-bold text-white text-base">{t('tools.events.initialCommands', { defaultValue: 'Comandos Iniciais' })}</h3>
                  </div>

                  <form onSubmit={handleAddStartupCommand} className="space-y-3">
                    <div className="relative flex gap-2">
                      <div ref={dropdownRef} className="relative flex-1">
                        <input
                          id="new-event-cmd-input"
                          type="text"
                          placeholder={t('tools.events.searchTestedPlaceholder', { defaultValue: 'Pesquisar comando homologado...' })}
                          value={newCommandString || searchTerm}
                          onChange={(e) => {
                            if (newCommandString) {
                              setNewCommandString('');
                            }
                            setSearchTerm(e.target.value);
                            setIsOpen(true);
                          }}
                          onFocus={() => setIsOpen(true)}
                          className="w-full px-3 py-1.5 rounded-lg bg-white/5 border border-white/10 text-white text-sm focus:outline-none focus:ring-1 focus:ring-scum-orange font-mono text-xs"
                        />
                        {isOpen && (
                          <div className="absolute left-0 right-0 bottom-full mb-1 max-h-48 overflow-y-auto bg-[#0b0e13] border border-white/10 rounded-lg shadow-xl z-50 divide-y divide-white/5">
                            {filteredCommands.length === 0 ? (
                              <div className="p-2 text-xs text-white/40 text-center">{t('tools.events.noTestedCommands', { defaultValue: 'Nenhum comando homologado' })}</div>
                            ) : (
                              filteredCommands.map((tc) => (
                                <button
                                  key={tc.command_id}
                                  type="button"
                                  onClick={() => handleSelectTestedCommand(tc)}
                                  className="w-full text-left px-3 py-2 text-xs text-white/80 hover:bg-scum-orange hover:text-white font-mono transition-colors truncate"
                                >
                                  {tc.command_string}
                                </button>
                              ))
                            )}
                          </div>
                        )}
                      </div>
                      <button
                        type="submit"
                        disabled={!(newCommandString.trim() || searchTerm.trim())}
                        className="p-1.5 rounded-lg bg-scum-orange hover:bg-scum-orange-hover text-white transition-colors shrink-0 disabled:opacity-50"
                        title={t('tools.events.addCommandTooltip', { defaultValue: 'Adicionar comando selecionado ao evento' })}
                      >
                        <Plus size={18} />
                      </button>
                    </div>
                  </form>

                  {loadingDetails ? (
                    <div className="text-xs text-white/40 text-center py-4">{t('tools.events.loadingCommands', { defaultValue: 'Carregando comandos...' })}</div>
                  ) : !selectedEventDetails || editableCommands.length === 0 ? (
                    <div className="text-xs text-white/40 text-center py-4 font-mono">{t('tools.events.noCommandsAdded', { defaultValue: 'Nenhum comando adicionado.' })}</div>
                  ) : (
                    <div className="space-y-2 max-h-[300px] overflow-y-auto pr-1">
                      {editableCommands.map((cmd) => (
                        <div key={cmd.startup_id} className="flex flex-col gap-2 p-2.5 rounded bg-[#0b0e13]/40 border border-white/5 text-xs font-mono">
                          <div className="flex items-center justify-between gap-3">
                            <code className="text-white/90 truncate flex-1 font-mono">{cmd.command_string}</code>
                            <button
                              type="button"
                              onClick={() => handleRemoveStartupCommand(cmd.startup_id)}
                              className="text-white/40 hover:text-red-400 transition-colors p-1 shrink-0"
                              title={t('tools.events.removeCommandTooltip', { defaultValue: 'Remover comando' })}
                            >
                              <Trash2 size={13} />
                            </button>
                          </div>

                          <div className="flex items-center justify-start gap-6 pt-1.5 border-t border-white/5 text-[10px] text-white/50 font-sans">
                            <label className="flex items-center gap-1 cursor-pointer select-none">
                              <input
                                type="checkbox"
                                checked={cmd.recurrence_interval_minutes !== null}
                                onChange={(e) => handleToggleCommandRecurrence(cmd, e.target.checked)}
                                className="rounded border-white/10 bg-white/5 text-scum-orange focus:ring-scum-orange focus:ring-offset-0 scale-75"
                              />
                              <span>{t('tools.events.repeatCommand', { defaultValue: 'Repetir comando?' })}</span>
                            </label>
                            
                            {cmd.recurrence_interval_minutes !== null && (
                              <div className="flex items-center gap-1">
                                <span>{t('tools.events.every', { defaultValue: 'a cada' })}</span>
                                <input
                                  type="number"
                                  min={1}
                                  required
                                  value={cmd.recurrence_interval_minutes || ''}
                                  onChange={(e) => {
                                    const val = e.target.value === '' ? null : Number(e.target.value);
                                    handleUpdateCommandRecurrenceInterval(cmd, val);
                                  }}
                                  className="w-10 px-1 py-0.5 rounded bg-white/10 border border-white/10 text-white text-center font-bold text-[10px]"
                                />
                                <span>{t('tools.events.minutesUnit', { defaultValue: 'min' })}</span>
                              </div>
                            )}
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </div>

                {/* CONFIGURAÇÃO DE COORDENADAS */}
                <div className="card p-6 space-y-4">
                  <div className="flex items-center gap-2">
                    <MapPin className="text-scum-orange" size={18} />
                    <h3 className="font-bold text-white text-base">{t('tools.events.coordinatesLabel', { defaultValue: 'Coordenadas de Teleporte (Spawn)' })}</h3>
                  </div>

                  <form onSubmit={handleAddCoordinate} className="space-y-3">
                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                      <div className="space-y-1">
                        <label className="text-[10px] uppercase text-white/50 block">{t('tools.events.pointNameLabel', { defaultValue: 'Nome do Ponto' })}</label>
                        <input
                          type="text"
                          required
                          placeholder={t('tools.events.pointNamePlaceholder', { defaultValue: 'Ex: Ponto de Spawn 1' })}
                          value={newCoordName}
                          onChange={(e) => setNewCoordName(e.target.value)}
                          className="w-full px-3 py-1.5 rounded-lg bg-white/5 border border-white/10 text-white text-xs focus:outline-none focus:ring-1 focus:ring-scum-orange"
                        />
                      </div>
                      <div className="space-y-1">
                        <label className="text-[10px] uppercase text-white/50 block">{t('tools.events.coordinatesTelemetryLabel', { defaultValue: 'Coordenada Telemetria' })}</label>
                        <div className="flex gap-2">
                          <input
                            type="text"
                            required
                            placeholder={t('tools.events.telemetryPlaceholder', { defaultValue: 'Cole aqui a telemetria do jogo...' })}
                            value={newRawCoord}
                            onChange={(e) => setNewRawCoord(e.target.value)}
                            className="flex-1 px-3 py-1.5 rounded-lg bg-white/5 border border-white/10 text-white text-xs focus:outline-none focus:ring-1 focus:ring-scum-orange font-mono"
                          />
                          <button
                            type="submit"
                            className="px-3 py-1.5 rounded-lg bg-scum-orange/20 border border-scum-orange/45 text-scum-orange hover:bg-scum-orange/30 text-xs font-semibold flex items-center gap-1 transition-all shrink-0"
                          >
                            <Plus size={14} />
                            {t('tools.events.add', { defaultValue: 'Adicionar' })}
                          </button>
                        </div>
                      </div>
                    </div>
                  </form>

                  {loadingDetails ? (
                    <div className="text-xs text-white/40 text-center py-4">{t('tools.events.loadingCoords', { defaultValue: 'Carregando coordenadas...' })}</div>
                  ) : !selectedEventDetails || editableCoordinates.length === 0 ? (
                    <div className="text-xs text-white/40 text-center py-4 font-mono">{t('tools.events.noCoordsAdded', { defaultValue: 'Nenhuma coordenada adicionada.' })}</div>
                  ) : (
                    <div className="space-y-2 max-h-[300px] overflow-y-auto pr-1">
                      {editableCoordinates.map((coord) => (
                        <div key={coord.coord_id} className="flex items-center justify-between gap-3 p-2.5 rounded bg-[#0b0e13]/40 border border-white/5 text-xs">
                          <div className="flex flex-col gap-0.5 truncate">
                            <span className="font-bold text-white/90 truncate">{coord.name}</span>
                            <span className="font-mono text-[10px] text-white/40 truncate">
                              X: {coord.x.toFixed(3)} | Y: {coord.y.toFixed(3)} | Z: {coord.z.toFixed(3)}
                            </span>
                          </div>
                          <button
                            type="button"
                            onClick={() => handleRemoveCoordinate(coord.coord_id)}
                            className="text-white/40 hover:text-red-400 transition-colors p-1 shrink-0"
                            title={t('tools.events.removeCoordinateTooltip', { defaultValue: 'Remover coordenada' })}
                          >
                            <Trash2 size={13} />
                          </button>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              </div>

              {/* Botão de Salvar Alterações (se houver alterações pendentes) */}
              {selectedEventDetails && (
                <div className="card p-4 flex items-center justify-between border border-white/5 bg-white/[0.02]">
                  <div className="text-[11px] text-white/40 font-medium">
                    {hasUnsavedChanges ? (
                      <span className="text-amber-500 font-semibold flex items-center gap-1">
                        {t('tools.events.unsavedChanges', { defaultValue: '⚠️ Você possui alterações não salvas' })}
                      </span>
                    ) : (
                      <span className="text-green-500 font-semibold flex items-center gap-1">
                        {t('tools.events.allSavedStatus', { defaultValue: '✓ Todos os comandos e coordenadas estão salvos' })}
                      </span>
                    )}
                  </div>
                  <button
                    type="button"
                    disabled={!hasUnsavedChanges || savingCommands}
                    onClick={handleSaveStartupCommands}
                    className="flex items-center gap-1.5 px-4 py-2 rounded-lg bg-scum-orange hover:bg-scum-orange-hover disabled:bg-white/5 disabled:text-white/20 text-white text-xs font-semibold transition-colors shadow-lg"
                  >
                    {savingCommands 
                      ? t('tools.events.saving', { defaultValue: 'Salvando...' }) 
                      : t('tools.events.saveChangesBtn', { defaultValue: 'Salvar Alterações' })}
                  </button>
                </div>
              )}
            </div>
          )}
        </div>
      </ModuleToolPage>
  );
}
