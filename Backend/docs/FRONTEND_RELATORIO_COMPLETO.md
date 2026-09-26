# 📊 Documentação Completa Frontend: Relatórios de Jogadores

## 🎯 Visão Geral

Sistema de relatórios para análise de jogadores online com:
- Gráficos de linha por hora do dia
- Estatísticas de picos e baixas
- **Pico absoluto** (timestamp exato com mais jogadores) ⭐ NOVO

---

## 🔌 Endpoints Disponíveis

### **1. Média por Hora do Dia**
```
GET /api/reports/players/hourly-average?days=7
```

**Retorna:**
- Média de jogadores por hora (0-23)
- Pico e baixa por hora
- **Pico absoluto** (dia + hora exatos) ⭐

### **2. Dados para Gráfico**
```
GET /api/reports/players/chart-data?days=7&granularity=hour
```

**Retorna:**
- Labels e dados formatados para gráficos
- Pronto para Chart.js, Plotly, Recharts

### **3. Média por Dia**
```
GET /api/reports/players/daily-average?days=7&interval_minutes=15
```

**Retorna:**
- Média de jogadores por dia
- Pico e baixa por dia
- **Pico absoluto** (dia + hora exatos) ⭐

---

## 🎯 Pico Absoluto - NOVA FUNCIONALIDADE

### **O que é?**

O campo `absolute_peak` mostra o **timestamp exato** (dia + hora + minuto) que teve o maior número de jogadores online no período.

**Exemplo:** "Dia 23 de dezembro de 2025 às 01:35 teve 33 jogadores online simultaneamente"

### **Estrutura:**

```json
{
  "absolute_peak": {
    "timestamp": "2025-12-23T01:35:10.180745",
    "date": "2025-12-23",
    "hour": 1,
    "minute": 35,
    "players_count": 33,
    "formatted": "2025-12-23 01:35"
  }
}
```

### **Diferença:**

- **`peak_hour`**: Hora do dia com maior média (agregado)
- **`absolute_peak`**: Timestamp exato com mais jogadores (snapshot específico)

---

## ⚡ Implementação Rápida

### **1. Buscar Dados**

```javascript
const response = await fetch(
  '/api/reports/players/hourly-average?days=30',
  {
    headers: {
      'Authorization': `Bearer ${token}`
    }
  }
);

const result = await response.json();
const data = result.data;
```

### **2. Exibir Pico Absoluto**

```jsx
function AbsolutePeakCard({ data }) {
  const peak = data.absolute_peak;
  
  if (!peak) return null;
  
  return (
    <div className="peak-card">
      <h3>🎯 Pico Absoluto</h3>
      <p className="date">{peak.formatted}</p>
      <p className="count">{peak.players_count} jogadores</p>
    </div>
  );
}
```

### **3. Criar Gráfico**

```javascript
import Chart from 'chart.js/auto';

new Chart(ctx, {
  type: 'line',
  data: {
    labels: data.by_hour.map(h => `${h.hour}:00`),
    datasets: [{
      label: 'Jogadores Online',
      data: data.by_hour.map(h => h.average),
      borderColor: 'rgb(75, 192, 192)',
      fill: true
    }]
  }
});
```

---

## 📊 Exemplo de Resposta Completa

```json
{
  "success": true,
  "data": {
    "period": {
      "start": "2025-12-14T13:35:10",
      "end": "2026-01-13T13:35:10",
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
      // ... 24 horas
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

## 🎨 Componente React Completo

```jsx
import React, { useState, useEffect } from 'react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';

