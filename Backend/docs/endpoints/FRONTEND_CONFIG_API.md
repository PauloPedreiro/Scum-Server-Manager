## API de Configuração (config.json) - Frontend

### Visão Geral

- **Objetivo**: Gerenciar o arquivo `data/config.json` através do frontend.
- **Fonte dos dados**: Arquivo `data/config.json` no diretório de dados da aplicação.
- **Formato das respostas**: JSON com estrutura hierárquica de seções e campos.
- **Backup automático**: Sistema cria backup antes de cada modificação (mantém últimos 10 backups).

---

### Endpoints Disponíveis

| Método | Endpoint | Descrição |
| --- | --- | --- |
| `GET` | `/api/config` | Obter configuração completa ou seção específica |
| `GET` | `/api/config/sections` | Listar todas as seções disponíveis |
| `PATCH` | `/api/config` | Atualizar uma ou mais seções (merge profundo) |
| `PUT` | `/api/config` | Substituir configuração completa |
| `PUT` | `/api/config/<section>` | Atualizar seção específica (aceita qualquer campo) |
| `GET` | `/api/config/backup` | Listar backups disponíveis |
| `POST` | `/api/config/restore` | Restaurar configuração de um backup |

---

### 1. `GET /api/config`

Obter configuração completa ou uma seção específica do `config.json`.

**Query Params**

| Parâmetro | Tipo | Default | Descrição |
| --- | --- | --- | --- |
| `section` | `string` | - | Nome da seção (ex: `api`, `server`, `scheduler`, `paths.scum_server`) |

**Nota**: Suporta caminhos aninhados usando ponto (`.`). Exemplo: `paths.scum_server` para acessar a subseção `scum_server` dentro de `paths`.

**Exemplos**

```bash
# Obter configuração completa
GET /api/config

# Obter apenas seção api
GET /api/config?section=api
```

**Resposta de Exemplo (Configuração Completa)**

```json
{
  "success": true,
  "data": {
    "paths": {
      "application": {
        "data_directory": "data",
        "logs_directory": "data/logs",
        "database": "data/SSM.db"
      },
      "scum_server": {
        "root_directory": "C:\\Servers\\Scum",
        "binaries_directory": "C:\\Servers\\Scum\\SCUM\\Binaries\\Win64"
      }
    },
    "server": {
      "steamcmd_path": "C:\\Servers\\steamcmd",
      "port": 8900,
      "max_players": 64
    },
    "api": {
      "host": "0.0.0.0",
      "port": 3000,
      "debug": false
    },
    "scheduler": {
      "enabled": true,
      "restart_times": ["02:00", "03:00"]
    }
  },
  "timestamp": 1701504000
}
```

**Resposta de Exemplo (Seção Específica)**

```json
{
  "success": true,
  "data": {
    "api": {
      "host": "0.0.0.0",
      "port": 3000,
      "debug": false
    }
  },
  "timestamp": 1701504000
}
```

---

### 2. `GET /api/config/sections`

Listar todas as seções disponíveis no `config.json`.

**Query Params (opcional)**

| Parâmetro | Tipo | Default | Descrição |
| --- | --- | --- | --- |
| `include_nested` | `boolean` | `true` | Incluir subseções aninhadas (ex: `paths.scum_server`) |

**Resposta de Exemplo**

```json
{
  "success": true,
  "data": {
    "sections": [
      "paths",
      "paths.application",
      "paths.scum_server",
      "server",
      "logging",
      "api",
      "updates",
      "communication",
      "scheduler",
      "weather_scheduler",
      "squad_sync",
      "survival_sync",
      "rankings_sync",
      "player_skills_sync",
      "chest_sync",
      "notifications",
      "logs",
      "steam",
      "chat_monitoring",
      "time_precision",
      "fishing_ranking",
      "lockpicking_ranking",
      "kills_ranking",
      "snipers_ranking",
      "vehicle_verification",
      "player_gps_sync",
      "scum_db_shared_copy"
    ],
    "total": 27
  },
  "timestamp": 1701504000
}
```

**Nota**: Quando `include_nested=true`, a lista inclui tanto seções de primeiro nível quanto subseções aninhadas (usando notação com ponto, ex: `paths.scum_server`).

---

### 3. `PATCH /api/config`

Atualizar uma ou mais seções do `config.json`. O sistema faz **merge profundo (deep merge)**, preservando campos não especificados.

**Body**

