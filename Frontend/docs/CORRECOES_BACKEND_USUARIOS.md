# 🔧 Correções Necessárias - Sistema de Gerenciamento de Usuários

**Data:** 2025-12-05  
**Versão:** 1.0  
**Prioridade:** Alta  
**Status:** ✅ **CORRIGIDO PELO BACKEND** (Ver `docs/CORRECOES_BACKEND_CONFIRMADAS.md`)

---

## 📋 Resumo Executivo

Durante a implementação e testes do sistema de gerenciamento de usuários no frontend, foram identificados **dois problemas críticos** no backend que impedem o funcionamento correto do sistema:

1. **Erro no logger ao criar usuário** - Retorna HTTP 500 mesmo quando o usuário é criado com sucesso
2. **Erro na query SQL ao listar usuários** - Coluna `p.name` não existe no banco de dados

---

## 🐛 Problema 1: Erro no Logger ao Criar Usuário

### **Descrição do Problema**

Ao criar um novo usuário através do endpoint `POST /api/auth/users`, o backend retorna HTTP 500 com a seguinte mensagem de erro:

```
StructuredLogger.error() got an unexpected keyword argument 'exc_info'
```

**Comportamento Observado:**
- ✅ O usuário **é criado com sucesso** no banco de dados
- ❌ O backend retorna erro HTTP 500
- ❌ O frontend interpreta como falha e mostra mensagem de erro

### **Logs do Backend**

```
2025-12-05 10:51:30,180 - scum_backend - ERROR - {"timestamp": "2025-12-05T10:51:30.180883", "level": "ERROR", "message": "Erro ao criar usuário: StructuredLogger.error() got an unexpected keyword argument 'exc_info'"}
192.168.100.3 - - [05/Dec/2025 10:51:30] "POST /api/auth/users HTTP/1.1" 500 -
```

### **Causa Raiz**

O código está tentando usar o argumento `exc_info` no método `StructuredLogger.error()`, mas esse argumento não é suportado pela implementação atual do logger.

### **Localização Provável**

No arquivo que implementa o endpoint `POST /api/auth/users`, provavelmente algo como:

```python
# Código problemático (exemplo)
logger.error("Erro ao criar usuário", exc_info=True)  # ❌ Não funciona
```

### **Solução Proposta**

**Opção 1: Remover o argumento `exc_info`**
```python
# Correção
logger.error("Erro ao criar usuário")  # ✅ Funciona
```

**Opção 2: Usar `exception=True` (se suportado)**
```python
# Alternativa
logger.error("Erro ao criar usuário", exception=True)  # Verificar se suportado
```

**Opção 3: Usar `logger.exception()` para logs de exceção**
```python
# Melhor prática para exceções
try:
    # código que pode gerar exceção
    pass
except Exception as e:
    logger.exception("Erro ao criar usuário")  # ✅ Automaticamente inclui traceback
```

### **Impacto**

- **Severidade:** Alta
- **Usuários Afetados:** Todos os administradores tentando criar novos usuários
- **Workaround Atual:** Frontend trata como sucesso parcial quando detecta erro do logger

---

## 🐛 Problema 2: Erro na Query SQL ao Listar Usuários

### **Descrição do Problema**

Ao listar usuários através do endpoint `GET /api/auth/users`, o backend retorna HTTP 200 mas com erro na resposta:

```
no such column: p.name
```

**Comportamento Observado:**
- ❌ A query SQL está tentando buscar uma coluna `p.name` que não existe
- ❌ O frontend não consegue exibir a lista de usuários
- ✅ O endpoint retorna HTTP 200 (não 500), mas com erro na resposta

### **Logs do Backend**

```
2025-12-05 10:50:56,791 - scum_backend - ERROR - {"timestamp": "2025-12-05T10:50:56.790931", "level": "ERROR", "message": "Erro ao listar usuários: no such column: p.name"}
192.168.100.3 - - [05/Dec/2025 10:50:56] "GET /api/auth/users HTTP/1.1" 200 -
```

### **Causa Raiz**

A query SQL está usando um alias `p` para a tabela `players` e tentando acessar `p.name`, mas a coluna correta é `p.player_name`.

### **Estrutura do Banco de Dados**

Baseado na análise do banco de dados `SSM.db`, a tabela `players` possui:
- ✅ `player_name` (nome do jogador)
- ✅ `steam_id` (Steam ID)
- ❌ `name` (não existe)

### **Query SQL Problemática (Estimada)**

```sql
-- Query provavelmente está assim (ERRADA):
SELECT 
    u.*,
    p.name as player_name  -- ❌ p.name não existe
FROM frontend_users u
LEFT JOIN players p ON u.steam_id = p.steam_id
```

### **Solução Proposta**

```sql
-- Query corrigida:
SELECT 
    u.*,
    p.player_name as player_name  -- ✅ Usar p.player_name
FROM frontend_users u
LEFT JOIN players p ON u.steam_id = p.steam_id
```

### **Localização Provável**

No arquivo que implementa o endpoint `GET /api/auth/users`, provavelmente em uma função como:

```python
def list_users():
    query = """
        SELECT 
            u.id,
            u.username,
            u.role,
            u.is_active,
            u.password_changed,
            u.steam_id,
            p.player_name,  # ✅ Corrigir aqui
            p.player_id,
            u.last_login,
            u.created_at
        FROM frontend_users u
        LEFT JOIN players p ON u.steam_id = p.steam_id
    """
```

### **Impacto**

- **Severidade:** Crítica
- **Usuários Afetados:** Todos os administradores tentando visualizar a lista de usuários
- **Workaround Atual:** Nenhum - a funcionalidade não funciona

---

## 📊 Resumo dos Endpoints Afetados

| Endpoint | Método | Status HTTP | Problema | Impacto |
|----------|--------|-------------|----------|----------|
| `/api/auth/users` | POST | 500 | Erro no logger | Usuário criado mas retorna erro |
| `/api/auth/users` | GET | 200 | Query SQL incorreta | Lista não funciona |

---

## ✅ Checklist de Correções

### **Problema 1: Logger**
- [ ] Localizar o código que usa `logger.error(..., exc_info=True)`
- [ ] Remover o argumento `exc_info` ou usar `logger.exception()`
- [ ] Testar criação de usuário
- [ ] Verificar se retorna HTTP 201/200 com `success: true`
- [ ] Verificar logs do backend (não deve ter erro)

### **Problema 2: Query SQL**
- [ ] Localizar a query SQL no endpoint `GET /api/auth/users`
- [ ] Trocar `p.name` por `p.player_name`
- [ ] Testar listagem de usuários
- [ ] Verificar se retorna lista completa com `player_name` preenchido
- [ ] Verificar logs do backend (não deve ter erro)

---

## 🧪 Testes Recomendados

### **Teste 1: Criar Usuário**

**Request:**
```http
POST /api/auth/users
Authorization: Bearer <token>
Content-Type: application/json

{
  "username": "teste_user",
  "password": "senha123456",
  "role": "moderator",
  "steam_id": "76561198012345678"
}
```

**Response Esperada (Corrigido):**
```json
{
  "success": true,
  "data": {
    "id": 3,
    "username": "teste_user",
    "role": "moderator",
    "is_active": true,
    "password_changed": false,
    "steam_id": "76561198012345678",
    "player_name": "Player Name",
    "created_at": "2025-12-05T10:55:00",
    "message": "User created. Password must be changed on first login."
  }
}
```

**Status HTTP:** `201 Created` ou `200 OK`

### **Teste 2: Listar Usuários**

**Request:**
```http
GET /api/auth/users
Authorization: Bearer <token>
```

**Response Esperada (Corrigido):**
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
        "last_login": "2025-12-05T03:05:53.674777",
        "created_at": "2025-12-04T10:00:00"
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
        "created_at": "2025-12-05T13:47:20"
      }
    ],
    "total": 2
  }
}
```

**Status HTTP:** `200 OK`

---

## 📝 Notas Adicionais

### **Estrutura da Tabela `frontend_users`**

Baseado na análise do banco de dados:

```sql
CREATE TABLE frontend_users (
    id INTEGER PRIMARY KEY,
    username TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    password_changed INTEGER DEFAULT 0,
    is_active INTEGER DEFAULT 1,
    role TEXT NOT NULL,  -- 'admin' ou 'moderator'
    steam_id TEXT,
    created_at TIMESTAMP,
    updated_at TIMESTAMP
);
```

### **Estrutura da Tabela `players`**

```sql
-- Colunas relevantes:
player_name TEXT,  -- ✅ Nome do jogador (NÃO "name")
steam_id TEXT,     -- ✅ Steam ID
player_id INTEGER  -- ✅ ID do jogador
```

### **Relacionamento**

- `frontend_users.steam_id` → `players.steam_id` (LEFT JOIN)
- Quando vinculado, retornar `players.player_name` e `players.player_id`

---

## 🔍 Como Reproduzir os Problemas

### **Problema 1: Logger**

1. Fazer login como admin
2. Acessar Settings → Users
3. Clicar em "Create User"
4. Preencher os campos:
   - Username: `teste`
   - Password: `senha123456`
   - Role: `moderator`
   - Steam ID: (opcional)
5. Clicar em "Create"
6. **Resultado:** Usuário é criado no banco, mas aparece erro no frontend
7. **Log do Backend:** Mostra erro do logger

### **Problema 2: Query SQL**

1. Fazer login como admin
2. Acessar Settings → Users
3. A página tenta carregar a lista de usuários
4. **Resultado:** Lista não aparece, mostra "No users found"
5. **Log do Backend:** Mostra erro `no such column: p.name`

---

## 🚀 Prioridade de Implementação

1. **ALTA:** Corrigir query SQL (Problema 2) - Bloqueia funcionalidade principal
2. **MÉDIA:** Corrigir logger (Problema 1) - Funciona mas com erro

---

## 📞 Contato

Em caso de dúvidas sobre a implementação ou necessidade de mais informações sobre os logs, favor entrar em contato.

**Última atualização:** 2025-12-05  
**Versão do Frontend:** 1.4.1

