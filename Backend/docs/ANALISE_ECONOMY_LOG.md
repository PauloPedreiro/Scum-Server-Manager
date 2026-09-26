# 📊 Análise Completa do Arquivo economy_*.log

## 🎯 Objetivo

Analisar a estrutura completa dos logs `economy_*.log` para identificar:
- Todos os tipos de transações
- Padrões de locais (quadrantes + tipos de vendedores)
- Estrutura de dados completa
- Melhor forma de implementar as tabelas

## 📝 Exemplos Fornecidos

### Exemplo 1: Venda para Armory
```
2025.12.06-00.41.27: [Trade] Before selling tradeables to trader B_4_Armory, player TutiCats(76561199617993331) had 0 cash, 26019 account balance and 68 gold and trader had 100000 funds.
```

**Análise:**
- **Tipo**: `[Trade]` - Venda
- **Local Completo**: `B_4_Armory`
  - **Quadrante**: `B_4`
  - **Tipo de Local**: `Armory`
- **Player**: `TutiCats(76561199617993331)`
- **Informações**: Saldo antes (cash: 0, account: 26019, gold: 68)

### Exemplo 2: Compra de Trader
```
2025.12.06-00.51.48: [Trade] Tradeable (Batteries (x2)) purchased by TutiCats(76561199617993331) for 200 money from trader B_4_Trader, old amount in store was -1, new amount is -1, and effective users online: 3
```

**Análise:**
- **Tipo**: `[Trade]` - Compra
- **Local Completo**: `B_4_Trader`
  - **Quadrante**: `B_4`
  - **Tipo de Local**: `Trader`
- **Item**: `Batteries (x2)`
- **Player**: `TutiCats(76561199617993331)`
- **Valor**: 200 money
- **Informações adicionais**: Quantidade no estoque (-1 = ilimitado), jogadores online: 3

### Exemplo 3: Venda para Mechanic
```
2025.12.06-01.35.44: [Trade] Tradeable (BPC_Dirtbike (health: 152.54)) sold by Guarani(76561198157950243) for 4909 (3972 + 937 worth of contained items) to trader B_4_Mechanic, old amount in store is -1, new amount is -1, and effective users online: 3
```

**Análise:**
- **Tipo**: `[Trade]` - Venda
- **Local Completo**: `B_4_Mechanic`
  - **Quadrante**: `B_4`
  - **Tipo de Local**: `Mechanic`
- **Item**: `BPC_Dirtbike (health: 152.54)`
- **Player**: `Guarani(76561198157950243)`
- **Valor Total**: 4909
  - **Valor Base**: 3972
  - **Valor Itens Contidos**: 937
- **Informações adicionais**: Quantidade no estoque, jogadores online: 3

## 🔍 Padrões Identificados

### 1. Estrutura de Localização

**Padrão**: `[QUADRANTE]_[TIPO]`

- **Quadrantes**: Letra + Número (ex: `B_4`, `A_1`, `C_2`)
- **Tipos de Locais Identificados**:
  - `Armory` - Arsenal (venda de armas/equipamentos)
  - `Trader` - Comerciante (compra/venda geral)
  - `Mechanic` - Mecânico (veículos/peças)

**Tipos de Locais Confirmados no Log**:
- `Armory` - Arsenal (armas, munições, equipamentos militares) ✅
- `Trader` - Comerciante geral (itens diversos) ✅
- `Mechanic` - Mecânico (peças de veículos, reparos) ✅
- `Saloon` - Saloon (bebidas, itens de bar) ✅

**Locais Completos Encontrados**:
- `B_4_Armory`, `B_4_Trader`, `B_4_Mechanic`, `B_4_Saloon`
- `A_0_Armory`, `A_0_Mechanic`
- `C_2_Trader`
- `Z_3_Mechanic`, `Z_3_Trader`, `Z_3_Armory`

**Quadrantes Encontrados**: `B_4` (mais comum), `A_0`, `C_2`, `Z_3`

### 2. Tipos de Transações

