# Endpoint: Cadastro Manual de Item/Veículo no Catálogo da Loja

**Versão:** 1.0  
**Data:** 2026-05-21  
**Módulo:** Shop Admin  
**Autor:** SSM Backend Team

---

## Contexto

O sistema de loja possui um catálogo (`shop_catalog`) que armazena todos os itens e veículos disponíveis para compra, e uma tabela de ofertas (`shop_offer`) que define preço, quantidade e disponibilidade de cada item.

Até agora, itens eram adicionados ao catálogo via **scanner de baú** (leitura automática do SCUM.db). Veículos, porém, não podem ser escaneados dessa forma — eles precisam ser cadastrados manualmente pelo administrador, informando o nome do **blueprint** usado no comando in-game `#SpawnVehicle`.

Este endpoint permite que o administrador cadastre qualquer item ou veículo diretamente via interface, sem precisar do scanner.

---

## Endpoint

### `POST /api/shop/admin/catalog`

Cadastra um item ou veículo no catálogo da loja de forma atômica. Cria uma linha em `shop_catalog` e outra em `shop_offer` na mesma transação.

---

## Autenticação

Requer **JWT de administrador** no header `Authorization`.

```
Authorization: Bearer <token>
```

---

## Request

### Headers

| Header | Valor |
|---|---|
| `Content-Type` | `application/json` |
| `Authorization` | `Bearer <token>` |

### Body (JSON)

| Campo | Tipo | Obrigatório | Padrão | Descrição |
|---|---|---|---|---|
| `setup` | `string` | ✅ | — | Nome da classe/blueprint. Veículos usam prefixo `BPC_` ou `BP_` (ex: `BPC_SidecarBike`). Itens usam o nome do item SCUM. Deve ser único no catálogo. |
| `display_name` | `string` | ❌ | mesmo valor de `setup` | Nome amigável exibido na loja para o jogador. |
| `price` | `integer` | ❌ | `0` | Preço em coins (moeda da loja). Deve ser ≥ 0. |
| `qty` | `integer` | ❌ | `1` | Quantidade entregue por compra. Mínimo: 1. |
| `enabled` | `boolean` | ❌ | `true` | Se `true`, o item aparece e pode ser comprado na loja. Se `false`, fica oculto/desativado. |
| `code` | `integer` | ❌ | auto | Código numérico único do item. Se omitido, é calculado automaticamente como `MAX(code) + 1`. |

### Exemplos de Request

**Cadastrar um veículo:**
```json
{
  "setup": "BPC_SidecarBike",
  "display_name": "Sidecar Bike",
  "price": 25000,
  "qty": 1,
  "enabled": true
}
```

**Cadastrar um item comum:**
```json
{
  "setup": "BP_Weapon_AK74_C",
  "display_name": "AK-74",
  "price": 5000,
  "qty": 1,
  "enabled": true
}
```

**Cadastrar desativado (rascunho):**
```json
{
  "setup": "BPC_ATV",
  "display_name": "ATV (Em breve)",
  "price": 40000,
  "enabled": false
}
```

---

## Responses

### ✅ Sucesso — `201 Created`

```json
{
  "success": true,
  "data": {
    "code": 142,
    "setup": "BPC_SidecarBike",
    "display_name": "Sidecar Bike",
    "price": 25000,
    "qty": 1,
    "enabled": true
  }
}
```

| Campo | Tipo | Descrição |
|---|---|---|
| `code` | `integer` | Código único gerado (usar para edição futura via `PATCH /api/shop/admin/catalog/{code}`) |
| `setup` | `string` | Blueprint cadastrado |
| `display_name` | `string` | Nome exibido na loja |
| `price` | `integer` | Preço em coins |
| `qty` | `integer` | Quantidade por compra |
| `enabled` | `boolean` | Se está ativo na loja |

---

### ❌ Erros de Validação — `400 Bad Request`

**Campo `setup` ausente:**
```json
{
  "success": false,
  "error": "Missing required field: setup"
}
```

**`setup` já existe no catálogo:**
```json
{
  "success": false,
  "error": "Item/Vehicle with setup 'BPC_SidecarBike' already exists in catalog"
}
```

**Preço negativo:**
```json
{
  "success": false,
  "error": "Price must be a non-negative integer"
}
```

**`code` manual inválido:**
```json
{
  "success": false,
  "error": "Invalid code value"
}
```

**`code` manual já em uso:**
```json
{
  "success": false,
  "error": "Catalog code 99 already exists"
}
```

---

### ❌ Erro interno — `500 Internal Server Error`

```json
{
  "success": false,
  "error": "descrição do erro"
}
```

---

## Comportamento do Sistema

### Como identificar veículos vs. itens

O backend detecta automaticamente se o item é um **veículo** ou **item comum** pelo prefixo do campo `setup`:

| Prefixo | Tipo | Comando RCON usado na entrega |
|---|---|---|
| `BPC_` ou `BP_` (seguido de veículo) | Veículo | `#SpawnVehicle <setup> <x> <y> <z>` |
| Qualquer outro | Item | `#SpawnItem <steam_id> <setup> <qty>` |

> **Exemplos de blueprints de veículos conhecidos:**
> - `BPC_SidecarBike` — Sidecar Bike
> - `BPC_ATV` — ATV
> - `BPC_Riser` — Riser
> - `BPC_Lada` — Lada
> - `BPC_BRDM` — BRDM
>
> O administrador pode obter o blueprint exato executando `#SpawnVehicle` no jogo e observando o nome usado.

