# 🏆 Proposta: Sistema de Rankings

## 📋 Visão Geral

Sistema completo de rankings para exibir estatísticas e classificações dos jogadores em diferentes categorias do SCUM.

## 🎯 Objetivos

- ✅ Criar rankings em tempo real ou materializados
- ✅ Agregar dados de múltiplas tabelas
- ✅ Performance otimizada para consultas
- ✅ Atualização automática ou sob demanda
- ✅ Interface simples para frontend

## 📊 Rankings Solicitados

### 1. **Kills e Deaths** (kill_events)
- **Deaths**: Contar `victim_steam_id` onde `event_type = 'kill'`
- **Kills**: Contar `killer_steam_id` onde `event_type = 'kill' AND killer_is_npc = 0`
- **KDR**: Kills / Deaths

### 2. **Tiro de Maior Distância** (kill_events)
- **Weapon**: Arma usada
- **Distance**: Distância máxima do tiro (campo `distance`)
- **Jogador**: `killer_steam_id` e `killer_profile_name`

### 3. **Raid Lockpicking** (minigame_events)
- **Success**: Contar `success = 1` onde `minigame_type = 'LockpickingMinigame_C'`
- **Fails**: Contar `success = 0` onde `minigame_type = 'LockpickingMinigame_C'`
- **Total**: Success + Fails
- **% Success**: (Success / Total) * 100

### 4. **Suicídios** (kill_events)
- **Total**: Contar `event_type = 'suicide'` agrupado por `victim_steam_id`

### 5. **Maior Cagão** (survival_stats_snapshot)
- **Métrica**: Maior valor de defecações (procurar coluna relacionada a `poop`, `defecation`, `stool`, etc.)
- **Jogador**: `steam_id` e `player_name`

### 6. **Destruição de Veículos** (vehicle_destruction_events)
- **Total**: Contar eventos agrupados por `owner_steam_id`
- **Tipo de evento**: Pode filtrar por `event_type` (Destroyed, Disappeared, VehicleInactiveTimerReached)

### 7. **Caça** (survival_stats_snapshot)
- **Métrica**: Soma de `animals_killed` (ou similar)
- **Jogador**: `steam_id` e `player_name`

### 8. **Master Bruce Lee (Nocautes)** (survival_stats_snapshot)
- **Métrica**: `players_knocked_out` ✅ (CONFIRMADO)
- **Jogador**: `steam_id` e `player_name`

### 9. **Headshots** (survival_stats_snapshot)
- **Métrica**: `headshots`
- **Jogador**: `steam_id` e `player_name`

### 10. **Minutos Sobrevividos** (survival_stats_snapshot)
- **Métrica**: `minutes_survived` (maior valor)
- **Jogador**: `steam_id` e `player_name`

### 11. **Overdoses** (survival_stats_snapshot)
- **Métrica**: Coluna relacionada a overdoses (verificar nome exato)
- **Jogador**: `steam_id` e `player_name`

### 12. **Hulk (Maior Peso Carregado)** (survival_stats_snapshot)
- **Métrica**: `highest_weight_carried` ou similar (verificar coluna exata)
- **Jogador**: `steam_id` e `player_name`

## 🏗️ Arquitetura Proposta

### Opção 1: Views SQL (Tempo Real) ⚡

**Vantagens:**
- ✅ Sempre atualizado
- ✅ Sem necessidade de atualização manual
- ✅ Dados sempre corretos

**Desvantagens:**
- ⚠️ Pode ser mais lento com muitos dados
- ⚠️ Não cacheado

**Estrutura:**
```sql
-- View para Ranking de Kills/Deaths
CREATE VIEW ranking_kills_deaths AS
SELECT 
    steam_id,
    player_name,
    COUNT(CASE WHEN event_type = 'kill' AND killer_is_npc = 0 THEN 1 END) as kills,
    COUNT(CASE WHEN victim_steam_id = steam_id AND event_type = 'kill' THEN 1 END) as deaths,
    CASE 
        WHEN COUNT(CASE WHEN victim_steam_id = steam_id AND event_type = 'kill' THEN 1 END) > 0
        THEN CAST(COUNT(CASE WHEN event_type = 'kill' AND killer_is_npc = 0 THEN 1 END) AS REAL) / 
             COUNT(CASE WHEN victim_steam_id = steam_id AND event_type = 'kill' THEN 1 END)
        ELSE CAST(COUNT(CASE WHEN event_type = 'kill' AND killer_is_npc = 0 THEN 1 END) AS REAL)
    END as kdr
FROM (
    SELECT killer_steam_id as steam_id, killer_profile_name as player_name, event_type, killer_is_npc, victim_steam_id
    FROM kill_events
    WHERE killer_steam_id IS NOT NULL
    UNION ALL
    SELECT victim_steam_id as steam_id, victim_name as player_name, event_type, 0 as killer_is_npc, victim_steam_id
    FROM kill_events
    WHERE victim_steam_id IS NOT NULL
)
GROUP BY steam_id, player_name;
```

