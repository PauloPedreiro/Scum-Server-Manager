# 🔌 Documentação da API - SSM 3.0 Frontend

Esta documentação descreve como o frontend interage com a API do backend SSM 3.0.

## 📡 Cliente API

O cliente HTTP está configurado em `src/services/server.ts` usando **Axios**.

### Configuração Base

```typescript
import axios from 'axios';
import configData from '../config.json';

const api = axios.create({
  baseURL: getApiBaseURL(), // Ex: http://192.168.100.3:3000/api
  timeout: configData?.backend?.timeout ?? 60000,
  headers: {
    'Content-Type': 'application/json'
  }
});
```

### Tratamento de Erros

O interceptor captura erros de conexão:

```typescript
api.interceptors.response.use(
  (r) => r,
  (e) => {
    if (e.code === 'ERR_NETWORK' || e.message?.includes('ERR_CONNECTION_REFUSED')) {
      const errorMsg = `Não foi possível conectar ao servidor backend...`;
      return Promise.reject(new Error(errorMsg));
    }
    return Promise.reject(e);
  }
);
```

---

## 🎮 Endpoints Utilizados

### Status do Servidor

#### `GET /api/server/status`
Obtém o status atual do servidor SCUM.

**Resposta:**
```typescript
interface ServerStatusResponse {
  success: boolean;
  data?: {
    install_path: string;
    is_running: boolean;
    last_check: number;
    max_players: number;
    port: number;
    service_info: {
      ESTADO?: string; // "4 RUNNING", "1 STOPPED", etc.
      // ... outros campos
    };
    service_name: string;
    use_battleye: boolean;
  };
  timestamp?: number;
  error?: string;
}
```

**Uso:**
```typescript
import { getServerStatus } from '@/services/server';

const status = await getServerStatus();
if (status.success && status.data) {
  console.log('Servidor rodando:', status.data.is_running);
}
```

---

### Controle do Servidor

#### `POST /api/server/start`
Inicia o servidor SCUM.

**Body (opcional):**
```json
{
  "force": false,
  "wait_timeout": 30
}
```

**Resposta:**
```typescript
interface ServerControlResponse {
  success: boolean;
  message?: string;
  status?: string;
  data?: any;
  final_status?: any;
  error?: string;
}
```

#### `POST /api/server/stop`
Para o servidor SCUM.

#### `POST /api/server/restart`
Reinicia o servidor SCUM.

**Uso:**
```typescript
import { startServer, stopServer, restartServer } from '@/services/server';

await startServer();
await stopServer();
await restartServer();
```

---

### Tempo do Servidor

#### `GET /api/weather/time`
Obtém o horário atual do servidor.

**Resposta:**
```typescript
interface ServerTimeResponse {
  success: boolean;
  data?: {
    is_running: boolean;
    last_sync: string;
    next_sync: string;
    server_time: string; // "10:30"
    sync_interval_minutes: number;
    time_of_day: number;
  };
  timestamp?: number;
  error?: string;
}
```

**Uso:**
```typescript
import { getServerTime } from '@/services/server';

const time = await getServerTime();
if (time.success && time.data) {
  console.log('Horário do servidor:', time.data.server_time);
}
```

---

### Players Online

#### `GET /api/players/online/stats`
Estatísticas de players online.

**Resposta:**
```typescript
interface PlayersOnlineStatsResponse {
  success: boolean;
  data?: {
    last_update: string;
    offline_count: number;
    online_count: number;
    total_tracked: number;
  };
}
```

#### `GET /api/players/online/list`
Lista de players online com detalhes.

**Resposta:**
```typescript
interface PlayersOnlineListResponse {
  success: boolean;
  data?: {
    count: number;
    players: Array<{
      player_id: number;
      player_name: string;
      steam_id: string;
      coordinates: { x: number; y: number; z: number };
      last_activity: string;
      steam_info: {
        avatar_url: string;
        persona_name: string;
        profile_url: string;
        // ... outros campos
      };
      activity_types: string[];
      total_activities: number;
    }>;
    timestamp: string;
  };
}
```

