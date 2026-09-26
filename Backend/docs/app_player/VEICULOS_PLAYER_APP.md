# Player App - Veiculos do Jogador (SSM)

Este documento descreve os endpoints **player-scoped** para consultar os veiculos registrados do jogador autenticado.

Os dados vem da tabela `vehicle_current_ownership` (populada automaticamente pelo sistema de logs de ownership do SSM).

---

## 1) Autenticacao

Todos os endpoints exigem:

- Header `Authorization: Bearer <player_token>` (JWT emitido pelo SSM via exchange)

---

## 2) Endpoints

### 2.1) Listar veiculos

- **Metodo:** `GET`
- **Path:** `/api/player/vehicles`
- **Query params (opcionais):**
  - `status` - Filtrar por status (valores: `0`=Ativo, `1`=Inativo, `2`=Desaparecido, `3`=Destruido). Aceita multiplos separados por virgula: `?status=0,1`
  - `limit` - Max itens por pagina (default: 200, max: 1000)
  - `offset` - Paginacao (default: 0)

#### Resposta (HTTP 200)

```json
{
  "success": true,
  "data": {
    "steam_id": "76561198040636105",
    "total": 5,
    "count": 5,
    "limit": 200,
    "offset": 0,
    "summary": {
      "by_status": { "0": 3, "2": 2 },
      "by_class": { "Wolfswagen": 2, "Rager": 1, "Dirtbike": 2 }
    },
    "vehicles": [
      {
        "entity_id": 12345,
        "vehicle_entity_id": 67890,
        "steam_id": "76561198040636105",
        "player_name": "NomeDoJogador",
        "vehicle_class": "BPC_Wolfswagen",
        "vehicle_class_display": "Wolfswagen",
        "vehicle_asset_id": "...",
        "is_vehicle_functional": 1,
        "status": 0,
        "status_text": "Ativo",
        "location": { "x": 1234.5, "y": 5678.9, "z": 100.0 },
        "last_ownership_change": "2026-02-18T12:00:00",
        "container_class": "...",
        "updated_at": "2026-02-18T12:00:00"
      }
    ]
  },
  "timestamp": 1739900000.0
}
```

Campos:

- `total`: total de veiculos do jogador (respeitando filtro de status).
- `summary.by_status`: contagem por status (0/1/2/3).
- `summary.by_class`: contagem por tipo de veiculo (nome amigavel).
- `vehicles[]`: lista de veiculos.
- `vehicles[].status`: `0`=Ativo, `1`=Inativo, `2`=Desaparecido, `3`=Destruido.
- `vehicles[].status_text`: label textual do status.
- `vehicles[].vehicle_class_display`: nome amigavel do veiculo.
- `vehicles[].is_vehicle_functional`: `1` = funcional, `0` = nao funcional.
- `vehicles[].location`: coordenadas do ultimo registro (pode ser `null`).

---

### 2.2) Resumo de veiculos

- **Metodo:** `GET`
- **Path:** `/api/player/vehicles/summary`

#### Resposta (HTTP 200)

```json
{
  "success": true,
  "data": {
    "steam_id": "76561198040636105",
    "total": 5,
    "by_status": {
      "0": { "count": 3, "label": "Ativo" },
      "2": { "count": 2, "label": "Desaparecido" }
    },
    "by_class": {
      "Wolfswagen": 2,
      "Rager": 1,
      "Dirtbike": 2
    }
  },
  "timestamp": 1739900000.0
}
```

---

### 2.3) Detalhe de um veiculo

- **Metodo:** `GET`
- **Path:** `/api/player/vehicles/<vehicle_entity_id>`
- **Query params (opcionais):**
  - `history=true` - Incluir historico de ownership do veiculo.
  - `history_limit` - Max registros de historico (default: 20, max: 100).

#### Resposta (HTTP 200)

```json
{
  "success": true,
  "data": {
    "vehicle": {
      "entity_id": 12345,
      "vehicle_entity_id": 67890,
      "steam_id": "76561198040636105",
      "player_name": "NomeDoJogador",
      "vehicle_class": "BPC_Wolfswagen",
      "vehicle_class_display": "Wolfswagen",
      "status": 0,
      "status_text": "Ativo",
      "is_vehicle_functional": 1,
      "location": { "x": 1234.5, "y": 5678.9, "z": 100.0 },
      "last_ownership_change": "2026-02-18T12:00:00"
    },
    "history": [
      {
        "id": 1,
        "entity_id": 12345,
        "vehicle_entity_id": 67890,
        "steam_id": "76561198040636105",
        "player_name": "NomeDoJogador",
        "ownership_type": "claimed",
        "timestamp": "2026-02-17T10:00:00"
      }
    ],
    "history_count": 1
  },
  "timestamp": 1739900000.0
}
```

Nota: `history` e `history_count` so aparecem se `?history=true`.

---

## 3) Erros

### 3.1 Veiculo nao encontrado (ou nao pertence ao jogador)

- HTTP `404`

```json
{ "success": false, "error": "VEHICLE_NOT_FOUND" }
```

### 3.2 Servico indisponivel

- HTTP `503`

```json
{ "success": false, "error": "SERVICE_UNAVAILABLE" }
```

### 3.3 Token invalido

- HTTP `401`

```json
{ "success": false, "error": "AUTH_REQUIRED" }
```

---

## 4) Status de veiculos

| Codigo | Label          | Descricao                                        |
|--------|----------------|--------------------------------------------------|
| 0      | Ativo          | Veiculo existe e esta no mundo                   |
| 1      | Inativo        | Veiculo nao verificado recentemente              |
| 2      | Desaparecido   | Veiculo nao encontrado no SCUM.db (pode ter sido destruido) |
| 3      | Destruido      | Veiculo confirmado como destruido                |

---

## 5) Origem dos dados

Os dados vem da tabela `vehicle_current_ownership`, que e atualizada automaticamente pelo SSM:

- Quando um jogador registra/clama um veiculo (via logs de chest_ownership).
- Quando ha transferencia de propriedade.
- Pelo servico `VehicleVerificationService` que verifica periodicamente se veiculos ainda existem no SCUM.db (marca como status=2 quando desaparecem).
