## API de Webhooks (webhooks.json) - Frontend

### Visão Geral

- **Objetivo**: Gerenciar o arquivo `data/webhooks.json` através do frontend.
- **Fonte dos dados**: Arquivo `data/webhooks.json` no diretório de dados da aplicação.
- **Formato das respostas**: JSON com estrutura simples de pares chave-valor (nome do webhook: URL).
- **Backup automático**: Sistema cria backup antes de cada modificação (mantém últimos 10 backups).

---

### Endpoints Disponíveis

| Método | Endpoint | Descrição |
| --- | --- | --- |
| `GET` | `/api/webhooks` | Obter todos os webhooks ou um específico |
| `GET` | `/api/webhooks/names` | Listar todos os nomes de webhooks disponíveis |
| `GET` | `/api/webhooks/<webhook_name>` | Obter um webhook específico |
| `PATCH` | `/api/webhooks` | Atualizar múltiplos webhooks |
| `PUT` | `/api/webhooks` | Substituir todos os webhooks |
| `PUT` | `/api/webhooks/<webhook_name>` | Atualizar um webhook específico (apenas existentes) |
| `POST` | `/api/webhooks/<webhook_name>/test` | Testar webhook enviando mensagem de teste |
| `POST` | `/api/webhooks/test` | Testar webhook por URL (antes de salvar) |
| `GET` | `/api/webhooks/backup` | Listar backups disponíveis |
| `POST` | `/api/webhooks/restore` | Restaurar webhooks de um backup |

---

### 1. `GET /api/webhooks`

Obter todos os webhooks ou um webhook específico.

**Query Params (opcional)**

| Parâmetro | Tipo | Descrição |
| --- | --- | --- |
| `webhook` | `string` | Nome do webhook específico para retornar apenas um |

**Exemplos**

```bash
# Obter todos os webhooks
GET /api/webhooks

# Obter apenas um webhook específico
GET /api/webhooks?webhook=serverstatus
```

**Resposta de Exemplo (Todos os Webhooks)**

```json
{
  "success": true,
  "data": {
    "serverstatus": "https://discord.com/api/webhooks/1428458802499424279/Pv_380rxyuHl7VOCi34tgVN5pYg4cAk_F4333Q4oz7a6TLdibBT3PdMV5mtJTrtuTvJg",
    "new_player": "https://discord.com/api/webhooks/1428940874590584964/l5OBQurNMovFR27apRsU7XN-Wi-4k3R-fvb7Ox3uqUhMiYSrVvrFPx_zUbBHUJuKm1kY",
    "players_online": "https://discord.com/api/webhooks/1428973563179700318/gsSRwcrM5FGtgKar67N81Dl9p6hW5QkMiG7u94M80LyGbIGZieULfCHkSQY0YzbgvVA4",
    "vehicle_registration": "https://discord.com/api/webhooks/1429333841654452234/CySpgdtLgOCLyy1LswvuG717CS3OdqqQmfTNfQfgugzmYrnVZ12zqmjkcRdsoWAxQtiR",
    "chat_in_game": "https://discord.com/api/webhooks/1429673577686237278/V5BaoOH9aNMCovfCVar8QrizI2Uy8dq11YPEvs2_a5UGat9oZRXh_OVAxDOJ5c50hn5a"
  },
  "timestamp": 1701504000
}
```

**Resposta de Exemplo (Webhook Específico)**

```json
{
  "success": true,
  "data": {
    "serverstatus": "https://discord.com/api/webhooks/1428458802499424279/Pv_380rxyuHl7VOCi34tgVN5pYg4cAk_F4333Q4oz7a6TLdibBT3PdMV5mtJTrtuTvJg"
  },
  "timestamp": 1701504000
}
```

---

### 2. `GET /api/webhooks/names`

Listar todos os nomes de webhooks disponíveis.

**Resposta de Exemplo**

```json
{
  "success": true,
  "data": {
    "webhooks": [
      "serverstatus",
      "new_player",
      "players_online",
      "vehicle_registration",
      "chat_in_game",
      "adminlog",
      "vehicle-log",
      "bunkers_status",
      "timer",
      "commands",
      "fishing_ranking",
      "kill_log",
      "chest_events",
      "chest_vehicle_alerts",
      "log-ssm",
      "lockpicking_events",
      "top20_lockpicking",
      "top20_kills",
      "top20_snipers"
    ],
    "total": 19
  },
  "timestamp": 1701504000
}
```

---

### 3. `GET /api/webhooks/<webhook_name>`

