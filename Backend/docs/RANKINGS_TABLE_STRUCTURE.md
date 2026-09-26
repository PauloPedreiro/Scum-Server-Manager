# 📊 Estrutura da Tabela `rankings` - Visão Organizada

## 🎯 Conceito

**Uma linha por jogador** com todas as métricas agregadas, organizadas por **fonte de dados**.

## 📋 Estrutura Visual

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    IDENTIFICAÇÃO DO JOGADOR                              │
├─────────────────────────────────────────────────────────────────────────┤
│ id | steam_id | player_name                                             │
└─────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────┐
│                         kill_events                                      │
├─────────────────────────────────────────────────────────────────────────┤
│ kills | deaths | kdr | longest_shot_distance | longest_shot_weapon |    │
│ longest_shot_timestamp | suicides                                         │
└─────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────┐
│                       minigame_events                                    │
├─────────────────────────────────────────────────────────────────────────┤
│ lockpick_success | lockpick_fails | lockpick_total |                    │
│ lockpick_success_rate                                                   │
└─────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────┐
│                  vehicle_destruction_events                              │
├─────────────────────────────────────────────────────────────────────────┤
│ vehicles_destroyed                                                       │
└─────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────┐
│                    survival_stats_snapshot                               │
├─────────────────────────────────────────────────────────────────────────┤
│ highest_defecation | animals_killed | players_knocked_out | headshots | │
│ minutes_survived | overdoses | highest_weight_carried                   │
└─────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────┐
│                            METADATA                                      │
├─────────────────────────────────────────────────────────────────────────┤
│ last_updated                                                             │
└─────────────────────────────────────────────────────────────────────────┘
```

## 📊 Schema SQL Organizado

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
    kills INTEGER DEFAULT 0,
    deaths INTEGER DEFAULT 0,
    kdr REAL DEFAULT 0,
    longest_shot_distance REAL DEFAULT 0,
    longest_shot_weapon TEXT,
    longest_shot_timestamp DATETIME,
    suicides INTEGER DEFAULT 0,
    
    -- ==========================================
    -- minigame_events
    -- ==========================================
    lockpick_success INTEGER DEFAULT 0,
    lockpick_fails INTEGER DEFAULT 0,
    lockpick_total INTEGER DEFAULT 0,
    lockpick_success_rate REAL DEFAULT 0,
    
    -- ==========================================
    -- vehicle_destruction_events
    -- ==========================================
    vehicles_destroyed INTEGER DEFAULT 0,
    
    -- ==========================================
    -- survival_stats_snapshot
    -- ==========================================
    highest_defecation INTEGER DEFAULT 0,
    animals_killed INTEGER DEFAULT 0,
    players_knocked_out INTEGER DEFAULT 0,
    headshots INTEGER DEFAULT 0,
    minutes_survived REAL DEFAULT 0,
    overdoses INTEGER DEFAULT 0,
    highest_weight_carried REAL DEFAULT 0,
    
    -- ==========================================
    -- METADATA
    -- ==========================================
    last_updated DATETIME DEFAULT CURRENT_TIMESTAMP,
    
    UNIQUE(steam_id)
);
```

## 📈 Mapeamento: Coluna → Fonte de Dados

