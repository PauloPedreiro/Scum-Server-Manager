import { useState, useRef, useEffect, useMemo, useCallback } from 'react';
import { useTranslation } from 'react-i18next';
import {
  MapPin,
  AlertCircle
} from 'lucide-react';
import mapImage from '@/assets/maps/Map.webp';
import {
  SCUM_WIKI_MAP_BOUNDS,
  SCUM_WIKI_CATEGORIES,
  SCUM_WIKI_MARKERS
} from '@/assets/maps/scumWikiMapData';
import {
  parseCoordinates,
  gameToPixel,
  calculateQuadrant,
  MAP_COORDINATE_ERROR,
  type GameCoordinates,
  type PixelCoordinates
} from '@/utils/mapCoordinates';
import { MAP_WIDTH, MAP_HEIGHT } from '@/utils/mapCalibration';
import { gameYawToArrowAngle } from '@/utils/yawCalibration';
import MapFiltersPanel from '@/components/map/MapFiltersPanel';
import {
  getChests,
  splitChestsByLocation,
  type ChestSnapshot,
  type ChestPlayerSummary,
  type ChestVehicleInfo
} from '@/services/chests';
import {
  getOnlinePlayersGps,
  type PlayerGpsData
} from '@/services/gps';
import {
  getFlags,
  type Flag
} from '@/services/flags';

interface MapInfo {
  gameCoords: GameCoordinates;
  pixelCoords: PixelCoordinates;
  quadrant: string;
}

type ChestLoadStatus = 'idle' | 'loading' | 'success' | 'error';
type GpsLoadStatus = 'idle' | 'loading' | 'success' | 'error';
type FlagsLoadStatus = 'idle' | 'loading' | 'success' | 'error';

interface ChestMarker {
  id: string;
  pixel: PixelCoordinates;
  chest: ChestSnapshot;
  label: string;
}

interface VehicleChestGroup {
  key: string;
  vehicle: ChestVehicleInfo | null;
  ownerName: string | null;
  ownerSteamId: string | null;
  chests: ChestSnapshot[];
  lastSeenAt: string | null;
}

interface DisplayMarker {
  id: string;
  pixel: PixelCoordinates;
  color: string;
  borderColor: string;
  pulse?: boolean;
  label?: string;
  yaw?: number; // Direção em graus para GPS
  playerName?: string; // Nome do jogador para GPS
  gpsClusterKey?: string;
  gpsClusterMembers?: string[];
  flag?: Flag; // Dados da bandeira para renderização customizada
  wiki?: {
    categoryId: string;
    title: string;
    description?: string;
    linkUrl?: string;
    linkLabel?: string;
  };
}

interface GpsMarker {
  id: string;
  pixel: PixelCoordinates;
  player: PlayerGpsData;
  yaw: number; // Direção em graus
  label: string;
  clusterKey: string;
  clusterMembers?: string[];
}

interface GpsDataState {
  status: GpsLoadStatus;
  markers: GpsMarker[];
  players: PlayerGpsData[];
  count: number;
  timestamp: string | number | null;
  error?: string;
}

interface FlagMarker {
  id: string;
  pixel: PixelCoordinates;
  flag: Flag;
  label: string;
}

interface FlagsDataState {
  status: FlagsLoadStatus;
  markers: FlagMarker[];
  flags: Flag[];
  total: number;
  with_owner: number;
  no_owner: number;
  error?: string;
}

function matchesChestFilter(chest: ChestSnapshot, filter: string): boolean {
  if (!filter) return true;

  const normalizedFilter = filter.toLowerCase();
  const isSteamId = /^\d{5,}$/.test(filter.replace(/\D/g, ''));

  const steamId = chest.steam_id?.toLowerCase() ?? '';
  const playerName = chest.player_name?.toLowerCase() ?? '';
  const fakeName = chest.fake_name?.toLowerCase() ?? '';
  const customName = chest.custom_name?.toLowerCase() ?? '';

  if (isSteamId) {
    return steamId.includes(normalizedFilter);
  }

  return (
    playerName.includes(normalizedFilter) ||
    fakeName.includes(normalizedFilter) ||
    customName.includes(normalizedFilter)
  );
}

function matchesFlagFilter(flag: Flag, filter: string): boolean {
  if (!filter) return true;

  const normalizedFilter = filter.toLowerCase();
  const isSteamId = /^\d{5,}$/.test(filter.replace(/\D/g, ''));

  const ownerName = flag.owner_name?.toLowerCase() ?? '';
  const owner = flag.owner?.toLowerCase() ?? '';

  if (isSteamId) {
    // Verificar se o owner contém o Steam ID
    return owner.includes(normalizedFilter);
  }

  // Buscar por nome do proprietário
  return ownerName.includes(normalizedFilter) || owner.includes(normalizedFilter);
}

interface ChestDataState {
  status: ChestLoadStatus;
  markers: ChestMarker[];
  groups: VehicleChestGroup[];
  totalCount: number;
  displayedCount: number;
  missingCount: number;
  error?: string;
  playersSummary?: ChestPlayerSummary[];
  timestamp?: number;
}

function formatRelativeTimeFromSeconds(timestamp: number, locale: string): string {
  const formatter = new Intl.RelativeTimeFormat(locale, { numeric: 'auto' });
  const now = Date.now();
  const diffMs = now - timestamp * 1000;

  if (!Number.isFinite(diffMs)) {
    return '';
  }

  const units: Array<[number, Intl.RelativeTimeFormatUnit]> = [
    [60, 'second'],
    [60, 'minute'],
    [24, 'hour'],
    [7, 'day'],
    [4.34524, 'week'],
    [12, 'month'],
  ];

  let value = diffMs / 1000;
  let unit: Intl.RelativeTimeFormatUnit = 'second';

  for (const [divider, nextUnit] of units) {
    if (Math.abs(value) < divider) {
      break;
    }

    value /= divider;
    unit = nextUnit;
  }

  const rounded = Math.round(value);
  return formatter.format(-rounded, unit);
}

function formatDateTime(value: string | null | undefined, locale: string): string {
  if (!value) {
    return '—';
  }

  const date = new Date(value);

  if (Number.isNaN(date.getTime())) {
    return value;
  }

  return new Intl.DateTimeFormat(locale, {
    dateStyle: 'short',
    timeStyle: 'short',
  }).format(date);
}