**Uso:**
```typescript
import { getPlayersOnlineStats, getPlayersOnlineList } from '@/services/server';

const stats = await getPlayersOnlineStats();
const onlineList = await getPlayersOnlineList();
```

---

### Todos os Players

#### `GET /api/players`
Lista todos os players (online e offline).

**Resposta:**
```typescript
interface AllPlayersResponse {
  success: boolean;
  data?: {
    count: number;
    limit: number | null;
    offset: number;
    players: Array<{
      player_id: number;
      player_name: string;
      steam_id: string;
      permissao: 0 | 1; // Permissão do comando /tm
      first_seen: string;
      last_seen: string;
      total_playtime: number;
      total_sessions: number;
      is_new_player: boolean;
      notification_sent: boolean;
      created_at: string;
    }>;
    total: number;
  };
}
```

**Uso:**
```typescript
import { getAllPlayers } from '@/services/server';

const allPlayers = await getAllPlayers();
```

---

### Logs de Players

#### `GET /api/logs/players?limit=100&offset=0`
Obtém logs e sessões ativas de players.

**Query Parameters:**
- `limit`: Número máximo de resultados (padrão: 100)
- `offset`: Offset para paginação (padrão: 0)

**Resposta:**
```typescript
interface PlayersLogsResponse {
  success: boolean;
  data?: {
    active_players: number;
    online_now: number;
    total_players: number;
    new_players: number;
    active_sessions: Array<{
      player_id: number;
      player_name: string;
      steam_id: string;
      login_time: string;
      duration: number;
    }>;
    top_players: Array<{
      player_name: string;
      total_playtime: number;
      total_sessions: number;
    }>;
  };
}
```

---

### Permissões

#### `GET /api/players/{steam_id}/permissions`
Lista todas as permissões de um player.

**Query Parameters:**
- `include_inactive`: boolean (padrão: false)

**Resposta:**
```typescript
interface PlayerPermissionsResponse {
  success: boolean;
  data?: {
    steam_id: string;
    player_name: string;
    permissions: Array<{
      id: number;
      permission_type: string; // "admin", "banned", etc.
      is_active: boolean | number; // true/false ou 1/0
      granted_by: string | null;
      granted_at: string | null;
      revoked_by: string | null;
      revoked_at: string | null;
      notes: string | null;
    }>;
    total_permissions: number;
    active_permissions: number;
    inactive_permissions: number;
  };
}
```

#### `POST /api/players/{steam_id}/permissions/{permission_type}/activate`
Ativa uma permissão para um player.

**Tipos de Permissão:**
- `admin` - Administrador
- `banned` - Banido
- `server_admin` - Admin do Servidor (Config)
- `silenced` - Silenciado
- `whitelisted` - Whitelist
- `exclusive` - Exclusivo (oculto na UI)

**Body (opcional):**
```json
{
  "granted_by": "admin",
  "notes": "Permissão concedida via painel"
}
```

#### `POST /api/players/{steam_id}/permissions/{permission_type}/deactivate`
Desativa uma permissão de um player.

**Body (opcional):**
```json
{
  "revoked_by": "admin",
  "notes": "Permissão revogada"
}
```

#### `PUT /api/players/{steam_id}/permissao`
Atualiza a permissão do comando `/tm` para um player.

**Body:**
```json
{
  "permissao": 1  // 0 = desativado, 1 = ativado
}
```

**Uso:**
```typescript
import { 
  getPlayerPermissions,
  activatePermission,
  deactivatePermission,
  updatePlayerPermissao
} from '@/services/server';

// Obter permissões
const perms = await getPlayerPermissions('76561198040636105', true);

// Ativar permissão
await activatePermission('76561198040636105', 'admin', 'admin', 'Nota opcional');

// Desativar permissão
await deactivatePermission('76561198040636105', 'admin', 'admin', 'Nota opcional');

// Atualizar permissão do /tm
await updatePlayerPermissao('76561198040636105', 1);
```

---

### Veículos

