# 🛒 Shop / Economy / Mailbox - Frontend API (Quick Reference)

Base URL:
```
http://localhost:3000
```

## 🔐 Authentication (JWT)

Most admin/panel endpoints require JWT.

**Headers**
```http
Authorization: Bearer <token>
Content-Type: application/json
```

Token is obtained via:
- `POST /api/auth/login`

---

## ✅ Endpoints (Shop / Economy / Mailbox)

### `GET /api/shop/wallet/balance`
Get current wallet balance.

- Normal user: gets own balance
- Admin: can pass `steam_id` query param to get other player's balance

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

## 🌐 Integrations (X-Integration-Key)

Endpoints usados por bots/sistemas externos. Exigem o header `X-Integration-Key`.

### `POST /api/integrations/wallet/balance`
Consulta saldo atual da carteira por `steam_id`.

**Rate limit**

- 10 minutos por `(integrationKey, steam_id)`.
- Se consultar novamente antes do tempo, retorna `429` com `retry_after_seconds`.

**Headers**
```http
X-Integration-Key: <key>
Content-Type: application/json
```

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
  "balance": 1000,
  "meta": { "source": "discord" }
}
```

**429**
```json
{
  "success": false,
  "error": "RATE_LIMITED",
  "retry_after_seconds": 600
}
```

**Common errors**
- `401`: `INTEGRATION_KEY_REQUIRED` / `INTEGRATION_KEY_INVALID`
- `400`: `PLAYER_NOT_FOUND`

### `GET /api/shop/wallet/transactions`
Get wallet transaction history (latest movements for the current user).

**Query (optional)**
```
limit=50
```

### `GET /api/shop/catalog`
List the **buyable** catalog for the frontend (only enabled catalog + enabled offers).

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

### `POST /api/shop/mailbox`
Register/update player mailbox (`steam_id -> chest_id`).

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

### `POST /api/shop/orders`
Create an order. Wallet is charged at order creation.

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

**Common errors**
- `400`: `MAILBOX_NOT_REGISTERED`, `OFFER_DISABLED:<code>`, `OFFER_NOT_AVAILABLE:<code>`, `MAX_PER_ORDER` (if configured)
- `409`: `INSUFFICIENT_FUNDS`

---

### `POST /api/shop/rewards/time-tick`
Run time reward tick (if enabled in `app_config`).

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

## 🛡️ Admin endpoints (Shop)

### `POST /api/shop/admin/wallet/adjust`
Manual wallet adjustment (delta +/-). Idempotent by `external_id`.

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

---

### `GET /api/shop/admin/wallet/transactions`
Admin wallet transaction history for a specific `steam_id`.

**Query (required)**
```
steam_id=76561198012345678
```

### `GET /api/shop/admin/catalog`
List the full catalog for admin UI (includes disabled catalog/offers).

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

### `PATCH /api/shop/admin/catalog/<code>`
Update one catalog/offer item by `code`.

**Body (all optional)**
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

---

### `POST /api/shop/admin/catalog/clear`
Hard-clear the shop catalog (deletes all rows from `shop_offer` and `shop_catalog`). Use this when the admin wants to re-run the scanner from scratch.

**Body (required)**
```json
{ "confirm": "DELETE_ALL_CATALOG" }
```

### `POST /api/shop/admin/credit`
Idempotent admin credit (e.g., PIX / external purchase). Re-sending the same `external_id` will not duplicate the credit.

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

---

### `POST /api/shop/admin/scanner-chest`
Set which chest will be used as catalog scanner.

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
Sync items from scanner chest (SCUM.db) to catalog (SSM.db).

- Creates `shop_catalog` entries for discovered setups
- Creates matching `shop_offer` rows (disabled by default)

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
Mark retry for failed orders.

**200**
```json
{ "success": true, "retry_requested": true, "order_id": "..." }
```

---

### `POST /api/shop/delivery/run`
Run the offline delivery job manually.

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

## 🧩 TypeScript types (suggestion)

```ts
export type SteamId = string;

export type ShopOrderItemInput = {
  code: number;
  qty: number;
};

export type ApiSuccess<T> = {
  success: true;
  data: T;
  message?: string;
};

export type ApiError = {
  success: false;
  error?: string;
  message?: string;
};

export type ApiResponse<T> = ApiSuccess<T> | ApiError;

export type ShopCreateOrderRequest = {
  steam_id: SteamId;
  items: ShopOrderItemInput[];
};

export type ShopCreateOrderResponse = {
  order_id: string;
  total_price: number;
  balance: number;
};

export type ShopMailboxRequest = {
  steam_id: SteamId;
  chest_id: number;
};

export type ShopMailboxResponse = {
  steam_id: SteamId;
  chest_id: number;
};
```

---

## 🔌 Frontend integration notes

- Use your existing API client (axios/fetch) and attach JWT headers.
- Treat `success: false` as an application-level error even when HTTP=200 (some endpoints do this).
- For `/api/shop/orders`, handle HTTP `409` as insufficient funds.
