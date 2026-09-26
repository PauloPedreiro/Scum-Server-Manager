# 🔍 Diagnóstico Completo das APIs - SSM 3.0 Frontend

**Data:** 2025-01-27  
**Status:** Problemas identificados e correções propostas

## 🚨 PROBLEMA CRÍTICO IDENTIFICADO

### Problema Principal: Inicialização Assíncrona do `api`

**Localização:** `src/services/server.ts` (linhas 98-110)

**Descrição:**
O `api` exportado é criado com valores padrão (`baseURL: '/api'`) **antes** da inicialização assíncrona completar. Quando os serviços importam e usam `api.get()`, `api.post()`, etc., eles estão usando a instância padrão que **não tem o IP correto do backend**.

**Código Problemático:**
```typescript
// Linha 98-101: Inicialização assíncrona (não esperada)
initializeApi().catch((error) => {
  console.error('[API] Erro ao inicializar API:', error);
});

// Linha 104-110: api exportado com valores padrão (executado ANTES da inicialização)
const api = apiInstance || axios.create({
  baseURL: '/api',  // ❌ Valor padrão incorreto
  timeout: 60000,
  headers: {
    'Content-Type': 'application/json'
  }
});
```

**Impacto:**
- Todos os serviços que importam `api` diretamente usam `baseURL: '/api'` ao invés de `http://192.168.100.3:3000/api`
- Chamadas de API falham porque tentam conectar em `localhost:3000` (relativo) ao invés do IP correto
- Erros em cascata em todas as funcionalidades

## 📊 Análise por Serviço

### ✅ Serviços que Funcionam Corretamente

#### 1. `auth.ts`
- **Status:** ✅ Funciona (usa `getApiBaseURLAsync()` diretamente)
- **Motivo:** Não usa `api` exportado, cria suas próprias chamadas axios com URL correta
- **Chamadas:** Login, logout, change password, CRUD de usuários

### ❌ Serviços com Problema

Todos os serviços abaixo importam `api` diretamente e sofrem do problema de inicialização:

#### 2. `chests.ts`
- **Endpoint:** `GET /api/chests`
- **Problema:** Usa `api.get()` que pode ter `baseURL` incorreto
- **Impacto:** Erro ao carregar baús no mapa

#### 3. `gps.ts`
- **Endpoint:** `GET /api/gps/online`
- **Problema:** Usa `api.get()` que pode ter `baseURL` incorreto
- **Impacto:** Erro ao carregar GPS no mapa

#### 4. `flags.ts`
- **Endpoint:** `GET /api/flags`
- **Problema:** Usa `api.get()` que pode ter `baseURL` incorreto
- **Impacto:** Erro ao carregar bandeiras no mapa

#### 5. `notifications.ts`
- **Endpoints:** 
  - `GET /api/notifications/status`
  - `POST /api/notifications/send`
  - `POST /api/notifications/admin/send`
  - `GET /api/notifications/admin/templates`
  - `POST /api/notifications/clear`
  - `POST /api/notifications/cooldowns/reset`
  - `POST /api/notifications/restart/create`
- **Problema:** Usa `api.get()` e `api.post()` que podem ter `baseURL` incorreto
- **Impacto:** Erro ao carregar status das notificações

#### 6. `server.ts` (funções internas)
- **Endpoints:** Múltiplos (status, start, stop, restart, scheduler, etc.)
- **Problema:** Usa `api` exportado que pode ter `baseURL` incorreto
- **Impacto:** Erros em todas as funcionalidades do servidor

#### 7. `squads.ts`
- **Endpoints:**
  - `GET /api/squads`
  - `GET /api/squads/:id/members`
- **Problema:** Usa `api.get()` que pode ter `baseURL` incorreto
- **Impacto:** Erro ao carregar squads

#### 8. `survival.ts`
- **Endpoints:**
  - `GET /api/survival/player/:identifier`
  - `GET /api/survival/leaderboard`
- **Problema:** Usa `api.get()` que pode ter `baseURL` incorreto
- **Impacto:** Erro ao carregar estatísticas de sobrevivência

#### 9. `rankings.ts`
- **Endpoint:** `GET /api/rankings/list`
- **Problema:** Usa `api.get()` que pode ter `baseURL` incorreto
- **Impacto:** Erro ao carregar rankings

#### 10. `config.ts`
- **Endpoints:** Múltiplos (config, sections, backup, restore)
- **Problema:** Usa `api.get()`, `api.patch()`, `api.put()` que podem ter `baseURL` incorreto
- **Impacto:** Erro ao carregar/configurar configurações

