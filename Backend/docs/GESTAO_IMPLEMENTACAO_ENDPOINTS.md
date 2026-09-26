# 📡 Documentação Técnica: Implementação de Endpoints para Sincronização SSM Backend

> **Destinatário**: Desenvolvedor do Gestão  
> **Objetivo**: Implementar endpoints para receber dados de sincronização dos servidores SSM Backend  
> **Data**: 2025-12-XX

---

## 🎯 Visão Geral

O **SSM Backend** envia dados periodicamente (a cada 4 horas) para o **Gestão** através de dois endpoints:

1. **GET `/api/v1/servers/ready`** - Handshake (verificar se Gestão está pronto)
2. **POST `/api/v1/servers/sync`** - Sincronização de dados

### **Arquitetura**

```
SSM Backend (Cliente)                    Gestão (Servidor)
─────────────────────                    ────────────────
     │                                          │
     │ 1. GET /api/v1/servers/ready            │
     │    ?server_hash={hash}                  │
     ├─────────────────────────────────────────>│
     │                                          │
     │ 2. {ready: true}                        │
     │<─────────────────────────────────────────┤
     │                                          │
     │ 3. POST /api/v1/servers/sync            │
     │    Body: {server_hash, api_key, ...}    │
     ├─────────────────────────────────────────>│
     │                                          │
     │ 4. {success: true}                       │
     │<─────────────────────────────────────────┤
```

---

## 🔐 Autenticação e Identificação

### **Identificação do Servidor**

- **Server Hash**: SHA-256 hash único do servidor (64 caracteres hexadecimais)
- **Formato**: `918aabd12dc60d8432ab952f8eab6557a5b8b14066953e26516fab6f1ff0c54d`
- **Origem**: Gerado pelo SSM Backend baseado no hardware fingerprint

### **API Key**

- **Formato**: `ssm_` + 64 caracteres hexadecimais
- **Exemplo**: `ssm_2d9ba653192f1a872fbef6583485c50fd6265384ace80ecf222727cc41c4ac4c`
- **Origem**: Gerada pelo Gestão quando o servidor é cadastrado
- **Validação**: O Gestão deve validar que o `server_hash` corresponde ao `api_key` fornecido

### **Fluxo de Cadastro**

1. Admin do Gestão cadastra servidor com `server_hash`
2. Gestão gera `api_key` única e associa ao servidor
3. Admin copia `api_key` e configura no SSM Backend
4. SSM Backend usa `server_hash` + `api_key` para sincronizar

---

## 📡 Endpoint 1: Handshake (GET /api/v1/servers/ready)

### **Objetivo**

Verificar se o Gestão está pronto para receber dados de sincronização. Permite controle de carga e rate limiting.

### **Request**

```
GET /api/v1/servers/ready?server_hash={hash}
```

**Query Parameters:**
- `server_hash` (string, obrigatório): Hash único do servidor (64 caracteres hex)

**Headers:**
```
Content-Type: application/json
```

### **Respostas**

#### **200 OK - Pronto para receber**

```json
{
  "ready": true,
  "message": "Pronto para receber dados"
}
```

#### **503 Service Unavailable - Não pronto**

```json
{
  "ready": false,
  "retry_after": 60,
  "message": "Servidor ocupado, tente novamente em 60 segundos"
}
```

**Campos:**
- `retry_after` (int): Segundos que o SSM Backend deve aguardar antes de tentar novamente (mínimo: 30, máximo: 3600)

#### **429 Too Many Requests - Rate Limit**

```json
{
  "ready": false,
  "retry_after": 300,
  "message": "Rate limit atingido, tente novamente em 5 minutos"
}
```

### **Lógica de Implementação**

```python
# Pseudocódigo
def get_servers_ready(server_hash):
    # 1. Validar formato do hash
    if not is_valid_hash(server_hash):
        return 400, {"error": "Hash inválido"}
    
    # 2. Verificar se servidor está cadastrado (opcional - pode ser verificado no sync)
    # server = Server.query.filter_by(server_hash=server_hash).first()
    # if not server:
    #     return 404, {"error": "Servidor não cadastrado"}
    
    # 3. Verificar carga do servidor
    current_load = get_current_load()
    max_load = get_max_load()
    
    if current_load >= max_load:
        retry_after = calculate_retry_time(current_load, max_load)
        return 503, {
            "ready": false,
            "retry_after": retry_after,
            "message": f"Servidor ocupado, tente novamente em {retry_after} segundos"
        }
    
    # 4. Verificar rate limiting (opcional)
    if is_rate_limited(server_hash):
        retry_after = 300  # 5 minutos
        return 429, {
            "ready": false,
            "retry_after": retry_after,
            "message": "Rate limit atingido, tente novamente em 5 minutos"
        }
    
    # 5. Pronto para receber
    return 200, {
        "ready": true,
        "message": "Pronto para receber dados"
    }
```

