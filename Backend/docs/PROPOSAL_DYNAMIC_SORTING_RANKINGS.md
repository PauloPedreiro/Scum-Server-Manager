# 🔄 Proposta: Ordenação Dinâmica na Tabela de Rankings

## 🎯 Objetivo

Implementar ordenação dinâmica no frontend onde o usuário pode clicar em qualquer coluna da tabela para ordenar os dados por aquela coluna, alternando entre ascendente (ASC) e descendente (DESC).

---

## 🤔 Análise: Abordagens Possíveis

### **Opção 1: Ordenação no Servidor (Server-Side)** ⭐ **RECOMENDADA**

**Como funciona**:
- Cada clique na coluna faz uma nova requisição ao servidor
- Servidor retorna dados já ordenados
- Frontend apenas atualiza a tabela

**Fluxo**:
```
Usuário clica em "Kills"
    ↓
Frontend: sort_by=kills&sort_order=desc
    ↓
Backend: SELECT ... ORDER BY kills DESC
    ↓
Frontend: Atualiza tabela com dados ordenados
```

**Vantagens**:
- ✅ Funciona perfeitamente com paginação
- ✅ Sempre ordena corretamente (mesmo com muitos dados)
- ✅ Performance boa (índices no banco)
- ✅ Não carrega todos os dados na memória
- ✅ Escalável para grandes volumes

**Desvantagens**:
- ⚠️ Requer requisição HTTP a cada clique
- ⚠️ Pode ter pequeno delay (depende da rede)

---

### **Opção 2: Ordenação no Cliente (Client-Side)**

**Como funciona**:
- Carrega todos os dados uma vez
- Ordenação acontece no JavaScript do navegador
- Sem requisições adicionais

**Fluxo**:
```
Carregar página: GET /api/rankings/list?limit=1000
    ↓
Frontend: Armazena todos os dados em memória
    ↓
Usuário clica em "Kills"
    ↓
Frontend: Ordena array localmente
    ↓
Frontend: Atualiza tabela (sem requisição)
```

**Vantagens**:
- ✅ Ordenação instantânea (sem delay de rede)
- ✅ Melhor UX (sem loading)
- ✅ Funciona offline (após carregar)

**Desvantagens**:
- ❌ Não funciona bem com paginação
- ❌ Carrega todos os dados na memória
- ❌ Pode ser lento com muitos registros (1000+)
- ❌ Consome mais memória do navegador
- ❌ Primeira carga pode ser lenta

---

### **Opção 3: Híbrida (Melhor dos Dois Mundos)** 🎯

**Como funciona**:
- Carrega página atual do servidor (com paginação)
- Ordenação sempre no servidor
- Cache inteligente para evitar requisições desnecessárias

**Fluxo**:
```
Usuário clica em "Kills"
    ↓
Frontend: Verifica se já tem dados ordenados por kills
    ↓
Se não tem: Requisição ao servidor
    ↓
Se já tem: Usa dados em cache (se mesma página)
    ↓
Atualiza tabela
```

**Vantagens**:
- ✅ Melhor performance (cache)
- ✅ Funciona com paginação
- ✅ Ordenação correta sempre
- ✅ Boa UX

**Desvantagens**:
- ⚠️ Implementação mais complexa
- ⚠️ Precisa gerenciar cache

---

## ✅ Recomendação: Opção 1 (Server-Side)

**Por quê?**
1. ✅ Mais simples de implementar
2. ✅ Funciona perfeitamente com paginação
3. ✅ Escalável (funciona com qualquer volume de dados)
4. ✅ Performance boa (índices no banco)
5. ✅ Sempre correto (não depende de dados em cache)

**Delay de rede**: Geralmente < 200ms (aceitável para boa UX)

---

## 🎨 Implementação no Frontend

### **1. Estrutura do Componente**

