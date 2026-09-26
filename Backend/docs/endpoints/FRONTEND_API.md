# 📚 Documentação de API - Endpoints de Controle do Servidor

Esta documentação é destinada ao desenvolvedor do frontend para integração com os endpoints de controle do servidor.

---

## 🚀 **POST /api/server/start**

Inicia o servidor SCUM com atualização SteamCMD automática.

### **URL Base**
```
http://localhost:3000/api/server/start
```
*(Substitua pela URL do seu ambiente de produção)*

### **Método HTTP**
```
POST
```

### **Headers**
```
Content-Type: application/json
```

### **Body (Opcional)**
```json
{
  "force": false,
  "wait_timeout": 30
}
```

### **Parâmetros**

| Parâmetro | Tipo | Obrigatório | Padrão | Descrição |
|-----------|------|-------------|--------|-----------|
| `force` | boolean | Não | `false` | Força início mesmo se o servidor já estiver rodando |
| `wait_timeout` | number | Não | `30` | Tempo de espera (em segundos) para confirmação do status. Máximo: 10 segundos |

### **Resposta de Sucesso (200)**

```json
{
  "success": true,
  "message": "Servidor iniciado com sucesso",
  "status": "started",
  "data": {
    "service_name": "SCUMServer",
    "pid": 1234,
    "uptime": 0
  },
  "final_status": {
    "is_running": true,
    "service_name": "SCUMServer"
  }
}
```

### **Resposta de Erro (400) - Servidor já está rodando**

```json
{
  "success": false,
  "message": "Servidor já está rodando",
  "status": "already_running"
}
```

### **Resposta de Erro (500)**

```json
{
  "success": false,
  "error": "Erro específico"
}
```

### **Exemplo de Uso (JavaScript/TypeScript)**

```typescript
const startServer = async (force = false, waitTimeout = 30) => {
  try {
    const response = await fetch('http://localhost:3000/api/server/start', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        force,
        wait_timeout: waitTimeout
      })
    });

    const data = await response.json();

    if (data.success) {
      console.log('Servidor iniciado:', data.message);
      console.log('PID:', data.data?.pid);
      console.log('Status final:', data.final_status);
      return data;
    } else {
      console.error('Erro:', data.message || data.error);
      throw new Error(data.message || data.error);
    }
  } catch (error) {
    console.error('Erro na requisição:', error);
    throw error;
  }
};
```

### **Exemplo de Uso (Axios)**

```typescript
import axios from 'axios';

const startServer = async (force = false, waitTimeout = 30) => {
  try {
    const response = await axios.post('http://localhost:3000/api/server/start', {
      force,
      wait_timeout: waitTimeout
    });
    
    return response.data;
  } catch (error) {
    console.error('Erro ao iniciar servidor:', error.response?.data || error.message);
    throw error;
  }
};
```

---

## 🛑 **POST /api/server/stop**

Para o servidor SCUM de forma segura.

### **URL Base**
```
http://localhost:3000/api/server/stop
```
*(Substitua pela URL do seu ambiente de produção)*

### **Método HTTP**
```
POST
```

### **Headers**
```
Content-Type: application/json
```

### **Body (Opcional)**
```json
{
  "force": false,
  "wait_timeout": 30
}
```

### **Parâmetros**

| Parâmetro | Tipo | Obrigatório | Padrão | Descrição |
|-----------|------|-------------|--------|-----------|
| `force` | boolean | Não | `false` | Força parada mesmo se o servidor não estiver rodando |
| `wait_timeout` | number | Não | `30` | Tempo de espera (em segundos) para confirmação do status. Máximo: 10 segundos |

### **Resposta de Sucesso (200)**

```json
{
  "success": true,
  "message": "Servidor parado com sucesso",
  "status": "stopped",
  "final_status": {
    "is_running": false,
    "service_name": "SCUMServer"
  }
}
```

### **Resposta de Erro (400) - Servidor não está rodando**

```json
{
  "success": false,
  "message": "Servidor não está rodando",
  "status": "not_running"
}
```

### **Resposta de Erro (500)**

```json
{
  "success": false,
  "error": "Erro específico"
}
```

### **Exemplo de Uso (JavaScript/TypeScript)**

```typescript
const stopServer = async (force = false, waitTimeout = 30) => {
  try {
    const response = await fetch('http://localhost:3000/api/server/stop', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        force,
        wait_timeout: waitTimeout
      })
    });

    const data = await response.json();

    if (data.success) {
      console.log('Servidor parado:', data.message);
      console.log('Status final:', data.final_status);
      return data;
    } else {
      console.error('Erro:', data.message || data.error);
      throw new Error(data.message || data.error);
    }
  } catch (error) {
    console.error('Erro na requisição:', error);
    throw error;
  }
};
```

