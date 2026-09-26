# 📊 Modelo de Tabelas - Sistema de Transações Bancárias

## 🎯 Visão Geral

Este documento apresenta o modelo completo das tabelas para armazenar transações bancárias e comerciais do jogo SCUM, baseado na análise do arquivo `economy_*.log`.

---

## 📋 Diagrama de Relacionamentos

```
┌─────────────────┐
│   players       │
│  (existente)    │
│                 │
│ - steam_id (PK) │◄─────┐
│ - player_name   │      │
└─────────────────┘      │
                         │
┌─────────────────┐      │
│ transaction_    │      │
│    types        │      │
│                 │      │
│ - id (PK)       │◄─────┤
│ - name          │      │
│ - category      │      │
└─────────────────┘      │
                         │
┌─────────────────┐      │
│   locations     │      │
│                 │      │
│ - id (PK)       │◄─────┤
│ - quadrant      │      │
│ - location_type │      │
│ - full_name     │      │
└─────────────────┘      │
                         │
┌─────────────────┐      │
│     items       │      │
│                 │      │
│ - id (PK)       │◄─────┤
│ - name          │      │
│ - base_name     │      │
└─────────────────┘      │
                         │
┌─────────────────────────┴──────────────────────┐
│         bank_transactions                      │
│                                                 │
│ - id (PK)                                      │
│ - steam_id (FK → players.steam_id)            │
│ - transaction_type_id (FK → transaction_types) │
│ - location_id (FK → locations)                │
│ - item_id (FK → items)                         │
│ - transaction_value                            │
│ - currency_type                                │
│ - balance_before_*                             │
│ - balance_after_*                              │
│ - timestamp                                    │
└─────────────────────────────────────────────────┘
```

---

## 📑 Estrutura Detalhada das Tabelas

### 1. Tabela: `transaction_types`

**Descrição**: Tipos de transações possíveis no sistema.

```sql
CREATE TABLE transaction_types (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,         -- trade_sale, trade_purchase, etc.
    category TEXT,                     -- trade, bank, currency, service
    description TEXT,
    is_income BOOLEAN,                 -- true se adiciona dinheiro ao player
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_transaction_types_name ON transaction_types(name);
CREATE INDEX idx_transaction_types_category ON transaction_types(category);
```

**Dados Iniciais**:
```sql
INSERT INTO transaction_types (name, category, description, is_income) VALUES
('trade_sale', 'trade', 'Venda de item para trader', true),
('trade_purchase', 'trade', 'Compra de item de trader', false),
('bank_deposit', 'bank', 'Depósito bancário', false),
('bank_withdrawal', 'bank', 'Saque bancário', true),
('currency_conversion', 'currency', 'Conversão de moeda (credits → gold)', false),
('service_repair', 'service', 'Serviço de reparo de veículo', false),
('service_modification', 'service', 'Serviço de modificação de veículo', false);
```

**Exemplo de Registro**:
```
id: 1
name: "trade_sale"
category: "trade"
description: "Venda de item para trader"
is_income: true
created_at: "2025-12-06 00:00:00"
```

---

### 2. Tabela: `locations`

**Descrição**: Locais onde as transações ocorrem (quadrante + tipo de vendedor).

```sql
CREATE TABLE locations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    quadrant TEXT NOT NULL,           -- B_4, A_0, C_2, Z_3, etc.
    location_type TEXT NOT NULL,      -- Armory, Trader, Mechanic, Saloon, etc.
    full_name TEXT NOT NULL UNIQUE,   -- B_4_Armory (quadrant_location_type)
    description TEXT,
    first_seen TEXT DEFAULT CURRENT_TIMESTAMP,
    last_seen TEXT DEFAULT CURRENT_TIMESTAMP,
    transaction_count INTEGER DEFAULT 0,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_locations_quadrant ON locations(quadrant);
CREATE INDEX idx_locations_type ON locations(location_type);
CREATE INDEX idx_locations_full_name ON locations(full_name);
CREATE UNIQUE INDEX idx_locations_quadrant_type ON locations(quadrant, location_type);
```

