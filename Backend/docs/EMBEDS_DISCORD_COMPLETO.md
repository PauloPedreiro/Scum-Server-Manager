# 📋 Lista Completa de Embeds Discord - SSM Backend

Este documento lista **todos os embeds** que são enviados para o Discord através do sistema de webhooks do SSM Backend.

---

## 📊 Índice por Webhook

Baseado em `data/webhooks.json`, os seguintes webhooks estão configurados:

1. **serverstatus** - Status do servidor e agendamentos
2. **new_player** - Novos jogadores
3. **players_online** - Lista de jogadores online
4. **vehicle_registration** - Registro de veículos
5. **chat_in_game** - Chat do jogo
6. **adminlog** - Logs administrativos
7. **vehicle-log** - Logs de veículos
8. **bunkers_status** - Status dos bunkers
9. **timer** - Notificações de timer
10. **commands** - Comandos de chat
11. **fishing_ranking** - Ranking de pescadores
12. **kill_log** - Logs de kills
13. **chest_events** - Eventos de baús
14. **chest_vehicle_alerts** - Alertas de baús em veículos
15. **log-ssm** - Logs do SSM
16. **lockpicking_events** - Eventos de lockpicking
17. **top20_lockpicking** - Top 20 lockpicking
18. **top20_kills** - Top 20 kills
19. **top20_snipers** - Top 20 snipers
20. **bank_transaction** - Transações bancárias
21. **cargo_drop** - Spawn de Cargo Drop (SCUM.log)

---

## 🎯 1. Status do Servidor (`serverstatus`)

### 1.1. Eventos de Servidor (`send_server_status`)

**Método:** `DiscordWebhook.send_server_status(event, data)`

#### 📌 `server_starting`
- **Título:** `🚀 Server Starting`
- **Cor:** `0xffaa00` (Laranja)
- **Descrição:** (vazia - título já informa)
- **Campos:** (nenhum)
- **Compacto:** Sim

#### 📌 `server_started`
- **Título:** `✅ Server Started`
- **Cor:** `0x00ff00` (Verde)
- **Descrição:** (vazia)
- **Campos:** (nenhum)
- **Compacto:** Sim

#### 📌 `server_stopping`
- **Título:** `🛑 Server Stopping`
- **Cor:** `0xffaa00` (Laranja)
- **Descrição:** (vazia)
- **Campos:** (nenhum)
- **Compacto:** Sim

#### 📌 `server_stopped`
- **Título:** `⏹️ Server Stopped`
- **Cor:** `0x0099ff` (Azul)
- **Descrição:** (vazia)
- **Campos:** (nenhum)
- **Compacto:** Sim

#### 📌 `server_restarting`
- **Título:** `🔄 Server Restarting`
- **Cor:** `0xffaa00` (Laranja)
- **Descrição:** (vazia)
- **Campos:** (nenhum)
- **Compacto:** Sim

#### 📌 `server_restarted`
- **Título:** `✅ Server Restarted`
- **Cor:** `0x00ff00` (Verde)
- **Descrição:** (vazia)
- **Campos:** (nenhum)
- **Compacto:** Sim

#### 📌 `server_restart_failed`
- **Título:** `❌ Restart Failed`
- **Cor:** `0xff0000` (Vermelho)
- **Descrição:** `Failed to restart SCUM server.`
- **Campos:** Status, PID, Uptime, Port, Max Players
- **Compacto:** Não

### 1.2. Notificações do Scheduler (`send_scheduler_notification`)

**Método:** `DiscordWebhook.send_scheduler_notification(event, data)`

#### 📌 `restart_scheduled`
- **Título:** `📅 Restart Scheduled` (dinâmico baseado em minutos)
- **Cor:** `0x0099ff` (Azul)
- **Descrição:** (vazia)
- **Campos:** 
  - Next Restart
  - Scheduled Times
  - Notifications (Before: Xmin)

#### 📌 `restart_warning`
- **Título:** `📅 Restart in X minute(s)` (dinâmico)
- **Cor:** `0xff6600` (Laranja forte)
- **Descrição:** (vazia)
- **Campos:** 
  - Next Restart
  - Scheduled Times
  - Notifications

