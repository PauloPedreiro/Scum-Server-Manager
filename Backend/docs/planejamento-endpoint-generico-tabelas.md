# 📋 Planejamento: Endpoint Genérico para Consulta de Tabelas

## 🎯 Objetivo

Criar um endpoint genérico `/api/table/<table_name>` que permita consultar qualquer tabela do banco de dados SSM.db para **alimentar um sistema central de gestão** que controlará múltiplos servidores.

**Contexto:**
- ✅ Endpoint será usado por sistema externo (não apenas frontend interno)
- ✅ Cada servidor SSM alimentará o sistema central de gestão
- ✅ Precisa ser robusto, seguro e performático
- ✅ Suporte a sincronização incremental (última atualização)
- ✅ Formato padronizado para fácil integração

**Exemplos:**
- `/api/table/players`
- `/api/table/rankings`
- `/api/table/survival_stats_snapshot`
- `/api/table/squad_snapshot`

## 🤔 Análise das Opções

### **Opção 1: Endpoint Simples com Whitelist de Tabelas** ⭐ (Recomendada)

**Características:**
- Lista de tabelas permitidas (whitelist)
- Consulta simples: `SELECT * FROM <table>`
- Parâmetros de paginação (limit, offset)
- Parâmetros de ordenação (sort_by, sort_order)
- Filtros básicos via query params

**Vantagens:**
- ✅ Seguro (apenas tabelas permitidas)
- ✅ Simples de implementar
- ✅ Fácil de manter
- ✅ Performance controlada

**Desvantagens:**
- ⚠️ Precisa adicionar tabelas manualmente na whitelist
- ⚠️ Menos flexível para filtros complexos

**Exemplo de uso:**
```
GET /api/table/players?limit=50&offset=0&sort_by=last_seen&sort_order=desc
GET /api/table/rankings?limit=20&sort_by=kills&sort_order=desc
```

---

### **Opção 2: Endpoint com Schema Dinâmico**

**Características:**
- Descobre tabelas automaticamente via `PRAGMA table_list`
- Valida se tabela existe antes de consultar
- Permite consultar qualquer tabela do SSM.db
- Mesmos parâmetros de paginação/ordenação

**Vantagens:**
- ✅ Mais flexível (não precisa whitelist)
- ✅ Funciona automaticamente com novas tabelas
- ✅ Menos manutenção

**Desvantagens:**
- ⚠️ Menos seguro (expõe todas as tabelas)
- ⚠️ Pode expor tabelas sensíveis
- ⚠️ Pode ter problemas de performance com tabelas grandes

**Exemplo de uso:**
```
GET /api/table/players
GET /api/table/any_table_name
```

---

### **Opção 3: Endpoint com Blacklist de Tabelas**

**Características:**
- Lista de tabelas proibidas (blacklist)
- Permite todas as outras tabelas
- Mais flexível que whitelist
- Mais seguro que sem validação

**Vantagens:**
- ✅ Mais flexível que whitelist
- ✅ Mais seguro que sem validação
- ✅ Funciona automaticamente com novas tabelas

**Desvantagens:**
- ⚠️ Precisa manter blacklist atualizada
- ⚠️ Risco de esquecer tabelas sensíveis

---

### **Opção 4: Endpoint com Configuração por Tabela**

**Características:**
- Configuração JSON por tabela
- Define campos permitidos, ordenação padrão, limites
- Mais controle e personalização
- Pode ter diferentes comportamentos por tabela

**Vantagens:**
- ✅ Máximo controle
- ✅ Personalização por tabela
- ✅ Pode definir limites específicos
- ✅ Pode ocultar campos sensíveis

**Desvantagens:**
- ⚠️ Mais complexo de implementar
- ⚠️ Mais manutenção
- ⚠️ Configuração pode ficar grande

**Exemplo de configuração:**
```json
{
  "players": {
    "allowed": true,
    "default_sort": "last_seen",
    "default_order": "desc",
    "max_limit": 1000,
    "hidden_fields": ["internal_id", "secret_token"]
  },
  "rankings": {
    "allowed": true,
    "default_sort": "kills",
    "default_order": "desc",
    "max_limit": 100
  }
}
```

