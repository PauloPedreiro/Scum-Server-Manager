# 📊 Análise: Logs `famepoints_*.log`

## 🎯 Visão Geral

Os arquivos de log `famepoints_*.log` contêm informações detalhadas sobre a concessão de pontos de fama aos jogadores no servidor SCUM. Cada arquivo registra eventos de fama em intervalos de tempo (geralmente a cada 10 minutos).

---

## 📋 Estrutura dos Logs

### **Formato das Linhas**

Cada entrada de fama segue o padrão:

```
2025.11.26-20.39.19: Player NOME_JOGADOR(STEAM_ID) was awarded X.XXXXXX fame points [in 10 minutes] for a total of Y.YYYYYY
```

### **Informações Adicionais**

Após a linha principal, podem aparecer detalhes sobre como a fama foi obtida:

```
DistanceTraveledOnFoot: 0.003035
OnlineFlagOwnersAwardAwarded: 0.113347
BaseFameInflux: 0.630211
PuppetKill: 0.210000
SkillLeveledUp: 10.500000
DistanceTraveledWhileMounted: 0.012092
```

### **Estrutura de Dados Identificada**

```python
{
    'timestamp': '2025.11.26-20.39.19',
    'player_name': 'NOME_JOGADOR',
    'steam_id': '76561198777583030',
    'awarded': 185.593964,  # Pontos concedidos neste evento
    'total': 185.593964,    # Total acumulado de fama
    'details': {            # Detalhes opcionais
        'DistanceTraveledOnFoot': 0.003035,
        'OnlineFlagOwnersAwardAwarded': 0.113347,
        'BaseFameInflux': 0.630211,
        'PuppetKill': 0.210000,
        'SkillLeveledUp': 10.500000,
        'DistanceTraveledWhileMounted': 0.012092
    }
}
```

---

## 🔍 Análise dos Dados

### **Estatísticas dos Logs**

- **Total de arquivos encontrados**: 31 arquivos
- **Formato de encoding**: UTF-16LE (padrão dos logs do SCUM)
- **Frequência**: Arquivos criados periodicamente (a cada ~4 horas)
- **Conteúdo**: Eventos de concessão de fama a jogadores

### **Padrão Regex Identificado**

```python
r'Player\s+(?P<player_name>.+?)\((?P<steam_id>\d+)\)\s+was awarded\s+'
r'(?P<awarded>[-\d.]+)\s+fame points.*?for a total of\s+(?P<total>[-\d.]+)'
```

---

## 🗄️ Estado Atual do Sistema

### **Processador Existente**

✅ **Já existe**: `FamepointsProcessor` (`core/logs/famepoints_processor.py`)
- Processa arquivos `famepoints_*.log`
- Extrai informações de fama usando regex
- Atualiza tabela `player_fame_totals` no banco SSM.db

### **Tabela Existente**

✅ **Já existe**: `player_fame_totals` no banco `SSM.db`

```sql
CREATE TABLE IF NOT EXISTS player_fame_totals (
    steam_id TEXT PRIMARY KEY,
    player_name TEXT NOT NULL,
    total_fame REAL NOT NULL,
    last_updated DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (steam_id) REFERENCES players (steam_id) ON DELETE CASCADE
);
```

**Limitação**: Esta tabela armazena apenas o **total consolidado** de fama por jogador, não o histórico de eventos.

---

## 💡 Proposta: Tabela de Histórico de Famepoints

### **Objetivo**

Criar uma tabela para armazenar o **histórico completo** de eventos de fama, permitindo:

1. ✅ Análise temporal de ganho de fama
2. ✅ Identificação de fontes de fama (PuppetKill, SkillLeveledUp, etc.)
3. ✅ Estatísticas detalhadas por jogador
4. ✅ Rankings e análises avançadas
5. ✅ Detecção de padrões de gameplay

### **Estrutura Proposta da Tabela**

```sql
CREATE TABLE IF NOT EXISTS famepoints_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    steam_id TEXT NOT NULL,
    player_name TEXT NOT NULL,
    timestamp DATETIME NOT NULL,
    
    -- Valores principais
    awarded REAL NOT NULL,              -- Pontos concedidos neste evento
    total_after REAL NOT NULL,           -- Total após este evento
    
    -- Detalhes de como a fama foi obtida (opcionais)
    distance_traveled_on_foot REAL,
    distance_traveled_while_mounted REAL,
    online_flag_owners_award REAL,
    base_fame_influx REAL,
    puppet_kill REAL,
    skill_leveled_up REAL,
    
    -- Metadados
    log_file TEXT,                      -- Nome do arquivo de log origem
    log_line TEXT,                      -- Linha original do log (para debug)
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (steam_id) REFERENCES players (steam_id) ON DELETE CASCADE
);
```

