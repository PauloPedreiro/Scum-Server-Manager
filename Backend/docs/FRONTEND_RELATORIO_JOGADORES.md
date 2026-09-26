# 📊 Documentação Frontend: Relatório de Média de Jogadores Online

## 🎯 Objetivo

Implementar um relatório visual que mostre:
- **Média de jogadores online a cada 24 horas**
- **Gráficos de linha** identificando horários de pico e baixa
- **Estatísticas** como média geral, pico máximo e menor número de jogadores

---

## 📡 Endpoints Disponíveis

### Base URL
```
http://localhost:3000/api/reports/players
```
*(Ajustar conforme ambiente de produção)*

### Autenticação
Todos os endpoints requerem autenticação JWT:
```
Authorization: Bearer {token}
```

---

## 🔌 Endpoints Detalhados

### 1. **Média por Hora do Dia**

**Endpoint:** `GET /api/reports/players/hourly-average`

**Descrição:** Retorna a média de jogadores online por hora do dia (0-23) no período especificado.

**Parâmetros:**
- `days` (query, opcional): Número de dias para analisar (1-365, padrão: 7)

**Exemplo de Requisição:**
```javascript
fetch('/api/reports/players/hourly-average?days=7', {
  headers: {
    'Authorization': `Bearer ${token}`
  }
})
```

**Resposta de Sucesso (200):**
```json
{
  "success": true,
  "data": {
    "period": {
      "start": "2025-01-06T10:00:00",
      "end": "2025-01-13T10:00:00",
      "days": 7
    },
    "by_hour": [
      {
        "hour": 0,
        "average": 8.2,
        "min": 3,
        "max": 15,
        "samples": 7
      },
      {
        "hour": 1,
        "average": 7.5,
        "min": 2,
        "max": 14,
        "samples": 7
      },
      // ... 24 horas (0-23)
      {
        "hour": 20,
        "average": 26.2,
        "min": 20,
        "max": 35,
        "samples": 7
      }
    ],
    "overall_average": 15.2,
    "peak_hour": 20,
    "peak_hour_average": 26.2,
    "lowest_hour": 4,
    "lowest_hour_average": 4.1
  }
}
```

**Estrutura dos Dados:**
- `by_hour`: Array com 24 objetos (uma para cada hora)
  - `hour`: Hora do dia (0-23)
  - `average`: Média de jogadores nesta hora
  - `min`: Mínimo de jogadores nesta hora
  - `max`: Máximo de jogadores nesta hora
  - `samples`: Número de amostras (dias analisados)
- `overall_average`: Média geral de jogadores no período
- `peak_hour`: Hora com maior média (0-23)
- `peak_hour_average`: Média na hora de pico
- `lowest_hour`: Hora com menor média (0-23)
- `lowest_hour_average`: Média na hora de baixa

---

### 2. **Dados para Gráfico (Recomendado)**

**Endpoint:** `GET /api/reports/players/chart-data`

**Descrição:** Retorna dados formatados prontos para uso em gráficos.

**Parâmetros:**
- `days` (query, opcional): Número de dias para analisar (1-365, padrão: 7)
- `granularity` (query, opcional): Tipo de granularidade
  - `"hour"`: Média por hora do dia (0-23) - **Recomendado para gráfico de 24h**
  - `"day"`: Média por dia no período

**Exemplo de Requisição:**
```javascript
fetch('/api/reports/players/chart-data?days=7&granularity=hour', {
  headers: {
    'Authorization': `Bearer ${token}`
  }
})
```

**Resposta de Sucesso (200) - Granularidade "hour":**
```json
{
  "success": true,
  "data": {
    "period": {
      "start": "2025-01-06T10:00:00",
      "end": "2025-01-13T10:00:00",
      "days": 7
    },
    "granularity": "hour",
    "labels": [
      "00:00",
      "01:00",
      "02:00",
      // ... 24 horas
      "23:00"
    ],
    "datasets": [
      {
        "label": "Jogadores Online",
        "data": [8.2, 7.5, 6.8, 5.2, 4.1, 4.5, 5.8, 7.2, 9.5, 12.3, 15.1, 17.8, 19.5, 20.2, 21.1, 22.3, 23.5, 24.2, 25.1, 25.8, 26.2, 25.5, 23.8, 19.2],
        "average": 15.2,
        "peak": 26.2,
        "lowest": 4.1
      }
    ]
  }
}
```

