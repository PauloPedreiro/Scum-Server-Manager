## API de Squads (Frontend)

### Visão Geral

- **Objetivo**: disponibilizar para o frontend os dados de squads e seus membros vindos do SCUM, já processados e armazenados no `SSM.db`.
- **Fonte dos dados**: snapshots atualizados pelo serviço `SquadSyncService`.
- **Formato das respostas**: JSON com estrutura pronta para uso em listas, rankings e telas de detalhes.
- **Paginação**: endpoints suportam `limit` e `offset` (padrão 50 / 0).
- **Filtros principais**: `min_score`, `name`, `event_type`, etc.
- **Atualização dos dados**: configurada em `config.json` (`squad_sync.sync_interval_minutes`, padrão 30 min).

### Endpoints Disponíveis

| Método | Endpoint | Descrição |
| --- | --- | --- |
| `GET` | `/api/squads` | Lista completa de squads disponíveis |
| `GET` | `/api/squads/ranking` | Ranking de squads com score, limite e quantidade de membros |
| `GET` | `/api/squads/{squad_id}` | Detalhes completos do squad + membros |
| `GET` | `/api/squads/{squad_id}/members` | Listagem paginada de membros (útil p/ scroll infinito) |
| `GET` | `/api/flags` | Lista todas as bandeiras do mapa com localizações e owners |

---

### 1. `GET /api/squads`

Lista todos os squads disponíveis no snapshot atual. Não possui paginação (sempre retorna o conjunto completo).

**Resposta de exemplo**

```json
{
  "success": true,
  "data": {
    "squads": [
      {
        "snapshot_id": 12,
        "squad_id": 5,
        "name": "Fazendinha GVT",
        "message": "Onde a internet cai, mas a diversão nunca",
        "information": "",
        "emblem": "720595822739195935",
        "score": 4510.61,
        "member_limit": 10,
        "member_count": 8,
        "last_member_login_time": "2025-10-31T00:02:58.907Z",
        "last_member_logout_time": "2025-10-31T00:58:54.721Z",
        "rank_position": 1,
        "snapshot_at": "2025-11-07T01:41:00.635179",
        "flag_count": 4
      }
    ],
    "total": 64
  }
}
```

> `flag_count`: número de bandeiras/territórios atribuídos ao squad (persistido no `SSM.db` durante a sincronização).

### 2. `GET /api/squads/ranking`

**Query params**

| Parâmetro | Tipo | Default | Descrição |
| --- | --- | --- | --- |
| `limit` | `number` | 50 | Quantidade máxima |
| `offset` | `number` | 0 | Deslocamento |
| `min_score` | `number` | - | Filtra punts >= valor |
| `name` | `string` | - | Filtro `LIKE` case-insensitive |

**Resposta de exemplo**

```json
{
  "success": true,
  "data": {
    "squads": [
      {
        "snapshot_id": 12,
        "squad_id": 5,
        "name": "Fazendinha GVT",
        "message": "Onde a internet cai, mas a diversão nunca",
        "information": "",
        "emblem": "720595822739195935",
        "score": 4510.61,
        "member_limit": 10,
        "member_count": 8,
        "last_member_login_time": "2025-10-31T00:02:58.907Z",
        "last_member_logout_time": "2025-10-31T00:58:54.721Z",
        "rank_position": 1,
        "snapshot_at": "2025-11-07T01:41:00.635179",
        "flag_count": 4
      }
    ],
    "total": 64,
    "limit": 50,
    "offset": 0,
    "count": 1
  }
}
```

### 3. `GET /api/squads/{squad_id}`

**Resposta de exemplo**

```json
{
  "success": true,
  "data": {
    "snapshot_id": 12,
    "squad_id": 5,
    "name": "Fazendinha GVT",
    "message": "Onde a internet cai, mas a diversão nunca",
    "information": "",
    "emblem": "720595822739195935",
    "score": 4510.61,
    "member_limit": 10,
    "member_count": 8,
    "last_member_login_time": "2025-10-31T00:02:58.907Z",
    "last_member_logout_time": "2025-10-31T00:58:54.721Z",
    "rank_position": 1,
        "snapshot_at": "2025-11-07T01:41:00.635179",
        "flag_count": 4,
    "members": [
      {
        "snapshot_member_id": 201,
        "squad_member_id": 463,
        "user_profile_id": 38,
        "steam_id": "76561198040636105",
        "name": "Pedreiro",
        "rank": 4,
        "fame_points": 1234.5,
        "last_login_time": "2025-10-30T11:15:00Z",
        "last_logout_time": "2025-10-30T12:01:00Z",
        "play_time": 9823
      }
    ]
  }
}
```

