# LogVeiculos - Guia para Desenvolvedor Frontend

## Resumo do Endpoint

O endpoint `/api/LogVeiculos` processa logs de eventos de veículos do SCUM (destruição, desaparecimento, inatividade) e mantém um histórico completo com controle de duplicatas.

---

## Endpoints Disponíveis

### 1. Processar Log de Veículos
**GET** `/api/LogVeiculos`

**O que faz:** Lê o log mais recente e retorna apenas eventos novos (não duplicados).

**Resposta de exemplo:**
```json
{
  "success": true,
  "message": "Log de veículos processado com sucesso. 3 novos eventos encontrados.",
  "data": [
    {
      "timestamp": "2025.07.13-04.01.37",
      "event": "Destroyed",
      "vehicleType": "Kinglet_Duster_ES",
      "vehicleId": "1600649",
      "ownerSteamId": "76561198040636105",
      "ownerPlayerId": "1",
      "ownerName": "Pedreiro",
      "location": {
        "x": -311773.969,
        "y": 5480.525,
        "z": 36099.227
      },
      "processedAt": "2025-07-13T05:20:42.658Z"
    }
  ]
}
```

---

### 2. Histórico Completo
**GET** `/api/vehicles/history`

**O que faz:** Retorna todos os eventos já processados.

**Uso no frontend:** Para mostrar tabela/página de histórico completo.

---

### 3. Veículos por Proprietário
**GET** `/api/vehicles/owner/:steamId`

**O que faz:** Filtra eventos por Steam ID do proprietário.

**Exemplo:** `/api/vehicles/owner/76561198140545020`

**Uso no frontend:** Para mostrar perfil de jogador com seus veículos perdidos.

---

### 4. Estatísticas
**GET** `/api/vehicles/stats`

**O que faz:** Retorna estatísticas agregadas.

**Resposta:**
```json
{
  "success": true,
  "data": {
    "totalEvents": 3,
    "eventsByType": {
      "Destroyed": 1,
      "Disappeared": 1,
      "VehicleInactiveTimerReached": 1
    },
    "topOwners": [
      { "steamId": "76561198140545020", "name": "mariocs10", "count": 2 },
      { "steamId": "76561198040636105", "name": "Pedreiro", "count": 1 }
    ],
    "topVehicleTypes": [
      { "type": "Tractor_ES", "count": 2 },
      { "type": "Kinglet_Duster_ES", "count": 1 }
    ]
  }
}
```

**Uso no frontend:** Para dashboard com gráficos e rankings.

---

### 5. Enviar Histórico para Discord
**POST** `/api/vehicles/send-history`

**O que faz:** Envia o histórico completo de veículos para o Discord via webhook com formatação bonita.

**Parâmetros (opcional):**
```json
{
  "limit": 10
}
```

**Resposta de sucesso:**
```json
{
  "success": true,
  "message": "Histórico de 4 veículos enviado para o Discord com sucesso",
  "data": {
    "totalEvents": 4,
    "sentToDiscord": true
  }
}
```

**Uso no frontend:** Botão "Enviar para Discord" na página de histórico.

---

## Tipos de Eventos

- **Destroyed** 💥 - Veículo foi destruído
- **Disappeared** 👻 - Veículo desapareceu
- **VehicleInactiveTimerReached** ⏰ - Timer de inatividade atingido

---

## Estrutura de Dados

### Evento de Veículo
```typescript
interface VehicleEvent {
  timestamp: string;           // "2025.07.13-04.01.37"
  event: string;               // "Destroyed" | "Disappeared" | "VehicleInactiveTimerReached"
  vehicleType: string;         // "Kinglet_Duster_ES"
  vehicleId: string;           // "1600649"
  ownerSteamId: string;        // "76561198040636105"
  ownerPlayerId: string;       // "1"
  ownerName: string;           // "Pedreiro"
  location: {
    x: number;                 // -311773.969
    y: number;                 // 5480.525
    z: number;                 // 36099.227
  };
  processedAt: string;         // "2025-07-13T05:20:42.658Z"
}
```

---

## Exemplos de Implementação

### JavaScript/TypeScript

```javascript
// Processar log de veículos
async function processVehicleLog() {
  try {
    const response = await fetch('http://localhost:3000/api/LogVeiculos');
    const data = await response.json();
    
    if (data.success) {
      console.log(`${data.data.length} novos eventos encontrados`);
      return data.data;
    }
  } catch (error) {
    console.error('Erro ao processar log:', error);
  }
}

// Buscar histórico
async function getVehicleHistory() {
  const response = await fetch('http://localhost:3000/api/vehicles/history');
  const data = await response.json();
  return data.data;
}

// Buscar por proprietário
async function getVehiclesByOwner(steamId) {
  const response = await fetch(`http://localhost:3000/api/vehicles/owner/${steamId}`);
  const data = await response.json();
  return data.data;
}

