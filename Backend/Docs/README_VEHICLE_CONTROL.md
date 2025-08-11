# Sistema de Controle de Veículos - SCUM Server Manager

## Visão Geral

Este sistema monitora automaticamente os veículos registrados dos jogadores e mantém uma lista atualizada de veículos ativos por jogador. Quando um veículo é destruído, desaparece ou fica inativo, ele é automaticamente removido da lista do jogador.

## Funcionalidades

- ✅ **Monitoramento Automático:** Processa eventos de veículos em tempo real
- ✅ **Embeds Individuais:** Cada jogador tem seu próprio embed no Discord
- ✅ **Lista Numerada:** Veículos organizados em lista numerada
- ✅ **Cores Dinâmicas:** Verde para jogadores com veículos, vermelho para sem veículos
- ✅ **Atualização Periódica:** Verifica novos eventos a cada 5 minutos
- ✅ **Controle de Duplicação:** Evita processar eventos duplicados

## Arquivos do Sistema

### Principais
- `src/vehicle_control.js` - Sistema principal de controle
- `src/vehicle_control_integration.js` - Integração com servidor
- `src/data/players/player_vehicles.json` - Dados dos jogadores e veículos
- `src/data/vehicles/lastProcessedEvent.json` - Controle de eventos processados

### Dados de Entrada
- `src/data/bot/vehicle_registrations.json` - Registros de veículos
- `src/data/vehicles/vehicles.json` - Log de eventos de veículos
- `src/data/webhooks.json` - Configuração de webhooks

## Como Usar

### 1. Teste Inicial
```bash
node test_vehicle_control.js
```

### 2. Integração com Servidor
```javascript
const VehicleControlIntegration = require('./src/vehicle_control_integration');

const vehicleControl = new VehicleControlIntegration();
vehicleControl.start(); // Inicia o monitoramento
```

### 3. Controles Disponíveis
```javascript
// Forçar atualização
vehicleControl.forceUpdate();

// Parar sistema
vehicleControl.stop();

// Verificar status
const status = vehicleControl.getStatus();
console.log(status);
```

## Estrutura dos Dados

### player_vehicles.json
```json
{
  "76561198040636105": {
    "steamId": "76561198040636105",
    "playerName": "Pedreiro",
    "discordUserId": "592132368635265034",
    "activeVehicles": [
      {
        "vehicleId": "11001",
        "vehicleType": "QUAD MONTADO",
        "status": "active"
      }
    ],
    "lastUpdated": "2025-08-02T20:15:30.000Z"
  }
}
```

## Embeds do Discord

### Jogador com Veículos
```
🚗 Veículos de Pedreiro
Status atual dos seus veículos registrados

📊 Resumo
Total de Veículos: 3
Última Atualização: 2025-08-02T20:15:30.000Z

🚙 Veículos Ativos
1. 11001 - QUAD MONTADO
2. 11003 - BICLETA DE MONTANHA
3. 11004 - BICICLETA DO ZE
```

### Jogador sem Veículos
```
🚗 Veículos de Aqu1n0
Status atual dos seus veículos registrados

📊 Resumo
Total de Veículos: 0
Última Atualização: 2025-08-02T20:15:30.000Z

🚙 Veículos Ativos
Todos os veículos foram perdidos
```

## Eventos Processados

O sistema monitora e processa os seguintes eventos:
- `Destroyed` - Veículo destruído
- `Disappeared` - Veículo desaparecido
- `VehicleInactiveTimerReached` - Timer de inatividade atingido

## Configuração

### Webhook
O webhook `player-vehicles` deve ser configurado em `src/data/webhooks.json`:
```json
{
  "player-vehicles": "https://discord.com/api/webhooks/..."
}
```

### Intervalo de Verificação
Por padrão, o sistema verifica novos eventos a cada 5 minutos. Para alterar, modifique o valor em `src/vehicle_control_integration.js`:
```javascript
setInterval(() => {
    // ...
}, 5 * 60 * 1000); // 5 minutos
```

## Logs

O sistema gera logs detalhados:
- Inicialização com registros atuais
- Processamento de eventos
- Remoção de veículos
- Atualização de embeds
- Erros e exceções

## Manutenção

### Reinicialização
Para reinicializar o sistema com os registros atuais:
```javascript
vehicleControl.vehicleControl.initializeFromRegistrations();
```

### Backup
Os arquivos importantes para backup:
- `src/data/players/player_vehicles.json`
- `src/data/vehicles/lastProcessedEvent.json`

## Troubleshooting

### Problema: Embeds não aparecem
- Verificar se o webhook está configurado corretamente
- Verificar permissões do webhook no Discord
- Verificar logs de erro

### Problema: Veículos não são removidos
- Verificar se os eventos estão sendo processados
- Verificar se o `lastProcessedEvent.json` está sendo atualizado
- Verificar logs de processamento

### Problema: Sistema não inicia
- Verificar se todos os arquivos JSON existem
- Verificar permissões de leitura/escrita
- Verificar dependências (axios) 