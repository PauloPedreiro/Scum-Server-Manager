# 🕐 Sistema de Agendamento - Documentação Frontend

## 📋 Visão Geral

Esta documentação descreve os endpoints da API para controle completo do sistema de agendamento de reinicializações automáticas do servidor SCUM. O sistema permite:

- Gerenciar horários de reinicialização automática
- Configurar notificações prévias (em minutos antes do restart)
- Controlar o estado do agendador (iniciar, parar, reiniciar)
- Visualizar logs de todas as operações
- Forçar reinicialização imediata do servidor
- Atualizar configurações dinamicamente via API

---

## 🌐 Base URL

```
http://localhost:3000/api
```

**⚠️ Nota:** Em produção, substitua `localhost:3000` pela URL do servidor backend.

---

## 📊 Estruturas TypeScript

### **SchedulerStatus**
```typescript
interface SchedulerStatus {
  enabled: boolean;
  is_running: boolean;
  restart_times: string[]; // Formato "HH:MM"
  next_restart: string | null; // ISO 8601
  notification_minutes: number[];
  scheduled_jobs: number;
  logs_count: number;
}
```

### **SchedulerConfig**
```typescript
interface SchedulerConfig {
  enabled: boolean;
  auto_start: boolean;
  restart_times: string[]; // Formato "HH:MM"
  notification_minutes: number[];
  timezone: string; // Ex: "America/Sao_Paulo"
}
```

### **SchedulerLog**
```typescript
interface SchedulerLog {
  timestamp: string; // ISO 8601
  event_type: string;
  message: string;
  data: Record<string, any>;
}
```

### **SchedulerLogResponse**
```typescript
interface SchedulerLogResponse {
  logs: SchedulerLog[];
  count: number;
  limit: number;
}
```

### **ApiResponse**
```typescript
interface ApiResponse<T> {
  success: boolean;
  data?: T;
  message?: string;
  status?: string;
  error?: string;
  timestamp?: number;
  restart_result?: {
    success: boolean;
    message: string;
    status: string;
  };
}
```

### **ForceRestartResponse**
```typescript
interface ForceRestartResponse {
  success: boolean;
  message: string;
  status: string;
  data?: {
    service_name: string;
    pid: number;
    uptime: number;
  };
}
```

---

## 🔌 Endpoints Disponíveis

### 1. Obter Status do Agendador

Retorna o status atual do agendador, incluindo se está rodando, próximos horários de reinicialização e estatísticas.

#### **Endpoint**
```
GET /api/scheduler/status
```

#### **Parâmetros**

Nenhum parâmetro necessário.

#### **Resposta de Sucesso (200)**

```json
{
  "success": true,
  "data": {
    "enabled": true,
    "is_running": true,
    "restart_times": [
      "01:00",
      "05:00",
      "09:00",
      "13:00",
      "17:00",
      "21:00"
    ],
    "next_restart": "2025-11-01T05:00:00",
    "notification_minutes": [10, 5, 4, 3, 2, 1],
    "scheduled_jobs": 8,
    "logs_count": 15
  },
  "timestamp": 1730455200.123456
}
```

#### **Campos da Resposta**

| Campo | Tipo | Descrição |
|-------|------|-----------|
| `enabled` | `boolean` | Se o agendador está habilitado |
| `is_running` | `boolean` | Se o agendador está em execução |
| `restart_times` | `string[]` | Lista de horários configurados (formato "HH:MM") |
| `next_restart` | `string \| null` | Próximo horário de reinicialização (ISO 8601) |
| `notification_minutes` | `number[]` | Minutos antes do restart para notificar |
| `scheduled_jobs` | `number` | Quantidade de jobs agendados |
| `logs_count` | `number` | Quantidade total de logs armazenados |

#### **Resposta de Erro (500)**

```json
{
  "success": false,
  "error": "RestartScheduler não inicializado"
}
```

---

