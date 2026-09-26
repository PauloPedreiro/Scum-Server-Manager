# Player App - Banco / Saldos em Tempo Real (SSM)

Este documento descreve o endpoint player-scoped para consultar o saldo **atual** do jogador a partir da tabela `bank_accounts_current`.

---

## 1) Autenticacao

- Header `Authorization: Bearer <player_token>`
- Header `X-Server-Hash: <server_hash>` (mesma regra dos demais endpoints player-scoped)

---

## 2) Endpoint

### 2.1) Saldo atual do jogador

- **Metodo:** `GET`
- **Path:** `/api/player/bank-account/current`

A resposta e baseada em uma linha por jogador na tabela `bank_accounts_current` (chave `steam_id`).

---

## 3) Contrato de dados (semantica)

Os campos refletem tres valores de saldo e um total monetario:

- `money_in_hand`: **dinheiro em maos** (cash) do jogador.
- `money_in_bank`: **dinheiro na conta bancaria**.
- `money_total`: **sempre** `money_in_hand + money_in_bank`.
- `gold`: **gold separado** (na conta). **Nao soma** com `money_total`.

### 3.1) Regra explicita (importante)

- `money_total` **NAO inclui** `gold`.
- `gold` deve ser exibido separadamente na UI.

---

## 4) Resposta

### 4.1) Caso normal (conta existe)

HTTP `200`

```json
{
  "success": true,
  "data": {
    "account_number": "12345",
    "balances": {
      "money_in_hand": 813.0,
      "money_in_bank": 28653.0,
      "money_total": 29466.0,
      "gold": 120.0
    },
    "meta": {
      "has_data": true,
      "updated_at": "2026-02-20T18:16:00",
      "source": "bank_transaction",
      "last_transaction_ts": "2026-02-20T18:15:40"
    }
  },
  "timestamp": 1739990000.0
}
```

### 4.2) Caso jogador ainda nao tem conta / nao existe linha

HTTP `200`

**Regra:** quando nao existir registro em `bank_accounts_current` para o jogador, o endpoint retorna tudo zerado.

```json
{
  "success": true,
  "data": {
    "account_number": null,
    "balances": {
      "money_in_hand": 0.0,
      "money_in_bank": 0.0,
      "money_total": 0.0,
      "gold": 0.0
    },
    "meta": {
      "has_data": false,
      "updated_at": null,
      "source": null,
      "last_transaction_ts": null
    }
  },
  "timestamp": 1739990000.0
}
```

---

## 5) Campos de meta

- `meta.updated_at`: quando o registro foi atualizado no `SSM.db`.
- `meta.source`: fonte do ultimo update (ex.: reconcile vs processador de transacoes).
- `meta.last_transaction_ts`: timestamp do ultimo evento/transacao conhecido.

---

## 6) Erros

### 6.1) Token invalido/ausente

HTTP `401`

```json
{ "success": false, "error": "AUTH_REQUIRED" }
```

### 6.2) Servico indisponivel

HTTP `503`

```json
{ "success": false, "error": "SERVICE_UNAVAILABLE" }
```
