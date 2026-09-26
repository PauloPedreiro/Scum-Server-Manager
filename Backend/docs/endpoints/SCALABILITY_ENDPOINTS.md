# 🆕 Endpoints de Escalabilidade

## 📋 Visão Geral

Esta documentação descreve os novos endpoints implementados para funcionalidades de escalabilidade do SCUM Backend.

## 🆔 Identidade do Backend

### `GET /api/identity`

Obter identidade única do backend.

**Resposta:**
```json
{
  "success": true,
  "data": {
    "backend_id": "SCUM-BACKEND-ABC123456789",
    "owner_id": "OWNER-ABC-123",
    "created_at": "2025-01-15T10:30:00Z",
    "last_updated": "2025-01-15T10:30:00Z",
    "version": "1.0.0",
    "region": "america_south",
    "status": "registered",
    "capabilities": [
      "server_control",
      "scheduler",
      "notifications",
      "discord_webhooks"
    ]
  },
  "timestamp": 1760629995.398204
}
```

## 🔍 Health Check Detalhado

### `GET /api/health/detailed`

Health check completo para monitoramento central.

**Resposta:**
```json
{
  "backend_id": "SCUM-BACKEND-ABC123456789",
  "owner_id": "OWNER-ABC-123",
  "status": "healthy",
  "timestamp": 1760629995.398204,
  "components": {
    "server_manager": true,
    "restart_scheduler": true,
    "notification_manager": true,
    "discord_webhook": true,
    "backend_identity": true,
    "heartbeat_manager": true,
    "remote_command_handler": true,
    "license_validator": true
  },
  "server_status": {
    "is_running": true,
    "service_name": "SCUMServer",
    "port": 8900,
    "max_players": 64
  },
  "heartbeat_status": {
    "running": false,
    "last_heartbeat": null,
    "failures": 0,
    "interval": 60,
    "auto_register": false
  },
  "license_status": {
    "is_valid": true,
    "last_validation": "2025-01-15T10:30:00Z",
    "validation_failures": 0,
    "grace_period_active": false,
    "enabled": true
  }
}
```

## 🎮 Comandos Remotos

### `POST /api/remote/command`

Processar comando remoto do frontend central.

#### **Mensagem Global**

**Request:**
```json
{
  "type": "global_message",
  "message": "Mensagem para todos os jogadores",
  "duration": 30,
  "color": "255-255-100"
}
```

**Resposta:**
```json
{
  "success": true,
  "message": "Mensagem global enviada: Mensagem para todos os jogadores",
  "data": {
    "success": true,
    "message": "Notificação personalizada enviada com sucesso",
    "data": {
      "notifications_created": 1,
      "message": "Mensagem para todos os jogadores",
      "duration": 30,
      "color": "255-255-100"
    }
  }
}
```

#### **Controle do Servidor**

**Request:**
```json
{
  "type": "server_control",
  "action": "restart",
  "force": false,
  "wait_timeout": 30
}
```

**Ações disponíveis:**
- `start` - Iniciar servidor
- `stop` - Parar servidor
- `restart` - Reiniciar servidor

**Resposta:**
```json
{
  "success": true,
  "message": "Servidor restart executado",
  "data": {
    "success": true,
    "message": "Servidor reiniciado com sucesso",
    "status": "restarted"
  }
}
```

#### **Controle do Scheduler**

**Request:**
```json
{
  "type": "scheduler_control",
  "action": "restart"
}
```

**Ações disponíveis:**
- `start` - Iniciar scheduler
- `stop` - Parar scheduler
- `restart` - Reiniciar scheduler

#### **Solicitação de Status**

**Request:**
```json
{
  "type": "status_request"
}
```