#### 📌 `restart_started`
- **Título:** `🔄 Restart Started`
- **Cor:** `0xffaa00` (Laranja)
- **Descrição:** `The scheduled SCUM server restart has been initiated.`
- **Campos:** Next Restart, Scheduled Times, Notifications

#### 📌 `restart_completed`
- **Título:** `✅ Restart Completed`
- **Cor:** `0x00ff00` (Verde)
- **Descrição:** `The scheduled SCUM server restart has been completed successfully!`
- **Campos:** Next Restart, Scheduled Times, Notifications

#### 📌 `restart_failed`
- **Título:** `❌ Restart Failed`
- **Cor:** `0xff0000` (Vermelho)
- **Descrição:** `The scheduled SCUM server restart has failed.`
- **Campos:** Next Restart, Scheduled Times, Notifications

---

## 👤 2. Novos Jogadores (`new_player`)

**Método:** `PlayerProcessor._send_new_player_notification()`

### 📌 Novo Jogador Conectado
- **Título:** `🎉 New Player on Server!`
- **Cor:** `0xFF6B35` (Laranja)
- **Campos:**
  - **In-Game Name:** Nome do jogador (inline)
  - **Steam Name:** Nome na Steam (inline)
  - **Steam ID:** ID do Steam (inline)
  - **🔗 Steam Profile:** Link clicável (se disponível)
- **Thumbnail:** Avatar do Steam (se disponível)
- **Footer:** `SCUM Server Manager`

---

## 🟢 3. Jogadores Online (`players_online`)

**Método:** `OnlinePlayersMonitor._send_discord_notification()`

### 📌 Lista de Jogadores Online
- **Título:** `⚔️ SCUM Server (X online)`
- **Cor:** `0x00FF00` (Verde) se online > 0, `0xFF0000` (Vermelho) se 0
- **Campos:**
  - **Online Players:** Lista com nome e tempo online (ex: `• PlayerName (2h 30min)`)
- **Footer:** `SCUM Server Manager`

---

## ⚔️ 4. Kills (`kill_log`)

**Método:** `KillProcessor._build_embed()`

### 📌 PvP Kill
- **Título:** `⚔️ PvP Kill`
- **Cor:** `0xe74c3c` (Vermelho)
- **Descrição:**
  - Vítima: [Nome]
  - Killer: [Nome]
  - Arma: [Arma normalizada]
  - Distância: [X.XX] m (se disponível)
- **Thumbnail:** Imagem da arma (se disponível)
- **Footer:** `SCUM Server Manager`
- **Timestamp:** Timestamp do evento

### 📌 NPC Kill
- **Título:** `🤖 Morto por NPC - [Nome da Vítima]`
- **Cor:** `0xe67e22` (Laranja)
- **Descrição:**
  - Killer: NPC Pro Player
  - Arma: [Arma normalizada]
  - Distância: [X.XX] m (se disponível)
- **Thumbnail:** Imagem da arma (se disponível)
- **Footer:** `SCUM Server Manager`
- **Timestamp:** Timestamp do evento

### 📌 Suicídio
- **Título:** `💀 Suicídio - [Nome]`
- **Cor:** `0x95a5a6` (Cinza)
- **Descrição:** `Vítima: [Nome]`
- **Thumbnail:** Imagem `Suicide.png` (se disponível)
- **Footer:** `SCUM Server Manager`
- **Timestamp:** Timestamp do evento

---

## 🚗 5. Veículos (`vehicle_registration` / `vehicle-log`)

### 5.1. Registro de Veículos (`vehicle_registration`)

**Método:** `VehicleNotifier.send_notification()`

#### 📌 Eventos de Veículo
- **Título:** Dinâmico baseado no evento:
  - `🚗 Vehicle Registered`
  - `🔄 Ownership Transferred`
  - `🚗 Vehicle Event` (outros eventos)
- **Cor:** Dinâmica baseada no evento
- **Campos:**
  - **Vehicle:** Nome do veículo
  - **Player:** Nome do jogador (sem ID)
  - **Location:** Link para SCUM Maps
  - **Transfer:** (apenas se ownership_type == 'changed') From: [Nome] To: [Nome]
