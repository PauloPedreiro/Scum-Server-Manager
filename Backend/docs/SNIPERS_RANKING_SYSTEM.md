# 🎯 Sistema de Rankings de Snipers

## 📋 Visão Geral

O Sistema de Rankings de Snipers gera e envia automaticamente rankings dos jogadores com os tiros de maior distância para o Discord. O sistema busca dados da tabela `rankings` no banco `SSM.db` e envia um ranking formatado com os Top 20 snipers.

## 🎯 Funcionalidades

### ✅ Ranking Automático
- **Envio diário agendado**: Executa automaticamente no horário configurado (padrão: 00:00)
- **Envio na inicialização**: Opção de enviar ranking imediatamente ao iniciar o backend
- **Envio manual**: Endpoint API para forçar envio imediato

### 📊 Dados do Ranking
- **Fonte**: Tabela `rankings` do banco `SSM.db`
- **Colunas utilizadas**:
  - `longest_shot_distance`: Maior distância de tiro em metros
  - `longest_shot_weapon`: Nome da arma usada no tiro mais longo
  - `player_name`: Nome do jogador
- **Ordenação**: Por `longest_shot_distance DESC` (maior distância primeiro)
- **Filtro**: Apenas jogadores com `longest_shot_distance > 0`

### 🎨 Formato do Embed Discord
- **Título**: 🎯 TOP SNIPERS 🎯
- **Tabela formatada**:
  ```
  🏆 | Player        | Weapon      | Distance
  -----------------------------------------
  1   | Ragnar       | M82A1       | 339.35m
  2   | popovick     | M1_Garand   | 273.02m
  ```
- **GIF no rodapé**: Imagem animada de sniper (`data/imagens/SCUM GIF/Sniper.gif`)
- **Cor**: Verde (0x2ecc71)

### 🔧 Limpeza de Nomes de Armas
O sistema remove automaticamente:
- Prefixo `Weapon_` (ex: `Weapon_M82A1_C` → `M82A1`)
- Sufixo `_C` e códigos numéricos (ex: `M82A1_C_21452063` → `M82A1`)

## 🔧 Configuração

### Webhook Discord
Adicione o webhook no arquivo `data/webhooks.json`:

```json
{
  "top20_snipers": "https://discord.com/api/webhooks/..."
}
```

### Configuração do Serviço
Configure no `data/config.json`:

```json
{
  "snipers_ranking": {
    "enabled": true,
    "schedule_time": "00:00",
    "top_n": 20,
    "send_on_startup": true,
    "description": "Sistema de ranking diário de snipers - envia Top 20 snipers (maior distância de tiro) para Discord"
  }
}
```

**Parâmetros:**
- `enabled`: Ativa/desativa o serviço (padrão: `true`)
- `schedule_time`: Horário do envio diário no formato `HH:MM` (padrão: `"00:00"`)
- `top_n`: Número de jogadores no ranking (padrão: `20`)
- `send_on_startup`: Enviar ranking ao iniciar o backend (padrão: `true`)

## 🚀 API Endpoints

### `POST /api/rankings/snipers/send`

Envia o ranking de snipers para Discord manualmente.

**Request:**
```http
POST /api/rankings/snipers/send
Content-Type: application/json
```

**Resposta de Sucesso (200):**
```json
{
  "success": true,
  "message": "Ranking enviado com sucesso",
  "sent": 1
}
```

**Resposta de Erro (400/500):**
```json
{
  "success": false,
  "message": "Erro ao enviar ranking: [detalhes do erro]"
}
```

**Resposta quando serviço não inicializado (500):**
```json
{
  "success": false,
  "error": "SnipersRankingService não inicializado"
}
```

### `GET /api/rankings/snipers/status`

Obtém o status e configuração atual do serviço.

**Request:**
```http
GET /api/rankings/snipers/status
```

**Resposta de Sucesso (200):**
```json
{
  "success": true,
  "data": {
    "enabled": true,
    "webhook_configured": true,
    "top_n": 20,
    "last_send": {
      "timestamp": "2025-11-24T00:32:00",
      "status": "success",
      "details": {
        "sent": 1,
        "failed": 0,
        "total_rankings": 1
      }
    },
    "next_scheduled": "00:00 (diariamente)"
  },
  "timestamp": 1760629995.398204
}
```

**Resposta quando serviço não inicializado (500):**
```json
{
  "success": false,
  "error": "SnipersRankingService não inicializado"
}
```

## 📁 Estrutura de Arquivos

```
core/survival/
└── snipers_ranking_service.py    # Serviço principal

data/
├── config.json                    # Configuração do serviço
├── webhooks.json                  # Webhook Discord
└── imagens/
    └── SCUM GIF/
        └── Sniper.gif             # GIF para rodapé do embed
```

## 🔄 Fluxo de Funcionamento

1. **Inicialização**:
   - Serviço é inicializado no `main.py`
   - Carrega configuração do `config.json`
   - Carrega webhook do `webhooks.json`
   - Agenda envio diário no horário configurado
   - Se `send_on_startup: true`, envia ranking imediatamente

2. **Envio Agendado**:
   - Scheduler executa no horário configurado (padrão: 00:00)
   - Busca dados da tabela `rankings`
   - Formata ranking em tabela
   - Limpa nomes de armas
   - Envia para Discord com GIF anexado

3. **Envio Manual**:
   - Endpoint `POST /api/rankings/snipers/send` pode ser chamado a qualquer momento
   - Processa e envia ranking imediatamente

## 📊 Exemplo de Embed Discord

```
🎯 TOP SNIPERS 🎯

🏆 | Player        | Weapon      | Distance
-----------------------------------------
1   | Ragnar       | M82A1       | 339.35m
2   | popovick     | M1_Garand   | 273.02m
3   | darkzinho    | MP5_SD      |   7.10m
4   | luc_sc       | MP5_SD      |   6.50m
5   | MarioBrother | 590A11      |   3.72m

[GIF do sniper aparece aqui]

Top 20 | Atualizado • Hoje às 00:32
```

## 🔍 Logs do Sistema

O sistema gera logs detalhados:

```
INFO SnipersRankingService inicializado
INFO SnipersRankingService iniciado automaticamente (agendado para 00:00)
INFO Enviando ranking de snipers na inicialização...
DEBUG Top Snipers: 11 jogadores encontrados
DEBUG Adicionando GIF como anexo: Sniper.gif
✅ Top Snipers enviado com sucesso
```

## 🐛 Troubleshooting

### Problema: Ranking não é enviado
- Verificar se `enabled: true` no `config.json`
- Verificar se webhook está configurado em `webhooks.json`
- Verificar logs do backend para erros

### Problema: GIF não aparece
- Verificar se arquivo existe em `data/imagens/SCUM GIF/Sniper.gif`
- Verificar permissões de leitura do arquivo
- Verificar logs para erros de anexo

### Problema: Nomes de armas não estão limpos
- Verificar se a lógica de limpeza está funcionando
- Verificar formato dos nomes no banco de dados

## 📝 Notas Técnicas

- O sistema usa `multipart/form-data` quando há GIF anexado
- O sistema usa `application/json` quando não há anexos
- O tamanho da tabela foi otimizado para evitar quebras de linha no Discord (38 caracteres)
- O serviço roda em thread separada para não bloquear o backend principal

