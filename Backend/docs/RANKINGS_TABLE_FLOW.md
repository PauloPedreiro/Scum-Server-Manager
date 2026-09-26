# 📊 Fluxo da Tabela `rankings` - SSM.db

## 🎯 Visão Geral

A tabela `rankings` é uma **tabela de cache materializada** que armazena dados agregados de múltiplas fontes para permitir consultas rápidas de rankings. Ela é atualizada periodicamente através do serviço `RankingsUpdateService`.

---

## 🔄 Fluxo Completo

### **1. Inicialização do Sistema**

```
Aplicação inicia (main.py)
    ↓
RankingsUpdateService é inicializado
    ↓
Verifica se está habilitado no config.json
    ↓
Se auto_start = true, inicia automaticamente
```

**Arquivo**: `main.py` (linhas 206-210)

```python
rankings_update_service = RankingsUpdateService(config, path_helper, logger)
```

**Configuração** (`config.json`):
```json
{
  "rankings_sync": {
    "enabled": true,
    "auto_start": true,
    "update_interval_hours": 24,
    "update_time": "03:00"
  }
}
```

---

### **2. Agendamento da Atualização**

O serviço usa a biblioteca `schedule` para agendar atualizações diárias:

```
RankingsUpdateService.start()
    ↓
Executa atualização inicial imediatamente
    ↓
Agenda atualização diária no horário configurado (padrão: 03:00)
    ↓
Thread de scheduler fica rodando em background
```

**Arquivo**: `core/survival/rankings_update_service.py` (linhas 59-90)

```python
def start(self):
    # Executa atualização inicial
    self.update_once()
    
    # Agenda atualização diária
    self.scheduler.every().day.at(self.update_time).do(self.update_once)
    
    # Inicia thread de scheduler
    self.scheduler_thread = threading.Thread(target=self._scheduler_loop, daemon=True)
    self.scheduler_thread.start()
```

---

### **3. Processo de Atualização (`update_once`)**

#### **3.1. Obter Todos os Jogadores**

O sistema busca jogadores únicos de **múltiplas fontes**:

**Fontes de Dados**:
1. `kill_events` (killer_steam_id)
2. `kill_events` (victim_steam_id)
3. `minigame_events` (steam_id)
4. `vehicle_destruction_events` (owner_steam_id)
5. `survival_stats_snapshot` (steam_id)
6. `players` (fallback)

**Arquivo**: `core/survival/rankings_update_service.py` (linhas 191-264)

```python
def _get_all_players(self) -> Dict[str, str]:
    players = {}
    
    # Busca de kill_events (killer)
    # Busca de kill_events (victim)
    # Busca de minigame_events
    # Busca de vehicle_destruction_events
    # Busca de survival_stats_snapshot
    # Busca de players (fallback)
    
    return players
```

---

#### **3.2. Calcular Rankings para Cada Jogador**

Para cada jogador encontrado, o sistema calcula todas as métricas:

**Arquivo**: `core/survival/rankings_update_service.py` (linhas 266-431)

##### **A) Dados de `kill_events`**

```python
# Kills (PvP apenas, exclui NPCs)
SELECT COUNT(*) 
FROM kill_events 
WHERE killer_steam_id = ? AND event_type = 'kill' AND killer_is_npc = 0

# Deaths
SELECT COUNT(*) 
FROM kill_events 
WHERE victim_steam_id = ? AND event_type = 'kill'

# KDR (calculado)
kdr = kills / deaths (ou kills se deaths = 0)

# Longest Shot
SELECT distance, weapon, timestamp
FROM kill_events
WHERE killer_steam_id = ? AND event_type = 'kill' AND distance > 0
ORDER BY distance DESC
LIMIT 1

# Suicides
SELECT COUNT(*) 
FROM kill_events 
WHERE victim_steam_id = ? AND event_type = 'suicide'
```

##### **B) Dados de `minigame_events` (Lockpicking)**

Para cada tipo de fechadura (Basic, Medium, Advanced, VeryEasy, DialLock, Other):

