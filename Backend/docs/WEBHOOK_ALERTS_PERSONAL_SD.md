# Webhook Pessoal de Raid (\`/sd\`) + Deduplicacao de Entrega

## Objetivo
Permitir que jogadores com permissao adequada cadastrem um webhook pessoal do Discord para receber alertas de lockpicking (raid) relacionados as propriedades que eles possuem.

O sistema envia:

- Global/Admin: continua usando o webhook configurado em `data/webhooks.json` (chave `lockpicking_events`).
- Pessoal (Owner): envia para o webhook que o jogador cadastrou via comando `\`/sd\``.

Tambem foi implementada deduplicacao robusta por destino (global vs owner), para evitar reenvios duplicados.

## Comando de Chat

### Cadastrar/atualizar webhook
No chat do jogo:

- `\`/sd <discord_webhook_url>\``

Regras:

- O jogador precisa da permissao `raid_webhook_manage` ativa.
- O webhook e validado para padrao de URL do Discord.
- Ha cooldown (anti-spam) para evitar trocas muito frequentes.

### Remover webhook pessoal
No chat do jogo:

- `\`/sd off\``

Isso remove o registro do webhook pessoal do jogador.

## Permissao

A checagem do comando usa a permissao do tipo:

- `raid_webhook_manage`

A permissao e consultada no banco (tabela de permissoes do sistema), sem depender do arquivo INI.

## Banco de Dados

### Tabela: `player_webhooks`
Armazena o webhook pessoal por Steam ID.

Campos (resumo):

- `steam_id` (PK)
- `webhook_url`
- `created_at`
- `updated_at`

Operacoes:

- `\`/sd <url>\`` faz upsert.
- `\`/sd off\`` faz delete.

### Tabela: `minigame_event_deliveries`
Armazena o status de entrega por evento e por destino (global vs owner), garantindo deduplicacao persistente.

Campos (resumo):

- `event_key`
- `target_type` (ex: `global`, `owner`)
- `target_steam_id` (NULL para global; Steam ID do owner para owner)
- `status` (ex: `pending`, `sent`, `failed`)
- `attempt_count`
- `last_attempt_at`
- `last_error`
- `created_at`
- `updated_at`

## Fluxo de Envio (Lockpicking)

Quando um evento de lockpicking e processado, o backend:

1. Monta um `event_key` deterministico para o evento (baseado nos dados do evento/log).
2. Tenta enviar para o destino `global`.
3. Se houver owner e ele tiver webhook cadastrado, tenta enviar para o destino `owner`.
4. Cada destino possui seu proprio registro de entrega e status, evitando duplicatas.

Observacao: o envio global continua marcando `discord_sent` no evento (como ja existia), mas a deduplicacao principal do novo fluxo fica na tabela `minigame_event_deliveries`.

## Diferenca de Embed (Global vs Pessoal)

A formatacao do embed foi separada por "target":

- Global (Admin): mantem o bloco de teleport, para facilitar acao rapida do admin.

  Exemplo:

  ```
  #Teleport X Y Z
  ```

- Pessoal (Owner): substitui o bloco `#Teleport` por um link clicavel do SCUM Map.

  Exemplo:

  - `[View on Map](https://scum-map.com/en/shared/scum/island/X,Y,4)`

Essa diferenca e aplicada somente ao envio pessoal, sem alterar o embed global.

## Observacao sobre "Hoje as 14:35" no Discord

A parte "Hoje as 14:35" (ou "Today at ...") **nao vem do webhook**. E o cliente do Discord que renderiza esse texto conforme o idioma/locale de quem esta visualizando.

## Arquivos/Locais Principais

- `utils/database_initializer.py`
  - Criacao/garantia das tabelas `player_webhooks` e `minigame_event_deliveries`.

- `core/logs/chat_command_monitor.py`
  - Implementacao do comando `\`/sd\``.

- `core/logs/log_processor.py`
  - Fluxo de lockpicking chamando envio global + envio pessoal com deduplicacao.

- `core/logs/minigame_notifier.py`
  - `format_discord_message(..., target=...)`
  - Global: `target="global"` => `#Teleport`.
  - Pessoal: `target="owner"` => link SCUM Map.

## Teste Manual (Checklist)

- Conferir que o jogador tem permissao `raid_webhook_manage`.
- No jogo:
  - `\`/sd <url>\`` e verificar que foi cadastrado.
- Gerar evento de lockpicking em propriedade do jogador.
- Validar no Discord:
  - Global/Admin: aparece `#Teleport X Y Z`.
  - Pessoal (jogador): aparece `View on Map`.
- Opcional:
  - `\`/sd off\`` e confirmar que nao envia mais para o owner.
