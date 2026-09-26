# Admin Vehicle Templates Endpoints

This document describes the backend admin endpoints used to manage **vehicle templates** for SCUM vehicle spawning and to populate the **SSM vehicle catalog**.

## Overview (DBs)

- **SCUM.db**
  - The live game database.
  - Must be treated as **writeable only when the SCUM server is OFFLINE**.
- **SCUM_TEMPLATES.db**
  - Templates database used as the *source of truth* for cloning/spawning vehicles into SCUM.db.
  - Output path (current): `data/templates/SCUM_TEMPLATES.db`.
- **SSM.db**
  - Backend application database.
  - Vehicle shop uses table `vehicle_catalog`.

## Auth / Permissions

Both endpoints require:

- `Authorization: Bearer <JWT>`
- Admin user permissions (`require_admin`)
- `Content-Type: application/json`

---

# POST `/api/vehicles/admin/templates/sync`

Sync (merge) vehicle templates from an **offline** SCUM.db into `SCUM_TEMPLATES.db`, and then **upsert** synced items into `SSM.db -> vehicle_catalog`.

## Intended usage

- You extracted/identified `template_vehicle_entity_id` values from a SCUM.db.
- You want to update `SCUM_TEMPLATES.db` so that vehicle spawn/cloning works.
- You want the backend to create/update `vehicle_catalog` entries automatically.

## Safety / constraints

- By default, the endpoint refuses to run if `SCUMServer` is running.
- Use `force=true` only if the source SCUM.db is **offline**.

## Request

### Body

```json
{
  "source_scum_db": "@config",
  "ids": [640004, 641258],
  "force": true
}
```

### Fields

- `source_scum_db` (string, required)
  - Path to the source **offline** SCUM.db.
  - Special values:
    - `"@config"`, `"config"`, `"default"`: uses `paths.scum_server.database` from `data/config.json`.
- `ids` (array<int>, required)
  - List of template vehicle entity ids (SCUM `entity.id`) to sync.
  - Alias supported: `template_vehicle_entity_ids`.
- `force` (bool, optional; default `false`)
  - If `false` and SCUMServer is running, the request is blocked.

## Behavior

### 1) Merge into `SCUM_TEMPLATES.db`

For each id in `ids`:

- Copies/merges required rows from the source SCUM.db into `data/templates/SCUM_TEMPLATES.db`.
- Tracks ids successfully synced and ids missing from source.

### 2) Upsert into `SSM.db -> vehicle_catalog`

For each id in `report.synced`:

- Ensures a row exists in `vehicle_catalog`.
- Fills `setup` and `display_name` using the name resolved from the *generated* `SCUM_TEMPLATES.db`.
- Uses safe defaults for new items:
  - `enabled = 0`
  - `price = 0`

#### How `code` is assigned

`vehicle_catalog.code` is an **INTEGER PRIMARY KEY** and is expected to be **sequential (1..N)**.

- If a row already exists for the same `template_vehicle_entity_id`, the endpoint **reuses** its existing `code`.
- Otherwise, the endpoint allocates a new sequential code:
  - `code = MAX(code) + 1`

> Note: If you previously created rows with `code=template_vehicle_entity_id`, you should run `templates/reset` with `reset_catalog=true` (Option A) and then run sync again to rebuild sequential codes.

#### Non-overwrite rules (safe upsert)

- `setup` / `display_name` are updated only when the current values are still defaults (empty or equal to id/code strings).
- `price` and `enabled` are not overwritten if already set (only filled if NULL).

## Responses

### 200 OK (success)

```json
{
  "success": true,
  "data": {
    "report": {
      "output": "data/templates/SCUM_TEMPLATES.db",
      "synced": [640004],
      "missing": [],
      "counts": {
        "requested": 1,
        "synced": 1,
        "missing": 0
      }
    },
    "invalid": [],
    "catalog": {
      "ssm_db_path": "data/SSM.db",
      "upserted": 1,
      "skipped": 0,
      "name_source_db": "C:\\...\\data\\templates\\SCUM_TEMPLATES.db",
      "defaults": {
        "code": "template_vehicle_entity_id",
        "setup": "<template id as string>",
        "display_name": "<template id as string>",
        "price": 0,
        "enabled": 0
      }
    }
  }
}
```

### 409 Conflict (SCUMServer running)

When the server is running and `force=false`:

```json
{
  "success": false,
  "error": "SCUMServer is running. Stop the server before syncing templates.",
  "code": "SERVER_RUNNING"
}
```

### 400 Bad Request

Examples:

- Missing `source_scum_db`
- `source_scum_db` file does not exist
- `ids` missing or not a list

### 500 Internal Server Error

Unexpected backend errors.

---

# POST `/api/vehicles/admin/templates/reset`

Resets (clears) the templates database `SCUM_TEMPLATES.db` and optionally clears SSM tables used for vehicle shop testing.

## Intended usage

- Prepare a clean environment for testing template sync and vehicle spawning.
- Prevent shop/vehicle order side effects (including Discord notifications) during tests.
- Rebuild the vehicle catalog sequential codes from scratch (Option A).

## Safety / constraints

- By default, the endpoint refuses to run if `SCUMServer` is running.
- Use `force=true` only when you know what you are doing.

## Request

### Body

```json
{
  "force": true,
  "make_backup": true,
  "reset_catalog": true,
  "reset_orders": true
}
```

### Fields

- `force` (bool, optional; default `false`)
  - If `true`, bypasses the SCUMServer-running block.
- `make_backup` (bool, optional)
  - If `true`, creates a backup of `SCUM_TEMPLATES.db` (when implemented/available).
- `reset_catalog` (bool, optional; default `false`)
  - If `true`, clears `SSM.db -> vehicle_catalog`.
- `reset_orders` (bool, optional; default `false`)
  - If `true`, clears `SSM.db -> vehicle_order`.

## Behavior

- Clears all relevant tables in `data/templates/SCUM_TEMPLATES.db`.
- If requested, clears `vehicle_catalog` and/or `vehicle_order` in `data/SSM.db`.

## Responses

### 200 OK

Typical response:

```json
{
  "success": true,
  "data": {
    "templates_db": "data/templates/SCUM_TEMPLATES.db",
    "reset_catalog": true,
    "reset_orders": true
  }
}
```

### 409 Conflict (SCUMServer running)

If SCUMServer is running and `force=false`:

```json
{
  "success": false,
  "error": "SCUMServer is running. Stop the server before resetting templates.",
  "code": "SERVER_RUNNING"
}
```

### 500 Internal Server Error

Unexpected backend errors.

---

## Recommended test flow (Option A)

1) `POST /api/vehicles/admin/templates/reset` with:

```json
{
  "force": true,
  "reset_catalog": true,
  "reset_orders": true,
  "make_backup": true
}
```

2) `POST /api/vehicles/admin/templates/sync` with:

```json
{
  "source_scum_db": "@config",
  "ids": [640004],
  "force": true
}
```

Result:

- `SCUM_TEMPLATES.db` updated with template data
- `SSM.db.vehicle_catalog` populated
  - sequential `code`
  - `setup`/`display_name` from template name
  - defaults `enabled=0`, `price=0`