```json
{
  "sections": {
    "api": {
      "port": 3001,
      "debug": true
    },
    "scheduler": {
      "enabled": false
    }
  },
  "create_backup": true
}
```

**Campos do Body**

| Campo | Tipo | Obrigatório | Descrição |
| --- | --- | --- | --- |
| `sections` | `object` | Sim | Objeto com seções a atualizar |
| `create_backup` | `boolean` | Não | Criar backup antes de atualizar (padrão: `true`) |

**Resposta de Exemplo**

```json
{
  "success": true,
  "message": "Configuração atualizada com sucesso",
  "data": {
    "updated_sections": ["api", "scheduler"],
    "requires_restart": ["api", "scheduler"]
  },
  "timestamp": 1701504000
}
```

**Nota sobre Merge Profundo**

O sistema faz merge profundo, então você pode atualizar apenas campos específicos dentro de objetos aninhados:

```json
{
  "sections": {
    "scheduler": {
      "restart_times": ["02:00", "03:00", "04:00"]
    }
  }
}
```

Isso atualiza apenas `restart_times`, mantendo outros campos de `scheduler` intactos.

---

### 4. `PUT /api/config`

Substituir toda a configuração do `config.json`. **Use com cuidado** - isso substitui completamente o arquivo.

**Body**

```json
{
  "config": {
    "paths": {},
    "server": {},
    "api": {},
    "scheduler": {}
  },
  "create_backup": true
}
```

**Campos do Body**

| Campo | Tipo | Obrigatório | Descrição |
| --- | --- | --- | --- |
| `config` | `object` | Sim | Configuração completa |
| `create_backup` | `boolean` | Não | Criar backup antes de substituir (padrão: `true`) |

**Resposta de Exemplo**

```json
{
  "success": true,
  "message": "Configuração completa atualizada",
  "data": {
    "requires_restart": true
  },
  "timestamp": 1701504000
}
```

---

### 5. `PUT /api/config/<section>`

Atualizar seção completa do `config.json`. Aceita qualquer campo (conhecido ou customizado). Útil para salvar múltiplas alterações de uma vez.

**Path Params**

| Parâmetro | Tipo | Descrição |
| --- | --- | --- |
| `section` | `string` | Nome da seção (ex: `api`, `server`, `scheduler`, `paths.scum_server`) |

**Nota**: Suporta caminhos aninhados usando ponto (`.`). Exemplo: `paths.scum_server` para atualizar a subseção `scum_server` dentro de `paths`.

**Body**

```json
{
  "host": "0.0.0.0",
  "port": 3001,
  "debug": true,
  "custom_field": "value"
}
```

**Nota**: O body deve ser um objeto direto com os campos da seção, não um objeto aninhado.

**Query Params (opcional)**

| Parâmetro | Tipo | Default | Descrição |
| --- | --- | --- | --- |
| `create_backup` | `boolean` | `true` | Criar backup antes de atualizar |

**Resposta de Exemplo**

```json
{
  "success": true,
  "message": "Seção \"api\" atualizada com sucesso",
  "data": {
    "section": "api",
    "updated_fields": ["host", "port", "debug"],
    "requires_restart": ["api"]
  },
  "timestamp": 1701504000
}
```

**Exemplo de Uso**

```bash
# Atualizar seção api
PUT /api/config/api
Content-Type: application/json

{
  "host": "0.0.0.0",
  "port": 3001,
  "debug": true
}
```

**Diferença entre PATCH e PUT /api/config/<section>**

- **`PATCH /api/config`**: Atualiza múltiplas seções com merge profundo (preserva campos não especificados)
- **`PUT /api/config/<section>`**: Atualiza uma seção específica, substituindo completamente os campos da seção (mas preserva outras seções)

---

### 6. `GET /api/config/backup`

Listar backups disponíveis do `config.json`.

**Query Params**

| Parâmetro | Tipo | Default | Descrição |
| --- | --- | --- | --- |
| `limit` | `number` | `10` | Número máximo de backups a retornar |

**Resposta de Exemplo**

```json
{
  "success": true,
  "data": {
    "backups": [
      {
        "filename": "config.backup.20251202_153045.json",
        "path": "data/config.backup.20251202_153045.json",
        "created_at": "2025-12-02T15:30:45",
        "size": 15234
      },
      {
        "filename": "config.backup.20251202_143022.json",
        "path": "data/config.backup.20251202_143022.json",
        "created_at": "2025-12-02T14:30:22",
        "size": 15189
      }
    ],
    "total": 2
  },
  "timestamp": 1701504000
}
```

