# Vehicles Templates Sync (Frontend Notes)

## Endpoint

- **POST** `/api/vehicles/admin/templates/sync`
- **Auth**: Admin (`Authorization: Bearer <token>`)

## What it does

- Generates/updates the local templates DB:
  - `data/templates/SCUM_TEMPLATES.db`
- Also inserts missing templates into `SSM.db` table `vehicle_catalog` with safe defaults:
  - `setup`/`display_name`: template id as string
  - `enabled`: `0` (disabled by default)
  - `price`: `0`
  - Does **not** overwrite existing catalog entries.

## Payload (recommended)

```json
{
  "source_scum_db": "@config",
  "ids": [640004]
}
```

### Optional fields

- `source_scum_db`
  - `"@config"` uses the SCUM.db path configured in backend.
  - Can be an absolute path to an offline SCUM.db copy.
- `ids`
  - List of `template_vehicle_entity_id` integers.
- `force` (boolean)
  - When `true`, backend will read directly from `source_scum_db` (no snapshot).
  - Recommended only when `source_scum_db` is an **offline** file.

## New behavior when SCUMServer is running

When SCUMServer is **Running** and `force != true`:

- Backend automatically creates a **temporary, consistent** snapshot of `SCUM.db` using SQLite Backup API.
- Sync/merge is executed against the snapshot.
- Snapshot is deleted at the end.

This avoids:

- intermittent `database is locked`
- inconsistent reads from live SCUM.db

## Response diagnostics (useful for UI)

Successful response includes:

- `data.diagnostics.service_running`: boolean
- `data.diagnostics.used_snapshot`: boolean

Recommended UI messages:

- If `used_snapshot == true`: show `Running: using safe SCUM.db snapshot`
- Else: show `Stopped: reading SCUM.db directly`

## Error handling (new)

If snapshot creation fails, endpoint may return **HTTP 500** with:

- `code: "SCUMDB_SNAPSHOT_FAILED"`
- `details: <string>`

Recommended UI message:

- `Failed to create SCUM.db snapshot. Try again. If it persists, stop the server and retry.`

## Suggested tooltip/help text (PT-BR)

**Titulo:** Sync de Templates de Veiculos

**Texto:**

- Ao sincronizar os templates, o backend gera/atualiza `data/templates/SCUM_TEMPLATES.db` e cadastra templates faltantes no `vehicle_catalog` (desativados por padrao).
- Se o SCUMServer estiver **Running**, o backend cria automaticamente um **snapshot temporario** do `SCUM.db` para uma leitura segura e apaga o snapshot ao final.
- Se ocorrer erro `SCUMDB_SNAPSHOT_FAILED`, tente novamente ou faca o sync com o servidor parado.
- Opcional: enviar `force=true` para ler direto do `source_scum_db` (use apenas com arquivo offline/backup).
