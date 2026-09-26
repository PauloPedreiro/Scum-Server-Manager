# 🔐 Planejamento: Sistema de Autenticação Simplificado

## 📋 Visão Geral

Sistema de autenticação simples para proteger o painel de administração do backend SSM. Apenas um usuário admin padrão, sem cadastros ou emails.

---

## 🎯 Objetivos

1. **Autenticação Simples**: Login com username e senha
2. **Usuário Padrão**: Admin criado automaticamente na primeira execução
3. **Proteção de Rotas**: Endpoints administrativos requerem autenticação
4. **Mudança de Senha Obrigatória**: Forçar alteração no primeiro login
5. **Sessão Persistente**: JWT tokens para manter usuário logado
6. **Expansibilidade**: Suporte para criar moderadores no futuro
7. **Armazenamento**: Usar SSM.db (consistente com o sistema)

---

## 🗄️ Armazenamento de Dados

### **Tabela: `frontend_users` no SSM.db** ⭐

Armazenar usuários no banco de dados existente `SSM.db`:

```sql
CREATE TABLE IF NOT EXISTS frontend_users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username VARCHAR(50) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    password_changed INTEGER DEFAULT 0,
    is_active INTEGER DEFAULT 1,
    role VARCHAR(20) DEFAULT 'admin',  -- 'admin', 'moderator', ou outros roles futuros
    steam_id TEXT,  -- Vincular a tabela players (apenas para moderadores)
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    last_login DATETIME,
    last_password_change DATETIME,
    FOREIGN KEY (steam_id) REFERENCES players(steam_id) ON DELETE SET NULL
);

CREATE INDEX idx_frontend_users_username ON frontend_users(username);
CREATE INDEX idx_frontend_users_role ON frontend_users(role);
CREATE INDEX idx_frontend_users_steam_id ON frontend_users(steam_id);
```

**Campos:**
- `id`: ID único do usuário
- `username`: Nome de usuário (único, obrigatório)
- `password_hash`: Hash da senha (bcrypt)
- `password_changed`: Se a senha foi alterada (0 = não, 1 = sim)
- `is_active`: Se o usuário está ativo (1) ou desativado (0)
- `role`: Papel do usuário ('admin' ou 'moderator')
- `steam_id`: Steam ID do jogador (opcional, apenas para moderadores vinculados a players)
- `created_at`: Data de criação
- `updated_at`: Última atualização
- `last_login`: Último login bem-sucedido
- `last_password_change`: Data da última mudança de senha

**Vinculação com Tabela `players`:**
- `steam_id` referencia `players.steam_id`
- **Admin**: Não precisa de `steam_id` (pode ser NULL)
- **Moderador**: Pode ter `steam_id` vinculado ao jogador do servidor
- **Vantagens da vinculação**:
  - Mostrar informações do jogador no painel (nome, stats, etc.)
  - Verificar se jogador está online
  - Integração com sistema de permissões do jogo
  - Auditoria: saber qual jogador fez ações administrativas

**Vantagens:**
- ✅ Consistente com o resto do sistema (já usa SSM.db)
- ✅ Permite expansão futura (múltiplos usuários, moderadores)
- ✅ Fácil de fazer queries e gerenciar
- ✅ Backup automático junto com o banco
- ✅ Pode adicionar mais campos no futuro se necessário

**Inicialização Automática:**
- Ao iniciar o backend pela primeira vez, verifica se a tabela existe
- Se não existe, cria a tabela
- Verifica se existe usuário 'admin'
- Se não existe, cria usuário padrão:
  - `username`: "admin"
  - `password_hash`: Hash de "12345678910"
  - `password_changed`: 0 (false) - **FORÇA mudança no primeiro login**
  - `role`: "admin"
  - `is_active`: 1 (true)

**Fluxo de Senha:**
- **Admin padrão**: Criado com `password_changed = 0` → força mudança no primeiro login
- **Moderadores criados**: Admin pode criar com senha temporária e `password_changed = 0` → moderador é forçado a mudar no primeiro login
- **Segurança**: Todos os usuários devem mudar a senha inicial antes de usar o sistema

---

## 🔑 Sistema de Autenticação

### **JWT (JSON Web Tokens)**

**Fluxo:**
1. Usuário faz login com `admin` / `12345678910`
2. Backend valida credenciais
3. Se é primeiro login (`password_changed: false`), retorna flag `must_change_password: true`
4. Frontend redireciona para tela de mudança de senha
5. Após mudança, gera JWT token normal
6. Frontend armazena token e usa em requisições