### Opção 2: Tabela Materializada (Cache) 📦

**Vantagens:**
- ✅ Performance muito melhor
- ✅ Pode ser atualizada periodicamente
- ✅ Consultas rápidas

**Desvantagens:**
- ⚠️ Precisa ser atualizada periodicamente
- ⚠️ Dados podem estar desatualizados entre atualizações

**Estrutura:**
```sql
CREATE TABLE rankings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    steam_id TEXT NOT NULL,
    player_name TEXT NOT NULL,
    
    -- Kills/Deaths
    kills INTEGER DEFAULT 0,
    deaths INTEGER DEFAULT 0,
    kdr REAL DEFAULT 0,
    
    -- Longest Shot
    longest_shot_distance REAL DEFAULT 0,
    longest_shot_weapon TEXT,
    
    -- Lockpicking
    lockpick_success INTEGER DEFAULT 0,
    lockpick_fails INTEGER DEFAULT 0,
    lockpick_total INTEGER DEFAULT 0,
    lockpick_success_rate REAL DEFAULT 0,
    
    -- Suicides
    suicides INTEGER DEFAULT 0,
    
    -- Survival Stats (do snapshot mais recente)
    highest_defecation REAL DEFAULT 0,
    vehicles_destroyed INTEGER DEFAULT 0,
    animals_killed INTEGER DEFAULT 0,
    melee_kills INTEGER DEFAULT 0,
    headshots INTEGER DEFAULT 0,
    minutes_survived REAL DEFAULT 0,
    overdoses INTEGER DEFAULT 0,
    highest_weight_carried REAL DEFAULT 0,
    
    -- Metadata
    last_updated DATETIME DEFAULT CURRENT_TIMESTAMP,
    
    UNIQUE(steam_id)
);

CREATE INDEX idx_rankings_steam_id ON rankings(steam_id);
CREATE INDEX idx_rankings_kills ON rankings(kills DESC);
CREATE INDEX idx_rankings_deaths ON rankings(deaths DESC);
CREATE INDEX idx_rankings_kdr ON rankings(kdr DESC);
CREATE INDEX idx_rankings_longest_shot ON rankings(longest_shot_distance DESC);
CREATE INDEX idx_rankings_lockpick_success ON rankings(lockpick_success DESC);
CREATE INDEX idx_rankings_suicides ON rankings(suicides DESC);
```

### Opção 3: Híbrida (Recomendada) 🎯

**Estrutura:**
- Tabela `rankings` para cache de dados frequentes
- Views SQL para rankings que mudam muito ou são complexos
- Job agendado para atualizar a tabela periodicamente

## 📝 Proposta Detalhada: Opção Híbrida

### Tabela Principal: `rankings`

