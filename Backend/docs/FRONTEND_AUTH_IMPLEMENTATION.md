# 🔐 Guia de Implementação - Sistema de Autenticação Frontend

## 📋 Visão Geral

Este documento descreve como implementar o sistema de autenticação no frontend do SSM Backend. O sistema utiliza **JWT (JSON Web Tokens)** para autenticação e suporta múltiplos usuários (admin e moderadores).

---

## 🧪 Checklist - Teste de fogo (ponta a ponta)

1. Backend rodando e bot conectado ao Discord
2. Confirmar que existe o evento `log-ssm` no `data/webhooks.json` com `target.channel.id`
3. Login com `admin`
4. Se `must_change_password`:
   - mudar a senha
   - refazer login
5. Confirmar em `GET /api/auth/me`:
   - `must_link_discord === true`
6. Chamar `POST /api/auth/discord-link-code` e copiar `command`
7. Colar no canal `log-ssm`: `!link ...`
8. Polling em `GET /api/auth/me` ate `must_link_discord === false`
9. Testar um endpoint admin (ex.: `GET /api/auth/users`) e confirmar que nao retorna mais `DISCORD_LINK_REQUIRED`

## 🎯 Características Principais

- ✅ **Login com username e senha**
- ✅ **Mudança de senha obrigatória no primeiro login**
- ✅ **Tokens JWT com expiração de 24 horas**
- ✅ **Proteção de rotas baseada em roles (admin/moderator)**
- ✅ **Ativação obrigatória do admin via Discord (vinculação)**
- ✅ **Gerenciamento completo de usuários (apenas admin)**
  - Criar novos usuários (admin/moderator)
  - Listar todos os usuários
  - Atualizar usuários (ativar/desativar, alterar role, vincular player)
  - Deletar usuários (exceto admin)
  - Buscar players para vincular a moderadores

---

## 🌐 Base URL

```
http://localhost:3000
```

---

## 📡 Endpoints Disponíveis

### **1. Login**

```
POST /api/auth/login
```

**Request Body:**
```json
{
  "username": "admin",
  "password": "12345678910"
}
```

**Response (200) - Primeiro Login (senha não mudada):**
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

---

### **2. Mudar Senha**

```
POST /api/auth/change-password
```

**Request Body (primeiro login - sem token):**
```json
{
  "username": "admin",
  "current_password": "12345678910",
  "new_password": "NovaSenhaSegura123!"
}
```

**Request Body (mudança normal - com token):**
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

**Response (400) - Senha Inválida:**
```json
{
  "success": false,
  "error": "Password must be at least 8 characters"
}
```

---

### **3. Obter Usuário Atual**

```
GET /api/auth/me
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
    "id": 1,
    "username": "admin",
    "role": "admin_pending",
    "password_changed": true,
    "discord_user_id": null,
    "must_link_discord": true,
    "steam_id": null,
    "player_name": null,
    "player_id": null,
    "last_login": "2025-12-05T03:05:53.674777"
  }
}
```

**Response (401) - Token Inválido/Expirado:**
```json
{
  "success": false,
  "error": "Invalid or expired token",
  "code": "INVALID_TOKEN"
}
```

---

## 🔗 Vinculação Discord obrigatória (Admin)

### Quando acontece

O admin pode autenticar normalmente, mas fica com permissões bloqueadas enquanto:

- `role === "admin_pending"`
- ou `role === "admin"` e `discord_user_id === null`

O frontend deve tratar esse estado como **"Conta pendente de ativação"** e guiar o usuário no processo abaixo.

### Endpoint para gerar o código

```
POST /api/auth/discord-link-code
```

**Headers:**

```http
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

### O que o usuário precisa fazer

1. Copiar o `command` retornado
2. Colar no canal Discord **`log-ssm`**
3. O bot vai deletar a mensagem e enviar uma DM confirmando

### O que o frontend deve fazer (UX recomendado)

- Mostrar banner/modal quando `must_link_discord === true`
- Exibir botão: **"Gerar código de vinculação"**
- Exibir instruções:
  - “Cole o comando no canal `log-ssm` do seu Discord”
  - “O código expira em 10 minutos”
- Após gerar o código, iniciar **polling** em `GET /api/auth/me` a cada 2s-3s por até ~60s:
  - Se `must_link_discord` virar `false`, liberar o acesso e seguir fluxo normal

### Tratamento de erro padrão (rotas admin)

Se o frontend chamar um endpoint protegido por admin e receber:

- HTTP `403`
- `code: "DISCORD_LINK_REQUIRED"`

O frontend deve redirecionar para a tela/estado de ativação (vinculação).

### Snippets (TypeScript/React)

#### Cliente HTTP simples (fetch)

```ts
type ApiError = {
  success: false;
  error?: string;
  code?: string;
};

type ApiSuccess<T> = {
  success: true;
  data: T;
};

type ApiResponse<T> = ApiSuccess<T> | ApiError;

function getToken(): string | null {
  return localStorage.getItem('ssm_token');
}