### **Índices Propostos**

```sql
-- Índice para consultas por jogador e data
CREATE INDEX idx_famepoints_steam_timestamp 
    ON famepoints_events(steam_id, timestamp DESC);

-- Índice para consultas por data
CREATE INDEX idx_famepoints_timestamp 
    ON famepoints_events(timestamp DESC);

-- Índice para consultas por jogador
CREATE INDEX idx_famepoints_steam_id 
    ON famepoints_events(steam_id);
```

---

## 🔄 Modificações Necessárias

### **1. Atualizar `FamepointsProcessor`**

**Arquivo**: `core/logs/famepoints_processor.py`

**Mudanças**:
- ✅ Melhorar regex para capturar detalhes adicionais (DistanceTraveledOnFoot, etc.)
- ✅ Adicionar método para processar detalhes de fama
- ✅ Inserir eventos na nova tabela `famepoints_events`
- ✅ Manter compatibilidade com atualização de `player_fame_totals`

### **2. Adicionar Métodos no `DatabaseManager`**

**Arquivo**: `core/logs/database_manager.py`

**Novos métodos**:
- `insert_famepoints_event()` - Inserir evento individual
- `insert_batch_famepoints_events()` - Inserir múltiplos eventos
- `get_famepoints_history()` - Obter histórico de um jogador
- `get_famepoints_stats()` - Estatísticas de fama

### **3. Criar Tabela no Banco**

**Arquivo**: `core/logs/database_manager.py` (método `init_database()`)

**Adicionar**: Criação da tabela `famepoints_events` com índices

---

## 📊 Casos de Uso

### **1. Histórico de Fama por Jogador**

```sql
SELECT 
    timestamp,
    awarded,
    total_after,
    puppet_kill,
    skill_leveled_up,
    base_fame_influx
FROM famepoints_events
WHERE steam_id = '76561198777583030'
ORDER BY timestamp DESC
LIMIT 100;
```

### **2. Ranking de Ganho de Fama (últimas 24h)**

```sql
SELECT 
    steam_id,
    player_name,
    SUM(awarded) as total_gained,
    COUNT(*) as events_count
FROM famepoints_events
WHERE timestamp >= datetime('now', '-24 hours')
GROUP BY steam_id, player_name
ORDER BY total_gained DESC
LIMIT 20;
```

### **3. Análise de Fontes de Fama**

```sql
SELECT 
    steam_id,
    player_name,
    SUM(COALESCE(puppet_kill, 0)) as total_puppet_kill,
    SUM(COALESCE(skill_leveled_up, 0)) as total_skill_leveled,
    SUM(COALESCE(base_fame_influx, 0)) as total_base_fame
FROM famepoints_events
WHERE timestamp >= datetime('now', '-7 days')
GROUP BY steam_id, player_name;
```

### **4. Estatísticas de Atividade**

```sql
SELECT 
    DATE(timestamp) as date,
    COUNT(DISTINCT steam_id) as unique_players,
    COUNT(*) as total_events,
    SUM(awarded) as total_fame_awarded
FROM famepoints_events
GROUP BY DATE(timestamp)
ORDER BY date DESC;
```

---

## ⚠️ Considerações Importantes

### **1. Volume de Dados**

- **Estimativa**: ~10-50 eventos por arquivo de log
- **Frequência**: Arquivos criados a cada ~4 horas
- **Crescimento**: ~240-1200 eventos por dia
- **Armazenamento**: ~1-5 MB por mês (estimativa)

### **2. Performance**

- ✅ Índices adequados para consultas rápidas
- ✅ Considerar limpeza de dados antigos (ex: > 90 dias)
- ✅ Manter tabela `player_fame_totals` para consultas rápidas de total

### **3. Compatibilidade**

- ✅ Manter processamento atual de `player_fame_totals`
- ✅ Adicionar processamento de histórico sem quebrar funcionalidade existente
- ✅ Processar arquivos antigos retroativamente (opcional)

---

## 🚀 Plano de Implementação

### **Fase 1: Análise e Planejamento** ✅
- [x] Analisar estrutura dos logs
- [x] Identificar dados disponíveis
- [x] Propor estrutura de tabela
- [x] Documentar casos de uso

### **Fase 2: Implementação**
- [ ] Criar tabela `famepoints_events` no banco
- [ ] Atualizar `FamepointsProcessor` para extrair detalhes
- [ ] Adicionar métodos no `DatabaseManager`
- [ ] Testar processamento de arquivos existentes

