# 🔐 Exemplos de Uso - Sistema de Permissões

## Configuração Inicial

Antes de usar os endpoints, certifique-se de que:
1. O backend está rodando na porta 3000
2. O banco de dados SSM.db está configurado
3. Os caminhos dos arquivos INI estão corretos no `config.json`

## Exemplos com cURL

### 1. Ativar Permissão de Administrador

```bash
curl -X POST "http://localhost:3000/api/players/76561198040636105/permissions/admin/activate" \
  -H "Content-Type: application/json" \
  -d '{
    "granted_by": "admin",
    "notes": "Promovido a administrador do servidor"
  }'
```

**Resposta esperada:**
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
    "notes": "Promovido a administrador do servidor",
    "ini_file_updated": true,
    "ini_file_path": "C:\\Servers\\scum\\SCUM\\Saved\\Config\\WindowsServer\\AdminUsers.ini"
  }
}
```

### 2. Ativar Múltiplas Permissões

```bash
# Ativar permissão de administrador
curl -X POST "http://localhost:3000/api/players/76561198040636105/permissions/admin/activate" \
  -H "Content-Type: application/json" \
  -d '{"granted_by": "admin", "notes": "Admin principal"}'

# Ativar permissão de server admin
curl -X POST "http://localhost:3000/api/players/76561198040636105/permissions/server_admin/activate" \
  -H "Content-Type: application/json" \
  -d '{"granted_by": "admin", "notes": "Admin de configurações"}'

# Ativar whitelist
curl -X POST "http://localhost:3000/api/players/76561198040636105/permissions/whitelisted/activate" \
  -H "Content-Type: application/json" \
  -d '{"granted_by": "admin", "notes": "Jogador VIP"}'
```

### 2.1. Ativar Permissão DB-only (\`raid_webhook_manage\`)

Essa permissão permite o jogador utilizar o comando `/sd` para cadastrar/remover webhook pessoal de alertas de raid.

Observação:

- Esta permissão é **DB-only** (não atualiza arquivos INI)
- A resposta virá com `ini_file_updated: null` e `ini_file_path: null`

```bash
curl -X POST "http://localhost:3000/api/players/76561198040636105/permissions/raid_webhook_manage/activate" \
  -H "Content-Type: application/json" \
  -d '{
    "granted_by": "admin",
    "notes": "Permite usar /sd para webhook pessoal"
  }'
```

### 3. Desativar Permissão

```bash
curl -X POST "http://localhost:3000/api/players/76561198040636105/permissions/admin/deactivate" \
  -H "Content-Type: application/json" \
  -d '{
    "revoked_by": "admin",
    "notes": "Permissão revogada por violação das regras"
  }'
```

### 3.0. Desativar novamente (NO-OP idempotente)

Se a permissão já estiver inativa e você chamar o endpoint novamente, ele retorna **200 OK** com `success: true`.

```bash
curl -X POST "http://localhost:3000/api/players/76561198040636105/permissions/admin/deactivate" \
  -H "Content-Type: application/json" \
  -d '{
    "revoked_by": "admin",
    "notes": "Chamada repetida (no-op)"
  }'
```

### 3.1. Desativar Permissão DB-only (\`raid_webhook_manage\`)

```bash
curl -X POST "http://localhost:3000/api/players/76561198040636105/permissions/raid_webhook_manage/deactivate" \
  -H "Content-Type: application/json" \
  -d '{
    "revoked_by": "admin",
    "notes": "Removido acesso ao /sd"
  }'
```

### 3.1.1. Desativar DB-only novamente (NO-OP idempotente)

```bash
curl -X POST "http://localhost:3000/api/players/76561198040636105/permissions/raid_webhook_manage/deactivate" \
  -H "Content-Type: application/json" \
  -d '{
    "revoked_by": "admin",
    "notes": "Chamada repetida (no-op)"
  }'
```

## Checklist de verificação pós-deploy (toggle idempotente)

- Testar `activate` para permissão já ativa e confirmar:
  - HTTP 200
  - `success: true`
  - `data.is_active: true`
- Testar `deactivate` para permissão já inativa e confirmar:
  - HTTP 200
  - `success: true`
  - `data.is_active: false`
- Repetir para múltiplos tipos:
  - `admin`, `banned`, `server_admin`, `silenced`, `whitelisted`, `raid_webhook_manage`

### 4. Listar Permissões de um Jogador

```bash
curl -X GET "http://localhost:3000/api/players/76561198040636105/permissions"
```

**Resposta esperada:**
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
        "notes": "Admin principal"
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
    "active_permissions": 2
  }
}
```

### 5. Obter Estatísticas Gerais

```bash
curl -X GET "http://localhost:3000/api/permissions/stats"
```

### 6. Listar Tipos de Permissão Disponíveis

```bash
curl -X GET "http://localhost:3000/api/permissions/types"
```

### 7. Listar Jogadores com Permissão Específica

```bash
# Listar todos os administradores
curl -X GET "http://localhost:3000/api/permissions/by-type/admin"

# Listar todos os jogadores banidos
curl -X GET "http://localhost:3000/api/permissions/by-type/banned"

# Listar todos os jogadores na whitelist
curl -X GET "http://localhost:3000/api/permissions/by-type/whitelisted"
```

### 8. Sincronizar Arquivos INI

```bash
curl -X POST "http://localhost:3000/api/permissions/sync-ini-files"
```

**Resposta esperada:**
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

## Exemplos com PowerShell (Windows)

### 1. Ativar Permissão

