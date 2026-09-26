# 🚗 API de Veículos por Player - Documentação Frontend

## 📋 Visão Geral

Esta documentação descreve os endpoints da API para consulta de veículos vinculados a players, incluindo filtros por status e agrupamento. Os endpoints permitem:

- Listar veículos de um player específico filtrados por status
- Listar todos os players com seus respectivos veículos
- Filtrar por status (Ativo, Inativo, Desaparecido, Destruído)
- Agrupar veículos por status

---

## 🌐 Base URL

```
http://localhost:3000/api
```

**⚠️ Nota:** Em produção, substitua `localhost:3000` pela URL do servidor backend.

---

## 📊 Status dos Veículos

Antes de usar os endpoints, é importante entender os status disponíveis:

| Status | Valor | Descrição |
|--------|-------|-----------|
| **Ativo** | `0` | Veículo está ativo e em uso |
| **Inativo** | `1` | Veículo inativo (VehicleInactiveTimerReached) |
| **Desaparecido** | `2` | Veículo desapareceu do servidor |
| **Destruído** | `3` | Veículo foi destruído |

---

## 🔌 Endpoints Disponíveis

### 1. Listar Veículos de um Player por Status

Obtém todos os veículos de um player específico, com opção de filtrar por status.

#### **Endpoint**
```
GET /api/vehicles/player/:steam_id/by-status
```

#### **Parâmetros**

##### Path Parameters
| Parâmetro | Tipo | Obrigatório | Descrição |
|-----------|------|-------------|-----------|
| `steam_id` | `string` | ✅ Sim | Steam ID do player (ex: `76561198040636105`) |

##### Query Parameters (Opcionais)
| Parâmetro | Tipo | Obrigatório | Descrição | Exemplo |
|-----------|------|-------------|-----------|---------|
| `status` | `string` | ❌ Não | Filtro por status. Pode ser um único valor ou múltiplos separados por vírgula | `0` ou `0,1` ou `1,2,3` |

#### **Comportamento**

- **Sem parâmetro `status`**: Retorna todos os veículos do player agrupados por status
- **Com parâmetro `status`**: Retorna apenas os veículos que correspondem ao(s) status(s) especificado(s)

#### **Resposta de Sucesso (200)**

**Sem filtro de status (agrupado):**
```json
{
  "success": true,
  "data": {
    "steam_id": "76561198040636105",
    "player_name": "Pedreiro",
    "player_id": 230,
    "summary": {
      "total_vehicles": 10,
      "by_status": {
        "0": 5,
        "1": 2,
        "2": 1,
        "3": 2
      }
    },
    "vehicles_by_status": {
      "0": [
        {
          "entity_id": 15720005,
          "vehicle_entity_id": 15720004,
          "vehicle_class": "BPC_Kinglet_Duster",
          "vehicle_class_display": "Kinglet_Duster",
          "status": 0,
          "status_text": "Ativo",
          "location_x": -616882.0,
          "location_y": -554072.0,
          "location_z": 2477.0,
          "last_ownership_change": "2025-10-31 14:29:04",
          "is_vehicle_functional": 1,
          "container_class": "Kinglet_Duster_Item_Container_ES",
          "vehicle_asset_id": "Vehicle:BPC_Kinglet_Duster",
          "notification_sent": true,
          "updated_at": "2025-10-31 14:29:04"
        }
      ],
      "1": [
        {
          "entity_id": 15850793,
          "vehicle_entity_id": 15850792,
          "vehicle_class": "BPC_WolfsWagen",
          "vehicle_class_display": "WolfsWagen",
          "status": 1,
          "status_text": "Inativo",
          "location_x": -314658.969,
          "location_y": -6662.034,
          "location_z": 35707.980,
          "last_ownership_change": "2025-10-30 10:15:22",
          "is_vehicle_functional": 0
        }
      ],
      "3": [
        {
          "entity_id": 15850795,
          "vehicle_entity_id": 15850793,
          "vehicle_class": "BPC_WolfsWagen",
          "vehicle_class_display": "WolfsWagen",
          "status": 3,
          "status_text": "Destruído",
          "location_x": -314658.969,
          "location_y": -6662.034,
          "location_z": 35707.980,
          "last_ownership_change": "2025-10-29 18:45:30"
        }
      ]
    }
  },
  "timestamp": 1760907347.523
}
```

