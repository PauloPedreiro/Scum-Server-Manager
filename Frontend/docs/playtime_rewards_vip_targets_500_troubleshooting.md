---
description: Troubleshooting HTTP 500 on VIP target add (Playtime Rewards)
---

# Troubleshooting: HTTP 500 on POST `/api/shop/admin/rewards/playtime-rules/{rule_id}/targets`

This document is meant for backend debugging when the Admin UI attempts to add a Steam ID to a playtime rule target list and the server responds with **HTTP 500**.

## Context / Business rules (backend)

- Rules are identified by **`name`**:
  - Default rule: `name == "Padrão"`
  - VIP rule: `name == "VIP"`
- Both rules are expected to be `audience_type = "list"`.
- VIP promotion constraint:
  - When adding a target to rule `name=="VIP"`, backend must ensure the Steam ID is already in Default (`"Padrão"`) targets.
  - On success, backend adds to VIP and removes from Default.
- Expected error codes for VIP add (should be **HTTP 400**, not 500):
  - `DEFAULT_RULE_NOT_FOUND`
  - `NOT_IN_DEFAULT_RULE`

If you are returning 500, an exception is being thrown somewhere in this VIP promotion path.

## Repro (request details)

### Endpoint

`POST /api/shop/admin/rewards/playtime-rules/{rule_id}/targets`

### Headers

- `Authorization: Bearer <token>`
- `Content-Type: application/json`

### Payload

```json
{ "steam_id": "7656119..." }
```

### Curl example

```bash
curl -i \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"steam_id":"76561198000000000"}' \
  http://localhost:3000/api/shop/admin/rewards/playtime-rules/<RULE_ID>/targets
```

## What to capture when it fails

- HTTP status + full response body
- Server logs / stacktrace for the request
- The resolved rule row in DB (by `rule_id`) and whether its `name` is `VIP` or `Padrão`
- The Default rule lookup result (`name == "Padrão"`) at the moment of the request

## Debug checklist (most common root causes)

### 0) NameError: `name 'ssm_tx' is not defined` (direct cause of HTTP 500)

If the response/logs show:

```
NameError: name 'ssm_tx' is not defined
```

This is a backend bug and will always surface as **HTTP 500**.

Typical causes:
- A transaction/context variable (e.g. `ssm_tx`) is referenced inside the handler/service but is not:
  - imported
  - created
  - passed as a parameter
  - injected via dependency

Where to look:
- The handler for `POST /shop/admin/rewards/playtime-rules/{rule_id}/targets`.
- Any helper used for VIP promotion (add to VIP + remove from Default) that references `ssm_tx`.

Fix recommendation:
- Ensure the function receives the transaction/context explicitly (parameter) or creates it locally.
- Or replace `ssm_tx` with the correct available variable (e.g. `tx`, `db`, `session`, etc.).
- Add tests / guards so missing transaction variables return 500 with a clear log, but preferably do not rely on implicit globals.

### 1) Default rule lookup by name fails due to accent/encoding mismatch

Backend logic depends on **exact** `name == "Padrão"`.

Check in DB:
- Is the row stored as `Padrão` (with `ã`) or `Padrao`?
- Is collation/encoding correct (`UTF-8`)?

If your code uses a hardcoded string and DB contains a different spelling, the lookup returns null and downstream code might crash.

**Fix recommendation:**
- Ensure DB contains exactly `Padrão`.
- Guard null lookups and return `DEFAULT_RULE_NOT_FOUND` (HTTP 400).

### 2) Rule is not `audience_type="list"`

Doc requires both rules to be lists.

If VIP or Default is `audience_type="all"`, the targets logic may not expect it.

**Fix recommendation:**
- Validate rule fields before applying targets.
- If rule is not a list, return HTTP 400 with a clear error (e.g. `RULE_NOT_LIST`).

### 3) VIP promotion code assumes Default rule exists and dereferences null

Example pattern that can throw:
- `defaultRule.rule_id` when `defaultRule` is null

**Fix recommendation:**
- Explicitly check `if (!defaultRule) return 400 DEFAULT_RULE_NOT_FOUND`.

### 4) DB constraint / duplicate insert not handled

If target table has unique constraints and you insert duplicates without catching, you might throw.

**Fix recommendation:**
- Use upsert/ignore semantics or catch unique-violation and return success (idempotent) or return HTTP 400 with code like `ALREADY_IN_RULE`.

### 5) Transaction handling during VIP promotion

VIP promotion is conceptually a multi-step operation:
- insert into VIP targets
- delete from Default targets

If not wrapped in a transaction, partial failures may occur.

**Fix recommendation:**
- Wrap in a DB transaction and ensure consistent state.

### 6) Player eligibility check throws

VIP add requires Steam ID is in Default.

Potential failures:
- query returns unexpected shape
- null handling
- type conversion

**Fix recommendation:**
- Validate inputs and query results, return `NOT_IN_DEFAULT_RULE` (HTTP 400).

### 7) Request body parsing issues

Confirm backend expects `steam_id` (snake_case). If it expects `steamId`, request payload may parse as null and crash.

**Fix recommendation:**
- Validate request body and return HTTP 422/400 with message.

## Expected backend behavior for VIP add

When `POST .../targets` is called for the VIP rule:

- If Default rule (`Padrão`) does not exist:
  - return **HTTP 400** `{ "error": "DEFAULT_RULE_NOT_FOUND" }`
- If Steam ID not in Default targets:
  - return **HTTP 400** `{ "error": "NOT_IN_DEFAULT_RULE" }`
- If OK:
  - add to VIP targets
  - remove from Default targets
  - return **HTTP 200** (or your ApiResponse success format)

## Notes for frontend compatibility

Frontend currently:
- Sends `{ steam_id: string }`.
- Treats 400 error codes above as user-friendly messages.
- For 500, it asks for Network Response body.

Therefore, returning **400 with `error` field** is strongly preferred over 500.
