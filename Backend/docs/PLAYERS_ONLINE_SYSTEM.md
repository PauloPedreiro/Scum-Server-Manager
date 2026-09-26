# Sistema de Monitoramento de Jogadores Online (Atualizado)

## 📋 Visão Geral

O sistema de monitoramento de jogadores online utiliza logs de gameplay do SCUM para detectar jogadores ativos em tempo real, oferecendo uma alternativa mais precisa que apenas analisar eventos de login/logout.

## 🏗️ Arquitetura

### Componentes Principais

- **`OnlinePlayersMonitor`**: Monitor principal de jogadores online (baseado apenas em `login_*.log`)
- **`DatabaseManager`**: Gerenciamento da tabela `players_online`
- **`TempFileManager`**: Sistema de arquivos temporários
- **`SteamAPI`**: Integração com Steam API

### Fluxo de Funcionamento

```
1. A cada 30s o monitor seleciona o arquivo `login_*.log` mais recente
   ↓
2. Copia o arquivo para `data/temp` e lê todo o conteúdo (UTF-16LE → UTF-8 fallback)
   ↓
3. Reconstrói a lista: último `login` sem `logout` posterior por `steam_id`
   ↓
4. Atualiza a tabela `players_online` e marca offline quem saiu
   ↓
5. Se houver mudança (entrou/saiu), envia notificação ao Discord imediatamente
```

## 📊 Estrutura de Dados

### Tabela `players_online`

```sql
CREATE TABLE players_online (
    steam_id TEXT PRIMARY KEY,
    player_name TEXT NOT NULL,
    player_id INTEGER NOT NULL,
    last_activity DATETIME NOT NULL,
    coordinates_x REAL NOT NULL,
    coordinates_y REAL NOT NULL,
    coordinates_z REAL NOT NULL,
    activity_types TEXT,           -- JSON array de tipos de atividade
    total_activities INTEGER DEFAULT 0,
    status TEXT DEFAULT 'online',
    last_updated DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (steam_id) REFERENCES players (steam_id)
);
```

### Tipos de Atividade Detectados

**Logs de Login/Logout:**
- **login**: Jogador entrou no servidor
- **logout**: Jogador saiu do servidor

**Logs de Gameplay:**
- **minigame**: Lockpicking, hacking, etc.
- **kill**: Eliminações de jogadores
- **damage**: Dano recebido/infligido
- **inventory**: Manipulação de inventário
- **vehicle**: Uso de veículos
- **building**: Construção/destruição

### Fonte Única de Verdade

O sistema usa exclusivamente o arquivo `login_*.log` mais recente como referência:

- Novo `login_*.log` detectado → estado é resetado e só volta a contar quem aparecer neste arquivo
- Sem dependência de `gameplay_*.log`

## ⚙️ Configuração

### `config.json`

```json
{
  "logs": {
    "gameplay_logs_path": "\\\\192.168.100.31\\Servers\\Scum\\SCUM\\Saved\\SaveFiles\\Logs",
    "monitor_enabled": true,
    "real_time_processing": true,
    "file_check_interval": 5
  }
}
```

### `webhooks.json`

```json
{
  "players_online": "https://discord.com/api/webhooks/YOUR_WEBHOOK_URL"
}
```

### Parâmetros de Monitoramento

- **Intervalo de verificação**: 30 segundos
- **Arquivo fonte**: `login_*.log` mais recente
- **Cópia temporária**: leitura sempre via `data/temp` para evitar lock

## 🔌 API Endpoints

### `GET /api/players/online`

Obter jogadores online atuais.

**Parâmetros:**
- `force_check` (opcional): `true` para forçar verificação imediata

**Resposta:**
```json
{
  "success": true,
  "data": {
    "players": {
      "76561198042887008": {
        "steam_id": "76561198042887008",
        "player_name": "Mantones",
        "player_id": 230,
        "last_activity": "2025-10-18T04:32:30",
        "last_coordinates": {"x": 495110.25, "y": -191789.73, "z": 660.887},
        "activity_types": ["minigame"],
        "total_activities": 8
      }
    },
    "count": 1,
    "last_check": "2025-10-18T04:32:30",
    "status": "monitoring"
  }
}
```

### `GET /api/players/online/list`

Obter lista detalhada com informações do Steam.

**Resposta:**
```json
{
  "success": true,
  "data": {
    "players": [
      {
        "steam_id": "76561198042887008",
        "player_name": "Mantones",
        "player_id": 230,
        "last_activity": "2025-10-18T04:32:30",
        "coordinates": {"x": 495110.25, "y": -191789.73, "z": 660.887},
        "activity_types": ["minigame"],
        "total_activities": 8,
        "steam_info": {
          "persona_name": "Mantones",
          "avatar_url": "https://avatars.steamstatic.com/...",
          "country": "🇧🇷 Brazil"
        }
      }
    ],
    "count": 1,
    "timestamp": "2025-10-18T04:32:30"
  }
}
```

### `GET /api/players/online/stats`