Obter um webhook específico pelo nome.

**Parâmetros de Rota**

| Parâmetro | Tipo | Descrição |
| --- | --- | --- |
| `webhook_name` | `string` | Nome do webhook (ex: `serverstatus`, `new_player`) |

**Exemplo**

```bash
GET /api/webhooks/serverstatus
```

**Resposta de Exemplo**

```json
{
  "success": true,
  "data": {
    "serverstatus": "https://discord.com/api/webhooks/1428458802499424279/Pv_380rxyuHl7VOCi34tgVN5pYg4cAk_F4333Q4oz7a6TLdibBT3PdMV5mtJTrtuTvJg"
  },
  "timestamp": 1701504000
}
```

**Resposta de Erro (404)**

```json
{
  "success": false,
  "error": "Webhook \"serverstatus\" não encontrado"
}
```

---

### 4. `PATCH /api/webhooks`

Atualizar múltiplos webhooks de uma vez. Mantém webhooks não especificados.

**Body**

```json
{
  "webhooks": {
    "serverstatus": "https://discord.com/api/webhooks/NOVA_URL",
    "new_player": "https://discord.com/api/webhooks/OUTRA_URL"
  },
  "create_backup": true
}
```

**Campos**

| Campo | Tipo | Obrigatório | Descrição |
| --- | --- | --- | --- |
| `webhooks` | `object` | Sim | Objeto com pares nome: URL dos webhooks a atualizar |
| `create_backup` | `boolean` | Não | Criar backup antes de atualizar (padrão: `true`) |

**Resposta de Exemplo**

```json
{
  "success": true,
  "message": "Webhooks atualizados com sucesso",
  "data": {
    "updated_webhooks": ["serverstatus", "new_player"]
  },
  "timestamp": 1701504000
}
```

---

### 5. `PUT /api/webhooks`

Substituir completamente todos os webhooks.

**Body**

```json
{
  "webhooks": {
    "serverstatus": "https://discord.com/api/webhooks/...",
    "new_player": "https://discord.com/api/webhooks/...",
    "players_online": "https://discord.com/api/webhooks/..."
  },
  "create_backup": true
}
```

**Campos**

| Campo | Tipo | Obrigatório | Descrição |
| --- | --- | --- | --- |
| `webhooks` | `object` | Sim | Objeto completo com todos os webhooks |
| `create_backup` | `boolean` | Não | Criar backup antes de substituir (padrão: `true`) |

**Resposta de Exemplo**

```json
{
  "success": true,
  "message": "Webhooks completos atualizados",
  "timestamp": 1701504000
}
```

---

### 6. `PUT /api/webhooks/<webhook_name>`

Atualizar um webhook específico (apenas webhooks existentes).

**Parâmetros de Rota**

| Parâmetro | Tipo | Descrição |
| --- | --- | --- |
| `webhook_name` | `string` | Nome do webhook (ex: `serverstatus`) |

**Query Params (opcional)**

| Parâmetro | Tipo | Default | Descrição |
| --- | --- | --- | --- |
| `create_backup` | `boolean` | `true` | Criar backup antes de atualizar |

**Body**

```json
{
  "url": "https://discord.com/api/webhooks/NOVA_URL",
  "create_backup": true
}
```

**Campos**

| Campo | Tipo | Obrigatório | Descrição |
| --- | --- | --- | --- |
| `url` | `string` | Sim | URL do webhook |
| `create_backup` | `boolean` | Não | Criar backup antes de atualizar (padrão: `true`) |

**Exemplo**

```bash
PUT /api/webhooks/serverstatus
Content-Type: application/json

{
  "url": "https://discord.com/api/webhooks/NOVA_URL"
}
```

**Resposta de Exemplo**

```json
{
  "success": true,
  "message": "Webhook \"serverstatus\" atualizado com sucesso",
  "data": {
    "webhook_name": "serverstatus",
    "url": "https://discord.com/api/webhooks/NOVA_URL"
  },
  "timestamp": 1701504000
}
```

**Resposta de Erro (404)**

```json
{
  "success": false,
  "error": "Webhook 'serverstatus' não existe. Apenas atualização de webhooks existentes é permitida."
}
```

**Nota**: Apenas webhooks existentes podem ser atualizados. Novos webhooks devem ser criados pelo desenvolvimento.

---

### 7. `POST /api/webhooks/<webhook_name>/test`

Testar um webhook enviando uma mensagem de teste para o webhook configurado.

