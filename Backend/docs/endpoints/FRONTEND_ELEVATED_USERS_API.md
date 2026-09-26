# 🔐 Sistema de Elevated Users - Documentação Frontend

## 📋 Visão Geral

Esta documentação descreve os endpoints da API para gerenciamento completo do sistema de Elevated Users (super usuários) do servidor SCUM. O sistema permite:

- Verificar status do sistema de elevated users
- Listar todos os elevated users cadastrados
- Marcar/desmarcar jogadores como elevated users
- Forçar sincronização de mudanças pendentes
- Monitorar sincronizações automáticas quando o servidor para/restarta

**⚠️ Importante:** As modificações no banco `SCUM.db` só podem ser feitas quando o servidor está parado. O sistema gerencia automaticamente o agendamento e sincronização quando o servidor está rodando.

---

## 🌐 Base URL

```
http://localhost:3000/api
```

**⚠️ Nota:** Em produção, substitua `localhost:3000` pela URL do servidor backend.

---

## 📊 Estruturas TypeScript

### **ElevatedUserStatus**
```typescript
interface ElevatedUserStatus {
  server_status: "running" | "stopped";
  is_running: boolean;
  can_modify: boolean;
  total_elevated_users: number;
  pending_changes: number;
  pending_add: number;
  pending_remove: number;
  scum_db_path: string;
  scum_db_exists: boolean;
  ssm_db_path: string;
  last_sync: string | null; // ISO 8601
}
```

### **ElevatedUser**
```typescript
interface ElevatedUser {
  steam_id: string;
  player_name: string;
  is_synced: boolean;
  created_at: string; // ISO 8601
  synced_at: string | null; // ISO 8601
}
```

### **ElevatedUserListResponse**
```typescript
interface ElevatedUserListResponse {
  success: boolean;
  data: {
    elevated_users: ElevatedUser[];
    total: number;
  };
  timestamp: string; // ISO 8601
}
```

### **MarkElevatedUserRequest**
```typescript
interface MarkElevatedUserRequest {
  elevated_user: 0 | 1; // 1 = marcar, 0 = desmarcar
  reason?: string; // Opcional
}
```

### **MarkElevatedUserResponse**
```typescript
interface MarkElevatedUserResponse {
  success: boolean;
  data: {
    steam_id: string;
    player_name: string;
    elevated_user: 0 | 1;
    action: "added" | "removed" | "scheduled" | "synced" | "no_change";
    synced: boolean;
    message: string;
    backup_created?: string; // Caminho do backup (se sincronizado)
    pending_sync?: boolean; // Se foi agendado
  };
  timestamp: string; // ISO 8601
}
```

### **SyncResponse**
```typescript
interface SyncResponse {
  success: boolean;
  data: {
    changes_count: number;
    added: number;
    removed: number;
    message: string;
    backup_created?: string;
    synced_at?: string; // ISO 8601
  };
  timestamp: string; // ISO 8601
}
```

### **ApiResponse**
```typescript
interface ApiResponse<T> {
  success: boolean;
  data?: T;
  error?: string;
  timestamp?: string; // ISO 8601
}
```

---

## 🔌 Endpoints

### 1. `GET /api/elevated-users/status`

Obtém o status completo do sistema de elevated users.

| Método | URL | Autenticação | Cache Recomendado |
| --- | --- | --- | --- |
| `GET` | `/api/elevated-users/status` | não | 5-10 segundos |

**Uso**
- Carregar na abertura da tela de gerenciamento
- Atualizar via polling quando necessário (ex.: a cada 5-10s)
- Exibir indicadores visuais de status do servidor e mudanças pendentes

**Resposta (`200 OK`)**
```json
{
  "success": true,
  "data": {
    "server_status": "stopped",
    "is_running": false,
    "can_modify": true,
    "total_elevated_users": 2,
    "pending_changes": 0,
    "pending_add": 0,
    "pending_remove": 0,
    "scum_db_path": "C:\\Servers\\Scum\\SCUM\\Saved\\SaveFiles\\SCUM.db",
    "scum_db_exists": true,
    "ssm_db_path": "data/SSM.db",
    "last_sync": "2025-01-15T10:30:00Z"
  },
  "timestamp": "2025-01-15T10:30:00Z"
}
```

**Tratamento de Erros**
| Status | Estrutura | Quando acontece | Ação recomendada |
| --- | --- | --- | --- |
| `500` | `{ "success": false, "error": "mensagem" }` | Sistema não inicializado ou erro interno | Exibir toast de erro e desabilitar funcionalidades |

**Frontend**
- Exibir badge/indicador visual se `is_running === true` (servidor rodando)
- Mostrar contador de `pending_changes` se > 0
- Habilitar/desabilitar botões de ação baseado em `can_modify`
- Exibir última sincronização formatada

---

### 2. `GET /api/elevated-users/list`