### **Fase 3: Processamento Retroativo (Opcional)**
- [ ] Script para processar arquivos antigos
- [ ] Validar dados históricos
- [ ] Verificar integridade dos dados

### **Fase 4: Endpoints API (Opcional)**
- [ ] Endpoint para histórico de fama por jogador
- [ ] Endpoint para estatísticas de fama
- [ ] Endpoint para rankings de ganho de fama

---

## 📝 Exemplo de Dados Extraídos

### **Linha Original do Log**

```
2025.11.26-20.39.19: Player TONINHO DA RAPADURA(76561198330210602) was awarded 185.593964 fame points in 10 minutes for a total of 185.593964
DistanceTraveledOnFoot: 0.003035
OnlineFlagOwnersAwardAwarded: 0.113347
BaseFameInflux: 0.630211
PuppetKill: 0.210000
SkillLeveledUp: 10.500000
```

### **Dados Extraídos**

```json
{
    "steam_id": "76561198330210602",
    "player_name": "TONINHO DA RAPADURA",
    "timestamp": "2025-11-26 20:39:19",
    "awarded": 185.593964,
    "total_after": 185.593964,
    "distance_traveled_on_foot": 0.003035,
    "online_flag_owners_award": 0.113347,
    "base_fame_influx": 0.630211,
    "puppet_kill": 0.210000,
    "skill_leveled_up": 10.500000
}
```

---

## ✅ Conclusão

**A tabela `player_fame_totals` já existe e está funcionando corretamente!**

### **Status Atual**

✅ **Tabela criada**: `player_fame_totals` no banco `SSM.db`
✅ **Processador ativo**: `FamepointsProcessor` processa logs automaticamente
✅ **Atualização automática**: Tabela é atualizada sempre que há eventos de fama (ganho ou perda)
✅ **Endpoints API**: Criados endpoints para consultar os dados

### **Endpoints Disponíveis**

#### **1. Listar Todos os Jogadores com Fama**
```
GET /api/players/fame
```

**Parâmetros Query (opcionais):**
- `limit` (number): Número máximo de registros (padrão: 100, máximo: 1000)
- `offset` (number): Deslocamento para paginação (padrão: 0)
- `sort_order` (string): Ordenação (`asc` ou `desc`, padrão: `desc`)

**Resposta:**
```json
{
  "success": true,
  "data": {
    "players": [
      {
        "steam_id": "76561198777583030",
        "player_name": "ADM Guns",
        "total_fame": 234.79837,
        "last_updated": "2025-12-02 00:21:39"
      }
    ],
    "total": 28,
    "limit": 100,
    "offset": 0,
    "count": 28,
    "sort_order": "desc"
  }
}
```

#### **2. Obter Fama de um Jogador Específico**
```
GET /api/players/{steam_id}/fame
```

**Resposta:**
```json
{
  "success": true,
  "data": {
    "steam_id": "76561198777583030",
    "player_name": "ADM Guns",
    "total_fame": 234.79837,
    "last_updated": "2025-12-02 00:21:39"
  }
}
```

**📚 Documentação Completa**: Consulte [PLAYERS_FAME_ENDPOINTS.md](./endpoints/PLAYERS_FAME_ENDPOINTS.md) para documentação detalhada dos endpoints.

### **Como Funciona**

1. **Processamento Automático**: O `FamepointsProcessor` monitora arquivos `famepoints_*.log` em tempo real
2. **Extração de Dados**: Regex extrai informações de cada evento (incluindo valores negativos para perda de fama)
3. **Atualização da Tabela**: O total de fama é atualizado usando `UPSERT` (INSERT ou UPDATE)
4. **Valores Negativos**: O sistema suporta valores negativos quando o jogador perde fama

### **Exemplo de Log Processado**

```
Player TONINHO DA RAPADURA(76561198330210602) was awarded -50.0 fame points for a total of 77.747253
```

**Resultado**: Tabela atualizada com `total_fame = 77.747253` para o jogador.

### **Vantagens**

- ✅ Atualização automática em tempo real
- ✅ Suporta ganho e perda de fama (valores positivos e negativos)
- ✅ Consulta rápida via API
- ✅ Integrado com sistema existente
- ✅ Dados sempre atualizados

---

## 📝 Nota sobre Histórico de Eventos

A tabela atual (`player_fame_totals`) armazena apenas o **total consolidado** de fama por jogador. Se você precisar de um **histórico completo de eventos** (para análises temporais, estatísticas detalhadas, etc.), consulte a seção "💡 Proposta: Tabela de Histórico de Famepoints" acima.

