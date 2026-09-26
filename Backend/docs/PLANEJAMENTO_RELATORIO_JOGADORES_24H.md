# 📊 Planejamento: Relatório de Média de Jogadores a cada 24h

## 🎯 Objetivo

Criar um sistema de relatórios que mostre:
- **Média de jogadores online a cada 24 horas**
- **Gráficos de linha** mostrando horários de pico e baixa
- **Análise de comportamento** do servidor ao longo do tempo

---

## 📋 Análise dos Dados Disponíveis

### ✅ Dados que JÁ TEMOS no Banco

#### 1. **Tabela `players_online`** (Estado Atual)
```sql
CREATE TABLE players_online (
    steam_id TEXT PRIMARY KEY,
    player_name TEXT NOT NULL,
    player_id INTEGER NOT NULL,
    last_activity DATETIME NOT NULL,
    coordinates_x REAL NOT NULL,
    coordinates_y REAL NOT NULL,
    coordinates_z REAL NOT NULL,
    activity_types TEXT,
    total_activities INTEGER DEFAULT 0,
    status TEXT DEFAULT 'online',
    last_updated DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

**O que temos:**
- ✅ Estado atual dos jogadores online
- ✅ Timestamp de última atualização (`last_updated`)
- ✅ Atualizado a cada 30 segundos pelo `OnlinePlayersMonitor`

**Limitação:**
- ❌ Não armazena histórico (só estado atual)
- ❌ Não podemos ver quantos jogadores estavam online ontem às 14h

---

#### 2. **Tabela `player_logins`** (Histórico de Login/Logout)
```sql
CREATE TABLE player_logins (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    steam_id TEXT NOT NULL,
    player_name TEXT NOT NULL,
    player_id INTEGER NOT NULL,
    ip_address TEXT,
    action TEXT NOT NULL,  -- 'login' ou 'logout'
    coordinates_x REAL,
    coordinates_y REAL,
    coordinates_z REAL,
    timestamp DATETIME NOT NULL,
    server_date DATE,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

**O que temos:**
- ✅ Histórico completo de logins e logouts
- ✅ Timestamps precisos de cada evento
- ✅ Pode ser usado para **estimar** jogadores online em momentos passados

**Limitação:**
- ⚠️ Requer cálculo complexo (reconstruir estado a partir de eventos)
- ⚠️ Pode ter gaps se houver problemas nos logs
- ⚠️ Não reflete jogadores que estavam online antes do primeiro registro

---

#### 3. **Tabela `bank_transactions`** (Dados Adicionais)
```sql
-- Campo relevante:
players_online INTEGER  -- Número de jogadores online no momento da transação
```

**O que temos:**
- ✅ Snapshots esporádicos de jogadores online (quando há transações bancárias)
- ✅ Timestamp de cada transação

**Limitação:**
- ❌ Dados muito esparsos (só quando há transações)
- ❌ Não cobre todos os horários

---

## 🔍 Análise: O que PODEMOS fazer com os dados atuais?

### ✅ **OPÇÃO 1: Usar `player_logins` para Reconstruir Histórico**

**Como funciona:**
1. Para cada hora do dia, reconstruir o estado dos jogadores
2. Contar quantos tinham `login` sem `logout` correspondente até aquele momento
3. Calcular média por hora do dia

**Vantagens:**
- ✅ Não precisa coletar novos dados
- ✅ Funciona com dados históricos existentes
- ✅ Implementação relativamente simples
- ✅ **Dados precisos:** Timestamps exatos de login/logout
- ✅ **Índices otimizados:** Consultas rápidas
- ✅ **Histórico completo:** Dados retroativos desde o início

**Desvantagens:**
- ⚠️ Processamento pode ser lento para muitos dados (mas otimizável)
- ⚠️ Não reflete jogadores que já estavam online antes do primeiro registro (caso raro)

**Precisão estimada:** 90-95% ✅ (VALIDADO - Ver `ANALISE_PLAYER_LOGINS_PARA_RELATORIO.md`)

---

### ✅ **OPÇÃO 2: Criar Tabela de Snapshots Periódicos** (RECOMENDADO)

**Nova tabela: `server_player_count_history`**
```sql
CREATE TABLE server_player_count_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp DATETIME NOT NULL,
    player_count INTEGER NOT NULL,
    date DATE NOT NULL,
    hour INTEGER NOT NULL,  -- 0-23
    day_of_week INTEGER,    -- 0=Segunda, 6=Domingo
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(timestamp)
);

CREATE INDEX idx_player_count_date ON server_player_count_history(date);
CREATE INDEX idx_player_count_hour ON server_player_count_history(hour);
CREATE INDEX idx_player_count_timestamp ON server_player_count_history(timestamp);
```

**Como funciona:**
1. Criar um serviço que roda periodicamente (ex: a cada 15 minutos ou 1 hora)
2. Contar jogadores online naquele momento
3. Salvar snapshot na tabela
4. Usar os snapshots para gerar relatórios

**Vantagens:**
- ✅ Dados precisos e confiáveis
- ✅ Consultas rápidas (dados agregados)
- ✅ Permite análises detalhadas (por hora, dia da semana, etc.)
- ✅ Não depende de reconstrução de eventos

**Desvantagens:**
- ⚠️ Precisa implementar coleta periódica
- ⚠️ Dados históricos só começam a partir da implementação
- ⚠️ Requer espaço adicional no banco (mas é mínimo)

**Precisão estimada:** 95-99%

---

### ✅ **OPÇÃO 3: Híbrida (Melhor dos dois mundos)**

**Como funciona:**
1. Implementar sistema de snapshots (Opção 2) para dados futuros
2. Usar `player_logins` para reconstruir dados históricos passados
3. Combinar ambos nos relatórios

**Vantagens:**
- ✅ Dados precisos a partir de agora
- ✅ Histórico retroativo usando `player_logins`
- ✅ Melhor cobertura temporal

**Desvantagens:**
- ⚠️ Implementação mais complexa
- ⚠️ Pode haver inconsistências entre métodos

---

## 🎨 Proposta de Implementação

### **FASE 1: Coleta de Dados** (Opção 2 - Recomendada)

#### 1.1 Criar Tabela de Histórico
```sql
CREATE TABLE server_player_count_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp DATETIME NOT NULL,
    player_count INTEGER NOT NULL,
    date DATE NOT NULL,
    hour INTEGER NOT NULL,
    day_of_week INTEGER,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(timestamp)
);
```

#### 1.2 Criar Serviço de Coleta Periódica
- **Arquivo:** `core/reports/player_count_collector.py`
- **Frequência:** A cada 15 minutos (configurável)
- **Função:** Contar jogadores online e salvar snapshot

#### 1.3 Integrar com Sistema Existente
- Usar `OnlinePlayersMonitor` existente para obter contagem
- Adicionar ao scheduler do sistema

---

### **FASE 2: API de Relatórios**

#### 2.1 Endpoint: Média Diária
```
GET /api/reports/players/daily-average
```

**Parâmetros:**
- `start_date` (opcional): Data inicial (padrão: 7 dias atrás)
- `end_date` (opcional): Data final (padrão: hoje)
- `group_by` (opcional): 'day' | 'hour' | 'day_of_week'

**Resposta:**
```json
{
  "success": true,
  "data": {
    "period": {
      "start": "2025-01-01",
      "end": "2025-01-08"
    },
    "average_players": 12.5,
    "peak_hour": 20,
    "lowest_hour": 4,
    "by_hour": [
      {
        "hour": 0,
        "average": 8.2,
        "min": 3,
        "max": 15
      },
      {
        "hour": 1,
        "average": 7.5,
        "min": 2,
        "max": 14
      }
      // ... 24 horas
    ],
    "by_day": [
      {
        "date": "2025-01-01",
        "average": 11.3,
        "peak": 18,
        "lowest": 5
      }
      // ... dias do período
    ]
  }
}
```

#### 2.2 Endpoint: Dados para Gráfico
```
GET /api/reports/players/chart-data
```

**Parâmetros:**
- `start_date`, `end_date`
- `granularity`: 'hour' | 'day' | 'week'

**Resposta:**
```json
{
  "success": true,
  "data": {
    "labels": ["00:00", "01:00", "02:00", ...],
    "datasets": [
      {
        "label": "Jogadores Online",
        "data": [8, 7, 6, 5, 4, 5, 7, 10, 12, 15, 18, 20, ...],
        "average": 12.5,
        "peak": 25,
        "lowest": 2
      }
    ]
  }
}
```

---

### **FASE 3: Frontend/Visualização**

#### 3.1 Gráfico de Linha (Chart.js ou similar)
- Eixo X: Horas do dia (0-23) ou Datas
- Eixo Y: Número de jogadores
- Linha principal: Média de jogadores
- Área sombreada: Min/Max (opcional)
- Marcadores: Picos e baixas

#### 3.2 Métricas Principais
- **Média geral:** X jogadores
- **Horário de pico:** XX:XX (Y jogadores)
- **Horário de baixa:** XX:XX (Z jogadores)
- **Tendência:** ↑ Crescendo | ↓ Diminuindo | → Estável

#### 3.3 Filtros
- Período (últimos 7 dias, 30 dias, 90 dias)
- Dia da semana específico
- Comparação entre períodos

---

## 📊 Estrutura de Dados Proposta

### Tabela: `server_player_count_history`

```sql
CREATE TABLE server_player_count_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp DATETIME NOT NULL,
    player_count INTEGER NOT NULL,
    date DATE NOT NULL,
    hour INTEGER NOT NULL,        -- 0-23
    day_of_week INTEGER,          -- 0=Segunda, 6=Domingo
    week_number INTEGER,          -- Semana do ano (1-52)
    month INTEGER,                 -- 1-12
    year INTEGER,                  -- 2025, 2026, etc.
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(timestamp)
);

-- Índices para performance
CREATE INDEX idx_player_count_date ON server_player_count_history(date);
CREATE INDEX idx_player_count_hour ON server_player_count_history(hour);
CREATE INDEX idx_player_count_day_of_week ON server_player_count_history(day_of_week);
CREATE INDEX idx_player_count_timestamp ON server_player_count_history(timestamp DESC);
CREATE INDEX idx_player_count_date_hour ON server_player_count_history(date, hour);
```

**Tamanho estimado:**
- 1 registro a cada 15 minutos = 96 registros/dia
- 96 registros × 365 dias = ~35.000 registros/ano
- Cada registro ≈ 100 bytes
- **Total: ~3.5 MB/ano** (muito pequeno!)

---

## 🔄 Fluxo de Funcionamento

```
┌─────────────────────────────────────────────────────────┐
│  OnlinePlayersMonitor (a cada 30s)                      │
│  └─> Atualiza players_online                            │
└─────────────────────────────────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────────────────────┐
│  PlayerCountCollector (a cada 15 min)                  │
│  └─> Conta jogadores em players_online                  │
│  └─> Salva snapshot em server_player_count_history     │
└─────────────────────────────────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────────────────────┐
│  API Endpoints (/api/reports/players/*)                 │
│  └─> Consulta server_player_count_history              │
│  └─> Calcula médias, picos, baixas                     │
│  └─> Retorna dados formatados para gráficos             │
└─────────────────────────────────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────────────────────┐
│  Frontend (Gráficos)                                    │
│  └─> Chart.js / Plotly / etc.                          │
│  └─> Visualiza dados de picos e baixas                 │
└─────────────────────────────────────────────────────────┘
```

---

## 📈 Exemplo de Relatório

### **Média de Jogadores por Hora (Últimos 7 dias)**

```
Horário | Média | Min | Max | Gráfico
--------|-------|-----|-----|--------
00:00   |  8.2  |  3  | 15  | ████████░░
01:00   |  7.5  |  2  | 14  | ███████░░░
02:00   |  6.8  |  2  | 12  | ██████░░░░
03:00   |  5.2  |  1  | 10  | █████░░░░░
04:00   |  4.1  |  0  |  8  | ████░░░░░░
05:00   |  4.5  |  1  |  9  | ████░░░░░░
06:00   |  5.8  |  2  | 11  | █████░░░░░
07:00   |  7.2  |  3  | 13  | ███████░░░
08:00   |  9.5  |  4  | 16  | █████████░
09:00   | 12.3  |  6  | 19  | ████████████
10:00   | 15.1  |  8  | 22  | ███████████████
11:00   | 17.8  | 10  | 25  | ██████████████████
12:00   | 19.5  | 12  | 27  | ███████████████████
13:00   | 20.2  | 13  | 28  | ████████████████████
14:00   | 21.1  | 14  | 29  | █████████████████████
15:00   | 22.3  | 15  | 30  | ██████████████████████
16:00   | 23.5  | 16  | 31  | ███████████████████████
17:00   | 24.2  | 17  | 32  | ████████████████████████
18:00   | 25.1  | 18  | 33  | █████████████████████████
19:00   | 25.8  | 19  | 34  | ██████████████████████████
20:00   | 26.2  | 20  | 35  | ███████████████████████████  ← PICO
21:00   | 25.5  | 19  | 34  | ██████████████████████████
22:00   | 23.8  | 17  | 32  | █████████████████████████
23:00   | 19.2  | 12  | 28  | ████████████████████

📊 RESUMO:
• Média geral: 15.2 jogadores
• Horário de pico: 20:00 (26.2 jogadores)
• Horário de baixa: 04:00 (4.1 jogadores)
• Variação: 22.1 jogadores (pico - baixa)
```

---

## 🛠️ Arquivos a Criar/Modificar

### **Novos Arquivos:**
1. `core/reports/__init__.py`
2. `core/reports/player_count_collector.py` - Coleta periódica
3. `core/reports/player_count_service.py` - Lógica de relatórios
4. `main.py` - Adicionar endpoints de relatórios
5. `utils/database_initializer.py` - Adicionar criação da nova tabela

### **Modificações:**
1. `main.py` - Adicionar rotas de API
2. `utils/database_initializer.py` - Inicializar nova tabela
3. `core/scheduler/` - Agendar coleta periódica (se existir)

---

## ⚙️ Configuração

### `config.json`
```json
{
  "reports": {
    "player_count_collection": {
      "enabled": true,
      "interval_minutes": 15,
      "retention_days": 365
    }
  }
}
```

---

## 📝 Próximos Passos

1. **Decisão:** Escolher entre Opção 1, 2 ou 3
2. **Implementação Fase 1:** Criar tabela e serviço de coleta
3. **Implementação Fase 2:** Criar endpoints de API
4. **Implementação Fase 3:** Criar visualização frontend (se necessário)
5. **Testes:** Validar dados coletados
6. **Documentação:** Documentar endpoints e uso

---

## ❓ Perguntas para Decisão

1. **Qual opção prefere?** (1, 2 ou 3)
2. **Frequência de coleta:** 15 minutos, 30 minutos ou 1 hora?
3. **Retenção de dados:** Quantos dias/meses manter histórico?
4. **Frontend:** Já tem frontend ou precisa criar?
5. **Biblioteca de gráficos:** Chart.js, Plotly, ou outra preferência?

---

## 💡 Recomendação Final

**Após análise detalhada da tabela `player_logins`, recomendo a OPÇÃO 1** porque:

### ✅ **Vantagens da Opção 1:**
- ✅ **Dados precisos:** Timestamps exatos de login/logout (validado)
- ✅ **Histórico completo:** Dados retroativos desde o início do sistema
- ✅ **Não precisa coletar novos dados:** Usa dados existentes
- ✅ **Índices otimizados:** Consultas rápidas (já existem)
- ✅ **Implementação simples:** Lógica direta de cálculo
- ✅ **Precisão validada:** 90-95% (ver `ANALISE_PLAYER_LOGINS_PARA_RELATORIO.md`)

### 📊 **Como Funciona:**
1. Para cada timestamp que queremos verificar
2. Encontrar último evento (login/logout) de cada jogador antes desse timestamp
3. Se último evento foi `login` → jogador estava online
4. Se último evento foi `logout` → jogador estava offline
5. Contar quantos estavam online

### 🚀 **Implementação:**
- Criar `core/reports/player_count_calculator.py`
- Adicionar endpoints de API em `main.py`
- Usar queries SQL otimizadas com os índices existentes

**Ver análise completa em:** `docs/ANALISE_PLAYER_LOGINS_PARA_RELATORIO.md`

---

**Pronto para implementar!** 🚀
