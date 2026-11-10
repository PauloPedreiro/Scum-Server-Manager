# Diário de Bordo: Migração de Teleporte de Evento (Botão do Discord para Comando In-game)

Este documento registra as decisões, o diagnóstico do problema, a nova arquitetura desenvolvida e as alterações realizadas nos arquivos do sistema para servir de memória persistente para futuras sessões de desenvolvimento.

---

## 🎯 1. Histórico e Diagnóstico do Problema

### O Problema Original
* Jogadores clicavam no botão de teleporte de eventos no canal `#events` do Discord e frequentemente recebiam a mensagem **"Esta interação falhou"**.
* O bot por vezes ficava com status cinza/offline ou demorava para responder.

### O Diagnóstico
1. **Timeout da API do Discord**: A API do Discord exige que uma interação de botão seja respondida em até 3 segundos.
2. **Lentidão do Fluxo Antigo**: O fluxo antigo tentava verificar se o jogador estava online (via RCON ou banco), buscar as coordenadas e enfileirar o comando RCON diretamente na thread de callback do botão. Se o servidor ou banco estivesse sob carga, o tempo passava de 3 segundos, quebrando a interação do Discord.
3. **Dependência Crítica**: Se o jogador estivesse com problemas de conexão com a API do Discord, a ação falhava por completo.
4. **Criação da View Fora do Loop de Eventos (Causa Raiz)**: O construtor do `discord.ui.View` tenta detectar o loop de eventos asyncio ativo chamando `asyncio.get_running_loop()`. Como a view dinâmica de teleporte era construída e registrada a partir da thread secundária do `EventManager`, essa detecção falhava (gerando `RuntimeError`) e definia o controle interno `self.__stopped` do `discord.py` como `None`. Por conta disso, qualquer clique posterior no botão do Discord era descartado silenciosamente pela biblioteca no método `_dispatch_item`, sem disparar o callback. Em contrapartida, o `ssm_select_menu`, construído na thread principal do loop (no `on_ready`), funcionava normalmente. Corrigido forçando a criação e o registro da view de teleporte na thread principal através de `loop.call_soon_threadsafe`.

---

## 🏗️ 2. Nova Arquitetura de Teleporte Seguro

Para blindar o sistema de timeouts e melhorar a experiência do jogador, mudamos o fluxo de ação:

1. **Geração Instantânea de Código (Discord)**:
   * O botão no Discord foi alterado para **"Get Teleport Code"** (Gerar Código).
   * Ele apenas valida o registro do jogador localmente no banco `SSM.db` e gera um código de 4 dígitos alfanuméricos em caixa alta.
   * O código é gravado em um arquivo JSON temporário (`event_teleport_codes.json`, salvo dinamicamente na pasta pai do banco de dados `self.ssm_db_path` para evitar erros de permissão ou caminhos incorretos quando o app roda compilado).
   * O bot responde com uma mensagem efêmera (instantânea, em milissegundos) com o código formatado para **cópia rápida**:
     ```
     `7F3A`
     ```
2. **Comando In-Game (`/evento [código]`)**:
   * O jogador digita `/evento 7F3A` no chat global do SCUM.
   * O `ChatCommandMonitor` lê a linha do chat nos logs locais de texto.
   * O monitor valida se o código existe no JSON temporário e se o `steam_id` de quem digitou é o mesmo dono do código (impedindo compartilhamento e uso por não registrados).
   * O monitor busca as coordenadas do evento ativo no banco e envia o teleporte via fila do RCON (`#teleport X Y Z SteamID`).
3. **Auditoria e Logs**:
   * Uma notificação de sucesso é enviada para o canal de logs/comandos do Discord (`#commands`).
4. **Limpeza Automática**:
   * Ao finalizar ou limpar o evento, os códigos associados a ele são limpos do JSON temporário.

---

## 📂 3. Arquivos Modificados e Alterações

### 1. `core/discord_bot_service.py`
* **Botão `TeleportEventButton`**: Rótulo atualizado para `"Get Teleport Code"`.
* **Callback `_handle_teleport_interaction`**:
  * Adicionada verificação de conta registrada (com mensagem em português: `"❌ Você precisa registrar sua conta primeiro."`).
  * Implementada geração de código aleatório com caracteres não ambíguos (excluindo `I`, `1`, `O`, `0`).
  * Escrita dos códigos no arquivo `data/event_teleport_codes.json` com trava de thread (`threading.Lock`).
  * Retorno do código formatado em monotexto (crase) para cópia imediata.

### 2. `core/logs/chat_command_monitor.py`
* **Padrões de Comando**: Adicionado o padrão `'evento': r'/evento\b'`.
* **Roteamento**: Adicionada a verificação `cmd == "evento"` chamando `_handle_evento_command`.
* **Método `_handle_evento_command`**:
  * Extrai o código enviado na mensagem do chat.
  * Valida o `steam_id` do remetente e o `event_id` no arquivo JSON.
  * Consulta a tabela `event_configs` e `event_coordinates` para obter as coordenadas de destino do evento correspondente.
  * Enfileira o comando de teleporte RCON.
  * Dispara uma notificação assíncrona informando o uso do teleporte para o canal `#commands` no Discord.

### 3. `core/events/event_manager.py`
* **Método `_send_discord_notification`**:
  * Alterado o rótulo (`label`) do botão no componente enviado à API REST do Discord de `"Teleport to Event"` para `"Get Teleport Code"`.
* **Método `_clear_discord_messages`**:
  * Ao ser chamado (quando um evento finaliza ou é limpo), ele remove todos os códigos associados àquele `event_id` do arquivo `data/event_teleport_codes.json` para manter o JSON limpo e invalidar os acessos futuros.

---

## 💾 4. Estrutura do JSON Temporário (`data/event_teleport_codes.json`)

Mantido na pasta de dados do sistema, estruturado para múltiplos eventos simultâneos:
```json
{
  "codes": {
    "7F3A": {
      "steam_id": "76561198000000000",
      "player_name": "Pedreiro",
      "event_id": 42,
      "generated_at": "2026-06-29T22:25:00Z"
    }
  }
}
```

## 🔍 5. Sistema de Rastreabilidade e Logs de Interação
Para diagnosticar falhas na produção (como a mensagem de erro "Interação falhou"), adicionamos um logger passo a passo dedicado:
* **Arquivo de Log**: `data/logs/discord_events.log` (procurar pela tag `[TELEPORT_DEBUG]`)
* **O que registra**:
  * Entrada e saída no callback da view.
  * Resolução de instância do singleton `DiscordBotService`.
  * Status detalhado de cada etapa (recebimento do custom ID, parsing de IDs, deferimento da resposta, consultas ao banco SQLite para jogador e evento, leitura e escrita no arquivo JSON).
  * Exceções com traceback completo (caso ocorra qualquer erro).

---

## 🚀 6. Como Testar o Novo Fluxo

1. Inicie um evento pelo painel SSM.
2. No canal `#events` do Discord, clique no botão **Pegar Código** (com emoji 🌀).
3. O bot responderá instantaneamente de forma privada com o código. Clique sobre ele para copiar.
4. Entre no jogo e digite no chat global: `/evento [CÓDIGO_COPIADO]`.
5. Você será teleportado em instantes para as coordenadas do evento.
6. Em caso de erro "Interação falhou", verifique o arquivo `data/logs/discord_events.log` na máquina servidora para identificar a tag `[TELEPORT_DEBUG]` e o traceback exato da falha.

---

## 🔧 7. Auditoria do Welcome Pack & Aba de Manutenção (SSM 3.0)

### 1. Correção da Entrega Automática do Kit de Boas-Vindas (Welcome Pack)
* **Diagnóstico**: O kit de boas-vindas (`welcomepack`, código `1`) estava desabilitado no catálogo da loja (`enabled = 0` na tabela `shop_kit`) para impedir que os jogadores o resgatassem manualmente pelo site. Porém, a regra do `ShopService.create_order` exigia que o item estivesse habilitado no catálogo, levantando a exceção `OFFER_DISABLED:1` durante a tentativa de entrega automática pós-registro.
* **Solução**: Atualizamos o método `ShopService.create_order` para verificar a flag `auto_deliver_on_register` do kit. Se for um kit de entrega automática de registro, a verificação de catálogo ativo (`enabled == 1`) é contornada com sucesso.

### 2. Implementação da Aba de Manutenção (Maintenance) na GUI Desktop
* **Objetivo**: Permitir aos administradores executar tarefas de suporte diretamente pelo painel do SSM Desktop sem precisar de scripts Python ou scripts externos.
* **Visual**: Adicionada uma nova aba **"Maintenance"** (após a aba `RCON/Mods`) nas configurações do sistema.
* **Funcionalidades**:
  * **Reset de Jogador Específico (Reset Specific Player)**: Campo para digitar o SteamID do jogador e botão para executar o reset. Limpa seu vínculo de Discord, histórico de pedidos/entregas da loja e redefine a carteira para R$ 5.000 (com modal de confirmação em inglês).
  * **Reset Geral (Reset All Players)**: Botão de alerta vermelho para limpar todos os vínculos de Discord, deletar todos os tokens de link, remover todo o histórico da loja e resetar as carteiras de todos os jogadores (com confirmação dupla de segurança).
* **Arquivos Modificados**:
  * `gui/main_window.py`: Inclusão do botão de aba, frame de layout e callbacks SQL de manutenção.


## 🎮 8. Sistema de In-Game Kill Feed e Limpeza de Notificações do Discord (SSM 3.0)

### 1. Objetivo e Nova Arquitetura do Kill Feed
O objetivo principal foi criar um sistema dinâmico e humorístico para notificar mortes PvP diretamente no chat do jogo (via comandos RCON), reduzindo também a poluição visual no canal de kills do Discord.
* **Discord Cleaner**: Removido o link fixo `"Ver todos os rankings"` dos embeds de todos os tipos de logs de morte (suicídio, morte por NPC e PvP) para manter o canal limpo.
* **In-Game Kill Feed**: Ao detectar uma morte PvP a partir do log, o sistema formata uma mensagem usando um template customizável e anexa uma frase de "zoeira" aleatória obtida de `data/kill_feed_phrases.json`.
* **Fila RCON Segura e Priorizada**:
  * A mensagem é enviada para os jogadores que estão online no momento (`players_online`) usando o comando RCON `SendChat` (ou em modo global usando `Announce`).
  * Os comandos RCON são enfileirados no `RconQueueManager` com prioridade **15** (abaixo de compras da loja e comandos manuais de teleporte) para evitar que mensagens de chat atrasem funcionalidades vitais do servidor.
  * O tempo de atraso entre comandos sequenciais de chat é ajustado para **50ms** (`delay_after=0.05`), mitigando perdas de pacotes no socket RCON.

