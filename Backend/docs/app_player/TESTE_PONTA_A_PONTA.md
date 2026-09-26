# Player App - Guia de Teste (Gestão Frontend -> SSM)

Este guia é para você e para o dev do Gestão validarem o fluxo completo do Player App após o exchange.

---

## 1) Pré-requisitos

- **Gestão** rodando (dev) em `http://localhost:8000`
- **SSM Backend** rodando em `http://127.0.0.1:3000`
- No SSM, confirmar que `data/config.json` contém:

```json
"public": {
  "backend_base_url_enabled": true,
  "backend_base_url": "http://127.0.0.1:3000",
  "gestao_player_me_path": "/api/v1/player/me",
  "player_jwt_expiration_hours": 24
}
```

- No Gestão, confirmar que existe um endpoint de identidade do jogador:
  - `GET /api/v1/player/me`
  - Header: `Authorization: Bearer <gestao_access_token>`
  - Resposta mínima:

```json
{ "steam_id": "7656119..." }
```

(SSM também aceita `{ "success": true, "data": { "steam_id": "..." } }`)

---

## 2) Fluxo que será testado

1. Jogador faz login no **Gestão**.
2. Gestão/Frontend obtém lista de servidores (inclui `server_hash` e `backend_base_url`).
3. Frontend chama o **SSM** para fazer o exchange do token do Gestão por um token do SSM.
4. Com o `player_token`, o Frontend chama endpoints `/api/player/*` do SSM.

Observação: o Gestão **não deve ser proxy** do tráfego de dados do SSM. O browser/app chama o SSM direto.

---

## 3) Teste 1 - Exchange (Gestão -> SSM)

### Request

- URL:
  - `POST {backend_base_url}/api/player/auth/exchange`

- Autenticação (token do Gestão):
  - Header: `Authorization: Bearer <gestao_access_token>`

- Body:

```json
{ "server_hash": "<server_hash_do_servidor_selecionado>" }
```

### Resposta esperada (SSM)

- HTTP 200

```json
{
  "success": true,
  "data": {
    "player_token": "<jwt>",
    "token_type": "Bearer",
    "steam_id": "7656119...",
    "server_hash": "<server_hash>"
  }
}
```

### Falhas esperadas

- Sem `server_hash`:
  - HTTP 400 `SERVER_HASH_REQUIRED`
- Token do Gestão inválido:
  - HTTP 401 `GESTAO_TOKEN_INVALID`
- Gestão fora do ar (ou endpoint não responde):
  - HTTP 401 `GESTAO_UNREACHABLE`

---

## 4) Teste 2 - Validar token do SSM (GET /api/player/me)

### Request

- URL:
  - `GET {backend_base_url}/api/player/me`
- Header:
  - `Authorization: Bearer <player_token>`
  - `X-Server-Hash: <server_hash_do_servidor_selecionado>`

### Resposta esperada

- HTTP 200

```json
{
  "success": true,
  "data": {
    "steam_id": "7656119...",
    "server_hash": "<server_hash>"
  }
}
```

---

## 5) Teste 3 - Wallet balance (GET /api/player/wallet/balance)

### Request

- URL:
  - `GET {backend_base_url}/api/player/wallet/balance`
- Header:
  - `Authorization: Bearer <player_token>`
  - `X-Server-Hash: <server_hash_do_servidor_selecionado>`

### Resposta esperada

- HTTP 200

```json
{
  "success": true,
  "data": {
    "balance": 0
  }
}
```

Observação: se existir registro na tabela `wallet`, o `balance` vem com o valor real.

---

## 5.1) Teste 4 - Rankings (leaderboard)

### Request

- URL:
  - `GET {backend_base_url}/api/player/rankings?category=kills&limit=20&offset=0`
- Header:
  - `Authorization: Bearer <player_token>`
  - `X-Server-Hash: <server_hash_do_servidor_selecionado>`

### Resposta esperada

- HTTP 200

```json
{
  "success": true,
  "data": {
    "category": "kills",
    "order_column": "kills",
    "rankings": [
      {
        "rank": 1,
        "steam_id": "...",
        "player_name": "...",
        "value": 123,
        "last_updated": "..."
      }
    ],
    "total": 100,
    "limit": 20,
    "offset": 0
  },
  "timestamp": 0
}
```

### Categorias disponíveis

O endpoint aceita, por exemplo:
- `kills`
- `deaths`
- `kdr`
- `longest_shot`
- `fame`
- `headshots`
- `survival_time`

Se enviar uma categoria inválida, retorna HTTP 400 `INVALID_CATEGORY` com `available_categories`.

---

## 5.2) Teste 5 - Meu ranking (por categoria)

### Request

- URL:
  - `GET {backend_base_url}/api/player/rankings/me?category=kills`
- Header:
  - `Authorization: Bearer <player_token>`
  - `X-Server-Hash: <server_hash_do_servidor_selecionado>`

### Resposta esperada

- HTTP 200