Lista todos os elevated users cadastrados no sistema.

| Método | URL | Autenticação | Cache Recomendado |
| --- | --- | --- | --- |
| `GET` | `/api/elevated-users/list` | não | 30 segundos |

**Uso**
- Carregar lista completa de elevated users
- Exibir em tabela ou lista
- Atualizar após marcar/desmarcar um jogador

**Resposta (`200 OK`)**
```json
{
  "success": true,
  "data": {
    "elevated_users": [
      {
        "steam_id": "76561198040636105",
        "player_name": "Pedreiro",
        "is_synced": true,
        "created_at": "2025-01-15T10:00:00Z",
        "synced_at": "2025-01-15T10:05:00Z"
      },
      {
        "steam_id": "76561198042887008",
        "player_name": "Mantones",
        "is_synced": true,
        "created_at": "2025-01-15T09:00:00Z",
        "synced_at": "2025-01-15T09:05:00Z"
      }
    ],
    "total": 2
  },
  "timestamp": "2025-01-15T10:30:00Z"
}
```

**Tratamento de Erros**
| Status | Estrutura | Quando acontece | Ação recomendada |
| --- | --- | --- | --- |
| `500` | `{ "success": false, "error": "mensagem" }` | Erro ao acessar banco de dados | Exibir toast de erro e sugerir recarregar |

**Frontend**
- Renderizar lista/tabela com informações dos elevated users
- Destacar usuários com `is_synced === false` (pendentes de sincronização)
- Exibir timestamps formatados (ex.: "15/01/2025 10:00")

---

### 3. `POST /api/players/<steam_id>/elevated-user`

Marca ou desmarca um jogador como elevated user.

| Método | URL | Autenticação | Cache Recomendado |
| --- | --- | --- | --- |
| `POST` | `/api/players/{steam_id}/elevated-user` | não | n/a |

**Parâmetros de URL**
- `steam_id` (string, obrigatório): Steam ID do jogador (17 dígitos)

**Body**
```json
{
  "elevated_user": 1,
  "reason": "Promovido a administrador"
}
```

**Campos do Body**
- `elevated_user` (integer, opcional): `1` para marcar como elevated, `0` para desmarcar. Padrão: `1`
- `reason` (string, opcional): Motivo da alteração

**Resposta (`200 OK`) - Servidor Parado (Sincronizado)**
```json
{
  "success": true,
  "data": {
    "steam_id": "76561198040636105",
    "player_name": "Pedreiro",
    "elevated_user": 1,
    "action": "added",
    "synced": true,
    "message": "Elevated user adicionado e sincronizado com sucesso",
    "backup_created": "C:\\Servers\\Scum\\SCUM\\Saved\\SaveFiles\\SCUM.db.backup.20250115103000"
  },
  "timestamp": "2025-01-15T10:30:00Z"
}
```

**Resposta (`200 OK`) - Servidor Rodando (Agendado)**
```json
{
  "success": true,
  "data": {
    "steam_id": "76561198040636105",
    "player_name": "Pedreiro",
    "elevated_user": 1,
    "action": "scheduled",
    "synced": false,
    "message": "Elevated user agendado. Será sincronizado quando o servidor parar",
    "pending_sync": true
  },
  "timestamp": "2025-01-15T10:30:00Z"
}
```

**Tratamento de Erros**
| Status | Estrutura | Quando acontece | Ação recomendada |
| --- | --- | --- | --- |
| `400` | `{ "success": false, "error": "mensagem" }` | Steam ID inválido, jogador não encontrado, ou erro de validação | Exibir toast com mensagem de erro |
| `500` | `{ "success": false, "error": "mensagem" }` | Erro interno do servidor | Exibir toast de erro genérico |

**Frontend**
- Validar formato do Steam ID (17 dígitos) antes de enviar
- Exibir feedback baseado em `data.action`:
  - `"scheduled"`: Mostrar aviso que será sincronizado quando servidor parar
  - `"added"` ou `"removed"`: Confirmar sucesso imediato
- Atualizar lista de elevated users após sucesso
- Atualizar status do sistema após sucesso

---

### 4. `POST /api/elevated-users/sync`

Força a sincronização imediata de todas as mudanças pendentes.

| Método | URL | Autenticação | Cache Recomendado |
| --- | --- | --- | --- |
| `POST` | `/api/elevated-users/sync` | não | n/a |

**Body** (opcional)
```json
{}
```

**Resposta (`200 OK`) - Com Mudanças**
```json
{
  "success": true,
  "data": {
    "changes_count": 2,
    "added": 1,
    "removed": 1,
    "backup_created": "C:\\Servers\\Scum\\SCUM\\Saved\\SaveFiles\\SCUM.db.backup.20250115103000",
    "message": "Sincronização concluída: 1 adicionado, 1 removido",
    "synced_at": "2025-01-15T10:30:00Z"
  },
  "timestamp": "2025-01-15T10:30:00Z"
}
```

