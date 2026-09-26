# Bank (Admin) - API para Frontend (Gestão)

Este documento descreve os endpoints **admin** para consulta de saldos bancários (Money e Gold) no backend.

## Autenticação

Todos os endpoints abaixo exigem:

- Header `Authorization: Bearer <JWT>`
- Usuário com role `admin`

### Login (obter token)

- **POST** `/api/auth/login`
- Body (JSON):

```json
{
  "username": "admin",
  "password": "..."
}
```

- Resposta (exemplo):

```json
{
  "success": true,
  "data": {
    "token": "<jwt>",
    "expires_in": 86400,
    "role": "admin",
    "username": "admin"
  }
}
```

No Postman, a collection já está configurada para salvar automaticamente o token em `{{token}}` após o login.

## Convenções de valores

- `money_in_hand`: dinheiro em mãos
- `money_in_bank`: dinheiro no banco
- `money_total`: total de money (em mãos + banco)
- `gold`: saldo de gold (separado de money)

## Endpoint 1: Consultar saldo de 1 jogador (por SteamID)

- **GET** `/api/shop/admin/bank-account/current?steam_id=<steam_id>`

### Query params

- `steam_id` (obrigatório)

### Resposta (exemplo)

```json
{
  "success": true,
  "data": {
    "steam_id": "76561198040636105",
    "account_number": "712603000001",
    "balances": {
      "money_in_hand": 813,
      "money_in_bank": 0,
      "money_total": 813,
      "gold": 0
    },
    "meta": {
      "has_data": true,
      "updated_at": "2026-03-12 00:10:57",
      "source": "scum_db_reconcile",
      "last_transaction_ts": "2026.02.20-18.01.25"
    }
  },
  "timestamp": 1773271188.9035263
}
```

### Quando não existir registro

Retorna `success=true` com `meta.has_data=false` e saldos zerados.

## Endpoint 2: Listar saldos de todos (paginação + busca)

- **GET** `/api/shop/admin/bank-accounts/current`

### Objetivo

- Listar **todos** os jogadores com saldo atual.
- Ordenação padrão (fixa):
  - `money_total DESC`
  - `gold DESC`
  - depois `updated_at DESC`

### Query params

- `limit` (opcional)
  - default: `50`
  - max: `200`
- `offset` (opcional)
  - default: `0`
- `q` (opcional)
  - Busca por:
    - `steam_id` (prefixo)
    - `player_name` (contém)

### Exemplos de uso

- Top 50 (mais ricos):
  - `/api/shop/admin/bank-accounts/current?limit=50&offset=0`

- Página 2:
  - `/api/shop/admin/bank-accounts/current?limit=50&offset=50`

- Buscar por SteamID (prefixo):
  - `/api/shop/admin/bank-accounts/current?q=7656119`

- Buscar por nome:
  - `/api/shop/admin/bank-accounts/current?q=pedr`

### Resposta (exemplo)

```json
{
  "success": true,
  "data": {
    "items": [
      {
        "steam_id": "76561198040636105",
        "player_name": "Pedreiro",
        "account_number": "712603000001",
        "balances": {
          "money_in_hand": 813,
          "money_in_bank": 0,
          "money_total": 813,
          "gold": 0
        },
        "meta": {
          "updated_at": "2026-03-12 00:10:57",
          "source": "scum_db_reconcile",
          "last_transaction_ts": "2026.02.20-18.01.25"
        }
      }
    ],
    "count": 1,
    "total": 1,
    "limit": 50,
    "offset": 0,
    "has_more": false
  },
  "timestamp": 1773274474.0696096
}
```

## Recomendações para implementação no frontend

- Paginação:
  - Usar `limit` fixo (ex: 50)
  - Controlar `offset`
  - Usar `data.has_more` para habilitar/desabilitar “Próxima página”

- Busca:
  - Implementar debounce (ex: 300–500ms) ao digitar
  - Ao mudar `q`, resetar `offset=0`

- Tratamento de erros:
  - `401 AUTH_REQUIRED`: token ausente/expirado
  - `403` (quando aplicável): usuário sem role admin
  - `500`: erro interno

## Postman

A collection está em `docs/endpoints/postman-collection.json`, pasta **Bank**, com as requests:

- `GET /api/shop/admin/bank-account/current?steam_id={{steamId}}`
- `GET /api/shop/admin/bank-accounts/current?limit=50&offset=0&q=`