### 2. Iniciar Agendador

Inicia o agendador de reinicializações. Se já estiver rodando, retorna sucesso sem efeito.

#### **Endpoint**
```
POST /api/scheduler/start
```

#### **Parâmetros**

Nenhum parâmetro necessário no body.

#### **Resposta de Sucesso (200)**

```json
{
  "success": true,
  "message": "Agendador iniciado com sucesso",
  "status": "started",
  "data": {
    "restart_times": ["01:00", "05:00", "09:00", "13:00", "17:00", "21:00"],
    "next_restart": "2025-11-01T05:00:00",
    "notification_minutes": [10, 5, 4, 3, 2, 1]
  }
}
```

#### **Resposta de Erro (400)**

```json
{
  "success": false,
  "message": "Nenhum horário de reinicialização configurado",
  "status": "no_times_configured"
}
```

#### **Resposta de Erro (500)**

```json
{
  "success": false,
  "error": "RestartScheduler não inicializado"
}
```

---

### 3. Parar Agendador

Para o agendador de reinicializações. Não reinicia o servidor, apenas para o agendamento.

#### **Endpoint**
```
POST /api/scheduler/stop
```

#### **Parâmetros**

Nenhum parâmetro necessário no body.

#### **Resposta de Sucesso (200)**

```json
{
  "success": true,
  "message": "Agendador parado com sucesso",
  "status": "stopped"
}
```

#### **Resposta de Erro (500)**

```json
{
  "success": false,
  "error": "RestartScheduler não inicializado"
}
```

---

### 4. Reiniciar Agendador

Reinicia o agendador, recarregando as configurações e reagendando todos os horários.

#### **Endpoint**
```
POST /api/scheduler/restart
```

#### **Parâmetros**

Nenhum parâmetro necessário no body.

#### **Resposta de Sucesso (200)**

```json
{
  "success": true,
  "message": "Agendador reiniciado com sucesso",
  "status": "restarted"
}
```

#### **Resposta de Erro (500)**

```json
{
  "success": false,
  "error": "RestartScheduler não inicializado"
}
```

---

### 5. Obter Logs do Agendador

Retorna os logs recentes do agendador, permitindo acompanhar todas as operações realizadas.

#### **Endpoint**
```
GET /api/scheduler/logs
```

#### **Query Parameters (Opcionais)**

| Parâmetro | Tipo | Obrigatório | Descrição | Padrão |
|-----------|------|-------------|-----------|--------|
| `limit` | `number` | ❌ Não | Número máximo de logs a retornar | `50` |

#### **Resposta de Sucesso (200)**

```json
{
  "success": true,
  "data": {
    "logs": [
      {
        "timestamp": "2025-11-01T04:55:00.123456",
        "event_type": "notification",
        "message": "Reinicialização em 5 minutos",
        "data": {
          "restart_time": "2025-11-01T05:00:00"
        }
      },
      {
        "timestamp": "2025-11-01T04:30:00.654321",
        "event_type": "scheduler_started",
        "message": "Agendador iniciado com sucesso",
        "data": {
          "restart_times": ["01:00", "05:00", "09:00"],
          "next_restart": "2025-11-01T05:00:00",
          "notification_minutes": [5, 1]
        }
      }
    ],
    "count": 2,
    "limit": 50
  },
  "timestamp": 1730455200.123456
}
```

#### **Tipos de Eventos**

| Tipo | Descrição |
|------|-----------|
| `scheduler_started` | Agendador iniciado |
| `scheduler_stopped` | Agendador parado |
| `config_updated` | Configuração atualizada |
| `restart_scheduled` | Reinicialização agendada |
| `notification_scheduled` | Notificação agendada |
| `notification` | Notificação enviada |
| `restart_started` | Reinicialização iniciada |
| `restart_success` | Reinicialização bem-sucedida |
| `restart_failed` | Falha na reinicialização |
| `force_restart` | Reinicialização forçada |