**Estrutura do Token:**
```json
{
  "username": "admin",
  "password_changed": true,
  "exp": 1735689600
}
```

---

## 🔒 Segurança

### **1. Hash de Senhas**
- Usar **bcrypt** com salt automático
- Rounds: 12

### **2. Senha Inicial**
- Padrão: `12345678910`
- Hash armazenado no arquivo JSON
- **OBRIGATÓRIO** mudar no primeiro login

### **3. Validação de Tokens**
- Verificar assinatura JWT
- Verificar expiração (24 horas)
- Validar estrutura

### **4. Proteção de Rotas**
- Decorator `@require_auth` para rotas administrativas
- Endpoints públicos: `/api/health`, `/api/auth/login`

---

## 📡 Endpoints da API

### **1. POST /api/auth/login**

**Request:**
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
    "expires_in": 86400
  }
}
```

**Response (401):**
```json
{
  "success": false,
  "error": "Invalid credentials"
}
```

### **2. POST /api/auth/change-password**

**Request (sem token - primeiro login):**
```json
{
  "username": "admin",
  "current_password": "12345678910",
  "new_password": "NovaSenhaSegura123!"
}
```

**Request (com token - mudança normal):**
```json
{
  "current_password": "senha_atual",
  "new_password": "NovaSenhaSegura123!"
}
```

**Headers (opcional - se já tiver token):**
```
Authorization: Bearer <token>
```

**Response (200):**
```json
{
  "success": true,
  "data": {
    "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "message": "Password changed successfully",
    "password_changed": true,
    "expires_in": 86400
  }
}
```

**Nota:**
- Após mudança, atualiza `password_changed = 1` no banco
- Gera novo token JWT com `password_changed: true`
- Usuário pode agora acessar o sistema normalmente

**Response (400):**
```json
{
  "success": false,
  "error": "Current password is incorrect"
}
```

**Response (400):**
```json
{
  "success": false,
  "error": "New password must be at least 8 characters"
}
```

### **3. GET /api/auth/me**

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
    "role": "admin",
    "password_changed": true,
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
    "last_login": "2025-12-04T20:00:00"
  }
}
```

**Nota:**
- Se `steam_id` estiver vinculado, retorna também `player_name` e `player_id` da tabela `players`
- Facilita exibir informações do jogador no frontend

### **4. POST /api/auth/logout**

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

### **5. POST /api/auth/users** (Admin apenas)

**Headers:**
```
Authorization: Bearer <token>
```

**Request (sem vinculação):**
```json
{
  "username": "moderador1",
  "password": "senha_temporaria123",
  "role": "moderator"
}
```

**Request (com vinculação a player):**
```json
{
  "username": "moderador1",
  "password": "senha_temporaria123",
  "role": "moderator",
  "steam_id": "76561198012345678"
}
```

**Nota:**
- `steam_id` é opcional
- Se fornecido, deve existir na tabela `players`
- Vincula o moderador ao jogador do servidor
- Permite mostrar dados do jogador no painel

**Response (200):**
```json
{
  "success": true,
  "data": {
    "id": 2,
    "username": "moderador1",
    "role": "moderator",
    "is_active": true,
    "password_changed": false,
    "created_at": "2025-12-04T20:00:00",
    "message": "User created. Password must be changed on first login."
  }
}
```

**Nota:** 
- Usuário criado com `password_changed = 0` (false)
- Moderador será **forçado a mudar a senha** no primeiro login
- Admin define senha temporária ao criar
- Moderador define senha definitiva no primeiro acesso

**Response (400):**
```json
{
  "success": false,
  "error": "Username already exists"
}
```

### **6. GET /api/auth/users** (Admin apenas)

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
        "role": "admin",
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

**Nota:**
- Se `steam_id` estiver vinculado, inclui `player_name` da tabela `players`
- Facilita identificar qual jogador é o moderador

### **7. PUT /api/auth/users/<id>** (Admin apenas)

**Headers:**
```
Authorization: Bearer <token>
```

**Request:**
```json
{
  "is_active": false,
  "role": "moderator"
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
    "updated_at": "2025-12-04T20:00:00"
  }
}
```

### **8. DELETE /api/auth/users/<id>** (Admin apenas)

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

**Response (400):**
```json
{
  "success": false,
  "error": "Cannot delete admin user"
}
```

---

## 🛡️ Proteção de Rotas