**Resposta de Sucesso (200) - Granularidade "day":**
```json
{
  "success": true,
  "data": {
    "period": {
      "start": "2025-01-06T10:00:00",
      "end": "2025-01-13T10:00:00",
      "days": 7
    },
    "granularity": "day",
    "labels": [
      "2025-01-06",
      "2025-01-07",
      "2025-01-08",
      // ... dias do período
      "2025-01-13"
    ],
    "datasets": [
      {
        "label": "Jogadores Online",
        "data": [14.5, 15.2, 16.1, 15.8, 14.9, 15.5, 16.2],
        "average": 15.46,
        "peak": 16.2,
        "lowest": 14.5
      }
    ]
  }
}
```

**Estrutura dos Dados:**
- `labels`: Array de strings com os rótulos do eixo X
- `datasets`: Array com um objeto de dataset
  - `label`: Nome do dataset
  - `data`: Array de valores numéricos (média de jogadores)
  - `average`: Média geral
  - `peak`: Valor máximo
  - `lowest`: Valor mínimo

---

### 3. **Média por Dia**

**Endpoint:** `GET /api/reports/players/daily-average`

**Descrição:** Retorna a média de jogadores por dia no período especificado.

**Parâmetros:**
- `days` (query, opcional): Número de dias para analisar (1-365, padrão: 7)
- `interval_minutes` (query, opcional): Intervalo entre snapshots em minutos (5-60, padrão: 15)

**Exemplo de Requisição:**
```javascript
fetch('/api/reports/players/daily-average?days=7&interval_minutes=15', {
  headers: {
    'Authorization': `Bearer ${token}`
  }
})
```

**Resposta de Sucesso (200):**
```json
{
  "success": true,
  "data": {
    "period": {
      "start": "2025-01-06T10:00:00",
      "end": "2025-01-13T10:00:00",
      "days": 7
    },
    "interval_minutes": 15,
    "by_day": [
      {
        "date": "2025-01-06",
        "average": 14.5,
        "min": 3,
        "max": 28,
        "peak": 28,
        "lowest": 3,
        "samples": 96
      }
      // ... dias do período
    ],
    "overall_average": 15.2,
    "peak_day": "2025-01-10",
    "peak_day_count": 32,
    "lowest_day": "2025-01-06",
    "lowest_day_count": 3
  }
}
```

---

## ❌ Tratamento de Erros

**Resposta de Erro (500):**
```json
{
  "success": false,
  "error": "Mensagem de erro descritiva"
}
```

**Exemplo de Tratamento:**
```javascript
try {
  const response = await fetch('/api/reports/players/chart-data?days=7', {
    headers: {
      'Authorization': `Bearer ${token}`
    }
  });
  
  const result = await response.json();
  
  if (!result.success) {
    console.error('Erro:', result.error);
    // Mostrar mensagem de erro ao usuário
    return;
  }
  
  // Usar result.data para criar gráfico
} catch (error) {
  console.error('Erro na requisição:', error);
  // Mostrar mensagem de erro ao usuário
}
```

---

## 📊 Implementação com Chart.js

### Instalação
```bash
npm install chart.js
```

### Exemplo Completo