#### **Resposta de Erro (500)**

```json
{
  "success": false,
  "error": "RestartScheduler não inicializado"
}
```

---

### 6. Obter Configuração do Agendador

Retorna a configuração atual do agendador, incluindo horários, notificações e outras opções.

#### **Endpoint**
```
GET /api/scheduler/config
```

#### **Parâmetros**

Nenhum parâmetro necessário.

#### **Resposta de Sucesso (200)**

```json
{
  "success": true,
  "data": {
    "enabled": true,
    "auto_start": true,
    "restart_times": [
      "01:00",
      "05:00",
      "09:00",
      "13:00",
      "17:00",
      "21:00"
    ],
    "notification_minutes": [10, 5, 4, 3, 2, 1],
    "timezone": "America/Sao_Paulo"
  },
  "timestamp": 1730455200.123456
}
```

#### **Resposta de Erro (500)**

```json
{
  "success": false,
  "error": "RestartScheduler não inicializado"
}
```

---

### 7. Atualizar Configuração do Agendador

Atualiza a configuração do agendador. O agendador é reiniciado automaticamente após a atualização bem-sucedida.

#### **Endpoint**
```
POST /api/scheduler/config
Content-Type: application/json
```

#### **Body (JSON)**

```json
{
  "enabled": true,
  "restart_times": [
    "02:00",
    "06:00",
    "10:00",
    "14:00",
    "18:00",
    "22:00"
  ],
  "notification_minutes": [10, 5, 1]
}
```

#### **Parâmetros do Body (Opcionais)**

| Parâmetro | Tipo | Obrigatório | Descrição |
|-----------|------|-------------|-----------|
| `enabled` | `boolean` | ❌ Não | Habilita/desabilita o agendador |
| `auto_start` | `boolean` | ❌ Não | Inicia automaticamente com o backend |
| `restart_times` | `string[]` | ❌ Não | Lista de horários no formato "HH:MM" |
| `notification_minutes` | `number[]` | ❌ Não | Minutos antes do restart para notificar |
| `timezone` | `string` | ❌ Não | Fuso horário (ex: "America/Sao_Paulo") |

#### **Validações**

- `restart_times` deve ser um array
- Cada horário deve estar no formato "HH:MM"
- Hora deve estar entre 00-23
- Minuto deve estar entre 00-59

#### **Resposta de Sucesso (200)**

```json
{
  "success": true,
  "message": "Configuração atualizada e agendador reiniciado",
  "status": "updated_and_restarted",
  "restart_result": {
    "success": true,
    "message": "Agendador reiniciado com sucesso",
    "status": "restarted"
  }
}
```

#### **Resposta de Erro (400)**

```json
{
  "success": false,
  "error": "restart_times deve ser uma lista"
}
```

```json
{
  "success": false,
  "error": "Formato de horário inválido: 25:00. Use HH:MM"
}
```

#### **Resposta de Erro (500)**

```json
{
  "success": false,
  "error": "RestartScheduler não inicializado"
}
```

---

### 8. Forçar Reinicialização

Força uma reinicialização imediata do servidor SCUM, independente dos horários agendados.

#### **Endpoint**
```
POST /api/scheduler/force-restart
```

#### **Parâmetros**

Nenhum parâmetro necessário no body.

#### **Resposta de Sucesso (200)**

```json
{
  "success": true,
  "message": "Servidor reiniciado com sucesso",
  "status": "restarted",
  "data": {
    "service_name": "SCUMServer",
    "pid": 1234,
    "uptime": 0
  }
}
```

#### **Resposta de Erro (500)**

```json
{
  "success": false,
  "error": "RestartScheduler não inicializado"
}
```

```json
{
  "success": false,
  "error": "Servidor não está rodando"
}
```

---

## 💻 Exemplos de Implementação

### **React com TypeScript**

