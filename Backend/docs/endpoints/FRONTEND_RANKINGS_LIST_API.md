## API de Rankings - Lista Completa (Frontend)

### Visão Geral

- **Objetivo**: disponibilizar uma lista completa de todos os jogadores com todos os dados de ranking para criar uma página de ranking interativa no frontend.
- **Fonte dos dados**: tabela `rankings` do `SSM.db`, atualizada periodicamente pelo `RankingsUpdateService`.
- **Formato das respostas**: JSON com estrutura otimizada para tabelas/listagens com ordenação dinâmica.
- **Paginação**: suporta `limit` e `offset` (padrão 50 / 0, máximo 200).
- **Ordenação dinâmica**: permite ordenar por qualquer coluna (kills, deaths, kdr, total_fame, minutes_survived, etc.).
- **Busca**: filtro por nome do jogador (busca parcial, case-insensitive).
- **Atualização dos dados**: configurada em `config.json` (serviço de atualização de rankings).

---

### Endpoint Principal

| Método | Endpoint | Descrição |
| --- | --- | --- |
| `GET` | `/api/rankings/list` | Lista completa de jogadores com todos os rankings |

---

### 1. `GET /api/rankings/list`

**Query Params**

| Parâmetro | Tipo | Default | Descrição | Valores Aceitos |
| --- | --- | --- | --- | --- |
| `limit` | `number` | `50` | Número máximo de registros | 1-200 |
| `offset` | `number` | `0` | Deslocamento para paginação | >= 0 |
| `sort_by` | `string` | `kills` | Campo de ordenação | Ver lista abaixo |
| `sort_order` | `string` | `desc` | Direção da ordenação | `asc` ou `desc` |
| `search` | `string` | - | Buscar por nome do jogador | Qualquer texto |

**Campos de Ordenação (`sort_by`)**

### Combat Stats
- `kills` - Total de kills
- `deaths` - Total de deaths
- `kdr` - Kill/Death Ratio
- `longest_shot` ou `longest_shot_distance` - Maior distância de tiro
- `suicides` - Total de suicídios
- `headshots` - Total de headshots

### Lockpicking Stats
- `lockpick_basic_rate` - Taxa de sucesso lockpick básico
- `lockpick_medium_rate` - Taxa de sucesso lockpick médio
- `lockpick_advanced_rate` - Taxa de sucesso lockpick avançado
- `lockpick_veryeasy_rate` - Taxa de sucesso lockpick muito fácil
- `lockpick_diallock_rate` - Taxa de sucesso lockpick diallock

### Survival Stats
- `vehicles_destroyed` - Veículos destruídos
- `highest_defecation` ou `defecation` - Maior defecação
- `animals_killed` ou `hunting` - Animais mortos
- `players_knocked_out` ou `melee` - Nocautes em jogadores
- `minutes_survived` ou `survival_time` - Minutos sobrevividos
- `overdoses` - Total de overdoses
- `highest_weight_carried` ou `weight` - Maior peso carregado
- `total_fame` ou `fame` - Total de fama

### Outros
- `player_name` - Nome do jogador (ordem alfabética)
- `last_updated` - Data da última atualização

**Resposta de Exemplo**

