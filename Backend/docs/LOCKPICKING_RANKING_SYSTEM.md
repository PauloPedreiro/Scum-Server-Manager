# 🔓 Sistema de Rankings de Lockpicking

## 📋 Visão Geral

O Sistema de Rankings de Lockpicking gera e envia automaticamente rankings dos jogadores com melhor desempenho em lockpicking, separados por tipo de fechadura, para o Discord.

## 🎯 Funcionalidades

### ✅ Rankings Automáticos por Tipo
- **6 rankings separados**: Um para cada tipo de fechadura
- **Envio diário agendado**: Executa automaticamente no horário configurado (padrão: 00:00)
- **Envio na inicialização**: Opção de enviar rankings imediatamente ao iniciar o backend
- **Envio manual**: Endpoint API para forçar envio imediato

### 📊 Tipos de Fechaduras

1. **Basic** - Fechadura básica
2. **Medium** - Fechadura média
3. **Advanced** - Fechadura avançada
4. **VeryEasy** - Fechadura muito fácil
5. **Diallock** - Fechadura de disco
6. **Other** - Outros tipos

### 📊 Dados do Ranking
- **Fonte**: Tabela `minigame_events` do banco `SSM.db`
- **Filtros**:
  - `minigame_type = 'LockpickingMinigame_C'`
  - `lock_type` específico para cada ranking
  - Mínimo de tentativas configurável (padrão: 10)
- **Ordenação**: Por total de sucessos DESC, depois por nome ASC
- **Cálculo de taxa**: `(sucessos / total_tentativas) * 100`

### 🎨 Formato do Embed Discord
- **Título**: Nome do tipo de fechadura com ícone
- **Tabela formatada**:
  ```
  Rank | Player            | Sucess | Fails |      (%)
  -----------------------------------------------------
  1    | popovick          |     13 |     0 | 100.00%
  2    | Reav              |     11 |     3 |  78.57%
  3    | Ozyr              |      5 |    10 |  33.33%
  ```
- **Ícone**: Imagem específica para cada tipo (usando `author.icon_url`)
- **Cores**: Diferentes para cada tipo de fechadura

## 🔧 Configuração

### Webhook Discord
Adicione o webhook no arquivo `data/webhooks.json`:

```json
{
  "top20_lockpicking": "https://discord.com/api/webhooks/..."
}
```

### Configuração do Serviço
Configure no `data/config.json`:

```json
{
  "lockpicking_ranking": {
    "enabled": true,
    "schedule_time": "00:00",
    "min_attempts": 10,
    "top_n": 20,
    "send_on_startup": true,
    "description": "Sistema de ranking diário de lockpicking por tipo - executa uma vez por dia no horário configurado e envia top 20 por tipo de fechadura"
  }
}
```

## 🚀 API Endpoints

### `POST /api/rankings/lockpicking/send`

Envia os rankings de lockpicking para Discord manualmente.

**Resposta de Sucesso (200):**
```json
{
  "success": true,
  "message": "Rankings enviados com sucesso (6 tipos)",
  "sent": 6
}
```

### `GET /api/rankings/lockpicking/status`

Obtém o status e configuração atual do serviço.

**Resposta de Sucesso (200):**
```json
{
  "success": true,
  "data": {
    "enabled": true,
    "webhook_configured": true,
    "min_attempts": 10,
    "top_n": 20,
    "last_send": {
      "timestamp": "2025-11-24T00:32:00",
      "status": "success",
      "details": {
        "sent": 6,
        "failed": 0,
        "total_rankings": 6
      }
    },
    "next_scheduled": "00:00 (diariamente)"
  },
  "timestamp": 1760629995.398204
}
```