**Parâmetros de Rota**

| Parâmetro | Tipo | Descrição |
| --- | --- | --- |
| `webhook_name` | `string` | Nome do webhook a testar (ex: `serverstatus`) |

**Exemplo**

```bash
POST /api/webhooks/serverstatus/test
```

**Resposta de Sucesso (200)**

```json
{
  "success": true,
  "message": "Webhook testado com sucesso",
  "data": {
    "webhook_name": "serverstatus",
    "webhook_url": "https://discord.com/api/webhooks/...",
    "status_code": 204
  },
  "timestamp": 1701504000
}
```

**Resposta de Erro (404)**

```json
{
  "success": false,
  "error": "Webhook \"serverstatus\" não encontrado"
}
```

**Resposta de Erro (400)**

```json
{
  "success": false,
  "message": "Erro ao testar webhook: 404",
  "data": {
    "webhook_name": "serverstatus",
    "status_code": 404,
    "error": "Unknown Webhook"
  },
  "timestamp": 1701504000
}
```

---

### 8. `POST /api/webhooks/test`

Testar um webhook enviando uma mensagem de teste usando a URL diretamente. Útil para testar antes de salvar no arquivo.

**Body**

```json
{
  "url": "https://discord.com/api/webhooks/SUA_URL_AQUI"
}
```

**Campos**

| Campo | Tipo | Obrigatório | Descrição |
| --- | --- | --- | --- |
| `url` | `string` | Sim | URL do webhook a testar |

**Exemplo**

```bash
POST /api/webhooks/test
Content-Type: application/json

{
  "url": "https://discord.com/api/webhooks/SUA_URL_AQUI"
}
```

**Resposta de Sucesso (200)**

```json
{
  "success": true,
  "message": "Webhook testado com sucesso",
  "data": {
    "webhook_url": "https://discord.com/api/webhooks/...",
    "status_code": 204
  },
  "timestamp": 1701504000
}
```

**Resposta de Erro (400)**

```json
{
  "success": false,
  "message": "Erro ao testar webhook: 404",
  "data": {
    "webhook_url": "https://discord.com/api/webhooks/...",
    "status_code": 404,
    "error": "Unknown Webhook"
  },
  "timestamp": 1701504000
}
```

---

### 8. `GET /api/webhooks/backup`

Listar backups disponíveis do `webhooks.json`.

**Query Params (opcional)**

| Parâmetro | Tipo | Default | Descrição |
| --- | --- | --- | --- |
| `limit` | `number` | `10` | Número máximo de backups a retornar |

**Exemplo**

```bash
GET /api/webhooks/backup?limit=10
```

**Resposta de Exemplo**

```json
{
  "success": true,
  "data": {
    "backups": [
      {
        "filename": "webhooks.backup.20251202_153045.json",
        "path": "data/webhooks.backup.20251202_153045.json",
        "created_at": "2025-12-02T15:30:45",
        "size": 1234
      },
      {
        "filename": "webhooks.backup.20251202_140030.json",
        "path": "data/webhooks.backup.20251202_140030.json",
        "created_at": "2025-12-02T14:00:30",
        "size": 1200
      }
    ],
    "total": 2
  },
  "timestamp": 1701504000
}
```

---

### 9. `POST /api/webhooks/restore`

Restaurar webhooks de um backup. Cria backup dos webhooks atuais antes de restaurar.

**Body**

```json
{
  "backup_file": "webhooks.backup.20251202_153045.json",
  "create_backup": true
}
```

**Campos**

| Campo | Tipo | Obrigatório | Descrição |
| --- | --- | --- | --- |
| `backup_file` | `string` | Sim | Nome do arquivo de backup (ex: `webhooks.backup.20251202_153045.json`) |
| `create_backup` | `boolean` | Não | Criar backup dos webhooks atuais antes de restaurar (padrão: `true`) |

**Exemplo**

```bash
POST /api/webhooks/restore
Content-Type: application/json

{
  "backup_file": "webhooks.backup.20251202_153045.json",
  "create_backup": true
}
```

**Resposta de Exemplo**

```json
{
  "success": true,
  "message": "Webhooks restaurados com sucesso",
  "data": {
    "restored_from": "webhooks.backup.20251202_153045.json"
  },
  "timestamp": 1701504000
}
```

**Resposta de Erro (404)**

```json
{
  "success": false,
  "error": "Backup não encontrado: webhooks.backup.20251202_153045.json"
}
```

---

## TypeScript Interfaces