> 📋 **Documento Completo de Segurança**: Veja `docs/SEGURANCA_ENDPOINTS.md` para a lista completa de quais endpoints devem ser protegidos e quais devem permanecer públicos.

### **Resumo de Proteção**

- **Públicos**: `GET /api/health`, `GET /api/health/detailed`, `GET /api/server/status`, `POST /api/auth/login`
- **Protegidos** (`@require_auth`): ~90 endpoints (controle, configuração, logs, players, etc.)
- **Admin Apenas** (`@require_admin`): ~5 endpoints (gerenciamento de usuários, operações destrutivas)

### **Decorator para Autenticação**

```python
from functools import wraps
from flask import request, jsonify
import jwt

def require_auth(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        token = None
        
        if 'Authorization' in request.headers:
            auth_header = request.headers['Authorization']
            try:
                token = auth_header.split(' ')[1]  # "Bearer <token>"
            except:
                return jsonify({
                    "success": False,
                    "error": "Invalid token format"
                }), 401
        
        if not token:
            return jsonify({
                "success": False,
                "error": "Token is missing"
            }), 401
        
        try:
            data = jwt.decode(token, SECRET_KEY, algorithms=['HS256'])
            request.current_user_id = data['user_id']
            request.current_username = data['username']
            request.current_role = data.get('role', 'admin')
            request.password_changed = data.get('password_changed', False)
        except jwt.ExpiredSignatureError:
            return jsonify({
                "success": False,
                "error": "Token has expired"
            }), 401
        except jwt.InvalidTokenError:
            return jsonify({
                "success": False,
                "error": "Invalid token"
            }), 401
        
        return f(*args, **kwargs)
    return decorated_function
```

### **Aplicação nas Rotas**

**Exemplos:**

```python
@app.route('/api/server/start', methods=['POST'])
@require_auth
def start_server():
    # Apenas usuários autenticados
    ...

@app.route('/api/config', methods=['PATCH'])
@require_auth
def update_config():
    # Apenas usuários autenticados
    ...

@app.route('/api/auth/users', methods=['POST'])
@require_admin
def create_user():
    # Apenas admins podem criar usuários
    ...
```

**Nota:** Veja `docs/SEGURANCA_ENDPOINTS.md` para a lista completa de todos os ~99 endpoints e suas categorias de proteção (Públicos, Protegidos, Admin Apenas).

---

## 🔧 Estrutura de Arquivos

```
core/
├── auth/
│   ├── __init__.py
│   ├── auth_manager.py      # Lógica principal (login, change password)
│   ├── user_manager.py      # CRUD de usuários no banco
│   ├── password_handler.py  # Hash/verificação de senhas (bcrypt)
│   ├── jwt_handler.py       # Geração/validação de JWT
│   └── decorators.py        # Decorators @require_auth, @require_admin
```

---

## ⚙️ Configuração

### **Adicionar ao `config.json`:**

```json
{
  "auth": {
    "enabled": true,
    "jwt_secret": "ssm-backend-secret-key-change-in-production",
    "jwt_expiration_hours": 24,
    "default_username": "admin",
    "default_password": "12345678910",
    "password_min_length": 8,
    "auto_create_admin": true
  }
}
```

---

## 🔄 Inicialização Automática

### **Ao iniciar o backend:**

1. Verifica se tabela `frontend_users` existe no `SSM.db`
2. Se não existe, cria a tabela
3. Verifica se existe usuário com `username = 'admin'`
4. Se não existe, cria usuário padrão:
   - `username`: "admin"
   - `password_hash`: Hash de "12345678910"
   - `password_changed`: 0 (false)
   - `role`: "admin"
   - `is_active`: 1 (true)

**Código de inicialização:**
```python
def init_auth_system():
    """Inicializar sistema de autenticação"""
    # Verificar/criar tabela
    ensure_auth_table()
    
    # Verificar/criar usuário admin padrão
    if not user_exists('admin'):
        create_default_admin()
```

---

## 🚀 Fluxo de Implementação

### **Fase 1: Estrutura Base**
1. Criar módulo `core/auth/`
2. Implementar `password_handler.py` (bcrypt)
3. Implementar `jwt_handler.py`
4. Implementar `user_manager.py` (CRUD de usuários no banco)
5. Criar função de inicialização que:
   - Cria tabela `frontend_users` se não existir
   - Cria usuário admin padrão se não existir

