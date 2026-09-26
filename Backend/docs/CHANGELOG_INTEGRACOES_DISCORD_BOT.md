# Changelog — Integrações (Discord Bot)

## 2026-02-07

### Adicionado

#### API Key de integração (senha) via header
- Autenticação para integrações externas via header `X-Integration-Key`.
- A key é validada por **hash SHA-256** (o backend não armazena a senha em texto puro).
- A key deve ter **mínimo de 32 caracteres**.
- Atualização automática de `last_used_at` no uso da key.

#### Tabelas novas (SSM.db)
- `integration_keys`
  - Guarda metadados da key e o hash (`key_hash`).
  - Campos: `key_id`, `name`, `key_hash`, `enabled`, `created_at`, `last_used_at`.
- `integration_requests`
  - Auditoria + idempotência por request.
  - Campos: `req_id`, `key_id`, `endpoint`, `external_id`, `steam_id`, `request_json`, `response_json`, `status_code`, `created_at`.
  - Constraint/índice de idempotência: **UNIQUE (`key_id`, `endpoint`, `external_id`)**.

#### Endpoints admin (JWT + admin)
- `GET /api/shop/admin/integrations/keys`
  - Lista keys configuradas (metadados, sem expor senha).
- `POST /api/shop/admin/integrations/keys`
  - Cria/rotaciona key.
  - **Modo “1 ativa”**: ao criar uma nova, o backend **auto-desabilita** as anteriores.
- `PATCH /api/shop/admin/integrations/keys/<key_id>`
  - Ativa/desativa key.
  - Ao ativar (`enabled=1`), o backend desativa as demais.

#### Endpoints públicos de integração (sem JWT)
> Todos exigem `X-Integration-Key`.

- Wallet
  - `POST /api/integrations/wallet/credit`
    - Adiciona créditos ao jogador.
    - Requer `external_id` (idempotência).
  - `POST /api/integrations/wallet/debit`
    - Remove créditos do jogador.
    - Não permite saldo negativo.
    - Retorna `409 INSUFFICIENT_FUNDS` quando aplicável.

- VIP
  - `POST /api/integrations/vip/activate`
    - Ativa VIP somente se o jogador estiver no **Padrão**.
    - Ao ativar VIP, remove do **Padrão**.
  - `POST /api/integrations/vip/deactivate`
    - Desativa VIP.
    - Ao desativar VIP, volta automaticamente para o **Padrão**.

#### Segurança operacional
- Idempotência baseada em `external_id` registrada em `integration_requests`.
- Rate limit básico por key (janela de 60 segundos) retornando `429 RATE_LIMIT`.

### Alterado

#### Inicialização do banco
- `utils/database_initializer.py` atualizado para incluir as novas tabelas de integração em `EXPECTED_TABLES` e no fluxo de criação.

#### Documentação
- `docs/endpoints/SHOP_ENDPOINTS.md`
  - Nova seção “Integrações (Discord Bot)” com endpoints, headers e exemplos.
- `docs/endpoints/postman-collection.json`
  - Novas variáveis e requests para testar endpoints admin e públicos de integração.
- `docs/FRONTEND_INTEGRACAO_DISCORD_BOT.md`
  - Documento dedicado para orientar a implementação do fluxo no frontend.
