# Sistema de Logging Melhorado

## 📋 Visão Geral

O sistema de logging foi completamente reformulado para fornecer logs mais limpos, organizados e controláveis. O novo sistema substitui os `console.log` verbosos por um logger centralizado com diferentes níveis de verbosidade.

## 🎯 Benefícios do Novo Sistema

### ✅ **Logs Limpos e Organizados**
- **Sem spam**: Logs desnecessários foram removidos
- **Estruturados**: Informações organizadas em JSON
- **Coloridos**: Diferentes cores para diferentes níveis
- **Contexto**: Informações adicionais em cada log

### ✅ **Níveis de Log Configuráveis**
- **error**: Erros críticos (vermelho)
- **warn**: Avisos importantes (amarelo)
- **info**: Informações gerais (ciano)
- **debug**: Detalhes técnicos (cinza)

### ✅ **Logs Específicos por Módulo**
- **Bot**: 🤖 Logs do bot Discord
- **Server**: 🖥️ Logs do servidor
- **Vehicle**: 🚗 Logs de veículos
- **User**: 👤 Logs de usuários
- **Webhook**: 📡 Logs de webhooks
- **Database**: 💾 Logs de banco de dados
- **Config**: ⚙️ Logs de configuração

## 🔧 Configuração

### Arquivo de Configuração
```javascript
// src/config/logger.config.js
module.exports = {
    level: 'info',           // Nível de log
    file: 'src/data/logs/app.log',  // Arquivo de log
    maxSize: 10 * 1024 * 1024,     // 10MB
    maxFiles: 5,                    // 5 arquivos de backup
    colors: true,                   // Cores no console
    debug: false                    // Logs de debug
};
```

### Variáveis de Ambiente
```bash
LOG_LEVEL=info              # error, warn, info, debug
LOG_FILE_PATH=logs/app.log  # Caminho do arquivo
LOG_MAX_SIZE=10485760       # Tamanho máximo (10MB)
LOG_MAX_FILES=5            # Número de backups
```

## 📝 Como Usar

### Importar o Logger
```javascript
const logger = require('./src/logger');
```

### Logs Básicos
```javascript
logger.error('Erro crítico');
logger.warn('Aviso importante');
logger.info('Informação geral');
logger.debug('Debug detalhado');
logger.success('Operação realizada');
```

### Logs Específicos
```javascript
// Bot Discord
logger.bot('Bot conectado');

// Servidor
logger.server('Servidor iniciado');

// Veículos
logger.vehicle('Veículo registrado');

// Usuários
logger.user('Usuário vinculado');

// Webhooks
logger.webhook('Mensagem recebida');

// Banco de dados
logger.database('Dados salvos');

// Configuração
logger.config('Config atualizada');
```

### Logs de Comandos
```javascript
// Comando executado
logger.command('rv', 'Pedreiro', '76561198040636105', '11005', {
    vehicleType: 'RANGER'
});

// Registro de veículo
logger.registration('Veículo', '11005', 'Pedreiro', '76561198040636105');

// Erro de comando
logger.commandError('rv', new Error('Veículo já registrado'), {
    vehicleId: '11005'
});
```

### Logs de Vinculação
```javascript
// Vinculação criada
logger.linking('criada', '76561198040636105', '123456789012345678');

// Vinculação atualizada
logger.linking('atualizada', '76561198040636105', '123456789012345678');
```

### Logs de Webhook
```javascript
logger.webhookMessage('Chat_in_Game', '🎯 Pedreiro (76561198040636105): /rv 11005 RANGER');
```

### Logs de Status
```javascript
logger.serverStatus('Online', { players: 15, maxPlayers: 64 });
```

### Logs de Performance
```javascript
logger.performance('Processamento de comando', 150, { command: 'rv' });
```

### Logs de Cooldown
```javascript
logger.cooldown('76561198040636105', 'rv', 25);
```

### Logs de Denúncia
```javascript
logger.denunciation('criada', '11005', 'Pedreiro', '76561198040636105', {
    location: '{X=123 Y=456 Z=789}'
});
```

### Logs de Permissão
```javascript
logger.permission('verificada', 'Pedreiro', 'Staff', {
    action: 'denunciation_verify'
});
```

## 📊 Exemplo de Saída