### 4. `GET /api/squads/{squad_id}/members`

**Query params**

| Parâmetro | Tipo | Default | Descrição |
| --- | --- | --- | --- |
| `limit` | `number` | 50 | Quantidade |
| `offset` | `number` | 0 | Deslocamento |

**Resposta de exemplo**

```json
{
  "success": true,
  "data": {
    "squad_id": 5,
    "squad_name": "Fazendinha GVT",
    "members": [
      {
        "snapshot_member_id": 201,
        "squad_member_id": 463,
        "user_profile_id": 38,
        "steam_id": "76561198040636105",
        "name": "Pedreiro",
        "rank": 4,
        "fame_points": 1234.5,
        "last_login_time": "2025-10-30T11:15:00Z",
        "last_logout_time": "2025-10-30T12:01:00Z",
        "play_time": 9823
      }
    ],
    "total": 8,
    "limit": 50,
    "offset": 0,
    "count": 1
  }
}
```

---

### Interfaces TypeScript (sugestão)

```ts
export interface SquadSummary {
  snapshot_id: number;
  squad_id: number;
  name: string;
  message: string | null;
  information: string | null;
  emblem: string | null;
  score: number | null;
  member_limit: number | null;
  member_count: number;
  flag_count: number;
  last_member_login_time: string | null;
  last_member_logout_time: string | null;
  rank_position: number | null;
  snapshot_at: string;
}

export interface SquadMember {
  snapshot_member_id: number;
  squad_member_id: number;
  user_profile_id: number | null;
  steam_id: string | null;
  name: string;
  rank: number | null;
  fame_points: number | null;
  last_login_time: string | null;
  last_logout_time: string | null;
  play_time: number | null;
}

export interface SquadDetail extends SquadSummary {
  members: SquadMember[];
}

export interface SquadRankingResponse {
  success: true;
  data: {
    squads: SquadSummary[];
    total: number;
    limit: number | null;
    offset: number;
    count: number;
  };
}

export interface SquadDetailResponse {
  success: true;
  data: SquadDetail;
}

export interface SquadMembersResponse {
  success: true;
  data: {
    squad_id: number;
    squad_name: string;
    members: SquadMember[];
    total: number;
    limit: number;
    offset: number;
    count: number;
  };
}
```

### Hooks React (exemplo)

```ts
import { useQuery } from '@tanstack/react-query';

export function useSquadRanking(params?: { limit?: number; offset?: number; min_score?: number; name?: string }) {
  return useQuery({
    queryKey: ['squads', 'ranking', params],
    queryFn: async () => {
      const url = new URL('/api/squads/ranking', window.location.origin);
      Object.entries(params || {}).forEach(([key, value]) => {
        if (value !== undefined && value !== null && value !== '') {
          url.searchParams.append(key, String(value));
        }
      });
      const res = await fetch(url.toString());
      if (!res.ok) throw new Error('Falha ao carregar ranking');
      return (await res.json()) as SquadRankingResponse;
    },
    staleTime: 60_000,
  });
}

export function useSquadDetail(squadId?: number) {
  return useQuery({
    queryKey: ['squads', squadId],
    enabled: Boolean(squadId),
    queryFn: async () => {
      const res = await fetch(`/api/squads/${squadId}`);
      if (!res.ok) throw new Error('Squad não encontrado');
      return (await res.json()) as SquadDetailResponse;
    },
    staleTime: 60_000,
  });
}

export function useSquadMembers(squadId?: number, params?: { limit?: number; offset?: number }) {
  return useQuery({
    queryKey: ['squads', squadId, 'members', params],
    enabled: Boolean(squadId),
    queryFn: async () => {
      const url = new URL(`/api/squads/${squadId}/members`, window.location.origin);
      Object.entries(params || {}).forEach(([key, value]) => {
        if (value !== undefined && value !== null) {
          url.searchParams.append(key, String(value));
        }
      });
      const res = await fetch(url.toString());
      if (!res.ok) throw new Error('Falha ao carregar membros');
      return (await res.json()) as SquadMembersResponse;
    },
    keepPreviousData: true,
  });
}
```

### 5. `GET /api/flags`

Lista todas as bandeiras (flags) do mapa com suas localizações e informações de proprietário. Dados consultados diretamente do `SCUM.db` em tempo real.

**Query params**: não suportados.

**Resposta de exemplo**

