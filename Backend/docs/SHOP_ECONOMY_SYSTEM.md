# 🛒 Shop + 💰 Economy + 📦 Mailbox (Item Delivery System)

Este documento descreve o sistema de **Shop/Economy/Mailbox** implementado no backend.

A base do sistema é:
- **SSM.db** (autoridade): catálogo, ofertas, pedidos, ledger e estado.
- **SCUM.db** (jogo): entrega física dos itens em um **baú (mailbox)** registrado para cada jogador.

> Importante: A entrega física só aparece no jogo de forma consistente após **restart do servidor**, pois o SCUM cacheia inventários.

---

## 📌 Visão Geral

### Componentes
- **Wallet**: saldo do jogador em moeda virtual.
- **Ledger (`wallet_tx`)**: transações imutáveis de crédito/débito com idempotência.
- **Catalog/Offers**:
  - `shop_catalog`: lista de itens (setup/class do SCUM).
  - `shop_offer`: configura preço, habilitação e limites.
- **Orders**:
  - `shop_order`: pedido do jogador (status, total, tentativas, erro).
  - `shop_order_item`: itens do pedido (setup + qty).
  - `shop_delivery_item`: controle de entrega parcial (idempotência).
- **Mailbox**:
  - `player_mailbox`: mapeia `steam_id -> chest_id`.
- **Scanner**:
  - Chest “scanner” (configurado em `app_config`) para popular catálogo automaticamente com base nos itens dentro do baú.
- **Delivery Job**:
  - Processo offline que entrega pedidos pendentes no SCUM.db.
  - Roda automaticamente antes de restart (agendado e manual), e também pode ser acionado via endpoint.
- **Rewards**:
  - `time_reward` (crédito por período) com idempotência por janela de tempo.

---

## 🧱 Banco de Dados (SSM.db)

As tabelas do sistema são criadas automaticamente pelo `utils/database_initializer.py`.

### `app_config`
Chave/valor de configurações de aplicação.
- Chaves usadas:
  - `shop.scanner_chest_id`
  - `economy.time_reward.enabled`
  - `economy.time_reward.amount`
  - `economy.time_reward.period_seconds`

### `wallet`
Saldo atual do jogador.
- `steam_id` (PK)
- `balance` (int)

### `wallet_tx`
Ledger (imutável). Todas as mudanças de saldo devem passar por essa tabela.
- `tx_id` (PK)
- `steam_id`
- `delta`
- `reason`
- `ref_type`, `ref_id`
- `meta_json`
- **Idempotência**: índice único `ux_wallet_tx_ref` em `(steam_id, reason, ref_type, ref_id)`.

### `admin_credit`
Controle de crédito administrativo (PIX/compra externa).
- `external_id` tem índice único `ux_admin_credit_external`.

### `player_mailbox`
Registro do baú por jogador.
- `steam_id` (PK)
- `chest_id` (int)

### `shop_catalog`
Catálogo de itens.
- `code` (PK)
- `setup` (unique)
- `display_name` (opcional)
- `enabled`

### `shop_offer`
Configurações comerciais por item.
- `code` (PK)
- `qty`, `price`, `enabled`
- `max_per_order`, `max_per_day`

### `shop_order`
Pedido.
- `order_id` (PK)
- `steam_id`
- `chest_id`
- `total_price`
- `status`: `pending | delivering | delivered | failed`
- `attempt_count`, `last_attempt_at`
- `retry_requested` (0/1)
- `error`

### `shop_order_item`
Itens do pedido.
- PK `(order_id, code)`
- `setup`, `qty`

### `shop_delivery_item`
Controle de entrega parcial.
- PK `(order_id, code)`
- `qty_delivered`, `last_delivered_at`

---

## 🔄 Fluxos

### 1) Registrar Mailbox (baú do jogador)
1. Admin/jogador escolhe um baú (entity_id) no jogo.
2. Registra em `player_mailbox`.
3. Entregas futuras serão feitas nesse baú.

### 2) Scanner -> Catalog
1. Admin define um chest como “scanner”.
2. O backend lê os itens desse baú no SCUM.db (read-only).
3. Para cada `entity.class` encontrado:
   - Cria `shop_catalog` (code incremental)
   - Cria `shop_offer` (disabled por padrão)

### 3) Comprar (Order)
1. Cliente chama `POST /api/shop/orders`.
2. Backend valida:
   - mailbox registrado
   - ofertas habilitadas
   - limites por pedido
3. Cria `shop_order` + `shop_order_item`.
4. Debita saldo usando `WalletService.apply_delta()` com:
   - `reason=shop_purchase`
   - `ref_type=order`
   - `ref_id=<order_id>`

### 4) Delivery Job (offline)
1. Busca pedidos:
   - `status='pending'` **ou**
   - `status='failed' AND retry_requested=1`
2. Para cada item, calcula `remaining = qty - qty_delivered`.
3. Spawna `remaining` itens no `SCUM.db` dentro do chest (`entity_inventory_component_entry`).
4. Atualiza `shop_delivery_item`.
5. Se todos itens entregues: marca `shop_order.status='delivered'`.
6. Se erro: marca `failed`, salva `error`.

### 5) Retry
- Apenas pedidos `failed` podem ser marcados com `retry_requested=1`.

### 6) Rewards (time tick)
- Aplicado com idempotência por janela (período em segundos).
- O `ref_id` usado é `time:<period_seconds>:<period_index>`.

---

## 🔌 Endpoints

Base URL:
```
http://localhost:3000
```

### Admin
#### `POST /api/shop/admin/credit`
Creditar saldo via id externo (idempotente).

**Body**:
```json
{
  "external_id": "PIX_ABC123",
  "steam_id": "7656119...",
  "amount": 100,
  "meta": {"provider": "pix"}
}
```

#### `POST /api/shop/admin/scanner-chest`
Define o chest de scanner.

**Body**:
```json
{ "chest_id": 60008 }
```

#### `POST /api/shop/admin/scanner/sync`
Lê o chest scanner no SCUM.db e cria entradas no catálogo/oferta.

**Body**: `{}`

#### `POST /api/shop/orders/<order_id>/retry`
Marca retry para pedido falhado.

#### `POST /api/shop/delivery/run`
Executa o delivery job manualmente.

**Body**:
```json
{ "limit": 50 }
```

### Auth
#### `POST /api/shop/mailbox`
Registra/atualiza mailbox do jogador.

**Body**:
```json
{ "steam_id": "7656119...", "chest_id": 60008 }
```

#### `POST /api/shop/orders`
Cria pedido.

**Body**:
```json
{
  "steam_id": "7656119...",
  "items": [
    {"code": 1, "qty": 2},
    {"code": 5, "qty": 1}
  ]
}
```

#### `POST /api/shop/rewards/time-tick`
Executa o time reward tick.

**Body**:
```json
{ "steam_id": "7656119..." }
```

---

## 🧪 Smoke Test

Arquivo:
- `tools/shop_smoke.py`

Uso:
```bash
python tools/shop_smoke.py http://127.0.0.1:3000 <JWT> 7656119...
```

---

## ⚠️ Notas Importantes
- **SCUM.db** é sensível: o backend lê com modo read-only (quando possível) e escreve apenas no delivery.
- Itens em baú não usam `virtualized_item`.
- Entrega pode precisar de:
  - fechar/abrir o baú
  - aguardar alguns segundos
  - **restart do servidor** (recomendado)