```sql
CREATE TABLE rankings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    steam_id TEXT NOT NULL,
    player_name TEXT NOT NULL,
    
    -- 1. Kills/Deaths (kill_events)
    kills INTEGER DEFAULT 0,
    deaths INTEGER DEFAULT 0,
    kdr REAL DEFAULT 0,
    
    -- 2. Longest Shot (kill_events)
    longest_shot_distance REAL DEFAULT 0,
    longest_shot_weapon TEXT,
    longest_shot_timestamp DATETIME,
    
    -- 3. Lockpicking (minigame_events)
    lockpick_success INTEGER DEFAULT 0,
    lockpick_fails INTEGER DEFAULT 0,
    lockpick_total INTEGER DEFAULT 0,
    lockpick_success_rate REAL DEFAULT 0,
    
    -- 4. Suicides (kill_events)
    suicides INTEGER DEFAULT 0,
    
    -- 5. Maior Cagão (survival_stats_snapshot)
    highest_defecation REAL DEFAULT 0,
    
    -- 6. Vehicle Destruction (vehicle_destruction_events)
    vehicles_destroyed INTEGER DEFAULT 0,
    
    -- 7. Hunting (survival_stats_snapshot)
    animals_killed INTEGER DEFAULT 0,
    
    -- 8. Master Bruce Lee - Nocautes (survival_stats_snapshot)
    players_knocked_out INTEGER DEFAULT 0,
    
    -- 9. Headshots (survival_stats_snapshot)
    headshots INTEGER DEFAULT 0,
    
    -- 10. Minutes Survived (survival_stats_snapshot)
    minutes_survived REAL DEFAULT 0,
    
    -- 11. Overdoses (survival_stats_snapshot)
    overdoses INTEGER DEFAULT 0,
    
    -- 12. Highest Weight (survival_stats_snapshot)
    highest_weight_carried REAL DEFAULT 0,
    
    -- Metadata
    last_updated DATETIME DEFAULT CURRENT_TIMESTAMP,
    
    UNIQUE(steam_id)
);
```

### Índices para Performance

```sql
CREATE INDEX idx_rankings_steam_id ON rankings(steam_id);
CREATE INDEX idx_rankings_kills ON rankings(kills DESC);
CREATE INDEX idx_rankings_deaths ON rankings(deaths DESC);
CREATE INDEX idx_rankings_kdr ON rankings(kdr DESC);
CREATE INDEX idx_rankings_longest_shot ON rankings(longest_shot_distance DESC);
CREATE INDEX idx_rankings_lockpick_success ON rankings(lockpick_success DESC);
CREATE INDEX idx_rankings_lockpick_success_rate ON rankings(lockpick_success_rate DESC);
CREATE INDEX idx_rankings_suicides ON rankings(suicides DESC);
CREATE INDEX idx_rankings_vehicles_destroyed ON rankings(vehicles_destroyed DESC);
CREATE INDEX idx_rankings_animals_killed ON rankings(animals_killed DESC);
CREATE INDEX idx_rankings_players_knocked_out ON rankings(players_knocked_out DESC);
CREATE INDEX idx_rankings_headshots ON rankings(headshots DESC);
CREATE INDEX idx_rankings_minutes_survived ON rankings(minutes_survived DESC);
CREATE INDEX idx_rankings_highest_defecation ON rankings(highest_defecation DESC);
CREATE INDEX idx_rankings_overdoses ON rankings(overdoses DESC);
CREATE INDEX idx_rankings_highest_weight ON rankings(highest_weight_carried DESC);
CREATE INDEX idx_rankings_last_updated ON rankings(last_updated DESC);
```

### Stored Procedures / Funções Python

#### Atualização de Rankings

