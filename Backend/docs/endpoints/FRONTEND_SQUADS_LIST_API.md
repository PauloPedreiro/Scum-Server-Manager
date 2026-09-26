## Documentação `/api/squads` (Frontend)

### Visão Geral
- **Objetivo**: fornecer ao frontend a lista completa de squads disponíveis no snapshot mais recente sincronizado pelo `SquadSyncService`.
- **Fonte dos dados**: tabela `squad_snapshot` do `SSM.db`.
- **Atualização**: conforme intervalo configurado em `config.json` (`squad_sync.sync_interval_minutes`, padrão 30 minutos).
- **Ordenação padrão**: `rank_position` crescente, depois `score` decrescente, e `squad_id` crescente.
- **Paginação**: não aplicável. A rota retorna todos os registros do snapshot atual.
- **Sincronização de bandeiras**: o campo `flag_count` é recalculado a cada execução do `SquadSyncService`, com base no `SCUM.db` (tabela `base_element_flag`). Diminuir ou aumentar bandeiras no jogo refletirá aqui após a próxima sincronização.

---

### Endpoint
| Método | URL | Autenticação | Cache Recomendado |
| --- | --- | --- | --- |
| `GET` | `/api/squads` | não | até 1 minuto (dados mudam apenas a cada sincronização) |

#### Requisição
- **Headers**: nenhum obrigatório.
- **Body**: não se aplica.
- **Query params**: não suportados.

Exemplo (fetch):
```ts
const response = await fetch('/api/squads');
const json = await response.json();
```

---

### Resposta (`200 OK`)

```json
{
  "success": true,
  "data": {
    "squads": [
      {
        "snapshot_id": 12,
        "squad_id": 5,
        "name": "Fazendinha GVT",
        "message": "Onde a internet cai, mas a diversão nunca",
        "information": "",
        "emblem": "720595822739195935",
        "score": 4510.61,
        "member_limit": 10,
        "member_count": 8,
        "last_member_login_time": "2025-10-31T00:02:58.907Z",
        "last_member_logout_time": "2025-10-31T00:58:54.721Z",
        "rank_position": 1,
        "snapshot_at": "2025-11-07T01:41:00.635179",
        "flag_count": 4
      }
    ],
    "total": 64
  }
}
```

#### Campos
- `success`: indica sucesso da requisição.
- `data.squads`: array com todos os squads.
  - `snapshot_id`: identificador interno do registro na tabela de snapshot.
  - `squad_id`: identificador do squad no SCUM.
  - `name`: nome atual do squad.
  - `message`: mensagem personalizada configurada pelo squad (pode ser vazio).
  - `information`: informações extras/lore (pode ser vazio).
  - `emblem`: hash usado para recuperar o emblema do squad (pode ser `null`).
  - `score`: pontuação agregada do squad (pode ser `null` se recém-criado).
  - `member_limit`: limite máximo de membros suportado (pode ser `null`).
  - `member_count`: quantidade atual de membros.
  - `flag_count`: quantidade de bandeiras (territórios) registradas para o squad (valor persistido no `SSM.db`).
  - `last_member_login_time` / `last_member_logout_time`: horários ISO do último login/logout de qualquer membro (podem ser `null`).
  - `rank_position`: posição do squad no ranking geral (pode ser `null` quando não calculada).
  - `snapshot_at`: data/hora em que o snapshot foi gerado.
- `data.total`: quantidade total de squads retornados.

---

### Tratamento de Erros
| Status | Estrutura | Quando acontece | Ação recomendada |
| --- | --- | --- | --- |
| `500` | `{ "success": false, "error": "mensagem" }` | Falha ao localizar o `SSM.db` ou ler a tabela | Exibir mensagem “Não foi possível carregar squads” e sugerir recarregar |

---

### Recomendações para o Frontend
- **Revalidação**: como os dados mudam apenas em intervalos fixos, use cache `stale-while-revalidate` curto (ex.: 60s) ou `react-query` com `staleTime = 60_000`.
- **Ordenação**: usar diretamente a ordenação retornada. Caso precise ordenação customizada, ordene no cliente a partir dos campos existentes.
- **Resiliência**: exibir aviso “Dados sincronizados em `<tempo>`” usando `snapshot_at`.
- **Fallbacks de UI**:
  - Mostrar placeholder quando `emblem` for `null`.
  - Exibir “Sem mensagem” quando `message` estiver vazio.
  - Mostrar `member_count/member_limit` apenas se `member_limit` não for `null`.
- **Integrações**:
  - Aproveite `squad_id` para navegar para `/api/squads/{squad_id}` (detalhe expandido).
  - Usar `last_member_login_time` e `last_member_logout_time` para indicar atividade recente.

---

### Checklist para Integração
- [ ] Configurou fetch/axios com timeout (ex.: 10s) e tratamento de erro (toast/modal)?
- [ ] Exibe loading skeleton enquanto aguarda resposta?
- [ ] Usa `snapshot_at` para indicar frescor dos dados?
- [ ] Possui fallback para lista vazia (`total = 0`)?
- [ ] Linka a partir do `squad_id` para tela de detalhes ou modal?

---

### Histórico
- **07/11/2025**: endpoint implementado no backend.
- **10/11/2025**: documentado para repasse ao frontend.

> Em caso de necessidade de filtros ou paginação futuros, alinhar antes com o backend para avaliar impacto na consulta ao `SSM.db`.