```typescript
interface RankingsTableState {
  players: PlayerRanking[];
  pagination: {
    total: number;
    limit: number;
    offset: number;
  };
  sorting: {
    sort_by: string;        // Coluna atual ordenada
    sort_order: 'asc' | 'desc';  // Direção atual
  };
  loading: boolean;
}

// Campos ordenáveis
const SORTABLE_COLUMNS = {
  'kills': 'kills',
  'deaths': 'deaths',
  'kdr': 'kdr',
  'longest_shot': 'longest_shot_distance',
  'suicides': 'suicides',
  'lockpick_basic_rate': 'lockpick_basic_rate',
  'lockpick_medium_rate': 'lockpick_medium_rate',
  'lockpick_advanced_rate': 'lockpick_advanced_rate',
  'vehicles_destroyed': 'vehicles_destroyed',
  'highest_defecation': 'highest_defecation',
  'animals_killed': 'animals_killed',
  'players_knocked_out': 'players_knocked_out',
  'headshots': 'headshots',
  'minutes_survived': 'minutes_survived',
  'overdoses': 'overdoses',
  'highest_weight_carried': 'highest_weight_carried',
  'total_fame': 'total_fame',
  'player_name': 'player_name',
} as const;
```

### **2. Handler de Clique na Coluna**

```typescript
const handleColumnClick = (columnKey: string) => {
  const sortBy = SORTABLE_COLUMNS[columnKey];
  if (!sortBy) return; // Coluna não é ordenável
  
  setLoading(true);
  
  // Determinar nova direção de ordenação
  let newSortOrder: 'asc' | 'desc' = 'desc';
  
  if (sorting.sort_by === sortBy) {
    // Se já está ordenado por esta coluna, alterna direção
    newSortOrder = sorting.sort_order === 'desc' ? 'asc' : 'desc';
  }
  
  // Atualizar estado
  setSorting({
    sort_by: sortBy,
    sort_order: newSortOrder
  });
  
  // Fazer requisição
  fetchRankings({
    sort_by: sortBy,
    sort_order: newSortOrder,
    limit: pagination.limit,
    offset: 0  // Resetar para primeira página ao ordenar
  });
};
```

### **3. Função de Requisição**

```typescript
const fetchRankings = async (params: {
  sort_by?: string;
  sort_order?: 'asc' | 'desc';
  limit?: number;
  offset?: number;
  search?: string;
}) => {
  try {
    setLoading(true);
    
    const queryParams = new URLSearchParams({
      limit: (params.limit || pagination.limit).toString(),
      offset: (params.offset || pagination.offset).toString(),
      sort_by: params.sort_by || sorting.sort_by || 'kills',
      sort_order: params.sort_order || sorting.sort_order || 'desc',
      ...(params.search && { search: params.search })
    });
    
    const response = await fetch(
      `/api/rankings/list?${queryParams}`
    );
    
    const data = await response.json();
    
    if (data.success) {
      setPlayers(data.data.players);
      setPagination(data.data.pagination);
      setSorting(data.data.sorting);
    }
  } catch (error) {
    console.error('Erro ao buscar rankings:', error);
  } finally {
    setLoading(false);
  }
};
```

### **4. Componente de Cabeçalho da Tabela**

```tsx
const TableHeader = ({ columnKey, label }: { columnKey: string; label: string }) => {
  const isSortable = SORTABLE_COLUMNS[columnKey] !== undefined;
  const isCurrentSort = sorting.sort_by === SORTABLE_COLUMNS[columnKey];
  
  return (
    <th
      onClick={() => isSortable && handleColumnClick(columnKey)}
      className={`
        ${isSortable ? 'cursor-pointer hover:bg-gray-100' : ''}
        ${isCurrentSort ? 'bg-blue-50 font-semibold' : ''}
      `}
    >
      <div className="flex items-center gap-2">
        <span>{label}</span>
        {isSortable && (
          <span className="text-gray-400">
            {isCurrentSort ? (
              sorting.sort_order === 'desc' ? '▼' : '▲'
            ) : (
              '⇅'  // Indicador de ordenável
            )}
          </span>
        )}
      </div>
    </th>
  );
};
```