### **Exemplo de Uso (Axios)**

```typescript
import axios from 'axios';

const stopServer = async (force = false, waitTimeout = 30) => {
  try {
    const response = await axios.post('http://localhost:3000/api/server/stop', {
      force,
      wait_timeout: waitTimeout
    });
    
    return response.data;
  } catch (error) {
    console.error('Erro ao parar servidor:', error.response?.data || error.message);
    throw error;
  }
};
```

---

## 🔄 **POST /api/server/restart**

Reinicia o servidor SCUM (para + inicia). Envia notificações para Discord durante o processo.

### **URL Base**
```
http://localhost:3000/api/server/restart
```
*(Substitua pela URL do seu ambiente de produção)*

### **Método HTTP**
```
POST
```

### **Headers**
```
Content-Type: application/json
```

### **Body (Opcional)**
```json
{
  "force": false,
  "wait_timeout": 30
}
```

### **Parâmetros**

| Parâmetro | Tipo | Obrigatório | Padrão | Descrição |
|-----------|------|-------------|--------|-----------|
| `force` | boolean | Não | `false` | Força reinício mesmo se o servidor não estiver rodando |
| `wait_timeout` | number | Não | `30` | Tempo de espera (em segundos) para confirmação do status. Máximo: 10 segundos |

### **Resposta de Sucesso (200)**

```json
{
  "success": true,
  "message": "Servidor reiniciado com sucesso",
  "status": "restarted",
  "final_status": {
    "is_running": true,
    "service_name": "SCUMServer"
  }
}
```

### **Resposta de Erro (400) - Servidor não está rodando**

```json
{
  "success": false,
  "message": "Servidor não está rodando",
  "status": "not_running"
}
```

### **Resposta de Erro (500)**

```json
{
  "success": false,
  "error": "Erro específico"
}
```

### **Exemplo de Uso (JavaScript/TypeScript)**

```typescript
const restartServer = async (force = false, waitTimeout = 30) => {
  try {
    const response = await fetch('http://localhost:3000/api/server/restart', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        force,
        wait_timeout: waitTimeout
      })
    });

    const data = await response.json();

    if (data.success) {
      console.log('Servidor reiniciado:', data.message);
      console.log('Status final:', data.final_status);
      return data;
    } else {
      console.error('Erro:', data.message || data.error);
      throw new Error(data.message || data.error);
    }
  } catch (error) {
    console.error('Erro na requisição:', error);
    throw error;
  }
};
```

### **Exemplo de Uso (Axios)**

```typescript
import axios from 'axios';

const restartServer = async (force = false, waitTimeout = 30) => {
  try {
    const response = await axios.post('http://localhost:3000/api/server/restart', {
      force,
      wait_timeout: waitTimeout
    });
    
    return response.data;
  } catch (error) {
    console.error('Erro ao reiniciar servidor:', error.response?.data || error.message);
    throw error;
  }
};
```

---

## 📋 **Tipos TypeScript**

Para facilitar a integração, você pode usar os seguintes tipos:

```typescript
interface ServerRequest {
  force?: boolean;
  wait_timeout?: number;
}

interface ServerResponse {
  success: boolean;
  message?: string;
  status?: 'started' | 'stopped' | 'restarted' | 'already_running' | 'not_running';
  data?: {
    service_name?: string;
    pid?: number;
    uptime?: number;
  };
  final_status?: {
    is_running: boolean;
    service_name?: string;
  };
  error?: string;
}
```

---

## ⚠️ **Observações Importantes**

### **1. Body Opcional**
Todos os endpoints aceitam o body vazio `{}` ou sem body. Se não for enviado, o backend utilizará os valores padrão:
- `force: false`
- `wait_timeout: 30`

### **2. Tempo de Resposta**
As requisições podem demorar alguns segundos devido a:
- Processos de atualização SteamCMD (no caso de `start` e `restart`)
- Verificação de status do servidor
- Aguardar confirmação se `wait_timeout > 0`

**Recomendação**: Configure um timeout adequado no seu cliente HTTP (ex: 60 segundos).

### **3. Códigos HTTP**
- **200**: Operação bem-sucedida
- **400**: Erro de validação (servidor já está rodando/não está rodando)
- **500**: Erro interno do servidor ou ServerManager não inicializado