### 2. Segurança e Sanitização de RCON
Implementamos regras estritas de segurança para garantir a imunidade do console RCON contra injeção de comandos maliciosos por nomes de jogadores:
* **Prevenção de Command Injection (Newline Injection)**: Substituição de quaisquer quebras de linha (`\n` e `\r`) por espaços em branco ou vazios nos nomes de assassino, vítima, arma e frase. Como novas linhas separam comandos RCON, isso impede a injeção de comandos paralelos.
* **Tratamento de Delimitadores de String**: Substituição de aspas duplas (`"`) por aspas simples (`'`) para evitar que caracteres de aspas nos nomes dos jogadores fechem a string delimitadora do RCON `SendChat <tipo> "<mensagem>" <steam_id>` precocemente, o que corromperia o comando.
* **Filtro de Controle**: Remoção de caracteres de controle invisíveis para evitar falhas de codificação no console do SCUM.

### 3. Gerenciamento e API de Frases
* **Arquivo de Dados (`data/kill_feed_phrases.json`)**: Inicializado com uma coletânea inicial de mais de 120 frases de zoeira, trash-talk e piadas internas de servidores de SCUM criadas pela comunidade.
* **Endpoints Criados**:
  * `GET /api/config/kill-feed-phrases`: Retorna o array JSON contendo a lista atual de frases cadastradas.
  * `POST /api/config/kill-feed-phrases`: Recebe a lista modificada de frases da interface administrativa e sobrescreve o arquivo no disco de forma atômica após validação de formato e tipo de dados (array de strings).

### 4. Configuração Padrão (`config.json`)
O sistema integra auto-migração de chaves que insere dinamicamente a seguinte seção caso esteja ausente no servidor:
```json
"kill_feed": {
  "enabled": true,
  "mode": "chat",
  "chat_type": 2,
  "message_template": "{killer} matou {victim} ({weapon} - {distance}m) | {phrase}",
  "phrases_path": "data/kill_feed_phrases.json",
  "priority": 15
}
```

### 5. Arquivos Modificados e Criados
* `core/logs/kill_processor.py`: Atualizado construtor com injeção de configurações, remoção de campos de ranking dos embeds, implementação de `_get_random_kill_phrase` e lógica RCON sanitizada em `_send_in_game_feed`.
* `core/logs/log_processor.py`: Correção de importação de `Path` global de forma a impedir shadowing e UnboundLocalError, auto-migração de `kill_feed` na carga do config, instanciação do `KillProcessor` com injeção das dependências.
* `app/routes/config_routes.py`: Criação dos endpoints REST `GET` e `POST` para `/api/config/kill-feed-phrases`.
* `tools/copy_data_files.py`: Inclusão de `data/kill_feed_phrases.json` na lista de itens copiados no processo de build do executável.
* `data/config.example.json` & `data/config.json`: Declaração das configurações padrão.
* `data/kill_feed_phrases.json`: Nova lista de frases da comunidade.
* `scratch/test_kill_feed.py` & `scratch/test_config_api.py`: Scripts utilitários de testes criados para validação rápida das mecânicas de RCON, Discord e endpoints REST.

---

## 🧠 9. Criação do Contexto da IA (AGENT_CONTEXT.md)

### 1. Objetivo
Simplificar e focar a atuação de assistentes de Inteligência Artificial no projeto, consolidando as regras essenciais de arquitetura, banco de dados e comunicação em um único arquivo de referência rápida (`AGENT_CONTEXT.md`), evitando a burocracia excessiva e a duplicação de informações sugeridas por prompts genéricos.

### 2. Arquivos Modificados e Criados
* `AGENT_CONTEXT.md`: Criação do arquivo contendo a arquitetura simplificada (RconQueueManager, SQLite locks, Discord timeouts), a stack tecnológica e as regras de ouro/diretrizes de desenvolvimento do SSM 3.0 Backend.
* `docs/kill_feed_frontend_doc.md`: Documentação técnica para a equipe de desenvolvimento do front-end sobre o módulo de Kill Feed (configurações, mapeamento de cores RCON e endpoints HTTP).

---

## 📅 10. Implementação do Agendador de Rotinas RCON & Hotfix

### 1. Objetivo
Desenvolver o módulo de agendamento automático de comandos RCON (limpeza de itens, anúncios, etc.) com salvamento local no formato JSON, suporte a CRUD, execução imediata via botão de teste e prevenção contra disparos durante restarts do servidor. Além disso, corrigir o erro de inicialização do monitor de jogadores online.

### 2. Arquivos Modificados e Criados
* `core/scheduler/rcon_routine_manager.py`: CRUD persistente das rotinas com concorrência segura (`threading.Lock`), agora incluindo campos de aviso prévio (`warning_enabled`, `warning_message`, `warning_color`, `warning_minutes_before`, `last_warning_run`).
* `core/scheduler/rcon_routine_scheduler.py`: Serviço de background com checagem de 60s, prioridade baixa (20) e delay de 2.0s para evitar travamento do RCON do jogo, integrado com `is_restart_active()`. Implementa a lógica de tempo e envio do aviso prévio formatado usando rich text tags do SCUM chat.
* `app/routes/rcon_routine_routes.py`: Rotas `/api/rcon-routines` para listagem, criação, edição, remoção e teste instantâneo de rotinas. O endpoint `/test` retorna de forma síncrona a resposta detalhada da RCON em tempo real.
* `core/logs/online_monitor.py`: Hotfix do erro `'OnlinePlayersMonitor' object has no attribute 'gameplay_logs_path'` ajustando a ordem de inicialização do construtor.
* `main.py` & `app/extensions.py`: Registro e inicialização dos serviços de agendamento de rotinas RCON no startup e shutdown do backend.
* `scratch/test_rcon_routines.py`: Script de teste para validação automatizada das rotinas, incluindo validação da emissão de avisos no tempo correto.

---

## 💰 11. Configuração de Saldo Inicial e Resets de Jogador

### 1. Objetivo
Centralizar a definição do saldo inicial de novos jogadores e impedir a injeção indesejada do saldo de 5.000 pontos (antigo valor hardcoded) durante resets de manutenção no console ou interface gráfica do SSM. O saldo passa a ler a chave `economy.initial_balance` do `config.json` (padrão: `0`) e a auto-migrar o arquivo em servidores de usuários de forma transparente no startup.

### 2. Arquivos Modificados
* `main.py`: Atualizada a função `ensure_default_config_sections` para garantir a inserção automática do bloco `economy` com `initial_balance: 0` se ausente no `config.json`.
* `core/shop/wallet_service.py`: Implementado helper `_get_initial_balance` e ajustado `ensure_wallet_row` para usar o saldo da configuração quando o jogador se registra/vincula.
* `reset_player.py`: Alterada a query de redefinição SQL da carteira de jogador específico para usar o saldo configurado.
* `reset_all_players.py`: Alterada a query de redefinição SQL de lote para usar o saldo configurado.
* `gui/main_window.py`: Atualizadas as operações `_maintenance_reset_player` e `_maintenance_reset_all_players` na aba Maintenance para obter o saldo configurado e redefinir as carteiras de acordo, além de ajustar o texto descritivo correspondente na interface.

---

## 📢 12. Correção e Refinamento do Aviso Prévio das Rotinas RCON

### 1. Objetivo
Corrigir a lógica de envio de avisos prévios das rotinas periódicas de RCON. Anteriormente, rotinas recém-criadas (com `last_run = None`) ou que ficavam atrasadas/overdue (por exemplo, após o startup do backend ou se o app ficasse offline) executavam a rotina principal imediatamente sem aviso, ou disparavam o aviso prévio e a execução da rotina em paralelo no mesmo segundo, invalidando a finalidade do alerta prévio aos jogadores.

### 2. Solução Arquitetural
Implementou-se uma lógica inteligente que adia a rotina principal temporariamente caso o aviso prévio precise ser enviado:
1. **Nova Rotina (`last_run is None`)**: Se os avisos estiverem ativos, o sistema envia o aviso prévio imediatamente e atualiza o `last_run` para `now - (interval_minutes - warning_minutes_before) * 60` (ajustado retroativamente). Dessa forma, a execução dos comandos principais é adiada de forma precisa por `warning_minutes_before` minutos.
2. **Rotina Atrasada/Overdue (Startup/Shutdown)**: Se o tempo decorrido desde o último ciclo for maior que o intervalo programado e o aviso prévio deste ciclo ainda não foi enviado, o sistema dispara o aviso imediatamente e ajusta o `last_run` retroativamente da mesma forma, garantindo que a rotina principal execute no chat após exatamente `warning_minutes_before` minutos.
3. **Prevenção de Sobreposição**: Evitou-se o disparo simultâneo do aviso e dos comandos principais no mesmo ciclo, isolando o envio do alerta e atualizando o rastreador de mensagens enviadas de forma persistente.

### 3. Arquivos Modificados
* `core/scheduler/rcon_routine_scheduler.py`: Refatorada a função `_check_and_run_routines` introduzindo o helper interno `_send_warning` e as tratativas para novos estados e rotinas atrasadas.
* `app/routes/rcon_routine_routes.py`: Modificado o endpoint de teste manual `/api/rcon-routines/<routine_id>/test` para injetar e disparar o comando de aviso prévio (`#say`) no topo da fila se o aviso prévio estiver ativo na rotina, permitindo auditoria visual direta no jogo do alerta.
* `scratch/test_rcon_routines.py`: Adicionados novos cenários de testes automatizados (`6.1` e `6.2`) simulando rotinas novas e overdue com envio de avisos prévios, validando o cálculo de last_run retroativo e o correto agendamento. Todos os testes integrados passaram com sucesso.

---

## ⏱️ 13. Sistema de Recompensas por Tempo de Jogo (Playtime Rewards System) & Auditoria no Discord

### 1. Objetivo
Refatorar e aprimorar o sistema de recompensas por tempo de jogo no SCUM, adicionando persistência resiliente com período de tolerância (Grace Period) para desconexões temporárias, mitigação de bugs de fuso horário e canais de auditoria em texto puro e em inglês no Discord.

