# Changelog - Chat In-Game -> Discord

Este arquivo documenta as mudancas realizadas no fluxo de envio de mensagens do chat do jogo (logs `chat_*.log`) para o Discord (webhook `chat_in_game`).

## Funcionalidades / Melhorias

### Separacao por canal (Global/Local/Squad/Admin)
- As mensagens do `chat_*.log` agora sao parseadas com o tipo de canal quando presente na linha.
- O canal e extraido e repassado ate o envio ao Discord.
- Normaliza variacoes do canal Global encontradas no log (ex.: `Globaal`, `Gloobal` -> `Global`).

### Formato da mensagem no Discord com icones
- O formato ficou: `icone Nome: mensagem` (sem tags como `[GLOBAL]`).
- Icones/shortcodes por canal (conforme configurado no codigo):
  - Global: `:mega:`
  - Local: `:round_pushpin:` (ou equivalente unicode no codigo)
  - Squad: `:military_helmet:`
  - Admin: `:man_detective::skin-tone-1:`
  - Default (sem canal): `:speech_balloon:` (ou equivalente unicode no codigo)

### Filtro por canais via configuracao
- Implementado filtro por canais em `data/config.json` (chave `chat_monitoring.channels`).
- Configurado para permitir todos os canais:
  - `Global`
  - `Local`
  - `Squad`
  - `Admin`

## Correcoes / Robustez

### Deduplicacao com canal
- O hash de deduplicacao passou a considerar tambem o canal para evitar colisoes entre mensagens iguais em canais diferentes.
- Mantida compatibilidade com hashes legados (sem canal) para evitar reenvio em massa de mensagens antigas ja processadas em `data/chat_processed.json`.

### Fila / retry com rate limit transportando canal
- A fila interna e o retry apos rate limit (HTTP 429) agora preservam o `channel` junto com `player_name` e `message`.

## Outros ajustes relacionados

### Log de playtime rewards mais estruturado
- Ajustado log no `main.py` para registrar os valores do tick de playtime rewards como objeto (estrutura), em vez de string formatada com muitos placeholders.
