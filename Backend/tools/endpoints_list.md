# Lista Completa de Endpoints - SSM Backend

## 🔐 Autenticação

### Públicos
- `POST /api/auth/login` - Login
- `POST /api/auth/change-password` - Mudar senha
- `POST /api/auth/request-password-reset` - Solicitar reset de senha
- `POST /api/auth/reset-password` - Resetar senha com token
- `GET /api/auth/debug` - Debug de autenticação
- `POST /api/auth/reset-admin-password` - Resetar senha do admin (emergência)

### Protegidos (Requer Auth)
- `GET /api/auth/me` - Informações do usuário atual
- `POST /api/auth/logout` - Logout

### Admin Apenas
- `POST /api/auth/users` - Criar usuário
- `GET /api/auth/users` - Listar usuários
- `GET /api/auth/users/search-players` - Buscar players para vincular
- `PUT /api/auth/users/<id>` - Atualizar usuário
- `DELETE /api/auth/users/<id>` - Deletar usuário

## 🏥 Health Check

### Públicos
- `GET /api/health` - Health check básico
- `GET /api/health/detailed` - Health check detalhado

## 🖥️ Servidor

### Públicos
- `GET /api/server/status` - Status do servidor

### Protegidos (Requer Auth)
- `POST /api/server/start` - Iniciar servidor
- `POST /api/server/stop` - Parar servidor
- `POST /api/server/restart` - Reiniciar servidor
- `POST /api/server/cleanup-wal` - Limpar arquivos WAL
- `GET /api/server/settings` - Obter configurações
- `PATCH /api/server/settings` - Atualizar configurações
- `PUT /api/server/settings/<section>` - Atualizar seção específica
- `GET /api/server/logs` - Obter logs do servidor

## ⚙️ Configuração

### Protegidos (Requer Auth)
- `GET /api/config` - Obter configuração
- `GET /api/config/sections` - Listar seções
- `PATCH /api/config` - Atualizar configuração parcial
- `GET /api/config/backup` - Backup da configuração

### Admin Apenas
- `PUT /api/config` - Substituir configuração completa
- `PUT /api/config/<section>` - Substituir seção
- `POST /api/config/restore` - Restaurar configuração

## 🔔 Webhooks

### Protegidos (Requer Auth)
- `GET /api/webhooks` - Listar webhooks
- `GET /api/webhooks/names` - Nomes dos webhooks
- `GET /api/webhooks/<webhook_name>` - Obter webhook específico
- `PATCH /api/webhooks` - Atualizar webhooks parcialmente
- `PUT /api/webhooks/<webhook_name>` - Atualizar webhook específico
- `POST /api/webhooks/<webhook_name>/test` - Testar webhook
- `POST /api/webhooks/test` - Testar webhook genérico
- `GET /api/webhooks/backup` - Backup dos webhooks

### Admin Apenas
- `PUT /api/webhooks` - Substituir webhooks completos
- `POST /api/webhooks/restore` - Restaurar webhooks

## 📅 Agendador

### Protegidos (Requer Auth)
- `GET /api/scheduler/status` - Status do agendador
- `POST /api/scheduler/start` - Iniciar agendador
- `POST /api/scheduler/stop` - Parar agendador
- `POST /api/scheduler/restart` - Reiniciar agendador
- `GET /api/scheduler/logs` - Logs do agendador
- `GET /api/scheduler/config` - Configuração do agendador
- `POST /api/scheduler/config` - Atualizar configuração

### Admin Apenas
- `POST /api/scheduler/force-restart` - Forçar restart imediato

## 🌤️ Clima

### Protegidos (Requer Auth)
- `GET /api/weather/status` - Status do clima
- `GET /api/weather/time` - Hora atual do jogo
- `POST /api/weather/start` - Iniciar agendador de clima
- `POST /api/weather/stop` - Parar agendador de clima

## 👥 Players

### Protegidos (Requer Auth)
- `GET /api/players` - Listar players
- `GET /api/players/online/stats` - Estatísticas de jogadores online
- `GET /api/players/online/list` - Lista de jogadores online
- `GET /api/players/online/check` - Verificar jogador
- `GET /api/players/fame` - Fama dos players
- `GET /api/players/<steam_id>/fame` - Fama de um player
- `GET /api/players/vehicles/summary` - Resumo de veículos
- `PUT /api/players/<steam_id>/permissao` - Atualizar permissão
- `GET /api/players/<steam_id>/permissions` - Permissões do player
- `POST /api/players/<steam_id>/permissions/<type>/activate` - Ativar permissão
- `POST /api/players/<steam_id>/permissions/<type>/deactivate` - Desativar permissão

## 🏆 Rankings

### Protegidos (Requer Auth)
- `GET /api/rankings` - Rankings por categoria
- `GET /api/rankings/list` - Lista completa de rankings

## 👥 Squads

### Protegidos (Requer Auth)
- `GET /api/squads` - Listar squads
- `GET /api/squads/ranking` - Ranking de squads
- `GET /api/squads/<squad_id>` - Detalhes do squad
- `GET /api/squads/<squad_id>/members` - Membros do squad

## 🗺️ GPS

### Protegidos (Requer Auth)
- `GET /api/gps/online` - GPS de jogadores online

## 📦 Baús

### Protegidos (Requer Auth)
- `GET /api/chests` - Listar baús

## 🚩 Flags

### Protegidos (Requer Auth)
- `GET /api/flags` - Bandeiras do mapa

## 📝 Logs

### Protegidos (Requer Auth)
- `GET /api/logs/players` - Logs de players

### Admin Apenas
- `POST /api/logs/cleanup` - Limpar logs

## 🔔 Notificações

### Protegidos (Requer Auth)
- `GET /api/notifications/status` - Status de notificações
- `GET /api/notifications/admin/templates` - Templates de notificações

## 🔐 Permissões

### Protegidos (Requer Auth)
- `GET /api/permissions/stats` - Estatísticas de permissões
- `POST /api/permissions/sync-ini-files` - Sincronizar arquivos INI

## ⬆️ Elevated Users

### Protegidos (Requer Auth)
- `GET /api/elevated-users/list` - Lista de elevated users

## 🎯 Survival Stats

### Protegidos (Requer Auth)
- `GET /api/survival/leaderboard` - Leaderboard de sobrevivência
- `GET /api/survival/player/<identifier>` - Stats de um player

## 🎣 Fishing Ranking

### Protegidos (Requer Auth)
- `POST /api/fishing-ranking/test` - Testar ranking de pesca

## 🚗 Veículos

### Protegidos (Requer Auth)
- `GET /api/vehicles/players` - Veículos dos players

## 👤 Owner Info

### Protegidos (Requer Auth)
- `GET /api/owner/info` - Informações do proprietário
- `POST /api/owner/info` - Atualizar proprietário

## 📡 Remote Commands

### Protegidos (Requer Auth)
- `POST /api/remote/command` - Comandos remotos

## 🔍 Identity

### Públicos (ou Protegidos)
- `GET /api/identity` - Identidade do backend

## 📜 Licensing

### Públicos
- `GET /api/licensing/hardware-fingerprint` - Hardware fingerprint
