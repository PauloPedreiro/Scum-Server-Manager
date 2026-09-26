# 📋 Planejamento - Implementação de Recuperação de Senha

**Data:** 2025-01-XX  
**Status:** 🟡 Em Planejamento

---

## 📋 Visão Geral

Implementar sistema de recuperação de senha na tela de login, permitindo que usuários admin resetem sua senha quando esquecida. O processo utiliza tokens únicos enviados via webhook Discord.

---

## 🎯 Objetivos

1. ✅ Adicionar link "Esqueci minha senha" na tela de login
2. ✅ Criar modal/fluxo para solicitar reset de senha
3. ✅ Criar modal/fluxo para resetar senha com token
4. ✅ Integrar com endpoints do backend
5. ✅ Adicionar validações client-side
6. ✅ Implementar tratamento de erros
7. ✅ Adicionar traduções (PT-BR e EN)
8. ✅ Manter consistência visual com o design existente

---

## 🏗️ Arquitetura da Solução

### **Estrutura de Arquivos**

```
src/
├── services/
│   └── auth.ts                    # Adicionar funções requestPasswordReset() e resetPassword()
├── pages/
│   └── auth/
│       └── Login.tsx              # Adicionar link e modais de recuperação
└── i18n/
    └── locales/
        ├── pt-BR/
        │   └── translation.json   # Adicionar traduções PT-BR
        └── en/
            └── translation.json   # Adicionar traduções EN
```

---

## 🔄 Fluxo de Implementação

### **Fase 1: Serviços de API** ✅

**Arquivo:** `src/services/auth.ts`

**Tarefas:**
1. Adicionar interface `RequestPasswordResetResponse`
2. Adicionar interface `ResetPasswordResponse`
3. Implementar função `requestPasswordReset(username: string)`
4. Implementar função `resetPassword(token: string, newPassword: string)`

**Código base:**
```typescript
// Interfaces
export interface RequestPasswordResetResponse {
  success: boolean;
  message: string;
}

export interface ResetPasswordResponse {
  success: boolean;
  message?: string;
  error?: string;
}

// Funções
export async function requestPasswordReset(username: string): Promise<RequestPasswordResetResponse> {
  const { data } = await api.post<RequestPasswordResetResponse>('/auth/request-password-reset', {
    username
  });
  return data;
}

export async function resetPassword(token: string, newPassword: string): Promise<ResetPasswordResponse> {
  const { data } = await api.post<ResetPasswordResponse>('/auth/reset-password', {
    token,
    new_password: newPassword
  });
  return data;
}
```

---

### **Fase 2: Traduções** ✅

**Arquivos:** 
- `src/i18n/locales/pt-BR/translation.json`
- `src/i18n/locales/en/translation.json`

**Chaves a adicionar:**
```json
{
  "auth": {
    "passwordReset": {
      "forgotPassword": "Esqueci minha senha",
      "requestReset": {
        "title": "Recuperar Senha",
        "subtitle": "Solicite um token de recuperação",
        "username": "Usuário",
        "usernamePlaceholder": "Digite seu usuário",
        "submit": "Solicitar Token",
        "loading": "Enviando...",
        "success": "Se o usuário existir, um token foi enviado via Discord. Verifique o canal log-ssm.",
        "info": "O token será enviado para o webhook Discord configurado (log-ssm).",
        "errors": {
          "networkError": "Erro ao solicitar reset. Tente novamente."
        }
      },
      "resetPassword": {
        "title": "Resetar Senha",
        "subtitle": "Digite o token recebido e sua nova senha",
        "token": "Token",
        "tokenPlaceholder": "Cole o token recebido do Discord",
        "newPassword": "Nova Senha",
        "newPasswordPlaceholder": "Digite a nova senha (mín. 8 caracteres)",
        "confirmPassword": "Confirmar Nova Senha",
        "confirmPasswordPlaceholder": "Confirme a nova senha",
        "submit": "Resetar Senha",
        "loading": "Resetando...",
        "success": "Senha alterada com sucesso! Redirecionando...",
        "errors": {
          "tokenInvalid": "Token inválido ou expirado",
          "passwordMinLength": "A senha deve ter no mínimo 8 caracteres",
          "passwordMismatch": "As senhas não coincidem",
          "networkError": "Erro ao resetar senha. Verifique o token e tente novamente.",
          "required": "Por favor, preencha todos os campos"
        }
      }
    }
  }
}
```

---

### **Fase 3: Componente de Login** ✅

**Arquivo:** `src/pages/auth/Login.tsx`

**Modificações:**

1. **Adicionar estados:**
   - `showRequestResetModal: boolean`
   - `showResetPasswordModal: boolean`
   - Estados para formulários de reset

2. **Adicionar link "Esqueci minha senha":**
   - Abaixo do botão de login
   - Estilo: texto pequeno, link, cor scum-orange

3. **Modal 1: Solicitar Reset**
   - Formulário com campo username
   - Botão "Solicitar Token"
   - Mensagem informativa sobre Discord
   - Feedback de sucesso/erro

4. **Modal 2: Resetar Senha**
   - Formulário com campos: token, nova senha, confirmar senha
   - Validações client-side
   - Botão "Resetar Senha"
   - Feedback de sucesso/erro
   - Redirecionamento após sucesso