```python
# Success por tipo
SELECT COUNT(*) 
FROM minigame_events 
WHERE steam_id = ? AND minigame_type = 'LockpickingMinigame_C' 
  AND success = 1 AND lock_type = ?

# Fails por tipo
SELECT COUNT(*) 
FROM minigame_events 
WHERE steam_id = ? AND minigame_type = 'LockpickingMinigame_C' 
  AND success = 0 AND lock_type = ?

# Total e Taxa de Sucesso (calculados)
total = success + fails
rate = (success / total) * 100
```

**Colunas geradas**:
- `lockpick_basic_success`, `lockpick_basic_fails`, `lockpick_basic_total`, `lockpick_basic_rate`
- `lockpick_medium_success`, `lockpick_medium_fails`, `lockpick_medium_total`, `lockpick_medium_rate`
- `lockpick_advanced_success`, `lockpick_advanced_fails`, `lockpick_advanced_total`, `lockpick_advanced_rate`
- `lockpick_veryeasy_success`, `lockpick_veryeasy_fails`, `lockpick_veryeasy_total`, `lockpick_veryeasy_rate`
- `lockpick_diallock_success`, `lockpick_diallock_fails`, `lockpick_diallock_total`, `lockpick_diallock_rate`
- `lockpick_other_success`, `lockpick_other_fails`, `lockpick_other_total`, `lockpick_other_rate`

##### **C) Dados de `vehicle_destruction_events`**

```python
SELECT COUNT(*) 
FROM vehicle_destruction_events 
WHERE owner_steam_id = ?
```

##### **D) Dados de `survival_stats_snapshot`**

Usa o **snapshot mais recente** de cada jogador:

```python
SELECT total_defecations, animals_killed, players_knocked_out, 
       headshots, minutes_survived, overdose, highest_weight_carried
FROM survival_stats_snapshot
WHERE steam_id = ?
ORDER BY snapshot_at DESC
LIMIT 1
```

**Colunas populadas**:
- `highest_defecation` (total_defecations)
- `animals_killed`
- `players_knocked_out`
- `headshots`
- `minutes_survived`
- `overdoses` (overdose)
- `highest_weight_carried`

---

#### **3.3. Inserir ou Atualizar na Tabela `rankings`**

**Método**: `INSERT OR REPLACE` (atualiza se existe, cria se não existe)

**Arquivo**: `core/survival/rankings_update_service.py` (linhas 433-507)

```python
def _insert_or_update_ranking(self, conn, steam_id, player_name, rankings):
    # Atualiza player_name se necessário (pega o mais recente)
    # Executa INSERT OR REPLACE com todos os dados calculados
    cursor.execute('''
        INSERT OR REPLACE INTO rankings (
            steam_id, player_name,
            kills, deaths, kdr,
            longest_shot_distance, longest_shot_weapon, longest_shot_timestamp,
            suicides,
            lockpick_basic_success, lockpick_basic_fails, lockpick_basic_total, lockpick_basic_rate,
            ... (outros tipos de lockpick)
            vehicles_destroyed,
            highest_defecation, animals_killed, players_knocked_out,
            headshots, minutes_survived, overdoses, highest_weight_carried,
            last_updated
        ) VALUES (?, ?, ...)
    ''', (...))
```

**Características**:
- ✅ `UNIQUE(steam_id)` garante apenas um registro por jogador
- ✅ `last_updated` é atualizado com timestamp atual
- ✅ `player_name` é atualizado se houver nome mais recente

---

### **4. Consulta dos Rankings (API)**

**Endpoint**: `GET /api/rankings`

**Arquivo**: `main.py` (linhas 6750-6870)

**Parâmetros**:
- `category`: Categoria do ranking (kills, deaths, kdr, longest_shot, etc.)
- `limit`: Número de resultados (padrão: 20, máximo: 100)
- `offset`: Paginação (padrão: 0)

**Categorias Disponíveis**:
```python
category_map = {
    'kills': 'kills',
    'deaths': 'deaths',
    'kdr': 'kdr',
    'longest_shot': 'longest_shot_distance',
    'lockpick_basic_rate': 'lockpick_basic_rate',
    'lockpick_medium_rate': 'lockpick_medium_rate',
    'lockpick_advanced_rate': 'lockpick_advanced_rate',
    'lockpick_veryeasy_rate': 'lockpick_veryeasy_rate',
    'lockpick_diallock_rate': 'lockpick_diallock_rate',
    'suicides': 'suicides',
    'defecation': 'highest_defecation',
    'vehicles': 'vehicles_destroyed',
    'hunting': 'animals_killed',
    'melee': 'players_knocked_out',
    'headshots': 'headshots',
    'survival_time': 'minutes_survived',
    'overdoses': 'overdoses',
    'weight': 'highest_weight_carried'
}
```