---

## 🔒 Considerações de Segurança (CRÍTICO para uso externo)

### **1. Autenticação/Autorização** 🔐
- ✅ **OBRIGATÓRIO**: API Key ou Token de autenticação
- ✅ Validar origem das requisições (IP whitelist opcional)
- ✅ Rate limiting por API key
- ✅ Logs de acesso para auditoria

### **2. SQL Injection**
- ✅ **CRÍTICO**: Usar sempre prepared statements
- ✅ Validar nome da tabela (whitelist obrigatória)
- ✅ Validar todos os parâmetros de entrada
- ✅ Nunca concatenar strings SQL diretamente
- ✅ Sanitizar todos os inputs

### **3. Exposição de Dados Sensíveis**
- ⚠️ Algumas tabelas podem conter dados sensíveis
- ⚠️ Ocultar campos específicos por tabela
- ⚠️ Considerar diferentes níveis de acesso por API key
- ⚠️ Não expor tabelas de sistema interno

### **4. Performance e Escalabilidade**
- ⚠️ Limitar número máximo de registros retornados
- ⚠️ Implementar paginação obrigatória para tabelas grandes
- ⚠️ Suporte a sincronização incremental (since, last_updated)
- ⚠️ Timeout de query (ex: 30 segundos)
- ⚠️ Indexar colunas usadas para ordenação e filtros
- ⚠️ Cache opcional para consultas frequentes

### **5. Rate Limiting**
- ⚠️ Limitar número de requisições por API key/IP
- ⚠️ Prevenir abuso do endpoint
- ⚠️ Diferentes limites para diferentes tipos de requisição

---

## 📊 Tabelas Identificadas no SSM.db

Baseado na análise do código, as principais tabelas são:

1. **players** - Jogadores cadastrados
2. **rankings** - Rankings de jogadores
3. **survival_stats_snapshot** - Estatísticas de sobrevivência
4. **squad_snapshot** - Squads
5. **kill_events** - Eventos de kills
6. **minigame_events** - Eventos de minigames
7. **vehicle_destruction_events** - Eventos de destruição de veículos
8. **player_vehicles** - Veículos dos jogadores
9. **admin_commands_processed** - Comandos admin processados
10. **log_files_processed** - Arquivos de log processados
11. **elevated_user** - Elevated users (pode ser sensível)
12. **player_gps_snapshot** - Posições GPS dos jogadores (pode ser sensível)

---

## 🎨 Proposta de Implementação (Opção 1 + Melhorias para Sistema Central)

### **Estrutura do Endpoint**

```
GET /api/table/<table_name>
```

### **Autenticação**

**Header obrigatório:**
```
Authorization: Bearer <api_key>
```
ou
```
X-API-Key: <api_key>
```

### **Parâmetros Query**

| Parâmetro | Tipo | Obrigatório | Padrão | Descrição |
|-----------|------|-------------|--------|-----------|
| `limit` | integer | Não | 100 | Número máximo de registros (1-5000) |
| `offset` | integer | Não | 0 | Deslocamento para paginação |
| `sort_by` | string | Não | `id` | Campo para ordenação |
| `sort_order` | string | Não | `asc` | Direção (`asc` ou `desc`) |
| `fields` | string | Não | `*` | Campos específicos (separados por vírgula) |
| `since` | string | Não | - | Data/hora ISO (ex: `2025-01-15T10:30:00`) - retorna apenas registros atualizados desde |
| `last_updated_field` | string | Não | `last_updated` | Campo usado para sincronização incremental |
| `format` | string | Não | `json` | Formato de resposta (`json` ou `csv`) |
| `include_metadata` | boolean | Não | `true` | Incluir metadados do servidor na resposta |

### **Whitelist de Tabelas Permitidas**