#### `GET /api/vehicles/player/{steam_id}/by-status`
Obtém veículos de um player específico, com opção de filtro por status.

**Parâmetros:**
- `steam_id` (path): Steam ID do player
- `status` (query, opcional): Filtro por status (0=Ativo, 1=Inativo, 2=Desaparecido, 3=Destruído). Pode ser múltiplos separados por vírgula.

**Resposta:**
```typescript
interface PlayerVehiclesResponse {
  success: boolean;
  data?: {
    steam_id: string;
    player_name: string;
    player_id: number;
    summary: {
      total_vehicles: number;
      by_status?: { [status: string]: number };
    };
    vehicles?: Vehicle[];
    vehicles_by_status?: { [status: string]: Vehicle[] };
  };
}
```

**Uso:**
```typescript
import { getPlayerVehiclesByStatus } from '@/services/server';

// Todos os veículos agrupados por status
const allVehicles = await getPlayerVehiclesByStatus('76561198040636105');

// Apenas veículos ativos
const activeVehicles = await getPlayerVehiclesByStatus('76561198040636105', '0');
```

#### `GET /api/vehicles/players`
Obtém todos os players que possuem veículos.

**Parâmetros Query (opcionais):**
- `status`: Filtro por status (0, 1, 2, 3 ou múltiplos separados por vírgula)
- `group_by_status`: Agrupar veículos por status (`true`/`false`)
- `limit`: Número máximo de players (padrão: 1000, máx: 10000)
- `offset`: Deslocamento para paginação

**Resposta:**
```typescript
interface AllPlayersVehiclesResponse {
  success: boolean;
  data?: {
    total_players: number;
    total_vehicles: number;
    players: Array<{
      steam_id: string;
      player_name: string;
      player_id: number;
      vehicles_count: number;
      vehicles?: Vehicle[];
      vehicles_by_status?: { [status: string]: Vehicle[] };
    }>;
  };
}
```

**Uso:**
```typescript
import { getAllPlayersVehicles } from '@/services/server';

// Players com veículos ativos
const playersWithActiveVehicles = await getAllPlayersVehicles('0');

// Players com veículos agrupados por status
const groupedVehicles = await getAllPlayersVehicles(undefined, true);
```

**Observações:**
- O endpoint `/api/vehicles/player/{steam_id}/by-status` retorna 404 quando o player não possui veículos (tratado como situação normal no frontend)
- Erros 404 para veículos são suprimidos do console do navegador

---

## Solicitação de Endpoint: Resumo de Veículos por Jogador

### Contexto
A tela de Players exibe, na tabela principal, a quantidade de veículos associados a cada jogador. O backend atualmente disponibiliza apenas o endpoint detalhado (`GET /api/vehicles/player/{steam_id}/by-status`), que retorna todos os veículos do jogador. Para mostrar o total diretamente na listagem sem carregar centenas de registros, precisamos de um endpoint leve que agregue as contagens.

### Requisito
Criar um endpoint paginado que devolva, para cada jogador listado, a contagem de veículos (total e, opcionalmente, por status). Esse endpoint será chamado em conjunto com `/api/players`, usando os mesmos parâmetros `limit` e `offset`, para preencher a coluna “Vehicles” sem buscar os detalhes completos.

### Proposta
```
GET /api/players/vehicles/summary
```

#### Parâmetros de Query
| Parâmetro | Tipo  | Obrigatório | Padrão | Descrição                                     |
|-----------|-------|-------------|--------|-----------------------------------------------|
| `limit`    | int    | não         | 10      | Quantidade de jogadores por página (1–100)    |
| `offset`   | int    | não         | 0       | Deslocamento para paginação (>= 0)            |
| `steam_id` | string | não         | —       | Filtra contagem para um jogador específico    |
| `sort_by`  | string | não         | `last_seen` | Campo de ordenação aplicado no backend        |
| `sort_order` | string (`asc`/`desc`) | não | `desc`  | Direção da ordenação                           |

> Observação: os parâmetros devem seguir a mesma regra do `/api/players` para manter sincronização de páginas.