**Com filtro de status (lista simples):**
```json
{
  "success": true,
  "data": {
    "steam_id": "76561198040636105",
    "player_name": "Pedreiro",
    "player_id": 230,
    "summary": {
      "total_vehicles": 10,
      "filtered_status": [0],
      "count": 5
    },
    "vehicles": [
      {
        "entity_id": 15720005,
        "vehicle_entity_id": 15720004,
        "vehicle_class": "BPC_Kinglet_Duster",
        "vehicle_class_display": "Kinglet_Duster",
        "status": 0,
        "status_text": "Ativo",
        "location_x": -616882.0,
        "location_y": -554072.0,
        "location_z": 2477.0,
        "last_ownership_change": "2025-10-31 14:29:04",
        "is_vehicle_functional": 1
      },
      {
        "entity_id": 15987332,
        "vehicle_entity_id": 15987331,
        "vehicle_class": "BPC_Laika",
        "vehicle_class_display": "Laika",
        "status": 0,
        "status_text": "Ativo",
        "location_x": -868534.0,
        "location_y": -177313.0,
        "location_z": 20619.0,
        "last_ownership_change": "2025-10-31 15:10:22",
        "is_vehicle_functional": 1
      }
    ]
  },
  "timestamp": 1760907347.523
}
```

#### **Resposta de Erro**

**404 - Player não encontrado:**
```json
{
  "success": false,
  "error": "Player com Steam ID 76561199999999999 não encontrado ou não possui veículos"
}
```

**400 - Status inválido:**
```json
{
  "success": false,
  "error": "Parâmetro 'status' inválido. Use valores: 0 (Ativo), 1 (Inativo), 2 (Desaparecido), 3 (Destruído) ou múltiplos separados por vírgula"
}
```

**500 - Erro interno:**
```json
{
  "success": false,
  "error": "Mensagem de erro específica"
}
```

#### **Exemplos de Uso**

```javascript
// Exemplo 1: Obter todos os veículos de um player agrupados por status
const getPlayerVehiclesGrouped = async (steamId) => {
  const response = await fetch(
    `http://localhost:3000/api/vehicles/player/${steamId}/by-status`
  );
  const data = await response.json();
  return data;
};

// Exemplo 2: Obter apenas veículos ativos de um player
const getPlayerActiveVehicles = async (steamId) => {
  const response = await fetch(
    `http://localhost:3000/api/vehicles/player/${steamId}/by-status?status=0`
  );
  const data = await response.json();
  return data;
};

// Exemplo 3: Obter veículos ativos e inativos de um player
const getPlayerActiveAndInactiveVehicles = async (steamId) => {
  const response = await fetch(
    `http://localhost:3000/api/vehicles/player/${steamId}/by-status?status=0,1`
  );
  const data = await response.json();
  return data;
};