### Fluxo após o cadastro

1. Administrador cadastra o veículo via este endpoint
2. O item aparece na loja (se `enabled: true`)
3. O jogador realiza a compra pela interface
4. O backend executa `#SpawnVehicle <setup> <x> <y> <z>` via RCON **em tempo real**, na posição atual do jogador — **sem necessidade de restart do servidor**

---

## Sugestão de Interface (UX)

### Formulário de Cadastro

```
┌─────────────────────────────────────────────┐
│  Adicionar ao Catálogo da Loja              │
├─────────────────────────────────────────────┤
│  Blueprint / Setup *                        │
│  [ BPC_SidecarBike                       ]  │
│  (Ex: BPC_SidecarBike — copie do jogo)      │
│                                             │
│  Nome de Exibição                           │
│  [ Sidecar Bike                          ]  │
│                                             │
│  Preço (coins)                              │
│  [ 25000                                 ]  │
│                                             │
│  Quantidade por compra                      │
│  [ 1                                     ]  │
│                                             │
│  ☑ Ativo na loja                           │
│                                             │
│              [ Cancelar ] [ Adicionar ✓ ]   │
└─────────────────────────────────────────────┘
```

### Estados de resposta sugeridos

| Situação | Mensagem ao usuário |
|---|---|
| `201` | ✅ Item adicionado com sucesso ao catálogo! |
| `400` setup duplicado | ⚠️ Este blueprint já existe no catálogo. |
| `400` setup vazio | ⚠️ O campo Blueprint é obrigatório. |
| `400` preço inválido | ⚠️ O preço deve ser um número inteiro positivo. |
| `500` | ❌ Erro ao adicionar item. Tente novamente. |

---

---

## Atualização de Item/Veículo do Catálogo

### `PUT /api/shop/admin/catalog/<code_i>` ou `PATCH /api/shop/admin/catalog/<code_i>`

Atualiza um item ou veículo existente. Aceita atualizações parciais.

#### Request Body
Qualquer combinação dos campos: `setup`, `display_name`, `price`, `qty`, `enabled`.

#### Exemplo de Request (`PATCH /api/shop/admin/catalog/110`):
```json
{
  "setup": "Gasoline_Canister",
  "price": 1200
}
```

#### Response (`200 OK`):
```json
{
  "success": true,
  "data": {
    "code": 110,
    "setup": "Gasoline_Canister",
    "display_name": "Galão de Gasolina",
    "price": 1200,
    "qty": 1,
    "enabled": true
  }
}
```

---

## Exclusão de Item/Veículo do Catálogo

### `DELETE /api/shop/admin/catalog/<code_i>`

Exclui o item/veículo do catálogo (`shop_catalog`) e sua oferta correspondente (`shop_offer`).

#### Response (`200 OK`):
```json
{
  "success": true,
  "message": "Item/Vehicle with code 110 successfully deleted from catalog"
}
```

---

## Regra Especial de Entrega RCON: Limpeza de Sufixo `_ES` para Itens

No SCUM, os nomes dos itens obtidos via logs de baús/economia do jogo possuem o sufixo `_ES` (por exemplo, `Gasoline_Canister_ES`, `BP_Weapon_AK47_ES`).
No entanto, os comandos de spawn do servidor RCON (`#SpawnItem`) rejeitam itens com o sufixo `_ES`. O comando correto exige o nome base do item (ex: `Gasoline_Canister`, `BP_Weapon_AK47`).

### Tratamento Automático no Backend:
O `ShopDeliveryService` aplica uma limpeza transparente antes de enviar os comandos ao servidor:
1. Se o `setup` cadastrado no catálogo terminar com o sufixo `_ES` e **não for um veículo**:
   - O backend remove automaticamente os 3 caracteres finais (`_ES`) ao enviar o comando via RCON.
   - Exemplo: `Gasoline_Canister_ES` é enviado como `#SpawnItem Gasoline_Canister`.
2. Se o item for cadastrado sem o `_ES`, ele é enviado exatamente como cadastrado.
3. Se for detectado como um veículo (prefixo `BPC_` ou `BP_` reconhecido), o nome é mantido intacto no `#SpawnVehicle`.

*Dessa forma, os itens cadastrados via scanner (que vêm com `_ES`) funcionam via RCON sem necessidade de edição manual pelo administrador!*

---

## Endpoints relacionados

| Método | URL | Descrição |
|---|---|---|
| `GET` | `/api/shop/admin/catalog` | Lista todo o catálogo (incluindo desativados) |
| `POST` | `/api/shop/admin/catalog` | Cadastra novo item/veículo manualmente |
| `PUT/PATCH` | `/api/shop/admin/catalog/{code}` | Edita item/veículo existente (preço, nome, etc) |
| `DELETE` | `/api/shop/admin/catalog/{code}` | Exclui item/veículo do catálogo |
| `POST` | `/api/shop/admin/catalog/import` | Importação em massa via scanner de baú |
| `POST` | `/api/shop/admin/catalog/clear` | Remove todos os itens do catálogo |
| `GET` | `/api/shop/catalog` | Lista catálogo público (somente ativos) |

