# 🔒 Segurança dos Endpoints - Plano de Proteção

## 📋 Visão Geral

Este documento define quais endpoints devem ser protegidos com autenticação e quais podem permanecer públicos após a implementação do sistema de autenticação.

---

## 🎯 Estratégia de Proteção

### **Categorias de Endpoints:**

1. **Públicos** - Sem autenticação (acesso livre)
2. **Protegidos** - Requer autenticação (`@require_auth`)
3. **Admin Apenas** - Requer admin (`@require_admin`)

---

## ✅ Endpoints Públicos (Sem Autenticação)

Estes endpoints devem permanecer **públicos** para:
- Monitoramento externo
- Integrações básicas
- Health checks
- Informações não sensíveis

### **Health & Status**
- ✅ `GET /api/health` - Health check básico
- ✅ `GET /api/health/detailed` - Health check detalhado (pode ser protegido no futuro)
- ✅ `GET /api/server/status` - Status do servidor (informação pública)

### **Autenticação**
- ✅ `POST /api/auth/login` - Login (obviamente público)
- ✅ `POST /api/auth/change-password` - Mudança de senha (valida senha atual)

### **Informações Públicas (Opcional - Pode ser protegido)**
- ⚠️ `GET /api/identity` - Identidade do backend (pode ser público ou protegido)
- ⚠️ `GET /api/licensing/hardware-fingerprint` - Hardware fingerprint (pode ser protegido)

---

## 🔐 Endpoints Protegidos (Requer Autenticação)

Todos os usuários autenticados (admin ou moderador) podem acessar:

### **Controle do Servidor**
- 🔒 `POST /api/server/start` - Iniciar servidor
- 🔒 `POST /api/server/stop` - Parar servidor
- 🔒 `POST /api/server/restart` - Reiniciar servidor
- 🔒 `POST /api/server/cleanup-wal` - Limpar arquivos WAL

### **Configurações do Servidor**
- 🔒 `GET /api/server/settings` - Obter configurações
- 🔒 `PATCH /api/server/settings` - Atualizar configurações
- 🔒 `PUT /api/server/settings/<section>` - Atualizar seção específica

### **Configuração (config.json)**
- 🔒 `GET /api/config` - Obter configuração
- 🔒 `GET /api/config/sections` - Obter seções
- 🔒 `PATCH /api/config` - Atualizar configuração
- 🔒 `PUT /api/config` - Substituir configuração
- 🔒 `PUT /api/config/<section>` - Atualizar seção
- 🔒 `GET /api/config/backup` - Backup da configuração
- 🔒 `POST /api/config/restore` - Restaurar configuração

### **Webhooks**
- 🔒 `GET /api/webhooks` - Listar webhooks
- 🔒 `GET /api/webhooks/names` - Nomes dos webhooks
- 🔒 `PATCH /api/webhooks` - Atualizar webhooks
- 🔒 `PUT /api/webhooks` - Substituir webhooks
- 🔒 `GET /api/webhooks/<webhook_name>` - Obter webhook específico
- 🔒 `PUT /api/webhooks/<webhook_name>` - Atualizar webhook específico
- 🔒 `POST /api/webhooks/<webhook_name>/test` - Testar webhook
- 🔒 `POST /api/webhooks/test` - Testar todos webhooks
- 🔒 `GET /api/webhooks/backup` - Backup de webhooks
- 🔒 `POST /api/webhooks/restore` - Restaurar webhooks

### **Scheduler (Agendador)**
- 🔒 `GET /api/scheduler/status` - Status do agendador
- 🔒 `POST /api/scheduler/start` - Iniciar agendador
- 🔒 `POST /api/scheduler/stop` - Parar agendador
- 🔒 `POST /api/scheduler/restart` - Reiniciar agendador
- 🔒 `GET /api/scheduler/logs` - Logs do agendador
- 🔒 `GET /api/scheduler/config` - Configuração do agendador
- 🔒 `POST /api/scheduler/config` - Atualizar configuração
- 🔒 `POST /api/scheduler/force-restart` - Forçar restart