function PlayersReport() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [days, setDays] = useState(30);

  useEffect(() => {
    fetchData(days);
  }, [days]);

  const fetchData = async (daysParam) => {
    try {
      setLoading(true);
      const response = await fetch(
        `/api/reports/players/hourly-average?days=${daysParam}`,
        {
          headers: {
            'Authorization': `Bearer ${getAuthToken()}`
          }
        }
      );
      
      const result = await response.json();
      if (result.success) {
        setData(result.data);
      }
    } catch (error) {
      console.error('Erro:', error);
    } finally {
      setLoading(false);
    }
  };

  if (loading) return <div>Carregando...</div>;
  if (!data) return <div>Nenhum dado disponível</div>;

  // Preparar dados para gráfico
  const chartData = data.by_hour.map(h => ({
    hour: `${h.hour}:00`,
    players: h.average,
    max: h.max,
    min: h.min
  }));

  return (
    <div className="players-report">
      <h2>Relatório de Jogadores Online</h2>
      
      {/* Filtro de período */}
      <select value={days} onChange={(e) => setDays(Number(e.target.value))}>
        <option value={7}>Últimos 7 dias</option>
        <option value={30}>Últimos 30 dias</option>
        <option value={90}>Últimos 90 dias</option>
      </select>

      {/* Card de Pico Absoluto */}
      {data.absolute_peak && (
        <div className="absolute-peak-card">
          <h3>🎯 Pico Absoluto</h3>
          <p className="date">{data.absolute_peak.formatted}</p>
          <p className="count">{data.absolute_peak.players_count} jogadores</p>
        </div>
      )}

      {/* Estatísticas */}
      <div className="stats-grid">
        <div className="stat-card">
          <div className="label">Média Geral</div>
          <div className="value">{data.overall_average.toFixed(1)}</div>
        </div>
        <div className="stat-card">
          <div className="label">Hora de Pico</div>
          <div className="value">{data.peak_hour}:00</div>
          <div className="sub-value">média: {data.peak_hour_average.toFixed(1)}</div>
        </div>
        <div className="stat-card">
          <div className="label">Hora de Baixa</div>
          <div className="value">{data.lowest_hour}:00</div>
          <div className="sub-value">média: {data.lowest_hour_average.toFixed(1)}</div>
        </div>
      </div>

      {/* Gráfico */}
      <div className="chart-container">
        <ResponsiveContainer width="100%" height={400}>
          <LineChart data={chartData}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="hour" />
            <YAxis />
            <Tooltip />
            <Line 
              type="monotone" 
              dataKey="players" 
              stroke="#667eea" 
              strokeWidth={2}
              fill="#667eea"
              fillOpacity={0.2}
            />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}

export default PlayersReport;
```

---

## 🎨 CSS Sugerido

```css
.players-report {
  padding: 20px;
  max-width: 1200px;
  margin: 0 auto;
}

.absolute-peak-card {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  padding: 20px;
  border-radius: 12px;
  margin-bottom: 20px;
  box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
}

.absolute-peak-card h3 {
  margin: 0 0 10px 0;
  font-size: 18px;
}

.absolute-peak-card .date {
  font-size: 16px;
  opacity: 0.9;
  margin: 5px 0;
}

.absolute-peak-card .count {
  font-size: 32px;
  font-weight: bold;
  margin: 10px 0 0 0;
}

.stats-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 20px;
  margin: 20px 0;
}

.stat-card {
  background: #f5f5f5;
  padding: 20px;
  border-radius: 8px;
  text-align: center;
}

.stat-card .label {
  font-size: 14px;
  color: #666;
  margin-bottom: 8px;
}

.stat-card .value {
  font-size: 32px;
  font-weight: bold;
  color: #333;
}

.stat-card .sub-value {
  font-size: 12px;
  color: #999;
  margin-top: 4px;
}

.chart-container {
  background: white;
  padding: 20px;
  border-radius: 8px;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
  margin-top: 20px;
}
```

---

## 📋 Checklist de Implementação

### **Básico**
- [ ] Buscar dados do endpoint
- [ ] Exibir gráfico de linha
- [ ] Exibir estatísticas (média, pico, baixa)
- [ ] Filtro de período (7, 30, 90 dias)

### **Pico Absoluto** ⭐ NOVO
- [ ] Verificar se `absolute_peak` existe
- [ ] Exibir card destacado com pico absoluto
- [ ] Formatar data/hora conforme locale
- [ ] Tratamento de erro (null)

### **Opcional**
- [ ] Adicionar anotação no gráfico (marcar pico absoluto)
- [ ] Comparar `peak_hour` com `absolute_peak`
- [ ] Tooltip customizado
- [ ] Exportar dados (CSV/PDF)

---

## 📖 Documentação Detalhada

- **Relatórios Gerais:** `docs/FRONTEND_RELATORIO_JOGADORES.md`
- **Pico Absoluto:** `docs/FRONTEND_PICO_ABSOLUTO.md`
- **Resumo Executivo:** `docs/FRONTEND_RELATORIO_JOGADORES_RESUMO.md`
- **API Completa:** `docs/endpoints/REPORTS_PLAYERS_API.md`

---

## 🔗 Recursos

- **Postman Collection:** `docs/endpoints/postman-collection.json`
- **Exemplos de Código:** Ver documentação detalhada acima

---

**Tudo pronto para implementar!** 🚀