function setToken(token: string | null) {
  if (token) localStorage.setItem('ssm_token', token);
  else localStorage.removeItem('ssm_token');
}

export async function apiRequest<T>(
  path: string,
  options: RequestInit = {}
): Promise<ApiResponse<T>> {
  const token = getToken();
  const headers = new Headers(options.headers);

  if (!headers.has('Content-Type') && options.body) {
    headers.set('Content-Type', 'application/json');
  }
  if (token) {
    headers.set('Authorization', `Bearer ${token}`);
  }

  const res = await fetch(`${import.meta.env.VITE_BACKEND_URL}${path}`, {
    ...options,
    headers,
  });

  const json = (await res.json().catch(() => null)) as ApiResponse<T> | null;
  if (json) return json;
  return { success: false, error: 'Invalid JSON response' };
}
```

#### Tratamento centralizado do erro `DISCORD_LINK_REQUIRED`

Padrão recomendado:

- Se qualquer request retornar `code === "DISCORD_LINK_REQUIRED"`, o frontend deve:
  - forçar estado `must_link_discord=true`
  - redirecionar para tela de ativação

```ts
async function apiRequestWithDiscordGate<T>(
  path: string,
  options: RequestInit = {}
): Promise<ApiResponse<T>> {
  const res = await apiRequest<T>(path, options);
  if (!res.success && res.code === 'DISCORD_LINK_REQUIRED') {
    window.location.href = '/activate-discord';
  }
  return res;
}
```

#### Polling para liberar admin

```ts
type MeResponse = {
  id: number;
  username: string;
  role: string;
  password_changed: boolean;
  discord_user_id: string | null;
  must_link_discord: boolean;
};

export async function waitForDiscordLink(options?: {
  timeoutMs?: number;
  intervalMs?: number;
}): Promise<boolean> {
  const timeoutMs = options?.timeoutMs ?? 60_000;
  const intervalMs = options?.intervalMs ?? 2_500;

  const start = Date.now();
  while (Date.now() - start < timeoutMs) {
    const me = await apiRequest<MeResponse>('/api/auth/me');
    if (me.success && me.data.must_link_discord === false) return true;
    await new Promise((r) => setTimeout(r, intervalMs));
  }
  return false;
}
```

#### Guard de rota (conceito)

Regras:

- Se nao tem token: ir para `/login`
- Se `must_link_discord=true`: ir para `/activate-discord`

```tsx
import { Navigate } from 'react-router-dom';

export function AdminRoute({ children }: { children: JSX.Element }) {
  const token = localStorage.getItem('ssm_token');
  const mustLink = localStorage.getItem('ssm_must_link_discord') === '1';

  if (!token) return <Navigate to="/login" replace />;
  if (mustLink) return <Navigate to="/activate-discord" replace />;
  return children;
}
```

---

### **4. Logout**

```
POST /api/auth/logout
```

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

**Nota:** Com JWT, o logout é apenas do lado do cliente. Remova o token do armazenamento local.

---

### **5. Criar Usuário (Admin Apenas)**

```
POST /api/auth/users
```

**Headers:**
```
Authorization: Bearer <token>
```

**Request Body:**
```json
{
  "username": "moderador1",
  "password": "senha123456",
  "role": "moderator",
  "steam_id": "76561198012345678"
}
```

**Campos:**
- `username` (obrigatório): Nome de usuário único
- `password` (obrigatório): Senha (mínimo 8 caracteres)
- `role` (opcional): `"admin"` ou `"moderator"` (padrão: `"moderator"`)
- `steam_id` (opcional): Steam ID para vincular moderador a um player

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
    "player_name": "Player Name",
    "created_at": "2025-12-05T10:30:00",
    "message": "User created. Password must be changed on first login."
  }
}
```

**Response (400) - Username Já Existe:**
```json
{
  "success": false,
  "error": "Username already exists or invalid steam_id"
}
```

**Response (400) - Senha Inválida:**
```json
{
  "success": false,
  "error": "Password must be at least 8 characters"
}
```

**Response (401) - Não Autorizado:**
```json
{
  "success": false,
  "error": "Admin access required"
}
```

---

### **6. Listar Usuários (Admin Apenas)**

```
GET /api/auth/users
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
    "users": [
      {
        "id": 1,
        "username": "admin",
        "role": "admin",
        "is_active": true,
        "password_changed": true,
        "steam_id": null,
        "player_name": null,
        "player_id": null,
        "last_login": "2025-12-05T03:05:53.674777",
        "created_at": "2025-12-04T10:00:00"
      },
      {
        "id": 2,
        "username": "moderador1",
        "role": "moderator",
        "is_active": true,
        "password_changed": false,
        "steam_id": "76561198012345678",
        "player_name": "Player Name",
        "player_id": 123,
        "last_login": null,
        "created_at": "2025-12-05T10:30:00"
      }
    ],
    "total": 2
  }
}
```

---

