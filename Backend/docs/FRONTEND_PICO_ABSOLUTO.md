# 🎯 Documentação Frontend: Pico Absoluto de Jogadores

## 📋 Visão Geral

Os endpoints de relatórios agora incluem informação sobre o **timestamp exato** (dia + hora + minuto) que teve o maior número de jogadores online no período analisado.

**Exemplo:** "Dia 23 de dezembro de 2025 às 01:35 teve o maior número de jogadores com 33 online simultaneamente"

---

## 🔌 Endpoints Atualizados

### **1. `/api/reports/players/hourly-average`**

**Novo campo adicionado:** `absolute_peak`

### **2. `/api/reports/players/daily-average`**

**Novo campo adicionado:** `absolute_peak`

---

## 📊 Estrutura do Campo `absolute_peak`

```json
{
  "absolute_peak": {
    "timestamp": "2025-12-23T01:35:10.180745",  // ISO 8601
    "date": "2025-12-23",                        // Data (YYYY-MM-DD)
    "hour": 1,                                   // Hora (0-23)
    "minute": 35,                                // Minuto (0-59)
    "players_count": 33,                         // Número de jogadores
    "formatted": "2025-12-23 01:35"             // Formato legível
  }
}
```

**Se não houver dados:**
```json
"absolute_peak": null
```

---

## 📡 Exemplo de Resposta Completa

### **Endpoint: `/api/reports/players/hourly-average?days=30`**

```json
{
  "success": true,
  "data": {
    "period": {
      "start": "2025-12-14T13:35:10.180745",
      "end": "2026-01-13T13:35:10.180745",
      "days": 30
    },
    "by_hour": [
      {
        "hour": 1,
        "average": 14.11,
        "max": 33,
        "min": 0,
        "samples": 124
      }
      // ... outras horas
    ],
    "overall_average": 9.05,
    "peak_hour": 1,
    "peak_hour_average": 14.11,
    "lowest_hour": 9,
    "lowest_hour_average": 4.23,
    "absolute_peak": {
      "timestamp": "2025-12-23T01:35:10.180745",
      "date": "2025-12-23",
      "hour": 1,
      "minute": 35,
      "players_count": 33,
      "formatted": "2025-12-23 01:35"
    }
  }
}
```

---

## 💡 Diferença entre Campos

### **`peak_hour` / `peak_day`**
- Mostra a **hora do dia** ou **dia** com maior **média**
- Agregado de múltiplos dias/horas
- **Exemplo:** "Hora 1 tem a maior média (14.11 jogadores)"

### **`absolute_peak`** ⭐ NOVO
- Mostra o **timestamp exato** (dia + hora + minuto) com maior número de jogadores
- Snapshot específico, não média
- **Exemplo:** "Dia 23 de dezembro às 01:35 teve 33 jogadores (pico absoluto)"

---

## 🎨 Implementação no Frontend

### **1. Exibição Simples**

```javascript
function displayAbsolutePeak(data) {
  const absolutePeak = data.absolute_peak;
  
  if (!absolutePeak) {
    return <div>Nenhum dado disponível</div>;
  }
  
  return (
    <div className="absolute-peak-card">
      <h3>Pico Absoluto</h3>
      <p className="peak-date">{absolutePeak.formatted}</p>
      <p className="peak-count">{absolutePeak.players_count} jogadores</p>
    </div>
  );
}
```

### **2. Card Destacado**

```jsx
function AbsolutePeakCard({ data }) {
  const absolutePeak = data?.absolute_peak;
  
  if (!absolutePeak) {
    return null;
  }
  
  return (
    <div className="card peak-card">
      <div className="card-header">
        <h3>🎯 Pico Absoluto</h3>
      </div>
      <div className="card-body">
        <div className="peak-info">
          <div className="peak-date">
            <span className="label">Data/Hora:</span>
            <span className="value">{absolutePeak.formatted}</span>
          </div>
          <div className="peak-players">
            <span className="label">Jogadores:</span>
            <span className="value highlight">{absolutePeak.players_count}</span>
          </div>
        </div>
      </div>
    </div>
  );
}
```

