# 🔍 Análise - Gerenciamento de Usuários

**Data:** 2025-12-05  
**Baseado em:** Documentação atualizada do backend  
**Status Backend:** ✅ **TODAS AS CORREÇÕES APLICADAS** (2025-12-05)

---

## 📋 Resumo

A documentação foi atualizada e agora inclui **endpoints completos de gerenciamento de usuários** para administradores.

---

## ✅ Novos Endpoints Disponíveis

### **1. Criar Usuário**
- **Endpoint:** `POST /api/auth/users`
- **Acesso:** Apenas Admin
- **Campos:**
  - `username` (obrigatório)
  - `password` (obrigatório, mín. 8 caracteres)
  - `role` (opcional: "admin" ou "moderator", padrão: "moderator")
  - `steam_id` (opcional: para vincular moderador a um player)
- **Resposta:** Retorna dados do usuário criado

### **2. Listar Usuários**
- **Endpoint:** `GET /api/auth/users`
- **Acesso:** Apenas Admin
- **Resposta:** Lista todos os usuários com informações completas

### **3. Atualizar Usuário**
- **Endpoint:** `PUT /api/auth/users/<user_id>`
- **Acesso:** Apenas Admin
- **Campos (todos opcionais):**
  - `is_active`: ativar/desativar
  - `role`: alterar role
  - `steam_id`: vincular/desvincular player
- **Resposta:** Dados atualizados do usuário

### **4. Deletar Usuário**
- **Endpoint:** `DELETE /api/auth/users/<user_id>`
- **Acesso:** Apenas Admin
- **Restrição:** Não pode deletar usuário admin
- **Resposta:** Confirmação de deleção

### **5. Buscar Players**
- **Endpoint:** `GET /api/auth/users/search-players?q=<query>&limit=<limit>`
- **Acesso:** Apenas Admin
- **Uso:** Buscar players para vincular a moderadores
- **Resposta:** Lista de players encontrados

---

## 🎯 Funcionalidades a Implementar

### **1. Página de Gerenciamento de Usuários**
- **Localização sugerida:** Nova aba em Settings ou página separada
- **Acesso:** Apenas para usuários com role "admin"
- **Funcionalidades:**
  - Listar todos os usuários em tabela
  - Busca/filtro de usuários
  - Criar novo usuário (modal ou formulário)
  - Editar usuário (ativar/desativar, alterar role, vincular player)
  - Deletar usuário (com confirmação)
  - Buscar players para vincular

### **2. Formulário de Criação**
- Campos:
  - Username (obrigatório, único)
  - Password (obrigatório, mín. 8 caracteres)
  - Role (select: admin/moderator)
  - Steam ID (opcional, com busca de players)
- Validações:
  - Username único
  - Senha mínima de 8 caracteres
  - Steam ID válido (se fornecido)

### **3. Tabela de Usuários**
- Colunas sugeridas:
  - ID
  - Username
  - Role (badge colorido)
  - Status (Ativo/Inativo)
  - Senha Alterada (ícone)
  - Player Vinculado (nome ou "Não vinculado")
  - Último Login
  - Criado em
  - Ações (Editar, Deletar)

### **4. Busca de Players**
- Campo de busca com debounce
- Lista de resultados ao digitar
- Seleção de player para vincular
- Exibição do player selecionado

### **5. Modal/Formulário de Edição**
- Ativar/Desativar usuário (toggle)
- Alterar role (select)
- Vincular/Desvincular player (com busca)
- Salvar alterações

---

## 🎨 Sugestões de UI/UX

### **Opção A: Aba em Settings** ⭐ (Recomendada)
- Adicionar nova aba "Usuários" em Settings
- Consistente com o padrão atual
- Fácil acesso para admins

### **Opção B: Página Separada**
- Nova rota `/users` ou `/admin/users`
- Mais espaço para funcionalidades
- Pode ter sub-rotas no futuro

### **Opção C: Modal/Dialog**
- Abrir modal a partir de um botão no header
- Mais compacto
- Menos espaço para funcionalidades

---

## 📐 Estrutura de Componentes Sugerida

