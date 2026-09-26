# Shop Catalog Import/Upsert (Backend Request)

## Goal
Enable importing a ready-to-use shop catalog on a fresh server **without** requiring the scanner to seed item codes.

Today the frontend can export/import a JSON snapshot, but it can only **update** existing items (by `code`).
On a new/empty server, `GET /api/shop/admin/catalog` returns an empty list, so the import cannot be applied (all codes are effectively “missing”).

This document describes a backend endpoint (Python) to support **upsert** (create/update) of catalog items by `code`.

---

## Proposed Endpoint

### Route
`POST /api/shop/admin/catalog/import`

### Auth
Admin-only (same rule as other `/shop/admin/*` endpoints).

---

## Request Body (JSON)
The frontend exports this schema.

```json
{
  "schema": "shop_catalog_snapshot_v1",
  "exportedAt": "2026-02-09T04:00:00Z",
  "items": [
    {
      "code": 60008,
      "display_name": "AK-47",
      "setup": "Ammo_Weapons",
      "catalog_enabled": true,
      "offer_enabled": true,
      "price": 120,
      "qty": 1,
      "max_per_order": 1,
      "max_per_day": 3
    }
  ]
}
```

### Field meanings
- **code**: unique item identifier.
- **display_name**: name shown to players.
- **setup**: grouping/category from scanner (used to organize).
- **catalog_enabled**: item visible/enabled in catalog.
- **offer_enabled**: item purchasable as offer.
- **price**: offer price.
- **qty**: delivered quantity.
- **max_per_order**: nullable limit per purchase.
- **max_per_day**: nullable limit per day.

---

## Validation Rules
- `schema` required and must be `shop_catalog_snapshot_v1`
- `items` required array
- each item:
  - `code`: integer > 0
  - `display_name`: string (allow empty if desired)
  - `setup`: string
  - `catalog_enabled`: boolean
  - `offer_enabled`: boolean
  - `price`: number >= 0
  - `qty`: integer >= 1
  - `max_per_order`: null or integer >= 0
  - `max_per_day`: null or integer >= 0

If you want strictness on `setup`, return per-item error; otherwise accept any string.

---

## Behavior (Upsert)
For each item in `items`:
- if `code` exists:
  - UPDATE fields
- else:
  - INSERT a new catalog row (create)

Recommended:
- Run in a **transaction** (all-or-nothing), OR
- Allow partial apply and return per-item errors.

---

## Response (Summary)
Return a summary so the UI can display results:

```json
{
  "success": true,
  "data": {
    "created": 120,
    "updated": 80,
    "ignored": 3,
    "errors": [
      { "code": 99999, "reason": "INVALID_SETUP" }
    ]
  }
}
```

Notes:
- `ignored`: optional bucket for items intentionally skipped (e.g., invalid data but non-fatal, unknown setup, etc.).
- `errors`: optional list of per-item failures.

---

## Optional Improvements

### Dry-run
Support `dry_run=true` (query or body) to validate and return the summary without writing.

### Mode
- `mode=merge` (default): create/update only the provided codes.
- `mode=replace`: remove items not in snapshot (dangerous, should require explicit confirmation).

---

## Alternative (not recommended)
Change `PATCH /api/shop/admin/catalog/{code}` to behave as upsert.
This works but is inefficient for large imports and provides worse validation/reporting.