### **7. Atualizar Usuário (Admin Apenas)**

```
PUT /api/auth/users/<user_id>
```

**Headers:**
```
Authorization: Bearer <token>
```

**Request Body:**
```json
{
  "is_active": false,
  "role": "moderator",
  "steam_id": "76561198012345678"
}
```

**Campos (todos opcionais):**
- `is_active`: `true` ou `false` para ativar/desativar usuário
- `role`: `"admin"` ou `"moderator"`
- `steam_id`: Steam ID para vincular (ou `null` para remover vínculo)

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
    "updated_at": "2025-12-05T11:00:00"
  }
}
```

**Response (404) - Usuário Não Encontrado:**
```json
{
  "success": false,
  "error": "User not found"
}
```

---

### **8. Deletar Usuário (Admin Apenas)**

```
DELETE /api/auth/users/<user_id>
```

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

**Response (400) - Tentativa de Deletar Admin:**
```json
{
  "success": false,
  "error": "Cannot delete admin user"
}
```

**Response (404) - Usuário Não Encontrado:**
```json
{
  "success": false,
  "error": "User not found"
}
```

---

### **9. Buscar Players (Admin Apenas)**

```
GET /api/auth/users/search-players?q=<query>&limit=<limit>
```

**Headers:**
```
Authorization: Bearer <token>
```

**Query Parameters:**
- `q` (obrigatório): Termo de busca (nome ou steam_id)
- `limit` (opcional): Limite de resultados (padrão: 20)

**Exemplo:**
```
GET /api/auth/users/search-players?q=PlayerName&limit=10
```

**Response (200):**
```json
{
  "success": true,
  "data": {
    "players": [
      {
        "steam_id": "76561198012345678",
        "name": "Player Name",
        "id": 123
      },
      {
        "steam_id": "76561198087654321",
        "name": "Another Player",
        "id": 456
      }
    ],
    "total": 2
  }
}
```

**Response (400) - Query Não Fornecida:**
```json
{
  "success": false,
  "error": "Query parameter 'q' required"
}
```

---

## 🔄 Fluxos de Autenticação

### **Fluxo 1: Primeiro Login (Senha Padrão)**

```
1. Usuário acessa frontend
2. Frontend verifica se há token armazenado
3. Se não houver, redireciona para /login
4. Usuário digita: admin / 12345678910
5. POST /api/auth/login
6. Backend retorna: { must_change_password: true }
7. Frontend mostra tela de mudança de senha
8. Usuário digita senha atual e nova senha
9. POST /api/auth/change-password
10. Backend retorna token JWT
11. Frontend armazena token e redireciona para dashboard
```

### **Fluxo 2: Login Normal (Senha Já Alterada)**

```
1. Usuário acessa frontend
2. Frontend verifica token armazenado
3. Se token válido, mostra dashboard
4. Se token inválido/expirado, redireciona para /login
5. Usuário digita: username / senha_atual
6. POST /api/auth/login
7. Backend retorna token JWT
8. Frontend armazena token e mostra dashboard
```

### **Fluxo 3: Verificação de Token**

```
1. Frontend faz requisição protegida
2. Adiciona header: Authorization: Bearer <token>
3. Backend valida token
4. Se válido, processa requisição
5. Se inválido/expirado, retorna 401
6. Frontend redireciona para /login
```

---

## 💻 Exemplos de Implementação

### **Exemplo 1: Serviço de Autenticação (TypeScript/JavaScript)**

```typescript
// auth.service.ts
const API_BASE_URL = 'http://localhost:3000';

interface LoginResponse {
  success: boolean;
  data?: {
    token?: string;
    username?: string;
    role?: string;
    expires_in?: number;
    must_change_password?: boolean;
    message?: string;
  };
  error?: string;
}

interface User {
  id: number;
  username: string;
  role: string;
  password_changed: boolean;
  steam_id?: string;
  player_name?: string;
  last_login?: string;
}

class AuthService {
  private tokenKey = 'ssm_auth_token';
  private userKey = 'ssm_user';

