# 📊 Análise: Relação entre Logs de Bunkers e Banco de Dados

## 📋 Visão Geral

Este documento descreve a relação entre os logs de bunkers do SCUM e as tabelas no banco de dados `SCUM.db`.

---

## 🔍 Logs Analisados

```
2025.11.19-01.50.20: [LogBunkerLock] D1 Bunker Activated 00h 00m 00s ago
2025.11.19-01.50.22: [LogBunkerLock] A1 Bunker Activated 00h 00m 00s ago
2025.11.19-01.50.32: [LogBunkerLock] Bunker activations:
2025.11.19-01.50.32: [LogBunkerLock] D1 Bunker is Active. Activated 00h 00m 00s ago. X=-537889.562 Y=540004.312 Z=81279.648
2025.11.19-01.50.32: [LogBunkerLock] A1 Bunker is Active. Activated 00h 00m 00s ago. X=-348529.312 Y=-469201.781 Z=4247.645
2025.11.19-01.50.32: [LogBunkerLock] Locked bunkers:
2025.11.19-01.50.32: [LogBunkerLock] A3 Bunker is Locked. Locked 00h 00m 00s ago, next Activation in 23h 59m 59s. X=230229.672 Y=-447157.625 Z=9555.422
2025.11.19-01.50.32: [LogBunkerLock] C4 Bunker is Locked. Locked 00h 00m 00s ago, next Activation in 23h 59m 59s. X=446323.000 Y=263051.188 Z=18552.514
```

---

## 🗄️ Tabelas Relacionadas

### **1. `custom_zone_region` - Mapeamento de Nomes e Coordenadas**

Esta tabela contém o **mapeamento de nomes de bunkers** (D1, A1, A3, C4) com suas coordenadas no mapa.

#### **Estrutura**

```sql
CREATE TABLE custom_zone_region (
    id INTEGER PRIMARY KEY,
    map_id INTEGER,
    name CHAR(100),
    location_x REAL,
    location_y REAL,
    size_x REAL,
    size_y REAL,
    configuration_index TINYINT,
    default_region_name CHAR(50),
    default_region_state TINYINT
);
```

#### **Dados Encontrados**

| ID | Nome | Location X | Location Y | Size X | Size Y |
|---|---|---|---|---|---|
| 1 | Bunker D1 | -534410 | 542036 | 16000 | 0 |
| 2 | Bunker A1 | -353073 | -463033 | 20000 | 0 |
| 3 | Bunker A3 | 235306 | -447600 | 16000 | 0 |
| 4 | Bunker C4 | 443168 | 266172 | 16000 | 0 |

#### **Função**

- **Mapeia nomes de bunkers** para suas coordenadas no mapa
- As coordenadas são **aproximadamente 100x maiores** que as coordenadas na tabela `abandoned_bunker`
- As coordenadas do log são **próximas** às coordenadas desta tabela (diferença de alguns milhares de unidades, provavelmente representando objetos/entidades dentro dos bunkers)

---

### **2. `abandoned_bunker` - Status de Ativação/Bloqueio**

Esta tabela contém o **status de ativação e bloqueio** dos bunkers.

#### **Estrutura**

```sql
CREATE TABLE abandoned_bunker (
    id INTEGER PRIMARY KEY,
    user_profile_id INTEGER,
    map_id INTEGER,
    location_x INTEGER,
    location_y INTEGER,
    is_day INTEGER,
    time_since_previous_activation_end REAL,
    time_until_activation_start REAL,
    keycard_override_activation_start REAL
);
```

#### **Campos Importantes**

| Campo | Descrição |
|---|---|
| `time_until_activation_start` | **0 = Active** (bunker ativado)<br>**> 0 = Locked** (bunker bloqueado, valor é o tempo até próxima ativação em segundos) |
| `time_since_previous_activation_end` | Tempo desde o fim da última ativação (em segundos) |
| `keycard_override_activation_start` | Timestamp de override de ativação via keycard (se aplicável) |

#### **Dados Encontrados (Relacionados aos Logs)**

| Bunker | Zone Region ID | Bunker ID | Status | Time Until Start |
|---|---|---|---|---|
| D1 | 1 | 23 | **Active** | 0.00 (0h 0m 0s) |
| A1 | 2 | 20 | **Active** | 0.00 (0h 0m 0s) |
| A3 | 3 | 21 | **Locked** | 86399.80 (23h 59m 59s) |
| C4 | 4 | 22 | **Locked** | 86399.80 (23h 59m 59s) |

---

## 🔗 Relação entre as Tabelas

### **Mapeamento de Nomes para IDs**

A relação entre `custom_zone_region` e `abandoned_bunker` é feita através de **proximidade de coordenadas**:

1. **`custom_zone_region`** fornece o nome do bunker (D1, A1, A3, C4) e coordenadas em escala maior
2. **`abandoned_bunker`** fornece o status (Active/Locked) e coordenadas em escala menor (aproximadamente 100x menor)

### **Correspondência de Coordenadas**

