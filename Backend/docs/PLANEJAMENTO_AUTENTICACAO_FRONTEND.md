# 🔐 Planejamento: Sistema de Autenticação para Frontend

## 📋 Visão Geral

Sistema de autenticação para proteger o acesso ao frontend do SSM Backend, permitindo que apenas usuários autorizados acessem o painel de controle.

---

## 🎯 Objetivos

1. **Autenticação de Usuários**: Login com username/email e senha
2. **Proteção de Rotas**: Endpoints protegidos requerem autenticação
3. **Sessão Persistente**: Manter usuário logado (JWT tokens)
4. **Segurança**: Senhas hasheadas, proteção contra ataques comuns
5. **Gerenciamento de Usuários**: CRUD básico de usuários

---

## 🗄️ Armazenamento de Dados

### **Tabela: `frontend_users`**

Armazenar usuários no `SSM.db`:

```sql
CREATE TABLE IF NOT EXISTS frontend_users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username VARCHAR(50) UNIQUE NOT NULL,
    email VARCHAR(255) UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    is_active INTEGER DEFAULT 1,
    is_admin INTEGER DEFAULT 0,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    last_login DATETIME,
    failed_login_attempts INTEGER DEFAULT 0,
    locked_until DATETIME
);

CREATE INDEX idx_frontend_users_username ON frontend_users(username);
CREATE INDEX idx_frontend_users_email ON frontend_users(email);
```

### **Campos:**
- `id`: ID único do usuário
- `username`: Nome de usuário (único)
- `email`: Email (opcional, único se fornecido)
- `password_hash`: Hash da senha (bcrypt)
- `is_active`: Se o usuário está ativo (1) ou desativado (0)
- `is_admin`: Se é administrador (1) ou usuário comum (0)
- `created_at`: Data de criação
- `updated_at`: Última atualização
- `last_login`: Último login bem-sucedido
- `failed_login_attempts`: Tentativas de login falhadas
- `locked_until`: Data até quando a conta está bloqueada (proteção contra brute force)

---

## 🔑 Sistema de Autenticação

### **Opção 1: JWT (JSON Web Tokens)** ⭐ RECOMENDADO

**Vantagens:**
- Stateless (não precisa armazenar sessões no servidor)
- Escalável
- Funciona bem com APIs REST
- Tokens podem conter informações do usuário

**Fluxo:**
1. Usuário faz login → Backend valida credenciais
2. Backend gera JWT token com informações do usuário
3. Frontend armazena token (localStorage/sessionStorage)
4. Frontend envia token no header `Authorization: Bearer <token>` em cada requisição
5. Backend valida token antes de processar requisição

**Estrutura do Token:**
```json
{
  "user_id": 1,
  "username": "admin",
  "is_admin": 1,
  "exp": 1735689600  // Expiração (ex: 24 horas)
}
```

### **Opção 2: Sessions (Flask-Session)**

**Vantagens:**
- Mais controle sobre sessões
- Pode invalidar sessões facilmente

**Desvantagens:**
- Requer armazenamento no servidor
- Mais complexo para escalar

**Decisão: JWT** ✅

---

## 🔒 Segurança

### **1. Hash de Senhas**
- Usar **bcrypt** (biblioteca `bcrypt` ou `passlib`)
- Salt automático
- Rounds: 12 (balance entre segurança e performance)

### **2. Proteção contra Brute Force**
- Limitar tentativas de login (ex: 5 tentativas)
- Bloquear conta temporariamente após falhas
- Resetar contador após login bem-sucedido

### **3. Validação de Tokens**
- Verificar assinatura
- Verificar expiração
- Validar estrutura do token

### **4. HTTPS (Produção)**
- Sempre usar HTTPS em produção
- Tokens não devem ser enviados via HTTP não criptografado

### **5. CORS**
- Configurar CORS adequadamente
- Permitir apenas origens confiáveis

---

## 📡 Endpoints da API

### **1. POST /api/auth/login**

**Request:**
```json
{
  "username": "admin",
  "password": "senha123"
}
```

**Response (200):**
```json
{
  "success": true,
  "data": {
    "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "user": {
      "id": 1,
      "username": "admin",
      "email": "admin@example.com",
      "is_admin": true
    },
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

### **2. POST /api/auth/logout**

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
    "email": "admin@example.com",
    "is_admin": true,
    "last_login": "2025-12-04T20:00:00"
  }
}
```

### **4. POST /api/auth/change-password**

**Headers:**
```
Authorization: Bearer <token>
```

**Request:**
```json
{
  "current_password": "senha123",
  "new_password": "novaSenha456"
}
```

**Response (200):**
```json
{
  "success": true,
  "message": "Password changed successfully"
}
```

### **5. POST /api/auth/users** (Admin apenas)

**Headers:**
```
Authorization: Bearer <token>
```

**Request:**
```json
{
  "username": "novo_usuario",
  "email": "usuario@example.com",
  "password": "senha123",
  "is_admin": false
}
```

**Response (200):**
```json
{
  "success": true,
  "data": {
    "id": 2,
    "username": "novo_usuario",
    "email": "usuario@example.com",
    "is_admin": false,
    "created_at": "2025-12-04T20:00:00"
  }
}
```

### **6. GET /api/auth/users** (Admin apenas)

**Response (200):**
```json
{
  "success": true,
  "data": {
    "users": [
      {
        "id": 1,
        "username": "admin",
        "email": "admin@example.com",
        "is_admin": true,
        "is_active": true,
        "last_login": "2025-12-04T20:00:00"
      }
    ],
    "total": 1
  }
}
```

---

## 🛡️ Proteção de Rotas

### **Decorator para Autenticação**