```typescript
import { useState, useEffect } from 'react';

const API_BASE_URL = 'http://localhost:3000/api';

// Hook para status do agendador
function useSchedulerStatus() {
  const [status, setStatus] = useState<SchedulerStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchStatus = async () => {
      try {
        const response = await fetch(`${API_BASE_URL}/scheduler/status`);
        const data: ApiResponse<SchedulerStatus> = await response.json();
        
        if (data.success && data.data) {
          setStatus(data.data);
        } else {
          setError(data.error || 'Erro ao obter status');
        }
      } catch (err) {
        setError('Erro de conexão');
      } finally {
        setLoading(false);
      }
    };

    fetchStatus();
    const interval = setInterval(fetchStatus, 30000); // Atualizar a cada 30s

    return () => clearInterval(interval);
  }, []);

  return { status, loading, error };
}

// Componente de controle do agendador
function SchedulerControl() {
  const { status, loading, error } = useSchedulerStatus();
  const [updating, setUpdating] = useState(false);

  const handleStart = async () => {
    setUpdating(true);
    try {
      const response = await fetch(`${API_BASE_URL}/scheduler/start`, {
        method: 'POST',
      });
      const data = await response.json();
      if (data.success) {
        // Recarregar status
        window.location.reload();
      }
    } catch (err) {
      console.error('Erro ao iniciar agendador:', err);
    } finally {
      setUpdating(false);
    }
  };

  const handleStop = async () => {
    setUpdating(true);
    try {
      const response = await fetch(`${API_BASE_URL}/scheduler/stop`, {
        method: 'POST',
      });
      const data = await response.json();
      if (data.success) {
        window.location.reload();
      }
    } catch (err) {
      console.error('Erro ao parar agendador:', err);
    } finally {
      setUpdating(false);
    }
  };

  if (loading) return <div>Carregando...</div>;
  if (error) return <div>Erro: {error}</div>;
  if (!status) return null;

  return (
    <div>
      <h2>Sistema de Agendamento</h2>
      <p>Status: {status.is_running ? 'Rodando' : 'Parado'}</p>
      <p>Próximo restart: {status.next_restart || 'N/A'}</p>
      
      <div>
        <button onClick={handleStart} disabled={updating || status.is_running}>
          Iniciar
        </button>
        <button onClick={handleStop} disabled={updating || !status.is_running}>
          Parar
        </button>
      </div>

      <div>
        <h3>Horários Configurados:</h3>
        <ul>
          {status.restart_times.map((time, idx) => (
            <li key={idx}>{time}</li>
          ))}
        </ul>
      </div>
    </div>
  );
}

// Hook para atualizar configuração
function useUpdateConfig() {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const updateConfig = async (config: Partial<SchedulerConfig>) => {
    setLoading(true);
    setError(null);

    try {
      const response = await fetch(`${API_BASE_URL}/scheduler/config`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(config),
      });

      const data: ApiResponse<any> = await response.json();

      if (!data.success) {
        setError(data.error || 'Erro ao atualizar configuração');
        return false;
      }

      return true;
    } catch (err) {
      setError('Erro de conexão');
      return false;
    } finally {
      setLoading(false);
    }
  };

  return { updateConfig, loading, error };
}
```

---

### **Vue.js com TypeScript**

