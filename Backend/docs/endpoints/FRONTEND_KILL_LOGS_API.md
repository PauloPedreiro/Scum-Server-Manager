# ⚔️ API de Kill Logs - Documentação Frontend

## 📋 Visão Geral

Esta documentação descreve os endpoints da API para consulta de eventos de morte/kill processados pelo sistema. O sistema monitora automaticamente os arquivos `kill_*.log` e armazena informações detalhadas sobre:

- **Mortes por NPC** (Guards, Zombies, etc.)
- **PvP Kills** (Jogador vs Jogador)
- **Suicídios**

Cada evento inclui informações sobre vítima, killer, arma, distância, localização e hora do jogo.

### 🖼️ Sistema de Imagens

O sistema utiliza um mapeamento JSON (`data/imagens/Weapons/mapping.json`) para vincular armas às suas imagens:

- **Auto-descoberta**: Novas armas são automaticamente adicionadas ao JSON com valor vazio
- **Imagens de armas**: Cada arma pode ter uma imagem específica (thumbnail no Discord)
- **Imagem de suicídio**: Eventos de suicídio usam automaticamente `Suicide.png`
- **Fallback**: Se não houver imagem mapeada, o evento é enviado sem thumbnail

Para mais detalhes sobre o sistema de imagens, consulte: `docs/KILL_LOGS_SYSTEM.md`

---

## 🌐 Base URL

```
http://localhost:3000/api
```

**⚠️ Nota:** Em produção, substitua `localhost:3000` pela URL do servidor backend.

---

## 🔌 Endpoints Disponíveis

### 📋 Listar Eventos de Kill Recentes

Retorna os últimos eventos de morte/kill processados pelo sistema.

#### **Endpoint**
```
GET /api/kill-logs/recent
```

#### **Query Parameters (Opcionais)**

| Parâmetro | Tipo | Obrigatório | Descrição | Padrão | Exemplo |
|-----------|------|-------------|-----------|--------|---------|
| `limit` | `number` | ❌ Não | Número máximo de eventos a retornar | `50` | `?limit=20` |
| `event_type` | `string` | ❌ Não | Filtrar por tipo: `kill` ou `suicide` | `null` | `?event_type=kill` |
| `victim_steam_id` | `string` | ❌ Não | Filtrar por Steam ID da vítima | `null` | `?victim_steam_id=76561198040636105` |
| `killer_steam_id` | `string` | ❌ Não | Filtrar por Steam ID do killer | `null` | `?killer_steam_id=76561198042887008` |

#### **Resposta de Sucesso (200)**

```json
{
  "success": true,
  "data": {
    "events": [
      {
        "id": 1,
        "event_type": "kill",
        "timestamp": "2025-11-01T20:37:54",
        "game_time": "16:07:13",
        "victim": {
          "steam_id": "76561198065382168",
          "player_id": 319,
          "name": "EARENDEL",
          "location": {
            "x": -59323.78,
            "y": -83752.15,
            "z": 36399.42
          }
        },
        "killer": {
          "steam_id": null,
          "user_id": "NPC",
          "profile_name": "BP_Guard_Lvl_3_C_2146864901",
          "is_npc": true,
          "location": {
            "x": -57264.25,
            "y": -82747.10,
            "z": 36356.62
          },
          "has_immortality": false
        },
        "weapon": {
          "name": "Weapon_DT11B_C",
          "type": "Projectile"
        },
        "distance": 22.92,
        "is_in_game_event": false,
        "discord_sent": true,
        "created_at": "2025-11-01T20:37:54"
      },
      {
        "id": 2,
        "event_type": "suicide",
        "timestamp": "2025-11-01T20:43:50",
        "game_time": null,
        "victim": {
          "steam_id": "76561198065382168",
          "player_id": 319,
          "name": "EARENDEL",
          "location": {
            "x": -61563.809,
            "y": 400799.875,
            "z": 146379.031
          }
        },
        "killer": null,
        "weapon": null,
        "distance": null,
        "is_in_game_event": false,
        "discord_sent": true,
        "created_at": "2025-11-01T20:43:50"
      }
    ],
    "total": 156,
    "count": 2,
    "limit": 50
  },
  "timestamp": 1730573951.523
}
```