### **4. Validação de Resposta**
Sempre verifique o campo `success` na resposta antes de processar os dados:

```typescript
if (response.success) {
  // Processar sucesso
} else {
  // Tratar erro
  const errorMessage = response.message || response.error;
}
```

### **5. Status Possíveis**
O campo `status` pode conter os seguintes valores:
- `"started"` - Servidor iniciado com sucesso
- `"stopped"` - Servidor parado com sucesso
- `"restarted"` - Servidor reiniciado com sucesso
- `"already_running"` - Servidor já está rodando (erro)
- `"not_running"` - Servidor não está rodando (erro)

### **6. Notificações Discord**
Os endpoints enviam automaticamente notificações para o Discord durante as operações. Isso é feito em background e não afeta a resposta da API.

### **7. Wait Timeout**
O parâmetro `wait_timeout` é limitado a no máximo 10 segundos pelo backend, mesmo que você envie um valor maior.

---

## 🔗 **Integração Completa (Exemplo React)**

```typescript
import { useState } from 'react';
import axios from 'axios';

const API_BASE_URL = 'http://localhost:3000';

interface ServerControlProps {
  onStatusChange?: (status: string) => void;
}

export const ServerControl: React.FC<ServerControlProps> = ({ onStatusChange }) => {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleStart = async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await axios.post(`${API_BASE_URL}/api/server/start`, {
        force: false,
        wait_timeout: 30
      });
      
      if (response.data.success) {
        onStatusChange?.(response.data.status);
      } else {
        setError(response.data.message || response.data.error);
      }
    } catch (err: any) {
      setError(err.response?.data?.error || err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleStop = async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await axios.post(`${API_BASE_URL}/api/server/stop`, {
        force: false,
        wait_timeout: 30
      });
      
      if (response.data.success) {
        onStatusChange?.(response.data.status);
      } else {
        setError(response.data.message || response.data.error);
      }
    } catch (err: any) {
      setError(err.response?.data?.error || err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleRestart = async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await axios.post(`${API_BASE_URL}/api/server/restart`, {
        force: false,
        wait_timeout: 30
      });
      
      if (response.data.success) {
        onStatusChange?.(response.data.status);
      } else {
        setError(response.data.message || response.data.error);
      }
    } catch (err: any) {
      setError(err.response?.data?.error || err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div>
      <button onClick={handleStart} disabled={loading}>
        {loading ? 'Processando...' : 'Iniciar Servidor'}
      </button>
      <button onClick={handleStop} disabled={loading}>
        {loading ? 'Processando...' : 'Parar Servidor'}
      </button>
      <button onClick={handleRestart} disabled={loading}>
        {loading ? 'Processando...' : 'Reiniciar Servidor'}
      </button>
      {error && <div className="error">{error}</div>}
    </div>
  );
};
```

---

## 🔐 **PUT/PATCH /api/players/{steam_id}/permissao**

Atualiza a permissão do comando `/tm` para um jogador na tabela `players`. A coluna `permissao` controla se o jogador pode usar o comando `/tm`.

### **URL Base**
```
http://192.168.100.3:3000/api/players/{steam_id}/permissao
```
*(Substitua pela URL do seu ambiente de produção)*

### **Método HTTP**
```
PUT ou PATCH
```

### **Headers**
```
Content-Type: application/json
```

### **Parâmetros**

| Parâmetro | Tipo | Obrigatório | Local | Descrição |
|-----------|------|-------------|-------|-----------|
| `steam_id` | string | Sim | Path | Steam ID do jogador |
| `permissao` | number | Sim | Body | `0` (desativado) ou `1` (ativado) |

### **Body (Obrigatório)**
```json
{
  "permissao": 1
}
```

### **Resposta de Sucesso (200)**

```json
{
  "success": true,
  "message": "Permissão do comando /tm ativada com sucesso",
  "data": {
    "steam_id": "76561198040636105",
    "player_name": "Pedreiro",
    "player_id": 230,
    "first_seen": "2025-10-27 22:21:01",
    "last_seen": "2025-10-31 02:53:09",
    "total_sessions": 34,
    "total_playtime": 9.928,
    "is_new_player": false,
    "notification_sent": true,
    "permissao": 1,
    "created_at": "2025-10-27 22:21:01"
  }
}
```

### **Resposta de Erro (400) - Campo obrigatório**

```json
{
  "success": false,
  "error": "Campo 'permissao' é obrigatório"
}
```

### **Resposta de Erro (400) - Valor inválido**