### **Fase 2: Autenticação**
1. Implementar `auth_manager.py`:
   - `login(username, password)` - Valida credenciais
   - `change_password(current, new)` - Muda senha
   - `get_auth_data()` - Lê dados do arquivo
   - `save_auth_data()` - Salva dados no arquivo
2. Criar decorator `@require_auth`
3. Criar endpoint `POST /api/auth/login`
4. Testar login com senha padrão

### **Fase 3: Mudança de Senha**
1. Implementar lógica de `password_changed` flag
2. Criar endpoint `POST /api/auth/change-password`
3. Validar que senha atual está correta
4. Validar que nova senha atende requisitos (min 8 caracteres)
5. Atualizar `password_changed: true` após mudança
6. Gerar novo token após mudança

### **Fase 4: Proteção de Rotas**
1. Consultar `docs/SEGURANCA_ENDPOINTS.md` para lista completa de endpoints
2. Aplicar `@require_auth` em ~90 endpoints protegidos:
   - Controle do servidor (start/stop/restart)
   - Configurações (config.json, server settings, webhooks)
   - Scheduler, Weather, Notifications
   - Logs, Players, Squads, Rankings
   - E outros endpoints administrativos
3. Aplicar `@require_admin` em ~5 endpoints admin apenas:
   - Gerenciamento de usuários (`/api/auth/users/*`)
   - Operações destrutivas (restore, force operations)
4. Manter públicos (~4 endpoints):
   - `/api/health`, `/api/health/detailed`
   - `/api/server/status`
   - `/api/auth/login`
5. Criar endpoint `GET /api/auth/me`
6. Criar endpoint `POST /api/auth/logout`

### **Fase 5: Inicialização e Gerenciamento**
1. Integrar inicialização no `init_components()`
2. Criar endpoints de gerenciamento de usuários (admin apenas):
   - `POST /api/auth/users` - Criar novo usuário (moderador)
   - `GET /api/auth/users` - Listar usuários
   - `PUT /api/auth/users/<id>` - Atualizar usuário
   - `DELETE /api/auth/users/<id>` - Deletar/desativar usuário
3. Implementar controle de roles (admin vs moderator)
4. Aplicar permissões baseadas em role (se necessário)

---

## 🔄 Fluxo de Primeiro Login

```
1. Usuário acessa frontend
2. Frontend tenta verificar token (não existe)
3. Redireciona para /login
4. Usuário digita: admin / 12345678910
5. POST /api/auth/login
6. Backend valida: password_changed = false
7. Retorna: { must_change_password: true }
8. Frontend mostra tela de mudança de senha
9. Usuário digita senha atual e nova senha
10. POST /api/auth/change-password
11. Backend valida senha atual
12. Backend valida nova senha (min 8 chars)
13. Backend atualiza hash e marca password_changed = true
14. Backend gera token JWT
15. Retorna token
16. Frontend armazena token e redireciona para dashboard
```

---

## 🔄 Fluxo de Login Normal (password_changed = 1)

```
1. Usuário acessa frontend
2. Frontend verifica token (existe e válido)
3. Se válido, mostra dashboard
4. Se inválido/expirado, redireciona para /login
5. Usuário digita: username / senha_atual
6. POST /api/auth/login
7. Backend valida credenciais
8. Backend verifica: password_changed = 1
9. Backend atualiza last_login = NOW()
10. Retorna token JWT (com password_changed: true)
11. Frontend armazena token e mostra dashboard
```

**Nota:** 
- Apenas usuários com `password_changed = 1` recebem token
- Usuários com `password_changed = 0` são forçados a mudar senha primeiro

---

## 📝 Dependências

Adicionar ao `requirements.txt`:

```
PyJWT>=2.8.0
bcrypt>=4.0.1
```

---

## ✅ Checklist de Implementação

- [ ] Criar estrutura `core/auth/`
- [ ] Implementar `password_handler.py` (bcrypt)
- [ ] Implementar `jwt_handler.py` (JWT)
- [ ] Implementar `user_manager.py` (CRUD no banco)
- [ ] Implementar `auth_manager.py` (lógica principal)
- [ ] Criar função de inicialização (criar tabela e admin padrão)
- [ ] Criar decorator `@require_auth`
- [ ] Criar decorator `@require_admin` (para rotas admin apenas)
- [ ] Criar endpoint `POST /api/auth/login`
- [ ] Criar endpoint `POST /api/auth/change-password`
- [ ] Criar endpoint `GET /api/auth/me`
- [ ] Criar endpoint `POST /api/auth/logout`
- [ ] Criar endpoints de gerenciamento de usuários (admin):
  - [ ] `POST /api/auth/users` - Criar usuário (com opção de vincular steam_id)
  - [ ] `GET /api/auth/users` - Listar usuários (com dados do player se vinculado)
  - [ ] `GET /api/auth/users/search-players` - Buscar players para vincular
  - [ ] `PUT /api/auth/users/<id>` - Atualizar usuário (incluindo steam_id)
  - [ ] `DELETE /api/auth/users/<id>` - Deletar usuário