#### Resposta (200)
```json
{
  "success": true,
  "data": {
    "count": 57,
    "limit": 10,
    "offset": 0,
    "total": 317,
    "sort_by": "last_seen",
    "sort_order": "desc",
    "summaries": [
      {
        "steam_id": "76561198040636105",
        "player_id": 230,
        "total": 4,
        "by_status": {
          "0": 3,
          "1": 1,
          "2": 0,
          "3": 0
        },
        "updated_at": "2025-11-10T01:30:00Z"
      }
    ]
  }
}
```

#### Campos
- `success`: indica sucesso da requisição.
- `data.count`: quantidade de registros retornados nesta página.
- `data.limit / data.offset`: replicam os parâmetros recebidos.
- `data.total`: total de jogadores considerados (equivalente ao `/api/players`).
- `data.sort_by` / `data.sort_order`: metadados indicando a ordenação aplicada pelo backend.
- `data.summaries`: lista com um item por jogador na página atual.
  - `steam_id`: identificador do jogador.
  - `player_id`: identificador interno do jogador.
  - `total`: quantidade total de veículos associados.
  - `by_status`: objeto com contagens por status (0 = ativo, 1 = inativo, 2 = desaparecido, 3 = destruído).
  - `updated_at`: timestamp para garantir rastreabilidade (opcional).

#### Erros
| Código | Resposta                                      | Quando ocorre                           |
|--------|-----------------------------------------------|------------------------------------------|
| 500    | `{ "success": false, "error": "mensagem" }` | Falha na consulta ao banco (`SSM.db`).   |

### Uso no Frontend
O frontend chamará `/api/players` e `/api/players/vehicles/summary` com os mesmos parâmetros `limit` e `offset`. Ao renderizar a tabela, usará `summaries.total` para preencher a coluna “Vehicles” de cada jogador sem acionar o endpoint detalhado até que o usuário abra a aba "Veículos".

### Observações
- Manter o endpoint protegido pelas mesmas regras de autenticação já utilizadas no `/api/players`.
- A consulta pode ser feita com `LEFT JOIN`/subquery agregando a tabela de veículos (`player_vehicle_snapshot`) filtrada pelo snapshot vigente.
- Caso não haja veículos para um jogador, retornar `total: 0` e `by_status` vazio.

---

## Solicitação de Ajuste: Ordenação Global por Veículos

### Contexto
Na página de Players, a coluna "Veículos" exibe o total retornado pelo endpoint `/api/players/vehicles/summary`. Atualmente, aplicamos paginação (ex.: 10 jogadores por página) e apenas reordenamos os dados localmente. Quando o usuário ordena pelo cabeçalho, a ordenação acontece somente dentro da página atual: os jogadores com maior número de veículos podem estar em outra página e não aparecem no topo.

### Necessidade
Permitir que o frontend solicite a ordenação global no backend, garantindo que a resposta já venha ordenada considerando **todos** os jogadores. Assim, ao ordenar pela quantidade de veículos (descendente), os maiores valores surgem na primeira página.

### Requisito
Garantir que a ordenação global por quantidade de veículos seja suportada de forma consistente entre `/api/players` e `/api/players/vehicles/summary`, utilizando os parâmetros já expostos `sort_by` e `sort_order`:

- `sort_by`: deve aceitar ao menos `"vehicles_total"` (além de opções existentes como `"player_name"`, `"last_seen"`, etc.)
- `sort_order`: `asc` ou `desc`

Exemplo de chamada esperada:
```
GET /api/players?limit=10&offset=0&sort_by=vehicles_total&sort_order=desc
GET /api/players/vehicles/summary?limit=10&offset=0&sort_by=vehicles_total&sort_order=desc
```

> Atualização (2025-11-11): o endpoint `/api/players/vehicles/summary` já responde com os metadados `sort_by` e `sort_order`. Precisamos apenas confirmar o suporte ao campo `vehicles_total` e replicar a mesma ordenação no `/api/players` para manter a lista sincronizada.