```json
{
  "success": true,
  "data": {
    "players": [
      {
        "rank": 1,
        "steam_id": "76561198777583030",
        "player_name": "ADM Guns",
        
        "kills": 150,
        "deaths": 25,
        "kdr": 6.0,
        "longest_shot": {
          "distance": 125.50,
          "weapon": "Weapon_AK47_C",
          "timestamp": "2025-01-15 14:30:00"
        },
        "suicides": 3,
        "headshots": 142,
        
        "lockpicking": {
          "basic": {
            "success": 45,
            "fails": 12,
            "total": 57,
            "rate": 78.95
          },
          "medium": {
            "success": 30,
            "fails": 8,
            "total": 38,
            "rate": 78.95
          },
          "advanced": {
            "success": 20,
            "fails": 5,
            "total": 25,
            "rate": 80.0
          },
          "veryeasy": {
            "success": 10,
            "fails": 2,
            "total": 12,
            "rate": 83.33
          },
          "diallock": {
            "success": 5,
            "fails": 1,
            "total": 6,
            "rate": 83.33
          },
          "other": {
            "success": 0,
            "fails": 0,
            "total": 0,
            "rate": 0.0
          }
        },
        
        "vehicles_destroyed": 5,
        "highest_defecation": 250,
        "animals_killed": 87,
        "players_knocked_out": 23,
        "minutes_survived": 5000.5,
        "overdoses": 8,
        "highest_weight_carried": 45.7,
        "total_fame": 234.79837,
        
        "last_updated": "2025-12-02 03:00:00"
      }
    ],
    "pagination": {
      "total": 150,
      "limit": 50,
      "offset": 0,
      "count": 50,
      "has_more": true
    },
    "sorting": {
      "sort_by": "kills",
      "sort_order": "desc",
      "order_column": "kills"
    },
    "search": null
  },
  "timestamp": 1701504000
}
```

**Resposta de Erro (400 Bad Request)**

```json
{
  "success": false,
  "error": "Campo de ordenação inválido: invalid_field. Campos disponíveis: kills, deaths, kdr, ..."
}
```

---

### Interfaces TypeScript Sugeridas

```typescript
export interface LongestShot {
  distance: number;
  weapon: string | null;
  timestamp: string | null;
}

export interface LockpickStats {
  success: number;
  fails: number;
  total: number;
  rate: number;
}

export interface LockpickingStats {
  basic: LockpickStats;
  medium: LockpickStats;
  advanced: LockpickStats;
  veryeasy: LockpickStats;
  diallock: LockpickStats;
  other: LockpickStats;
}

export interface PlayerRanking {
  rank: number;
  steam_id: string;
  player_name: string;
  
  // Combat Stats
  kills: number;
  deaths: number;
  kdr: number;
  longest_shot: LongestShot;
  suicides: number;
  headshots: number;
  
  // Lockpicking Stats
  lockpicking: LockpickingStats;
  
  // Survival Stats
  vehicles_destroyed: number;
  highest_defecation: number;
  animals_killed: number;
  players_knocked_out: number;
  minutes_survived: number;
  overdoses: number;
  highest_weight_carried: number;
  total_fame: number;
  
  // Metadata
  last_updated: string;
}

export interface RankingsListResponse {
  success: boolean;
  data: {
    players: PlayerRanking[];
    pagination: {
      total: number;
      limit: number;
      offset: number;
      count: number;
      has_more: boolean;
    };
    sorting: {
      sort_by: string;
      sort_order: 'asc' | 'desc';
      order_column: string;
    };
    search: string | null;
  };
  timestamp: number;
}

export interface RankingsListError {
  success: false;
  error: string;
}
```

---

### Hooks React (exemplo com React Query)

```typescript
import { useQuery } from '@tanstack/react-query';

export interface RankingsListParams {
  limit?: number;
  offset?: number;
  sort_by?: string;
  sort_order?: 'asc' | 'desc';
  search?: string;
}

export function useRankingsList(params?: RankingsListParams) {
  return useQuery({
    queryKey: ['rankings', 'list', params],
    queryFn: async () => {
      const url = new URL('/api/rankings/list', window.location.origin);
      
      if (params?.limit) url.searchParams.append('limit', params.limit.toString());
      if (params?.offset) url.searchParams.append('offset', params.offset.toString());
      if (params?.sort_by) url.searchParams.append('sort_by', params.sort_by);
      if (params?.sort_order) url.searchParams.append('sort_order', params.sort_order);
      if (params?.search) url.searchParams.append('search', params.search);
      
      const res = await fetch(url.toString());
      if (!res.ok) {
        const error = await res.json();
        throw new Error(error.error || 'Falha ao carregar rankings');
      }
      return (await res.json()) as RankingsListResponse;
    },
    staleTime: 60_000, // 1 minuto
  });
}
```

