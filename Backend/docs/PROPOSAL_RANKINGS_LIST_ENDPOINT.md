# 📊 Proposta: Endpoint de Lista Completa de Rankings

## 🎯 Objetivo

Criar um endpoint que retorne **todos os jogadores** com **todas as colunas de ranking** para criar uma página de ranking completa no frontend, mostrando uma tabela/listagem com todos os dados.

---

## 📋 Análise do Estado Atual

### **Endpoints Existentes**

1. **`GET /api/rankings?category=X`**
   - ✅ Retorna rankings ordenados por uma categoria específica
   - ✅ Filtra apenas jogadores com valor > 0 na categoria
   - ✅ Retorna todos os dados de ranking
   - ❌ **Limitação**: Filtra por categoria (não mostra todos os jogadores)

2. **`GET /api/rankings/player/<steam_id>`**
   - ✅ Retorna dados completos de um jogador específico
   - ❌ **Limitação**: Apenas um jogador por vez

### **Necessidade do Frontend**

- 📋 Lista completa de todos os jogadores
- 📊 Todas as colunas de ranking visíveis
- 🔄 Paginação para grandes volumes
- 🔍 Ordenação flexível
- 📱 Estrutura otimizada para tabela/listagem

---

## 💡 Proposta de Endpoint

### **Opção 1: Endpoint Dedicado (Recomendada)** ⭐

**Endpoint**: `GET /api/rankings/list`

**Características**:
- ✅ Endpoint específico para listagem completa
- ✅ Não filtra por categoria (mostra todos os jogadores)
- ✅ Retorna todos os dados de ranking
- ✅ Paginação e ordenação flexíveis
- ✅ Estrutura otimizada para tabela

**Vantagens**:
- Separação clara de responsabilidades
- Não quebra compatibilidade com endpoint existente
- Fácil de entender e usar

---

### **Opção 2: Parâmetro no Endpoint Existente**

**Endpoint**: `GET /api/rankings?all=true`

**Características**:
- ✅ Reutiliza endpoint existente
- ✅ Parâmetro `all=true` remove filtro de categoria
- ❌ Pode confundir (mudança de comportamento)

**Desvantagens**:
- Mistura dois casos de uso diferentes
- Pode ser confuso para o frontend

---

## 🎯 Estrutura Proposta (Opção 1)

### **Endpoint**

```
GET /api/rankings/list
```

### **Parâmetros Query**

| Parâmetro | Tipo | Obrigatório | Padrão | Descrição |
|-----------|------|-------------|--------|-----------|
| `limit` | number | Não | `50` | Número máximo de registros (1-200) |
| `offset` | number | Não | `0` | Deslocamento para paginação (>= 0) |
| `sort_by` | string | Não | `kills` | Campo de ordenação (ver lista abaixo) |
| `sort_order` | string | Não | `desc` | Direção da ordenação (`asc` ou `desc`) |
| `search` | string | Não | - | Buscar por nome do jogador (case-insensitive) |

### **Campos de Ordenação (`sort_by`)**

- `kills` - Total de kills
- `deaths` - Total de deaths
- `kdr` - Kill/Death Ratio
- `longest_shot` - Maior distância de tiro
- `suicides` - Total de suicídios
- `lockpick_basic_rate` - Taxa de sucesso lockpick básico
- `lockpick_medium_rate` - Taxa de sucesso lockpick médio
- `lockpick_advanced_rate` - Taxa de sucesso lockpick avançado
- `vehicles_destroyed` - Veículos destruídos
- `highest_defecation` - Maior defecação
- `animals_killed` - Animais mortos
- `players_knocked_out` - Nocautes em jogadores
- `headshots` - Total de headshots
- `minutes_survived` - Minutos sobrevividos
- `overdoses` - Total de overdoses
- `highest_weight_carried` - Maior peso carregado
- `total_fame` - Total de fama
- `player_name` - Nome do jogador (ordem alfabética)
- `last_updated` - Data da última atualização

### **Estrutura de Resposta**