### Resposta Esperada
- Manter os campos atuais (`limit`, `offset`, `total`, `count`, `summaries`, `sort_by`, `sort_order`).
- Se `sort_by` não for informado, manter o comportamento atual (ordenar por `last_seen` ou padrão existente).

### Tratamento de Erros
Caso o backend receba um `sort_by` inválido, responder:
```json
{
  "success": false,
  "error": "Sort field 'vehicles_total' is not supported"
}
```

### Uso no Frontend
1. O componente de Players envia `sort_by`/`sort_order` nos dois endpoints.
2. A tabela é renderizada na ordem já pronta — a coluna “Veículos” aparecerá com os valores ordenados globalmente.
3. A paginação permanece funcional: navegar para pagina 2/3 traz o próximo conjunto mais alto ou mais baixo, conforme o `sort_order`.

### Observações
- Caso seja preferível, o backend pode expor a ordenação apenas no `vehicles/summary`, desde que `/api/players` retorne os jogadores no mesmo `steam_id` + `offset`. Ou seja, usar `steam_id` como chave para sincronizar as duas respostas.
- Para evitar impacto de performance, considerar índices ou uma consulta agregada eficiente (`ORDER BY total DESC LIMIT ?, ?`).

---

## ⚙️ Configurações (Settings)

### ServerSettings.ini

#### `GET /api/server-settings/{section}`
Obtém configurações de uma seção específica do ServerSettings.ini.

**Parâmetros:**
- `section` (path): Nome da seção (General, World, Respawn, Vehicles, Damage, Features)

**Resposta:**
```typescript
interface ServerSettingsResponse {
  success: boolean;
  data?: {
    section: string;
    fields: Record<string, any>;
    total_fields: number;
  };
  error?: string;
}
```

#### `PUT /api/server-settings/{section}`
Atualiza configurações de uma seção.

**Body:**
```json
{
  "fields": {
    "scum.ServerName": "Meu Servidor",
    "scum.MaxPlayers": 50
  }
}
```

#### `POST /api/server-settings/{section}/fields`
Adiciona um campo customizado à seção.

**Body:**
```json
{
  "key": "scum.CustomField",
  "value": "valor"
}
```

#### `DELETE /api/server-settings/{section}/fields/{key}`
Remove um campo customizado.

**Uso:**
```typescript
import { getServerSettings, updateServerSettings } from '@/services/settings';

const settings = await getServerSettings('General');
await updateServerSettings('General', { 'scum.MaxPlayers': 50 });
```

### Config.json

#### `GET /api/config/{section}`
Obtém uma seção específica do config.json.

**Parâmetros:**
- `section` (path): Nome da seção (server, updates, weather_scheduler, etc.)

**Resposta:**
```typescript
interface ConfigSectionResponse {
  success: boolean;
  data?: {
    section: string;
    fields: Record<string, any>;
    requires_restart?: boolean;
  };
  error?: string;
}
```

#### `PUT /api/config/{section}`
Atualiza uma seção do config.json.

**Body:**
```json
{
  "fields": {
    "enabled": true,
    "auto_start": false
  }
}
```

#### `GET /api/config/backups`
Lista backups disponíveis do config.json.

**Resposta:**
```typescript
interface ConfigBackupsResponse {
  success: boolean;
  data?: Array<{
    filename: string;
    created_at: string;
    size: number;
  }>;
}
```

#### `POST /api/config/backups/{filename}/restore`
Restaura um backup do config.json.

**Uso:**
```typescript
import { getConfigSection, updateConfigSection, getConfigBackups } from '@/services/config';

const section = await getConfigSection('server');
await updateConfigSection('server', { port: 3000 });
const backups = await getConfigBackups();
```

### Discord Webhooks

#### `GET /api/webhooks`
Lista todos os webhooks configurados.

**Resposta:**
```typescript
interface WebhooksResponse {
  success: boolean;
  data?: Record<string, string>; // { webhook_name: url }
  error?: string;
}
```

#### `GET /api/webhooks/names`
Lista nomes de webhooks disponíveis.

**Resposta:**
```typescript
interface WebhookNamesResponse {
  success: boolean;
  data?: {
    webhooks: string[];
  };
}
```