**Resposta:**
```json
{
  "success": true,
  "message": "Status obtido com sucesso",
  "data": {
    "timestamp": 1760629995.398204,
    "server": {
      "is_running": true,
      "service_name": "SCUMServer",
      "port": 8900,
      "max_players": 64
    },
    "scheduler": {
      "is_running": true,
      "next_restart": "2025-01-16T01:00:00Z",
      "restart_times": ["01:00", "02:00", "03:00"]
    },
    "notifications": {
      "enabled": true,
      "active_count": 5,
      "last_sent": "2025-01-15T10:30:00Z"
    }
  }
}
```

#### **Controle de Notificações**

**Request:**
```json
{
  "type": "notification_control",
  "action": "clear"
}
```

**Ações disponíveis:**
- `clear` - Limpar notificações
- `create_restart` - Criar notificações de restart

## 👤 Informações do Proprietário

### `GET /api/owner/info`

Obter informações do proprietário.

**Resposta:**
```json
{
  "success": true,
  "data": {
    "owner_id": "OWNER-ABC-123",
    "owner_name": "João Silva",
    "email": "joao@email.com",
    "region": "america_south",
    "server_name": "Servidor do João",
    "license_type": "individual",
    "max_servers": 1,
    "features": [
      "server_control",
      "scheduler",
      "notifications",
      "discord_webhooks"
    ],
    "created_at": "2025-01-15T10:30:00Z",
    "last_updated": "2025-01-15T10:30:00Z"
  },
  "timestamp": 1760629995.398204
}
```

### `POST /api/owner/info`

Atualizar informações do proprietário.

**Request:**
```json
{
  "owner_name": "João Silva",
  "email": "joao@email.com",
  "region": "america_south",
  "owner_id": "OWNER-ABC-123"
}
```

**Resposta:**
```json
{
  "success": true,
  "message": "Informações do proprietário atualizadas",
  "data": {
    "owner_id": "OWNER-ABC-123",
    "owner_name": "João Silva",
    "region": "america_south"
  }
}
```

## 🔧 Configuração

### **Modo Individual (Padrão)**

```json
{
  "communication": {
    "auto_register": false,
    "heartbeat_interval": 60
  }
}
```

**Características:**
- ✅ Todas as funcionalidades atuais mantidas
- ✅ Backend ID gerado automaticamente
- ✅ Heartbeat desabilitado
- ✅ Comandos remotos disponíveis localmente

### **Modo Escalável (Futuro)**

```json
{
  "communication": {
    "auto_register": true,
    "frontend_url": "https://seu-frontend-central.com",
    "api_key": "chave-real-do-frontend"
  }
}
```

**Características:**
- ✅ Registro automático no frontend central
- ✅ Heartbeat ativo
- ✅ Comandos remotos do frontend central
- ✅ Validação de licença

## 🧪 Testes

### **Testar Endpoints**

```bash
# Testar identidade
curl http://localhost:3000/api/identity

# Testar health check detalhado
curl http://localhost:3000/api/health/detailed

# Testar comando remoto
curl -X POST http://localhost:3000/api/remote/command \
  -H "Content-Type: application/json" \
  -d '{"type": "status_request"}'
```

### **Script de Teste Automatizado**

```bash
python test_scalability.py
```

## 📊 Monitoramento

### **Logs de Escalabilidade**

```
[INFO] Backend ID: SCUM-BACKEND-ABC123456789
[INFO] OwnerManager inicializado
[INFO] Sistema de heartbeat inicializado
[INFO] RemoteCommandHandler inicializado
[INFO] LicenseValidator inicializado
[INFO] Sistema de escalabilidade inicializado com sucesso
```

### **Status do Heartbeat**

```json
{
  "running": false,
  "last_heartbeat": null,
  "failures": 0,
  "interval": 60,
  "auto_register": false
}
```

## 🚀 Próximos Passos

1. **Desenvolver frontend central**
2. **Implementar comunicação real**
3. **Sistema de autenticação**
4. **Dashboard multi-tenant**
5. **Escala global**

---

**Última atualização**: 15/01/2025  
**Versão**: 1.0.0  
**Status**: Implementado ✅