---

### Implementação de Ordenação Dinâmica

**Exemplo de Componente React com Ordenação**

```typescript
import { useState } from 'react';
import { useRankingsList } from './hooks/useRankingsList';

type SortField = 'kills' | 'deaths' | 'kdr' | 'total_fame' | 'minutes_survived' | 'longest_shot';
type SortOrder = 'asc' | 'desc';

export function RankingsTable() {
  const [sorting, setSorting] = useState<{
    sort_by: SortField;
    sort_order: SortOrder;
  }>({
    sort_by: 'kills',
    sort_order: 'desc',
  });
  
  const [page, setPage] = useState(0);
  const [search, setSearch] = useState('');
  const limit = 50;
  
  const { data, isLoading, error } = useRankingsList({
    limit,
    offset: page * limit,
    sort_by: sorting.sort_by,
    sort_order: sorting.sort_order,
    search: search || undefined,
  });
  
  const handleColumnClick = (column: SortField) => {
    setSorting(prev => {
      // Se já está ordenado por esta coluna, alterna direção
      if (prev.sort_by === column) {
        return {
          sort_by: column,
          sort_order: prev.sort_order === 'desc' ? 'asc' : 'desc',
        };
      }
      // Senão, ordena por esta coluna em ordem decrescente
      return {
        sort_by: column,
        sort_order: 'desc',
      };
    });
    setPage(0); // Reset para primeira página ao mudar ordenação
  };
  
  const getSortIcon = (column: SortField) => {
    if (sorting.sort_by !== column) return '↕️';
    return sorting.sort_order === 'desc' ? '↓' : '↑';
  };
  
  if (isLoading) return <div>Carregando...</div>;
  if (error) return <div>Erro: {error.message}</div>;
  if (!data?.data) return <div>Nenhum dado disponível</div>;
  
  return (
    <div>
      {/* Busca */}
      <input
        type="text"
        placeholder="Buscar por nome..."
        value={search}
        onChange={(e) => {
          setSearch(e.target.value);
          setPage(0);
        }}
      />
      
      {/* Tabela */}
      <table>
        <thead>
          <tr>
            <th>Rank</th>
            <th>Nome</th>
            <th onClick={() => handleColumnClick('kills')}>
              Kills {getSortIcon('kills')}
            </th>
            <th onClick={() => handleColumnClick('deaths')}>
              Deaths {getSortIcon('deaths')}
            </th>
            <th onClick={() => handleColumnClick('kdr')}>
              KDR {getSortIcon('kdr')}
            </th>
            <th onClick={() => handleColumnClick('total_fame')}>
              Fama {getSortIcon('total_fame')}
            </th>
            <th onClick={() => handleColumnClick('minutes_survived')}>
              Minutos Sobrevividos {getSortIcon('minutes_survived')}
            </th>
          </tr>
        </thead>
        <tbody>
          {data.data.players.map((player) => (
            <tr key={player.steam_id}>
              <td>{player.rank}</td>
              <td>{player.player_name}</td>
              <td>{player.kills}</td>
              <td>{player.deaths}</td>
              <td>{player.kdr.toFixed(2)}</td>
              <td>{player.total_fame.toFixed(2)}</td>
              <td>{Math.floor(player.minutes_survived)}</td>
            </tr>
          ))}
        </tbody>
      </table>
      
      {/* Paginação */}
      <div>
        <button
          disabled={page === 0}
          onClick={() => setPage(p => p - 1)}
        >
          Anterior
        </button>
        <span>
          Página {page + 1} de {Math.ceil(data.data.pagination.total / limit)}
        </span>
        <button
          disabled={!data.data.pagination.has_more}
          onClick={() => setPage(p => p + 1)}
        >
          Próxima
        </button>
      </div>
    </div>
  );
}
```

---

### Exemplos de Uso

**1. Buscar Top 20 por Kills**
```typescript
const { data } = useRankingsList({
  limit: 20,
  sort_by: 'kills',
  sort_order: 'desc',
});
```

