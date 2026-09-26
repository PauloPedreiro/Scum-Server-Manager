# 📊 Colunas da Tabela `rankings` - SSM.db

Este documento lista todas as colunas da tabela `rankings` no banco de dados `SSM.db`.

**Total de Colunas:** 44

---

## 📋 Lista Completa de Colunas

### 🆔 Identificação do Jogador

| # | Coluna | Tipo | Descrição |
|---|--------|------|-----------|
| 1 | `id` | INTEGER | Primary Key (AUTOINCREMENT) |
| 2 | `steam_id` | TEXT | ID Steam do jogador (NOT NULL, UNIQUE) |
| 3 | `player_name` | TEXT | Nome do jogador (NOT NULL) |

---

### ⚔️ Kills e Deaths (kill_events)

| # | Coluna | Tipo | Descrição |
|---|--------|------|-----------|
| 4 | `kills` | INTEGER | Total de kills PvP (exclui NPCs) |
| 5 | `deaths` | INTEGER | Total de mortes |
| 6 | `kdr` | REAL | Kill/Death Ratio (calculado: kills / deaths) |

---

### 🎯 Longest Shot (kill_events)

| # | Coluna | Tipo | Descrição |
|---|--------|------|-----------|
| 7 | `longest_shot_distance` | REAL | Maior distância de tiro em metros |
| 8 | `longest_shot_weapon` | TEXT | Nome da arma usada no tiro mais longo |
| 9 | `longest_shot_timestamp` | DATETIME | Data/hora do tiro mais longo |

---

### 💀 Suicides (kill_events)

| # | Coluna | Tipo | Descrição |
|---|--------|------|-----------|
| 10 | `suicides` | INTEGER | Total de suicídios (event_type='suicide') |

---

### 🔓 Lockpicking - Basic (minigame_events)

| # | Coluna | Tipo | Descrição |
|---|--------|------|-----------|
| 11 | `lockpick_basic_success` | INTEGER | Sucessos em lockpicking básico |
| 12 | `lockpick_basic_fails` | INTEGER | Falhas em lockpicking básico |
| 13 | `lockpick_basic_total` | INTEGER | Total de tentativas básicas (calculado) |
| 14 | `lockpick_basic_rate` | REAL | Taxa de sucesso básico % (calculado) |

---

### 🔓 Lockpicking - Medium (minigame_events)

| # | Coluna | Tipo | Descrição |
|---|--------|------|-----------|
| 15 | `lockpick_medium_success` | INTEGER | Sucessos em lockpicking médio |
| 16 | `lockpick_medium_fails` | INTEGER | Falhas em lockpicking médio |
| 17 | `lockpick_medium_total` | INTEGER | Total de tentativas médias (calculado) |
| 18 | `lockpick_medium_rate` | REAL | Taxa de sucesso médio % (calculado) |

---

### 🔓 Lockpicking - Advanced (minigame_events)

| # | Coluna | Tipo | Descrição |
|---|--------|------|-----------|
| 19 | `lockpick_advanced_success` | INTEGER | Sucessos em lockpicking avançado |
| 20 | `lockpick_advanced_fails` | INTEGER | Falhas em lockpicking avançado |
| 21 | `lockpick_advanced_total` | INTEGER | Total de tentativas avançadas (calculado) |
| 22 | `lockpick_advanced_rate` | REAL | Taxa de sucesso avançado % (calculado) |

---

### 🔓 Lockpicking - Very Easy (minigame_events)

| # | Coluna | Tipo | Descrição |
|---|--------|------|-----------|
| 23 | `lockpick_veryeasy_success` | INTEGER | Sucessos em lockpicking muito fácil |
| 24 | `lockpick_veryeasy_fails` | INTEGER | Falhas em lockpicking muito fácil |
| 25 | `lockpick_veryeasy_total` | INTEGER | Total de tentativas muito fáceis (calculado) |
| 26 | `lockpick_veryeasy_rate` | REAL | Taxa de sucesso muito fácil % (calculado) |