#### `[Trade]` - Transações de Comércio
- **Venda**: `Before selling tradeables to trader [LOCAL]`
- **Compra**: `Tradeable (...) purchased by [PLAYER] from trader [LOCAL]`
- **Venda com detalhes**: `Tradeable (...) sold by [PLAYER] to trader [LOCAL]`

**Informações capturadas**:
- Player (nome + Steam ID)
- Item (nome base, quantidade - **health não será armazenado**)
- Local (quadrante + tipo)
- Valores (total, base, itens contidos)
- Saldos antes/depois (cash, account balance, gold) - em linhas separadas "Before" e "After"
- Quantidade no estoque do trader (sempre -1 = ilimitado neste log)
- Jogadores online no momento
- **Correlação**: Múltiplos itens podem ser vendidos/comprados entre uma linha "Before" e uma linha "After"

#### `[Bank]` - Transações Bancárias
- **Depósitos**: `[Bank] PLAYER(ID:STEAM_ID)(Account Number:ACCOUNT) deposited AMOUNT(ACTUAL_ADDED was added) to Account Number: ACCOUNT(PLAYER)(STEAM_ID) at X=... Y=... Z=...`
  - Exemplo: `[Bank] TENEBROSO(ID:76561198202684968)(Account Number:718003040384) deposited 375(367 was added) to Account Number: 718003040384(TENEBROSO)(76561198202684968) at X=-150502.234 Y=290073.969 Z=69695.891`
  - **Informações**: Player, Account Number, Valor depositado, Valor efetivamente adicionado (pode ser diferente devido a taxas)
- **Saques**: Não encontrados neste log (padrão similar esperado)
- **Transferências**: Não encontradas neste log

#### `[Currency Conversion]` - Conversão de Moeda
- **Padrão**: `[Currency Conversion] PLAYER(ID:STEAM_ID)(Account Number:ACCOUNT) purchased GOLD_AMOUNT gold for CREDITS credits (new account balance is GOLD gold/CREDITS credits) at X=... Y=... Z=...`
  - Exemplo: `[Currency Conversion] TutiCats(ID:76561199617993331)(Account Number:718705046343) purchased 50 gold for 58000 credits (new account balance is 50 gold/47415 credits) at X=575022.438 Y=-227326.094 Z=356.130.`
  - **Informações**: Player, Account Number, Quantidade de gold comprada, Créditos gastos, Novo saldo (gold e credits)

#### `[Trade-Mechanic]` - Serviços de Mecânico
- **Padrão**: `[Trade-Mechanic] Service (SERVICE_DESCRIPTION) purchased by PLAYER(STEAM_ID) for VALOR money from trader LOCAL`
  - Exemplo: `[Trade-Mechanic] Service (Repair attachment BPC_WolfsWagen_Body_Front_C (x1)) purchased by TutiCats(76561199617993331) for 129 money from trader B_4_Mechanic`
  - **Informações**: Tipo de serviço (ex: "Repair attachment"), Item/peça, Player, Valor (money), Local (sempre Mechanic)
  - **Tipos encontrados**: Reparos de veículos (attachment repairs)

### 3. Estrutura de Itens

**Padrões identificados**:
- `ItemName (x2)` - Item com quantidade
- `ItemName (health: 152.54)` - Item com durabilidade (não necessário para transações)
- `ItemName (x2) (health: 100.0)` - Item com quantidade e durabilidade
- `ItemName (x2) (health: 100.0) (contained items: ...)` - Item com itens contidos

**Nota**: Para transações bancárias, não precisamos extrair health/durabilidade. Focamos apenas em:
- Nome do item (base)
- Quantidade (se houver)
- Valor da transação

### 4. Estrutura de Valores

**Valores monetários**:
- `money` - Dinheiro em mãos
- `account balance` - Saldo bancário
- `gold` - Ouro
- `credits` - Créditos

**Valores de transação**:
- Valor total
- Valor base
- Valor de itens contidos (para veículos/containers)

## 📋 Proposta de Estrutura de Tabelas

