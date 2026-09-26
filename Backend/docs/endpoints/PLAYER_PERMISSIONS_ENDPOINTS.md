# 🔐 Documentação - Sistema de Permissões de Jogadores

## 📋 Visão Geral

Este sistema permite gerenciar diferentes tipos de permissões para jogadores do servidor SCUM através da tabela `player_permissions`. As permissões são sincronizadas automaticamente com os arquivos de configuração `.ini` do servidor.

### **Diferença entre Sistemas de Permissão**

⚠️ **Importante:** Este sistema é diferente da coluna `permissao` na tabela `players`:

- **`player_permissions` (esta documentação):** Controla permissões avançadas (admin, banned, exclusive, etc.)
- **`permissao` (tabela `players`):** Controla apenas o comando `/tm` (documentado separadamente)

---

## 🎯 Tipos de Permissão Disponíveis

| Tipo | Nome | Arquivo INI | Descrição |
|------|------|-------------|-----------|
| `admin` | Administrador | `AdminUsers.ini` | Permissões de administrador do servidor |
| `banned` | Banido | `BannedUsers.ini` | Jogador banido do servidor |
| `exclusive` | Exclusivo | `ExclusiveUsers.ini` | Acesso exclusivo ao servidor |
| `server_admin` | Admin do Servidor | `ServerSettingsAdminUsers.ini` | Administrador das configurações |
| `silenced` | Silenciado | `SilencedUsers.ini` | Jogador silenciado no chat |
| `whitelisted` | Whitelist | `WhitelistedUsers.ini` | Jogador na lista branca |
| `raid_webhook_manage` | Gerenciar Webhook de Raid | *(DB-only)* | Permite usar o comando `/sd` para cadastrar/remover webhook pessoal de alertas de raid |

### **Permissões DB-only (sem INI)**

Algumas permissões existem apenas no banco e **não possuem arquivo INI**.

- Para essas permissões, os endpoints de ativar/desativar continuam funcionando normalmente.
- O retorno da API virá com:
  - `ini_file_updated: null`
  - `ini_file_path: null`

---

## 📡 **Endpoints Disponíveis**

### **1. Ativar Permissão**

**POST** `/api/players/{steam_id}/permissions/{permission_type}/activate`

Ativa uma permissão específica para um jogador.

#### **URL Base**
```
http://192.168.100.3:3000/api/players/{steam_id}/permissions/{permission_type}/activate
```

**Exemplo:**
```
http://192.168.100.3:3000/api/players/76561198040636105/permissions/admin/activate
```

#### **Parâmetros**

| Parâmetro | Tipo | Obrigatório | Local | Descrição | Exemplo |
|-----------|------|-------------|-------|-----------|---------|
| `steam_id` | string | ✅ Sim | Path | Steam ID do jogador | `76561198040636105` |
| `permission_type` | string | ✅ Sim | Path | Tipo da permissão | `admin`, `banned`, `exclusive`, etc. |

#### **Body da Requisição (Opcional)**

```json
{
  "granted_by": "admin",
  "notes": "Permissão de administrador concedida"
}
```

**Campos:**
- `granted_by` (string, opcional): Quem concedeu a permissão (padrão: `"system"`)
- `notes` (string, opcional): Observações sobre a permissão

#### **Resposta de Sucesso (200 OK)**

```json
{
  "success": true,
  "message": "Permissão 'admin' ativada com sucesso para o jogador 76561198040636105",
  "data": {
    "permission_id": 1,
    "steam_id": "76561198040636105",
    "permission_type": "admin",
    "is_active": true,
    "granted_by": "admin",
    "granted_at": "2025-01-15T10:30:00Z",
    "notes": "Permissão de administrador concedida",
    "ini_file_updated": true,
    "ini_file_path": "C:\\Servers\\scum\\SCUM\\Saved\\Config\\WindowsServer\\AdminUsers.ini"
  }
}
```

#### **Respostas de Erro**

#### **Comportamento Idempotente (recomendado para toggles)**

Se a permissão já estiver ativa, o endpoint retorna **200 OK** com `success: true` (no-op) e o estado final em `data.is_active`.

