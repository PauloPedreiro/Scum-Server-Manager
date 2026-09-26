## API de Attributes (Frontend)

> [!IMPORTANT]
> **Nota de Fluxo**: Com a nova progressão de atributos baseada em comandos de chat in-game e RCON, o administrador não altera os atributos dos jogadores diretamente por esta API. No frontend, o administrador apenas define a tabela de custos de resgate por nível de atributo. Consulte [FRONTEND_ATTRIBUTES_HANDOFF.md](file:///c:/Users/paulo/Desktop/Aplicativos/SSM/SSM%203.0/Backend/docs/endpoints/FRONTEND_ATTRIBUTES_HANDOFF.md) para a documentação de configuração de preços. Os endpoints abaixo servem como API legada/secundária.

### Visao Geral

- **Fonte**: `SCUM.db` (tabela `prisoner` + `user_profile`).
- **O que faz**: ler e atualizar atributos do player (`Strength`, `Constitution`, `Dexterity`, `Intelligence`).
- **Como funciona**: os valores sao armazenados no BLOB `prisoner.body_simulation`. O backend faz uma edicao binaria "cirurgica" no BLOB (double little-endian) para alterar os atributos.
- **Seguranca**:
  - Leitura: requer autenticacao (`@require_auth`).
  - Escrita: requer admin (`@require_auth` + `@require_admin`).
  - Servidor rodando: se o jogador estiver online, o backend atualiza os atributos e todas as skills associadas em tempo real via RCON (`SetAttributes` + `SetSkillLevel`). Se o jogador estiver offline, a escrita binária direta no banco `SCUM.db` (atributos) e inserção/update na tabela `prisoner_skill` (skills) é executada com segurança.
  - Backup automatico: antes de qualquer escrita direta em banco (jogador offline), e criado um backup do `SCUM.db` em `data/backups/scum_db/`.
  - Notificacao Discord: quando uma atualizacao e aplicada, o backend envia um embed no webhook `log-ssm` com ator, player, changes e backup.

---

### Headers (Autenticacao)

Para endpoints protegidos, enviar:

```
Authorization: Bearer <JWT>
Content-Type: application/json
```

Para obter o JWT, use `POST /api/auth/login`.

---

### 1) `GET /api/attributes/prisoners`

Lista prisioneiros do `SCUM.db` para selecao no frontend.

**Auth**: `require_auth`

**Query params (opcionais)**

| Parametro | Tipo | Default | Descricao |
| --- | --- | --- | --- |
| `query` | `string` | `""` | Filtra por `prisoner_id`, `steam_id` ou `name` (contains, case-insensitive). |
| `limit` | `number` | `200` | Maximo de itens por pagina (1 a 2000). |
| `offset` | `number` | `0` | Paginacao (>= 0). |

**Resposta (200)**

```json
{
  "success": true,
  "data": {
    "prisoners": [
      {
        "prisoner_id": 123,
        "steam_id": "7656119...",
        "name": "Player"
      }
    ],
    "total": 1000,
    "limit": 200,
    "offset": 0,
    "count": 200
  }
}
```

---

### 2) `GET /api/attributes/player/{identifier}`

Obtem atributos do player.

- `identifier`: pode ser `steam_id` (string) ou `prisoner_id` (inteiro).

**Auth**: `require_auth`

**Resposta (200)**

```json
{
  "success": true,
  "data": {
    "player": {
      "prisoner_id": 123,
      "steam_id": "7656119...",
      "name": "Player"
    },
    "attributes": {
      "strength": 5.0,
      "constitution": 3.0,
      "dexterity": 3.0,
      "intelligence": 2.0
    }
  }
}
```

**Erros**

- `404`: player nao encontrado no `SCUM.db`.
- `500`: falha de leitura do BLOB/DB.

---

### 3) `PATCH /api/attributes/player/{identifier}`

Atualiza atributos do player.

**Auth**: `require_auth` + `require_admin`

**Regras de Atualização e Habilidades (RCON)**

- **Atualização via RCON**: O backend executa os comandos RCON `SetAttributes` e `SetSkillLevel` para todas as skills correspondentes do grupo do atributo. Como agora a progressão usa apenas RCON para atualizar também as Skills em tempo real, o jogador precisa estar online no servidor para que o comando seja aplicado.
- **Propagação de Skills**: A atualização do atributo propaga automaticamente o upgrade de todas as habilidades (skills) associadas para o mesmo nível do atributo.


**Body (formatos aceitos)**

Formato recomendado:

```json
{
  "attributes": {
    "strength": 5.0,
    "constitution": 3.0,
    "dexterity": 3.0,
    "intelligence": 2.0
  }
}
```

Tambem aceita (sem wrapper):

```json
{
  "strength": 5.0,
  "constitution": 3.0
}
```

**Validacoes**

- `strength`: 1.0 a 8.0
- `constitution`: 1.0 a 5.0
- `dexterity`: 1.0 a 5.0
- `intelligence`: 1.0 a 5.0

**Resposta (200)**

```json
{
  "success": true,
  "message": "Atributos atualizados com sucesso",
  "data": {
    "player": {
      "prisoner_id": 123,
      "steam_id": "7656119...",
      "name": "Player"
    },
    "before": {
      "strength": 1.0,
      "constitution": 1.0,
      "dexterity": 1.0,
      "intelligence": 1.0
    },
    "after": {
      "strength": 5.0,
      "constitution": 3.0,
      "dexterity": 3.0,
      "intelligence": 2.0
    },
    "changes": [
      "strength: 1.00 -> 5.00"
    ],
    "backup_path": "data/backups/scum_db/SCUM.db.20260204_201500.bak"
  }
}
```

**Resposta (409) - jogador online com servidor rodando**

```json
{
  "success": false,
  "error": "Jogador está online. Para alterar atributos com servidor rodando, o jogador precisa estar offline.",
  "details": {
    "steam_id": "7656119..."
  }
}
```

---

### Sugestao de UX (staging no frontend)

Para replicar o comportamento do app SetAttributes:

1. Ao selecionar o player, chamar `GET /api/attributes/player/{identifier}` e guardar como `originalAttributes`.
2. Manter `draftAttributes` em state (inputs).
3. Marcar pendencias quando `draft != original` (exibir `*`, contador, borda laranja etc.).
4. Botao "Reverter": voltar `draftAttributes = originalAttributes`.
5. Botao "Salvar": chamar `PATCH /api/attributes/player/{identifier}`.

---

### Arquivos relacionados (backend)

- `utils/scum_attributes_editor.py`: leitura/escrita do BLOB `body_simulation`.
- `utils/scum_db_helper.py`: conexao read-only strict (nao cria WAL/SHM).
- `main.py`: implementacao dos endpoints `/api/attributes/*`.