// Exemplo 4: Obter veículos destruídos e desaparecidos
const getPlayerDestroyedAndDisappearedVehicles = async (steamId) => {
  const response = await fetch(
    `http://localhost:3000/api/vehicles/player/${steamId}/by-status?status=2,3`
  );
  const data = await response.json();
  return data;
};
```

---

### 2. Listar Todos os Players e Seus Veículos

Obtém uma lista de todos os players que possuem veículos, com opções de filtro e agrupamento.

#### **Endpoint**
```
GET /api/vehicles/players
```

#### **Query Parameters (Todos Opcionais)**

| Parâmetro | Tipo | Obrigatório | Descrição | Padrão |
|-----------|------|-------------|-----------|--------|
| `status` | `string` | ❌ Não | Filtro por status (0, 1, 2, 3 ou múltiplos separados por vírgula) | Todos |
| `group_by_status` | `boolean` | ❌ Não | Agrupar veículos por status dentro de cada player (`true`/`false`) | `false` |
| `limit` | `number` | ❌ Não | Número máximo de players a retornar (máximo: 10000) | `1000` |
| `offset` | `number` | ❌ Não | Deslocamento para paginação | `0` |

#### **Resposta de Sucesso (200)**

**Sem agrupamento:**
```json
{
  "success": true,
  "data": {
    "total_players": 15,
    "total_vehicles": 45,
    "count": 15,
    "limit": 100,
    "offset": 0,
    "players": [
      {
        "steam_id": "76561198040636105",
        "player_name": "Pedreiro",
        "player_id": 230,
        "vehicles_count": 5,
        "vehicles": [
          {
            "entity_id": 15720005,
            "vehicle_entity_id": 15720004,
            "vehicle_class": "BPC_Kinglet_Duster",
            "vehicle_class_display": "Kinglet_Duster",
            "status": 0,
            "status_text": "Ativo",
            "location_x": -616882.0,
            "location_y": -554072.0,
            "location_z": 2477.0,
            "last_ownership_change": "2025-10-31 14:29:04",
            "is_vehicle_functional": 1
          },
          {
            "entity_id": 15987332,
            "vehicle_entity_id": 15987331,
            "vehicle_class": "BPC_Laika",
            "vehicle_class_display": "Laika",
            "status": 0,
            "status_text": "Ativo",
            "location_x": -868534.0,
            "location_y": -177313.0,
            "location_z": 20619.0,
            "last_ownership_change": "2025-10-31 15:10:22",
            "is_vehicle_functional": 1
          }
        ]
      },
      {
        "steam_id": "76561199174184873",
        "player_name": "o pastor",
        "player_id": 247,
        "vehicles_count": 3,
        "vehicles": [
          {
            "entity_id": 16000123,
            "vehicle_entity_id": 16000122,
            "vehicle_class": "BPC_Tractor",
            "vehicle_class_display": "Tractor",
            "status": 0,
            "status_text": "Ativo",
            "location_x": -500000.0,
            "location_y": -300000.0,
            "location_z": 5000.0,
            "last_ownership_change": "2025-10-31 16:00:00"
          }
        ]
      }
    ]
  },
  "timestamp": 1760907347.523
}
```

**Com agrupamento (`group_by_status=true`):**
```json
{
  "success": true,
  "data": {
    "total_players": 15,
    "total_vehicles": 45,
    "players": [
      {
        "steam_id": "76561198040636105",
        "player_name": "Pedreiro",
        "player_id": 230,
        "vehicles_count": 5,
        "summary": {
          "total": 5,
          "by_status": {
            "0": 3,
            "1": 1,
            "3": 1
          }
        },
        "vehicles_by_status": {
          "0": [
            {
              "entity_id": 15720005,
              "vehicle_entity_id": 15720004,
              "vehicle_class": "BPC_Kinglet_Duster",
              "vehicle_class_display": "Kinglet_Duster",
              "status": 0,
              "status_text": "Ativo"
            }
          ],
          "1": [
            {
              "entity_id": 15850793,
              "vehicle_entity_id": 15850792,
              "vehicle_class": "BPC_WolfsWagen",
              "vehicle_class_display": "WolfsWagen",
              "status": 1,
              "status_text": "Inativo"
            }
          ],
          "3": [
            {
              "entity_id": 15850795,
              "vehicle_entity_id": 15850793,
              "vehicle_class": "BPC_WolfsWagen",
              "vehicle_class_display": "WolfsWagen",
              "status": 3,
              "status_text": "Destruído"
            }
          ]
        }
      }
    ]
  },
  "timestamp": 1760907347.523
}
```

**Com filtro de status:**
```json
{
  "success": true,
  "data": {
    "total_players": 10,
    "total_vehicles": 25,
    "count": 10,
    "limit": 100,
    "offset": 0,
    "filtered_status": [0],
    "players": [
      {
        "steam_id": "76561198040636105",
        "player_name": "Pedreiro",
        "player_id": 230,
        "vehicles_count": 3,
        "vehicles": [
          {
            "entity_id": 15720005,
            "vehicle_entity_id": 15720004,
            "vehicle_class": "BPC_Kinglet_Duster",
            "vehicle_class_display": "Kinglet_Duster",
            "status": 0,
            "status_text": "Ativo"
          }
        ]
      }
    ]
  },
  "timestamp": 1760907347.523
}
```

#### **Resposta de Erro**

**400 - Parâmetro inválido:**
```json
{
  "success": false,
  "error": "Parâmetro 'status' inválido. Use valores: 0 (Ativo), 1 (Inativo), 2 (Desaparecido), 3 (Destruído) ou múltiplos separados por vírgula"
}
```

**500 - Erro interno:**
```json
{
  "success": false,
  "error": "Mensagem de erro específica"
}
```

#### **Exemplos de Uso**

```javascript
// Exemplo 1: Listar todos os players com seus veículos
const getAllPlayersVehicles = async () => {
  const response = await fetch(
    'http://localhost:3000/api/vehicles/players?limit=100&offset=0'
  );
  const data = await response.json();
  return data;
};

