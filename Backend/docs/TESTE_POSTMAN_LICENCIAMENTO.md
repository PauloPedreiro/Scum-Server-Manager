# Guia de Teste - API de Licenciamento no Postman

## 📋 Informações Gerais

- **URL Base**: `http://localhost:8000` (teste) ou `https://www.scumsm.com` (produção)
- **Endpoint**: `POST /api/v1/validate`
- **Content-Type**: `application/json`

---

## 🔧 Configuração no Postman

### 1. Criar Nova Requisição

1. Abra o Postman
2. Clique em **"New"** → **"HTTP Request"**
3. Configure:
   - **Method**: `POST`
   - **URL**: `http://localhost:8000/api/v1/validate`

### 2. Configurar Headers

Na aba **Headers**, adicione:

```
Content-Type: application/json
User-Agent: SSM-Backend/1.0
```

---

## 📤 Payload Completo (Exemplo)

### Estrutura do Request Body

```json
{
  "equipment_hash": "918aabd12dc60d8432ab952f8eab6557a5b8b14066953e26",
  "hardware_list": {
    "network_interfaces": [
      {
        "name": "Ethernet",
        "mac_address": "00:1B:44:11:3A:B7",
        "ip_address": "192.168.1.100",
        "type": "ethernet"
      },
      {
        "name": "Wi-Fi",
        "mac_address": "02:00:4C:4F:4F:50",
        "ip_address": "192.168.1.101",
        "type": "wireless"
      }
    ],
    "cpu": {
      "manufacturer": "Intel",
      "model": "Intel Core i7-9700K",
      "cores": 8,
      "threads": 8,
      "serial": null
    },
    "disks": [
      {
        "device": "\\\\.\\PHYSICALDRIVE0",
        "model": "Samsung SSD 860 EVO",
        "serial": "S3Z1NX0K123456",
        "size_gb": 500,
        "type": "SSD"
      },
      {
        "device": "\\\\.\\PHYSICALDRIVE1",
        "model": "Western Digital HDD",
        "serial": "WD-WMC1A1234567",
        "size_gb": 1000,
        "type": "HDD"
      }
    ],
    "motherboard": {
      "manufacturer": "ASUS",
      "model": "ROG STRIX Z390-E GAMING",
      "serial": "MB-123456789"
    },
    "memory": {
      "total_gb": 16,
      "modules": [
        {
          "size_gb": 8,
          "speed": "3200MHz",
          "type": "DDR4"
        },
        {
          "size_gb": 8,
          "speed": "3200MHz",
          "type": "DDR4"
        }
      ]
    },
    "system": {
      "hostname": "DESKTOP-ABC123",
      "architecture": "AMD64",
      "os": "Windows",
      "os_version": "Windows 10 10.0.26100"
    }
  },
  "timestamp": "2025-01-20T17:30:00.000Z",
  "version": "3.0.1",
  "backend_id": "SCUM-BACKEND-ABC123"
}
```

### Campos Obrigatórios

- ✅ `equipment_hash` (string): Hash único do equipamento
- ✅ `hardware_list` (object): Objeto completo com informações de hardware
- ✅ `timestamp` (string): ISO 8601 UTC com "Z" no final (ex: `2025-01-20T17:30:00.000Z`)

### Campos Opcionais

- ⚪ `version` (string): Versão do SSM Backend (ex: `"3.0.1"`)
- ⚪ `backend_id` (string): ID único do backend (ex: `"SCUM-BACKEND-ABC123"`)

---

## 📥 Respostas Esperadas

### ✅ Sucesso (200) - Equipamento Válido

```json
{
  "valid": true,
  "license": {
    "key": "SSM-XXXX-XXXX-XXXX",
    "expires_at": "2025-02-20T00:00:00Z",
    "days_remaining": 15,
    "type": "monthly"
  },
  "hardware": {
    "fingerprint": "918aabd12dc60d8432ab952f8eab6557a5b8b14066953e26",
    "matches": true,
    "registered_at": "2025-01-15T00:00:00Z"
  },
  "validation": {
    "timestamp": "2025-01-20T17:30:00Z",
    "next_check_at": "2025-01-20T21:30:00Z",
    "server_time": "2025-01-20T17:30:01Z"
  },
  "features": {
    "server_control": true,
    "scheduler": true,
    "notifications": true
  }
}
```

### ❌ Erro (200) - Equipamento Inválido

```json
{
  "valid": false,
  "reason": "not_registered",
  "message": "Equipamento não cadastrado no sistema",
  "requires_revalidation": false
}
```

**Possíveis valores de `reason`**:
- `not_registered`: Equipamento não cadastrado
- `hardware_changed`: Hardware mudou desde o último registro
- `expired`: Licença expirada
- `license_inactive`: Licença inativa
- `invalid_timestamp`: Timestamp inválido
- `no_license`: Nenhuma licença associada

### ⚠️ Erro de Servidor (500)

```json
{
  "success": false,
  "error": "Erro interno do servidor",
  "status_code": 500
}
```

### 🔌 Erro de Conexão (Timeout/Connection Refused)