---

### 🔓 Lockpicking - Dial Lock (minigame_events)

| # | Coluna | Tipo | Descrição |
|---|--------|------|-----------|
| 27 | `lockpick_diallock_success` | INTEGER | Sucessos em cadeado (dial lock) |
| 28 | `lockpick_diallock_fails` | INTEGER | Falhas em cadeado (dial lock) |
| 29 | `lockpick_diallock_total` | INTEGER | Total de tentativas em cadeado (calculado) |
| 30 | `lockpick_diallock_rate` | REAL | Taxa de sucesso em cadeado % (calculado) |

---

### 🔓 Lockpicking - Other (minigame_events)

| # | Coluna | Tipo | Descrição |
|---|--------|------|-----------|
| 31 | `lockpick_other_success` | INTEGER | Sucessos em outros tipos de lockpicking |
| 32 | `lockpick_other_fails` | INTEGER | Falhas em outros tipos de lockpicking |
| 33 | `lockpick_other_total` | INTEGER | Total de tentativas outros (calculado) |
| 34 | `lockpick_other_rate` | REAL | Taxa de sucesso outros % (calculado) |

---

### 🚗 Vehicle Destruction (vehicle_destruction_events)

| # | Coluna | Tipo | Descrição |
|---|--------|------|-----------|
| 35 | `vehicles_destroyed` | INTEGER | Total de veículos destruídos |

---

### 🏃 Survival Stats (survival_stats_snapshot)

| # | Coluna | Tipo | Descrição |
|---|--------|------|-----------|
| 36 | `highest_defecation` | INTEGER | Maior Cagão - Maior valor de total_defecations |
| 37 | `animals_killed` | INTEGER | Caça - Total de animais mortos |
| 38 | `players_knocked_out` | INTEGER | Master Bruce Lee - Total de nocautes em jogadores |
| 39 | `headshots` | INTEGER | Total de headshots |
| 40 | `minutes_survived` | REAL | Minutos Sobrevividos - Maior tempo de sobrevivência |
| 41 | `overdoses` | INTEGER | Total de overdoses (overdose) |
| 42 | `highest_weight_carried` | REAL | Hulk - Maior peso já carregado em kg |

---

### ⭐ Fama (player_fame_totals)

| # | Coluna | Tipo | Descrição |
|---|--------|------|-----------|
| 43 | `total_fame` | REAL | Total de fama acumulada do jogador |

---

### 📅 Metadata

| # | Coluna | Tipo | Descrição |
|---|--------|------|-----------|
| 44 | `last_updated` | DATETIME | Última atualização dos dados (DEFAULT CURRENT_TIMESTAMP) |

---

## 📊 Resumo por Categoria

- **Identificação:** 3 colunas
- **Kills/Deaths:** 3 colunas
- **Longest Shot:** 3 colunas
- **Suicides:** 1 coluna
- **Lockpicking (6 tipos):** 24 colunas (4 colunas por tipo)
- **Vehicle Destruction:** 1 coluna
- **Survival Stats:** 7 colunas
- **Fama:** 1 coluna
- **Metadata:** 1 coluna

---

## 🔍 Observações

1. **Lockpicking Detalhado:** A tabela possui lockpicking separado por 6 níveis/dificuldades:
   - Basic
   - Medium
   - Advanced
   - Very Easy
   - Dial Lock
   - Other

2. **Colunas Calculadas:** Algumas colunas são calculadas automaticamente:
   - `kdr` = kills / deaths
   - `lockpick_*_total` = success + fails
   - `lockpick_*_rate` = (success / total) * 100

3. **Constraint UNIQUE:** A coluna `steam_id` possui constraint UNIQUE, garantindo um registro por jogador.

4. **Índices:** A tabela possui índices para otimização de consultas (ver documentação de schema completo).

---

**Última atualização:** Gerado automaticamente a partir do banco de dados `SSM.db`