```javascript
import Chart from 'chart.js/auto';

// Função para buscar dados e criar gráfico
async function createPlayersChart(days = 7) {
  try {
    // Buscar dados
    const response = await fetch(
      `/api/reports/players/chart-data?days=${days}&granularity=hour`,
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
    
    const chartData = result.data;
    
    // Destruir gráfico anterior se existir
    const existingChart = Chart.getChart('playersChart');
    if (existingChart) {
      existingChart.destroy();
    }
    
    // Criar novo gráfico
    const ctx = document.getElementById('playersChart').getContext('2d');
    new Chart(ctx, {
      type: 'line',
      data: {
        labels: chartData.labels,
        datasets: [
          {
            label: chartData.datasets[0].label,
            data: chartData.datasets[0].data,
            borderColor: 'rgb(75, 192, 192)',
            backgroundColor: 'rgba(75, 192, 192, 0.2)',
            tension: 0.1,
            fill: true
          }
        ]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          title: {
            display: true,
            text: `Média de Jogadores Online - Últimos ${days} dias`
          },
          legend: {
            display: true,
            position: 'top'
          },
          tooltip: {
            callbacks: {
              label: function(context) {
                return `Média: ${context.parsed.y.toFixed(1)} jogadores`;
              }
            }
          }
        },
        scales: {
          y: {
            beginAtZero: true,
            title: {
              display: true,
              text: 'Jogadores Online'
            },
            ticks: {
              stepSize: 1
            }
          },
          x: {
            title: {
              display: true,
              text: 'Hora do Dia'
            }
          }
        }
      }
    });
    
    // Exibir estatísticas
    displayStats(chartData.datasets[0]);
    
  } catch (error) {
    console.error('Erro ao criar gráfico:', error);
    // Mostrar mensagem de erro ao usuário
  }
}

// Função para exibir estatísticas
function displayStats(dataset) {
  const statsElement = document.getElementById('stats');
  statsElement.innerHTML = `
    <div class="stats-card">
      <h3>Estatísticas</h3>
      <p><strong>Média Geral:</strong> ${dataset.average.toFixed(1)} jogadores</p>
      <p><strong>Pico:</strong> ${dataset.peak} jogadores</p>
      <p><strong>Baixa:</strong> ${dataset.lowest} jogadores</p>
    </div>
  `;
}

// Chamar ao carregar a página
createPlayersChart(7);
```

### HTML de Exemplo

```html
<div class="chart-container">
  <canvas id="playersChart"></canvas>
</div>
<div id="stats"></div>

<style>
  .chart-container {
    position: relative;
    height: 400px;
    width: 100%;
  }
  
  .stats-card {
    margin-top: 20px;
    padding: 15px;
    background: #f5f5f5;
    border-radius: 8px;
  }
</style>
```

---

## 📊 Implementação com Plotly.js

### Instalação
```bash
npm install plotly.js-dist-min
```

### Exemplo Completo

```javascript
import Plotly from 'plotly.js-dist-min';

async function createPlayersChartPlotly(days = 7) {
  try {
    const response = await fetch(
      `/api/reports/players/chart-data?days=${days}&granularity=hour`,
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
    
    const chartData = result.data;
    
    const trace = {
      x: chartData.labels,
      y: chartData.datasets[0].data,
      type: 'scatter',
      mode: 'lines+markers',
      name: chartData.datasets[0].label,
      line: {
        color: 'rgb(75, 192, 192)',
        width: 2
      },
      fill: 'tonexty',
      fillcolor: 'rgba(75, 192, 192, 0.2)',
      marker: {
        size: 4
      }
    };
    
    const layout = {
      title: {
        text: `Média de Jogadores Online - Últimos ${days} dias`,
        font: { size: 18 }
      },
      xaxis: {
        title: 'Hora do Dia',
        showgrid: true
      },
      yaxis: {
        title: 'Jogadores Online',
        showgrid: true
      },
      hovermode: 'closest',
      showlegend: true,
      height: 400
    };
    
    Plotly.newPlot('playersChart', [trace], layout, {
      responsive: true
    });
    
    // Exibir estatísticas
    displayStats(chartData.datasets[0]);
    
  } catch (error) {
    console.error('Erro ao criar gráfico:', error);
  }
}

createPlayersChartPlotly(7);
```

---

## 📊 Implementação com Recharts (React)

### Instalação
```bash
npm install recharts
```

### Exemplo Completo (React Component)

