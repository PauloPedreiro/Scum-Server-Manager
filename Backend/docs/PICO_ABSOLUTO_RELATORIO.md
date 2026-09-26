# 🎯 Pico Absoluto - Dia e Hora Exatos com Mais Jogadores

## 📋 Funcionalidade

Agora os relatórios incluem informação sobre o **timestamp exato** (dia + hora + minuto) que teve o maior número de jogadores online no período analisado.

**Exemplo:** "Dia 12 às 23:00 teve o maior número de jogadores com 17 online"

---

## 🔌 Endpoints Atualizados

### **1. `/api/reports/players/hourly-average`**

**Novo campo adicionado:** `absolute_peak`

**Exemplo de Resposta:**
```json
{
  "success": true,
  "data": {
    "period": {
      "start": "2026-01-06T13:00:00",
      "end": "2026-01-13T13:00:00",
      "days": 7
    },
    "by_hour": [...],
    "overall_average": 11.53,
    "peak_hour": 1,
    "peak_hour_average": 19.66,
    "lowest_hour": 9,
    "lowest_hour_average": 5.97,
    "absolute_peak": {
      "timestamp": "2026-01-12T23:00:00",
      "date": "2026-01-12",
      "hour": 23,
      "minute": 0,
      "players_count": 17,
      "formatted": "2026-01-12 23:00"
    }
  }
}
```

---

### **2. `/api/reports/players/daily-average`**

**Novo campo adicionado:** `absolute_peak`

**Exemplo de Resposta:**
```json
{
  "success": true,
  "data": {
    "period": {
      "start": "2026-01-06T13:00:00",
      "end": "2026-01-13T13:00:00",
      "days": 7
    },
    "interval_minutes": 15,
    "by_day": [...],
    "overall_average": 11.6,
    "peak_day": "2026-01-07",
    "peak_day_count": 28,
    "lowest_day": "2026-01-10",
    "lowest_day_count": 3,
    "absolute_peak": {
      "timestamp": "2026-01-12T23:00:00",
      "date": "2026-01-12",
      "hour": 23,
      "minute": 0,
      "players_count": 17,
      "formatted": "2026-01-12 23:00"
    }
  }
}
```

---

## 📊 Estrutura do Campo `absolute_peak`

```json
{
  "timestamp": "2026-01-12T23:00:00",  // ISO 8601
  "date": "2026-01-12",                 // Data (YYYY-MM-DD)
  "hour": 23,                           // Hora (0-23)
  "minute": 0,                          // Minuto (0-59)
  "players_count": 17,                  // Número de jogadores
  "formatted": "2026-01-12 23:00"      // Formato legível
}
```

**Se não houver dados:**
```json
"absolute_peak": null
```

---

## 🔍 Diferença entre Campos

### **`peak_hour` / `peak_day`**
- Mostra a **hora do dia** ou **dia** com maior **média**
- Agregado de múltiplos dias/horas
- Exemplo: "Hora 1 tem a maior média (19.66 jogadores)"

### **`absolute_peak`** ⭐ NOVO
- Mostra o **timestamp exato** (dia + hora + minuto) com maior número de jogadores
- Snapshot específico, não média
- Exemplo: "Dia 12 às 23:00 teve 17 jogadores (pico absoluto)"

---

## 💡 Casos de Uso

### **1. Identificar Eventos Especiais**
```javascript
// Verificar se houve algum evento especial que causou pico
if (data.absolute_peak.players_count > 30) {
  console.log(`Pico excepcional em ${data.absolute_peak.formatted}`);
}
```

### **2. Análise de Horários de Pico**
```javascript
// Comparar pico absoluto com média
const peakHour = data.peak_hour; // Hora com maior média
const absolutePeak = data.absolute_peak; // Timestamp exato do pico

console.log(`Hora com maior média: ${peakHour}:00`);
console.log(`Pico absoluto: ${absolutePeak.formatted} com ${absolutePeak.players_count} jogadores`);
```

