# Player App (Gestão + SSM) - Autenticação e Arquitetura (Gestão NÃO é proxy)

Este documento é para o dev do **Gestão**. Ele descreve o fluxo recomendado de autenticação do Player App e a arquitetura onde o Gestão **não** faz proxy das chamadas de dados (o frontend chama o SSM diretamente).

---

## 1) Objetivo

- O **Gestão** é responsável por:
  - Login/cadastro do jogador
  - Disponibilizar a UI (telas) do Player App
  - Disponibilizar a lista de servidores (com `backend_base_url`)
- O **SSM Backend** é responsável por:
  - Segurança de acesso aos dados do servidor (wallet, shop, perfil no servidor)
  - Emissão de um token próprio do SSM para o jogador (Player JWT)
  - Servir os dados do jogador vinculados ao `steam_id`

---

## 2) Princípio de segurança (regra mais importante)

- O SSM **NUNCA** deve aceitar `steam_id` vindo do client como identificador do jogador.
- O `steam_id` deve sempre ser derivado de um token validado (exchange).

Isso evita que alguém tente acessar dados de outro jogador apenas trocando `steam_id` no request.

---

## 3) Arquitetura recomendada: Gestão NÃO é proxy

### O que isso significa

- O **Gestão não chama o SSM** para buscar dados de wallet/perfil.
- O Gestão apenas **serve as telas** (frontend) e **entrega metadados** (lista de servidores e `backend_base_url`).
- O **frontend** (rodando no navegador/app do jogador) chama o **SSM diretamente** usando o `backend_base_url`.

### Por que essa arquitetura

- Evita carga no Gestão (SSM vira a origem dos dados de jogo/servidor)
- Evita que o Gestão vire um gargalo/“single point of failure” de tráfego
- Mantém o SSM como autoridade de segurança dos endpoints `/api/player/*`

---

## 4) Fluxo de autenticação (Exchange) - visão geral

1. Jogador faz login no **Gestão** e obtém um `gestao_access_token` (Bearer token).
2. Frontend pede ao Gestão a lista de servidores.
3. Jogador seleciona um servidor (obtém `server_hash` e `backend_base_url`).
4. Frontend chama o SSM: `POST {backend_base_url}/api/player/auth/exchange`.
5. SSM valida o token do Gestão consultando um endpoint de identidade no Gestão.
6. SSM emite um **Player JWT** e devolve ao frontend.
7. Frontend usa o Player JWT nas chamadas seguintes ao SSM: `Authorization: Bearer <player_token>`.

---

## 5) Endpoints necessários do lado do Gestão

### 5.1 Listar servidores do jogador

- Endpoint sugerido:
  - `GET /api/player/servers`

- Resposta sugerida:

```json
{
  "success": true,
  "data": [
    {
      "server_hash": "<hash>",
      "server_name": "Meu Servidor",
      "backend_base_url": "http://<ip-ou-dominio>:3000",
      "backend_base_url_checked": true,
      "backend_base_url_source": "configured"
    }
  ]
}
```

Observação: o `backend_base_url` vem do sync do SSM (`server_info.backend_base_url`).

### 5.2 Endpoint de identidade do jogador (para o SSM validar token)

O SSM precisa conseguir, a partir do `gestao_access_token`, obter o `steam_id` do jogador.

- Endpoint recomendado:
  - `GET /api/v1/player/me`

- Request (SSM -> Gestão):
  - Header: `Authorization: Bearer <gestao_access_token>`

- Response mínima (Gestão -> SSM):

```json
{ "steam_id": "7656119..." }
```

O SSM também aceita este formato alternativo:

```json
{ "success": true, "data": { "steam_id": "7656119..." } }
```

---

## 6) Endpoints do lado do SSM (o que o Gestão/Frontend vai consumir)

### 6.1 Exchange

- `POST /api/player/auth/exchange`

Autenticação (enviar token do Gestão):
- Header: `Authorization: Bearer <gestao_access_token>`

Body (mínimo):

```json
{ "server_hash": "<server_hash>" }
```

Resposta:

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

### 6.2 Player-scoped endpoints

Depois do exchange, chamar o SSM com:
- `Authorization: Bearer <player_token>`
- `X-Server-Hash: <server_hash_do_servidor_selecionado>`

Endpoints iniciais implementados no SSM:
- `GET /api/player/me`
- `GET /api/player/wallet/balance`
- `GET /api/player/profile`
- `GET /api/player/survival-stats/snapshot`
- `GET /api/player/chests`
- `GET /api/player/chests/<entity_id>`
- `GET /api/player/chests/<entity_id>/inventory`
- `GET /api/player/chests/history`
- `GET /api/player/vehicles`
- `GET /api/player/vehicles/summary`
- `GET /api/player/vehicles/<vehicle_entity_id>`
- `GET /api/player/rankings?category=<categoria>&limit=<n>&offset=<n>`
- `GET /api/player/rankings/me?category=<categoria>`

Observação:
- O SSM valida que o `X-Server-Hash` enviado no request é igual ao `server_hash` gravado no `player_token`.
- Se faltar header, retorna `SERVER_HASH_REQUIRED`.
- Se for diferente, retorna `SERVER_HASH_MISMATCH`.

---

## 7) Observações operacionais

- O SSM resolve o endpoint de identidade do Gestão via:
  - `GESTAO_SERVER_URL` (hardcoded em `core/config/server_urls.py` para dev/prod)
  - `public.gestao_player_me_path` no `config.json` (default: `/api/v1/player/me`)

- O Player JWT expira conforme:
  - `public.player_jwt_expiration_hours` (default: 24)

---

## 8) Checklist de implementação (Gestão)

- Expor `GET /api/player/servers` com `backend_base_url` por servidor.
- Expor `GET /api/v1/player/me` retornando `steam_id` a partir do Bearer token do jogador.
- No frontend:
  - usar `backend_base_url` para chamar o SSM direto
  - fazer exchange e armazenar `player_token`
  - chamar endpoints `/api/player/*` do SSM com `Authorization: Bearer <player_token>`