### **Considerações**

- **Performance**: Este endpoint deve ser rápido (< 100ms)
- **Rate Limiting**: Implementar rate limiting por `server_hash` (ex: máximo 1 requisição por minuto por servidor)
- **Load Control**: Verificar carga do servidor antes de permitir sincronização
- **Validação**: Validar formato do hash (64 caracteres hex)

---

## 📡 Endpoint 2: Sincronização (POST /api/v1/servers/sync)

### **Objetivo**

Receber e processar dados de sincronização do servidor SSM Backend.

### **Request**

```
POST /api/v1/servers/sync
```

**Headers:**
```
Content-Type: application/json
```

**Body:**
```json
{
  "server_hash": "918aabd12dc60d8432ab952f8eab6557a5b8b14066953e26516fab6f1ff0c54d",
  "api_key": "ssm_2d9ba653192f1a872fbef6583485c50fd6265384ace80ecf222727cc41c4ac4c",
  "server_info": {
    "name": "Meu Servidor SCUM",
    "version": "3.0.0",
    "max_players": 64,
    "current_players": 32
  },
  "players": [
    {
      "steam_id": "76561198012345678",
      "name": "PlayerName",
      "fame": 50000,
      "is_online": true,
      "last_seen": "2025-01-15T10:30:00Z"
    }
  ],
  "rankings": {
    "kills": [
      {
        "steam_id": "76561198012345678",
        "name": "PlayerName",
        "score": 150,
        "kdr": 6.0,
        "deaths": 25
      }
    ],
    "survival": [
      {
        "steam_id": "76561198012345678",
        "name": "PlayerName",
        "score": 5000,
        "fame": 50000
      }
    ],
    "lockpicking": [
      {
        "steam_id": "76561198012345678",
        "name": "PlayerName",
        "score": 80.5,
        "basic_rate": 75.0,
        "medium_rate": 82.0,
        "advanced_rate": 85.0
      }
    ],
    "fishing": [
      {
        "steam_id": "76561198012345678",
        "name": "PlayerName",
        "score": 87
      }
    ]
  },
  "timestamp": "2025-01-15T10:30:00Z"
}
```

### **Estrutura Detalhada do Payload**

#### **server_hash** (string, obrigatório)
- Hash único do servidor (64 caracteres hex)
- Usado para identificar o servidor no banco de dados

#### **api_key** (string, obrigatório)
- API key gerada pelo Gestão
- Formato: `ssm_` + 64 caracteres hex
- Deve corresponder ao `server_hash` fornecido

#### **server_info** (object, obrigatório)
```json
{
  "name": "string",           // Nome do servidor
  "version": "string",         // Versão do SSM Backend (ex: "3.0.0")
  "max_players": int,          // Máximo de jogadores
  "current_players": int       // Jogadores online no momento
}
```

#### **players** (array, obrigatório)
- Lista de até 1000 jogadores
- Inclui jogadores online e offline
- Ordenados por fama (maior para menor)

```json
{
  "steam_id": "string",        // Steam ID do jogador (17 dígitos)
  "name": "string",            // Nome do jogador
  "fame": float,               // Fama total do jogador
  "is_online": boolean,        // true se online, false se offline
  "last_seen": "string"        // ISO 8601 timestamp (ex: "2025-01-15T10:30:00Z") ou null
}
```

#### **rankings** (object, obrigatório)
- Rankings por categoria
- Cada categoria contém até 100 registros

**Estrutura:**
```json
{
  "kills": [                   // Top 100 killers
    {
      "steam_id": "string",
      "name": "string",
      "score": int,             // Total de kills
      "kdr": float,             // Kill/Death Ratio
      "deaths": int
    }
  ],
  "survival": [                // Top 100 por minutos sobrevividos
    {
      "steam_id": "string",
      "name": "string",
      "score": int,             // Minutos sobrevividos
      "fame": float
    }
  ],
  "lockpicking": [             // Top 100 por taxa de sucesso média
    {
      "steam_id": "string",
      "name": "string",
      "score": float,           // Taxa média (0-100)
      "basic_rate": float,
      "medium_rate": float,
      "advanced_rate": float
    }
  ],
  "fishing": [                 // Top 100 por animais mortos
    {
      "steam_id": "string",
      "name": "string",
      "score": int              // Total de animais mortos
    }
  ]
}
```