---

### 7. `POST /api/config/restore`

Restaurar configuração de um backup. O sistema cria backup da configuração atual antes de restaurar.

**Body**

```json
{
  "backup_file": "config.backup.20251202_153045.json",
  "create_backup": true
}
```

**Campos do Body**

| Campo | Tipo | Obrigatório | Descrição |
| --- | --- | --- | --- |
| `backup_file` | `string` | Sim | Nome do arquivo de backup (ex: `config.backup.20251202_153045.json`) |
| `create_backup` | `boolean` | Não | Criar backup da configuração atual antes de restaurar (padrão: `true`) |

**Resposta de Exemplo**

```json
{
  "success": true,
  "message": "Configuração restaurada com sucesso",
  "data": {
    "restored_from": "config.backup.20251202_153045.json",
    "requires_restart": true
  },
  "timestamp": 1701504000
}
```

**Erro 404**

Se o backup não for encontrado:

```json
{
  "success": false,
  "error": "Backup não encontrado: config.backup.20251202_153045.json"
}
```

---

## TypeScript Interfaces

```typescript
// Tipos básicos
interface ConfigResponse {
  success: boolean;
  data: Record<string, any>;
  timestamp: number;
}

interface SectionsResponse {
  success: boolean;
  data: {
    sections: string[];
    total: number;
  };
  timestamp: number;
}

interface UpdateConfigRequest {
  sections: Record<string, any>;
  create_backup?: boolean;
}

interface UpdateConfigResponse {
  success: boolean;
  message: string;
  data: {
    updated_sections: string[];
    requires_restart: string[];
  };
  timestamp: number;
}

interface BackupInfo {
  filename: string;
  path: string;
  created_at: string;
  size: number;
}

interface BackupsResponse {
  success: boolean;
  data: {
    backups: BackupInfo[];
    total: number;
  };
  timestamp: number;
}

interface RestoreConfigRequest {
  backup_file: string;
  create_backup?: boolean;
}

interface RestoreConfigResponse {
  success: boolean;
  message: string;
  data: {
    restored_from: string;
    requires_restart: boolean;
  };
  timestamp: number;
}
```

---

## React Hooks

### Hook para Obter Configuração

```typescript
import { useState, useEffect } from 'react';

function useConfig(section?: string) {
  const [config, setConfig] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchConfig = async () => {
      try {
        setLoading(true);
        const url = section 
          ? `/api/config?section=${section}`
          : '/api/config';
        
        const response = await fetch(url);
        const data = await response.json();
        
        if (data.success) {
          setConfig(section ? data.data[section] : data.data);
        } else {
          setError(data.error || 'Erro ao carregar configuração');
        }
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Erro desconhecido');
      } finally {
        setLoading(false);
      }
    };

    fetchConfig();
  }, [section]);

  return { config, loading, error };
}
```

### Hook para Atualizar Configuração

```typescript
import { useState } from 'react';

function useUpdateConfig() {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const updateConfig = async (
    sections: Record<string, any>,
    createBackup: boolean = true
  ) => {
    try {
      setLoading(true);
      setError(null);

      const response = await fetch('/api/config', {
        method: 'PATCH',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          sections,
          create_backup: createBackup,
        }),
      });

      const data = await response.json();

      if (data.success) {
        return data.data;
      } else {
        throw new Error(data.error || 'Erro ao atualizar configuração');
      }
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Erro desconhecido';
      setError(errorMessage);
      throw err;
    } finally {
      setLoading(false);
    }
  };

  return { updateConfig, loading, error };
}
```

### Hook para Listar Backups

```typescript
import { useState, useEffect } from 'react';

function useConfigBackups(limit: number = 10) {
  const [backups, setBackups] = useState<BackupInfo[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchBackups = async () => {
      try {
        setLoading(true);
        const response = await fetch(`/api/config/backup?limit=${limit}`);
        const data = await response.json();

        if (data.success) {
          setBackups(data.data.backups);
        } else {
          setError(data.error || 'Erro ao listar backups');
        }
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Erro desconhecido');
      } finally {
        setLoading(false);
      }
    };

    fetchBackups();
  }, [limit]);

  return { backups, loading, error };
}
```

### Hook para Restaurar Backup