**Exemplos de Registros**:
```
id: 1
quadrant: "B_4"
location_type: "Armory"
full_name: "B_4_Armory"
description: "Arsenal no quadrante B_4"
first_seen: "2025-12-06 00:34:57"
last_seen: "2025-12-06 02:47:45"
transaction_count: 150
created_at: "2025-12-06 00:34:57"

id: 2
quadrant: "B_4"
location_type: "Trader"
full_name: "B_4_Trader"
description: "Comerciante geral no quadrante B_4"
first_seen: "2025-12-06 00:50:35"
last_seen: "2025-12-06 03:50:26"
transaction_count: 80
created_at: "2025-12-06 00:50:35"

id: 3
quadrant: "B_4"
location_type: "Mechanic"
full_name: "B_4_Mechanic"
description: "Mecânico no quadrante B_4"
first_seen: "2025-12-06 00:38:12"
last_seen: "2025-12-06 02:52:53"
transaction_count: 25
created_at: "2025-12-06 00:38:12"

id: 4
quadrant: "B_4"
location_type: "Saloon"
full_name: "B_4_Saloon"
description: "Saloon no quadrante B_4"
first_seen: "2025-12-06 01:42:11"
last_seen: "2025-12-06 01:42:47"
transaction_count: 2
created_at: "2025-12-06 01:42:11"
```

---

### 3. Tabela: `items`

**Descrição**: Itens normalizados (nome base, sem health/durabilidade).

```sql
CREATE TABLE items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,         -- Nome base do item (limpo)
    base_name TEXT,                    -- Mesmo que name (para compatibilidade)
    category TEXT,                     -- weapon, vehicle, consumable, etc. (opcional)
    first_seen TEXT DEFAULT CURRENT_TIMESTAMP,
    last_seen TEXT DEFAULT CURRENT_TIMESTAMP,
    usage_count INTEGER DEFAULT 0,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_items_name ON items(name);
CREATE INDEX idx_items_category ON items(category);
```

**Exemplos de Registros**:
```
id: 1
name: "BPC_Dirtbike"
base_name: "BPC_Dirtbike"
category: "vehicle"
first_seen: "2025-12-06 01:35:44"
last_seen: "2025-12-06 01:35:44"
usage_count: 1
created_at: "2025-12-06 01:35:44"

id: 2
name: "Weapon_MK18"
base_name: "Weapon_MK18"
category: "weapon"
first_seen: "2025-12-06 00:41:27"
last_seen: "2025-12-06 00:41:27"
usage_count: 1
created_at: "2025-12-06 00:41:27"

id: 3
name: "Cal_9mm_Ammobox"
base_name: "Cal_9mm_Ammobox"
category: "ammunition"
first_seen: "2025-12-06 00:35:29"
last_seen: "2025-12-06 01:25:42"
usage_count: 5
created_at: "2025-12-06 00:35:29"

id: 4
name: "Batteries"
base_name: "Batteries"
category: "consumable"
first_seen: "2025-12-06 00:51:48"
last_seen: "2025-12-06 00:51:48"
usage_count: 1
created_at: "2025-12-06 00:51:48"
```

**Nota**: O campo `name` armazena apenas o nome base do item, sem:
- Health/durabilidade: `(health: 152.54)`
- Quantidade: `(x2)`
- Uses: `(uses: 1)`
- Contained items: `(contained items: ...)`

**Exemplo de Limpeza**:
- **Original**: `BPC_Dirtbike (health: 152.54)` → **Armazenado**: `BPC_Dirtbike`
- **Original**: `Cal_9mm_Ammobox (x1)` → **Armazenado**: `Cal_9mm_Ammobox`
- **Original**: `Weapon_MK18 (health: 99.94, uses: 1)` → **Armazenado**: `Weapon_MK18`

---

### 4. Tabela: `bank_transactions`

**Descrição**: Transações principais do sistema.

```sql
CREATE TABLE bank_transactions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    
    -- Relacionamentos
    steam_id TEXT NOT NULL,                    -- FK → players.steam_id
    transaction_type_id INTEGER NOT NULL,      -- FK → transaction_types.id
    location_id INTEGER,                       -- FK → locations.id (NULL se não aplicável)
    item_id INTEGER,                           -- FK → items.id (NULL se não aplicável)
    item_quantity INTEGER DEFAULT 1,          -- Quantidade do item (se aplicável)
    
    -- Valores monetários
    transaction_value REAL NOT NULL,           -- Valor total da transação
    currency_type TEXT DEFAULT 'money',        -- money, gold, credits
    value_base REAL,                           -- Valor base (sem itens contidos)
    value_contained_items REAL DEFAULT 0,      -- Valor de itens contidos
    
    -- Saldos ANTES da transação
    balance_before_money REAL DEFAULT 0,      -- Dinheiro em mãos antes
    balance_before_gold REAL DEFAULT 0,       -- Ouro antes
    balance_before_account REAL DEFAULT 0,    -- Saldo bancário antes
    
    -- Saldos DEPOIS da transação
    balance_after_money REAL DEFAULT 0,       -- Dinheiro em mãos depois
    balance_after_gold REAL DEFAULT 0,        -- Ouro depois
    balance_after_account REAL DEFAULT 0,    -- Saldo bancário depois
    
    -- Informações adicionais (para transações de Trade)
    trader_funds_before INTEGER,               -- Fundos do trader antes
    trader_funds_after INTEGER,                -- Fundos do trader depois
    store_quantity_before INTEGER,             -- Quantidade no estoque antes (-1 = ilimitado)
    store_quantity_after INTEGER,              -- Quantidade no estoque depois (-1 = ilimitado)
    players_online INTEGER,                  -- Jogadores online no momento
    
    -- Metadados
    timestamp TEXT NOT NULL,                  -- Timestamp da transação (formato: YYYY.MM.DD-HH.mm.ss)
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

-- Índices para performance
CREATE INDEX idx_bank_transactions_steam_timestamp ON bank_transactions(steam_id, timestamp DESC);
CREATE INDEX idx_bank_transactions_location ON bank_transactions(location_id);
CREATE INDEX idx_bank_transactions_type ON bank_transactions(transaction_type_id);
CREATE INDEX idx_bank_transactions_item ON bank_transactions(item_id);
CREATE INDEX idx_bank_transactions_timestamp ON bank_transactions(timestamp DESC);
CREATE INDEX idx_bank_transactions_steam_id ON bank_transactions(steam_id);
```