### 2. Nova Arquitetura de Sessão Resiliente e Auditoria
* **Período de Tolerância (Grace Period)**: Adicionada a chave `playtime_rewards.grace_period_minutes` (padrão `5`) nas configurações do sistema. Quando um jogador desconecta, sua sessão de jogo não é destruída imediatamente. O progresso de minutos acumulados é congelado e o timestamp de desconexão é salvo em `playtime_sessions.json` sob a chave `offline_since`. Se ele retornar dentro de 5 minutos, a sessão é restaurada sem perdas de progresso. Se exceder a tolerância, o progresso acumulado na hora parcial é descartado permanentemente.
* **Fuso Horário Unificado (UTC)**: Todos os logs e análises de sessões e timestamps locais e de banco de dados usam estritamente o padrão UTC (via `datetime.utcnow()`), blindando o sistema contra discrepâncias de fuso horário do servidor de hospedagem.
* **Logs de Auditoria em Inglês**: Todas as mensagens de status de auditoria no Discord são enviadas exclusivamente em inglês para o canal `⏱️┃playtime-rewards` (gerido no `WebhooksManager` e provisionado pelo botão "Create/Sync Channels"). O formato usa texto simples de alto contraste (sem embeds) com crases estrategicamente posicionadas em volta de chaves como nomes de jogadores, SteamIDs, saldos, e regras (ex: `Player Jessynha (SteamID: 76561198962669673 | Discord: @Jessynha) completed 1 hour(s) online and earned +6 points (Rule: VIP). New balance: 6 points.`).
* **Concorrência e Performance**: O saldo do jogador no tick de sessão de recompensas é buscado diretamente da tabela de carteiras (`wallet`) utilizando a conexão ativa da transação (`ssm_tx`), prevenindo deadlocks no SQLite decorrentes de múltiplas threads solicitando locks concorrentes de escrita. Logs de auditoria são disparados apenas para jogadores registrados/vinculados ao Discord.

### 3. Arquivos Criados e Modificados
* `core/shop/rewards_service.py`: Refatoradas as rotinas de tick global (`tick_playtime_reward_all_players`) e multi-regras (`tick_playtime_reward_multi_rules`) adicionando resiliência de banco, tolerância de logout e parsing UTC unificado. Também foi corrigido o carregamento de webhooks no método `_load_config()`, que antes lia apenas `config.json` e deixava os webhooks vazios (já que as URLs residem no arquivo `webhooks.json`).
* `core/webhooks/manager.py`: Registrado o canal `playtime_rewards` na lista de canais default e de sincronização do painel administrativo.
* `core/webhooks/discord_webhook.py`: Adicionado o método `send_text_webhook` para enviar mensagens formatadas de texto simples de alto contraste para o Discord.
* `core/logs/online_monitor.py`: Corrigido o fuso horário usando `datetime.utcnow()` para o cálculo de tempo online.
* `data/config.example.json` & `data/config.json`: Adicionada a chave `"grace_period_minutes": 5` sob as configurações de playtime_rewards.
* `scratch/test_playtime_rewards.py`: Script de integração cobrindo fluxos de login, ticks subsequentes, desconexão (início da tolerância), reconexão no grace period e validação de todas as mensagens em inglês no webhook.

---

## 👥 14. Correção e Customização do Canal de Jogadores Online (Delimitador `|`)

### 1. Objetivo
Corrigir a perda permanente de emojis e caracteres especiais no canal de monitoramento de jogadores online (`players_online`) do Discord e permitir que os administradores personalizem o título do canal diretamente no Discord ou na configuração, mantendo a atualização dinâmica da contagem de jogadores de forma não destrutiva.

### 2. Solução Implementada
* **Sanitização Unicode-safe**: Refatorada a função `_sanitize_discord_channel_name` no `OnlinePlayersMonitor` para não remover mais emojis (ex: `👥`, `🛜`), a barra vertical `┃` e outros caracteres Unicode não-ASCII. Agora, a sanitização apenas normaliza caracteres ASCII para minúsculas, remove caracteres de controle inválidos e substitui múltiplos espaços/hífens por um único hífen, alinhando-se com a especificação padrão do provisionador oficial do SSM.
* **Detecção e Atualização por Delimitador (`|`)**:
  * Modificada a lógica de renomeação no `OnlinePlayersMonitor` para pesquisar o caractere pipe (`|`) no título atual do canal no Discord.
  * Se o delimitador `|` estiver presente (ex: `"👥┃players-online|13"`), o monitor separa a string e extrai apenas o que está à esquerda como nome base (`"👥┃players-online"`), preservando emojis, símbolos e formatação personalizada dos administradores.
  * Se o delimitador não estiver presente, o monitor usa o nome do canal como base e anexa o delimitador junto com o número (ex: `"🛜online"` virando `"🛜online|19"`).
  * No próximo tick de atualização, apenas a parte após o `|` é modificada com o novo número de jogadores online.

### 3. Arquivos Modificados
* `core/logs/online_monitor.py`: Refatoradas as funções `_sanitize_discord_channel_name` e `_rename_discord_channel_online_count` para implementar a nova regra baseada em `|` e a sanitização compatível com caracteres Unicode.

---

## ⏳ 15. Sistema Global de Expiração de Atributos (Attribute Expiration System)

### 1. Objetivo
Implementar um sistema global de expiração automática para upgrades de atributos comprados na loja virtual de forma justa e uniforme (válido para todos os atributos, sem distinção de nível). Quando o período de expiração configurado expira, o atributo do jogador deve retornar ao seu valor base (original) de forma atômica no banco de dados e notificar os administradores via Discord.

### 2. Solução Implementada
* **Estrutura de Armazenamento**: A configuração de expiração é armazenada no banco `app_config` do `SSM.db` sob chaves consistentes:
  * `attributes.expiration.enabled` (booleano)
  * `attributes.expiration.duration_days` (inteiro >= 1)
* **API Unificada**: O endpoint `/api/attributes/prices` foi estendido:
  * `GET`: Retorna a lista de preços e as configurações de expiração vigentes.
  * `PUT`: Salva em transação atômica os preços de atributos atualizados e as regras de expiração (ligar/desligar e duração em dias).
* **Agendador Periódico (`AttributeExpirationScheduler`)**: Roda periodicamente verificando o banco de dados. Ao detectar atributos expirados de um jogador, inicia o processo de regressão de atributos de volta para os valores bases registrados quando ele adquiriu o primeiro upgrade.
* **Canal de Logs no Discord**: Integração com o canal `#shop-log` para notificar os administradores marcando os IDs de usuários do Discord correspondentes quando seus atributos expiram e são desfeitos.

### 3. Arquivos Modificados
* `app/routes/admin.py`: Estendida a rota `/api/attributes/prices` (GET e PUT) para manusear as configurações de expiração de forma transacional.
* `core/scheduler/attribute_expiration_scheduler.py`: Criado o agendador e o fluxo completo de regressão de atributos no banco do SCUM.
* `main.py`: Integrado o `AttributeExpirationScheduler` no loop de inicialização e ciclo de vida do backend.

---

## 🌐 16. Patches de Conexão Frontend e Estabilidade do Discord

### 1. Objetivo
Resolver o bloqueio de requisições de login originadas do frontend web devido à falta de regras de CORS no backend Flask e corrigir a duplicação progressiva do contador de jogadores no canal do Discord (ex: `online1313`, `online131313`).

### 2. Solução Implementada
* **Configuração de CORS**: Adicionadas as origens `http://localhost:5173` e `http://127.0.0.1:5173` no factory `create_app` em `app/__init__.py`. Isso permite que o frontend se autentique com sucesso e envie requisições autenticadas por cookies/tokens via Axios/Fetch no ambiente de desenvolvimento ou produção.
* **Prevenção de Duplicação no Discord**: 
  * O método `_rename_discord_channel_online_count` foi reestruturado para usar a regex `re.sub(r"[|┃ \-~•·_]*\d+$", "", base)` ao ler o nome do canal do Discord. Isso remove de forma limpa qualquer número e delimitador anterior no final do nome, neutralizando a perda do pipe (`|`) original quando o Discord o remove automaticamente dos canais de texto.
  * O bot detecta inteligentemente se o canal usa a barra Unicode grossa (`┃`) e a usa como delimitador definitivo (ex: `👾┃online┃13`), preservando o layout visual e eliminando as duplicações acumuladas.

### 3. Arquivos Modificados
* `app/__init__.py`: Incluídas as origens da porta 5173 na lista de origens autorizadas pelo CORS.
* `core/logs/online_monitor.py`: Refatorado o método `_rename_discord_channel_online_count` com limpeza regex de números finais e escolha inteligente de delimitador Unicode.

---

## 🖥️ 17. Estabilidade de Inicialização e Correção do Scheduler

### 1. Objetivo
1. Corrigir falsos positivos na inicialização do backend que ocorriam quando portas da API (ex: 3000) possuíam sockets obsoletos em estado de cooldown `TIME_WAIT` (ex: após fechar o Docker ou outros apps), impedindo o painel GUI de iniciar o servidor Flask local.
2. Corrigir o bug onde as alterações nos horários de reinicialização do agendador feitas pelo frontend web não eram persistidas no arquivo `data/config.json`.

### 2. Solução Implementada
* **Detecção Precisa de Portas (`LISTEN` vs `TIME_WAIT`)**:
  * Refatorada a função `_find_backend_processes` e os helpers de verificação de status na GUI para buscar dinamicamente a porta de API configurada no `config.json` e filtrar conexões do sistema operacional buscando estritamente o estado **`LISTEN`** (usando `psutil.CONN_LISTEN`).
  * Conexões residuais em `TIME_WAIT` são agora ignoradas com sucesso. Também foi adicionado um filtro para desconsiderar o PID da própria GUI do SSM nas buscas de processos conflitantes.
* **Correção de NameError no Scheduler**:
  * Importado o módulo padrão `copy` do Python no topo do arquivo `app/routes/scheduler_routes.py`.
  * Isso corrige a falha silenciosa na chamada `copy.deepcopy(config)` executada na rota `POST /api/scheduler/config`, garantindo que as alterações de configuração feitas a partir do frontend sejam gravadas com sucesso no arquivo `data/config.json`.

### 3. Arquivos Modificados
* `gui/main_window.py`: Atualizada a lógica de filtragem de processos e validação de porta na GUI para usar filtros de conexões em estado `LISTEN` e ignorar o PID local.
* `app/routes/scheduler_routes.py`: Adicionado `import copy` na seção de imports do Blueprint do scheduler.

---

## 🤖 18. Exibição de Contagem de Jogadores Online no Bot do Discord (Status/Presença e Nickname)

### 1. Objetivo
Permitir que o Bot do Discord exiba em tempo real a quantidade de jogadores online em relação ao limite máximo de jogadores do servidor (ex: `5/64`). A informação deve ser exibida tanto na Atividade de Presença do Bot ("Assistindo X/Y Jogadores") quanto no Apelido do Bot dentro do servidor do Discord (ex: `[5/64] Nome-Do-Bot`), garantindo excelente visibilidade e alinhamento visual com servidores SCUM profissionais.

### 2. Solução Implementada
* **Atualização de Status no DiscordBotService**:
  * Adicionado o método thread-safe `update_bot_status(count, max_players)` que enfileira a corrotina assíncrona `_update_bot_status_async` no loop principal do bot do Discord usando `asyncio.run_coroutine_threadsafe`.
  * Na corrotina de atualização, o bot atualiza a sua presença (Atividade "Watching/Assistindo") e obtém o membro correspondente ao bot na Guild configurada (`guild_id`).
  * O apelido do bot é limpo usando expressões regulares para remover qualquer prefixo `[X/Y]` anterior e atualizado para `[count/max_players] NomeBase`, respeitando o limite de 32 caracteres do Discord. Falhas de permissão (ex: se o bot não tiver a permissão "Alterar Apelido") são capturadas graciosamente, mantendo o funcionamento da presença ativo.