### **5. Exemplo Completo de Tabela**

```tsx
const RankingsTable = () => {
  const [state, setState] = useState<RankingsTableState>({
    players: [],
    pagination: { total: 0, limit: 50, offset: 0 },
    sorting: { sort_by: 'kills', sort_order: 'desc' },
    loading: false
  });
  
  useEffect(() => {
    fetchRankings({});
  }, []);
  
  return (
    <div className="rankings-table">
      {state.loading && <LoadingSpinner />}
      
      <table>
        <thead>
          <tr>
            <TableHeader columnKey="player_name" label="Jogador" />
            <TableHeader columnKey="kills" label="Kills" />
            <TableHeader columnKey="deaths" label="Deaths" />
            <TableHeader columnKey="kdr" label="KDR" />
            <TableHeader columnKey="longest_shot" label="Tiro Mais Longo" />
            <TableHeader columnKey="headshots" label="Headshots" />
            <TableHeader columnKey="minutes_survived" label="Minutos Sobrevividos" />
            <TableHeader columnKey="total_fame" label="Fama" />
            {/* ... outras colunas */}
          </tr>
        </thead>
        <tbody>
          {state.players.map((player, index) => (
            <tr key={player.steam_id}>
              <td>{player.player_name}</td>
              <td>{player.kills}</td>
              <td>{player.deaths}</td>
              <td>{player.kdr.toFixed(2)}</td>
              <td>{player.longest_shot.distance.toFixed(2)}m</td>
              <td>{player.headshots}</td>
              <td>{formatMinutes(player.minutes_survived)}</td>
              <td>{player.total_fame.toFixed(2)}</td>
            </tr>
          ))}
        </tbody>
      </table>
      
      <Pagination
        total={state.pagination.total}
        limit={state.pagination.limit}
        offset={state.pagination.offset}
        onPageChange={(newOffset) => fetchRankings({ offset: newOffset })}
      />
    </div>
  );
};
```

---

## 🔄 Comportamento de Ordenação

### **Regras de Toggle**

1. **Primeiro clique na coluna**:
   - Ordena por DESC (maior para menor)
   - Exemplo: Clica em "Kills" → Ordena por kills DESC

2. **Segundo clique na mesma coluna**:
   - Alterna para ASC (menor para maior)
   - Exemplo: Clica novamente em "Kills" → Ordena por kills ASC

3. **Clique em outra coluna**:
   - Ordena por DESC na nova coluna
   - Exemplo: Estava em "Kills" DESC, clica em "Deaths" → Ordena por deaths DESC

### **Indicadores Visuais**

| Estado | Indicador | Descrição |
|--------|-----------|-----------|
| **Não ordenado** | `⇅` (cinza) | Coluna é ordenável, mas não está ordenada |
| **Ordenado DESC** | `▼` (azul) | Ordenado descendente (maior → menor) |
| **Ordenado ASC** | `▲` (azul) | Ordenado ascendente (menor → maior) |
| **Coluna atual** | Fundo azul claro | Destaque visual da coluna ordenada |

---

## 📊 Mapeamento: Coluna Frontend → Coluna Backend

```typescript
const COLUMN_MAPPING = {
  // Frontend Key → Backend Column
  'kills': 'kills',
  'deaths': 'deaths',
  'kdr': 'kdr',
  'longest_shot': 'longest_shot_distance',  // ⚠️ Nome diferente
  'suicides': 'suicides',
  'lockpick_basic': 'lockpick_basic_rate',
  'lockpick_medium': 'lockpick_medium_rate',
  'lockpick_advanced': 'lockpick_advanced_rate',
  'vehicles_destroyed': 'vehicles_destroyed',
  'defecation': 'highest_defecation',  // ⚠️ Nome diferente
  'hunting': 'animals_killed',  // ⚠️ Nome diferente
  'melee': 'players_knocked_out',  // ⚠️ Nome diferente
  'headshots': 'headshots',
  'survival_time': 'minutes_survived',  // ⚠️ Nome diferente
  'overdoses': 'overdoses',
  'weight': 'highest_weight_carried',  // ⚠️ Nome diferente
  'fame': 'total_fame',  // ⚠️ Nome diferente
  'player_name': 'player_name',
} as const;
```