Obter estatísticas de jogadores online.

**Resposta:**
```json
{
  "success": true,
  "data": {
    "online_count": 5,
    "offline_count": 12,
    "total_tracked": 17,
    "last_update": "2025-10-18T04:32:30"
  }
}
```

### `POST /api/players/online/check`

Forçar verificação imediata de jogadores online.

**Resposta:**
```json
{
  "success": true,
  "message": "Verificação forçada concluída",
  "data": {
    "players": {...},
    "count": 5,
    "last_check": "2025-10-18T04:32:30",
    "status": "monitoring"
  }
}
```

## 📢 Notificações Discord

### Formato da Notificação

```json
{
  "embeds": [{
    "title": "👥 SCUM Server - Player Status",
    "color": 65280,
    "fields": [
      {
        "name": "📊 Statistics",
        "value": "• **Online Players:** 4\n• **Total Tracked:** 4",
        "inline": false
      },
      {
        "name": "🟢 Online Players (4):",
        "value": "• 🆕 **NEW Véio** - Oh\n• 🆕 **NEW Mantones** - Oh\n• 🆕 **NEW Ice** - Oh\n• 🆕 **NEW Stnyx** - Oh",
        "inline": false
      }
    ],
    "timestamp": "2025-10-18T01:20:41.000Z",
    "footer": {
      "text": "SCUM Server Manager • Hoje às 01:20"
    }
  }]
}
```

### Quando as Notificações são Enviadas

- **Mudanças no status**: Sempre que a contagem mudar (entrou/saiu)
- **Zero → Maior que zero**: notificação imediata
- **Maior que zero → Zero**: notificação imediata

## 🔧 Vantagens do Sistema

### ✅ Precisão
- Dados diretos do servidor SCUM
- Baseado em atividades reais dos jogadores
- Não depende apenas de eventos de login/logout

### ✅ Tempo Real
- Verificação a cada 60 segundos
- Detecção imediata de mudanças
- Atividades constantes nos logs de gameplay

### ✅ Detalhes
- Coordenadas atuais dos jogadores
- Tipos de atividade realizadas
- Informações do Steam API
- Histórico de atividades

### ✅ Confiabilidade
- Sistema de arquivos temporários
- Múltiplas fontes de dados
- Tratamento de erros robusto

## 🚀 Uso Prático

### Para Administradores
- Monitorar jogadores ativos em tempo real
- Detectar padrões de atividade
- Notificações automáticas de mudanças

### Para Desenvolvedores
- API completa para integração
- Dados estruturados em JSON
- Endpoints RESTful padronizados

### Para Análise
- Dados de coordenadas para mapas
- Padrões de atividade dos jogadores
- Estatísticas de uso do servidor

## 🔍 Exemplo de Log de Gameplay

```
2025.10.18-04.26.50: [LogMinigame] [LockpickingMinigame_C] User: Mantones (230, 76561198042887008). Success: Yes. Elapsed time: 4.00. Failed attempts: 0. Target object: BPLockpick_Weapon_Locker_Police_C(ID: N/A). Lock type: VeryEasy. User owner: N/A. Location: X=494263.219 Y=-191576.953 Z=238.119
```

### Dados Extraídos
- **Timestamp**: 2025-10-18 04:26:50
- **Player Name**: Mantones
- **Player ID**: 230
- **Steam ID**: 76561198042887008
- **Activity**: minigame (lockpicking)
- **Coordinates**: X=494263.219, Y=-191576.953, Z=238.119

## 📝 Logs e Debugging

### Mensagens de Log
- `OK`: Operações bem-sucedidas
- `AVISO`: Situações que requerem atenção
- `ERRO`: Falhas que precisam ser investigadas

### Exemplo de Log
```
OK GameplayLogParser inicializado
OK Arquivo de gameplay mais recente: gameplay_20251018040030.log
OK Processando 20 linhas do arquivo gameplay
OK Atividade encontrada: minigame - Mantones
OK Total de atividades extraídas: 8
OK Jogadores com atividade recente: 3
OK Verificação concluída: 3 jogadores online
OK Notificação de status enviada: 3 jogadores online
```

## 🔧 Configuração Avançada

### Personalização de Timeout
```python
# No OnlinePlayersMonitor
self.activity_timeout_minutes = 45  # 45 minutos sem atividade = offline
self.check_interval_seconds = 30    # Verificar a cada 30 segundos
```

### Filtros de Atividade
```python
# No GameplayLogParser - adicionar novos tipos
self.activity_patterns['custom'] = re.compile(r'\[LogCustom\]...')
```

### Configuração de Notificações
```python
# Desabilitar notificações específicas
self.send_notifications = False
```

## 🎯 Casos de Uso

1. **Dashboard de Administração**: Mostrar jogadores online em tempo real
2. **Análise de Tráfego**: Padrões de uso do servidor
3. **Moderação**: Detectar jogadores problemáticos
4. **Estatísticas**: Relatórios de atividade
5. **Integração**: APIs para outros sistemas
