# 🛒 Shop / Economy / Mailbox - API Endpoints

Base URL:
```
http://localhost:3000
```

Autenticação (quando requerido):
```
Authorization: Bearer <token>
Content-Type: application/json
```

---

## Admin

### `POST /api/shop/admin/credit`
Crédito administrativo idempotente (ex: PIX, compra externa). Se o mesmo `external_id` for enviado novamente, o crédito não será duplicado.

**Body**
```json
{
  "external_id": "PIX_ABC123",
  "steam_id": "76561198012345678",
  "amount": 100,
  "meta": {"provider": "pix"}
}
```

**200**
```json
{
  "success": true,
  "already_applied": false,
  "steam_id": "76561198012345678",
  "amount": 100,
  "balance": 100
}
```

**Erros comuns**
- `400`: campos obrigatórios ausentes / `amount` inválido

---

### `GET /api/shop/admin/rewards/playtime-config`
Consulta configurações do reward automático de pontos por tempo jogado.

**200**
```json
{
  "success": true,
  "data": {
    "enabled": 0,
    "points_per_hour": 10,
    "max_hours_per_run": 24,
    "interval_minutes": 30,
    "baseline_mode": "lazy"
  }
}
```

---

### `PATCH /api/shop/admin/rewards/playtime-config`
Atualiza configurações do reward automático de pontos por tempo jogado (admin).

**Body (campos opcionais)**
```json
{
  "enabled": 1,
  "points_per_hour": 10,
  "max_hours_per_run": 24
}
```

**200**
Mesmo formato do endpoint de consulta.

**Erros comuns**
- `400`: campo inválido (`enabled` deve ser 0/1; valores devem ser inteiros e >= 0)

---

### `GET /api/shop/admin/rewards/playtime-rules`
Lista regras de reward por tempo jogado.

**Observação (exclusividade / substituição)**
Se um jogador estiver elegível para qualquer regra com `exclusive=1`, ele **não recebe** as regras com `exclusive=0` (ex: regra padrão `audience_type="all"`).

**Campos da regra (para UI Admin / Frontend)**
- **`enabled`**: `0|1` (liga/desliga a regra)
- **`exclusive`**: `0|1`
  - `1` = modo *substituição* (quem cair em uma regra exclusiva não recebe regras não-exclusivas)
- **`audience_type`**:
  - `all` = aplica para todos os jogadores
  - `list` = aplica apenas para steam_ids cadastrados nos targets da regra
- **`points_per_hour`**: pontos creditados por hora jogada
- **`max_hours_per_run`**: máximo de horas pagas por execução do scheduler (0 = sem limite)

**Configuração recomendada (Padrão + VIP substituição)**
- **[Padrão]** `audience_type="all"`, `exclusive=0`, `enabled=1`
- **[VIP]** `audience_type="list"`, `exclusive=1`, `enabled=1` + targets com os steam_ids VIP

Resultado:
- Jogador VIP recebe **somente VIP**
- Jogador não-VIP recebe **somente Padrão**

**Query (opcional)**
```
enabled_only=1
```

**200**
```json
{
  "success": true,
  "data": {
    "items": [
      {
        "rule_id": "...",
        "name": "VIP",
        "enabled": 1,
        "exclusive": 1,
        "points_per_hour": 10,
        "max_hours_per_run": 24,
        "audience_type": "list"
      }
    ],
    "count": 1
  }
}
```

---

### `POST /api/shop/admin/rewards/playtime-rules`
Cria uma regra de reward por tempo jogado.

**Body**
```json
{
  "name": "VIP",
  "enabled": 1,
  "exclusive": 1,
  "points_per_hour": 10,
  "max_hours_per_run": 24,
  "audience_type": "list"
}
```

**201**
```json
{ "success": true, "data": {"rule_id": "..."} }
```

---

### `PATCH /api/shop/admin/rewards/playtime-rules/<rule_id>`
Atualiza uma regra existente.

**Body (campos opcionais)**
```json
{
  "enabled": 0,
  "points_per_hour": 5
}
```

**Erros comuns**
- `404`: `RULE_NOT_FOUND`

---

### `DELETE /api/shop/admin/rewards/playtime-rules/<rule_id>`
Remove uma regra (também remove estados e targets via cascade).