**Resposta (`200 OK`) - Sem Mudanças**
```json
{
  "success": true,
  "data": {
    "changes_count": 0,
    "added": 0,
    "removed": 0,
    "message": "Nenhuma mudança pendente para sincronizar"
  },
  "timestamp": "2025-01-15T10:30:00Z"
}
```

**Tratamento de Erros**
| Status | Estrutura | Quando acontece | Ação recomendada |
| --- | --- | --- | --- |
| `400` | `{ "success": false, "error": "mensagem" }` | Servidor está rodando (não é possível sincronizar) | Exibir toast informando que servidor precisa estar parado |
| `500` | `{ "success": false, "error": "mensagem" }` | Erro interno do servidor | Exibir toast de erro genérico |

**Frontend**
- Verificar status do servidor antes de habilitar botão de sincronização
- Desabilitar botão se `server_status === "running"`
- Exibir loading durante sincronização
- Mostrar resumo de mudanças após sucesso
- Atualizar lista e status após sincronização

---

## 💡 Recomendações para o Frontend

### **1. Fluxo de Uso Recomendado**

1. **Ao abrir a tela:**
   - Carregar status (`GET /api/elevated-users/status`)
   - Carregar lista (`GET /api/elevated-users/list`)
   - Exibir indicadores visuais de estado

2. **Ao marcar/desmarcar elevated user:**
   - Validar Steam ID
   - Enviar requisição (`POST /api/players/{steam_id}/elevated-user`)
   - Verificar `data.action`:
     - Se `"scheduled"`: Mostrar aviso de agendamento
     - Se `"added"` ou `"removed"`: Confirmar sucesso
   - Atualizar lista e status

3. **Sincronização automática:**
   - O sistema sincroniza automaticamente quando o servidor para/restarta
   - Não é necessário chamar `/sync` manualmente na maioria dos casos
   - Use `/sync` apenas para forçar sincronização quando necessário

### **2. Indicadores Visuais**

- **Servidor rodando** (`is_running === true`):
  - Badge vermelho/laranja: "Servidor Online"
  - Desabilitar botão de sincronização manual
  - Mostrar aviso: "Mudanças serão sincronizadas quando o servidor parar"

- **Mudanças pendentes** (`pending_changes > 0`):
  - Badge amarelo: "X mudanças pendentes"
  - Exibir lista de mudanças pendentes (se disponível)

- **Elevated users não sincronizados** (`is_synced === false`):
  - Ícone de relógio ou badge "Pendente"
  - Destaque visual na lista

### **3. Validações**

- **Steam ID**: Validar formato (17 dígitos, começa com `7656119`)
- **Servidor status**: Verificar antes de permitir sincronização manual
- **Jogador existe**: Verificar se Steam ID existe na lista de players antes de marcar

### **4. Feedback ao Usuário**

- **Agendamento**: "Elevated user agendado. Será sincronizado quando o servidor parar."
- **Sincronização imediata**: "Elevated user sincronizado com sucesso."
- **Erro**: Exibir mensagem de erro específica retornada pela API
- **Servidor rodando**: "Servidor está rodando. Mudanças serão aplicadas quando o servidor parar."

---

## 📝 Exemplo de Integração (React/TypeScript + React Query)