### Console (Colorido)
```
🤖 Bot Discord conectado
🖥️ Servidor iniciado na porta 3000
🚗 Veículo registrado com sucesso
👤 Usuário vinculado ao Discord
📡 Mensagem recebida via webhook
💾 Dados salvos no banco
⚙️ Configuração atualizada
🎮 Comando /rv executado {"player":"Pedreiro","steamId":"7656****6105","vehicleId":"11005"}
```

### Arquivo de Log (JSON)
```json
{
  "timestamp": "2025-07-20T04:08:52.358Z",
  "level": "info",
  "message": "🤖 Bot Discord conectado",
  "context": {}
}
{
  "timestamp": "2025-07-20T04:08:52.378Z",
  "level": "info",
  "message": "🎮 Comando /rv executado",
  "context": {
    "player": "Pedreiro",
    "steamId": "7656****6105",
    "vehicleId": "11005",
    "vehicleType": "RANGER"
  }
}
```

## 🔍 Filtros e Busca

### Por Nível
```bash
# Apenas erros
grep '"level":"error"' src/data/logs/app.log

# Apenas comandos
grep '"message":"🎮 Comando' src/data/logs/app.log

# Apenas veículos
grep '"message":"🚗' src/data/logs/app.log
```

### Por Steam ID
```bash
# Logs de um jogador específico
grep '7656****6105' src/data/logs/app.log
```

### Por Veículo
```bash
# Logs de um veículo específico
grep '"vehicleId":"11005"' src/data/logs/app.log
```

## 📁 Estrutura de Arquivos

```
src/
├── logger.js                    # Sistema de logging
├── config/
│   └── logger.config.js        # Configuração do logger
└── data/
    └── logs/
        ├── app.log             # Log atual
        ├── app.log.1           # Backup 1
        ├── app.log.2           # Backup 2
        └── ...
```

## ⚙️ Configurações Avançadas

### Rotação Automática
- **Tamanho máximo**: 10MB por arquivo
- **Backups**: 5 arquivos de backup
- **Rotação**: Automática quando atinge o limite

### Níveis por Módulo
```javascript
modules: {
    bot: { level: 'info', enabled: true },
    server: { level: 'info', enabled: true },
    webhook: { level: 'debug', enabled: true },
    database: { level: 'debug', enabled: true },
    vehicle: { level: 'info', enabled: true },
    user: { level: 'info', enabled: true }
}
```

### Mascaramento de Dados Sensíveis
- **Steam IDs**: `76561198040636105` → `7656****6105`
- **Tokens**: `MTM5NTQ5NjY1NDE1NjU5NTQwNA...` → `***`
- **Discord IDs**: Mantidos para rastreamento

## 🚀 Migração do Sistema Antigo

### Antes (Console.log)
```javascript
console.log(`🔍 Processando mensagem de chat: ${messageContent}`);
console.log(`✅ Veículo ${vehicleId} registrado automaticamente`);
console.log(`⚠️ Steam ID ${steamId} já vinculado`);
```

### Depois (Logger)
```javascript
logger.debug('Processando mensagem de chat', { message: messageContent.substring(0, 100) });
logger.registration('Veículo', vehicleId, 'automático', steamId);
logger.linking('já vinculado', steamId, discordUserId);
```

## 📈 Benefícios de Performance

### ✅ **Menos I/O**
- Logs estruturados reduzem processamento
- Rotação automática evita arquivos gigantes
- Filtros eficientes por nível

### ✅ **Debugging Melhorado**
- Contexto rico em cada log
- Timestamps precisos
- Rastreamento de ações

### ✅ **Monitoramento**
- Logs específicos por funcionalidade
- Métricas de performance
- Alertas automáticos

## 🎯 Próximos Passos

1. **Implementar logs de performance** para comandos lentos
2. **Adicionar alertas** para erros críticos
3. **Criar dashboard** de logs em tempo real
4. **Integrar com ferramentas** de monitoramento

## 📞 Suporte

Para dúvidas sobre o sistema de logging:
- Consulte `src/logger.js` para implementação
- Verifique `src/config/logger.config.js` para configuração
- Teste com `node test_logger.js` para exemplos

**O novo sistema de logging está pronto para uso! 🎉** 