```vue
<template>
  <div class="scheduler-control">
    <h2>Sistema de Agendamento</h2>
    
    <div v-if="loading">Carregando...</div>
    <div v-else-if="error">Erro: {{ error }}</div>
    <div v-else-if="status">
      <p>Status: {{ status.is_running ? 'Rodando' : 'Parado' }}</p>
      <p>Próximo restart: {{ formatDate(status.next_restart) || 'N/A' }}</p>
      
      <button 
        @click="startScheduler" 
        :disabled="updating || status.is_running"
      >
        Iniciar
      </button>
      <button 
        @click="stopScheduler" 
        :disabled="updating || !status.is_running"
      >
        Parar
      </button>

      <div>
        <h3>Horários Configurados:</h3>
        <ul>
          <li v-for="(time, idx) in status.restart_times" :key="idx">
            {{ time }}
          </li>
        </ul>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue';

const API_BASE_URL = 'http://localhost:3000/api';
const status = ref<SchedulerStatus | null>(null);
const loading = ref(true);
const error = ref<string | null>(null);
const updating = ref(false);

const fetchStatus = async () => {
  try {
    const response = await fetch(`${API_BASE_URL}/scheduler/status`);
    const data: ApiResponse<SchedulerStatus> = await response.json();
    
    if (data.success && data.data) {
      status.value = data.data;
    } else {
      error.value = data.error || 'Erro ao obter status';
    }
  } catch (err) {
    error.value = 'Erro de conexão';
  } finally {
    loading.value = false;
  }
};

const startScheduler = async () => {
  updating.value = true;
  try {
    const response = await fetch(`${API_BASE_URL}/scheduler/start`, {
      method: 'POST',
    });
    const data = await response.json();
    if (data.success) {
      await fetchStatus();
    }
  } catch (err) {
    console.error('Erro ao iniciar agendador:', err);
  } finally {
    updating.value = false;
  }
};

const stopScheduler = async () => {
  updating.value = true;
  try {
    const response = await fetch(`${API_BASE_URL}/scheduler/stop`, {
      method: 'POST',
    });
    const data = await response.json();
    if (data.success) {
      await fetchStatus();
    }
  } catch (err) {
    console.error('Erro ao parar agendador:', err);
  } finally {
    updating.value = false;
  }
};

const formatDate = (dateStr: string | null): string => {
  if (!dateStr) return '';
  return new Date(dateStr).toLocaleString('pt-BR');
};

onMounted(() => {
  fetchStatus();
  setInterval(fetchStatus, 30000); // Atualizar a cada 30s
});
</script>
```

---

### **JavaScript (Vanilla)**

```javascript
const API_BASE_URL = 'http://localhost:3000/api';

// Obter status do agendador
async function getSchedulerStatus() {
  try {
    const response = await fetch(`${API_BASE_URL}/scheduler/status`);
    const data = await response.json();
    
    if (data.success) {
      console.log('Status:', data.data);
      return data.data;
    } else {
      console.error('Erro:', data.error);
      return null;
    }
  } catch (error) {
    console.error('Erro de conexão:', error);
    return null;
  }
}

// Iniciar agendador
async function startScheduler() {
  try {
    const response = await fetch(`${API_BASE_URL}/scheduler/start`, {
      method: 'POST',
    });
    const data = await response.json();
    
    if (data.success) {
      console.log('Agendador iniciado:', data.message);
      return true;
    } else {
      console.error('Erro:', data.message || data.error);
      return false;
    }
  } catch (error) {
    console.error('Erro de conexão:', error);
    return false;
  }
}

// Parar agendador
async function stopScheduler() {
  try {
    const response = await fetch(`${API_BASE_URL}/scheduler/stop`, {
      method: 'POST',
    });
    const data = await response.json();
    
    if (data.success) {
      console.log('Agendador parado:', data.message);
      return true;
    } else {
      console.error('Erro:', data.error);
      return false;
    }
  } catch (error) {
    console.error('Erro de conexão:', error);
    return false;
  }
}

// Atualizar configuração
async function updateSchedulerConfig(config) {
  try {
    const response = await fetch(`${API_BASE_URL}/scheduler/config`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(config),
    });
    
    const data = await response.json();
    
    if (data.success) {
      console.log('Configuração atualizada:', data.message);
      return true;
    } else {
      console.error('Erro:', data.error);
      return false;
    }
  } catch (error) {
    console.error('Erro de conexão:', error);
    return false;
  }
}

// Obter logs
async function getSchedulerLogs(limit = 50) {
  try {
    const response = await fetch(`${API_BASE_URL}/scheduler/logs?limit=${limit}`);
    const data = await response.json();
    
    if (data.success) {
      console.log('Logs:', data.data.logs);
      return data.data.logs;
    } else {
      console.error('Erro:', data.error);
      return [];
    }
  } catch (error) {
    console.error('Erro de conexão:', error);
    return [];
  }
}

// Forçar reinicialização
async function forceRestart() {
  if (!confirm('Tem certeza que deseja forçar a reinicialização do servidor?')) {
    return false;
  }

  try {
    const response = await fetch(`${API_BASE_URL}/scheduler/force-restart`, {
      method: 'POST',
    });
    const data = await response.json();
    
    if (data.success) {
      console.log('Servidor reiniciado:', data.message);
      return true;
    } else {
      console.error('Erro:', data.error);
      return false;
    }
  } catch (error) {
    console.error('Erro de conexão:', error);
    return false;
  }
}
```