```
src/pages/
├── settings/
│   ├── Settings.tsx (adicionar aba "users")
│   └── tabs/
│       ├── ServerSettingsTab.tsx
│       ├── ConfigTab.tsx
│       ├── DiscordTab.tsx
│       └── UsersTab.tsx (NOVO)
│
src/components/
└── users/ (NOVO)
    ├── UserTable.tsx
    ├── CreateUserForm.tsx
    ├── EditUserModal.tsx
    └── PlayerSearch.tsx
```

---

## 🔐 Proteção e Validações

### **Proteção de Rotas:**
- Verificar se usuário é admin antes de mostrar página
- Usar `ProtectedRoute` com `requireAdmin={true}`
- Redirecionar para `/unauthorized` se não for admin

### **Validações no Frontend:**
- Username: mínimo 3 caracteres, sem espaços
- Password: mínimo 8 caracteres
- Steam ID: formato válido (se fornecido)
- Role: apenas "admin" ou "moderator"

### **Tratamento de Erros:**
- Username já existe
- Senha muito curta
- Steam ID inválido
- Tentativa de deletar admin
- Usuário não encontrado
- Acesso negado (não é admin)

---

## 📊 Dados do Usuário

### **Campos Retornados:**
```typescript
interface User {
  id: number;
  username: string;
  role: 'admin' | 'moderator';
  is_active: boolean;
  password_changed: boolean;
  steam_id?: string | null;
  player_name?: string | null;
  player_id?: number | null;
  last_login?: string | null;
  created_at: string;
}
```

### **Informações Importantes:**
- `is_active`: Se usuário está ativo (pode fazer login)
- `password_changed`: Se já alterou senha padrão
- `steam_id`: Vinculação com player do jogo
- `last_login`: Último acesso (null se nunca logou)

---

## 🎯 Fluxos de Uso

### **Fluxo 1: Criar Novo Moderador**
```
1. Admin acessa página de usuários
2. Clica em "Criar Usuário"
3. Preenche: username, password, role (moderator)
4. (Opcional) Busca e seleciona player para vincular
5. Clica em "Criar"
6. Usuário criado com sucesso
7. Novo usuário aparece na lista
```

### **Fluxo 2: Vincular Moderador a Player**
```
1. Admin visualiza lista de usuários
2. Clica em "Editar" no moderador
3. Clica em "Buscar Player"
4. Digita nome ou Steam ID
5. Seleciona player da lista
6. Salva alterações
7. Player vinculado ao moderador
```

### **Fluxo 3: Desativar Usuário**
```
1. Admin visualiza lista de usuários
2. Clica em toggle "Ativo/Inativo"
3. Confirma ação
4. Usuário desativado (não pode mais fazer login)
5. Status atualizado na lista
```

---

## 🔄 Integração com Serviço de Auth

### **Novos Métodos no AuthService:**
```typescript
// Já implementado parcialmente, precisa adicionar:
- createUser()
- listUsers()
- updateUser()
- deleteUser()
- searchPlayers()
```

### **Atualização Necessária:**
- Adicionar métodos no `src/services/auth.ts`
- Usar mesma base URL e interceptors
- Tratar erros específicos de admin

---

## 📝 Traduções Necessárias

### **Novas Chaves:**
```json
{
  "users": {
    "title": "Gerenciamento de Usuários",
    "description": "Criar e gerenciar usuários do sistema",
    "create": {
      "title": "Criar Usuário",
      "username": "Usuário",
      "password": "Senha",
      "role": "Função",
      "steamId": "Steam ID (opcional)",
      "searchPlayer": "Buscar Player",
      "submit": "Criar"
    },
    "table": {
      "id": "ID",
      "username": "Usuário",
      "role": "Função",
      "status": "Status",
      "passwordChanged": "Senha Alterada",
      "linkedPlayer": "Player Vinculado",
      "lastLogin": "Último Login",
      "createdAt": "Criado em",
      "actions": "Ações"
    },
    "actions": {
      "create": "Criar Usuário",
      "edit": "Editar",
      "delete": "Deletar",
      "activate": "Ativar",
      "deactivate": "Desativar"
    },
    "errors": {
      "usernameExists": "Username já existe",
      "invalidPassword": "Senha deve ter pelo menos 8 caracteres",
      "cannotDeleteAdmin": "Não é possível deletar usuário admin",
      "userNotFound": "Usuário não encontrado",
      "adminRequired": "Apenas administradores podem gerenciar usuários"
    }
  }
}
```