---

### `GET /api/shop/admin/rewards/playtime-rules/<rule_id>/targets`
Lista os jogadores (steam_id) incluídos na regra quando `audience_type="list"`.

**200**
```json
{
  "success": true,
  "data": {
    "rule_id": "...",
    "items": ["7656119..."],
    "count": 1
  }
}
```

---

### `POST /api/shop/admin/rewards/playtime-rules/<rule_id>/targets`
Adiciona um jogador (steam_id) à lista da regra.

**Body**
```json
{ "steam_id": "76561198012345678" }
```

---

### `DELETE /api/shop/admin/rewards/playtime-rules/<rule_id>/targets/<steam_id>`
Remove um jogador da lista da regra.

---

### `POST /api/shop/admin/wallet/adjust`
Ajuste manual de saldo (delta positivo ou negativo). Endpoint pensado para a UI Admin.

- Idempotente via `external_id` (por `steam_id + reason + ref_type + ref_id`).
- `delta` pode ser positivo (crédito) ou negativo (débito).

**Body**
```json
{
  "external_id": "ADJ_ABC123",
  "steam_id": "76561198012345678",
  "delta": -50,
  "reason": "admin_adjust",
  "meta": {"note": "chargeback"}
}
```

**200**
```json
{
  "success": true,
  "already_applied": false,
  "steam_id": "76561198012345678",
  "delta": -50,
  "balance": 950
}
```

**Erros comuns**
- `409`: `INSUFFICIENT_FUNDS` (se delta negativo ultrapassar o saldo)
- `400`: campos inválidos / ausentes

---

### `POST /api/shop/admin/scanner-chest`
Define o chest (baú) que será usado como **scanner** de catálogo.

**Body**
```json
{ "chest_id": 60008 }
```

**200**
```json
{ "success": true, "chest_id": 60008 }
```

---

### `POST /api/shop/admin/scanner/sync`
Sincroniza itens do chest scanner (SCUM.db) para o catálogo (SSM.db).

- Cria entrada em `shop_catalog` para cada `entity.class` encontrado.
- Cria `shop_offer` correspondente (desabilitada por padrão).

**Body**
```json
{}
```

**200**
```json
{
  "success": true,
  "data": {
    "chest_id": 60008,
    "discovered_setups": 12,
    "created_catalog": 3
  }
}
```

---

### `POST /api/shop/orders/<order_id>/retry`
Marca retry para pedidos falhados.

**200**
```json
{ "success": true, "retry_requested": true, "order_id": "..." }
```

---

### `POST /api/shop/delivery/run`
Executa o job offline de entrega manualmente.

**Body**
```json
{ "limit": 50 }
```

**200**
```json
{
  "success": true,
  "data": {
    "processed_orders": 2,
    "delivered_orders": 1,
    "failed_orders": 1
  }
}
```

---

## Auth

### `POST /api/shop/mailbox`
Registra / atualiza o mailbox do jogador (`steam_id -> chest_id`).

**Body**
```json
{ "steam_id": "76561198012345678", "chest_id": 60008 }
```

**200**
```json
{
  "success": true,
  "message": "Mailbox atualizado. Entregas so aparecem apos restart.",
  "data": {"steam_id": "76561198012345678", "chest_id": 60008}
}
```

---

### `GET /api/shop/mailbox`
Lista jogadores com mailbox registrado (tabela `player_mailbox`).

Requer autenticação.

**Query (opcional)**
```
limit=100
offset=0
```

**200**
```json
{
  "success": true,
  "data": {
    "items": [
      {
        "steam_id": "7656119...",
        "player_name": "Player",
        "chest_id": 123,
        "created_at": "2026-02-07 03:00:00",
        "updated_at": "2026-02-07 03:10:00"
      }
    ],
    "total": 1,
    "count": 1,
    "limit": 100,
    "offset": 0
  }
}
```

---

### `POST /api/shop/orders`
Cria um pedido. O saldo é debitado no momento da criação do pedido.

**Body**
```json
{
  "steam_id": "76561198012345678",
  "items": [
    {"code": 1, "qty": 2},
    {"code": 5, "qty": 1}
  ]
}
```

**200**
```json
{
  "success": true,
  "data": {
    "order_id": "...",
    "total_price": 150,
    "balance": 850
  }
}
```