---

## ✅ Boas Práticas

### **1. Cache de Status**
- Implemente cache local para evitar requisições excessivas
- Atualize o cache a cada 30-60 segundos
- Use polling inteligente (aumente intervalo quando agendador está parado)

```typescript
// Exemplo de cache com intervalo adaptativo
const POLL_INTERVAL_RUNNING = 30000; // 30s quando rodando
const POLL_INTERVAL_STOPPED = 60000; // 60s quando parado

const interval = status?.is_running 
  ? POLL_INTERVAL_RUNNING 
  : POLL_INTERVAL_STOPPED;
```

### **2. Tratamento de Erros**
- Sempre verifique o campo `success` antes de usar os dados
- Trate erros de conexão separadamente de erros da API
- Exiba mensagens amigáveis ao usuário

```typescript
try {
  const response = await fetch(url);
  const data: ApiResponse<T> = await response.json();
  
  if (!data.success) {
    // Erro da API
    throw new Error(data.error || 'Erro desconhecido');
  }
  
  return data.data;
} catch (error) {
  if (error instanceof TypeError) {
    // Erro de conexão
    throw new Error('Erro de conexão com o servidor');
  }
  throw error;
}
```

### **3. Validação de Horários**
- Valide o formato "HH:MM" antes de enviar
- Use regex para validação: `/^([0-1]?[0-9]|2[0-3]):[0-5][0-9]$/`
- Mostre feedback imediato ao usuário

```typescript
function validateTime(time: string): boolean {
  const regex = /^([0-1]?[0-9]|2[0-3]):[0-5][0-9]$/;
  return regex.test(time);
}

function validateRestartTimes(times: string[]): boolean {
  return times.every(time => validateTime(time));
}
```

### **4. Loading States**
- Mostre estados de carregamento durante operações
- Desabilite botões durante requisições
- Use spinners ou skeleton screens para melhor UX

### **5. Confirmação de Ações Destrutivas**
- Sempre peça confirmação antes de `force-restart`
- Considere confirmação para parar o agendador
- Mostre impacto das ações (ex: "Servidor será reiniciado agora")

### **6. Formatação de Datas**
- Formate `next_restart` para exibição amigável
- Use timezone do usuário
- Mostre contagem regressiva quando relevante

```typescript
function formatNextRestart(nextRestart: string | null): string {
  if (!nextRestart) return 'N/A';
  
  const date = new Date(nextRestart);
  const now = new Date();
  const diff = date.getTime() - now.getTime();
  const hours = Math.floor(diff / (1000 * 60 * 60));
  const minutes = Math.floor((diff % (1000 * 60 * 60)) / (1000 * 60));
  
  if (diff < 0) return 'Já passou';
  if (hours > 0) return `Em ${hours}h ${minutes}m`;
  return `Em ${minutes}m`;
}
```

### **7. Debounce para Atualizações**
- Use debounce ao editar múltiplos horários
- Salve apenas quando usuário terminar de editar
- Evite requisições desnecessárias

