# 🔍 Análise dos JSONs Retornados pelos Endpoints

## 📊 Análise dos Resultados

### ✅ **Estrutura dos JSONs: CORRETA**

Todos os JSONs têm a estrutura correta conforme especificado na documentação.

---

## ⚠️ **Problemas Identificados**

### 1. **JSON 1 e 2: Média por Hora - Valores Idênticos**

**Problema:** Todas as 24 horas têm exatamente a mesma média (13.38)

**Análise:**
- ✅ Estrutura correta
- ✅ 24 horas presentes (0-23)
- ⚠️ **Todas as médias são idênticas** (13.38)
- ⚠️ **`samples: 8`** quando deveria ser 7 (7 dias)

**Possíveis Causas:**

#### **Causa 1: Dados Realmente Constantes**
Se o servidor teve número constante de jogadores durante todo o período, isso é normal. Mas o fato de `min=6` e `max=16` sugere que há variação, então a média não deveria ser igual.

#### **Causa 2: Bug no Cálculo (Mais Provável)**
O problema pode estar na lógica de `get_hourly_average`:
- Está calculando para cada hora do dia (0-23)
- Para cada dia no período (7 dias)
- Mas pode estar usando o mesmo timestamp ou calculando errado

**Verificação Necessária:**
```python
# O código atual faz:
timestamp = datetime.combine(
    current_date, datetime.min.time().replace(hour=hour)
)
# Isso cria: 2026-01-06 00:00:00, 2026-01-06 01:00:00, etc.
# Parece correto, mas vamos verificar se está realmente variando
```

#### **Causa 3: Dados Insuficientes**
Se há poucos dados de login/logout, pode estar retornando sempre o mesmo valor.

---

### 2. **JSON 2: `peak_hour` e `lowest_hour` Incorretos**

**Problema:**
```json
"peak_hour": 0,
"lowest_hour": 0,
"peak_hour_average": 13.38,
"lowest_hour_average": 13.38
```

**Análise:**
- Se todas as médias são iguais (13.38), `peak_hour` e `lowest_hour` deveriam ser `null` ou ter lógica diferente
- Atualmente está retornando `0` (primeira hora) para ambos, o que não faz sentido

**Correção Necessária:**
```python
# No endpoint, quando todas as médias são iguais:
if all(h['average'] == hourly_data[0]['average'] for h in hourly_data):
    peak_hour_data = None
    lowest_hour_data = None
else:
    peak_hour_data = max(hourly_data, key=lambda x: x['average'])
    lowest_hour_data = min(hourly_data, key=lambda x: x['average'])
```

---

### 3. **JSON 2: `samples: 8` em vez de 7**

**Problema:** Mostra 8 amostras quando o período é de 7 dias

**Análise:**
- Período: 2026-01-06 até 2026-01-13 = 8 dias (inclusive)
- Cálculo: `end_date - start_date = 7 dias`, mas inclui ambos os dias = 8 dias
- **Isso está CORRETO!** (6, 7, 8, 9, 10, 11, 12, 13 = 8 dias)

**Conclusão:** Não é um erro, está correto.

---

### 4. **JSON 3: Média por Dia - CORRETO ✅**

**Análise:**
- ✅ Há variação entre dias (15, 14, 16, 15, 6, 11, 16, 14)
- ✅ `samples` varia corretamente:
  - Primeiro dia: 44 amostras (início do período)
  - Dias intermediários: 96 amostras (24h × 4 snapshots/hora = 96)
  - Último dia: 53 amostras (até o momento atual)
- ✅ `peak_day` e `lowest_day` corretos
- ✅ `overall_average` calculado corretamente

**Este JSON está PERFEITO!** ✅

---

## 🔧 Correções Necessárias

### 1. **Corrigir Lógica de `peak_hour` e `lowest_hour`**

Quando todas as médias são iguais, retornar `null`:

```python
# No endpoint get_players_hourly_average
if hourly_data:
    # Verificar se todas as médias são iguais
    all_same = all(h['average'] == hourly_data[0]['average'] for h in hourly_data)
    
    if all_same:
        peak_hour_data = None
        lowest_hour_data = None
    else:
        peak_hour_data = max(hourly_data, key=lambda x: x['average'])
        lowest_hour_data = min(hourly_data, key=lambda x: x['average'])
```

### 2. **Investigar Por Que Médias São Idênticas**

**Teste Sugerido:**
```python
# Adicionar logs para debug
for hour in range(24):
    timestamp = datetime.combine(current_date, datetime.min.time().replace(hour=hour))
    count = self.get_players_online_at(timestamp)
    print(f"Hora {hour:02d}:00 - Jogadores: {count}")
```

**Verificar:**
- Se os timestamps estão variando corretamente
- Se a query SQL está retornando valores diferentes
- Se há dados suficientes em `player_logins`

---

## 📋 Resumo da Análise

| Item | Status | Observação |
|------|--------|------------|
| **Estrutura JSON 1** | ✅ Correto | Formato correto |
| **Estrutura JSON 2** | ✅ Correto | Formato correto |
| **Estrutura JSON 3** | ✅ Correto | Formato correto |
| **Valores JSON 1** | ⚠️ Suspeito | Todas as horas = 13.38 |
| **Valores JSON 2** | ⚠️ Suspeito | Todas as horas = 13.38 |
| **Valores JSON 3** | ✅ Correto | Variação entre dias |
| **peak_hour/lowest_hour** | ❌ Incorreto | Ambos = 0 quando deveria ser null |
| **samples** | ✅ Correto | 8 dias está correto |

---

## 🎯 Conclusão

### ✅ **O que está CORRETO:**
1. Estrutura dos JSONs
2. Cálculo de média por dia (JSON 3)
3. Número de samples (8 dias está correto)

### ⚠️ **O que precisa INVESTIGAR:**
1. Por que todas as horas têm a mesma média (13.38)?
   - Pode ser dados reais (servidor constante)
   - Pode ser bug no cálculo
   - Precisa verificar dados em `player_logins`

### ❌ **O que precisa CORRIGIR:**
1. `peak_hour` e `lowest_hour` devem ser `null` quando todas as médias são iguais
2. Adicionar validação para casos onde não há variação

---

## 🔍 Próximos Passos

1. **Verificar dados reais:**
   ```sql
   SELECT 
     DATE(timestamp) as date,
     CAST(strftime('%H', timestamp) AS INTEGER) as hour,
     COUNT(DISTINCT steam_id) as unique_players
   FROM player_logins
   WHERE action = 'login'
     AND timestamp >= '2026-01-06'
     AND timestamp <= '2026-01-13'
   GROUP BY date, hour
   ORDER BY date, hour;
   ```

2. **Testar cálculo manualmente:**
   - Escolher uma hora específica (ex: 14:00)
   - Verificar quantos jogadores estavam online em cada dia
   - Comparar com o resultado da API

3. **Adicionar logs de debug** no código para entender o que está acontecendo

---

**Os JSONs estão estruturalmente corretos, mas havia problemas no cálculo que foram corrigidos.**

## ✅ **Correções Aplicadas**

Ver documento: `docs/CORRECOES_RELATORIO_JOGADORES.md`

### **Resumo das Correções:**

1. ✅ **`peak_hour` e `lowest_hour`** agora retornam `null` quando todas as médias são iguais
2. ✅ **Cálculo de média por hora** melhorado para usar 4 snapshots por hora (a cada 15 min)
3. ✅ **Validações adicionais** para evitar erros e casos especiais

### **Resultado Esperado Após Correções:**

- Médias por hora devem mostrar variação real (não todas idênticas)
- `peak_hour` e `lowest_hour` devem ser `null` apenas quando realmente todas as médias são iguais
- Número de `samples` aumentou de 8 para 32 (8 dias × 4 snapshots)
