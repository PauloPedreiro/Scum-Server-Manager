# Sistema de Auto-Registro de Veículos

## Visão Geral

O Sistema de Auto-Registro de Veículos é uma funcionalidade que monitora automaticamente os logs de `chest_ownership_*.log` do SCUM para detectar quando jogadores trancam ou transferem veículos, registrando essas informações no banco de dados e enviando notificações para o Discord.

## Funcionalidades

### 🔒 Detecção Automática de Veículos Trancados
- Monitora logs de `chest_ownership_*.log` em tempo real
- Detecta eventos de `ownership claimed` (primeira tranca)
- Detecta eventos de `ownership changed` (transferência de propriedade)

### 🗄️ Armazenamento de Dados
- **Histórico completo** de todas as mudanças de propriedade
- **Propriedade atual** de cada veículo
- **Duplo identificador**: Container ID + Vehicle Entity ID
- **Informações detalhadas**: localização, tipo de veículo, status funcional

### 💬 Notificações Discord
- Notificações automáticas para canal específico
- Embeds ricos com imagem do veículo
- Informações completas: jogador, localização, IDs

## Estrutura do Banco de Dados

### Tabela: `vehicle_ownership_history`
Armazena o histórico completo de todas as mudanças de propriedade.

```sql
CREATE TABLE vehicle_ownership_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    entity_id INTEGER NOT NULL,              -- ID do container/recipiente
    vehicle_entity_id INTEGER,               -- ID do veículo (novo campo)
    steam_id TEXT NOT NULL,                  -- Steam ID do proprietário
    player_id INTEGER,                       -- ID do jogador
    player_name TEXT NOT NULL,               -- Nome do jogador
    ownership_type TEXT NOT NULL,            -- 'claimed' ou 'changed'
    previous_owner_steam_id TEXT,            -- Steam ID do proprietário anterior
    previous_owner_name TEXT,                -- Nome do proprietário anterior
    location_x REAL,                         -- Coordenada X
    location_y REAL,                         -- Coordenada Y
    location_z REAL,                         -- Coordenada Z
    timestamp DATETIME NOT NULL,             -- Data/hora do evento
    log_file TEXT,                           -- Arquivo de log origem
    container_class TEXT,                    -- Classe do container
    vehicle_class TEXT,                      -- Classe do veículo
    vehicle_asset_id TEXT,                   -- Asset ID do veículo
    is_vehicle_functional INTEGER,           -- Veículo funcional (0/1)
    notification_sent BOOLEAN DEFAULT 0,     -- Notificação enviada
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

### Tabela: `vehicle_current_ownership`
Armazena a propriedade atual de cada veículo.

```sql
CREATE TABLE vehicle_current_ownership (
    entity_id INTEGER PRIMARY KEY,           -- ID do container/recipiente
    vehicle_entity_id INTEGER,               -- ID do veículo (novo campo)
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
    status INTEGER DEFAULT 0,               -- Status: 0=Ativo, 1=Inativo, 2=Desaparecido, 3=Destruído
    notification_sent BOOLEAN DEFAULT 0,     -- Notificação enviada
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

## Relação entre Tabelas

### Ligação com Sistema de Destruição
A tabela `vehicle_current_ownership` está relacionada com `vehicle_destruction_events` através do campo `vehicle_entity_id`:
- **`vehicle_destruction_events.vehicle_id`** = **`vehicle_current_ownership.vehicle_entity_id`**
- Quando um evento de destruição, inatividade ou desaparecimento é detectado, o campo `status` em `vehicle_current_ownership` é atualizado automaticamente

### Status dos Veículos
- **0 = Ativo**: Veículo está ativo e vinculado a um jogador
- **1 = Inativo**: Veículo atingiu timer de inatividade (`VehicleInactiveTimerReached`)
- **2 = Desaparecido**: Veículo desapareceu do mapa (`Disappeared`)
- **3 = Destruído**: Veículo foi destruído (`Destroyed`)

## Identificadores de Veículos

### Container ID (`entity_id`)
- **O que é**: ID do recipiente/container do veículo
- **Uso**: Identifica o container onde o jogador coloca a tranca
- **Exemplo**: `14370020`
- **Primary Key**: Usado como chave primária da tabela

### Vehicle Entity ID (`vehicle_entity_id`)
- **O que é**: ID da entidade do veículo propriamente dito
- **Uso**: Identifica o veículo real para rastreamento e ligação com eventos de destruição
- **Exemplo**: `14370019`
- **Benefício**: Permite rastrear o mesmo veículo mesmo se o container mudar
- **Importante**: Este campo é usado para atualizar o status quando há eventos de destruição

## Tipos de Eventos

### 🔒 Ownership Claimed
**Quando**: Jogador coloca uma tranca pela primeira vez em um veículo
```json
{
    "ownership_type": "claimed",
    "previous_owner_steam_id": null,
    "previous_owner_name": null
}
```

### 🔄 Ownership Changed
**Quando**: Veículo é transferido de um jogador para outro
```json
{
    "ownership_type": "changed",
    "previous_owner_steam_id": "76561198140683162",
    "previous_owner_name": "Jovigono"
}
```

## Mapeamento de Imagens

O sistema possui um mapeamento completo entre tipos de veículos e imagens:

| Tipo de Veículo | Arquivo de Imagem |
|-----------------|-------------------|
| BPC_Tractor | BPC_Tractor.png |
| BPC_Dirtbike | BPC_Dirtbike.png |
| BPC_CityBike | BPC_CityBike.png |
| BPC_Cruiser | BPC_Cruiser.png |
| BPC_Kinglet_Duster | BPC_Kinglet_Duster.png |
| BPC_Kinglet_Mariner | BPC_Kinglet_Mariner.png |
| BPC_Laika | BPC_Laika.png |
| BPC_MountainBike | BPC_MountainBike.png |
| BPC_Rager | BPC_Rager.png |
| BPC_RIS | BPC_RIS.png |
| BPC_SmallRaft | BPC_SmallRaft.png |
| BPC_SUP | BPC_SUP.png |
| BPC_WolfsWagen | BPC_WolfsWagen.png |
| BP_WheelBarrow_Improvised | BP_WheelBarrow_Improvised.png |
| BP_WheelBarrow_Metal | BP_WheelBarrow_Metal.png |

## Notificações Discord

### Formato da Notificação
```json
{
    "title": "🔒 Veículo Trancado",
    "description": "Um veículo foi trancado por um jogador",
    "color": 16742965,
    "fields": [
        {
            "name": "🚗 Veículo",
            "value": "Trator",
            "inline": true
        },
        {
            "name": "👤 Jogador",
            "value": "Pedreiro (ID: 1)",
            "inline": true
        },
        {
            "name": "📍 Localização",
            "value": "X: -616882\nY: -554072\nZ: 2477",
            "inline": true
        }
    ],
    "footer": {
        "text": "Container ID: 14370020 • Vehicle ID: 14370019 • Steam ID: 76561198040636105"
    },
    "image": {
        "url": "https://exemplo.com/images/BPC_Tractor.png"
    }
}
```

## Prevenção de Duplicação

### Sistema de Deduplicação por Vehicle Entity ID
O sistema implementa uma verificação robusta para evitar registros duplicados do mesmo veículo:

#### Problema Resolvido
Alguns veículos possuem múltiplos containers (ex: Trator com `Tractor_Item_Container_ES` e `Tractor_Carriage_Item_Container_ES`). Sem a verificação, o mesmo veículo poderia ser registrado múltiplas vezes quando diferentes containers fossem trancados.

#### Solução Implementada
1. **Verificação no Banco de Dados**: Antes de inserir um novo registro, o sistema verifica se já existe um registro com o mesmo `vehicle_entity_id` na tabela `vehicle_current_ownership`
2. **Ignorar Duplicatas**: Se o veículo já estiver registrado, o novo container é ignorado silenciosamente
3. **Log de Aviso**: Quando uma duplicata é detectada, uma mensagem de aviso é registrada nos logs:
   ```
   AVISO: Veículo já registrado ignorado - Vehicle Entity ID: 16270075, Container ID: 16270077, Container Class: Tractor_Carriage_Item_Container_ES
   ```

#### Containers Secundários Filtrados
O sistema também filtra containers secundários que não devem ser registrados:
- `Big_Vehicle_StorageRack_ES`
- `Small_Vehicle_StorageRack_ES`
- `Medium_Vehicle_StorageRack_ES`
- `Big_Inventory_Expansion_Item_Container_ES`
- `Small_Inventory_Expansion_Item_Container_ES`
- `Medium_Inventory_Expansion_Item_Container_ES`
- `Tractor_Carriage_Item_Container_ES` (carreta do trator)

#### Benefícios
- **Um veículo = Um registro**: Garante que cada `vehicle_entity_id` apareça apenas uma vez em `vehicle_current_ownership`
- **Registro pelo primeiro container**: O primeiro container trancado é registrado (geralmente o principal)
- **Funciona em tempo real**: A verificação ocorre tanto para eventos simultâneos quanto para eventos que chegam em momentos diferentes

## Monitoramento em Tempo Real

### Sistema Híbrido de Monitoramento
1. **Watchdog**: Detecta mudanças gerais nos arquivos
2. **Polling**: Verifica arquivos em uso pelo SCUM Server a cada 5 segundos

### Processamento Incremental
- Processa apenas novas linhas dos arquivos
- Evita reprocessamento de dados antigos
- Previne duplicatas no banco de dados

## Configuração

### Webhook Discord
```json
{
    "vehicle_registration": "https://discord.com/api/webhooks/..."
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

### Listar Histórico de Veículos
```
GET /api/vehicles/ownership/history
```

**Parâmetros:**
- `limit`: Número de registros por página (padrão: 50)
- `offset`: Deslocamento para paginação (padrão: 0)
- `steam_id`: Filtrar por Steam ID do jogador
- `vehicle_class`: Filtrar por tipo de veículo
- `ownership_type`: Filtrar por tipo de evento ('claimed' ou 'changed')

### Listar Propriedade Atual
```
GET /api/vehicles/ownership/current
```

### Estatísticas de Veículos
```
GET /api/vehicles/stats
```

### Listar Veículos Ativos
Para listar apenas veículos ativos vinculados a jogadores, use o endpoint `/api/vehicles/ownership/current` com filtro de status (futuro) ou faça a query diretamente no banco:

```sql
SELECT * FROM vehicle_current_ownership 
WHERE status = 0                    -- Apenas veículos ativos
  AND steam_id IS NOT NULL          -- Vinculados a jogadores
  AND steam_id != ''
  AND vehicle_entity_id IS NOT NULL  -- Garantir que tem ID do veículo
ORDER BY last_ownership_change DESC
```

**Critérios para veículo ativo:**
- `status = 0` (Ativo)
- `steam_id` não nulo e não vazio (vinculado a jogador)
- `vehicle_entity_id` não nulo (tem identificador válido)

## Benefícios do Sistema

### Para Administradores
- **Rastreamento completo** de propriedade de veículos
- **Histórico detalhado** de todas as mudanças
- **Notificações em tempo real** no Discord
- **Identificação única** de veículos para rastreamento

### Para Desenvolvedores
- **API completa** para consultas
- **Dados estruturados** e normalizados
- **Sistema extensível** para futuras funcionalidades
- **Monitoramento robusto** com sistema híbrido

## Logs de Debug

O sistema gera logs detalhados para monitoramento:

```
VEÍCULOS Processando logs de chest ownership: chest_ownership_20251019200029.log
   Novas linhas: 19
OK Mapeamento de veículos concluído: 18 containers mapeados
OK Claims processadas: 18 total, 18 veículos
   Veículos encontrados: 18
   OK 18 veículos inseridos no banco
```

## Troubleshooting

### Problema: Notificações não sendo enviadas
- Verificar configuração do webhook no `data/webhooks.json`
- Verificar se o canal Discord aceita webhooks
- Verificar logs do backend para erros de conexão

### Problema: Veículos não sendo detectados
- Verificar se os arquivos `chest_ownership_*.log` estão sendo gerados
- Verificar permissões de leitura na pasta de logs
- Verificar se o banco SCUM.db está acessível

### Problema: Imagens não aparecendo
- Verificar se os arquivos de imagem estão na pasta `data/imagens/carros/`
- Verificar mapeamento de tipos de veículo para imagens
- Verificar se o webhook suporta imagens

## Futuras Funcionalidades

- [ ] API para transferir propriedade manualmente
- [ ] Relatórios de veículos por jogador
- [ ] Sistema de alertas para veículos abandonados
- [ ] Integração com sistema de login/logout
- [ ] Dashboard web para visualização de dados