- **Thumbnail:** Imagem do veículo (se disponível)
- **Footer:** `Container ID: X • Vehicle ID: Y • Steam ID: Z` (sem data/hora)

### 5.2. Destruição de Veículos (`vehicle-log`)

**Método:** `VehicleDestructionProcessor._build_embed()`

#### 📌 Eventos de Destruição
- **Título:** `[Emoji] [Categoria]` (sem nome do veículo)
- **Cor:** Baseada na categoria
- **Campos:**
  - **Vehicle:** Nome do veículo (sem ID)
  - **Owner:** Nome
  - **Location:** Link para SCUM Maps
- **Thumbnail:** Imagem do veículo (se disponível)
- **Footer:** `Vehicle ID: X • Steam ID: Y` (se disponível)

**Categorias:**
- Vehicle Inactive: 🟡 (Amarelo)
- Vehicle Disappeared: 🔴 (Vermelho)
- Vehicle Destroyed: ⚫ (Preto)

---

## 💬 6. Chat (`chat_in_game`)

**Método:** `ChatProcessor` (via `log_processor`)

### 📌 Mensagens de Chat
- **Título:** `💬 Chat Message`
- **Cor:** `0x0099ff` (Azul)
- **Descrição:** Mensagem do chat
- **Campos:**
  - **Jogador:** Nome
  - **Steam ID:** ID
  - **Mensagem:** Texto da mensagem
- **Footer:** `SCUM Server Manager`
- **Timestamp:** Timestamp da mensagem

---

## 🔐 7. Comandos (`commands`)

**Método:** `ChatCommandMonitor._send_discord_notification()`

### 📌 Comando Detectado
- **Título:** `✅ Command /[comando] Detected` ou `❌ Command /[comando] Detected`
- **Cor:** `0x00ff00` (Verde) se autorizado, `0xff0000` (Vermelho) se negado
- **Descrição:**
  - **Player:** [Nome]
  - **Steam ID:** [ID]
  - **Status:** [Command authorized and executed / Command denied - no permission]
- **Campos:**
  - **🔐 Permission:** Authorized ou Denied
- **Footer:** `SSM Backend - Chat Commands Monitor`

---

## 📦 8. Baús (`chest_events` / `chest_vehicle_alerts`)

**Método:** `ChestSyncService._build_embed()`

### 8.1. Eventos de Baús (`chest_events`)

#### 📌 Baú Criado
- **Título:** `📦 Chest Created`
- **Cor:** `0x00FF7F` (Verde claro)
- **Campos:** ID, Chest Type, Location, Chest Owner, Map
- **Thumbnail:** Imagem do baú (se disponível)
- **Footer:** `SCUM Backend • Chest Monitoring`
- **Timestamp:** Timestamp UTC

#### 📌 Baú Removido
- **Título:** `💥 Chest Removed`
- **Cor:** `0xFF5555` (Vermelho claro)
- **Campos:** ID, Chest Type, Location, Chest Owner, Map
- **Footer:** `SCUM Backend • Chest Monitoring`

#### 📌 Baú Transferido
- **Título:** `🔄 Chest Transferred`
- **Cor:** `0xFFAA00` (Laranja)
- **Campos:** ID, Chest Type, Location, Chest Owner, Map
- **Footer:** `SCUM Backend • Chest Monitoring`

#### 📌 Baú Movido
- **Título:** `🚚 Chest Moved`
- **Cor:** `0x3399FF` (Azul)
- **Campos:** ID, Chest Type, Location, Chest Owner, Map
- **Footer:** `SCUM Backend • Chest Monitoring`

#### 📌 Baú Renomeado
- **Título:** `✏️ Chest Renamed`
- **Cor:** `0x9966FF` (Roxo)
- **Campos:** ID, Chest Type, Location, Chest Owner, Previous Name, Map
- **Footer:** `SCUM Backend • Chest Monitoring`

