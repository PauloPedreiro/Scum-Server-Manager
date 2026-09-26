# 🎮 Proposta: Tabela de Eventos de Minigame

## 📋 Visão Geral

Proposta para criar uma tabela genérica no banco `SSM.db` para armazenar **todos os eventos de `LogMinigame`** dos logs de gameplay. A tabela armazenará a linha completa do log, permitindo processamento futuro para alertas, rankings e estatísticas.

## 🎯 Objetivo

- ✅ Capturar **todos os tipos** de `LogMinigame` (não apenas Lockpicking)
- ✅ Salvar **linha completa** do log original
- ✅ Estrutura **simples e escalável**
- ✅ Processamento futuro conforme necessário

## 🔍 Tipos de Minigame Identificados

Com base nos logs do SCUM, existem vários tipos de minigames:

1. **LockpickingMinigame_C** - Lockpicking (abertura de fechaduras)
2. **HackingMinigame_C** - Hacking (possível)
3. **Outros tipos** - Pode haver mais no futuro

## 🗄️ Estrutura da Tabela (Simplificada)

### Tabela Genérica de Minigames

```sql
CREATE TABLE IF NOT EXISTS minigame_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    
    -- LINHA COMPLETA DO LOG (PRESERVAÇÃO TOTAL)
    log_line TEXT NOT NULL,                -- Linha completa do log original
    
    -- Campos básicos extraídos (mínimos para queries)
    timestamp DATETIME NOT NULL,           -- Quando aconteceu
    
    -- Tipo de minigame (extraído da linha)
    minigame_type TEXT,                    -- Ex: LockpickingMinigame_C, HackingMinigame_C
    
    -- Jogador (extraído da linha)
    steam_id TEXT,                         -- Steam ID do jogador
    player_id INTEGER,                     -- Player ID
    player_name TEXT,                      -- Nome do jogador
    
    -- Localização (extraído da linha)
    location_x REAL,                       -- Coordenada X
    location_y REAL,                       -- Coordenada Y
    location_z REAL,                       -- Coordenada Z
    
    -- Metadata
    log_file TEXT,                         -- Nome do arquivo de log (ex: gameplay_20251122023029.log)
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    
    -- Relacionamento (se steam_id existe na tabela players)
    FOREIGN KEY (steam_id) REFERENCES players(steam_id) ON DELETE SET NULL
);
```

### Índices para Performance

```sql
-- Buscar eventos por timestamp (últimos eventos)
CREATE INDEX IF NOT EXISTS idx_minigame_timestamp 
ON minigame_events(timestamp DESC);

-- Buscar eventos por jogador (rankings futuros)
CREATE INDEX IF NOT EXISTS idx_minigame_steam_id 
ON minigame_events(steam_id)
WHERE steam_id IS NOT NULL;

-- Buscar eventos por tipo de minigame (filtrar por tipo)
CREATE INDEX IF NOT EXISTS idx_minigame_type 
ON minigame_events(minigame_type)
WHERE minigame_type IS NOT NULL;

-- Buscar eventos por arquivo de log (debugging)
CREATE INDEX IF NOT EXISTS idx_minigame_log_file 
ON minigame_events(log_file);
```

## 📊 Exemplo de Dados na Tabela

### Exemplo 1: Lockpicking (Sucesso)

```sql
INSERT INTO minigame_events (
    log_line,
    timestamp,
    minigame_type,
    steam_id,
    player_id,
    player_name,
    location_x,
    location_y,
    location_z,
    log_file
) VALUES (
    '2025.11.22-02.20.34: [LogMinigame] [LockpickingMinigame_C] User: Pedreiro (1, 76561198040636105). Success: Yes. Elapsed time: 77.53. Failed attempts: 38. Target object: BPC_ModularDoor_Loophole_Double_Wood_C(ID: N/A). Lock type: Basic. User owner: 84([76561198094354554] ARKANJO). Location: X=313071.812 Y=236477.641 Z=22334.223',
    '2025-11-22 02:20:34',
    'LockpickingMinigame_C',
    '76561198040636105',
    1,
    'Pedreiro',
    313071.812,
    236477.641,
    22334.223,
    'gameplay_20251122023029.log'
);
```

### Exemplo 2: Lockpicking (Falha)

```sql
INSERT INTO minigame_events (
    log_line,
    timestamp,
    minigame_type,
    steam_id,
    player_id,
    player_name,
    location_x,
    location_y,
    location_z,
    log_file
) VALUES (
    '2025.11.22-02.34.52: [LogMinigame] [LockpickingMinigame_C] User: Pedreiro (1, 76561198040636105). Success: No. Elapsed time: 144.67. Failed attempts: 64. Target object: WoodenWeaponRack_C(ID: 12941790). Lock type: Medium. User owner: 84([76561198094354554] ARKANJO). Location: X=313037.562 Y=237024.531 Z=22334.223',
    '2025-11-22 02:34:52',
    'LockpickingMinigame_C',
    '76561198040636105',
    1,
    'Pedreiro',
    313037.562,
    237024.531,
    22334.223,
    'gameplay_20251122023029.log'
);
```

