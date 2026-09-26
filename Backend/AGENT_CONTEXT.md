# AGENT_CONTEXT.md

Este documento serve como a fonte da verdade para o estado atual da arquitetura, restrições e regras do **SSM 3.0 Backend**. Qualquer agente de IA deve ler este arquivo no início de cada sessão para garantir a consistência das implementações.

---

## 🗺️ 1. Visão Geral do Projeto
O **SSM 3.0 Backend** é o núcleo de controle do servidor SCUM. Ele gerencia a comunicação RCON com o servidor do jogo, integra ações via Bot do Discord, processa logs de eventos do jogo em tempo real (como mortes e chat) e fornece uma interface de gerenciamento (GUI Desktop + rotas de API).

### Stack Tecnológica
* **Linguagem:** Python 3.x
* **Banco de Dados:** SQLite (`SSM.db`)
* **Comunicação Discord:** `discord.py` (Bot assíncrono)
* **Interface Gráfica:** GUI nativa em Python (`gui/main_window.py`)
* **Processamento de Logs:** Monitores de arquivos locais de logs do SCUM (Chat, Kills, etc.)

---

## 🏗️ 2. Arquitetura & Componentes Críticos

### ⚡ Comunicação RCON (`RconQueueManager`)
* **Como funciona:** Todo comando enviado ao servidor de jogo deve passar pela fila de RCON (`RconQueueManager`) para evitar sobrecarga no socket.
* **Regra de Prioridade:** Comandos vitais (teleporte manual, compras de loja) têm prioridade alta. Mensagens de chat ou zoeiras (como o Kill Feed) rodam com prioridade menor (ex: `priority = 15`).
* **Delays:** Um atraso mínimo (ex: `delay_after = 0.05` - 50ms) é necessário entre comandos sequenciais para mitigar perdas de pacotes.
* **Segurança (RCON Injection):** Sempre sanitizar nomes de jogadores em comandos RCON. Substituir quebras de linha (`\n`, `\r`) por espaços e aspas duplas (`"`) por aspas simples (`'`) para evitar injeção de comandos arbitrários.

### 🗄️ Concorrência do Banco de Dados (SQLite)
* **Desafio:** Como o SQLite não lida nativamente com dezenas de escritas paralelas de threads diferentes, há risco de erros do tipo `"database is locked"`.
* **Regra de Ouro:** Operações de escrita demoradas ou em lote devem ser enfileiradas ou protegidas por travas de thread (`threading.Lock` ou filas de escrita dedicadas).

### 💰 Economia & Carteiras (Wallet System)
* **Saldo Inicial Dinâmico:** Carteiras recém-criadas ou redefinidas em operações de reset de cadastro (manutenção CLI e GUI) devem herdar o saldo inicial definido em `config.json` na seção `economy.initial_balance` (padrão: `0`). Nunca utilize valores hardcoded (como o antigo padrão `5000`) nestas rotinas.

### 🌀 Integração Discord e Timeouts
* **Limitação da API:** O Discord exige resposta em interações de botões em até **3 segundos**.
* **Padrão de Teleporte Seguro:** Em vez de executar o teleporte do RCON de forma síncrona no clique do botão (o que causa timeout), o bot valida o jogador rapidamente, gera um código de 4 dígitos (salvo em `data/event_teleport_codes.json`) e o exibe de forma efêmera para que o jogador digite `/evento <codigo>` dentro do jogo.
* **Loop de Eventos (Asyncio):** Views dinâmicas do Discord devem ser instanciadas e registradas na thread principal do loop do Bot usando `loop.call_soon_threadsafe`.

### 📂 Estrutura de Arquivos de Dados e Integração
* `data/config.json`: Configurações globais do sistema.
* `data/event_teleport_codes.json`: Códigos temporários de teleporte ativo.
* `data/kill_feed_phrases.json`: Frases de zoeira para o sistema de Kill Feed PvP.
* `data/rcon_routines.json`: Armazenamento persistente de rotinas RCON periódicas.
* `docs/kill_feed_frontend_doc.md`: Especificação técnica de integração do front-end para o Kill Feed.
* `docs/rcon_routine_scheduler_plan.md`: Plano de arquitetura do agendador de rotinas RCON.
* `docs/rcon_routines_frontend_doc.md`: Especificação técnica de integração do front-end para o Agendador de Rotinas RCON (Scheduler).
* `data/logs/`: Diretório de logs específicos de serviços (ex: `discord_events.log` para debug de eventos).

