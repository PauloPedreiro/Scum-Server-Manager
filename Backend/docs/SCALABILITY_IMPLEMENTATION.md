# 🚀 SCUM Backend - Implementação de Escalabilidade

## 📋 Visão Geral

Este documento descreve a implementação de funcionalidades de escalabilidade no SCUM Backend, permitindo que o sistema seja preparado para controle centralizado de múltiplos servidores.

## 🏗️ Arquitetura Implementada

### **Estrutura de Módulos**

```
core/
├── identity/                    # 🆕 Módulo de Identidade
│   ├── __init__.py
│   ├── backend_id.py           # Geração de Backend ID único
│   └── owner_manager.py        # Gerenciamento do proprietário
├── communication/              # 🆕 Módulo de Comunicação
│   ├── __init__.py
│   ├── heartbeat_manager.py    # Sistema de heartbeat
│   ├── remote_commands.py      # Comandos remotos
│   └── license_validator.py   # Validação de licença
├── server_control/            # Módulos existentes
├── scheduler/
├── notifications/
└── webhooks/
```

### **Arquivos de Dados**

```
data/
├── config.json                # ✅ Expandido com campos de escalabilidade
├── identity.json              # 🆕 Identidade única do backend
├── webhooks.json             # Existente
└── logs/                     # Existente
```

## 🔧 Configuração Expandida

### **Novos Campos no config.json**

```json
{
  "communication": {
    "frontend_url": "https://your-frontend.com",
    "api_key": "your-api-key-here",
    "webhook_url": "https://discord.com/api/webhooks/...",
    "timeout": 30,
    "retry_attempts": 3,
    "retry_delay": 5000,
    
    // 🆕 CAMPOS DE ESCALABILIDADE
    "backend_id": null,                    // Será gerado automaticamente
    "owner_id": null,                      // Será definido no registro
    "server_name": "Meu Servidor SCUM",   // Nome do servidor
    "region": "america_south",            // Região do servidor
    "auto_register": false,               // Modo individual por padrão
    "heartbeat_interval": 60,             // Intervalo de heartbeat (segundos)
    "license_validation": {               // Validação de licença
      "enabled": true,
      "check_interval": 3600,             // Verificar a cada 1h
      "grace_period": 86400               // Período de graça de 24h
    }
  }
}
```

## 🆔 Sistema de Identidade

### **BackendIdentity**

Gerencia a identidade única do backend:

```python
from core.identity.backend_id import BackendIdentity

# Inicializar
identity = BackendIdentity()

# Obter informações
backend_id = identity.get_backend_id()
owner_id = identity.get_owner_id()
is_registered = identity.is_registered()

# Atualizar
identity.set_owner_id("OWNER-ABC-123")
identity.set_region("america_south")
```

### **OwnerManager**

Gerencia informações do proprietário:

```python
from core.identity.owner_manager import OwnerManager

# Inicializar
owner = OwnerManager()

# Definir proprietário
owner.set_owner_info(
    owner_id="OWNER-ABC-123",
    owner_name="João Silva",
    email="joao@email.com",
    region="america_south"
)

# Obter informações
info = owner.get_owner_info()
server_name = owner.get_server_name()
```

## 🔄 Sistema de Comunicação

### **HeartbeatManager**

Sistema de heartbeat para comunicação com frontend central:

```python
from core.communication.heartbeat_manager import HeartbeatManager

# Inicializar
heartbeat = HeartbeatManager(config, logger, backend_identity)

# Iniciar heartbeat (só funciona se auto_register=true)
heartbeat.start_heartbeat()

# Obter status
status = heartbeat.get_heartbeat_status()
```

### **RemoteCommandHandler**

Processa comandos remotos do frontend central:

```python
from core.communication.remote_commands import RemoteCommandHandler

# Inicializar
handler = RemoteCommandHandler(logger, notification_manager, server_manager, scheduler)

# Processar comando
result = handler.handle_command({
    "type": "global_message",
    "message": "Mensagem global",
    "duration": 30
})
```

