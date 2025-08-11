# Log Veículos

## Descrição
Endpoint para processar logs de destruição e eventos de veículos do SCUM. O sistema lê o log mais recente de veículos, extrai informações sobre destruição, desaparecimento e inatividade de veículos, e retorna os dados estruturados. Agora conta com histórico, controle de duplicatas e endpoints de consulta.

---

## Controle de Duplicatas
- O sistema mantém o último timestamp processado em `src/data/vehicles/lastVehicleRead.json`.
- Só eventos com timestamp maior que o último processado são salvos e retornados.
- Isso evita duplicidade no histórico e no envio de webhooks.

## Banco de Histórico
- Todos os eventos processados são salvos em `src/data/vehicles/vehicles.json`.
- Permite consultas, estatísticas e histórico completo dos eventos de veículos.

---

## Endpoints

### 1. Processar Log de Veículos
**GET** `/api/LogVeiculos`

Lê o log de veículos mais recente, extrai informações novas e retorna dados estruturados.

#### Funcionamento
1. Encontra o arquivo de log de veículos mais recente (`vehicle_destruction_*.log`)
2. Copia o arquivo para pasta temporária
3. Lê o conteúdo em UTF-16LE (fallback UTF-8)
4. Extrai apenas eventos novos (controle por timestamp)
5. Salva no histórico (`vehicles.json`)
6. Atualiza o controle de duplicatas (`lastVehicleRead.json`)
7. Remove arquivo temporário
8. Retorna dados estruturados em JSON

#### Exemplo de Response (Sucesso)
```json
{
    "success": true,
    "message": "Log de veículos processado com sucesso. 3 novos eventos encontrados.",
    "data": [
        {
            "timestamp": "2025.07.13-04.01.37",
            "event": "Destroyed",
            "vehicleType": "Kinglet_Duster_ES",
            "vehicleId": "1600649",
            "ownerSteamId": "76561198040636105",
            "ownerPlayerId": "1",
            "ownerName": "Pedreiro",
            "location": {
                "x": -311773.969,
                "y": 5480.525,
                "z": 36099.227
            },
            "processedAt": "2025-07-13T05:20:42.658Z"
        }
    ]
}
```

#### Exemplo de Response (Sem eventos novos)
```json
{
    "success": true,
    "message": "Log de veículos processado com sucesso. 0 novos eventos encontrados.",
    "data": []
}
```

---

### 2. Histórico Completo
**GET** `/api/vehicles/history`

Retorna todos os eventos já processados e salvos no banco de dados.

#### Exemplo de Response
```json
{
    "success": true,
    "message": "Histórico de veículos recuperado com sucesso",
    "data": [
        {
            "timestamp": "2025.07.13-04.01.37",
            "event": "Destroyed",
            ...
        }
    ]
}
```

---

### 3. Veículos por Proprietário
**GET** `/api/vehicles/owner/:steamId`

Retorna todos os eventos de veículos de um proprietário específico.

#### Exemplo de Response
```json
{
    "success": true,
    "message": "Veículos do proprietário 76561198140545020 recuperados com sucesso",
    "data": [
        {
            "timestamp": "2025.07.13-04.01.37",
            "event": "Disappeared",
            ...
        }
    ]
}
```

---

### 4. Estatísticas de Veículos
**GET** `/api/vehicles/stats`

Retorna estatísticas agregadas dos eventos de veículos.

#### Exemplo de Response
```json
{
    "success": true,
    "message": "Estatísticas de veículos recuperadas com sucesso",
    "data": {
        "totalEvents": 3,
        "eventsByType": {
            "Destroyed": 1,
            "Disappeared": 1,
            "VehicleInactiveTimerReached": 1
        },
        "topOwners": [
            { "steamId": "76561198140545020", "name": "mariocs10", "count": 2 },
            { "steamId": "76561198040636105", "name": "Pedreiro", "count": 1 }
        ],
        "topVehicleTypes": [
            { "type": "Tractor_ES", "count": 2 },
            { "type": "Kinglet_Duster_ES", "count": 1 }
        ]
    }
}
```

---

### 5. Enviar Histórico para Discord
**POST** `/api/vehicles/send-history`

Envia o histórico completo de veículos para o Discord via webhook com formatação bonita.

#### Parâmetros (opcional)
```json
{
    "limit": 10
}
```

#### Funcionamento
1. Lê todo o histórico de veículos
2. Cria embed do Discord com:
   - Estatísticas por tipo de evento
   - Top proprietários
   - Últimos eventos (limitados pelo parâmetro)
3. Envia para o webhook configurado

#### Exemplo de Response (Sucesso)
```json
{
    "success": true,
    "message": "Histórico de 4 veículos enviado para o Discord com sucesso",
    "data": {
        "totalEvents": 4,
        "sentToDiscord": true
    }
}
```