**Erros comuns**
- `400`: `MAILBOX_NOT_REGISTERED`, `OFFER_DISABLED:<code>`, `OFFER_NOT_AVAILABLE:<code>`
- `409`: `INSUFFICIENT_FUNDS`

---

### `GET /api/shop/catalog`
Lista o catálogo **visível** para compra no frontend. Retorna apenas itens com:

- `shop_catalog.enabled = 1`
- `shop_offer.enabled = 1`

**200**
```json
{
  "success": true,
  "data": {
    "items": [
      {
        "code": 1,
        "setup": "2H_Axe_ES",
        "name": "2H Axe",
        "price": 100,
        "qty": 1,
        "max_per_order": 5,
        "max_per_day": null
      }
    ],
    "count": 1
  }
}
```

---

### `GET /api/shop/wallet/balance`
Consulta saldo da wallet.

- Usuário comum: consulta o **próprio** saldo (steam_id vindo do token).
- Admin: pode consultar saldo de outro jogador via query `steam_id`.

**Query (opcional para admin)**
```
steam_id=76561198012345678
```

**200**
```json
{
  "success": true,
  "data": {
    "steam_id": "76561198012345678",
    "balance": 1000
  }
}
```

---

### `GET /api/shop/wallet/transactions`
Lista as últimas movimentações do jogador (extrato). Retorna lançamentos de `wallet_tx`.

**Query (opcional)**
```
limit=50
```

**200**
```json
{
  "success": true,
  "data": {
    "steam_id": "76561198012345678",
    "items": [
      {
        "tx_id": "...",
        "delta": -100,
        "reason": "shop_purchase",
        "ref_type": "order",
        "ref_id": "...",
        "meta": {"order_id": "..."},
        "created_at": "2026-02-06 22:10:00"
      }
    ],
    "count": 1
  }
}
```

---

### `GET /api/shop/admin/wallet/transactions`
Lista movimentações de um jogador específico (admin).

**Query (obrigatório + opcional)**
```
steam_id=76561198012345678
limit=100
```

**200**
Mesmo formato do endpoint do usuário.

### `GET /api/shop/admin/catalog`
Lista o catálogo completo para administração, incluindo itens desativados.

- Inclui status do catálogo e da oferta (`catalog_enabled`, `offer_enabled`)

**200**
```json
{
  "success": true,
  "data": {
    "items": [
      {
        "code": 1,
        "setup": "2H_Axe_ES",
        "name": "2H Axe",
        "catalog_enabled": true,
        "offer_enabled": false,
        "price": 100,
        "qty": 1,
        "max_per_order": 5,
        "max_per_day": null
      }
    ],
    "count": 1
  }
}
```

---

### `PATCH /api/shop/admin/catalog/<code>`
Atualiza um item do catálogo/oferta por `code`. Endpoint pensado para a UI Admin (edição por item).

Permite:

- Toggle do catálogo: `catalog_enabled`
- Toggle da oferta: `offer_enabled`
- Renomear no frontend: `display_name` (o campo retornado como `name` usa `display_name` quando preenchido)
- Alterar oferta: `price`, `qty`, `max_per_order`, `max_per_day`

**Body (todos os campos são opcionais)**
```json
{
  "display_name": "2H Axe",
  "catalog_enabled": true,
  "offer_enabled": true,
  "price": 100,
  "qty": 1,
  "max_per_order": 5,
  "max_per_day": null
}
```

**200**
```json
{
  "success": true,
  "data": {
    "item": {
      "code": 1,
      "setup": "2H_Axe_ES",
      "name": "2H Axe",
      "catalog_enabled": true,
      "offer_enabled": true,
      "price": 100,
      "qty": 1,
      "max_per_order": 5,
      "max_per_day": null
    }
  }
}
```

**Erros comuns**
- `404`: `CATALOG_ITEM_NOT_FOUND`
- `400`: valores inválidos (ex: `price < 0`, boolean inválido)

---

### `POST /api/shop/admin/catalog/clear`
Limpa (zera) o catálogo **por completo**. Remove todas as linhas de:

- `shop_offer`
- `shop_catalog`

Use esse endpoint quando o admin quiser “recomeçar do zero” e rodar o scanner novamente.

