# App Player (SSM) - Fluxo e Contratos (raciocínio)

Este documento consolida o raciocínio e as decisões para suportar um **aplicativo do jogador** (Player App) integrado ao **SSM Backend** (Flask) e ao sistema externo **Gestão**.

## Objetivos

- Permitir que um jogador acesse **somente seus próprios dados** (escopo individual).
- Manter compatibilidade com o backend em produção.
- Evitar expor credenciais do servidor (API key de licença) no Player App.
- Permitir que o Gestão descubra qual URL do backend deve ser usada pelo Player App (**backend_base_url**).

---

## Componentes e responsabilidades

### Gestão

- Autentica/identifica o jogador e mantém o cadastro de identidades externas (Steam).
- Mostra ao jogador uma lista de servidores.
- Armazena o `backend_base_url` por servidor (chaveado por `server_hash`).

### SSM Backend

- Continua responsável pelos dados locais do servidor (SQLite).
- Emite um token local de Player (JWT) para o Player App.
- Fornece endpoints `/api/player/*` escopados por jogador.
- Envia periodicamente dados para o Gestão (sync de rankings etc.) e **inclui** `backend_base_url` no payload.

### Player App

- Não conhece API keys do servidor.
- Obtém a lista de servidores pelo Gestão.
- Chama o SSM Backend usando `backend_base_url`.

---

## Identidade do jogador no SSM

- O SSM **não usa `discord_id`**.
- A identidade mínima para dados no SSM é **`steam_id`**.

---

## Autenticação Player App (token local do SSM)

### Decisão

- O Player App não envia `steam_id` para acessar dados.
- O SSM emite um **JWT separado** do JWT admin/painel.
- O JWT do Player é **amarrado ao servidor** via `server_hash` para evitar reutilização em outro servidor.

### Claims recomendadas (Player JWT)

- `sub`: `steam_id`
- `aud`: `player`
- `server_hash`: hash do servidor (binding)
- `exp`, `iat`

> Observação: `discord_id` não é incluído porque o SSM não trabalha com isso.

---

## Fluxo: descoberta do servidor (server list)

1. O Player App chama o **Gestão** para listar servidores do jogador.
2. O Gestão retorna, por servidor:
   - `server_hash`
   - `server_name` (opcional)
   - `backend_base_url` (ex.: `http://177.3.52.227:3000`)
   - `backend_base_url_checked` (opcional)

O Player App passa a chamar o SSM diretamente usando `backend_base_url`.

---

## Fluxo: login do jogador no servidor (exchange)

### Endpoint (SSM)

- **POST** `/api/player/auth/exchange`

### Entrada (Player App -> SSM)

- `gestao_access_token` (ou equivalente)

### Passo interno (SSM -> Gestão)

O SSM valida/resolve a identidade do jogador junto ao Gestão, para obter ao menos:

- `steam_id`

### Saída (SSM -> Player App)

- `token` (Player JWT do SSM)
- `expires_in`
- `steam_id`
- `server_hash`

---

## Endpoints do Player App no SSM (escopados)

Todos exigem:

- Header `Authorization: Bearer <player_jwt>`

### Regra de ouro (escopo individual)

- Nenhum endpoint `/api/player/*` aceita `steam_id` via `body`/`query` para definir acesso.
- O `steam_id` vem sempre do token (`sub`).

### Endpoints iniciais (mínimo)

- **GET** `/api/player/me`
  - Retorna dados derivados do token: `steam_id`, `server_hash`.

- **GET** `/api/player/wallet/balance`
  - Retorna o saldo da carteira para o `steam_id` do token.

### Próximos (planejados)

- Wallet:
  - **GET** `/api/player/wallet/transactions?limit=&offset=`

- Shop:
  - **GET** `/api/player/shop/catalog`
  - **POST** `/api/player/shop/orders`

- Mailbox:
  - **GET** `/api/player/mailbox`
  - **PUT** `/api/player/mailbox` (ex.: atualizar chest)

---

## Como o Gestão descobre o `backend_base_url`

### Decisão: enviar via sync de 4 em 4 horas

Como o SSM já envia rankings a cada 4 horas, será incluído no mesmo payload de sync:

- `server_info.backend_base_url`
- `server_info.backend_base_url_source`
- `server_info.backend_base_url_checked`

### `backend_base_url` - prioridade

1. Se existir `config.public.backend_base_url` no SSM, usar isso.
   - `backend_base_url_source = "configured"`

2. Senão, o SSM detecta IP externo (via serviço público tipo "meu ip") e monta:
   - `http://{ip}:3000`
   - `backend_base_url_source = "detected"`

3. Se detecção falhar:
   - usar valor cacheado, se existir; senão, omitir `backend_base_url` no payload.

### `backend_base_url_checked`

- `true` quando o SSM conseguir confirmar que a URL responde (ex.: `GET {backend_base_url}/api/health` com HTTP 200).
- `false` caso contrário.

Regras para não impactar produção:

- timeout curto (2-3s)
- cache do resultado (evitar checagem a cada sync se não necessário)
- nunca falhar o sync por causa do healthcheck

---

## Observações de produção (resumo)

- A liberação/encaminhamento da porta é responsabilidade do administrador do servidor.
- Mesmo com IP detectado, se a porta não estiver aberta, o Player App não conseguirá acessar.

---

## Pendências (para quando for implementar)

- Definir com o dev do Gestão:
  - contrato exato do endpoint de identidade do jogador usado no exchange (ex.: `/api/v1/player/me`).
  - contrato exato do payload do `/api/v1/servers/sync` para incluir `server_info.backend_base_url*`.
- Implementar endpoints `/api/player/*` no backend com JWT separado.
- Implementar detecção de IP externo + cache + healthcheck.