* **Ciclo de Vida Integrado**:
  * **No Startup (`on_ready`)**: Assim que o Bot se conecta e fica pronto, ele consulta o `OnlinePlayersMonitor` (através do registro de serviços unificado `get_services()`) para obter a contagem inicial de jogadores e realizar a primeira atualização do status.
  * **Em Mudanças de Jogadores (`OnlinePlayersMonitor`)**: Sempre que o monitor de jogadores online detecta uma mudança real na contagem de jogadores (ou quando a atualização é forçada), ele aciona a chamada ao `update_bot_status` junto com a lógica de renomeação do canal.

### 3. Arquivos Modificados
* `core/discord_bot_service.py`: Implementados os métodos de atualização de status/apelido no `DiscordBotService` e adicionada a inicialização no evento `on_ready` do `SSMDiscordClient`.
* `core/logs/online_monitor.py`: Integrado o acionamento da atualização do status do bot no método `_send_status_notification` sempre que a contagem de jogadores online sofrer alterações.






---

## 🔒 19. Agendador de Webhooks de Raid Pessoais e Estabilização do Módulo de Prisão por TK (Squad TK Jail)

### 1. Objetivo
1. Finalizar o **Personal Webhook Scheduler** para gerenciar o ciclo de vida dos webhooks pessoais cadastrados por jogadores, descontando saldo dinamicamente via `WalletService` com renovação automática, avisos de proximidade de expiração no chat/DM e prevenção de abusos.
2. Resolver a divergência de estados no módulo **Squad TK Jail**, onde alterações administrativas feitas no dashboard web (como desativar o módulo) eram gravadas em disco no `config.json` mas ignoradas pelo serviço ativo na memória (que persistia rodando e punindo jogadores).
3. Corrigir a liberação de prisioneiros para retornar de forma confiável para o local original (coordenadas de onde foram presos) como fallback caso seu squad não possua uma bandeira ativa no mapa.

### 2. Solução Implementada
* **Sincronização de Configuração em Tempo Real (In-Memory)**:
  * Criada a função helper `sync_services_config(manager, services)` em `app/routes/config_routes.py`.
  * Integrado este helper em todas as rotas de gravação/alteração de configuração do painel (`PUT /api/config`, `PATCH /api/config`, `PUT /api/config/<section>` e `POST /api/config/restore`).
  * Esta alteração limpa e atualiza dinamicamente o dicionário global em memória `services.config` mantido pelo `ServiceRegistry`, garantindo que qualquer mudança no painel web se reflita instantaneamente nos serviços rodando em segundo plano.
* **Leituras Dinâmicas no Módulo de Prisão**:
  * Refatorado o `SquadTKJailService` para carregar seus parâmetros diretamente do dicionário de configuração ativo em tempo real (`self.config`) a cada chamada de lógica (`check_and_punish_tk`, `jail_player`, `release_player`, `_announce_message` e no loop periódico de monitoramento `_monitor_loop`).
  * O loop periódico de monitoramento agora respeita instantaneamente o estado `enabled: false`, interrompendo o monitoramento e o uso de recursos e economizando ciclos de processamento sem a necessidade de reiniciar o backend.
* **Integridade de Dados e Fallback de Coordenadas de Soltura**:
  * Modificada a estrutura da tabela `prison_records` no banco de dados SQLite (`SSM.db`) para armazenar as coordenadas de captura originais do jogador (`release_coords_x`, `release_coords_y`, `release_coords_z`).
  * No momento em que o jogador é enviado para a prisão (`jail_player`), o serviço obtém as coordenadas atuais de onde o jogador estava no jogo via `players_online` e as salva no banco de dados.
  * Na liberação (`release_player`), caso a bandeira do squad não seja encontrada ou o squad não tenha bandeira, o jogador é teleportado de volta de forma precisa para a posição exata onde estava antes de ser preso, evitando quedas do mapa ou teletransporte para `0,0,0`.
  * Ajustada a lógica do loop de monitoramento de suspensão (`_monitor_loop`) para que quando um jogador online tiver o tempo expirado (`new_remaining <= 0`), ele seja liberado e teleportado imediatamente.

### 3. Arquivos Modificados
* `app/routes/config_routes.py`: Adicionado `sync_services_config` e integrado nas rotas de modificação e restauração.
* `core/squads/squad_tk_punish_service.py`: Refatoração completa com verificação em tempo real de configs, migração automática do banco de dados, gravação/leitura de coordenadas originais do jogador e fallback robusto de soltura.
* `scratch/test_squad_tk_jail.py`: Criada suíte de testes unitários para validar a integridade do banco de dados, parsing e fallbacks de coordenadas do `SquadTKJailService`.
* `scratch/test_config_sync.py`: Criada suíte de testes unitários para validar a sincronização automática em tempo real do dicionário de configurações global Flask/ServiceRegistry.

---

## 🎯 20. Sistema Wanted Killstreak e Correção do Banco de Autenticação

### 1. Objetivo
1. Implementar o sistema **Wanted Killstreak (Procurado)**, com recompensas automáticas integradas à carteira virtual (`WalletService`), anúncios in-game do status e atualizações em tempo real no Discord (através de mensagens persistentes editadas via PATCH para evitar spam no canal).
2. Proteger o sistema contra abusos de claim de recompensa, impedindo que membros do mesmo squad (ou ex-membros recentes) ganhem os pontos ao matar o procurado.
3. Resolver o erro de "Credenciais inválidas" no login de administrador (`admin`), garantindo que o banco de dados e a configuração local estejam sincronizados com a senha correta (`12345678910`).

### 2. Solução Implementada
* **Sistema Wanted & Bounty (`BountyService`)**:
  * Implementação da tabela `player_killstreaks` e `bounty_claims` no `SSM.db`.
  * Criação da lógica de streaks: ao alcançar 5 kills PvP consecutivos (ou valor definido em `config.json`), o jogador fica marcado como procurado. A cada kill extra, o valor aumenta.
  * Desenvolvimento de validações de squad no método `verify_squad_relation` para impedir que membros do squad da vítima reinvindiquem a recompensa. Implementado um cooldown de 24 horas para jogadores que abandonaram o squad da vítima recentemente.
  * Otimização de transação de banco: passagem explícita do objeto `conn` para subfunções e para o `WalletService` para evitar deadlocks de transações no SQLite.
* **Discord Rankings Embeds**:
  * Em vez de enviar novas mensagens a cada alteração, o bot executa um método `PATCH` para editar a mensagem existente no Discord com a listagem dinâmica de procurados online/offline e o ranking TOP 20.
  * Fallback automático para o webhook global de kills (`top20_kills`) caso o webhook de procurados esteja vazio.
* **Correção do Banco de Autenticação**:
  * Identificado que o banco de dados armazena os dados dos usuários na tabela `frontend_users` e que o usuário `admin` estava cadastrado com o hash da senha padrão legada `"your-password-here"`, enquanto a senha esperada era `"12345678910"`.
  * Atualizado o arquivo `data/config.json` para definir `"default_password": "12345678910"`.
  * Executado script no banco `SSM.db` recalculando e atualizando o hash do usuário `admin` para a senha `"12345678910"`, resolvendo permanentemente o bloqueio de autenticação do painel administrativo.

### 3. Arquivos Modificados
* `core/survival/bounty_service.py`: Lógica central do sistema de procurado, checagem de squads e edição persistente no Discord.
* `core/shop/wallet_service.py`: Ajuste para suportar conexões atômicas externas nas transações de pagamento de recompensas.
* `app/routes/survival.py`: Criação das rotas REST de visualização, disparo manual, resets e edição da configuração.
* `data/config.json`: Atualização de chaves de autenticação administrativa.

---

## 🔧 21. Suporte Automatizado a Coordenadas no Agendador de Rotinas RCON

### 1. Objetivo
Permitir o agendamento e teste manual de comandos RCON contendo coordenadas geográficas complexas copiadas diretamente do jogo (telemetria da Unreal Engine no formato `{X=... Y=... Z=...|...}`). Corrigir também a falha onde eventos de mundo do SCUM (como `#ScheduleWorldEvent`) falhavam caso uma altitude (Z) diferente de `0` fosse fornecida.

### 2. Solução Implementada
* **Sanitização de Coordenadas de Comandos RCON (`sanitize_rcon_command_coords`)**:
  * Desenvolvido um parser regex robusto em `utils/sanitize.py` que detecta blocos `{X=... Y=... Z=...|...}` ou `{X=... Y=... Z=...}`.
  * Para o comando `#ScheduleWorldEvent`, o parser extrai as posições X e Y e obrigatoriamente define Z como `0` (ex: `X Y 0`), que é a sintaxe exigida pelo SCUM para spawnar drops a partir do céu. Adicionalmente, se o administrador digitar coordenadas limpas separadas por espaço manualmente com um Z diferente de zero (ex: `X Y Z`), o parser corrige o Z automaticamente para `0`.
  * Para o comando `#teleport`, o parser substitui a telemetria Unreal por coordenadas limpas separadas por espaço (ex: `X Y Z`), preservando a altitude Z original para que o jogador não caia no limbo ou sofra danos de queda.
  * Outros comandos permanecem intocados para evitar interferências.
* **Integração Completa**:
  * **Agendamento em Segundo Plano**: Integrado o método de sanitização em `RconRoutineScheduler.execute_routine` antes de enfileirar cada comando no `RconQueueManager`.
  * **Testes Manuais de Rotinas**: Integrada a mesma higienização no endpoint de teste `/api/rcon-routines/<routine_id>/test` em `app/routes/rcon_routine_routes.py`.
* **Testes de Validação**:
  * Criado o script `scratch/test_coords_sanitization.py` que valida a conformidade com diversos casos de teste (formatos Unreal, formatos com aspas, coordenadas limpas manuais e outros comandos).

### 3. Arquivos Modificados
* `utils/sanitize.py`: Adicionada a função `sanitize_rcon_command_coords`.
* `core/scheduler/rcon_routine_scheduler.py`: Integrado no fluxo de execução do agendador periódico.
* `app/routes/rcon_routine_routes.py`: Integrado na rota de teste manual de rotinas.
* `scratch/test_coords_sanitization.py`: Criada suíte de validação de comandos com coordenadas.

---

## 🔒 22. Preservação de Preços de Atributos Customizados no Startup

### 1. Objetivo
Corrigir a falha onde a liberação de novas atualizações do backend ou a reinicialização do servidor resetava os preços de upgrades de atributos (cadastrados no painel administrativo) para o valor padrão de 100.000 contido no `config.json`.

