# API de Configuração do Servidor SCUM

## 📋 Visão Geral

Este documento descreve o endpoint `/api/server/config` que permite obter e atualizar as configurações do servidor SCUM, incluindo as configurações do bot Discord.

## 🔧 Endpoint de Configuração

### Obter Configuração Atual
**GET** `http://localhost:3000/api/server/config`

Retorna todas as configurações atuais do servidor, incluindo configurações do bot Discord.

**Resposta de Sucesso:**
```json
{
  "success": true,
  "config": {
    "serverPath": "C:\\Servers\\Scum\\SCUM\\Binaries\\Win64",
    "steamCMDPath": "C:\\Servers\\steamcmd",
    "installPath": "C:\\Servers\\Scum",
    "batPath": "C:\\Servers\\start-server-no-pause.bat",
    "port": 8900,
    "maxPlayers": 64,
    "useBattleye": true,
    "autoRestart": false,
    "restartInterval": 3600000,
    "logLevel": "info",
    "checkInterval": 30000,
    "discord_bot": {
      "enabled": true,
      "token": "MTM5NTQ5NjY1NDE1NjU5NTQwNA.GEIINd.JT9KLS2ZPnC4WZr0O4ko8uqR4PdacB7u4tw42Q",
      "guild_id": "1343764652114575513",
      "webhook_key": "Chat_in_Game",
      "channels": {
        "vehicle_registration": "1395477789313994812",
        "vehicle_mount_registration": "1395634763733405756",
        "vehicle_denunciation": "1396238276808937567"
      },
      "features": {
        "vehicle_registration": {
          "enabled": true,
          "command_prefix": "/rv",
          "auto_register": true,
          "cooldown_seconds": 30,
          "embed_color": "#00ff00",
          "notification_channel": "vehicle_registration"
        },
        "vehicle_mount_registration": {
          "enabled": true,
          "command_prefix": "/rm",
          "auto_register": true,
          "cooldown_seconds": 30,
          "embed_color": "#ff8800",
          "notification_channel": "vehicle_mount_registration"
        },
        "vehicle_mount_complete": {
          "enabled": true,
          "command_prefix": "/mc",
          "auto_register": true,
          "cooldown_seconds": 30,
          "embed_color": "#00ff88",
          "notification_channel": "vehicle_registration"
        },
        "vehicle_denunciation": {
          "enabled": true,
          "command_prefix": "/dv",
          "auto_register": false,
          "cooldown_seconds": 60,
          "embed_color": "#ff0000",
          "notification_channel": "vehicle_denunciation",
          "required_roles": ["Staff", "STAFF", "Adm", "ADM"]
        },
        "user_linking": {
          "enabled": true,
          "auto_link": true,
          "link_expiration_hours": 24,
          "link_button_timeout": 300000
        },
        "notifications": {
          "error_notifications": true,
          "success_notifications": true
        }
      }
    }
  }
}
```

### Atualizar Configuração
**PUT** `http://localhost:3000/api/server/config`

Atualiza as configurações do servidor.

**Corpo da Requisição:**
```json
{
  "port": 8900,
  "maxPlayers": 64,
  "useBattleye": true,
  "autoRestart": false,
  "discord_bot": {
    "enabled": true,
    "token": "SEU_NOVO_TOKEN_AQUI",
    "guild_id": "ID_DO_SERVIDOR_DISCORD",
    "webhook_key": "Chat_in_Game",
    "channels": {
      "vehicle_registration": "ID_CANAL_VEICULOS",
      "vehicle_mount_registration": "ID_CANAL_MONTAGEM",
      "vehicle_denunciation": "ID_CANAL_DENUNCIAS"
    },
    "features": {
      "vehicle_registration": {
        "enabled": true,
        "command_prefix": "/rv",
        "auto_register": true,
        "cooldown_seconds": 30,
        "embed_color": "#00ff00",
        "notification_channel": "vehicle_registration"
      },
      "vehicle_mount_registration": {
        "enabled": true,
        "command_prefix": "/rm",
        "auto_register": true,
        "cooldown_seconds": 30,
        "embed_color": "#ff8800",
        "notification_channel": "vehicle_mount_registration"
      },
      "vehicle_mount_complete": {
        "enabled": true,
        "command_prefix": "/mc",
        "auto_register": true,
        "cooldown_seconds": 30,
        "embed_color": "#00ff88",
        "notification_channel": "vehicle_registration"
      },
      "vehicle_denunciation": {
        "enabled": true,
        "command_prefix": "/dv",
        "auto_register": false,
        "cooldown_seconds": 60,
        "embed_color": "#ff0000",
        "notification_channel": "vehicle_denunciation",
        "required_roles": ["Staff", "STAFF", "Adm", "ADM"]
      },
      "user_linking": {
        "enabled": true,
        "auto_link": true,
        "link_expiration_hours": 24,
        "link_button_timeout": 300000
      },
      "notifications": {
        "error_notifications": true,
        "success_notifications": true
      }
    }
  }
}
```