| Bunker | Zone Region (X, Y) | Log (X, Y) | Bunker ID | Bunker DB (X, Y) |
|---|---|---|---|---|
| D1 | (-534410, 542036) | (-537890, 540004) | 23 | (-5434, 5444) |
| A1 | (-353073, -463033) | (-348529, -469202) | 20 | (-3415, -4709) |
| A3 | (235306, -447600) | (230230, -447158) | 21 | (2270, -4407) |
| C4 | (443168, 266172) | (446323, 263051) | 22 | (4483, 2699) |

**Observações:**
- As coordenadas do **log** são próximas às de `custom_zone_region` (diferença de alguns milhares)
- As coordenadas de `abandoned_bunker` são aproximadamente **100x menores** que as de `custom_zone_region`
- As coordenadas do log provavelmente representam **objetos/entidades dentro dos bunkers**, não os bunkers em si

---

## 📊 Consultas Úteis

### **1. Listar Todos os Bunkers com Status**

```sql
SELECT 
    czr.name as bunker_name,
    czr.location_x as zone_x,
    czr.location_y as zone_y,
    ab.id as bunker_id,
    ab.location_x as bunker_x,
    ab.location_y as bunker_y,
    CASE 
        WHEN ab.time_until_activation_start = 0 THEN 'Active'
        WHEN ab.time_until_activation_start > 0 THEN 'Locked'
        ELSE 'Unknown'
    END as status,
    ab.time_since_previous_activation_end as time_since_activation,
    ab.time_until_activation_start as time_until_activation
FROM custom_zone_region czr
LEFT JOIN abandoned_bunker ab ON (
    ABS(czr.location_x / 100 - ab.location_x) < 100
    AND ABS(czr.location_y / 100 - ab.location_y) < 100
)
WHERE czr.name LIKE 'Bunker%'
ORDER BY czr.name;
```

### **2. Buscar Bunker por Nome (D1, A1, A3, C4)**

```sql
SELECT 
    czr.name,
    czr.location_x,
    czr.location_y,
    ab.id,
    ab.time_until_activation_start,
    CASE 
        WHEN ab.time_until_activation_start = 0 THEN 'Active'
        ELSE 'Locked'
    END as status
FROM custom_zone_region czr
LEFT JOIN abandoned_bunker ab ON (
    ABS(czr.location_x / 100 - ab.location_x) < 100
    AND ABS(czr.location_y / 100 - ab.location_y) < 100
)
WHERE czr.name = 'Bunker D1';  -- ou A1, A3, C4
```

### **3. Listar Bunkers Ativos**

```sql
SELECT 
    czr.name,
    ab.time_since_previous_activation_end
FROM custom_zone_region czr
LEFT JOIN abandoned_bunker ab ON (
    ABS(czr.location_x / 100 - ab.location_x) < 100
    AND ABS(czr.location_y / 100 - ab.location_y) < 100
)
WHERE czr.name LIKE 'Bunker%'
AND ab.time_until_activation_start = 0
ORDER BY czr.name;
```

### **4. Listar Bunkers Bloqueados com Tempo Restante**

```sql
SELECT 
    czr.name,
    ab.time_until_activation_start,
    CAST(ab.time_until_activation_start / 3600 AS INTEGER) as hours_remaining,
    CAST((ab.time_until_activation_start % 3600) / 60 AS INTEGER) as minutes_remaining
FROM custom_zone_region czr
LEFT JOIN abandoned_bunker ab ON (
    ABS(czr.location_x / 100 - ab.location_x) < 100
    AND ABS(czr.location_y / 100 - ab.location_y) < 100
)
WHERE czr.name LIKE 'Bunker%'
AND ab.time_until_activation_start > 0
ORDER BY ab.time_until_activation_start;
```

---

## 💡 Conclusões

1. **`custom_zone_region`**: Contém o mapeamento de nomes de bunkers (D1, A1, A3, C4) com coordenadas em escala maior
2. **`abandoned_bunker`**: Contém o status de ativação/bloqueio com coordenadas em escala menor
3. **Relação**: A correspondência é feita por proximidade de coordenadas (dividindo as coordenadas de `custom_zone_region` por 100)
4. **Logs**: As coordenadas nos logs são próximas às de `custom_zone_region`, provavelmente representando objetos/entidades dentro dos bunkers

---

## 🔧 Possíveis Melhorias

1. **Criar uma tabela de mapeamento explícito** entre `custom_zone_region.id` e `abandoned_bunker.id` para facilitar consultas
2. **Adicionar índices** nas colunas de coordenadas para melhorar performance de JOINs
3. **Criar uma view** que combine as duas tabelas para facilitar consultas frequentes

---

## 📝 Notas Técnicas

- As coordenadas em `custom_zone_region` são em **escala de mapa** (centenas de milhares)
- As coordenadas em `abandoned_bunker` são em **escala reduzida** (milhares)
- A relação de escala é aproximadamente **100:1** (custom_zone_region : abandoned_bunker)
- As coordenadas do log são em escala similar a `custom_zone_region`, mas podem representar objetos específicos dentro dos bunkers