### 🕐 Agendador de Rotinas RCON (`RconRoutineScheduler` / `RconRoutineManager`)
* **Como funciona:** Executa sequências periódicas de comandos RCON (como `#DestroyAllItemsWithinRadius` ou `#say` periódicos) salvos de forma segura em `data/rcon_routines.json`.
* **Segurança:** O agendador roda em uma thread paralela verificando o tempo a cada 60 segundos. Ele verifica se o Restart Guard (`is_restart_active()`) está ativo para evitar disparar rotinas durante ciclos de reinicialização do servidor.
* **Respiro do Servidor:** Todos os comandos de uma rotina são enfileirados com prioridade baixa (20) e um delay pós-execução (`delay_after = 2.0`) entre comandos individuais para mitigar lag e sobrecarga de buffer.
* **Aviso Prévio (Pre-announcement):** Suporta o envio automatizado de uma mensagem customizada e colorida no chat (usando rich text tags do SCUM chat) antes da rotina principal iniciar (ex: 5 minutos antes), controlada pelas variáveis `warning_enabled`, `warning_message`, `warning_color` e `warning_minutes_before`.
* **Garantia de Antecedência do Aviso:** Em rotinas novas (`last_run = None`) ou atrasadas/overdue (após restarts ou inatividade), o agendador automaticamente envia o aviso prévio imediatamente e atualiza o `last_run` de forma retroativa para adiar a execução principal em exatos `warning_minutes_before` minutos. Isso evita o disparo simultâneo de avisos e comandos de manutenção no mesmo segundo.
* **Feedback de Teste em Tempo Real:** O endpoint de teste `/api/rcon-routines/<routine_id>/test` executa os comandos com maior prioridade (5) e delay otimizado (0.5s), aguardando de forma síncrona pelo retorno do console RCON do jogo para exibir o resultado imediato (sucesso/erro/resposta) na resposta HTTP (limite de timeout interno de 25 segundos para a resposta). Se a rotina tiver o aviso prévio ativado, o comando de aviso (`#say` correspondente) também é injetado e testado no topo da execução.
* **Sanitização Inteligente de Coordenadas:** O agendador de rotinas e o endpoint de teste executam automaticamente a função `sanitize_rcon_command_coords` em todos os comandos antes do enfileiramento. Telemetria do SCUM no formato `{X=... Y=... Z=...|...}` é convertida para coordenadas separadas por espaços simples. Para o comando `#ScheduleWorldEvent`, a altitude Z é forçada a ser `0` (exigência do SCUM para drops que caem do céu), enquanto em comandos como `#teleport`, a altitude Z original é mantida.


### ⏱️ Recompensas por Tempo de Jogo (Playtime Rewards System)
* **Tolerância de Desconexão (Grace Period):** Para evitar a perda de progresso por desconexões temporárias ou crash do jogo, o sistema implementa uma tolerância configurável (`playtime_rewards.grace_period_minutes`, padrão de 5 minutos). Quando o jogador desloga, a sessão é congelada e o timestamp do logoff é registrado em `data/playtime_sessions.json` sob `offline_since`. Se ele retornar dentro da tolerância, a sessão e o progresso parcial de minutos são retomados. Caso exceda o tempo, a sessão é fechada em definitivo e o progresso parcial descartado.
* **Fuso Horário UTC Estrito:** Todos os timestamps de log, banco de dados e sessões são tratados estritamente em UTC (`datetime.utcnow()`), garantindo que não ocorram drifts ou bugs de fuso horário causados pelo relógio do servidor de hospedagem.
* **Logs de Auditoria em Inglês no Discord:** Notificações de login, logout temporário, logout permanente, reconexão e premiação são disparadas em texto puro (sem Embeds) e obrigatoriamente na língua inglesa para o canal dedicado `⏱️┃playtime-rewards` (gerido no `WebhooksManager`). O `RewardsService` carrega as URLs desses webhooks dinamicamente do arquivo `webhooks.json` via `WebhooksManager` no seu construtor para manter a funcionalidade de auditoria ativa em threads em segundo plano. As mensagens seguem um modelo formatado com crases em torno de campos-chave (ex: `Player Jessynha (SteamID: 76561198962669673 | Discord: @Jessynha) completed 1 hour(s) online and earned +6 points (Rule: VIP). New balance: 6 points.`).
* **Segurança e Concorrência de Carteira:** Para evitar deadlocks com transações concorrentes do SQLite, a consulta de saldos da carteira (`wallet`) durante o ciclo de ticks é efetuada diretamente na conexão ativa da transação (`ssm_tx`). Apenas jogadores ativamente registrados e com ID do Discord associado geram logs de auditoria no canal do Discord.
* **Canal de Jogadores Online Customizável (Delimitador `|` / `┃`):** O canal de contagem de jogadores online (`players_online`, padrão `"👥┃players-online"`) aceita emojis, símbolos e caracteres Unicode especiais. As atualizações automáticas de contagem feitas pelo `OnlinePlayersMonitor` preservam qualquer alteração visual ou de texto feita pelo administrador. Para evitar duplicações causadas pela remoção de delimitadores ASCII pelo Discord (como `|`), o monitor limpa números acumulados no final com regex (`re.sub(r"[|┃ \-~•·_]*\d+$", "", base)`) e seleciona de forma inteligente o delimitador correspondente (preservando o caractere de caixa `┃` se presente, ou aplicando o hífen `-` padrão).

