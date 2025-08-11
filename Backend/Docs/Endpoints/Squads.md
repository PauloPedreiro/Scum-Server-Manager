# API de Squads Backend

## Visão Geral

O sistema de squads permite monitorar automaticamente os squads do servidor SCUM, copiando o banco de dados, lendo as informações dos squads e enviando embeds atualizados para o Discord a cada hora.

## Endpoints Disponíveis

### 1. GET /api/squads

**Descrição:** Executa a verificação de squads

**Resposta de Sucesso:**
```json
{
  "success": true,
  "message": "Verificação de squads executada com sucesso",
  "data": {
    "squads_count": 5,
    "last_check": "2024-01-20T10:30:00.000Z",
    "last_execution": "2024-01-20T10:30:00.000Z",
    "next_execution": "2024-01-20T11:30:00.000Z",
    "interval_hours": 1
  }
}
```

### 2. GET /api/squads/status

**Descrição:** Obtém o status atual do sistema de squads

**Resposta de Sucesso:**
```json
{
  "success": true,
  "message": "Status do sistema de squads recuperado com sucesso",
  "data": {
    "squads_count": 5,
    "last_check": "2024-01-20T10:30:00.000Z",
    "last_execution": "2024-01-20T10:30:00.000Z",
    "next_execution": "2024-01-20T11:30:00.000Z",
    "interval_hours": 1,
    "is_enabled": true
  }
}
```

### 3. GET /api/squads/list

**Descrição:** Lista todos os squads salvos

**Resposta de Sucesso:**
```json
{
  "success": true,
  "message": "Lista de squads recuperada com sucesso",
  "data": {
            "squads": {
          "squad_id_1": {
            "id": "squad_id_1",
            "name": "Nome do Squad",
            "message": "Mensagem do Squad",
            "emblem": "ID do Emblema",
            "information": "Informações do Squad",
            "score": 1000.0,
            "member_limit": 8,
            "last_member_login_time": "2024-01-20T10:30:00.000Z",
            "last_member_logout_time": "2024-01-20T10:30:00.000Z",
            "members": [
              {
                "id": "member_id_1",
                "user_profile_id": "user_profile_id_1",
                "name": "Nome do Membro 1",
                "steam_id": "steam_id_1",
                "rank": 1
              },
              {
                "id": "member_id_2",
                "user_profile_id": "user_profile_id_2", 
                "name": "Nome do Membro 2",
                "steam_id": "steam_id_2",
                "rank": 2
              }
            ],
            "embed_message_id": "discord_message_id",
            "last_updated": "2024-01-20T10:30:00.000Z"
          }
        },
    "total_count": 1,
    "last_check": "2024-01-20T10:30:00.000Z"
  }
}
```

### 4. POST /api/squads/force-update

**Descrição:** Força uma atualização completa dos squads

**Resposta de Sucesso:**
```json
{
  "success": true,
  "message": "Atualização forçada de squads executada com sucesso",
  "data": {
    "timestamp": "2024-01-20T10:30:00.000Z"
  }
}
```

## Configuração

### Configuração no config.json

Adicionar na seção `discord_bot.channels`:
```json
{
  "discord_bot": {
    "channels": {
      "squads": "1400729821918531604"
    }
  }
}
```

### Configuração no webhooks.json

Adicionar webhook para squads:
```json
{
  "squads": "https://discord.com/api/webhooks/1400729821918531604/webhook_token_aqui"
}
```

## Funcionamento

### Fluxo de Execução

1. **Cópia do Banco:** Copia `C:\Servers\scum\SCUM\Saved\SaveFiles\SCUM.db` para `src/data/squad/temp/SCUM.db`

2. **Leitura dos Dados:** Executa queries SQL para buscar squads e membros:
   ```sql
   SELECT 
       s.id as squad_id,
       s.name as squad_name,
       s.message as squad_message,
       s.emblem as squad_emblem,
       s.information as squad_information,
       s.score as squad_score,
       s.member_limit,
       s.last_member_login_time,
       s.last_member_logout_time,
       sm.id as member_id,
       sm.squad_id,
       sm.user_profile_id,
       sm.rank as member_rank,
       u.name as member_name,
       u.user_id as member_steam_id
   FROM squad s
   LEFT JOIN squad_member sm ON s.id = sm.squad_id
   LEFT JOIN user_profile u ON sm.user_profile_id = u.id
   ORDER BY s.id, sm.rank DESC, u.name
   ```

3. **Processamento:** Organiza os dados em estrutura de squads com líder e membros

4. **Comparação:** Compara com dados salvos anteriormente para identificar mudanças

5. **Atualização:** Atualiza apenas squads que tiveram modificações

6. **Envio de Embeds:** Envia embeds atualizados para o Discord

7. **Limpeza:** Remove arquivo temporário do banco

### Controle de Intervalo

- **Intervalo:** 1 hora (3600000ms)
- **Verificação:** Se passou 1 hora desde a última execução
- **Atualização:** Apenas squads modificados
- **Embeds:** Atualiza embed existente ou cria novo

### Estrutura de Dados

**squads.json:**
```json
{
  "squads": {
    "squad_id": {
      "id": "squad_id",
      "name": "Nome do Squad",
      "message": "Mensagem do Squad",
      "emblem": "ID do Emblema",
      "information": "Informações do Squad",
      "score": 1000.0,
      "member_limit": 8,
      "last_member_login_time": "2024-01-20T10:30:00.000Z",
      "last_member_logout_time": "2024-01-20T10:30:00.000Z",
      "members": [
        {
          "id": "member_id",
          "user_profile_id": "user_profile_id",
          "name": "Nome do Membro",
          "steam_id": "steam_id",
          "rank": 1
        }
      ],
      "embed_message_id": "discord_message_id",
      "last_updated": "2024-01-20T10:30:00.000Z"
    }
  },
  "last_check": "2024-01-20T10:30:00.000Z"
}
```

**lastProcessed.json:**
```json
{
  "last_execution": "2024-01-20T10:30:00.000Z",
  "next_execution": "2024-01-20T11:30:00.000Z",
  "interval_hours": 1
}
```

## Integração com Scheduler

O endpoint `/api/squads` é executado automaticamente pelo scheduler backend a cada 30 segundos, mas só processa se passou 1 hora desde a última execução.

### Configuração no Scheduler

```json
{
  "scheduler": {
    "endpoints": [
      "/api/adminlog",
      "/api/chat_in_game",
      "/api/LogVeiculos", 
      "/api/famepoints",
      "/api/bunkers/status",
      "/api/players/painelplayers",
      "/api/squads"
    ]
  }
}
```

## Tratamento de Erros

- **Banco não encontrado:** Erro se arquivo `SCUM.db` não existir
- **Erro na cópia:** Falha se não conseguir copiar arquivo
- **Erro SQL:** Falha se query não funcionar
- **Erro Discord:** Falha se não conseguir enviar embed
- **Timeout:** Timeout se operação demorar muito

## Logs

O sistema registra logs detalhados:
- ✅ Banco de dados copiado para pasta temp
- 🔄 Squad modificado, atualizando...
- ✅ Embed do squad atualizado
- 💾 Dados dos squads atualizados
- ✅ Banco de dados temporário removido
- ✅ Sistema de squads executado com sucesso 