**Query SQL**:
```sql
SELECT steam_id, player_name, kills, deaths, kdr, ...
FROM rankings
WHERE {order_column} > 0
ORDER BY {order_column} DESC, steam_id ASC
LIMIT ? OFFSET ?
```

---

## 📊 Estrutura da Tabela

### **Schema Completo**

```sql
CREATE TABLE IF NOT EXISTS rankings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    steam_id TEXT NOT NULL,
    player_name TEXT NOT NULL,
    
    -- kill_events
    kills INTEGER DEFAULT 0,
    deaths INTEGER DEFAULT 0,
    kdr REAL DEFAULT 0,
    longest_shot_distance REAL DEFAULT 0,
    longest_shot_weapon TEXT,
    longest_shot_timestamp DATETIME,
    suicides INTEGER DEFAULT 0,
    
    -- minigame_events (por tipo de fechadura)
    lockpick_basic_success INTEGER DEFAULT 0,
    lockpick_basic_fails INTEGER DEFAULT 0,
    lockpick_basic_total INTEGER DEFAULT 0,
    lockpick_basic_rate REAL DEFAULT 0,
    -- ... (medium, advanced, veryeasy, diallock, other)
    
    -- vehicle_destruction_events
    vehicles_destroyed INTEGER DEFAULT 0,
    
    -- survival_stats_snapshot
    highest_defecation INTEGER DEFAULT 0,
    animals_killed INTEGER DEFAULT 0,
    players_knocked_out INTEGER DEFAULT 0,
    headshots INTEGER DEFAULT 0,
    minutes_survived REAL DEFAULT 0,
    overdoses INTEGER DEFAULT 0,
    highest_weight_carried REAL DEFAULT 0,
    
    -- Metadata
    last_updated DATETIME DEFAULT CURRENT_TIMESTAMP,
    
    UNIQUE(steam_id)
);
```

---

## 🔄 Diagrama de Fluxo

```
┌─────────────────────────────────────────────────────────────┐
│                    INICIALIZAÇÃO                            │
│  RankingsUpdateService é criado e configurado               │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│                    AGENDAMENTO                              │
│  - Executa atualização inicial                              │
│  - Agenda atualização diária (03:00)                        │
│  - Thread de scheduler em background                       │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼ (A cada 24h ou manualmente)
┌─────────────────────────────────────────────────────────────┐
│              PROCESSO DE ATUALIZAÇÃO                        │
│                                                              │
│  1. _get_all_players()                                      │
│     └─ Busca jogadores de:                                  │
│        - kill_events (killer + victim)                      │
│        - minigame_events                                    │
│        - vehicle_destruction_events                        │
│        - survival_stats_snapshot                            │
│        - players (fallback)                                 │
│                                                              │
│  2. Para cada jogador:                                       │
│     └─ _calculate_player_rankings()                         │
│        ├─ Calcula kills/deaths/kdr (kill_events)            │
│        ├─ Calcula longest_shot (kill_events)                │
│        ├─ Calcula suicides (kill_events)                    │
│        ├─ Calcula lockpicking por tipo (minigame_events)    │
│        ├─ Calcula vehicles_destroyed (vehicle_events)       │
│        └─ Obtém survival stats (survival_stats_snapshot)    │
│                                                              │
│  3. _insert_or_update_ranking()                             │
│     └─ INSERT OR REPLACE na tabela rankings                │
│                                                              │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│                    TABELA RANKINGS                           │
│  Dados agregados prontos para consulta rápida              │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│                    API ENDPOINT                              │
│  GET /api/rankings?category=kills&limit=20                  │
│  └─ Consulta rápida com índices otimizados                  │
└─────────────────────────────────────────────────────────────┘
```

---

## ⚙️ Configuração

### **config.json**

