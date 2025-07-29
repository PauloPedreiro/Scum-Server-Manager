# 🔐 Sistema de Autenticação - Frontend

## 📋 **Visão Geral**

O sistema de autenticação foi implementado no frontend para se conectar com o backend real. O sistema inclui login, logout, proteção de rotas, visualização de logs e alteração de senha.

## 🎯 **Funcionalidades Implementadas**

### ✅ **Login/Logout**
- Formulário de login funcional com validação
- Logout automático com limpeza de dados
- Redirecionamento após login/logout
- Credenciais padrão: `admin` / `admin123`

### ✅ **Proteção de Rotas**
- Rotas protegidas por autenticação
- Rotas específicas para admin (`/logs`)
- Redirecionamento automático para login
- Loading state durante verificação

### ✅ **Gerenciamento de Estado**
- Contexto global de autenticação (`useAuth`)
- Persistência de dados no localStorage
- Verificação automática de token
- Estados de loading e erro

### ✅ **Interface de Logs (Admin)**
- Visualização de logs de acesso
- Filtros por data e status
- Atualização manual de logs
- Interface responsiva

### ✅ **Alteração de Senha**
- Modal para alteração de senha
- Validação de senhas
- Feedback visual de erros
- Integração com backend

## 🔧 **Arquivos Implementados**

### **1. Serviço de Autenticação**
- **Arquivo:** `src/services/authService.ts`
- **Função:** Comunicação com backend
- **Métodos:**
  - `login(username, password)`
  - `logout()`
  - `getMe()`
  - `getLogs()`
  - `changePassword(currentPassword, newPassword)`

### **2. Hook de Autenticação**
- **Arquivo:** `src/hooks/useAuth.tsx`
- **Função:** Gerenciamento de estado global
- **Estados:**
  - `user`: Dados do usuário
  - `token`: Token JWT
  - `isLoading`: Estado de carregamento
  - `error`: Mensagens de erro
  - `isAuthenticated`: Se está autenticado
  - `isAdmin`: Se é administrador

### **3. Proteção de Rotas**
- **Arquivo:** `src/components/ProtectedRoute.tsx`
- **Função:** Proteger rotas por autenticação
- **Recursos:**
  - Verificação de autenticação
  - Verificação de permissões admin
  - Loading state
  - Redirecionamento automático

### **4. Visualização de Logs**
- **Arquivo:** `src/components/AuthLogsView.tsx`
- **Função:** Interface para logs de acesso
- **Recursos:**
  - Tabela responsiva
  - Filtros visuais
  - Atualização manual
  - Formatação de datas

### **5. Alteração de Senha**
- **Arquivo:** `src/components/ChangePasswordModal.tsx`
- **Função:** Modal para alterar senha
- **Recursos:**
  - Validação de campos
  - Feedback visual
  - Integração com backend

### **6. Configuração de Rotas**
- **Arquivo:** `src/main.tsx`
- **Função:** Configuração de rotas da aplicação
- **Rotas:**
  - `/login`: Página de login
  - `/dashboard`: Dashboard principal (protegida)
  - `/logs`: Logs de acesso (protegida, admin)

## 🚀 **Como Usar**

### **1. Login**
1. Acesse a aplicação
2. Digite as credenciais: `admin` / `admin123`
3. Clique em "ACESSAR SISTEMA"
4. Será redirecionado para o dashboard

### **2. Visualizar Logs (Admin)**
1. Faça login como admin
2. Clique no ícone de logs no header (📄)
3. Visualize os logs de acesso
4. Use o botão "Atualizar" para recarregar

### **3. Alterar Senha**
1. Clique no ícone de cadeado no header (🔒)
2. Digite a senha atual
3. Digite a nova senha
4. Confirme a nova senha
5. Clique em "Alterar Senha"

### **4. Logout**
1. Clique no ícone de logout no header (🚪)
2. Será redirecionado para a página de login
3. Dados serão limpos automaticamente

## 🔍 **Estrutura de Dados**

### **User Interface**
```typescript
interface User {
  id: string;
  username: string;
  steamId?: string | null;
  role: string;
  permissions: string[];
  profile: {
    firstName: string;
    lastName: string;
    avatar?: string | null;
    timezone: string;
    language: string;
  };
  isFirstLogin: boolean;
  requiresPasswordChange: boolean;
}
```

### **Auth Log Interface**
```typescript
interface AuthLog {
  id: string;
  timestamp: string;
  username: string;
  action: string;
  ip: string;
  success: boolean;
}
```

## 🔧 **Configuração**

### **Backend URL**
O sistema está configurado para conectar com:
```
http://localhost:3000/api/auth
```

### **Endpoints Utilizados**
- `POST /api/auth/login` - Login
- `POST /api/auth/logout` - Logout
- `GET /api/auth/me` - Verificar usuário
- `GET /api/auth/logs` - Buscar logs
- `POST /api/auth/change-password` - Alterar senha

### **LocalStorage Keys**
- `scum_auth_token` - Token JWT
- `scum_user_data` - Dados do usuário

## 🎨 **Interface**

### **Página de Login**
- Design responsivo
- Animações suaves
- Validação em tempo real
- Credenciais de teste visíveis

### **Dashboard Header**
- Status do servidor
- Contagem de jogadores
- Botões de ação (logs, alterar senha, logout)
- Indicadores visuais

### **Logs View**
- Tabela responsiva
- Filtros visuais
- Status coloridos
- Atualização manual

### **Change Password Modal**
- Modal responsivo
- Validação de campos
- Feedback visual
- Animações suaves

## 🔒 **Segurança**

### **Token JWT**
- Armazenado no localStorage
- Verificação automática de validade
- Limpeza automática em caso de invalidez

### **Proteção de Rotas**
- Verificação de autenticação
- Verificação de permissões
- Redirecionamento automático

### **Validação**
- Validação de campos obrigatórios
- Validação de senhas
- Feedback de erros

## 🐛 **Troubleshooting**

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

### **Problema: Logs não aparecem**
- Verificar se usuário tem permissão de admin
- Verificar se endpoint `/api/auth/logs` está funcionando
- Verificar console para erros de rede

## 📋 **Checklist de Implementação**

- [x] **Serviço de autenticação** (`authService.ts`)
- [x] **Contexto de autenticação** (`useAuth.tsx`)
- [x] **Proteção de rotas** (`ProtectedRoute.tsx`)
- [x] **Visualização de logs** (`AuthLogsView.tsx`)
- [x] **Alteração de senha** (`ChangePasswordModal.tsx`)
- [x] **Configuração de rotas** (`main.tsx`)
- [x] **Interface de login** (`Login.tsx`)
- [x] **Header com ações** (`DashboardHeader.tsx`)

## 🎉 **Sistema Pronto!**

O sistema de autenticação está **100% funcional** e integrado com o backend. Todas as funcionalidades estão implementadas e testadas.

**Credenciais padrão:**
- **Usuário:** `admin`
- **Senha:** `admin123`

---

**📞 Suporte:** Em caso de dúvidas, verificar logs do backend e console do navegador para debug. 