```typescript
// Tipos para Webhooks
interface WebhooksResponse {
  success: boolean;
  data: Record<string, string>; // { webhook_name: url }
  timestamp: number;
}

interface WebhookNamesResponse {
  success: boolean;
  data: {
    webhooks: string[];
    total: number;
  };
  timestamp: number;
}

interface UpdateWebhooksRequest {
  webhooks: Record<string, string>; // { webhook_name: url }
  create_backup?: boolean;
}

interface ReplaceWebhooksRequest {
  webhooks: Record<string, string>; // { webhook_name: url }
  create_backup?: boolean;
}

interface UpdateWebhookRequest {
  url: string;
  create_backup?: boolean;
}

interface UpdateWebhookResponse {
  success: boolean;
  message: string;
  data: {
    webhook_name: string;
    url: string;
  };
  timestamp: number;
}

interface BackupInfo {
  filename: string;
  path: string;
  created_at: string;
  size: number;
}

interface ListBackupsResponse {
  success: boolean;
  data: {
    backups: BackupInfo[];
    total: number;
  };
  timestamp: number;
}

interface RestoreBackupRequest {
  backup_file: string;
  create_backup?: boolean;
}

interface RestoreBackupResponse {
  success: boolean;
  message: string;
  data: {
    restored_from: string;
  };
  timestamp: number;
}

interface TestWebhookResponse {
  success: boolean;
  message: string;
  data: {
    webhook_name?: string;
    webhook_url: string;
    status_code: number;
    error?: string;
  };
  timestamp: number;
}

interface TestWebhookByUrlRequest {
  url: string;
}
```

---

## React Hooks

### Hook para Obter Todos os Webhooks

```typescript
import { useState, useEffect } from 'react';

function useWebhooks() {
  const [webhooks, setWebhooks] = useState<Record<string, string>>({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetch('/api/webhooks')
      .then(res => res.json())
      .then((data: WebhooksResponse) => {
        if (data.success) {
          setWebhooks(data.data);
        } else {
          setError(data.error || 'Erro ao carregar webhooks');
        }
      })
      .catch(err => setError(err.message))
      .finally(() => setLoading(false));
  }, []);

  return { webhooks, loading, error };
}
```

### Hook para Obter Nomes dos Webhooks

```typescript
import { useState, useEffect } from 'react';

function useWebhookNames() {
  const [webhookNames, setWebhookNames] = useState<string[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetch('/api/webhooks/names')
      .then(res => res.json())
      .then((data: WebhookNamesResponse) => {
        if (data.success) {
          setWebhookNames(data.data.webhooks);
        } else {
          setError(data.error || 'Erro ao carregar nomes dos webhooks');
        }
      })
      .catch(err => setError(err.message))
      .finally(() => setLoading(false));
  }, []);

  return { webhookNames, loading, error };
}
```

### Hook para Atualizar Webhook

```typescript
import { useState } from 'react';

function useUpdateWebhook() {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const updateWebhook = async (
    webhookName: string,
    url: string,
    createBackup: boolean = true
  ) => {
    setLoading(true);
    setError(null);

    try {
      const response = await fetch(`/api/webhooks/${webhookName}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ url, create_backup: createBackup })
      });

      const data: UpdateWebhookResponse = await response.json();

      if (!data.success) {
        throw new Error(data.error || 'Erro ao atualizar webhook');
      }

      return data;
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Erro desconhecido';
      setError(errorMessage);
      throw err;
    } finally {
      setLoading(false);
    }
  };

  return { updateWebhook, loading, error };
}
```

### Hook para Testar Webhook (por nome)

```typescript
import { useState } from 'react';

function useTestWebhook() {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const testWebhook = async (webhookName: string) => {
    setLoading(true);
    setError(null);

    try {
      const response = await fetch(`/api/webhooks/${webhookName}/test`, {
        method: 'POST'
      });

      const data = await response.json();

      if (!data.success) {
        throw new Error(data.error || data.message || 'Erro ao testar webhook');
      }

      return data;
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Erro desconhecido';
      setError(errorMessage);
      throw err;
    } finally {
      setLoading(false);
    }
  };

  return { testWebhook, loading, error };
}
```

### Hook para Testar Webhook (por URL)

```typescript
import { useState } from 'react';