### **3. Comparação com Média**

```jsx
function PeakComparison({ data }) {
  const absolutePeak = data.absolute_peak;
  const peakHour = data.peak_hour;
  const peakHourAverage = data.peak_hour_average;
  
  if (!absolutePeak) {
    return null;
  }
  
  return (
    <div className="peak-comparison">
      <div className="comparison-item">
        <h4>Hora com Maior Média</h4>
        <p>{peakHour}:00 - {peakHourAverage.toFixed(1)} jogadores (média)</p>
      </div>
      <div className="comparison-item highlight">
        <h4>Pico Absoluto</h4>
        <p>{absolutePeak.formatted} - {absolutePeak.players_count} jogadores</p>
      </div>
    </div>
  );
}
```

### **4. Formatação de Data (i18n)**

```javascript
function formatAbsolutePeak(absolutePeak, locale = 'pt-BR') {
  if (!absolutePeak) return null;
  
  const date = new Date(absolutePeak.timestamp);
  
  return {
    date: date.toLocaleDateString(locale, {
      year: 'numeric',
      month: 'long',
      day: 'numeric'
    }),
    time: date.toLocaleTimeString(locale, {
      hour: '2-digit',
      minute: '2-digit'
    }),
    full: date.toLocaleString(locale, {
      year: 'numeric',
      month: 'long',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    })
  };
}

// Uso:
const formatted = formatAbsolutePeak(data.absolute_peak);
// {
//   date: "23 de dezembro de 2025",
//   time: "01:35",
//   full: "23 de dezembro de 2025, 01:35"
// }
```

---

## 🎨 CSS Sugerido

```css
.absolute-peak-card {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  padding: 20px;
  border-radius: 12px;
  box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
}

.absolute-peak-card h3 {
  margin: 0 0 15px 0;
  font-size: 18px;
  font-weight: 600;
}

.peak-date {
  font-size: 16px;
  margin-bottom: 8px;
  opacity: 0.9;
}

.peak-count {
  font-size: 32px;
  font-weight: bold;
  margin: 0;
}

.peak-card {
  border: 2px solid #667eea;
  background: #f8f9ff;
}

.peak-info {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.peak-info .label {
  font-weight: 600;
  color: #666;
  margin-right: 8px;
}

.peak-info .value {
  color: #333;
}

.peak-info .value.highlight {
  color: #667eea;
  font-size: 24px;
  font-weight: bold;
}

.peak-comparison {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 20px;
  margin-top: 20px;
}

.comparison-item {
  padding: 15px;
  background: #f5f5f5;
  border-radius: 8px;
}

.comparison-item.highlight {
  background: #fff3cd;
  border: 2px solid #ffc107;
}

.comparison-item h4 {
  margin: 0 0 8px 0;
  font-size: 14px;
  color: #666;
}

.comparison-item p {
  margin: 0;
  font-size: 16px;
  font-weight: 600;
}
```

---

## 📱 Exemplo Completo (React)