```jsx
import React, { useState, useEffect } from 'react';
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  Area,
  AreaChart
} from 'recharts';

function PlayersReportChart() {
  const [chartData, setChartData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [days, setDays] = useState(7);

  useEffect(() => {
    fetchChartData(days);
  }, [days]);

  const fetchChartData = async (daysParam) => {
    try {
      setLoading(true);
      setError(null);

      const response = await fetch(
        `/api/reports/players/chart-data?days=${daysParam}&granularity=hour`,
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

      // Transformar dados para formato Recharts
      const formattedData = result.data.labels.map((label, index) => ({
        hour: label,
        players: result.data.datasets[0].data[index]
      }));

      setChartData({
        data: formattedData,
        stats: result.data.datasets[0]
      });
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

  if (!chartData) {
    return <div>Nenhum dado disponível</div>;
  }

  return (
    <div className="players-report">
      <div className="report-header">
        <h2>Relatório de Jogadores Online</h2>
        <select
          value={days}
          onChange={(e) => setDays(Number(e.target.value))}
        >
          <option value={7}>Últimos 7 dias</option>
          <option value={30}>Últimos 30 dias</option>
          <option value={90}>Últimos 90 dias</option>
        </select>
      </div>

      {/* Estatísticas */}
      <div className="stats-grid">
        <div className="stat-card">
          <div className="stat-label">Média Geral</div>
          <div className="stat-value">
            {chartData.stats.average.toFixed(1)}
          </div>
          <div className="stat-unit">jogadores</div>
        </div>
        <div className="stat-card">
          <div className="stat-label">Pico</div>
          <div className="stat-value">{chartData.stats.peak}</div>
          <div className="stat-unit">jogadores</div>
        </div>
        <div className="stat-card">
          <div className="stat-label">Baixa</div>
          <div className="stat-value">{chartData.stats.lowest}</div>
          <div className="stat-unit">jogadores</div>
        </div>
      </div>

      {/* Gráfico */}
      <div className="chart-wrapper">
        <ResponsiveContainer width="100%" height={400}>
          <AreaChart data={chartData.data}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis
              dataKey="hour"
              label={{ value: 'Hora do Dia', position: 'insideBottom', offset: -5 }}
            />
            <YAxis
              label={{ value: 'Jogadores Online', angle: -90, position: 'insideLeft' }}
            />
            <Tooltip
              formatter={(value) => [`${value.toFixed(1)} jogadores`, 'Média']}
            />
            <Legend />
            <Area
              type="monotone"
              dataKey="players"
              stroke="rgb(75, 192, 192)"
              fill="rgba(75, 192, 192, 0.2)"
              name="Jogadores Online"
            />
          </AreaChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}

export default PlayersReportChart;
```

### CSS de Exemplo

```css
.players-report {
  padding: 20px;
}

.report-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.report-header h2 {
  margin: 0;
}

.stats-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 20px;
  margin-bottom: 30px;
}

.stat-card {
  background: #f5f5f5;
  padding: 20px;
  border-radius: 8px;
  text-align: center;
}

.stat-label {
  font-size: 14px;
  color: #666;
  margin-bottom: 8px;
}

.stat-value {
  font-size: 32px;
  font-weight: bold;
  color: #333;
}

.stat-unit {
  font-size: 12px;
  color: #999;
  margin-top: 4px;
}

.chart-wrapper {
  background: white;
  padding: 20px;
  border-radius: 8px;
  box-shadow: 0 2px 4px rgba(0,0,0,0.1);
}
```

---

## 🎨 Design Sugerido

### Layout Recomendado

```
┌─────────────────────────────────────────────────┐
│  Relatório de Jogadores Online                  │
│  [Últimos 7 dias ▼] [Últimos 30 dias] [90 dias]│
├─────────────────────────────────────────────────┤
│  ┌──────────┐  ┌──────────┐  ┌──────────┐     │
│  │ Média    │  │  Pico    │  │  Baixa   │     │
│  │ 15.2     │  │   26     │  │    4     │     │
│  │jogadores │  │jogadores │  │jogadores │     │
│  └──────────┘  └──────────┘  └──────────┘     │
├─────────────────────────────────────────────────┤
│                                                 │
│         [Gráfico de Linha]                     │
│                                                 │
│     30 ┤                                       │
│     25 ┤              ╭─╮                      │
│     20 ┤         ╭───╯ ╰───╮                  │
│     15 ┤    ╭────╯          ╰────╮            │
│     10 ┤ ╭──╯                     ╰──╮        │
│      5 ┤╯                            ╰─╮      │
│      0 └─────────────────────────────────────  │
│       00:00  06:00  12:00  18:00  24:00       │
│                                                 │
└─────────────────────────────────────────────────┘
```

### Cores Sugeridas