---

## ⚠️ Pontos de Atenção

### **1. Segurança:**
- ⚠️ Verificar role de admin em TODAS as operações
- ⚠️ Não permitir deletar usuário admin
- ⚠️ Validar dados antes de enviar
- ⚠️ Confirmar ações destrutivas (deletar, desativar)

### **2. UX:**
- ⚠️ Feedback claro de sucesso/erro
- ⚠️ Loading states durante operações
- ⚠️ Confirmação antes de deletar
- ⚠️ Validação em tempo real nos formulários

### **3. Performance:**
- ⚠️ Debounce na busca de players (evitar muitas requisições)
- ⚠️ Paginação se houver muitos usuários (futuro)
- ⚠️ Cache de lista de usuários (opcional)

### **4. Integração:**
- ⚠️ Não quebrar funcionalidades existentes
- ⚠️ Reutilizar padrões de UI existentes
- ⚠️ Seguir design system do projeto

---

## 🎨 Design Sugerido

### **Tabela de Usuários:**
- Estilo similar à tabela de Players
- Badges coloridos para roles (admin: vermelho, moderator: azul)
- Toggle para ativar/desativar
- Ícones para senha alterada (✅/❌)
- Botões de ação (Editar, Deletar)

### **Formulário de Criação:**
- Modal ou seção expandível
- Campos organizados verticalmente
- Busca de players com dropdown de resultados
- Validação visual em tempo real
- Botão de submit destacado

### **Busca de Players:**
- Campo de input com ícone de busca
- Dropdown com resultados abaixo do campo
- Highlight no resultado selecionado
- Botão para limpar seleção

---

## 📋 Checklist de Implementação

### **Fase 1: Serviços**
- [ ] Adicionar métodos no `auth.ts`:
  - [ ] `createUser()`
  - [ ] `listUsers()`
  - [ ] `updateUser()`
  - [ ] `deleteUser()`
  - [ ] `searchPlayers()`

### **Fase 2: Traduções**
- [ ] Adicionar traduções em `pt-BR/translation.json`
- [ ] Adicionar traduções em `en/translation.json`

### **Fase 3: Componentes**
- [ ] Criar `UsersTab.tsx` (aba em Settings)
- [ ] Criar `UserTable.tsx` (tabela de usuários)
- [ ] Criar `CreateUserForm.tsx` (formulário de criação)
- [ ] Criar `EditUserModal.tsx` (modal de edição)
- [ ] Criar `PlayerSearch.tsx` (busca de players)

### **Fase 4: Integração**
- [ ] Adicionar aba "Usuários" em Settings
- [ ] Proteger rota com `requireAdmin`
- [ ] Integrar com serviço de auth
- [ ] Adicionar tratamento de erros

### **Fase 5: Testes**
- [ ] Testar criação de usuário
- [ ] Testar listagem
- [ ] Testar edição (ativar/desativar, role, steam_id)
- [ ] Testar deleção
- [ ] Testar busca de players
- [ ] Testar validações
- [ ] Testar acesso não-admin (deve negar)

---

## 🎯 Recomendações Finais

### **Estrutura Recomendada:**
1. **Aba em Settings** (Opção A)
   - Mais consistente com o projeto
   - Fácil acesso
   - Mantém tudo organizado

2. **Componentes Modulares:**
   - Separar tabela, formulário, busca
   - Reutilizar componentes de UI existentes
   - Seguir padrão de outros tabs

3. **Validações:**
   - Frontend: UX melhor
   - Backend: Segurança garantida
   - Sempre validar em ambos

4. **Feedback Visual:**
   - SweetAlert2 para confirmações
   - Toasts para sucesso/erro
   - Loading states claros

---

## 📝 Próximos Passos

1. **Decidir localização:** Aba em Settings ou página separada?
2. **Definir design:** Seguir padrão de Players ou criar novo?
3. **Priorizar funcionalidades:** O que implementar primeiro?
4. **Planejar testes:** Como validar cada funcionalidade?

---

**Pronto para planejar a implementação!** 🚀