function useTestWebhookByUrl() {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const testWebhookByUrl = async (url: string) => {
    setLoading(true);
    setError(null);

    try {
      const response = await fetch('/api/webhooks/test', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ url })
      });

      const data = await response.json();

      if (!data.success) {
        throw new Error(data.error || data.message || 'Erro ao testar webhook');
      }

      return data;
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Erro desconhecido';
      setError(errorMessage);
      throw err;
    } finally {
      setLoading(false);
    }
  };

  return { testWebhookByUrl, loading, error };
}
```

### Hook para Listar Backups

```typescript
import { useState, useEffect } from 'react';

function useWebhookBackups(limit: number = 10) {
  const [backups, setBackups] = useState<BackupInfo[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetch(`/api/webhooks/backup?limit=${limit}`)
      .then(res => res.json())
      .then((data: ListBackupsResponse) => {
        if (data.success) {
          setBackups(data.data.backups);
        } else {
          setError(data.error || 'Erro ao carregar backups');
        }
      })
      .catch(err => setError(err.message))
      .finally(() => setLoading(false));
  }, [limit]);

  return { backups, loading, error };
}
```

### Hook para Restaurar Backup

```typescript
import { useState } from 'react';

function useRestoreWebhookBackup() {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const restoreBackup = async (
    backupFile: string,
    createBackup: boolean = true
  ) => {
    setLoading(true);
    setError(null);

    try {
      const response = await fetch('/api/webhooks/restore', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          backup_file: backupFile,
          create_backup: createBackup
        })
      });

      const data: RestoreBackupResponse = await response.json();

      if (!data.success) {
        throw new Error(data.error || 'Erro ao restaurar backup');
      }

      return data;
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Erro desconhecido';
      setError(errorMessage);
      throw err;
    } finally {
      setLoading(false);
    }
  };

  return { restoreBackup, loading, error };
}
```

---

## Exemplos de Uso

### Componente React para Listar Webhooks

```typescript
import React from 'react';
import { useWebhooks } from './hooks/useWebhooks';

function WebhooksList() {
  const { webhooks, loading, error } = useWebhooks();

  if (loading) return <div>Carregando webhooks...</div>;
  if (error) return <div>Erro: {error}</div>;

  return (
    <div>
      <h2>Webhooks Configurados</h2>
      <ul>
        {Object.entries(webhooks).map(([name, url]) => (
          <li key={name}>
            <strong>{name}:</strong> {url}
          </li>
        ))}
      </ul>
    </div>
  );
}
```

### Componente React para Editar Webhook com Teste

```typescript
import React, { useState } from 'react';
import { useUpdateWebhook } from './hooks/useUpdateWebhook';
import { useTestWebhook } from './hooks/useTestWebhook';
import { useTestWebhookByUrl } from './hooks/useTestWebhookByUrl';

function EditWebhook({ webhookName, currentUrl }: { webhookName: string; currentUrl: string }) {
  const [url, setUrl] = useState(currentUrl);
  const [testUrl, setTestUrl] = useState('');
  const { updateWebhook, loading, error } = useUpdateWebhook();
  const { testWebhook, loading: testing, error: testError } = useTestWebhook();
  const { testWebhookByUrl, loading: testingUrl, error: testUrlError } = useTestWebhookByUrl();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      await updateWebhook(webhookName, url);
      alert('Webhook atualizado com sucesso!');
    } catch (err) {
      alert(`Erro: ${err}`);
    }
  };

  const handleTest = async () => {
    try {
      const result = await testWebhook(webhookName);
      alert(`✅ Webhook testado com sucesso! Status: ${result.data.status_code}`);
    } catch (err) {
      alert(`❌ Erro ao testar webhook: ${err}`);
    }
  };

  const handleTestUrl = async () => {
    if (!testUrl) {
      alert('Por favor, insira uma URL para testar');
      return;
    }
    try {
      const result = await testWebhookByUrl(testUrl);
      alert(`✅ Webhook testado com sucesso! Status: ${result.data.status_code}`);
      // Se o teste foi bem-sucedido, pode sugerir salvar
      if (confirm('Teste bem-sucedido! Deseja salvar esta URL?')) {
        setUrl(testUrl);
      }
    } catch (err) {
      alert(`❌ Erro ao testar webhook: ${err}`);
    }
  };

  return (
    <div>
      <form onSubmit={handleSubmit}>
        <label>
          URL do Webhook:
          <input
            type="url"
            value={url}
            onChange={(e) => setUrl(e.target.value)}
            required
          />
        </label>
        <div style={{ display: 'flex', gap: '10px', marginTop: '10px' }}>
          <button type="submit" disabled={loading}>
            {loading ? 'Salvando...' : 'Salvar'}
          </button>
          <button type="button" onClick={handleTest} disabled={testing || !url}>
            {testing ? 'Testando...' : 'Testar Webhook'}
          </button>
        </div>
        {error && <div className="error">{error}</div>}
        {testError && <div className="error">Erro no teste: {testError}</div>}
      </form>
      
      <div style={{ marginTop: '20px', padding: '10px', border: '1px solid #ccc', borderRadius: '5px' }}>
        <h3>Testar URL Antes de Salvar</h3>
        <label>
          URL para Testar:
          <input
            type="url"
            value={testUrl}
            onChange={(e) => setTestUrl(e.target.value)}
            placeholder="Cole a URL do webhook aqui"
            style={{ width: '100%', marginTop: '5px' }}
          />
        </label>
        <button 
          type="button" 
          onClick={handleTestUrl} 
          disabled={testingUrl || !testUrl}
          style={{ marginTop: '10px' }}
        >
          {testingUrl ? 'Testando...' : 'Testar URL'}
        </button>
        {testUrlError && <div className="error" style={{ marginTop: '10px' }}>Erro: {testUrlError}</div>}
      </div>
    </div>
  );
}
```

### Componente React para Gerenciar Backups

```typescript
import React from 'react';
import { useWebhookBackups } from './hooks/useWebhookBackups';
import { useRestoreWebhookBackup } from './hooks/useRestoreWebhookBackup';

