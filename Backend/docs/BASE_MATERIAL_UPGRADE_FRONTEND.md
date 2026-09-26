# Integração Frontend (Admin) - Base Material Upgrade (Flag Upgrade)

Este documento descreve o contrato de integração para a funcionalidade de **upgrade de base** (também referido como *flag upgrade* / **base material**) no painel Admin.

## Autenticação

Todos os endpoints abaixo exigem:

- Autenticação (`@require_auth`)
- Perfil Admin (`@require_admin`)

### Header

- `Authorization: Bearer <token>`

---

# 1) Listar Flags/Owners (seleção da base)

## Endpoint

- `GET /api/admin/flags/owners`

### Query params

- `page` (int, default `1`)
- `page_size` (int, default `50`)

### Response 200

```json
{
  "success": true,
  "data": {
    "flags": [
      {
        "flag_id": 123,
        "owner": "NomeDoClãOuDono",
        "owner_type": "squad|player|unknown",
        "elements": 456,
        "last_seen_at": "2026-02-23T20:00:00Z"
      }
    ],
    "total": 999,
    "page": 1,
    "page_size": 50
  }
}
```

### Observações de UI

- Use este endpoint para popular dropdown/tabela para o admin escolher a `flag_id`.
- Se `owner` vier vazio/desconhecido, a flag ainda pode existir e ser selecionável (fica a critério da regra no frontend).

---

# 2) Simular upgrade (prévia antes de agendar)

## Endpoint

- `POST /api/admin/base-material/dry-run`

### Body (JSON)

```json
{
  "flag_id": 123,
  "target_level": 5,
  "fallback_lowest": true,
  "auto_enrich_whitelist": true
}
```

### Regras

- `target_level` deve ser entre `1..5`.
- `fallback_lowest`:
  - `true`: se não existir mapping exato para o level, tenta usar o melhor level disponível **menor ou igual** ao alvo (`<= target_level`).
    - Se não existir nenhum `<= target_level` (caso raro), usa o menor level disponível.
  - `false`: se não tiver mapping, conta como “sem mapping” e não troca.
- `auto_enrich_whitelist` (default `true`):
  - Quando `true`, o backend enriquece automaticamente o `scum_base_template.db` (somente a tabela `asset_whitelist`) com quaisquer `asset` novos observados na base (SCUM.db) que ainda não existam no template.
  - Isto reduz (ou elimina) `stats.not_whitelisted` ao longo do tempo conforme novas estruturas aparecem.
  - **Importante:** isto **não** cria/atualiza mappings de nível em `family_level_asset` (não “adivinha” upgrades). Se uma família não tiver mapping para algum level, continuará contando em `no_mapping`.

### Response 200

```json
{
  "success": true,
  "data": {
    "flag_id": 123,
    "internal_base_id": 456,
    "target_level": 5,
    "stats": {
      "total": 200,
      "not_whitelisted": 10,
      "no_family": 0,
      "no_mapping": 3,
      "fallback_lowest_used": 2,
      "already_target": 50,
      "to_change": 140
    },
    "changes_sample": [
      {
        "element_id": 111,
        "old_asset": "BP_WoodWall_A",
        "new_asset": "BP_MetalWall_A",
        "from_asset": "BP_WoodWall_A",
        "to_asset": "BP_MetalWall_A",
        "family_key": "Wall"
      }
    ],
    "changes_sample_truncated": true
  }
}
```

### Debug (observabilidade)

Quando disponível, `data.debug` pode incluir:

- `auto_whitelisted` (int): quantos assets foram inseridos no `asset_whitelist` automaticamente neste dry-run.
- `auto_whitelisted_assets` (array): amostra (até 25) dos assets inseridos automaticamente.

### Erros comuns

- `404`: `FLAG_NOT_FOUND`
- `400`: `TARGET_LEVEL_FORBIDDEN` (nível alvo não permitido para essa base)
- `400`: `INVALID_FLAG_ID`, `INVALID_TARGET_LEVEL`, `TARGET_LEVEL_INVALID_RANGE`
- `500`: problemas de arquivo/DB (ex.: `SCUM_DB_NOT_FOUND`, `TEMPLATE_DB_NOT_FOUND`)

Observação: o backend retorna `code` (e opcionalmente `details`) junto com `error`.

### Observações de UI

- Mostrar um resumo com `stats.to_change` e contadores relevantes (`not_whitelisted`, `no_mapping`, etc.).
- `changes_sample` é apenas uma amostra (não é lista completa).

---

# 3) Agendar upgrade (executa no próximo restart automático)

## Endpoint

- `POST /api/admin/base-material/schedule`

### Body (JSON)

```json
{
  "flag_id": 123,
  "target_level": 5,
  "fallback_lowest": true,
  "run_now_if_offline": true
}
```

### Comportamento (regra crítica)

- O endpoint **NÃO dispara restart**.
- Se o servidor estiver **online**:
  - o job fica **pendente** e será executado no **próximo restart automático** (janela offline do restart).
- Se o servidor estiver **offline** e `run_now_if_offline=true`:
  - o backend pode executar imediatamente (ainda assim sem disparar restart).

### Response 200

```json
{
  "success": true,
  "data": {
    "job_id": "uuid-do-job",
    "scheduled": true,
    "deduplicated": false,
    "executed_now": false,
    "run_result": null
  }
}
```

### Se executar na hora (offline)

```json
{
  "success": true,
  "data": {
    "job_id": "uuid-do-job",
    "scheduled": true,
    "executed_now": true,
    "run_result": {
      "claimed": 1,
      "updated": 140,
      "no_changes": 0,
      "failed": 0,
      "job_ids": ["uuid-do-job"]
    }
  }
}
```

### Observabilidade (Discord)

O backend envia logs informativos para o webhook **`shop-log`**:

- `📌 Base Material Upgrade Scheduled`
- `🧱 Base Material Upgrade Completed`
- `🔴 Base Material Upgrade Failed`

O frontend não depende disso para funcionar; é apenas para acompanhamento.

---

# 4) Listar jobs agendados / status

## Endpoint

- `GET /api/admin/base-material/jobs`

### Query params

- `status` (opcional) ex.: `pending`, `done`, `failed` (conforme gravado pelo backend)
- `limit` (default `50`, max `200`)
- `offset` (default `0`)

### Response 200 (exemplo)

```json
{
  "success": true,
  "data": {
    "jobs": [
      {
        "job_id": "uuid",
        "flag_id": 123,
        "target_level": 5,
        "fallback_lowest": true,
        "status": "pending",
        "attempt_count": 0,
        "next_attempt_at": null,
        "locked_by": null,
        "locked_at": null,
        "error_code": null,
        "error_message": null,
        "created_at": "2026-02-23 20:00:00",
        "updated_at": "2026-02-23 20:00:00"
      }
    ],
    "total": 10,
    "limit": 50,
    "offset": 0
  }
}
```

---

# Fluxo recomendado no Frontend

- 1) Carregar flags: `GET /api/admin/flags/owners`
- 2) Admin escolhe `flag_id`, define `target_level` e `fallback_lowest`
- 3) Prévia: `POST /api/admin/base-material/dry-run`
- 4) Confirmar e agendar: `POST /api/admin/base-material/schedule`
- 5) Feedback:
  - `executed_now=false`: “Agendado. Será aplicado no próximo restart automático.”
  - `executed_now=true`: mostrar `run_result`
- 6) (Opcional) Tela de acompanhamento: `GET /api/admin/base-material/jobs`
