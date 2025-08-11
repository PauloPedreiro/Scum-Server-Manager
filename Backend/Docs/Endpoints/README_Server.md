# 🖥️ Endpoint de Gerenciamento do Servidor SCUM

## Visão Geral

Este endpoint permite gerenciar completamente o servidor SCUM através de uma API REST, incluindo:

- ✅ **Iniciar** o servidor SCUM
- 🛑 **Parar** o servidor SCUM  
- 🔄 **Reiniciar** o servidor SCUM
- 📊 **Monitorar** status em tempo real
- ⚙️ **Configurar** parâmetros do servidor
- 📱 **Notificações** via Discord

## 🚀 Funcionalidades Principais

### 1. Detecção Inteligente de Processo
- Verifica automaticamente se `SCUMServer.exe` está rodando
- Atualiza status a cada 30 segundos
- Registra PID do processo para controle preciso

### 2. Geração Dinâmica de .bat
- Cria arquivo .bat temporário com configurações atuais
- Permite alterar parâmetros via API
- Mantém compatibilidade com configurações existentes

### 3. Sistema de Webhooks
- Envia notificações para Discord sobre mudanças de status
- Configurado via `src/data/webhooks.json` com chave `serverstatus`
- Inclui informações detalhadas sobre ações

### 4. Logs e Monitoramento
- Registra todas as ações de start/stop/restart
- Mantém histórico de erros
- Conta número de reinicializações

## 📋 Endpoints Disponíveis

| Método | Endpoint | Descrição |
|--------|----------|-----------|
| `GET` | `/api/server/status` | Obter status atual do servidor |
| `POST` | `/api/server/start` | Iniciar o servidor SCUM |
| `POST` | `/api/server/stop` | Parar o servidor SCUM |
| `POST` | `/api/server/restart` | Reiniciar o servidor SCUM |
| `GET` | `/api/server/config` | Obter configurações atuais |
| `PUT` | `/api/server/config` | Atualizar configurações |

## ⚙️ Configurações

### Arquivo: `src/data/server/config.json`

```json
{
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
```

### Parâmetros Configuráveis

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

## 🔧 Como Usar

### 1. Verificar Status
```bash
curl -X GET http://localhost:3000/api/server/status
```

### 2. Iniciar Servidor
```bash
curl -X POST http://localhost:3000/api/server/start
```

### 3. Parar Servidor
```bash
curl -X POST http://localhost:3000/api/server/stop
```

### 4. Reiniciar Servidor
```bash
curl -X POST http://localhost:3000/api/server/restart
```

### 5. Atualizar Configurações
```bash
curl -X PUT http://localhost:3000/api/server/config \
  -H "Content-Type: application/json" \
  -d '{
    "port": 8900,
    "maxPlayers": 64,
    "useBattleye": true
  }'
```

## 📱 Notificações Discord

O sistema envia notificações automáticas para Discord quando:

- ✅ Servidor iniciado com sucesso
- 🛑 Servidor parado com sucesso  
- 🔄 Servidor reiniciado com sucesso
- ❌ Erro ao iniciar/parar/reiniciar servidor
- ⚙️ Configurações atualizadas

### Configurar Webhooks

Edite o arquivo `src/data/webhooks.json`:

```json
{
  "serverstatus": "https://discord.com/api/webhooks/SEU_WEBHOOK_URL"
}
```

## 🧪 Testes

Execute o arquivo de teste para verificar se tudo está funcionando:

```bash
node test_server_endpoint.js
```

Ou teste um endpoint específico:

```bash
node test_server_endpoint.js /status GET
node test_server_endpoint.js /start POST
```

## 📁 Estrutura de Arquivos

```
Backend/
├── routes/
│   └── server.js              # Endpoint principal
├── src/data/server/
│   ├── config.json            # Configurações do servidor
│   └── status.json            # Status atual do servidor
├── src/data/temp/
│   ├── start-server-temp.bat  # Arquivo .bat para iniciar servidor
│   ├── stop-server.bat        # Arquivo .bat para parar servidor
│   └── restart-server.bat     # Arquivo .bat para reiniciar servidor
├── Docs/Endpoints/
│   ├── Server.md              # Documentação completa
│   └── README_Server.md       # Este arquivo
├── test_server_endpoint.js    # Arquivo de teste da API
├── test_bat_files.js          # Arquivo de teste dos .bat
└── SOLUCAO_PERMISSOES.md     # Solução para problemas de permissões
```

## 🔒 Segurança

- ✅ Validação de parâmetros de entrada
- ✅ Verificação de permissões de arquivo
- ✅ Timeout para operações longas
- ✅ Logs detalhados de todas as operações
- ✅ Tratamento de erros robusto

## ⚠️ Notas Importantes

1. **Permissões**: O backend precisa ter permissão para executar comandos no sistema
2. **Caminhos**: Verifique se os caminhos no `config.json` estão corretos
3. **Webhooks**: Configure webhooks para receber notificações
4. **Backup**: Faça backup das configurações antes de alterar
5. **Monitoramento**: O status é atualizado automaticamente a cada 30 segundos

## 🐛 Solução de Problemas

### Servidor não inicia
- Verifique se os caminhos no `config.json` estão corretos
- Confirme se o SteamCMD está instalado
- Verifique as permissões do usuário

### Erro ao parar/reiniciar servidor
- Execute o teste de processo: `node test_server_process.js`
- Verifique se o processo `SCUMServer.exe` está realmente rodando
- Confirme se o backend tem permissões para executar `taskkill`
- Verifique os logs detalhados no console do backend

### Webhooks não funcionam
- Verifique se a URL do webhook está correta
- Confirme se o webhook tem permissões de envio
- Verifique os logs do console

### Status incorreto
- Aguarde 30 segundos para atualização automática
- Execute manualmente: `GET /api/server/status`
- Verifique se o processo `SCUMServer.exe` está rodando

### Debugging Avançado

#### Teste da API:
```bash
node test_server_endpoint.js
```

#### Teste dos arquivos .bat:
```bash
node test_bat_files.js
```

#### Teste do processo:
```bash
node test_server_process.js
```

Estes testes irão:
- Verificar se `SCUMServer.exe` está rodando
- Testar todos os arquivos .bat individualmente
- Listar todos os processos relacionados ao SCUM
- Testar comandos de parada
- Mostrar logs detalhados de cada operação

## 📞 Suporte

Para dúvidas ou problemas:

1. Verifique os logs do console
2. Teste os endpoints individualmente
3. Confirme as configurações no `config.json`
4. Verifique as permissões do sistema

---

**Desenvolvido para SCUM Server Manager 2.0** 🎮 