import { motion } from 'framer-motion';
import { useEffect, useMemo, useRef, useState } from 'react';
import { Users, Clock, Server as ServerIcon, Thermometer, Droplets, Moon, RotateCw, BarChart3, Target } from 'lucide-react';
import { getServerStatus_legacy, getServerStatus, getServerTime, getPlayersOnlineStats, getSchedulerStatus, getPlayersLogs, type ServerStatusResponse, type ServerTimeResponse, type PlayersOnlineStatsResponse, type SchedulerStatus, type PlayersLogsData } from '@/services/server';
import { getPlayersChartData, getPlayersHourlyAverage, type PlayersChartDataResponse, type PlayersHourlyAverageResponse } from '@/services/reports';
import { useTranslation } from 'react-i18next';

function useCanvasGrid() {
  const ref = useRef<HTMLCanvasElement | null>(null);
  useEffect(() => {
    const canvas = ref.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    const draw = () => {
      const dpr = window.devicePixelRatio || 1;
      const rect = canvas.getBoundingClientRect();
      canvas.width = Math.max(1, Math.floor(rect.width * dpr));
      canvas.height = Math.max(1, Math.floor(rect.height * dpr));
      ctx.setTransform(1, 0, 0, 1, 0, 0);
      ctx.scale(dpr, dpr);
      ctx.clearRect(0, 0, rect.width, rect.height);
      ctx.strokeStyle = 'rgba(255,255,255,0.05)';
      for (let x = 0; x < rect.width; x += 24) {
        ctx.beginPath();
        ctx.moveTo(x, 0);
        ctx.lineTo(x, rect.height);
        ctx.stroke();
      }
      for (let y = 0; y < rect.height; y += 24) {
        ctx.beginPath();
        ctx.moveTo(0, y);
        ctx.lineTo(rect.width, y);
        ctx.stroke();
      }
    };

    draw();
    window.addEventListener('resize', draw);
    window.addEventListener('orientationchange', draw);
    return () => {
      window.removeEventListener('resize', draw);
      window.removeEventListener('orientationchange', draw);
    };
  }, []);
  return ref;
}

