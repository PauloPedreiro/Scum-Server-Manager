# Sistema de Monitoramento de Destruição de Veículos

## Visão Geral

O Sistema de Monitoramento de Destruição de Veículos monitora automaticamente os logs de `vehicle_destruction_*.log` do SCUM para detectar quando veículos são destruídos, inativos ou desaparecem, registrando essas informações no banco de dados e enviando notificações para o Discord com imagens específicas dos veículos.

## Funcionalidades

### 🚗 Detecção Automática de Eventos de Veículos
- Monitora logs de `vehicle_destruction_*.log` em tempo real
- Detecta eventos de `Destroyed` (veículo destruído)
- Detecta eventos de `VehicleInactiveTimerReached` (veículo inativo)
- Detecta eventos de `Disappeared` (veículo desaparecido)

### 🖼️ Sistema de Imagens
- **Imagens específicas** para cada tipo de veículo
- **Mapeamento JSON** para fácil manutenção
- **Notificações ricas** com imagens dos veículos
- **Fallback automático** para veículos sem imagem

### 🗄️ Armazenamento de Dados
- **Histórico completo** de todos os eventos de destruição
- **Status atual** de cada veículo
- **Informações detalhadas**: localização, proprietário, tipo de evento
- **Integração com banco SCUM.db** para dados adicionais

### 💬 Notificações Discord
- Notificações automáticas para canal específico
- Embeds ricos com imagem do veículo
- Informações completas: jogador, localização, tipo de evento
- Categorização por cores e emojis

## Estrutura do Banco de Dados

### Tabela: `vehicle_destruction_events`
Armazena todos os eventos de destruição de veículos.

```sql
CREATE TABLE vehicle_destruction_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    vehicle_id INTEGER NOT NULL,              -- ID do veículo
    vehicle_name TEXT NOT NULL,               -- Nome do veículo
    owner_steam_id TEXT,                      -- Steam ID do proprietário
    owner_id INTEGER,                         -- ID do proprietário
    owner_name TEXT,                        -- Nome do proprietário
    event_type TEXT NOT NULL,                 -- Tipo do evento
    location_x REAL,                         -- Coordenada X
    location_y REAL,                         -- Coordenada Y
    location_z REAL,                         -- Coordenada Z
    timestamp DATETIME NOT NULL,             -- Data/hora do evento
    discord_sent BOOLEAN DEFAULT 0           -- Notificação enviada
);
```

### Tabela: `vehicle_current_ownership`
Atualiza status dos veículos quando destruídos, inativos ou desaparecem.

**Relação com `vehicle_destruction_events`:**
- `vehicle_destruction_events.vehicle_id` corresponde a `vehicle_current_ownership.vehicle_entity_id`
- Quando um evento de destruição é processado, o status é atualizado nesta tabela

