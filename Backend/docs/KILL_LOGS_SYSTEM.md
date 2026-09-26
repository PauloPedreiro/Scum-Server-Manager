# ⚔️ Sistema de Monitoramento de Kill Logs

## 📋 Visão Geral

O Sistema de Monitoramento de Kill Logs monitora automaticamente os logs de `kill_*.log` do SCUM para detectar eventos de morte, incluindo mortes por NPC, PvP kills e suicídios, registrando essas informações no banco de dados e enviando notificações para o Discord com imagens específicas das armas utilizadas.

## 🎯 Funcionalidades

### ✅ Detecção Automática de Eventos
- Monitora logs de `kill_*.log` em tempo real
- Detecta eventos de **Kill** (PvP e NPC)
- Detecta eventos de **Suicídio**
- Processamento incremental: apenas eventos novos
- Controle de duplicatas: sistema baseado em timestamp + steam_id

### 🖼️ Sistema de Imagens
- **Imagens específicas** para cada tipo de arma
- **Mapeamento JSON** para fácil manutenção
- **Auto-descoberta** de novas armas
- **Notificações ricas** com imagens das armas
- **Imagem especial** para eventos de suicídio
- **Fallback automático** para armas sem imagem

### 🗄️ Armazenamento de Dados
- **Histórico completo** de todos os eventos de morte
- **Informações detalhadas**: localização, arma, distância, tipo de evento
- **Integração com banco SSM.db** para consultas e estatísticas

### 💬 Notificações Discord
- Notificações automáticas para canal específico
- Embeds ricos com imagem da arma (thumbnail)
- Informações completas: jogador, killer, arma, distância
- Categorização por cores e emojis
- Imagem especial para suicídios

### 🎮 In-Game Kill Feed (Chat Global)
- Notificações no chat do jogo com frases humorísticas aleatórias
- Fila RCON priorizada para evitar atrasar ações críticas
- Sanitização estrita contra injeção de comandos RCON

## 🔧 Configuração

### Webhook Discord
Adicione o webhook no arquivo `data/webhooks.json`:

```json
{
  "kill_log": "https://discord.com/api/webhooks/..."
}
```

### Pasta de Logs
Configure no `data/config.json`:

```json
{
  "logs": {
    "logs_directory": "C:\\Servers\\scum\\SCUM\\Saved\\SaveFiles\\Logs"
  }
}
```

### In-Game Kill Feed
Configure no `data/config.json`:

```json
{
  "kill_feed": {
    "enabled": true,
    "mode": "chat",
    "chat_type": 2,
    "message_template": "{killer} matou {victim} ({weapon} - {distance}m) | {phrase}",
    "phrases_path": "data/kill_feed_phrases.json",
    "priority": 15
  }
}
```

## 📁 Estrutura de Arquivos

### Mapeamento de Armas e Frases
```
data/
├── imagens/Weapons/
│   ├── mapping.json                  # Mapeamento de armas para imagens
│   ├── AK47.png                      # Imagem do AK47
│   └── ...
└── kill_feed_phrases.json            # Frases humorísticas da comunidade
```

### Arquivo mapping.json
O arquivo `mapping.json` contém o mapeamento entre nomes normalizados de armas e seus arquivos de imagem:

```json
{
  "AK47": "AK47.png",
  "AK74U": "AK74U.png",
  "DT11B": "DT11B.png",
  "M1887": "M1887.png",
  "Improvised_Crossbow": "",
  "NovaArma_Desconhecida": ""
}
```

**Formato:**
- **Chave**: Nome normalizado da arma (sem prefixos/sufixos)
- **Valor**: Nome do arquivo de imagem ou string vazia `""` se não houver imagem

## 🔄 Fluxo de Processamento

### 1. Detecção
- **FileMonitor**: Detecta mudanças em `kill_*.log`
- **Polling**: Verifica arquivos a cada 5 segundos
- **Trigger**: Qualquer mudança no arquivo

### 2. Processamento
- **Cópia para temp**: Evita conflitos com arquivo em uso
- **Parse das linhas**: Extrai timestamp, vítima, killer, arma e localização
- **Normalização**: Remove prefixos (`Weapon_`), sufixos (`_C`, IDs) e tipos `[Melee]`/`[Projectile]`
- **Mapeamento de imagem**: Busca imagem específica da arma no JSON
- **Auto-descoberta**: Se arma não existe no JSON, adiciona com valor vazio
- **Verificação de duplicatas**: Compara com eventos já processados

### 3. Envio
- **Categorização**: Determina categoria e cor do embed
- **Formatação**: Cria embed Discord com informações e imagem
- **Envio**: POST para webhook Discord com anexo da imagem
- **Salvamento**: Atualiza banco de dados

## 🖼️ Sistema de Imagens

### Normalização de Nomes de Armas

O sistema normaliza automaticamente os nomes das armas antes de buscar no mapeamento:

**Exemplos de normalização:**
- `Weapon_AK47_C` → `AK47`
- `Weapon_DT11B_C_2147299856` → `DT11B`
- `AK47 [Projectile]` → `AK47`
- `Weapon_M1887_C` → `M1887`

### Auto-Descoberta de Novas Armas

Quando uma nova arma é detectada:

1. **Normalização**: Nome da arma é normalizado
2. **Verificação**: Sistema verifica se existe no `mapping.json`
3. **Auto-criação**: Se não existe, adiciona automaticamente com valor vazio `""`
4. **Log**: Registra no log que uma nova arma foi descoberta
5. **Salvamento**: Salva o JSON ordenado alfabeticamente

**Exemplo:**
```
Nova arma detectada: "Weapon_NovaArma_C"
→ Normalizado: "NovaArma"
→ Adicionado ao mapping.json: "NovaArma": ""
→ Usuário pode editar manualmente: "NovaArma": "NovaArma.png"
```

### Imagens Especiais

#### Eventos de Suicídio
- **Imagem fixa**: `Suicide.png`
- **Localização**: `data/imagens/Weapons/Suicide.png`
- **Uso**: Todos os eventos de suicídio usam esta imagem automaticamente

### Adicionando Novas Imagens de Armas

#### 1. Adicionar Imagem
- Colocar imagem na pasta `data/imagens/Weapons/`
- Nome do arquivo: `NomeDaArma.png` (ou `.webp`)

#### 2. Atualizar Mapeamento
- Editar arquivo `mapping.json`
- Adicionar entrada: `"NomeNormalizado": "NomeDaArma.png"`

**Exemplo:**
```json
{
  "AK47": "AK47.png",
  "NovaArma": "NovaArma.png"
}
```

#### 3. Reiniciar Sistema (Opcional)
- O sistema carrega o mapping automaticamente na inicialização
- Para novas armas descobertas, não é necessário reiniciar

## 📊 Estrutura do Banco de Dados

### Tabela: `kill_events`
Armazena todos os eventos de morte/kill.

```sql
CREATE TABLE kill_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    event_type TEXT NOT NULL,              -- 'kill' ou 'suicide'
    timestamp TEXT NOT NULL,                -- ISO 8601
    game_time TEXT,                         -- Hora do jogo (ex: "16:07:13")
    
    -- Vítima
    victim_steam_id TEXT,
    victim_player_id INTEGER,
    victim_name TEXT NOT NULL,
    victim_location_x REAL,
    victim_location_y REAL,
    victim_location_z REAL,
    
    -- Killer (null para suicídio)
    killer_steam_id TEXT,
    killer_user_id TEXT,
    killer_profile_name TEXT,
    killer_is_npc BOOLEAN DEFAULT 0,
    killer_location_x REAL,
    killer_location_y REAL,
    killer_location_z REAL,
    killer_has_immortality BOOLEAN DEFAULT 0,
    
    -- Arma e combate
    weapon TEXT,
    weapon_type TEXT,                       -- 'Projectile' ou 'Melee'
    distance REAL,                          -- em metros
    
    -- Contexto
    is_in_game_event BOOLEAN DEFAULT 0,
    log_file TEXT,
    raw_json TEXT,                          -- JSON completo do evento
    discord_sent BOOLEAN DEFAULT 0,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);
```

## 🎨 Formato das Notificações Discord

### PvP Kill
```json
{
  "embeds": [{
    "title": "⚔️ PvP Kill",
    "color": 15158332,
    "description": "Vítima: Player1\nKiller: Player2\nArma: AK47\nDistância: 25.50 m",
    "timestamp": "2025-11-01T20:37:54",
    "thumbnail": {
      "url": "attachment://AK47.png"
    },
    "footer": {
      "text": "SCUM Server Manager"
    }
  }]
}
```

### NPC Kill
```json
{
  "embeds": [{
    "title": "🤖 Morto por NPC - Player1",
    "color": 15105570,
    "description": "Killer: NPC Pro Player\nArma: DT11B\nDistância: 22.92 m",
    "timestamp": "2025-11-01T20:37:54",
    "thumbnail": {
      "url": "attachment://DT11B.png"
    },
    "footer": {
      "text": "SCUM Server Manager"
    }
  }]
}
```

### Suicídio
```json
{
  "embeds": [{
    "title": "💀 Suicídio - Player1",
    "color": 9807270,
    "description": "Vítima: Player1",
    "timestamp": "2025-11-01T20:43:50",
    "thumbnail": {
      "url": "attachment://Suicide.png"
    },
    "footer": {
      "text": "SCUM Server Manager"
    }
  }]
}
```

## 🔍 Cores e Categorias

