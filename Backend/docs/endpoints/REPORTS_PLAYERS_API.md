# 📊 API de Relatórios de Jogadores

Endpoints para análise de média de jogadores online com gráficos.

---

## 📋 Endpoints Disponíveis

### 1. **Média por Hora do Dia**

```
GET /api/reports/players/hourly-average
```

**Descrição:** Retorna a média de jogadores online por hora do dia (0-23) no período especificado.

**Parâmetros Query:**
- `days` (opcional, padrão: 7): Número de dias para analisar (1-365)

**Exemplo de Requisição:**
```
GET /api/reports/players/hourly-average?days=7
```

**Resposta de Sucesso (200 OK):**
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

**Campos da Resposta:**
- `by_hour`: Array com 24 objetos (uma para cada hora)
  - `hour`: Hora do dia (0-23)
  - `average`: Média de jogadores nesta hora
  - `min`: Mínimo de jogadores nesta hora
  - `max`: Máximo de jogadores nesta hora
  - `samples`: Número de amostras (dias analisados)
- `overall_average`: Média geral de jogadores no período
- `peak_hour`: Hora com maior média
- `peak_hour_average`: Média na hora de pico
- `lowest_hour`: Hora com menor média
- `lowest_hour_average`: Média na hora de baixa

---

### 2. **Dados para Gráfico**

```
GET /api/reports/players/chart-data
```

**Descrição:** Retorna dados formatados prontos para uso em gráficos (Chart.js, Plotly, etc.).

**Parâmetros Query:**
- `days` (opcional, padrão: 7): Número de dias para analisar (1-365)
- `granularity` (opcional, padrão: "hour"): Tipo de granularidade
  - `"hour"`: Média por hora do dia (0-23)
  - `"day"`: Média por dia no período

**Exemplo de Requisição:**
```
GET /api/reports/players/chart-data?days=7&granularity=hour
```

**Resposta de Sucesso (200 OK) - Granularidade "hour":**
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

**Resposta de Sucesso (200 OK) - Granularidade "day":**
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

**Campos da Resposta:**
- `labels`: Array de strings com os rótulos do eixo X
- `datasets`: Array com um objeto de dataset
  - `label`: Nome do dataset
  - `data`: Array de valores numéricos (média de jogadores)
  - `average`: Média geral
  - `peak`: Valor máximo
  - `lowest`: Valor mínimo

---

### 3. **Média por Dia**

```
GET /api/reports/players/daily-average
```

**Descrição:** Retorna a média de jogadores por dia no período especificado.

**Parâmetros Query:**
- `days` (opcional, padrão: 7): Número de dias para analisar (1-365)
- `interval_minutes` (opcional, padrão: 15): Intervalo entre snapshots em minutos (5-60)

**Exemplo de Requisição:**
```
GET /api/reports/players/daily-average?days=7&interval_minutes=15
```

**Resposta de Sucesso (200 OK):**
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
      },
      {
        "date": "2025-01-07",
        "average": 15.2,
        "min": 4,
        "max": 30,
        "peak": 30,
        "lowest": 4,
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

**Campos da Resposta:**
- `by_day`: Array com um objeto para cada dia
  - `date`: Data no formato ISO (YYYY-MM-DD)
  - `average`: Média de jogadores no dia
  - `min`: Mínimo de jogadores no dia
  - `max`: Máximo de jogadores no dia
  - `peak`: Pico de jogadores no dia
  - `lowest`: Menor número de jogadores no dia
  - `samples`: Número de snapshots coletados no dia
- `overall_average`: Média geral de jogadores no período
- `peak_day`: Data com maior pico
- `peak_day_count`: Número de jogadores no pico
- `lowest_day`: Data com menor número
- `lowest_day_count`: Menor número de jogadores

---

## ❌ Respostas de Erro

Todos os endpoints retornam erros no seguinte formato:

```json
{
  "success": false,
  "error": "Mensagem de erro descritiva"
}
```

**Códigos de Status HTTP:**
- `200 OK`: Sucesso
- `500 Internal Server Error`: Erro no servidor

---

## 📊 Exemplo de Uso com Chart.js

```javascript
// Buscar dados
fetch('/api/reports/players/chart-data?days=7&granularity=hour')
  .then(response => response.json())
  .then(data => {
    if (data.success) {
      const chartData = data.data;
      
      // Criar gráfico
      const ctx = document.getElementById('playersChart').getContext('2d');
      new Chart(ctx, {
        type: 'line',
        data: {
          labels: chartData.labels,
          datasets: [{
            label: chartData.datasets[0].label,
            data: chartData.datasets[0].data,
            borderColor: 'rgb(75, 192, 192)',
            backgroundColor: 'rgba(75, 192, 192, 0.2)',
            tension: 0.1
          }]
        },
        options: {
          responsive: true,
          scales: {
            y: {
              beginAtZero: true,
              title: {
                display: true,
                text: 'Jogadores Online'
              }
            },
            x: {
              title: {
                display: true,
                text: 'Hora do Dia'
              }
            }
          },
          plugins: {
            legend: {
              display: true
            },
            tooltip: {
              callbacks: {
                label: function(context) {
                  return `Média: ${context.parsed.y.toFixed(1)} jogadores`;
                }
              }
            }
          }
        }
      });
    }
  });
```

---

## 📊 Exemplo de Uso com Plotly

```javascript
// Buscar dados
fetch('/api/reports/players/chart-data?days=7&granularity=hour')
  .then(response => response.json())
  .then(data => {
    if (data.success) {
      const chartData = data.data;
      
      const trace = {
        x: chartData.labels,
        y: chartData.datasets[0].data,
        type: 'scatter',
        mode: 'lines+markers',
        name: chartData.datasets[0].label,
        line: { color: 'rgb(75, 192, 192)' },
        fill: 'tonexty',
        fillcolor: 'rgba(75, 192, 192, 0.2)'
      };
      
      const layout = {
        title: 'Média de Jogadores Online por Hora',
        xaxis: { title: 'Hora do Dia' },
        yaxis: { title: 'Jogadores Online' },
        hovermode: 'closest'
      };
      
      Plotly.newPlot('playersChart', [trace], layout);
    }
  });
```

---

## 🔍 Notas Importantes

1. **Performance:** 
   - Consultas podem levar alguns segundos com muitos dados
   - Recomenda-se usar cache no frontend para períodos longos

2. **Dados Históricos:**
   - Os dados são calculados a partir da tabela `player_logins`
   - Dados retroativos desde o início do sistema
   - Precisão: 90-95%

3. **Limites:**
   - `days`: Máximo 365 dias
   - `interval_minutes`: Entre 5 e 60 minutos

4. **Formato de Datas:**
   - Todas as datas são retornadas em formato ISO 8601
   - Timezone: UTC

---

## 🚀 Próximos Passos para Frontend

1. Criar componente de gráfico (Chart.js, Plotly, ou similar)
2. Adicionar filtros de período (7 dias, 30 dias, 90 dias)
3. Adicionar toggle entre granularidade "hour" e "day"
4. Exibir métricas principais (média, pico, baixa)
5. Adicionar loading states durante requisições

---

**Documentação criada em:** 2025-01-13  
**Versão da API:** 1.0
