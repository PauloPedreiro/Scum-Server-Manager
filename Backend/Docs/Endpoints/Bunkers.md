# Sistema de Bunkers - SCUM Server Manager

## Visão Geral

O sistema de bunkers foi completamente reformulado para incluir um banco de dados persistente que controla o status de todos os bunkers do servidor SCUM. O sistema agora é inteligente e mantém histórico de ativações, coordenadas e tempos de ativação.

## Funcionalidades

### ✅ Banco de Dados Persistente
- Armazena informações de todos os bunkers em `src/data/bunkers/bunkers.json`
- Controle de arquivos processados em `src/data/bunkers/lastProcessed.json`
- Evita reprocessamento desnecessário de logs

### ✅ Detecção Inteligente
- Detecta bunkers ativos e bloqueados automaticamente
- Identifica ativações via keycard
- Mantém coordenadas quando disponíveis
- Calcula tempos decorridos desde ativação

### ✅ Formatação Detalhada
- Informações completas de cada bunker
- Tempo decorrido desde ativação
- Coordenadas precisas
- Status de atualização

## Endpoints

### GET `/api/bunkers/status`

**Descrição:** Obtém o status atual de todos os bunkers

**Resposta de Sucesso:**
```json
{
  "success": true,
  "message": "Status dos bunkers recuperado com sucesso.",
  "data": {
    "active": [
      {
        "name": "A1",
        "status": "active",
        "activated": "00h 00m 00s",
        "coordinates": {
          "x": -348529.312,
          "y": -469201.781,
          "z": 4247.645
        },
        "lastUpdate": "2025.07.15-20.16.51",
        "activationTime": "2025.07.15-20.16.51"
      }
    ],
    "locked": [
      {
        "name": "D1",
        "status": "locked",
        "nextActivation": "21h 53m 18s",
        "coordinates": {
          "x": -537889.562,
          "y": 540004.312,
          "z": 81279.648
        },
        "lastUpdate": "2025.07.15-20.16.51"
      }
    ],
    "lastUpdate": "2025.07.15-20.16.51"
  },
  "logFile": "gameplay_2025.07.15.log"
}
```

### POST `/api/bunkers/force-update`

**Descrição:** Força atualização dos bunkers sem enviar webhook

**Resposta de Sucesso:**
```json
{
  "success": true,
  "message": "Status dos bunkers atualizado (sem envio para webhook).",
  "data": {
    "active": [...],
    "locked": [...],
    "lastUpdate": "2025.07.15-20.16.51"
  }
}
```

## Formato do Webhook Discord

O webhook envia informações detalhadas no seguinte formato:

```
🏰 Status dos Bunkers - SCUM Server

Bunkers Ativos:
A1 Bunker
Status: Ativo
Ativado: 00h 00m 00s atrás (02h 15m 30s decorridos)
Coordenadas: X=-348529.312 Y=-469201.781 Z=4247.645

A3 Bunker
Status: Ativo
Ativado: Via Keycard 00h 30m 15s atrás
Coordenadas: X=230229.672 Y=-447157.625 Z=9555.422

Bunkers Bloqueados:
D1 Bunker
Status: Bloqueado
Próxima ativação: 21h 53m 18s (atualizado há 01h 45m 20s)
Coordenadas: X=-537889.562 Y=540004.312 Z=81279.648

C4 Bunker
Status: Bloqueado
Próxima ativação: 21h 53m 18s (atualizado há 01h 45m 20s)
Coordenadas: X=446323.000 Y=263051.188 Z=18552.514
```

## Estrutura do Banco de Dados

### Arquivo: `src/data/bunkers/bunkers.json`
```json
{
  "A1": {
    "name": "A1",
    "status": "active",
    "activated": "00h 00m 00s",
    "coordinates": {
      "x": -348529.312,
      "y": -469201.781,
      "z": 4247.645
    },
    "lastUpdate": "2025.07.15-20.16.51",
    "activationTime": "2025.07.15-20.16.51"
  },
  "D1": {
    "name": "D1",
    "status": "locked",
    "nextActivation": "21h 53m 18s",
    "coordinates": {
      "x": -537889.562,
      "y": 540004.312,
      "z": 81279.648
    },
    "lastUpdate": "2025.07.15-20.16.51"
  }
}
```

### Arquivo: `src/data/bunkers/lastProcessed.json`
```json
{
  "fileName": "gameplay_2025.07.15.log",
  "fileMTimeMs": 1731622611000,
  "processedAt": "2025-07-15T20:16:51.000Z"
}
```

## Padrões de Log Detectados

### Bunkers Ativos
- `A1 Bunker is Active. Activated 00h 00m 00s ago. X=-348529.312 Y=-469201.781 Z=4247.645`
- `A3 Bunker Activated 00h 06m 41s ago`
- `C2 Bunker Activated via Keycard 00h 30m 15s ago`

### Bunkers Bloqueados
- `D1 Bunker is Locked. Locked initially, next Activation in 23h 53m 18s. X=-537889.562 Y=540004.312 Z=81279.648`

## Configuração do Webhook

Para configurar o webhook do Discord, adicione no arquivo `src/data/webhooks.json`:

```json
{
  "bunkers": "https://discord.com/api/webhooks/SEU_WEBHOOK_URL"
}
```

## Melhorias Implementadas

1. **Banco de Dados Persistente**: Informações são salvas e mantidas entre reinicializações
2. **Controle de Processamento**: Evita reprocessar logs já analisados
3. **Detecção Inteligente**: Identifica novos bunkers automaticamente
4. **Formatação Detalhada**: Informações completas no Discord
5. **Cálculo de Tempo**: Mostra tempo decorrido desde ativação
6. **Suporte a Keycard**: Detecta ativações via keycard
7. **Coordenadas Precisas**: Mantém localização exata dos bunkers

## Exemplo de Uso

```bash
# Obter status atual
curl http://localhost:3000/api/bunkers/status

# Forçar atualização
curl -X POST http://localhost:3000/api/bunkers/force-update
```

O sistema agora é muito mais robusto e fornece informações detalhadas sobre o status dos bunkers do servidor SCUM.

## Notas Importantes

1. **Arquivo de Log:** A API lê o arquivo `gameplay_*.log` mais recente
2. **Coordenadas:** Podem ser null para bunkers ativados simples (sem coordenadas no log)
3. **Webhook:** Só funciona se configurado em `src/data/webhooks.json`
4. **Encoding:** Suporte nativo a UTF-16LE do SCUM
5. **Performance:** Processamento otimizado com limpeza automática de arquivos temporários

## Troubleshooting

### Problema: "Nenhum arquivo de log gameplay encontrado"
**Solução:** Verificar se o caminho `SCUM_LOG_PATH` no `.env` está correto

### Problema: Bunkers não aparecem na resposta
**Solução:** Verificar se há logs de bunkers no arquivo `gameplay_*.log` mais recente

### Problema: Webhook não funciona
**Solução:** Verificar se o webhook está configurado em `src/data/webhooks.json`

---

**Desenvolvido para SCUM Server Manager v2.0**  
**Compatível com logs do SCUM v1.0+** 