// Exemplo 2: Listar apenas players com veículos ativos
const getPlayersWithActiveVehicles = async () => {
  const response = await fetch(
    'http://localhost:3000/api/vehicles/players?status=0&limit=100'
  );
  const data = await response.json();
  return data;
};

// Exemplo 3: Listar players com veículos agrupados por status
const getPlayersWithGroupedVehicles = async () => {
  const response = await fetch(
    'http://localhost:3000/api/vehicles/players?group_by_status=true'
  );
  const data = await response.json();
  return data;
};

// Exemplo 4: Paginação
const getPlayersWithPagination = async (page = 1, pageSize = 50) => {
  const offset = (page - 1) * pageSize;
  const response = await fetch(
    `http://localhost:3000/api/vehicles/players?limit=${pageSize}&offset=${offset}`
  );
  const data = await response.json();
  return data;
};

// Exemplo 5: Filtrar por múltiplos status
const getPlayersWithMultipleStatus = async () => {
  const response = await fetch(
    'http://localhost:3000/api/vehicles/players?status=0,1&group_by_status=true'
  );
  const data = await response.json();
  return data;
};
```

---

## 📦 Estruturas de Dados

### **Objeto Vehicle**

```typescript
interface Vehicle {
  entity_id: number;                    // ID único do container do veículo
  vehicle_entity_id: number;              // ID único do veículo
  vehicle_class: string;                  // Classe do veículo (ex: "BPC_Kinglet_Duster")
  vehicle_class_display: string;          // Nome formatado do veículo (ex: "Kinglet_Duster")
  status: number;                        // Status do veículo (0, 1, 2, 3)
  status_text: string;                   // Texto legível do status (ex: "Ativo")
  location_x: number;                     // Coordenada X
  location_y: number;                     // Coordenada Y
  location_z: number;                     // Coordenada Z
  last_ownership_change: string;          // Data da última mudança de propriedade (ISO 8601)
  is_vehicle_functional: number;         // 1 = funcional, 0 = não funcional
  container_class?: string;               // Classe do container
  vehicle_asset_id?: string;              // Asset ID do veículo
  notification_sent?: boolean;             // Se notificação foi enviada
  updated_at?: string;                    // Data de atualização
}
```

### **Objeto Player Summary**

```typescript
interface PlayerSummary {
  steam_id: string;                     // Steam ID do player
  player_name: string;                   // Nome do player
  player_id: number;                      // ID interno do player
  vehicles_count: number;                 // Quantidade total de veículos
  vehicles?: Vehicle[];                  // Lista de veículos (quando não agrupado)
  vehicles_by_status?: {                  // Veículos agrupados por status (quando agrupado)
    [status: string]: Vehicle[];
  };
  summary?: {
    total: number;
    by_status: {
      [status: string]: number;
    };
  };
}
```

---

## 🛠️ Exemplos de Implementação Frontend

### **React / TypeScript**

```typescript
import { useState, useEffect } from 'react';

interface VehicleStatus {
  0: 'Ativo';
  1: 'Inativo';
  2: 'Desaparecido';
  3: 'Destruído';
}

const API_BASE_URL = 'http://localhost:3000/api';

// Hook para buscar veículos de um player
export const usePlayerVehicles = (steamId: string, status?: string) => {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchVehicles = async () => {
      try {
        setLoading(true);
        const url = `${API_BASE_URL}/vehicles/player/${steamId}/by-status${
          status ? `?status=${status}` : ''
        }`;
        
        const response = await fetch(url);
        
        if (!response.ok) {
          throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const result = await response.json();
        
        if (result.success) {
          setData(result.data);
        } else {
          setError(result.error || 'Erro desconhecido');
        }
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Erro ao buscar veículos');
      } finally {
        setLoading(false);
      }
    };

    if (steamId) {
      fetchVehicles();
    }
  }, [steamId, status]);

  return { data, loading, error };
};