```python
from functools import wraps
from flask import request, jsonify
import jwt

def require_auth(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        token = None
        
        # Verificar header Authorization
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
            # Validar token
            data = jwt.decode(token, SECRET_KEY, algorithms=['HS256'])
            current_user_id = data['user_id']
            # Adicionar user_id ao request para uso na rota
            request.current_user_id = current_user_id
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

### **Decorator para Admin**

```python
def require_admin(f):
    @wraps(f)
    @require_auth
    def decorated_function(*args, **kwargs):
        # Verificar se usuário é admin
        user = get_user_by_id(request.current_user_id)
        if not user or not user.get('is_admin'):
            return jsonify({
                "success": False,
                "error": "Admin access required"
            }), 403
        return f(*args, **kwargs)
    return decorated_function
```

### **Aplicação nas Rotas**

```python
@app.route('/api/server/start', methods=['POST'])
@require_auth
def start_server():
    # Apenas usuários autenticados podem iniciar servidor
    ...

@app.route('/api/auth/users', methods=['POST'])
@require_admin
def create_user():
    # Apenas admins podem criar usuários
    ...
```

---

## 🔧 Estrutura de Arquivos

```
core/
├── auth/
│   ├── __init__.py
│   ├── user_manager.py      # Gerenciamento de usuários (CRUD)
│   ├── password_handler.py  # Hash/verificação de senhas
│   ├── jwt_handler.py       # Geração/validação de JWT
│   ├── decorators.py        # Decorators @require_auth, @require_admin
│   └── auth_manager.py      # Lógica principal de autenticação
```

---

## ⚙️ Configuração

### **Adicionar ao `config.json`:**

```json
{
  "auth": {
    "enabled": true,
    "jwt_secret": "your-secret-key-here-change-in-production",
    "jwt_expiration_hours": 24,
    "max_login_attempts": 5,
    "lockout_duration_minutes": 30,
    "password_min_length": 8,
    "require_strong_password": true
  }
}
```

---

## 🚀 Fluxo de Implementação

### **Fase 1: Estrutura Base**
1. Criar tabela `frontend_users` no `SSM.db`
2. Criar módulo `core/auth/`
3. Implementar `password_handler.py` (bcrypt)
4. Implementar `jwt_handler.py`
5. Implementar `user_manager.py` (CRUD básico)

### **Fase 2: Autenticação**
1. Implementar `auth_manager.py` com lógica de login
2. Criar endpoint `POST /api/auth/login`
3. Criar decorator `@require_auth`
4. Testar login básico

### **Fase 3: Proteção de Rotas**
1. Aplicar `@require_auth` nas rotas críticas
2. Criar endpoint `GET /api/auth/me`
3. Criar endpoint `POST /api/auth/logout`
4. Testar proteção de rotas

### **Fase 4: Gerenciamento de Usuários**
1. Implementar endpoints de CRUD de usuários
2. Adicionar proteção contra brute force
3. Implementar mudança de senha
4. Criar usuário admin inicial

### **Fase 5: Integração Frontend**
1. Frontend implementa tela de login
2. Frontend armazena token
3. Frontend envia token em requisições
4. Frontend trata erros de autenticação

---

## 📝 Dependências

Adicionar ao `requirements.txt`:

```
PyJWT>=2.8.0
bcrypt>=4.0.1
```

---

## 🔍 Considerações Importantes

### **1. Usuário Admin Inicial**
- Como criar o primeiro usuário admin?
- Opção 1: Script de inicialização
- Opção 2: Endpoint especial (desabilitar após primeiro uso)
- Opção 3: Variável de ambiente

### **2. Migração de Dados**
- Se já existirem usuários, como migrar?
- Script de migração se necessário

### **3. Compatibilidade**
- Manter endpoints públicos (ex: `/api/health`) sem autenticação
- Documentar quais endpoints requerem autenticação

### **4. Logs e Auditoria**
- Registrar tentativas de login (sucesso/falha)
- Registrar ações administrativas
- Logs de mudanças de senha

### **5. Recuperação de Senha (Futuro)**
- Sistema de reset de senha por email
- Tokens de recuperação temporários

---

## ✅ Checklist de Implementação

- [ ] Criar estrutura de pastas `core/auth/`
- [ ] Criar tabela `frontend_users` no banco
- [ ] Implementar `password_handler.py`
- [ ] Implementar `jwt_handler.py`
- [ ] Implementar `user_manager.py`
- [ ] Implementar `auth_manager.py`
- [ ] Criar decorators `@require_auth` e `@require_admin`
- [ ] Criar endpoint `POST /api/auth/login`
- [ ] Criar endpoint `GET /api/auth/me`
- [ ] Criar endpoint `POST /api/auth/logout`
- [ ] Criar endpoint `POST /api/auth/change-password`
- [ ] Criar endpoints de gerenciamento de usuários (admin)
- [ ] Aplicar `@require_auth` nas rotas críticas
- [ ] Implementar proteção contra brute force
- [ ] Criar script para usuário admin inicial
- [ ] Adicionar configurações ao `config.json`
- [ ] Testes de autenticação
- [ ] Documentação de endpoints

---

## 🎯 Próximos Passos

1. **Revisar este planejamento** com o time
2. **Decidir sobre usuário admin inicial** (como criar)
3. **Definir quais rotas precisam autenticação**
4. **Aprovar estrutura proposta**
5. **Iniciar implementação pela Fase 1**

---

## 📚 Referências

- [JWT.io](https://jwt.io/) - Documentação JWT
- [Flask-JWT-Extended](https://flask-jwt-extended.readthedocs.io/) - Alternativa com mais features
- [OWASP Authentication Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Authentication_Cheat_Sheet.html) - Boas práticas de segurança