```json
{
  "success": false,
  "error": "Campo 'permissao' deve ser 0 ou 1"
}
```

### **Resposta de Erro (404) - Jogador não encontrado**

```json
{
  "success": false,
  "error": "Jogador com steam_id 76561198040636105 não encontrado"
}
```

### **Resposta de Erro (500)**

```json
{
  "success": false,
  "error": "Erro específico"
}
```

### **Exemplo de Uso (JavaScript/TypeScript)**

```typescript
// Ativar permissão do comando /tm
const updatePlayerPermissao = async (steamId: string, permissao: 0 | 1) => {
  try {
    const response = await fetch(
      `http://192.168.100.3:3000/api/players/${steamId}/permissao`,
      {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          permissao
        })
      }
    );

    const data = await response.json();

    if (data.success) {
      console.log('Permissão atualizada:', data.message);
      console.log('Dados do jogador:', data.data);
      return data.data;
    } else {
      console.error('Erro:', data.error);
      throw new Error(data.error);
    }
  } catch (error) {
    console.error('Erro na requisição:', error);
    throw error;
  }
};

// Uso
await updatePlayerPermissao('76561198040636105', 1); // Ativar
await updatePlayerPermissao('76561198040636105', 0); // Desativar
```

### **Exemplo de Uso (Axios)**

```typescript
import axios from 'axios';

const updatePlayerPermissao = async (steamId: string, permissao: 0 | 1) => {
  try {
    const response = await axios.put(
      `http://192.168.100.3:3000/api/players/${steamId}/permissao`,
      { permissao }
    );
    
    return response.data.data;
  } catch (error) {
    console.error('Erro ao atualizar permissão:', error.response?.data || error.message);
    throw error;
  }
};

// Uso
await updatePlayerPermissao('76561198040636105', 1); // Ativar
await updatePlayerPermissao('76561198040636105', 0); // Desativar
```

### **Observações**

1. **Coluna `permissao`:** Controla se o jogador pode usar o comando `/tm` no servidor
2. **Valores:** 
   - `0` = Jogador **não pode** usar o comando `/tm`
   - `1` = Jogador **pode** usar o comando `/tm`
3. **Validação:** O endpoint valida que o jogador existe antes de atualizar
4. **Diferente de permissões:** Este endpoint é diferente do sistema de permissões (`player_permissions`), que gerencia outros tipos de permissões (admin, banned, etc.)

---

## 📞 **Suporte**

Em caso de dúvidas sobre a integração, entre em contato com o time de backend.

---

## 📚 **GET /api/players**

Lista todos os players cadastrados na tabela `players` do banco de dados SSM.db. Por padrão, retorna 100 registros por chamada (máximo 1000); use `offset` para paginação incremental.

### **URL Base**
```
http://192.168.100.3:3000/api/players
```
*(Substitua pela URL do seu ambiente de produção)*

### **Método HTTP**
```
GET
```

### **Headers**
```
Nenhum necessário
```

### **Parâmetros Query (Opcionais)**

| Parâmetro | Tipo | Obrigatório | Padrão | Descrição |
|-----------|------|-------------|--------|-----------|
| `limit` | number | Não | `100` | Número máximo de registros a retornar (1–1000) |
| `offset` | number | Não | `0` | Deslocamento para paginação (>= 0) |
| `sort_by` | string | Não | `last_seen` | Campo de ordenação. Valores suportados: `last_seen`, `first_seen`, `player_name`, `total_playtime`, `total_sessions`, `created_at`, `vehicles_total` |
| `sort_order` | string | Não | `desc` | Direção da ordenação (`asc` ou `desc`) |

> **Dica**: para ordenar pela coluna "Veículos" na lista do frontend, utilize `sort_by=vehicles_total` (e envie os mesmos parâmetros para `/api/players/vehicles/summary`).

### **Resposta de Sucesso (200)**

```json
{
  "success": true,
  "data": {
    "players": [
      {
        "steam_id": "76561198040636105",
        "player_name": "Pedreiro",
        "player_id": 230,
        "first_seen": "2025-10-27 22:21:01",
        "last_seen": "2025-10-31 02:53:09",
        "total_sessions": 34,
        "total_playtime": 9.928,
        "is_new_player": false,
        "notification_sent": true,
        "permissao": 0,
        "created_at": "2025-10-27 22:21:01"
      },
      {
        "steam_id": "76561198094354554",
        "player_name": "ARKANJO",
        "player_id": 231,
        "first_seen": "2025-10-31 00:02:58",
        "last_seen": "2025-10-31 00:58:54",
        "total_sessions": 8,
        "total_playtime": 13.424,
        "is_new_player": false,
        "notification_sent": true,
        "permissao": 0,
        "created_at": "2025-10-31 00:02:58"
      }
    ],
    "total": 317,
    "limit": 100,
    "offset": 0,
    "count": 100,
    "sort_by": "last_seen",
    "sort_order": "desc"
  }
}
```

### **Resposta de Erro (500)**

```json
{
  "success": false,
  "error": "Erro específico"
}
```

### **Exemplo de Uso (JavaScript/TypeScript)**

```typescript
// Listar todos os players
const getAllPlayers = async () => {
  try {
    const response = await fetch('http://192.168.100.3:3000/api/players');
    const data = await response.json();
    
    if (data.success) {
      console.log('Total de players:', data.data.total);
      console.log('Players:', data.data.players);
      return data.data.players;
    } else {
      console.error('Erro:', data.error);
      throw new Error(data.error);
    }
  } catch (error) {
    console.error('Erro na requisição:', error);
    throw error;
  }
};

