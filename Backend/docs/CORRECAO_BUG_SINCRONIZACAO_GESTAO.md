# 🐛 Correção de Bug: Erro 500 no Endpoint de Sincronização

> **Destinatário**: Desenvolvedor do Gestão  
> **Prioridade**: Alta  
> **Data**: 2025-01-15  
> **Status**: Bug identificado - Correção necessária

---

## 📋 Resumo do Problema

O endpoint **POST `/api/v1/servers/sync`** está retornando erro **500 (Internal Server Error)** ao processar dados de sincronização do SSM Backend.

### **Erro Retornado:**
```json
{
  "detail": "Erro interno ao processar sincronização: float() argument must be a string or a real number, not 'NoneType'"
}
```

### **Status dos Endpoints:**
- ✅ **GET `/api/v1/servers/ready`** - Funcionando corretamente (200 OK)
- ❌ **POST `/api/v1/servers/sync`** - Erro 500 ao processar dados

---

## 🔍 Análise do Problema

### **Causa Raiz:**
O erro indica que o código do Gestão está tentando converter um valor `None` para `float()`, o que causa uma exceção `TypeError`.

### **Campos Prováveis:**
Baseado na estrutura do payload, os campos que podem estar causando o problema são:

1. **`fame`** (float) - Pode ser `None` se o jogador não tiver fama
2. **`score`** (float/int) - Pode ser `None` em rankings vazios
3. **`kdr`** (float) - Kill/Death Ratio pode ser `None`
4. **`deaths`** (int) - Pode ser `None` se não houver deaths
5. **`last_seen`** (string/null) - Pode ser `None` para jogadores nunca vistos

### **Exemplo de Payload Enviado:**
```json
{
  "server_hash": "9bec6bc7379a5ce11db5430cd3fe536db7cdbcf133442a4accebc228be795be0",
  "api_key": "ssm_207d80c3a1e87d90f5b893591001e55ef0b043b58b2a803637535db110939c10",
  "server_info": {
    "name": "Servidor Teste SSM",
    "version": "3.0.105",
    "max_players": 64,
    "current_players": 0
  },
  "players": [
    {
      "steam_id": "76561198012345678",
      "name": "PlayerTest",
      "fame": 50000,
      "is_online": false,
      "last_seen": null  // ← Pode ser null
    }
  ],
  "rankings": {
    "kills": [
      {
        "steam_id": "76561198012345678",
        "name": "PlayerTest",
        "score": 150,
        "kdr": 6.0,
        "deaths": 25
      }
    ],
    "survival": [],  // ← Array vazio
    "lockpicking": [],  // ← Array vazio
    "fishing": []  // ← Array vazio
  },
  "timestamp": "2025-01-15T10:30:00Z"
}
```

---

## 🔧 Correções Necessárias

### **1. Validação e Tratamento de Valores None**

Implementar validação e tratamento de valores `None` antes de converter para `float()` ou `int()`.

#### **Exemplo em Python:**
```python
# ❌ Código problemático (atual)
fame = float(player_data.get('fame'))  # Erro se fame for None

# ✅ Código corrigido
fame = player_data.get('fame')
if fame is None:
    fame = 0.0
else:
    fame = float(fame)
```

#### **Função Helper Recomendada:**
```python
def safe_float(value, default=0.0):
    """Converte valor para float de forma segura"""
    if value is None:
        return default
    try:
        return float(value)
    except (ValueError, TypeError):
        return default

def safe_int(value, default=0):
    """Converte valor para int de forma segura"""
    if value is None:
        return default
    try:
        return int(value)
    except (ValueError, TypeError):
        return default
```

### **2. Validação de Campos Obrigatórios**

Validar que campos obrigatórios estão presentes e têm valores válidos:

```python
# Validar player
def validate_player(player_data):
    required_fields = ['steam_id', 'name']
    for field in required_fields:
        if field not in player_data or player_data[field] is None:
            raise ValueError(f"Campo obrigatório '{field}' ausente ou None")
    
    # Campos opcionais com valores padrão
    player_data['fame'] = safe_float(player_data.get('fame'), 0.0)
    player_data['is_online'] = bool(player_data.get('is_online', False))
    player_data['last_seen'] = player_data.get('last_seen')  # Pode ser None
    
    return player_data
```

### **3. Tratamento de Arrays Vazios**

Garantir que arrays vazios não causem erros:

```python
# Processar rankings
rankings = payload.get('rankings', {})
for category, items in rankings.items():
    if not items:  # Array vazio
        continue  # Pular categoria vazia
    
    for item in items:
        # Validar e processar cada item
        item['score'] = safe_float(item.get('score'), 0.0)
        item['kdr'] = safe_float(item.get('kdr'), 0.0)
        item['deaths'] = safe_int(item.get('deaths'), 0)
```