### Tabela 1: `locations` (Locais de Transação)
```sql
CREATE TABLE locations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    quadrant TEXT NOT NULL,           -- B_4, A_1, C_2, etc.
    location_type TEXT NOT NULL,      -- Armory, Trader, Mechanic, Bank, etc.
    full_name TEXT NOT NULL UNIQUE,   -- B_4_Armory (quadrant + type)
    description TEXT,
    first_seen TEXT DEFAULT CURRENT_TIMESTAMP,
    last_seen TEXT DEFAULT CURRENT_TIMESTAMP,
    transaction_count INTEGER DEFAULT 0,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_locations_quadrant ON locations(quadrant);
CREATE INDEX idx_locations_type ON locations(location_type);
CREATE INDEX idx_locations_full_name ON locations(full_name);
```

**Vantagens**:
- Normalização: evita repetir strings longas
- Facilita consultas por quadrante ou tipo
- Permite estatísticas por local
- Expansível para novos tipos de locais

### Tabela 2: `transaction_types` (Tipos de Transação)
```sql
CREATE TABLE transaction_types (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,         -- trade_sale, trade_purchase, bank_deposit, etc.
    category TEXT,                     -- trade, bank, currency, service
    description TEXT,
    is_income BOOLEAN,                 -- true se adiciona dinheiro ao player
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);
```

**Valores iniciais**:
- `trade_sale` - Venda de item
- `trade_purchase` - Compra de item
- `bank_deposit` - Depósito bancário
- `bank_withdrawal` - Saque bancário
- `currency_conversion` - Conversão de moeda
- `service_repair` - Serviço de reparo
- `service_modification` - Serviço de modificação

### Tabela 3: `items` (Itens - Normalização)
```sql
CREATE TABLE items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,         -- Nome base do item (limpo, sem quantidade/health)
    base_name TEXT,                    -- Nome limpo para agrupamento (mesmo que name)
    category TEXT,                     -- weapon, vehicle, consumable, etc. (opcional)
    first_seen TEXT DEFAULT CURRENT_TIMESTAMP,
    last_seen TEXT DEFAULT CURRENT_TIMESTAMP,
    usage_count INTEGER DEFAULT 0,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);
```

**Exemplo**:
- `name`: `BPC_Dirtbike` (extraído de `BPC_Dirtbike (health: 152.54)`)
- `base_name`: `BPC_Dirtbike`
- `category`: `vehicle` (opcional, pode ser NULL)

**Nota**: Health/durabilidade não é armazenado - foco apenas em transações financeiras.

### Tabela 4: `bank_transactions` (Transações Principais)
```sql
CREATE TABLE bank_transactions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    steam_id TEXT NOT NULL,           -- Referência a players.steam_id
    transaction_type_id INTEGER NOT NULL,  -- Referência a transaction_types
    location_id INTEGER,               -- Referência a locations (NULL se não aplicável)
    item_id INTEGER,                   -- Referência a items (NULL se não aplicável)
    item_quantity INTEGER DEFAULT 1,  -- Quantidade do item (se aplicável)
    
    -- Valores monetários
    transaction_value REAL NOT NULL,   -- Valor total da transação
    currency_type TEXT DEFAULT 'money', -- money, gold, credits
    
    -- Saldos antes da transação
    balance_before_money REAL DEFAULT 0,
    balance_before_gold REAL DEFAULT 0,
    balance_before_account REAL DEFAULT 0,
    
    -- Saldos depois da transação
    balance_after_money REAL DEFAULT 0,
    balance_after_gold REAL DEFAULT 0,
    balance_after_account REAL DEFAULT 0,
    
    -- Informações adicionais
    trader_funds_before INTEGER,       -- Fundos do trader antes
    trader_funds_after INTEGER,        -- Fundos do trader depois
    store_quantity_before INTEGER,     -- Quantidade no estoque antes
    store_quantity_after INTEGER,      -- Quantidade no estoque depois
    
    -- Metadados
    timestamp TEXT NOT NULL,
    log_line TEXT,                     -- Linha original do log (para debug)
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);
```

