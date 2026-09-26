# 🔌 Guia de Configuração - Integração Frontend/Backend SSM

## ✅ **Situação Atual**

### **Configuração do Backend**

O backend SSM está configurado para aceitar conexões externas e já possui **CORS habilitado**.

**Configuração atual:**

- **Protocolo:** `http`
- **Host:** `0.0.0.0` (aceita conexões de qualquer IP da rede)
- **Porta:** `3000`
- **Base Path:** `/api`
- **CORS:** ✅ Habilitado (sem restrições)

**Arquivo de configuração:** `data/config.json`

```json
{
  "api": {
    "host": "0.0.0.0",
    "port": 3000,
    "debug": false
  }
}
```

---

## 🌐 **URLs de Conexão**

### **Para conexão na mesma máquina (localhost):**

```
http://localhost:3000/api
```

### **Para conexão de outro dispositivo na rede:**

```
http://192.168.100.3:3000/api
```

*(Substitua `192.168.100.3` pelo IP real da máquina onde o backend está rodando)*

---

## 📋 **Configuração Recomendada para o Frontend**

### **Arquivo: `src/config.json`**

```json
{
  "backend": {
    "host": "192.168.100.3",
    "port": 3000,
    "protocol": "http",
    "basePath": "/api",
    "timeout": 60000
  }
}
```

### **URL Base Completa:**

```
http://192.168.100.3:3000/api
```

---

## 🚀 **Como Iniciar o Backend**

### **Opção 1: Executar diretamente**

```bash
python main.py
```

### **Opção 2: Executar com Python**

```bash
python3 main.py
```

### **Verificação de Inicialização**

Ao iniciar, você verá no console:

```
Iniciando SCUM Backend...
Servidor API iniciando em http://0.0.0.0:3000
```

---

## 🧪 **Como Testar a Conexão**

### **1. Teste no Navegador**

Acesse diretamente no navegador:

```
http://192.168.100.3:3000/api/server/status
```

**Resposta esperada (JSON):**

```json
{
  "success": true,
  "data": {
    "is_running": false,
    "service_name": "SCUMServer",
    ...
  }
}
```

### **2. Teste via cURL (Terminal)**

```bash
curl http://192.168.100.3:3000/api/server/status
```

### **3. Teste via Postman/Insomnia**

- **Método:** `GET`
- **URL:** `http://192.168.100.3:3000/api/server/status`
- **Headers:** Nenhum necessário

### **4. Teste via JavaScript/Fetch**

```javascript
fetch('http://192.168.100.3:3000/api/server/status')
  .then(response => response.json())
  .then(data => console.log('Status:', data))
  .catch(error => console.error('Erro:', error));
```

### **5. Teste dos Endpoints de Controle**

#### **Iniciar Servidor**

```bash
curl -X POST http://192.168.100.3:3000/api/server/start \
  -H "Content-Type: application/json" \
  -d '{}'
```

#### **Parar Servidor**

```bash
curl -X POST http://192.168.100.3:3000/api/server/stop \
  -H "Content-Type: application/json" \
  -d '{}'
```

#### **Reiniciar Servidor**

```bash
curl -X POST http://192.168.100.3:3000/api/server/restart \
  -H "Content-Type: application/json" \
  -d '{}'
```

---

## 🔧 **Troubleshooting**

### **Erro: `ERR_CONNECTION_REFUSED`**

#### **Causa 1: Backend não está rodando**

✅ **Solução:** Inicie o backend executando `python main.py`

#### **Causa 2: Firewall bloqueando a porta 3000**

✅ **Solução:** Configure o firewall do Windows para permitir conexões na porta 3000

**No Windows:**

1. Abra o "Firewall do Windows Defender"
2. Clique em "Configurações avançadas"
3. Clique em "Regras de entrada" → "Nova regra"
4. Selecione "Porta" → Próximo
5. Selecione "TCP" e digite `3000` na porta específica
6. Permita a conexão
7. Aplique a regra para todos os perfis

#### **Causa 3: IP incorreto**

✅ **Solução:** Verifique o IP da máquina do backend:

**No Windows (Prompt de Comando):**

```cmd
ipconfig
```

Procure pelo **IPv4** na seção do adaptador de rede ativo (ex: `192.168.100.3`)

#### **Causa 4: Backend configurado para localhost apenas**

✅ **Solução:** Verifique se o arquivo `data/config.json` tem:

```json
{
  "api": {
    "host": "0.0.0.0",  // ✅ Deve ser 0.0.0.0 (não 127.0.0.1)
    "port": 3000
  }
}
```