**Resposta de Sucesso:**
```json
{
  "success": true,
  "message": "Configurações atualizadas com sucesso",
  "config": {
    // ... configurações atualizadas
  }
}
```

## 📊 Estrutura de Configuração

### Configurações do Servidor
| Campo | Tipo | Descrição | Padrão |
|-------|------|-----------|--------|
| `serverPath` | string | Caminho para os binários do servidor | `C:\Servers\Scum\SCUM\Binaries\Win64` |
| `steamCMDPath` | string | Caminho para o SteamCMD | `C:\Servers\steamcmd` |
| `installPath` | string | Caminho de instalação do SCUM | `C:\Servers\Scum` |
| `batPath` | string | Caminho para o arquivo .bat original | `C:\Servers\start-server-no-pause.bat` |
| `port` | number | Porta do servidor (1-65535) | `8900` |
| `maxPlayers` | number | Máximo de jogadores (1-100) | `64` |
| `useBattleye` | boolean | Usar Battleye anti-cheat | `true` |
| `autoRestart` | boolean | Reiniciar automaticamente | `false` |
| `restartInterval` | number | Intervalo de reinício automático (ms) | `3600000` |
| `logLevel` | string | Nível de log | `info` |
| `checkInterval` | number | Intervalo de verificação de status (ms) | `30000` |

### Configurações do Bot Discord
| Campo | Tipo | Descrição |
|-------|------|-----------|
| `enabled` | boolean | Habilita/desabilita o bot |
| `token` | string | Token do bot Discord |
| `guild_id` | string | ID do servidor Discord |
| `webhook_key` | string | Chave do webhook para captura de mensagens |
| `channels` | object | IDs dos canais do Discord |
| `features` | object | Configurações dos comandos do bot |

### Canais do Discord
| Canal | Descrição | ID Exemplo |
|-------|-----------|------------|
| `vehicle_registration` | Canal para registros de veículos | `1395477789313994812` |
| `vehicle_mount_registration` | Canal para registros de montagem | `1395634763733405756` |
| `vehicle_denunciation` | Canal para denúncias de veículos | `1396238276808937567` |

### Comandos do Bot
| Comando | Prefixo | Descrição | Cooldown |
|---------|---------|-----------|----------|
| Registro de Veículo | `/rv` | Registra veículo no sistema | 30s |
| Registro de Montagem | `/rm` | Registra montagem de veículo | 30s |
| Conclusão de Montagem | `/mc` | Conclui montagem de veículo | 30s |
| Denúncia de Veículo | `/dv` | Denuncia veículo não registrado | 60s |

### Permissões para Denúncias
Os seguintes cargos podem verificar denúncias:
- `Staff` (minúsculo)
- `STAFF` (maiúsculo)
- `Adm` (minúsculo)
- `ADM` (maiúsculo)

## 🔄 Funcionalidades

### Comandos de Veículos
- **`/rv <ID> <TIPO>`** - Registra veículo
- **`/rm <ID> <TIPO>`** - Registra montagem
- **`/mc <ID>`** - Conclui montagem
- **`/dv <ID> <LOCALIZAÇÃO>`** - Denuncia veículo

### Sistema de Denúncias
- Verifica se veículo está registrado
- Mostra informações do denunciante (nome, Discord)
- Permite verificação por Staff/Adm
- Mantém histórico de denúncias

### Vinculação de Usuários
- Sistema de vinculação Discord ↔ Steam
- Botões para vincular contas
- Expiração automática de links
- Histórico de atividades

## 📝 Exemplos de Uso

### Obter Configuração
```bash
curl -X GET http://localhost:3000/api/server/config
```

### Atualizar Configuração
```bash
curl -X PUT http://localhost:3000/api/server/config \
  -H "Content-Type: application/json" \
  -d '{
    "port": 8900,
    "maxPlayers": 64,
    "discord_bot": {
      "enabled": true,
      "channels": {
        "vehicle_denunciation": "1396238276808937567"
      }
    }
  }'
```

## ⚠️ Observações

1. **Token do Discord**: O token é mascarado na resposta por segurança
2. **IDs de Canais**: Use IDs numéricos dos canais do Discord
3. **Permissões**: Configure corretamente os cargos para denúncias
4. **Cooldowns**: Evitam spam de comandos
5. **Webhooks**: Configure via `src/data/webhooks.json` 