### ⏳ Sistema Global de Expiração de Atributos (Attribute Expiration System)
* **Como funciona:** Permite que upgrades de atributos comprados na loja expirem após um período configurável (em dias). Gated pelo agendador periódico `AttributeExpirationScheduler`.
* **Configuração:** Armazenada no banco `app_config` do `SSM.db` sob as chaves `attributes.expiration.enabled` (boolean) e `attributes.expiration.duration_days` (inteiro >= 1).
* **Endpoints API:** `/api/attributes/prices` (`GET` para ler preços e configurações de expiração, e `PUT` para atualizar preços e expiração de forma atômica).
* **Preservação de Preços no Startup:** A rotina de inicialização `_init_attribute_upgrade_prices` em `utils/database_initializer.py` verifica previamente se a tabela `attribute_upgrade_prices` no `SSM.db` contém registros. Se existirem dados cadastrados pelo usuário, a sobrescrita destrutiva a partir de `config.json` é ignorada, mantendo os preços customizados intactos durante atualizações de versão e reinicializações.
* **Logs e Discord:** Notifica administradores via `@discord_user_id` tags no canal `#shop-log` quando os atributos expiram e sofrem rollback (regressão de nível para o valor base/original do jogador).
* **Fluxo de Regressão:** Quando o agendador roda, ele verifica quais atributos expiraram e executa a regressão direta no banco `SCUM.db` (aplica a regressão e gera o comando RCON necessário ou agenda a regressão imediata caso o jogador esteja online).

### 📡 Agendador de Webhooks de Raid Pessoais (Personal Webhook Scheduler)
* **Como funciona:** Gerencia a expiração, avisos prévios e renovação automática de webhooks pessoais de raid (comando `/rd` in-game) de jogadores. Roda em segundo plano a cada 1 hora.
* **Cobrança e Renovação**: Caso o jogador possua saldo na carteira (`WalletService`) maior ou igual ao configurado (`personal_webhooks.price_points`), o webhook é renovado por mais `duration_days` dias e o valor é debitado. Se o saldo for insuficiente, o webhook é desativado (limpando o campo `webhook_url` na tabela `player_webhooks`) e o jogador é notificado.
* **Alertas Prévios de Expiração**: Envia avisos automáticos via webhook do jogador e por DM no Discord (caso a conta esteja vinculada) restando 3 dias e 1 dia para a expiração, usando mensagens personalizáveis.