function WebhookBackupsManager() {
  const { backups, loading, error } = useWebhookBackups(10);
  const { restoreBackup, loading: restoring } = useRestoreWebhookBackup();

  const handleRestore = async (backupFile: string) => {
    if (!confirm('Tem certeza que deseja restaurar este backup?')) return;
    
    try {
      await restoreBackup(backupFile);
      alert('Backup restaurado com sucesso!');
    } catch (err) {
      alert(`Erro: ${err}`);
    }
  };

  if (loading) return <div>Carregando backups...</div>;
  if (error) return <div>Erro: {error}</div>;

  return (
    <div>
      <h2>Backups de Webhooks</h2>
      <table>
        <thead>
          <tr>
            <th>Arquivo</th>
            <th>Data de Criação</th>
            <th>Tamanho</th>
            <th>Ações</th>
          </tr>
        </thead>
        <tbody>
          {backups.map((backup) => (
            <tr key={backup.filename}>
              <td>{backup.filename}</td>
              <td>{new Date(backup.created_at).toLocaleString()}</td>
              <td>{(backup.size / 1024).toFixed(2)} KB</td>
              <td>
                <button
                  onClick={() => handleRestore(backup.filename)}
                  disabled={restoring}
                >
                  {restoring ? 'Restaurando...' : 'Restaurar'}
                </button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
```

---

## Tratamento de Erros

Todos os endpoints retornam um objeto com `success: false` em caso de erro:

```typescript
interface ErrorResponse {
  success: false;
  error: string;
}
```

**Exemplo de tratamento:**

```typescript
async function updateWebhook(webhookName: string, url: string) {
  try {
    const response = await fetch(`/api/webhooks/${webhookName}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ url })
    });

    const data = await response.json();

    if (!data.success) {
      throw new Error(data.error || 'Erro desconhecido');
    }

    return data;
  } catch (error) {
    console.error('Erro ao atualizar webhook:', error);
    throw error;
  }
}
```

---

## Notas Importantes

1. **Backup Automático**: Por padrão, todas as operações de escrita criam um backup automático antes de modificar o arquivo. Você pode desabilitar isso passando `create_backup: false`.

2. **Preservação de Ordem**: O sistema preserva a ordem das chaves no JSON, mantendo a estrutura original do arquivo.

3. **Validação de URL**: O frontend deve validar se a URL fornecida é uma URL válida antes de enviar para o backend.

4. **Limite de Backups**: O sistema mantém apenas os últimos 10 backups automaticamente. Backups mais antigos são removidos automaticamente.

5. **Não Permite Criar**: O sistema não permite criar novos webhooks. Apenas atualização de URLs de webhooks existentes é permitida. Novos webhooks devem ser criados pelo desenvolvimento.

6. **Não Permite Deletar**: O sistema não permite deletar webhooks. Apenas atualização de URLs é permitida para manter a estrutura padrão do arquivo.

7. **Teste de Webhooks**: Use `POST /api/webhooks/test` para testar uma URL antes de salvá-la, ou `POST /api/webhooks/<webhook_name>/test` para testar um webhook já configurado.

