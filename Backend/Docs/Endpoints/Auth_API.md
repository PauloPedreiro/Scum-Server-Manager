# 🔐 API de Autenticação - SCUM Server Manager

## 📋 Visão Geral

Sistema de autenticação baseado em JWT com armazenamento em JSON local. Inclui controle de sessões, logs de acesso e rate limiting.

## 🗂️ Estrutura de Arquivos

```
src/data/auth/
├── users.json          # Usuários cadastrados
├── sessions.json       # Sessões ativas
└── access_logs.json    # Logs de acesso
```

## 🔧 Configuração Inicial

### 1. **Instalar Dependências**
```bash
npm install bcrypt jsonwebtoken
```

### 2. **Configurar Primeira Senha**
```bash
# Gerar hash da senha para o usuário admin
node scripts/generate-password.js admin minhasenha123
```

### 3. **Verificar .env**
```env
JWT_SECRET=sua_chave_secreta_aqui
```

## 📡 Endpoints

### **POST /api/auth/login**
Faz login no sistema.

**Request:**
```json
{
  "username": "admin",
  "password": "minhasenha123"
}
```

**Response (Sucesso):**
```json
{
  "success": true,
  "message": "Login realizado com sucesso",
  "data": {
    "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "user": {
      "id": "1",
      "username": "admin",
      "role": "admin"
    }
  }
}
```

**Response (Erro):**
```json
{
  "success": false,
  "message": "Usuário ou senha inválidos"
}
```

### **POST /api/auth/logout**
Faz logout e invalida a sessão.

**Headers:**
```
Authorization: Bearer <token>
```

**Response:**
```json
{
  "success": true,
  "message": "Logout realizado com sucesso"
}
```

### **GET /api/auth/me**
Retorna informações do usuário logado.

**Headers:**
```
Authorization: Bearer <token>
```

**Response:**
```json
{
  "success": true,
  "data": {
    "id": "1",
    "username": "admin",
    "role": "admin"
  }
}
```

### **GET /api/auth/logs**
Retorna logs de acesso (apenas admin).

**Headers:**
```
Authorization: Bearer <token>
```

**Response:**
```json
{
  "success": true,
  "data": {
    "logs": [
      {
        "id": "1705756800000",
        "username": "admin",
        "action": "login_success",
        "ip": "192.168.1.100",
        "user_agent": "Mozilla/5.0...",
        "timestamp": "2025-01-20T15:30:00Z",
        "success": true
      }
    ],
    "total": 1
  }
}
```

### **POST /api/auth/change-password**
Altera a senha do usuário logado.

**Headers:**
```
Authorization: Bearer <token>
```

**Request:**
```json
{
  "currentPassword": "senha_atual",
  "newPassword": "nova_senha"
}
```

**Response:**
```json
{
  "success": true,
  "message": "Senha alterada com sucesso"
}
```

## 🔒 Segurança

### **Rate Limiting**
- Máximo 5 tentativas de login por IP em 15 minutos
- Bloqueio automático após exceder limite

### **JWT Token**
- Expiração: 24 horas
- Armazenado em `sessions.json`
- Invalidado no logout

### **Logs de Acesso**
- Todas as tentativas de login/logout
- Captura de IP real
- User-Agent do navegador
- Sucesso/falha da operação

### **Hash de Senhas**
- bcrypt com salt rounds = 10
- Senhas nunca armazenadas em texto plano

## 🛡️ Middleware de Proteção

### **requireAuth**
Protege rotas que precisam de autenticação.

```javascript
const { requireAuth } = require('../src/middleware/auth');

// Aplicar em rotas
app.get('/api/protected', requireAuth, (req, res) => {
  // req.user contém dados do usuário
  res.json({ user: req.user });
});
```

## 📊 Estrutura de Dados

### **users.json**
```json
{
  "users": [
    {
      "id": "1",
      "username": "admin",
      "password": "$2b$10$hash_aqui",
      "role": "admin",
      "created_at": "2025-01-20T10:00:00Z",
      "last_login": "2025-01-20T15:30:00Z",
      "active": true
    }
  ]
}
```

### **sessions.json**
```json
{
  "sessions": [
    {
      "token": "jwt_token_aqui",
      "user_id": "1",
      "username": "admin",
      "created_at": "2025-01-20T15:30:00Z",
      "expires_at": "2025-01-21T15:30:00Z",
      "ip": "192.168.1.100"
    }
  ]
}
```

### **access_logs.json**
```json
{
  "logs": [
    {
      "id": "1705756800000",
      "username": "admin",
      "action": "login_success",
      "ip": "192.168.1.100",
      "user_agent": "Mozilla/5.0...",
      "timestamp": "2025-01-20T15:30:00Z",
      "success": true
    }
  ]
}
```

## 🔧 Comandos Úteis

### **Gerar Hash de Senha**
```bash
node scripts/generate-password.js admin minhasenha123
```

### **Verificar Logs**
```bash
# Acessar via API
GET /api/auth/logs
```

### **Limpar Sessões Expiradas**
```bash
# Reiniciar servidor (limpa automaticamente)
npm restart
```

## ⚠️ Códigos de Status

- **200**: Sucesso
- **400**: Dados inválidos
- **401**: Não autenticado
- **403**: Acesso negado (não é admin)
- **429**: Rate limit excedido
- **500**: Erro interno

## 🎯 Exemplos de Uso

### **Login via Frontend**
```javascript
const login = async (username, password) => {
  const response = await fetch('/api/auth/login', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({ username, password })
  });
  
  const data = await response.json();
  
  if (data.success) {
    // Salvar token
    localStorage.setItem('token', data.data.token);
    return data.data.user;
  } else {
    throw new Error(data.message);
  }
};
```

### **Requisição Autenticada**
```javascript
const fetchProtectedData = async () => {
  const token = localStorage.getItem('token');
  
  const response = await fetch('/api/protected-endpoint', {
    headers: {
      'Authorization': `Bearer ${token}`
    }
  });
  
  return response.json();
};
```

## 🔍 Troubleshooting

### **Problema: Token inválido**
- Verificar se JWT_SECRET está configurado
- Verificar se token não expirou
- Verificar se sessão existe no `sessions.json`

### **Problema: Rate limit**
- Aguardar 15 minutos
- Verificar IP de origem
- Verificar logs em `access_logs.json`

### **Problema: Senha não funciona**
- Gerar novo hash com `generate-password.js`
- Verificar se usuário existe em `users.json`
- Verificar se `active: true`

---

**🔐 Sistema de autenticação pronto para uso!** 