| Coluna | Fonte | Tabela de Origem | Método de Cálculo |
|--------|-------|------------------|-------------------|
| `steam_id` | Identificação | Várias | - |
| `player_name` | Identificação | Várias | - |
| `kills` | kill_events | kill_events | COUNT(*) WHERE killer_steam_id = X AND event_type='kill' AND killer_is_npc=0 |
| `deaths` | kill_events | kill_events | COUNT(*) WHERE victim_steam_id = X AND event_type='kill' |
| `kdr` | kill_events | kill_events | CALCULADO: kills / deaths |
| `longest_shot_distance` | kill_events | kill_events | MAX(distance) WHERE killer_steam_id = X |
| `longest_shot_weapon` | kill_events | kill_events | weapon WHERE distance = MAX(distance) |
| `longest_shot_timestamp` | kill_events | kill_events | timestamp WHERE distance = MAX(distance) |
| `suicides` | kill_events | kill_events | COUNT(*) WHERE victim_steam_id = X AND event_type='suicide' |
| `lockpick_success` | minigame_events | minigame_events | COUNT(*) WHERE steam_id = X AND minigame_type='LockpickingMinigame_C' AND success=1 |
| `lockpick_fails` | minigame_events | minigame_events | COUNT(*) WHERE steam_id = X AND minigame_type='LockpickingMinigame_C' AND success=0 |
| `lockpick_total` | minigame_events | minigame_events | CALCULADO: success + fails |
| `lockpick_success_rate` | minigame_events | minigame_events | CALCULADO: (success / total) * 100 |
| `vehicles_destroyed` | vehicle_destruction_events | vehicle_destruction_events | COUNT(*) WHERE owner_steam_id = X |
| `highest_defecation` | survival_stats_snapshot | survival_stats_snapshot | MAX(total_defecations) WHERE steam_id = X |
| `animals_killed` | survival_stats_snapshot | survival_stats_snapshot | MAX(animals_killed) WHERE steam_id = X |
| `players_knocked_out` | survival_stats_snapshot | survival_stats_snapshot | MAX(players_knocked_out) WHERE steam_id = X |
| `headshots` | survival_stats_snapshot | survival_stats_snapshot | MAX(headshots) WHERE steam_id = X |
| `minutes_survived` | survival_stats_snapshot | survival_stats_snapshot | MAX(minutes_survived) WHERE steam_id = X |
| `overdoses` | survival_stats_snapshot | survival_stats_snapshot | MAX(overdose) WHERE steam_id = X |
| `highest_weight_carried` | survival_stats_snapshot | survival_stats_snapshot | MAX(highest_weight_carried) WHERE steam_id = X |
| `last_updated` | Sistema | - | CURRENT_TIMESTAMP |

## 🎯 Vantagens desta Estrutura

1. **Organização Clara**: Fácil identificar de onde vem cada dado
2. **Manutenção Simplificada**: Alterações em uma fonte não afetam outras seções
3. **Documentação Visual**: A estrutura SQL é auto-documentada
4. **Uma Linha por Jogador**: Ideal para rankings e consultas rápidas
5. **Agregação Eficiente**: Todos os dados consolidados em um único lugar

## 📊 Exemplo de Dados (Uma Linha por Jogador)

```sql
SELECT 
    -- Identificação
    steam_id,
    player_name,
    
    -- kill_events
    kills,
    deaths,
    kdr,
    longest_shot_distance,
    longest_shot_weapon,
    suicides,
    
    -- minigame_events
    lockpick_success,
    lockpick_fails,
    lockpick_total,
    lockpick_success_rate,
    
    -- vehicle_destruction_events
    vehicles_destroyed,
    
    -- survival_stats_snapshot
    highest_defecation,
    animals_killed,
    players_knocked_out,
    headshots,
    minutes_survived,
    overdoses,
    highest_weight_carried,
    
    -- Metadata
    last_updated
    
FROM rankings
WHERE steam_id = '76561198040636105';
```

Resultado:
```
steam_id: 76561198040636105
player_name: Pedreiro

kill_events:
  - kills: 150
  - deaths: 25
  - kdr: 6.0
  - longest_shot_distance: 125.50
  - longest_shot_weapon: Weapon_AK47_C
  - suicides: 3

minigame_events:
  - lockpick_success: 45
  - lockpick_fails: 12
  - lockpick_total: 57
  - lockpick_success_rate: 78.95

vehicle_destruction_events:
  - vehicles_destroyed: 5

survival_stats_snapshot:
  - highest_defecation: 250
  - animals_killed: 87
  - players_knocked_out: 23
  - headshots: 142
  - minutes_survived: 5000.5
  - overdoses: 8
  - highest_weight_carried: 45.7

last_updated: 2025-01-15 03:00:00
```

## 🔄 Atualização por Fonte

A função de atualização pode ser organizada para atualizar por grupos:

```python
def update_rankings(db_path: str):
    """Atualizar rankings agrupado por fonte de dados"""
    
    # 1. Atualizar dados de kill_events
    update_kill_events_rankings(db_path)
    
    # 2. Atualizar dados de minigame_events
    update_minigame_events_rankings(db_path)
    
    # 3. Atualizar dados de vehicle_destruction_events
    update_vehicle_destruction_rankings(db_path)
    
    # 4. Atualizar dados de survival_stats_snapshot
    update_survival_stats_rankings(db_path)
    
    # 5. Atualizar campos calculados
    update_calculated_fields(db_path)
```