  // Login
  async login(username: string, password: string): Promise<LoginResponse> {
    const response = await fetch(`${API_BASE_URL}/api/auth/login`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ username, password }),
    });

    const data: LoginResponse = await response.json();

    if (data.success && data.data?.token) {
      // Armazenar token
      localStorage.setItem(this.tokenKey, data.data.token);
      
      // Armazenar dados do usuário
      if (data.data.username && data.data.role) {
        localStorage.setItem(this.userKey, JSON.stringify({
          username: data.data.username,
          role: data.data.role,
        }));
      }
    }

    return data;
  }

  // Mudar senha
  async changePassword(
    currentPassword: string,
    newPassword: string,
    username?: string
  ): Promise<LoginResponse> {
    const token = this.getToken();
    const headers: HeadersInit = {
      'Content-Type': 'application/json',
    };

    if (token) {
      headers['Authorization'] = `Bearer ${token}`;
    }

    const body: any = {
      current_password: currentPassword,
      new_password: newPassword,
    };

    if (username) {
      body.username = username;
    }

    const response = await fetch(`${API_BASE_URL}/api/auth/change-password`, {
      method: 'POST',
      headers,
      body: JSON.stringify(body),
    });

    const data: LoginResponse = await response.json();

    if (data.success && data.data?.token) {
      // Atualizar token
      localStorage.setItem(this.tokenKey, data.data.token);
    }

    return data;
  }

  // Obter usuário atual
  async getCurrentUser(): Promise<User | null> {
    const token = this.getToken();
    if (!token) return null;

    try {
      const response = await fetch(`${API_BASE_URL}/api/auth/me`, {
        headers: {
          'Authorization': `Bearer ${token}`,
        },
      });

      if (response.status === 401) {
        // Token inválido/expirado
        this.logout();
        return null;
      }

      const data = await response.json();
      if (data.success) {
        return data.data;
      }
    } catch (error) {
      console.error('Erro ao obter usuário:', error);
    }

    return null;
  }

  // Logout
  async logout(): Promise<void> {
    const token = this.getToken();
    
    if (token) {
      try {
        await fetch(`${API_BASE_URL}/api/auth/logout`, {
          method: 'POST',
          headers: {
            'Authorization': `Bearer ${token}`,
          },
        });
      } catch (error) {
        console.error('Erro no logout:', error);
      }
    }

    // Remover token e dados do usuário
    localStorage.removeItem(this.tokenKey);
    localStorage.removeItem(this.userKey);
  }

  // Verificar se está autenticado
  isAuthenticated(): boolean {
    return !!this.getToken();
  }

  // Obter token
  getToken(): string | null {
    return localStorage.getItem(this.tokenKey);
  }

  // Obter dados do usuário do localStorage
  getUserFromStorage(): { username: string; role: string } | null {
    const userStr = localStorage.getItem(this.userKey);
    if (userStr) {
      try {
        return JSON.parse(userStr);
      } catch {
        return null;
      }
    }
    return null;
  }

  // Verificar se é admin
  isAdmin(): boolean {
    const user = this.getUserFromStorage();
    return user?.role === 'admin';
  }

  // ========== GERENCIAMENTO DE USUÁRIOS (ADMIN APENAS) ==========

  // Criar usuário
  async createUser(
    username: string,
    password: string,
    role: 'admin' | 'moderator' = 'moderator',
    steamId?: string
  ): Promise<any> {
    const token = this.getToken();
    if (!token) throw new Error('Not authenticated');

    const response = await fetch(`${API_BASE_URL}/api/auth/users`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`,
      },
      body: JSON.stringify({
        username,
        password,
        role,
        steam_id: steamId,
      }),
    });

    const data = await response.json();

    if (!data.success) {
      throw new Error(data.error || 'Failed to create user');
    }

    return data.data;
  }

  // Listar usuários
  async listUsers(): Promise<User[]> {
    const token = this.getToken();
    if (!token) throw new Error('Not authenticated');

    const response = await fetch(`${API_BASE_URL}/api/auth/users`, {
      headers: {
        'Authorization': `Bearer ${token}`,
      },
    });

    if (response.status === 401) {
      this.logout();
      throw new Error('Not authenticated');
    }

    const data = await response.json();

    if (!data.success) {
      throw new Error(data.error || 'Failed to list users');
    }

    return data.data.users;
  }

  // Atualizar usuário
  async updateUser(
    userId: number,
    updates: {
      is_active?: boolean;
      role?: 'admin' | 'moderator';
      steam_id?: string | null;
    }
  ): Promise<any> {
    const token = this.getToken();
    if (!token) throw new Error('Not authenticated');

    const response = await fetch(`${API_BASE_URL}/api/auth/users/${userId}`, {
      method: 'PUT',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`,
      },
      body: JSON.stringify(updates),
    });

    const data = await response.json();

    if (!data.success) {
      throw new Error(data.error || 'Failed to update user');
    }

    return data.data;
  }

  // Deletar usuário
  async deleteUser(userId: number): Promise<void> {
    const token = this.getToken();
    if (!token) throw new Error('Not authenticated');

    const response = await fetch(`${API_BASE_URL}/api/auth/users/${userId}`, {
      method: 'DELETE',
      headers: {
        'Authorization': `Bearer ${token}`,
      },
    });

    const data = await response.json();

    if (!data.success) {
      throw new Error(data.error || 'Failed to delete user');
    }
  }

  // Buscar players
  async searchPlayers(query: string, limit: number = 20): Promise<any[]> {
    const token = this.getToken();
    if (!token) throw new Error('Not authenticated');

    const response = await fetch(
      `${API_BASE_URL}/api/auth/users/search-players?q=${encodeURIComponent(query)}&limit=${limit}`,
      {
        headers: {
          'Authorization': `Bearer ${token}`,
        },
      }
    );

    if (response.status === 401) {
      this.logout();
      throw new Error('Not authenticated');
    }

    const data = await response.json();

    if (!data.success) {
      throw new Error(data.error || 'Failed to search players');
    }

    return data.data.players;
  }
}

