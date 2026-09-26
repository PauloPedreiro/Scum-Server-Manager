# 📡 **API Endpoints - SCUM Backend**

Documentação completa dos endpoints da API REST do SCUM Backend.

## **Base URL**
```
http://localhost:3000
```

## **Índice**

- [Health Check](#health-check)
- [Sistema de Autenticação](#sistema-de-autenticação)
- [Status do Servidor](#status-do-servidor)
- [Iniciar Servidor](#iniciar-servidor)
- [Parar Servidor](#parar-servidor)
- [Reiniciar Servidor](#reiniciar-servidor)
- [Obter Logs](#obter-logs)
- [Sistema de Notificações](#sistema-de-notificações)
- [Sistema de Admin Logs](#sistema-de-admin-logs)
- [Sistema de Deduplicação](#sistema-de-deduplicação)
- [Sistema de Precisão de Horário](#sistema-de-precisão-de-horário)
- [Sistema de Permissões de Jogadores](#sistema-de-permissões-de-jogadores)
- [Sistema de Fama dos Jogadores](#sistema-de-fama-dos-jogadores)
- [Sistema de Atributos (SCUM.db)](#sistema-de-atributos-scumdb)
- [Sistema de Rankings](#sistema-de-rankings)
- [Sistema de Configurações do Servidor](#sistema-de-configurações-do-servidor)
- [Sistema de Configuração (config.json)](#sistema-de-configuração-configjson)
- [Sistema de Webhooks (webhooks.json)](#sistema-de-webhooks-webhooksjson)
- [Sistema de Verificação de Veículos](#sistema-de-verificação-de-veículos)
- [Sistema de GPS](#sistema-de-gps)
- [Shop / Economy / Mailbox](./SHOP_ENDPOINTS.md)
- [Shop / Economy / Mailbox (Frontend)](./SHOP_FRONTEND_ENDPOINTS.md)
- [Sistema de Sincronização com Gestão](#sistema-de-sincronização-com-gestão)
- [Códigos de Status](#códigos-de-status)
- [Exemplos de Uso](#exemplos-de-uso)

---

## **Health Check**

Verifica a saúde da aplicação e status dos componentes.

### **Endpoint**
```
GET /api/health
```

### **Headers**
```
Nenhum necessário
```

### **Body**
```
Vazio
```

### **Resposta de Sucesso (200)**
```json
{
  "status": "healthy",
  "timestamp": 1760629995.398204,
  "components": {
    "server_manager": true,
    "logger": true,
    "config": true
  }
}
```

### **Resposta de Erro (500)**
```json
{
  "status": "unhealthy",
  "error": "Erro específico",
  "timestamp": 1760629995.398204
}
```

### **Exemplo de Uso**
```bash
curl http://localhost:3000/api/health
```

---

## **Sistema de Autenticação**

Sistema de autenticação JWT para proteger o painel de administração do backend. Suporta múltiplos usuários (admin e moderadores) com vinculação opcional à tabela `players`.

### **Endpoints Disponíveis**

#### **Login**
```
POST /api/auth/login
```

Realiza login do usuário. Retorna token JWT ou flag `must_change_password` se for primeiro login.

**Request Body:**
```json
{
  "username": "admin",
  "password": "12345678910"
}
```

**Response (200) - Primeiro Login:**
```json
{
  "success": true,
  "data": {
    "must_change_password": true,
    "message": "Please change your password"
  }
}
```

**Response (200) - Login Normal:**
```json
{
  "success": true,
  "data": {
    "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "username": "admin",
    "role": "admin_pending",
    "must_link_discord": true,
    "expires_in": 86400
  }
}
```

**Response (401) - Credenciais Inválidas:**
```json
{
  "success": false,
  "error": "Invalid credentials"
}
```

#### **Mudar Senha**
```
POST /api/auth/change-password
```

Muda a senha do usuário. Pode ser usado no primeiro login (sem token) ou após autenticação (com token).

**Headers (opcional - se já tiver token):**
```
Authorization: Bearer <token>
```

**Request Body:**
```json
{
  "username": "admin",
  "current_password": "12345678910",
  "new_password": "NovaSenhaSegura123!"
}
```

**Response (200):**
```json
{
  "success": true,
  "data": {
    "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "message": "Password changed successfully",
    "password_changed": true,
    "role": "admin_pending",
    "must_link_discord": true,
    "expires_in": 86400
  }
}
```

**Response (400) - Senha Atual Incorreta:**
```json
{
  "success": false,
  "error": "Current password is incorrect"
}
```

#### **Gerar Codigo de Vinculacao Discord (Admin)**
```
POST /api/auth/discord-link-code
```

Gera um codigo one-time para vinculacao do admin com a conta Discord. O admin deve copiar e colar no canal `log-ssm`:

```
!link SSM-LINK-XXXXXX
```

**Headers:**
```
Authorization: Bearer <token>
```

**Response (200):**
```json
{
  "success": true,
  "data": {
    "code": "SSM-LINK-1A2B3C",
    "expires_in_minutes": 10,
    "command": "!link SSM-LINK-1A2B3C"
  }
}
```

#### **Obter Usuário Atual**
```
GET /api/auth/me
```

Obtém dados do usuário autenticado atual. Requer autenticação.

**Headers:**
```
Authorization: Bearer <token>
```

**Response (200):**
```json
{
  "success": true,
  "data": {
    "id": 1,
    "username": "admin",
    "role": "admin_pending",
    "password_changed": true,
    "discord_user_id": null,
    "must_link_discord": true,
    "steam_id": null,
    "player_name": null,
    "last_login": "2025-12-04T20:00:00"
  }
}
```

**Response (200) - Moderador Vinculado:**
```json
{
  "success": true,
  "data": {
    "id": 2,
    "username": "moderador1",
    "role": "moderator",
    "password_changed": true,
    "steam_id": "76561198012345678",
    "player_name": "PlayerName",
    "player_id": 12345,
    "last_login": "2025-12-04T19:00:00"
  }
}
```

#### **Logout**
```
POST /api/auth/logout
```

Logout do usuário. Com JWT, logout é apenas do lado do cliente (remover token).

**Headers:**
```
Authorization: Bearer <token>
```

**Response (200):**
```json
{
  "success": true,
  "message": "Logged out successfully"
}
```

#### **Criar Usuário (Admin Apenas)**
```
POST /api/auth/users
```

Cria um novo usuário. Apenas admins podem criar usuários.

**Headers:**
```
Authorization: Bearer <token>
Content-Type: application/json
```

**Request Body (sem vinculação):**
```json
{
  "username": "moderador1",
  "password": "senha_temporaria123",
  "role": "moderator"
}
```

**Request Body (com vinculação a player):**
```json
{
  "username": "moderador1",
  "password": "senha_temporaria123",
  "role": "moderator",
  "steam_id": "76561198012345678"
}
```

**Response (201):**
```json
{
  "success": true,
  "data": {
    "id": 2,
    "username": "moderador1",
    "role": "moderator",
    "is_active": true,
    "password_changed": false,
    "steam_id": "76561198012345678",
    "player_name": "PlayerName",
    "created_at": "2025-12-04T20:00:00",
    "message": "User created. Password must be changed on first login."
  }
}
```

**Nota:** Usuário criado com `password_changed = false` - será forçado a mudar a senha no primeiro login.

#### **Listar Usuários (Admin Apenas)**
```
GET /api/auth/users
```

Lista todos os usuários. Apenas admins podem acessar.

**Headers:**
```
Authorization: Bearer <token>
```

**Response (200):**
```json
{
  "success": true,
  "data": {
    "users": [
      {
        "id": 1,
        "username": "admin",
        "role": "admin_pending",
        "is_active": true,
        "password_changed": true,
        "steam_id": null,
        "player_name": null,
        "last_login": "2025-12-04T20:00:00",
        "created_at": "2025-12-04T18:00:00"
      },
      {
        "id": 2,
        "username": "moderador1",
        "role": "moderator",
        "is_active": true,
        "password_changed": true,
        "steam_id": "76561198012345678",
        "player_name": "PlayerName",
        "last_login": "2025-12-04T19:00:00",
        "created_at": "2025-12-04T19:00:00"
      }
    ],
    "total": 2
  }
}
```

#### **Atualizar Usuário (Admin Apenas)**
```
PUT /api/auth/users/<id>
```

Atualiza um usuário. Apenas admins podem atualizar usuários.

**Headers:**
```
Authorization: Bearer <token>
Content-Type: application/json
```

**Request Body:**
```json
{
  "is_active": false,
  "role": "moderator",
  "steam_id": "76561198012345678"
}
```

**Response (200):**
```json
{
  "success": true,
  "data": {
    "id": 2,
    "username": "moderador1",
    "role": "moderator",
    "is_active": false,
    "steam_id": "76561198012345678",
    "updated_at": "2025-12-04T20:00:00"
  }
}
```

#### **Deletar Usuário (Admin Apenas)**
```
DELETE /api/auth/users/<id>
```

Deleta um usuário. Não permite deletar usuário admin. Apenas admins podem deletar usuários.

**Headers:**
```
Authorization: Bearer <token>
```

**Response (200):**
```json
{
  "success": true,
  "message": "User deleted successfully"
}
```

**Response (400) - Tentar Deletar Admin:**
```json
{
  "success": false,
  "error": "Cannot delete admin user"
}
```

#### **Buscar Players (Admin Apenas)**
```
GET /api/auth/users/search-players?q=nome&limit=20
```

Busca players para vincular a moderadores. Apenas admins podem acessar.

**Headers:**
```
Authorization: Bearer <token>
```

**Query Parameters:**
- `q` (string, obrigatório): Termo de busca (nome ou steam_id)
- `limit` (integer, opcional): Limite de resultados (padrão: 20)

**Response (200):**
```json
{
  "success": true,
  "data": {
    "players": [
      {
        "steam_id": "76561198012345678",
        "name": "PlayerName",
        "id": 12345
      }
    ],
    "total": 1
  }
}
```

### **🔒 Autenticação**

Todos os endpoints protegidos requerem o header:
```
Authorization: Bearer <token>
```

O token JWT tem validade de 24 horas.

### **📝 Notas Importantes**

1. **Usuário Admin Padrão**: Criado automaticamente na primeira execução:
   - Username: `admin`
   - Password: `12345678910`
   - **Obrigatório** mudar senha no primeiro login

2. **Mudança de Senha Obrigatória**: Todos os usuários (admin e moderadores) devem mudar a senha no primeiro login.

3. **Vinculação com Players**: Moderadores podem ser vinculados à tabela `players` via `steam_id` para mostrar informações do jogador no painel.

4. **Roles**: 
   - `admin`: Acesso total (apenas quando `discord_user_id` estiver vinculado)
   - `admin_pending`: Admin pendente de vinculacao Discord (login permitido, rotas admin bloqueadas)
   - `moderator`: Acesso limitado (pode ser expandido no futuro)

5. **Segurança**: 
   - Senhas armazenadas com hash bcrypt (12 rounds)
   - Tokens JWT com expiração
   - Validação de força de senha (mínimo 8 caracteres)

#### **Recuperação de Senha**
```
POST /api/auth/request-password-reset
POST /api/auth/reset-password
```

Sistema de recuperação de senha que envia tokens unicos via **DM do Discord** para admins que ja estejam vinculados (`discord_user_id`).

Se o admin ainda nao estiver vinculado ao Discord, nao ha como entregar o token via DM.

**📚 Documentação Completa**: [RECUPERACAO_SENHA_API.md](./RECUPERACAO_SENHA_API.md) - Documentação completa para desenvolvedor frontend com exemplos TypeScript/React

---

## 📊 **Status do Servidor**

Obtém informações detalhadas sobre o status do servidor SCUM.

### **Endpoint**
```
GET /api/server/status
```

### **Headers**
```
Nenhum necessário
```

### **Body**
```
Vazio
```

### **Resposta de Sucesso (200)**
```json
{
  "success": true,
  "data": {
    "is_running": false,
    "service_name": "SCUMServer",
    "service_info": {
      "NOME_DO_SERVIÇO": "SCUMServer",
      "TIPO": "10  WIN32_OWN_PROCESS",
      "ESTADO": "1  STOPPED",
      "CÓDIGO_DE_SAÍDA_DO_WIN32": "0  (0x0)",
      "CÓDIGO_DE_SAÍDA_DO_SERVIÇO": "0  (0x0)",
      "PONTO_DE_VERIFICAÇÃO": "0x0",
      "AGUARDAR_DICA": "0x0"
    },
    "server_path": "C:\\Servers\\Scum\\SCUM\\Binaries\\Win64",
    "steamcmd_path": "C:\\Servers\\steamcmd",
    "install_path": "C:\\Servers\\Scum",
    "nssm_path": "nssm-2.24\\win64\\nssm.exe",
    "port": 8900,
    "max_players": 64,
    "use_battleye": true,
    "last_check": 1760629995.398204
  },
  "timestamp": 1760629995.398204
}
```

### **Resposta de Erro (500)**
```json
{
  "success": false,
  "error": "Erro específico"
}
```

### **Exemplo de Uso**
```bash
curl http://localhost:3000/api/server/status
```

---

## 🚀 **Iniciar Servidor**

Inicia o servidor SCUM com atualização SteamCMD automática.

### **Endpoint**
```
POST /api/server/start
```

### **Headers**
```
Content-Type: application/json
```

### **Body**
```json
{
  "force": false,
  "wait_timeout": 30
}
```

### **Parâmetros**
- **`force`** (boolean, opcional): Força início mesmo se já estiver rodando
- **`wait_timeout`** (integer, opcional): Tempo de espera para confirmação (segundos)

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

### **Resposta de Erro (400)**
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

### **Exemplo de Uso**
```bash
curl -X POST http://localhost:3000/api/server/start \
  -H "Content-Type: application/json" \
  -d '{"force": false, "wait_timeout": 30}'
```

### **Processo Executado**
1. ✅ Verifica se serviço já está rodando
2. ✅ Executa atualização SteamCMD
3. ✅ Inicia serviço via NSSM com elevação
4. ✅ Fallback para PowerShell se NSSM falhar
5. ✅ Verifica se iniciou com sucesso

---

## 🛑 **Parar Servidor**

Para o servidor SCUM de forma segura.

### **Endpoint**
```
POST /api/server/stop
```

### **Headers**
```
Content-Type: application/json
```

### **Body**
```json
{
  "force": false,
  "wait_timeout": 30
}
```

### **Parâmetros**
- **`force`** (boolean, opcional): Força parada mesmo se não estiver rodando
- **`wait_timeout`** (integer, opcional): Tempo de espera para confirmação (segundos)

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

### **Resposta de Erro (400)**
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

### **Exemplo de Uso**
```bash
curl -X POST http://localhost:3000/api/server/stop \
  -H "Content-Type: application/json" \
  -d '{"force": false, "wait_timeout": 30}'
```

### **Processo Executado**
1. ✅ Verifica se serviço está rodando
2. ✅ Para serviço via NSSM com elevação
3. ✅ Fallback para PowerShell se NSSM falhar
4. ✅ Verifica se parou com sucesso

---

## 🔄 **Reiniciar Servidor**

Reinicia o servidor SCUM (para + inicia). **Envia notificações para Discord** durante o processo.

### **Endpoint**
```
POST /api/server/restart
```

### **Headers**
```
Content-Type: application/json
```

### **Body**
```json
{
  "force": false,
  "wait_timeout": 30
}
```

### **Parâmetros**
- **`force`** (boolean, opcional): Força reinício mesmo se não estiver rodando
- **`wait_timeout`** (integer, opcional): Tempo de espera para confirmação (segundos)

### **Notificações Discord**
O endpoint envia automaticamente as seguintes notificações para o Discord:

1. **🔄 Servidor Reiniciando** - Quando o processo de restart inicia
2. **✅ Servidor Reiniciado** - Quando o restart é concluído com sucesso
3. **❌ Falha no Reinício** - Se houver erro durante o processo

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

### **Resposta de Erro (400)**
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

### **Exemplo de Uso**
```bash
curl -X POST http://localhost:3000/api/server/restart \
  -H "Content-Type: application/json" \
  -d '{"force": false, "wait_timeout": 30}'
```

### **Processo Executado**
1. ✅ Para o servidor (se estiver rodando)
2. ✅ Aguarda 5 segundos
3. ✅ Inicia o servidor (com atualização SteamCMD)
4. ✅ Verifica se reiniciou com sucesso

---

## 📝 **Obter Logs**

Obtém logs do sistema com filtros opcionais.

### **Endpoint**
```
GET /api/server/logs
```

### **Headers**
```
Nenhum necessário
```

### **Query Parameters**
- **`limit`** (integer, opcional): Número máximo de logs (padrão: 100)
- **`level`** (string, opcional): Nível do log (debug, info, warn, error, critical)
- **`since`** (timestamp, opcional): Logs desde este timestamp

### **Resposta de Sucesso (200)**
```json
{
  "success": true,
  "data": {
    "logs": [
      {
        "timestamp": "2025-10-16T15:22:15.360641",
        "level": "INFO",
        "message": "SCUM Backend iniciado"
      },
      {
        "timestamp": "2025-10-16T15:22:15.361204",
        "level": "INFO",
        "message": "ServerManager inicializado",
        "data": {
          "operation": "start_server",
          "duration": 5.2,
          "success": true
        }
      }
    ],
    "count": 10,
    "limit": 10
  },
  "timestamp": 1760629995.398204
}
```

### **Resposta de Erro (500)**
```json
{
  "success": false,
  "error": "Erro específico"
}
```

### **Exemplo de Uso**
```bash
# Obter últimos 10 logs
curl "http://localhost:3000/api/server/logs?limit=10"

# Obter logs de erro
curl "http://localhost:3000/api/server/logs?level=error&limit=5"

# Obter logs desde timestamp específico
curl "http://localhost:3000/api/server/logs?since=1760629995"
```

---

## 📢 **Sistema de Notificações**

### **Status das Notificações**

Obter status completo do sistema de notificações.

#### **Endpoint**
```
GET /api/notifications/status
```

#### **Resposta de Sucesso (200)**
```json
{
  "success": true,
  "data": {
    "enabled": true,
    "is_running": false,
    "check_interval": 30000,
    "restart_protection_window": 15,
    "last_restart_notifications": "21:00",
    "cooldowns": {
      "cooldowns": {
        "restart": 600,
        "custom": 30,
        "events": 120
      },
      "last_sent": {
        "restart": "2025-10-16T20:16:57.996991",
        "custom": null,
        "events": null
      }
    },
    "scum_notifier": {
      "enabled": true,
      "notifications_file_exists": true,
      "current_notifications_count": 0,
      "highest_priority": 0
    }
  },
  "timestamp": 1760656651.889322
}
```

---

### **Enviar Notificação Personalizada**

Enviar notificação personalizada para jogadores com comportamento idêntico ao projeto original.

#### **Endpoint**
```
POST /api/notifications/send
```

#### **Parâmetros do Body**
- **`message`** (string, obrigatório): Mensagem a ser enviada
- **`duration`** (integer, opcional): Duração em segundos (padrão: 15)
- **`color`** (string, opcional): Cor RGB no formato "R-G-B" (padrão: "255-255-255")

#### **Exemplo de Request**
```json
{
  "message": "Sua mensagem personalizada aqui",
  "duration": 15,
  "color": "255-255-255"
}
```

#### **Resposta de Sucesso (200)**
```json
{
  "success": true,
  "message": "Notificação enviada com sucesso",
  "data": {
    "message": "Sua mensagem personalizada aqui",
    "color": "255-255-255",
    "duration": 15,
    "time": "00:44",
    "path": "C:\\Servers\\Scum\\SCUM\\Saved\\Config\\WindowsServer\\Notifications.json"
  }
}
```

#### **Características Especiais**
- **Offset automático**: Mensagem aparece 2 minutos após envio
- **Proteção inteligente**: Preservada por 5 minutos antes de restart
- **Comportamento original**: Idêntico ao projeto SSM 2.0
- **Sem verificações de bloqueio**: Envio direto e imediato

---

### **Enviar Notificação Administrativa**

Enviar notificação administrativa usando templates pré-configurados.

#### **Endpoint**
```
POST /api/notifications/admin/send
```

#### **Parâmetros do Body**
- **`type`** (string, obrigatório): Tipo de mensagem administrativa
- **`message`** (string, obrigatório): Mensagem personalizada

#### **Tipos de Mensagem Disponíveis**
| Tipo | Cor | Duração | Descrição |
|------|-----|---------|-----------|
| `admin_announcement` | 🟡 Amarelo | 25s | Anúncios gerais |
| `admin_warning` | 🟠 Laranja | 30s | Avisos importantes |
| `admin_info` | 🔵 Azul | 20s | Informações úteis |
| `admin_success` | 🟢 Verde | 15s | Confirmações |
| `admin_error` | 🔴 Vermelho | 25s | Problemas técnicos |
| `admin_maintenance` | 🟠 Laranja Claro | 30s | Manutenções |
| `admin_event` | 🟣 Roxo | 20s | Eventos especiais |

#### **Exemplo de Request**
```json
{
  "type": "admin_announcement",
  "message": "Novo evento especial iniciado! Participem todos!"
}
```

#### **Resposta de Sucesso (200)**
```json
{
  "success": true,
  "count": 1,
  "priority": 10,
  "path": "C:\\Servers\\Scum\\SCUM\\Saved\\Config\\WindowsServer\\Notifications.json"
}
```

#### **Resposta de Cooldown (200)**
```json
{
  "success": false,
  "message": "Cooldown ativo para notificações personalizadas"
}
```

---

### **Obter Templates Administrativos**

Obter todos os templates de mensagens administrativas disponíveis.

#### **Endpoint**
```
GET /api/notifications/admin/templates
```

#### **Resposta de Sucesso (200)**
```json
{
  "success": true,
  "data": {
    "name": "admin_messages",
    "description": "Template para mensagens administrativas enviadas pelo administrador",
    "version": "1.0",
    "admin_message_types": [
      {
        "type": "admin_announcement",
        "description": "Anúncios gerais do administrador",
        "color": "255-255-100",
        "duration": 25,
        "examples": [
          "Novo evento especial iniciado!",
          "Regras do servidor atualizadas",
          "Bem-vindos novos jogadores!"
        ]
      }
      // ... outros tipos
    ]
  },
  "timestamp": 1760657151.755308
}
```

---

### **Limpar Notificações**

Limpar todas as notificações ativas.

#### **Endpoint**
```
POST /api/notifications/clear
```

#### **Resposta de Sucesso (200)**
```json
{
  "success": true
}
```

---

### **Resetar Cooldowns**

Resetar todos os cooldowns de notificações para permitir envio imediato.

#### **Endpoint**
```
POST /api/notifications/cooldowns/reset
```

#### **Resposta de Sucesso (200)**
```json
{
  "success": true,
  "message": "Cooldowns resetados com sucesso",
  "cooldowns": {
    "cooldowns": {
      "restart": 600,
      "custom": 30,
      "events": 120
    },
    "last_sent": {
      "restart": null,
      "custom": null,
      "events": null
    }
  }
}
```

---

## 🛡️ **Sistema de Proteção Inteligente**

### **Lógica de 12 Minutos**

O sistema implementa uma proteção inteligente para preservar mensagens personalizadas:

#### **⏰ Timeline de Proteção**
```
00:38 - Mensagem personalizada enviada
00:40 - SCUM lê a mensagem (offset 2min)
00:43-00:47 - Sistema verifica mas NÃO recria (fora da janela)
00:48 - Sistema detecta janela de 12 minutos
00:48 - Sistema cria notificações de restart
00:50 - Notificações de restart começam
01:00 - Restart do servidor
```

#### **🔧 Configurações**
- **Janela de proteção**: 12 minutos antes do restart
- **Proteção de mensagem**: 5 minutos após envio
- **Offset automático**: 2 minutos para visibilidade no Discord

#### **✅ Benefícios**
- Mensagens personalizadas preservadas por tempo suficiente
- Sistema inteligente que não interfere desnecessariamente
- Timing perfeito para ambos os tipos de notificação
- Comportamento idêntico ao projeto original

---

### **Criar Notificações de Restart**

Criar notificações de restart para horário específico.

#### **Endpoint**
```
POST /api/notifications/restart/create
```

#### **Parâmetros do Body**
- **`restart_time`** (string, obrigatório): Horário do restart no formato "HH:MM"
- **`restart_date`** (string, opcional): Data do restart no formato "YYYY-MM-DD" (padrão: hoje)

#### **Exemplo de Request**
```json
{
  "restart_time": "21:00",
  "restart_date": "2025-10-16"
}
```

#### **Resposta de Sucesso (200)**
```json
{
  "success": true,
  "count": 6,
  "priority": 100,
  "path": "C:\\Servers\\Scum\\SCUM\\Saved\\Config\\WindowsServer\\Notifications.json"
}
```

#### **Exemplos de Uso**
```bash
# Enviar anúncio administrativo
curl -X POST http://localhost:3000/api/notifications/admin/send \
  -H "Content-Type: application/json" \
  -d '{
    "type": "admin_announcement",
    "message": "Novo evento especial iniciado!"
  }'

# Obter templates disponíveis
curl http://localhost:3000/api/notifications/admin/templates

# Limpar notificações
curl -X POST http://localhost:3000/api/notifications/clear

# Criar notificações de restart
curl -X POST http://localhost:3000/api/notifications/restart/create \
  -H "Content-Type: application/json" \
  -d '{
    "restart_time": "21:00",
    "restart_date": "2025-10-16"
  }'
```

---

## 🚫 **Sistema de Deduplicação**

Sistema implementado na versão 1.6.0 para eliminar notificações duplicadas no Discord.

### **📋 Endpoints Disponíveis**

#### **Status da Deduplicação**
```
GET /api/deduplication/status
```
Verifica o status atual do sistema de deduplicação.

**Resposta:**
```json
{
  "success": true,
  "data": {
    "deduplication_active": true,
    "processed_files_count": 15,
    "processing_locks_count": 0,
    "last_cleanup": "2025-10-22T00:54:25.000Z",
    "processors_status": {
      "admin_logs": {
        "deduplication_enabled": true,
        "files_processed": 5,
        "last_processed": "2025-10-22T00:54:25.000Z"
      },
      "vehicle_destruction": {
        "deduplication_enabled": true,
        "files_processed": 3,
        "last_processed": "2025-10-22T00:54:25.000Z"
      },
      "chat": {
        "deduplication_enabled": true,
        "files_processed": 4,
        "last_processed": "2025-10-22T00:54:25.000Z"
      },
      "bunkers": {
        "deduplication_enabled": true,
        "files_processed": 2,
        "last_processed": "2025-10-22T00:54:25.000Z"
      },
      "chest_ownership": {
        "deduplication_enabled": true,
        "files_processed": 1,
        "last_processed": "2025-10-22T00:54:25.000Z"
      }
    }
  }
}
```

#### **Limpar Cache de Deduplicação**
```
POST /api/deduplication/clear-cache
```
Limpa o cache de deduplicação (arquivos processados e locks).

**Resposta:**
```json
{
  "success": true,
  "message": "Cache de deduplicação limpo com sucesso",
  "data": {
    "processed_files_cleared": 15,
    "processing_locks_cleared": 0,
    "timestamp": "2025-10-22T00:54:25.000Z"
  }
}
```

#### **Forçar Reprocessamento**
```
POST /api/deduplication/force-reprocess
```
Força o reprocessamento de um arquivo específico.

**Request Body:**
```json
{
  "file_path": "data/logs/admin_2025.10.22.log",
  "force_reprocess": true
}
```

**Resposta:**
```json
{
  "success": true,
  "message": "Arquivo marcado para reprocessamento",
  "data": {
    "file_path": "data/logs/admin_2025.10.22.log",
    "removed_from_processed": true,
    "timestamp": "2025-10-22T00:54:25.000Z"
  }
}
```

### **📊 Benefícios da Deduplicação**

- **Performance**: Redução de 66% no processamento desnecessário
- **Discord**: Eliminação completa de notificações duplicadas
- **Recursos**: Menor uso de CPU e memória
- **Experiência**: Interface Discord mais limpa e organizada
- **Confiabilidade**: Sistema mais estável e previsível

### **🔍 Monitoramento**

**Métricas Importantes:**
- `processed_files_count`: Arquivos já processados
- `processing_locks_count`: Arquivos sendo processados (deve ser 0)
- `last_cleanup`: Última limpeza do cache
- `processors_status`: Status individual de cada processador

**Documentação Completa**: [DEDUPLICATION_ENDPOINTS.md](./DEDUPLICATION_ENDPOINTS.md)

---

## 🔄 **Sistema de Sincronização com Gestão**

Sistema automático de sincronização de dados com o servidor Gestão. O SSM Backend envia periodicamente (a cada 4 horas) informações do servidor, lista de jogadores e rankings para centralização no Gestão.

### **📡 Funcionamento**

O sistema funciona de forma **automática** e **transparente**:

1. **Handshake**: Antes de cada sincronização, o SSM Backend verifica se o Gestão está pronto
2. **Sincronização**: Se o Gestão estiver pronto, envia os dados
3. **Retry**: Se falhar, aguarda e tenta novamente (até 3 tentativas)
4. **Intervalo**: Executa automaticamente a cada 4 horas (configurável)

### **⚙️ Configuração**

Configure no `config.json` na seção `licensing`:

```json
{
  "licensing": {
    "gestao_url": "https://gestao.seudominio.com",
    "gestao_api_key": "ssm_<chave_gerada_pelo_gestao>",
    "gestao_enabled": true,
    "gestao_sync_interval_seconds": 14400,  // 4 horas
    "gestao_handshake_timeout_seconds": 5,
    "gestao_sync_timeout_seconds": 30,
    "gestao_max_retry_delay_seconds": 3600,
    "gestao_max_retries": 3
  }
}
```

### **📊 Dados Sincronizados**

#### **Server Info**
- Nome do servidor
- Versão do SSM Backend
- Máximo de jogadores
- Jogadores online no momento

#### **Players**
- Lista de até 1000 jogadores (online e offline)
- Steam ID, nome, fama
- Status online/offline
- Última vez visto

#### **Rankings**
- **Kills**: Top 100 killers (kills, deaths, KDR)
- **Survival**: Top 100 por minutos sobrevividos
- **Lockpicking**: Top 100 por taxa de sucesso média
- **Fishing/Hunting**: Top 100 por animais mortos

### **🔐 Autenticação**

- **API Key**: Gerada pelo Gestão quando o servidor é cadastrado
- **Server Hash**: Identificador único do servidor (equipment_hash)
- **Validação**: Gestão valida hash + API key antes de processar

### **📝 Endpoints do Gestão (Referência)**

> ⚠️ **NOTA**: Estes são endpoints do **Gestão**, não do SSM Backend. O SSM Backend chama estes endpoints automaticamente.

#### **GET /api/servers/ready**
Verifica se o Gestão está pronto para receber dados.

**Query Params:**
- `server_hash` (string, obrigatório): Hash único do servidor

**Resposta (200):**
```json
{
  "ready": true,
  "message": "Pronto para receber dados"
}
```

**Resposta (503):**
```json
{
  "ready": false,
  "retry_after": 60,
  "message": "Servidor ocupado, tente novamente em 60 segundos"
}
```

#### **POST /api/servers/sync**
Sincroniza dados do servidor com o Gestão.

**Body:**
```json
{
  "server_hash": "918aabd12dc60d8432ab952f8eab6557a5b8b14066953e26516fab6f1ff0c54d",
  "api_key": "ssm_2d9ba653192f1a872fbef6583485c50fd6265384ace80ecf222727cc41c4ac4c",
  "server_info": {
    "name": "Meu Servidor SCUM",
    "version": "3.0.0",
    "max_players": 64,
    "current_players": 32
  },
  "players": [...],
  "rankings": {...},
  "timestamp": "2025-01-15T10:30:00Z"
}
```

**Resposta (200):**
```json
{
  "success": true,
  "message": "Dados sincronizados com sucesso",
  "server_id": 1,
  "players_synced": 150,
  "rankings_synced": 4
}
```

### **📚 Documentação Completa**

Para mais detalhes sobre o planejamento e implementação, consulte:
- [PLANEJAMENTO_ENDPOINT_SINCRONIZACAO_GESTAO.md](../PLANEJAMENTO_ENDPOINT_SINCRONIZACAO_GESTAO.md) - Documentação completa do planejamento e implementação

---

## 📊 **Códigos de Status**

### **HTTP Status Codes**
- **200** - Sucesso
- **400** - Bad Request (parâmetros inválidos)
- **500** - Internal Server Error

### **Status do Servidor**
- **`already_running`** - Servidor já está rodando
- **`not_running`** - Servidor não está rodando
- **`started`** - Servidor iniciado com sucesso
- **`stopped`** - Servidor parado com sucesso
- **`restarted`** - Servidor reiniciado com sucesso
- **`start_failed`** - Falha ao iniciar servidor
- **`stop_failed`** - Falha ao parar servidor
- **`steam_update_failed`** - Falha na atualização Steam
- **`nssm_not_found`** - NSSM não encontrado
- **`error`** - Erro inesperado

### **Status das Notificações**
- **`success`** - Operação realizada com sucesso
- **`cooldown_active`** - Cooldown ativo para envio
- **`priority_insufficient`** - Prioridade insuficiente (restart ativo)
- **`template_not_found`** - Template não encontrado
- **`message_required`** - Mensagem é obrigatória
- **`invalid_format`** - Formato de data/hora inválido

---

## 🧪 **Exemplos de Uso**

### **Python**
```python
import requests

# Health check
response = requests.get('http://localhost:3000/api/health')
print(response.json())

# Status do servidor
response = requests.get('http://localhost:3000/api/server/status')
print(response.json())

# Iniciar servidor
response = requests.post('http://localhost:3000/api/server/start', 
                        json={'force': False, 'wait_timeout': 30})
print(response.json())

# Parar servidor
response = requests.post('http://localhost:3000/api/server/stop', 
                        json={'force': False, 'wait_timeout': 30})
print(response.json())

# Reiniciar servidor
response = requests.post('http://localhost:3000/api/server/restart', 
                        json={'force': False, 'wait_timeout': 30})
print(response.json())

# Obter logs
response = requests.get('http://localhost:3000/api/server/logs?limit=10')
print(response.json())

# Sistema de Notificações
# Status das notificações
response = requests.get('http://localhost:3000/api/notifications/status')
print(response.json())

# Enviar notificação personalizada
response = requests.post('http://localhost:3000/api/notifications/send', 
                        json={
                            'message': 'Sua mensagem personalizada',
                            'duration': 20,
                            'color': '100-200-255'
                        })
print(response.json())

# Enviar notificação administrativa
response = requests.post('http://localhost:3000/api/notifications/admin/send', 
                        json={
                            'type': 'admin_announcement',
                            'message': 'Novo evento especial iniciado!'
                        })
print(response.json())

# Obter templates administrativos
response = requests.get('http://localhost:3000/api/notifications/admin/templates')
print(response.json())

# Limpar notificações
response = requests.post('http://localhost:3000/api/notifications/clear')
print(response.json())
```

### **JavaScript (Node.js)**
```javascript
const axios = require('axios');

// Health check
const health = await axios.get('http://localhost:3000/api/health');
console.log(health.data);

// Iniciar servidor
const start = await axios.post('http://localhost:3000/api/server/start', {
  force: false,
  wait_timeout: 30
});
console.log(start.data);

// Sistema de Notificações
// Enviar notificação administrativa
const notification = await axios.post('http://localhost:3000/api/notifications/admin/send', {
  type: 'admin_announcement',
  message: 'Novo evento especial iniciado!'
});
console.log(notification.data);

// Obter templates
const templates = await axios.get('http://localhost:3000/api/notifications/admin/templates');
console.log(templates.data);
```

### **PowerShell**
```powershell
# Health check
Invoke-RestMethod -Uri "http://localhost:3000/api/health" -Method GET

# Iniciar servidor
Invoke-RestMethod -Uri "http://localhost:3000/api/server/start" -Method POST -ContentType "application/json" -Body '{"force": false, "wait_timeout": 30}'

# Status do servidor
Invoke-RestMethod -Uri "http://localhost:3000/api/server/status" -Method GET

# Sistema de Notificações
# Status das notificações
Invoke-RestMethod -Uri "http://localhost:3000/api/notifications/status" -Method GET

# Enviar notificação administrativa
$body = @{
    type = "admin_announcement"
    message = "Novo evento especial iniciado!"
} | ConvertTo-Json

Invoke-RestMethod -Uri "http://localhost:3000/api/notifications/admin/send" -Method POST -ContentType "application/json" -Body $body

# Obter templates
Invoke-RestMethod -Uri "http://localhost:3000/api/notifications/admin/templates" -Method GET
```

### **cURL**
```bash
# Health check
curl http://localhost:3000/api/health

# Status do servidor
curl http://localhost:3000/api/server/status

# Iniciar servidor
curl -X POST http://localhost:3000/api/server/start \
  -H "Content-Type: application/json" \
  -d '{"force": false, "wait_timeout": 30}'

# Parar servidor
curl -X POST http://localhost:3000/api/server/stop \
  -H "Content-Type: application/json" \
  -d '{"force": false, "wait_timeout": 30}'

# Reiniciar servidor
curl -X POST http://localhost:3000/api/server/restart \
  -H "Content-Type: application/json" \
  -d '{"force": false, "wait_timeout": 30}'

# Obter logs
curl "http://localhost:3000/api/server/logs?limit=10"

# Sistema de Notificações
# Status das notificações
curl http://localhost:3000/api/notifications/status

# Enviar notificação administrativa
curl -X POST http://localhost:3000/api/notifications/admin/send \
  -H "Content-Type: application/json" \
  -d '{
    "type": "admin_announcement",
    "message": "Novo evento especial iniciado!"
  }'

# Obter templates
curl http://localhost:3000/api/notifications/admin/templates

# Limpar notificações
curl -X POST http://localhost:3000/api/notifications/clear
```

---

## ⚠️ **Notas Importantes**

### **Permissões**
- **Administrador**: Necessário para controlar serviços Windows
- **NSSM**: Deve estar instalado e acessível
- **SteamCMD**: Deve estar instalado e funcionando

### **Timeouts**
- **SteamCMD**: 10 minutos (600 segundos)
- **NSSM**: 30 segundos
- **PowerShell**: 30 segundos

### **Fallbacks**
- **NSSM falha** → PowerShell com elevação
- **Serviço não responde** → Timeout e retry

### **Logs**
- **Rotação automática** a cada 10MB
- **Backup** dos últimos 5 arquivos
- **Formato JSON** estruturado

---

## 🔧 **Troubleshooting**

### **Erro 500 - "ServerManager não inicializado"**
- Verificar se `data/config.json` existe
- Verificar se caminhos estão corretos
- Verificar permissões de leitura

### **Erro 500 - "NSSM não encontrado"**
- Verificar se `nssm-2.24/win64/nssm.exe` existe
- Verificar caminho no `config.json`
- Verificar permissões de execução

### **Erro 500 - "Falha na atualização Steam"**
- Verificar se SteamCMD está instalado
- Verificar caminho no `config.json`
- Verificar conexão com internet
- Verificar permissões de escrita

### **Serviço não inicia**
- Verificar se serviço `SCUMServer` existe
- Verificar permissões de administrador
- Verificar logs do Windows Event Viewer
- Verificar se porta 8900 está livre

---

## 📡 **Sistema de Webhooks Discord**

O SCUM Backend envia automaticamente notificações para o Discord através de webhooks configurados.

### **Configuração**
Os webhooks são configurados no arquivo `data/webhooks.json`:

```json
{
  "serverstatus": "https://discord.com/api/webhooks/SEU_WEBHOOK_AQUI"
}
```

### **Auto-criação de chaves**
Na inicialização, o backend pode **adicionar automaticamente** chaves conhecidas no `data/webhooks.json` quando estiverem faltando (com valor `""`), por exemplo:

- `bank_transaction`
- `cargo_drop`

### **Eventos de Webhook**

#### **🚀 Inicialização do Backend**
- **Evento:** `backend_started`
- **Descrição:** Enviado quando o backend é iniciado
- **Cor:** Verde (0x00ff00)

#### **🔄 Controle do Servidor**
- **`server_starting`** - Servidor iniciando (Laranja)
- **`server_started`** - Servidor iniciado com sucesso (Verde)
- **`server_stopping`** - Servidor parando (Laranja)
- **`server_stopped`** - Servidor parado (Azul)
- **`server_restarting`** - Servidor reiniciando (Laranja)
- **`server_restarted`** - Servidor reiniciado com sucesso (Verde)
- **`server_restart_failed`** - Falha no reinício (Vermelho)

#### **⏰ Agendador**
- **`restart_scheduled`** - Reinicialização agendada
- **`restart_started`** - Reinicialização iniciada
- **`restart_completed`** - Reinicialização concluída
- **`restart_failed`** - Falha na reinicialização

### **Formato das Mensagens**
As mensagens são enviadas como embeds do Discord com:
- **Título** com emoji e descrição
- **Cor** baseada no tipo de evento
- **Timestamp** da ocorrência
- **Campos** com informações adicionais (PID, porta, etc.)

### **Rate Limiting**
- **Máximo:** 30 requisições por minuto
- **Retry:** 3 tentativas com delay de 5 segundos
- **Timeout:** 10 segundos por requisição

---

## 👨‍💼 **Sistema de Admin Logs**

Sistema de monitoramento de comandos de administradores em tempo real.

### **Endpoints Disponíveis**

#### **📊 Status do Sistema**
```
GET /api/admin-logs/status
```
Verifica o status do sistema de monitoramento de comandos admin.

**Resposta:**
```json
{
  "success": true,
  "data": {
    "admin_log_processor": true,
    "webhook_configured": true,
    "last_processed_command": "2025.10.21-00.13.01:76561198040636105",
    "total_commands_processed": 156,
    "commands_by_category": {
      "spawn": 89,
      "teleport": 34,
      "godmode": 12,
      "info": 15,
      "command": 6
    },
    "most_active_admin": "Pedreiro (76561198040636105)",
    "last_activity": "2025-10-21T00:13:01Z"
  }
}
```

#### **📈 Estatísticas Detalhadas**
```
GET /api/admin-logs/stats
```
Obtém estatísticas detalhadas dos comandos admin processados.

**Resposta:**
```json
{
  "success": true,
  "data": {
    "total_commands": 156,
    "commands_today": 23,
    "commands_this_week": 89,
    "commands_this_month": 156,
    "categories": {
      "spawn": {
        "count": 89,
        "percentage": 57.1,
        "emoji": "🎁",
        "color": "#f1c40f"
      }
    },
    "top_admins": [
      {
        "steam_id": "76561198040636105",
        "name": "Pedreiro",
        "commands_count": 89,
        "percentage": 57.1
      }
    ]
  }
}
```

#### **📋 Últimos Comandos**
```
GET /api/admin-logs/recent?limit=10
```
Obtém os últimos comandos admin executados.

**Parâmetros:**
- `limit` (opcional): Número de comandos a retornar (padrão: 10)

**Resposta:**
```json
{
  "success": true,
  "data": {
    "commands": [
      {
        "command_id": "2025.10.21-00.13.01:76561198040636105",
        "timestamp": "2025-10-21T00:13:01Z",
        "steam_id": "76561198040636105",
        "player_name": "Pedreiro",
        "action": "SpawnItem Phoenix_Tears",
        "category": {
          "name": "spawn",
          "emoji": "🎁",
          "color": "#f1c40f"
        }
      }
    ],
    "total": 156,
    "limit": 10
  }
}
```

### **🎨 Categorização de Comandos**

- **🚀 Teleport** (roxo) - Comandos de teleporte
- **🎁 Spawn** (amarelo) - Spawn de itens
- **🛡️ God Mode** (vermelho) - Comandos de god mode
- **👁️ Info** (azul) - Informações de jogadores
- **⚡ Command** (laranja) - Outros comandos
- **📋 Default** (verde) - Comandos não categorizados

### **📚 Documentação Adicional**

- [Exemplos de Uso](./admin-logs-examples.md) - Exemplos práticos em Python e cURL
- [Sistema de Admin Logs](../ADMIN_LOGS_SYSTEM.md) - Documentação completa do sistema

---

## ⏰ **Sistema de Precisão de Horário**

Sistema que permite ajustar a precisão do horário exibido nas notificações do comando `/tm` através de um offset configurável.

### **🔧 Configuração**

Arquivo: `data/config.json`
```json
{
  "time_precision": {
    "enabled": true,
    "offset_minutes": 8,
    "description": "Minutos para adicionar ao horário do servidor para maior precisão no comando /tm"
  }
}
```

### **📡 Endpoints**

#### **Obter Configuração de Precisão**
```
GET /api/time-precision/config
```
Retorna a configuração atual de precisão de horário.

**Resposta:**
```json
{
  "success": true,
  "data": {
    "enabled": true,
    "offset_minutes": 8,
    "description": "Minutos para adicionar ao horário do servidor para maior precisão no comando /tm"
  },
  "timestamp": 1760629995.398204
}
```

#### **Testar Precisão de Horário**
```
POST /api/time-precision/test
```
Testa a precisão de horário aplicando o offset configurado.

**Resposta:**
```json
{
  "success": true,
  "data": {
    "base_time": "15:35",
    "adjusted_time": "15:43",
    "offset_minutes": 8,
    "enabled": true,
    "time_of_day": 15.5857553482,
    "difference_minutes": 8
  },
  "timestamp": 1760629995.398204
}
```

### **🎯 Como Funciona**

1. **Comando `/tm` executado** - Sistema detecta comando no chat
2. **Consulta horário** - Obtém `time_of_day` do banco SCUM.db
3. **Aplica offset** - Adiciona minutos configurados ao horário
4. **Cria notificação** - Gera notificação in-game com horário ajustado
5. **Envia Discord** - Confirma execução no canal Discord

---

## 🔐 **Sistema de Permissões de Jogadores**

Sistema completo para gerenciamento de permissões de jogadores com sincronização automática com arquivos INI do servidor SCUM.

### **📡 Endpoints**

#### **Ativar Permissão**
```
POST /api/players/{steam_id}/permissions/{permission_type}/activate
```
Ativa uma permissão específica para um jogador.

**Parâmetros:**
- `steam_id` (path): Steam ID do jogador
- `permission_type` (path): Tipo da permissão (admin, banned, exclusive, etc.)

**Body:**
```json
{
  "granted_by": "admin",
  "notes": "Permissão de administrador concedida"
}
```

**Resposta:**
```json
{
  "success": true,
  "message": "Permissão 'admin' ativada com sucesso para o jogador 76561198040636105",
  "data": {
    "permission_id": 1,
    "steam_id": "76561198040636105",
    "permission_type": "admin",
    "is_active": true,
    "granted_by": "admin",
    "granted_at": "2025-01-15T10:30:00Z",
    "notes": "Permissão de administrador concedida",
    "ini_file_updated": true,
    "ini_file_path": "C:\\Servers\\scum\\SCUM\\Saved\\Config\\WindowsServer\\AdminUsers.ini"
  }
}
```

#### **Desativar Permissão**
```
POST /api/players/{steam_id}/permissions/{permission_type}/deactivate
```
Desativa uma permissão específica para um jogador.

#### **Listar Permissões do Jogador**
```
GET /api/players/{steam_id}/permissions
```
Lista todas as permissões de um jogador específico.

#### **Estatísticas de Permissões**
```
GET /api/permissions/stats
```
Obtém estatísticas gerais do sistema de permissões.

#### **Sincronizar Arquivos INI**
```
POST /api/permissions/sync-ini-files
```
Sincroniza todos os arquivos INI com as permissões do banco de dados.

#### **Listar Tipos de Permissão**
```
GET /api/permissions/types
```
Lista todos os tipos de permissão disponíveis.

#### **Listar Permissões por Tipo**
```
GET /api/permissions/by-type/{permission_type}
```
Lista todos os jogadores com um tipo específico de permissão.

### **🎯 Tipos de Permissão Suportados**

| Tipo | Nome | Arquivo INI | Formato | Descrição |
|------|------|-------------|---------|-----------|
| `admin` | Administrador | `AdminUsers.ini` | `{steam_id}[setgodmode]` | Permissões de administrador do servidor |
| `banned` | Banido | `BannedUsers.ini` | `{steam_id}` | Jogador banido do servidor |
| `exclusive` | Exclusivo | `ExclusiveUsers.ini` | `{steam_id}` | Acesso exclusivo ao servidor |
| `server_admin` | Admin do Servidor | `ServerSettingsAdminUsers.ini` | `{steam_id}` | Administrador das configurações |
| `silenced` | Silenciado | `SilencedUsers.ini` | `{steam_id}` | Jogador silenciado no chat |
| `whitelisted` | Whitelist | `WhitelistedUsers.ini` | `{steam_id}` | Jogador na lista branca |

### **🔧 Funcionalidades**

- ✅ **Ativação/Desativação** de permissões por jogador
- ✅ **Sincronização automática** com arquivos INI do servidor
- ✅ **Múltiplas permissões** simultâneas para um mesmo jogador
- ✅ **Auditoria completa** com histórico de alterações
- ✅ **Validação de dados** e verificação de integridade

### **📚 Documentação Adicional**

- [Sistema de Permissões](../PERMISSIONS_SYSTEM.md) - Documentação completa do sistema de permissões
- [Exemplos de Permissões](./permissions-examples.md) - Exemplos práticos de uso
- [Endpoints de Precisão de Horário](./TIME_PRECISION_ENDPOINTS.md) - Documentação completa dos endpoints
- [Sistema de Admin Logs](../ADMIN_LOGS_SYSTEM.md) - Documentação completa do sistema
- [Sistema de Fama dos Jogadores](./PLAYERS_FAME_ENDPOINTS.md) - Documentação completa dos endpoints de fama
- [Sistema de Verificação de Veículos](./VEHICLE_VERIFICATION_ENDPOINTS.md) - Documentação completa dos endpoints de verificação periódica de veículos

---

## 🏆 **Sistema de Fama dos Jogadores**

Sistema para consultar os totais de fama dos jogadores do servidor SCUM. A fama é atualizada automaticamente em tempo real através do processamento dos logs `famepoints_*.log`.

### **📡 Endpoints Disponíveis**

#### **Listar Todos os Jogadores com Fama**
```
GET /api/players/fame
```
Lista todos os jogadores com seus totais de fama, ordenados por total de fama.

**Parâmetros Query (opcionais):**
- `limit` (number): Número máximo de registros (padrão: 100, máximo: 1000)
- `offset` (number): Deslocamento para paginação (padrão: 0)
- `sort_order` (string): Direção da ordenação (`asc` ou `desc`, padrão: `desc`)

**Resposta de Sucesso (200):**
```json
{
  "success": true,
  "data": {
    "players": [
      {
        "steam_id": "76561198777583030",
        "player_name": "ADM Guns",
        "total_fame": 234.79837,
        "last_updated": "2025-12-02 00:21:39"
      }
    ],
    "total": 28,
    "limit": 100,
    "offset": 0,
    "count": 28,
    "sort_order": "desc"
  }
}
```

#### **Obter Fama de um Jogador Específico**
```
GET /api/players/{steam_id}/fame
```
Obtém o total de fama de um jogador específico pelo Steam ID.

**Resposta de Sucesso (200):**
```json
{
  "success": true,
  "data": {
    "steam_id": "76561198777583030",
    "player_name": "ADM Guns",
    "total_fame": 234.79837,
    "last_updated": "2025-12-02 00:21:39"
  }
}
```

**Resposta de Erro (404):**
```json
{
  "success": false,
  "error": "Jogador 76561199999999999 não encontrado na tabela de fama"
}
```

### **🎯 Funcionalidades**

- ✅ **Atualização automática** em tempo real através dos logs `famepoints_*.log`
- ✅ **Suporte a ganho e perda de fama** (valores positivos e negativos)
- ✅ **Paginação** com `limit` e `offset`
- ✅ **Ordenação** por total de fama (crescente ou decrescente)
- ✅ **Consulta individual** por Steam ID

### **📚 Documentação Completa**

Para mais detalhes, consulte: [PLAYERS_FAME_ENDPOINTS.md](./PLAYERS_FAME_ENDPOINTS.md)

---

## 🏆 **Sistema de Rankings**

Sistema completo para consultar rankings de jogadores com todos os dados agregados da tabela `rankings`. Permite ordenação dinâmica por qualquer coluna e busca por nome do jogador.

### **📡 Endpoints Disponíveis**

#### **Listar Todos os Rankings**
```
GET /api/rankings/list
```
Lista todos os jogadores com rankings completos para criar uma tabela de rankings. Permite ordenação dinâmica por qualquer coluna e busca por nome.

**Parâmetros Query (opcionais):**
- `limit` (number): Número máximo de registros (padrão: 50, máximo: 200)
- `offset` (number): Deslocamento para paginação (padrão: 0)
- `sort_by` (string): Campo de ordenação (padrão: `kills`)
  - Combat: `kills`, `deaths`, `kdr`, `longest_shot`, `suicides`, `headshots`
  - Lockpicking: `lockpick_basic_rate`, `lockpick_medium_rate`, `lockpick_advanced_rate`, etc.
  - Survival: `vehicles_destroyed`, `highest_defecation`, `animals_killed`, `minutes_survived`, `total_fame`, etc.
- `sort_order` (string): Direção da ordenação (`asc` ou `desc`, padrão: `desc`)
- `search` (string): Buscar por nome do jogador (busca parcial, case-insensitive)

**Resposta de Sucesso (200):**
```json
{
  "success": true,
  "data": {
    "players": [
      {
        "rank": 1,
        "steam_id": "76561198777583030",
        "player_name": "ADM Guns",
        "kills": 150,
        "deaths": 25,
        "kdr": 6.0,
        "longest_shot": {
          "distance": 125.50,
          "weapon": "Weapon_AK47_C",
          "timestamp": "2025-01-15 14:30:00"
        },
        "suicides": 3,
        "headshots": 142,
        "lockpicking": {
          "basic": { "success": 45, "fails": 12, "total": 57, "rate": 78.95 },
          "medium": { "success": 30, "fails": 8, "total": 38, "rate": 78.95 },
          "advanced": { "success": 20, "fails": 5, "total": 25, "rate": 80.0 },
          "veryeasy": { "success": 10, "fails": 2, "total": 12, "rate": 83.33 },
          "diallock": { "success": 5, "fails": 1, "total": 6, "rate": 83.33 },
          "other": { "success": 0, "fails": 0, "total": 0, "rate": 0.0 }
        },
        "vehicles_destroyed": 5,
        "highest_defecation": 250,
        "animals_killed": 87,
        "players_knocked_out": 23,
        "minutes_survived": 5000.5,
        "overdoses": 8,
        "highest_weight_carried": 45.7,
        "total_fame": 234.79837,
        "last_updated": "2025-12-02 03:00:00"
      }
    ],
    "pagination": {
      "total": 150,
      "limit": 50,
      "offset": 0,
      "count": 50,
      "has_more": true
    },
    "sorting": {
      "sort_by": "kills",
      "sort_order": "desc",
      "order_column": "kills"
    },
    "search": null
  },
  "timestamp": 1701504000
}
```

**Resposta de Erro (400):**
```json
{
  "success": false,
  "error": "Campo de ordenação inválido: invalid_field. Campos disponíveis: kills, deaths, kdr, ..."
}
```

### **🎯 Funcionalidades**

- ✅ **Ordenação dinâmica** por qualquer coluna (kills, deaths, kdr, longest_shot, total_fame, minutes_survived, etc.)
- ✅ **Paginação** com `limit` e `offset`
- ✅ **Busca por nome** do jogador (busca parcial, case-insensitive)
- ✅ **Dados completos** de todos os rankings (combat, lockpicking, survival, fama)
- ✅ **Toggle de ordenação** (asc/desc) ao clicar na mesma coluna
- ✅ **Performance otimizada** com índices no banco de dados

### **📚 Documentação Completa**

- **Para desenvolvedores frontend**: [FRONTEND_RANKINGS_LIST_API.md](./FRONTEND_RANKINGS_LIST_API.md) - Documentação completa com exemplos TypeScript/React
- **Documentação técnica**: [RANKINGS_LIST_ENDPOINT.md](./RANKINGS_LIST_ENDPOINT.md) - Detalhes técnicos do endpoint

---

## ⚙️ **Sistema de Configurações do Servidor**

Sistema para gerenciar o arquivo `ServerSettings.ini` do servidor SCUM. Permite ler, editar e adicionar qualquer configuração, incluindo campos customizados e de mods.

### **📡 Endpoints Disponíveis**

#### **Obter Todas as Configurações**
```
GET /api/server/settings
```
Retorna **todas as seções e configurações** do `ServerSettings.ini`, incluindo todos os campos de cada seção (aproximadamente 62 campos em General, 100+ em World, etc.).

**Query Params (opcional):**
- `section` (string): Nome da seção para retornar apenas uma seção específica (ex: `General`, `World`, `Respawn`)

**Resposta de Sucesso (200):**
```json
{
  "success": true,
  "data": {
    "General": {
      "scum.ServerName": "SCUM Server",
      "scum.ServerDescription": "Server Description",
      "scum.ServerPassword": "",
      "scum.MaxPlayers": "64",
      "scum.ServerBannerUrl": "",
      "scum.ServerPlaystyle": "PVE",
      "scum.WelcomeMessage": "Welcome to our SCUM Server",
      "scum.MessageOfTheDay": "This is the Message of the Day.",
      "scum.MessageOfTheDayCooldown": "10.000000",
      "scum.MinServerTickRate": "5",
      "scum.MaxServerTickRate": "30",
      "scum.MaxPingCheckEnabled": "1",
      "scum.MaxPing": "200.000000",
      "scum.LogoutTimer": "60.000000",
      "scum.AllowFirstPerson": "1",
      "scum.AllowThirdPerson": "1",
      "scum.AllowCrosshair": "1",
      "scum.AllowVoting": "1",
      "scum.AllowMapScreen": "1",
      "scum.AllowKillClaiming": "1",
      "scum.AllowComa": "1",
      "scum.AllowMinesAndTraps": "1",
      "scum.AllowSkillGainInSafeZones": "0",
      "scum.AllowEvents": "1",
      "scum.LimitGlobalChat": "0",
      "scum.AllowGlobalChat": "1",
      "scum.AllowLocalChat": "1",
      "scum.AllowSquadChat": "1",
      "scum.AllowAdminChat": "1",
      "scum.RustyLocksLogging": "0",
      "scum.HideKillNotification": "1",
      "scum.DisableTimedGifts": "0",
      "scum.UseMapBaseBuildingRestriction": "1",
      "scum.DisableBaseBuilding": "0",
      "scum.VotingDuration": "60.000000",
      "scum.PlayerMinimalVotingInterest": "0.500000",
      "scum.PlayerPositiveVotePercentage": "0.500000",
      "scum.MasterServerUpdateSendInterval": "60",
      "scum.MasterServerIsLocalTest": "0",
      "scum.PartialWipe": "0",
      "scum.GoldWipe": "0",
      "scum.FullWipe": "0",
      "scum.ItemVirtualizationRelevancyUpdatePeriod": "1.000000",
      "scum.ItemVirtualizationEventProcessingTimeBudget": "5.000000",
      "scum.ItemVirtualizationVisitorDistanceTravelledForUpdate": "100.000000",
      "scum.ItemVirtualizationVisitorBounds": "10000.000000",
      "scum.VirtualizedItemBounds": "100.000000",
      "scum.FameGainMultiplier": "1.000000",
      "scum.FamePointPenaltyOnDeath": "0.100000",
      "scum.FamePointPenaltyOnKilled": "0.500000",
      "scum.FamePointRewardOnKill": "0.250000",
      "scum.LogSuicides": "0",
      "scum.EnableSpawnOnGround": "0",
      "scum.DeleteInactiveUsers": "1",
      "scum.DaysSinceLastLoginToBecomeInactive": "180",
      "scum.DeleteBannedUsers": "0",
      "scum.MaximumTimeForChestsInForbiddenZones": "02:00:00",
      "scum.LogChestOwnership": "1",
      "scum.SettingsVersion": "3",
      "scum.DisableExamineGhost": "0"
    },
    "World": {
      "scum.MaxAllowedBirds": "15",
      "scum.MaxAllowedCharacters": "-1",
      "scum.MaxAllowedPuppets": "-1"
    },
    "Respawn": {
      "scum.AllowSectorRespawn": "1",
      "scum.AllowShelterRespawn": "1",
      "scum.RandomRespawnPrice": "250"
    },
    "Vehicles": {},
    "Damage": {},
    "Features": {}
  },
  "timestamp": 1701504000
}
```

**Nota**: A resposta inclui **todos os campos** de cada seção. O exemplo acima mostra apenas alguns campos da seção `General` para brevidade. Na prática, a seção `General` contém aproximadamente 62 campos, `World` contém mais de 100 campos, etc.

#### **Atualizar Campo Específico**
```
PATCH /api/server/settings
```
Atualiza uma configuração específica. Aceita qualquer campo (conhecido ou customizado).

**Body:**
```json
{
  "section": "General",
  "key": "scum.MaxPlayers",
  "value": 100
}
```

**Resposta de Sucesso (200):**
```json
{
  "success": true,
  "message": "Configuração scum.MaxPlayers atualizada",
  "data": {
    "section": "General",
    "key": "scum.MaxPlayers",
    "value": "100",
    "backup": "C:\\Servers\\Scum\\SCUM\\Saved\\Config\\WindowsServer\\backups\\ServerSettings.backup.20251202_190000.ini"
  },
  "timestamp": 1701504000
}
```

#### **Atualizar Seção Completa**
```
PUT /api/server/settings/{section}
```
Atualiza uma seção completa. Útil para salvar múltiplas alterações de uma vez. Aceita qualquer campo (conhecido ou customizado).

**Body:**
```json
{
  "scum.ServerName": "Meu Servidor SCUM",
  "scum.MaxPlayers": "100",
  "scum.ServerPlaystyle": "PVP",
  "custom.MyCustomSetting": "value"
}
```

**Resposta de Sucesso (200):**
```json
{
  "success": true,
  "message": "3 campo(s) atualizado(s)",
  "data": {
    "section": "General",
    "updated_fields": ["scum.ServerName", "scum.MaxPlayers", "scum.ServerPlaystyle", "custom.MyCustomSetting"],
    "backup": "C:\\Servers\\Scum\\SCUM\\Saved\\Config\\WindowsServer\\backups\\ServerSettings.backup.20251202_190000.ini"
  },
  "timestamp": 1701504000
}
```

### **🎯 Funcionalidades**

- ✅ **Leitura completa** do `ServerSettings.ini`
- ✅ **Edição de qualquer campo** (conhecido ou não)
- ✅ **Adição de campos customizados** (mods, configurações personalizadas)
- ✅ **Preservação automática** de todos os campos ao salvar
- ✅ **Backup automático** antes de modificar (mantém últimos 10 backups)
- ✅ **Suporte a mods** automaticamente
- ✅ **Compatibilidade** com qualquer versão do jogo

### **📚 Documentação Completa**

- **Para desenvolvedores frontend**: [FRONTEND_SERVERSETTINGS_API.md](./FRONTEND_SERVERSETTINGS_API.md) - Documentação completa com exemplos TypeScript/React
- **Análise do arquivo**: [ANALYSIS_SERVERSETTINGS_INI.md](../ANALYSIS_SERVERSETTINGS_INI.md) - Estrutura completa do ServerSettings.ini
- **Solução implementada**: [SIMPLE_SERVERSETTINGS_SOLUTION.md](../SIMPLE_SERVERSETTINGS_SOLUTION.md) - Detalhes da implementação

---

## ⚙️ **Sistema de Configuração (config.json)**

Sistema para gerenciar o arquivo `data/config.json` da aplicação. Permite ler, editar seções específicas ou substituir a configuração completa, com backup automático.

### **📡 Endpoints Disponíveis**

#### **Obter Configuração Completa ou Seção**
```
GET /api/config
GET /api/config?section={nome_secao}
```

Retorna a configuração completa ou uma seção específica do `config.json`.

**Query Params (opcional):**
- `section` (string): Nome da seção para retornar apenas uma seção específica (ex: `api`, `server`, `scheduler`, `paths.scum_server`)

**Nota**: Suporta caminhos aninhados usando ponto (`.`). Exemplo: `paths.scum_server` para acessar a subseção `scum_server` dentro de `paths`.

**Resposta de Sucesso (200):**
```json
{
  "success": true,
  "data": {
    "paths": {},
    "server": {},
    "api": {
      "host": "0.0.0.0",
      "port": 3000,
      "debug": false
    }
  },
  "timestamp": 1701504000
}
```

#### **Listar Seções Disponíveis**
```
GET /api/config/sections
```

Retorna lista de todas as seções disponíveis no `config.json`.

**Query Params (opcional):**
- `include_nested` (boolean): Incluir subseções aninhadas (padrão: `true`)

**Resposta de Sucesso (200):**
```json
{
  "success": true,
  "data": {
    "sections": [
      "paths",
      "paths.application",
      "paths.scum_server",
      "server",
      "api",
      "scheduler"
    ],
    "total": 6
  },
  "timestamp": 1701504000
}
```

**Nota**: Quando `include_nested=true`, a lista inclui tanto seções de primeiro nível quanto subseções aninhadas (usando notação com ponto).

#### **Atualizar Seções (Merge Profundo)**
```
PATCH /api/config
```

Atualiza uma ou mais seções do `config.json`. Faz merge profundo, preservando campos não especificados.

**Body:**
```json
{
  "sections": {
    "api": {
      "port": 3001,
      "debug": true
    },
    "scheduler": {
      "enabled": false
    }
  },
  "create_backup": true
}
```

**Resposta de Sucesso (200):**
```json
{
  "success": true,
  "message": "Configuração atualizada com sucesso",
  "data": {
    "updated_sections": ["api", "scheduler"],
    "requires_restart": ["api", "scheduler"]
  },
  "timestamp": 1701504000
}
```

#### **Substituir Configuração Completa**
```
PUT /api/config
```

Substitui toda a configuração do `config.json`. **Use com cuidado**.

**Body:**
```json
{
  "config": {
    "paths": {},
    "server": {},
    "api": {}
  },
  "create_backup": true
}
```

**Resposta de Sucesso (200):**
```json
{
  "success": true,
  "message": "Configuração completa atualizada",
  "data": {
    "requires_restart": true
  },
  "timestamp": 1701504000
}
```

#### **Atualizar Seção Específica**
```
PUT /api/config/{section}
```

Atualiza uma seção completa do `config.json`. Aceita qualquer campo (conhecido ou customizado). Útil para salvar múltiplas alterações de uma vez.

**Path Params:**
- `section` (string): Nome da seção (ex: `api`, `server`, `scheduler`, `paths.scum_server`)

**Nota**: Suporta caminhos aninhados usando ponto (`.`). Exemplo: `paths.scum_server` para atualizar a subseção `scum_server` dentro de `paths`.

**Body:**
```json
{
  "host": "0.0.0.0",
  "port": 3001,
  "debug": true,
  "custom_field": "value"
}
```

**Nota**: O body deve ser um objeto direto com os campos da seção, não um objeto aninhado.

**Query Params (opcional):**
- `create_backup` (boolean): Criar backup antes de atualizar (padrão: `true`)

**Resposta de Sucesso (200):**
```json
{
  "success": true,
  "message": "Seção \"api\" atualizada com sucesso",
  "data": {
    "section": "api",
    "updated_fields": ["host", "port", "debug"],
    "requires_restart": ["api"]
  },
  "timestamp": 1701504000
}
```

#### **Listar Backups**
```
GET /api/config/backup?limit=10
```

Lista backups disponíveis do `config.json`.

**Query Params (opcional):**
- `limit` (number): Número máximo de backups (padrão: 10)

**Resposta de Sucesso (200):**
```json
{
  "success": true,
  "data": {
    "backups": [
      {
        "filename": "config.backup.20251202_153045.json",
        "path": "data/config.backup.20251202_153045.json",
        "created_at": "2025-12-02T15:30:45",
        "size": 15234
      }
    ],
    "total": 1
  },
  "timestamp": 1701504000
}
```

#### **Restaurar Backup**
```
POST /api/config/restore
```

Restaura configuração de um backup. Cria backup da configuração atual antes de restaurar.

**Body:**
```json
{
  "backup_file": "config.backup.20251202_153045.json",
  "create_backup": true
}
```

**Resposta de Sucesso (200):**
```json
{
  "success": true,
  "message": "Configuração restaurada com sucesso",
  "data": {
    "restored_from": "config.backup.20251202_153045.json",
    "requires_restart": true
  },
  "timestamp": 1701504000
}
```

### **🔧 Funcionalidades**

- ✅ **Leitura completa** ou por seção do `config.json`
- ✅ **Atualização parcial** com merge profundo (preserva campos não especificados)
- ✅ **Substituição completa** da configuração
- ✅ **Backup automático** antes de modificar (mantém últimos 10 backups)
- ✅ **Listagem de backups** disponíveis
- ✅ **Restauração de backups** com backup da configuração atual
- ✅ **Preservação de ordem** das chaves no JSON

### **📚 Documentação Adicional**

- **Para desenvolvedores frontend**: [FRONTEND_CONFIG_API.md](./FRONTEND_CONFIG_API.md) - Documentação completa com exemplos TypeScript/React
- **Proposta original**: [PROPOSAL_CONFIG_ENDPOINT.md](../PROPOSAL_CONFIG_ENDPOINT.md) - Planejamento e especificações

---

## 🔔 **Sistema de Webhooks (webhooks.json)**

Sistema de gerenciamento de webhooks do Discord para notificações do servidor SCUM. Permite configurar, atualizar e gerenciar URLs de webhooks através de endpoints REST.

### **📡 Endpoints Disponíveis**

#### **Obter Todos os Webhooks**
```
GET /api/webhooks
```

Retorna todos os webhooks configurados no `webhooks.json`.

**Query Params (opcional):**
- `webhook` (string): Nome do webhook específico para retornar apenas um

**Resposta de Sucesso (200):**
```json
{
  "success": true,
  "data": {
    "serverstatus": "https://discord.com/api/webhooks/...",
    "new_player": "https://discord.com/api/webhooks/...",
    "players_online": "https://discord.com/api/webhooks/...",
    "vehicle_registration": "https://discord.com/api/webhooks/...",
    "chat_in_game": "https://discord.com/api/webhooks/..."
  },
  "timestamp": 1701504000
}
```

#### **Obter Webhook Específico**
```
GET /api/webhooks?webhook=serverstatus
```

ou

```
GET /api/webhooks/serverstatus
```

Retorna apenas um webhook específico.

**Resposta de Sucesso (200):**
```json
{
  "success": true,
  "data": {
    "serverstatus": "https://discord.com/api/webhooks/..."
  },
  "timestamp": 1701504000
}
```

**Resposta de Erro (404):**
```json
{
  "success": false,
  "error": "Webhook \"serverstatus\" não encontrado"
}
```

#### **Listar Nomes dos Webhooks**
```
GET /api/webhooks/names
```

Retorna lista com todos os nomes de webhooks disponíveis.

**Resposta de Sucesso (200):**
```json
{
  "success": true,
  "data": {
    "webhooks": [
      "serverstatus",
      "new_player",
      "players_online",
      "vehicle_registration",
      "chat_in_game"
    ],
    "total": 5
  },
  "timestamp": 1701504000
}
```

#### **Atualizar Múltiplos Webhooks**
```
PATCH /api/webhooks
```

Atualiza múltiplos webhooks de uma vez. Mantém webhooks não especificados.

**Body:**
```json
{
  "webhooks": {
    "serverstatus": "https://discord.com/api/webhooks/NOVA_URL",
    "new_player": "https://discord.com/api/webhooks/OUTRA_URL"
  },
  "create_backup": true
}
```

**Resposta de Sucesso (200):**
```json
{
  "success": true,
  "message": "Webhooks atualizados com sucesso",
  "data": {
    "updated_webhooks": ["serverstatus", "new_player"]
  },
  "timestamp": 1701504000
}
```

#### **Substituir Todos os Webhooks**
```
PUT /api/webhooks
```

Substitui completamente o arquivo `webhooks.json` com novos valores.

**Body:**
```json
{
  "webhooks": {
    "serverstatus": "https://discord.com/api/webhooks/...",
    "new_player": "https://discord.com/api/webhooks/...",
    "players_online": "https://discord.com/api/webhooks/..."
  },
  "create_backup": true
}
```

**Resposta de Sucesso (200):**
```json
{
  "success": true,
  "message": "Webhooks completos atualizados",
  "timestamp": 1701504000
}
```

#### **Atualizar Webhook Específico**
```
PUT /api/webhooks/serverstatus
```

Atualiza um webhook específico (apenas webhooks existentes).

**Body:**
```json
{
  "url": "https://discord.com/api/webhooks/NOVA_URL",
  "create_backup": true
}
```

**Query Params (opcional):**
- `create_backup` (boolean): Se deve criar backup antes de atualizar (padrão: true)

**Resposta de Sucesso (200):**
```json
{
  "success": true,
  "message": "Webhook \"serverstatus\" atualizado com sucesso",
  "data": {
    "webhook_name": "serverstatus",
    "url": "https://discord.com/api/webhooks/NOVA_URL"
  },
  "timestamp": 1701504000
}
```

**Resposta de Erro (404):**
```json
{
  "success": false,
  "error": "Webhook 'serverstatus' não existe. Apenas atualização de webhooks existentes é permitida."
}
```

#### **Testar Webhook (por nome)**
```
POST /api/webhooks/serverstatus/test
```

Envia uma mensagem de teste para o webhook configurado.

**Resposta de Sucesso (200):**
```json
{
  "success": true,
  "message": "Webhook testado com sucesso",
  "data": {
    "webhook_name": "serverstatus",
    "webhook_url": "https://discord.com/api/webhooks/...",
    "status_code": 204
  },
  "timestamp": 1701504000
}
```

**Resposta de Erro (404):**
```json
{
  "success": false,
  "error": "Webhook \"serverstatus\" não encontrado"
}
```

**Resposta de Erro (400):**
```json
{
  "success": false,
  "message": "Erro ao testar webhook: 404",
  "data": {
    "webhook_name": "serverstatus",
    "status_code": 404,
    "error": "Unknown Webhook"
  },
  "timestamp": 1701504000
}
```

#### **Testar Webhook (por URL)**
```
POST /api/webhooks/test
```

Testa um webhook enviando uma mensagem de teste usando a URL diretamente (útil para testar antes de salvar).

**Body:**
```json
{
  "url": "https://discord.com/api/webhooks/SUA_URL_AQUI"
}
```

**Resposta de Sucesso (200):**
```json
{
  "success": true,
  "message": "Webhook testado com sucesso",
  "data": {
    "webhook_url": "https://discord.com/api/webhooks/...",
    "status_code": 204
  },
  "timestamp": 1701504000
}
```

**Resposta de Erro (400):**
```json
{
  "success": false,
  "message": "Erro ao testar webhook: 404",
  "data": {
    "webhook_url": "https://discord.com/api/webhooks/...",
    "status_code": 404,
    "error": "Unknown Webhook"
  },
  "timestamp": 1701504000
}
```

#### **Listar Backups**
```
GET /api/webhooks/backup?limit=10
```

Lista backups disponíveis do `webhooks.json`.

**Query Params (opcional):**
- `limit` (number): Número máximo de backups (padrão: 10)

**Resposta de Sucesso (200):**
```json
{
  "success": true,
  "data": {
    "backups": [
      {
        "filename": "webhooks.backup.20251202_153045.json",
        "path": "data/webhooks.backup.20251202_153045.json",
        "created_at": "2025-12-02T15:30:45",
        "size": 1234
      }
    ],
    "total": 1
  },
  "timestamp": 1701504000
}
```

#### **Restaurar Backup**
```
POST /api/webhooks/restore
```

Restaura webhooks de um backup. Cria backup dos webhooks atuais antes de restaurar.

**Body:**
```json
{
  "backup_file": "webhooks.backup.20251202_153045.json",
  "create_backup": true
}
```

**Resposta de Sucesso (200):**
```json
{
  "success": true,
  "message": "Webhooks restaurados com sucesso",
  "data": {
    "restored_from": "webhooks.backup.20251202_153045.json"
  },
  "timestamp": 1701504000
}
```

### **🔧 Funcionalidades**

- ✅ **Leitura completa** ou webhook específico do `webhooks.json`
- ✅ **Atualização parcial** de múltiplos webhooks
- ✅ **Substituição completa** de todos os webhooks
- ✅ **Atualização** de webhook individual (apenas URLs de webhooks existentes)
- ✅ **Teste de webhooks** enviando mensagens de teste
- ✅ **Teste por URL** antes de salvar no arquivo
- ✅ **Backup automático** antes de modificar (mantém últimos 10 backups)
- ✅ **Listagem de backups** disponíveis
- ✅ **Restauração de backups** com backup dos webhooks atuais
- ✅ **Preservação de ordem** das chaves no JSON
- ⚠️ **Não permite criar** novos webhooks (apenas atualização de existentes)
- ⚠️ **Não permite deletar** webhooks (estrutura padrão preservada)

### **📚 Documentação Adicional**

- **Para desenvolvedores frontend**: [FRONTEND_WEBHOOKS_API.md](./FRONTEND_WEBHOOKS_API.md) - Documentação completa com exemplos TypeScript/React, hooks e componentes

---

## 🚗 **Sistema de Verificação de Veículos**

Sistema de verificação periódica que verifica se os veículos registrados no SSM.db ainda existem no SCUM.db.

### **📡 Endpoints Disponíveis**

#### **Status do Serviço**
```
GET /api/vehicles/verification/status
```
Retorna o status atual do serviço de verificação periódica.

#### **Iniciar Serviço**
```
POST /api/vehicles/verification/start
```
Inicia o serviço de verificação periódica. Executa uma verificação imediata e agenda as próximas execuções.

#### **Parar Serviço**
```
POST /api/vehicles/verification/stop
```
Para o serviço de verificação periódica.

#### **Executar Verificação Manual**
```
POST /api/vehicles/verification/run-now
```
Executa uma verificação manual imediata, independente do agendamento.

### **🔧 Configuração**

O serviço é configurado no arquivo `config.json`:

```json
{
  "vehicle_verification": {
    "enabled": true,
    "auto_start": true,
    "verification_interval_hours": 24
  }
}
```

### **📚 Documentação Completa**

Para mais detalhes, consulte: [VEHICLE_VERIFICATION_ENDPOINTS.md](./VEHICLE_VERIFICATION_ENDPOINTS.md)

---

## 📍 **Sistema de GPS**

Sistema de sincronização de GPS que obtém a localização tridimensional (X, Y, Z) dos jogadores online em tempo real diretamente do servidor de jogo via comandos RCON (`ListPlayers`).

### **📡 Endpoints Disponíveis**

#### **Status do Serviço**
```
GET /api/gps/sync/status
```
Retorna o status atual do serviço de sincronização de GPS.

#### **Iniciar Serviço**
```
POST /api/gps/sync/start
```
Inicia o serviço de sincronização de GPS. Executa uma sincronização imediata e agenda as próximas execuções.

#### **Parar Serviço**
```
POST /api/gps/sync/stop
```
Para o serviço de sincronização de GPS.

#### **Executar Sincronização Manual**
```
POST /api/gps/sync/run-now
```
Executa uma sincronização manual imediata, independente do agendamento.

#### **Obter GPS dos Jogadores Online**
```
GET /api/gps/online
```
Obtém dados de GPS apenas dos jogadores que estão online no momento.

### **🔧 Configuração**

O serviço é configurado no arquivo `config.json`:

```json
{
  "player_gps_sync": {
    "enabled": true,
    "auto_start": true,
    "sync_interval_seconds": 30
  }
}
```

### **📚 Documentação Completa**

- [GPS_ENDPOINTS.md](./GPS_ENDPOINTS.md) - Documentação técnica completa dos endpoints
- [FRONTEND_GPS_API.md](./FRONTEND_GPS_API.md) - Documentação para desenvolvedor frontend (TypeScript, exemplos, fluxos)

---

## 👥 **Endpoints de Players (Tabela Players)**

Endpoints para gerenciamento de players cadastrados diretamente na tabela `players` do banco SSM.db.

### **📡 Endpoints**

#### **Listar Todos os Players**
```
GET /api/players
```
Lista todos os players cadastrados na tabela `players` do banco SSM.db.

**Parâmetros Query (opcionais):**
- `limit` (number): Número máximo de registros (padrão: 100, intervalo suportado: 1–1000)
- `offset` (number): Deslocamento para paginação (padrão: 0, mínimo: 0)
- `sort_by` (string): Campo de ordenação (`last_seen`, `first_seen`, `player_name`, `total_playtime`, `total_sessions`, `created_at`, `vehicles_total`). Padrão: `last_seen`
- `sort_order` (string): Direção da ordenação (`asc` ou `desc`). Padrão: `desc`

**Resposta de Sucesso (200):**
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
        "created_at": "2025-10-27 22:21:01䀢
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

**Resposta de Erro (500):**
```json
{
  "success": false,
  "error": "Erro específico"
}
```

#### **Resumo de Veículos por Jogador**
```
GET /api/players/vehicles/summary
```
Retorna a contagem de veículos (total e por status) para os jogadores da página corrente.

**Parâmetros Query (opcionais):**
- `limit` (number): Número máximo de jogadores (padrão: 100, intervalo 1–1000)
- `offset` (number): Deslocamento para paginação (padrão: 0, mínimo: 0)
- `steam_id` (string): Filtra o resumo para um jogador específico
- `sort_by` (string): Campo de ordenação (`last_seen`, `first_seen`, `player_name`, `total_playtime`, `total_sessions`, `created_at`, `vehicles_total`). Padrão: `last_seen`
- `sort_order` (string): Direção da ordenação (`asc` ou `desc`). Padrão: `desc`

> Utilize os mesmos valores de `sort_by` e `sort_order` aplicados no `/api/players` para manter a sincronização da tabela.

**Resposta de Sucesso (200):**
```json
{
  "success": true,
  "data": {
    "limit": 100,
    "offset": 0,
    "total": 317,
    "count": 100,
    "sort_by": "last_seen",
    "sort_order": "desc",
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

**Resposta de Erro (500):**
```json
{
  "success": false,
  "error": "mensagem"
}
```

#### **Atualizar Permissão do Comando /tm**
```
PUT /api/players/{steam_id}/permissao
```
ou
```
PATCH /api/players/{steam_id}/permissao
```

Atualiza a permissão do comando `/tm` para um jogador na tabela `players`.

**Parâmetros:**
- `steam_id` (path): Steam ID do jogador
- `permissao` (body): `0` (desativado) ou `1` (ativado)

**Body:**
```json
{
  "permissao": 1
}
```

**Resposta de Sucesso (200):**
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

**Resposta de Erro (400):**
```json
{
  "success": false,
  "error": "Campo 'permissao' é obrigatório"
}
```
ou
```json
{
  "success": false,
  "error": "Campo 'permissao' deve ser 0 ou 1"
}
```

**Resposta de Erro (404):**
```json
{
  "success": false,
  "error": "Jogador com steam_id 76561198040636105 não encontrado"
}
```

**Resposta de Erro (500):**
```json
{
  "success": false,
  "error": "Erro específico"
}
```

### **🎯 Funcionalidades**

- ✅ **Listagem completa** de todos os players cadastrados
- ✅ **Paginação** com `limit` e `offset`
- ✅ **Ordenação** por `last_seen` (mais recentes primeiro)
- ✅ **Atualização de permissão** do comando `/tm` (coluna `permissao`)
- ✅ **Validação** de dados (jogador existe, permissão válida)

### **📚 Observações**

- A coluna `permissao` na tabela `