#### 📌 Baú Colocado em Veículo
- **Título:** `🚗 Chest Placed in Vehicle`
- **Cor:** `0x2ECC71` (Verde)
- **Campos:** ID, Chest Type, Location, Chest Owner, Map
- **Footer:** `SCUM Backend • Chest Monitoring`

#### 📌 Baú Removido do Veículo
- **Título:** `🛑 Chest Removed from Vehicle`
- **Cor:** `0xE74C3C` (Vermelho)
- **Campos:** ID, Chest Type, Location, Chest Owner, Map
- **Footer:** `SCUM Backend • Chest Monitoring`

#### 📌 Baú Movido Entre Veículos
- **Título:** `🔁 Chest Moved Between Vehicles`
- **Cor:** `0xF1C40F` (Amarelo)
- **Campos:** ID, Type, Location, Owner, Vehicle (com ID e proprietário), Map
- **Footer:** `SCUM Backend • Chest Monitoring`

#### 📌 Alerta de Baú em Veículo
- **Título:** `⚠️ CHEST ALERT ⚠️`
- **Cor:** `0xE67E22` (Laranja escuro)
- **Descrição:** `Chest owned by ([chest_owner]) is inside vehicle owned by ([vehicle_owner]).\n\nCHEST ID: [id]\nVEHICLE ID: [id]`
- **Campos:** (nenhum)
- **Footer:** `SCUM Backend • Chest Monitoring`

### 8.2. Alertas de Baús em Veículos (`chest_vehicle_alerts`)

**Método:** `ChestSyncService._build_embed()` (mesmo método de `chest_events`)

Os eventos de `chest_vehicle_alerts` são os mesmos de `chest_events`, mas enviados para um webhook específico quando o evento é `vehicle_owner_mismatch`.

#### 📌 Alerta de Baú em Veículo
- **Título:** `⚠️ CHEST ALERT ⚠️`
- **Cor:** `0xE67E22` (Laranja escuro)
- **Descrição:** `Chest owned by ([chest_owner]) is inside vehicle owned by ([vehicle_owner]).\n\nCHEST ID: [id]\nVEHICLE ID: [id]`
- **Campos:** (nenhum)
- **Thumbnail:** Imagem do baú (se disponível)
- **Footer:** `SCUM Backend • Chest Monitoring`
- **Timestamp:** Timestamp UTC

---

## 🏗️ 9. Bunkers (`bunkers_status`)

**Método:** `DiscordWebhook.send_bunker_status()` ou `LogProcessor._send_bunker_status_to_discord()`

### 📌 Status dos Bunkers
- **Título:** `🏗️ BUNKER STATUS` ou `🏗️ BUNKER STATUS - SCUM`
- **Cor:** `0x0099ff` (Azul)
- **Descrição:** Lista de bunkers com status:
  - `🔓 [Nome] - ACTIVE - há X tempo`
  - `🔒 [Nome] - LOCKED - Next Activation: X`
- **Campos:** (apenas no formato do LogProcessor)
  - Campos individuais por bunker (inline)
  - **📊 Estatísticas:** Total, Ativos, Bloqueados
- **Footer:** `🔧 SCUM Server Manager` ou `SCUM Backend - Management System`
- **Timestamp:** Timestamp atual

---

## 🎮 10. Minigames / Raids (`lockpicking_events`)

**Método:** `MinigameNotifier._build_embed()`

### 📌 Evento de Raid (Lockpicking)
- **Título:** `🔓 [Objeto] Raidado` ou `🔒 [Objeto] Falhou`
- **Cor:** `0x00ff00` (Verde) se sucesso, `0xff0000` (Vermelho) se falhou
- **Descrição:**
  - **Jogador:** [Nome]
  - **Steam ID:** [ID]
  - **Objeto:** [Nome do objeto]
  - **Tentativas:** X/Y
- **Thumbnail:** Imagem do objeto (se disponível)
- **Footer:** `SCUM Server Manager`
- **Timestamp:** Timestamp do evento

---

## 📊 11. Rankings

### 11.1. Top 20 Lockpicking (`top20_lockpicking`)

**Método:** `LockpickingRankingService.format_ranking_embed()`

