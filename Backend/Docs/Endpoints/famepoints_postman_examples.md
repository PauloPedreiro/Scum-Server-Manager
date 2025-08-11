# Exemplos de Uso - Endpoint Famepoints (Postman)

## Configuração Inicial

### 1. Configurar Environment
Crie um environment no Postman com as seguintes variáveis:

| Variable | Initial Value | Current Value |
|----------|---------------|---------------|
| `base_url` | `http://localhost:3000` | `http://localhost:3000` |
| `api_path` | `/api/famepoints` | `/api/famepoints` |

## Coleções de Exemplos

### 1. GET - Dados Básicos de Famepoints

**Request:**
```
GET {{base_url}}{{api_path}}
```

**Headers:**
```
Content-Type: application/json
```

**Response Esperada (Sucesso):**
```json
{
    "success": true,
    "message": "Dados de famepoints processados com sucesso",
    "data": [
        {
            "playerName": "Aqu1n0",
            "steamId": "76561197995901898",
            "totalFame": 588.845947,
            "timestamp": "2025-07-14T23:53:08.970Z"
        },
        {
            "playerName": "ARKANJO",
            "steamId": "76561198094354554",
            "totalFame": 771.324768,
            "timestamp": "2025-07-14T23:53:08.970Z"
        }
    ]
}
```

**Response (Arquivo Já Processado):**
```json
{
    "success": true,
    "message": "Arquivo já processado",
    "data": []
}
```

### 2. GET - Análise Completa

**Request:**
```
GET {{base_url}}{{api_path}}/analysis
```

**Headers:**
```
Content-Type: application/json
```

**Response Esperada:**
```json
{
    "success": true,
    "message": "Análise completa de todos os logs de famepoints",
    "data": {
        "summary": {
            "totalPlayers": 18,
            "totalLogsProcessed": 30,
            "dateRange": {
                "earliest": 1752176458751,
                "latest": 1752536135287
            }
        },
        "topPlayers": [
            {
                "playerName": "Reav",
                "steamId": "76561197963358180",
                "totalFame": 1099.879395,
                "logCount": 33
            }
        ],
        "players": [
            {
                "playerName": "Til4toxico",
                "steamId": "76561198129911132",
                "totalFame": 725.690002,
                "logCount": 11,
                "firstSeen": "2025-07-10T19:40:58.751Z",
                "lastSeen": "2025-07-13T23:44:32.467Z"
            }
        ]
    }
}
```

### 3. GET - Processamento Completo com Query Parameter

**Request:**
```
GET {{base_url}}{{api_path}}?all=true
```

**Headers:**
```
Content-Type: application/json
```

**Response Esperada:**
```json
{
    "success": true,
    "message": "Análise completa de todos os logs de famepoints processada",
    "data": {
        "summary": {
            "totalPlayers": 18,
            "totalLogsProcessed": 30,
            "fieldsFound": [
                "DistanceTraveledOnFoot",
                "OnlineFlagOwnersAwardAwarded",
                "BaseFameInflux",
                "DistanceTraveledWhileMounted",
                "ItemLooted",
                "PuppetKill",
                "RecoveredFromInfection",
                "ItemCrafted",
                "MeleeKill",
                "SkillLeveledUp",
                "MinigameCompleted",
                "LockPicked",
                "BandageApplied",
                "AnimalKill",
                "BlueprintBuilt",
                "BaseElementBuilt",
                "WeedsPlucked"
            ]
        },
        "players": [
            {
                "playerName": "Reav",
                "steamId": "76561197963358180",
                "history": [
                    {
                        "totalFame": 1099.879395,
                        "timestamp": "2025-07-14T23:35:35.287Z",
                        "logFile": "famepoints_20250714200120.log",
                        "DistanceTraveledOnFoot": 0.000899,
                        "OnlineFlagOwnersAwardAwarded": 0.138442,
                        "BaseFameInflux": 0.787671,
                        "MinigameCompleted": 0.000000,
                        "LockPicked": 0.035000,
                        "ItemLooted": 0.000000,
                        "PuppetKill": 0.262500,
                        "RecoveredFromInfection": 0.175000
                    }
                ]
            }
        ]
    }
}
```

## Testes Automatizados

### 1. Teste de Status de Sucesso
```javascript
pm.test("Status code is 200", function () {
    pm.response.to.have.status(200);
});

pm.test("Response has success field", function () {
    var jsonData = pm.response.json();
    pm.expect(jsonData).to.have.property('success');
});

pm.test("Success is true", function () {
    var jsonData = pm.response.json();
    pm.expect(jsonData.success).to.eql(true);
});
```

### 2. Teste de Estrutura de Dados
```javascript
pm.test("Data structure is correct", function () {
    var jsonData = pm.response.json();
    
    if (jsonData.data && jsonData.data.length > 0) {
        pm.expect(jsonData.data[0]).to.have.property('playerName');
        pm.expect(jsonData.data[0]).to.have.property('steamId');
        pm.expect(jsonData.data[0]).to.have.property('totalFame');
        pm.expect(jsonData.data[0]).to.have.property('timestamp');
    }
});
```

### 3. Teste de Validação de Dados
```javascript
pm.test("TotalFame is a number", function () {
    var jsonData = pm.response.json();
    
    if (jsonData.data && jsonData.data.length > 0) {
        pm.expect(typeof jsonData.data[0].totalFame).to.eql('number');
    }
});

pm.test("SteamId is valid format", function () {
    var jsonData = pm.response.json();
    
    if (jsonData.data && jsonData.data.length > 0) {
        var steamId = jsonData.data[0].steamId;
        pm.expect(steamId).to.match(/^\d{17}$/);
    }
});
```

## Cenários de Teste

### Cenário 1: Primeira Execução
1. Deletar arquivo `lastProcessed.json` (se existir)
2. Executar GET `/api/famepoints`
3. Verificar se retorna dados processados
4. Verificar se arquivo `lastProcessed.json` foi criado

### Cenário 2: Execução Repetida
1. Executar GET `/api/famepoints` novamente
2. Verificar se retorna "Arquivo já processado"
3. Verificar se `data` está vazio

### Cenário 3: Novo Log Disponível
1. Adicionar novo arquivo de log na pasta
2. Executar GET `/api/famepoints`
3. Verificar se processa o novo arquivo
4. Verificar se dados são atualizados

### Cenário 4: Análise Completa
1. Executar GET `/api/famepoints/analysis`
2. Verificar se retorna todos os jogadores
3. Verificar se inclui histórico completo
4. Verificar se inclui campos detalhados

## Troubleshooting

### Problema: "Arquivo já processado" sempre
**Solução:**
```bash
# Deletar arquivo de controle
rm src/data/famepoints/lastProcessed.json
```

### Problema: Dados não atualizam
**Solução:**
1. Verificar se há novo arquivo de log
2. Verificar permissões da pasta
3. Verificar encoding do arquivo

### Problema: Erro de encoding
**Solução:**
1. Verificar se arquivo está em UTF-16LE
2. Verificar se arquivo não está corrompido
3. Verificar logs do console

## Monitoramento

### Headers Úteis para Monitoramento
```javascript
// Adicionar headers para monitoramento
pm.request.headers.add({
    key: 'X-Request-ID',
    value: pm.variables.get('requestId')
});

pm.request.headers.add({
    key: 'User-Agent',
    value: 'PostmanRuntime/7.32.3'
});
```

### Logs de Performance
```javascript
pm.test("Response time is acceptable", function () {
    pm.expect(pm.response.responseTime).to.be.below(5000);
});
``` 