function buildVehicleGroups(chests: ChestSnapshot[]): VehicleChestGroup[] {
  const groups = new Map<string, VehicleChestGroup>();

  chests.forEach((chest) => {
    const vehicleKey =
      (chest.vehicle?.entity_id ?? undefined)?.toString() ??
      (chest.container_entity_id ?? undefined)?.toString() ??
      `unknown-${chest.entity_id}`;

    let group = groups.get(vehicleKey);

    if (!group) {
      group = {
        key: vehicleKey,
        vehicle: chest.vehicle,
        ownerName: chest.player_name ?? chest.fake_name,
        ownerSteamId: chest.steam_id,
        chests: [],
        lastSeenAt: chest.last_seen_at ?? null,
      };
      groups.set(vehicleKey, group);
    }

    group.chests.push(chest);

    const currentLastSeen = group.lastSeenAt ? new Date(group.lastSeenAt).getTime() : 0;
    const chestLastSeen = new Date(chest.last_seen_at).getTime();

    if (!currentLastSeen || chestLastSeen > currentLastSeen) {
      group.lastSeenAt = chest.last_seen_at;
    }
  });

  return Array.from(groups.values()).sort((a, b) => b.chests.length - a.chests.length);
}

function getChestDisplayLabel(chest: ChestSnapshot): string {
  return (
    chest.custom_name ||
    chest.player_name ||
    chest.fake_name ||
    chest.chest_type ||
    `Chest ${chest.entity_id}`
  );
}