```powershell
$headers = @{
    "Content-Type" = "application/json"
}

$body = @{
    granted_by = "admin"
    notes = "Permissão de administrador concedida"
} | ConvertTo-Json

Invoke-RestMethod -Uri "http://localhost:3000/api/players/76561198040636105/permissions/admin/activate" -Method POST -Headers $headers -Body $body
```

### 2. Listar Permissões

```powershell
Invoke-RestMethod -Uri "http://localhost:3000/api/players/76561198040636105/permissions" -Method GET
```

### 3. Obter Estatísticas

```powershell
Invoke-RestMethod -Uri "http://localhost:3000/api/permissions/stats" -Method GET
```

## Exemplos com Python

### 1. Script para Ativar Permissão

```python
import requests
import json

def activate_permission(steam_id, permission_type, granted_by, notes):
    url = f"http://localhost:3000/api/players/{steam_id}/permissions/{permission_type}/activate"
    
    data = {
        "granted_by": granted_by,
        "notes": notes
    }
    
    response = requests.post(url, json=data)
    return response.json()

# Exemplo de uso
result = activate_permission(
    steam_id="76561198040636105",
    permission_type="admin",
    granted_by="admin",
    notes="Promovido a administrador"
)

print(json.dumps(result, indent=2))
```

### 2. Script para Listar Todas as Permissões

```python
import requests

def get_player_permissions(steam_id):
    url = f"http://localhost:3000/api/players/{steam_id}/permissions"
    response = requests.get(url)
    return response.json()

# Exemplo de uso
permissions = get_player_permissions("76561198040636105")
print(f"Jogador: {permissions['data']['player_name']}")
print(f"Total de permissões: {permissions['data']['total_permissions']}")

for perm in permissions['data']['permissions']:
    status = "Ativa" if perm['is_active'] else "Inativa"
    print(f"- {perm['permission_type']}: {status}")
```

### 3. Script para Sincronizar Arquivos INI

```python
import requests

def sync_ini_files():
    url = "http://localhost:3000/api/permissions/sync-ini-files"
    response = requests.post(url)
    return response.json()

# Exemplo de uso
result = sync_ini_files()
print(f"Arquivos atualizados: {result['data']['files_updated']}")
print(f"Permissões sincronizadas: {result['data']['total_permissions_synced']}")
```

## Casos de Uso Comuns

### 1. Promover Jogador a Administrador

```bash
# 1. Verificar se o jogador existe
curl -X GET "http://localhost:3000/api/players/76561198040636105/permissions"

# 2. Ativar permissão de admin
curl -X POST "http://localhost:3000/api/players/76561198040636105/permissions/admin/activate" \
  -H "Content-Type: application/json" \
  -d '{"granted_by": "admin", "notes": "Promovido a administrador"}'

# 3. Verificar se foi ativada
curl -X GET "http://localhost:3000/api/players/76561198040636105/permissions"
```

### 2. Banir Jogador

```bash
# 1. Ativar permissão de banido
curl -X POST "http://localhost:3000/api/players/76561198040636105/permissions/banned/activate" \
  -H "Content-Type: application/json" \
  -d '{"granted_by": "admin", "notes": "Banido por hacking"}'

# 2. Verificar lista de banidos
curl -X GET "http://localhost:3000/api/permissions/by-type/banned"
```

### 3. Adicionar à Whitelist

```bash
# 1. Ativar whitelist
curl -X POST "http://localhost:3000/api/players/76561198040636105/permissions/whitelisted/activate" \
  -H "Content-Type: application/json" \
  -d '{"granted_by": "admin", "notes": "Jogador VIP"}'

# 2. Verificar whitelist
curl -X GET "http://localhost:3000/api/permissions/by-type/whitelisted"
```

### 4. Remover Todas as Permissões

```bash
# 1. Listar permissões ativas
curl -X GET "http://localhost:3000/api/players/76561198040636105/permissions"

# 2. Desativar cada permissão ativa
curl -X POST "http://localhost:3000/api/players/76561198040636105/permissions/admin/deactivate" \
  -H "Content-Type: application/json" \
  -d '{"revoked_by": "admin", "notes": "Todas as permissões removidas"}'

curl -X POST "http://localhost:3000/api/players/76561198040636105/permissions/server_admin/deactivate" \
  -H "Content-Type: application/json" \
  -d '{"revoked_by": "admin", "notes": "Todas as permissões removidas"}'
```

## Verificação de Arquivos INI

Após ativar/desativar permissões, você pode verificar os arquivos INI:

### Windows
```cmd
type "C:\Servers\scum\SCUM\Saved\Config\WindowsServer\AdminUsers.ini"
type "C:\Servers\scum\SCUM\Saved\Config\WindowsServer\BannedUsers.ini"
```

### Linux/Mac
```bash
cat "/path/to/SCUM/Saved/Config/WindowsServer/AdminUsers.ini"
cat "/path/to/SCUM/Saved/Config/WindowsServer/BannedUsers.ini"
```

## Troubleshooting

### Erro: Jogador não encontrado
```bash
# Verificar se o jogador existe na tabela players
curl -X GET "http://localhost:3000/api/logs/players?limit=100"
```

### Erro: Permissão já ativa
```bash
# Verificar permissões atuais
curl -X GET "http://localhost:3000/api/players/76561198040636105/permissions"
```

### Erro: Arquivo INI não atualizado
```bash
# Forçar sincronização
curl -X POST "http://localhost:3000/api/permissions/sync-ini-files"
```
