# Frontend Handoff - Playtime Rewards (Padrão + VIP)

Base URL:
```
http://localhost:3000
```

Autenticação:
```
Authorization: Bearer <token>
Content-Type: application/json
```

## Objetivo (regra de negócio)

- **Regra Padrão**: o jogador só entra no Padrão depois de cadastrar o baú (mailbox) via comando `/mail <id>`.
- **Regra VIP**: só pode virar VIP se já estiver no Padrão.
- **Limpeza (promoção VIP)**: ao promover para VIP, o jogador é removido do Padrão.
- **Exclusividade/Substituição**: regras com `exclusive=1` substituem as não-exclusivas (quando o jogador é elegível para uma exclusiva, ele não recebe regras `exclusive=0`).

## Identificação das regras

O backend identifica as regras por `name`:

- **Padrão**: `name == "Padrão"`
- **VIP**: `name == "VIP"`

Recomendação: manter esses nomes estáveis e únicos.

## Automação do Padrão via /mail

Quando o jogador registra mailbox:

- O comando `/mail <id>` grava em `player_mailbox`.
- Após gravar, o backend tenta inserir o `steam_id` nos targets da regra `name="Padrão"` (se existir).

Consequência:

- Jogador sem mailbox: não está no Padrão, não recebe playtime reward.
- Jogador com mailbox: entra no Padrão automaticamente.

## Endpoints Admin (UI)

### Listar regras
`GET /api/shop/admin/rewards/playtime-rules`

### Criar regra
`POST /api/shop/admin/rewards/playtime-rules`

Campos relevantes:

- `enabled`: 0/1
- `exclusive`: 0/1
- `audience_type`: `all|list`
- `points_per_hour`: int
- `max_hours_per_run`: int

Neste modelo, **Padrão e VIP devem ser `audience_type="list"`**.

### Editar regra
`PATCH /api/shop/admin/rewards/playtime-rules/<rule_id>`

### Deletar regra
`DELETE /api/shop/admin/rewards/playtime-rules/<rule_id>`

### Targets (listas)

- Listar targets: `GET /api/shop/admin/rewards/playtime-rules/<rule_id>/targets`
- Adicionar target: `POST /api/shop/admin/rewards/playtime-rules/<rule_id>/targets`
- Remover target: `DELETE /api/shop/admin/rewards/playtime-rules/<rule_id>/targets/<steam_id>`

## Promoção VIP (regra do backend)

Ao adicionar `steam_id` em targets de uma regra cujo `name == "VIP"`:

- O backend exige que o `steam_id` já esteja nos targets da regra `name == "Padrão"`.
- Se permitido, ele:
  - adiciona em VIP
  - remove do Padrão (limpeza)

### Erros esperados (VIP)

No `POST .../targets` para regra `VIP`:

- `DEFAULT_RULE_NOT_FOUND` (HTTP 400): regra `"Padrão"` não existe.
- `NOT_IN_DEFAULT_RULE` (HTTP 400): jogador não está no Padrão ainda.

## Recomendação de configuração

- Regra **Padrão**:
  - `name`: `Padrão`
  - `audience_type`: `list`
  - `exclusive`: `0`
  - `enabled`: `1`

- Regra **VIP**:
  - `name`: `VIP`
  - `audience_type`: `list`
  - `exclusive`: `1`
  - `enabled`: `1`

Resultado:

- VIP recebe somente VIP.
- Padrão recebe somente Padrão.