// Buscar estatísticas
async function getVehicleStats() {
  const response = await fetch('http://localhost:3000/api/vehicles/stats');
  const data = await response.json();
  return data.data;
}

// Enviar histórico para Discord
async function sendVehicleHistoryToDiscord(limit = 10) {
  try {
    const response = await fetch('http://localhost:3000/api/vehicles/send-history', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({ limit })
    });
    const data = await response.json();
    return data;
  } catch (error) {
    console.error('Erro ao enviar para Discord:', error);
    return { success: false, message: 'Erro de conexão' };
  }
}
```

### React/Vue/Angular

```javascript
// Hook React para veículos
function useVehicles() {
  const [vehicles, setVehicles] = useState([]);
  const [loading, setLoading] = useState(false);

  const processLog = async () => {
    setLoading(true);
    try {
      const response = await fetch('/api/LogVeiculos');
      const data = await response.json();
      if (data.success) {
        setVehicles(prev => [...data.data, ...prev]);
      }
    } catch (error) {
      console.error('Erro:', error);
    } finally {
      setLoading(false);
    }
  };

  return { vehicles, loading, processLog };
}
```

---

## Sugestões de Interface

### 1. Dashboard Principal
- Botão "Processar Log" que chama `/api/LogVeiculos`
- Contador de eventos novos
- Lista dos últimos eventos
- Gráficos usando dados de `/api/vehicles/stats`

### 2. Página de Histórico
- Tabela com todos os eventos (`/api/vehicles/history`)
- Filtros por tipo de evento, proprietário, data
- Paginação se necessário

### 3. Perfil de Jogador
- Seção "Veículos Perdidos" usando `/api/vehicles/owner/:steamId`
- Estatísticas pessoais

### 4. Página de Histórico
- Tabela com todos os eventos (`/api/vehicles/history`)
- Botão "Enviar para Discord" que chama `/api/vehicles/send-history`
- Filtros por tipo de evento, proprietário, data

### 5. Componentes Sugeridos
```javascript
// Componente de evento de veículo
function VehicleEventCard({ event }) {
  const getEventIcon = (eventType) => {
    const icons = {
      'Destroyed': '💥',
      'Disappeared': '👻',
      'VehicleInactiveTimerReached': '⏰'
    };
    return icons[eventType] || '❓';
  };

  return (
    <div className="vehicle-event-card">
      <div className="event-icon">{getEventIcon(event.event)}</div>
      <div className="event-details">
        <h4>{event.vehicleType}</h4>
        <p>Proprietário: {event.ownerName}</p>
        <p>Evento: {event.event}</p>
        <p>Horário: {event.timestamp}</p>
      </div>
    </div>
  );
}
```

---

## Configuração de Proxy (Vite)

Se estiver usando Vite, adicione no `vite.config.js`:

```javascript
export default defineConfig({
  server: {
    proxy: {
      '/api': {
        target: 'http://localhost:3000',
        changeOrigin: true
      }
    }
  }
});
```

---

## Observações Importantes

1. **Controle de Duplicatas:** O endpoint só retorna eventos novos. Se chamar várias vezes, só retorna dados na primeira vez.

2. **Frequência de Chamadas:** Pode chamar `/api/LogVeiculos` periodicamente (ex: a cada 5 minutos) sem problemas.

3. **Codificação:** O backend responde em UTF-8, então não há problemas com caracteres especiais.

4. **CORS:** O backend já está configurado com CORS habilitado.

5. **Erro Handling:** Sempre verifique `data.success` antes de usar os dados.

---

## Testes

Para testar no Postman ou similar:

1. **Processar log:** `GET http://localhost:3000/api/LogVeiculos`
2. **Histórico:** `GET http://localhost:3000/api/vehicles/history`
3. **Por proprietário:** `GET http://localhost:3000/api/vehicles/owner/76561198140545020`
4. **Estatísticas:** `GET http://localhost:3000/api/vehicles/stats`
5. **Enviar para Discord:** `POST http://localhost:3000/api/vehicles/send-history`

---

## Próximos Passos

1. Implementar interface básica com os endpoints
2. Adicionar filtros e paginação
3. Implementar gráficos com as estatísticas
4. Adicionar notificações em tempo real (se necessário)
5. Integrar com sistema de players existente

Se precisar de mais detalhes sobre algum endpoint ou tiver dúvidas sobre a implementação, é só perguntar! 