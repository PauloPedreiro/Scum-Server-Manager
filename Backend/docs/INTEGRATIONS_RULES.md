# Integrations API Rules (/api/integrations)

Este documento define o padrão para criação/manutenção de endpoints públicos sob `POST /api/integrations/*`.

## 1) Padrão de rota

- **Prefixo fixo**: `/api/integrations/...`
- **Método**: `POST`
- **Ações explícitas** (evitar `action` no body)
  - Ex.: `/api/integrations/wallet/credit`, `/api/integrations/vip/activate`

## 2) Autenticação

- **Obrigatório**: header `X-Integration-Key: <key>`
- O endpoint deve rejeitar sem a chave:
  - `401` quando ausente/inválida

## 3) Payload padrão

- **Formato**: JSON
- Campos comuns:
  - `external_id` (string)
  - `steam_id` (string)
  - `meta` (obj, opcional)

## 4) Validação

- Validar JSON inválido / body ausente
- Validar campos obrigatórios (ex.: `external_id`, `steam_id`)
- Validar tipos/limites:
  - `steam_id` não vazio
  - `amount` (quando existir) deve ser inteiro > 0

## 5) Idempotência (quando há efeito colateral)

Para endpoints que alteram estado (ex.: crédito/débito VIP/Wallet), aplicar idempotência por `external_id`:

- `external_id` **obrigatório**
- Requisições repetidas com o mesmo `external_id` devem **retornar replay** do resultado anterior
- `external_id` deve ser **único por operação**
  - Reutilizar somente em retry do mesmo evento

## 6) Rate limit (quando aplicável)

- Aplicar rate limit em endpoints consultivos/abusáveis quando necessário
- Resposta padrão:
  - `429` com `retry_after_seconds`

## 7) Resposta e erros

- Resposta padronizada:
  - Sucesso: `{"success": true, ...}`
  - Erro: `{"success": false, "error": "ERROR_CODE"}`
- Usar códigos estáveis (ex.: `PLAYER_NOT_FOUND`, `INSUFFICIENT_FUNDS`)
- Usar status HTTP coerente:
  - `400` validação
  - `401` auth
  - `404` recurso/jogador não encontrado
  - `409` conflito
  - `429` rate limit
  - `500` erro interno

## 8) Persistência/Auditoria

- Para integrations, registrar:
  - `external_id`
  - payload (sem segredos)
  - resposta final
  - timestamps

## 9) Documentação e Postman (obrigatório)

Ao criar/alterar endpoints em `/api/integrations/*`, atualizar sempre:

- Documentação em `docs/endpoints/*.md`
- Postman collection `docs/endpoints/postman-collection.json`

### Postman: regra de `external_id`

- Em requests que exigem idempotência, usar `external_id` único por envio:
  - `postman:<acao>:{{$randomUUID}}`

## 10) Testes mínimos manuais

Antes de considerar o endpoint pronto:

- 1 caso de sucesso
- 1 caso de erro por validação (campos faltando)
- 1 caso idempotente (repetir o mesmo `external_id`)
- (quando houver) 1 caso de rate limit (confirmar `429` e `retry_after_seconds`)