#### 📌 Ranking por Tipo de Lock
- **Author:** `[Nome do Lock] - Top 20` (com ícone)
- **Cor:** Baseada no tipo de lock
- **Descrição:** Tabela formatada:
  ```
  Rank | Player           | Success | Fails | Rate
  -----|------------------|---------|-------|--------
  1    | PlayerName       |    150  |   10  | 93.75%
  ```
- **Footer:** `Mínimo X tentativas | Atualizado`
- **Timestamp:** Timestamp UTC

**Tipos de Lock:**
- Padlock (Azul)
- Electronic Lock (Verde)
- Safe (Amarelo)
- etc.

### 11.2. Top 20 Kills (`top20_kills`)

**Método:** `KillsRankingService.format_top_killers_embed()`

#### 📌 Top Killers
- **Título:** `⚔️ TOP KILLERS ⚔️`
- **Cor:** `0xe74c3c` (Vermelho)
- **Descrição:** Tabela formatada:
  ```
  Rank | Player           | Kills
  -----|------------------|-------
  1    | PlayerName       |   150
  ```
- **Footer:** `Top 20 | Atualizado`
- **Timestamp:** Timestamp UTC

#### 📌 Shame Rank (Deaths by NPC)
- **Título:** `💀 SHAME RANK | Deaths by NPC 💀`
- **Cor:** `0x95a5a6` (Cinza)
- **Descrição:** Tabela formatada:
  ```
  Rank  | Player           |💀
  ------|------------------|---
  1     | PlayerName       | 25
  ```
- **Footer:** `Top 20 | Atualizado`
- **Timestamp:** Timestamp UTC

### 11.3. Top 20 Snipers (`top20_snipers`)

**Método:** `SnipersRankingService.format_top_snipers_embed()`

#### 📌 Top Snipers
- **Título:** `🎯 TOP SNIPERS 🎯`
- **Cor:** `0x2ecc71` (Verde)
- **Descrição:** Tabela formatada:
  ```
  Rank | Player           | Kills | Distance
  -----|------------------|-------|----------
  1    | PlayerName       |   50  | 250.5m
  ```
- **Image:** GIF de sniper (anexado)
- **Footer:** `Top 20 | Atualizado`
- **Timestamp:** Timestamp UTC

---

## 🎣 12. Fishing Ranking (`fishing_ranking`)

**Método:** `FishingRankingNotifier.send_ranking_parts()`

### ⚠️ Nota Importante
O Fishing Ranking **NÃO usa embeds**. Ele envia **mensagens de texto simples** (`content`) divididas em **7 partes**:

1. **Header and General Statistics** - Date, temperature, server statistics
2. **TOP 20 Most Active Fishermen** - Ranking by fish quantity
3. **Detailed Statistics** - Kept, released, broken lines
4. **Ranking by Fish Species** - Individual rankings by fish type
5. **Special Records** - Heaviest fish, longest fish, etc.
6. **Fishing Statistics** - Success rate, average weight, etc.
7. **Footer** - Final information and tips

**Formato:** Mensagens de texto com formatação Markdown (code blocks, tabelas)

---

## 👨‍💼 13. Admin Log (`adminlog`)

**Método:** `AdminLogProcessor._build_embed()`

### 📌 Comandos Administrativos
- **Título:** `[Emoji] [Categoria]`
- **Cor:** Baseada na categoria
- **Descrição:**
  - **Admin:** [Nome]
  - **Steam ID:** `[ID]`
  - **Comando:** [Ação]
  - **Horário:** DD/MM/YYYY HH:MM:SS
- **Footer:** `SCUM Server Manager - Admin Log`
- **Timestamp:** Timestamp do evento

**Categorias:**
- Kick/Ban: 🚫 (Vermelho)
- Teleport: 📍 (Azul)
- Spawn: ✨ (Verde)
- Give: 🎁 (Amarelo)
- Outros: ℹ️ (Azul)

---

## ⚡ 14. Elevated Users

**Método:** `ElevatedUsersManager._send_discord_notification()`

