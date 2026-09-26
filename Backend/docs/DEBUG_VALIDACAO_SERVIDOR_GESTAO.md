# 🐛 Debug: Validação de Servidor no Gestão

> **Destinatário**: Desenvolvedor do Gestão  
> **Prioridade**: Alta  
> **Data**: 2025-01-15  
> **Status**: Servidor cadastrado, mas validação falha

---

## ✅ Confirmação: Servidor Está Cadastrado

**Dados do Servidor no Dashboard:**
- **Hash**: `9bec6bc7379a5ce11db5430cd3fe536db7cdbcf133442a4accebc228be795be0`
- **API Key**: `ssm_207d80c3a1e87d90f5b893591001e55ef0b043b58b2a803637535db110939c10`
- **Nome**: `Scum Server Manager2`
- **Status**: Ativo (verificado no dashboard)

---

## ❌ Problema: Validação Falha

**Endpoint:** `POST /api/v1/servers/sync`

**Payload Enviado:**
```json
{
  "server_hash": "9bec6bc7379a5ce11db5430cd3fe536db7cdbcf133442a4accebc228be795be0",
  "api_key": "ssm_207d80c3a1e87d90f5b893591001e55ef0b043b58b2a803637535db110939c10",
  "server_info": {...},
  "players": [...],
  "rankings": {...},
  "timestamp": "2025-01-15T10:30:00Z"
}
```

**Resposta Recebida:**
```json
{
  "detail": "Servidor não encontrado ou credenciais inválidas"
}
```

**Status Code:** Provavelmente 401 ou 404

---

## 🔍 Possíveis Causas

### 1. **Busca no Banco de Dados**

Verifique se a query está correta:

```python
# ❌ Pode estar errado
server = Server.query.filter_by(server_hash=payload['server_hash']).first()

# ✅ Verificar:
# - O campo no banco se chama exatamente 'server_hash'?
# - Há espaços em branco ou caracteres invisíveis?
# - A busca é case-sensitive?
```

**Teste SQL Direto:**
```sql
SELECT * FROM server 
WHERE server_hash = '9bec6bc7379a5ce11db5430cd3fe536db7cdbcf133442a4accebc228be795be0';
```

**Verificar:**
- Se retorna o registro
- Se o campo `server_hash` está exatamente igual (sem espaços, sem caracteres especiais)
- Se o campo `api_key` está exatamente igual

---

### 2. **Validação da API Key**

Verifique se a comparação está correta:

```python
# ❌ Pode estar errado (comparação case-sensitive ou com espaços)
if server.api_key != payload['api_key']:
    return {"detail": "Servidor não encontrado ou credenciais inválidas"}, 401

# ✅ Verificar:
# - Há trim()/strip() sendo aplicado?
# - A comparação é exata ou há normalização?
# - Há encoding issues (UTF-8, etc)?
```

**Teste de Comparação:**
```python
# Adicionar logs para debug
print(f"API Key do banco: '{server.api_key}'")
print(f"API Key do payload: '{payload['api_key']}'")
print(f"São iguais? {server.api_key == payload['api_key']}")
print(f"Tamanho banco: {len(server.api_key)}")
print(f"Tamanho payload: {len(payload['api_key'])}")
```

---

### 3. **Servidor Inativo**

Verifique se o servidor está marcado como ativo:

```python
# Verificar se há validação de is_active
if not server.is_active:
    return {"detail": "Servidor inativo"}, 403
```

**Teste SQL:**
```sql
SELECT server_hash, api_key, is_active FROM server 
WHERE server_hash = '9bec6bc7379a5ce11db5430cd3fe536db7cdbcf133442a4accebc228be795be0';
```

**Verificar:**
- `is_active` está como `true` ou `1`?

---

### 4. **Problema de Encoding ou Espaços**

Verifique se há espaços em branco ou caracteres invisíveis:

```python
# Adicionar sanitização
server_hash = payload['server_hash'].strip()
api_key = payload['api_key'].strip()

server = Server.query.filter_by(server_hash=server_hash).first()
```

---

### 5. **Tipo de Dados no Banco**

Verifique o tipo do campo no banco:

```sql
-- Se for VARCHAR com tamanho limitado, pode estar truncando
DESCRIBE server;
-- ou
PRAGMA table_info(server);  -- SQLite
```

**Verificar:**
- O campo `server_hash` tem tamanho suficiente? (precisa de 64 caracteres)
- O campo `api_key` tem tamanho suficiente? (precisa de 68 caracteres: `ssm_` + 64 hex)