Exemplo de resposta (200 OK - no-op):
```json
{
  "success": true,
  "message": "Permissão 'admin' já está ativa para este jogador",
  "data": {
    "steam_id": "76561198040636105",
    "permission_type": "admin",
    "is_active": true,
    "ini_file_updated": null,
    "ini_file_path": "C:\\Servers\\scum\\SCUM\\Saved\\Config\\WindowsServer\\AdminUsers.ini"
  }
}
```

**404 Not Found** - Jogador não encontrado:
```json
{
  "success": false,
  "error": "Jogador não encontrado"
}
```

**500 Internal Server Error**:
```json
{
  "success": false,
  "error": "Erro específico"
}
```

---

### **2. Desativar Permissão**

**POST** `/api/players/{steam_id}/permissions/{permission_type}/deactivate`

Desativa uma permissão específica de um jogador.

#### **URL Base**
```
http://192.168.100.3:3000/api/players/{steam_id}/permissions/{permission_type}/deactivate
```

**Exemplo:**
```
http://192.168.100.3:3000/api/players/76561198040636105/permissions/admin/deactivate
```

#### **Parâmetros**

| Parâmetro | Tipo | Obrigatório | Local | Descrição | Exemplo |
|-----------|------|-------------|-------|-----------|---------|
| `steam_id` | string | ✅ Sim | Path | Steam ID do jogador | `76561198040636105` |
| `permission_type` | string | ✅ Sim | Path | Tipo da permissão | `admin`, `banned`, etc. |

#### **Body da Requisição (Opcional)**

```json
{
  "revoked_by": "admin",
  "notes": "Permissão revogada por violação das regras"
}
```

**Campos:**
- `revoked_by` (string, opcional): Quem revogou a permissão (padrão: `"system"`)
- `notes` (string, opcional): Observações sobre a revogação

#### **Resposta de Sucesso (200 OK)**

```json
{
  "success": true,
  "message": "Permissão 'admin' desativada com sucesso para o jogador 76561198040636105",
  "data": {
    "permission_id": 1,
    "steam_id": "76561198040636105",
    "permission_type": "admin",
    "is_active": false,
    "revoked_by": "admin",
    "revoked_at": "2025-01-15T10:35:00Z",
    "notes": "Permissão revogada por violação das regras",
    "ini_file_updated": true,
    "ini_file_path": "C:\\Servers\\scum\\SCUM\\Saved\\Config\\WindowsServer\\AdminUsers.ini"
  }
}
```

#### **Respostas de Erro**

#### **Comportamento Idempotente (recomendado para toggles)**

Se a permissão já estiver inativa, o endpoint retorna **200 OK** com `success: true` (no-op) e o estado final em `data.is_active`.

Exemplo de resposta (200 OK - no-op):
```json
{
  "success": true,
  "message": "Permissão 'admin' já está inativa para este jogador",
  "data": {
    "steam_id": "76561198040636105",
    "permission_type": "admin",
    "is_active": false,
    "ini_file_updated": null,
    "ini_file_path": "C:\\Servers\\scum\\SCUM\\Saved\\Config\\WindowsServer\\AdminUsers.ini"
  }
}
```

**404 Not Found**:
```json
{
  "success": false,
  "error": "Jogador não encontrado"
}
```

---

### **3. Listar Permissões do Jogador**

**GET** `/api/players/{steam_id}/permissions`

Lista todas as permissões de um jogador específico.

#### **URL Base**
```
http://192.168.100.3:3000/api/players/{steam_id}/permissions
```

**Exemplo:**
```
http://192.168.100.3:3000/api/players/76561198040636105/permissions?include_inactive=true
```

#### **Parâmetros**

| Parâmetro | Tipo | Obrigatório | Local | Descrição | Exemplo |
|-----------|------|-------------|-------|-----------|---------|
| `steam_id` | string | ✅ Sim | Path | Steam ID do jogador | `76561198040636105` |
| `include_inactive` | boolean | ❌ Não | Query | Incluir permissões inativas (padrão: `false`) | `true`, `false` |

#### **Resposta de Sucesso (200 OK)**