### 2. Solução Implementada
* **Verificação Prévia de Existência de Registros**:
  * Refatorada a função `_init_attribute_upgrade_prices` em `utils/database_initializer.py`.
  * Adicionada a checagem `SELECT COUNT(*) FROM attribute_upgrade_prices` na tabela do banco `SSM.db`.
  * Se o banco já contiver registros (preços customizados configurados pelo usuário), a função loga que os dados serão mantidos e interrompe o processo sem executar a limpeza destrutiva (`DELETE FROM attribute_upgrade_prices`).
* **Carga Apenas em Bancos Zerados/Novos**:
  * A importação de `config.json` ou o preenchimento de fallback só ocorre se a tabela `attribute_upgrade_prices` estiver completamente vazia (`count == 0`).
* **Validação de Persistência**:
  * Criado o script de teste automatizado `scratch/test_attribute_prices_persistence.py` que simulou cargas iniciais, alterações de usuários e reinicializações com arquivos de configuração de atualização, confirmando a preservação dos dados.

### 3. Arquivos Modificados e Criados
* `utils/database_initializer.py`: Refatoração da rotina `_init_attribute_upgrade_prices` com verificação de registros existentes antes do seed.
* `tools/ResourceHacker.ini`: Atualização do caminho MRU para o novo diretório `C:\Projetos\SSM\SSM 3.0\Backend\dist\Panel SSM.exe`.
* `scratch/test_attribute_prices_persistence.py`: Criado script de teste para validação de persistência dos preços de atributos.

---

## 🧹 23. Limpeza Automatizada e Manual de Logs do SCUM (GUI & Discord)

### 1. Objetivo
Evitar o acúmulo excessivo de arquivos de log no diretório do servidor SCUM (`Saved/SaveFiles/Logs`), permitindo ao administrador definir regras de retenção (por idade e tamanho total) com disparo automático no startup/agendamento, além de permitir limpeza sob demanda através da interface gráfica com envio de relatório para o canal de auditoria do Discord.

### 2. Solução Implementada
* **Configuração e Retenção na GUI**:
  * Adicionado card ultra-compacto na aba **Maintenance** do `Panel SSM` para gerenciamento das configurações de limpeza (`enabled`, `max_age_days`, `max_total_size_mb`).
  * Botão **"Limpar Logs Agora"** com diálogo de confirmação exibindo a volumetria e quantidade de arquivos a serem deletados.
* **Relatório de Auditoria (`log-ssm`)**:
  * Geração e envio de embed detalhado para o webhook `log-ssm` contendo quantidade de arquivos deletados, espaço liberado em disco (MB) e lista resumida de categorias apagadas.

### 3. Arquivos Modificados
* `gui/views/maintenance_view.py`: Adicionados controles de interface, persistência de configurações e método `_run_logs_cleanup_now()`.
* `core/server_control/server_manager.py`: Rotina central de expurgo e cálculo de espaço de logs do SCUM.

---

## 🔴 24. Alerta Dinâmico no Live Embed do Discord (Despoluição do Canal `serverstatus`)

### 1. Objetivo
Eliminar a poluição contínua do canal **`🟢┃serverstatus`**, onde cards soltos de contagem regressiva de restart (`Restart in 10m`, `5m`, `1m`) e avisos de status (`Server Starting`, `Server Started`) eram enviados continuamente e ficavam acumulados sem serem apagados.

### 2. Solução Implementada
* **Canal Exclusivo para o Live Embed**:
  * O canal `🟢┃serverstatus` passa a manter única e exclusivamente a mensagem permanente do Live Dashboard Embed editada in-place (`PATCH /messages/{id}`).
  * Nenhuma mensagem avulsa de contagem regressiva é postada no canal.
* **Embed Reativo com Alertas de Restart**:
  * Em `core/scheduler/weather_scheduler.py`, o método `_get_next_restart_info()` calcula os minutos restantes para o próximo restart.
  * O título e cor do card principal mudam dinamicamente:
    * **Normal (> 10 min)**: `🟢 SERVER ONLINE — {Nome}` | Cor Verde (`#2ecc71`).
    * **Aviso (<= 10 min)**: `🟡 RESTART WARNING — {Nome}` | Cor Amarela (`#f1c40f`) | `⚠️ RESTART IN {X} MINUTE(S)!`.
    * **Crítico (<= 3 min)**: `🔴 RESTART IMMINENT — {Nome}` | Cor Vermelha (`#e74c3c`) | `🔴 RESTART IMMINENT IN {X} MINUTE(S)!`.
    * **Final (<= 1 min)**: `🚨 RESTART IN LESS THAN 1 MINUTE!`.
    * **Reiniciando / Offline**: `🔄 SERVER RESTARTING / OFFLINE — {Nome}` | Cor Laranja (`#e67e22`).
* **Refresh Imediato (`trigger_immediate_refresh`)**:
  * Em `main.py` (`scheduler_notification_callback`) e `core/webhooks/discord_webhook.py` (`send_server_status`), ao ocorrer um gatilho de aviso de restart ou mudança de status, o Live Embed é atualizado imediatamente sem aguardar o tick de 60s.
* **Redirecionamento de Logs Operacionais**:
  * Mensagens técnicas de ciclo de vida (`Server Starting`, `Server Started`, `Restart Started`, `Restart Completed`) foram roteadas para o canal administrativo **`🛰️┃log-ssm`**.

### 3. Arquivos Modificados
* `core/scheduler/weather_scheduler.py`: Cálculo de minutos restantes, títulos/cores dinâmicos e método `trigger_immediate_refresh()`.
* `main.py`: Ajuste de `scheduler_notification_callback` para atualizar o embed dinamicamente e enviar eventos para `log-ssm`.
* `core/webhooks/discord_webhook.py`: Roteamento de `send_server_status` para `log-ssm` com refresh imediato do live embed.

---

## ⚡ 25. Otimização de Inicialização do Executável (Migração para `--onedir`)

### 1. Objetivo
Solucionar a lentidão crítica de inicialização do executável `Panel SSM.exe` em produção (levava de 10 a 30 segundos para abrir a janela desktop).

### 2. Diagnóstico da Causa Raiz
* O empacotamento com PyInstaller estava em modo **`--onefile`**, gerando um executável monolítico de **180.7 MB**.
* A cada execução (duplo clique), o Windows/PyInstaller precisava descompactar os 180 MB por completo em uma pasta temporária (`%TEMP%\_MEIXXXXXX`) antes de executar o Python, além do tempo extra gasto pelo antivírus do Windows escaneando centenas de arquivos extraídos.

### 3. Solução Implementada
* **Migração para `--onedir`**:
  * Em `ssm_backend.spec`, removidos os binários/zipfiles/datas do objeto `EXE()` e adicionada a seção `COLLECT()`.
  * O executável `Panel SSM.exe` foi reduzido de **180.7 MB para 12.3 MB**.
  * Todos os binários e dependências Python (205 MB) agora residem pré-extraídos na pasta `_internal/` dentro da distribuição (`dist/Panel SSM/`).
* **Ajustes no Script de Cópia (`copy_data_files.py`)**:
  * Atualizada a detecção da pasta destino para reconhecer automaticamente a estrutura de diretórios `dist/Panel SSM/`.
* **Resultado**:
  * **Tempo de inicialização reduzido para ~1 segundo** (abertura instantânea da GUI).
  * Eliminação de 100% da escrita e extração contínua no disco temporário `%TEMP%`.

### 4. Arquivos Modificados
* `ssm_backend.spec`: Migração do build de `--onefile` para `--onedir` com `COLLECT()`.
* `tools/copy_data_files.py`: Detecção inteligente de caminhos para distribuição em pasta `dist/Panel SSM/`.

---

## 🎨 26. Tela de Preparação Integrada na Janela Principal

### 1. Objetivo e Desafio
* Fornecer resposta visual imediata no duplo clique do executável `Panel SSM.exe` através de uma tela de preparação animada.
* Evitar os problemas de renderização do Windows DWM que ocorriam com janelas secundárias separadas (*frameless toplevels*).

### 2. Solução Definitiva (In-Window Overlay)
* A tela de preparação foi integrada **diretamente dentro da janela principal (`MainWindow`)**:
  * Ao dar duplo clique, a janela principal abre instantaneamente (< 50ms) exibindo a tela de preparação escura com a Logo oficial do SSM, título, versão, barra de progresso animada e mensagens de status.
  * A montagem da interface e seus controles é executada de forma assíncrona (`self.after(30, ...)`).
  * Ao concluir, a tela de preparação faz uma transição suave e revela o painel de controle principal sem qualquer janela fantasma, artefato visual ou conflito de Tkinter.

### 3. Arquivos Modificados
* `gui/main_window.py`: Implementados `_show_startup_overlay()`, `_async_init_main_dashboard()` e `_reveal_main_dashboard()`.
* `version.py`: Atualizado para a versão `3.22.65`.

---

## 💬 27. Substituição do Botão do Site pelo Convite Oficial do Discord

### 1. Objetivo
Substituir o atalho antigo do site `scumsm.com` no cabeçalho da janela principal pelo convite oficial do canal da comunidade SSM no Discord (`https://discord.gg/EHwQTKWAtv`).

### 2. Solução Implementada
* **Atualização do Ícone e Tooltip (`gui/main_window.py`)**:
  * Substituído o ícone `www.png` pelo logo oficial `Discord-Symbol-Blurple.png`.
  * Tooltip atualizado para `"SSM Discord Community"`.
* **Redirecionamento do Navegador**:
  * Implementado o método `_open_discord_community()` apontando diretamente para `https://discord.gg/EHwQTKWAtv`.
* **Build e Versão**:
  * Versão incrementada para `3.22.66`.

---

## 🌐 28. Estruturação e Publicação do Monorepo Open Source no GitHub