#### **Resposta de Erro (500)**

```json
{
  "success": false,
  "error": "Erro ao consultar eventos de kill",
  "timestamp": 1730573951.523
}
```

---

### 📊 Estatísticas de Kill Logs

Obtém estatísticas detalhadas sobre eventos de kill processados.

#### **Endpoint**
```
GET /api/kill-logs/stats
```

#### **Resposta de Sucesso (200)**

```json
{
  "success": true,
  "data": {
    "total_events": 156,
    "events_today": 23,
    "events_this_week": 89,
    "events_this_month": 156,
    "by_event_type": {
      "kill": {
        "count": 142,
        "percentage": 91.0
      },
      "suicide": {
        "count": 14,
        "percentage": 9.0
      }
    },
    "by_killer_type": {
      "npc": {
        "count": 98,
        "percentage": 62.8
      },
      "player": {
        "count": 44,
        "percentage": 28.2
      }
    },
    "top_weapons": [
      {
        "weapon": "Weapon_DT11B_C",
        "count": 45,
        "percentage": 28.8
      },
      {
        "weapon": "Weapon_AS_Val_C",
        "count": 23,
        "percentage": 14.7
      }
    ],
    "top_victims": [
      {
        "steam_id": "76561198065382168",
        "name": "EARENDEL",
        "deaths": 12,
        "percentage": 7.7
      }
    ],
    "top_killers": [
      {
        "steam_id": "76561198040636105",
        "name": "Pedreiro",
        "kills": 8,
        "percentage": 5.1
      }
    ],
    "average_distance": 18.5,
    "discord_notifications_sent": 156
  },
  "timestamp": 1730573951.523
}
```

---

### 🔍 Listar Eventos com Filtros

Lista eventos de kill com filtros avançados e paginação.

#### **Endpoint**
```
GET /api/kill-logs/events
```

#### **Query Parameters (Opcionais)**

| Parâmetro | Tipo | Obrigatório | Descrição | Padrão | Exemplo |
|-----------|------|-------------|-----------|--------|---------|
| `limit` | `number` | ❌ Não | Número máximo de eventos | `50` | `?limit=20` |
| `offset` | `number` | ❌ Não | Deslocamento para paginação | `0` | `?offset=50` |
| `event_type` | `string` | ❌ Não | Filtrar por tipo: `kill` ou `suicide` | `null` | `?event_type=kill` |
| `victim_steam_id` | `string` | ❌ Não | Filtrar por Steam ID da vítima | `null` | `?victim_steam_id=76561198040636105` |
| `killer_steam_id` | `string` | ❌ Não | Filtrar por Steam ID do killer | `null` | `?killer_steam_id=76561198042887008` |
| `killer_is_npc` | `boolean` | ❌ Não | Filtrar apenas kills por NPC | `null` | `?killer_is_npc=true` |
| `weapon` | `string` | ❌ Não | Filtrar por nome da arma | `null` | `?weapon=Weapon_DT11B_C` |
| `weapon_type` | `string` | ❌ Não | Filtrar por tipo: `Projectile` ou `Melee` | `null` | `?weapon_type=Projectile` |
| `from_date` | `string` | ❌ Não | Filtrar desde data (ISO 8601) | `null` | `?from_date=2025-11-01T00:00:00` |
| `to_date` | `string` | ❌ Não | Filtrar até data (ISO 8601) | `null` | `?to_date=2025-11-02T00:00:00` |

#### **Resposta de Sucesso (200)**