- **Linha principal:** `rgb(75, 192, 192)` ou `#4BC0C0`
- **Área preenchida:** `rgba(75, 192, 192, 0.2)`
- **Pico destacado:** `rgb(255, 99, 132)` ou `#FF6384`
- **Baixa destacada:** `rgb(54, 162, 235)` ou `#36A2EB`

---

## 🔄 Funcionalidades Recomendadas

### 1. **Filtros de Período**

```javascript
const periodOptions = [
  { label: 'Últimos 7 dias', value: 7 },
  { label: 'Últimos 30 dias', value: 30 },
  { label: 'Últimos 90 dias', value: 90 },
  { label: 'Últimos 180 dias', value: 180 },
  { label: 'Último ano', value: 365 }
];
```

### 2. **Toggle de Granularidade**

```javascript
const [granularity, setGranularity] = useState('hour'); // 'hour' ou 'day'

// Botões de toggle
<button 
  onClick={() => setGranularity('hour')}
  className={granularity === 'hour' ? 'active' : ''}
>
  Por Hora
</button>
<button 
  onClick={() => setGranularity('day')}
  className={granularity === 'day' ? 'active' : ''}
>
  Por Dia
</button>
```

### 3. **Loading States**

```javascript
{loading && (
  <div className="loading">
    <div className="spinner"></div>
    <p>Carregando dados...</p>
  </div>
)}
```

### 4. **Marcadores de Pico e Baixa**

```javascript
// Adicionar linhas de referência no gráfico
const annotations = [
  {
    type: 'line',
    yMin: chartData.stats.peak,
    yMax: chartData.stats.peak,
    borderColor: 'rgb(255, 99, 132)',
    borderDash: [5, 5],
    label: {
      content: `Pico: ${chartData.stats.peak}`,
      enabled: true
    }
  },
  {
    type: 'line',
    yMin: chartData.stats.lowest,
    yMax: chartData.stats.lowest,
    borderColor: 'rgb(54, 162, 235)',
    borderDash: [5, 5],
    label: {
      content: `Baixa: ${chartData.stats.lowest}`,
      enabled: true
    }
  }
];
```

---

## 📱 Responsividade

### Breakpoints Sugeridos

```css
/* Mobile */
@media (max-width: 768px) {
  .chart-container {
    height: 300px;
  }
  
  .stats-grid {
    grid-template-columns: 1fr;
  }
}

/* Tablet */
@media (min-width: 769px) and (max-width: 1024px) {
  .chart-container {
    height: 350px;
  }
  
  .stats-grid {
    grid-template-columns: repeat(3, 1fr);
  }
}

/* Desktop */
@media (min-width: 1025px) {
  .chart-container {
    height: 400px;
  }
}
```

---

## ⚡ Performance e Otimizações

### 1. **Cache de Dados**

```javascript
// Cache simples em memória
const cache = new Map();

async function fetchChartDataCached(days) {
  const cacheKey = `players-chart-${days}`;
  
  // Verificar cache (válido por 5 minutos)
  if (cache.has(cacheKey)) {
    const cached = cache.get(cacheKey);
    if (Date.now() - cached.timestamp < 5 * 60 * 1000) {
      return cached.data;
    }
  }
  
  // Buscar dados
  const data = await fetchChartData(days);
  
  // Salvar no cache
  cache.set(cacheKey, {
    data,
    timestamp: Date.now()
  });
  
  return data;
}
```

### 2. **Debounce em Filtros**

```javascript
import { debounce } from 'lodash';

const debouncedFetch = debounce((days) => {
  fetchChartData(days);
}, 300);

// Usar em onChange
<input 
  type="number" 
  onChange={(e) => debouncedFetch(e.target.value)}
/>
```

### 3. **Lazy Loading**

```javascript
// Carregar gráfico apenas quando componente estiver visível
import { useInView } from 'react-intersection-observer';

function PlayersChart() {
  const { ref, inView } = useInView({
    triggerOnce: true,
    threshold: 0.1
  });
  
  useEffect(() => {
    if (inView) {
      fetchChartData(days);
    }
  }, [inView, days]);
  
  return <div ref={ref}>{/* gráfico */}</div>;
}
```

---

## 🧪 Testes de Integração

