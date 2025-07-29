# Bot Discord - APIs de Configuração

## 📋 Visão Geral

Este documento descreve as APIs disponíveis para configurar e gerenciar o bot Discord do servidor SCUM.

## 🔧 APIs de Configuração

### 1. Obter Configuração Atual
**GET** `/api/bot/config`

Retorna as configurações atuais do bot.

**Resposta:**
```json
{
  "enabled": true,
  "features": {
    "vehicle_registration": {
      "enabled": true,
      "command_prefix": "/rv",
      "auto_register": true,
      "cooldown_seconds": 30,
      "embed_color": "#00ff00"
    },
    "vehicle_mount_registration": {
      "enabled": true,
      "command_prefix": "/rm",
      "auto_register": true,
      "cooldown_seconds": 30,
      "embed_color": "#ff8800"
    }
  },
  "channels": {
    "vehicle_registration": "1395477789313994812",
    "vehicle_mount_registration": "1395634763733405756"
  }
}
```

### 2. Atualizar Configuração
**POST** `/api/bot/config`

Atualiza as configurações do bot.

**Corpo da Requisição:**
```json
{
  "discord_bot": {
    "enabled": true,
    "token": "SEU_NOVO_TOKEN_AQUI",
    "guild_id": "ID_DO_SERVIDOR_DISCORD",
    "webhook_key": "Chat_in_Game",
    "channels": {
      "vehicle_registration": "ID_CANAL_VEICULOS",
      "vehicle_mount_registration": "ID_CANAL_MONTAGEM"
    },
    "features": {
      "vehicle_registration": {
        "enabled": true,
        "command_prefix": "/rv",
        "auto_register": true,
        "cooldown_seconds": 30,
        "embed_color": "#00ff00"
      },
      "vehicle_mount_registration": {
        "enabled": true,
        "command_prefix": "/rm",
        "auto_register": true,
        "cooldown_seconds": 30,
        "embed_color": "#ff8800"
      }
    }
  }
}
```

**Resposta:**
```json
{
  "message": "Configuração atualizada com sucesso",
  "config": {
    "enabled": true,
    "token": "***",
    "guild_id": "1343764652114575513",
    "channels": {
      "vehicle_registration": "1395477789313994812",
      "vehicle_mount_registration": "1395634763733405756"
    }
  }
}
```

## 📊 APIs de Status

### 3. Status do Bot
**GET** `/api/bot/status`

Retorna o status atual do bot e estatísticas.

**Resposta:**
```json
{
  "enabled": true,
  "linked_users": 5,
  "total_registrations": 25,
  "pending_requests": 2,
  "active_cooldowns": 1
}
```

## 👥 APIs de Gerenciamento de Usuários

### 4. Listar Usuários Vinculados
**GET** `/api/bot/linked-users`

Lista todos os usuários vinculados (Discord ↔ Steam).

**Resposta:**
```json
[
  {
    "discord_id": "123456789012345678",
    "steam_id": "76561198040636105",
    "linked_at": "2025-07-18T18:30:00.000Z",
    "last_activity": "2025-07-18T18:45:00.000Z",
    "total_registrations": 3
  }
]
```

### 5. Vincular Usuário
**POST** `/api/bot/link-user`

Vincula um usuário Discord a um Steam ID.

**Corpo da Requisição:**
```json
{
  "discord_id": "123456789012345678",
  "steam_id": "76561198040636105"
}
```

**Resposta:**
```json
{
  "message": "Usuário vinculado com sucesso",
  "discord_id": "123456789012345678",
  "steam_id": "76561198040636105"
}
```

### 6. Desvincular Usuário
**DELETE** `/api/bot/unlink-user/:discordId`

Remove a vinculação de um usuário.

**Resposta:**
```json
{
  "message": "Usuário desvinculado com sucesso",
  "discord_id": "123456789012345678"
}
```

## 🚗 APIs de Gerenciamento de Veículos

### 7. Listar Registros de Veículos
**GET** `/api/bot/vehicle-registrations`

Lista todos os registros de veículos.

**Resposta:**
```json
[
  {
    "vehicleId": "2174460",
    "vehicleType": "AVIAO",
    "steamId": "76561198040636105",
    "discordUserId": "123456789012345678",
    "discordUsername": "Pedreiro",
    "registeredAt": "2025-07-18T18:30:00.000Z",
    "channelId": "1395477789313994812"
  }
]
```

### 8. Registros por Usuário
**GET** `/api/bot/vehicle-registrations/:steamId`

Lista registros de um usuário específico.

### 9. Registrar Veículo Manualmente
**POST** `/api/bot/vehicle-registration`

Registra um veículo manualmente via API.

**Corpo da Requisição:**
```json
{
  "vehicleId": "2194242",
  "vehicleType": "AVIAO",
  "steamId": "76561198040636105",
  "discordUserId": "123456789012345678"
}
```

## ⚡ APIs Utilitárias

### 10. Limpar Cooldown
**POST** `/api/bot/clear-cooldown/:steamId`

Remove o cooldown de um usuário.

**Resposta:**
```json
{
  "message": "Cooldown limpo com sucesso",
  "steam_id": "76561198040636105"
}
```

### 11. Solicitações Pendentes
**GET** `/api/bot/pending-requests`

Lista solicitações pendentes de vinculação.

**Resposta:**
```json
[
  {
    "steam_id": "76561198040636105",
    "vehicle_id": "2194242",
    "vehicle_type": "AVIAO",
    "requested_at": "2025-07-18T18:30:00.000Z",
    "expires_at": "2025-07-18T18:35:00.000Z"
  }
]
```

## 🔧 Exemplos de Uso

### Atualizar Token do Bot
```bash
curl -X POST http://localhost:8900/api/bot/config \
  -H "Content-Type: application/json" \
  -d '{
    "discord_bot": {
      "token": "SEU_NOVO_TOKEN_AQUI"
    }
  }'
```

### Atualizar IDs dos Canais
```bash
curl -X POST http://localhost:8900/api/bot/config \
  -H "Content-Type: application/json" \
  -d '{
    "discord_bot": {
      "channels": {
        "vehicle_registration": "NOVO_ID_CANAL_VEICULOS",
        "vehicle_mount_registration": "NOVO_ID_CANAL_MONTAGEM"
      }
    }
  }'
```

### Vincular Usuário
```bash
curl -X POST http://localhost:8900/api/bot/link-user \
  -H "Content-Type: application/json" \
  -d '{
    "discord_id": "123456789012345678",
    "steam_id": "76561198040636105"
  }'
```

## 📝 Notas Importantes

1. **Token do Bot**: Deve ser um token válido do Discord
2. **IDs dos Canais**: Deve ser IDs válidos de canais do Discord
3. **Guild ID**: Deve ser o ID do servidor Discord
4. **Permissões**: O bot deve ter permissões nos canais configurados
5. **Webhook**: O webhook "Chat_in_Game" deve estar configurado no servidor

## 🚨 Códigos de Erro

- **400**: Dados inválidos na requisição
- **404**: Recurso não encontrado
- **500**: Erro interno do servidor

## 🔄 Reinicialização

Após alterar configurações importantes (token, IDs de canais), é recomendado reiniciar o bot para aplicar as mudanças. 