```json
{
  "success": true,
  "data": {
    "events": [
      {
        "id": 1,
        "event_type": "kill",
        "timestamp": "2025-11-01T20:37:54",
        "game_time": "16:07:13",
        "victim_steam_id": "76561198065382168",
        "victim_player_id": 319,
        "victim_name": "EARENDEL",
        "victim_location_x": -59323.78,
        "victim_location_y": -83752.15,
        "victim_location_z": 36399.42,
        "killer_steam_id": null,
        "killer_user_id": "NPC",
        "killer_profile_name": "BP_Guard_Lvl_3_C_2146864901",
        "killer_is_npc": true,
        "killer_location_x": -57264.25,
        "killer_location_y": -82747.10,
        "killer_location_z": 36356.62,
        "killer_has_immortality": false,
        "weapon": "Weapon_DT11B_C",
        "weapon_type": "Projectile",
        "distance": 22.92,
        "is_in_game_event": false,
        "log_file": "kill_20251101200045.log",
        "discord_sent": true,
        "created_at": "2025-11-01T20:37:54"
      }
    ],
    "total": 156,
    "count": 1,
    "limit": 50,
    "offset": 0
  },
  "timestamp": 1730573951.523
}
```

---

## 📊 Estruturas TypeScript

### **KillEvent (Formato Aninhado - `/api/kill-logs/recent`)**

```typescript
interface KillEventNested {
  id: number;
  event_type: 'kill' | 'suicide';
  timestamp: string; // ISO 8601
  game_time: string | null; // Hora do jogo (ex: "16:07:13")
  
  // Vítima (sempre presente)
  victim: {
    steam_id: string | null;
    player_id: number | null;
    name: string;
    location: {
      x: number | null;
      y: number | null;
      z: number | null;
    };
  };
  
  // Killer (null para suicídio)
  killer: {
    steam_id: string | null;
    user_id: string | null;
    profile_name: string;
    is_npc: boolean;
    location: {
      x: number | null;
      y: number | null;
      z: number | null;
    };
    has_immortality: boolean;
  } | null;
  
  // Arma (null para suicídio)
  weapon: {
    name: string;
    type: string | null; // "Projectile" | "Melee"
  } | null;
  
  distance: number | null; // em metros
  is_in_game_event: boolean;
  discord_sent: boolean;
  created_at: string; // ISO 8601
}
```

### **KillEvent (Formato Plano - `/api/kill-logs/events`)**

```typescript
interface KillEvent {
  id: number;
  event_type: 'kill' | 'suicide';
  timestamp: string; // ISO 8601
  game_time: string | null; // Hora do jogo (ex: "16:07:13")
  
  // Vítima
  victim_steam_id: string | null;
  victim_player_id: number | null;
  victim_name: string;
  victim_location_x: number | null;
  victim_location_y: number | null;
  victim_location_z: number | null;
  
  // Killer (null para suicídio)
  killer_steam_id: string | null;
  killer_user_id: string | null;
  killer_profile_name: string | null;
  killer_is_npc: boolean;
  killer_location_x: number | null;
  killer_location_y: number | null;
  killer_location_z: number | null;
  killer_has_immortality: boolean;
  
  // Arma e combate
  weapon: string | null;
  weapon_type: string | null; // "Projectile" | "Melee"
  distance: number | null; // em metros
  
  // Contexto
  is_in_game_event: boolean;
  log_file: string;
  discord_sent: boolean;
  created_at: string; // ISO 8601
  raw_json?: string; // JSON completo do evento original
}
```

### **KillLogsStats**

```typescript
interface KillLogsStats {
  total_events: number;
  events_today: number;
  events_this_week: number;
  events_this_month: number;
  by_event_type: {
    kill: { count: number; percentage: number };
    suicide: { count: number; percentage: number };
  };
  by_killer_type: {
    npc: { count: number; percentage: number };
    player: { count: number; percentage: number };
  };
  top_weapons: Array<{
    weapon: string;
    count: number;
    percentage: number;
  }>;
  top_victims: Array<{
    steam_id: string;
    name: string;
    deaths: number;
    percentage: number;
  }>;
  top_killers: Array<{
    steam_id: string;
    name: string;
    kills: number;
    percentage: number;
  }>;
  average_distance: number;
  discord_notifications_sent: number;
}
```

### **KillLogsResponse**

#### **Resposta do endpoint `/api/kill-logs/recent`**

