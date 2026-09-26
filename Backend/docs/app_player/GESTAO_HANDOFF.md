# Handoff para Dev do Gestão - Player App (SSM)

Este documento descreve o que o **Gestão** precisa implementar/ajustar para suportar o **Player App**, usando o **SSM Backend** como origem dos dados.

---

## 1) Como o Gestão descobre o `backend_base_url` de cada servidor

O SSM já sincroniza com o Gestão (sync de rankings/players) e grava auditoria local em:

- `SSM/data/logs/gestao_sync/*.json`

No payload enviado para o Gestão (`POST /api/v1/servers/sync`), o SSM agora inclui em `payload.server_info` os campos:

- `backend_base_url`
- `backend_base_url_source`
- `backend_base_url_checked`

### Exemplo real (extraído do log)

```json
"server_info": {
  "name": "Meu Servidor SCUM",
  "region": "america_south",
  "version": "3.0.0",
  "max_players": 64,
  "current_players": 0,
  "is_online": false,
  "backend_base_url": "http://177.3.52.227:3000",
  "backend_base_url_source": "detected",
  "backend_base_url_checked": false
}
```

### Significado dos campos

- `backend_base_url`
  - URL base pública do backend do SSM que o Player App deve chamar.
  - Exemplo: `http://177.3.52.227:3000`

- `backend_base_url_source`
  - `configured`: veio do `config.public.backend_base_url` no SSM (admin configurou explicitamente)
  - `detected`: SSM detectou IP externo e montou `http://IP:3000`

- `backend_base_url_checked`
  - `true`: SSM conseguiu confirmar `GET {backend_base_url}/api/health` com HTTP 200
  - `false`: não confirmou (porta fechada, URL incorreta, offline etc.)

### Regras recomendadas no Gestão

- Armazenar `backend_base_url`, `backend_base_url_source`, `backend_base_url_checked` por servidor.
- Armazenar também `backend_base_url_last_seen_at` (timestamp do último sync que trouxe esses campos).
- Se `backend_base_url_source == configured`, considerar como valor preferencial.

---

## 2) Endpoint no Gestão: listar servidores para o jogador

O Player App precisa obter do Gestão uma lista de servidores em que o jogador pode entrar.

### Recomendação de endpoint

- `GET /api/player/servers`

### Recomendação de autenticação

- Autenticar o jogador no Gestão (método atual do Gestão)
- Retornar apenas servidores acessíveis a este jogador

### Resposta recomendada

```json
{
  "success": true,
  "data": [
    {
      "server_hash": "<hash>",
      "server_name": "Meu Servidor SCUM",
      "backend_base_url": "http://177.3.52.227:3000",
      "backend_base_url_checked": false,
      "backend_base_url_source": "detected"
    }
  ]
}
```

### Observação

- O Player App usará `backend_base_url` para chamar diretamente o SSM:
  - `{backend_base_url}/api/player/...`

---

## 3) Fluxo de login do jogador no servidor (exchange)

O SSM terá um endpoint `POST /api/player/auth/exchange`.

Para isso, o SSM precisa validar/obter o `steam_id` do jogador consultando o Gestão.

### O que o Gestão precisa expor (recomendado)

Um endpoint que, dado o token/sessão do jogador no Gestão, devolva a identidade mínima do jogador:

- `steam_id`

#### Recomendação de endpoint

- `GET /api/v1/player/me`

#### Request (SSM -> Gestão)

Headers sugeridos:

- `Authorization: Bearer <gestao_access_token_do_jogador>`

#### Response (Gestão -> SSM)

```json
{
  "steam_id": "7656119..."
}
```

### Observação importante

- O SSM **não usa** `discord_id`.
- O `steam_id` é suficiente.

---

## 4) Regras de segurança (importantes)

- A API key do servidor (licença) não deve ser exposta no Player App.
- O Player App deve falar com o SSM apenas por:
  - `backend_base_url` (descoberto via Gestão)
  - token do jogador emitido pelo SSM (Player JWT)

---

## 5) Checklist rápido para o dev do Gestão

- Consumir e persistir do `/api/v1/servers/sync` os campos:
  - `server_info.backend_base_url`
  - `server_info.backend_base_url_source`
  - `server_info.backend_base_url_checked`

- Expor `GET /api/player/servers` retornando `backend_base_url` por servidor.

- Expor `GET /api/v1/player/me` retornando pelo menos `steam_id` a partir do token do jogador no Gestão.
