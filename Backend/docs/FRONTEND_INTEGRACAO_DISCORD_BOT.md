# Integração Discord Bot (Frontend)

Este documento é direcionado ao dev do frontend para implementar a tela/fluxo de configuração da Integração (Discord Bot), que permite que um bot (ou sistema externo) chame endpoints do backend usando uma **senha (API Key)** enviada no header `X-Integration-Key`.

## Objetivo

Permitir que um admin configure e rotacione uma **Integration Key** (senha) via frontend, para que o bot consiga executar:

- Crédito de wallet (adicionar)
- Débito de wallet (remover sem deixar negativo)
- Ativar VIP
- Desativar VIP (e voltar automaticamente para o Padrão)

## Conceitos

- A “senha” é uma **API Key**.
- O backend **não armazena a senha em texto puro**. Ele armazena somente o **hash SHA-256**.
- A senha precisa ter **no mínimo 32 caracteres**.
- Modelo recomendado: **1 key ativa por vez**.
  - Ao criar uma nova, o backend **desabilita automaticamente as anteriores**.

## Autenticação

### Endpoints admin (usados pelo frontend)

- Usam JWT normal do painel.
- Header:

```http
Authorization: Bearer <JWT>
```

### Endpoints públicos de integração (usados pelo bot)

- Não usam JWT.
- Header:

```http
X-Integration-Key: <SENHA>
```

## Fluxo recomendado no Frontend

### 1) Tela “Integrações > Discord Bot”

A tela deve permitir:

- Visualizar a key atual (somente status/metadados, nunca a senha)
- Criar/rotacionar key (gerar senha forte e enviar ao backend)
- Desativar key (opcional)
- Mostrar instruções de como configurar o bot (copiar Base URL e exemplos)

### 2) Gerar senha no Frontend

Regras:

- Tamanho mínimo: **32 caracteres**
- Recomendações:
  - Usar `crypto.getRandomValues`
  - Preferir 32 bytes aleatórios e converter para Base64URL ou hex

Exemplo de estratégia (conceitual):

- Gerar 32 bytes aleatórios
- Transformar em string base64url (vai resultar em > 32 chars)

### 3) Criar/rotacionar key (backend)

- O frontend gera a senha
- O frontend chama o endpoint admin com `name` e `key`
- Se sucesso, o frontend deve:
  - Mostrar a senha **para copiar**
  - Exibir aviso: “Essa senha será exibida apenas agora. Salve em local seguro.”

### 4) Guardar senha no bot

Fora do escopo do backend. O bot deve armazenar a senha como o dev do bot preferir (ex.: `.env`, secrets, etc.).

## Endpoints (para o Frontend)

### Listar keys

`GET /api/shop/admin/integrations/keys`

**Auth**: `Bearer <JWT>`

**Resposta 200**

```json
{
  "success": true,
  "data": {
    "items": [
      {
        "key_id": "...",
        "name": "discord-bot",
        "enabled": 1,
        "created_at": "2026-02-07 14:00:00",
        "last_used_at": "2026-02-07 14:10:00"
      }
    ],
    "count": 1
  }
}
```

Notas:

- `enabled` é `0/1`.
- `last_used_at` pode ser `null`.

### Criar/rotacionar key (1 ativa)

`POST /api/shop/admin/integrations/keys`

**Auth**: `Bearer <JWT>`

**Body**

```json
{
  "name": "discord-bot",
  "key": "SENHA_COM_NO_MINIMO_32_CARACTERES"
}
```

**Validações**

- Se `key.length < 32` retorna `400`.
- Ao criar uma nova key, o backend executa:
  - desabilita todas as anteriores
  - cria a nova como `enabled = 1`

**Resposta 201**

```json
{
  "success": true,
  "data": {
    "key_id": "...",
    "name": "discord-bot",
    "enabled": 1
  }
}
```

### Ativar/desativar uma key específica

`PATCH /api/shop/admin/integrations/keys/<key_id>`

**Auth**: `Bearer <JWT>`

**Body**

```json
{ "enabled": 0 }
```

Notas:

- Se enviar `{ "enabled": 1 }`, o backend desabilita as demais e ativa apenas essa.

## Endpoints (para referência do Frontend / instruções ao usuário)

Estes endpoints são usados pelo bot e podem ser exibidos no frontend como “como integrar”.

### Wallet credit

`POST /api/integrations/wallet/credit`

Header:

```http
X-Integration-Key: <SENHA>
```

Body:

```json
{
  "external_id": "discord:credit:123",
  "steam_id": "76561198012345678",
  "amount": 100,
  "meta": { "source": "discord" }
}
```

### Wallet debit (sem saldo negativo)

`POST /api/integrations/wallet/debit`

Body:

```json
{
  "external_id": "discord:debit:123",
  "steam_id": "76561198012345678",
  "amount": 50,
  "meta": { "source": "discord" }
}
```

Erros importantes:

- `409` com `INSUFFICIENT_FUNDS`

### VIP activate

`POST /api/integrations/vip/activate`

Body:

```json
{
  "external_id": "discord:vip_on:123",
  "steam_id": "76561198012345678",
  "meta": { "source": "discord" }
}
```

### VIP deactivate (volta para Padrão)

`POST /api/integrations/vip/deactivate`

Body:

```json
{
  "external_id": "discord:vip_off:123",
  "steam_id": "76561198012345678",
  "meta": { "source": "discord" }
}
```

## UX / Regras de tela (sugestão)

- Mostrar um bloco “Status”:
  - Key ativa: `enabled=1`
  - Criada em: `created_at`
  - Último uso: `last_used_at`

- Ações:
  - Botão “Gerar nova senha (rotacionar)”
  - Botão “Desativar key atual” (opcional)

- Alertas:
  - “A senha só será exibida uma vez.”
  - “Use HTTPS em produção.”

## Erros e mensagens que o frontend pode exibir

- `401/403` com JWT: usuário não autenticado ou sem permissão admin
- `400` ao criar key: `key must be at least 32 characters`
- `409` ao criar key: `KEY_ALREADY_EXISTS`

## Arquivo relacionado

- Endpoints detalhados do shop: `docs/endpoints/SHOP_ENDPOINTS.md`
- Coleção Postman: `docs/endpoints/postman-collection.json`
