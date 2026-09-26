# 📊 Resumo Executivo: Relatório de Jogadores Online

## 🎯 Objetivo Rápido

Criar gráfico de linha mostrando média de jogadores online por hora do dia (0-23) com identificação de picos e baixas.

---

## 🔌 Endpoint Principal (Recomendado)

```
GET /api/reports/players/chart-data?days=7&granularity=hour
```

**Headers:**
```
Authorization: Bearer {token}
```

**Resposta:**
```json
{
  "success": true,
  "data": {
    "labels": ["00:00", "01:00", ..., "23:00"],
    "datasets": [{
      "label": "Jogadores Online",
      "data": [8.2, 7.5, ..., 19.2],
      "average": 15.2,
      "peak": 26.2,
      "lowest": 4.1
    }]
  }
}
```

---

## ⚡ Implementação Rápida (Chart.js)

```javascript
// 1. Buscar dados
const response = await fetch('/api/reports/players/chart-data?days=7&granularity=hour', {
  headers: { 'Authorization': `Bearer ${token}` }
});
const { data } = await response.json();

// 2. Criar gráfico
new Chart(ctx, {
  type: 'line',
  data: {
    labels: data.labels,
    datasets: [{
      label: data.datasets[0].label,
      data: data.datasets[0].data,
      borderColor: 'rgb(75, 192, 192)',
      backgroundColor: 'rgba(75, 192, 192, 0.2)',
      fill: true
    }]
  },
  options: {
    responsive: true,
    scales: {
      y: { beginAtZero: true, title: { text: 'Jogadores Online' } },
      x: { title: { text: 'Hora do Dia' } }
    }
  }
});
```

---

## 🎯 Pico Absoluto (NOVO!)

**Campo `absolute_peak`** nos endpoints mostra o timestamp exato (dia + hora + minuto) com mais jogadores:

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

**Exemplo de uso:**
```javascript
if (data.absolute_peak) {
  console.log(`${data.absolute_peak.formatted} - ${data.absolute_peak.players_count} jogadores`);
}
```

---

## 📋 Checklist Mínimo

- [ ] Endpoint: `/api/reports/players/chart-data?days=7&granularity=hour`
- [ ] Headers: `Authorization: Bearer {token}`
- [ ] Gráfico de linha com 24 pontos (0-23 horas)
- [ ] Exibir: Média, Pico, Baixa
- [ ] Exibir: Pico Absoluto (dia + hora exatos) ⭐ NOVO
- [ ] Filtro de período (7, 30, 90 dias)

---

## 📖 Documentação Completa

- **Relatórios:** `docs/FRONTEND_RELATORIO_JOGADORES.md`
- **Pico Absoluto:** `docs/FRONTEND_PICO_ABSOLUTO.md` ⭐ NOVO

---

**Pronto para implementar!** 🚀
