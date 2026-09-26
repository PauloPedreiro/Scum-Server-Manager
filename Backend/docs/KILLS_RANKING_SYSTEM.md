# ⚔️ Sistema de Rankings de Kills

## 📋 Visão Geral

O Sistema de Rankings de Kills gera e envia automaticamente dois rankings relacionados a kills para o Discord:
1. **TOP KILLERS**: Jogadores com mais kills PvP
2. **SHAME RANK**: Jogadores com mais mortes por NPC

## 🎯 Funcionalidades

### ✅ Rankings Automáticos
- **Envio diário agendado**: Executa automaticamente no horário configurado (padrão: 00:00)
- **Envio na inicialização**: Opção de enviar rankings imediatamente ao iniciar o backend
- **Envio manual**: Endpoint API para forçar envio imediato

### 📊 Dados dos Rankings

#### TOP KILLERS
- **Fonte**: Tabela `rankings` do banco `SSM.db`
- **Colunas utilizadas**:
  - `kills`: Total de kills PvP
  - `deaths`: Total de mortes
  - `player_name`: Nome do jogador
- **Ordenação**: Por `kills DESC` (mais kills primeiro)
- **Filtro**: Apenas jogadores com `kills > 0`

#### SHAME RANK (Deaths by NPC)
- **Fonte**: Tabela `kill_events` do banco `SSM.db`
- **Query**: `WHERE event_type='kill' AND killer_user_id='NPC'`
- **Ordenação**: Por total de mortes por NPC DESC
- **Agrupamento**: Por `victim_steam_id` e `victim_name`

### 🎨 Formato dos Embeds Discord

#### TOP KILLERS
```
⚔️ TOP KILLERS ⚔️

Rank | Player            | Kills | Deaths
----------------------------------------
1    | popovick          |    11 |      4
2    | Over              |     4 |      0
3    | Ragnar            |     4 |      1
```

#### SHAME RANK
```
💀 SHAME RANK | Deaths by NPC 💀

Rank   | Player             | 💀
---------------------------------
1      | Cleyton            |  6
2      | alvesandre037      |  4
3      | Sulivan            |  3
```

## 🔧 Configuração

### Webhook Discord
Adicione o webhook no arquivo `data/webhooks.json`:

```json
{
  "top20_kills": "https://discord.com/api/webhooks/..."
}
```

### Configuração do Serviço
Configure no `data/config.json`:

```json
{
  "kills_ranking": {
    "enabled": true,
    "schedule_time": "00:00",
    "top_n": 20,
    "send_on_startup": true,
    "description": "Sistema de ranking diário de kills - envia Top Killers e Shame Rank (deaths by NPC) para Discord"
  }
}
```

## 🚀 API Endpoints

### `POST /api/rankings/kills/send`

Envia os rankings de kills para Discord manualmente.

**Resposta de Sucesso (200):**
```json
{
  "success": true,
  "message": "Rankings enviados com sucesso (2 rankings)",
  "sent": 2
}
```

### `GET /api/rankings/kills/status`

Obtém o status e configuração atual do serviço.

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
        "sent": 2,
        "failed": 0,
        "total_rankings": 2
      }
    },
    "next_scheduled": "00:00 (diariamente)"
  },
  "timestamp": 1760629995.398204
}
```