#### **timestamp** (string, obrigatório)
- ISO 8601 timestamp da sincronização
- Formato: `"2025-01-15T10:30:00Z"`

### **Validações Necessárias**

1. **Formato do Hash**
   - Deve ter exatamente 64 caracteres hexadecimais
   - Regex: `^[a-f0-9]{64}$`

2. **Formato da API Key**
   - Deve começar com `ssm_`
   - Deve ter 64 caracteres hex após o prefixo
   - Regex: `^ssm_[a-f0-9]{64}$`

3. **Servidor Cadastrado**
   - Verificar se `server_hash` existe no banco de dados
   - Verificar se `api_key` corresponde ao servidor

4. **Estrutura do Payload**
   - Validar que todos os campos obrigatórios estão presentes
   - Validar tipos de dados (string, int, float, boolean, array, object)
   - Validar que arrays não excedem limites (players: 1000, rankings: 100 por categoria)

5. **Formato de Timestamp**
   - Validar formato ISO 8601
   - Validar que não é uma data futura

### **Respostas**

#### **200 OK - Sincronização Bem-sucedida**

```json
{
  "success": true,
  "message": "Dados sincronizados com sucesso",
  "server_id": 1,
  "players_synced": 150,
  "rankings_synced": 4,
  "timestamp": "2025-01-15T10:30:00Z"
}
```

#### **400 Bad Request - Dados Inválidos**

```json
{
  "success": false,
  "error": "Dados inválidos",
  "details": {
    "server_hash": "Hash deve ter 64 caracteres hexadecimais",
    "api_key": "API key deve começar com 'ssm_' e ter 64 caracteres hex"
  }
}
```

#### **401 Unauthorized - API Key Inválida**

```json
{
  "success": false,
  "error": "API key inválida ou não corresponde ao servidor"
}
```

#### **404 Not Found - Servidor Não Cadastrado**

```json
{
  "success": false,
  "error": "Servidor não encontrado ou não cadastrado"
}
```

#### **422 Unprocessable Entity - API Key Obrigatória**

```json
{
  "success": false,
  "error": "API key é obrigatória",
  "message": "Configure a API key no payload"
}
```

#### **503 Service Unavailable - Servidor Ocupado**

```json
{
  "success": false,
  "error": "Servidor ocupado",
  "retry_after": 60,
  "message": "Tente novamente em 60 segundos"
}
```

### **Lógica de Implementação**

```python
# Pseudocódigo
def post_servers_sync(data):
    # 1. Validar formato do hash
    server_hash = data.get('server_hash')
    if not is_valid_hash(server_hash):
        return 400, {"success": False, "error": "Hash inválido"}
    
    # 2. Validar formato da API key
    api_key = data.get('api_key')
    if not api_key:
        return 422, {"success": False, "error": "API key é obrigatória"}
    
    if not is_valid_api_key(api_key):
        return 400, {"success": False, "error": "Formato de API key inválido"}
    
    # 3. Buscar servidor no banco
    server = Server.query.filter_by(server_hash=server_hash).first()
    if not server:
        return 404, {"success": False, "error": "Servidor não encontrado ou não cadastrado"}
    
    # 4. Validar API key
    if server.api_key != api_key:
        return 401, {"success": False, "error": "API key inválida ou não corresponde ao servidor"}
    
    # 5. Verificar carga do servidor (opcional)
    if is_server_overloaded():
        return 503, {
            "success": False,
            "error": "Servidor ocupado",
            "retry_after": 60
        }
    
    # 6. Validar estrutura do payload
    validation_errors = validate_payload(data)
    if validation_errors:
        return 400, {
            "success": False,
            "error": "Dados inválidos",
            "details": validation_errors
        }
    
    # 7. Processar sincronização
    try:
        # Atualizar informações do servidor
        server.server_name = data['server_info'].get('name', server.server_name)
        server.version = data['server_info'].get('version', server.version)
        server.max_players = data['server_info'].get('max_players', server.max_players)
        server.current_players = data['server_info'].get('current_players', 0)
        server.last_sync = parse_timestamp(data['timestamp'])
        
        # Sincronizar jogadores
        players_synced = sync_players(server.id, data['players'])
        
        # Sincronizar rankings
        rankings_synced = sync_rankings(server.id, data['rankings'])
        
        # Salvar no banco
        db.session.commit()
        
        return 200, {
            "success": True,
            "message": "Dados sincronizados com sucesso",
            "server_id": server.id,
            "players_synced": players_synced,
            "rankings_synced": rankings_synced,
            "timestamp": data['timestamp']
        }
    except Exception as e:
        db.session.rollback()
        return 500, {
            "success": False,
            "error": "Erro ao processar sincronização",
            "message": str(e)
        }
```

