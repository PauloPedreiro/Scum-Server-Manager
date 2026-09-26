## API de Survival Stats (Frontend)

### Visão Geral

- **Fonte**: snapshot `survival_stats_snapshot` criado pelo `SurvivalStatsSyncService` no `SSM.db`.
- **Atualização**: configurada em `survival_sync` (padrão a cada 30 minutos). Pode ser forçada manualmente (`service.sync_once()`).
- **Identidade**: cada linha traz `steam_id`, `player_name`, `user_profile_id` e todas as métricas brutas do SCUM.
- **Endpoints principais**:
  - `GET /api/survival/leaderboard`: ranking por métrica (sobrevivência, kills, crafting etc.).
  - `GET /api/survival/player/{id}`: detalhe completo de um jogador (aceita `steam_id` ou `user_profile_id`).

---

### 1. `GET /api/survival/leaderboard`

**Query params**

| Parâmetro | Tipo | Default | Descrição |
| --- | --- | --- | --- |
| `metric` | `string` | `minutes_survived` | Métrica numérica para ordenar o ranking. Ex.: `kills`, `animals_killed`, `puppets_killed`, `minutes_survived`, `shots_fired`, `distance_travelled_by_foot`, `longest_kill_distance`. |
| `limit` | `number` | `20` | Máximo de registros (1 a 100). |
| `offset` | `number` | `0` | Deslocamento para paginação. |

**Resposta de exemplo**

```json
{
  "success": true,
  "data": {
    "metric": "minutes_survived",
    "available_metrics": [
      "animals_killed",
      "kills",
      "minutes_survived",
      "puppets_killed",
      "shots_fired",
      "shots_hit"
    ],
    "players": [
      {
        "position": 1,
        "steam_id": "76561198040636105",
        "player_name": "Pedreiro",
        "user_profile_id": 1,
        "value": 9394.02,
        "kills": 226,
        "deaths": 37,
        "kdr": 6.11,
        "animals_killed": 221,
        "puppets_killed": 221,
        "longest_kill_distance": 101.12,
        "shots_fired": 19410,
        "shots_hit": 451,
        "accuracy_percent": 2.32,
        "headshots": 240,
        "snapshot_at": "2025-11-07T03:07:46.731047"
      }
    ],
    "total": 366,
    "limit": 20,
    "offset": 0,
    "count": 1
  },
  "timestamp": 1730958467.7130435
}
```

### 2. `GET /api/survival/player/{identifier}`

- `identifier`: pode ser `steam_id` (`7656...`) ou `user_profile_id` (inteiro do SCUM).

**Resposta de exemplo**

```json
{
  "success": true,
  "data": {
    "steam_id": "76561198040636105",
    "player_name": "Pedreiro",
    "user_profile_id": 1,
    "snapshot_at": "2025-11-07T03:07:46.731047",
    "metrics": {
      "highest_positive_fame_points": 5000.0,
      "minutes_survived": 9394.0224609375,
      "kills": 226,
      "deaths": 37,
      "animals_killed": 221,
      "puppets_killed": 221,
      "longest_kill_distance": 101.12427520751953,
      "shots_fired": 19410,
      "shots_hit": 451,
      "headshots": 240,
      "distance_travelled_by_foot": 160496.234375,
      "distance_travelled_in_vehicle": 505139.90625,
      "food_eaten": 13.770502090454102,
      "liquid_drank": 6.931460857391357,
      "wounds_patched": 5437,
      "locks_picked": 17,
      "boars_killed": 4,
      "wolves_killed": 10,
      "firearm_kills": 35
      // ... demais campos numéricos do snapshot
    },
    "derived": {
      "kdr": 6.11,
      "accuracy_percent": 2.32
    }
  },
  "timestamp": 1730958467.7130435
}
```

---

### Interfaces TypeScript Sugeridas

```ts
export interface SurvivalLeaderboardPlayer {
  position: number;
  steam_id: string | null;
  player_name: string | null;
  user_profile_id: number | null;
  value: number;
  kills: number;
  deaths: number;
  kdr: number;
  animals_killed: number;
  puppets_killed: number;
  longest_kill_distance: number | null;
  shots_fired: number;
  shots_hit: number;
  accuracy_percent: number | null;
  headshots: number;
  snapshot_at: string | null;
}

export interface SurvivalLeaderboardResponse {
  success: true;
  data: {
    metric: string;
    available_metrics: string[];
    players: SurvivalLeaderboardPlayer[];
    total: number;
    limit: number;
    offset: number;
    count: number;
  };
  timestamp: number;
}

export interface SurvivalPlayerDetailResponse {
  success: true;
  data: {
    steam_id: string | null;
    player_name: string | null;
    user_profile_id: number | null;
    snapshot_at: string | null;
    metrics: Record<string, number>;
    derived: {
      kdr: number;
      accuracy_percent: number | null;
    };
  };
  timestamp: number;
}
```

### Hooks React (exemplo com React Query)

```ts
export function useSurvivalLeaderboard(options?: { metric?: string; limit?: number; offset?: number }) {
  return useQuery({
    queryKey: ['survival', 'leaderboard', options],
    queryFn: async () => {
      const url = new URL('/api/survival/leaderboard', window.location.origin);
      Object.entries(options ?? {}).forEach(([key, value]) => {
        if (value !== undefined && value !== null && value !== '') {
          url.searchParams.append(key, String(value));
        }
      });
      const res = await fetch(url.toString());
      if (!res.ok) throw new Error('Falha ao carregar leaderboard de survival');
      return (await res.json()) as SurvivalLeaderboardResponse;
    },
    staleTime: 60_000,
  });
}

export function useSurvivalPlayer(identifier?: string) {
  return useQuery({
    queryKey: ['survival', 'player', identifier],
    enabled: Boolean(identifier),
    queryFn: async () => {
      const res = await fetch(`/api/survival/player/${identifier}`);
      if (!res.ok) throw new Error('Jogador não encontrado');
      return (await res.json()) as SurvivalPlayerDetailResponse;
    },
    staleTime: 60_000,
  });
}
```

### UX & Visualizações Sugeridas

- **Ranking**: tabela com coluna dinâmica (métrica escolhida), colunas auxiliares (kills, mortes, kdr, accuracy, animais, puppets).
- **Filtros**: permitir usuário trocar métrica no frontend (combo com `available_metrics`).
- **Detalhe jogador**: painel com cards (Combate, Sobrevivência, Mobilidade, Crafting). Mostrar KDR, accuracy, distâncias, consumo.
- **Badges**: destaque para eventos curiosos (`times_mauled_by_bear`, `teeth_lost`, `heart_attacks`).
- **Integração**: link cruzado com kill logs, squads, fishing stats usando `steam_id`.

### Considerações

- Se o snapshot ainda não existir, os endpoints retornam erro 500 indicando ausência da tabela (execute `SurvivalStatsSyncService.sync_once()`).
- Valores são acumulativos desde o início do servidor (dados originais do SCUM).
- Para métricas percentuais, o backend já retorna KDR e accuracy; outras podem ser calculadas no frontend conforme necessidade.

---

Última atualização: **07/11/2025** • Status: ✅ Implementado e Testado