**ATENÇÃO:** isso é um *hard clear* do catálogo. Pedidos antigos podem continuar existindo no histórico (ex: `shop_order_item`) mas os itens do catálogo não existirão mais.

**Body (obrigatório)**
```json
{ "confirm": "DELETE_ALL_CATALOG" }
```

**200**
```json
{
  "success": true,
  "data": {
    "deleted": {
      "shop_offer": 10,
      "shop_catalog": 10
    }
  }
}
```

**Erros comuns**
- `400`: `CONFIRMATION_REQUIRED`

---

### `POST /api/shop/admin/catalog/import`
Importa um snapshot do catálogo e faz **upsert** (create/update) por `code`.

Objetivo: permitir importar um catálogo pronto em um servidor novo (DB vazia) sem depender do scanner para semear códigos.

**Query/Body (opcional)**
```
dry_run=true|false   (default: false)
mode=merge           (default: merge)
```

**Observações importantes (integridade/segurança)**
- O banco possui `UNIQUE(setup)` em `shop_catalog`.
- Duplicidade de `code` ou `setup` dentro do snapshot é rejeitada.
- Se o `code` já existir no banco, **não é permitido alterar o `setup`** (conflito).
- Se o `setup` já estiver em uso no banco por outro `code`, ocorre conflito.
- `mode=replace` não é suportado.

**Body**
```json
{
  "schema": "shop_catalog_snapshot_v1",
  "exportedAt": "2026-02-09T04:42:07.889Z",
  "mode": "merge",
  "dry_run": false,
  "items": [
    {
      "code": 1,
      "display_name": "2H_Axe_ES",
      "setup": "2H_Axe_ES",
      "catalog_enabled": true,
      "offer_enabled": false,
      "price": 0,
      "qty": 1,
      "max_per_order": null,
      "max_per_day": null
    }
  ]
}
```

**200**
```json
{
  "success": true,
  "data": {
    "created": 120,
    "updated": 80,
    "ignored": 0,
    "errors": []
  }
}
```

**400 (VALIDATION_FAILED)**
```json
{
  "success": false,
  "error": "VALIDATION_FAILED",
  "data": {
    "errors": [
      {"code": 1, "reason": "DUPLICATE_CODE"},
      {"code": 2, "reason": "INVALID_QTY", "field": "qty"}
    ]
  }
}
```

**409 (CONFLICT)**
```json
{
  "success": false,
  "error": "CONFLICT",
  "data": {
    "created": 1,
    "updated": 0,
    "ignored": 0,
    "errors": [
      {"code": 1, "reason": "SETUP_ALREADY_USED"}
    ]
  }
}
```

### `POST /api/shop/rewards/time-tick`
Executa o tick de recompensa por tempo (se habilitado em `app_config`).

**Body**
```json
{ "steam_id": "76561198012345678" }
```

**200**
```json
{
  "success": true,
  "data": {
    "applied": true,
    "balance": 1010,
    "ref_id": "time:3600:488888"
  }
}
```

---

## Integrações (Discord Bot)

Esses endpoints permitem que um bot (ou integração externa) execute ações administrativas **sem JWT**, usando uma senha (API Key) enviada no header.

### Autenticação

- Header obrigatório: `X-Integration-Key: <SENHA>`
- A senha deve ter **no mínimo 32 caracteres**.
- O backend armazena apenas o **hash SHA-256** da senha no banco (não armazena em texto puro).

### Admin: gerenciar keys

#### `GET /api/shop/admin/integrations/keys`
Lista todas as keys configuradas.

**Auth**: `Bearer token` (admin)

**200**
```json
{
  "success": true,
  "data": {
    "items": [
      {
        "key_id": "...",
        "name": "discord-bot",
        "enabled": 1,
        "created_at": "2026-02-07 14:00:00",
        "last_used_at": "2026-02-07 14:10:00"
      }
    ],
    "count": 1
  }
}
```

#### `POST /api/shop/admin/integrations/keys`
Cria uma nova key e **auto-desabilita as anteriores** (modo “1 ativa”).

**Auth**: `Bearer token` (admin)

**Body**
```json
{
  "name": "discord-bot",
  "key": "SENHA_COM_NO_MINIMO_32_CARACTERES"
}
```

