## API de Baús (Frontend)

### Visão Geral

- **Objetivo**: disponibilizar para o frontend os dados consolidados dos baús sincronizados do SCUM, permitindo filtros por jogador e uso em mapas.
- **Fonte dos dados**: tabela `chest_snapshot` abastecida periodicamente pelo `ChestSyncService` (SCUM → SSM.db).
- **Formato das respostas**: JSON pronto para uso, com campos de localização, nomes e metadados de veículo quando aplicável.
- **Atualização dos dados**: configurada via `data/config.json` (`chest_sync.sync_interval_minutes`, padrão 30 minutos).
- **Privacidade**: os endpoints retornam o `steam_id` do proprietário para uso administrativo, mas os embeds do Discord ocultam essa informação.

### Endpoints Disponíveis

| Método | Endpoint | Descrição |
| --- | --- | --- |
| `GET` | `/api/chests` | Lista todos os baús do snapshot com suporte a filtros básicos e resumo por jogador |
| `GET` | `/api/chests/player/{steam_id}` | Lista apenas os baús vinculados ao Steam ID informado |

---

### 1. `GET /api/chests`

**Query params**

| Parâmetro | Tipo | Default | Descrição |
| --- | --- | --- | --- |
| `steam_id` | `string` | - | Filtra os baús vinculados ao jogador informado |
| `limit` | `number` | - | Quantidade máxima de registros (1 a 1000) |
| `offset` | `number` | 0 | Deslocamento para paginação (usado com `limit`) |
| `minimal` | `boolean` | `false` | Retorna apenas campos essenciais (útil para mapas) |
| `disable_summary` | `boolean` | `false` | Oculta a seção `players` (resumo por dono) |

**Resposta de exemplo**

```json
{
  "success": true,
  "data": {
    "count": 2,
    "chests": [
      {
        "entity_id": 11965144,
        "container_entity_id": null,
        "owner_profile_id": 42,
        "steam_id": "76561198040636105",
        "player_name": "Pedreiro",
        "fake_name": "BL",
        "custom_name": "Base Sul",
        "chest_class": "Improvised_Metal_Chest_ES",
        "chest_type": "Metal",
        "location": {
          "x": -117459.62,
          "y": -122890.77,
          "z": 37164.78
        },
        "rotation": {
          "x": 0.0,
          "y": 90.0,
          "z": 0.0
        },
        "vehicle_owner_mismatch": false,
        "vehicle": null,
        "last_seen_at": "2025-11-08T14:23:12",
        "created_at": "2025-11-08T13:55:01",
        "has_vehicle": false
      },
      {
        "entity_id": 11890001,
        "container_entity_id": 16240176,
        "owner_profile_id": 58,
        "steam_id": "76561198845263299",
        "player_name": "Salotes",
        "fake_name": null,
        "custom_name": null,
        "chest_class": "Improvised_Metal_Chest_ES",
        "chest_type": "Metal",
        "location": {
          "x": -615149.88,
          "y": -554526.0,
          "z": 2319.33
        },
        "rotation": {
          "x": 0.0,
          "y": 0.0,
          "z": 0.0
        },
        "vehicle_owner_mismatch": false,
        "vehicle": {
          "entity_id": 15612640,
          "class": "Wolfswagen_ES",
          "container_class": "Wolfswagen_Item_Container_ES",
          "owner_name": "Salotes",
          "owner_steam_id": "76561198845263299",
          "owner_player_id": 7561,
          "registered_at": "2025-11-08T13:19:44"
        },
        "last_seen_at": "2025-11-08T13:20:02",
        "created_at": "2025-11-08T12:48:55",
        "has_vehicle": true
      }
    ],
    "players": [
      {
        "steam_id": "76561198040636105",
        "count": 1,
        "player_name": "Pedreiro",
        "fake_name": "BL"
      },
      {
        "steam_id": "76561198845263299",
        "count": 1,
        "player_name": "Salotes",
        "fake_name": null
      }
    ],
    "limit": 100,
    "offset": 0,
    "total": 2
  },
  "timestamp": 1731075800.123
}
```

> Use o parâmetro `minimal=true` quando precisar apenas de `entity_id`, `steam_id`, `player_name`, `fake_name`, `chest_type`, `location` e `last_seen_at`.

---

### 2. `GET /api/chests/player/{steam_id}`

**Descrição**

Retorna todos os baús vinculados a um jogador específico, incluindo contagem por tipo e nomes conhecidos (player/fake).

**Resposta de exemplo**

```json
{
  "success": true,
  "data": {
    "steam_id": "76561198040636105",
    "count": 2,
    "type_counts": {
      "Metal": 2
    },
    "player_names": ["Pedreiro"],
    "fake_names": ["BL"],
    "chests": [
      {
        "entity_id": 11965144,
        "container_entity_id": null,
        "owner_profile_id": 42,
        "steam_id": "76561198040636105",
        "player_name": "Pedreiro",
        "fake_name": "BL",
        "custom_name": "Base Sul",
        "chest_class": "Improvised_Metal_Chest_ES",
        "chest_type": "Metal",
        "location": {
          "x": -117459.62,
          "y": -122890.77,
          "z": 37164.78
        },
        "rotation": {
          "x": 0.0,
          "y": 90.0,
          "z": 0.0
        },
        "vehicle_owner_mismatch": false,
        "vehicle": null,
        "last_seen_at": "2025-11-08T14:23:12",
        "created_at": "2025-11-08T13:55:01",
        "has_vehicle": false
      }
    ]
  },
  "timestamp": 1731075800.123
}
```

---

### Interfaces TypeScript (sugestão)

```ts
export interface ChestLocation {
  x: number | null;
  y: number | null;
  z: number | null;
}

export interface ChestRotation {
  x: number | null;
  y: number | null;
  z: number | null;
}

export interface ChestVehicleInfo {
  entity_id: number | null;
  class: string | null;
  container_class: string | null;
  owner_name: string | null;
  owner_steam_id: string | null;
  owner_player_id: number | null;
  registered_at: string | null;
}

export interface ChestSnapshot {
  entity_id: number;
  container_entity_id: number | null;
  owner_profile_id: number | null;
  steam_id: string | null;
  player_name: string | null;
  fake_name: string | null;
  custom_name: string | null;
  chest_class: string | null;
  chest_type: string;
  location: ChestLocation;
  rotation: ChestRotation;
  vehicle_owner_mismatch: boolean;
  vehicle: ChestVehicleInfo | null;
  last_seen_at: string;
  created_at: string;
  has_vehicle: boolean;
}

export interface ChestPlayerSummary {
  steam_id: string | null;
  count: number;
  player_name: string | null;
  fake_name: string | null;
}

export interface ChestListResponse {
  success: true;
  data: {
    count: number;
    chests: ChestSnapshot[];
    players?: ChestPlayerSummary[];
    limit?: number;
    offset?: number;
    total?: number;
  };
  timestamp: number;
}

export interface PlayerChestResponse {
  success: true;
  data: {
    steam_id: string;
    count: number;
    type_counts: Record<string, number>;
    player_names: string[];
    fake_names: string[];
    chests: ChestSnapshot[];
  };
  timestamp: number;
}
```

---

### Dicas de Uso no Frontend

- Use `GET /api/chests?minimal=true` para carregar rapidamente marcadores de mapa (retorna apenas campos essenciais).
- O resumo `players` ajuda a montar filtros de seleção rápida (quantidade de baús por jogador).
- Combine o endpoint geral com o específico por jogador para exibir detalhes ou dashboards por proprietário.