```typescript
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';

// Tipos
interface ElevatedUserStatus {
  server_status: "running" | "stopped";
  is_running: boolean;
  can_modify: boolean;
  total_elevated_users: number;
  pending_changes: number;
  pending_add: number;
  pending_remove: number;
  scum_db_path: string;
  scum_db_exists: boolean;
  ssm_db_path: string;
  last_sync: string | null;
}

interface ElevatedUser {
  steam_id: string;
  player_name: string;
  is_synced: boolean;
  created_at: string;
  synced_at: string | null;
}

interface MarkElevatedUserRequest {
  elevated_user: 0 | 1;
  reason?: string;
}

// Hooks
export function useElevatedUsersStatus() {
  return useQuery({
    queryKey: ['elevated-users', 'status'],
    queryFn: async () => {
      const res = await fetch('/api/elevated-users/status');
      const json = await res.json();
      if (!json.success) throw new Error(json.error ?? 'Erro ao carregar status');
      return json.data as ElevatedUserStatus;
    },
    staleTime: 5_000, // 5 segundos
    refetchInterval: 10_000, // Atualizar a cada 10 segundos
  });
}

export function useElevatedUsersList() {
  return useQuery({
    queryKey: ['elevated-users', 'list'],
    queryFn: async () => {
      const res = await fetch('/api/elevated-users/list');
      const json = await res.json();
      if (!json.success) throw new Error(json.error ?? 'Erro ao carregar lista');
      return json.data.elevated_users as ElevatedUser[];
    },
    staleTime: 30_000, // 30 segundos
  });
}

export function useMarkElevatedUser() {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: async ({ steamId, elevated, reason }: { 
      steamId: string; 
      elevated: 0 | 1; 
      reason?: string 
    }) => {
      const res = await fetch(`/api/players/${steamId}/elevated-user`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ 
          elevated_user: elevated,
          reason 
        }),
      });
      const json = await res.json();
      if (!json.success) throw new Error(json.error ?? 'Erro ao marcar elevated user');
      return json.data;
    },
    onSuccess: () => {
      // Invalidar queries para atualizar dados
      queryClient.invalidateQueries({ queryKey: ['elevated-users'] });
      queryClient.invalidateQueries({ queryKey: ['players'] });
    },
  });
}

export function useSyncElevatedUsers() {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: async () => {
      const res = await fetch('/api/elevated-users/sync', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({}),
      });
      const json = await res.json();
      if (!json.success) throw new Error(json.error ?? 'Erro ao sincronizar');
      return json.data;
    },
    onSuccess: () => {
      // Invalidar queries para atualizar dados
      queryClient.invalidateQueries({ queryKey: ['elevated-users'] });
    },
  });
}

// Componente de exemplo
export function ElevatedUsersManager() {
  const { data: status, isLoading: statusLoading } = useElevatedUsersStatus();
  const { data: elevatedUsers, isLoading: listLoading } = useElevatedUsersList();
  const markMutation = useMarkElevatedUser();
  const syncMutation = useSyncElevatedUsers();

  if (statusLoading || listLoading) {
    return <div>Carregando...</div>;
  }

  const handleMark = async (steamId: string, elevated: 0 | 1) => {
    try {
      const result = await markMutation.mutateAsync({ 
        steamId, 
        elevated,
        reason: elevated ? 'Promovido a administrador' : 'Removido de administrador'
      });
      
      if (result.action === 'scheduled') {
        alert('Elevated user agendado. Será sincronizado quando o servidor parar.');
      } else {
        alert('Elevated user sincronizado com sucesso!');
      }
    } catch (error) {
      alert(`Erro: ${error.message}`);
    }
  };

  const handleSync = async () => {
    try {
      const result = await syncMutation.mutateAsync();
      alert(`Sincronização concluída: ${result.added} adicionado(s), ${result.removed} removido(s)`);
    } catch (error) {
      alert(`Erro: ${error.message}`);
    }
  };

  return (
    <div>
      <div>
        <h2>Status do Sistema</h2>
        <p>Servidor: {status?.is_running ? '🟢 Online' : '🔴 Offline'}</p>
        <p>Mudanças pendentes: {status?.pending_changes || 0}</p>
        <button 
          onClick={handleSync}
          disabled={status?.is_running || status?.pending_changes === 0}
        >
          Sincronizar Agora
        </button>
      </div>

      <div>
        <h2>Elevated Users ({status?.total_elevated_users || 0})</h2>
        <table>
          <thead>
            <tr>
              <th>Jogador</th>
              <th>Steam ID</th>
              <th>Status</th>
              <th>Ações</th>
            </tr>
          </thead>
          <tbody>
            {elevatedUsers?.map((user) => (
              <tr key={user.steam_id}>
                <td>{user.player_name}</td>
                <td>{user.steam_id}</td>
                <td>
                  {user.is_synced ? '✅ Sincronizado' : '⏳ Pendente'}
                </td>
                <td>
                  <button onClick={() => handleMark(user.steam_id, 0)}>
                    Remover
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
```

---

## ✅ Checklist para Entrega

- [ ] Endpoint de status configurado no cliente HTTP
- [ ] Endpoint de lista configurado no cliente HTTP
- [ ] Endpoint de marcar/desmarcar configurado no cliente HTTP
- [ ] Endpoint de sincronização configurado no cliente HTTP
- [ ] Hooks/Queries criados para cada endpoint
- [ ] Validação de Steam ID implementada
- [ ] Indicadores visuais de status do servidor
- [ ] Indicadores visuais de mudanças pendentes
- [ ] Feedback ao usuário para ações agendadas vs sincronizadas
- [ ] Tratamento de erros implementado
- [ ] Atualização automática de lista após ações
- [ ] Desabilitar botões quando servidor está rodando (se aplicável)
- [ ] Formatação de timestamps
- [ ] Testes de integração realizados

---

## 🔗 Endpoints Relacionados

- `GET /api/server/status` - Verificar status do servidor
- `GET /api/players` - Listar jogadores (para validar Steam ID antes de marcar)

---

## 📚 Referências

- Documentação técnica completa: `docs/ELEVATED_USERS_SYSTEM_PROPOSAL.md`
- Postman Collection: `docs/endpoints/postman-collection.json` (seção "🔐 Sistema de Elevated Users")