### Exemplo de Teste (Jest + React Testing Library)

```javascript
import { render, screen, waitFor } from '@testing-library/react';
import PlayersReportChart from './PlayersReportChart';

// Mock da API
global.fetch = jest.fn(() =>
  Promise.resolve({
    json: () => Promise.resolve({
      success: true,
      data: {
        labels: ['00:00', '01:00'],
        datasets: [{
          label: 'Jogadores Online',
          data: [8.2, 7.5],
          average: 7.85,
          peak: 8.2,
          lowest: 7.5
        }]
      }
    })
  })
);

test('renderiza gráfico com dados da API', async () => {
  render(<PlayersReportChart />);
  
  await waitFor(() => {
    expect(screen.getByText('Média Geral')).toBeInTheDocument();
    expect(screen.getByText('7.9')).toBeInTheDocument();
  });
});
```

---

## 📋 Checklist de Implementação

- [ ] Instalar biblioteca de gráficos (Chart.js, Plotly, Recharts, etc.)
- [ ] Criar componente de gráfico
- [ ] Implementar busca de dados da API
- [ ] Adicionar tratamento de erros
- [ ] Adicionar loading states
- [ ] Implementar filtros de período (7, 30, 90 dias)
- [ ] Adicionar toggle de granularidade (hora/dia)
- [ ] Exibir estatísticas (média, pico, baixa)
- [ ] Adicionar marcadores de pico e baixa no gráfico
- [ ] Implementar responsividade
- [ ] Adicionar cache de dados (opcional)
- [ ] Testar com diferentes períodos
- [ ] Validar tratamento de erros
- [ ] Otimizar performance

---

## 🎯 Exemplo de Fluxo Completo

```javascript
// 1. Usuário seleciona período
const [days, setDays] = useState(7);

// 2. Buscar dados
const [data, setData] = useState(null);
const [loading, setLoading] = useState(false);

const fetchData = async () => {
  setLoading(true);
  try {
    const response = await fetch(
      `/api/reports/players/chart-data?days=${days}&granularity=hour`,
      {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      }
    );
    
    const result = await response.json();
    
    if (result.success) {
      setData(result.data);
    } else {
      // Tratar erro
      showError(result.error);
    }
  } catch (error) {
    // Tratar erro de rede
    showError('Erro ao conectar com o servidor');
  } finally {
    setLoading(false);
  }
};

// 3. Renderizar gráfico quando dados estiverem prontos
useEffect(() => {
  fetchData();
}, [days]);

// 4. Componente de gráfico
{loading ? (
  <LoadingSpinner />
) : data ? (
  <ChartComponent data={data} />
) : (
  <ErrorMessage />
)}
```

---

## 🔗 Recursos Adicionais

### Documentação das Bibliotecas

- **Chart.js:** https://www.chartjs.org/docs/latest/
- **Plotly.js:** https://plotly.com/javascript/
- **Recharts:** https://recharts.org/

### Exemplos de Código

Todos os exemplos acima são funcionais e podem ser adaptados conforme necessário.

---

## ❓ Dúvidas Frequentes

### 1. **Qual biblioteca usar?**
- **Chart.js:** Simples, leve, boa para gráficos básicos
- **Plotly.js:** Mais recursos, gráficos interativos avançados
- **Recharts:** Ideal para React, componentes declarativos

### 2. **Como lidar com dados vazios?**
```javascript
if (!data || data.datasets[0].data.length === 0) {
  return <EmptyState message="Nenhum dado disponível para o período selecionado" />;
}
```

### 3. **Como formatar datas?**
```javascript
// Para granularity="day"
const formattedDate = new Date(dateString).toLocaleDateString('pt-BR');
```

### 4. **Como destacar horário de pico?**
```javascript
// Adicionar ponto especial no gráfico
const peakIndex = data.datasets[0].data.indexOf(data.datasets[0].peak);
// Destacar este ponto com cor diferente ou tamanho maior
```

---

## 📞 Suporte

Para dúvidas ou problemas na implementação, consulte:
- Documentação da API: `docs/endpoints/REPORTS_PLAYERS_API.md`
- Coleção Postman: `docs/endpoints/postman-collection.json`

---

**Boa implementação!** 🚀