```json
{
  "success": true,
  "data": {
    "steam_id": "76561198040636105",
    "player_name": "Pedreiro",
    "permissions": [
      {
        "id": 1,
        "permission_type": "admin",
        "is_active": true,
        "granted_by": "admin",
        "granted_at": "2025-01-15T10:30:00Z",
        "revoked_by": null,
        "revoked_at": null,
        "notes": "Permissão de administrador concedida"
      },
      {
        "id": 2,
        "permission_type": "server_admin",
        "is_active": true,
        "granted_by": "admin",
        "granted_at": "2025-01-15T10:32:00Z",
        "revoked_by": null,
        "revoked_at": null,
        "notes": "Admin de configurações"
      }
    ],
    "total_permissions": 2,
    "active_permissions": 2,
    "inactive_permissions": 0
  }
}
```

#### **Respostas de Erro**

**404 Not Found**:
```json
{
  "success": false,
  "error": "Jogador não encontrado"
}
```

---

### **4. Estatísticas de Permissões**

**GET** `/api/permissions/stats`

Obtém estatísticas gerais do sistema de permissões.

#### **URL Base**
```
http://192.168.100.3:3000/api/permissions/stats
```

#### **Resposta de Sucesso (200 OK)**

```json
{
  "success": true,
  "data": {
    "total_permissions": 15,
    "active_permissions": 12,
    "inactive_permissions": 3,
    "permissions_by_type": {
      "admin": 3,
      "banned": 2,
      "exclusive": 4,
      "server_admin": 3,
      "silenced": 1,
      "whitelisted": 2
    },
    "permissions_by_status": {
      "active": 12,
      "inactive": 3
    },
    "recent_activity": {
      "last_24h": 5,
      "last_7d": 12,
      "last_30d": 25
    }
  }
}
```

---

### **5. Sincronizar Arquivos INI**

**POST** `/api/permissions/sync-ini-files`

Sincroniza todos os arquivos `.ini` do servidor SCUM com as permissões do banco de dados.

#### **URL Base**
```
http://192.168.100.3:3000/api/permissions/sync-ini-files
```

#### **Resposta de Sucesso (200 OK)**

```json
{
  "success": true,
  "message": "Sincronização de arquivos INI concluída com sucesso",
  "data": {
    "files_updated": 6,
    "files_created": 0,
    "files_skipped": 0,
    "total_permissions_synced": 12,
    "files_processed": [
      "AdminUsers.ini",
      "BannedUsers.ini",
      "ExclusiveUsers.ini",
      "ServerSettingsAdminUsers.ini",
      "SilencedUsers.ini",
      "WhitelistedUsers.ini"
    ]
  }
}
```

---

### **6. Listar Tipos de Permissão**

**GET** `/api/permissions/types`

Lista todos os tipos de permissão disponíveis e seus mapeamentos de arquivos.

#### **URL Base**
```
http://192.168.100.3:3000/api/permissions/types
```

#### **Resposta de Sucesso (200 OK)**

```json
{
  "success": true,
  "data": {
    "permission_types": [
      "admin",
      "banned",
      "exclusive",
      "server_admin",
      "silenced",
      "whitelisted",
      "raid_webhook_manage"
    ],
    "file_mapping": {
      "admin": "AdminUsers.ini",
      "banned": "BannedUsers.ini",
      "exclusive": "ExclusiveUsers.ini",
      "server_admin": "ServerSettingsAdminUsers.ini",
      "silenced": "SilencedUsers.ini",
      "whitelisted": "WhitelistedUsers.ini"
    }
  }
}
```

---

### **7. Listar Jogadores por Tipo de Permissão**

**GET** `/api/permissions/by-type/{permission_type}`

Lista todos os jogadores com um tipo específico de permissão ativa.

#### **URL Base**
```
http://192.168.100.3:3000/api/permissions/by-type/{permission_type}
```

**Exemplo:**
```
http://192.168.100.3:3000/api/permissions/by-type/admin
```

#### **Parâmetros**

| Parâmetro | Tipo | Obrigatório | Local | Descrição | Exemplo |
|-----------|------|-------------|-------|-----------|---------|
| `permission_type` | string | ✅ Sim | Path | Tipo da permissão | `admin`, `banned`, etc. |

#### **Resposta de Sucesso (200 OK)**

