## Documentação `/api/squads/{squad_id}/members` (Frontend)

### Visão Geral
- **Objetivo**: disponibilizar a lista paginada de membros de um squad específico para telas de detalhe, modais ou infinit scroll.
- **Fonte dos dados**: tabela `squad_member_snapshot` do `SSM.db`, atualizada pelo `SquadSyncService`.
- **Relacionamentos**: cada membro está vinculado ao `squad_id` e ao snapshot mais recente do squad.
- **Paginação**: suporta parâmetros `limit` e `offset` para paginação manual.
- **Uso típico**: combinar com detalhamento de `/api/squads/{squad_id}` ou com a listagem `/api/squads/ranking`.

---

### Endpoint
| Método | URL | Descrição |
| --- | --- | --- |
| `GET` | `/api/squads/{squad_id}/members` | Retorna a lista paginada de membros do squad informado |

#### Query Params
| Nome | Tipo | Default | Obrigatório | Descrição |
| --- | --- | --- | --- | --- |
| `limit` | number | 50 | opcional | Quantidade de registros. Máximo prático: 200 (alterar no backend se precisar mais) |
| `offset` | number | 0 | opcional | Deslocamento para paginação |

#### Request Sample
```http
GET /api/squads/5/members?limit=50&offset=0
```

#### Exemplo Fetch
```ts
const url = new URL('/api/squads/5/members', window.location.origin);
url.searchParams.set('limit', '50');
url.searchParams.set('offset', '0');

const response = await fetch(url.toString());
if (!response.ok) throw new Error('Falha ao carregar membros');
const data = await response.json();
```

---

### Resposta (`200 OK`)

```json
{
  "success": true,
  "data": {
    "squad_id": 5,
    "squad_name": "Fazendinha GVT",
    "members": [
      {
        "snapshot_member_id": 201,
        "squad_member_id": 463,
        "user_profile_id": 38,
        "steam_id": "76561198040636105",
        "name": "Pedreiro",
        "rank": 4,
        "fame_points": 1234.5,
        "last_login_time": "2025-10-30T11:15:00Z",
        "last_logout_time": "2025-10-30T12:01:00Z",
        "play_time": 9823
      }
    ],
    "total": 8,
    "limit": 50,
    "offset": 0,
    "count": 1
  }
}
```

#### Campos
- `success`: indica sucesso da requisição.
- `data.squad_id`: identificador do squad requisitado.
- `data.squad_name`: nome atual do squad (auxilia o frontend a exibir título rápido).
- `data.members`: array de membros.
  - `snapshot_member_id`: identificador interno do registro na tabela de snapshot.
  - `squad_member_id`: identificador do membro no contexto do SCUM squad.
  - `user_profile_id`: ID interno do perfil (pode ser `null` se não associado).
  - `steam_id`: Steam ID do jogador (pode ser `null` se não encontrado no SCUM).
  - `name`: nome do jogador na data do snapshot.
  - `rank`: patente dentro do squad (pode ser `null`).
  - `fame_points`: fame atual (pode ser `null`).
  - `last_login_time` / `last_logout_time`: timestamps ISO da última sessão (podem ser `null`).
  - `play_time`: tempo de jogo acumulado (segundos, pode ser `null`).
- `data.total`: total de membros no squad (independente do `limit`).
- `data.limit`: limite aplicado à consulta.
- `data.offset`: offset aplicado.
- `data.count`: quantidade de registros retornados na página atual.

---

### Tratamento de Erros
| Status | Estrutura | Cenário | Ação recomendada |
| --- | --- | --- | --- |
| `404` | `{ "success": false, "error": "Squad {id} não encontrado" }` | Squad inexistente ou sem snapshot | Exibir mensagem “Squad não encontrado” e voltar para tela anterior |
| `500` | `{ "success": false, "error": "mensagem" }` | Problemas com acesso ao banco ou consulta | Mostrar toast “Falha ao carregar membros” e permitir tentar novamente |

---

### Recomendações para o Frontend
- **Paginação**:
  - Usar `limit` fixo (ex.: 25 ou 50) e incrementar `offset` (`offset += limit`) para carregar mais membros.
  - Habilitar `keepPreviousData` (React Query) ou mecanismo de loading incremental.
- **Tratamento de dados**:
  - Destacar `rank` (ícones de comando, capitão, membro).
  - Converter `play_time` em horas/minutos para UI.
  - Mostrar badge de atividade com base em `last_login_time`.
- **Fallbacks**:
  - Exibir placeholder quando `steam_id` for `null`.
  - Mostrar “Sem patente” quando `rank` for `null`.
  - Quando `total === 0`, exibir estado vazio.
- **Integrações futuras**:
  - Usar `steam_id` para cruzar com módulos de players, kill-logs e inventário.
  - Linkar membros de squad com detalhes individuais em `/api/survival/player/{steam_id}`.

---

### Checklist de Integração
- [ ] Montou hook ou chamada com `limit` e controle de `offset`?
- [ ] Implementou botões ou scroll para carregar mais (`total > members.length`)?
- [ ] Exibe estado vazio para squads sem membros?
- [ ] Usei `squad_name` para mostrar título da seção?
- [ ] Tratamento de erros 404/500 com mensagens amigáveis?
- [ ] Cache configurado (`staleTime` curto) para evitar requisições repetidas?

---

### Histórico
- **07/11/2025**: endpoint confirmado no backend.
- **10/11/2025**: documentação criada para integração frontend.

> Para necessidades de filtros adicionais (por rank, fame, etc.), alinhar com o backend antes de implementar para avaliar impacto em performance.

