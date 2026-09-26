# 📊 Migração: Adicionar Total de Fama na Tabela Rankings

## 🎯 Objetivo

Adicionar a coluna `total_fame` da tabela `player_fame_totals` na tabela `rankings` para permitir rankings de fama junto com os outros rankings.

---

## ✅ Implementação Realizada

### **1. Modificações no Código**

#### **A) RankingsUpdateService** (`core/survival/rankings_update_service.py`)

**Adicionado em `_calculate_player_rankings()`**:
```python
# ==========================================
# player_fame_totals
# ==========================================

cursor.execute('''
    SELECT total_fame
    FROM player_fame_totals
    WHERE steam_id = ?
''', (steam_id,))
fame_row = cursor.fetchone()

if fame_row:
    rankings['total_fame'] = fame_row[0] or 0.0
else:
    rankings['total_fame'] = 0.0
```

**Adicionado em `_insert_or_update_ranking()`**:
- Coluna `total_fame` adicionada no `INSERT OR REPLACE`
- Valor obtido de `rankings.get('total_fame', 0.0)`

#### **B) API Endpoint** (`main.py`)

**Adicionado no `category_map`**:
```python
'fame': 'total_fame'
```

**Adicionado na query SELECT**:
```sql
SELECT ..., total_fame, last_updated
FROM rankings
```

**Adicionado no resultado JSON**:
```python
'total_fame': row.get('total_fame', 0.0)
```

---

### **2. Script de Migração SQL**

**Arquivo**: `scripts/migrations/add_total_fame_to_rankings.sql`

```sql
-- Adicionar coluna total_fame
ALTER TABLE rankings ADD COLUMN total_fame REAL DEFAULT 0.0;

-- Criar índice para ordenação rápida
CREATE INDEX IF NOT EXISTS idx_rankings_total_fame ON rankings(total_fame DESC);

-- Atualizar valores existentes com dados de player_fame_totals
UPDATE rankings
SET total_fame = (
    SELECT COALESCE(total_fame, 0.0)
    FROM player_fame_totals
    WHERE player_fame_totals.steam_id = rankings.steam_id
)
WHERE EXISTS (
    SELECT 1
    FROM player_fame_totals
    WHERE player_fame_totals.steam_id = rankings.steam_id
);
```

---

## 📋 Como Aplicar a Migração

### **Opção 1: Executar Script SQL Manualmente**

```bash
sqlite3 data/SSM.db < scripts/migrations/add_total_fame_to_rankings.sql
```

### **Opção 2: Executar via Python**

```python
import sqlite3

db_path = "data/SSM.db"

with sqlite3.connect(db_path) as conn:
    cursor = conn.cursor()
    
    # Adicionar coluna
    cursor.execute('ALTER TABLE rankings ADD COLUMN total_fame REAL DEFAULT 0.0')
    
    # Criar índice
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_rankings_total_fame ON rankings(total_fame DESC)')
    
    # Atualizar valores existentes
    cursor.execute('''
        UPDATE rankings
        SET total_fame = (
            SELECT COALESCE(total_fame, 0.0)
            FROM player_fame_totals
            WHERE player_fame_totals.steam_id = rankings.steam_id
        )
        WHERE EXISTS (
            SELECT 1
            FROM player_fame_totals
            WHERE player_fame_totals.steam_id = rankings.steam_id
        )
    ''')
    
    conn.commit()
    print("Migração aplicada com sucesso!")
```

---

## 🔄 Comportamento Após Migração

### **1. Atualização Automática**

A coluna `total_fame` será atualizada automaticamente a cada execução do `RankingsUpdateService`:

- **Frequência**: Diariamente (padrão: 03:00)
- **Fonte**: Tabela `player_fame_totals`
- **Valor padrão**: `0.0` se o jogador não tiver registro de fama

### **2. Endpoint de Rankings**

Agora é possível consultar rankings de fama:

```bash
GET /api/rankings?category=fame&limit=20
```

**Resposta**:
```json
{
  "success": true,
  "data": {
    "category": "fame",
    "order_column": "total_fame",
    "rankings": [
      {
        "rank": 1,
        "steam_id": "76561198777583030",
        "player_name": "ADM Guns",
        "value": 234.79837,
        "total_fame": 234.79837,
        ...
      }
    ],
    "total": 28,
    "limit": 20,
    "offset": 0
  }
}
```

---

## 📊 Estrutura Atualizada da Tabela

```sql
CREATE TABLE IF NOT EXISTS rankings (
    ...
    highest_weight_carried REAL DEFAULT 0,
    total_fame REAL DEFAULT 0,              -- NOVA COLUNA
    last_updated DATETIME DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(steam_id)
);
```

---

## ✅ Verificação

### **Verificar se a coluna foi adicionada**:

```sql
SELECT sql FROM sqlite_master WHERE type='table' AND name='rankings';
```

### **Verificar valores populados**:

```sql
SELECT steam_id, player_name, total_fame 
FROM rankings 
WHERE total_fame > 0 
ORDER BY total_fame DESC 
LIMIT 10;
```

### **Verificar índice**:

```sql
SELECT name FROM sqlite_master WHERE type='index' AND name='idx_rankings_total_fame';
```

---

## ⚠️ Observações Importantes

1. **Compatibilidade**: A migração é compatível com tabelas existentes (usa `ALTER TABLE ADD COLUMN`)
2. **Valores Existentes**: Jogadores sem registro em `player_fame_totals` terão `total_fame = 0.0`
3. **Atualização**: Valores serão atualizados na próxima execução do `RankingsUpdateService`
4. **Performance**: Índice criado para ordenação rápida de rankings de fama

---

## 🔗 Arquivos Modificados

- ✅ `core/survival/rankings_update_service.py` - Adicionado cálculo e inserção de `total_fame`
- ✅ `main.py` - Adicionado categoria `fame` no endpoint de rankings
- ✅ `docs/RANKINGS_TABLE_SCHEMA.md` - Documentação atualizada
- ✅ `scripts/migrations/add_total_fame_to_rankings.sql` - Script de migração criado

---

**Data da Implementação**: 2025-12-02  
**Status**: ✅ Implementado e pronto para uso