### 🌐 Configuração de CORS, Portas e Detecção de Status do Backend
* **Regra de CORS:** O backend Flask permite conexões Cross-Origin originadas das portas `8000` (legado/desktop) e `5173` (porta padrão de desenvolvimento/produção do frontend web) via cabeçalhos específicos `Authorization` e `X-Server-Hash` com suporte a credenciais.
* **Detecção Resiliente de Sockets (`LISTEN` vs `TIME_WAIT`):** A verificação de portas ocupadas para determinar se o backend já está rodando (`_find_backend_processes` e `_is_backend_running`) lê a porta de API dinamicamente de `config.json` (padrão `3000`) e filtra conexões do sistema operacional para considerar apenas aquelas que estejam ativamente escutando no estado **`LISTEN`** (usando `psutil.CONN_LISTEN`). Conexões obsoletas/residuais em `TIME_WAIT` (comuns ao fechar serviços como Docker) são ignoradas. O monitor também ignora o PID do próprio processo da GUI para evitar loops de autoverificação.
### 🔒 Módulo Squad TK Jail (Prisão por Team Kill)
* **Sincronização Ativa em Memória:** As rotas HTTP de alteração de configuração (`app/routes/config_routes.py`) sincronizam o dicionário global `services.config` em tempo real sempre que gravam no disco (`config.json`).
* **Leituras Dinâmicas (Live Reads):** O `SquadTKJailService` não armazena em cache o estado ativado ou outros parâmetros. Ele lê as configurações diretamente do dicionário atualizado em tempo real no início de todas as lógicas e em cada ciclo do loop `_monitor_loop`.
* **Segurança e Fallback de Soltura (Release Fallback):** Ao prender um jogador, as coordenadas originais são armazenadas nas colunas `release_coords_x`, `release_coords_y`, `release_coords_z` da tabela `prison_records`. Ao soltar o jogador, caso a bandeira do squad não esteja disponível no mapa, essas coordenadas salvas são usadas como fallback para teleportá-lo de volta exatamente ao local de captura (em vez de `0, 0, 0`).

### 🎯 Módulo Wanted Killstreak (Sistema de Procurado)
* **Funcionamento Central (`BountyService`)**: Monitora PvP kills para rastrear streaks de jogadores. Ao atingir o gatilho (`killstreak_trigger`), o jogador é marcado como procurado (`is_wanted = 1`) e recebe uma recompensa base (`base_bounty`). Kills subsequentes do procurado incrementam o bounty.
* **Anti-Exploit de Squad**:
  * **Verificação de Esquadrão**: Bloqueia reivindicações de recompensa se o assassino for do mesmo squad da vítima.
  * **Cooldown de Deserção**: Aplica uma restrição de 24 horas (`squad_leave_cooldown_hours`) para jogadores que abandonaram o squad do procurado recentemente, impedindo que abandonem o clã apenas para pegar o prêmio.
* **Integração do Discord e Edição de Mensagens**:
  * Envia atualizações em tempo real para o Discord. Em vez de criar novos posts como spam, o bot realiza requisições `PATCH` (edita) nas mensagens existentes dos embeds de rankings (`top_killers_message_id` e `shame_rank_message_id`).
  * Se o webhook do procurado estiver vazio, o backend faz fallback automático para o webhook global de ranking de kills (`top20_kills`).
* **Transações SQLite**: Todas as consultas e operações auxiliares de wallet dentro do processamento de PvP kill compartilham a conexão ativa (`conn`) da transação corrente, eliminando timeouts e deadlocks.

### 🔑 Autenticação e Configuração de Administrador
* **Usuário Padrão (`admin`)**: Armazenado na tabela `frontend_users`. O usuário inicial é provisionado com base na configuração `auth` do `config.json`.
* **Sincronização de Senhas**: As credenciais no banco devem refletir de forma idêntica o campo `default_password` de `config.json` (por padrão, `"12345678910"`). Caso ocorram divergências ou erros de login administrativo, o hash do banco deve ser recalculado e sincronizado utilizando o `PasswordHandler` do backend.

---

## 🚦 3. Diretrizes de Desenvolvimento para IA

1. **Leitura Prévia Obrigatória:** Sempre use a ferramenta de visualização de arquivos para ler o código completo antes de fazer qualquer alteração. Não faça suposições sobre imports, variáveis globais ou estrutura de métodos.
2. **Escopo do Projeto:** Modificações devem ocorrer estritamente na pasta `Backend`. Ignorar completamente pastas como `dist`, `.venv`, `venv`, `.cursor`, `node_modules` e pastas de cache python (`__pycache__`).
3. **Tratamento de Erros:** Adicionar logs detalhados (usando tags claras como `[TELEPORT_DEBUG]`, `[KILL_FEED_DEBUG]`) em blocos `try/except` de rotinas de integração para facilitar a depuração no servidor de produção.