#### `PUT /api/webhooks/{name}`
Atualiza a URL de um webhook.

**Body:**
```json
{
  "url": "https://discord.com/api/webhooks/...",
  "create_backup": true
}
```

#### `POST /api/webhooks/{name}/test`
Testa um webhook configurado.

**Resposta:**
```typescript
interface TestWebhookResponse {
  success: boolean;
  message?: string;
  error?: string;
}
```

#### `POST /api/webhooks/test-url`
Testa uma URL antes de salvar.

**Body:**
```json
{
  "url": "https://discord.com/api/webhooks/..."
}
```

**Uso:**
```typescript
import { 
  getWebhooks, 
  getWebhookNames, 
  updateWebhook, 
  testWebhook 
} from '@/services/webhooks';

const webhooks = await getWebhooks();
const names = await getWebhookNames();
await updateWebhook('serverstatus', 'https://discord.com/api/webhooks/...');
await testWebhook('serverstatus');
```

---

## 🔄 Polling e Atualização Automática

O frontend utiliza polling para manter os dados atualizados:

### Home Page
- **Status do Servidor**: Atualiza a cada 30 segundos
- **Horário do Servidor**: Atualiza a cada 30 segundos
- **Players Online**: Atualiza a cada 10 segundos

### Players Page
- **Lista de Players**: Atualiza a cada 15 segundos
- **Permissões**: Recarregadas após cada modificação

### Server Page
- **Status do Servidor**: Atualiza a cada 30 segundos

---

## ⚠️ Tratamento de Erros

### Erros de Conexão

```typescript
try {
  const data = await getServerStatus();
} catch (error) {
  if (error.message.includes('ERR_CONNECTION_REFUSED')) {
    // Backend não está rodando
    console.error('Backend não está acessível');
  }
}
```

### Erros HTTP

```typescript
try {
  await activatePermission(steamId, 'admin');
} catch (error: any) {
  if (error.response?.status === 400) {
    // Bad Request - permissão já ativa, etc.
    const errorText = error.response.data.error;
  } else if (error.response?.status === 404) {
    // Not Found - player não encontrado
  } else if (error.response?.status === 500) {
    // Erro interno do servidor
  }
}
```

---

## 📊 Interfaces TypeScript

Todas as interfaces estão definidas em `src/services/server.ts`:

```typescript
// Exportadas
export interface ServerStatusData { ... }
export interface ServerStatusResponse { ... }
export interface ServerTimeData { ... }
export interface PlayersOnlineListData { ... }
export interface AllPlayer { ... }
export interface PlayerPermissionsData { ... }
export type PermissionType = 'admin' | 'banned' | 'server_admin' | 'silenced' | 'whitelisted';
```

---

## 🔐 Autenticação

Atualmente, o frontend não implementa autenticação. Todas as requisições são públicas.

**Futuro**: Autenticação via JWT ou tokens pode ser adicionada.

---

## 📝 Exemplo Completo

```typescript
import { 
  getServerStatus,
  getPlayersOnlineList,
  getAllPlayers,
  getPlayerPermissions,
  activatePermission
} from '@/services/server';

// Buscar status
const status = await getServerStatus();
if (status.success) {
  console.log('Servidor:', status.data?.is_running ? 'Online' : 'Offline');
}

// Buscar players
const [onlinePlayers, allPlayers] = await Promise.all([
  getPlayersOnlineList(),
  getAllPlayers()
]);

// Buscar e ativar permissão
const permissions = await getPlayerPermissions('76561198040636105');
if (permissions.success && permissions.data) {
  const hasAdmin = permissions.data.permissions.some(
    p => p.permission_type === 'admin' && p.is_active
  );
  
  if (!hasAdmin) {
    await activatePermission('76561198040636105', 'admin');
  }
}
```

---

## 📚 Referências

- [Documentação Principal](./README.md)
- [Guia de Configuração](./CONFIGURACAO.md)
- Documentação do Backend SSM 3.0

---

**Última atualização**: 2025-12-03

