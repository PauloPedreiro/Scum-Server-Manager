# 📊 Endpoint: Lista Completa de Rankings

## 🎯 Visão Geral

Endpoint para obter **todos os jogadores** com **todos os dados de ranking** para criar uma página de ranking completa no frontend. Permite ordenação dinâmica por qualquer coluna e busca por nome.

---

## 📡 Endpoint

**GET** `/api/rankings/list`

---

## 🔗 URL Base

```
http://192.168.100.3:3000/api/rankings/list
```

*(Substitua pela URL do seu ambiente de produção)*

---

## 📋 Parâmetros Query (Opcionais)

| Parâmetro | Tipo | Obrigatório | Padrão | Descrição | Valores Aceitos |
|-----------|------|-------------|--------|-----------|------------------|
| `limit` | number | Não | `50` | Número máximo de registros | 1-200 |
| `offset` | number | Não | `0` | Deslocamento para paginação | >= 0 |
| `sort_by` | string | Não | `kills` | Campo de ordenação | Ver lista abaixo |
| `sort_order` | string | Não | `desc` | Direção da ordenação | `asc` ou `desc` |
| `search` | string | Não | - | Buscar por nome do jogador | Qualquer texto |

---

## 🎯 Campos de Ordenação (`sort_by`)

### **Combat Stats**
- `kills` - Total de kills
- `deaths` - Total de deaths
- `kdr` - Kill/Death Ratio
- `longest_shot` ou `longest_shot_distance` - Maior distância de tiro
- `suicides` - Total de suicídios
- `headshots` - Total de headshots

### **Lockpicking Stats**
- `lockpick_basic_rate` - Taxa de sucesso lockpick básico
- `lockpick_medium_rate` - Taxa de sucesso lockpick médio
- `lockpick_advanced_rate` - Taxa de sucesso lockpick avançado
- `lockpick_veryeasy_rate` - Taxa de sucesso lockpick muito fácil
- `lockpick_diallock_rate` - Taxa de sucesso lockpick diallock

### **Survival Stats**
- `vehicles_destroyed` - Veículos destruídos
- `highest_defecation` ou `defecation` - Maior defecação
- `animals_killed` ou `hunting` - Animais mortos
- `players_knocked_out` ou `melee` - Nocautes em jogadores
- `minutes_survived` ou `survival_time` - Minutos sobrevividos
- `overdoses` - Total de overdoses
- `highest_weight_carried` ou `weight` - Maior peso carregado
- `total_fame` ou `fame` - Total de fama

### **Outros**
- `player_name` - Nome do jogador (ordem alfabética)
- `last_updated` - Data da última atualização

---

## 📥 Exemplo de Requisição

### **Requisição Básica**
```bash
GET /api/rankings/list
```

### **Com Ordenação**
```bash
GET /api/rankings/list?sort_by=kills&sort_order=desc
```

### **Com Paginação**
```bash
GET /api/rankings/list?limit=25&offset=0&sort_by=total_fame&sort_order=desc
```

### **Com Busca**
```bash
GET /api/rankings/list?search=ADM&sort_by=kills
```

### **Ordenar por Minutos Sobrevividos**
```bash
GET /api/rankings/list?sort_by=survival_time&sort_order=desc
```

---

## 📤 Resposta de Sucesso (200 OK)

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

---

## ❌ Resposta de Erro

### **400 Bad Request - Campo de Ordenação Inválido**

```json
{
  "success": false,
  "error": "Campo de ordenação inválido: invalid_field. Campos disponíveis: kills, deaths, kdr, ..."
}
```

### **500 Internal Server Error**

```json
{
  "success": false,
  "error": "Mensagem de erro específica"
}
```

---

## 💻 Exemplos de Uso

### **TypeScript/React**

```typescript
interface RankingsListResponse {
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

interface PlayerRanking {
  rank: number;
  steam_id: string;
  player_name: string;
  kills: number;
  deaths: number;
  kdr: number;
  longest_shot: {
    distance: number;
    weapon: string | null;
    timestamp: string | null;
  };
  suicides: number;
  headshots: number;
  lockpicking: {
    [key: string]: {
      success: number;
      fails: number;
      total: number;
      rate: number;
    };
  };
  vehicles_destroyed: number;
  highest_defecation: number;
  animals_killed: number;
  players_knocked_out: number;
  minutes_survived: number;
  overdoses: number;
  highest_weight_carried: number;
  total_fame: number;
  last_updated: string;
}

// Função para buscar rankings
async function getRankingsList(params: {
  limit?: number;
  offset?: number;
  sort_by?: string;
  sort_order?: 'asc' | 'desc';
  search?: string;
}): Promise<RankingsListResponse> {
  const queryParams = new URLSearchParams();
  
  if (params.limit) queryParams.append('limit', params.limit.toString());
  if (params.offset) queryParams.append('offset', params.offset.toString());
  if (params.sort_by) queryParams.append('sort_by', params.sort_by);
  if (params.sort_order) queryParams.append('sort_order', params.sort_order);
  if (params.search) queryParams.append('search', params.search);
  
  const response = await fetch(
    `/api/rankings/list?${queryParams.toString()}`
  );
  
  if (!response.ok) {
    throw new Error(`HTTP error! status: ${response.status}`);
  }
  
  return await response.json();
}

// Exemplo de uso
const rankings = await getRankingsList({
  limit: 50,
  offset: 0,
  sort_by: 'kills',
  sort_order: 'desc'
});
```

