# Vehicle Catalog API (Frontend)

Este documento descreve os endpoints de catálogo de veículos (`vehicle_catalog`) para consumo pelo frontend.

## Autenticação

Todos os endpoints abaixo exigem JWT.

- Header obrigatório:
  - `Authorization: Bearer <token>`

O token é obtido no login:
- `POST /api/auth/login`

## Modelo de dados (resumo)

Cada item do catálogo representa um veículo disponível para compra/spawn.

Campos retornados:
- `code` (int): identificador do item no catálogo.
- `setup` (string): nome original/técnico (igual `shop_catalog.setup`).
- `display_name` (string): nome de exibição editável.
- `name` (string): nome final para exibir no frontend (fallback: `display_name` ou `setup`).
- `template_vehicle_entity_id` (int): ID do template no `SCUM_TEMPLATES.db`.
- `price` (int): preço em pontos/moeda do sistema.
- `enabled` (bool): se o item está habilitado no catálogo (apenas no endpoint admin).

## Responses padrão

- Sucesso:
  - `{"success": true, "data": ...}`
- Erro:
  - `{"success": false, "error": "..."}`

---

## 1) Listar catálogo público (somente habilitados)

`GET /api/vehicles/catalog`

### Regras
- Retorna **somente** itens com `enabled=1`.

### Exemplo de resposta (200)

```json
{
  "success": true,
  "data": {
    "items": [
      {
        "code": 1,
        "setup": "Laika",
        "display_name": "Laika",
        "name": "Laika",
        "template_vehicle_entity_id": 12345,
        "price": 25000
      }
    ],
    "count": 1
  }
}
```

---

## 2) Listar catálogo admin (todos)

`GET /api/vehicles/admin/catalog`

### Autorização
- Requer usuário com permissão de admin.

### Exemplo de resposta (200)

```json
{
  "success": true,
  "data": {
    "items": [
      {
        "code": 1,
        "setup": "Laika",
        "display_name": "Laika",
        "name": "Laika",
        "template_vehicle_entity_id": 12345,
        "price": 25000,
        "enabled": true
      },
      {
        "code": 2,
        "setup": "Tractor",
        "display_name": "Tractor",
        "name": "Tractor",
        "template_vehicle_entity_id": 67890,
        "price": 0,
        "enabled": false
      }
    ],
    "count": 2
  }
}
```

---

## 3) Atualizar item do catálogo (admin) — `display_name`, `price` e `enabled`

`PATCH /api/vehicles/admin/catalog/<code>`

### Autorização
- Requer usuário com permissão de admin.

### Body (JSON)
Campos aceitos (opcionais):
- `display_name` (string)
- `price` (int, `>= 0`)
- `enabled` (boolean)

Observação:
- Se nenhum campo válido for enviado, retorna `400` com `NO_CHANGES`.

### Exemplo de request

```http
PATCH /api/vehicles/admin/catalog/1
Authorization: Bearer <token>
Content-Type: application/json

{
  "display_name": "Laika (VIP)",
  "price": 30000,
  "enabled": true
}
```

### Exemplo de resposta (200)

```json
{
  "success": true,
  "data": {
    "item": {
      "code": 1,
      "setup": "Laika",
      "display_name": "Laika (VIP)",
      "name": "Laika (VIP)",
      "template_vehicle_entity_id": 12345,
      "price": 30000,
      "enabled": true
    }
  }
}
```

### Erros possíveis

- `400 price must be >= 0`
  - Quando `price < 0`.

- `400 NO_CHANGES`
  - Quando o body não contém `price` nem `enabled`.

- `400 invalid boolean`
  - Quando `enabled` não é interpretável como boolean.

- `404 CATALOG_ITEM_NOT_FOUND`
  - Quando não existe `vehicle_catalog.code` com o `<code>` informado.

---

## Notas para o frontend

- O endpoint público (`/api/vehicles/catalog`) é o recomendado para montar a tela de compra, pois já filtra somente itens habilitados.
- Para tela de administração, usar `/api/vehicles/admin/catalog` para exibir e permitir toggle de `enabled` e ajuste de `price` via PATCH.
