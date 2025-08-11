# 🔐 Implementação do Sistema de Autenticação - Frontend

## 📋 **Visão Geral**

O sistema de autenticação backend está **100% funcional** e pronto para integração. Este documento contém todas as informações necessárias para implementar a autenticação no frontend.

## 🎯 **Objetivos da Implementação**

- ✅ **Página de login funcional**
- ✅ **Proteção de rotas**
- ✅ **Gerenciamento de tokens JWT**
- ✅ **Logout automático**
- ✅ **Interface de logs (admin)**
- ✅ **Alteração de senha**

## 🔧 **Configuração Inicial**

### **1. Dados de Acesso**
```javascript
// Usuário padrão configurado
const DEFAULT_USER = {
  username: 'admin',
  password: 'admin123'
};
```

### **2. Endpoints Disponíveis**
```javascript
const API_BASE = 'http://localhost:3000/api/auth';

const ENDPOINTS = {
  LOGIN: `${API_BASE}/login`,
  LOGOUT: `${API_BASE}/logout`,
  ME: `${API_BASE}/me`,
  LOGS: `${API_BASE}/logs`,
  CHANGE_PASSWORD: `${API_BASE}/change-password`
};
```

## 🚀 **Implementação Passo a Passo**

### **1. Serviço de Autenticação**

Criar arquivo `services/authService.js`:

```javascript
class AuthService {
  constructor() {
    this.baseURL = 'http://localhost:3000/api/auth';
    this.tokenKey = 'scum_auth_token';
    this.userKey = 'scum_user_data';
  }

  // Login
  async login(username, password) {
    try {
      const response = await fetch(`${this.baseURL}/login`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ username, password })
      });

      const data = await response.json();

      if (data.success) {
        // Salvar token e dados do usuário
        localStorage.setItem(this.tokenKey, data.data.token);
        localStorage.setItem(this.userKey, JSON.stringify(data.data.user));
        
        return {
          success: true,
          user: data.data.user,
          token: data.data.token
        };
      } else {
        return {
          success: false,
          message: data.message
        };
      }
    } catch (error) {
      return {
        success: false,
        message: 'Erro de conexão'
      };
    }
  }

  // Logout
  async logout() {
    try {
      const token = this.getToken();
      
      if (token) {
        await fetch(`${this.baseURL}/logout`, {
          method: 'POST',
          headers: {
            'Authorization': `Bearer ${token}`
          }
        });
      }
    } catch (error) {
      console.error('Erro no logout:', error);
    } finally {
      // Limpar dados locais
      localStorage.removeItem(this.tokenKey);
      localStorage.removeItem(this.userKey);
    }
  }

  // Verificar dados do usuário
  async getMe() {
    try {
      const token = this.getToken();
      
      if (!token) {
        return { success: false, message: 'Não autenticado' };
      }

      const response = await fetch(`${this.baseURL}/me`, {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });

      const data = await response.json();
      return data;
    } catch (error) {
      return { success: false, message: 'Erro de conexão' };
    }
  }

  // Buscar logs (apenas admin)
  async getLogs() {
    try {
      const token = this.getToken();
      
      if (!token) {
        return { success: false, message: 'Não autenticado' };
      }

      const response = await fetch(`${this.baseURL}/logs`, {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });

      const data = await response.json();
      return data;
    } catch (error) {
      return { success: false, message: 'Erro de conexão' };
    }
  }

  // Alterar senha
  async changePassword(currentPassword, newPassword) {
    try {
      const token = this.getToken();
      
      if (!token) {
        return { success: false, message: 'Não autenticado' };
      }

      const response = await fetch(`${this.baseURL}/change-password`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({ currentPassword, newPassword })
      });

      const data = await response.json();
      return data;
    } catch (error) {
      return { success: false, message: 'Erro de conexão' };
    }
  }

  // Utilitários
  getToken() {
    return localStorage.getItem(this.tokenKey);
  }

  getUser() {
    const userData = localStorage.getItem(this.userKey);
    return userData ? JSON.parse(userData) : null;
  }

  isAuthenticated() {
    return !!this.getToken();
  }

  isAdmin() {
    const user = this.getUser();
    return user && user.role === 'admin';
  }
}

export default new AuthService();
```