```json
{
  "success": true,
  "data": {
    "permission_type": "admin",
    "players": [
      {
        "steam_id": "76561198040636105",
        "player_name": "Pedreiro",
        "player_id": 230,
        "permission_id": 1,
        "is_active": true,
        "granted_by": "admin",
        "granted_at": "2025-01-15T10:30:00Z",
        "notes": "Permissão de administrador concedida"
      }
    ],
    "total_players": 1,
    "active_players": 1
  }
}
```

---

## 💻 **Exemplos de Implementação**

### **TypeScript/React - Funções Base**

```typescript
import axios, { AxiosError } from 'axios';

const BASE_URL = 'http://192.168.100.3:3000';

// Interfaces
interface Permission {
  id: number;
  permission_type: string;
  is_active: boolean;
  granted_by: string | null;
  granted_at: string | null;
  revoked_by: string | null;
  revoked_at: string | null;
  notes: string | null;
}

interface PlayerPermissionsResponse {
  success: boolean;
  data: {
    steam_id: string;
    player_name: string;
    permissions: Permission[];
    total_permissions: number;
    active_permissions: number;
    inactive_permissions: number;
  };
}

interface ActivatePermissionResponse {
  success: boolean;
  message: string;
  data: {
    permission_id: number;
    steam_id: string;
    permission_type: string;
    is_active: boolean;
    granted_by: string;
    granted_at: string;
    notes: string | null;
    ini_file_updated: boolean;
    ini_file_path: string;
  };
}

interface ErrorResponse {
  success: false;
  error: string;
}

// 1. Ativar Permissão
export const activatePermission = async (
  steamId: string,
  permissionType: string,
  grantedBy?: string,
  notes?: string
): Promise<ActivatePermissionResponse['data']> => {
  try {
    const response = await axios.post<ActivatePermissionResponse>(
      `${BASE_URL}/api/players/${steamId}/permissions/${permissionType}/activate`,
      {
        granted_by: grantedBy || 'system',
        notes: notes || null
      }
    );
    
    if (!response.data.success) {
      throw new Error(response.data.message || 'Erro ao ativar permissão');
    }
    
    return response.data.data;
  } catch (error) {
    if (axios.isAxiosError(error)) {
      const errorData = error.response?.data as ErrorResponse;
      throw new Error(errorData?.error || error.message);
    }
    throw error;
  }
};

// 2. Desativar Permissão
export const deactivatePermission = async (
  steamId: string,
  permissionType: string,
  revokedBy?: string,
  notes?: string
): Promise<ActivatePermissionResponse['data']> => {
  try {
    const response = await axios.post<ActivatePermissionResponse>(
      `${BASE_URL}/api/players/${steamId}/permissions/${permissionType}/deactivate`,
      {
        revoked_by: revokedBy || 'system',
        notes: notes || null
      }
    );
    
    if (!response.data.success) {
      throw new Error(response.data.message || 'Erro ao desativar permissão');
    }
    
    return response.data.data;
  } catch (error) {
    if (axios.isAxiosError(error)) {
      const errorData = error.response?.data as ErrorResponse;
      throw new Error(errorData?.error || error.message);
    }
    throw error;
  }
};

// 3. Listar Permissões do Jogador
export const getPlayerPermissions = async (
  steamId: string,
  includeInactive: boolean = false
): Promise<PlayerPermissionsResponse['data']> => {
  try {
    const response = await axios.get<PlayerPermissionsResponse>(
      `${BASE_URL}/api/players/${steamId}/permissions`,
      {
        params: {
          include_inactive: includeInactive
        }
      }
    );
    
    if (!response.data.success) {
      throw new Error('Erro ao obter permissões');
    }
    
    return response.data.data;
  } catch (error) {
    if (axios.isAxiosError(error)) {
      const errorData = error.response?.data as ErrorResponse;
      throw new Error(errorData?.error || error.message);
    }
    throw error;
  }
};

// 4. Obter Estatísticas
export const getPermissionStats = async () => {
  try {
    const response = await axios.get(`${BASE_URL}/api/permissions/stats`);
    return response.data.data;
  } catch (error) {
    if (axios.isAxiosError(error)) {
      const errorData = error.response?.data as ErrorResponse;
      throw new Error(errorData?.error || error.message);
    }
    throw error;
  }
};

// 5. Sincronizar Arquivos INI
export const syncIniFiles = async () => {
  try {
    const response = await axios.post(`${BASE_URL}/api/permissions/sync-ini-files`);
    return response.data.data;
  } catch (error) {
    if (axios.isAxiosError(error)) {
      const errorData = error.response?.data as ErrorResponse;
      throw new Error(errorData?.error || error.message);
    }
    throw error;
  }
};

// 6. Listar Tipos de Permissão
export const getPermissionTypes = async () => {
  try {
    const response = await axios.get(`${BASE_URL}/api/permissions/types`);
    return response.data.data;
  } catch (error) {
    if (axios.isAxiosError(error)) {
      const errorData = error.response?.data as ErrorResponse;
      throw new Error(errorData?.error || error.message);
    }
    throw error;
  }
};

// 7. Listar Jogadores por Tipo
export const getPlayersByPermissionType = async (permissionType: string) => {
  try {
    const response = await axios.get(
      `${BASE_URL}/api/permissions/by-type/${permissionType}`
    );
    return response.data.data;
  } catch (error) {
    if (axios.isAxiosError(error)) {
      const errorData = error.response?.data as ErrorResponse;
      throw new Error(errorData?.error || error.message);
    }
    throw error;
  }
};
```