Se o servidor não estiver rodando, o Postman retornará:
- **Connection Error**: "Could not get any response"
- **Timeout**: Se o servidor não responder em tempo hábil

---

## 🧪 Casos de Teste

### Teste 1: Validação com Equipamento Cadastrado

**Payload Mínimo**:
```json
{
  "equipment_hash": "918aabd12dc60d8432ab952f8eab6557a5b8b14066953e26",
  "hardware_list": {
    "network_interfaces": [],
    "cpu": {},
    "disks": [],
    "motherboard": {},
    "memory": {},
    "system": {}
  },
  "timestamp": "2025-01-20T17:30:00.000Z"
}
```

**Resultado Esperado**: `valid: true` ou `valid: false` com `reason`

---

### Teste 2: Validação com Hardware List Completo

Use o payload completo acima com todos os campos preenchidos.

**Resultado Esperado**: Mesma resposta, mas com mais informações para o servidor processar.

---

### Teste 3: Timestamp Inválido

**Payload**:
```json
{
  "equipment_hash": "918aabd12dc60d8432ab952f8eab6557a5b8b14066953e26",
  "hardware_list": {
    "network_interfaces": [],
    "cpu": {},
    "disks": [],
    "motherboard": {},
    "memory": {},
    "system": {}
  },
  "timestamp": "2020-01-01T00:00:00.000Z"
}
```

**Resultado Esperado**: `valid: false`, `reason: "invalid_timestamp"`

---

### Teste 4: Equipment Hash Não Cadastrado

**Payload**:
```json
{
  "equipment_hash": "00000000000000000000000000000000000000000000",
  "hardware_list": {
    "network_interfaces": [],
    "cpu": {},
    "disks": [],
    "motherboard": {},
    "memory": {},
    "system": {}
  },
  "timestamp": "2025-01-20T17:30:00.000Z"
}
```

**Resultado Esperado**: `valid: false`, `reason: "not_registered"`

---

## 🔍 Como Obter o Equipment Hash Real

Para obter o `equipment_hash` real da sua máquina:

1. **Via GUI SSM**:
   - Abra a GUI do SSM Backend
   - O hash está exibido no rodapé (campo "Hash:")
   - Copie o valor completo

2. **Via API Local** (se backend estiver rodando):
   ```
   GET http://localhost:3000/api/licensing/hardware-fingerprint
   ```
   Resposta:
   ```json
   {
     "hash": "918aabd12dc60d8432ab952f8eab6557a5b8b14066953e26",
     "stored_hash": "918aabd12dc60d8432ab952f8eab6557a5b8b14066953e26",
     "components": {...}
   }
   ```

---

## 🐛 Debug de Erros

### Erro 500 (Internal Server Error)

**Possíveis causas**:
1. Servidor de licenciamento com erro interno
2. Formato do `hardware_list` incorreto
3. Campo obrigatório faltando
4. Erro no banco de dados do servidor

**Solução**:
- Verifique os logs do servidor de licenciamento
- Valide o formato JSON do payload
- Verifique se todos os campos obrigatórios estão presentes

### Erro de Conexão

**Possíveis causas**:
1. Servidor não está rodando
2. Porta incorreta (deve ser `8000` para teste)
3. Firewall bloqueando conexão

**Solução**:
- Verifique se o servidor está rodando: `netstat -an | findstr :8000`
- Teste com `curl` ou navegador: `http://localhost:8000/api/v1/validate`

### Resposta com `valid: false`

**Verifique**:
1. Se o `equipment_hash` está cadastrado no servidor
2. Se a licença não expirou
3. Se o hardware não mudou desde o último registro

---

## 📝 Checklist de Validação

Antes de testar, verifique:

- [ ] Servidor de licenciamento está rodando
- [ ] URL está correta (`http://localhost:8000/api/v1/validate`)
- [ ] Headers estão configurados (`Content-Type: application/json`)
- [ ] `equipment_hash` está correto (copiado da GUI ou API)
- [ ] `timestamp` está no formato ISO 8601 UTC com "Z"
- [ ] `hardware_list` tem pelo menos a estrutura básica (mesmo que vazia)

---

## 💡 Dicas

1. **Use Variáveis do Postman**: Crie variáveis para `equipment_hash` e `server_url` para facilitar testes
2. **Salve como Collection**: Organize os testes em uma collection do Postman
3. **Use Pre-request Script**: Para gerar timestamp automaticamente:
   ```javascript
   pm.environment.set("timestamp", new Date().toISOString());
   ```
4. **Use Tests**: Adicione testes automáticos:
   ```javascript
   pm.test("Status code is 200", function () {
       pm.response.to.have.status(200);
   });
   
   pm.test("Response has valid field", function () {
       var jsonData = pm.response.json();
       pm.expect(jsonData).to.have.property('valid');
   });
   ```

---

## 🔗 Links Úteis

- **Documentação da API**: Ver arquivos em `docs/` sobre licenciamento
- **Config do Backend**: `data/config.json` → seção `licensing`
- **Logs do Backend**: Verificar logs quando validação falha

---

**Última atualização**: 2025-01-20