**⚠️ Importante**: Algumas colunas têm nomes diferentes no frontend e backend. O mapeamento resolve isso.

---

## 🎯 Estrutura de Resposta do Backend

O backend deve retornar informações sobre a ordenação atual:

```json
{
  "success": true,
  "data": {
    "players": [...],
    "pagination": {...},
    "sorting": {
      "sort_by": "kills",        // Coluna atual ordenada
      "sort_order": "desc"       // Direção atual
    }
  }
}
```

Isso permite ao frontend:
- ✅ Saber qual coluna está ordenada
- ✅ Saber a direção atual
- ✅ Atualizar indicadores visuais corretamente
- ✅ Alternar direção no próximo clique

---

## ⚡ Otimizações de Performance

### **1. Debounce (Opcional)**

Se o usuário clicar muito rápido, pode fazer debounce:

```typescript
const debouncedFetch = useMemo(
  () => debounce(fetchRankings, 300),
  []
);
```

### **2. Loading State**

Mostrar indicador de loading durante requisição:

```tsx
{loading && (
  <div className="loading-overlay">
    <Spinner />
    <span>Ordenando...</span>
  </div>
)}
```

### **3. Manter Scroll Position (Opcional)**

Se necessário, manter posição do scroll após ordenação:

```typescript
const scrollPosition = useRef(0);

const handleColumnClick = (columnKey: string) => {
  scrollPosition.current = window.scrollY;
  // ... ordenação
  setTimeout(() => {
    window.scrollTo(0, scrollPosition.current);
  }, 100);
};
```

---

## 📋 Checklist de Implementação

### **Backend**
- [ ] Endpoint `/api/rankings/list` com parâmetros `sort_by` e `sort_order`
- [ ] Validação de campos ordenáveis
- [ ] Mapeamento correto de nomes de colunas
- [ ] Retornar informações de ordenação na resposta
- [ ] Índices no banco para performance

### **Frontend**
- [ ] Componente de tabela com cabeçalhos clicáveis
- [ ] Handler de clique nas colunas
- [ ] Lógica de toggle (DESC ↔ ASC)
- [ ] Indicadores visuais (setas, highlight)
- [ ] Estado de loading durante requisição
- [ ] Resetar paginação ao ordenar
- [ ] Mapeamento frontend → backend

---

## 🎨 Exemplo Visual

```
┌─────────────────────────────────────────────────────────────┐
│  Jogador  │ Kills ▼ │ Deaths │ KDR │ Tiro Longo │ Fama ⇅  │
├───────────┼─────────┼────────┼─────┼────────────┼─────────┤
│ Player 1  │   150   │   25   │ 6.0 │   125.5m   │ 234.79  │
│ Player 2  │   120   │   30   │ 4.0 │   110.2m   │ 200.34  │
│ Player 3  │   100   │   20   │ 5.0 │   98.7m    │ 185.59  │
└─────────────────────────────────────────────────────────────┘
```

**Legenda**:
- `▼` = Ordenado DESC (Kills está ordenado)
- `⇅` = Ordenável mas não ordenado (Fama)
- Cabeçalho azul = Coluna atual ordenada

---

## ✅ Recomendação Final

**Implementar**: Ordenação Server-Side com toggle ASC/DESC

**Fluxo**:
1. Usuário clica em coluna
2. Frontend determina nova ordenação (toggle se mesma coluna)
3. Requisição ao servidor com `sort_by` e `sort_order`
4. Servidor retorna dados ordenados
5. Frontend atualiza tabela e indicadores visuais

**Vantagens**:
- ✅ Simples de implementar
- ✅ Funciona com paginação
- ✅ Escalável
- ✅ Sempre correto
- ✅ Boa UX (loading rápido)

---

**Data da Proposta**: 2025-12-02