// Hook para buscar todos os players
export const useAllPlayersVehicles = (
  status?: string,
  groupByStatus: boolean = false,
  limit: number = 100,
  offset: number = 0
) => {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchPlayers = async () => {
      try {
        setLoading(true);
        const params = new URLSearchParams();
        
        if (status) params.append('status', status);
        if (groupByStatus) params.append('group_by_status', 'true');
        params.append('limit', limit.toString());
        params.append('offset', offset.toString());
        
        const url = `${API_BASE_URL}/vehicles/players?${params.toString()}`;
        const response = await fetch(url);
        
        if (!response.ok) {
          throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const result = await response.json();
        
        if (result.success) {
          setData(result.data);
        } else {
          setError(result.error || 'Erro desconhecido');
        }
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Erro ao buscar players');
      } finally {
        setLoading(false);
      }
    };

    fetchPlayers();
  }, [status, groupByStatus, limit, offset]);

  return { data, loading, error };
};

// Componente de exemplo
const PlayerVehiclesComponent = ({ steamId }: { steamId: string }) => {
  const [selectedStatus, setSelectedStatus] = useState<string>('');
  const { data, loading, error } = usePlayerVehicles(steamId, selectedStatus);

  if (loading) return <div>Carregando...</div>;
  if (error) return <div>Erro: {error}</div>;
  if (!data) return <div>Nenhum dado encontrado</div>;

  return (
    <div>
      <h2>Veículos de {data.player_name}</h2>
      
      <select
        value={selectedStatus}
        onChange={(e) => setSelectedStatus(e.target.value)}
      >
        <option value="">Todos</option>
        <option value="0">Ativo</option>
        <option value="1">Inativo</option>
        <option value="2">Desaparecido</option>
        <option value="3">Destruído</option>
      </select>

      {selectedStatus ? (
        // Lista simples quando há filtro
        <div>
          <p>Total: {data.summary.count} veículos</p>
          <ul>
            {data.vehicles?.map((vehicle) => (
              <li key={vehicle.entity_id}>
                {vehicle.vehicle_class_display} - {vehicle.status_text}
              </li>
            ))}
          </ul>
        </div>
      ) : (
        // Agrupado por status quando não há filtro
        <div>
          <p>Total: {data.summary.total_vehicles} veículos</p>
          {Object.entries(data.vehicles_by_status || {}).map(([status, vehicles]) => (
            <div key={status}>
              <h3>Status {status}: {vehicles.length} veículos</h3>
              <ul>
                {vehicles.map((vehicle) => (
                  <li key={vehicle.entity_id}>
                    {vehicle.vehicle_class_display} - {vehicle.status_text}
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};
```

### **Vue.js / TypeScript**

```typescript
<template>
  <div>
    <h2>Veículos de {{ playerName }}</h2>
    
    <select v-model="selectedStatus" @change="fetchVehicles">
      <option value="">Todos</option>
      <option value="0">Ativo</option>
      <option value="1">Inativo</option>
      <option value="2">Desaparecido</option>
      <option value="3">Destruído</option>
    </select>

    <div v-if="loading">Carregando...</div>
    <div v-else-if="error">Erro: {{ error }}</div>
    <div v-else>
      <p>Total: {{ summary.total }} veículos</p>
      <!-- Renderizar veículos -->
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue';

const props = defineProps<{
  steamId: string;
}>();

const selectedStatus = ref('');
const loading = ref(false);
const error = ref<string | null>(null);
const playerName = ref('');
const vehicles = ref([]);
const summary = ref({ total: 0 });

const fetchVehicles = async () => {
  loading.value = true;
  error.value = null;
  
  try {
    const url = `http://localhost:3000/api/vehicles/player/${props.steamId}/by-status${
      selectedStatus.value ? `?status=${selectedStatus.value}` : ''
    }`;
    
    const response = await fetch(url);
    const result = await response.json();
    
    if (result.success) {
      playerName.value = result.data.player_name;
      vehicles.value = result.data.vehicles || [];
      summary.value = result.data.summary;
    } else {
      error.value = result.error;
    }
  } catch (err) {
    error.value = err instanceof Error ? err.message : 'Erro desconhecido';
  } finally {
    loading.value = false;
  }
};

onMounted(() => {
  fetchVehicles();
});
</script>
```

---

## ⚠️ Tratamento de Erros

### **Códigos HTTP**

| Código | Significado | Quando Ocorre |
|--------|-------------|---------------|
| `200` | Sucesso | Requisição processada com sucesso |
| `400` | Bad Request | Parâmetros inválidos (ex: status inválido) |
| `404` | Not Found | Player não encontrado ou não possui veículos |
| `500` | Internal Server Error | Erro no servidor |

### **Estrutura de Erro**

```typescript
interface ErrorResponse {
  success: false;
  error: string;
}
```

### **Exemplo de Tratamento**

```typescript
const handleApiError = (response: Response) => {
  if (response.status === 404) {
    return 'Player não encontrado';
  }
  
  if (response.status === 400) {
    return 'Parâmetros inválidos';
  }
  
  if (response.status >= 500) {
    return 'Erro no servidor. Tente novamente mais tarde.';
  }
  
  return 'Erro desconhecido';
};

const fetchWithErrorHandling = async (url: string) => {
  try {
    const response = await fetch(url);
    
    if (!response.ok) {
      const errorMessage = handleApiError(response);
      throw new Error(errorMessage);
    }
    
    const data = await response.json();
    
    if (!data.success) {
      throw new Error(data.error || 'Erro na resposta da API');
    }
    
    return data.data;
  } catch (error) {
    console.error('Erro ao buscar dados:', error);
    throw error;
  }
};
```

---

## 💡 Boas Práticas

### **1. Cache e Paginação**

- Use paginação para listas grandes (`limit` e `offset`)
- Implemente cache local para reduzir requisições
- Considere usar `React Query`, `SWR` ou similar para cache automático

### **2. Loading States**

Sempre exiba estados de carregamento:

```typescript
if (loading) return <LoadingSpinner />;
if (error) return <ErrorMessage error={error} />;
if (!data) return <EmptyState />;
```

### **3. Validação de Dados**

Valide os dados recebidos antes de usar:

```typescript
const validateVehicle = (vehicle: any): vehicle is Vehicle => {
  return (
    vehicle &&
    typeof vehicle.entity_id === 'number' &&
    typeof vehicle.vehicle_class === 'string' &&
    [0, 1, 2, 3].includes(vehicle.status)
  );
};
```

### **4. Debounce em Filtros**

Use debounce ao filtrar em tempo real:

```typescript
import { useDebounce } from 'use-debounce';

const [statusFilter, setStatusFilter] = useState('');
const [debouncedStatus] = useDebounce(statusFilter, 300);

useEffect(() => {
  fetchVehicles(debouncedStatus);
}, [debouncedStatus]);
```

---

## 📝 Notas Importantes

1. **Formato de Nomes de Veículos**: O campo `vehicle_class_display` remove os prefixos `BPC_`, `BP_` e `_ES` para melhor legibilidade.

2. **Status em String**: Quando os veículos são agrupados por status, as chaves do objeto são strings (`"0"`, `"1"`, etc.), não números.

3. **Paginação**: O endpoint `/api/vehicles/players` tem limite máximo de 10000 players por requisição.

4. **Timestamp**: Todas as respostas incluem um campo `timestamp` com o tempo Unix da resposta.

5. **Coordenadas**: As coordenadas (`location_x`, `location_y`, `location_z`) estão no sistema de coordenadas do jogo SCUM.

---

## 🔗 Recursos Adicionais

- **Postman Collection**: Veja `docs/endpoints/postman-collection.json` para exemplos completos
- **Documentação Backend**: Consulte `docs/VEHICLE_REGISTRATION_SYSTEM.md` para detalhes técnicos
- **Status de Destruição**: Veja `docs/VEHICLE_DESTRUCTION_SYSTEM.md` para entender como os status são atualizados

---

## ✅ Checklist de Implementação

- [ ] Configurar base URL da API
- [ ] Implementar tratamento de erros
- [ ] Criar interfaces TypeScript para os dados
- [ ] Implementar estados de loading
- [ ] Adicionar paginação (se necessário)
- [ ] Implementar filtros por status
- [ ] Criar componentes para exibir veículos
- [ ] Testar todos os cenários (com e sem filtros)
- [ ] Adicionar debounce em filtros em tempo real
- [ ] Implementar cache/local storage (opcional)

---

**Última atualização**: 2025-11-01  
**Versão da API**: 1.12.0