### **Weather (Clima)**
- 🔒 `GET /api/weather/status` - Status do clima
- 🔒 `POST /api/weather/start` - Iniciar sincronização de clima
- 🔒 `POST /api/weather/stop` - Parar sincronização
- 🔒 `POST /api/weather/sync` - Sincronizar clima
- 🔒 `GET /api/weather/logs` - Logs do clima
- 🔒 `GET /api/weather/time` - Horário do jogo

### **Notificações**
- 🔒 `GET /api/notifications/status` - Status das notificações
- 🔒 `POST /api/notifications/send` - Enviar notificação
- 🔒 `POST /api/notifications/clear` - Limpar notificações
- 🔒 `POST /api/notifications/cooldowns/reset` - Resetar cooldowns
- 🔒 `POST /api/notifications/restart/create` - Criar notificação de restart
- 🔒 `POST /api/notifications/restart/create-next` - Criar próxima notificação
- 🔒 `POST /api/notifications/restart/create-all` - Criar todas notificações
- 🔒 `POST /api/notifications/verify` - Verificar notificações
- 🔒 `POST /api/notifications/admin/send` - Enviar notificação admin
- 🔒 `GET /api/notifications/admin/templates` - Templates de notificações

### **Logs do Servidor**
- 🔒 `GET /api/server/logs` - Logs do servidor

### **Logs e Estatísticas**
- 🔒 `GET /api/logs/players` - Logs de jogadores
- 🔒 `GET /api/logs/players/active` - Jogadores ativos
- 🔒 `GET /api/logs/stats` - Estatísticas de logs
- 🔒 `POST /api/logs/cleanup` - Limpar logs

### **Deduplicação**
- 🔒 `GET /api/deduplication/status` - Status da deduplicação
- 🔒 `POST /api/deduplication/clear-cache` - Limpar cache
- 🔒 `POST /api/deduplication/force-reprocess` - Reprocessar forçado

### **Admin Logs**
- 🔒 `GET /api/admin-logs/status` - Status dos admin logs
- 🔒 `GET /api/admin-logs/stats` - Estatísticas
- 🔒 `GET /api/admin-logs/recent` - Logs recentes
- 🔒 `GET /api/admin-logs/processing-status` - Status de processamento
- 🔒 `GET /api/admin-logs/files-status` - Status dos arquivos

### **Kill Logs**
- 🔒 `GET /api/kill-logs/recent` - Kills recentes
- 🔒 `GET /api/kill-logs/stats` - Estatísticas de kills
- 🔒 `GET /api/kill-logs/events` - Eventos de kills

### **Players Online**
- 🔒 `GET /api/players/online` - Jogadores online
- 🔒 `GET /api/players/online/list` - Lista de jogadores online
- 🔒 `GET /api/players/online/stats` - Estatísticas
- 🔒 `POST /api/players/online/check` - Verificar jogador

### **Players**
- 🔒 `GET /api/players` - Listar players
- 🔒 `GET /api/players/fame` - Fama dos players
- 🔒 `GET /api/players/<steam_id>/fame` - Fama de um player
- 🔒 `GET /api/players/vehicles/summary` - Resumo de veículos
- 🔒 `PUT /api/players/<steam_id>/permissao` - Atualizar permissão
- 🔒 `GET /api/players/<steam_id>/permissions` - Permissões do player
- 🔒 `POST /api/players/<steam_id>/permissions/<type>/activate` - Ativar permissão
- 🔒 `POST /api/players/<steam_id>/permissions/<type>/deactivate` - Desativar permissão

### **Squads**
- 🔒 `GET /api/squads` - Listar squads
- 🔒 `GET /api/squads/ranking` - Ranking de squads
- 🔒 `GET /api/squads/<squad_id>` - Detalhes do squad
- 🔒 `GET /api/squads/<squad_id>/members` - Membros do squad
- 🔒 `GET /api/flags` - Bandeiras do mapa