---

### **React Hook Customizado**

```typescript
import { useState, useCallback } from 'react';
import {
  activatePermission,
  deactivatePermission,
  getPlayerPermissions
} from './api/permissions';

interface UsePlayerPermissionsOptions {
  steamId: string;
  includeInactive?: boolean;
}

export const usePlayerPermissions = ({
  steamId,
  includeInactive = false
}: UsePlayerPermissionsOptions) => {
  const [permissions, setPermissions] = useState<Permission[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [playerName, setPlayerName] = useState<string>('');

  const loadPermissions = useCallback(async () => {
    setLoading(true);
    setError(null);
    
    try {
      const data = await getPlayerPermissions(steamId, includeInactive);
      setPermissions(data.permissions);
      setPlayerName(data.player_name);
    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }, [steamId, includeInactive]);

  const activate = useCallback(async (
    permissionType: string,
    grantedBy?: string,
    notes?: string
  ) => {
    setLoading(true);
    setError(null);
    
    try {
      await activatePermission(steamId, permissionType, grantedBy, notes);
      await loadPermissions(); // Recarregar permissões
    } catch (err: any) {
      setError(err.message);
      throw err;
    } finally {
      setLoading(false);
    }
  }, [steamId, loadPermissions]);

  const deactivate = useCallback(async (
    permissionType: string,
    revokedBy?: string,
    notes?: string
  ) => {
    setLoading(true);
    setError(null);
    
    try {
      await deactivatePermission(steamId, permissionType, revokedBy, notes);
      await loadPermissions(); // Recarregar permissões
    } catch (err: any) {
      setError(err.message);
      throw err;
    } finally {
      setLoading(false);
    }
  }, [steamId, loadPermissions]);

  return {
    permissions,
    playerName,
    loading,
    error,
    loadPermissions,
    activate,
    deactivate
  };
};
```

---

### **Componente React Completo**