**201**
```json
{
  "success": true,
  "data": {
    "key_id": "...",
    "name": "discord-bot",
    "enabled": 1
  }
}
```

#### `PATCH /api/shop/admin/integrations/keys/<key_id>`
Ativa/desativa uma key. Ao ativar (`enabled=1`), o backend desativa as demais.

**Auth**: `Bearer token` (admin)

**Body**
```json
{ "enabled": 0 }
```

---

### Integração: créditos (wallet)

#### `POST /api/integrations/wallet/credit`
Adiciona créditos ao jogador.

**Headers**
- `X-Integration-Key`

**Body**
```json
{
  "external_id": "discord:credit:123",
  "steam_id": "76561198012345678",
  "amount": 100,
  "meta": { "source": "discord" }
}
```

**200**
```json
{
  "success": true,
  "already_applied": false,
  "steam_id": "76561198012345678",
  "amount": 100,
  "balance": 500
}
```

**Erros comuns**
- `401`: `INTEGRATION_KEY_REQUIRED` / `INTEGRATION_KEY_INVALID`
- `400`: `PLAYER_NOT_FOUND`

#### `POST /api/integrations/wallet/debit`
Remove créditos do jogador (não permite saldo negativo).

**Headers**
- `X-Integration-Key`

**Body**
```json
{
  "external_id": "discord:debit:123",
  "steam_id": "76561198012345678",
  "amount": 50,
  "meta": { "source": "discord" }
}
```

**200**
```json
{
  "success": true,
  "already_applied": false,
  "steam_id": "76561198012345678",
  "amount": 50,
  "balance": 450
}
```

**Erros comuns**
- `409`: `INSUFFICIENT_FUNDS`

#### `POST /api/integrations/wallet/balance`
Consulta saldo atual da carteira.

**Rate limit**

- O backend aplica rate limit de **10 minutos** por `(integrationKey, steam_id)`.
- Se consultar novamente antes do tempo, retorna HTTP `429`.

**Headers**
- `X-Integration-Key`

**Body**
```json
{
  "external_id": "discord:balance:123",
  "steam_id": "76561198012345678",
  "meta": { "source": "discord" }
}
```

**200**
```json
{
  "success": true,
  "steam_id": "76561198012345678",
  "player_name": "PlayerName",
  "balance": 0,
  "meta": { "source": "discord" }
}
```

**429 (RATE_LIMITED)**
```json
{
  "success": false,
  "error": "RATE_LIMITED",
  "retry_after_seconds": 600
}
```

**Erros comuns**
- `401`: `INTEGRATION_KEY_REQUIRED` / `INTEGRATION_KEY_INVALID`
- `400`: `PLAYER_NOT_FOUND`

---

### Integração: VIP

#### `POST /api/integrations/vip/activate`
Ativa VIP para o jogador.

**Regras**
- Só ativa VIP se o jogador já estiver no **Padrão**.
- Ao ativar VIP, remove do **Padrão**.
- As regras são identificadas por `name`:
  - **Padrão**: `name == "Padrão"`
  - **VIP**: `name == "VIP"`

**Headers**
- `X-Integration-Key`

**Body**
```json
{
  "external_id": "discord:vip_on:123",
  "steam_id": "76561198012345678",
  "meta": { "source": "discord" }
}
```

**200**
```json
{
  "success": true,
  "already_applied": false,
  "steam_id": "76561198012345678",
  "vip": 1,
  "meta": { "source": "discord" }
}
```

**Erros comuns**
- `400`: `PLAYER_NOT_FOUND`
- `400`: `VIP_RULE_NOT_FOUND`
- `400`: `DEFAULT_RULE_NOT_FOUND`
- `400`: `NOT_IN_DEFAULT_RULE`

#### `POST /api/integrations/vip/deactivate`
Desativa VIP e **volta automaticamente** para o **Padrão**.

**Headers**
- `X-Integration-Key`

**Body**
```json
{
  "external_id": "discord:vip_off:123",
  "steam_id": "76561198012345678",
  "meta": { "source": "discord" }
}
```

**200**
```json
{
  "success": true,
  "already_applied": false,
  "steam_id": "76561198012345678",
  "vip": 0,
  "meta": { "source": "discord" }
}
```
