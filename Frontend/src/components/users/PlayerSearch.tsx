import { useState, useEffect, useRef } from 'react';
import { useTranslation } from 'react-i18next';
import { Search, Loader2, X } from 'lucide-react';
import { getAllPlayers, type AllPlayer } from '@/services/server';

interface PlayerSearchProps {
  value?: string;
  onChange: (steamId: string | undefined) => void;
  onPlayerSelect?: (player: AllPlayer) => void;
}

export default function PlayerSearch({ value, onChange, onPlayerSelect }: PlayerSearchProps) {
  const { t } = useTranslation();
  const [query, setQuery] = useState('');
  const [results, setResults] = useState<AllPlayer[]>([]);
  const [loading, setLoading] = useState(false);
  const [showResults, setShowResults] = useState(false);
  const [selectedPlayer, setSelectedPlayer] = useState<AllPlayer | null>(null);
  const searchTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const [initialized, setInitialized] = useState(false);
  const lastValueRef = useRef<string | undefined>(undefined);

  // Fechar resultados ao clicar fora
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (containerRef.current && !containerRef.current.contains(event.target as Node)) {
        setShowResults(false);
      }
    };

    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  // Buscar players com debounce
  useEffect(() => {
    if (searchTimeoutRef.current) {
      clearTimeout(searchTimeoutRef.current);
    }

    if (selectedPlayer && query === selectedPlayer.steam_id) {
      setResults([]);
      setShowResults(false);
      return;
    }

    if (query.length < 2) {
      setResults([]);
      setShowResults(false);
      return;
    }

    searchTimeoutRef.current = setTimeout(async () => {
      setLoading(true);
      try {
        // Buscar até 500 players (mesmo limite usado na página de Players)
        const response = await getAllPlayers(500, 0);
        
        if (response.success && response.data?.players) {
          const queryLower = query.toLowerCase().trim();
          
          // Filtrar players localmente por nome ou steam_id
          const filtered = response.data.players.filter((player) => {
            const nameMatch = player.player_name?.toLowerCase().includes(queryLower);
            const steamIdMatch = player.steam_id?.includes(queryLower);
            return nameMatch || steamIdMatch;
          });

          // Limitar a 10 resultados para exibição
          setResults(filtered.slice(0, 10));
          setShowResults(true);
        } else {
          setResults([]);
        }
      } catch (error: any) {
        console.error('Erro ao buscar players:', error);
        setResults([]);
      } finally {
        setLoading(false);
      }
    }, 500);

    return () => {
      if (searchTimeoutRef.current) {
        clearTimeout(searchTimeoutRef.current);
      }
    };
  }, [query]);

  const handleSelectPlayer = (player: AllPlayer) => {
    console.log('PlayerSearch - Player selecionado:', player);
    setSelectedPlayer(player);
    // Mostrar Steam ID no campo, não o nome
    setQuery(player.steam_id);
    setResults([]);
    setShowResults(false);
    onChange(player.steam_id);
    if (onPlayerSelect) {
      onPlayerSelect(player);
    }
  };

  const handleClear = () => {
    setQuery('');
    setSelectedPlayer(null);
    setResults([]);
    setShowResults(false);
    setInitialized(false);
    onChange(undefined);
  };

  // Inicializar com o valor do Steam ID se fornecido
  useEffect(() => {
    console.log('PlayerSearch - value mudou:', { value, lastValue: lastValueRef.current, currentQuery: query });
    
    // Se o value mudou, reinicializar
    if (value !== lastValueRef.current) {
      lastValueRef.current = value;
      
      if (value) {
        console.log('PlayerSearch - Inicializando/Atualizando com Steam ID:', value);
        // Buscar o player pelo Steam ID para manter referência, mas mostrar o Steam ID no campo
        const loadPlayerBySteamId = async () => {
          try {
            const response = await getAllPlayers(500, 0);
            if (response.success && response.data?.players) {
              const player = response.data.players.find(p => p.steam_id === value);
              console.log('PlayerSearch - Player encontrado:', player);
              if (player) {
                setSelectedPlayer(player);
                // Mostrar Steam ID no campo, não o nome
                setQuery(value);
              } else {
                // Se não encontrou, usar o Steam ID
                setQuery(value);
                setSelectedPlayer(null);
              }
            } else {
              setQuery(value);
              setSelectedPlayer(null);
            }
          } catch (error) {
            console.error('Erro ao carregar player:', error);
            setQuery(value);
            setSelectedPlayer(null);
          }
          setInitialized(true);
        };
        loadPlayerBySteamId();
      } else {
        // Se o value foi removido, limpar
        console.log('PlayerSearch - Limpando (value removido)');
        setQuery('');
        setSelectedPlayer(null);
        setInitialized(false);
      }
    }
  }, [value]);

  return (
    <div ref={containerRef} className="relative w-full">
      <div className="relative">
        <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-white/50" size={18} />
        <input
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onFocus={() => query.length >= 2 && results.length > 0 && setShowResults(true)}
          placeholder={t('settings.users.playerSearch.placeholder')}
          className="w-full pl-10 pr-10 py-2 bg-white/5 border border-white/10 rounded-lg text-white placeholder-white/50 focus:outline-none focus:ring-2 focus:ring-scum-orange focus:border-transparent text-sm sm:text-base"
        />
        {loading && (
          <Loader2 className="absolute right-3 top-1/2 transform -translate-y-1/2 text-white/50 animate-spin" size={18} />
        )}
        {selectedPlayer && !loading && (
          <button
            onClick={handleClear}
            className="absolute right-3 top-1/2 transform -translate-y-1/2 text-white/50 hover:text-white"
            type="button"
          >
            <X size={18} />
          </button>
        )}
      </div>

      {showResults && results.length > 0 && (
        <div className="absolute z-50 w-full mt-2 bg-scum-panel border border-white/10 rounded-lg shadow-lg max-h-48 sm:max-h-60 overflow-y-auto">
          {results.map((player) => (
            <button
              key={player.steam_id}
              onClick={() => handleSelectPlayer(player)}
              className="w-full px-3 sm:px-4 py-2 text-left hover:bg-white/5 transition-colors border-b border-white/5 last:border-b-0"
              type="button"
            >
              <div className="text-white font-medium text-sm sm:text-base truncate">{player.player_name || 'Sem nome'}</div>
              <div className="text-white/60 text-xs sm:text-sm truncate">{player.steam_id}</div>
            </button>
          ))}
        </div>
      )}

      {showResults && query.length >= 2 && !loading && results.length === 0 && (
        <div className="absolute z-50 w-full mt-2 bg-scum-panel border border-white/10 rounded-lg shadow-lg p-4 text-white/60 text-center">
          {t('settings.users.playerSearch.noResults')}
        </div>
      )}
    </div>
  );
}