```typescript
interface KillLogsRecentResponse {
  success: boolean;
  data: {
    events: KillEventNested[];
    total: number;
    count: number;
    limit: number;
  };
  timestamp: number;
}
```

#### **Resposta do endpoint `/api/kill-logs/events`**

```typescript
interface KillLogsEventsResponse {
  success: boolean;
  data: {
    events: KillEvent[];
    total: number;
    count: number;
    limit: number;
    offset: number;
  };
  timestamp: number;
}
```
```

### **ErrorResponse**

```typescript
interface ErrorResponse {
  success: false;
  error: string;
  timestamp: number;
}
```

---

## 💻 Exemplos de Implementação

### **React/TypeScript**

```tsx
import React, { useState, useEffect } from 'react';

interface KillEvent {
  id: number;
  event_type: 'kill' | 'suicide';
  timestamp: string;
  game_time: string | null;
  victim: {
    steam_id: string | null;
    player_id: number | null;
    name: string;
    location: {
      x: number | null;
      y: number | null;
      z: number | null;
    };
  };
  killer: {
    steam_id: string | null;
    user_id: string | null;
    profile_name: string;
    is_npc: boolean;
    location: {
      x: number | null;
      y: number | null;
      z: number | null;
    };
    has_immortality: boolean;
  } | null;
  weapon: {
    name: string;
    type: string | null;
  } | null;
  distance: number | null;
  is_in_game_event: boolean;
  discord_sent: boolean;
  created_at: string;
}

function KillLogsList() {
  const [events, setEvents] = useState<KillEvent[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchKillLogs();
  }, []);

  const fetchKillLogs = async () => {
    try {
      setLoading(true);
      const response = await fetch('http://localhost:3000/api/kill-logs/recent?limit=20');
      const data = await response.json();

      if (data.success) {
        setEvents(data.data.events);
      } else {
        setError(data.error || 'Erro ao carregar eventos');
      }
    } catch (err) {
      setError('Erro de conexão');
    } finally {
      setLoading(false);
    }
  };

  const getEventIcon = (event: KillEvent) => {
    if (event.event_type === 'suicide') return '💀';
    if (event.killer?.is_npc) return '🤖';
    return '⚔️';
  };

  if (loading) return <div>Carregando...</div>;
  if (error) return <div>Erro: {error}</div>;

  return (
    <div className="kill-logs-list">
      <h2>Eventos de Kill Recentes</h2>
      {events.map((event) => (
        <div key={event.id} className="kill-event">
          <span className="icon">{getEventIcon(event)}</span>
          <div className="details">
            <strong>{event.victim.name}</strong>
            {event.event_type === 'kill' && event.killer && (
              <>
                {' foi morto por '}
                <strong>{event.killer.profile_name}</strong>
                {event.killer.is_npc && ' (NPC)'}
                {event.weapon && ` usando ${event.weapon.name}`}
                {event.distance && ` a ${event.distance.toFixed(2)}m`}
              </>
            )}
            {event.event_type === 'suicide' && ' cometeu suicídio'}
            <div className="timestamp">
              {new Date(event.timestamp).toLocaleString('pt-BR')}
            </div>
          </div>
        </div>
      ))}
    </div>
  );
}

export default KillLogsList;
```

### **Vue.js/TypeScript**

```vue
<template>
  <div class="kill-logs-list">
    <h2>Eventos de Kill Recentes</h2>
    <div v-if="loading">Carregando...</div>
    <div v-else-if="error" class="error">Erro: {{ error }}</div>
    <div v-else>
      <div
        v-for="event in events"
        :key="event.id"
        class="kill-event"
      >
        <span class="icon">{{ getEventIcon(event) }}</span>
        <div class="details">
          <strong>{{ event.victim.name }}</strong>
          <template v-if="event.event_type === 'kill' && event.killer">
            foi morto por
            <strong>{{ event.killer.profile_name }}</strong>
            <span v-if="event.killer.is_npc"> (NPC)</span>
            <span v-if="event.weapon"> usando {{ event.weapon.name }}</span>
            <span v-if="event.distance">
              a {{ event.distance.toFixed(2) }}m
            </span>
          </template>
          <template v-else>
            cometeu suicídio
          </template>
          <div class="timestamp">
            {{ formatDate(event.timestamp) }}
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue';

