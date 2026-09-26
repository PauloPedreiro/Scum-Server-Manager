# 🔐 Sistema de Permissões de Jogadores

## Visão Geral

O Sistema de Permissões de Jogadores permite gerenciar diferentes tipos de permissões para jogadores do servidor SCUM, sincronizando automaticamente com os arquivos de configuração `.ini` do servidor.

## Funcionalidades

- ✅ **Ativação/Desativação de Permissões**: Controle granular de permissões por jogador
- ✅ **Sincronização Automática**: Atualização instantânea dos arquivos `.ini` do servidor
- ✅ **Múltiplas Permissões**: Um jogador pode ter várias permissões simultaneamente
- ✅ **Auditoria Completa**: Histórico de todas as alterações de permissões
- ✅ **Validação de Dados**: Verificação de integridade e consistência

## Tipos de Permissão

| Tipo | Nome | Arquivo INI | Formato | Descrição |
|------|------|-------------|---------|-----------|
| `admin` | Administrador | `AdminUsers.ini` | `{steam_id}[setgodmode]` | Permissões de administrador do servidor |
| `banned` | Banido | `BannedUsers.ini` | `{steam_id}` | Jogador banido do servidor |
| `exclusive` | Exclusivo | `ExclusiveUsers.ini` | `{steam_id}` | Acesso exclusivo ao servidor |
| `server_admin` | Admin do Servidor | `ServerSettingsAdminUsers.ini` | `{steam_id}` | Administrador das configurações |
| `silenced` | Silenciado | `SilencedUsers.ini` | `{steam_id}` | Jogador silenciado no chat |
| `whitelisted` | Whitelist | `WhitelistedUsers.ini` | `{steam_id}` | Jogador na lista branca |

## Estrutura do Banco de Dados

### Tabela `player_permissions`

```sql
CREATE TABLE player_permissions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    steam_id TEXT NOT NULL,
    permission_type TEXT NOT NULL,
    is_active BOOLEAN DEFAULT 1,
    granted_by TEXT,
    granted_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    revoked_by TEXT,
    revoked_at DATETIME,
    notes TEXT,
    FOREIGN KEY (steam_id) REFERENCES players (steam_id)
);
```

### Índices

```sql
CREATE INDEX idx_player_permissions_steam_id ON player_permissions(steam_id);
CREATE INDEX idx_player_permissions_type ON player_permissions(permission_type);
CREATE INDEX idx_player_permissions_active ON player_permissions(is_active);
CREATE INDEX idx_player_permissions_granted_at ON player_permissions(granted_at);
```

## Endpoints da API

### 1. Ativar Permissão

**POST** `/api/players/{steam_id}/permissions/{permission_type}/activate`

Ativa uma permissão específica para um jogador.

**Parâmetros:**
- `steam_id` (path): Steam ID do jogador
- `permission_type` (path): Tipo da permissão (admin, banned, exclusive, etc.)

**Body:**
```json
{
  "granted_by": "admin",
  "notes": "Permissão de administrador concedida"
}
```

**Resposta de Sucesso (200):**
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

### 2. Desativar Permissão

**POST** `/api/players/{steam_id}/permissions/{permission_type}/deactivate`

Desativa uma permissão específica para um jogador.

**Parâmetros:**
- `steam_id` (path): Steam ID do jogador
- `permission_type` (path): Tipo da permissão

**Body:**
```json
{
  "revoked_by": "admin",
  "notes": "Permissão revogada por violação das regras"
}
```

**Resposta de Sucesso (200):**
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

### 3. Listar Permissões do Jogador

**GET** `/api/players/{steam_id}/permissions`

Lista todas as permissões de um jogador específico.

**Parâmetros:**
- `steam_id` (path): Steam ID do jogador