**Exemplos de Registros**:

#### Exemplo 1: Venda de Item (Trade Sale)
```
id: 1
steam_id: "76561199617993331"
transaction_type_id: 1  -- trade_sale
location_id: 1          -- B_4_Armory
item_id: 2              -- Weapon_MK18
item_quantity: 1
transaction_value: 3278.0
currency_type: "money"
value_base: 2870.0
value_contained_items: 408.0
balance_before_money: 0.0
balance_before_gold: 68.0
balance_before_account: 26019.0
balance_after_money: 0.0
balance_after_gold: 68.0
balance_after_account: 29297.0
trader_funds_before: 100000
trader_funds_after: 100000
store_quantity_before: -1
store_quantity_after: -1
players_online: 3
timestamp: "2025.12.06-00.41.27"
created_at: "2025-12-06 00:41:27"
```

#### Exemplo 2: Compra de Item (Trade Purchase)
```
id: 2
steam_id: "76561199617993331"
transaction_type_id: 2  -- trade_purchase
location_id: 2          -- B_4_Trader
item_id: 4              -- Batteries
item_quantity: 2
transaction_value: 200.0
currency_type: "money"
value_base: 200.0
value_contained_items: 0.0
balance_before_money: 0.0
balance_before_gold: 68.0
balance_before_account: 26717.0
balance_after_money: 0.0
balance_after_gold: 68.0
balance_after_account: 26517.0
trader_funds_before: 100000
trader_funds_after: 100000
store_quantity_before: -1
store_quantity_after: -1
players_online: 3
timestamp: "2025.12.06-00.51.48"
created_at: "2025-12-06 00:51:48"
```

#### Exemplo 3: Depósito Bancário (Bank Deposit)
```
id: 3
steam_id: "76561198202684968"
transaction_type_id: 3  -- bank_deposit
location_id: NULL       -- Não aplicável
item_id: NULL           -- Não aplicável
item_quantity: 1
transaction_value: 375.0
currency_type: "money"
value_base: 367.0       -- Valor efetivamente adicionado (após taxas)
value_contained_items: 0.0
balance_before_money: 375.0
balance_before_gold: 0.0
balance_before_account: 0.0
balance_after_money: 0.0
balance_after_gold: 0.0
balance_after_account: 367.0
trader_funds_before: NULL
trader_funds_after: NULL
store_quantity_before: NULL
store_quantity_after: NULL
players_online: NULL
timestamp: "2025.12.06-01.31.11"
created_at: "2025-12-06 01:31:11"
```

#### Exemplo 4: Conversão de Moeda (Currency Conversion)
```
id: 4
steam_id: "76561199617993331"
transaction_type_id: 5  -- currency_conversion
location_id: NULL       -- Não aplicável
item_id: NULL           -- Não aplicável
item_quantity: 1
transaction_value: 58000.0
currency_type: "credits"
value_base: 58000.0
value_contained_items: 0.0
balance_before_money: 0.0
balance_before_gold: 0.0
balance_before_account: 105415.0  -- credits antes
balance_after_money: 0.0
balance_after_gold: 50.0
balance_after_account: 47415.0    -- credits depois
trader_funds_before: NULL
trader_funds_after: NULL
store_quantity_before: NULL
store_quantity_after: NULL
players_online: NULL
timestamp: "2025.12.06-00.36.50"
created_at: "2025-12-06 00:36:50"
```

