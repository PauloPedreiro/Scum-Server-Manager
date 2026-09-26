# Player App - Inventario do Bau (SSM)

Este documento descreve o endpoint **player-scoped** para consultar o inventario (itens) dentro de um bau do jogador.

A consulta dos itens e feita diretamente no `SCUM.db` usando a conexao read-only via **copia compartilhada** (shared copy). O SSM persiste um snapshot no `SSM.db` para auditoria/caching.

---

## 1) Endpoint

- Metodo: `GET`
- Path: `/api/player/chests/<entity_id>/inventory`

---

## 2) Autenticacao e headers obrigatorios

Este endpoint e **player-scoped** e exige:

- `Authorization: Bearer <player_token>`
- `X-Server-Hash: <server_hash_do_servidor_selecionado>`

Regras:

- O `steam_id` e derivado do `player_token`.
- O SSM valida que o `X-Server-Hash` enviado no request e igual ao `server_hash` gravado no token.
- O SSM valida que o bau (`entity_id`) pertence ao jogador comparando com `chest_snapshot.steam_id`.

---

## 3) Fonte dos dados

- Leitura do inventario:
  - `SCUM.db` (via copia compartilhada)
  - Tabelas usadas:
    - `entity_component` (componente `Inventory` do bau)
    - `entity_inventory_component_entry` (itens e slots)
    - `entity` (classe do item)

- Persistencia de snapshot:
  - `SSM.db`
  - Tabelas criadas/atualizadas:
    - `chest_inventory_snapshot`
    - `chest_inventory_item`

---

## 4) Resposta (HTTP 200)

```json
{
  "success": true,
  "data": {
    "chest_entity_id": 123,
    "steam_id": "...",
    "player_name": "...",
    "scanned_at": "2026-02-18T04:00:00.000000",
    "items_total": 2,
    "counts": {
      "SomeItemClass": 2
    },
    "quantity_by_class": {
      "SomeItemClass": 10
    },
    "items": [
      {
        "item_entity_id": 456,
        "item_class": "SomeItemClass",
        "slot_index": 0,
        "quantity": 5
      }
    ],
    "catalog_new_items": 1
  },
  "timestamp": 0
}
```

Campos:

- `counts`: agregacao por `item_class`.
- `quantity_by_class`: soma de quantidades por `item_class`.
- `items`: lista de itens (cada item tem `item_entity_id`, `item_class`, `slot_index`).
- `items[].quantity`: quantidade do item (stack/ammo). Quando nao aplicavel, default = 1.
- `catalog_new_items`: quantos `item_class` novos foram inseridos automaticamente em `item_catalog` neste request.

---

## 5) Erros

### 5.1 Bau nao encontrado (ou nao pertence ao jogador)

- HTTP `404`

```json
{ "success": false, "error": "CHEST_NOT_FOUND" }
```

### 5.2 Bau nao encontrado no SCUM.db

- HTTP `404`

```json
{ "success": false, "error": "CHEST_NOT_FOUND_SCUMDB" }
```

---

## 6) Observacoes

- Este endpoint retorna apenas a classe do item (`entity.class`) e a posicao (`slot_index`).
- Se você precisar de mais detalhes (quantidade, qualidade, durabilidade, conteudo de itens dentro de itens), ai e necessario expandir a leitura para outras tabelas/estrutura do SCUM.

Sobre normalizacao (catalogo):

- Sempre que o endpoint detecta novos `item_class`, o SSM faz `INSERT OR IGNORE` em `item_catalog`.
- Os campos `display_name`, `category` e `icon` ficam vazios por padrao para serem preenchidos manualmente (ou via import futuro).