### **LicenseValidator**

Valida licença com frontend central:

```python
from core.communication.license_validator import LicenseValidator

# Inicializar
validator = LicenseValidator(config, logger, backend_identity)

# Validar licença
is_valid = validator.validate_license()

# Obter status
status = validator.get_license_status()
```

## 🌐 Novos Endpoints da API

### **1. Identidade do Backend**

#### `GET /api/identity`
Obter identidade completa do backend.

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

### **2. Comandos Remotos**

#### `POST /api/remote/command`
Processar comando remoto do frontend central.

**Tipos de Comandos Suportados:**

##### Mensagem Global
```json
{
  "type": "global_message",
  "message": "Mensagem para todos os jogadores",
  "duration": 30,
  "color": "255-255-100"
}
```

##### Controle do Servidor
```json
{
  "type": "server_control",
  "action": "start|stop|restart",
  "force": false,
  "wait_timeout": 30
}
```

##### Controle do Scheduler
```json
{
  "type": "scheduler_control",
  "action": "start|stop|restart"
}
```

##### Solicitação de Status
```json
{
  "type": "status_request"
}
```

##### Controle de Notificações
```json
{
  "type": "notification_control",
  "action": "clear|create_restart"
}
```

### **3. Health Check Detalhado**

#### `GET /api/health/detailed`
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

### **4. Informações do Proprietário**

#### `GET /api/owner/info`
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

#### `POST /api/owner/info`
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

## 🔄 Modos de Operação

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
- ✅ Zero impacto no comportamento atual

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
- ✅ Sincronização de status

## 🛠️ Scripts de Apoio

### **1. Migração Automática**

```bash
python migrate_to_scalable.py
```

**Funcionalidades:**
- ✅ Backup da configuração atual
- ✅ Adição de campos de escalabilidade
- ✅ Criação de arquivo de identidade
- ✅ Verificação da migração

### **2. Testes de Compatibilidade**

```bash
python test_scalability.py
```

**Testes Incluídos:**
- ✅ Funcionalidades existentes
- ✅ Novos endpoints
- ✅ Comandos remotos
- ✅ Health checks

## 📊 Monitoramento e Logs

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

## 🚀 Próximos Passos para Escala

### **Fase 1: Frontend Central**
1. Desenvolver frontend central
2. Implementar autenticação/autorização
3. Sistema de registro de proprietários
4. Dashboard multi-tenant

### **Fase 2: Comunicação Real**
1. Implementar comunicação HTTP real
2. Sistema de WebSockets
3. Validação de licenças
4. Sincronização de dados

### **Fase 3: Escala Global**
1. Sistema de regiões
2. Mensagens globais/regionais
3. Analytics centralizados
4. Monitoramento global

## 🔒 Segurança

### **Autenticação**
- Backend ID único por instância
- API Key para comunicação
- Validação de licença periódica
- Grace period para falhas de rede

### **Autorização**
- Proprietários controlam apenas seus servidores
- Admin global pode controlar todos
- Comandos remotos com validação
- Logs de auditoria

## 📈 Vantagens da Implementação

### **Compatibilidade Total**
- ✅ Zero impacto nas funcionalidades atuais
- ✅ Modo individual mantido por padrão
- ✅ Migração opcional e reversível
- ✅ Testes de compatibilidade incluídos

### **Escalabilidade Preparada**
- ✅ Estrutura modular
- ✅ Identificação única
- ✅ Sistema de comunicação
- ✅ Comandos remotos
- ✅ Monitoramento avançado

### **Flexibilidade**
- ✅ Modo individual ou escalável
- ✅ Configuração por proprietário
- ✅ Suporte a múltiplas regiões
- ✅ Extensibilidade futura

---

**Última atualização**: 15/01/2025  
**Versão**: 1.0.0  
**Status**: Implementado e Testado ✅
