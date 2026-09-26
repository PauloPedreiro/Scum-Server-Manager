# ✅ Endpoints Corretos do Gestão

## ⚠️ IMPORTANTE: Use o prefixo `/v1`!

Os endpoints do Gestão **SEMPRE** usam o prefixo `/api/v1/` (não apenas `/api/`).

---

## 📡 Endpoints Corretos

### 1. **GET Handshake (Verificar se Gestão está pronto)**

```
GET /api/v1/servers/ready?server_hash={hash}
```

**Exemplo no Postman:**
```
GET http://localhost:8000/api/v1/servers/ready?server_hash=9bec6bc7379a5ce11db5430cd3fe536db7cdbcf133442a4accebc228be795be0
```

**Resposta esperada (200 OK):**
```json
{
  "ready": true,
  "retry_after": null
}
```

---

### 2. **POST Sincronização (Enviar dados)**

```
POST /api/v1/servers/sync
```

**Exemplo no Postman:**
```
POST http://localhost:8000/api/v1/servers/sync
```

**Headers:**
```
Content-Type: application/json
```

**Body (JSON):**
```json
{
  "server_hash": "9bec6bc7379a5ce11db5430cd3fe536db7cdbcf133442a4accebc228be795be0",
  "api_key": "ssm_207d80c3a1e87d90f5b893591001e55ef0b043b58b2a803637535db110939c10",
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
    "survival": [],
    "lockpicking": [],
    "fishing": []
  },
  "timestamp": "2025-01-15T10:30:00Z"
}
```

**Resposta esperada (200 OK):**
```json
{
  "success": true,
  "message": "Sincronização concluída com sucesso",
  "server_id": 2,
  "players_synced": 1,
  "rankings_created": 0
}
```

---

## ❌ Endpoints INCORRETOS (NÃO funcionam)

### ❌ ERRADO:
```
GET /api/servers/ready?server_hash={hash}
POST /api/servers/sync
```

**Resultado:** `{"detail": "Not Found"}` (404)

### ✅ CORRETO:
```
GET /api/v1/servers/ready?server_hash={hash}
POST /api/v1/servers/sync
```

---

## 🔧 Configuração no Postman

### Variáveis do Postman:

1. **`{{gestaoUrl}}`**: `http://localhost:8000` (sem barra final)
2. **`{{serverHash}}`**: `9bec6bc7379a5ce11db5430cd3fe536db7cdbcf133442a4accebc228be795be0`

### Requisições:

**GET Handshake:**
```
GET {{gestaoUrl}}/api/v1/servers/ready?server_hash={{serverHash}}
```

**POST Sync:**
```
POST {{gestaoUrl}}/api/v1/servers/sync
```

---

## 📝 Checklist

- [ ] URL base sem barra final: `http://localhost:8000` (não `http://localhost:8000/`)
- [ ] Endpoint GET usa `/api/v1/servers/ready` (com `/v1`)
- [ ] Endpoint POST usa `/api/v1/servers/sync` (com `/v1`)
- [ ] Hash do servidor tem 64 caracteres hexadecimais
- [ ] API Key começa com `ssm_` e tem 64 caracteres hex após o prefixo
- [ ] Content-Type: `application/json` no POST

---

## 🐛 Troubleshooting

### Erro 404 "Not Found"
- ✅ Verifique se está usando `/api/v1/` (não `/api/`)
- ✅ Verifique se a URL base está correta
- ✅ Verifique se o Gestão está rodando

### Erro 400 "Bad Request"
- ✅ Verifique se o `server_hash` tem exatamente 64 caracteres hexadecimais
- ✅ Verifique se a API Key está no formato correto (`ssm_` + 64 hex)

### Erro 401 "Unauthorized"
- ✅ Verifique se a API Key corresponde ao `server_hash` no Gestão
- ✅ Verifique se o servidor está cadastrado no Gestão

---

**Última atualização:** 2025-01-15

