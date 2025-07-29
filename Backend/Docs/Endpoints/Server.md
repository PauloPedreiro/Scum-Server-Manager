# Endpoint de Gerenciamento do Servidor SCUM

Este endpoint permite gerenciar o servidor SCUM através de uma API REST, incluindo iniciar, parar, reiniciar e monitorar o status do servidor.

## Base URL
```
http://localhost:3000/api/server
```

## Endpoints Disponíveis

### 1. Obter Status do Servidor
**GET** `/status`

Retorna o status atual do servidor SCUM.

**Resposta de Sucesso:**
```json
{
  "success": true,
  "status": {
    "isRunning": true,
    "pid": "1234",
    "startTime": "2025-01-16T10:30:00.000Z",
    "lastCheck": "2025-01-16T10:35:00.000Z",
    "uptime": 300000,
    "restartCount": 2,
    "lastError": null,
    "version": null
  },
  "config": {
    "port": 8900,
    "maxPlayers": 64,
    "useBattleye": true,
    "serverPath": "C:\\Servers\\Scum\\SCUM\\Binaries\\Win64"
  }
}
```

### 2. Iniciar Servidor
**POST** `/start`

Inicia o servidor SCUM usando as configurações atuais.

**Resposta de Sucesso:**
```json
{
  "success": true,
  "message": "Servidor iniciado com sucesso"
}
```

**Resposta de Erro (já rodando):**
```json
{
  "success": false,
  "error": "Servidor já está rodando"
}
```

### 3. Parar Servidor
**POST** `/stop`

Para o servidor SCUM em execução.

**Resposta de Sucesso:**
```json
{
  "success": true,
  "message": "Servidor parado com sucesso"
}
```

**Resposta de Erro (não está rodando):**
```json
{
  "success": false,
  "error": "Servidor não está rodando"
}
```

### 4. Reiniciar Servidor
**POST** `/restart`

Para e reinicia o servidor SCUM.

**Resposta de Sucesso:**
```json
{
  "success": true,
  "message": "Servidor reiniciado com sucesso"
}
```

**Resposta de Erro (não está rodando):**
```json
{
  "success": false,
  "error": "Servidor não está rodando"
}
```

### 5. Obter Configurações
**GET** `/config`

Retorna as configurações atuais do servidor, incluindo configurações do bot Discord.

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
      "token": "***",
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
          "embed_color": "#00ff00"
        },
        "vehicle_mount_registration": {
          "enabled": true,
          "command_prefix": "/rm",
          "auto_register": true,
          "cooldown_seconds": 30,
          "embed_color": "#ff8800"
        },
        "vehicle_mount_complete": {
          "enabled": true,
          "command_prefix": "/mc",
          "auto_register": true,
          "cooldown_seconds": 30,
          "embed_color": "#00ff88"
        },
        "vehicle_denunciation": {
          "enabled": true,
          "command_prefix": "/dv",
          "auto_register": false,
          "cooldown_seconds": 60,
          "embed_color": "#ff0000",
          "required_roles": ["Staff", "STAFF", "Adm", "ADM"]
        }
      }
    }
  }
}
```

### 6. Atualizar Configurações
**PUT** `/config`

Atualiza as configurações do servidor.

**Corpo da Requisição:**
```json
{
  "port": 8900,
  "maxPlayers": 64,
  "useBattleye": true,
  "autoRestart": false
}
```

**Resposta de Sucesso:**
```json
{
  "success": true,
  "message": "Configurações atualizadas com sucesso",
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
    "checkInterval": 30000
  }
}
```

## Configurações Disponíveis

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

## Funcionalidades

### Detecção de Processo
- Verifica automaticamente se `SCUMServer.exe` está rodando
- Atualiza status a cada 30 segundos
- Registra PID do processo para controle preciso

### Geração Dinâmica de .bat
- Cria arquivo .bat temporário com configurações atuais
- Permite alterar parâmetros via API
- Mantém compatibilidade com configurações existentes

### Webhooks
- Envia notificações para Discord sobre mudanças de status
- Configurado via `src/data/webhooks.json` com chave `serverstatus`
- Inclui informações detalhadas sobre ações

### Bot Discord - Sistema de Veículos
- **Comando `/rv`**: Registro de veículos no jogo
- **Comando `/rm`**: Registro de montagem de veículos
- **Comando `/mc`**: Conclusão de montagem de veículos
- **Comando `/dv`**: Denúncias de veículos não registrados
- Sistema de vinculação Discord ↔ Steam
- Embeds informativos com botões interativos
- Sistema de permissões para Staff/Adm
- Histórico completo de registros e denúncias

### Logs e Monitoramento
- Registra todas as ações de start/stop/restart
- Mantém histórico de erros
- Conta número de reinicializações

## Exemplos de Uso

### Verificar Status
```bash
curl -X GET http://localhost:3000/api/server/status
```

### Iniciar Servidor
```bash
curl -X POST http://localhost:3000/api/server/start
```

### Parar Servidor
```bash
curl -X POST http://localhost:3000/api/server/stop
```

### Reiniciar Servidor
```bash
curl -X POST http://localhost:3000/api/server/restart
```

### Atualizar Configurações
```bash
curl -X PUT http://localhost:3000/api/server/config \
  -H "Content-Type: application/json" \
  -d '{
    "port": 8900,
    "maxPlayers": 64,
    "useBattleye": true
  }'
```

## Arquivos de Configuração

### config.json
Localizado em `src/data/server/config.json`, contém todas as configurações do servidor.

### status.json
Localizado em `src/data/server/status.json`, mantém o status atual do servidor.

## Segurança

- Validação de parâmetros de entrada
- Verificação de permissões de arquivo
- Timeout para operações longas
- Logs detalhados de todas as operações

## Notas Importantes

1. **Permissões**: O backend precisa ter permissão para executar comandos no sistema
2. **Caminhos**: Verifique se os caminhos no config.json estão corretos
3. **Webhooks**: Configure webhooks para receber notificações
4. **Backup**: Faça backup das configurações antes de alterar
5. **Monitoramento**: O status é atualizado automaticamente a cada 30 segundos 