# API do Scheduler Backend

## Visão Geral

O sistema de scheduler backend permite executar automaticamente uma sequência de endpoints a cada 30 segundos, como alternativa ao frontend. O sistema implementa uma abordagem híbrida onde o backend pode executar independentemente, mas o frontend ainda pode executar quando necessário.

## Endpoints Disponíveis

### 1. GET /api/scheduler/status

**Descrição:** Obtém o status atual do scheduler

**Resposta de Sucesso:**
```json
{
  "success": true,
  "message": "Status do scheduler recuperado com sucesso",
  "data": {
    "isRunning": true,
    "enabled": true,
    "interval": 30000,
    "lastExecution": 1703123456789,
    "executionSource": "backend",
    "timeSinceLastExecution": 15000,
    "stats": {
      "totalExecutions": 10,
      "successfulExecutions": 9,
      "failedExecutions": 1,
      "lastError": "2025-01-20T10:30:00.000Z",
      "lastSuccess": "2025-01-20T10:35:00.000Z"
    },
    "endpoints": [
      "/api/adminlog",
      "/api/chat_in_game",
      "/api/LogVeiculos",
      "/api/famepoints",
      "/api/bunkers/status",
      "/api/players/painelplayers"
    ],
    "nextExecution": 1703123486789
  }
}
```

### 2. POST /api/scheduler/start

**Descrição:** Inicia o scheduler backend

**Resposta de Sucesso:**
```json
{
  "success": true,
  "message": "Scheduler iniciado com sucesso",
  "data": {
    "isRunning": true,
    "enabled": true,
    "interval": 30000,
    "lastExecution": null,
    "executionSource": null,
    "timeSinceLastExecution": null,
    "stats": {
      "totalExecutions": 0,
      "successfulExecutions": 0,
      "failedExecutions": 0,
      "lastError": null,
      "lastSuccess": null
    },
    "endpoints": [
      "/api/adminlog",
      "/api/chat_in_game",
      "/api/LogVeiculos",
      "/api/famepoints",
      "/api/bunkers/status",
      "/api/players/painelplayers"
    ],
    "nextExecution": null
  }
}
```

### 3. POST /api/scheduler/stop

**Descrição:** Para o scheduler backend

**Resposta de Sucesso:**
```json
{
  "success": true,
  "message": "Scheduler parado com sucesso",
  "data": {
    "isRunning": false,
    "enabled": true,
    "interval": 30000,
    "lastExecution": 1703123456789,
    "executionSource": "backend",
    "timeSinceLastExecution": 15000,
    "stats": {
      "totalExecutions": 10,
      "successfulExecutions": 9,
      "failedExecutions": 1,
      "lastError": "2025-01-20T10:30:00.000Z",
      "lastSuccess": "2025-01-20T10:35:00.000Z"
    },
    "endpoints": [
      "/api/adminlog",
      "/api/chat_in_game",
      "/api/LogVeiculos",
      "/api/famepoints",
      "/api/bunkers/status",
      "/api/players/painelplayers"
    ],
    "nextExecution": null
  }
}
```

### 4. POST /api/scheduler/execute

**Descrição:** Executa manualmente a sequência de endpoints

**Resposta de Sucesso:**
```json
{
  "success": true,
  "message": "Execução manual realizada com sucesso",
  "data": {
    "success": true,
    "executionTime": 8500,
    "successCount": 5,
    "failureCount": 1,
    "results": [
      {
        "success": true,
        "status": 200,
        "endpoint": "/api/adminlog"
      },
      {
        "success": true,
        "status": 200,
        "endpoint": "/api/chat_in_game"
      },
      {
        "success": false,
        "error": "Request timeout",
        "endpoint": "/api/LogVeiculos"
      },
      {
        "success": true,
        "status": 200,
        "endpoint": "/api/famepoints"
      },
      {
        "success": true,
        "status": 200,
        "endpoint": "/api/bunkers/status"
      },
      {
        "success": true,
        "status": 200,
        "endpoint": "/api/players/painelplayers"
      }
    ],
    "source": "manual"
  }
}
```

### 5. GET /api/scheduler/can-frontend-execute

**Descrição:** Verifica se o frontend pode executar (para evitar conflitos)

