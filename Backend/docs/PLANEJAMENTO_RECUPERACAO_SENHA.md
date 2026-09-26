# 🔐 Planejamento: Sistema de Recuperação de Senha Admin

**Data:** 2025-01-XX  
**Status:** 📝 Planejamento

---

## 🎯 Objetivo

Implementar um sistema seguro de recuperação de senha para o usuário admin do frontend, utilizando o webhook `log-ssm` do Discord para enviar o token de recuperação.

---

## 📊 Análise do Sistema Atual

### **Componentes Disponíveis:**

1. **Sistema de Autenticação:**
   - ✅ `AuthManager` - Gerencia autenticação
   - ✅ `UserManager` - CRUD de usuários no SSM.db
   - ✅ `PasswordHandler` - Hash/verificação de senhas (bcrypt)
   - ✅ Tabela `frontend_users` no SSM.db

2. **Webhook Discord:**
   - ✅ `DiscordWebhook` (`core/webhooks/discord_webhook.py`)
   - ✅ Webhook `log-ssm` configurado em `data/webhooks.json`
   - ✅ Método `send_webhook()` disponível

3. **Estrutura Atual:**
   - Usuário admin criado automaticamente com senha padrão
   - Senhas hasheadas com bcrypt
   - JWT para autenticação

---

## 🔧 Proposta de Implementação

### **1. Estrutura de Dados**

#### **Nova Tabela: `password_reset_tokens`**

```sql
CREATE TABLE IF NOT EXISTS password_reset_tokens (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username VARCHAR(50) NOT NULL,
    token VARCHAR(64) UNIQUE NOT NULL,
    expires_at DATETIME NOT NULL,
    used INTEGER DEFAULT 0,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    ip_address TEXT,
    FOREIGN KEY (username) REFERENCES frontend_users(username) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_password_reset_tokens_token ON password_reset_tokens(token);
CREATE INDEX IF NOT EXISTS idx_password_reset_tokens_username ON password_reset_tokens(username);
CREATE INDEX IF NOT EXISTS idx_password_reset_tokens_expires_at ON password_reset_tokens(expires_at);
```

**Campos:**
- `id`: ID único do token
- `username`: Username do usuário que solicitou reset
- `token`: Token único de 64 caracteres (hex)
- `expires_at`: Data/hora de expiração (15 minutos)
- `used`: Se o token já foi usado (0 = não, 1 = sim)
- `created_at`: Data de criação
- `ip_address`: IP de origem (opcional, para auditoria)

---

### **2. Fluxo de Recuperação**

#### **Passo 1: Solicitar Reset de Senha**
- **Endpoint:** `POST /api/auth/request-password-reset`
- **Público:** Sim (não requer autenticação)
- **Request:**
  ```json
  {
    "username": "admin"
  }
  ```
- **Validações:**
  - ✅ Verificar se username existe
  - ✅ Verificar se usuário está ativo
  - ✅ Rate limiting: máximo 3 tentativas por IP a cada 15 minutos
  - ✅ Rate limiting: máximo 1 tentativa por username a cada 5 minutos

- **Ações:**
  1. Gerar token único (64 caracteres hex)
  2. Salvar token no banco com expiração de 15 minutos
  3. Enviar notificação via webhook `log-ssm` com o token
  4. Retornar resposta genérica (não revelar se usuário existe)

- **Response (sempre 200, mesmo se usuário não existir):**
  ```json
  {
    "success": true,
    "message": "Se o usuário existir, um token de recuperação foi enviado via Discord"
  }
  ```

#### **Passo 2: Resetar Senha com Token**
- **Endpoint:** `POST /api/auth/reset-password`
- **Público:** Sim (não requer autenticação)
- **Request:**
  ```json
  {
    "token": "abc123...",
    "new_password": "NovaSenhaSegura123!"
  }
  ```
- **Validações:**
  - ✅ Token existe e não foi usado
  - ✅ Token não expirou
  - ✅ Nova senha atende requisitos (mínimo 8 caracteres)
  - ✅ Verificar força da senha (opcional)