```json
{
  "success": true,
  "data": {
    "flags": [
      {
        "element_id": 2,
        "location": {
          "x": 501103.75,
          "y": -228677.21875,
          "z": 5156.22802734375
        },
        "base": {
          "id": 3,
          "name": "Base #3",
          "location": {
            "x": 501103.75,
            "y": -228677.21875
          }
        },
        "owner": "NomeJogador (76561198040636105) - Squad: NomeSquad",
        "owner_profile_id": 304,
        "owner_steam_id": "76561198040636105",
        "owner_name": "NomeJogador",
        "squad_id": 5,
        "squad_name": "NomeSquad",
        "overtake_end_time": null,
        "overtaker_user_profile_id": null
      },
      {
        "element_id": 16569,
        "location": {
          "x": 121548.92,
          "y": -92814.97,
          "z": 12345.67
        },
        "base": {
          "id": 49,
          "name": "Base #49",
          "location": {
            "x": 121548.92,
            "y": -92814.97
          }
        },
        "owner": "no owner",
        "owner_profile_id": null,
        "owner_steam_id": null,
        "owner_name": null,
        "squad_id": null,
        "squad_name": null,
        "overtake_end_time": null,
        "overtaker_user_profile_id": null
      }
    ],
    "total": 75,
    "with_owner": 56,
    "no_owner": 19
  }
}
```

**Campos importantes**:
- `location`: Coordenadas (x, y, z) da bandeira no mapa
- `base`: Informações da base associada (pode ser `null`)
- `owner`: String formatada com owner ou `"no owner"` quando não houver proprietário
- `squad_id` / `squad_name`: Informações do squad do owner (quando disponível)

**Uso com React Query**:

```typescript
function useFlags() {
  return useQuery({
    queryKey: ['flags'],
    queryFn: async () => {
      const res = await fetch('/api/flags');
      if (!res.ok) throw new Error('Erro ao buscar bandeiras');
      return res.json();
    },
    refetchInterval: 30000, // Atualizar a cada 30 segundos
  });
}

// Filtrar bandeiras sem owner
const { data } = useFlags();
const noOwnerFlags = data?.data.flags.filter(f => f.owner === "no owner") || [];

// Filtrar bandeiras de um squad específico
const squadFlags = data?.data.flags.filter(f => f.squad_id === 5) || [];
```

> **Nota**: Este endpoint é complementar ao sistema de squads. Use `/api/squads` para ver a contagem total de bandeiras por squad (`flag_count`) e `/api/flags` para visualizar cada bandeira individualmente no mapa.

### Tratamento de Estados

- **Nenhum squad cadastrado**: backend retorna `total: 0`, basta checar `data.squads.length`.
- **Detalhe inexistente**: resposta 404 com `{ success: false, error: "Squad X não encontrado" }`. Tratar via `try/catch`.
- **Snapshot desatualizado**: `snapshot_at` indica horário da última sincronização. Exibir tag “Atualizado há …”.
- **Paginação infinita**: use `offset += limit` com `useInfiniteQuery` ou scroll manual.

### Roadmap para Frontend

1. Criar página de ranking (grid ou tabela) consumindo `/api/squads/ranking`.
2. Ao clicar em um squad, abrir modal/página `/api/squads/{id}` com resumo + lista inicial de membros.
3. Para listas longas, usar `/api/squads/{id}/members` com paginação incremental.
4. Exibir selo com `rank_position` (🥇, 🥈, 🥉) e barra de progresso com `score`.
5. Destacar membros pelo `rank` e `fame_points` (ícones diferentes por patente).
6. Mostrar o `steam_id` do membro (quando disponível) para linkar com demais módulos (ex.: players, kill logs, inventário).

### Monitoramento

- Endpoint auxiliar (backend) em construção: `/api/squad-sync/status` (futuro). Por enquanto, monitore via logs.
- Em caso de ausência de dados, verificar se `squad_sync.enabled` está `true` e logs não acusam erro de conexão com `SCUM.db`.

### Resiliência & Manutenção

- O `SquadSyncService` recria automaticamente as tabelas `squad_snapshot` e `squad_member_snapshot` se o `SSM.db` for apagado ou estiver vazio.
- Sempre que roda, o serviço limpa os snapshots e repopula tudo a partir do `SCUM.db` (incluindo `steam_id` de cada membro quando encontrado).
- A coluna `player_steam_id` é atualizada tanto pelos dados do SCUM quanto, como fallback, pela tabela `players` do `SSM.db`.

---

Última atualização: **XX/01/2025** • Status: ✅ Implementado e Testado

**Novo**: Endpoint `/api/flags` adicionado para listar todas as bandeiras do mapa com localizações.