| Tipo de Evento | Cor | Emoji | Descrição |
|----------------|-----|-------|-----------|
| **PvP Kill** | Vermelho (#e74c3c) | ⚔️ | Morte entre jogadores |
| **NPC Kill** | Laranja (#e67e22) | 🤖 | Morte por NPC |
| **Suicídio** | Cinza (#95a5a6) | 💀 | Suicídio do jogador |

## 📝 Exemplos de Logs

### Kill Log (PvP)
```
2025.11.01-20.37.54: Died: Player1 (76561198065382168), Killer: Player2 (76561198042887008) Weapon: Weapon_AK47_C [Projectile] S:...
KillerLoc : -57264.25, -82747.10, 36356.62 VictimLoc: -59323.78, -83752.15, 36399.42, Distance: 25.50 m
```

### Kill Log (NPC)
```
2025.11.01-20.37.54: Died: Player1 (76561198065382168), Killer: BP_Guard_Lvl_3_C_2146864901 (NPC) Weapon: Weapon_DT11B_C [Projectile] S:...
KillerLoc : -57264.25, -82747.10, 36356.62 VictimLoc: -59323.78, -83752.15, 36399.42, Distance: 22.92 m
```

### Suicide Log
```
2025.11.01-20.43.50: Comitted suicide. User: Player1 (319, 76561198065382168), [Player1]. Location: X=-61563.809 Y=400799.875 Z=146379.031.
```

## 🛠️ Manutenção

### Adicionar Nova Arma Manualmente

1. **Adicionar Imagem**: Colocar `NovaArma.png` em `data/imagens/Weapons/`
2. **Atualizar JSON**: Editar `mapping.json`:
   ```json
   {
     "NovaArma": "NovaArma.png"
   }
   ```
3. **Sistema detecta automaticamente**: Próximo kill com essa arma usará a imagem

### Arma Descoberta Automaticamente

Quando uma nova arma aparece nos logs:

1. **Sistema adiciona automaticamente**: `"NovaArma": ""`
2. **Usuário edita manualmente**: `"NovaArma": "NovaArma.png"`
3. **Próximo kill**: Usa a imagem automaticamente

### Verificar Logs de Descoberta

O sistema registra quando novas armas são descobertas:

```
INFO Nova arma descoberta e adicionada ao mapping: NovaArma
```

## 🔗 Endpoints da API

### Listar Eventos de Kill Recentes
```
GET /api/kill-logs/recent
```

### Estatísticas de Kill Logs
```
GET /api/kill-logs/stats
```

### Listar Eventos com Filtros
```
GET /api/kill-logs/events
```

### Obter Frases do In-Game Kill Feed
```
GET /api/config/kill-feed-phrases
```

### Atualizar Frases do In-Game Kill Feed
```
POST /api/config/kill-feed-phrases
```
Corpo da requisição deve ser um array JSON contendo strings.

Para documentação completa da API, consulte: `docs/endpoints/FRONTEND_KILL_LOGS_API.md`

## 🐛 Troubleshooting

### Problema: Imagens não aparecem
- Verificar se arquivo existe na pasta `Weapons/`
- Verificar mapeamento no `mapping.json`
- Verificar se nome está normalizado corretamente
- Verificar logs de debug

### Problema: Nova arma não aparece no JSON
- Verificar se o sistema está processando logs
- Verificar permissões de escrita no arquivo `mapping.json`
- Verificar logs de erro

### Problema: Notificações não sendo enviadas
- Verificar configuração do webhook no `data/webhooks.json`
- Verificar se o canal Discord aceita webhooks
- Verificar logs de erro

### Problema: Imagem de suicídio não aparece
- Verificar se `Suicide.png` existe em `data/imagens/Weapons/`
- Verificar permissões de leitura do arquivo

## 📚 Arquivos do Sistema

### Core Files
- `core/logs/kill_processor.py` - Processador principal
- `core/logs/log_processor.py` - Integração com sistema de logs
- `core/logs/file_monitor.py` - Monitoramento de arquivos

### Data Files
- `data/SSM.db` - Banco de dados SQLite com eventos processados
- `data/webhooks.json` - Configuração de webhooks
- `data/kill_feed_phrases.json` - Frases do kill feed in-game
- `data/imagens/Weapons/mapping.json` - Mapeamento de armas
- `data/imagens/Weapons/*.png` - Imagens das armas
- `data/imagens/Weapons/Suicide.png` - Imagem para suicídios

## 🚀 Vantagens do Sistema

### ✅ Eficiência
- **Processamento incremental**: Não reprocessa eventos antigos
- **Thread-safe**: Suporta múltiplos processamentos simultâneos
- **Auto-descoberta**: Detecta novas armas automaticamente

### ✅ Manutenibilidade
- **Mapeamento JSON**: Fácil de editar e manter
- **Ordenação automática**: JSON sempre ordenado alfabeticamente
- **Logs detalhados**: Facilita debugging

### ✅ Flexibilidade
- **Suporte a múltiplos formatos**: PNG, WEBP
- **Fallback seguro**: Funciona mesmo sem imagens
- **Extensível**: Fácil adicionar novas funcionalidades