```sql
CREATE TABLE vehicle_current_ownership (
    entity_id INTEGER PRIMARY KEY,           -- ID do container/recipiente
    vehicle_entity_id INTEGER,               -- ID do veículo (liga com vehicle_destruction_events.vehicle_id)
    steam_id TEXT NOT NULL,                  -- Steam ID do proprietário atual
    player_id INTEGER,                       -- ID do jogador atual
    player_name TEXT NOT NULL,               -- Nome do jogador atual
    location_x REAL,                         -- Coordenada X atual
    location_y REAL,                         -- Coordenada Y atual
    location_z REAL,                         -- Coordenada Z atual
    last_ownership_change DATETIME NOT NULL, -- Última mudança de propriedade
    container_class TEXT,                    -- Classe do container
    vehicle_class TEXT,                      -- Classe do veículo
    vehicle_asset_id TEXT,                   -- Asset ID do veículo
    is_vehicle_functional INTEGER,           -- Veículo funcional (0/1)
    status INTEGER DEFAULT 0,               -- 0: Ativo, 1: Inativo, 2: Desaparecido, 3: Destruído
    notification_sent BOOLEAN DEFAULT 0,     -- Notificação enviada
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

## Sistema de Imagens

### Estrutura de Arquivos
```
data/imagens/carros/vehicle-log/
├── mapping.json                    # Mapeamento de veículos para imagens
├── Kinglet_Duster_ES.png          # Imagem do Kinglet Duster
├── Laika_ES.png                   # Imagem do Laika
├── WolfsWagen_ES.png              # Imagem do WolfsWagen
├── Dirtbike_ES.png                # Imagem do Dirtbike
├── Rager_ES.png                   # Imagem do Rager
├── Tractor_ES.png                 # Imagem do Tractor
├── Cruiser_ES.png                 # Imagem do Cruiser
├── CityBike_ES.png                # Imagem do CityBike
├── MountainBike_ES.png            # Imagem do MountainBike
├── Barba_ES.png                   # Imagem do Barba
├── BigRaft_ES.png                 # Imagem do BigRaft
├── SmallRaft_ES.png               # Imagem do SmallRaft
├── SUP_ES.png                     # Imagem do SUP
├── RIS_ES.png                     # Imagem do RIS
└── Kinglet_Mariner_ES.png         # Imagem do Kinglet Mariner
```

### Arquivo de Mapeamento JSON
```json
{
  "Kinglet_Duster": "Kinglet_Duster_ES.png",
  "Laika": "Laika_ES.png",
  "WolfsWagen": "WolfsWagen_ES.png",
  "Dirtbike": "Dirtbike_ES.png",
  "Rager": "Rager_ES.png",
  "Tractor": "Tractor_ES.png",
  "Cruiser": "Cruiser_ES.png",
  "CityBike": "CityBike_ES.png",
  "MountainBike": "MountainBike_ES.png",
  "Barba": "Barba_ES.png",
  "BigRaft": "BigRaft_ES.png",
  "SmallRaft": "SmallRaft_ES.png",
  "SUP": "SUP_ES.png",
  "RIS": "RIS_ES.png",
  "Kinglet_Mariner": "Kinglet_Mariner_ES.png"
}
```

## Relação com Sistema de Registro de Veículos

### Como Funciona a Atualização de Status
Quando um evento de destruição é processado:
1. O evento é salvo na tabela `vehicle_destruction_events`
2. O sistema procura o veículo correspondente em `vehicle_current_ownership` usando:
   - `vehicle_destruction_events.vehicle_id` = `vehicle_current_ownership.vehicle_entity_id`
3. Se encontrado, atualiza o campo `status` na tabela `vehicle_current_ownership`

**Importante:** Se o `vehicle_entity_id` não estiver preenchido em `vehicle_current_ownership`, a atualização de status não ocorrerá.

## Tipos de Eventos

### 🟡 VehicleInactiveTimerReached
- **Descrição**: Veículo ficou inativo por muito tempo
- **Cor**: Amarelo (#f39c12)
- **Emoji**: 🟡
- **Status**: 1 (Inativo)
- **Atualiza**: `vehicle_current_ownership.status = 1`

### 🔴 Disappeared
- **Descrição**: Veículo desapareceu do mapa
- **Cor**: Vermelho (#e74c3c)
- **Emoji**: 🔴
- **Status**: 2 (Desaparecido)
- **Atualiza**: `vehicle_current_ownership.status = 2`

### ⚫ Destroyed
- **Descrição**: Veículo foi destruído
- **Cor**: Preto (#2c3e50)
- **Emoji**: ⚫
- **Status**: 3 (Destruído)
- **Atualiza**: `vehicle_current_ownership.status = 3`

## Configuração

### Webhook Discord
```json
{
    "vehicle-log": "https://discord.com/api/webhooks/..."
}
```

### Pasta de Logs
```json
{
    "logs": {
        "logs_directory": "C:\\Servers\\scum\\SCUM\\Saved\\SaveFiles\\Logs"
    }
}
```

## Endpoints da API

### Listar Eventos de Destruição
```
GET /api/vehicles/destruction/events
```

**Parâmetros:**
- `limit`: Número de registros por página (padrão: 50)
- `offset`: Deslocamento para paginação (padrão: 0)
- `event_type`: Filtrar por tipo de evento
- `vehicle_name`: Filtrar por nome do veículo
- `owner_steam_id`: Filtrar por Steam ID do proprietário

### Estatísticas de Destruição
```
GET /api/vehicles/destruction/stats
```

### Processar Log de Destruição
```
POST /api/vehicles/destruction/process
```

**Body:**
```json
{
    "log_file_path": "C:\\Servers\\scum\\SCUM\\Saved\\SaveFiles\\Logs\\vehicle_destruction_20251021174728.log"
}
```

## Fluxo de Processamento

### 1. Detecção
- **FileMonitor**: Detecta mudanças em `vehicle_destruction_*.log`
- **Polling**: Verifica arquivos a cada 5 segundos
- **Trigger**: Qualquer mudança no arquivo

### 2. Processamento
- **Cópia para temp**: Evita conflitos com arquivo em uso
- **Parse das linhas**: Extrai timestamp, veículo, proprietário e localização
- **Mapeamento de imagem**: Busca imagem específica do veículo
- **Verificação de duplicatas**: Compara com eventos já processados

### 3. Envio
- **Categorização**: Determina categoria e cor do embed
- **Formatação**: Cria embed Discord com informações e imagem
- **Envio**: POST para webhook Discord
- **Salvamento**: Atualiza banco de dados

## Exemplo de Embed Discord

```json
{
  "embeds": [{
    "title": "⚫ Veículo Destruído - WolfsWagen_ES",
    "color": 2960685,
    "fields": [
      {
        "name": "🚗 Veículo",
        "value": "WolfsWagen_ES (ID: 14620065)",
        "inline": true
      },
      {
        "name": "👤 Proprietário",
        "value": "Pedreiro (76561198040636105)",
        "inline": true
      },
      {
        "name": "📍 Localização",
        "value": "X: -314659.0\nY: -6662.0\nZ: 35708.0",
        "inline": true
      },
      {
        "name": "🕐 Timestamp",
        "value": "2025-10-21 19:25:46",
        "inline": true
      }
    ],
    "image": {
      "url": "attachment://WolfsWagen_ES.png"
    },
    "footer": {
      "text": "SCUM Server Manager - Vehicle Destruction Log"
    }
  }]
}
```

## Adicionando Novos Veículos

### 1. Adicionar Imagem
- Colocar imagem na pasta `data/imagens/carros/vehicle-log/`
- Nome do arquivo: `NomeDoVeiculo_ES.png`

### 2. Atualizar Mapeamento
- Editar arquivo `mapping.json`
- Adicionar entrada: `"NomeDoVeiculo": "NomeDoVeiculo_ES.png"`

### 3. Reiniciar Sistema
- Reiniciar aplicação para carregar novo mapeamento

## Logs de Debug

O sistema gera logs detalhados para monitoramento:

```
VEHICLE DESTRUCTION Novo arquivo detectado: vehicle_destruction_20251021174728.log
OK Arquivo copiado para temp: data\temp\vehicle_destruction_20251021174728_1761075794309.log
OK Vehicle destruction log processado: vehicle_destruction_20251021174728.log
OK Evento de destruição enviado com imagem: WolfsWagen_ES.png
```

## Troubleshooting

### Problema: Imagens não aparecem
- Verificar se arquivo existe na pasta `vehicle-log/`
- Verificar mapeamento no `mapping.json`
- Verificar logs de debug

### Problema: Notificações não sendo enviadas
- Verificar configuração do webhook no `data/webhooks.json`
- Verificar se o canal Discord aceita webhooks
- Verificar logs de erro

### Problema: Eventos duplicados
- Sistema tem proteção contra duplicatas
- Verificar se evento já existe no banco de dados
- Verificar logs de processamento

## Vantagens do Sistema

### ✅ Para Administradores
- **Rastreamento completo** de destruição de veículos
- **Histórico detalhado** de todos os eventos
- **Notificações visuais** com imagens dos veículos
- **Categorização automática** por tipo de evento

### ✅ Para Desenvolvedores
- **API completa** para consultas
- **Dados estruturados** e normalizados
- **Sistema extensível** para futuras funcionalidades
- **Monitoramento robusto** com sistema híbrido

### ✅ Para Jogadores
- **Transparência** sobre eventos de veículos
- **Notificações em tempo real** no Discord
- **Histórico visual** de destruições