### **8. Exibição de Logs**
- Pagine logs grandes
- Agrupe por tipo de evento
- Mostre timestamp formatado
- Filtre por tipo de evento quando necessário

---

## 📝 Checklist de Implementação

### **Funcionalidades Básicas**
- [ ] Exibir status do agendador (rodando/parado)
- [ ] Mostrar próximos horários de reinicialização
- [ ] Listar horários configurados
- [ ] Botões para iniciar/parar/reiniciar agendador

### **Configuração**
- [ ] Formulário para editar horários de reinicialização
- [ ] Adicionar/remover horários dinamicamente
- [ ] Validar formato de horários (HH:MM)
- [ ] Configurar minutos de notificação
- [ ] Salvar configuração e mostrar feedback

### **Visualização de Logs**
- [ ] Listar logs recentes
- [ ] Filtrar por tipo de evento
- [ ] Paginação de logs
- [ ] Formatação de timestamps

### **Controles Avançados**
- [ ] Botão para forçar reinicialização (com confirmação)
- [ ] Indicador visual de próximo restart
- [ ] Contagem regressiva até próximo restart
- [ ] Histórico de reinicializações

### **UX/UI**
- [ ] Estados de loading
- [ ] Mensagens de erro amigáveis
- [ ] Feedback de sucesso
- [ ] Confirmações para ações destrutivas
- [ ] Design responsivo

### **Otimizações**
- [ ] Cache de status
- [ ] Polling inteligente
- [ ] Debounce em edições
- [ ] Tratamento de erros robusto

---

## 🔄 Exemplo de Fluxo Completo

### **Cenário: Atualizar Horários de Reinicialização**

```typescript
// 1. Carregar configuração atual
const config = await fetch(`${API_BASE_URL}/scheduler/config`)
  .then(r => r.json())
  .then(data => data.data);

// 2. Permitir edição no frontend
// Usuário adiciona "23:00" e remove "01:00"

// 3. Validar antes de enviar
const newTimes = ["05:00", "09:00", "13:00", "17:00", "21:00", "23:00"];
const isValid = validateRestartTimes(newTimes);
if (!isValid) {
  alert('Formato de horário inválido');
  return;
}

// 4. Enviar atualização
const response = await fetch(`${API_BASE_URL}/scheduler/config`, {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ restart_times: newTimes }),
});

const result = await response.json();

// 5. Verificar resultado
if (result.success) {
  alert('Configuração atualizada com sucesso!');
  // Recarregar status para mostrar próximo restart atualizado
  await refreshStatus();
} else {
  alert(`Erro: ${result.error}`);
}
```

---

## 📚 Recursos Adicionais

- **Formato de Horário**: Sempre use "HH:MM" (ex: "01:00", "23:59")
- **Timezone**: O sistema usa o timezone configurado, mas você pode converter no frontend para exibição
- **Notificações**: Os minutos de notificação são relativos ao horário de restart
- **Force Restart**: Esta ação é imediata e não pode ser desfeita

---

## ⚠️ Observações Importantes

1. **Atualização Dinâmica**: Ao atualizar a configuração, o agendador é reiniciado automaticamente
2. **Formato de Horário**: Sempre valide o formato "HH:MM" antes de enviar
3. **Timezone**: O `next_restart` retorna em ISO 8601, converta para o timezone do usuário
4. **Force Restart**: Esta é uma ação crítica - sempre peça confirmação
5. **Status em Tempo Real**: Considere usar polling para atualizar o status periodicamente
6. **Erros Comuns**: 
   - "RestartScheduler não inicializado" = Backend não iniciou corretamente
   - "Nenhum horário configurado" = Configure horários antes de iniciar
   - "Formato inválido" = Use formato HH:MM (00:00 a 23:59)

---

**Última atualização**: 2025-11-01  
**Versão da API**: 1.12.0