```typescript
import { useState } from 'react';

function useRestoreConfig() {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const restoreConfig = async (
    backupFile: string,
    createBackup: boolean = true
  ) => {
    try {
      setLoading(true);
      setError(null);

      const response = await fetch('/api/config/restore', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          backup_file: backupFile,
          create_backup: createBackup,
        }),
      });

      const data = await response.json();

      if (data.success) {
        return data.data;
      } else {
        throw new Error(data.error || 'Erro ao restaurar backup');
      }
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Erro desconhecido';
      setError(errorMessage);
      throw err;
    } finally {
      setLoading(false);
    }
  };

  return { restoreConfig, loading, error };
}
```

---

## Exemplos de Uso

### Exemplo 1: Obter e Exibir Configuração da API

```typescript
import React from 'react';
import { useConfig } from './hooks/useConfig';

function ApiConfig() {
  const { config, loading, error } = useConfig('api');

  if (loading) return <div>Carregando...</div>;
  if (error) return <div>Erro: {error}</div>;
  if (!config) return <div>Configuração não encontrada</div>;

  return (
    <div>
      <h2>Configuração da API</h2>
      <p>Host: {config.host}</p>
      <p>Porta: {config.port}</p>
      <p>Debug: {config.debug ? 'Sim' : 'Não'}</p>
    </div>
  );
}
```

### Exemplo 2: Atualizar Porta da API

```typescript
import React, { useState } from 'react';
import { useUpdateConfig } from './hooks/useUpdateConfig';

function UpdateApiPort() {
  const [port, setPort] = useState(3000);
  const { updateConfig, loading, error } = useUpdateConfig();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      await updateConfig({
        api: { port },
      });
      alert('Porta atualizada com sucesso!');
    } catch (err) {
      alert(`Erro: ${err}`);
    }
  };

  return (
    <form onSubmit={handleSubmit}>
      <label>
        Porta da API:
        <input
          type="number"
          value={port}
          onChange={(e) => setPort(Number(e.target.value))}
        />
      </label>
      <button type="submit" disabled={loading}>
        {loading ? 'Salvando...' : 'Salvar'}
      </button>
      {error && <div style={{ color: 'red' }}>{error}</div>}
    </form>
  );
}
```

### Exemplo 3: Listar e Restaurar Backups

```typescript
import React from 'react';
import { useConfigBackups } from './hooks/useConfigBackups';
import { useRestoreConfig } from './hooks/useRestoreConfig';

function BackupManager() {
  const { backups, loading, error } = useConfigBackups(10);
  const { restoreConfig, loading: restoring } = useRestoreConfig();

  const handleRestore = async (backupFile: string) => {
    if (!confirm('Tem certeza que deseja restaurar este backup?')) {
      return;
    }

    try {
      await restoreConfig(backupFile);
      alert('Backup restaurado com sucesso!');
    } catch (err) {
      alert(`Erro: ${err}`);
    }
  };

  if (loading) return <div>Carregando backups...</div>;
  if (error) return <div>Erro: {error}</div>;

  return (
    <div>
      <h2>Backups Disponíveis</h2>
      <ul>
        {backups.map((backup) => (
          <li key={backup.filename}>
            <div>
              <strong>{backup.filename}</strong>
              <br />
              Criado em: {new Date(backup.created_at).toLocaleString()}
              <br />
              Tamanho: {(backup.size / 1024).toFixed(2)} KB
            </div>
            <button
              onClick={() => handleRestore(backup.filename)}
              disabled={restoring}
            >
              {restoring ? 'Restaurando...' : 'Restaurar'}
            </button>
          </li>
        ))}
      </ul>
    </div>
  );
}
```

---

## Notas Importantes

1. **Backup Automático**: O sistema cria backup automaticamente antes de cada modificação (padrão: `create_backup: true`). Os últimos 10 backups são mantidos automaticamente.

2. **Merge Profundo**: Ao usar `PATCH /api/config`, o sistema faz merge profundo, preservando campos não especificados. Isso permite atualizar apenas campos específicos sem perder outras configurações.

3. **Requires Restart**: Algumas seções requerem reinício do servidor após atualização. O endpoint retorna `requires_restart` indicando quais seções precisam de restart.

4. **Ordem Preservada**: O sistema preserva a ordem das chaves no JSON (usando `sort_keys=False`).

5. **Validação**: O sistema valida o JSON antes de salvar, mas não valida valores específicos (ex: portas válidas). Isso deve ser feito no frontend.

6. **Thread Safety**: As operações são thread-safe, mas recomenda-se evitar atualizações simultâneas da mesma seção.

---

**Última atualização**: 02/12/2025