### 📌 Elevated User Added
- **Título:** `✅ Elevated User Added`
- **Cor:** `65280` (Verde)
- **Descrição:** Detalhes do usuário adicionado
- **Footer:** `Sistema SSM - Elevated Users`
- **Timestamp:** Timestamp atual

### 📌 Elevated User Removed
- **Título:** `❌ Elevated User Removed`
- **Cor:** `15158332` (Vermelho)
- **Descrição:** Detalhes do usuário removido
- **Footer:** `Sistema SSM - Elevated Users`
- **Timestamp:** Timestamp atual

---

## 🕐 15. Timer (`timer`)

**Método:** `WeatherScheduler._send_discord_notification()`

### 📌 Notificação de Horário do Servidor
- **Título:** `🕐 SCUM Server Time`
- **Cor:** `0x00ff00` (Verde)
- **Descrição:** Horário do servidor formatado (ex: `# 09:02`)
- **Footer:** `SSM Backend - Monitoring System`

---

## 📦 16. Cargo Drop (`cargo_drop`)

**Método:** `CargoDropNotifier.send(event)`

### 📌 Cargo Drop Spawned
- **Título:** `📦 Cargo Drop Spawned`
- **Cor:** `0xF1C40F` (Amarelo)
- **Campos:**
  - **Map:** Link clicável: `Open in SCUM Map`
- **Thumbnail:** `Cargo_Drop.webp` (anexo) — arquivo: `data/imagens/Drop/Cargo_Drop.webp`
- **Footer:** `SCUM Server Manager • Cargo Drop`

---

## 📝 17. Log SSM (`log-ssm`)

**Método:** Via `send_webhook()` genérico

### 📌 Logs do Sistema
- **Título:** Dinâmico
- **Cor:** `0x0099ff` (Azul padrão)
- **Descrição:** Mensagem do log
- **Footer:** `SCUM Backend - Management System`
- **Timestamp:** Timestamp atual

---

## 🔧 Métodos Genéricos

### `send_webhook(webhook_name, title, description, color, fields)`
Método genérico para enviar qualquer embed customizado.

### `send_embed_with_image(webhook_name, embed, image_path, thumbnail_path, extra_attachments, components)`
Método para enviar embed com imagens anexadas.

---

## 📊 Resumo por Webhook

| Webhook | Embeds Enviados |
|---------|----------------|
| `serverstatus` | Status do servidor (7 tipos) + Scheduler (5 tipos) |
| `new_player` | Novo jogador conectado |
| `players_online` | Lista de jogadores online |
| `vehicle_registration` | Eventos de registro de veículos |
| `chat_in_game` | Mensagens de chat |
| `adminlog` | Comandos administrativos |
| `vehicle-log` | Destruição de veículos |
| `bunkers_status` | Status dos bunkers |
| `timer` | Notificações de timer |
| `commands` | Comandos de chat detectados |
| `fishing_ranking` | Ranking de pescadores (7 mensagens de texto, não embeds) |
| `kill_log` | PvP Kill, NPC Kill, Suicídio |
| `chest_events` | 9 tipos de eventos de baús |
| `chest_vehicle_alerts` | Alertas de baús em veículos |
| `log-ssm` | Logs do sistema |
| `lockpicking_events` | Eventos de lockpicking/raid |
| `top20_lockpicking` | Rankings de lockpicking |
| `top20_kills` | Top Killers + Shame Rank |
| `top20_snipers` | Top Snipers |
| `bank_transaction` | Notificações de transações bancárias |
| `cargo_drop` | Cargo Drop spawned (SCUM Map link + thumbnail) |

---

## 📝 Notas Importantes

1. **Rate Limiting:** Todos os webhooks respeitam rate limit de 30 requisições/minuto
2. **Retry:** Todos os webhooks têm retry automático (3 tentativas)
3. **Thumbnails/Images:** Muitos embeds incluem thumbnails ou imagens anexadas
4. **Timestamps:** Todos os embeds incluem timestamp ISO 8601
5. **Footers:** Todos os embeds incluem footer identificando o sistema

---

**Última atualização:** 2026-01-20  
**Versão do Backend:** 3.7.3
