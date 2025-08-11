# Endpoints do Servidor SCUM

## Visão Geral

Esta documentação descreve os endpoints disponíveis para gerenciar o servidor SCUM através da API REST.

**Base URL:** `http://localhost:3000/api/server`

---

## 1. Status do Servidor

### GET `/status`

Retorna o status atual do servidor SCUM.

**URL:** `http://localhost:3000/api/server/status`

**Método:** `GET`

**Headers:**
```
Content-Type: application/json
```

**Resposta de Sucesso (200):**
```json
{
  "success": true,
  "status": {
    "isRunning": true,
    "pid": "12345",
    "startTime": "2024-01-15T10:30:00.000Z",
    "lastCheck": "2024-01-15T11:00:00.000Z",
    "uptime": 1800000,
    "restartCount": 2,
    "lastError": null,
    "version": "0.9.0"
  },
  "config": {
    "port": 8900,
    "maxPlayers": 64,
    "useBattleye": true,
    "serverPath": "C:\\Servers\\Scum\\SCUM\\Binaries\\Win64"
  }
}
```

**Resposta de Erro (500):**
```json
{
  "success": false,
  "error": "Erro interno do servidor"
}
```

**Campos do Status:**
- `isRunning`: Boolean - Se o servidor está rodando
- `pid`: String - ID do processo (se rodando)
- `startTime`: String - Data/hora de início (ISO)
- `lastCheck`: String - Última verificação (ISO)
- `uptime`: Number - Tempo de execução em ms
- `restartCount`: Number - Número de reinicializações
- `lastError`: String - Último erro (se houver)
- `version`: String - Versão do servidor

---

## 2. Iniciar Servidor

### POST `/start`

Inicia o servidor SCUM se não estiver rodando.

**URL:** `http://localhost:3000/api/server/start`

**Método:** `POST`

**Headers:**
```
Content-Type: application/json
```

**Body:** (vazio ou configurações opcionais)
```json
{}
```

**Resposta de Sucesso (200):**
```json
{
  "success": true,
  "message": "Servidor iniciado com sucesso"
}
```

**Resposta de Erro (200) - Servidor já rodando:**
```json
{
  "success": false,
  "error": "Servidor já está rodando"
}
```

**Resposta de Erro (500):**
```json
{
  "success": false,
  "error": "Erro ao iniciar servidor",
  "details": "Detalhes do erro..."
}
```

---

## 3. Parar Servidor

### POST `/stop`

Para o servidor SCUM se estiver rodando.

**URL:** `http://localhost:3000/api/server/stop`

**Método:** `POST`

**Headers:**
```
Content-Type: application/json
```

**Body:** (vazio)
```json
{}
```

**Resposta de Sucesso (200):**
```json
{
  "success": true,
  "message": "Servidor parado com sucesso"
}
```

**Resposta de Erro (200) - Servidor não rodando:**
```json
{
  "success": false,
  "error": "Servidor não está rodando"
}
```

**Resposta de Erro (500):**
```json
{
  "success": false,
  "error": "Erro ao parar servidor",
  "details": "Acesso negado. Tente executar o backend como administrador ou parar o servidor manualmente."
}
```

---

## 4. Reiniciar Servidor

### POST `/restart`

Reinicia o servidor SCUM (para e inicia novamente).

**URL:** `http://localhost:3000/api/server/restart`

**Método:** `POST`

**Headers:**
```
Content-Type: application/json
```

**Body:** (vazio)
```json
{}
```

**Resposta de Sucesso (200):**
```json
{
  "success": true,
  "message": "Servidor reiniciado com sucesso"
}
```

**Resposta de Erro (200) - Servidor não rodando:**
```json
{
  "success": false,
  "error": "Servidor não está rodando"
}
```

**Resposta de Erro (500):**
```json
{
  "success": false,
  "error": "Erro ao reiniciar servidor",
  "details": "Servidor não iniciou após reiniciar"
}
```

---

## Implementação Frontend

### Exemplo com JavaScript/TypeScript

