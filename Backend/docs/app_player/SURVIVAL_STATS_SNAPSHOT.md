# Player App - Survival Stats Snapshot (SSM)

Este documento descreve o endpoint Player-scoped para ler o snapshot de `survival_stats_snapshot` do jogador autenticado.

---

## 1) Endpoint

- Método: `GET`
- Path: `/api/player/survival-stats/snapshot`

---

## 2) Autenticação e headers obrigatórios

Este endpoint é **player-scoped** e exige:

- `Authorization: Bearer <player_token>`
- `X-Server-Hash: <server_hash_do_servidor_selecionado>`

Regras:

- O `steam_id` é derivado do `player_token` (nunca é aceito via query/body).
- O `X-Server-Hash` é validado contra o `server_hash` embutido no `player_token`.

---

## 3) Resposta (HTTP 200)

### 3.1 Quando existe snapshot

```json
{
  "success": true,
  "data": {
    "steam_id": "7656119...",
    "player_name": "PlayerName",
    "user_profile_id": 123,
    "snapshot_at": "2026-02-18T00:00:00.000000",
    "metrics": {
      "kills": 10,
      "deaths": 2,
      "shots_fired": 100,
      "shots_hit": 25
    },
    "derived": {
      "kdr": 5.0,
      "accuracy_percent": 25.0
    }
  },
  "timestamp": 0
}
```

Campos:

- `metrics`: contém todas as colunas da linha retornada exceto:
  - `user_profile_id`
  - `steam_id`
  - `player_name`
  - `snapshot_at`
- `derived.kdr`: calculado a partir de `kills`/`deaths` (se `deaths=0`, usa `kills` como KDR).
- `derived.accuracy_percent`: `shots_hit/shots_fired*100` (se `shots_fired=0`, retorna `null`).

### 3.2 Quando NAO existe snapshot

Se não existir linha na `survival_stats_snapshot` para o jogador:

```json
{
  "success": true,
  "data": null,
  "timestamp": 0
}
```

---

## 4) Erros comuns

### 4.1 Sem Authorization

- HTTP `401`

```json
{ "success": false, "error": "AUTH_REQUIRED" }
```

### 4.2 Token invalido/expirado

- HTTP `401`

```json
{ "success": false, "error": "INVALID_TOKEN" }
```

### 4.3 Sem X-Server-Hash

- HTTP `400`

```json
{ "success": false, "error": "SERVER_HASH_REQUIRED" }
```

### 4.4 X-Server-Hash diferente do token

- HTTP `403`

```json
{ "success": false, "error": "SERVER_HASH_MISMATCH" }
```

---

## 5) Observacao sobre a fonte dos dados

A tabela `survival_stats_snapshot` no `SSM.db` é alimentada pelo serviço `SurvivalStatsSyncService`, que sincroniza periodicamente dados do `SCUM.db` para o SSM.
