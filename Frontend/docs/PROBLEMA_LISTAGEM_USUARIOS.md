# 🐛 Problema: Listagem de Usuários Retorna Data Vazio

**Data:** 2025-12-05  
**Prioridade:** Alta  
**Status:** 🔴 **PROBLEMA IDENTIFICADO**

---

## 📋 Descrição do Problema

O endpoint `GET /api/auth/users` está retornando `success: true` mas com `data: {}` (objeto vazio), quando deveria retornar `data: { users: [...], total: X }`.

---

## 🔍 Evidências

### **Resposta Atual do Backend:**

```json
{
  "success": true,
  "data": {}
}
```

### **Resposta Esperada:**

```json
{
  "success": true,
  "data": {
    "users": [
      {
        "id": 1,
        "username": "admin",
        "role": "admin",
        "is_active": true,
        "password_changed": true,
        "steam_id": null,
        "player_name": null,
        "player_id": null,
        "last_login": "2025-12-05T...",
        "created_at": "2025-12-04T..."
      },
      {
        "id": 2,
        "username": "pedreiro",
        "role": "moderator",
        "is_active": true,
        "password_changed": false,
        "steam_id": "76561198040636105",
        "player_name": "Player Name",
        "player_id": 123,
        "last_login": null,
        "created_at": "2025-12-05T..."
      }
    ],
    "total": 2
  }
}
```

---

## 🔍 Logs do Frontend

```
ListUsers - Response status: 200
ListUsers - Response data: {data: {}, success: true}
ListUsers - Usuários retornados: 0
```

---

## 🔍 Verificação no Banco de Dados

O banco de dados **tem usuários cadastrados**:
- `id: 1` - `username: "admin"` - `role: "admin"`
- `id: 2` - `username: "pedreiro"` - `role: "moderator"`
- `id: 4` - (usuário recém-criado)

---

## 🔧 Possíveis Causas

### **1. Query SQL Não Está Retornando Dados**

A query SQL pode estar com problema mesmo após a correção de `p.name` → `p.player_name`.

**Verificar:**
- Se a query está executando corretamente
- Se há algum erro silencioso sendo suprimido
- Se o JOIN com a tabela `players` está funcionando

### **2. Estrutura da Resposta Incorreta**

O código pode estar construindo a resposta incorretamente.

**Verificar:**
- Se `list_users()` está retornando os dados corretamente
- Se a estrutura `{"users": [...], "total": X}` está sendo criada
- Se há algum tratamento de erro que está retornando `{}` vazio

### **3. Erro Silencioso**

Pode haver um erro sendo capturado e suprimido, retornando objeto vazio.

**Verificar:**
- Logs do backend ao chamar `GET /api/auth/users`
- Se há exceções sendo capturadas silenciosamente
- Se a query está realmente executando

---

## 🧪 Como Reproduzir

1. Fazer login como admin
2. Acessar Settings → Users
3. Abrir Console do navegador (F12)
4. Verificar logs: `ListUsers - Response data: {data: {}, success: true}`
5. Verificar que não há usuários sendo exibidos

---

## 🔍 Verificações Necessárias no Backend

### **1. Verificar Query SQL**

```python
# No método list_users(), verificar se a query está assim:
query = """
    SELECT 
        u.id,
        u.username,
        u.role,
        u.is_active,
        u.password_changed,
        u.steam_id,
        p.player_name,  -- ✅ Deve ser player_name, não name
        p.id as player_id,
        u.last_login,
        u.created_at
    FROM frontend_users u
    LEFT JOIN players p ON u.steam_id = p.steam_id
"""
```

### **2. Verificar Construção da Resposta**

```python
# Verificar se está retornando assim:
users_list = cursor.fetchall()
users_data = [dict(row) for row in users_list]  # ou similar

return {
    "success": True,
    "data": {
        "users": users_data,  # ✅ Deve ter users aqui
        "total": len(users_data)  # ✅ Deve ter total aqui
    }
}
```

### **3. Verificar Logs do Backend**

Ao chamar `GET /api/auth/users`, verificar nos logs:
- Se a query está executando
- Se há erros sendo capturados
- Quantos registros estão sendo retornados

---

## 📝 Código Esperado no Backend

```python
def list_users():
    try:
        # Query SQL corrigida
        query = """
            SELECT 
                u.id,
                u.username,
                u.role,
                u.is_active,
                u.password_changed,
                u.steam_id,
                p.player_name,  -- ✅ CORRETO
                p.id as player_id,
                u.last_login,
                u.created_at
            FROM frontend_users u
            LEFT JOIN players p ON u.steam_id = p.steam_id
            ORDER BY u.created_at DESC
        """
        
        cursor.execute(query)
        rows = cursor.fetchall()
        
        # Converter para lista de dicionários
        users = []
        for row in rows:
            users.append({
                "id": row[0],
                "username": row[1],
                "role": row[2],
                "is_active": bool(row[3]),
                "password_changed": bool(row[4]),
                "steam_id": row[5],
                "player_name": row[6],
                "player_id": row[7],
                "last_login": row[8],
                "created_at": row[9].isoformat() if row[9] else None,
            })
        
        # Retornar estrutura correta
        return {
            "success": True,
            "data": {
                "users": users,  # ✅ IMPORTANTE: deve ter users aqui
                "total": len(users)  # ✅ IMPORTANTE: deve ter total aqui
            }
        }
    except Exception as e:
        logger.error(f"Erro ao listar usuários: {e}")
        return {
            "success": False,
            "error": str(e)
        }
```

---

## ✅ Checklist de Verificação

- [ ] Verificar se a query SQL está usando `p.player_name` (não `p.name`)
- [ ] Verificar se a query está executando sem erros
- [ ] Verificar se `cursor.fetchall()` está retornando dados
- [ ] Verificar se a estrutura da resposta tem `data.users` e `data.total`
- [ ] Verificar logs do backend ao chamar o endpoint
- [ ] Testar a query SQL diretamente no banco de dados
- [ ] Verificar se há tratamento de erro que está retornando `{}` vazio

---

## 🚨 Urgência

**ALTA** - A funcionalidade de listagem de usuários não está funcionando, impedindo o uso completo do sistema de gerenciamento.

---

**Última Atualização:** 2025-12-05

