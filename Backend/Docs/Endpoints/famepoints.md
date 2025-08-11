# Endpoint Famepoints

## Descrição
Endpoint para processar e gerenciar dados de famepoints (pontos de fama) dos jogadores do servidor SCUM.

## Base URL
```
http://localhost:3000/api/famepoints
```

## Endpoints Disponíveis

### 1. GET /api/famepoints
Processa o arquivo de log mais recente de famepoints e retorna os dados dos jogadores.

#### Parâmetros
- Nenhum parâmetro obrigatório

#### Resposta de Sucesso (Novo Log Processado)
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

#### Resposta (Arquivo Já Processado)
```json
{
    "success": true,
    "message": "Arquivo já processado",
    "data": []
}
```

#### Resposta de Erro
```json
{
    "success": false,
    "message": "Nenhum arquivo de log de famepoints encontrado",
    "data": []
}
```

### 2. GET /api/famepoints/analysis
Processa todos os logs de famepoints disponíveis e retorna uma análise completa.

#### Parâmetros
- Nenhum parâmetro obrigatório

#### Resposta de Sucesso
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

### 3. GET /api/famepoints?all=true
Processa todos os logs de famepoints e retorna análise completa (mesmo comportamento do /analysis).

## Como Funciona

### Processamento de Logs
1. **Busca o arquivo mais recente**: Procura por arquivos que começam com `famepoints_` e terminam com `.log`
2. **Verifica se já foi processado**: Evita reprocessamento do mesmo arquivo
3. **Copia para pasta temporária**: Para evitar conflitos de encoding
4. **Lê com encoding UTF-16LE**: Formato padrão dos logs do SCUM
5. **Extrai informações**: Usa regex para capturar dados dos jogadores
6. **Salva no banco local**: Arquivo JSON em `src/data/famepoints/famepoints.json`
7. **Limpa arquivo temporário**: Remove o arquivo copiado

### Campos Capturados
O sistema captura automaticamente todos os campos encontrados nos logs, incluindo:
- `DistanceTraveledOnFoot`
- `OnlineFlagOwnersAwardAwarded`
- `BaseFameInflux`
- `DistanceTraveledWhileMounted`
- `ItemLooted`
- `PuppetKill`
- `RecoveredFromInfection`
- `ItemCrafted`
- `MeleeKill`
- `SkillLeveledUp`
- `MinigameCompleted`
- `LockPicked`
- `BandageApplied`
- `AnimalKill`
- `BlueprintBuilt`
- `BaseElementBuilt`
- `WeedsPlucked`

### Atualização de Dados
- **Sempre atualiza**: O sistema sempre sobrescreve com o valor mais recente do log
- **Independente de aumento/diminuição**: Atualiza mesmo se o jogador perdeu pontos
- **Baseado no timestamp**: Usa o valor mais recente encontrado no log

## Estrutura de Arquivos

### Arquivos de Dados
```
src/data/famepoints/
├── famepoints.json          # Dados dos jogadores
└── lastProcessed.json       # Controle de arquivos processados
```

### Arquivos Temporários
```
src/data/temp/
└── famepoints_*.log         # Cópias temporárias dos logs
```

## Variáveis de Ambiente

### Obrigatórias
- `SCUM_LOG_PATH`: Caminho para a pasta de logs do SCUM
- `SCUM_LOG_CACHE_PATH`: Caminho para cache de logs

### Exemplo
```env
SCUM_LOG_PATH=Z:\\Scum\\SCUM\\Saved\\SaveFiles\\Logs
SCUM_LOG_CACHE_PATH=src/data/logs/cache
```

## Logs do Sistema

### Mensagens de Debug
```
[FAMEPOINTS] Arquivo mais recente: famepoints_20250714200120.log
[FAMEPOINTS] Conteúdo do log lido: 4268 caracteres
[FAMEPOINTS] Jogador encontrado: Aqu1n0 (76561197995901898) - Total Fame: 588.845947
[FAMEPOINTS] Total de jogadores processados: 6
```

## Casos de Uso

### 1. Monitoramento Regular
```bash
# Verificar dados mais recentes
curl -X GET "http://localhost:3000/api/famepoints"
```

### 2. Análise Completa
```bash
# Análise de todos os logs
curl -X GET "http://localhost:3000/api/famepoints/analysis"
```

### 3. Forçar Reprocessamento
```bash
# Deletar controle de processamento
rm src/data/famepoints/lastProcessed.json

# Chamar endpoint novamente
curl -X GET "http://localhost:3000/api/famepoints"
```

## Tratamento de Erros

### Erros Comuns
1. **Arquivo não encontrado**: Retorna mensagem de erro específica
2. **Erro de encoding**: Tenta UTF-16LE, depois UTF-8
3. **Erro de permissão**: Log detalhado no console
4. **Arquivo corrompido**: Salta para o próximo arquivo

### Logs de Erro
```
[FAMEPOINTS] Erro ao copiar log: ENOENT: no such file or directory
[FAMEPOINTS] Erro ao ler log: ENOENT: no such file or directory
[FAMEPOINTS] Erro ao salvar dados de famepoints: EACCES: permission denied
```

## Integração com Webhooks

O endpoint pode ser integrado com webhooks do Discord para notificações automáticas quando novos dados são processados.

## Performance

- **Processamento rápido**: Apenas arquivos novos são processados
- **Baixo uso de memória**: Arquivos temporários são limpos automaticamente
- **Escalável**: Suporta múltiplos logs sem degradação de performance

## Segurança

- **Validação de entrada**: Regex para extrair apenas dados válidos
- **Sanitização**: Remove caracteres especiais perigosos
- **Isolamento**: Processamento em pasta temporária separada 