```typescript
import React, { useEffect, useState } from 'react';
import {
  usePlayerPermissions,
  getPermissionTypes,
  Permission
} from './hooks/usePlayerPermissions';

const PERMISSION_NAMES: Record<string, string> = {
  admin: 'Administrador',
  banned: 'Banido',
  exclusive: 'Exclusivo',
  server_admin: 'Admin do Servidor',
  silenced: 'Silenciado',
  whitelisted: 'Whitelist'
};

const PlayerPermissionsPanel: React.FC<{ steamId: string }> = ({ steamId }) => {
  const {
    permissions,
    playerName,
    loading,
    error,
    loadPermissions,
    activate,
    deactivate
  } = usePlayerPermissions({ steamId, includeInactive: true });

  const [availableTypes, setAvailableTypes] = useState<string[]>([]);
  const [selectedType, setSelectedType] = useState<string>('');
  const [notes, setNotes] = useState<string>('');
  const [actionLoading, setActionLoading] = useState(false);

  useEffect(() => {
    loadPermissions();
    loadAvailableTypes();
  }, [steamId]);

  const loadAvailableTypes = async () => {
    try {
      const data = await getPermissionTypes();
      setAvailableTypes(data.permission_types);
    } catch (err) {
      console.error('Erro ao carregar tipos de permissão:', err);
    }
  };

  const handleActivate = async () => {
    if (!selectedType) return;
    
    setActionLoading(true);
    try {
      await activate(selectedType, 'admin', notes || undefined);
      setSelectedType('');
      setNotes('');
      alert('Permissão ativada com sucesso!');
    } catch (err: any) {
      alert(`Erro: ${err.message}`);
    } finally {
      setActionLoading(false);
    }
  };

  const handleDeactivate = async (permissionType: string) => {
    if (!window.confirm(`Deseja realmente desativar a permissão ${PERMISSION_NAMES[permissionType]}?`)) {
      return;
    }
    
    setActionLoading(true);
    try {
      await deactivate(permissionType, 'admin', 'Desativado via painel');
      alert('Permissão desativada com sucesso!');
    } catch (err: any) {
      alert(`Erro: ${err.message}`);
    } finally {
      setActionLoading(false);
    }
  };

  const isPermissionActive = (permissionType: string): boolean => {
    return permissions.some(
      p => p.permission_type === permissionType && p.is_active
    );
  };

  if (loading && permissions.length === 0) {
    return <div>Carregando permissões...</div>;
  }

  return (
    <div style={{ padding: '20px', maxWidth: '800px' }}>
      <h2>Permissões - {playerName}</h2>
      <p>Steam ID: {steamId}</p>

      {error && (
        <div style={{ color: 'red', marginBottom: '16px' }}>
          Erro: {error}
        </div>
      )}

      {/* Lista de Permissões Ativas */}
      <div style={{ marginBottom: '24px' }}>
        <h3>Permissões Ativas</h3>
        {permissions.filter(p => p.is_active).length === 0 ? (
          <p>Nenhuma permissão ativa</p>
        ) : (
          <ul>
            {permissions
              .filter(p => p.is_active)
              .map(permission => (
                <li key={permission.id} style={{ marginBottom: '8px' }}>
                  <strong>{PERMISSION_NAMES[permission.permission_type]}</strong>
                  {permission.notes && <span> - {permission.notes}</span>}
                  <button
                    onClick={() => handleDeactivate(permission.permission_type)}
                    disabled={actionLoading}
                    style={{ marginLeft: '8px', color: 'red' }}
                  >
                    Desativar
                  </button>
                </li>
              ))}
          </ul>
        )}
      </div>

      {/* Adicionar Nova Permissão */}
      <div style={{ borderTop: '1px solid #ddd', paddingTop: '20px' }}>
        <h3>Adicionar Permissão</h3>
        <div style={{ marginBottom: '12px' }}>
          <label>
            Tipo de Permissão:
            <select
              value={selectedType}
              onChange={(e) => setSelectedType(e.target.value)}
              style={{ marginLeft: '8px' }}
            >
              <option value="">Selecione...</option>
              {availableTypes
                .filter(type => !isPermissionActive(type))
                .map(type => (
                  <option key={type} value={type}>
                    {PERMISSION_NAMES[type] || type}
                  </option>
                ))}
            </select>
          </label>
        </div>
        <div style={{ marginBottom: '12px' }}>
          <label>
            Observações (opcional):
            <textarea
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              style={{ width: '100%', marginTop: '8px' }}
              rows={3}
            />
          </label>
        </div>
        <button
          onClick={handleActivate}
          disabled={!selectedType || actionLoading}
        >
          {actionLoading ? 'Processando...' : 'Ativar Permissão'}
        </button>
      </div>

      {/* Permissões Inativas */}
      {permissions.filter(p => !p.is_active).length > 0 && (
        <div style={{ marginTop: '24px', borderTop: '1px solid #ddd', paddingTop: '20px' }}>
          <h3>Histórico de Permissões</h3>
          <ul>
            {permissions
              .filter(p => !p.is_active)
              .map(permission => (
                <li key={permission.id} style={{ opacity: 0.6 }}>
                  <strong>{PERMISSION_NAMES[permission.permission_type]}</strong>
                  {permission.revoked_at && (
                    <span> - Desativada em {new Date(permission.revoked_at).toLocaleDateString()}</span>
                  )}
                </li>
              ))}
          </ul>
        </div>
      )}
    </div>
  );
};

export default PlayerPermissionsPanel;
```