---

## 🔄 Ordenação Dinâmica no Frontend

### **Handler de Clique na Coluna**

```typescript
const [sorting, setSorting] = useState({
  sort_by: 'kills',
  sort_order: 'desc' as 'asc' | 'desc'
});

const handleColumnClick = (columnKey: string) => {
  const columnMap: Record<string, string> = {
    'kills': 'kills',
    'deaths': 'deaths',
    'kdr': 'kdr',
    'longest_shot': 'longest_shot',
    'survival_time': 'survival_time',
    'fame': 'fame',
    // ... outros mapeamentos
  };
  
  const sortBy = columnMap[columnKey];
  if (!sortBy) return;
  
  // Se já está ordenado por esta coluna, alterna direção
  let newSortOrder: 'asc' | 'desc' = 'desc';
  if (sorting.sort_by === sortBy) {
    newSortOrder = sorting.sort_order === 'desc' ? 'asc' : 'desc';
  }
  
  // Atualizar estado e buscar dados
  setSorting({ sort_by: sortBy, sort_order: newSortOrder });
  fetchRankings({ sort_by: sortBy, sort_order: newSortOrder, offset: 0 });
};
```

---

## 📊 Estrutura de Dados Detalhada

### **PlayerRanking Object**

```typescript
{
  rank: number;                    // Posição no ranking atual
  steam_id: string;                // Steam ID único
  player_name: string;             // Nome do jogador
  
  // Combat Stats
  kills: number;                   // Total de kills
  deaths: number;                  // Total de deaths
  kdr: number;                     // Kill/Death Ratio
  longest_shot: {                  // Tiro mais longo
    distance: number;              // Distância em metros
    weapon: string | null;        // Nome da arma
    timestamp: string | null;      // Data/hora do tiro
  };
  suicides: number;                // Total de suicídios
  headshots: number;               // Total de headshots
  
  // Lockpicking Stats (por tipo)
  lockpicking: {
    basic: { success, fails, total, rate },
    medium: { success, fails, total, rate },
    advanced: { success, fails, total, rate },
    veryeasy: { success, fails, total, rate },
    diallock: { success, fails, total, rate },
    other: { success, fails, total, rate }
  };
  
  // Survival Stats
  vehicles_destroyed: number;      // Veículos destruídos
  highest_defecation: number;      // Maior defecação
  animals_killed: number;          // Animais mortos
  players_knocked_out: number;     // Nocautes em jogadores
  minutes_survived: number;        // Minutos sobrevividos
  overdoses: number;               // Total de overdoses
  highest_weight_carried: number;  // Maior peso carregado (kg)
  total_fame: number;              // Total de fama
  
  // Metadata
  last_updated: string;            // Data/hora da última atualização
}
```

---

## 🎯 Casos de Uso

### **1. Tabela de Rankings Completa**

```typescript
// Carregar primeira página ordenada por kills
const data = await getRankingsList({
  limit: 50,
  offset: 0,
  sort_by: 'kills',
  sort_order: 'desc'
});
```

### **2. Ordenar por Fama**

```typescript
// Top jogadores por fama
const data = await getRankingsList({
  limit: 20,
  sort_by: 'fame',
  sort_order: 'desc'
});
```

### **3. Buscar Jogador Específico**

```typescript
// Buscar por nome
const data = await getRankingsList({
  search: 'ADM',
  limit: 10
});
```

### **4. Paginação**

```typescript
// Segunda página (registros 51-100)
const data = await getRankingsList({
  limit: 50,
  offset: 50,
  sort_by: 'kills'
});
```

### **5. Ordenar por Minutos Sobrevividos**

```typescript
// Jogadores que mais sobreviveram
const data = await getRankingsList({
  sort_by: 'survival_time',
  sort_order: 'desc'
});
```

---

## ⚠️ Observações Importantes

1. **Paginação**: Use `limit` e `offset` para paginar grandes listas
2. **Ordenação**: O campo `sort_by` aceita nomes alternativos (ex: `fame` = `total_fame`)
3. **Busca**: A busca é case-insensitive e usa `LIKE` (busca parcial)
4. **Rank**: O campo `rank` é calculado baseado no `offset` atual
5. **Valores Nulos**: Campos numéricos podem ser `0` se o jogador não tiver dados
6. **Performance**: Índices no banco garantem ordenação rápida

---

## 🔗 Endpoints Relacionados

- **GET /api/rankings**: Rankings por categoria específica
- **GET /api/rankings/player/{steam_id}**: Dados completos de um jogador
- **GET /api/players/fame**: Lista de jogadores com fama

---

## 📞 Suporte

Em caso de dúvidas sobre a integração, entre em contato com o time de backend.

---

**Última Atualização**: 2025-12-02

