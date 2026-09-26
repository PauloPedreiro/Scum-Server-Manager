# Vehicle Catalog Images (Backend API)

This document describes how the frontend should **upload** and **display** vehicle catalog images.

## Summary

- Each vehicle catalog item (`vehicle_catalog`) can have **one** image.
- The backend stores a **URL** in `vehicle_catalog.image_url`.
- Images are stored locally under:
  - `data/imagens/vehicle/`
- Images are served by `/api/vehicles/assets/<filename>`.
- The backend returns **signed image URLs** (querystring `exp` + `sig`) so the frontend can render with plain `<img src>`.

---

## Database

Table: `vehicle_catalog`

Column:

- `image_url` (TEXT, nullable)
  - Example value: `/api/vehicles/assets/vehicle_12_8c1e....webp`

The backend runs a migration automatically to create the column if missing.

---

## Endpoints

### 1) Upload / Replace image (ADMIN)

`POST /api/vehicles/admin/catalog/<code>/image`

- Auth: **required** (`Bearer JWT`)
- Admin: **required**
- Content-Type: `multipart/form-data`

#### Form fields

- `file` (required)
  - Allowed extensions: `.png`, `.jpg`, `.jpeg`, `.webp`
  - Max size: **5 MB**

#### Response (200)

```json
{
  "success": true,
  "data": {
    "code": 12,
    "image_url": "/api/vehicles/assets/vehicle_12_8c1e....webp?exp=1739...&sig=..."
  }
}
```

#### Errors

- `400 file is required`
- `400 INVALID_FILE_TYPE`
- `400 EMPTY_FILE`
- `413 FILE_TOO_LARGE`
- `404 CATALOG_ITEM_NOT_FOUND`
- `503 DATABASE_BUSY`

---

### 2) Serve image asset (Signed URL or Bearer)

`GET /api/vehicles/assets/<filename>`

- Auth: either
  - `Authorization: Bearer <JWT>`
  - OR signed querystring: `?exp=<unix_seconds>&sig=<hex>`
- Returns: raw image bytes

Notes:

- The catalog endpoints return `image_url` **already signed**.
- Signed URLs have a TTL (default: 1 hour).

#### Errors

- `400 INVALID_FILENAME`
- `404 NOT_FOUND`

---

## Catalog listing payloads (where `image_url` appears)

### Enabled catalog for users

`GET /api/vehicles/catalog`

Returns only `enabled=1` items and includes `image_url`.

### Full catalog for admin

`GET /api/vehicles/admin/catalog`

Returns all items and includes `image_url`.

---

## Frontend implementation notes (important)

The backend provides `image_url` as a **signed URL**, so you can render it directly:

```tsx
<img src={item.image_url} />
```

### Legacy option (not required anymore)

If you ever need to bypass signed URLs (for debugging), you can still fetch the asset with `Authorization: Bearer <JWT>` using `fetch()`.

### CORS

The backend already enables CORS for `/api/*`. If the frontend runs on a different origin, requests should work as long as the JWT is provided.

---

## Testing checklist

- Upload an image via Postman to `POST /api/vehicles/admin/catalog/<code>/image`.
- Call `GET /api/vehicles/admin/catalog` and confirm `image_url` is populated.
- Open the `image_url` in a browser tab and confirm the image loads (should work because it is signed).
- Optionally call `GET /api/vehicles/assets/<filename>` with `Authorization: Bearer <JWT>` and confirm it also works.