### **4. Validação Completa do Payload**

Implementar validação completa antes de processar:

```python
def validate_sync_payload(payload):
    """Validar payload completo de sincronização"""
    errors = []
    
    # Validar campos obrigatórios do nível raiz
    if not payload.get('server_hash'):
        errors.append("server_hash é obrigatório")
    if not payload.get('api_key'):
        errors.append("api_key é obrigatório")
    if not payload.get('server_info'):
        errors.append("server_info é obrigatório")
    if not payload.get('players'):
        errors.append("players é obrigatório (pode ser array vazio)")
    if not payload.get('rankings'):
        errors.append("rankings é obrigatório")
    
    # Validar server_info
    server_info = payload.get('server_info', {})
    server_info['max_players'] = safe_int(server_info.get('max_players'), 0)
    server_info['current_players'] = safe_int(server_info.get('current_players'), 0)
    
    # Validar players
    players = payload.get('players', [])
    for i, player in enumerate(players):
        try:
            validate_player(player)
        except ValueError as e:
            errors.append(f"Player[{i}]: {str(e)}")
    
    # Validar rankings
    rankings = payload.get('rankings', {})
    for category, items in rankings.items():
        if not isinstance(items, list):
            errors.append(f"rankings.{category} deve ser um array")
            continue
        
        for j, item in enumerate(items):
            if not isinstance(item, dict):
                errors.append(f"rankings.{category}[{j}] deve ser um objeto")
                continue
            
            # Validar campos numéricos
            item['score'] = safe_float(item.get('score'), 0.0)
            if 'kdr' in item:
                item['kdr'] = safe_float(item.get('kdr'), 0.0)
            if 'deaths' in item:
                item['deaths'] = safe_int(item.get('deaths'), 0)
    
    if errors:
        raise ValueError(f"Erros de validação: {', '.join(errors)}")
    
    return payload
```

---

## 📝 Implementação Sugerida

### **Estrutura de Tratamento de Erros:**

```python
@app.post("/api/v1/servers/sync")
async def sync_servers(payload: dict):
    try:
        # 1. Validar payload
        validated_payload = validate_sync_payload(payload)
        
        # 2. Validar autenticação (server_hash + api_key)
        server = await validate_server_auth(
            validated_payload['server_hash'],
            validated_payload['api_key']
        )
        
        # 3. Processar dados com valores seguros
        result = await process_sync_data(server, validated_payload)
        
        return {
            "success": True,
            "message": "Dados sincronizados com sucesso",
            "server_id": server.id,
            "players_synced": result['players_count'],
            "rankings_synced": result['rankings_count'],
            "timestamp": validated_payload['timestamp']
        }
        
    except ValueError as e:
        # Erro de validação
        return JSONResponse(
            status_code=400,
            content={
                "success": False,
                "error": "Dados inválidos",
                "detail": str(e)
            }
        )
    except Exception as e:
        # Erro interno
        logger.error(f"Erro ao processar sincronização: {e}", exc_info=True)
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "error": "Erro interno ao processar sincronização",
                "detail": str(e)  # Em produção, não expor detalhes do erro
            }
        )
```

---

## 🧪 Testes Recomendados

### **Teste 1: Payload com Valores None**
```json
{
  "server_hash": "...",
  "api_key": "...",
  "server_info": {...},
  "players": [
    {
      "steam_id": "76561198012345678",
      "name": "TestPlayer",
      "fame": null,  // ← None
      "is_online": false,
      "last_seen": null  // ← None
    }
  ],
  "rankings": {
    "kills": [
      {
        "steam_id": "76561198012345678",
        "name": "TestPlayer",
        "score": null,  // ← None
        "kdr": null,  // ← None
        "deaths": null  // ← None
      }
    ]
  }
}
```

**Resultado Esperado:** Deve processar sem erro, usando valores padrão (0.0 para float, 0 para int).

### **Teste 2: Arrays Vazios**
```json
{
  "players": [],
  "rankings": {
    "kills": [],
    "survival": [],
    "lockpicking": [],
    "fishing": []
  }
}
```

**Resultado Esperado:** Deve processar sem erro, simplesmente não sincronizando dados.

### **Teste 3: Campos Faltando**
```json
{
  "server_hash": "...",
  "api_key": "...",
  "server_info": {
    "name": "Test",
    // max_players e current_players faltando
  }
}
```

**Resultado Esperado:** Deve usar valores padrão (0) ou retornar erro 400 se obrigatório.