**2. Buscar Top 10 por Fama**
```typescript
const { data } = useRankingsList({
  limit: 10,
  sort_by: 'fame',
  sort_order: 'desc',
});
```

**3. Buscar Jogador Específico**
```typescript
const { data } = useRankingsList({
  search: 'ADM',
  limit: 10,
});
```

**4. Ordenar por Minutos Sobrevividos**
```typescript
const { data } = useRankingsList({
  sort_by: 'survival_time',
  sort_order: 'desc',
  limit: 50,
});
```

**5. Paginação**
```typescript
const page = 2;
const limit = 25;
const { data } = useRankingsList({
  limit,
  offset: page * limit,
  sort_by: 'kills',
});
```

---

### Mapeamento de Campos para Ordenação

Alguns campos aceitam nomes alternativos para facilitar o uso:

| Nome Alternativo | Campo Real |
| --- | --- |
| `fame` | `total_fame` |
| `survival_time` | `minutes_survived` |
| `defecation` | `highest_defecation` |
| `hunting` | `animals_killed` |
| `melee` | `players_knocked_out` |
| `weight` | `highest_weight_carried` |
| `longest_shot_distance` | `longest_shot_distance` |

---

### UX & Visualizações Sugeridas

- **Tabela de Rankings**: 
  - Colunas clicáveis para ordenação
  - Indicadores visuais de ordenação (setas ↑↓)
  - Highlight da coluna ativa
  - Alternância asc/desc ao clicar na mesma coluna

- **Filtros e Busca**:
  - Campo de busca por nome (busca parcial)
  - Filtros por categoria (combat, survival, lockpicking)
  - Reset de filtros

- **Paginação**:
  - Navegação anterior/próxima
  - Indicador de página atual
  - Total de páginas
  - Jump para página específica (opcional)

- **Detalhes do Jogador**:
  - Modal ou página de detalhes ao clicar no jogador
  - Mostrar todas as estatísticas agrupadas por categoria
  - Gráficos de progresso (opcional)

- **Performance**:
  - Loading states durante carregamento
  - Skeleton loaders para melhor UX
  - Debounce na busca (aguardar 300-500ms após parar de digitar)

---

### Tratamento de Erros

```typescript
const { data, error, isLoading } = useRankingsList(params);

if (error) {
  // Erro de rede ou servidor
  if (error.message.includes('Campo de ordenação inválido')) {
    // Campo de ordenação não existe
    console.error('Campo inválido:', error.message);
  } else {
    // Outro erro
    console.error('Erro ao carregar rankings:', error);
  }
}
```

---

### Considerações Importantes

1. **Paginação**: Use `limit` e `offset` para paginar grandes listas. O campo `has_more` indica se há mais registros.

2. **Ordenação**: O campo `sort_by` aceita nomes alternativos (ex: `fame` = `total_fame`). Consulte a lista completa acima.

3. **Busca**: A busca é case-insensitive e usa `LIKE` (busca parcial). Ex: buscar "ADM" encontrará "ADM Guns", "Admin", etc.

4. **Rank**: O campo `rank` é calculado baseado no `offset` atual. Se você está na página 2 (offset=50), o primeiro jogador terá rank 51.

5. **Valores Nulos**: Campos numéricos podem ser `0` se o jogador não tiver dados. Campos de texto podem ser `null`.

6. **Performance**: Índices no banco garantem ordenação rápida. Para grandes volumes, use paginação adequada.

7. **Atualização**: Os dados são atualizados periodicamente pelo serviço de rankings. O campo `last_updated` indica quando os dados foram atualizados pela última vez.

---

### Integração com Outros Endpoints

Este endpoint pode ser combinado com outros endpoints para funcionalidades mais avançadas:

- **`GET /api/rankings/player/{steam_id}`**: Detalhes completos de um jogador específico
- **`GET /api/players/fame`**: Lista de jogadores com fama (pode ser usado para comparação)
- **`GET /api/survival/leaderboard`**: Leaderboard de survival stats

