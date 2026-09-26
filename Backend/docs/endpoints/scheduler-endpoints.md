# 🕐 **Sistema de Agendamento - SCUM Backend**

Documentação completa do sistema de agendamento de reinicializações automáticas.

## 📋 **Visão Geral**

O sistema de agendamento permite configurar reinicializações automáticas do servidor SCUM em horários específicos, com notificações prévias e logs detalhados.

### **Funcionalidades:**
- ✅ **Reinicializações automáticas** em horários configuráveis
- ✅ **Notificações prévias** (5min e 1min antes)
- ✅ **Logs detalhados** de todas as operações
- ✅ **API REST** para controle completo
- ✅ **Configuração dinâmica** via API
- ✅ **Reinicialização forçada** imediata

---

## ⚙️ **Configuração**

### **Arquivo `data/config.json`**
```json
{
  "scheduler": {
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
    "notification_minutes": [5, 1],
    "timezone": "America/Sao_Paulo"
  }
}
```

### **Parâmetros:**
- **`enabled`** (boolean): Habilita/desabilita o agendador
- **`auto_start`** (boolean): Inicia automaticamente com o backend
- **`restart_times`** (array): Lista de horários no formato "HH:MM"
- **`notification_minutes`** (array): Minutos antes para notificar
- **`timezone`** (string): Fuso horário (futuro)

---

## 🔌 **API Endpoints**

### **Base URL**
```
http://localhost:3000
```

---

## 📊 **Status do Agendador**

### **Endpoint**
```
GET /api/scheduler/status
```

### **Resposta de Sucesso (200)**
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
    "next_restart": "2025-10-17T01:00:00",
    "notification_minutes": [5, 1],
    "scheduled_jobs": 8,
    "logs_count": 15
  },
  "timestamp": 1760629995.398204
}
```

### **Exemplo de Uso**
```bash
curl http://localhost:3000/api/scheduler/status
```

---

## 🚀 **Iniciar Agendador**

### **Endpoint**
```
POST /api/scheduler/start
```

### **Resposta de Sucesso (200)**
```json
{
  "success": true,
  "message": "Agendador iniciado com sucesso",
  "status": "started",
  "data": {
    "restart_times": ["01:00", "05:00", "09:00", "13:00", "17:00", "21:00"],
    "next_restart": "2025-10-17T01:00:00",
    "notification_minutes": [5, 1]
  }
}
```

### **Resposta de Erro (400)**
```json
{
  "success": false,
  "message": "Nenhum horário de reinicialização configurado",
  "status": "no_times_configured"
}
```

### **Exemplo de Uso**
```bash
curl -X POST http://localhost:3000/api/scheduler/start
```

---

## 🛑 **Parar Agendador**

### **Endpoint**
```
POST /api/scheduler/stop
```

### **Resposta de Sucesso (200)**
```json
{
  "success": true,
  "message": "Agendador parado com sucesso",
  "status": "stopped"
}
```

### **Exemplo de Uso**
```bash
curl -X POST http://localhost:3000/api/scheduler/stop
```

---

## 🔄 **Reiniciar Agendador**

### **Endpoint**
```
POST /api/scheduler/restart
```

### **Resposta de Sucesso (200)**
```json
{
  "success": true,
  "message": "Agendador reiniciado com sucesso",
  "status": "restarted"
}
```

### **Exemplo de Uso**
```bash
curl -X POST http://localhost:3000/api/scheduler/restart
```

---

## 📝 **Logs do Agendador**

### **Endpoint**
```
GET /api/scheduler/logs?limit=50
```

### **Query Parameters**
- **`limit`** (integer, opcional): Número máximo de logs (padrão: 50)

### **Resposta de Sucesso (200)**
```json
{
  "success": true,
  "data": {
    "logs": [
      {
        "timestamp": "2025-10-16T15:30:00.123456",
        "event_type": "scheduler_started",
        "message": "Agendador iniciado com sucesso",
        "data": {
          "restart_times": ["01:00", "05:00", "09:00", "13:00", "17:00", "21:00"],
          "next_restart": "2025-10-17T01:00:00",
          "notification_minutes": [5, 1]
        }
      },
      {
        "timestamp": "2025-10-16T15:30:05.654321",
        "event_type": "restart_scheduled",
        "message": "Reinicialização agendada para 01:00",
        "data": {}
      }
    ],
    "count": 2,
    "limit": 50
  },
  "timestamp": 1760629995.398204
}
```

### **Exemplo de Uso**
```bash
curl "http://localhost:3000/api/scheduler/logs?limit=20"
```

---

## ⚙️ **Configuração do Agendador**

### **Obter Configuração**
```
GET /api/scheduler/config
```

### **Resposta de Sucesso (200)**
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
    "notification_minutes": [5, 1],
    "timezone": "America/Sao_Paulo"
  },
  "timestamp": 1760629995.398204
}
```

### **Atualizar Configuração**
```
POST /api/scheduler/config
Content-Type: application/json
```

### **Body**
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

### **Resposta de Sucesso (200)**
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

### **Resposta de Erro (400)**
```json
{
  "success": false,
  "error": "Formato de horário inválido: 25:00. Use HH:MM"
}
```

