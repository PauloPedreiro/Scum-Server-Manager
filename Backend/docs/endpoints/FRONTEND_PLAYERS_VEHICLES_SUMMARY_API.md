## Documentação `/api/players/vehicles/summary` (Frontend)

### Visão Geral
- **Objetivo**: entregar ao frontend um resumo leve da quantidade de veículos por jogador, alinhado com a mesma paginação do `/api/players`.
- **Fonte dos dados**: tabela `players` no `SSM.db` + tabela `vehicle_current_ownership` (LogProcessor).
- **Sincronização**: os dados refletem a última coleta do LogProcessor; alterações em veículos aparecem aqui ao próximo processamento de logs.
- **Uso recomendado**: invocar em paralelo com `/api/players`, utilizando os mesmos parâmetros `limit` e `offset` para montar colunas de veículos sem carregar detalhes completos.

---

### Endpoint
| Método | URL | Autenticação | Cache Recomendado |
| --- | --- | --- | --- |
| `GET` | `/api/players/vehicles/summary` | não | até 30 segundos (dados mudam em lotes) |

#### Requisição
- **Headers**: nenhum obrigatório.
- **Query params**:
  - `limit` *(number, opcional, padrão `100` — intervalo permitido `1` a `1000`)*
  - `offset` *(number, opcional, padrão `0`, mínimo `0`)*
  - `steam_id` *(string, opcional)* — retorna apenas o resumo do jogador informado (útil para buscas pontuais ou atualização parcial de tabela).
  - `sort_by` *(string, opcional, padrão `last_seen`)* — campo de ordenação. Mesmos valores aceitos em `/api/players` (`last_seen`, `first_seen`, `player_name`, `total_playtime`, `total_sessions`, `created_at`, `vehicles_total`).
  - `sort_order` *(string, opcional, padrão `desc`)* — direção da ordenação (`asc` ou `desc`).

Exemplo (`fetch`):
```ts
const response = await fetch('/api/players/vehicles/summary?limit=100&offset=0');
const json = await response.json();
```

---

### Resposta (`200 OK`)

```json
{
  "success": true,
  "data": {
    "limit": 100,
    "offset": 0,
    "total": 317,
    "count": 100,
    "sort_by": "last_seen",
    "sort_order": "desc",
    "summaries": [
      {
        "steam_id": "76561198040636105",
        "player_id": 230,
        "total": 4,
        "by_status": {
          "0": 3,
          "1": 1,
          "2": 0,
          "3": 0
        },
        "updated_at": "2025-11-10T01:30:00Z"
      }
    ]
  }
}
```

#### Campos
- `success`: indica sucesso da chamada.
- `data.limit` / `data.offset`: ecoam os parâmetros utilizados (ou os padrões aplicados pelo backend).
- `data.total`: total de jogadores encontrados (equivale ao `/api/players`).
- `data.count`: quantidade de itens presentes em `summaries` na página atual.
- `data.summaries`: array com um item por jogador da página consultada.
  - `steam_id`: identificador do jogador.
  - `player_id`: identificador interno do jogador no banco de dados (opcionalmente exibido no frontend).
  - `total`: quantidade total de veículos associados ao jogador.
  - `by_status`: contagem por status (chaves `0` até `3`). Os códigos significam:
    - `0`: Ativo
    - `1`: Inativo
    - `2`: Desaparecido
    - `3`: Destruído
  - `updated_at`: último `last_ownership_change` registrado para qualquer veículo do jogador (pode ser `null` se não houver veículos).

---

### Tratamento de Erros
| Status | Estrutura | Quando acontece | Ação recomendada |
| --- | --- | --- | --- |
| `500` | `{ "success": false, "error": "mensagem" }` | Falha ao acessar o `SSM.db` ou o banco de veículos do LogProcessor | Exibir toast "Não foi possível carregar resumo de veículos" e sugerir recarregar |

---

### Recomendações para o Frontend
- **Chamada paralela**: faça `Promise.all([getAllPlayers(), getPlayersVehicleSummary(limit, offset)])` para preencher a tabela num único ciclo de render.
- **Associação**: use `steam_id` como chave ao unir os dados do resumo com os dados principais dos players.
- **Fallbacks**:
  - Quando `total` for `0`, exiba `0` na coluna e mantenha indicadores por status zerados.
  - Se `updated_at` for `null`, mostre "--" ou um placeholder discreto.
- **Paginação sincronizada**: mantenha `limit` e `offset` idênticos aos usados em `/api/players` para garantir correspondência linha a linha.
- **Polling**: se houver atualização automática da lista de players, reutilize a mesma cadência para o resumo (ex.: a cada 15 s) evitando sombrear dados antigos.

---

### Exemplo de Integração (React/TypeScript + React Query)
```ts
import { useQuery } from '@tanstack/react-query';

interface VehicleSummary {
  steam_id: string;
  player_id: number;
  total: number;
  by_status: Record<'0' | '1' | '2' | '3', number>;
  updated_at: string | null;
}

interface VehiclesSummaryResponse {
  success: boolean;
  data: {
    limit: number;
    offset: number;
    total: number;
    count: number;
    sort_by: string;
    sort_order: 'asc' | 'desc';
    summaries: VehicleSummary[];
  };
}

interface FetchSummaryParams {
  limit: number;
  offset: number;
  sortBy?: string;
  sortOrder?: 'asc' | 'desc';
}

async function fetchVehicleSummary({ limit, offset, sortBy, sortOrder }: FetchSummaryParams) {
  const search = new URLSearchParams({
    limit: String(limit),
    offset: String(offset),
  });

  if (sortBy) search.set('sort_by', sortBy);
  if (sortOrder) search.set('sort_order', sortOrder);

  const res = await fetch(`/api/players/vehicles/summary?${search.toString()}`);
  const json: VehiclesSummaryResponse = await res.json();
  if (!json.success) throw new Error(json.error ?? 'Erro ao carregar resumo de veículos');
  return json.data;
}

export function useVehicleSummary(limit: number, offset: number, sortBy?: string, sortOrder: 'asc' | 'desc' = 'desc') {
  return useQuery({
    queryKey: ['players-vehicles-summary', limit, offset, sortBy, sortOrder],
    queryFn: () => fetchVehicleSummary({ limit, offset, sortBy, sortOrder }),
    staleTime: 30_000,
  });
}
```

---

### Checklist para Entrega
- [ ] Endpoint configurado no cliente HTTP (`server.ts`).
- [ ] Hook/query reutiliza os mesmos `