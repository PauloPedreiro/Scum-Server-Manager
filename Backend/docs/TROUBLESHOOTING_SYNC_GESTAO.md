# 🔍 Troubleshooting: Erro "Servidor não encontrado ou credenciais inválidas"

> **Status**: ✅ **RESOLVIDO** - Correções implementadas pelo desenvolvedor do Gestão (2025-01-15)

## ✅ Status Atual

- **GET `/api/v1/servers/ready`**: ✅ Funcionando (retorna `{"ready": true}`)
- **POST `/api/v1/servers/sync`**: ✅ **CORRIGIDO** - Validação melhorada com logs detalhados e mensagens específicas

---

## 🔍 Análise do Problema

O erro `"Servidor não encontrado ou credenciais inválidas"` indica que:

1. **O servidor não está cadastrado no Gestão** com o `server_hash` fornecido, OU
2. **A API key não corresponde** ao `server_hash` cadastrado no Gestão

---

## ✅ Checklist de Verificação

### 1. **Servidor Cadastrado no Gestão?**

Verifique no banco de dados do Gestão se existe um registro com:
- `server_hash` = `9bec6bc7379a5ce11db5430cd3fe536db7cdbcf133442a4accebc228be795be0`

**Query SQL (exemplo):**
```sql
SELECT * FROM server WHERE server_hash = '9bec6bc7379a5ce11db5430cd3fe536db7cdbcf133442a4accebc228be795be0';
```

**Se não existir:**
- O servidor precisa ser cadastrado no Gestão primeiro
- Use o hash fornecido: `9bec6bc7379a5ce11db5430cd3fe536db7cdbcf133442a4accebc228be795be0`

---

### 2. **API Key Corresponde ao Servidor?**

Verifique se a API key cadastrada no Gestão corresponde à API key enviada:

**API Key enviada:**
```
ssm_207d80c3a1e87d90f5b893591001e55ef0b043b58b2a803637535db110939c10
```

**Query SQL (exemplo):**
```sql
SELECT server_hash, api_key FROM server 
WHERE server_hash = '9bec6bc7379a5ce11db5430cd3fe536db7cdbcf133442a4accebc228be795be0';
```

**Verificar:**
- A `api_key` no banco deve ser exatamente: `ssm_207d80c3a1e87d90f5b893591001e55ef0b043b58b2a803637535db110939c10`
- Se for diferente, atualize no banco OU use a API key correta no Postman

---

### 3. **Servidor Ativo?**

Verifique se o servidor está marcado como ativo:

```sql
SELECT server_hash, api_key, is_active FROM server 
WHERE server_hash = '9bec6bc7379a5ce11db5430cd3fe536db7cdbcf133442a4accebc228be795be0';
```

**Se `is_active = false`:**
- Ative o servidor: `UPDATE server SET is_active = true WHERE server_hash = '...';`

---

## 🔧 Soluções

### Solução 1: Cadastrar Servidor no Gestão

Se o servidor não está cadastrado, cadastre-o:

**Opção A: Via Interface do Gestão**
1. Acesse a interface administrativa do Gestão
2. Vá em "Servidores" → "Cadastrar Novo"
3. Preencha:
   - **Server Hash**: `9bec6bc7379a5ce11db5430cd3fe536db7cdbcf133442a4accebc228be795be0`
   - **Nome**: Nome do servidor (ex: "Meu Servidor SCUM")
   - O Gestão gerará uma API key automaticamente

**Opção B: Via SQL (se tiver acesso direto ao banco)**
```sql
INSERT INTO server (
    server_hash,
    server_name,
    api_key,
    is_active,
    created_at,
    updated_at
) VALUES (
    '9bec6bc7379a5ce11db5430cd3fe536db7cdbcf133442a4accebc228be795be0',
    'Meu Servidor SCUM',
    'ssm_207d80c3a1e87d90f5b893591001e55ef0b043b58b2a803637535db110939c10',
    true,
    CURRENT_TIMESTAMP,
    CURRENT_TIMESTAMP
);
```

---

### Solução 2: Atualizar API Key

Se o servidor existe mas a API key está diferente:

**Opção A: Via Interface do Gestão**
1. Acesse o servidor no Gestão
2. Atualize a API key para: `ssm_207d80c3a1e87d90f5b893591001e55ef0b043b58b2a803637535db110939c10`

**Opção B: Via SQL**
```sql
UPDATE server 
SET api_key = 'ssm_207d80c3a1e87d90f5b893591001e55ef0b043b58b2a803637535db110939c10',
    updated_at = CURRENT_TIMESTAMP
WHERE server_hash = '9bec6bc7379a5ce11db5430cd3fe536db7cdbcf133442a4accebc228be795be0';
```

---

### Solução 3: Ativar Servidor

Se o servidor existe mas está inativo:

```sql
UPDATE server 
SET is_active = true,
    updated_at = CURRENT_TIMESTAMP
WHERE server_hash = '9bec6bc7379a5ce11db5430cd3fe536db7cdbcf133442a4accebc228be795be0';
```

---

## 🧪 Teste Após Correção

Após cadastrar/atualizar o servidor, teste novamente:

**POST `/api/v1/servers/sync`**

**Resposta esperada (200 OK):**
```json
{
  "success": true,
  "message": "Sincronização concluída com sucesso",
  "server_id": 2,
  "players_synced": 1,
  "rankings_synced": 0
}
```

---

## 📋 Informações para o Desenvolvedor do Gestão

Se o problema persistir, verifique no código do Gestão:

### 1. **Validação do Servidor**

O código deve verificar:
```python
# Buscar servidor
server = Server.query.filter_by(server_hash=payload['server_hash']).first()

if not server:
    return {"detail": "Servidor não encontrado ou credenciais inválidas"}, 404

# Verificar se está ativo
if not server.is_active:
    return {"detail": "Servidor inativo"}, 403

# Validar API key
if server.api_key != payload['api_key']:
    return {"detail": "Servidor não encontrado ou credenciais inválidas"}, 401
```

### 2. **Logs do Gestão**

Verifique os logs do Gestão para ver:
- Se o servidor está sendo encontrado no banco
- Se a API key está sendo validada corretamente
- Qual é o erro exato retornado

---

## 🔗 Referências

- Documentação de implementação: `docs/GESTAO_IMPLEMENTACAO_ENDPOINTS.md`
- Endpoints corretos: `docs/ENDPOINTS_GESTAO_CORRETOS.md`
- Correção de bug: `docs/CORRECAO_BUG_SINCRONIZACAO_GESTAO.md`

---

---

## ✅ Correções Implementadas (2025-01-15)

O desenvolvedor do Gestão implementou as seguintes melhorias:

- ✅ Sanitização automática de inputs (remoção de espaços)
- ✅ Validação progressiva (Server → Machine → API Key)
- ✅ Logs detalhados em cada etapa
- ✅ Mensagens de erro específicas para cada caso
- ✅ Status codes HTTP corretos (400, 401, 403, 404)

**Ver documentação completa:** `docs/CORRECAO_VALIDACAO_GESTAO_CONFIRMADA.md`

---

**Última atualização:** 2025-01-15