#### Exemplo 5: Serviço de Reparo (Service Repair)
```
id: 5
steam_id: "76561199617993331"
transaction_type_id: 6  -- service_repair
location_id: 3           -- B_4_Mechanic
item_id: NULL            -- Não aplicável (é um serviço)
item_quantity: 1
transaction_value: 129.0
currency_type: "money"
value_base: 129.0
value_contained_items: 0.0
balance_before_money: 0.0
balance_before_gold: 68.0
balance_before_account: 0.0
balance_after_money: 0.0
balance_after_gold: 68.0
balance_after_account: 0.0
trader_funds_before: NULL
trader_funds_after: NULL
store_quantity_before: NULL
store_quantity_after: NULL
players_online: 3
timestamp: "2025.12.06-00.38.12"
created_at: "2025-12-06 00:38:12"
```

---

## 🔗 Relacionamentos e Constraints

### Foreign Keys (Recomendado adicionar)
```sql
-- Adicionar constraints de foreign key (opcional, mas recomendado)
-- SQLite não suporta ALTER TABLE ADD CONSTRAINT, então devem ser criadas junto com a tabela

-- Para bank_transactions:
-- FOREIGN KEY (steam_id) REFERENCES players(steam_id)
-- FOREIGN KEY (transaction_type_id) REFERENCES transaction_types(id)
-- FOREIGN KEY (location_id) REFERENCES locations(id)
-- FOREIGN KEY (item_id) REFERENCES items(id)
```

### Validações Importantes

1. **steam_id**: Deve existir na tabela `players` antes de inserir transação
2. **transaction_type_id**: Deve existir em `transaction_types`
3. **location_id**: Pode ser NULL para transações sem local (Bank, Currency Conversion)
4. **item_id**: Pode ser NULL para transações sem item (Bank, Currency Conversion, Services)
5. **timestamp**: Formato `YYYY.MM.DD-HH.mm.ss` (do log original)

---

## 📊 Consultas de Exemplo

### 1. Transações de um Player
```sql
SELECT 
    bt.timestamp,
    tt.name as transaction_type,
    l.full_name as location,
    i.name as item,
    bt.transaction_value,
    bt.currency_type,
    bt.balance_after_account
FROM bank_transactions bt
JOIN transaction_types tt ON bt.transaction_type_id = tt.id
LEFT JOIN locations l ON bt.location_id = l.id
LEFT JOIN items i ON bt.item_id = i.id
WHERE bt.steam_id = '76561199617993331'
ORDER BY bt.timestamp DESC
LIMIT 20;
```

### 2. Transações por Local
```sql
SELECT 
    l.full_name,
    l.location_type,
    COUNT(*) as total_transactions,
    SUM(bt.transaction_value) as total_value,
    COUNT(DISTINCT bt.steam_id) as unique_players
FROM bank_transactions bt
JOIN locations l ON bt.location_id = l.id
GROUP BY l.id
ORDER BY total_transactions DESC;
```

### 3. Itens Mais Vendidos
```sql
SELECT 
    i.name,
    i.category,
    COUNT(*) as times_sold,
    SUM(bt.transaction_value) as total_revenue,
    AVG(bt.transaction_value) as avg_price
FROM bank_transactions bt
JOIN items i ON bt.item_id = i.id
JOIN transaction_types tt ON bt.transaction_type_id = tt.id
WHERE tt.name = 'trade_sale'
GROUP BY i.id
ORDER BY total_revenue DESC
LIMIT 20;
```

### 4. Histórico de Saldo de um Player
```sql
SELECT 
    timestamp,
    transaction_type_id,
    balance_after_account,
    balance_after_money,
    balance_after_gold
FROM bank_transactions
WHERE steam_id = '76561199617993331'
ORDER BY timestamp DESC;
```

---

## ✅ Checklist de Implementação

- [x] Estrutura de tabelas definida
- [x] Relacionamentos mapeados
- [x] Índices criados
- [x] Exemplos de dados fornecidos
- [ ] Constraints de foreign key (opcional)
- [ ] Triggers para atualizar contadores (opcional)
- [ ] Validações de integridade
- [ ] Parser de log implementado
- [ ] Inserção normalizada implementada

---

## 📝 Notas Finais

1. **Normalização**: Todas as strings repetidas (locais, itens, tipos) são normalizadas em tabelas separadas
2. **Performance**: Índices criados nas colunas mais consultadas
3. **Flexibilidade**: Campos opcionais (location_id, item_id) permitem diferentes tipos de transações
4. **Expansibilidade**: Estrutura permite adicionar novos tipos sem alterar schema principal
