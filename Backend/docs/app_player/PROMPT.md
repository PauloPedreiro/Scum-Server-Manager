# Prompt - App Player (SSM Backend + Gestão)

Use este prompt como base para qualquer trabalho futuro relacionado ao **App Player** (Player App).

---

## Contexto

- O projeto é um backend **Python/Flask** rodando em Windows, em produção, usando **SQLite**.
- Existe um sistema externo chamado **Gestão** que:
  - autentica/cadastra jogadores (Steam)
  - mantém licenças/servidores (com `server_hash`)
  - lista servidores para o jogador selecionar
- O Player App deve permitir **acesso individual** (um jogador só acessa seus próprios dados).

---

## Regras de segurança (obrigatórias)

- Nunca expor a **API key do servidor** (licensing/gestão) no Player App.
- Endpoints `/api/player/*`:
  - nunca aceitar `steam_id` vindo do cliente para definir escopo
  - sempre derivar `steam_id` do token (claim `sub`)
- Autenticação do Player App deve ser separada da autenticação do painel/admin.
- Token do Player deve ser **amarrado ao servidor** via `server_hash` para evitar reutilização em outro servidor.

---

## Identidade do jogador no SSM

- O SSM **não usa `discord_id`**.
- A identidade mínima é **`steam_id`**.

---

## Fluxo de autenticação (design)

### Descoberta de servidores (no Gestão)

- O Gestão retorna lista de servidores com:
  - `server_hash`
  - `backend_base_url`

O Player App chama diretamente:

- `{backend_base_url}/api/player/...`

### Exchange (SSM)

- Endpoint: `POST /api/player/auth/exchange`
- Entrada: `gestao_access_token` (ou equivalente)
- O SSM consulta o Gestão para resolver identidade e obter `steam_id`
- O SSM emite um **Player JWT** local.

### Player JWT (claims)

- `sub`: `steam_id`
- `aud`: `player`
- `server_hash`: binding do servidor
- `exp`, `iat`

---

## Endpoints Player (mínimo acordado)

- `GET /api/player/me`
- `GET /api/player/wallet/balance`

Próximos planejados:

- `GET /api/player/wallet/transactions?limit=&offset=`
- `GET /api/player/shop/catalog`
- `POST /api/player/shop/orders`
- `GET /api/player/mailbox`
- `PUT /api/player/mailbox`

---

## Descoberta e envio do backend_base_url (via sync)

O SSM envia o `backend_base_url` dentro de `server_info` no **sync de 4 em 4 horas** (mesmo payload de rankings), para o Gestão armazenar por `server_hash`.

### Campos em `server_info`

- `backend_base_url`
- `backend_base_url_source`: `configured | detected`
- `backend_base_url_checked`: `true | false`

### Prioridade para `backend_base_url`

1. Se existir `config.public.backend_base_url`, usar esse valor.
   - source = `configured`
2. Senão, detectar IP externo via serviço público "what is my IP" e montar:
   - `http://{ip}:3000`
   - source = `detected`
3. `checked`:
   - `true` se `GET {backend_base_url}/api/health` responder 200 (timeout curto)
   - `false` caso contrário

Regras operacionais:

- timeout curto no check (2-3s)
- cache do IP e do check
- falhas de detecção/check **não podem** quebrar o sync

---

## SQLite (produção)

- Evitar transações longas.
- Preferir WAL + busy_timeout + retries em operações concorrentes.

---

## Referência

- Documento de fluxo: `docs/app_player/FLUXO_E_CONTRATOS.md`