#### Exemplo de Response (Webhook não configurado)
```json
{
    "success": false,
    "message": "Erro ao enviar para Discord ou webhook não configurado",
    "data": {
        "totalEvents": 4,
        "sentToDiscord": false
    }
}
```

---

## Webhook para LogVeiculos

- Para cadastrar um webhook para eventos de veículos:
  - **POST** `/api/webhook/LogVeiculos`
  - Body: `{ "url": "https://discord.com/api/webhooks/SEU_WEBHOOK" }`
- Para consultar o webhook cadastrado:
  - **GET** `/api/webhook/LogVeiculos`

---

## Observações
- O endpoint só processa eventos novos, nunca repete eventos já processados.
- O histórico é salvo em `src/data/vehicles/vehicles.json`.
- O controle de duplicatas é feito por timestamp em `src/data/vehicles/lastVehicleRead.json`.
- O sistema suporta codificação UTF-16LE e UTF-8.
- Linhas de versão do jogo são ignoradas durante o processamento.
- Coordenadas são convertidas para números de ponto flutuante.

---

## Exemplos de Uso

### Processar log de veículos:
```bash
curl http://localhost:3000/api/LogVeiculos
```

### Consultar histórico:
```bash
curl http://localhost:3000/api/vehicles/history
```

### Consultar veículos por proprietário:
```bash
curl http://localhost:3000/api/vehicles/owner/76561198140545020
```

### Consultar estatísticas:
```bash
curl http://localhost:3000/api/vehicles/stats
```

### Enviar histórico para Discord:
```bash
curl -X POST http://localhost:3000/api/vehicles/send-history -H "Content-Type: application/json" -d '{"limit": 10}'
```

### Cadastrar webhook:
```bash
curl -X POST http://localhost:3000/api/webhook/LogVeiculos -H "Content-Type: application/json" -d '{"url": "https://discord.com/api/webhooks/SEU_WEBHOOK"}'
```

## Tipos de Eventos

O sistema reconhece os seguintes tipos de eventos de veículos:

- **Destroyed**: Veículo foi destruído
- **Disappeared**: Veículo desapareceu
- **VehicleInactiveTimerReached**: Timer de inatividade do veículo foi atingido

## Estrutura do Log de Veículos

O sistema espera logs no formato:
```
2025.07.13-04.01.15: Game version: 1.0.1.2.96201
2025.07.13-04.01.37: [VehicleInactiveTimerReached] Tractor_ES. VehicleId: 670006. Owner: 76561198140545020 (12, mariocs10). Location: X=-176305.094 Y=-702604.250 Z=1444.222
2025.07.13-04.01.37: [Disappeared] Tractor_ES. VehicleId: 670006. Owner: 76561198140545020 (12, mariocs10). Location: X=-176305.094 Y=-702604.250 Z=1444.222
2025.07.13-04.58.18: [Destroyed] Kinglet_Duster_ES. VehicleId: 1600649. Owner: 76561198040636105 (1, Pedreiro). Location: X=-311773.969 Y=5480.525 Z=36099.227
```

## Campos da Resposta

### Evento de Veículo
- **timestamp**: Data e hora do evento (formato: YYYY.MM.DD-HH.MM.SS)
- **event**: Tipo do evento (Destroyed, Disappeared, VehicleInactiveTimerReached)
- **vehicleType**: Tipo/modelo do veículo
- **vehicleId**: ID único do veículo
- **ownerSteamId**: Steam ID do proprietário do veículo
- **ownerPlayerId**: ID do jogador no servidor
- **ownerName**: Nome do proprietário do veículo
- **location**: Coordenadas do veículo
  - **x**: Coordenada X
  - **y**: Coordenada Y
  - **z**: Coordenada Z

## Arquivos Utilizados

- **Log de veículos**: `{SCUM_LOG_PATH}/vehicle_destruction_*.log`
- **Pasta temporária**: `src/data/temp/`

## Códigos de Status HTTP

- **200**: Sucesso
- **500**: Erro interno do servidor

## Exemplo de Uso

### Processar log de veículos:
```bash
curl http://localhost:3000/api/LogVeiculos
```

### Exemplo com cURL:
```bash
curl -X GET http://localhost:3000/api/LogVeiculos \
  -H "Content-Type: application/json" \
  -H "Accept: application/json"
```

## Logs de Debug

O sistema exibe logs no console para debug:
- Linhas que não foram reconhecidas pelo regex
- Erros ao copiar ou ler arquivos
- Erros de processamento

## Dependências

- **SCUM_LOG_PATH**: Variável de ambiente com o caminho dos logs do SCUM

## Observações

- O endpoint processa apenas o arquivo de log mais recente
- Arquivos temporários são automaticamente removidos após processamento
- O sistema suporta codificação UTF-16LE e UTF-8
- Linhas de versão do jogo são ignoradas durante o processamento
- Coordenadas são convertidas para números de ponto flutuante 