---

## 🔍 **Tratamento de Erros**

### **Estrutura Recomendada**

```typescript
const handlePermissionAction = async () => {
  try {
    await activatePermission(steamId, 'admin', 'admin');
    // Sucesso
  } catch (error: any) {
    if (error.message.includes('já está ativa')) {
      // Permissão já ativa (400)
      console.warn('Permissão já estava ativa');
    } else if (error.message.includes('não encontrado')) {
      // Jogador não encontrado (404)
      alert('Jogador não encontrado');
    } else if (error.message.includes('tipo de permissão inválido')) {
      // Tipo de permissão inválido (400)
      alert('Tipo de permissão inválido');
    } else {
      // Erro genérico (500)
      console.error('Erro ao processar permissão:', error);
      alert('Erro ao processar permissão. Tente novamente.');
    }
  }
};
```

---

## 📊 **Validações no Frontend**

```typescript
const validatePermissionAction = (
  steamId: string,
  permissionType: string
): string | null => {
  // Validar Steam ID
  if (!steamId || steamId.trim() === '') {
    return 'Steam ID é obrigatório';
  }

  if (!/^\d+$/.test(steamId)) {
    return 'Steam ID deve conter apenas números';
  }

  // Validar Tipo de Permissão
  if (!permissionType || permissionType.trim() === '') {
    return 'Tipo de permissão é obrigatório';
  }

  const validTypes = ['admin', 'banned', 'exclusive', 'server_admin', 'silenced', 'whitelisted'];
  if (!validTypes.includes(permissionType)) {
    return `Tipo de permissão inválido. Tipos válidos: ${validTypes.join(', ')}`;
  }

  return null; // Válido
};
```

---

## 🧪 **Exemplos de Teste**

### **Via cURL**

```bash
# Ativar permissão
curl -X POST "http://192.168.100.3:3000/api/players/76561198040636105/permissions/admin/activate" \
  -H "Content-Type: application/json" \
  -d '{"granted_by": "admin", "notes": "Teste"}'

# Listar permissões
curl -X GET "http://192.168.100.3:3000/api/players/76561198040636105/permissions"

# Estatísticas
curl -X GET "http://192.168.100.3:3000/api/permissions/stats"
```

---

## ⚠️ **Observações Importantes**

### **1. Sincronização de Arquivos INI**

- Quando uma permissão é ativada/desativada, o arquivo `.ini` correspondente é atualizado automaticamente
- Se houver problemas na atualização, use o endpoint `/api/permissions/sync-ini-files` para forçar a sincronização

### **2. Múltiplas Permissões**

- Um jogador pode ter várias permissões simultaneamente
- Cada permissão é independente e gerenciada separadamente

### **3. Validações Automáticas**

O backend valida automaticamente:
- ✅ Jogador existe na tabela `players`
- ✅ Tipo de permissão é válido
- ✅ Permissão não está duplicada ao ativar
- ✅ Permissão existe ao desativar

### **4. Histórico**

- Permissões inativas são mantidas no banco de dados para auditoria
- Use `include_inactive=true` para ver o histórico completo

---

## 📋 **Checklist de Implementação**

- [ ] Configurar URL base da API no frontend
- [ ] Criar funções para todos os 7 endpoints
- [ ] Implementar interfaces TypeScript para tipos de dados
- [ ] Criar hook customizado para gerenciar estado
- [ ] Implementar tratamento de erros (400, 404, 500)
- [ ] Adicionar validações no frontend
- [ ] Criar componente de UI para listar permissões
- [ ] Criar componente para ativar/desativar permissões
- [ ] Implementar feedback visual (loading, success, error)
- [ ] Testar com diferentes tipos de permissão
- [ ] Testar com jogador inexistente
- [ ] Testar permissão já ativa/inativa
- [ ] Implementar busca/filtro de permissões
- [ ] Adicionar confirmação antes de desativar
- [ ] Implementar estatísticas visuais

---

**Última atualização:** 2025-01-15  
**Versão da API:** 1.10.0