### **Rankings**
- 🔒 `GET /api/rankings` - Rankings por categoria
- 🔒 `GET /api/rankings/list` - Lista completa de rankings

### **Survival Stats**
- 🔒 `GET /api/survival/leaderboard` - Leaderboard de sobrevivência
- 🔒 `GET /api/survival/player/<identifier>` - Stats de um player

### **Chat**
- 🔒 `GET /api/chat/status` - Status do chat
- 🔒 `POST /api/chat/test` - Testar chat
- 🔒 `POST /api/chat/cleanup` - Limpar chat

### **Bunkers**
- 🔒 `GET /api/bunkers/status` - Status dos bunkers
- 🔒 `POST /api/bunkers/notify` - Notificar sobre bunker

### **Veículos**
- 🔒 `GET /api/vehicles/players` - Veículos dos players

### **Permissões**
- 🔒 `GET /api/permissions/stats` - Estatísticas de permissões
- 🔒 `POST /api/permissions/sync-ini-files` - Sincronizar arquivos INI

### **Fishing Ranking**
- 🔒 `POST /api/fishing-ranking/test` - Testar ranking de pesca

### **Owner Info**
- 🔒 `GET /api/owner/info` - Informações do proprietário
- 🔒 `POST /api/owner/info` - Atualizar proprietário

### **Remote Commands**
- 🔒 `POST /api/remote/command` - Comandos remotos

---

## 👑 Endpoints Admin Apenas (Requer Admin)

Apenas usuários com `role = 'admin'` podem acessar:

### **Gerenciamento de Usuários**
- 👑 `POST /api/auth/users` - Criar usuário
- 👑 `GET /api/auth/users` - Listar usuários
- 👑 `GET /api/auth/users/search-players` - Buscar players para vincular
- 👑 `PUT /api/auth/users/<id>` - Atualizar usuário
- 👑 `DELETE /api/auth/users/<id>` - Deletar usuário

### **Configurações Críticas**
- 👑 `PUT /api/config` - Substituir configuração completa (destrutivo)
- 👑 `POST /api/config/restore` - Restaurar configuração (destrutivo)
- 👑 `PUT /api/webhooks` - Substituir webhooks completos (destrutivo)
- 👑 `POST /api/webhooks/restore` - Restaurar webhooks (destrutivo)

### **Operações Destrutivas**
- 👑 `POST /api/scheduler/force-restart` - Forçar restart imediato
- 👑 `POST /api/logs/cleanup` - Limpar logs (pode perder dados)
- 👑 `POST /api/deduplication/force-reprocess` - Reprocessar tudo

---

## 🔄 Migração de Endpoints

### **Fase 1: Implementar Autenticação**
1. Criar decorators `@require_auth` e `@require_admin`
2. Implementar endpoints de autenticação
3. Testar sistema de login

### **Fase 2: Proteger Endpoints Críticos**
1. Aplicar `@require_auth` em endpoints de controle (start/stop/restart)
2. Aplicar `@require_auth` em endpoints de configuração
3. Testar proteção

### **Fase 3: Proteger Endpoints Restantes**
1. Aplicar `@require_auth` em todos os endpoints protegidos
2. Aplicar `@require_admin` em endpoints admin apenas
3. Manter endpoints públicos sem decorator

### **Fase 4: Validação e Testes**
1. Testar todos os endpoints protegidos
2. Verificar que endpoints públicos ainda funcionam
3. Validar permissões de admin vs moderador

---

## 📝 Exemplo de Aplicação

### **Antes (Sem Autenticação):**
```python
@app.route('/api/server/start', methods=['POST'])
def start_server():
    # Código do endpoint
    ...
```

### **Depois (Com Autenticação):**
```python
@app.route('/api/server/start', methods=['POST'])
@require_auth
def start_server():
    # Código do endpoint
    # request.current_user_id disponível
    # request.current_username disponível
    # request.current_role disponível
    ...
```