```typescript
// Tipos para as respostas
interface ServerStatus {
  isRunning: boolean;
  pid: string | null;
  startTime: string | null;
  lastCheck: string | null;
  uptime: number;
  restartCount: number;
  lastError: string | null;
  version: string | null;
}

interface ServerConfig {
  port: number;
  maxPlayers: number;
  useBattleye: boolean;
  serverPath: string;
}

interface ApiResponse<T> {
  success: boolean;
  data?: T;
  error?: string;
  details?: string;
  message?: string;
}

// Classe para gerenciar o servidor
class ServerManager {
  private baseUrl = 'http://localhost:3000/api/server';

  // Obter status do servidor
  async getStatus(): Promise<ApiResponse<{status: ServerStatus, config: ServerConfig}>> {
    try {
      const response = await fetch(`${this.baseUrl}/status`);
      const data = await response.json();
      return data;
    } catch (error) {
      return {
        success: false,
        error: 'Erro ao conectar com o servidor'
      };
    }
  }

  // Iniciar servidor
  async startServer(): Promise<ApiResponse<{message: string}>> {
    try {
      const response = await fetch(`${this.baseUrl}/start`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({})
      });
      const data = await response.json();
      return data;
    } catch (error) {
      return {
        success: false,
        error: 'Erro ao conectar com o servidor'
      };
    }
  }

  // Parar servidor
  async stopServer(): Promise<ApiResponse<{message: string}>> {
    try {
      const response = await fetch(`${this.baseUrl}/stop`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({})
      });
      const data = await response.json();
      return data;
    } catch (error) {
      return {
        success: false,
        error: 'Erro ao conectar com o servidor'
      };
    }
  }

  // Reiniciar servidor
  async restartServer(): Promise<ApiResponse<{message: string}>> {
    try {
      const response = await fetch(`${this.baseUrl}/restart`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({})
      });
      const data = await response.json();
      return data;
    } catch (error) {
      return {
        success: false,
        error: 'Erro ao conectar com o servidor'
      };
    }
  }
}

// Exemplo de uso
const serverManager = new ServerManager();

// Verificar status
serverManager.getStatus().then(response => {
  if (response.success) {
    console.log('Servidor rodando:', response.data?.status.isRunning);
    console.log('Uptime:', response.data?.status.uptime);
  } else {
    console.error('Erro:', response.error);
  }
});

// Iniciar servidor
serverManager.startServer().then(response => {
  if (response.success) {
    console.log('Servidor iniciado:', response.message);
  } else {
    console.error('Erro:', response.error);
  }
});
```

### Exemplo com React

```tsx
import React, { useState, useEffect } from 'react';

interface ServerStatus {
  isRunning: boolean;
  pid: string | null;
  startTime: string | null;
  uptime: number;
  restartCount: number;
  lastError: string | null;
}

const ServerControl: React.FC = () => {
  const [status, setStatus] = useState<ServerStatus | null>(null);
  const [loading, setLoading] = useState(false);

  const fetchStatus = async () => {
    try {
      const response = await fetch('http://localhost:3000/api/server/status');
      const data = await response.json();
      if (data.success) {
        setStatus(data.status);
      }
    } catch (error) {
      console.error('Erro ao buscar status:', error);
    }
  };

  const handleAction = async (action: 'start' | 'stop' | 'restart') => {
    setLoading(true);
    try {
      const response = await fetch(`http://localhost:3000/api/server/${action}`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({})
      });
      const data = await response.json();
      
      if (data.success) {
        alert(`Servidor ${action === 'start' ? 'iniciado' : action === 'stop' ? 'parado' : 'reiniciado'} com sucesso!`);
        fetchStatus(); // Atualizar status
      } else {
        alert(`Erro: ${data.error}`);
      }
    } catch (error) {
      alert('Erro ao conectar com o servidor');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchStatus();
    const interval = setInterval(fetchStatus, 5000); // Atualizar a cada 5s
    return () => clearInterval(interval);
  }, []);

  return (
    <div>
      <h2>Controle do Servidor SCUM</h2>
      
      {status && (
        <div>
          <p>Status: {status.isRunning ? '🟢 Rodando' : '🔴 Parado'}</p>
          {status.isRunning && (
            <>
              <p>PID: {status.pid}</p>
              <p>Uptime: {Math.floor(status.uptime / 1000 / 60)} minutos</p>
              <p>Reinicializações: {status.restartCount}</p>
            </>
          )}
          {status.lastError && (
            <p>Último erro: {status.lastError}</p>
          )}
        </div>
      )}

      <div>
        <button 
          onClick={() => handleAction('start')} 
          disabled={loading || status?.isRunning}
        >
          Iniciar Servidor
        </button>
        
        <button 
          onClick={() => handleAction('stop')} 
          disabled={loading || !status?.isRunning}
        >
          Parar Servidor
        </button>
        
        <button 
          onClick={() => handleAction('restart')} 
          disabled={loading || !status?.isRunning}
        >
          Reiniciar Servidor
        </button>
      </div>
    </div>
  );
};

export default ServerControl;
```

---

## Notas Importantes

1. **Webhooks:** Todos os endpoints enviam notificações para Discord quando configurado
2. **Validações:** O backend valida se o servidor está rodando antes de executar ações
3. **PowerShell:** Os endpoints de stop e restart usam scripts PowerShell robustos
4. **Configuração:** O servidor usa configurações salvas em `config.json`
5. **Logs:** Todas as ações são logadas no console do backend

---

## Testes

Para testar os endpoints, use:

```bash
# Verificar status
curl -X GET http://localhost:3000/api/server/status

# Iniciar servidor
curl -X POST http://localhost:3000/api/server/start -H "Content-Type: application/json"

# Parar servidor
curl -X POST http://localhost:3000/api/server/stop -H "Content-Type: application/json"

# Reiniciar servidor
curl -X POST http://localhost:3000/api/server/restart -H "Content-Type: application/json"
``` 