#### 11. `settings.ts`
- **Endpoints:** `GET /api/server/settings`, `PATCH /api/server/settings`
- **Problema:** Usa `api.get()` e `api.patch()` que podem ter `baseURL` incorreto
- **Impacto:** Erro ao carregar/configurar settings do servidor

#### 12. `webhooks.ts`
- **Endpoints:** Múltiplos (CRUD completo de webhooks)
- **Problema:** Usa `api.get()`, `api.post()`, `api.put()`, `api.patch()`, `api.delete()` que podem ter `baseURL` incorreto
- **Impacto:** Erro ao gerenciar webhooks

## 🔧 SOLUÇÃO PROPOSTA

### Opção 1: Proxy Assíncrono (Recomendada)

Criar um proxy que garante que todas as chamadas aguardem a inicialização:

```typescript
// Exportar api como proxy que garante inicialização
const api = new Proxy({} as ReturnType<typeof axios.create>, {
  get: (target, prop) => {
    // Se apiInstance já existe, usar diretamente
    if (apiInstance) {
      return (apiInstance as any)[prop];
    }
    
    // Se for um método HTTP (get, post, put, delete, patch)
    if (typeof prop === 'string' && ['get', 'post', 'put', 'delete', 'patch'].includes(prop)) {
      return async (...args: any[]) => {
        const instance = await initializeApi();
        return (instance as any)[prop](...args);
      };
    }
    
    // Para outras propriedades (interceptors, etc.), aguardar inicialização
    return async (...args: any[]) => {
      const instance = await initializeApi();
      return (instance as any)[prop];
    };
  }
}) as ReturnType<typeof axios.create>;
```

### Opção 2: Função Helper para Todos os Serviços

Criar uma função helper que todos os serviços usam:

```typescript
export async function apiCall<T>(
  method: 'get' | 'post' | 'put' | 'delete' | 'patch',
  url: string,
  config?: any
): Promise<T> {
  const instance = await initializeApi();
  const response = await instance[method](url, config?.data, config);
  return response.data;
}
```

**Desvantagem:** Requer refatorar todos os serviços.

### Opção 3: Aguardar Inicialização no App Root

Aguardar `initializeApi()` no componente raiz antes de renderizar:

```typescript
// App.tsx ou main.tsx
useEffect(() => {
  initializeApi().then(() => {
    // App pronto para usar APIs
  });
}, []);
```

**Desvantagem:** Não resolve o problema de race conditions.

## ✅ RECOMENDAÇÃO

**Implementar Opção 1 (Proxy Assíncrono)** porque:
- ✅ Não requer mudanças nos serviços existentes
- ✅ Garante inicialização antes de qualquer chamada
- ✅ Mantém compatibilidade com código existente
- ✅ Resolve o problema na raiz

## 📝 CHECKLIST DE CORREÇÃO

- [ ] Implementar proxy assíncrono no `server.ts`
- [ ] Testar que `config.json` é carregado corretamente
- [ ] Verificar que todas as chamadas de API usam o IP correto
- [ ] Testar cada serviço individualmente:
  - [ ] `chests.ts` - Carregar baús no mapa
  - [ ] `gps.ts` - Carregar GPS no mapa
  - [ ] `flags.ts` - Carregar bandeiras no mapa
  - [ ] `notifications.ts` - Carregar status das notificações
  - [ ] `server.ts` - Status do servidor e agendador
  - [ ] `squads.ts` - Listar squads
  - [ ] `survival.ts` - Estatísticas de sobrevivência
  - [ ] `rankings.ts` - Rankings
  - [ ] `config.ts` - Configurações
  - [ ] `settings.ts` - Settings do servidor
  - [ ] `webhooks.ts` - Webhooks

## 🐛 OUTROS PROBLEMAS IDENTIFICADOS

### 1. Tratamento de Erro de Timeout

**Localização:** `server.ts` linha 54

**Problema:** Não trata `ERR_CONNECTION_TIMED_OUT` explicitamente

**Correção:** Adicionar verificação:
```typescript
if (e.code === 'ERR_NETWORK' || 
    e.code === 'ERR_CONNECTION_TIMED_OUT' ||
    e.message?.includes('ERR_CONNECTION_REFUSED') ||
    e.message?.includes('ERR_CONNECTION_TIMED_OUT')) {
  // ...
}
```

### 2. Interceptor de Response com Problema de Sintaxe

**Localização:** `server.ts` linha 50-95

**Problema:** Há um problema de fechamento de parênteses/chaves

**Correção:** Verificar estrutura do interceptor

---

**Próximo Passo:** Implementar correção do proxy assíncrono