### **Exemplo de Uso**
```bash
curl -X POST http://localhost:3000/api/scheduler/config \
  -H "Content-Type: application/json" \
  -d '{
    "restart_times": ["02:00", "06:00", "10:00", "14:00", "18:00", "22:00"],
    "notification_minutes": [10, 5, 1]
  }'
```

---

## ⚡ **Reinicialização Forçada**

### **Endpoint**
```
POST /api/scheduler/force-restart
```

### **Resposta de Sucesso (200)**
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

### **Exemplo de Uso**
```bash
curl -X POST http://localhost:3000/api/scheduler/force-restart
```

---

## 📊 **Tipos de Eventos**

### **Eventos do Agendador**
- **`scheduler_started`** - Agendador iniciado
- **`scheduler_stopped`** - Agendador parado
- **`config_updated`** - Configuração atualizada
- **`restart_scheduled`** - Reinicialização agendada
- **`notification_scheduled`** - Notificação agendada
- **`notification`** - Notificação enviada
- **`restart_started`** - Reinicialização iniciada
- **`restart_success`** - Reinicialização bem-sucedida
- **`restart_failed`** - Falha na reinicialização
- **`force_restart`** - Reinicialização forçada

---

## 🧪 **Exemplos de Uso**

### **Python**
```python
import requests

# Status do agendador
response = requests.get('http://localhost:3000/api/scheduler/status')
print(response.json())

# Configurar novos horários
new_config = {
    "restart_times": ["02:00", "06:00", "10:00", "14:00", "18:00", "22:00"],
    "notification_minutes": [10, 5, 1]
}
response = requests.post('http://localhost:3000/api/scheduler/config', json=new_config)
print(response.json())

# Forçar reinicialização
response = requests.post('http://localhost:3000/api/scheduler/force-restart')
print(response.json())
```

### **JavaScript**
```javascript
// Status do agendador
const status = await fetch('http://localhost:3000/api/scheduler/status').then(r => r.json());
console.log(status);

// Atualizar configuração
const config = {
    restart_times: ["02:00", "06:00", "10:00", "14:00", "18:00", "22:00"],
    notification_minutes: [10, 5, 1]
};
const result = await fetch('http://localhost:3000/api/scheduler/config', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(config)
}).then(r => r.json());
console.log(result);
```

### **PowerShell**
```powershell
# Status do agendador
Invoke-RestMethod -Uri "http://localhost:3000/api/scheduler/status" -Method GET

# Iniciar agendador
Invoke-RestMethod -Uri "http://localhost:3000/api/scheduler/start" -Method POST

# Atualizar configuração
$config = @{
    restart_times = @("02:00", "06:00", "10:00", "14:00", "18:00", "22:00")
    notification_minutes = @(10, 5, 1)
} | ConvertTo-Json

Invoke-RestMethod -Uri "http://localhost:3000/api/scheduler/config" -Method POST -ContentType "application/json" -Body $config
```

---

## 🔧 **Troubleshooting**

### **Agendador não inicia**
- Verificar se `enabled: true` no config
- Verificar se há horários configurados
- Verificar logs para erros específicos

### **Reinicializações não acontecem**
- Verificar se agendador está rodando
- Verificar se horários estão corretos
- Verificar logs do agendador
- Verificar se servidor está acessível

### **Notificações não funcionam**
- Verificar configuração de `notification_minutes`
- Verificar se callbacks estão registrados
- Verificar logs de notificação

### **Configuração não salva**
- Verificar permissões de escrita no arquivo
- Verificar formato JSON válido
- Verificar logs de erro

---

## 📈 **Monitoramento**

### **Verificar Status**
```bash
# Status geral
curl http://localhost:3000/api/scheduler/status

# Logs recentes
curl "http://localhost:3000/api/scheduler/logs?limit=10"

# Próxima reinicialização
curl http://localhost:3000/api/scheduler/status | jq '.data.next_restart'
```

### **Script de Monitoramento**
```bash
#!/bin/bash
while true; do
  echo "=== $(date) ==="
  
  # Status do agendador
  status=$(curl -s http://localhost:3000/api/scheduler/status | jq -r '.data.is_running')
  echo "Agendador rodando: $status"
  
  # Próxima reinicialização
  next=$(curl -s http://localhost:3000/api/scheduler/status | jq -r '.data.next_restart')
  echo "Próxima reinicialização: $next"
  
  # Último log
  last_log=$(curl -s "http://localhost:3000/api/scheduler/logs?limit=1" | jq -r '.data.logs[0].message // "Nenhum log"')
  echo "Último evento: $last_log"
  
  echo "---"
  sleep 60
done
```

---

## ⚠️ **Notas Importantes**

### **Horários**
- Formato: "HH:MM" (24 horas)
- Exemplo: "01:00", "13:30", "23:59"
- Validação automática de formato

### **Notificações**
- Configurável em minutos antes
- Exemplo: [5, 1] = notifica 5min e 1min antes
- Callbacks para integração externa

### **Logs**
- Mantém últimos 100 eventos
- Formato JSON estruturado
- Timestamps ISO 8601

### **Threading**
- Agendador roda em thread separada
- Não bloqueia API principal
- Shutdown graceful

---

**Documentação atualizada em: 16/10/2025**  
**Versão da API: 1.0.0**