```json
{
  "success": true,
  "data": {
    "steam_id": "...",
    "player_name": "...",
    "category": "kills",
    "value": 10,
    "approx_rank": 42,
    "last_updated": "..."
  },
  "timestamp": 0
}
```

Se não existir linha do jogador na tabela `rankings`, retorna `data: null`.

---

## 5.3) Teste 6 - Survival stats snapshot (GET /api/player/survival-stats/snapshot)

### Request

- URL:
  - `GET {backend_base_url}/api/player/survival-stats/snapshot`
- Header:
  - `Authorization: Bearer <player_token>`
  - `X-Server-Hash: <server_hash_do_servidor_selecionado>`

### Resposta esperada

- HTTP 200

```json
{
  "success": true,
  "data": {
    "steam_id": "...",
    "player_name": "...",
    "user_profile_id": 0,
    "snapshot_at": "...",
    "metrics": {
      "kills": 0,
      "deaths": 0
    },
    "derived": {
      "kdr": 0,
      "accuracy_percent": null
    }
  },
  "timestamp": 0
}
```

Se não existir linha do jogador na tabela `survival_stats_snapshot`, retorna `data: null`.

---

## 5.4) Teste 7 - Listar meus baús (GET /api/player/chests)

### Request

- URL:
  - `GET {backend_base_url}/api/player/chests?minimal=true&limit=200&offset=0`
- Header:
  - `Authorization: Bearer <player_token>`
  - `X-Server-Hash: <server_hash_do_servidor_selecionado>`

### Resposta esperada

- HTTP 200

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

---

## 5.5) Teste 8 - Detalhar 1 baú (GET /api/player/chests/<entity_id>)

### Request

- URL:
  - `GET {backend_base_url}/api/player/chests/123`
- Header:
  - `Authorization: Bearer <player_token>`
  - `X-Server-Hash: <server_hash_do_servidor_selecionado>`

### Resposta esperada

- HTTP 200 se o baú pertencer ao jogador.
- HTTP 404 `CHEST_NOT_FOUND` se o `entity_id` não existir ou não pertencer ao jogador.

---

## 5.5.1) Teste 8.1 - Inventário de 1 baú (GET /api/player/chests/<entity_id>/inventory)

### Request

- URL:
  - `GET {backend_base_url}/api/player/chests/123/inventory`
- Header:
  - `Authorization: Bearer <player_token>`
  - `X-Server-Hash: <server_hash_do_servidor_selecionado>`

### Resposta esperada

- HTTP 200 se o baú pertencer ao jogador.
- HTTP 404 `CHEST_NOT_FOUND` se o baú não existir no snapshot do SSM ou não pertencer ao jogador.
- HTTP 404 `CHEST_NOT_FOUND_SCUMDB` se o baú não existir no SCUM.db.

---

## 5.6) Teste 9 - Histórico dos meus baús (GET /api/player/chests/history)

### Request

- URL:
  - `GET {backend_base_url}/api/player/chests/history?limit=50&offset=0`
- Header:
  - `Authorization: Bearer <player_token>`
  - `X-Server-Hash: <server_hash_do_servidor_selecionado>`

### Resposta esperada

- HTTP 200

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

Opcional:
- Filtrar por tipo de evento: `?event_type=created`

---

## 6) Testes de segurança (obrigatórios)

### 6.1 Sem token do SSM

- `GET /api/player/me` sem header `Authorization`
- Esperado:
  - HTTP 401 `AUTH_REQUIRED`

### 6.2 Sem X-Server-Hash

- `GET /api/player/me` sem header `X-Server-Hash`
- Esperado:
  - HTTP 400 `SERVER_HASH_REQUIRED`

### 6.3 Token do SSM adulterado

- Alterar 1 caractere do `player_token`
- Esperado:
  - HTTP 401 `INVALID_TOKEN`

### 6.4 X-Server-Hash diferente do token

- Usar um `player_token` gerado para `server_hash=A` e chamar endpoint com `X-Server-Hash=B`
- Esperado:
  - HTTP 403 `SERVER_HASH_MISMATCH`

### 6.5 Persistência de sessão (frontend)

- Recarregar a página do player app
- Esperado:
  - Frontend ainda possui `player_token` (session/local storage)
  - Chamada automática para `/api/player/me` funciona sem novo exchange

---

## 7) Checklist de logs para debug

Se algo falhar, coletar:

- No browser (DevTools -> Network):
  - Request/Response do `POST /api/player/auth/exchange`
  - Request/Response do `GET /api/player/me`
  - Request/Response do `GET /api/player/wallet/balance`

- No SSM (logs):
  - mensagens de erro do exchange (ex: `GESTAO_UNREACHABLE`, `GESTAO_HTTP_ERROR`)

---

## 8) Observações importantes

- O SSM não aceita `steam_id` vindo do client. Ele deriva o `steam_id` através do token validado no exchange.
- O `player_token` é um token do SSM (aud=`player`) e deve ser usado apenas para consumir `/api/player/*`.