---

## 🔧 Código de Validação Sugerido

```python
@app.post("/api/v1/servers/sync")
async def sync_servers(payload: dict):
    try:
        # 1. Sanitizar inputs
        server_hash = payload.get('server_hash', '').strip()
        api_key = payload.get('api_key', '').strip()
        
        # 2. Validar formato
        if not server_hash or len(server_hash) != 64:
            return JSONResponse(
                status_code=400,
                content={"detail": "server_hash inválido"}
            )
        
        if not api_key or not api_key.startswith('ssm_'):
            return JSONResponse(
                status_code=400,
                content={"detail": "api_key inválida"}
            )
        
        # 3. Buscar servidor (com logs para debug)
        server = Server.query.filter_by(server_hash=server_hash).first()
        
        # LOG PARA DEBUG
        logger.info(f"Buscando servidor com hash: {server_hash}")
        logger.info(f"Servidor encontrado: {server is not None}")
        
        if not server:
            logger.warning(f"Servidor não encontrado: {server_hash}")
            return JSONResponse(
                status_code=404,
                content={"detail": "Servidor não encontrado ou credenciais inválidas"}
            )
        
        # LOG PARA DEBUG
        logger.info(f"API Key do banco: '{server.api_key}'")
        logger.info(f"API Key do payload: '{api_key}'")
        logger.info(f"São iguais? {server.api_key == api_key}")
        
        # 4. Verificar se está ativo
        if not server.is_active:
            logger.warning(f"Servidor inativo: {server_hash}")
            return JSONResponse(
                status_code=403,
                content={"detail": "Servidor inativo"}
            )
        
        # 5. Validar API key (comparação exata)
        if server.api_key.strip() != api_key:
            logger.warning(f"API Key não corresponde. Banco: '{server.api_key}', Payload: '{api_key}'")
            return JSONResponse(
                status_code=401,
                content={"detail": "Servidor não encontrado ou credenciais inválidas"}
            )
        
        # 6. Processar sincronização
        # ... resto do código ...
        
    except Exception as e:
        logger.error(f"Erro ao processar sincronização: {e}", exc_info=True)
        return JSONResponse(
            status_code=500,
            content={"detail": f"Erro interno: {str(e)}"}
        )
```

---

## 🧪 Testes Recomendados

### Teste 1: Query SQL Direta

```sql
SELECT 
    server_hash,
    api_key,
    is_active,
    LENGTH(server_hash) as hash_length,
    LENGTH(api_key) as key_length
FROM server 
WHERE server_hash = '9bec6bc7379a5ce11db5430cd3fe536db7cdbcf133442a4accebc228be795be0';
```

**Resultado esperado:**
- `server_hash`: `9bec6bc7379a5ce11db5430cd3fe536db7cdbcf133442a4accebc228be795be0`
- `api_key`: `ssm_207d80c3a1e87d90f5b893591001e55ef0b043b58b2a803637535db110939c10`
- `is_active`: `true` ou `1`
- `hash_length`: `64`
- `key_length`: `68`

### Teste 2: Comparação de Strings

```python
# No código do Gestão, adicionar:
db_hash = server.server_hash
db_key = server.api_key
payload_hash = payload['server_hash']
payload_key = payload['api_key']

print(f"Hash DB: '{db_hash}' (len={len(db_hash)})")
print(f"Hash Payload: '{payload_hash}' (len={len(payload_hash)})")
print(f"Hash iguais? {db_hash == payload_hash}")
print(f"Key DB: '{db_key}' (len={len(db_key)})")
print(f"Key Payload: '{payload_key}' (len={len(payload_key)})")
print(f"Key iguais? {db_key == payload_key}")
```

---

## 📋 Checklist de Verificação

- [ ] Query SQL retorna o servidor corretamente
- [ ] Campo `server_hash` no banco está exatamente igual ao enviado (sem espaços)
- [ ] Campo `api_key` no banco está exatamente igual ao enviado (sem espaços)
- [ ] `is_active` está como `true` no banco
- [ ] Comparação de strings está sendo feita corretamente (sem normalização indevida)
- [ ] Não há problemas de encoding (UTF-8)
- [ ] Logs estão sendo gerados para debug
- [ ] Status code retornado é o correto (401 vs 404)

---

## 🔗 Referências

- Documentação de implementação: `docs/GESTAO_IMPLEMENTACAO_ENDPOINTS.md`
- Troubleshooting: `docs/TROUBLESHOOTING_SYNC_GESTAO.md`

---

**Última atualização:** 2025-01-15