```jsx
import React from 'react';

function PlayersReport({ days = 30 }) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    fetchReportData(days);
  }, [days]);

  const fetchReportData = async (daysParam) => {
    try {
      setLoading(true);
      setError(null);

      const response = await fetch(
        `/api/reports/players/hourly-average?days=${daysParam}`,
        {
          headers: {
            'Authorization': `Bearer ${getAuthToken()}`
          }
        }
      );

      const result = await response.json();

      if (!result.success) {
        throw new Error(result.error);
      }

      setData(result.data);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return <div>Carregando dados...</div>;
  }

  if (error) {
    return <div>Erro: {error}</div>;
  }

  if (!data) {
    return <div>Nenhum dado disponível</div>;
  }

  return (
    <div className="players-report">
      <h2>Relatório de Jogadores Online</h2>
      
      {/* Card de Pico Absoluto */}
      {data.absolute_peak && (
        <AbsolutePeakCard data={data} />
      )}

      {/* Estatísticas Gerais */}
      <div className="stats-grid">
        <div className="stat-card">
          <div className="stat-label">Média Geral</div>
          <div className="stat-value">{data.overall_average.toFixed(1)}</div>
          <div className="stat-unit">jogadores</div>
        </div>
        <div className="stat-card">
          <div className="stat-label">Hora de Pico</div>
          <div className="stat-value">{data.peak_hour}:00</div>
          <div className="stat-unit">média: {data.peak_hour_average.toFixed(1)}</div>
        </div>
      </div>

      {/* Gráfico */}
      <ChartComponent data={data} />
    </div>
  );
}

function AbsolutePeakCard({ data }) {
  const peak = data.absolute_peak;
  
  if (!peak) return null;

  // Formatar data em português
  const date = new Date(peak.timestamp);
  const formattedDate = date.toLocaleDateString('pt-BR', {
    day: 'numeric',
    month: 'long',
    year: 'numeric'
  });
  const formattedTime = date.toLocaleTimeString('pt-BR', {
    hour: '2-digit',
    minute: '2-digit'
  });

  return (
    <div className="absolute-peak-card">
      <div className="card-icon">🎯</div>
      <h3>Pico Absoluto</h3>
      <div className="peak-details">
        <div className="peak-date-time">
          <span className="date">{formattedDate}</span>
          <span className="time">{formattedTime}</span>
        </div>
        <div className="peak-count">
          <span className="count">{peak.players_count}</span>
          <span className="label">jogadores online</span>
        </div>
      </div>
    </div>
  );
}

export default PlayersReport;
```

---

## 🎯 Casos de Uso

### **1. Exibir como Destaque**

```jsx
// Card destacado no topo do relatório
{data.absolute_peak && (
  <div className="highlight-banner">
    <h3>🎯 Recorde de Jogadores</h3>
    <p>
      {data.absolute_peak.formatted} - {data.absolute_peak.players_count} jogadores
    </p>
  </div>
)}
```

### **2. Tooltip no Gráfico**

```javascript
// Adicionar anotação no gráfico (Chart.js)
const chartOptions = {
  plugins: {
    annotation: {
      annotations: [{
        type: 'point',
        xValue: data.absolute_peak.formatted,
        yValue: data.absolute_peak.players_count,
        backgroundColor: 'rgba(255, 99, 132, 0.5)',
        borderColor: 'rgb(255, 99, 132)',
        borderWidth: 2,
        radius: 6,
        label: {
          content: `Pico: ${data.absolute_peak.players_count}`,
          enabled: true
        }
      }]
    }
  }
};
```

### **3. Comparação Visual**

```jsx
function PeakComparison({ data }) {
  const absolutePeak = data.absolute_peak;
  const peakHour = data.peak_hour;
  
  return (
    <div className="comparison-container">
      <div className="comparison-card">
        <h4>Hora com Maior Média</h4>
        <p className="time">{peakHour}:00</p>
        <p className="value">{data.peak_hour_average.toFixed(1)} jogadores (média)</p>
      </div>
      
      <div className="arrow">→</div>
      
      <div className="comparison-card highlight">
        <h4>Pico Absoluto</h4>
        <p className="time">{absolutePeak.formatted}</p>
        <p className="value">{absolutePeak.players_count} jogadores</p>
      </div>
    </div>
  );
}
```

---

## ⚠️ Tratamento de Erros

```javascript
function safeGetAbsolutePeak(data) {
  // Verificar se existe
  if (!data || !data.absolute_peak) {
    return null;
  }
  
  // Validar estrutura
  const peak = data.absolute_peak;
  if (!peak.timestamp || !peak.players_count) {
    console.warn('absolute_peak com estrutura inválida');
    return null;
  }
  
  return peak;
}

// Uso:
const peak = safeGetAbsolutePeak(data);
if (peak) {
  // Usar peak com segurança
  console.log(peak.formatted, peak.players_count);
} else {
  // Exibir mensagem alternativa
  console.log('Pico absoluto não disponível');
}
```