```json
{
  "success": true,
  "data": {
    "players": [
      {
        "steam_id": "76561198777583030",
        "player_name": "ADM Guns",
        
        // Combat Stats
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
        
        // Lockpicking Stats (por tipo)
        "lockpicking": {
          "basic": {
            "success": 45,
            "fails": 12,
            "total": 57,
            "rate": 78.95
          },
          "medium": { ... },
          "advanced": { ... },
          "veryeasy": { ... },
          "diallock": { ... },
          "other": { ... }
        },
        
        // Survival Stats
        "vehicles_destroyed": 5,
        "highest_defecation": 250,
        "animals_killed": 87,
        "players_knocked_out": 23,
        "minutes_survived": 5000.5,
        "overdoses": 8,
        "highest_weight_carried": 45.7,
        "total_fame": 234.79837,
        
        // Metadata
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
      "sort_order": "desc"
    }
  },
  "timestamp": 1701504000
}
```

---

## 🔍 Funcionalidades Adicionais (Opcional)

### **1. Filtros Avançados**

```json
{
  "filters": {
    "min_kills": 10,           // Mínimo de kills
    "min_kdr": 1.0,            // Mínimo KDR
    "has_fame": true,          // Apenas jogadores com fama > 0
    "min_total_fame": 50.0     // Mínimo de fama
  }
}
```

### **2. Agregações/Estatísticas**

```json
{
  "stats": {
    "total_players": 150,
    "players_with_kills": 120,
    "players_with_fame": 28,
    "average_kdr": 1.5,
    "top_killer": {
      "steam_id": "...",
      "player_name": "...",
      "kills": 200
    }
  }
}
```

### **3. Campos Calculados**

- `rank` - Posição no ranking atual (baseado em `sort_by`)
- `has_data` - Boolean indicando se o jogador tem algum dado de ranking

---

## 📊 Comparação com Endpoint Existente

| Característica | `/api/rankings` | `/api/rankings/list` (Proposta) |
|----------------|-----------------|----------------------------------|
| **Filtro por categoria** | ✅ Sim (obrigatório) | ❌ Não (mostra todos) |
| **Ordenação** | Por categoria | Flexível (qualquer campo) |
| **Busca por nome** | ❌ Não | ✅ Sim (opcional) |
| **Paginação** | ✅ Sim | ✅ Sim |
| **Estrutura** | Focada em ranking específico | Focada em listagem completa |
| **Uso** | Ranking por categoria | Tabela completa de rankings |

---

## 🎨 Estrutura para Frontend

### **Componente de Tabela**

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
    };
  };
  timestamp: number;
}

interface PlayerRanking {
  steam_id: string;
  player_name: string;
  
  // Combat
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
  
  // Lockpicking
  lockpicking: {
    [key: string]: {
      success: number;
      fails: number;
      total: number;
      rate: number;
    };
  };
  
  // Survival
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
```

---

## ✅ Recomendação Final

**Implementar Opção 1**: `GET /api/rankings/list`

**Razões**:
1. ✅ Separação clara de responsabilidades
2. ✅ Não quebra compatibilidade
3. ✅ Fácil de entender e usar
4. ✅ Otimizado para o caso de uso (listagem completa)
5. ✅ Permite evoluir independentemente

**Funcionalidades Iniciais**:
- ✅ Paginação (limit/offset)
- ✅ Ordenação flexível (sort_by/sort_order)
- ✅ Busca por nome (search)
- ✅ Retorna todos os dados de ranking
- ✅ Não filtra por categoria

**Funcionalidades Futuras (Opcional)**:
- ⏳ Filtros avançados
- ⏳ Estatísticas agregadas
- ⏳ Campos calculados (rank, has_data)

---

## 📝 Próximos Passos

1. ✅ Revisar proposta com o time
2. ⏳ Implementar endpoint `/api/rankings/list`
3. ⏳ Criar documentação para frontend
4. ⏳ Testar com dados reais
5. ⏳ Validar performance com grandes volumes

---

**Data da Proposta**: 2025-12-02