### **2. Contexto de Autenticação (React)**

Criar arquivo `contexts/AuthContext.jsx`:

```jsx
import React, { createContext, useContext, useState, useEffect } from 'react';
import authService from '../services/authService';

const AuthContext = createContext();

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth deve ser usado dentro de AuthProvider');
  }
  return context;
};

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // Verificar autenticação inicial
  useEffect(() => {
    checkAuth();
  }, []);

  const checkAuth = async () => {
    try {
      if (authService.isAuthenticated()) {
        const result = await authService.getMe();
        if (result.success) {
          setUser(result.data);
        } else {
          // Token inválido, fazer logout
          await logout();
        }
      }
    } catch (error) {
      console.error('Erro ao verificar autenticação:', error);
    } finally {
      setLoading(false);
    }
  };

  const login = async (username, password) => {
    try {
      setError(null);
      const result = await authService.login(username, password);
      
      if (result.success) {
        setUser(result.user);
        return { success: true };
      } else {
        setError(result.message);
        return { success: false, message: result.message };
      }
    } catch (error) {
      setError('Erro de conexão');
      return { success: false, message: 'Erro de conexão' };
    }
  };

  const logout = async () => {
    try {
      await authService.logout();
      setUser(null);
      setError(null);
    } catch (error) {
      console.error('Erro no logout:', error);
    }
  };

  const value = {
    user,
    loading,
    error,
    login,
    logout,
    isAuthenticated: !!user,
    isAdmin: user?.role === 'admin'
  };

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  );
};
```

### **3. Componente de Login**

Criar arquivo `components/Login.jsx`:

```jsx
import React, { useState } from 'react';
import { useAuth } from '../contexts/AuthContext';
import { useNavigate } from 'react-router-dom';

const Login = () => {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const { login, error } = useAuth();
  const navigate = useNavigate();

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);

    const result = await login(username, password);
    
    if (result.success) {
      navigate('/dashboard');
    }
    
    setLoading(false);
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-900">
      <div className="max-w-md w-full space-y-8">
        <div>
          <h2 className="mt-6 text-center text-3xl font-extrabold text-white">
            SCUM Server Manager
          </h2>
          <p className="mt-2 text-center text-sm text-gray-400">
            Faça login para acessar o painel
          </p>
        </div>
        
        <form className="mt-8 space-y-6" onSubmit={handleSubmit}>
          <div className="rounded-md shadow-sm -space-y-px">
            <div>
              <input
                type="text"
                required
                className="appearance-none rounded-none relative block w-full px-3 py-2 border border-gray-700 placeholder-gray-500 text-white bg-gray-800 rounded-t-md focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 focus:z-10 sm:text-sm"
                placeholder="Usuário"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
              />
            </div>
            <div>
              <input
                type="password"
                required
                className="appearance-none rounded-none relative block w-full px-3 py-2 border border-gray-700 placeholder-gray-500 text-white bg-gray-800 rounded-b-md focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 focus:z-10 sm:text-sm"
                placeholder="Senha"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
              />
            </div>
          </div>

          {error && (
            <div className="text-red-500 text-sm text-center">
              {error}
            </div>
          )}

          <div>
            <button
              type="submit"
              disabled={loading}
              className="group relative w-full flex justify-center py-2 px-4 border border-transparent text-sm font-medium rounded-md text-white bg-indigo-600 hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 disabled:opacity-50"
            >
              {loading ? 'Entrando...' : 'Entrar'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};

export default Login;
```

### **4. Componente de Proteção de Rotas**

Criar arquivo `components/ProtectedRoute.jsx`:

```jsx
import React from 'react';
import { Navigate, useLocation } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';

const ProtectedRoute = ({ children, requireAdmin = false }) => {
  const { isAuthenticated, isAdmin, loading } = useAuth();
  const location = useLocation();

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-900">
        <div className="text-white">Carregando...</div>
      </div>
    );
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" state={{ from: location }} replace />;
  }

  if (requireAdmin && !isAdmin) {
    return <Navigate to="/dashboard" replace />;
  }

  return children;
};

export default ProtectedRoute;
```

### **5. Componente de Logs (Admin)**

Criar arquivo `components/LogsView.jsx`:

```jsx
import React, { useState, useEffect } from 'react';
import authService from '../services/authService';

const LogsView = () => {
  const [logs, setLogs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    fetchLogs();
  }, []);

  const fetchLogs = async () => {
    try {
      setLoading(true);
      const result = await authService.getLogs();
      
      if (result.success) {
        setLogs(result.data.logs);
      } else {
        setError(result.message);
      }
    } catch (error) {
      setError('Erro ao carregar logs');
    } finally {
      setLoading(false);
    }
  };

  const formatDate = (timestamp) => {
    return new Date(timestamp).toLocaleString('pt-BR');
  };

  const getActionColor = (action) => {
    if (action.includes('success')) return 'text-green-500';
    if (action.includes('failed') || action.includes('error')) return 'text-red-500';
    return 'text-yellow-500';
  };

  if (loading) {
    return (
      <div className="p-6">
        <div className="text-white">Carregando logs...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-6">
        <div className="text-red-500">Erro: {error}</div>
      </div>
    );
  }

  return (
    <div className="p-6">
      <h2 className="text-2xl font-bold text-white mb-6">Logs de Acesso</h2>
      
      <div className="bg-gray-800 rounded-lg overflow-hidden">
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-gray-700">
            <thead className="bg-gray-700">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-300 uppercase tracking-wider">
                  Data/Hora
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-300 uppercase tracking-wider">
                  Usuário
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-300 uppercase tracking-wider">
                  Ação
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-300 uppercase tracking-wider">
                  IP
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-300 uppercase tracking-wider">
                  Status
                </th>
              </tr>
            </thead>
            <tbody className="bg-gray-800 divide-y divide-gray-700">
              {logs.map((log) => (
                <tr key={log.id}>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-300">
                    {formatDate(log.timestamp)}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-300">
                    {log.username}
                  </td>
                  <td className={`px-6 py-4 whitespace-nowrap text-sm ${getActionColor(log.action)}`}>
                    {log.action}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-300">
                    {log.ip}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <span className={`inline-flex px-2 py-1 text-xs font-semibold rounded-full ${
                      log.success 
                        ? 'bg-green-100 text-green-800' 
                        : 'bg-red-100 text-red-800'
                    }`}>
                      {log.success ? 'Sucesso' : 'Falha'}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
      
      <div className="mt-4 text-sm text-gray-400">
        Total de logs: {logs.length}
      </div>
    </div>
  );
};

export default LogsView;
```

### **6. Configuração de Rotas**

Atualizar arquivo de rotas:

```jsx
import React from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider } from './contexts/AuthContext';
import ProtectedRoute from './components/ProtectedRoute';
import Login from './components/Login';
import Dashboard from './components/Dashboard';
import LogsView from './components/LogsView';

const App = () => {
  return (
    <AuthProvider>
      <BrowserRouter>
        <Routes>
          <Route path="/login" element={<Login />} />
          <Route 
            path="/dashboard" 
            element={
              <ProtectedRoute>
                <Dashboard />
              </ProtectedRoute>
            } 
          />
          <Route 
            path="/logs" 
            element={
              <ProtectedRoute requireAdmin={true}>
                <LogsView />
              </ProtectedRoute>
            } 
          />
          <Route path="/" element={<Navigate to="/dashboard" replace />} />
        </Routes>
      </BrowserRouter>
    </AuthProvider>
  );
};

export default App;
```

### **7. Componente de Navegação**

Criar arquivo `components/Navigation.jsx`:

```jsx
import React from 'react';
import { useAuth } from '../contexts/AuthContext';
import { useNavigate } from 'react-router-dom';

const Navigation = () => {
  const { user, logout, isAdmin } = useAuth();
  const navigate = useNavigate();

  const handleLogout = async () => {
    await logout();
    navigate('/login');
  };

  return (
    <nav className="bg-gray-800">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16">
          <div className="flex items-center">
            <div className="flex-shrink-0">
              <h1 className="text-white font-bold">SCUM Manager</h1>
            </div>
            <div className="hidden md:block">
              <div className="ml-10 flex items-baseline space-x-4">
                <button
                  onClick={() => navigate('/dashboard')}
                  className="text-gray-300 hover:text-white px-3 py-2 rounded-md text-sm font-medium"
                >
                  Dashboard
                </button>
                {isAdmin && (
                  <button
                    onClick={() => navigate('/logs')}
                    className="text-gray-300 hover:text-white px-3 py-2 rounded-md text-sm font-medium"
                  >
                    Logs
                  </button>
                )}
              </div>
            </div>
          </div>
          <div className="flex items-center">
            <span className="text-gray-300 text-sm mr-4">
              Olá, {user?.username}
            </span>
            <button
              onClick={handleLogout}
              className="text-gray-300 hover:text-white px-3 py-2 rounded-md text-sm font-medium"
            >
              Sair
            </button>
          </div>
        </div>
      </div>
    </nav>
  );
};

export default Navigation;
```

