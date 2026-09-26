# 📊 Estrutura da Tabela `rankings`

## 🗄️ Schema Completo

```sql
CREATE TABLE IF NOT EXISTS rankings (
    -- ==========================================
    -- IDENTIFICAÇÃO DO JOGADOR
    -- ==========================================
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    steam_id TEXT NOT NULL,
    player_name TEXT NOT NULL,
    
    -- ==========================================
    -- kill_events
    -- ==========================================
    -- Kills e Deaths
    kills INTEGER DEFAULT 0,                    -- Total de kills (event_type='kill' AND killer_is_npc=0)
    deaths INTEGER DEFAULT 0,                   -- Total de deaths (event_type='kill')
    kdr REAL DEFAULT 0,                         -- Kill/Death Ratio (kills / deaths) - CALCULADO
    
    -- Longest Shot
    longest_shot_distance REAL DEFAULT 0,       -- Maior distância de tiro em metros
    longest_shot_weapon TEXT,                   -- Nome da arma usada no tiro mais longo
    longest_shot_timestamp DATETIME,            -- Data/hora do tiro mais longo
    
    -- Suicides
    suicides INTEGER DEFAULT 0,                 -- Total de suicídios (event_type='suicide')
    
    -- ==========================================
    -- minigame_events
    -- ==========================================
    -- Lockpicking Raid
    lockpick_success INTEGER DEFAULT 0,         -- Sucessos (success=1 AND minigame_type='LockpickingMinigame_C')
    lockpick_fails INTEGER DEFAULT 0,           -- Falhas (success=0 AND minigame_type='LockpickingMinigame_C')
    lockpick_total INTEGER DEFAULT 0,           -- Total de tentativas (success + fails) - CALCULADO
    lockpick_success_rate REAL DEFAULT 0,       -- Taxa de sucesso % ((success / total) * 100) - CALCULADO
    
    -- ==========================================
    -- vehicle_destruction_events
    -- ==========================================
    vehicles_destroyed INTEGER DEFAULT 0,       -- Total de veículos destruídos
    
    -- ==========================================
    -- survival_stats_snapshot
    -- ==========================================
    -- Maior Cagão
    highest_defecation INTEGER DEFAULT 0,       -- Maior valor de total_defecations
    
    -- Caça
    animals_killed INTEGER DEFAULT 0,           -- Total de animais mortos (animals_killed)
    
    -- Master Bruce Lee (Nocautes)
    players_knocked_out INTEGER DEFAULT 0,      -- Total de nocautes em jogadores
    
    -- Headshots
    headshots INTEGER DEFAULT 0,                -- Total de headshots
    
    -- Minutos Sobrevividos
    minutes_survived REAL DEFAULT 0,            -- Maior tempo de sobrevivência em minutos
    
    -- Overdoses
    overdoses INTEGER DEFAULT 0,                -- Total de overdoses (overdose)
    
    -- Hulk - Maior Peso Carregado
    highest_weight_carried REAL DEFAULT 0,      -- Maior peso já carregado em kg
    
    -- ==========================================
    -- player_fame_totals
    -- ==========================================
    total_fame REAL DEFAULT 0,                  -- Total de fama do jogador (de player_fame_totals)
    
    -- ==========================================
    -- METADATA
    -- ==========================================
    last_updated DATETIME DEFAULT CURRENT_TIMESTAMP,  -- Última atualização dos dados
    
    -- Constraint
    UNIQUE(steam_id)
);
```

## 📋 Descrição das Colunas por Fonte de Dados

### Estrutura Organizada por Tabela de Origem

A tabela está organizada agrupando as colunas por **fonte de dados**, facilitando:
- ✅ Manutenção e entendimento da origem dos dados
- ✅ Identificação rápida de onde cada métrica vem
- ✅ Organização lógica e visual clara
- ✅ Facilita futuras alterações ou adições

## 📋 Descrição das Colunas por Ranking

| # | Ranking | Coluna | Tipo | Fonte | Descrição |
|---|---------|--------|------|-------|-----------|
| 1 | Kills | `kills` | INTEGER | `kill_events` | Total de kills PvP (exclui NPCs) |
| 1 | Deaths | `deaths` | INTEGER | `kill_events` | Total de mortes |
| 1 | KDR | `kdr` | REAL | Calculado | Ratio Kills/Deaths |
| 2 | Longest Shot | `longest_shot_distance` | REAL | `kill_events` | Maior distância (metros) |
| 2 | Longest Shot | `longest_shot_weapon` | TEXT | `kill_events` | Arma do tiro mais longo |
| 3 | Lockpicking Success | `lockpick_success` | INTEGER | `minigame_events` | Sucessos |
| 3 | Lockpicking Fails | `lockpick_fails` | INTEGER | `minigame_events` | Falhas |
| 3 | Lockpicking Total | `lockpick_total` | INTEGER | Calculado | Total tentativas |
| 3 | Lockpicking Rate | `lockpick_success_rate` | REAL | Calculado | % de sucesso |
| 4 | Suicides | `suicides` | INTEGER | `kill_events` | Total suicídios |
| 5 | Maior Cagão | `highest_defecation` | INTEGER | `survival_stats_snapshot` | Máximo `total_defecations` |
| 6 | Vehicle Destruction | `vehicles_destroyed` | INTEGER | `vehicle_destruction_events` | Total destruídos |
| 7 | Caça | `animals_killed` | INTEGER | `survival_stats_snapshot` | Total `animals_killed` |
| 8 | Master Bruce Lee | `players_knocked_out` | INTEGER | `survival_stats_snapshot` | Total `players_knocked_out` |
| 9 | Headshots | `headshots` | INTEGER | `survival_stats_snapshot` | Total `headshots` |
| 10 | Survival Time | `minutes_survived` | REAL | `survival_stats_snapshot` | Máximo `minutes_survived` |
| 11 | Overdoses | `overdoses` | INTEGER | `survival_stats_snapshot` | Total `overdose` |
| 12 | Hulk (Weight) | `highest_weight_carried` | REAL | `survival_stats_snapshot` | Máximo `highest_weight_carried` |
| 13 | Fama | `total_fame` | REAL | `player_fame_totals` | Total de fama acumulada |