---

## 📋 Checklist de Implementação

- [ ] Verificar se `absolute_peak` existe na resposta
- [ ] Exibir card/destaque com informações do pico
- [ ] Formatar data/hora conforme locale
- [ ] Adicionar tratamento de erro (null)
- [ ] Estilizar card de forma destacada
- [ ] Opcional: Adicionar anotação no gráfico
- [ ] Opcional: Comparar com `peak_hour` / `peak_day`
- [ ] Testar com diferentes períodos (7, 30, 90 dias)
- [ ] Validar responsividade (mobile/desktop)

---

## 🎨 Design Sugerido

### **Layout Recomendado**

```
┌─────────────────────────────────────────────────┐
│  Relatório de Jogadores Online                  │
├─────────────────────────────────────────────────┤
│  ┌──────────────────────────────────────────┐  │
│  │  🎯 Pico Absoluto                         │  │
│  │                                            │  │
│  │  23 de dezembro de 2025, 01:35           │  │
│  │  33 jogadores online                      │  │
│  └──────────────────────────────────────────┘  │
├─────────────────────────────────────────────────┤
│  ┌──────────┐  ┌──────────┐  ┌──────────┐     │
│  │ Média    │  │  Pico    │  │  Baixa   │     │
│  │ 9.05     │  │   33     │  │    0     │     │
│  └──────────┘  └──────────┘  └──────────┘     │
├─────────────────────────────────────────────────┤
│         [Gráfico de Linha]                     │
└─────────────────────────────────────────────────┘
```

### **Cores Sugeridas**

- **Card de Pico:** Gradiente roxo/azul (`#667eea` → `#764ba2`)
- **Texto:** Branco ou preto (contraste adequado)
- **Destaque:** Amarelo (`#ffc107`) ou laranja (`#ff9800`)

---

## 📝 Exemplo de Mensagem para Usuário

```javascript
function getPeakMessage(absolutePeak) {
  if (!absolutePeak) {
    return 'Nenhum pico registrado no período';
  }
  
  const date = new Date(absolutePeak.timestamp);
  const dateStr = date.toLocaleDateString('pt-BR', {
    day: 'numeric',
    month: 'long',
    year: 'numeric'
  });
  const timeStr = date.toLocaleTimeString('pt-BR', {
    hour: '2-digit',
    minute: '2-digit'
  });
  
  return `O maior número de jogadores foi registrado em ${dateStr} às ${timeStr}, com ${absolutePeak.players_count} jogadores online simultaneamente.`;
}

// Uso:
const message = getPeakMessage(data.absolute_peak);
// "O maior número de jogadores foi registrado em 23 de dezembro de 2025 às 01:35, com 33 jogadores online simultaneamente."
```

---

## 🔗 Recursos Adicionais

- **Documentação da API:** `docs/endpoints/REPORTS_PLAYERS_API.md`
- **Documentação Técnica:** `docs/PICO_ABSOLUTO_RELATORIO.md`
- **Coleção Postman:** `docs/endpoints/postman-collection.json`

---

## ❓ Dúvidas Frequentes

### **1. Quando `absolute_peak` é `null`?**
Quando não há dados no período analisado ou ocorreu um erro no cálculo.

### **2. Qual a diferença entre `peak_hour` e `absolute_peak`?**
- `peak_hour`: Hora do dia com maior média (agregado)
- `absolute_peak`: Timestamp exato com mais jogadores (snapshot específico)

### **3. Como formatar a data?**
Use `absolute_peak.formatted` (já formatado) ou `new Date(absolute_peak.timestamp)` para customizar.

### **4. O `absolute_peak` sempre está na `peak_hour`?**
Não necessariamente. O `peak_hour` é a hora com maior média, mas o `absolute_peak` pode ser em qualquer hora do período.

---

**Boa implementação!** 🚀