export const authService = new AuthService();
```

---

### **Exemplo 2: Interceptor para Requisições (Axios)**

```typescript
// api.interceptor.ts
import axios from 'axios';
import { authService } from './auth.service';

const api = axios.create({
  baseURL: 'http://localhost:3000',
});

// Interceptor para adicionar token em todas as requisições
api.interceptors.request.use(
  (config) => {
    const token = authService.getToken();
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// Interceptor para tratar erros de autenticação
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      // Token inválido/expirado
      authService.logout();
      // Redirecionar para login
      window.location.href = '/login';
    }
    return Promise.reject(error);
  }
);

export default api;
```

---

### **Exemplo 3: Componente de Login (React)**

```tsx
// Login.tsx
import { useState } from 'react';
import { authService } from '../services/auth.service';
import { useNavigate } from 'react-router-dom';

export function Login() {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setLoading(true);

    try {
      const response = await authService.login(username, password);

      if (response.success) {
        if (response.data?.must_change_password) {
          // Redirecionar para mudança de senha
          navigate('/change-password', { 
            state: { username, currentPassword: password } 
          });
        } else {
          // Login bem-sucedido
          navigate('/dashboard');
        }
      } else {
        setError(response.error || 'Credenciais inválidas');
      }
    } catch (err) {
      setError('Erro ao fazer login. Tente novamente.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="login-container">
      <form onSubmit={handleLogin}>
        <h2>Login</h2>
        
        {error && <div className="error">{error}</div>}
        
        <input
          type="text"
          placeholder="Username"
          value={username}
          onChange={(e) => setUsername(e.target.value)}
          required
        />
        
        <input
          type="password"
          placeholder="Password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          required
        />
        
        <button type="submit" disabled={loading}>
          {loading ? 'Entrando...' : 'Entrar'}
        </button>
      </form>
    </div>
  );
}
```

---

### **Exemplo 4: Componente de Mudança de Senha (React)**

```tsx
// ChangePassword.tsx
import { useState, useEffect } from 'react';
import { authService } from '../services/auth.service';
import { useNavigate, useLocation } from 'react-router-dom';

export function ChangePassword() {
  const [currentPassword, setCurrentPassword] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();
  const location = useLocation();

  // Se veio do primeiro login, usar dados do state
  useEffect(() => {
    if (location.state?.username && location.state?.currentPassword) {
      setCurrentPassword(location.state.currentPassword);
    }
  }, [location]);

  const handleChangePassword = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');

    // Validações
    if (newPassword.length < 8) {
      setError('A senha deve ter pelo menos 8 caracteres');
      return;
    }

    if (newPassword !== confirmPassword) {
      setError('As senhas não coincidem');
      return;
    }

    setLoading(true);

    try {
      const username = location.state?.username;
      const response = await authService.changePassword(
        currentPassword,
        newPassword,
        username
      );

      if (response.success) {
        // Senha alterada com sucesso
        navigate('/dashboard');
      } else {
        setError(response.error || 'Erro ao alterar senha');
      }
    } catch (err) {
      setError('Erro ao alterar senha. Tente novamente.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="change-password-container">
      <form onSubmit={handleChangePassword}>
        <h2>Alterar Senha</h2>
        <p>Por favor, altere sua senha padrão</p>
        
        {error && <div className="error">{error}</div>}
        
        <input
          type="password"
          placeholder="Senha Atual"
          value={currentPassword}
          onChange={(e) => setCurrentPassword(e.target.value)}
          required
        />
        
        <input
          type="password"
          placeholder="Nova Senha (mín. 8 caracteres)"
          value={newPassword}
          onChange={(e) => setNewPassword(e.target.value)}
          required
          minLength={8}
        />
        
        <input
          type="password"
          placeholder="Confirmar Nova Senha"
          value={confirmPassword}
          onChange={(e) => setConfirmPassword(e.target.value)}
          required
          minLength={8}
        />
        
        <button type="submit" disabled={loading}>
          {loading ? 'Alterando...' : 'Alterar Senha'}
        </button>
      </form>
    </div>
  );
}
```

---

### **Exemplo 5: Proteção de Rotas (React Router)**

```tsx
// ProtectedRoute.tsx
import { Navigate } from 'react-router-dom';
import { authService } from '../services/auth.service';

interface ProtectedRouteProps {
  children: React.ReactNode;
  requireAdmin?: boolean;
}

export function ProtectedRoute({ children, requireAdmin = false }: ProtectedRouteProps) {
  const isAuthenticated = authService.isAuthenticated();
  const isAdmin = authService.isAdmin();

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />;
  }

  if (requireAdmin && !isAdmin) {
    return <Navigate to="/unauthorized" replace />;
  }

  return <>{children}</>;
}

// Uso:
// <Route path="/dashboard" element={<ProtectedRoute><Dashboard /></ProtectedRoute>} />
// <Route path="/admin" element={<ProtectedRoute requireAdmin><AdminPanel /></ProtectedRoute>} />
```

---

### **Exemplo 6: Verificação de Token ao Carregar App**

```tsx
// App.tsx
import { useEffect, useState } from 'react';
import { authService } from './services/auth.service';

function App() {
  const [isChecking, setIsChecking] = useState(true);
  const [isAuthenticated, setIsAuthenticated] = useState(false);

  useEffect(() => {
    const checkAuth = async () => {
      const token = authService.getToken();
      
      if (token) {
        // Verificar se token é válido
        const user = await authService.getCurrentUser();
        setIsAuthenticated(!!user);
      } else {
        setIsAuthenticated(false);
      }
      
      setIsChecking(false);
    };

    checkAuth();
  }, []);

  if (isChecking) {
    return <div>Verificando autenticação...</div>;
  }

  // Renderizar app baseado no estado de autenticação
  return (
    <Router>
      {/* Rotas */}
    </Router>
  );
}
```

---

### **Exemplo 7: Componente de Gerenciamento de Usuários (React)**

```tsx
// UserManagement.tsx
import { useState, useEffect } from 'react';
import { authService } from '../services/auth.service';
import { ProtectedRoute } from './ProtectedRoute';

interface User {
  id: number;
  username: string;
  role: string;
  is_active: boolean;
  password_changed: boolean;
  steam_id?: string;
  player_name?: string;
  last_login?: string;
  created_at: string;
}

export function UserManagement() {
  const [users, setUsers] = useState<User[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [showCreateForm, setShowCreateForm] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');

  // Formulário de criação
  const [newUsername, setNewUsername] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [newRole, setNewRole] = useState<'admin' | 'moderator'>('moderator');
  const [newSteamId, setNewSteamId] = useState('');
  const [playerSearchResults, setPlayerSearchResults] = useState<any[]>([]);

  useEffect(() => {
    loadUsers();
  }, []);

  const loadUsers = async () => {
    try {
      setLoading(true);
      const usersList = await authService.listUsers();
      setUsers(usersList);
      setError('');
    } catch (err: any) {
      setError(err.message || 'Erro ao carregar usuários');
    } finally {
      setLoading(false);
    }
  };

  const handleCreateUser = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');

    try {
      await authService.createUser(
        newUsername,
        newPassword,
        newRole,
        newSteamId || undefined
      );
      
      // Limpar formulário
      setNewUsername('');
      setNewPassword('');
      setNewRole('moderator');
      setNewSteamId('');
      setShowCreateForm(false);
      
      // Recarregar lista
      await loadUsers();
    } catch (err: any) {
      setError(err.message || 'Erro ao criar usuário');
    }
  };

  const handleToggleActive = async (userId: number, currentStatus: boolean) => {
    try {
      await authService.updateUser(userId, { is_active: !currentStatus });
      await loadUsers();
    } catch (err: any) {
      setError(err.message || 'Erro ao atualizar usuário');
    }
  };

  const handleDeleteUser = async (userId: number) => {
    if (!confirm('Tem certeza que deseja deletar este usuário?')) {
      return;
    }

    try {
      await authService.deleteUser(userId);
      await loadUsers();
    } catch (err: any) {
      setError(err.message || 'Erro ao deletar usuário');
    }
  };

  const handleSearchPlayers = async (query: string) => {
    if (query.length < 3) {
      setPlayerSearchResults([]);
      return;
    }

    try {
      const players = await authService.searchPlayers(query, 10);
      setPlayerSearchResults(players);
    } catch (err) {
      console.error('Erro ao buscar players:', err);
    }
  };

  const filteredUsers = users.filter((user) =>
    user.username.toLowerCase().includes(searchQuery.toLowerCase())
  );

  if (!authService.isAdmin()) {
    return <div>Acesso negado. Apenas administradores podem gerenciar usuários.</div>;
  }

  return (
    <ProtectedRoute requireAdmin>
      <div className="user-management">
        <h2>Gerenciamento de Usuários</h2>

        {error && <div className="error">{error}</div>}

        <div className="toolbar">
          <input
            type="text"
            placeholder="Buscar usuários..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
          />
          <button onClick={() => setShowCreateForm(!showCreateForm)}>
            {showCreateForm ? 'Cancelar' : '+ Criar Usuário'}
          </button>
        </div>

        {showCreateForm && (
          <form onSubmit={handleCreateUser} className="create-user-form">
            <h3>Criar Novo Usuário</h3>
            
            <input
              type="text"
              placeholder="Username"
              value={newUsername}
              onChange={(e) => setNewUsername(e.target.value)}
              required
            />
            
            <input
              type="password"
              placeholder="Senha (mín. 8 caracteres)"
              value={newPassword}
              onChange={(e) => setNewPassword(e.target.value)}
              required
              minLength={8}
            />
            
            <select
              value={newRole}
              onChange={(e) => setNewRole(e.target.value as 'admin' | 'moderator')}
            >
              <option value="moderator">Moderador</option>
              <option value="admin">Administrador</option>
            </select>

            <div className="steam-id-section">
              <input
                type="text"
                placeholder="Buscar player por nome ou Steam ID..."
                onChange={(e) => handleSearchPlayers(e.target.value)}
              />
              
              {playerSearchResults.length > 0 && (
                <div className="player-results">
                  {playerSearchResults.map((player) => (
                    <div
                      key={player.steam_id}
                      className="player-result"
                      onClick={() => {
                        setNewSteamId(player.steam_id);
                        setPlayerSearchResults([]);
                      }}
                    >
                      {player.name} ({player.steam_id})
                    </div>
                  ))}
                </div>
              )}
              
              {newSteamId && (
                <div className="selected-steam-id">
                  Steam ID: {newSteamId}
                  <button type="button" onClick={() => setNewSteamId('')}>
                    Remover
                  </button>
                </div>
              )}
            </div>
            
            <button type="submit">Criar Usuário</button>
          </form>
        )}

        {loading ? (
          <div>Carregando...</div>
        ) : (
          <table className="users-table">
            <thead>
              <tr>
                <th>ID</th>
                <th>Username</th>
                <th>Role</th>
                <th>Status</th>
                <th>Senha Alterada</th>
                <th>Player Vinculado</th>
                <th>Último Login</th>
                <th>Ações</th>
              </tr>
            </thead>
            <tbody>
              {filteredUsers.map((user) => (
                <tr key={user.id}>
                  <td>{user.id}</td>
                  <td>{user.username}</td>
                  <td>{user.role}</td>
                  <td>
                    <span className={user.is_active ? 'active' : 'inactive'}>
                      {user.is_active ? 'Ativo' : 'Inativo'}
                    </span>
                  </td>
                  <td>
                    {user.password_changed ? '✅' : '❌'}
                  </td>
                  <td>
                    {user.player_name ? (
                      <span>{user.player_name}</span>
                    ) : (
                      <span className="no-link">Não vinculado</span>
                    )}
                  </td>
                  <td>
                    {user.last_login
                      ? new Date(user.last_login).toLocaleString()
                      : 'Nunca'}
                  </td>
                  <td>
                    <button
                      onClick={() => handleToggleActive(user.id, user.is_active)}
                    >
                      {user.is_active ? 'Desativar' : 'Ativar'}
                    </button>
                    {user.role !== 'admin' && (
                      <button
                        onClick={() => handleDeleteUser(user.id)}
                        className="delete-btn"
                      >
                        Deletar
                      </button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </ProtectedRoute>
  );
}
```

---

## 🔒 Tratamento de Erros

### **Códigos de Erro Comuns**

| Código | Descrição | Ação Recomendada |
|--------|-----------|------------------|
| `AUTH_REQUIRED` | Token não fornecido | Redirecionar para login |
| `INVALID_TOKEN` | Token inválido ou expirado | Remover token e redirecionar para login |
| `ADMIN_REQUIRED` | Acesso admin necessário | Mostrar mensagem de acesso negado |
| `Invalid credentials` | Username/senha incorretos | Mostrar mensagem de erro |
| `Current password is incorrect` | Senha atual incorreta | Mostrar mensagem de erro |
| `Password must be at least 8 characters` | Senha muito curta | Mostrar mensagem de validação |

---

## 📝 Validações de Senha

- **Mínimo de 8 caracteres** (configurável em `config.json`)
- Validação é feita no backend
- Frontend pode validar antes de enviar para melhor UX

---

## 🔐 Armazenamento de Token

### **Recomendações:**

1. **localStorage** (Recomendado para este caso):
   ```typescript
   localStorage.setItem('ssm_auth_token', token);
   ```

2. **sessionStorage** (Alternativa - token expira ao fechar aba):
   ```typescript
   sessionStorage.setItem('ssm_auth_token', token);
   ```

3. **Cookies HttpOnly** (Mais seguro, mas requer configuração no backend):
   - Não implementado atualmente
   - Pode ser adicionado no futuro

### **⚠️ Importante:**
- Token expira em **24 horas** (configurável)
- Sempre verificar se token é válido antes de fazer requisições
- Remover token ao fazer logout

---

## 🎯 Estrutura do Token JWT

O token JWT contém:

```json
{
  "user_id": 1,
  "username": "admin",
  "role": "admin",
  "password_changed": true,
  "exp": 1764989378,
  "iat": 1764902953
}
```

**Campos:**
- `user_id`: ID do usuário no banco
- `username`: Nome de usuário
- `role`: Role do usuário (admin, moderator)
- `password_changed`: Se a senha foi alterada
- `exp`: Timestamp de expiração
- `iat`: Timestamp de criação

---

## 🔄 Fluxo de Renovação de Token

Atualmente, o token não é renovado automaticamente. Quando expirar:

1. Frontend recebe `401 INVALID_TOKEN`
2. Remover token do armazenamento
3. Redirecionar para `/login`
4. Usuário faz login novamente

**Futuro:** Pode ser implementado refresh token para renovação automática.

---

## 📱 Exemplo de Integração com Axios

```typescript
// api.ts
import axios from 'axios';
import { authService } from './auth.service';

const api = axios.create({
  baseURL: 'http://localhost:3000',
  headers: {
    'Content-Type': 'application/json',
  },
});

// Adicionar token em todas as requisições
api.interceptors.request.use(
  (config) => {
    const token = authService.getToken();
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => Promise.reject(error)
);

// Tratar erros de autenticação
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      const errorCode = error.response.data?.code;
      
      if (errorCode === 'INVALID_TOKEN' || errorCode === 'AUTH_REQUIRED') {
        authService.logout();
        // Redirecionar para login
        window.location.href = '/login';
      }
    }
    
    return Promise.reject(error);
  }
);

export default api;
```

---

## 🎨 Exemplo de UI/UX

### **Tela de Login**

```
┌─────────────────────────────┐
│      SSM Backend Login      │
├─────────────────────────────┤
│                             │
│  Username: [___________]    │
│  Password: [___________]    │
│                             │
│  [    Entrar    ]           │
│                             │
│  [Mensagem de erro se houver]│
└─────────────────────────────┘
```

### **Tela de Mudança de Senha (Primeiro Login)**

```
┌─────────────────────────────┐
│    Alterar Senha Obrigatória│
├─────────────────────────────┤
│                             │
│  Por favor, altere sua      │
│  senha padrão.              │
│                             │
│  Senha Atual: [___________] │
│  Nova Senha:  [___________] │
│  Confirmar:   [___________] │
│                             │
│  [  Alterar Senha  ]        │
│                             │
└─────────────────────────────┘
```

---

## ✅ Checklist de Implementação

### **Autenticação Básica:**
- [ ] Criar serviço de autenticação (`auth.service.ts`)
- [ ] Implementar tela de login
- [ ] Implementar tela de mudança de senha
- [ ] Configurar interceptor para adicionar token nas requisições
- [ ] Configurar interceptor para tratar erros 401
- [ ] Implementar proteção de rotas
- [ ] Verificar token ao carregar aplicação
- [ ] Implementar logout
- [ ] Adicionar validação de senha no frontend (UX)
- [ ] Tratar todos os códigos de erro
- [ ] Testar fluxo completo de primeiro login
- [ ] Testar fluxo de login normal
- [ ] Testar expiração de token
- [ ] Testar logout

### **Gerenciamento de Usuários (Admin):**
- [ ] Implementar componente de listagem de usuários
- [ ] Implementar formulário de criação de usuário
- [ ] Implementar busca de players para vincular
- [ ] Implementar ativação/desativação de usuários
- [ ] Implementar atualização de usuários
- [ ] Implementar deleção de usuários
- [ ] Adicionar proteção de rotas admin
- [ ] Testar todas as operações CRUD
- [ ] Testar validações e tratamento de erros

---

## 🧪 Testes Recomendados

### **Cenários de Teste:**

1. **Login com senha padrão:**
   - Deve redirecionar para mudança de senha
   - Deve aceitar nova senha
   - Deve retornar token após mudança

2. **Login com senha alterada:**
   - Deve retornar token diretamente
   - Deve redirecionar para dashboard

3. **Token expirado:**
   - Deve redirecionar para login
   - Deve limpar token do armazenamento

4. **Credenciais inválidas:**
   - Deve mostrar mensagem de erro
   - Não deve redirecionar

5. **Mudança de senha:**
   - Deve validar senha atual
   - Deve validar comprimento mínimo
   - Deve retornar novo token

---

## 📚 Recursos Adicionais

- **Documentação de Endpoints:** `docs/endpoints/README.md`
- **Postman Collection:** `docs/endpoints/postman-collection.json`
- **Segurança de Endpoints:** `docs/SEGURANCA_ENDPOINTS.md`

---

## 🆘 Suporte

Em caso de dúvidas ou problemas:

1. Verificar logs do backend
2. Verificar console do navegador
3. Testar endpoints diretamente no Postman
4. Verificar se token está sendo enviado corretamente

---

## 📝 Notas Importantes

1. **Senha Padrão:** `admin` / `12345678910` (deve ser alterada no primeiro login)
2. **Expiração:** Tokens expiram em 24 horas
3. **Segurança:** Sempre usar HTTPS em produção
4. **CORS:** Backend já está configurado para aceitar requisições do frontend
5. **Validação:** Backend valida todas as senhas (mínimo 8 caracteres)

---

## 🚀 Próximos Passos

Após implementar o login:

1. Proteger rotas administrativas no frontend
2. Implementar gerenciamento de usuários (se admin)
3. Adicionar indicador de sessão (tempo restante)
4. Implementar renovação automática de token (futuro)

---

**Versão:** 1.0  
**Última Atualização:** 2025-12-05