## 🔧 Vantagens da Abordagem Simplificada

### ✅ Simplicidade
- Estrutura mínima e fácil de manter
- Menos parsing no momento de inserção
- Mais rápido para processar logs

### ✅ Flexibilidade
- Suporta todos os tipos de minigame
- Processamento futuro conforme necessário
- Extração de campos apenas quando necessário

### ✅ Escalabilidade
- Fácil adicionar novos tipos de minigame
- Não precisa alterar estrutura da tabela
- Toda informação original preservada

### ✅ Performance
- Inserção rápida (pouco parsing)
- Índices mínimos mas eficientes
- Queries simples na linha completa quando necessário

## 🚀 Processamento Futuro

### Quando Criar Alertas/Rankings

No futuro, você pode:

1. **Extrair campos específicos** da `log_line` quando necessário
2. **Criar views** para facilitar queries
3. **Processar em lote** para gerar estatísticas
4. **Filtrar por tipo** usando `minigame_type`

### Exemplo: Query para Rankings de Lockpicking

```sql
-- Extrair dados específicos de lockpicking da log_line
-- (isso pode ser feito com REGEX ou em código Python)

SELECT 
    steam_id,
    player_name,
    COUNT(*) as total_attempts,
    COUNT(CASE WHEN log_line LIKE '%Success: Yes%' THEN 1 END) as successes
FROM minigame_events
WHERE minigame_type = 'LockpickingMinigame_C'
GROUP BY steam_id, player_name
ORDER BY successes DESC;
```

### Exemplo: View para Lockpicking (Opcional)

```sql
-- Criar view que extrai campos específicos de lockpicking
CREATE VIEW lockpicking_events_detailed AS
SELECT 
    id,
    timestamp,
    steam_id,
    player_id,
    player_name,
    location_x,
    location_y,
    location_z,
    log_line,
    -- Extrair campos específicos da log_line aqui (via REGEX ou função)
    -- success, elapsed_time, failed_attempts, etc.
    log_file
FROM minigame_events
WHERE minigame_type = 'LockpickingMinigame_C';
```

## 📝 Fluxo de Processamento

### 1. Detecção
- Monitora arquivos `gameplay_*.log`
- Detecta linhas com `[LogMinigame]`

### 2. Extração Mínima
- Extrai apenas campos básicos:
  - Timestamp
  - Tipo de minigame (do formato `[TipoMinigame_C]`)
  - Steam ID, Player ID, Nome (do formato `User: Nome (ID, STEAM_ID)`)
  - Coordenadas (do formato `Location: X=... Y=... Z=...`)

### 3. Inserção
- Salva linha completa em `log_line`
- Salva campos básicos extraídos
- Salva nome do arquivo de log

### 4. Processamento Futuro
- Quando necessário, parsear `log_line` para extrair campos específicos
- Criar alertas baseados em padrões na linha
- Gerar rankings usando campos básicos ou parsing dinâmico

## 🎯 Próximos Passos

1. ✅ **Criar tabela** no banco SSM.db
2. ✅ **Criar parser simples** que detecta `[LogMinigame]`
3. ✅ **Integrar no log processor** para processar `gameplay_*.log`
4. ⏳ **Testar com dados reais**
5. ⏳ **Implementar alertas/rankings** no futuro conforme necessário

## ❓ Perguntas para Decisão

1. **Campos básicos:** Está bom assim? Ou quer adicionar algum campo extraído inicialmente?
2. **Timestamp:** Manter como DATETIME ou TEXT?
3. **Limpeza:** Limpar dados antigos? Quantos dias manter?
4. **Deduplicação:** Verificar duplicatas? Geralmente não necessário.

## 🔍 Padrão de Detecção

### Regex para Detectar LogMinigame

```python
# Padrão para detectar qualquer LogMinigame
pattern = re.compile(
    r'(\d{4}\.\d{2}\.\d{2})-(\d{2}\.\d{2}\.\d{2}):\s*\[LogMinigame\]\s*\[([^\]]+)\]\s*User:\s*([^(]+)\s*\((\d+),\s*(\d+)\)'
)

# Padrão para extrair coordenadas
location_pattern = re.compile(
    r'Location:\s*X=([-\d.]+)\s+Y=([-\d.]+)\s+Z=([-\d.]+)'
)
```

---

**Versão:** 2.0  
**Data:** 2025-01-22  
**Autor:** Proposta Simplificada - Todos os Minigames