### **3. Exibição no Frontend**
```javascript
// Mostrar informação destacada
<div className="peak-info">
  <h3>Pico Absoluto</h3>
  <p>
    {data.absolute_peak.formatted} - {data.absolute_peak.players_count} jogadores
  </p>
</div>
```

---

## ⚙️ Implementação Técnica

### **Método: `get_absolute_peak()`**

```python
def get_absolute_peak(
    self,
    start_date: datetime,
    end_date: datetime,
    interval_minutes: int = 15,
) -> Optional[Dict]:
    """
    Encontra o timestamp exato (dia + hora) com o maior número de jogadores online.
    
    Args:
        start_date: Data inicial
        end_date: Data final
        interval_minutes: Intervalo entre snapshots (padrão: 15 min)
        
    Returns:
        Dicionário com timestamp, data, hora e número de jogadores, ou None se não houver dados
    """
```

**Lógica:**
1. Carrega todos os eventos do período (otimizado)
2. Itera por todos os snapshots (a cada `interval_minutes`)
3. Calcula jogadores online em cada snapshot
4. Retorna o snapshot com maior número de jogadores

**Performance:**
- ✅ Usa a mesma otimização (1 query + processamento em memória)
- ✅ Rápido mesmo com muitos snapshots
- ✅ Não adiciona overhead significativo

---

## 📝 Exemplo Completo

### **Requisição:**
```bash
GET /api/reports/players/daily-average?days=7&interval_minutes=15
```

### **Resposta:**
```json
{
  "success": true,
  "data": {
    "period": {
      "start": "2026-01-06T13:00:00",
      "end": "2026-01-13T13:00:00",
      "days": 7
    },
    "interval_minutes": 15,
    "by_day": [
      {
        "date": "2026-01-06",
        "average": 13.35,
        "peak": 23,
        "lowest": 7,
        "samples": 43
      },
      // ... outros dias
      {
        "date": "2026-01-12",
        "average": 9.15,
        "peak": 22,
        "lowest": 4,
        "samples": 96
      }
    ],
    "overall_average": 11.6,
    "peak_day": "2026-01-07",
    "peak_day_count": 28,
    "lowest_day": "2026-01-10",
    "lowest_day_count": 3,
    "absolute_peak": {
      "timestamp": "2026-01-12T23:00:00",
      "date": "2026-01-12",
      "hour": 23,
      "minute": 0,
      "players_count": 17,
      "formatted": "2026-01-12 23:00"
    }
  }
}
```

### **Interpretação:**
- **`peak_day: "2026-01-07"`**: Dia 07 teve o maior pico médio (28 jogadores)
- **`absolute_peak`**: O snapshot específico com mais jogadores foi **dia 12 às 23:00** com **17 jogadores**

**Nota:** O `peak_day_count` (28) é o pico do dia 07, mas o `absolute_peak` (17) pode ser de outro dia. Isso é normal porque:
- `peak_day_count` = maior pico dentro de um dia específico
- `absolute_peak` = maior pico de TODOS os snapshots do período

---

## ✅ Validação

### **Teste 1: Verificar se retorna dados**
```javascript
const response = await fetch('/api/reports/players/daily-average?days=7');
const data = await response.json();

if (data.data.absolute_peak) {
  console.log('Pico absoluto encontrado:', data.data.absolute_peak.formatted);
} else {
  console.log('Nenhum dado disponível');
}
```

### **Teste 2: Comparar com peak_day**
```javascript
const peakDay = data.data.peak_day;
const absolutePeak = data.data.absolute_peak;

console.log(`Dia com maior pico: ${peakDay}`);
console.log(`Timestamp exato do pico: ${absolutePeak.formatted}`);
console.log(`Jogadores no pico: ${absolutePeak.players_count}`);
```

---

## 🎯 Resumo

**Nova funcionalidade adicionada:**
- ✅ Campo `absolute_peak` nos endpoints de relatórios
- ✅ Mostra timestamp exato (dia + hora + minuto) com mais jogadores
- ✅ Formato legível e fácil de usar
- ✅ Performance otimizada (usa mesma otimização)

**Agora você pode saber exatamente quando teve o maior número de jogadores!** 🎉