// Com paginação
const getPlayersPaginated = async (limit = 10, offset = 0) => {
  try {
    const response = await fetch(
      `http://192.168.100.3:3000/api/players?limit=${limit}&offset=${offset}`
    );
    const data = await response.json();
    
    if (data.success) {
      return data.data;
    } else {
      throw new Error(data.error);
    }
  } catch (error) {
    console.error('Erro na requisição:', error);
    throw error;
  }
};
```

### **Exemplo de Uso (Axios)**

```typescript
import axios from 'axios';

// Listar todos os players
const getAllPlayers = async () => {
  try {
    const response = await axios.get('http://192.168.100.3:3000/api/players');
    return response.data.data.players;
  } catch (error) {
    console.error('Erro ao listar players:', error.response?.data || error.message);
    throw error;
  }
};

// Com paginação
const getPlayersPaginated = async (limit = 10, offset = 0) => {
  try {
    const response = await axios.get('http://192.168.100.3:3000/api/players', {
      params: {
        limit,
        offset
      }
    });
    return response.data.data;
  } catch (error) {
    console.error('Erro ao listar players:', error.response?.data || error.message);
    throw error;
  }
};
```

### **Observações**

1. **Ordenação:** Os players são ordenados por `last_seen` em ordem decrescente (mais recentes primeiro)
2. **Paginação:** Use `limit` e `offset` para paginar os resultados
3. **Campos:** Todos os campos da tabela `players` são retornados
4. **Tipos:** `is_new_player` e `notification_sent` são convertidos para boolean na resposta

---

### Resumo de Veículos por Jogador

#### `GET /api/players/vehicles/summary`
Retorna, para cada jogador da página atual de `/api/players`, a contagem de veículos por status.

**Query Parameters:**

| Parâmetro | Tipo | Obrigatório | Padrão | Descrição |
|-----------|------|-------------|--------|-----------|
| `limit`   | number | Não | `100` | Número máximo de jogadores por página (1–1000) |
| `offset`  | number | Não | `0` | Deslocamento para paginação (>= 0) |
| `steam_id`| string | Não | — | Quando informado, retorna apenas o resumo do jogador correspondente |

**Resposta de Sucesso (200):**

```json
{
  "success": true,
  "data": {
    "limit": 100,
    "offset": 0,
    "total": 317,
    "count": 100,
    "summaries": [
      {
        "steam_id": "76561198040636105",
        "player_id": 230,
        "total": 4,
        "by_status": {
          "0": 3,
          "1": 1,
          "2": 0,
          "3": 0
        },
        "updated_at": "2025-11-10T01:30:00Z"
      }
    ]
  }
}
```

`by_status` usa os mesmos códigos do endpoint detalhado (`0` = Ativo, `1` = Inativo, `2` = Desaparecido, `3` = Destruído). Jogadores sem veículos retornam `total: 0` e contagens zeradas.

**Uso:**

```typescript
import { getPlayersVehicleSummary } from '@/services/server';

// Resumo alinhado com /api/players (mesmo limit/offset)
const vehicleSummary = await getPlayersVehicleSummary(100, 0);

// Resumo de um jogador específico
const singleSummary = await getPlayersVehicleSummary(1, 0, '76561198040636105');
```

---

### Logs de Players

#### `GET /api/logs/players?limit=100&offset=0`
Obtém logs e sessões ativas de players.