**Resposta de Sucesso (200):**
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
      }
    ],
    "total_permissions": 1,
    "active_permissions": 1
  }
}
```

### 4. Estatísticas de Permissões

**GET** `/api/permissions/stats`

Obtém estatísticas gerais do sistema de permissões.

**Resposta de Sucesso (200):**
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

### 5. Sincronizar Arquivos INI

**POST** `/api/permissions/sync-ini-files`

Sincroniza todos os arquivos INI com as permissões do banco de dados.

**Resposta de Sucesso (200):**
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

### 6. Listar Tipos de Permissão

**GET** `/api/permissions/types`

Lista todos os tipos de permissão disponíveis.

**Resposta de Sucesso (200):**
```json
{
  "success": true,
  "data": {
    "permission_types": [
      {
        "type": "admin",
        "name": "Administrador",
        "description": "Permissões de administrador do servidor",
        "ini_file": "AdminUsers.ini",
        "format": "{steam_id}[setgodmode]"
      }
    ],
    "total_types": 6
  }
}
```

### 7. Listar Permissões por Tipo

**GET** `/api/permissions/by-type/{permission_type}`

Lista todos os jogadores com um tipo específico de permissão.

**Parâmetros:**
- `permission_type` (path): Tipo da permissão

**Resposta de Sucesso (200):**
```json
{
  "success": true,
  "data": {
    "permission_type": "admin",
    "players": [
      {
        "steam_id": "76561198040636105",
        "player_name": "Pedreiro",
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

## Códigos de Erro

| Código | Descrição |
|--------|-----------|
| 400 | Bad Request - Dados inválidos ou permissão já ativa/inativa |
| 404 | Not Found - Jogador ou tipo de permissão não encontrado |
| 500 | Internal Server Error - Erro interno do servidor |

## Exemplos de Uso

### Exemplo 1: Ativar Permissão de Administrador

```bash
curl -X POST "http://localhost:3000/api/players/76561198040636105/permissions/admin/activate" \
  -H "Content-Type: application/json" \
  -d '{
    "granted_by": "admin",
    "notes": "Promovido a administrador"
  }'
```

### Exemplo 2: Listar Todas as Permissões de um Jogador

```bash
curl -X GET "http://localhost:3000/api/players/76561198040636105/permissions"
```

### Exemplo 3: Sincronizar Arquivos INI

```bash
curl -X POST "http://localhost:3000/api/permissions/sync-ini-files"
```

## Arquivos de Configuração

O sistema trabalha com os seguintes arquivos INI do servidor SCUM:

- `C:\Servers\scum\SCUM\Saved\Config\WindowsServer\AdminUsers.ini`
- `C:\Servers\scum\SCUM\Saved\Config\WindowsServer\BannedUsers.ini`
- `C:\Servers\scum\SCUM\Saved\Config\WindowsServer\ExclusiveUsers.ini`
- `C:\Servers\scum\SCUM\Saved\Config\WindowsServer\ServerSettingsAdminUsers.ini`
- `C:\Servers\scum\SCUM\Saved\Config\WindowsServer\SilencedUsers.ini`
- `C:\Servers\scum\SCUM\Saved\Config\WindowsServer\WhitelistedUsers.ini`

## Segurança

- **Validação de Dados**: Verificação de integridade antes de aplicar mudanças
- **Logs de Auditoria**: Todas as operações são registradas nos logs do sistema
- **Transações Atômicas**: Operações de banco de dados são executadas em transações

## Monitoramento

O sistema registra todas as operações nos logs do backend:

```
[INFO] Permissão 'admin' ativada para jogador 76561198040636105
[INFO] Arquivo AdminUsers.ini atualizado com sucesso
```

## Troubleshooting

### Problema: Arquivo INI não é atualizado

**Solução:**
1. Verificar se o caminho do servidor está correto no `config.json`
2. Verificar permissões de escrita na pasta de configuração
3. Executar sincronização manual via API

### Problema: Jogador não encontrado

**Solução:**
1. Verificar se o Steam ID está correto
2. Verificar se o jogador existe na tabela `players`
3. Verificar se o jogador já foi registrado no sistema

### Problema: Permissão já ativa/inativa

**Solução:**
1. Verificar status atual da permissão
2. Usar endpoint de desativação antes de reativar
3. Verificar logs para entender o estado atual

## Integração com Frontend

O sistema foi projetado para integração com frontend futuro:

- **Lista de Jogadores**: Endpoint para buscar todos os jogadores
- **Controles de Permissão**: Botões para ativar/desativar cada permissão
- **Status em Tempo Real**: Atualização automática do status das permissões
- **Histórico de Alterações**: Visualização do histórico de mudanças

## Próximos Passos

- [ ] Interface web para gerenciamento de permissões
- [ ] Notificações Discord para mudanças de permissões
- [ ] Relatórios de permissões por período
- [ ] Integração com sistema de logs de administração
- [ ] API para importação/exportação de permissões
