# Player App - API Endpoint Analysis (Postman Collection)

Source: `docs/endpoints/postman-collection.json`

This document summarizes which existing endpoints can be reused for a **player-facing app** (each user has **individual access**) and which endpoints should remain **admin/ops/integration only**, plus recommended new endpoints to safely support the player app.

## Key requirement: individual access

A player app must guarantee:

- The authenticated player can only access their own data.
- The API must not accept identifiers (e.g., `steam_id`) from the client in a way that allows querying or modifying other players' data.

In practice this means:

- Either the backend derives `steam_id` (or `player_id`) from the authenticated token (`sub` claim),
- Or the backend uses explicit access control checks everywhere.

---

## Existing endpoints that are useful for the player app

### Health (public)

- `GET /api/health`
- `GET /api/health/detailed`

Use case:

- App health check and diagnostics.

### Authentication (JWT)

Folder: `Authentication`

Endpoints present:

- `POST /api/auth/login`
- `POST /api/auth/logout`
- `GET /api/auth/me`
- `POST /api/auth/change-password`
- `POST /api/auth/request-password-reset`
- `POST /api/auth/reset-password`
- `POST /api/auth/reset-admin-password`
- `GET /api/auth/debug`

Also present (admin-style management):

- `GET /api/auth/users`
- `POST /api/auth/users`
- `PUT /api/auth/users/<id>`
- `DELETE /api/auth/users/<id>`
- `GET /api/auth/users/search-players`

Notes for player app:

- The endpoints `login`, `me`, `logout`, `change-password` can be reused for player auth **only if** they represent player identities, not only admin identities.
- The endpoints that manage users and `search-players` must not be exposed to players.

---

## Shop / Economy / Mailbox

Folder: `Shop / Economy / Mailbox`

### Potentially player-facing endpoints (need authorization/scoping)

- `GET /api/shop/catalog`
  - Lists purchasable catalog (enabled items/offers).
- `POST /api/shop/orders`
  - Creates order and debits balance.
- `POST /api/shop/mailbox`
  - Registers/updates mailbox mapping `steam_id -> chest_id`.

Important risk:

- If these endpoints accept `steam_id` from the client, a player can impersonate another player.
- For a player app, the API should not allow the client to choose `steam_id`.

### Admin-only endpoints (do not expose to player app)

Wallet/admin:

- `POST /api/shop/admin/credit`
- `POST /api/shop/admin/wallet/adjust`
- `GET /api/shop/admin/wallet/transactions?steam_id=...`

Catalog/admin:

- `GET /api/shop/admin/catalog`
- `PATCH /api/shop/admin/catalog/<code>`
- `POST /api/shop/admin/catalog/import` (and dry_run)
- `POST /api/shop/admin/catalog/clear`

Scanner/sync/admin:

- `POST /api/shop/admin/scanner-chest`
- `POST /api/shop/admin/scanner/sync`

Jobs/admin:

- `POST /api/shop/delivery/run`
- `POST /api/shop/rewards/time-tick`

---

## Integrations (X-Integration-Key) - not for player app

Folder: `Integrations (X-Integration-Key)`

- `POST /api/integrations/wallet/credit`
- `POST /api/integrations/wallet/debit`
- `POST /api/integrations/wallet/balance`
- `POST /api/integrations/vip/activate`
- `POST /api/integrations/vip/deactivate`

Reason:

- These endpoints require a shared secret header `X-Integration-Key`.
- A player app cannot safely embed such a key.

---

## Server / Webhooks / Scheduler / Config - admin/ops only

Examples present in the collection:

Server control and settings:

- `GET /api/server/logs`
- `GET /api/server/settings`
- `PATCH /api/server/settings`
- `GET /api/server/status`
- `POST /api/server/start`
- `POST /api/server/stop`
- `POST /api/server/restart`
- `POST /api/server/cleanup-wal`

Webhooks configuration:

- `GET /api/webhooks/names`
- `PATCH /api/webhooks`
- `PUT /api/webhooks`
- `PUT /api/webhooks/<webhook_name>`
- `POST /api/webhooks/test`
- `POST /api/webhooks/<webhook_name>/test`
- `POST /api/webhooks/restore`

Scheduler:

- `GET /api/scheduler/config`

These endpoints should remain restricted to admin/operator roles.

---

## Gaps: what must be added (or changed) for a true player app

### 1) Player authentication model (Steam recommended)

If the player identity is Steam-based, add a dedicated auth flow:

- `POST /api/player/auth/steam/start`
  - Returns a Steam/OpenID URL + `state`.
- `GET /api/player/auth/steam/callback`
  - Validates OpenID response, creates/links player account, returns player JWT.

JWT recommendation:

- Use `sub` claim as the stable player identifier (e.g. `steam_id` or internal `player_id`).

### 2) Player profile

- `GET /api/player/me`
  - Returns player profile info (steam id, name, vip status, etc.).

### 3) Player wallet (balance + transactions)

Currently there is admin and integration access, but no player-scoped endpoints.

Add:

- `GET /api/player/wallet/balance`
- `GET /api/player/wallet/transactions?limit=&offset=`

### 4) Player orders

You can keep `POST /api/shop/orders`, but for a player app you typically also need:

- `GET /api/player/orders?limit=&offset=`
- `GET /api/player/orders/<id>`

### 5) Player mailbox (scoped)

Replace the current player-exposed behavior that accepts `steam_id`.

Add:

- `GET /api/player/mailbox`
- `PUT /api/player/mailbox`

Server logic:

- Derive `steam_id` from player JWT.

---

## Open questions to finalize the design

1) Will the player app authenticate via Steam (OpenID) or via username/password?
2) What features should the player app include?
   - Shop only (catalog, wallet, orders)?
   - VIP management?
   - Rankings / server stats?
3) Will this backend be exposed publicly on the internet or behind a private gateway?

---

## Summary

- The collection already includes JWT auth and several shop endpoints.
- Most endpoints are admin/ops/integration oriented.
- A player app requires new player-scoped endpoints and strict authorization so one player cannot act as another (especially around `steam_id`).