export default function Home() {
  const { t } = useTranslation();
  const gridRef = useCanvasGrid();
  const playerStatsGridRef = useCanvasGrid();
  const [serverStatus, setServerStatus] = useState<ServerStatusResponse | null>(null);
  const [serverTime, setServerTime] = useState<ServerTimeResponse | null>(null);
  const [playersStats, setPlayersStats] = useState<PlayersOnlineStatsResponse | null>(null);
  const [schedulerStatus, setSchedulerStatus] = useState<SchedulerStatus | null>(null);
  const [playersLogs, setPlayersLogs] = useState<PlayersLogsData | null>(null);
  const [peakHours, setPeakHours] = useState<Array<{ hour: string; count: number; avg: number }>>([]);
  const [analysisData, setAnalysisData] = useState<PlayersChartDataResponse | null>(null);
  const [hourlyAverageData, setHourlyAverageData] = useState<PlayersHourlyAverageResponse | null>(null);

  const variants = useMemo(() => ({
    enter: { opacity: 0, y: 8 },
    center: { opacity: 1, y: 0 },
  }), []);

  const status = getServerStatus_legacy.useQuery();

  // Buscar status do servidor
  useEffect(() => {
    const fetchStatus = async () => {
      try {
        const status = await getServerStatus();
        setServerStatus(status);
      } catch (err) {
        console.error('Erro ao buscar status do servidor:', err);
      }
    };

    fetchStatus();
    // Atualizar status a cada 30 segundos
    const interval = setInterval(fetchStatus, 30000);
    return () => clearInterval(interval);
  }, []);

  // Buscar tempo do servidor
  useEffect(() => {
    const fetchTime = async () => {
      try {
        const time = await getServerTime();
        setServerTime(time);
      } catch (err) {
        console.error('Erro ao buscar tempo do servidor:', err);
      }
    };

    fetchTime();
    // Atualizar tempo a cada 30 segundos
    const interval = setInterval(fetchTime, 30000);
    return () => clearInterval(interval);
  }, []);

  // Buscar estatísticas de jogadores online
  useEffect(() => {
    const fetchPlayersStats = async () => {
      try {
        const stats = await getPlayersOnlineStats();
        setPlayersStats(stats);
        
        // Coletar dados para histórico de horários
        if (stats.success && stats.data) {
          const now = new Date();
          const hour = now.getHours();
          const hourKey = `${hour.toString().padStart(2, '0')}:00`;
          
          // Recuperar histórico do localStorage
          const storageKey = 'playersOnlineHistory';
          const history = JSON.parse(localStorage.getItem(storageKey) || '{}');
          
          // Inicializar ou atualizar contagem para esta hora
          if (!history[hourKey]) {
            history[hourKey] = { counts: [], total: 0, samples: 0 };
          }
          
          history[hourKey].counts.push(stats.data.online_count);
          history[hourKey].total += stats.data.online_count;
          history[hourKey].samples += 1;
          
          // Manter apenas últimos 7 dias (limitar a 168 horas)
          const hours = Object.keys(history);
          if (hours.length > 168) {
            const sortedHours = hours.sort();
            const toRemove = sortedHours.slice(0, sortedHours.length - 168);
            toRemove.forEach(h => delete history[h]);
          }
          
          // Salvar no localStorage
          localStorage.setItem(storageKey, JSON.stringify(history));
          
          // Processar e calcular médias
          const processed: Array<{ hour: string; count: number; avg: number }> = [];
          Object.keys(history).forEach(h => {
            const data = history[h];
            const avg = data.samples > 0 ? Math.round(data.total / data.samples) : 0;
            const maxCount = Math.max(...data.counts, 0);
            processed.push({
              hour: h,
              count: maxCount,
              avg: avg
            });
          });
          
          // Ordenar por média (decrescente) e pegar top 6
          processed.sort((a, b) => b.avg - a.avg);
          setPeakHours(processed.slice(0, 6));
        }
      } catch (err) {
        console.error('Erro ao buscar estatísticas de jogadores:', err);
      }
    };

    fetchPlayersStats();
    // Atualizar estatísticas a cada 10 segundos
    const interval = setInterval(fetchPlayersStats, 10000);
    return () => clearInterval(interval);
  }, []);

  // Buscar status do agendador
  useEffect(() => {
    const fetchSchedulerStatus = async () => {
      try {
        const response = await getSchedulerStatus();
        if (response.success && response.data) {
          setSchedulerStatus(response.data);
        }
      } catch (err) {
        console.error('Erro ao buscar status do agendador:', err);
      }
    };

    fetchSchedulerStatus();
    // Atualizar status a cada 30 segundos
    const interval = setInterval(fetchSchedulerStatus, 30000);
    return () => clearInterval(interval);
  }, []);

  // Buscar logs de players
  useEffect(() => {
    const fetchPlayersLogs = async () => {
      try {
        const response = await getPlayersLogs(100, 0);
        if (response.success && response.data) {
          setPlayersLogs(response.data);
        }
      } catch (err) {
        console.error('Erro ao buscar logs de players:', err);
      }
    };

    fetchPlayersLogs();
    // Atualizar logs a cada 30 segundos
    const interval = setInterval(fetchPlayersLogs, 30000);
    return () => clearInterval(interval);
  }, []);

  // Buscar dados da análise (7 dias) para Estatísticas de Jogadores
  useEffect(() => {
    const fetchAnalysisData = async () => {
      try {
        const response = await getPlayersChartData(7, 'hour');
        if (response.success && response.data) {
          setAnalysisData(response);
        }
      } catch (err) {
        console.error('Erro ao buscar dados da análise:', err);
      }
    };

    fetchAnalysisData();
    // Atualizar dados da análise a cada 60 segundos
    const interval = setInterval(fetchAnalysisData, 60000);
    return () => clearInterval(interval);
  }, []);

  // Buscar dados de média por hora (7 dias) para Horários de Pico
  useEffect(() => {
    const fetchHourlyAverage = async () => {
      try {
        const response = await getPlayersHourlyAverage(7);
        if (response.success && response.data) {
          setHourlyAverageData(response);
        }
      } catch (err) {
        console.error('Erro ao buscar média por hora:', err);
      }
    };

    fetchHourlyAverage();
    // Atualizar dados a cada 60 segundos
    const interval = setInterval(fetchHourlyAverage, 60000);
    return () => clearInterval(interval);
  }, []);

  // Atualizar contagem regressiva a cada segundo
  useEffect(() => {
    if (schedulerStatus?.next_restart) {
      const interval = setInterval(() => {
        // Force re-render para atualizar contagem regressiva
        setSchedulerStatus(prev => prev ? { ...prev } : null);
      }, 1000);
      return () => clearInterval(interval);
    }
  }, [schedulerStatus?.next_restart]);

  // Extrair e formatar o estado do serviço para exibição
  const getServerStatusDisplay = () => {
    if (!serverStatus?.data) return { text: '—', color: 'text-white' };
    
    const estado = serverStatus.data.service_info?.ESTADO || (serverStatus.data.is_running ? '4 RUNNING' : '1 STOPPED');
    
    // Verificar se contém "4 RUNNING" ou apenas "RUNNING"
    if (estado.includes('4') && estado.includes('RUNNING')) {
      return { text: t('home.serverStatus.online', { defaultValue: 'Online' }), color: 'text-green-400' };
    }
    
    // Verificar se contém "3 STOP_PENDING" ou apenas "STOP_PENDING"
    if (estado.includes('3') && estado.includes('STOP_PENDING')) {
      return { text: t('home.serverStatus.stopping', { defaultValue: 'Stopping' }), color: 'text-red-400' };
    }
    
    // Verificar se contém "1 STOPPED" ou apenas "STOPPED"
    if (estado.includes('1') && estado.includes('STOPPED')) {
      return { text: t('home.serverStatus.offline', { defaultValue: 'Offline' }), color: 'text-red-400' };
    }
    
    // Para outros estados, mostrar o estado original
    return { text: estado, color: 'text-white' };
  };
  
  const statusDisplay = getServerStatusDisplay();

  // Funções helper para formatar dados
  const formatTemperature = (temp: number | undefined): string => {
    if (temp === undefined || temp === null) return '—';
    return `${temp.toFixed(1)}°C`;
  };

  const getMoonPhase = (rotation: number | undefined): { phase: string; icon: string } => {
    if (rotation === undefined || rotation === null) return { phase: '—', icon: '—' };
    
    // moon_rotation varia de 0 a ~7 (ciclo completo)
    // Dividir em 8 fases (0-7)
    const normalizedRotation = rotation % 7;
    const phaseIndex = Math.floor((normalizedRotation / 7) * 8);
    const clampedIndex = Math.min(phaseIndex, 7);
    
    const phases = [
      { phase: t('home.moon.new'), icon: '🌑' },
      { phase: t('home.moon.waxingCrescent'), icon: '🌒' },
      { phase: t('home.moon.firstQuarter'), icon: '🌓' },
      { phase: t('home.moon.waxingGibbous'), icon: '🌔' },
      { phase: t('home.moon.full'), icon: '🌕' },
      { phase: t('home.moon.waningGibbous'), icon: '🌖' },
      { phase: t('home.moon.lastQuarter'), icon: '🌗' },
      { phase: t('home.moon.waningCrescent'), icon: '🌘' },
    ];
    
    return phases[clampedIndex] || phases[0];
  };

  const getFogStatus = (density: number | undefined, cumulonimbus: boolean | undefined): { text: string; color: string } => {
    if (density === undefined || density === null) return { text: '—', color: 'text-white' };
    
    if (density < 0.0001) {
      return { text: t('home.fog.none'), color: 'text-green-400' };
    } else if (density < 0.001) {
      return { text: t('home.fog.light'), color: 'text-yellow-400' };
    } else if (density < 0.01) {
      return { text: t('home.fog.moderate'), color: 'text-orange-400' };
    } else {
      return { text: t('home.fog.heavy'), color: 'text-red-400' };
    }
  };

  // Função para calcular contagem regressiva
  const getCountdown = (nextRestart: string | null): string => {
    if (!nextRestart) return t('server.scheduler.status.noRestartScheduled') || 'N/A';
    
    const now = new Date();
    const restart = new Date(nextRestart);
    const diff = restart.getTime() - now.getTime();
    
    if (diff < 0) return t('server.scheduler.countdown.passed') || 'Já passou';
    
    const hours = Math.floor(diff / (1000 * 60 * 60));
    const minutes = Math.floor((diff % (1000 * 60 * 60)) / (1000 * 60));
    const seconds = Math.floor((diff % (1000 * 60)) / 1000);
    
    if (hours > 0) {
      return `${hours}${t('server.scheduler.countdown.hours')} ${minutes}${t('server.scheduler.countdown.minutes')}`;
    } else if (minutes > 0) {
      return `${minutes}${t('server.scheduler.countdown.minutes')} ${seconds}${t('server.scheduler.countdown.seconds')}`;
    } else {
      return `${seconds}${t('server.scheduler.countdown.seconds')}`;
    }
  };

  const moonPhaseInfo = getMoonPhase(serverTime?.data?.moon_rotation);
  const fogStatus = getFogStatus(serverTime?.data?.fog_density, serverTime?.data?.cumulonimbus_causes_fog);

  return (
    <div className="grid gap-4">
      <div className="relative card p-4 overflow-hidden">
        <canvas ref={gridRef} className="absolute inset-0 w-full h-full" />
        <div className="relative z-10 grid grid-cols-2 gap-3 sm:gap-4 md:gap-5">
          {/* Cards existentes */}
          <motion.div variants={variants} initial="enter" animate="center" className="p-3 sm:p-4 md:p-5 rounded-xl bg-black/30 border border-white/5 min-h-[84px]">
            <div className="flex items-center gap-2 text-white/70 text-sm sm:text-base"><Clock size={18} /> {t('home.time')}</div>
            <div className="text-2xl sm:text-3xl lg:text-4xl font-semibold leading-tight">
              {serverTime?.data?.server_time ?? '--:--'}
            </div>
          </motion.div>
          <motion.div variants={variants} initial="enter" animate="center" className="p-3 sm:p-4 md:p-5 rounded-xl bg-black/30 border border-white/5 min-h-[84px]">
            <div className="flex items-center gap-2 text-white/70 text-sm sm:text-base"><Users size={18} /> {t('home.players')}</div>
            <div className="text-2xl sm:text-3xl lg:text-4xl font-semibold leading-tight">
              {playersStats?.data?.online_count ?? 0}
            </div>
          </motion.div>
          <motion.div variants={variants} initial="enter" animate="center" className="p-3 sm:p-4 md:p-5 rounded-xl bg-black/30 border border-white/5 min-h-[84px]">
            <div className="flex items-center gap-2 text-white/70 text-sm sm:text-base"><ServerIcon size={18} /> {t('home.status')}</div>
            <div className={`text-2xl sm:text-3xl lg:text-4xl font-semibold leading-tight ${statusDisplay.color}`}>
              {statusDisplay.text}
            </div>
          </motion.div>

          {/* Novos cards: Temperaturas */}
          <motion.div variants={variants} initial="enter" animate="center" className="p-3 sm:p-4 md:p-5 rounded-xl bg-black/30 border border-white/5 min-h-[84px]">
            <div className="flex items-center gap-2 text-white/70 text-sm sm:text-base"><Thermometer size={18} /> {t('home.temperatures')}</div>
            <div className="text-sm sm:text-base font-medium leading-tight mt-1">
              <div className="flex items-center gap-2">
                <span className="text-white/60">{t('home.temp.air')}:</span>
                <span className="text-white">{formatTemperature(serverTime?.data?.air_temperature)}</span>
              </div>
              <div className="flex items-center gap-2 mt-1">
                <Droplets size={14} className="text-blue-400" />
                <span className="text-white/60">{t('home.temp.water')}:</span>
                <span className="text-white">{formatTemperature(serverTime?.data?.water_temperature)}</span>
              </div>
            </div>
          </motion.div>

          {/* Card: Astronomia e Clima */}
          <motion.div variants={variants} initial="enter" animate="center" className="p-3 sm:p-4 md:p-5 rounded-xl bg-black/30 border border-white/5 min-h-[84px]">
            <div className="flex items-center gap-2 text-white/70 text-sm sm:text-base"><Moon size={18} /> {t('home.astronomyAndClimate')}</div>
            <div className="flex items-center gap-3 mt-1">
              <span className="text-2xl">{moonPhaseInfo.icon}</span>
              <div>
                <div className="text-lg font-semibold">{moonPhaseInfo.phase}</div>
                {serverTime?.data?.moon_rotation !== undefined && (
                  <div className="text-xs text-white/50">
                    {t('home.moon.rotation')}: {serverTime.data.moon_rotation.toFixed(2)}
                  </div>
                )}
                <div className={`${fogStatus.color} text-xs font-semibold mt-1`}>
                  {fogStatus.text}
                </div>
                {serverTime?.data?.cumulonimbus_causes_fog && (
                  <div className="text-xs text-orange-400 mt-1">
                    {t('home.fog.cumulonimbus')}
                  </div>
                )}
              </div>
            </div>
          </motion.div>

          {/* Card: Próximo Reinício */}
          <motion.div variants={variants} initial="enter" animate="center" className="p-3 sm:p-4 md:p-5 rounded-xl bg-black/30 border border-white/5 min-h-[84px]">
            <div className="flex items-center gap-2 text-white/70 text-sm sm:text-base"><RotateCw size={18} /> {t('server.scheduler.status.nextRestart')}</div>
            <div className="text-2xl sm:text-3xl lg:text-4xl font-semibold leading-tight">
              {schedulerStatus?.next_restart 
                ? getCountdown(schedulerStatus.next_restart)
                : t('server.scheduler.status.noRestartScheduled') || '—'}
            </div>
          </motion.div>
        </div>
      </div>

      {/* Card: Estatísticas de Jogadores */}
      <div className="relative card p-3 sm:p-4 overflow-hidden">
        <canvas ref={playerStatsGridRef} className="absolute inset-0 w-full h-full" />
        <div className="relative z-10">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-lg font-semibold flex items-center gap-2">
              <Users size={20} />
              {t('home.playerStats.title')}
            </h2>
          </div>

        {/* Métricas Principais - Todos os cards lado a lado */}
        <div className="grid grid-cols-3 sm:grid-cols-6 gap-2 sm:gap-3">
          {/* Total de Jogadores */}
          <motion.div
            variants={variants}
            initial="enter"
            animate="center"
            className="p-2 sm:p-3 rounded-lg bg-black/30 border border-white/5"
          >
            <div className="flex items-center gap-1.5 text-white/70 text-xs mb-1">
              <Users size={12} />
              {t('home.playerStats.total', { defaultValue: 'Total' })}
            </div>
            <div className="text-lg sm:text-xl font-bold text-white">
              {playersLogs?.total_players ?? 0}
            </div>
          </motion.div>

          {/* Média (da análise de 7 dias) */}
          {analysisData?.data?.datasets?.[0] && (
            <motion.div
              variants={variants}
              initial="enter"
              animate="center"
              className="p-2 sm:p-3 rounded-lg bg-black/30 border border-white/5"
            >
              <div className="flex items-center gap-1.5 text-white/70 text-xs mb-1">
                <BarChart3 size={12} className="text-blue-400" />
                {t('home.playerStats.average', { defaultValue: 'Average' })}
              </div>
              <div className="text-lg sm:text-xl font-bold text-blue-400">
                {analysisData.data.datasets[0].average.toFixed(1)}
              </div>
              <div className="text-[10px] text-white/50 mt-0.5">
                {t('players.analyses.players')}
              </div>
            </motion.div>
          )}

          {/* Pico (da análise de 7 dias) */}
          {analysisData?.data?.datasets?.[0] && (
            <motion.div
              variants={variants}
              initial="enter"
              animate="center"
              className="p-2 sm:p-3 rounded-lg bg-black/30 border border-white/5"
            >
              <div className="flex items-center gap-1.5 text-white/70 text-xs mb-1">
                <BarChart3 size={12} className="text-green-400" />
                {t('home.playerStats.peak', { defaultValue: 'Peak' })}
              </div>
              <div className="text-lg sm:text-xl font-bold text-green-400">
                {analysisData.data.datasets[0].peak.toFixed(1)}
              </div>
              <div className="text-[10px] text-white/50 mt-0.5">
                {t('players.analyses.players')}
              </div>
            </motion.div>
          )}

          {/* Baixa (da análise de 7 dias) */}
          {analysisData?.data?.datasets?.[0] && (
            <motion.div
              variants={variants}
              initial="enter"
              animate="center"
              className="p-2 sm:p-3 rounded-lg bg-black/30 border border-white/5"
            >
              <div className="flex items-center gap-1.5 text-white/70 text-xs mb-1">
                <BarChart3 size={12} className="text-red-400" />
                {t('home.playerStats.lowest', { defaultValue: 'Lowest' })}
              </div>
              <div className="text-lg sm:text-xl font-bold text-red-400">
                {analysisData.data.datasets[0].lowest.toFixed(1)}
              </div>
              <div className="text-[10px] text-white/50 mt-0.5">
                {t('players.analyses.players')}
              </div>
            </motion.div>
          )}

          {/* Horário de Pico (da análise de 7 dias) */}
          <motion.div
            variants={variants}
            initial="enter"
            animate="center"
            className="p-2 sm:p-3 rounded-lg bg-black/30 border border-white/5"
          >
            <div className="flex items-center gap-1.5 text-white/70 text-xs mb-1">
              <BarChart3 size={12} className="text-purple-400" />
              {t('home.playerStats.peakHour', { defaultValue: 'Peak hour' })}
            </div>
            {hourlyAverageData?.data ? (
              <>
                <div className="text-lg sm:text-xl font-bold text-purple-400">
                  {hourlyAverageData.data.peak_hour}h
                </div>
                <div className="text-[10px] text-white/50 mt-0.5">
                  {Math.round(hourlyAverageData.data.peak_hour_average)} {t('players.analyses.players')}
                </div>
              </>
            ) : peakHours.length > 0 ? (
              <>
                <div className="text-lg sm:text-xl font-bold text-purple-400">
                  {peakHours[0].hour}
                </div>
                <div className="text-[10px] text-white/50 mt-0.5">
                  {peakHours[0].avg} {t('home.peakHours.avgPlayers')}
                </div>
              </>
            ) : (
              <div className="text-lg sm:text-xl font-bold text-white/50">
                —
              </div>
            )}
          </motion.div>

          {/* Pico Absoluto (da análise de 7 dias) */}
          {hourlyAverageData?.data?.absolute_peak && (
            <motion.div
              variants={variants}
              initial="enter"
              animate="center"
              className="p-2 sm:p-3 rounded-lg bg-black/30 border border-white/5"
            >
              <div className="flex items-center gap-1.5 text-white/70 text-xs mb-1">
                <Target size={12} className="text-purple-400" />
                {t('home.playerStats.absolutePeak', { defaultValue: 'Absolute peak' })}
              </div>
              <div className="text-lg sm:text-xl font-bold text-purple-400">
                {hourlyAverageData.data.absolute_peak.players_count}
              </div>
              <div className="text-[10px] text-white/50 mt-0.5">
                {(() => {
                  const date = new Date(hourlyAverageData.data.absolute_peak.timestamp);
                  const hour = date.getHours().toString().padStart(2, '0');
                  const minute = date.getMinutes().toString().padStart(2, '0');
                  return `${hour}:${minute}`;
                })()}
              </div>
            </motion.div>
          )}
        </div>

        </div>
      </div>
    </div>
  );
}


