# Player App - Baús (SSM)

Este documento descreve os endpoints **player-scoped** para o controle de baús do jogador no SSM.

Os dados vêm do `SSM.db` (tabelas `chest_snapshot` e `chest_history`), alimentados pelo `ChestSyncService`.

---

## 1) Autenticação e headers obrigatórios

Todos os endpoints abaixo exigem:

- `Authorization: Bearer <player_token>`
- `X-Server-Hash: <server_hash_do_servidor_selecionado>`

Regras:

- O `steam_id` é derivado do `player_token`.
- O SSM valida que o `X-Server-Hash` do request é igual ao `server_hash` embutido no token.

---

## 2) Listar meus baús

### Endpoint

- Método: `GET`
- Path: `/api/player/chests`

### Query params

- `minimal` (opcional): `true|false`
  - `true`: retorna payload reduzido (recomendado para lista)
  - `false`: retorna payload completo (inclui veículo etc.)
- `limit` (opcional): inteiro (máx 1000)
- `offset` (opcional): inteiro

### Resposta (HTTP 200)

```json
{
  "success": true,
  "data": {
    "steam_id": "...",
    "count": 1,
    "type_counts": {"Wooden": 1},
    "player_names": ["..."],
    "fake_names": [],
    "chests": [
      {
        "entity_id": 123,
        "chest_type": "Wooden",
        "custom_name": "...",
        "location": {"x": 0, "y": 0, "z": 0},
        "has_vehicle": false,
        "vehicle_owner_mismatch": false,
        "last_seen_at": "..."
      }
    ],
    "limit": 200,
    "offset": 0,
    "total": 1
  },
  "timestamp": 0
}
```

Observações:

- `count` é o número de baús retornados na página atual.
- `total` só aparece quando `limit`/`offset` são usados.

---

## 3) Detalhar 1 baú (somente se for do jogador)

### Endpoint

- Método: `GET`
- Path: `/api/player/chests/<entity_id>`

### Respostas

- HTTP 200: retorna o baú (formato completo, como no painel).
- HTTP 404: se o `entity_id` não existir **ou** não pertencer ao jogador autenticado.

Erro 404:

```json
{ "success": false, "error": "CHEST_NOT_FOUND" }
```

---

## 3.1) Inventário do baú (somente se for do jogador)

### Endpoint

- Método: `GET`
- Path: `/api/player/chests/<entity_id>/inventory`

### Observação

- Este endpoint lê o inventário diretamente do `SCUM.db` (usando a cópia compartilhada) via `entity_component` + `entity_inventory_component_entry`.
- O SSM também persiste um snapshot em `SSM.db` nas tabelas:
  - `chest_inventory_snapshot`
  - `chest_inventory_item`

### Respostas

- HTTP 200: retorna o inventário.
- HTTP 404: `CHEST_NOT_FOUND` se o baú não existir no `SSM.db` ou não pertencer ao jogador.
- HTTP 404: `CHEST_NOT_FOUND_SCUMDB` se o baú não existir no `SCUM.db`.

Exemplo (HTTP 200):

```json
{
  "success": true,
  "data": {
    "chest_entity_id": 123,
    "steam_id": "...",
    "player_name": "...",
    "scanned_at": "...",
    "items_total": 2,
    "counts": {
      "SomeItemClass": 2
    },
    "items": [
      {
        "item_entity_id": 456,
        "item_class": "SomeItemClass",
        "slot_index": 0
      }
    ]
  },
  "timestamp": 0
}
```

---

## 4) Histórico dos meus baús

### Endpoint

- Método: `GET`
- Path: `/api/player/chests/history`

### Query params

- `limit` (opcional): inteiro (máx 500, default 50)
- `offset` (opcional): inteiro
- `event_type` (opcional): filtra por tipo (ex: `created`, `destroyed`, `owner_changed`, `moved`, `renamed`, etc.)

### Resposta (HTTP 200)

```json
{
  "success": true,
  "data": {
    "steam_id": "...",
    "events": [
      {
        "id": 1,
        "entity_id": 123,
        "event_type": "created",
        "custom_name": "...",
        "chest_class": "...",
        "chest_type": "Wooden",
        "location": {"x": 0, "y": 0, "z": 0},
        "vehicle_owner_mismatch": false,
        "details": {},
        "event_at": "..."
      }
    ],
    "total": 1,
    "limit": 50,
    "offset": 0,
    "count": 1
  },
  "timestamp": 0
}
```

Notas:

- `details` vem do campo `details_json` do `chest_history`.
- Se `details_json` não for JSON válido, o SSM retorna o valor bruto como string.

---

## 5) Erros comuns

### 5.1 Sem Authorization

- HTTP `401`

```json
{ "success": false, "error": "AUTH_REQUIRED" }
```

### 5.2 Token inválido/expirado

- HTTP `401`

```json
{ "success": false, "error": "INVALID_TOKEN" }
```

### 5.3 Sem X-Server-Hash

- HTTP `400`

```json
{ "success": false, "error": "SERVER_HASH_REQUIRED" }
```

### 5.4 X-Server-Hash diferente do token

- HTTP `403`

```json
{ "success": false, "error": "SERVER_HASH_MISMATCH" }
```