---

### Exemplo Completo: Página de Rankings

```typescript
import { useState } from 'react';
import { useRankingsList } from './hooks/useRankingsList';

export function RankingsPage() {
  const [filters, setFilters] = useState({
    sort_by: 'kills' as string,
    sort_order: 'desc' as 'asc' | 'desc',
    search: '',
    page: 0,
  });
  
  const limit = 50;
  
  const { data, isLoading, error } = useRankingsList({
    limit,
    offset: filters.page * limit,
    sort_by: filters.sort_by,
    sort_order: filters.sort_order,
    search: filters.search || undefined,
  });
  
  const handleSort = (column: string) => {
    setFilters(prev => ({
      ...prev,
      sort_by: column,
      sort_order: prev.sort_by === column && prev.sort_order === 'desc' 
        ? 'asc' 
        : 'desc',
      page: 0,
    }));
  };
  
  return (
    <div className="rankings-page">
      <h1>Rankings dos Jogadores</h1>
      
      {/* Busca */}
      <div className="search-bar">
        <input
          type="text"
          placeholder="Buscar jogador..."
          value={filters.search}
          onChange={(e) => setFilters(prev => ({ ...prev, search: e.target.value, page: 0 }))}
        />
      </div>
      
      {/* Tabela */}
      {isLoading ? (
        <div>Carregando...</div>
      ) : error ? (
        <div>Erro: {error.message}</div>
      ) : data?.data ? (
        <>
          <table className="rankings-table">
            <thead>
              <tr>
                <th>Rank</th>
                <th onClick={() => handleSort('player_name')}>
                  Nome {filters.sort_by === 'player_name' && (filters.sort_order === 'desc' ? '↓' : '↑')}
                </th>
                <th onClick={() => handleSort('kills')}>
                  Kills {filters.sort_by === 'kills' && (filters.sort_order === 'desc' ? '↓' : '↑')}
                </th>
                <th onClick={() => handleSort('deaths')}>
                  Deaths {filters.sort_by === 'deaths' && (filters.sort_order === 'desc' ? '↓' : '↑')}
                </th>
                <th onClick={() => handleSort('kdr')}>
                  KDR {filters.sort_by === 'kdr' && (filters.sort_order === 'desc' ? '↓' : '↑')}
                </th>
                <th onClick={() => handleSort('total_fame')}>
                  Fama {filters.sort_by === 'total_fame' && (filters.sort_order === 'desc' ? '↓' : '↑')}
                </th>
                <th onClick={() => handleSort('minutes_survived')}>
                  Minutos {filters.sort_by === 'minutes_survived' && (filters.sort_order === 'desc' ? '↓' : '↑')}
                </th>
              </tr>
            </thead>
            <tbody>
              {data.data.players.map((player) => (
                <tr key={player.steam_id}>
                  <td>{player.rank}</td>
                  <td>{player.player_name}</td>
                  <td>{player.kills}</td>
                  <td>{player.deaths}</td>
                  <td>{player.kdr.toFixed(2)}</td>
                  <td>{player.total_fame.toFixed(2)}</td>
                  <td>{Math.floor(player.minutes_survived)}</td>
                </tr>
              ))}
            </tbody>
          </table>
          
          {/* Paginação */}
          <div className="pagination">
            <button
              disabled={filters.page === 0}
              onClick={() => setFilters(prev => ({ ...prev, page: prev.page - 1 }))}
            >
              Anterior
            </button>
            <span>
              Página {filters.page + 1} de {Math.ceil(data.data.pagination.total / limit)}
              {' '}({data.data.pagination.total} jogadores)
            </span>
            <button
              disabled={!data.data.pagination.has_more}
              onClick={() => setFilters(prev => ({ ...prev, page: prev.page + 1 }))}
            >
              Próxima
            </button>
          </div>
        </>
      ) : null}
    </div>
  );
}
```

---

Última atualização: **02/12/2025** • Status: ✅ Implementado e Testado