interface KillEvent {
  id: number;
  event_type: 'kill' | 'suicide';
  timestamp: string;
  game_time: string | null;
  victim: {
    steam_id: string | null;
    player_id: number | null;
    name: string;
    location: {
      x: number | null;
      y: number | null;
      z: number | null;
    };
  };
  killer: {
    steam_id: string | null;
    user_id: string | null;
    profile_name: string;
    is_npc: boolean;
    location: {
      x: number | null;
      y: number | null;
      z: number | null;
    };
    has_immortality: boolean;
  } | null;
  weapon: {
    name: string;
    type: string | null;
  } | null;
  distance: number | null;
  is_in_game_event: boolean;
  discord_sent: boolean;
  created_at: string;
}

const events = ref<KillEvent[]>([]);
const loading = ref(true);
const error = ref<string | null>(null);

const fetchKillLogs = async () => {
  try {
    loading.value = true;
    const response = await fetch('http://localhost:3000/api/kill-logs/recent?limit=20');
    const data = await response.json();

    if (data.success) {
      events.value = data.data.events;
    } else {
      error.value = data.error || 'Erro ao carregar eventos';
    }
  } catch (err) {
    error.value = 'Erro de conexão';
  } finally {
    loading.value = false;
  }
};

const getEventIcon = (event: KillEvent): string => {
  if (event.event_type === 'suicide') return '💀';
  if (event.killer?.is_npc) return '🤖';
  return '⚔️';
};

const formatDate = (timestamp: string): string => {
  return new Date(timestamp).toLocaleString('pt-BR');
};

onMounted(() => {
  fetchKillLogs();
});
</script>
```

### **JavaScript (Vanilla)**

```javascript
// Função para buscar eventos de kill
async function fetchKillLogs(limit = 50) {
  try {
    const response = await fetch(
      `http://localhost:3000/api/kill-logs/recent?limit=${limit}`
    );
    const data = await response.json();

    if (data.success) {
      return data.data.events;
    } else {
      throw new Error(data.error || 'Erro ao carregar eventos');
    }
  } catch (error) {
    console.error('Erro ao buscar kill logs:', error);
    throw error;
  }
}

// Exemplo de uso
fetchKillLogs(20)
  .then((events) => {
    console.log('Eventos encontrados:', events.length);
    events.forEach((event) => {
      if (event.event_type === 'kill' && event.killer) {
        console.log(`${event.victim.name} foi morto por ${event.killer.profile_name}`);
      } else {
        console.log(`${event.victim.name} cometeu suicídio`);
      }
    });
  })
  .catch((error) => {
    console.error('Erro:', error.message);
  });

// Função para buscar estatísticas
async function fetchKillStats() {
  try {
    const response = await fetch('http://localhost:3000/api/kill-logs/stats');
    const data = await response.json();

    if (data.success) {
      return data.data;
    } else {
      throw new Error(data.error || 'Erro ao carregar estatísticas');
    }
  } catch (error) {
    console.error('Erro ao buscar estatísticas:', error);
    throw error;
  }
}

// Exemplo de uso
fetchKillStats()
  .then((stats) => {
    console.log('Total de eventos:', stats.total_events);
    console.log('Eventos hoje:', stats.events_today);
    console.log('Top armas:', stats.top_weapons);
  })
  .catch((error) => {
    console.error('Erro:', error.message);
  });