```json
{
  "rankings_sync": {
    "enabled": true,              // Habilitar/desabilitar serviço
    "auto_start": true,           // Iniciar automaticamente
    "update_interval_hours": 24,  // Intervalo entre atualizações
    "update_time": "03:00",      // Horário da atualização diária
    "ssm_db_path": "data/SSM.db" // Caminho do banco (opcional)
  }
}
```

---

## 📈 Características Importantes

### **1. Tabela de Cache Materializada**

- ✅ **Performance**: Consultas muito rápidas (dados pré-calculados)
- ✅ **Índices**: Índices otimizados para ordenação por cada categoria
- ✅ **Atualização Periódica**: Atualizada diariamente (não em tempo real)

### **2. Dados Agregados**

- ✅ **Acumulados**: Todos os dados são totais acumulados (não resetam)
- ✅ **Snapshot Mais Recente**: Survival stats usam o snapshot mais recente
- ✅ **Cálculos Automáticos**: KDR, taxas de lockpick são calculadas automaticamente

### **3. Múltiplas Fontes**

- ✅ **kill_events**: Kills, deaths, longest shot, suicides
- ✅ **minigame_events**: Lockpicking por tipo de fechadura
- ✅ **vehicle_destruction_events**: Veículos destruídos
- ✅ **survival_stats_snapshot**: Stats de sobrevivência

### **4. Atualização Inteligente**

- ✅ **INSERT OR REPLACE**: Atualiza se existe, cria se não existe
- ✅ **Nome Atualizado**: Atualiza player_name se houver versão mais recente
- ✅ **Timestamp**: Sempre atualiza `last_updated` com timestamp atual

---

## 🔍 Métodos de Controle

### **Iniciar Atualização Manualmente**

```python
result = rankings_update_service.start()
# Retorna: {"success": True, "message": "...", "status": "started"}
```

### **Parar Atualização**

```python
result = rankings_update_service.stop()
# Retorna: {"success": True, "message": "...", "status": "stopped"}
```

### **Executar Atualização Única**

```python
result = rankings_update_service.update_once()
# Retorna: {"success": True, "rows_processed": 150, "elapsed_seconds": 12.345}
```

### **Verificar Status**

```python
status = rankings_update_service.get_status()
# Retorna: {
#   "enabled": true,
#   "is_running": true,
#   "update_interval_hours": 24,
#   "update_time": "03:00",
#   "last_update": {
#     "timestamp": "2025-12-02T03:00:00",
#     "status": "success",
#     "details": {"rows_processed": 150, "elapsed_seconds": 12.345}
#   }
# }
```

---

## 📊 Exemplo de Dados na Tabela

```sql
SELECT * FROM rankings WHERE steam_id = '76561198040636105';
```

**Resultado**:
```
id: 1
steam_id: '76561198040636105'
player_name: 'Pedreiro'
kills: 150
deaths: 25
kdr: 6.0
longest_shot_distance: 125.50
longest_shot_weapon: 'Weapon_AK47_C'
longest_shot_timestamp: '2025-01-15 14:30:00'
suicides: 3
lockpick_basic_success: 45
lockpick_basic_fails: 12
lockpick_basic_total: 57
lockpick_basic_rate: 78.95
... (outros tipos de lockpick)
vehicles_destroyed: 5
highest_defecation: 250
animals_killed: 87
players_knocked_out: 23
headshots: 142
minutes_survived: 5000.5
overdoses: 8
highest_weight_carried: 45.7
last_updated: '2025-12-02 03:00:00'
```

---

## ⚠️ Observações Importantes

1. **Atualização Não é em Tempo Real**: A tabela é atualizada diariamente (padrão: 03:00)
2. **Dados Acumulados**: Todos os valores são totais acumulados desde o início
3. **Performance**: A tabela é otimizada para consultas rápidas, não para inserções frequentes
4. **Único Registro por Jogador**: `UNIQUE(steam_id)` garante apenas um registro por jogador
5. **Fallback de Nome**: Se player_name não estiver disponível, usa steam_id

---

## 🔗 Arquivos Relacionados

- **Serviço**: `core/survival/rankings_update_service.py`
- **API Endpoint**: `main.py` (linha 6750)
- **Schema**: `docs/RANKINGS_TABLE_SCHEMA.md`
- **Estrutura**: `docs/RANKINGS_TABLE_STRUCTURE.md`

---

**Última Atualização**: 2025-12-02