---

## 🗄️ Modelos de Dados (Sugestão)

### **Tabela: Server**

```sql
CREATE TABLE server (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    server_hash VARCHAR(64) UNIQUE NOT NULL,
    server_name VARCHAR(255),
    version VARCHAR(50),
    max_players INTEGER,
    current_players INTEGER DEFAULT 0,
    api_key VARCHAR(255) UNIQUE NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    last_sync DATETIME,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_server_hash (server_hash),
    INDEX idx_api_key (api_key)
);
```

### **Tabela: ServerPlayer**

```sql
CREATE TABLE server_player (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    server_id INTEGER NOT NULL,
    steam_id VARCHAR(17) NOT NULL,
    player_name VARCHAR(255),
    fame FLOAT DEFAULT 0,
    is_online BOOLEAN DEFAULT FALSE,
    last_seen DATETIME,
    synced_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (server_id) REFERENCES server(id) ON DELETE CASCADE,
    UNIQUE(server_id, steam_id),
    INDEX idx_server_id (server_id),
    INDEX idx_steam_id (steam_id),
    INDEX idx_is_online (is_online)
);
```

### **Tabela: ServerRanking**

```sql
CREATE TABLE server_ranking (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    server_id INTEGER NOT NULL,
    category VARCHAR(50) NOT NULL,  -- 'kills', 'survival', 'lockpicking', 'fishing'
    steam_id VARCHAR(17) NOT NULL,
    player_name VARCHAR(255),
    score FLOAT,
    rank_position INTEGER,
    additional_data JSON,  -- Para campos específicos de cada categoria (kdr, deaths, etc)
    synced_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (server_id) REFERENCES server(id) ON DELETE CASCADE,
    INDEX idx_server_category (server_id, category),
    INDEX idx_steam_id (steam_id),
    INDEX idx_rank_position (rank_position)
);
```

### **Estrutura do additional_data (JSON)**

**Para categoria 'kills':**
```json
{
  "kdr": 6.0,
  "deaths": 25
}
```

**Para categoria 'survival':**
```json
{
  "fame": 50000
}
```

**Para categoria 'lockpicking':**
```json
{
  "basic_rate": 75.0,
  "medium_rate": 82.0,
  "advanced_rate": 85.0
}
```

**Para categoria 'fishing':**
```json
{}
```

---

## 🔄 Fluxo de Sincronização Completo

### **1. Handshake**

```
SSM Backend → GET /api/v1/servers/ready?server_hash={hash}
Gestão → {ready: true} ou {ready: false, retry_after: 60}
```

### **2. Sincronização**

```
SSM Backend → POST /api/v1/servers/sync
Body: {server_hash, api_key, server_info, players, rankings, timestamp}
Gestão → {success: true, server_id, players_synced, rankings_synced}
```

### **3. Processamento no Gestão**

1. Validar hash e API key
2. Buscar/atualizar servidor
3. Sincronizar jogadores (upsert: atualizar se existe, criar se não existe)
4. Sincronizar rankings (substituir rankings antigos pelos novos)
5. Atualizar `last_sync` do servidor

---

## ⚠️ Considerações Importantes

### **Performance**

- **Handshake**: Deve ser rápido (< 100ms)
- **Sincronização**: Pode levar alguns segundos dependendo do volume de dados
- **Timeout**: SSM Backend usa timeout de 30 segundos para sincronização

### **Rate Limiting**

- Implementar rate limiting por `server_hash`
- Sugestão: Máximo 1 requisição de handshake por minuto por servidor
- Sugestão: Máximo 1 sincronização por 5 minutos por servidor

### **Validação de Dados**

- **Obrigatório**: Validar formato de hash e API key antes de processar
- **Recomendado**: Validar estrutura completa do payload
- **Opcional**: Validar limites de arrays (players: 1000, rankings: 100 por categoria)