```

---

## 🎯 Tipos de Eventos

### **Kill (Morte)**

Evento quando um jogador é morto por outro jogador ou NPC.

**Características:**
- `event_type`: `"kill"`
- Sempre tem `killer_profile_name`
- Sempre tem `weapon` e `weapon_type`
- Pode ter `distance`
- `killer_is_npc` indica se foi NPC ou jogador

**Exemplo:**
```json
{
  "event_type": "kill",
  "victim_name": "EARENDEL",
  "killer_profile_name": "BP_Guard_Lvl_3_C_2146864901",
  "killer_is_npc": true,
  "weapon": "Weapon_DT11B_C",
  "weapon_type": "Projectile",
  "distance": 22.92
}
```

### **Suicide (Suicídio)**

Evento quando um jogador comete suicídio.

**Características:**
- `event_type`: `"suicide"`
- `killer_profile_name` é `null`
- `weapon` e `weapon_type` são `null`
- `distance` é `null`

**Exemplo:**
```json
{
  "event_type": "suicide",
  "victim_name": "EARENDEL",
  "killer_profile_name": null,
  "weapon": null,
  "distance": null
}
```

---

## 📝 Boas Práticas

### **1. Caching**

Implemente cache para reduzir requisições desnecessárias:

```typescript
const CACHE_TTL = 30000; // 30 segundos
let cache: { data: KillEvent[]; timestamp: number } | null = null;

async function getCachedKillLogs() {
  const now = Date.now();
  if (cache && (now - cache.timestamp) < CACHE_TTL) {
    return cache.data;
  }

  const events = await fetchKillLogs();
  cache = { data: events, timestamp: now };
  return events;
}
```

### **2. Paginação**

Para listas grandes, use paginação:

```typescript
async function fetchKillLogsPaginated(page = 1, limit = 20) {
  const offset = (page - 1) * limit;
  const response = await fetch(
    `http://localhost:3000/api/kill-logs/events?limit=${limit}&offset=${offset}`
  );
  const data = await response.json();
  return data;
}
```

### **3. Loading States**

Sempre mostre estados de carregamento:

```typescript
const [loading, setLoading] = useState(true);
const [events, setEvents] = useState<KillEvent[]>([]);

useEffect(() => {
  setLoading(true);
  fetchKillLogs()
    .then(setEvents)
    .finally(() => setLoading(false));
}, []);
```

### **4. Error Handling**

Implemente tratamento de erros robusto:

```typescript
try {
  const events = await fetchKillLogs();
  setEvents(events);
} catch (error) {
  console.error('Erro ao carregar kill logs:', error);
  // Mostrar mensagem amigável ao usuário
  showErrorToast('Não foi possível carregar os eventos');
}
```

### **5. Filtros com Debounce**

Use debounce para filtros de busca:

```typescript
import { debounce } from 'lodash';

const debouncedSearch = debounce(async (query: string) => {
  const events = await fetchKillLogs({
    victim_name: query
  });
  setEvents(events);
}, 300);
```

### **6. Formatação de Data**

Formate datas de forma amigável:

```typescript
function formatKillTimestamp(timestamp: string): string {
  const date = new Date(timestamp);
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffMins = Math.floor(diffMs / 60000);

  if (diffMins < 1) return 'Agora mesmo';
  if (diffMins < 60) return `${diffMins} minuto(s) atrás`;
  if (diffMins < 1440) return `${Math.floor(diffMins / 60)} hora(s) atrás`;
  return date.toLocaleDateString('pt-BR');
}
```

---

## 🚀 Checklist de Implementação

- [ ] Criar componente de lista de kill logs
- [ ] Implementar paginação
- [ ] Adicionar filtros (tipo, jogador, arma)
- [ ] Implementar busca por Steam ID
- [ ] Mostrar estatísticas de kills
- [ ] Adicionar indicadores visuais (NPC vs PvP vs Suicídio)
- [ ] Implementar cache para melhor performance
- [ ] Adicionar tratamento de erros
- [ ] Implementar estados de loading
- [ ] Formatação amigável de datas
- [ ] Tooltips com informações detalhadas
- [ ] Responsividade mobile

---

## 📅 Última atualização

**Data:** 02/01/2025  
**Versão da API:** 1.13.0  
**Status:** ✅ Implementado e Testado

---

## 📚 Documentação Relacionada

- [Documentação de Admin Logs](./FRONTEND_ADMIN_LOGS_API.md)
- [Documentação de Veículos](./FRONTEND_VEHICLES_API.md)
- [Documentação Geral da API](./FRONTEND_API.md)