## 🔍 Índices para Performance

```sql
-- Índice principal para buscas por jogador
CREATE INDEX IF NOT EXISTS idx_rankings_steam_id ON rankings(steam_id);

-- Índices para ordenação dos rankings (DESC = maior para menor)
CREATE INDEX IF NOT EXISTS idx_rankings_kills ON rankings(kills DESC);
CREATE INDEX IF NOT EXISTS idx_rankings_deaths ON rankings(deaths DESC);
CREATE INDEX IF NOT EXISTS idx_rankings_kdr ON rankings(kdr DESC);
CREATE INDEX IF NOT EXISTS idx_rankings_longest_shot ON rankings(longest_shot_distance DESC);
CREATE INDEX IF NOT EXISTS idx_rankings_lockpick_success ON rankings(lockpick_success DESC);
CREATE INDEX IF NOT EXISTS idx_rankings_lockpick_success_rate ON rankings(lockpick_success_rate DESC);
CREATE INDEX IF NOT EXISTS idx_rankings_suicides ON rankings(suicides DESC);
CREATE INDEX IF NOT EXISTS idx_rankings_highest_defecation ON rankings(highest_defecation DESC);
CREATE INDEX IF NOT EXISTS idx_rankings_vehicles_destroyed ON rankings(vehicles_destroyed DESC);
CREATE INDEX IF NOT EXISTS idx_rankings_animals_killed ON rankings(animals_killed DESC);
CREATE INDEX IF NOT EXISTS idx_rankings_players_knocked_out ON rankings(players_knocked_out DESC);
CREATE INDEX IF NOT EXISTS idx_rankings_headshots ON rankings(headshots DESC);
CREATE INDEX IF NOT EXISTS idx_rankings_minutes_survived ON rankings(minutes_survived DESC);
CREATE INDEX IF NOT EXISTS idx_rankings_overdoses ON rankings(overdoses DESC);
CREATE INDEX IF NOT EXISTS idx_rankings_highest_weight ON rankings(highest_weight_carried DESC);
CREATE INDEX IF NOT EXISTS idx_rankings_total_fame ON rankings(total_fame DESC);

-- Índice para verificar última atualização
CREATE INDEX IF NOT EXISTS idx_rankings_last_updated ON rankings(last_updated DESC);
```

## 📊 Exemplo de Dados

```sql
INSERT INTO rankings (
    steam_id, 
    player_name,
    kills, 
    deaths, 
    kdr,
    longest_shot_distance,
    longest_shot_weapon,
    lockpick_success,
    lockpick_fails,
    lockpick_total,
    lockpick_success_rate,
    suicides,
    highest_defecation,
    vehicles_destroyed,
    animals_killed,
    players_knocked_out,
    headshots,
    minutes_survived,
    overdoses,
    highest_weight_carried,
    last_updated
) VALUES (
    '76561198040636105',
    'Pedreiro',
    150,           -- kills
    25,            -- deaths
    6.0,           -- kdr
    125.50,        -- longest_shot_distance
    'Weapon_AK47_C',  -- longest_shot_weapon
    45,            -- lockpick_success
    12,            -- lockpick_fails
    57,            -- lockpick_total
    78.95,         -- lockpick_success_rate (%)
    3,             -- suicides
    250,           -- highest_defecation
    5,             -- vehicles_destroyed
    87,            -- animals_killed
    23,            -- players_knocked_out
    142,           -- headshots
    5000.5,        -- minutes_survived
    8,             -- overdoses
    45.7,          -- highest_weight_carried
    '2025-01-15 03:00:00'  -- last_updated
);
```

## 🔄 Constraints e Regras

1. **UNIQUE(steam_id)**: Cada jogador aparece apenas uma vez na tabela
2. **DEFAULT 0**: Todos os valores numéricos começam em 0
3. **DEFAULT CURRENT_TIMESTAMP**: `last_updated` é preenchido automaticamente
4. **NOT NULL**: `steam_id` e `player_name` são obrigatórios

## 📈 Campos Calculados

Alguns campos são calculados automaticamente durante a atualização:

- **`kdr`**: `kills / deaths` (ou `kills` se `deaths = 0`)
- **`lockpick_total`**: `lockpick_success + lockpick_fails`
- **`lockpick_success_rate`**: `(lockpick_success / lockpick_total) * 100`

## 🎯 Estratégia de Atualização

- **Frequência**: A cada 24 horas
- **Método**: `INSERT OR REPLACE` (atualiza se existe, cria se não existe)
- **Escopo**: Dados acumulados (todos os tempos)
- **Performance**: Índices otimizados para ordenação rápida