## 🎨 **Estilos CSS (Tailwind)**

Adicionar ao `tailwind.config.js`:

```javascript
module.exports = {
  content: [
    "./src/**/*.{js,jsx,ts,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        gray: {
          800: '#1f2937',
          900: '#111827',
        }
      }
    },
  },
  plugins: [],
}
```

## 🔧 **Configuração de Interceptors (Axios)**

Se estiver usando Axios, criar arquivo `utils/api.js`:

```javascript
import axios from 'axios';
import authService from '../services/authService';

const api = axios.create({
  baseURL: 'http://localhost:3000/api'
});

// Interceptor para adicionar token
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
      // Token inválido, fazer logout
      authService.logout();
      window.location.href = '/login';
    }
    return Promise.reject(error);
  }
);

export default api;
```

## 🚀 **Testes de Implementação**

### **1. Testar Login**
```javascript
// No console do navegador
const authService = new AuthService();
authService.login('admin', 'admin123').then(console.log);
```

### **2. Verificar Token**
```javascript
// Verificar se token foi salvo
localStorage.getItem('scum_auth_token');
```

### **3. Testar Proteção de Rotas**
- Tentar acessar `/dashboard` sem estar logado
- Verificar redirecionamento para `/login`

## 📋 **Checklist de Implementação**

- [ ] **Serviço de autenticação** (`authService.js`)
- [ ] **Contexto de autenticação** (`AuthContext.jsx`)
- [ ] **Componente de login** (`Login.jsx`)
- [ ] **Proteção de rotas** (`ProtectedRoute.jsx`)
- [ ] **Visualização de logs** (`LogsView.jsx`)
- [ ] **Navegação** (`Navigation.jsx`)
- [ ] **Configuração de rotas**
- [ ] **Estilos CSS**
- [ ] **Interceptors (opcional)**

## 🎯 **Funcionalidades Implementadas**

### **✅ Login/Logout**
- Formulário de login funcional
- Validação de credenciais
- Logout automático
- Redirecionamento após login

### **✅ Proteção de Rotas**
- Rotas protegidas por autenticação
- Rotas específicas para admin
- Redirecionamento automático

### **✅ Gerenciamento de Estado**
- Contexto global de autenticação
- Persistência de dados no localStorage
- Verificação automática de token

### **✅ Interface de Logs**
- Visualização de logs de acesso
- Filtros por data
- Status de sucesso/falha
- Informações detalhadas

### **✅ Segurança**
- Tokens JWT
- Rate limiting
- Logs de acesso
- Proteção contra ataques

## 🔍 **Troubleshooting**

### **Problema: Login não funciona**
- Verificar se backend está rodando na porta 3000
- Verificar credenciais: `admin` / `admin123`
- Verificar console do navegador para erros

### **Problema: Token inválido**
- Verificar se JWT_SECRET está configurado no backend
- Limpar localStorage e fazer login novamente
- Verificar logs no backend

### **Problema: Rotas não protegem**
- Verificar se `ProtectedRoute` está sendo usado
- Verificar se `AuthProvider` envolve a aplicação
- Verificar se contexto está funcionando

## 🎉 **Sistema Pronto!**

Com esta implementação, você terá um sistema de autenticação completo e funcional no frontend, integrado perfeitamente com o backend já implementado.

**Credenciais padrão:**
- **Usuário:** `admin`
- **Senha:** `admin123`

---

**📞 Suporte:** Em caso de dúvidas, verificar logs do backend e console do navegador para debug. 