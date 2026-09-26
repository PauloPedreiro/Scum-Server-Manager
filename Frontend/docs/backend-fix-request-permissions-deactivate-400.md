# Incidente + verificação pós-correção (Backend)

## Título
Correção esperada no backend: `activate/deactivate` devem ser idempotentes e retornar `200 OK` em cenários "já ativa"/"já inativa" (no-op), evitando `400 BAD REQUEST` no frontend.

## Contexto
O frontend possui toggles para ativar/desativar permissões de jogadores via endpoints:

- `POST /api/players/{steam_id}/permissions/{permission_type}/activate`
- `POST /api/players/{steam_id}/permissions/{permission_type}/deactivate`

Ativação está funcionando normalmente.
Na desativação, o backend altera o estado no banco (ou detecta que já está inativo), porém retorna `HTTP 400`, o que é tratado como erro pelo browser/axios e impacta a UX.

## Impacto
- No frontend, o DevTools/axios registra erro `400 (BAD REQUEST)` para `deactivate`, apesar do estado ficar corretamente inativo no banco.
- Isso causa:
  - poluição de logs (stacktraces)
  - sensação de falha no toggle
  - necessidade de tratamento especial no frontend para “sincronizar” estado.

## Evidência / exemplo de resposta
Ao tentar desativar, o backend retorna `400` com body semelhante a:

```json
{
  "error": "permission_already_inactive",
  "message": "Permissão <permission_type> já está inativa para este jogador",
  "success": false
}
```

## Evidência adicional (regressão atual observada)
Além do caso idempotente, foi observado retorno `400` com erro interno (não relacionado a idempotência):

```json
{
  "error": "unknown_error",
  "message": "Erro ao desativar permissão: name 'player' is not defined",
  "success": false
}
```

Esse payload indica um erro de runtime no backend (provavelmente Python `NameError`), sugerindo que o handler de `deactivate` referencia a variável `player` sem defini-la (ou com nome diferente) ao montar mensagem/log.

## Situação atual
O backend enviou documentação confirmando o comportamento idempotente recomendado para toggles:

- Para `activate`: se já estiver ativa, retornar **`200 OK`** com `success: true` (no-op) e `data.is_active: true`.
- Para `deactivate`: se já estiver inativa, retornar **`200 OK`** com `success: true` (no-op) e `data.is_active: false`.

Este documento serve para registrar o incidente observado anteriormente (`400` em no-op) e orientar a verificação de que a correção foi aplicada/deployada.

## Como reproduzir
1. Autenticar:
   - `POST /api/auth/login`
   - body:
     ```json
     {"username":"admin","password":"admin123"}
     ```
2. Selecionar um jogador e uma permissão já inativa (ou desativar uma permissão e repetir a operação).
3. Executar:
   - `POST /api/players/{steam_id}/permissions/{permission_type}/deactivate`
4. Observar que:
   - **ANTES da correção:** podia retornar `HTTP 400` com `permission_already_inactive`/`permission_already_active`.
   - **APÓS a correção:** deve retornar `HTTP 200` com `success: true` e `data.is_active` refletindo o estado final.

## Comportamento esperado
Para endpoints de toggle (activate/deactivate), o comportamento ideal é ser **idempotente**:

- Se a permissão já está no estado solicitado (ex.: já inativa), o endpoint deve retornar **sucesso** (sem tratar como erro HTTP).

Sugestões (qualquer uma é aceitável, depende do padrão do projeto):

- **Opção A (recomendada para UX):** retornar `200 OK` com `success: true` e o estado final em `data.is_active`.
- **Opção B:** retornar `204 No Content` quando não há mudança (já estava no estado).
- **Opção C:** retornar `409 Conflict` para indicar “já está no estado” (menos ideal para toggle, mas ainda melhor do que `400`).

## Recomendações de ajuste
1. Ajustar o handler de `deactivate` (e possivelmente `activate`) para que casos:
   - `permission_already_inactive`
   - `permission_already_active`
   não retornem `400`.
2. Retornar payload padronizado contendo o estado final:
   - `data.is_active` (false/true)
   - `permission_type`, `steam_id`, timestamps
3. Manter `400` apenas para validações reais:
   - `permission_type` inválido
   - `steam_id` inválido
   - payload malformado
   - permissões/autorização (ou `401/403`)

## Checklist de verificação (pós-deploy)
- Testar `deactivate` para uma permissão já inativa e confirmar:
  - `HTTP 200`
  - `success: true`
  - `data.is_active: false`
- Testar `activate` para uma permissão já ativa e confirmar:
  - `HTTP 200`
  - `success: true`
  - `data.is_active: true`
- Confirmar para múltiplos tipos:
  - `admin`, `banned`, `server_admin`, `silenced`, `whitelisted`, `raid_webhook_manage`

## Ação recomendada no backend (para a regressão `NameError`)
- Revisar o handler do endpoint `POST /api/players/{steam_id}/permissions/{permission_type}/deactivate`.
- Procurar por uso de `player` fora de escopo (ex.: `player.name`, `player.steam_id`, etc.).
- Garantir que o jogador seja carregado e atribuído (ex.: `player = ...`) antes do uso, ou usar a variável correta existente.
- Garantir retorno consistente com a documentação:
  - `200 OK` e `success: true` para no-op (já inativa)
  - `200 OK` e `success: true` para desativação com sucesso
  - `4xx` somente para validação real (steam_id inválido, tipo inválido, auth)

## Observações adicionais
- O problema foi observado em múltiplos tipos (`admin`, `banned`, `server_admin`, `silenced`, `whitelisted`, `raid_webhook_manage`).
- O `raid_webhook_manage` é DB-only (campos `ini_file_updated`/`ini_file_path` podem ser `null`).

---

## Resultado desejado
Eliminar `HTTP 400` em cenários idempotentes de `activate/deactivate`, garantindo contrato consistente para toggles e evitando erros no frontend.