### **Tratamento de Erros**

- **400**: Dados inválidos (formato incorreto)
- **401**: API key inválida
- **404**: Servidor não cadastrado
- **422**: API key obrigatória (quando não fornecida)
- **503**: Servidor ocupado (com `retry_after`)

### **Segurança**

- **Validação de API Key**: Sempre validar que a API key corresponde ao server_hash
- **HTTPS**: Recomendado usar HTTPS em produção
- **Rate Limiting**: Implementar para prevenir abuso
- **Logging**: Registrar tentativas de sincronização (sucesso e falha)

### **Idempotência**

- A sincronização deve ser **idempotente**
- Múltiplas sincronizações com os mesmos dados devem produzir o mesmo resultado
- Usar `upsert` (update or insert) para jogadores e rankings

---

## 📝 Exemplos de Requisições

### **Exemplo 1: Handshake Bem-sucedido**

**Request:**
```http
GET /api/v1/servers/ready?server_hash=918aabd12dc60d8432ab952f8eab6557a5b8b14066953e26516fab6f1ff0c54d HTTP/1.1
Host: gestao.seudominio.com
Content-Type: application/json
```

**Response:**
```http
HTTP/1.1 200 OK
Content-Type: application/json

{
  "ready": true,
  "message": "Pronto para receber dados"
}
```

### **Exemplo 2: Sincronização Bem-sucedida**

**Request:**
```http
POST /api/v1/servers/sync HTTP/1.1
Host: gestao.seudominio.com
Content-Type: application/json

{
  "server_hash": "918aabd12dc60d8432ab952f8eab6557a5b8b14066953e26516fab6f1ff0c54d",
  "api_key": "ssm_2d9ba653192f1a872fbef6583485c50fd6265384ace80ecf222727cc41c4ac4c",
  "server_info": {
    "name": "Meu Servidor SCUM",
    "version": "3.0.0",
    "max_players": 64,
    "current_players": 32
  },
  "players": [
    {
      "steam_id": "76561198012345678",
      "name": "PlayerName",
      "fame": 50000,
      "is_online": true,
      "last_seen": "2025-01-15T10:30:00Z"
    }
  ],
  "rankings": {
    "kills": [],
    "survival": [],
    "lockpicking": [],
    "fishing": []
  },
  "timestamp": "2025-01-15T10:30:00Z"
}
```

**Response:**
```http
HTTP/1.1 200 OK
Content-Type: application/json

{
  "success": true,
  "message": "Dados sincronizados com sucesso",
  "server_id": 1,
  "players_synced": 1,
  "rankings_synced": 0,
  "timestamp": "2025-01-15T10:30:00Z"
}
```

### **Exemplo 3: Erro - Servidor Não Cadastrado**

**Request:**
```http
POST /api/v1/servers/sync HTTP/1.1
Host: gestao.seudominio.com
Content-Type: application/json

{
  "server_hash": "hash_nao_cadastrado",
  "api_key": "ssm_invalid_key"
}
```

**Response:**
```http
HTTP/1.1 404 Not Found
Content-Type: application/json

{
  "success": false,
  "error": "Servidor não encontrado ou não cadastrado"
}
```

---

## ✅ Checklist de Implementação

- [ ] Endpoint GET `/api/v1/servers/ready` implementado
- [ ] Endpoint POST `/api/v1/servers/sync` implementado
- [ ] Validação de formato de hash (64 caracteres hex)
- [ ] Validação de formato de API key (`ssm_` + 64 hex)
- [ ] Validação de correspondência hash + API key
- [ ] Tabela `Server` criada
- [ ] Tabela `ServerPlayer` criada
- [ ] Tabela `ServerRanking` criada
- [ ] Lógica de upsert para jogadores
- [ ] Lógica de sincronização de rankings
- [ ] Rate limiting implementado
- [ ] Load control implementado
- [ ] Tratamento de erros completo
- [ ] Logging de sincronizações
- [ ] Testes unitários
- [ ] Testes de integração

---

## 📞 Suporte

Para dúvidas ou problemas na implementação, entre em contato com a equipe do SSM Backend.

**Documentação Adicional:**
- [PLANEJAMENTO_ENDPOINT_SINCRONIZACAO_GESTAO.md](./PLANEJAMENTO_ENDPOINT_SINCRONIZACAO_GESTAO.md) - Documentação completa do planejamento

---

**Versão**: 1.0  
**Última Atualização**: 2025-12-XX
