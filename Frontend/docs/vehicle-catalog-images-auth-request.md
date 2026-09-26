# Request: Remove Authorization requirement for Vehicle Catalog Images (frontend rendering)

## Context
The frontend currently authenticates against the admin panel using JWT (Bearer token).

The new vehicle catalog images feature stores `vehicle_catalog.image_url` like:

- `/api/vehicles/assets/<filename>`

And serves the image bytes via a **private** endpoint requiring:

- `Authorization: Bearer <JWT>`

## Problem
A plain HTML tag cannot attach custom headers:

- `<img src="/api/vehicles/assets/..." />` **does not send** `Authorization`.

So even if the user is already logged into the panel, the browser request for the `<img>` fails (401/403), unless the frontend implements a JS workaround:

- `fetch(image_url, { headers: { Authorization } })`
- `blob()` -> `URL.createObjectURL(blob)`
- render the object URL

This workaround works, but adds:

- extra client-side complexity
- object URL lifecycle management (`URL.revokeObjectURL`)
- harder caching / extra memory usage
- harder virtualization/lazy-loading (needs JS fetch per item)

## Request
Please provide an option to serve these images in a way that **works with `<img src>`** without requiring an `Authorization` header.

### Option A (recommended): Cookie-based auth for assets
If the backend can authenticate using an `HttpOnly` cookie (session cookie or JWT cookie), then `<img>` will automatically include the cookie.

Notes:

- This requires that the frontend login flow sets a cookie for the API origin.
- Ensure CORS is configured with `credentials: true` if frontend is on another origin.

### Option B: Signed URLs / temporary tokens
Make `image_url` be a signed URL with an expiry, e.g.:

- `/api/vehicles/assets/<filename>?sig=...&exp=...`

Then `<img src>` works without auth headers and the URL is time-limited.

### Option C: Make assets public
Expose `/api/vehicles/assets/<filename>` publicly.

This is simplest, but only acceptable if there is no need to protect these images.

## Expected result
With one of the options above, the frontend can simply do:

- `<img src={item.image_url} />`

No extra fetch/blob/objectURL logic needed.

## Current backend endpoints (for reference)
- `POST /api/vehicles/admin/catalog/<code>/image` (upload, multipart)
- `GET /api/vehicles/assets/<filename>` (currently private)