---

## ✅ Checklist de Correção

- [ ] Implementar função `safe_float()` para conversão segura
- [ ] Implementar função `safe_int()` para conversão segura
- [ ] Validar todos os campos numéricos antes de processar
- [ ] Tratar valores `None` com valores padrão apropriados
- [ ] Validar arrays vazios (não devem causar erro)
- [ ] Adicionar tratamento de exceções adequado
- [ ] Adicionar logging de erros para debug
- [ ] Testar com payload contendo valores `None`
- [ ] Testar com arrays vazios
- [ ] Testar com campos faltando
- [ ] Atualizar documentação da API se necessário

---

## 📊 Exemplo de Código Completo

```python
# helpers.py
def safe_float(value, default=0.0):
    """Converte valor para float de forma segura"""
    if value is None:
        return default
    try:
        return float(value)
    except (ValueError, TypeError):
        return default

def safe_int(value, default=0):
    """Converte valor para int de forma segura"""
    if value is None:
        return default
    try:
        return int(value)
    except (ValueError, TypeError):
        return default

def validate_and_normalize_player(player_data):
    """Validar e normalizar dados do jogador"""
    if not player_data.get('steam_id'):
        raise ValueError("steam_id é obrigatório")
    if not player_data.get('name'):
        raise ValueError("name é obrigatório")
    
    return {
        'steam_id': str(player_data['steam_id']),
        'name': str(player_data['name']),
        'fame': safe_float(player_data.get('fame'), 0.0),
        'is_online': bool(player_data.get('is_online', False)),
        'last_seen': player_data.get('last_seen')  # Pode ser None
    }

def validate_and_normalize_ranking_item(item, category):
    """Validar e normalizar item de ranking"""
    if not item.get('steam_id'):
        raise ValueError(f"steam_id é obrigatório em ranking.{category}")
    if not item.get('name'):
        raise ValueError(f"name é obrigatório em ranking.{category}")
    
    normalized = {
        'steam_id': str(item['steam_id']),
        'name': str(item['name']),
        'score': safe_float(item.get('score'), 0.0)
    }
    
    # Campos específicos por categoria
    if category == 'kills':
        normalized['kdr'] = safe_float(item.get('kdr'), 0.0)
        normalized['deaths'] = safe_int(item.get('deaths'), 0)
    elif category == 'survival':
        normalized['fame'] = safe_float(item.get('fame'), 0.0)
    elif category == 'lockpicking':
        normalized['basic_rate'] = safe_float(item.get('basic_rate'), 0.0)
        normalized['medium_rate'] = safe_float(item.get('medium_rate'), 0.0)
        normalized['advanced_rate'] = safe_float(item.get('advanced_rate'), 0.0)
    
    return normalized

# sync_handler.py
async def process_sync_data(server, payload):
    """Processar dados de sincronização"""
    try:
        # Normalizar server_info
        server_info = payload.get('server_info', {})
        server_info['max_players'] = safe_int(server_info.get('max_players'), 0)
        server_info['current_players'] = safe_int(server_info.get('current_players'), 0)
        
        # Processar players
        players_count = 0
        players_data = payload.get('players', [])
        for player_data in players_data:
            try:
                normalized_player = validate_and_normalize_player(player_data)
                await sync_player(server.id, normalized_player)
                players_count += 1
            except Exception as e:
                logger.warning(f"Erro ao processar player {player_data.get('steam_id')}: {e}")
                continue
        
        # Processar rankings
        rankings_count = 0
        rankings_data = payload.get('rankings', {})
        for category, items in rankings_data.items():
            if not isinstance(items, list):
                continue
            
            for item in items:
                try:
                    normalized_item = validate_and_normalize_ranking_item(item, category)
                    await sync_ranking(server.id, category, normalized_item)
                    rankings_count += 1
                except Exception as e:
                    logger.warning(f"Erro ao processar ranking {category}: {e}")
                    continue
        
        return {
            'players_count': players_count,
            'rankings_count': rankings_count
        }
        
    except Exception as e:
        logger.error(f"Erro ao processar sincronização: {e}", exc_info=True)
        raise
```

---

## 🔗 Referências

- Documentação de implementação: `docs/GESTAO_IMPLEMENTACAO_ENDPOINTS.md`
- Estrutura do payload: Ver seção "Estrutura Detalhada do Payload" na documentação

---

## 📞 Contato

Em caso de dúvidas sobre a estrutura do payload ou comportamento esperado, consulte a documentação completa ou entre em contato com a equipe do SSM Backend.

---

**Versão**: 1.0  
**Última Atualização**: 2025-01-15