- **Ações:**
  1. Buscar token no banco
  2. Verificar expiração
  3. Verificar se já foi usado
  4. Hash da nova senha
  5. Atualizar senha do usuário
  6. Marcar token como usado
  7. Enviar notificação via webhook `log-ssm` confirmando reset
  8. Invalidar todos os tokens JWT do usuário (opcional)

- **Response (200):**
  ```json
  {
    "success": true,
    "message": "Senha alterada com sucesso"
  }
  ```

- **Response (400):**
  ```json
  {
    "success": false,
    "error": "Token inválido ou expirado"
  }
  ```

---

### **3. Notificações Discord**

#### **Notificação 1: Token Gerado**

**Webhook:** `log-ssm`

**Embed:**
```json
{
  "embeds": [{
    "title": "🔐 Solicitação de Recuperação de Senha",
    "description": "Uma solicitação de recuperação de senha foi gerada para o usuário admin.",
    "color": 16776960,  // Amarelo (warning)
    "fields": [
      {
        "name": "👤 Usuário",
        "value": "admin",
        "inline": true
      },
      {
        "name": "🔑 Token",
        "value": "`abc123def456...`",
        "inline": false
      },
      {
        "name": "⏰ Expira em",
        "value": "15 minutos",
        "inline": true
      },
      {
        "name": "🌐 IP",
        "value": "192.168.1.100",
        "inline": true
      }
    ],
    "footer": {
      "text": "SSM Backend - Sistema de Autenticação"
    },
    "timestamp": "2025-01-XXT..."
  }]
}
```

#### **Notificação 2: Senha Resetada**

**Webhook:** `log-ssm`

**Embed:**
```json
{
  "embeds": [{
    "title": "✅ Senha Resetada com Sucesso",
    "description": "A senha do usuário admin foi alterada através do sistema de recuperação.",
    "color": 65280,  // Verde (success)
    "fields": [
      {
        "name": "👤 Usuário",
        "value": "admin",
        "inline": true
      },
      {
        "name": "⏰ Data/Hora",
        "value": "DD/MM/YYYY HH:MM:SS",
        "inline": true
      }
    ],
    "footer": {
      "text": "SSM Backend - Sistema de Autenticação"
    },
    "timestamp": "2025-01-XXT..."
  }]
}
```

#### **Notificação 3: Tentativa de Reset com Token Inválido**

**Webhook:** `log-ssm` (opcional, apenas para segurança)

**Embed:**
```json
{
  "embeds": [{
    "title": "⚠️ Tentativa de Reset com Token Inválido",
    "description": "Alguém tentou usar um token de recuperação inválido ou expirado.",
    "color": 15158332,  // Vermelho (error)
    "fields": [
      {
        "name": "🔑 Token",
        "value": "`abc123...` (inválido/expirado)",
        "inline": false
      },
      {
        "name": "🌐 IP",
        "value": "192.168.1.100",
        "inline": true
      }
    ],
    "footer": {
      "text": "SSM Backend - Sistema de Autenticação"
    },
    "timestamp": "2025-01-XXT..."
  }]
}
```

---

### **4. Segurança**

#### **Proteções Implementadas:**

1. **Rate Limiting:**
   - Máximo 3 solicitações por IP a cada 15 minutos
   - Máximo 1 solicitação por username a cada 5 minutos
   - Armazenar tentativas em memória (dict) ou banco temporário

2. **Token Seguro:**
   - 64 caracteres hexadecimais (256 bits de entropia)
   - Gerado com `secrets.token_hex(32)`
   - Expiração de 15 minutos
   - Uso único (marcado como usado após reset)

3. **Validação de Senha:**
   - Mínimo 8 caracteres
   - Verificar força da senha (opcional)

4. **Resposta Genérica:**
   - Sempre retornar sucesso na solicitação (não revelar se usuário existe)
   - Prevenir enumeração de usuários

5. **Auditoria:**
   - Registrar IP de origem
   - Logs de todas as tentativas
   - Notificações Discord para ações importantes

6. **Limpeza Automática:**
   - Remover tokens expirados periodicamente (opcional)
   - Limpar tokens antigos (> 24 horas)