```python
ALLOWED_TABLES = {
    'players': {
        'default_sort': 'last_seen',
        'default_order': 'desc',
        'max_limit': 1000
    },
    'rankings': {
        'default_sort': 'kills',
        'default_order': 'desc',
        'max_limit': 100
    },
    'survival_stats_snapshot': {
        'default_sort': 'snapshot_at',
        'default_order': 'desc',
        'max_limit': 500
    },
    'squad_snapshot': {
        'default_sort': 'score',
        'default_order': 'desc',
        'max_limit': 200
    },
    'kill_events': {
        'default_sort': 'timestamp',
        'default_order': 'desc',
        'max_limit': 1000
    },
    'minigame_events': {
        'default_sort': 'timestamp',
        'default_order': 'desc',
        'max_limit': 500
    },
    'vehicle_destruction_events': {
        'default_sort': 'timestamp',
        'default_order': 'desc',
        'max_limit': 500
    },
    'player_vehicles': {
        'default_sort': 'last_seen',
        'default_order': 'desc',
        'max_limit': 1000
    }
}
```

### **Exemplo de Resposta (com metadados do servidor)**

```json
{
  "success": true,
  "server": {
    "backend_id": "server-001",
    "server_name": "Servidor Principal",
    "version": "3.0.0",
    "timestamp": "2025-01-15T10:30:45.123456Z"
  },
  "data": {
    "table": "players",
    "records": [
      {
        "steam_id": "76561198040636105",
        "player_name": "Pedreiro",
        "last_seen": "2025-10-31 02:53:09",
        ...
      }
    ],
    "pagination": {
      "total": 317,
      "limit": 100,
      "offset": 0,
      "count": 100,
      "has_more": true
    },
    "sort": {
      "by": "last_seen",
      "order": "desc"
    },
    "sync": {
      "incremental": false,
      "since": null,
      "last_updated_field": "last_updated"
    }
  }
}
```

### **Exemplo de Resposta com Sincronização Incremental**

```json
{
  "success": true,
  "server": {
    "backend_id": "server-001",
    "server_name": "Servidor Principal",
    "version": "3.0.0",
    "timestamp": "2025-01-15T10:30:45.123456Z"
  },
  "data": {
    "table": "players",
    "records": [
      {
        "steam_id": "76561198040636105",
        "player_name": "Pedreiro",
        "last_seen": "2025-10-31 02:53:09",
        "last_updated": "2025-01-15T10:25:00Z",
        ...
      }
    ],
    "pagination": {
      "total": 15,
      "limit": 100,
      "offset": 0,
      "count": 15,
      "has_more": false
    },
    "sort": {
      "by": "last_updated",
      "order": "asc"
    },
    "sync": {
      "incremental": true,
      "since": "2025-01-15T10:00:00Z",
      "last_updated_field": "last_updated",
      "records_since": 15
    }
  }
}
```

---

## 🔧 Implementação Técnica

### **Validações Necessárias**

1. **Nome da Tabela:**
   - Verificar se está na whitelist
   - Validar formato (apenas letras, números, underscore)
   - Prevenir SQL injection

2. **Parâmetros:**
   - `limit`: 1-1000 (ou max_limit da tabela)
   - `offset`: >= 0
   - `sort_by`: Validar se campo existe na tabela
   - `sort_order`: Apenas 'asc' ou 'desc'
   - `fields`: Validar se campos existem

3. **Query SQL:**
   - Usar sempre prepared statements
   - Validar todos os inputs
   - Limitar resultados

### **Estrutura de Código**

```python
@app.route('/api/table/<table_name>', methods=['GET'])
def get_table_data(table_name: str):
    """
    Consultar dados de uma tabela específica
    
    Args:
        table_name: Nome da tabela (deve estar na whitelist)
    """
    # 1. Validar nome da tabela
    # 2. Obter configuração da tabela
    # 3. Validar parâmetros
    # 4. Construir query SQL segura
    # 5. Executar query
    # 6. Retornar resultados
```

---

## 🎯 Requisitos para Sistema Central de Gestão

### **Funcionalidades Essenciais**

1. **Autenticação por API Key**
   - Cada servidor terá uma API key única
   - Validação obrigatória em todas as requisições
   - Logs de acesso para auditoria

2. **Sincronização Incremental**
   - Parâmetro `since` para buscar apenas registros atualizados
   - Campo `last_updated` ou similar em cada tabela
   - Reduz tráfego de rede e processamento

3. **Metadados do Servidor**
   - `backend_id`: Identificador único do servidor
   - `server_name`: Nome do servidor
   - `version`: Versão do SSM
   - `timestamp`: Timestamp da resposta