### **Admin Apenas:**
```python
@app.route('/api/auth/users', methods=['POST'])
@require_admin
def create_user():
    # Apenas admins podem criar usuários
    ...
```

---

## ⚠️ Considerações Importantes

### **1. Compatibilidade Retroativa**
- Endpoints públicos devem continuar funcionando sem token
- Frontend existente pode precisar ser atualizado
- Documentar quais endpoints requerem autenticação

### **2. Configuração Opcional**
- Pode adicionar flag `auth.enabled` no `config.json`
- Se `false`, desabilitar autenticação (modo desenvolvimento)
- Se `true`, aplicar proteção

### **3. Mensagens de Erro**
- Endpoints protegidos devem retornar erro claro:
  ```json
  {
    "success": false,
    "error": "Authentication required",
    "code": "AUTH_REQUIRED"
  }
  ```

### **4. Logs de Auditoria**
- Registrar quem fez ações administrativas
- Usar `request.current_user_id` e `request.current_username`
- Logar ações críticas (start/stop/config changes)

---

## 📊 Resumo por Categoria

| Categoria | Total | Públicos | Protegidos | Admin Apenas |
|-----------|-------|----------|------------|--------------|
| Health | 2 | 2 | 0 | 0 |
| Server Control | 4 | 0 | 4 | 0 |
| Config | 7 | 0 | 5 | 2 |
| Webhooks | 9 | 0 | 9 | 0 |
| Scheduler | 8 | 0 | 8 | 0 |
| Weather | 6 | 0 | 6 | 0 |
| Notifications | 9 | 0 | 9 | 0 |
| Logs | 15 | 0 | 15 | 0 |
| Players | 8 | 0 | 8 | 0 |
| Squads | 5 | 0 | 5 | 0 |
| Rankings | 2 | 0 | 2 | 0 |
| Auth | 6 | 2 | 2 | 2 |
| **TOTAL** | **~99** | **~4** | **~90** | **~5** |

---

## ✅ Checklist de Implementação

- [ ] Criar decorators `@require_auth` e `@require_admin`
- [ ] Aplicar `@require_auth` em endpoints de controle do servidor
- [ ] Aplicar `@require_auth` em endpoints de configuração
- [ ] Aplicar `@require_auth` em endpoints de webhooks
- [ ] Aplicar `@require_auth` em endpoints de scheduler
- [ ] Aplicar `@require_auth` em endpoints de weather
- [ ] Aplicar `@require_auth` em endpoints de notificações
- [ ] Aplicar `@require_auth` em endpoints de logs
- [ ] Aplicar `@require_auth` em endpoints de players
- [ ] Aplicar `@require_auth` em endpoints de squads/rankings
- [ ] Aplicar `@require_admin` em endpoints de gerenciamento de usuários
- [ ] Aplicar `@require_admin` em operações destrutivas
- [ ] Manter endpoints públicos sem decorator
- [ ] Adicionar logs de auditoria
- [ ] Testar todos os endpoints
- [ ] Atualizar documentação

---

## 🎯 Prioridade de Implementação

### **Alta Prioridade (Críticos)**
1. Controle do servidor (start/stop/restart)
2. Configurações (config.json, server settings)
3. Gerenciamento de usuários (admin apenas)

### **Média Prioridade**
4. Webhooks
5. Scheduler
6. Notificações

### **Baixa Prioridade (Informações)**
7. Logs e estatísticas
8. Players, squads, rankings
9. Outros endpoints informativos

---

## 📚 Notas Finais

- **Flexibilidade**: Sistema permite adicionar novos roles e permissões no futuro
- **Segurança**: Todos os endpoints críticos protegidos
- **Usabilidade**: Endpoints públicos mantidos para monitoramento
- **Auditoria**: Logs de todas as ações administrativas
- **Escalabilidade**: Fácil adicionar novos tipos de acesso