**Resposta de Sucesso:**
```json
{
  "success": true,
  "message": "Verificação de execução do frontend realizada",
  "data": {
    "canExecute": false,
    "schedulerStatus": {
      "isRunning": true,
      "enabled": true,
      "interval": 30000,
      "lastExecution": 1703123456789,
      "executionSource": "backend",
      "timeSinceLastExecution": 5000,
      "stats": {
        "totalExecutions": 10,
        "successfulExecutions": 9,
        "failedExecutions": 1,
        "lastError": "2025-01-20T10:30:00.000Z",
        "lastSuccess": "2025-01-20T10:35:00.000Z"
      },
      "endpoints": [
        "/api/adminlog",
        "/api/chat_in_game",
        "/api/LogVeiculos",
        "/api/famepoints",
        "/api/bunkers/status",
        "/api/players/painelplayers"
      ],
      "nextExecution": 1703123486789
    }
  }
}
```

### 6. POST /api/scheduler/frontend-execute

**Descrição:** Executa a sequência pelo frontend (se permitido)

**Resposta de Sucesso:**
```json
{
  "success": true,
  "message": "Execução do frontend realizada com sucesso",
  "data": {
    "success": true,
    "executionTime": 8200,
    "successCount": 6,
    "failureCount": 0,
    "results": [
      {
        "success": true,
        "status": 200,
        "endpoint": "/api/adminlog"
      },
      {
        "success": true,
        "status": 200,
        "endpoint": "/api/chat_in_game"
      },
      {
        "success": true,
        "status": 200,
        "endpoint": "/api/LogVeiculos"
      },
      {
        "success": true,
        "status": 200,
        "endpoint": "/api/famepoints"
      },
      {
        "success": true,
        "status": 200,
        "endpoint": "/api/bunkers/status"
      },
      {
        "success": true,
        "status": 200,
        "endpoint": "/api/players/painelplayers"
      }
    ],
    "source": "frontend"
  }
}
```

**Resposta de Erro (quando não pode executar):**
```json
{
  "success": false,
  "error": "Frontend não pode executar neste momento"
}
```

## Configuração

O scheduler é configurado no arquivo `src/data/server/config.json`:

```json
{
  "scheduler": {
    "enabled": true,
    "interval": 30000,
    "frontend_fallback": true,
    "endpoints": [
      "/api/adminlog",
      "/api/chat_in_game",
      "/api/LogVeiculos",
      "/api/famepoints",
      "/api/bunkers/status",
      "/api/players/painelplayers"
    ],
    "retry_attempts": 3,
    "retry_delay": 5000,
    "timeout": 10000
  }
}
```

## Lógica de Controle

### Prioridade de Execução:
1. **Backend** tem prioridade quando ativo
2. **Frontend** só executa se backend estiver inativo ou se passou tempo suficiente
3. **Execução manual** sempre disponível

### Prevenção de Conflitos:
- Se backend executou há < 24 segundos → frontend não executa
- Se frontend executou há < 24 segundos → backend não executa
- Logs detalhados de qual fonte executou

### Estados do Sistema:
- **Backend Ativo + Frontend Ativo**: Backend executa, frontend monitora
- **Backend Inativo + Frontend Ativo**: Frontend executa normalmente
- **Backend Ativo + Frontend Inativo**: Apenas backend executa
- **Ambos Inativos**: Nenhuma execução automática

## Implementação no Frontend

### Verificação Antes de Executar:
```javascript
// Verificar se pode executar antes de fazer a chamada
const response = await fetch('/api/scheduler/can-frontend-execute');
const data = await response.json();

if (data.data.canExecute) {
  // Executar normalmente
  await executeEndpoints();
} else {
  // Backend está executando, apenas monitorar
  console.log('Backend está executando, aguardando...');
}
```

### Monitoramento de Status:
```javascript
// Verificar status periodicamente
setInterval(async () => {
  const response = await fetch('/api/scheduler/status');
  const data = await response.json();
  
  updateSchedulerStatus(data.data);
}, 5000);
```

### Controles de Interface:
```javascript
// Botões de controle
const startScheduler = async () => {
  await fetch('/api/scheduler/start', { method: 'POST' });
};

const stopScheduler = async () => {
  await fetch('/api/scheduler/stop', { method: 'POST' });
};

const executeManual = async () => {
  await fetch('/api/scheduler/execute', { method: 'POST' });
};
```

## Logs e Monitoramento

O sistema gera logs detalhados para:
- Início/parada do scheduler
- Execuções bem-sucedidas e falhas
- Conflitos entre backend e frontend
- Estatísticas de performance

## Migração Gradual

1. **Fase 1**: Implementar backend (paralelo)
2. **Fase 2**: Testar e ajustar configurações
3. **Fase 3**: Ativar backend, manter frontend como fallback
4. **Fase 4**: Opcional: desabilitar frontend

## Benefícios

- ✅ **Independência do frontend**
- ✅ **Execução garantida**
- ✅ **Melhor controle de erros**
- ✅ **Logs centralizados**
- ✅ **Configuração flexível**
- ✅ **Redundância em caso de falhas** 