### 1. Objetivo
Unificar o ecossistema do **SSM 3.0** (Backend Python e Frontend React/Vite) em um único repositório público no GitHub ([PauloPedreiro/Scum-Server-Manager](https://github.com/PauloPedreiro/Scum-Server-Manager.git)), adotando arquitetura de Monorepo com licença de código aberto (MIT), documentação profissional e blindagem total contra vazamento de segredos, bancos de dados e credenciais de produção.

### 2. Solução Implementada
* **Novo Repositório Limpo na Raiz**:
  * Inicializado o Git diretamente em `C:\Dev\SSM\SSM 3.0` como repositório monorepo (`main`).
  * Repositórios `.git` internos antigos foram migrados com segurança para pastas de backup (`.git_old` e `.git_old_root`), evitando a criação indesejada de submódulos Git e eliminando históricos legados com artefatos pesados do `dist/`.
* **Blindagem de Segurança com `.gitignore` Rigoroso**:
  * Ignorados todos os bancos SQLite de produção e desenvolvimento (`*.db`, `*.db-wal`, `*.db-shm`), preservando apenas bancos template oficiais.
  * Ignorados arquivos de segredos, senhas e credenciais (`config.json`, `webhooks.json`, `identity.json`, `license.json`, `.env*`).
  * Ignoradas predefinições confidenciais do servidor (`default.ini` em `Backend/data/server_settings_presets/`).
  * Ignorados diretórios de build e dependências (`dist/`, `build/`, `node_modules/`, `venv/`).
* **Documentação e Licenciamento Aberto**:
  * **`LICENSE`**: Criação da licença **MIT** oficial sob autoria de *Paulo Pedreiro (2026)*.
  * **`README.md`**: Elaboração de documentação completa em inglês com visão geral, badges, arquitetura de pastas, destaques técnicos (RCON Prioritário, Discord Bot, Playtime Rewards, Bounty, Shop) e guias passo a passo de *Quick Start* para Backend e Frontend.
* **Envio para o GitHub**:
  * Configurada a identidade do autor (`Paulo Pedreiro`).
  * Realizado o commit inicial e push com sucesso para `https://github.com/PauloPedreiro/Scum-Server-Manager.git`.

### 3. Arquivos Criados e Modificados
* `.gitignore`: Regras unificadas de exclusão para o ecossistema Python + Node.js.
* `LICENSE`: Termo da Licença MIT.
* `README.md`: Documentação oficial do projeto no GitHub.
* `Backend/.gitignore`: Inclusão de `default.ini` e regras estritas de banco de dados.
* `Backend/tools/setup_monorepo.ps1`: Script automatizado de criação e setup de ambientes monorepo.

---

## 📜 29. Transição para Licença GNU GPL v3, Código de Conduta, Guia de Contribuição e Showcase Visual

### 1. Objetivo
Alinhar o licenciamento do **Scum Server Manager** com o modelo copyleft forte utilizado nos projetos abertos do autor (como o *humanize*), adotando a licença **GNU General Public License v3 (GPL-3.0)** para garantir que o código permaneça sempre livre e comunitário. Adicionar também os padrões oficiais de governança aberta (**Código de Conduta** e **Guia de Contribuição**) e enriquecer o `README.md` com uma galeria completa de capturas de tela do Web Dashboard e Desktop GUI.

### 2. Solução Implementada
* **Licenciamento GNU GPL v3**:
  * Substituição do texto da licença `LICENSE` pela versão integral e oficial da **GNU General Public License v3, 29 June 2007** (Free Software Foundation).
* **Governança Comunitária**:
  * **`CODE_OF_CONDUCT.md`**: Implementado o padrão internacional *Contributor Covenant versão 2.1*, estabelecendo normas de respeito, acolhimento e diretrizes de moderação para a comunidade e Discord oficial.
  * **`CONTRIBUTING.md`**: Guia detalhado para desenvolvedores externos contendo fluxo de bugs, sugestões, configuração local de ambiente (Backend Python + Frontend Vite), padrões de segurança RCON/SQLite, formato de commits convencionais (`feat:`, `fix:`) e ciclo de vida de Pull Requests.
* **Galeria Visual no `README.md`**:
  * Normalização e renomeação semântica das 18 capturas de tela em `Backend/docs/images/` cobrindo:
    * **Web Dashboard**: Login, Visão Geral de telemetria e seletor de plano de fundo.
    * **Mapa Interativo**: Grade cartográfica do SCUM com localização de baús e bandeiras.
    * **Gestão de Jogadores**: Permissões granulares, rastreamento de veículos, estatísticas de sobrevivência/combate, economia/bancos e relatórios gráficos de picos de jogadores online.
    * **Loja & Economia**: Catálogo de itens, preços customizados de atributos com rollback automático por expiração, sistema Wanted (Bounty PvP) e notificações RCON.
    * **Automação & Anti-Abuso**: Agendador de reinicializações e comandos RCON, proteção de bandeiras contra minas ilegais, prisão Squad TK Jail e Kill Feed com trash-talk.
    * **Desktop GUI**: Painéis nativos em Tkinter de logs, RCON e configurações.
  * Atualização dos badges para GPL-3.0 e inclusão de links diretos de navegação para a documentação de governança.

### 3. Arquivos Criados e Modificados
* `LICENSE` & `Backend/LICENSE`: Termos oficiais da GNU GPL v3.
* `Backend/docs/images/`: 18 capturas de tela organizadas e normalizadas.

---

## 📺 30. Integração do Canal Oficial do YouTube e Comunidade Discord

### 1. Objetivo
Disponibilizar os links oficiais dos canais de suporte e aprendizado do projeto para a comunidade global de administradores de servidores SCUM:
* **Canal/Playlist Oficial do YouTube**: `https://www.youtube.com/playlist?list=PLqCDQyorrHOI3_RW1sDcc3NWppW4Y98T6` (tutoriais em vídeo passo a passo).
* **Discord da Comunidade Oficial**: `https://discord.gg/EHwQTKWAtv` (suporte, novidades e desenvolvimento).

### 2. Solução Implementada
* **`README.md`**:
  * Adicionado badge temático oficial do YouTube no cabeçalho superior.
  * Inclusa a seção dedicada **"📺 Video Tutorials & Guides"** antes do *Quick Start* com botão de chamada para ação e link direto para a playlist.
  * Atualizado o rodapé com botões de acesso direto ao Discord e YouTube.
* **`CONTRIBUTING.md`**:
  * Incluídos os links da playlist do YouTube e do Discord oficial na seção de comunicação comunitária para apoiar novos desenvolvedores.

### 3. Arquivos Modificados
* `README.md` & `Backend/README.md`
* `CONTRIBUTING.md` & `Backend/CONTRIBUTING.md`

---

## 🚀 31. Implementação do Gerenciador Nativo BSBR-SCUM, Versionamento Automático e Atualizador Seguro

### 1. Objetivo
Modernizar a arquitetura de comunicação e gerenciamento RCON do SSM 3.0, descontinuando a antiga seleção manual de múltiplos motores (como o `scum_rcon` legado) e estabelecendo o **BSBR-SCUM** (desenvolvido pelo Mazzotti com suporte a Source RCON na porta 28015 e API na porta 27100) como motor RCON nativo oficial. Implementar detecção automática de versão, fluxo de atualização com backup/rollback e trava de segurança contra processos em execução.

### 2. Solução Implementada
* **Detecção Robusta de Versões (`utils/rcon_mod_manager.py`)**:
  * **Recursos Binários PE (Windows)**: Extração precisa da `FileVersion` em `main.dll` via Win32 API (`GetFileVersionInfoW` / `VerQueryValueW` com `ctypes`).
  * **Fallback Estruturado**: Leitura da primeira linha de `version.txt` (`bsbr_scum X.Y.Z`), ignorando carimbos dinâmicos de runtime (como `carregado <timestamp>`).
  * **Inspeção de Pacotes**: Comparação semver automática entre os pacotes novos descompactados em `data/mods/bsbr_scum` e os binários em `SCUM/Binaries/Win64`.
* **Proteção Ativa e Atualizador Seguro**:
  * **Trava de Processo**: Verificação em tempo real de `SCUMServer.exe`. Se o servidor estiver ativo, o botão de atualização na interface é travado para prevenir `PermissionError` e corrupção de DLLs em memória.
  * **Backup Automático & Rollback**: Criação de snapshots em `data/mods/_backup/bsbr_scum_<versao>_<data>`, mantendo os últimos 5 backups e executando restauração automática em caso de falha de I/O.
  * **Preservação de Configurações**: Preservação estrita do `config.ini` pré-existente do servidor durante atualizações, impedindo perda de senhas, portas ou configurações de jogadores.
  * **Sincronização Cirúrgica de Credenciais**: Atualização direta da seção `[source]` do `config.ini` preservando comentários e outras seções.
* **Cliente Source RCON Oficial (`utils/rcon_client.py`)**:
  * Rota do `get_rcon_client_from_config` padronizada para o protocolo Source RCON nativo na porta padrão `28015`.
  * Implementação da função `query_live_mod_version` para telemetria em tempo real do mod via comando `version`.
* **Interface Gráfica Renovada (`gui/main_window.py`)**:
  * Substituição do diálogo legado de seleção por um painel limpo e integrado.
  * **Toggle Switch "Ativar RCON"**: Permite habilitar/desabilitar o mod dinamicamente no `mods.txt` (`bsbr_scum : 1/0`) e no `config.json`.
  * **Painel de Versões e Status**: Badges indicando versão instalada, versão do pacote disponível e status de execução do servidor.
  * **Botão Inteligente de Atualização**: Habilitado apenas quando o servidor está desligado e há nova versão disponível.
  * Atalhos para a pasta de atualizações (`data/mods/bsbr_scum`) e pasta do mod no servidor.
  * Limpeza de métodos obsoletos e duplicados no código da GUI.

### 3. Arquivos Criados e Modificados
* `Backend/utils/rcon_mod_manager.py`: Novo gerenciador nativo unificado com detecção PE, backups e sincronização INI.
* `Backend/utils/rcon_client.py`: Roteamento padrão para Source RCON 28015 e consulta `query_live_mod_version`.
* `Backend/gui/main_window.py`: Interface de controle de RCON remodelada e métodos obsoletos expurgados.
* `Backend/data/mods/bsbr_scum/`: Inclusão do pacote da versão `0.3.0` fornecido pelo Mazzotti.
* `Backend/diario_de_bordo.md`: Registro da Seção 31.


---

## ⚡ 32. Otimização e Entrega Instantânea de Compras da Loja via Chat In-Game (/buy) e RCON

### 1. Diagnóstico e Causa Raiz
* **Sintoma Relatado**: Jogadores digitavam `/buy <code>` no chat do SCUM para comprar um item e a entrega física não acontecia de imediato. Quando digitavam um segundo comando (frequentemente improvisando com `/sd` para ver o saldo), o item era subitamente entregue.
* **Diagnóstico Aprofundado nos Logs**:
  1. **Estrutura de Linha do Logger da Unreal Engine (Causa Principal)**: No logger do `SCUMServer.exe`, a quebra de linha `\n` é gravada no **início** de cada nova entrada de log (`b'\n\x002\x000\x002\x006...'`), enquanto o final da linha fecha com aspas simples (`'Canal: Mensagem'`) e **não possui `\n` ao final**. No `ChatCommandMonitor`, a condição `if not text.endswith("\n"):` sempre avaliava como verdadeira para o último comando digitado, empurrando a linha para `_pending_chat_text`. Somente quando um próximo comando chegava (como `/sd`), seu `\n` inicial fechava a linha anterior, liberando o `/buy` represado e retendo o `/sd`.
  2. **Sobrecarga de `ListPlayers` síncrono no RCON**: O `ShopDeliveryService` executava `ListPlayers` no RCON antes de entregar qualquer pedido. Se o retorno atrasasse ou falhasse, o pedido permanecia como `pending`. Em compras feitas pelo chat in-game, essa consulta era totalmente redundante, pois quem acabou de digitar no chat está comprovadamente online.
  3. **Latência de Polling no Worker**: O `ShopBuyJobWorker` operava com polling a cada 2 segundos (`poll_interval_seconds = 2.0`) e chamava `run_once(limit=10)`, concorrendo com a trava global de entregas periódicas offline.

### 2. Solução Implementada
* **Correção no Parsing de Linhas do Monitor de Chat (`core/logs/chat_command_monitor.py`)**:
  * Removida a exigência de `\n` no fim do buffer de texto.
  * O monitor agora analisa individualmente as linhas separadas por `\n`. Se o fragmento final terminar com aspas simples `'` ou for validado com sucesso por `_parse_chat_line()`, ele é processado imediatamente sem qualquer retenção. Linhas só são mantidas em `_pending_chat_text` se estiverem genuinamente truncadas.
* **Entrega Direta sem `ListPlayers` (`core/shop/delivery_service.py`)**:
  * Implementado o método `deliver_single_order_now(order_id)`.
  * Adicionado o parâmetro `bypass_online_check=True` em `_deliver_order_rcon`.
  * Para compras originadas no chat in-game, a chamada pesada de `ListPlayers` foi eliminada, disparando os comandos `spawnitem` e `SendChat` diretamente via RCON na mesma hora.
* **Fila de Execução Instantânea (`core/shop/shop_buy_job_worker.py`)**:
  * Introduzido sinalizador de evento entre threads (`_global_wake_event = threading.Event()`).
  * No momento em que `enqueue_buy_job` insere o pedido no SQLite, o worker é acordado instantaneamente no mesmo milissegundo (zero espera).
  * O processamento assíncrono agora invoca `svc.deliver_single_order_now(res.order_id)` em vez do batch genérico `run_once(limit=10)`.

### 3. Arquivos Modificados
* `Backend/core/logs/chat_command_monitor.py`: Suporte ao formato nativo de logs do SCUM (linhas terminadas em aspas simples sem `\n` final), entregando comandos de chat instantaneamente.
* `Backend/core/shop/delivery_service.py`: Criação de `deliver_single_order_now` e bypass de `ListPlayers`.
* `Backend/core/shop/shop_buy_job_worker.py`: Despertar instantâneo com `_global_wake_event` e entrega unitária imediata.
* `Backend/docs/SHOP_DELIVERY_RCON_INSTANTANEO.md`: Documentação técnica detalhada no padrão Obsidian.
* `Backend/docs/SHOP_ECONOMY_SYSTEM.md`: Atualização do fluxo de entrega do shop.

---

## 🛡️ 33. Blindagem Anti-Crash de Entregas RCON em Massa (Circuit Breaker, Serialização e Progresso por Sub-Item)

### 1. Diagnóstico do Incidente em Produção
* **Sintoma**: Quando múltiplos jogadores entravam no servidor simultaneamente e solicitavam kits de boas-vindas (`/register` e `/kit`), o servidor SCUM congelava a Game Thread (`"erro: sem resposta em 4s - o tick do jogo pode estar parado"`).
* **Causas Raiz Identificadas nos Logs (`rcon_2026-11-06.log` e `scum_backend.log`)**:
  1. **Concorrência sem Lock**: `deliver_single_order_now()` não adquiria o `_delivery_lock`, fazendo com que o `ShopDeliveryWorker`, o `ShopBuyJobWorker` e a thread do `/register` disparassem kits de vários jogadores em paralelo, intercalando dezenas de comandos `spawnitem` e `spawnvehicle` simultaneamente na Unreal Engine.
  2. **Cegueira de Erros do RCON**: O `RconClient` e o `ShopDeliveryService` tratavam qualquer texto retornado pelo socket (incluindo `"erro: sem resposta em 4s - o tick do jogo pode estar parado"`) como sucesso (`200 OK`). O SSM continuava metralhando o servidor travado por 30 minutos e ainda marcava os pedidos no banco como `delivered`, fazendo o jogador perder o kit único sem ter recebido os itens.
  3. **Sobrecarga da Game Thread**: Atores pesados (`Weapon_*` e veículos `BPC_*` / `BP_*`) eram instanciados a cada `0.5s` sem intervalo entre um kit e outro no momento crítico em que múltiplos jogadores estavam carregando o mapa.
  4. **Comandos Malformados Cadastrados em Kits**: Presença de typos como `Water_051` (número `1` no lugar da letra `l` de `Water_05l`, forçando varredura síncrona de Blueprints inexistentes na UE4) e `Cash 1 StackCount 5000 2` (duplicidade de quantidade quando `StackCount` estava embutido no `setup`).

### 2. Solução Implementada
* **Serialização Global e Cooldown entre Pedidos (`core/shop/delivery_service.py` & `core/logs/chat_command_monitor.py`)**:
  * `deliver_single_order_now()` agora adquire `_delivery_lock`, e o `/register` também utiliza `deliver_single_order_now(order_res.order_id)`.
  * Adicionado `_wait_inter_order_cooldown()` (`2.5s` obrigatórios entre o término de um pedido RCON e o início do próximo).
* **Detecção de Congelamento de Tick + *Circuit Breaker* (`utils/rcon_client.py` & `core/rcon_queue_manager.py`)**:
  * Implementadas `is_rcon_tick_frozen()` e `is_rcon_error_response()` para identificar travamentos da Game Thread e falhas de execução.
  * Implementado disjuntor automático (`is_circuit_open` / `trip_circuit` de `15s` a `45s`) no `RconQueueManager`. Quando o tick do servidor congela, comandos de spawn subsequentes são abortados em `0ms` sem sobrecarregar o socket do servidor.
* **Persistência Granular Sub-Item a Sub-Item em Kits (`core/shop/delivery_service.py`)**:
  * Cada sub-item de um kit (`KIT:...`) tem seu progresso salvo individualmente em `shop_delivery_item` (usando códigos sintéticos negativos durante a entrega).
  * Se o servidor travar no meio de um kit (ex.: no 11º item), a entrega é **abortada imediatamente**, o pedido retorna para `status='pending'` (via `_revert_or_fail_order`) e, quando o servidor recupera o tick, a entrega retoma exatamente do sub-item onde parou, sem perder o kit e sem duplicar itens ou veículos já entregues.
* **Execução Nativa via `as <SteamID>` em vez de `Location "<SteamID>"` (`v3.22.73` — Causa Raiz no Binário `main.dll` do `bsbr_scum 0.3.0`)**:
  * A engenharia reversa do binário `main.dll` (`bsbr_scum 0.3.0`, funções `0x383a0` `exec_admin_cmd`, `0x4e1a0` `rewrite_location`, `0x45420` `as` e `0x30ae0` `fantasma`) revelou por que `spawnitem Weapon_MP5 1 Location "<SteamID>"` congelava o `SCUMServer.exe` mesmo sendo o 1º item do kit:
    1. Quando o comando utiliza `Location "<SteamID>"`, o `bsbr_scum` **não define** o ponteiro global `g_target_controller` (`[0xa0f68]` permanece `NULL`) e apenas reescreve `Location "<SteamID>"` para `Location "{X=... Y=... Z=...|P=0 Y=0 R=0}"`.
    2. Em `0x383a0` (`exec_admin_cmd`), quando `g_target_controller == NULL`, o mod verifica `IsUserAdmin` (`0x3e0f0`). Se nenhum administrador cadastrado no `AdminUsers.ini` estiver online no servidor, `IsUserAdmin` retorna `false` e o mod **descarta os jogadores reais e instancia/usa o `g_fantasma_controller` (`0x30ae0`)** — um `BP_ConZPlayerController_C` sintético criado via `StaticConstructObject_Internal` **sem `Pawn` (`Pawn == NULL`) e sem `APrisoner`**.
    3. Enquanto itens simples (`Cal_9mm_Ammobox`, `Cash`, `MRE_Stew`) toleram ser spawnados por coordenada via `fantasma`, o `UAdminCommand_SpawnItem` do SCUM trava a Game Thread ao instanciar atores da classe `AWeapon` (`Weapon_MP5`) quando o `Executor` é o controller sintético `fantasma` (`Pawn == NULL`).
    4. Por outro lado, ao usar o prefixo nativo **`as <SteamID> spawnitem <Item> <Qty>`** (e **`as <SteamID> spawnvehicle <Vehicle> 1`**), a função `0x45420` define `g_target_controller ([0xa0f68]) = buyer_controller` (o `AConZPlayerController` real do comprador) e a instrução `0x383f8` (`test rax, rax; jne 0x38549`) **pula completamente o `IsUserAdmin` e o `g_fantasma_controller`**, executando o comando diretamente no controller real do próprio jogador (com `sudo` automático via `elevate = 1`) e fazendo o item nascer nativamente à frente dele sem jamais acionar o executor fantasma.
  * Além disso, o parser `parse_listplayers_response()` / `_parse_steam_ids_from_listplayers(..., exclude_lobby=True)` em `utils/rcon_client.py` foi atualizado para o formato `Pos: X=...` / `Pos: Lobby` do `bsbr_scum 0.3.0`, ignorando jogadores que ainda estão na tela de Lobby (`Pawn == NULL`) durante o `run_once()`.
* **Cadência Segura (*Throttling*), Ordenação de Armas e Pausa por Lote (`core/shop/delivery_service.py`)**:
  * **Armas Primeiro (`_kit_subitem_priority`)**: O SSM ordena automaticamente os sub-itens de qualquer kit para spawnar **Armas (`Weapon_*`) primeiro**, seguidas de itens comuns e **Veículos (`BPC_*` / `BP_*`) por último**, preservando o `synth_code` original no banco.
  * **Pausa de Respiro por Lote (`_KIT_BATCH_SIZE = 4` / `2.5s`)**: A cada 4 sub-itens entregues em um kit, o SSM aguarda `2.5s` para a física da Unreal Engine estabilizar os itens no chão antes do próximo lote.
  * Intervalo ajustado para `0.8s` em itens comuns e `2.0s` em atores pesados (`_is_heavy_actor`: armas `Weapon_*` e veículos `BPC_*` / `BP_*`).
  * Helper `_build_spawnitem_cmd()` e `_sanitize_asset_name()` corrigem automaticamente `Water_051` -> `Water_05l`, `Emergency_bandage_Big_S` / `Emergency_bandage_Big_ES` -> `Emergency_bandage_Big`, e montam `as <SteamID> spawnitem <Asset> <Qty> [StackCount <N>]`.
* **Fim do Loop de Crash Pós-Reinício e Eliminação de `ListPlayers` Ocioso (`v3.22.71` / `v3.22.72`)**:
  * Se um pedido causar `RCON_TICK_FROZEN`, `_revert_or_fail_order()` marca o pedido como `failed` (`retry_requested=0`) em vez de `pending`, impedindo que um kit problemático volte a rodar automaticamente 30 segundos após cada reinício do `SCUMServer.exe`.
  * Comandos originados no chat (`/register`, `/kit`, `/buy`) nunca chamam `ListPlayers` (pois o jogador comprovadamente está online), e o `run_once()` ignora pedidos recém-criados (`< 15s` e `attempt_count = 0`) que já estão sendo entregues diretamente por `deliver_single_order_now()`, além de verificar no SQLite se há pedidos pendentes antes de consultar o RCON.
  * `SendChat` (`/sd` e avisos no chat) permanece liberado mesmo com o *Circuit Breaker* aberto, e o socket RCON é reinicializado a cada timeout de tick.

### 3. Arquivos Modificados
* `Backend/utils/rcon_client.py`: Funções `is_rcon_tick_frozen` e `is_rcon_error_response`, além de marcação precisa de `success` nos logs RCON.
* `Backend/core/rcon_queue_manager.py`: *Circuit Breaker* automático para proteção da Game Thread do SCUM Server, reset de socket e isenção de `SendChat`.
* `Backend/core/shop/delivery_service.py`: Lock global unificado, ordenação de armas primeiro em kits, pausa por lote de 4 itens, prevenção de loop de crash pós-reinício, pré-checagem SQLite sem `ListPlayers` ocioso e sanitização de `StackCount`/typos.
* `Backend/core/gps/player_gps_sync_service.py`: Suspensão de sincronização RCON quando o *Circuit Breaker* está aberto.
* `Backend/core/logs/chat_command_monitor.py`: Unificação do disparo do Welcome Pack no `/register` via `deliver_single_order_now`.
* `Backend/docs/SHOP_DELIVERY_RCON_INSTANTANEO.md` & `Backend/docs/SHOP_ECONOMY_SYSTEM.md`: Atualização da documentação técnica e seção Obsidian.

---

## 🛡️ 34. Eliminação Definitiva de Congelamento por Assets Instáveis e Blindagem do Circuit Breaker (`v3.22.74`)

### 1. Diagnóstico dos Logs em Produção (07/11 a 10/11)
* **Amostra Analisada**: 654 comandos de entrega via RCON registrados nos logs `rcon_2026-11-07.log` a `rcon_2026-11-10.log`.
* **Resultado**:
  * **638 comandos de entrega bem-sucedidos (100% de sucesso)** para materiais, ferramentas, veículos, itens diversos e outras armas (`Weapon_Block21`, miras, supressores).
  * **14 falhas causadas exclusivamente por um único asset**: `as <SteamID> spawnitem Weapon_MP5 1`.
  * **Causa Raiz no SCUM Server**: A blueprint base `Weapon_MP5` (ao contrário de `Weapon_MP5_SD`, `Weapon_UMP45`, `Weapon_Block21` ou `Weapon_AKM`) possui uma falha crítica na resolução de colisão de sockets modulares quando instanciada em terreno aberto (fora de zonas com chão plano de concreto como postos de troca). A chamada a `UAdminCommand_SpawnItem::Execute` trava a Game Thread da Unreal Engine 4 em loop de colisão física (`"erro: sem resposta em 4s - o tick do jogo pode estar parado"`), congelando o servidor e impedindo respostas a qualquer comando subsequente do RCON (`ListPlayers`, `SendChat`, `/sd`, `/kit`, etc.).
  * **Efeito Loop Pós-Falha**: Como o pedido falhava por freeze (`status = 'failed'`), o `chat_command_monitor.py` só verificava pedidos em `('pending', 'delivering', 'delivered')`. Toda vez que o jogador digitava `/register` novamente no chat, um novo pedido com a MP5 era gerado, congelando o servidor de novo 2 minutos após o reinício.
  * **Bypass do Circuit Breaker**: O `rcon_queue_manager.py` testava `cmd_lower.startswith(("spawnitem", "spawnvehicle"))`. Como na v3.22.73 os comandos passaram a usar `as <SteamID> spawnitem`, o comando começava com `"as "`, não ativando o bloqueio rápido de spawns durante o congelamento.

### 2. Solução Implementada (`v3.22.74`)
1. **Sanitização Automática de Assets Perigosos (`core/shop/delivery_service.py`)**:
   * Adicionado mapeamento de segurança em `_CLASS_TYPO_FIXES`: `"weapon_mp5": "Weapon_MP5_SD"`.
   * A variante `Weapon_MP5_SD` possui silenciador integrado e malha de colisão fechada e estável, utilizando a mesma munição 9mm (`Cal_9mm_Ammobox`) e os mesmos carregadores (`Magazine_MP5`), impedindo o congelamento da engine mesmo se cadastrada como `Weapon_MP5` no banco de dados.
   * Log explícito de aviso crítico quando um comando RCON de spawn sofre congelamento de tick.
2. **Reconhecimento Universal do Circuit Breaker (`core/rcon_queue_manager.py`)**:
   * O disjuntor agora verifica se o comando contém `" spawnitem "` ou `" spawnvehicle "`, protegendo a fila mesmo quando prefixado por `as <SteamID>`.
3. **Bloqueio de Re-pedidos em Loop no Chat (`core/logs/chat_command_monitor.py`)**:
   * A checagem de kit de registro agora inclui `o.status IN ('pending', 'delivering', 'delivered', 'failed')`. Se a entrega do kit inicial falhou por qualquer motivo para aquele SteamID, novos comandos `/register` no chat não duplicam pedidos nem re-disparam comandos na fila.

### 3. Arquivos Modificados
* `Backend/core/shop/delivery_service.py`: Sanitização automática segura de `Weapon_MP5` para `Weapon_MP5_SD` e log crítico de congelamento.
* `Backend/core/rcon_queue_manager.py`: Detecção abrangente de comandos spawn sob o prefixo `as <SteamID>`.
* `Backend/core/logs/chat_command_monitor.py`: Trava de re-criação de pedido para kits com falha.
* `Backend/docs/SHOP_DELIVERY_RCON_INSTANTANEO.md`: Atualização da documentação técnica da blindagem.

---

## 🚀 35. Atualização do Mod RCON Nativo (`bsbr_scum 0.4.0`) e Suporte no SSM (`v3.22.75`)

### 1. Novidades e Correções do Mod RCON (`bsbr_scum 0.4.0`)
* **Validação Segura de Prisioneiro no Contexto `as <SteamID>`**:
  * Adicionada verificação no motor C++ do mod: caso o jogador do `as` esteja morto ou ainda carregando no mundo (`Pawn == NULL`), o mod agora responde com segurança:
    `"o jogador do 'as' nao tem prisioneiro no mundo agora (morto ou carregando)"`, evitando falhas de ponteiro ou spawning fantasma.
* **Comando `DestroyAllBrennersWithinRadius [Radius [m]]`**:
  * O jogo não possui comando nativo para remoção de Brenners (não são zumbis, animais nem NPCs armados). O mod adicionou o comando `DestroyAllBrennersWithinRadius` (1 a 2000m, padrão 50m) com destruição limpa via `K2_DestroyActor`.
* **Proteção em `SpawnBrenner`**:
  * Passou a exigir obrigatoriamente `as <SteamID>` para não nascer indevidamente na frente do primeiro jogador vivo aleatório.
* **Formato Estruturado de `version`**:
  * Saída padronizada:
    ```
    bsbr_scum 0.4.0
    portas source=28015 linha=27100
    opcoes elevate=1 split_replies=0 echo=0 perf_log=0
    ```

### 2. Integração no SSM Backend
* **Atualização do Pacote Staged (`data/mods/bsbr_scum/`)**:
  * Binário `main.dll` atualizado para `0.4.0` (675.840 bytes), documentação e `version.txt`.
  * Detectado e pronto para instalação com 1 clique pelo `RconModManager` no SSM.
* **Compatibilidade em `utils/rcon_client.py`**:
  * Adicionados marcadores `"nao tem prisioneiro"` e `"morto ou carregando"` a `is_rcon_error_response()`, garantindo que pedidos de entrega sejam mantidos em `pending` caso o jogador esteja morto ou na tela de carregamento.
  * Parser `query_live_mod_version()` atualizado com regex compatível com as versões `0.3.0` e `0.4.0+`.

### 3. Arquivos Modificados
* `Backend/data/mods/bsbr_scum/`: Atualização completa dos componentes e binários do mod para 0.4.0.
* `Backend/utils/rcon_client.py`: Detecção de respostas 0.4.0 e marcadores de estado de prisioneiro.
* `Backend/version.py`: Incremento para `v3.22.75`.

---

## 🔄 36. Atualização Automática do Mod RCON no Restart do Servidor (`v3.22.76`)

### 1. Desafio Operacional
* Ao distribuir uma nova versão do SSM contendo atualizações do mod RCON nativo (`bsbr_scum`), as DLLs (`main.dll`, `dwmapi.dll`, `UE4SS.dll`) não podem ser substituídas enquanto o executável `SCUMServer.exe` estiver rodando, pois o Windows bloqueia a sobrescrita de arquivos carregados na memória.
* Exigir que o administrador acesse o servidor, pare manualmente o jogo, vá na aba de Mods e clique em atualizar tornaria as atualizações manuais e propensas a esquecimento.

### 2. Solução Implementada (`v3.22.76`)
* **Auto-Atualização Integrada no Ciclo de Vida do Servidor (`core/server_control/server_manager.py`)**:
  * Adicionado o método `_auto_update_rcon_mod_if_needed()`, acionado em dois pontos estratégicos:
    1. **Dentro de `restart_server()`**: Durante a janela offline (logo após a parada confirmada do serviço e do processo `SCUMServer.exe` e antes do arranque do jogo).
    2. **Dentro de `start_server()`**: Antes de subir o serviço, caso o servidor estivesse previamente parado.
  * O método invoca o `RconModManager.check_update_status(bin_dir)`. Se a versão instalada no servidor for inferior à versão empacotada em `data/mods/bsbr_scum/` (ex: `0.3.0` -> `0.4.0`):
    * Faz backup automático da versão antiga em `data/mods/_backup/`.
    * Preserva intacto o arquivo `config.ini` (senhas RCON, portas e configurações de rede não são alteradas).
    * Atualiza `dwmapi.dll`, `UE4SS.dll` e a nova `main.dll`.
    * Garante `enabled.txt` e `mods.txt`.
    * Registra todo o processo com clareza nos logs estruturados (`[RCON_MOD_AUTO_UPDATE]`).
  * O processo é 100% automático, silencioso (leva ~100ms na cópia e ~2ms se já estiver atualizado) e não adiciona nenhum tempo perceptível ao restart.

### 3. Arquivos Modificados
* `Backend/core/server_control/server_manager.py`: Inclusão de `_auto_update_rcon_mod_if_needed` em `restart_server` e `start_server`.
* `Backend/version.py`: Incremento para `v3.22.76`.