**Design:**
- Usar SweetAlert2 para modais (já usado no projeto)
- OU criar modais customizados com Framer Motion (consistência visual)
- Manter estilo do card de login

**Decisão:** Usar modais customizados com Framer Motion para melhor integração visual.

---

## 🎨 Design e UX

### **Modal de Solicitar Reset**

**Layout:**
```
┌─────────────────────────────────┐
│  🔐 Recuperar Senha             │
│                                 │
│  Solicite um token de           │
│  recuperação                    │
│                                 │
│  [Usuário: _______________]     │
│                                 │
│  ℹ️ O token será enviado para   │
│     o webhook Discord (log-ssm) │
│                                 │
│  [Cancelar] [Solicitar Token]   │
└─────────────────────────────────┘
```

### **Modal de Resetar Senha**

**Layout:**
```
┌─────────────────────────────────┐
│  🔐 Resetar Senha               │
│                                 │
│  Digite o token recebido e      │
│  sua nova senha                 │
│                                 │
│  [Token: ___________________]    │
│  [Nova Senha: ______________]   │
│  [Confirmar: ______________]    │
│                                 │
│  [Cancelar] [Resetar Senha]     │
└─────────────────────────────────┘
```

---

## ✅ Validações Client-Side

### **Solicitar Reset:**
- ✅ Username não vazio

### **Resetar Senha:**
- ✅ Token não vazio
- ✅ Nova senha mínimo 8 caracteres
- ✅ Senhas coincidem
- ✅ Todos os campos preenchidos

---

## ⚠️ Tratamento de Erros

### **Erros do Backend:**

1. **Token Inválido/Expirado (400)**
   - Mensagem: "Token inválido ou expirado"
   - Ação: Permitir solicitar novo token

2. **Senha Muito Curta (400)**
   - Mensagem: "A senha deve ter no mínimo 8 caracteres"
   - Ação: Destacar campo e mostrar erro

3. **Rate Limit (implícito)**
   - Backend sempre retorna sucesso genérico
   - Frontend mostra mensagem genérica

4. **Erro de Rede**
   - Mensagem: "Erro ao conectar ao servidor"
   - Ação: Permitir tentar novamente

---

## 🔄 Fluxo Completo

```
1. Usuário clica em "Esqueci minha senha"
   ↓
2. Modal "Solicitar Reset" abre
   ↓
3. Usuário digita username e clica "Solicitar Token"
   ↓
4. Backend envia token via Discord
   ↓
5. Modal mostra mensagem de sucesso
   ↓
6. Usuário fecha modal e abre "Resetar Senha"
   ↓
7. Usuário cola token do Discord
   ↓
8. Usuário digita nova senha e confirma
   ↓
9. Backend valida e atualiza senha
   ↓
10. Modal mostra sucesso
   ↓
11. Redireciona para login após 2 segundos
```

---

## 📝 Checklist de Implementação

### **Fase 1: Serviços**
- [ ] Adicionar interfaces TypeScript
- [ ] Implementar `requestPasswordReset()`
- [ ] Implementar `resetPassword()`
- [ ] Testar chamadas de API

### **Fase 2: Traduções**
- [ ] Adicionar chaves PT-BR
- [ ] Adicionar chaves EN
- [ ] Verificar todas as mensagens

### **Fase 3: UI - Login**
- [ ] Adicionar link "Esqueci minha senha"
- [ ] Criar modal "Solicitar Reset"
- [ ] Criar modal "Resetar Senha"
- [ ] Implementar validações
- [ ] Implementar tratamento de erros
- [ ] Adicionar feedback visual (loading)
- [ ] Testar fluxo completo

### **Fase 4: Testes**
- [ ] Testar solicitação de reset
- [ ] Testar reset com token válido
- [ ] Testar reset com token inválido
- [ ] Testar reset com senha curta
- [ ] Testar validação de senhas não coincidem
- [ ] Testar redirecionamento após sucesso
- [ ] Testar responsividade mobile

---

## 🎯 Decisões de Design

### **1. Modais vs SweetAlert2**

**Decisão:** Modais customizados com Framer Motion

**Motivo:**
- Melhor integração visual com o card de login
- Mais controle sobre layout e animações
- Consistência com o design system

### **2. Localização dos Modais**

**Decisão:** Modais sobrepostos ao card de login

**Motivo:**
- Mantém contexto visual
- Não quebra o fluxo do usuário
- Melhor UX

### **3. Fluxo de Modais**

**Decisão:** Dois modais separados (não wizard)

**Motivo:**
- Mais simples de implementar
- Usuário pode fechar e voltar depois
- Melhor para mobile

---

## 🚀 Próximos Passos

1. ✅ Criar este documento de planejamento
2. ⏳ Implementar serviços de API
3. ⏳ Adicionar traduções
4. ⏳ Implementar UI no Login.tsx
5. ⏳ Testar fluxo completo
6. ⏳ Documentar uso

---

## 📚 Referências

- Documentação do Backend: `docs/API_RECUPERACAO_SENHA.md`
- Endpoints:
  - `POST /api/auth/request-password-reset`
  - `POST /api/auth/reset-password`
- Webhook Discord: `log-ssm`

---

**Última atualização:** 2025-01-XX