- [ ] Implementar validação de steam_id (verificar se existe em players)
- [ ] Implementar JOIN com tabela players para retornar dados do jogador
- [ ] Integrar inicialização no `init_components()`
- [ ] Aplicar `@require_auth` nas rotas administrativas
- [ ] Adicionar configurações ao `config.json`
- [ ] Testes de autenticação
- [ ] Documentação

---

## 🎯 Vantagens desta Abordagem

1. **Simplicidade**: Usuário admin padrão, sem emails ou cadastros complexos
2. **Segurança**: Senha inicial forçada a mudar
3. **Expansibilidade**: Fácil adicionar moderadores no futuro
4. **Consistência**: Usa o mesmo banco (SSM.db) do resto do sistema
5. **Manutenção**: Fácil de gerenciar via SQL ou endpoints
6. **Backup**: Backup automático junto com o banco de dados
7. **Inicialização**: Criação automática na primeira execução

---

## 🔧 Reset de Senha (Se Necessário)

Se o admin esquecer a senha:

1. **Opção 1**: Via SQL direto no banco:
   ```sql
   UPDATE frontend_users 
   SET password_hash = '<novo_hash_da_senha_padrao>',
       password_changed = 0
   WHERE username = 'admin';
   ```
   (Gerar hash de "12345678910" e atualizar)

2. **Opção 2**: Script de reset (futuro):
   - Criar endpoint admin especial para reset
   - Ou script Python standalone

3. **Opção 3**: Deletar usuário admin e reiniciar backend (recria automaticamente)

---

## 🚀 Escalabilidade e Expansão Futura

### **Sistema Preparado para Escalonar**

O sistema foi projetado para ser facilmente escalonável e permitir novos tipos de acesso no futuro:

#### **1. Novos Tipos de Roles**

A coluna `role` é flexível e pode suportar novos tipos sem alterar a estrutura:

**Roles Atuais:**
- `admin` - Administrador completo
- `moderator` - Moderador do servidor

**Possíveis Roles Futuros:**
- `viewer` - Apenas visualização (read-only)
- `operator` - Operador (pode iniciar/parar servidor, mas não configurar)
- `support` - Suporte técnico (acesso limitado)
- `analyst` - Analista (acesso apenas a relatórios e estatísticas)
- `custom_role` - Roles personalizados por servidor

**Como Adicionar:**
- Apenas criar usuário com novo `role`
- Sistema já suporta qualquer string em `role`
- Pode criar decorators específicos: `@require_operator`, `@require_viewer`, etc.

**Exemplo:**
```python
# Criar novo tipo de usuário
POST /api/auth/users
{
  "username": "analista1",
  "password": "senha_temp",
  "role": "analyst"  // Novo role
}
```

#### **2. Sistema de Permissões Granulares (Futuro)**

Pode evoluir para sistema de permissões mais detalhado:

**Opção A: Coluna de Permissões JSON**
```sql
ALTER TABLE frontend_users 
ADD COLUMN permissions TEXT;  -- JSON com permissões específicas

-- Exemplo:
{
  "server": {
    "start": true,
    "stop": true,
    "restart": false
  },
  "config": {
    "read": true,
    "write": false
  },
  "players": {
    "view": true,
    "edit": false,
    "ban": false
  },
  "reports": {
    "view": true,
    "export": true
  }
}
```

**Opção B: Tabela de Permissões Separada**
```sql
CREATE TABLE frontend_user_permissions (
    user_id INTEGER,
    permission_key VARCHAR(100),
    granted INTEGER DEFAULT 1,
    FOREIGN KEY (user_id) REFERENCES frontend_users(id)
);

-- Exemplo de permissões:
-- "server.start", "server.stop", "config.read", "config.write", etc.
```

#### **3. Múltiplos Admins e Hierarquia**

- Sistema já suporta múltiplos usuários
- Pode ter vários admins
- Cada um com seu próprio login/senha
- Pode implementar hierarquia de roles:

```
admin (nível 5) - Acesso total
  └─ operator (nível 4) - Operações do servidor
      └─ moderator (nível 3) - Moderação
          └─ viewer (nível 2) - Apenas visualização
              └─ guest (nível 1) - Acesso mínimo
```

#### **4. Grupos de Usuários (Futuro)**

```sql
CREATE TABLE frontend_user_groups (
    id INTEGER PRIMARY KEY,
    name VARCHAR(50),
    description TEXT,
    permissions TEXT  -- JSON com permissões do grupo
);

CREATE TABLE frontend_user_group_members (
    user_id INTEGER,
    group_id INTEGER,
    FOREIGN KEY (user_id) REFERENCES frontend_users(id),
    FOREIGN KEY (group_id) REFERENCES frontend_user_groups(id)
);
```

**Vantagens:**
- Atribuir permissões a grupos
- Usuários herdam permissões do grupo
- Fácil gerenciar múltiplos usuários

#### **5. Integração com Sistema de Permissões do Jogo**

- Moderadores vinculados a `steam_id` podem ter permissões no jogo
- Sincronizar permissões entre frontend e servidor SCUM
- Exemplo: Moderador no frontend = Elevated User no jogo
- Pode criar roles específicos para permissões do jogo

#### **6. Expansão de Campos**

A tabela pode ser expandida facilmente:

```sql
-- Exemplos de campos futuros:
ALTER TABLE frontend_users 
ADD COLUMN email VARCHAR(255);  -- Para notificações

ALTER TABLE frontend_users 
ADD COLUMN phone VARCHAR(20);  -- Para 2FA

ALTER TABLE frontend_users 
ADD COLUMN two_factor_enabled INTEGER DEFAULT 0;  -- 2FA

ALTER TABLE frontend_users 
ADD COLUMN session_timeout INTEGER DEFAULT 86400;  -- Timeout personalizado

ALTER TABLE frontend_users 
ADD COLUMN allowed_ips TEXT;  -- JSON com IPs permitidos
```

### **Vantagens da Arquitetura Atual**

1. **Flexível**: Campo `role` aceita qualquer string
2. **Extensível**: Fácil adicionar novos campos na tabela
3. **Modular**: Decorators podem ser criados para novos roles
4. **Escalável**: Suporta muitos usuários sem problemas
5. **Integrável**: Vinculação com `players` permite integrações futuras
6. **Backward Compatible**: Novos campos não quebram código existente

### **Exemplo de Expansão Futura**

```python
# Decorator para novo role
def require_operator(f):
    @wraps(f)
    @require_auth
    def decorated_function(*args, **kwargs):
        if request.current_role not in ['admin', 'operator']:
            return jsonify({
                "success": False,
                "error": "Operator access required"
            }), 403
        return f(*args, **kwargs)
    return decorated_function

# Decorator com permissões granulares
def require_permission(permission_key):
    def decorator(f):
        @wraps(f)
        @require_auth
        def decorated_function(*args, **kwargs):
            user = get_user_by_id(request.current_user_id)
            if not has_permission(user, permission_key):
                return jsonify({
                    "success": False,
                    "error": f"Permission '{permission_key}' required"
                }), 403
            return f(*args, **kwargs)
        return decorated_function
    return decorator

# Aplicar em rotas
@app.route('/api/server/start', methods=['POST'])
@require_operator  # Admin ou Operator podem iniciar
def start_server():
    ...

@app.route('/api/config', methods=['PATCH'])
@require_permission('config.write')  # Permissão específica
def update_config():
    ...
```

### **Roadmap de Expansão Sugerido**

**Fase 1 (Atual):**
- ✅ Admin e Moderador
- ✅ Vinculação com players

**Fase 2 (Futuro):**
- ⏳ Novos roles (viewer, operator, etc.)
- ⏳ Permissões granulares por endpoint

**Fase 3 (Futuro):**
- ⏳ Grupos de usuários
- ⏳ Hierarquia de roles
- ⏳ 2FA (Two-Factor Authentication)

**Fase 4 (Futuro):**
- ⏳ Integração com sistema de permissões do jogo
- ⏳ Sincronização automática de permissões
- ⏳ Auditoria avançada

---

## 📚 Próximos Passos

1. **Revisar este planejamento**
2. **Aprovar estrutura simplificada**
3. **Iniciar implementação pela Fase 1**
4. **Planejar expansões futuras conforme necessidade**