```python
def update_rankings(db_path: str):
    """Atualizar tabela de rankings com dados mais recentes"""
    
    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()
        
        # 1. Kills e Deaths
        cursor.execute("""
            INSERT OR REPLACE INTO rankings (steam_id, player_name, kills, deaths, kdr)
            SELECT 
                steam_id,
                player_name,
                kills,
                deaths,
                CASE WHEN deaths > 0 THEN CAST(kills AS REAL) / deaths ELSE kills END as kdr
            FROM (
                SELECT 
                    COALESCE(killer.steam_id, victim.steam_id) as steam_id,
                    COALESCE(killer.name, victim.name) as player_name,
                    COALESCE(killer.kills, 0) as kills,
                    COALESCE(victim.deaths, 0) as deaths
                FROM (
                    SELECT 
                        killer_steam_id as steam_id,
                        killer_profile_name as name,
                        COUNT(*) as kills
                    FROM kill_events
                    WHERE event_type = 'kill' 
                      AND killer_is_npc = 0
                      AND killer_steam_id IS NOT NULL
                    GROUP BY killer_steam_id, killer_profile_name
                ) killer
                FULL OUTER JOIN (
                    SELECT 
                        victim_steam_id as steam_id,
                        victim_name as name,
                        COUNT(*) as deaths
                    FROM kill_events
                    WHERE event_type = 'kill'
                      AND victim_steam_id IS NOT NULL
                    GROUP BY victim_steam_id, victim_name
                ) victim ON killer.steam_id = victim.steam_id
            )
        """)
        
        # 2. Longest Shot
        cursor.execute("""
            UPDATE rankings
            SET 
                longest_shot_distance = (
                    SELECT MAX(distance)
                    FROM kill_events
                    WHERE killer_steam_id = rankings.steam_id
                      AND distance IS NOT NULL
                ),
                longest_shot_weapon = (
                    SELECT weapon
                    FROM kill_events
                    WHERE killer_steam_id = rankings.steam_id
                      AND distance = (
                          SELECT MAX(distance)
                          FROM kill_events
                          WHERE killer_steam_id = rankings.steam_id
                      )
                    LIMIT 1
                )
            WHERE steam_id IN (
                SELECT DISTINCT killer_steam_id
                FROM kill_events
                WHERE killer_steam_id IS NOT NULL
            )
        """)
        
        # 3. Lockpicking
        cursor.execute("""
            UPDATE rankings
            SET 
                lockpick_success = (
                    SELECT COUNT(*)
                    FROM minigame_events
                    WHERE steam_id = rankings.steam_id
                      AND minigame_type = 'LockpickingMinigame_C'
                      AND success = 1
                ),
                lockpick_fails = (
                    SELECT COUNT(*)
                    FROM minigame_events
                    WHERE steam_id = rankings.steam_id
                      AND minigame_type = 'LockpickingMinigame_C'
                      AND success = 0
                )
            WHERE steam_id IN (
                SELECT DISTINCT steam_id
                FROM minigame_events
                WHERE minigame_type = 'LockpickingMinigame_C'
            )
        """)
        
        # Calcular total e taxa de sucesso
        cursor.execute("""
            UPDATE rankings
            SET 
                lockpick_total = lockpick_success + lockpick_fails,
                lockpick_success_rate = CASE 
                    WHEN (lockpick_success + lockpick_fails) > 0 
                    THEN CAST(lockpick_success AS REAL) / (lockpick_success + lockpick_fails) * 100
                    ELSE 0
                END
        """)
        
        # 4. Suicides
        cursor.execute("""
            UPDATE rankings
            SET suicides = (
                SELECT COUNT(*)
                FROM kill_events
                WHERE victim_steam_id = rankings.steam_id
                  AND event_type = 'suicide'
            )
            WHERE steam_id IN (
                SELECT DISTINCT victim_steam_id
                FROM kill_events
                WHERE event_type = 'suicide'
            )
        """)
        
        # 5-12. Survival Stats (do snapshot mais recente)
        cursor.execute("""
            UPDATE rankings
            SET 
                highest_defecation = (SELECT MAX(total_defecations) FROM survival_stats_snapshot WHERE steam_id = rankings.steam_id),
                animals_killed = (SELECT MAX(animals_killed) FROM survival_stats_snapshot WHERE steam_id = rankings.steam_id),
                melee_kills = (SELECT MAX(players_knocked_out) FROM survival_stats_snapshot WHERE steam_id = rankings.steam_id),
                headshots = (SELECT MAX(headshots) FROM survival_stats_snapshot WHERE steam_id = rankings.steam_id),
                minutes_survived = (SELECT MAX(minutes_survived) FROM survival_stats_snapshot WHERE steam_id = rankings.steam_id),
                overdoses = (SELECT MAX(overdose) FROM survival_stats_snapshot WHERE steam_id = rankings.steam_id),
                highest_weight_carried = (SELECT MAX(highest_weight_carried) FROM survival_stats_snapshot WHERE steam_id = rankings.steam_id)
            WHERE steam_id IN (
                SELECT DISTINCT steam_id
                FROM survival_stats_snapshot
            )
        """)
        
        # 6. Vehicle Destruction
        cursor.execute("""
            UPDATE rankings
            SET vehicles_destroyed = (
                SELECT COUNT(*)
                FROM vehicle_destruction_events
                WHERE owner_steam_id = rankings.steam_id
            )
            WHERE steam_id IN (
                SELECT DISTINCT owner_steam_id
                FROM vehicle_destruction_events
            )
        """)
        
        # Atualizar timestamp
        cursor.execute("UPDATE rankings SET last_updated = CURRENT_TIMESTAMP")
        
        conn.commit()
```

## 🚀 Implementação

### Passos Sugeridos:

1. ✅ **Criar tabela `rankings`** no banco de dados
2. ✅ **Verificar nomes exatos das colunas** em `survival_stats_snapshot` (CONCLUÍDO)
3. **Implementar função de atualização** (`update_rankings`)
4. **Criar endpoint API** para buscar rankings:
   - `GET /api/rankings?category=kills&limit=10&offset=0`
5. ✅ **Configurar atualização automática** (job agendado):
   - **A cada 24 horas** ✅ (CONFIRMADO)
   - Atualização diária automática via scheduler
   - Opção de atualização manual via API se necessário
   - Horário configurável (ex: 03:00 AM)
6. **Frontend**: Criar interface de rankings

### ⏰ Agendamento de Atualização

A atualização será executada **automaticamente a cada 24 horas** usando um scheduler (similar ao `SurvivalStatsSyncService`).

**Vantagens de atualização a cada 24h:**
- ✅ **Performance**: Não sobrecarrega o banco com queries frequentes
- ✅ **Consistência**: Dados consolidados uma vez por dia
- ✅ **Eficiência**: Rankings não precisam ser calculados em tempo real
- ✅ **Recursos**: Economiza recursos do servidor

**Implementação sugerida:**
```python
# Usar biblioteca 'schedule' (já utilizada no projeto)
import schedule
import time

def schedule_rankings_update():
    """Agendar atualização de rankings a cada 24 horas"""
    # Atualizar todos os dias às 03:00 AM
    schedule.every().day.at("03:00").do(update_rankings, db_path)
    
    # Ou a cada 24 horas desde o último update
    # schedule.every(24).hours.do(update_rankings, db_path)
```

**Atualização manual (opcional):**
- Endpoint: `POST /api/rankings/update`
- Força atualização imediata se necessário
- Útil para testes ou atualização após eventos importantes

## 📊 Endpoint API Proposto

```
GET /api/rankings
```

**Query Parameters:**
- `category`: `kills` | `deaths` | `kdr` | `longest_shot` | `lockpick` | `suicides` | `defecation` | `vehicles` | `hunting` | `melee` | `headshots` | `survival_time` | `overdoses` | `weight`
- `limit`: número de resultados (padrão: 20)
- `offset`: paginação (padrão: 0)

**Response:**
```json
{
  "success": true,
  "data": {
    "category": "kills",
    "players": [
      {
        "position": 1,
        "steam_id": "76561198040636105",
        "player_name": "Pedreiro",
        "value": 150,
        "kills": 150,
        "deaths": 25,
        "kdr": 6.0
      }
    ],
    "total": 50,
    "limit": 20,
    "offset": 0
  }
}
```

## ✅ Colunas Confirmadas em `survival_stats_snapshot`

Após consulta ao banco de dados, os nomes exatos das colunas são:

1. **Defecação (Maior Cagão)**: `total_defecations` ✅
2. **Melee Kills (Master Bruce Lee)**: `players_knocked_out` ✅ (CONFIRMADO)
3. **Overdoses**: `overdose` ✅
4. **Maior Peso Carregado (Hulk)**: `highest_weight_carried` ✅
5. **Caça (Animals)**: `animals_killed` ✅
6. **Headshots**: `headshots` ✅
7. **Minutos Sobrevividos**: `minutes_survived` ✅

2. ✅ **Frequência de atualização**: **A cada 24 horas** (CONFIRMADO)
   - Job agendado para atualizar automaticamente
   - Pode ser atualizado manualmente via API se necessário
   - Performance otimizada - não sobrecarrega o banco
   - Atualização diária garante dados sempre atualizados sem impacto na performance

3. **Escopo dos rankings**:
   - ✅ **Todos os tempos** (recomendado) - histórico completo
   - Opcionalmente pode filtrar por período se necessário no futuro
   - A tabela `rankings` sempre reflete dados totais acumulados

4. **Tratamento de jogadores sem nome/steam_id**:
   - Como tratar NPCs?
   - Como tratar jogadores deletados?

## 📌 Próximos Passos

1. ✅ Validar nomes das colunas em `survival_stats_snapshot`
2. ✅ Decidir frequência de atualização
3. ✅ Implementar tabela e funções de atualização
4. ✅ Criar endpoints API
5. ✅ Testar com dados reais
6. ✅ Integrar frontend