**Índices**:
```sql
CREATE INDEX idx_bank_transactions_steam_timestamp ON bank_transactions(steam_id, timestamp DESC);
CREATE INDEX idx_bank_transactions_location ON bank_transactions(location_id);
CREATE INDEX idx_bank_transactions_type ON bank_transactions(transaction_type_id);
CREATE INDEX idx_bank_transactions_item ON bank_transactions(item_id);
CREATE INDEX idx_bank_transactions_timestamp ON bank_transactions(timestamp DESC);
```

## 🔄 Fluxo de Processamento

### 1. Parse da Linha
```
Linha do log → Extrair:
  - Tipo de transação ([Trade], [Bank], etc.)
  - Player (nome + Steam ID)
  - Local (quadrante + tipo)
  - Item (se aplicável)
  - Valores monetários
  - Saldos antes/depois
```

### 2. Normalização
```
Local "B_4_Armory" → 
  - Verificar se existe em locations
  - Se não existe, criar:
    * quadrant: "B_4"
    * location_type: "Armory"
    * full_name: "B_4_Armory"
  - Obter location_id

Item "BPC_Dirtbike (health: 152.54)" →
  - Extrair base_name: "BPC_Dirtbike" (remover health, quantidade, etc.)
  - Verificar se base_name existe em items
  - Se não existe, criar
  - Obter item_id
  - Nota: Health/durabilidade não é armazenado
```

### 3. Inserção
```
Inserir em bank_transactions:
  - steam_id (verificar se existe em players)
  - transaction_type_id
  - location_id
  - item_id
  - Valores e saldos
  - timestamp
```

## 📊 Consultas Úteis

### Transações por Local
```sql
SELECT 
    l.full_name,
    l.location_type,
    COUNT(*) as total_transactions,
    SUM(bt.transaction_value) as total_value
FROM bank_transactions bt
JOIN locations l ON bt.location_id = l.id
GROUP BY l.id
ORDER BY total_transactions DESC;
```

### Transações por Quadrante
```sql
SELECT 
    l.quadrant,
    COUNT(*) as total_transactions,
    COUNT(DISTINCT bt.steam_id) as unique_players
FROM bank_transactions bt
JOIN locations l ON bt.location_id = l.id
GROUP BY l.quadrant;
```

### Itens Mais Vendidos
```sql
SELECT 
    i.base_name,
    i.category,
    COUNT(*) as times_sold,
    SUM(bt.transaction_value) as total_revenue
FROM bank_transactions bt
JOIN items i ON bt.item_id = i.id
JOIN transaction_types tt ON bt.transaction_type_id = tt.id
WHERE tt.name = 'trade_sale'
GROUP BY i.id
ORDER BY total_revenue DESC;
```

## ✅ Próximos Passos

1. **Executar análise completa do log**:
   - Identificar TODOS os tipos de locais
   - Identificar TODOS os quadrantes possíveis
   - Identificar TODOS os padrões de transações
   - Identificar TODOS os tipos de itens

2. **Validar estrutura proposta**:
   - Verificar se cobre todos os casos
   - Ajustar campos conforme necessário
   - Adicionar campos adicionais se necessário

3. **Implementar parser**:
   - Regex patterns para cada tipo de transação
   - Extração de dados normalizados
   - Validação de dados

4. **Implementar inserção**:
   - Get-or-create para locations
   - Get-or-create para items
   - Inserção em bank_transactions
   - Tratamento de erros

## 📝 Notas Importantes

- **Coordenadas removidas**: Conforme solicitado, não armazenamos coordenadas (location_x, location_y, location_z)
- **Health/Durabilidade removido**: Foco apenas em transações financeiras, não em detalhes técnicos dos itens
- **Normalização**: Usamos IDs em vez de strings repetidas para economizar espaço
- **Expansibilidade**: Estrutura permite adicionar novos tipos de locais/transações facilmente
- **Performance**: Índices otimizados para consultas comuns
- **Integridade**: Verificação de steam_id em players antes de inserir
- **Foco em transações**: Apenas informações relevantes para movimentações bancárias são armazenadas