Se estiver como `127.0.0.1`, altere para `0.0.0.0` e reinicie o backend.

---

### **Erro: `CORS Policy` (Cross-Origin)**

✅ **Status:** CORS já está habilitado no backend. Se ainda ocorrer erro, verifique se o backend está rodando a versão mais recente.

---

### **Erro: `Timeout`**

✅ **Solução:** Os endpoints de controle (`start`, `stop`, `restart`) podem demorar alguns segundos. Configure um timeout adequado no seu cliente HTTP:

**Exemplo com Axios:**

```typescript
const axios = require('axios');

const api = axios.create({
  baseURL: 'http://192.168.100.3:3000/api',
  timeout: 60000, // 60 segundos
  headers: {
    'Content-Type': 'application/json'
  }
});
```

---

## 📡 **Endpoints Disponíveis**

### **Controle do Servidor**

| Método | Endpoint | Descrição |
|--------|----------|-----------|
| `POST` | `/api/server/start` | Inicia o servidor SCUM |
| `POST` | `/api/server/stop` | Para o servidor SCUM |
| `POST` | `/api/server/restart` | Reinicia o servidor SCUM |
| `GET` | `/api/server/status` | Retorna status atual do servidor |

### **Health Check**

| Método | Endpoint | Descrição |
|--------|----------|-----------|
| `GET` | `/api/health` | Verifica se a API está respondendo |

**Resposta do Health Check:**

```json
{
  "status": "ok",
  "timestamp": "2024-01-15T10:30:45.123456"
}
```

---

## 📝 **Exemplo de Integração Completa (React + Axios)**

```typescript
// src/services/api.ts
import axios from 'axios';

const API_BASE_URL = 'http://192.168.100.3:3000/api';

const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 60000,
  headers: {
    'Content-Type': 'application/json'
  }
});

export interface ServerStatus {
  success: boolean;
  data?: {
    is_running: boolean;
    service_name: string;
    // ... outros campos
  };
  error?: string;
}

export interface ServerControlResponse {
  success: boolean;
  message?: string;
  status?: string;
  data?: any;
  final_status?: any;
  error?: string;
}

export const serverAPI = {
  // Verificar status
  getStatus: async (): Promise<ServerStatus> => {
    const response = await api.get('/server/status');
    return response.data;
  },

  // Iniciar servidor
  start: async (force = false, waitTimeout = 30): Promise<ServerControlResponse> => {
    const response = await api.post('/server/start', {
      force,
      wait_timeout: waitTimeout
    });
    return response.data;
  },

  // Parar servidor
  stop: async (force = false, waitTimeout = 30): Promise<ServerControlResponse> => {
    const response = await api.post('/server/stop', {
      force,
      wait_timeout: waitTimeout
    });
    return response.data;
  },

  // Reiniciar servidor
  restart: async (force = false, waitTimeout = 30): Promise<ServerControlResponse> => {
    const response = await api.post('/server/restart', {
      force,
      wait_timeout: waitTimeout
    });
    return response.data;
  },

  // Health check
  health: async (): Promise<{ status: string }> => {
    const response = await api.get('/health');
    return response.data;
  }
};
```

---

## ✅ **Checklist de Verificação**

Antes de integrar, verifique:

- [ ] Backend está rodando (`python main.py`)
- [ ] Backend mostra: `Servidor API iniciando em http://0.0.0.0:3000`
- [ ] Firewall permite conexões na porta 3000
- [ ] IP da máquina do backend está correto (`ipconfig`)
- [ ] Frontend está configurado com o IP correto
- [ ] рекомендует básico funciona: `http://[IP]:3000/api/server/status`

---

## 📞 **Suporte**

### **Logs do Backend**

Os logs do backend estão disponíveis em:

```
data/logs/
```

### **Verificar se o backend está rodando**

No terminal onde o backend está rodando, você verá mensagens de log para cada requisição recebida.

---

## 🎯 **Resumo Rápido**

**URL Base da API:**

```
http://192.168.100.3:3000/api
```

**Endpoints principais:**

- `GET /api/server/status` - Status do servidor
- `POST /api/server/start` - Iniciar servidor
- `POST /api/server/stop` - Parar servidor
- `POST /api/server/restart` - Reiniciar servidor

**CORS:** ✅ Habilitado  
**Autenticação:** ❌ Não requerida (por enquanto)  
**Timeout recomendado:** 60 segundos  

---

**Última atualização:** 2024-01-15  
**Versão do Backend:** SSM 3.0