4. **Formato Padronizado**
   - JSON estruturado e consistente
   - Opção de CSV para importação direta
   - Metadata sempre incluída

5. **Performance**
   - Suporte a grandes volumes (até 5000 registros por página)
   - Paginação eficiente
   - Timeout de 30 segundos

---

## ❓ Perguntas para Decisão

1. **Qual opção você prefere?**
   - [x] Opção 1: Whitelist (Recomendada para sistema externo)
   - [ ] Opção 2: Schema Dinâmico
   - [ ] Opção 3: Blacklist
   - [ ] Opção 4: Configuração por Tabela

2. **Quais tabelas devem ser permitidas?**
   - Todas as listadas acima?
   - Alguma específica?
   - Alguma deve ser excluída? (ex: `elevated_user`, `player_gps_snapshot`)

3. **Autenticação:**
   - API Key no header? (Recomendado)
   - Token JWT?
   - IP Whitelist adicional?

4. **Sincronização Incremental:**
   - Campo padrão `last_updated`?
   - Ou campo específico por tabela?
   - Formato de data/hora (ISO 8601)?

5. **Campos sensíveis:**
   - Algum campo deve ser ocultado?
   - Diferentes níveis de acesso por API key?

6. **Performance:**
   - Limite máximo de registros por página? (5000?)
   - Precisa de cache?
   - Timeout de query? (30s?)

---

## 📝 Próximos Passos

Após decidir as opções acima, podemos implementar:
1. Sistema de autenticação por API Key
2. Endpoint base com validações de segurança
3. Sistema de whitelist de tabelas
4. Parâmetros de paginação e ordenação
5. Sincronização incremental (since, last_updated)
6. Metadados do servidor na resposta
7. Suporte a formato CSV (opcional)
8. Rate limiting por API key
9. Logs de acesso para auditoria
10. Documentação completa da API
11. Testes de segurança e performance

---

## 🔐 Sistema de Autenticação Proposto

### **Configuração de API Keys**

```json
{
  "external_api": {
    "enabled": true,
    "api_keys": [
      {
        "key": "sk_live_abc123...",
        "name": "Sistema Central de Gestão",
        "allowed_tables": ["players", "rankings", "survival_stats_snapshot"],
        "rate_limit": {
          "requests_per_minute": 60,
          "requests_per_hour": 1000
        },
        "created_at": "2025-01-15T10:00:00Z",
        "last_used": "2025-01-15T10:30:00Z"
      }
    ]
  }
}
```

### **Validação de API Key**

```python
def validate_api_key(api_key: str) -> Dict[str, Any]:
    """
    Validar API key e retornar permissões
    
    Returns:
        {
            "valid": bool,
            "name": str,
            "allowed_tables": List[str],
            "rate_limit": Dict
        }
    """
    # Verificar se API key existe e está ativa
    # Retornar permissões e limites
    pass
```

---

## 📊 Exemplo de Uso pelo Sistema Central

### **Sincronização Inicial (Full Sync)**

```bash
# Buscar todos os players
GET /api/table/players?limit=5000&sort_by=last_updated&sort_order=asc
Authorization: Bearer sk_live_abc123...
```

### **Sincronização Incremental (Delta Sync)**

```bash
# Buscar apenas players atualizados desde última sincronização
GET /api/table/players?since=2025-01-15T10:00:00Z&limit=5000&sort_by=last_updated&sort_order=asc
Authorization: Bearer sk_live_abc123...
```

### **Buscar Rankings**

```bash
# Buscar top 100 players por kills
GET /api/table/rankings?limit=100&sort_by=kills&sort_order=desc
Authorization: Bearer sk_live_abc123...
```

---

## 🚀 Vantagens para Sistema Central

1. **Padronização**: Todos os servidores usam o mesmo formato
2. **Eficiência**: Sincronização incremental reduz tráfego
3. **Segurança**: API keys controlam acesso
4. **Escalabilidade**: Suporta múltiplos servidores
5. **Auditoria**: Logs de todas as requisições
6. **Flexibilidade**: Pode escolher campos e ordenação