export default function MapPage() {
  const { t, i18n } = useTranslation();
  const containerRef = useRef<HTMLDivElement>(null);
  const mapWrapperRef = useRef<HTMLDivElement>(null);
  const mapImageRef = useRef<HTMLImageElement>(null);
  const stageRef = useRef<HTMLDivElement>(null);
  const isDraggingRef = useRef(false);
  const dragStartRef = useRef<{ x: number; y: number; tx: number; ty: number } | null>(null);
  const isMountedRef = useRef(true);
  const [filtersState, setFiltersState] = useState({
    chests: false,
    gps: false,
    flags: false,
    wikiGeneral: false,
    wikiPois: false,
    wikiBunkers: false,
    wikiTraders: false,
  });
  const [chestsState, setChestsState] = useState<ChestDataState>({
    status: 'idle',
    markers: [],
    groups: [],
    totalCount: 0,
    displayedCount: 0,
    missingCount: 0,
  });
  
  const [gpsState, setGpsState] = useState<GpsDataState>({
    status: 'idle',
    markers: [],
    players: [],
    count: 0,
    timestamp: null,
  });
  
  const [flagsState, setFlagsState] = useState<FlagsDataState>({
    status: 'idle',
    markers: [],
    flags: [],
    total: 0,
    with_owner: 0,
    no_owner: 0,
  });
  
  // Estados para coordenadas
  const [coordsInput, setCoordsInput] = useState('');
  const [markerPosition, setMarkerPosition] = useState<PixelCoordinates | null>(null);
  const [mapInfo, setMapInfo] = useState<MapInfo | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [playerFilter, setPlayerFilter] = useState<string | null>(null);
  const [hoveredMarkerId, setHoveredMarkerId] = useState<string | null>(null);
  const [hoveredGpsClusterKey, setHoveredGpsClusterKey] = useState<string | null>(null);
  const [pinnedGpsClusterKey, setPinnedGpsClusterKey] = useState<string | null>(null);
  const [mapScale, setMapScale] = useState(1);
  const [mapTranslate, setMapTranslate] = useState({ x: 0, y: 0 });
  const mapScaleRef = useRef(1);
  const mapTranslateRef = useRef({ x: 0, y: 0 });
  const isChestsActive = filtersState.chests;
  const isGpsActive = filtersState.gps;
  const isFlagsActive = filtersState.flags;
  const CHESTS_LIMIT = 1000;
  const GPS_POLL_INTERVAL = 30000; // 30 segundos (apenas GPS tem atualização automática)

  const wikiBoundsWidth = SCUM_WIKI_MAP_BOUNDS[1][0] - SCUM_WIKI_MAP_BOUNDS[0][0];
  const wikiBoundsHeight = SCUM_WIKI_MAP_BOUNDS[1][1] - SCUM_WIKI_MAP_BOUNDS[0][1];

  // Alguns datasets do SCUM Wiki já vêm alinhados com a orientação do nosso Map.webp.
  // Deixe isso configurável por dataset (por enquanto, manter sem espelhar).
  const WIKI_FLIP_X = false;

  const wikiToPixel = useCallback(
    (wikiX: number, wikiY: number): PixelCoordinates => {
      // Wiki usa origin bottom-left, DOM usa top-left
      const normalizedX = WIKI_FLIP_X ? 1 - wikiX / wikiBoundsWidth : wikiX / wikiBoundsWidth;
      const normalizedY = (wikiBoundsHeight - wikiY) / wikiBoundsHeight;
      return {
        x: Math.max(0, Math.min(MAP_WIDTH, normalizedX * MAP_WIDTH)),
        y: Math.max(0, Math.min(MAP_HEIGHT, normalizedY * MAP_HEIGHT)),
      };
    },
    [WIKI_FLIP_X, wikiBoundsWidth, wikiBoundsHeight]
  );

  useEffect(() => {
    isMountedRef.current = true;
    return () => {
      isMountedRef.current = false;
    };
  }, []);

  const loadChestsData = useCallback(async () => {
    setChestsState((prev) => ({
      ...prev,
      status: 'loading',
      error: undefined,
    }));

    try {
      const response = await getChests({
        limit: CHESTS_LIMIT,
        offset: 0,
        minimal: true,
      });

      if (!response.success) {
        throw new Error(t('map.chests.error', 'Erro ao carregar baús'));
      }

      const { mappable, vehicleStored, withoutLocation } = splitChestsByLocation(response.data.chests);
      const markers: ChestMarker[] = mappable
        .map((chest) => ({
          id: `chest-${chest.entity_id}`,
          pixel: gameToPixel(chest.location.x ?? 0, chest.location.y ?? 0),
          chest,
          label: getChestDisplayLabel(chest),
        }))
        .sort((a, b) => {
          const timeA = new Date(a.chest.last_seen_at).getTime();
          const timeB = new Date(b.chest.last_seen_at).getTime();
          return timeB - timeA;
        });

      const groups = buildVehicleGroups([...vehicleStored, ...withoutLocation]);
      const returnedCount = response.data.chests.length;
      const totalCount = response.data.total ?? response.data.count ?? returnedCount;
      const missingCount = Math.max(returnedCount - markers.length, 0);

      if (!isMountedRef.current) {
        return;
      }

      setChestsState({
        status: 'success',
        markers,
        groups,
        totalCount,
        displayedCount: markers.length,
        missingCount,
        error: undefined,
        playersSummary: response.data.players,
        timestamp: response.timestamp,
      });
    } catch (err) {
      console.error('[Map] Falha ao carregar baús', err);
      if (!isMountedRef.current) {
        return;
      }

      const message =
        err instanceof Error ? err.message : t('map.chests.error', 'Erro ao carregar baús');

      setChestsState((prev) => ({
        ...prev,
        status: 'error',
        error: message,
      }));
    }
  }, [CHESTS_LIMIT, t]);

  useEffect(() => {
    if (!isChestsActive) {
      return;
    }

    if (chestsState.status === 'idle') {
      loadChestsData();
    }
  }, [isChestsActive, chestsState.status, loadChestsData]);

  // Limpar pesquisa e resetar estado quando desmarcar o filtro de baús
  useEffect(() => {
    if (!isChestsActive && chestsState.status !== 'idle') {
      // Limpar pesquisa se estiver ativa
      if (playerFilter) {
        setPlayerFilter(null);
        setCoordsInput('');
        setError(null);
      }
      // Resetar estado para 'idle' para forçar recarregamento quando marcar novamente
      setChestsState({
        status: 'idle',
        markers: [],
        groups: [],
        totalCount: 0,
        displayedCount: 0,
        missingCount: 0,
      });
    }
  }, [isChestsActive, playerFilter]);

  const handleRefreshChests = useCallback(() => {
    loadChestsData();
  }, [loadChestsData]);

  // Função para converter yaw do jogo para ângulo da seta (usando calibração)
  const convertYawToArrowAngle = useCallback((gameYaw: number): number => {
    return gameYawToArrowAngle(gameYaw);
  }, []);

  // Função para carregar dados GPS
  const loadGpsData = useCallback(async () => {
    setGpsState((prev) => ({
      ...prev,
      status: 'loading',
      error: undefined,
    }));

    try {
      const response = await getOnlinePlayersGps();

      if (!response.success) {
        throw new Error(response.error || t('map.gps.error', 'Erro ao carregar GPS'));
      }

      if (!response.data || !response.data.players) {
        if (!isMountedRef.current) {
          return;
        }

        setGpsState({
          status: 'success',
          markers: [],
          players: [],
          count: 0,
          timestamp: null,
        });
        return;
      }

      let skippedWithoutSpawn = 0;

      const rawMarkers: GpsMarker[] = response.data.players
        .map((player) => {
          // Usar coordenadas do GPS (gps_data.spawns[0])
          const spawn =
            player.gps_data?.spawns && player.gps_data.spawns.length > 0 ? player.gps_data.spawns[0] : null;

          if (!spawn) {
            skippedWithoutSpawn += 1;
            return null;
          }

          const yaw = convertYawToArrowAngle(spawn.rotation_yaw);

          const pixel = gameToPixel(spawn.location_x, spawn.location_y);

          const clusterKey = `${Math.round(pixel.x)}-${Math.round(pixel.y)}`;

          return {
            id: `gps-${player.steam_id}`,
            pixel,
            player,
            yaw,
            label: player.player_name,
            clusterKey,
          };
        })
        .filter((marker): marker is GpsMarker => marker !== null);

      // Evitar que jogadores no mesmo ponto "sumam" por sobreposição:
      // aplica offsets pequenos em espiral para markers que caem no mesmo pixel (arredondado).
      const stackIndexByKey = new Map<string, number>();
      const markers: GpsMarker[] = rawMarkers.map((m) => {
        const index = stackIndexByKey.get(m.clusterKey) ?? 0;
        stackIndexByKey.set(m.clusterKey, index + 1);

        if (index === 0) {
          return m;
        }

        const angle = index * 0.9;
        const radius = Math.min(18, 6 + index * 4);
        const offsetX = Math.cos(angle) * radius;
        const offsetY = Math.sin(angle) * radius;

        return {
          ...m,
          pixel: {
            x: Math.max(0, Math.min(MAP_WIDTH, m.pixel.x + offsetX)),
            y: Math.max(0, Math.min(MAP_HEIGHT, m.pixel.y + offsetY)),
          },
        };
      });

      const clusterMembersMap = new Map<string, string[]>();
      markers.forEach((m) => {
        const current = clusterMembersMap.get(m.clusterKey) ?? [];
        current.push(m.label);
        clusterMembersMap.set(m.clusterKey, current);
      });

      const markersWithClusters: GpsMarker[] = markers.map((m) => ({
        ...m,
        clusterMembers: clusterMembersMap.get(m.clusterKey) ?? [m.label],
      }));

      if (skippedWithoutSpawn > 0) {
        console.warn(`[Map] GPS: ${skippedWithoutSpawn} players sem spawn/gps_data (sem marker no mapa)`);
      }

      if (!isMountedRef.current) {
        return;
      }

      setGpsState({
        status: 'success',
        markers: markersWithClusters,
        players: response.data.players,
        count: response.data.count,
        timestamp: response.timestamp || null,
        error: undefined,
      });
    } catch (err) {
      console.error('[Map] Falha ao carregar GPS', err);
      if (!isMountedRef.current) {
        return;
      }

      const message =
        err instanceof Error ? err.message : t('map.gps.error', 'Erro ao carregar GPS');

      setGpsState((prev) => ({
        ...prev,
        status: 'error',
        error: message,
      }));
    }
  }, [t, convertYawToArrowAngle]);

  // Carregar GPS quando filtro for ativado
  useEffect(() => {
    if (!isGpsActive) {
      return;
    }

    if (gpsState.status === 'idle') {
      loadGpsData();
    }
  }, [isGpsActive, gpsState.status, loadGpsData]);

  // Polling automático para GPS (a cada 30 segundos quando ativo)
  useEffect(() => {
    if (!isGpsActive || gpsState.status !== 'success') {
      return;
    }

    const interval = setInterval(() => {
      loadGpsData();
    }, GPS_POLL_INTERVAL);

    return () => clearInterval(interval);
  }, [isGpsActive, gpsState.status, loadGpsData]);

  const handleRefreshGps = useCallback(() => {
    loadGpsData();
  }, [loadGpsData]);

  // Função para carregar dados de Flags
  const loadFlagsData = useCallback(async () => {
    setFlagsState((prev) => ({
      ...prev,
      status: 'loading',
      error: undefined,
    }));

    try {
      const response = await getFlags();

      if (!response.success) {
        throw new Error(response.error || t('map.flags.error', 'Erro ao carregar bandeiras'));
      }

      if (!response.data || !response.data.flags) {
        if (!isMountedRef.current) {
          return;
        }

        setFlagsState({
          status: 'success',
          markers: [],
          flags: [],
          total: 0,
          with_owner: 0,
          no_owner: 0,
        });
        return;
      }

      const markers: FlagMarker[] = response.data.flags
        .map((flag) => {
          const coords = flag.location;
          
          // Converter coordenadas para pixels
          const pixel = gameToPixel(coords.x, coords.y);
          
          // Ajustar posição das bandeiras: mover um pouco para a direita e para cima
          // Ajuste em pixels (valores positivos em X movem para direita, negativos em Y movem para cima)
          const adjustedPixel = {
            x: pixel.x + 15, // Move para a direita (ajuste mínimo)
            y: pixel.y - 18, // Move para cima (ajustado para baixo)
          };

          // Filtrar apenas marcadores com coordenadas válidas
          if (adjustedPixel.x < 0 || adjustedPixel.x > MAP_WIDTH || adjustedPixel.y < 0 || adjustedPixel.y > MAP_HEIGHT) {
            return null;
          }

          // Criar label com apenas o nome do proprietário
          let label = '';
          if (flag.owner !== 'no owner') {
            // Usar apenas o nome do owner, sem Steam ID e sem base
            label = flag.owner_name || flag.owner.split(' (')[0] || flag.owner;
          } else {
            label = t('map.flags.noOwner', 'Sem proprietário');
          }

          return {
            id: `flag-${flag.element_id}`,
            pixel: adjustedPixel,
            flag,
            label,
          };
        })
        .filter((marker): marker is FlagMarker => marker !== null);

      if (!isMountedRef.current) {
        return;
      }

      setFlagsState({
        status: 'success',
        markers,
        flags: response.data.flags,
        total: response.data.total,
        with_owner: response.data.with_owner,
        no_owner: response.data.no_owner,
      });
    } catch (err) {
      console.error('[Map] Falha ao carregar bandeiras', err);
      if (!isMountedRef.current) {
        return;
      }

      const message =
        err instanceof Error ? err.message : t('map.flags.error', 'Erro ao carregar bandeiras');

      setFlagsState((prev) => ({
        ...prev,
        status: 'error',
        error: message,
      }));
    }
  }, [t]);

  // Carregar flags quando o filtro for ativado (apenas uma vez, sem polling automático)
  useEffect(() => {
    if (!isFlagsActive) {
      return;
    }

    if (flagsState.status === 'idle') {
      loadFlagsData();
    }
  }, [isFlagsActive, flagsState.status, loadFlagsData]);

  // Limpar pesquisa e resetar estado quando desmarcar o filtro de bandeiras
  useEffect(() => {
    if (!isFlagsActive && flagsState.status !== 'idle') {
      // Limpar pesquisa se estiver ativa
      if (playerFilter) {
        setPlayerFilter(null);
        setCoordsInput('');
        setError(null);
      }
      // Resetar estado para 'idle' para forçar recarregamento quando marcar novamente
      setFlagsState({
        status: 'idle',
        markers: [],
        flags: [],
        total: 0,
        with_owner: 0,
        no_owner: 0,
      });
    }
  }, [isFlagsActive, playerFilter]);

  // Toggle mutuamente exclusivo: GPS, Baús e Bandeiras não podem estar ativos ao mesmo tempo
  const toggleFilter = useCallback((id: string) => {
    if (id === 'chests') {
      setFiltersState((prev) => ({
        ...prev,
        chests: !prev.chests,
        gps: false, // Desativa GPS se ativar Baús
        flags: false, // Desativa Flags se ativar Baús
      }));
    } else if (id === 'gps') {
      setFiltersState((prev) => ({
        ...prev,
        gps: !prev.gps,
        chests: false, // Desativa Baús se ativar GPS
        flags: false, // Desativa Flags se ativar GPS
      }));
    } else if (id === 'flags') {
      setFiltersState((prev) => ({
        ...prev,
        flags: !prev.flags,
        chests: false, // Desativa Baús se ativar Flags
        gps: false, // Desativa GPS se ativar Flags
      }));
    } else if (id === 'wikiGeneral') {
      setFiltersState((prev) => ({
        ...prev,
        wikiGeneral: !prev.wikiGeneral,
      }));
    } else if (id === 'wikiPois') {
      setFiltersState((prev) => ({
        ...prev,
        wikiPois: !prev.wikiPois,
      }));
    } else if (id === 'wikiBunkers') {
      setFiltersState((prev) => ({
        ...prev,
        wikiBunkers: !prev.wikiBunkers,
      }));
    } else if (id === 'wikiTraders') {
      setFiltersState((prev) => ({
        ...prev,
        wikiTraders: !prev.wikiTraders,
      }));
    }
  }, []);

  const filtersOptions = useMemo(
    () => [
      {
        id: 'chests',
        label: t('map.filters.labels.chests', 'Baús'),
        description: t('map.filters.descriptions.chests', 'Mostra todos os baús sincronizados'),
        active: filtersState.chests,
        loading: filtersState.chests && chestsState.status === 'loading',
        count: chestsState.totalCount || undefined,
      },
      {
        id: 'flags',
        label: t('map.filters.labels.flags', 'Bandeiras'),
        description: t('map.filters.descriptions.flags', 'Mostra todas as bandeiras do mapa'),
        active: filtersState.flags,
        loading: filtersState.flags && flagsState.status === 'loading',
        count: flagsState.total || undefined,
      },
    ],
    [
      t,
      filtersState.chests,
      filtersState.flags,
      chestsState.status,
      chestsState.totalCount,
      flagsState.status,
      flagsState.total,
    ]
  );

  const lastSyncLabel = useMemo(() => {
    if (!chestsState.timestamp) {
      return null;
    }
    const relative = formatRelativeTimeFromSeconds(chestsState.timestamp, i18n.language);
    return relative || null;
  }, [chestsState.timestamp, i18n.language]);

  const chestsLoading = chestsState.status === 'loading';
  const chestsError = chestsState.status === 'error' ? chestsState.error : null;

  const normalizedFilter = playerFilter?.trim().toLowerCase() ?? '';
  const hasFilter = Boolean(normalizedFilter);

  const allMarkers = chestsState.markers;
  const allGroups = chestsState.groups;

  const filteredMarkers = useMemo(() => {
    if (chestsState.status !== 'success' || !hasFilter) {
      return allMarkers;
    }

    return allMarkers.filter((marker) => matchesChestFilter(marker.chest, normalizedFilter));
  }, [chestsState.status, hasFilter, allMarkers, normalizedFilter]);

  const filteredGroups = useMemo(() => {
    if (chestsState.status !== 'success' || !hasFilter) {
      return allGroups;
    }

    return allGroups
      .map((group) => {
        const filteredChests = group.chests.filter((chest) =>
          matchesChestFilter(chest, normalizedFilter)
        );

        if (filteredChests.length === 0) {
          return null;
        }

        return {
          ...group,
          chests: filteredChests,
        };
      })
      .filter(Boolean) as VehicleChestGroup[];
  }, [chestsState, normalizedFilter, hasFilter]);

  const vehicleStoredTotal = useMemo(
    () =>
      filteredGroups.reduce((acc, group) => {
        return acc + group.chests.length;
      }, 0),
    [filteredGroups]
  );

  const visibleMarkersCount = useMemo(() => {
    if (!filtersState.chests) return 0;

    if (chestsState.status !== 'success') {
      return chestsState.displayedCount;
    }

    return filteredMarkers.length;
  }, [filtersState.chests, chestsState.status, chestsState.displayedCount, filteredMarkers]);

  const noLocationCount = useMemo(
    () => (filtersState.chests ? vehicleStoredTotal : 0),
    [filtersState.chests, vehicleStoredTotal]
  );

  const displayMarkers = useMemo<DisplayMarker[]>(() => {
    const markers: DisplayMarker[] = [];

    if (filtersState.chests && chestsState.status === 'success') {
      markers.push(
        ...filteredMarkers.map((marker) => ({
          id: marker.id,
          pixel: marker.pixel,
          color: '#f97316',
          borderColor: 'rgba(255,255,255,0.8)',
          pulse: false,
          label: undefined,
        }))
      );
    }

    if (filtersState.gps && gpsState.status === 'success') {
      markers.push(
        ...gpsState.markers.map((marker) => ({
          id: marker.id,
          pixel: marker.pixel,
          color: '#ef4444', // Vermelho para GPS
          borderColor: 'rgba(255,255,255,0.9)',
          pulse: false,
          label: marker.label,
          yaw: marker.yaw,
          playerName: marker.player.player_name,
          gpsClusterKey: marker.clusterKey,
          gpsClusterMembers: marker.clusterMembers,
        }))
      );
    }

    if (filtersState.flags && flagsState.status === 'success') {
      const flagsToShow = hasFilter
        ? flagsState.markers.filter((marker) => matchesFlagFilter(marker.flag, normalizedFilter))
        : flagsState.markers;
      
      markers.push(
        ...flagsToShow.map((marker) => ({
          id: marker.id,
          pixel: marker.pixel,
          color: marker.flag.owner === 'no owner' ? '#ef4444' : '#22c55e', // Vermelho se sem owner, verde se com owner
          borderColor: 'rgba(255,255,255,0.9)',
          pulse: false,
          label: marker.label,
          flag: marker.flag, // Adicionar flag para renderização customizada
        }))
      );
    }

    const wikiCategoriesToShow = new Set<string>();
    if (filtersState.wikiGeneral) wikiCategoriesToShow.add('1');
    if (filtersState.wikiPois) wikiCategoriesToShow.add('2');
    if (filtersState.wikiBunkers) wikiCategoriesToShow.add('3');
    if (filtersState.wikiTraders) wikiCategoriesToShow.add('6');

    if (wikiCategoriesToShow.size > 0) {
      const colorByCategory = new Map<string, string>();
      SCUM_WIKI_CATEGORIES.forEach((cat) => colorByCategory.set(cat.id, cat.color));

      const wikiMarkers = SCUM_WIKI_MARKERS.filter((m) => wikiCategoriesToShow.has(m.categoryId));
      markers.push(
        ...wikiMarkers.map((m) => {
          const pixel = wikiToPixel(m.position[0], m.position[1]);
          const color = colorByCategory.get(m.categoryId) ?? '#38bdf8';
          const title = m.popup?.title ?? 'Marker';
          return {
            id: `wiki-${m.id}`,
            pixel,
            color,
            borderColor: 'rgba(255,255,255,0.85)',
            pulse: false,
            label: undefined,
            wiki: {
              categoryId: m.categoryId,
              title,
              description: m.popup?.description,
              linkUrl: m.popup?.link?.url,
              linkLabel: m.popup?.link?.label,
            },
          };
        })
      );
    }

    if (markerPosition) {
      markers.push({
        id: 'manual-marker',
        pixel: markerPosition,
        color: '#ef4444',
        borderColor: 'rgba(255,255,255,0.9)',
        pulse: true,
        label: undefined,
      });
    }

    return markers;
  }, [
    filtersState.chests,
    filtersState.gps,
    filtersState.flags,
    filtersState.wikiGeneral,
    filtersState.wikiPois,
    filtersState.wikiBunkers,
    filtersState.wikiTraders,
    chestsState.status,
    gpsState.status,
    flagsState.status,
    filteredMarkers,
    gpsState.markers,
    flagsState.markers,
    markerPosition,
    hasFilter,
    normalizedFilter,
    wikiToPixel,
  ]);

  const pasteCoordsMessage = t('home.map.messages.pasteCoords');
  const invalidFormatMessage = t('home.map.messages.invalidFormat');
  const invalidNumbersMessage = t('home.map.messages.invalidNumbers');
  const processErrorMessage = t('home.map.messages.processError');

  // Reposiciona o marcador quando a janela é redimensionada
  useEffect(() => {
    const handleResize = () => {
      if (markerPosition && mapInfo) {
        // Recalcula a posição do marcador
        processCoordinates(coordsInput);
      }
    };

    let resizeTimeout: NodeJS.Timeout;
    const handleResizeDebounced = () => {
      clearTimeout(resizeTimeout);
      resizeTimeout = setTimeout(handleResize, 250);
    };

    window.addEventListener('resize', handleResizeDebounced);
    return () => {
      window.removeEventListener('resize', handleResizeDebounced);
      clearTimeout(resizeTimeout);
    };
  }, [markerPosition, mapInfo, coordsInput]);

  // Processa coordenadas
  const processCoordinates = (input: string) => {
    const trimmed = input.trim();

    if (!trimmed) {
      setError(pasteCoordsMessage);
      return;
    }

    try {
      setError(null);
      const gameCoords = parseCoordinates(trimmed);
      const pixelCoords = gameToPixel(gameCoords.x, gameCoords.y);
      const quadrant = calculateQuadrant(pixelCoords.x, pixelCoords.y);

      setPlayerFilter(null);
      setMarkerPosition(pixelCoords);
      setMapInfo({
        gameCoords,
        pixelCoords,
        quadrant,
      });
    } catch (err) {
      // Se não for coordenada válida, tratamos como filtro de busca (baús e bandeiras)
      setMarkerPosition(null);
      setMapInfo(null);
      setError(null);

      const normalized = trimmed.toLowerCase();
      setPlayerFilter(trimmed);

      let hasMatch = false;
      let matchType = '';

      // Buscar em baús
      if (chestsState.status === 'success') {
        const chestMatch =
          chestsState.markers.some((marker) => matchesChestFilter(marker.chest, normalized)) ||
          chestsState.groups.some((group) =>
            group.chests.some((chest) => matchesChestFilter(chest, normalized))
          );
        
        if (chestMatch) {
          hasMatch = true;
          matchType = 'chests';
        }
      }

      // Buscar em bandeiras
      if (flagsState.status === 'success') {
        const flagMatch = flagsState.markers.some((marker) => 
          matchesFlagFilter(marker.flag, normalized)
        );
        
        if (flagMatch) {
          hasMatch = true;
          matchType = matchType ? 'both' : 'flags';
        }
      }

      if (!hasMatch) {
        setError(t('map.search.noMatches', { query: trimmed }));
      }
    }
  };

  const clearPlayerFilter = useCallback(() => {
    setPlayerFilter(null);
    setError(null);
  }, []);

  const handleKeyPress = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter') {
      processCoordinates(coordsInput);
    }
  };

  useEffect(() => {
    mapScaleRef.current = mapScale;
  }, [mapScale]);

  useEffect(() => {
    mapTranslateRef.current = mapTranslate;
  }, [mapTranslate]);

  const handleMapWheelNative = useCallback((e: WheelEvent) => {
    // Necessário para impedir scroll da página ao dar zoom.
    e.preventDefault();

    const container = containerRef.current;
    if (!container) return;

    const rect = container.getBoundingClientRect();
    const cursorX = e.clientX - rect.left;
    const cursorY = e.clientY - rect.top;

    const currentScale = mapScaleRef.current;
    const currentTranslate = mapTranslateRef.current;

    const zoomIntensity = 0.0015;
    const delta = -e.deltaY;
    const nextScaleRaw = currentScale * (1 + delta * zoomIntensity);
    const nextScale = Math.max(1, Math.min(4, nextScaleRaw));

    const worldX = (cursorX - currentTranslate.x) / currentScale;
    const worldY = (cursorY - currentTranslate.y) / currentScale;
    const nextTranslateX = cursorX - worldX * nextScale;
    const nextTranslateY = cursorY - worldY * nextScale;

    setMapScale(nextScale);
    setMapTranslate({ x: nextTranslateX, y: nextTranslateY });
  }, []);

  useEffect(() => {
    const el = containerRef.current;
    if (!el) return;

    el.addEventListener('wheel', handleMapWheelNative, { passive: false });
    return () => {
      el.removeEventListener('wheel', handleMapWheelNative);
    };
  }, [handleMapWheelNative]);

  const handleMapMouseDown = useCallback(
    (e: React.MouseEvent<HTMLDivElement>) => {
      if (e.button !== 0) return;
      isDraggingRef.current = true;
      dragStartRef.current = {
        x: e.clientX,
        y: e.clientY,
        tx: mapTranslate.x,
        ty: mapTranslate.y,
      };
    },
    [mapTranslate.x, mapTranslate.y]
  );

  const handleMapMouseMove = useCallback((e: React.MouseEvent<HTMLDivElement>) => {
    if (!isDraggingRef.current || !dragStartRef.current) return;
    const dx = e.clientX - dragStartRef.current.x;
    const dy = e.clientY - dragStartRef.current.y;
    setMapTranslate({ x: dragStartRef.current.tx + dx, y: dragStartRef.current.ty + dy });
  }, []);

  const stopDragging = useCallback(() => {
    isDraggingRef.current = false;
    dragStartRef.current = null;
  }, []);

  return (
    <div className="grid gap-4 lg:grid-cols-[320px_1fr]">
      <MapFiltersPanel options={filtersOptions} onToggle={toggleFilter} />

      <div className="grid gap-4">
        <div className="card p-3 sm:p-4">
          <div className="mb-3 flex items-center justify-between">
            <h2 className="text-lg font-semibold">{t('home.map.title')}</h2>
          </div>

          {isGpsActive && gpsState.status === 'error' && gpsState.error && (
            <div className="mb-3 flex flex-wrap items-center gap-2 rounded-lg border border-red-500/40 bg-red-500/10 px-3 py-2 text-xs text-red-200 sm:text-sm">
              <AlertCircle className="shrink-0" size={16} />
              <span className="flex-1">{gpsState.error}</span>
            </div>
          )}

          {isChestsActive && chestsError && (
            <div className="mb-3 flex flex-wrap items-center gap-2 rounded-lg border border-red-500/40 bg-red-500/10 px-3 py-2 text-xs text-red-200 sm:text-sm">
              <AlertCircle className="shrink-0" size={16} />
              <span className="flex-1">{chestsError}</span>
            </div>
          )}

          {isFlagsActive && flagsState.status === 'error' && flagsState.error && (
            <div className="mb-3 flex flex-wrap items-center gap-2 rounded-lg border border-red-500/40 bg-red-500/10 px-3 py-2 text-xs text-red-200 sm:text-sm">
              <AlertCircle className="shrink-0" size={16} />
              <span className="flex-1">{flagsState.error}</span>
            </div>
          )}

          <div className="mb-4">
            <label
              htmlFor="coords-input"
              className="mb-2 block text-sm font-semibold text-white/90"
            >
              {t('home.map.input.label')}
            </label>
            <div className="flex flex-col gap-2 sm:flex-row">
              <input
                id="coords-input"
                type="text"
                value={coordsInput}
                onChange={(e: React.ChangeEvent<HTMLInputElement>) => setCoordsInput(e.target.value)}
                onKeyPress={handleKeyPress}
                placeholder={t('home.map.input.placeholder')}
                className="flex-1 rounded-lg border border-white/10 bg-black/30 px-3 py-2 text-sm text-white placeholder:text-white/40 focus:border-transparent focus:outline-none focus:ring-2 focus:ring-scum-accent font-mono"
              />
              <button
                onClick={() => processCoordinates(coordsInput)}
                type="button"
                className="flex items-center justify-center gap-2 rounded-lg bg-scum-accent px-4 py-2 text-sm font-semibold text-white transition hover:bg-scum-accent/90"
              >
                <MapPin size={16} />
                {t('home.map.input.submit')}
              </button>
            </div>
            {error && (
              <div className="mt-2 rounded-lg border border-red-500/30 bg-red-500/20 px-3 py-2 text-sm text-red-200">
                {error}
              </div>
            )}
          </div>

          <div
            ref={containerRef}
            className="relative aspect-square w-full max-w-[1080px] overflow-hidden rounded-lg border border-white/5 bg-black/30"
            style={{ userSelect: 'none', zIndex: 1, position: 'relative', touchAction: 'none' }}
            onMouseDown={handleMapMouseDown}
            onMouseMove={handleMapMouseMove}
            onMouseUp={stopDragging}
            onMouseLeave={stopDragging}
            onClick={() => setPinnedGpsClusterKey(null)}
          >
            <div
              ref={stageRef}
              className="absolute inset-0"
              style={{
                transform: `translate(${mapTranslate.x}px, ${mapTranslate.y}px) scale(${mapScale})`,
                transformOrigin: '0 0',
                cursor: isDraggingRef.current ? 'grabbing' : mapScale > 1 ? 'grab' : 'default',
              }}
            >
              <div ref={mapWrapperRef} className="absolute inset-0" style={{ zIndex: 1 }}>
                <img
                  src={mapImage}
                  alt={t('home.map.title')}
                  ref={mapImageRef}
                  className="h-full w-full select-none"
                  draggable={false}
                />
              </div>

              {displayMarkers.map((marker) => {
                const leftPercent = (marker.pixel.x / MAP_WIDTH) * 100;
                const topPercent = (marker.pixel.y / MAP_HEIGHT) * 100;

                // Se for marcador GPS, renderizar seta
                if (marker.yaw !== undefined) {
                  const playerName = marker.playerName || marker.label;
                  const clusterKey = marker.gpsClusterKey ?? marker.id;
                  const clusterMembers = marker.gpsClusterMembers ?? (playerName ? [playerName] : []);
                  const shouldShowClusterPopover =
                    pinnedGpsClusterKey === clusterKey || hoveredGpsClusterKey === clusterKey;

                  return (
                    <div
                      key={marker.id}
                      className="absolute z-10"
                      style={{
                        left: `${leftPercent}%`,
                        top: `${topPercent}%`,
                        transform: 'translate(-50%, -50%)',
                      }}
                      onMouseEnter={() => {
                        setHoveredMarkerId(marker.id);
                        setHoveredGpsClusterKey(clusterKey);
                      }}
                      onMouseLeave={() => {
                        setHoveredMarkerId(null);
                        setHoveredGpsClusterKey(null);
                      }}
                      onClick={(e) => {
                        e.stopPropagation();
                        setPinnedGpsClusterKey((prev) => (prev === clusterKey ? null : clusterKey));
                      }}
                    >
                      <div
                        className="relative flex items-center justify-center"
                        style={{ filter: 'drop-shadow(0 0 6px rgba(0,0,0,0.9))' }}
                      >
                        <div className="relative flex items-center justify-center h-8 w-8">
                          {/* Anel pulsante de atividade */}
                          <div className="absolute h-5 w-5 rounded-full bg-red-500/40 animate-ping" />
                          {/* Círculo vermelho com borda branca (estilo mapa in-game do SCUM) */}
                          <div
                            className="h-4 w-4 rounded-full border-2 border-white bg-red-600"
                            style={{
                              boxShadow: '0 0 8px rgba(220, 38, 38, 0.8)',
                            }}
                          />
                        </div>

                        {shouldShowClusterPopover && clusterMembers.length > 0 && (
                          <div
                            className="absolute bottom-full left-1/2 mb-2 w-[220px] -translate-x-1/2 rounded-lg bg-black/90 px-2 py-2 text-xs font-semibold text-white shadow-lg border border-white/20 z-20"
                            style={{
                              filter: 'drop-shadow(0 4px 6px rgba(0,0,0,0.5))',
                            }}
                            onClick={(e) => e.stopPropagation()}
                          >
                            <div className="mb-1 flex items-center justify-between gap-2">
                              <span className="text-[11px] font-bold text-white/80">
                                {clusterMembers.length === 1
                                  ? t('map.gps.player', 'Jogador')
                                  : t('map.gps.playersHere', {
                                      count: clusterMembers.length,
                                      defaultValue: `${clusterMembers.length} jogadores aqui`,
                                    })}
                              </span>
                              {pinnedGpsClusterKey === clusterKey ? (
                                <span className="text-[10px] font-semibold text-white/50">
                                  {t('map.gps.pinned', 'Fixado')}
                                </span>
                              ) : null}
                            </div>
                            <div className="max-h-40 overflow-auto pr-1">
                              {clusterMembers.map((name) => (
                                <div key={name} className="truncate text-white">
                                  {name}
                                </div>
                              ))}
                            </div>
                            <div
                              className="absolute top-full left-1/2 -translate-x-1/2 -mt-px border-4 border-transparent border-t-black/90"
                              style={{
                                filter: 'drop-shadow(0 2px 2px rgba(0,0,0,0.3))',
                              }}
                            />
                          </div>
                        )}
                      </div>
                    </div>
                  );
                }

                // SCUM Wiki marker
                if (marker.wiki) {
                  const isHovered = hoveredMarkerId === marker.id;
                  return (
                    <div
                      key={marker.id}
                      className="absolute"
                      style={{
                        left: `${leftPercent}%`,
                        top: `${topPercent}%`,
                        transform: 'translate(-50%, -50%)',
                        zIndex: isHovered ? 800 : 80,
                      }}
                      onMouseEnter={() => setHoveredMarkerId(marker.id)}
                      onMouseLeave={() => setHoveredMarkerId(null)}
                    >
                      <div
                        className="relative flex items-center justify-center"
                        style={{ filter: 'drop-shadow(0 0 6px rgba(0,0,0,0.8))' }}
                      >
                        <div
                          className="h-3 w-3 rounded-full border-2"
                          style={{
                            backgroundColor: marker.color,
                            borderColor: marker.borderColor,
                            boxShadow: `0 0 8px ${marker.color}80`,
                          }}
                        />

                        {isHovered && (
                          <div
                            className="absolute bottom-full left-1/2 mb-2 w-[260px] -translate-x-1/2 rounded-lg border border-white/20 bg-black/90 p-2 text-xs text-white shadow-lg"
                            style={{ pointerEvents: 'none' }}
                          >
                            <div className="text-sm font-semibold text-white">{marker.wiki.title}</div>
                          </div>
                        )}
                      </div>
                    </div>
                  );
                }

                // Flags marker
                if (marker.flag) {
                  const flagLabel = marker.label || '';
                  const isHovered = hoveredMarkerId === marker.id;
                  const hasOwner = marker.flag.owner !== 'no owner';
                  const flagColor = hasOwner ? '#22c55e' : '#ef4444';

                  const handleFlagClick = (e: React.MouseEvent) => {
                    e.preventDefault();
                    e.stopPropagation();
                    const { x, y } = marker.flag!.location;
                    const zoom = 4;
                    const scumMapUrl = `https://scum-map.com/en/shared/scum/island/${x},${y},${zoom}`;
                    window.open(scumMapUrl, '_blank', 'noopener,noreferrer');
                  };

                  return (
                    <div
                      key={marker.id}
                      className="absolute"
                      style={{
                        left: `${leftPercent}%`,
                        top: `${topPercent}%`,
                        transform: 'translate(-50%, -50%)',
                        zIndex: isHovered ? 1000 : 100,
                      }}
                      onMouseEnter={() => setHoveredMarkerId(marker.id)}
                      onMouseLeave={() => setHoveredMarkerId(null)}
                    >
                      <div
                        className="relative flex items-center justify-center cursor-pointer"
                        style={{ filter: 'drop-shadow(0 0 6px rgba(0,0,0,0.9))' }}
                        onClick={handleFlagClick}
                      >
                        <svg
                          width="32"
                          height="32"
                          viewBox="0 0 24 24"
                          fill="none"
                          xmlns="http://www.w3.org/2000/svg"
                        >
                          <line
                            x1="4"
                            y1="4"
                            x2="4"
                            y2="20"
                            stroke="#ffffff"
                            strokeWidth="2"
                            strokeLinecap="round"
                          />
                          <path
                            d="M 4 4 L 18 8 L 4 12 Z"
                            fill={flagColor}
                            stroke="#ffffff"
                            strokeWidth="1.5"
                            strokeLinejoin="round"
                          />
                        </svg>

                        {isHovered && flagLabel && (
                          <div className="absolute left-1/2 top-full mt-2 -translate-x-1/2 whitespace-nowrap rounded-lg bg-black/90 px-2 py-1 text-xs font-semibold text-white shadow-lg border border-white/20 pointer-events-none">
                            {flagLabel}
                          </div>
                        )}
                      </div>
                    </div>
                  );
                }

                // Marcador padrão (baús ou manual)
                return (
                  <div
                    key={marker.id}
                    className="pointer-events-none absolute z-10"
                    style={{
                      left: `${leftPercent}%`,
                      top: `${topPercent}%`,
                      transform: 'translate(-50%, -50%)',
                    }}
                  >
                    <div className="relative h-4 w-4" style={{ filter: 'drop-shadow(0 0 6px rgba(0,0,0,0.6))' }}>
                      {marker.pulse ? (
                        <div
                          className="absolute inset-0 animate-ping rounded-full opacity-75"
                          style={{ backgroundColor: marker.color }}
                        />
                      ) : null}
                      <div
                        className="relative h-full w-full rounded-full border-2"
                        style={{
                          backgroundColor: marker.color,
                          borderColor: marker.borderColor,
                          boxShadow: `0 0 10px ${marker.color}80`,
                        }}
                      />
                    </div>
                  </div>
                );
              })}
            </div>
          </div>

          {mapInfo && (
            <div className="card mt-4 p-4">
              <h3 className="mb-3 text-md font-semibold text-white">{t('home.map.info.title')}</h3>
              <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
                <div className="rounded-lg border border-white/10 bg-black/30 p-3">
                  <div className="mb-1 text-xs text-white/70">{t('home.map.info.gameCoords')}</div>
                  <div className="text-sm font-mono text-white">
                    X: {mapInfo.gameCoords.x.toFixed(2)}
                    <br />
                    Y: {mapInfo.gameCoords.y.toFixed(2)}
                  </div>
                </div>
                <div className="rounded-lg border border-white/10 bg-black/30 p-3">
                  <div className="mb-1 text-xs text-white/70">{t('home.map.info.mapPixels')}</div>
                  <div className="text-sm font-mono text-white">
                    X: {mapInfo.pixelCoords.x.toFixed(2)}px
                    <br />
                    Y: {mapInfo.pixelCoords.y.toFixed(2)}px
                  </div>
                </div>
                <div className="rounded-lg border border-white/10 bg-black/30 p-3">
                  <div className="mb-1 text-xs text-white/70">{t('home.map.info.quadrant')}</div>
                  <div className="inline-block rounded-full border border-scum-accent/30 bg-scum-accent/20 px-4 py-2 text-lg font-bold text-scum-accent">
                    {mapInfo.quadrant}
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>

        {isChestsActive && (
          <div className="card p-3 sm:p-4">
            <div className="mb-3">
              <h3 className="text-lg font-semibold text-white">
                {t('map.chests.vehicleList.title')}
              </h3>
              <p className="text-sm text-white/60">
                {t('map.chests.vehicleList.description')}
              </p>
            </div>

            {chestsLoading ? (
              <div className="rounded-lg border border-white/10 bg-black/30 px-3 py-3 text-sm text-white/60">
                {t('map.chests.loading')}
              </div>
            ) : vehicleStoredTotal === 0 ? (
              <div className="rounded-lg border border-white/10 bg-black/30 px-3 py-4 text-center text-sm text-white/50">
                {t('map.chests.vehicleList.empty')}
              </div>
            ) : (
              <div className="rounded-lg border border-white/10 bg-black/25 px-3 py-3 text-sm text-white/80">
                <div className="flex items-center justify-between gap-2">
                  <span className="font-semibold text-white">
                    {t('map.chests.vehicleList.totalTitle')}
                  </span>
                  <span className="inline-flex items-center rounded-full border border-white/10 bg-black/30 px-2 py-0.5 text-xs text-white/70">
                    {t('map.chests.vehicleList.totalCount', {
                      count: vehicleStoredTotal,
                    })}
                  </span>
                </div>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