---

### **5. Estrutura de Arquivos**

```
core/
├── auth/
│   ├── __init__.py
│   ├── auth_manager.py          # Existente
│   ├── user_manager.py          # Existente
│   ├── password_handler.py       # Existente
│   ├── jwt_handler.py           # Existente
│   ├── decorators.py            # Existente
│   └── password_reset.py         # NOVO - Lógica de reset
```

**Novo arquivo:** `core/auth/password_reset.py`

**Responsabilidades:**
- Gerar tokens únicos
- Validar tokens
- Gerenciar tokens no banco
- Rate limiting
- Integração com DiscordWebhook

---

### **6. Endpoints no main.py**

#### **Endpoint 1: Solicitar Reset**
```python
@app.route('/api/auth/request-password-reset', methods=['POST'])
def request_password_reset():
    """Solicitar reset de senha"""
    # Implementação aqui
```

#### **Endpoint 2: Resetar Senha**
```python
@app.route('/api/auth/reset-password', methods=['POST'])
def reset_password():
    """Resetar senha com token"""
    # Implementação aqui
```

---

### **7. Fluxo Completo**

```
1. Usuário esqueceu senha
   ↓
2. Acessa endpoint /api/auth/request-password-reset
   ↓
3. Sistema valida rate limiting
   ↓
4. Gera token único (64 chars)
   ↓
5. Salva token no banco (expira em 15 min)
   ↓
6. Envia notificação Discord com token
   ↓
7. Usuário copia token do Discord
   ↓
8. Acessa endpoint /api/auth/reset-password
   ↓
9. Sistema valida token (existe, não usado, não expirado)
   ↓
10. Hash da nova senha
   ↓
11. Atualiza senha no banco
   ↓
12. Marca token como usado
   ↓
13. Envia notificação Discord confirmando reset
   ↓
14. Usuário faz login com nova senha
```

---

## ✅ Vantagens da Proposta

1. **Segurança:**
   - Tokens únicos e expiração curta
   - Rate limiting previne abuso
   - Uso único dos tokens
   - Resposta genérica previne enumeração

2. **Auditoria:**
   - Todas as ações registradas no Discord
   - IP de origem registrado
   - Logs completos

3. **Usabilidade:**
   - Processo simples (2 endpoints)
   - Notificação clara no Discord
   - Token fácil de copiar

4. **Integração:**
   - Usa webhook existente (`log-ssm`)
   - Usa componentes existentes (UserManager, PasswordHandler)
   - Não quebra funcionalidades existentes

---

## 🚨 Considerações Importantes

1. **Acesso ao Discord:**
   - O usuário precisa ter acesso ao canal do Discord onde o webhook `log-ssm` está configurado
   - Se não tiver acesso, não conseguirá recuperar a senha

2. **Alternativa Futura:**
   - Se necessário, pode adicionar email no futuro
   - Por enquanto, Discord é suficiente para o caso de uso

3. **Backup:**
   - Se o Discord falhar, o token ainda estará no banco (mas não acessível)
   - Considerar adicionar endpoint admin para listar tokens pendentes (futuro)

4. **Limpeza:**
   - Tokens expirados podem ser limpos periodicamente
   - Considerar job de limpeza automática

---

## 📝 Próximos Passos

1. ✅ Criar tabela `password_reset_tokens`
2. ✅ Implementar `core/auth/password_reset.py`
3. ✅ Adicionar endpoints em `main.py`
4. ✅ Integrar com DiscordWebhook
5. ✅ Implementar rate limiting
6. ✅ Testar fluxo completo
7. ✅ Documentar uso

---

## 🎯 Resumo

**Sistema simples e seguro de recuperação de senha que:**
- Gera token único de 64 caracteres
- Expira em 15 minutos
- Envia token via webhook Discord (`log-ssm`)
- Permite reset de senha sem autenticação
- Registra todas as ações para auditoria
- Protege contra abuso com rate limiting

**Ideal para:** Usuário admin que esqueceu a senha e tem acesso ao Discord do servidor.

