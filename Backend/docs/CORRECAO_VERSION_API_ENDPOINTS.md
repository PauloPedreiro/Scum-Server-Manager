# 🔧 Correção: Versão da API dos Endpoints

**Data:** 18/12/2025  
**Status:** ⚠️ Aguardando Confirmação

---

## 📋 Problema Identificado

O usuário mencionou que na documentação do sistema de fila (v3.0) os endpoints estão em `/api/v3/`, mas o código estava usando `/api/v1/`.

---

## 🔍 Testes Realizados

### **Teste 1: Endpoint v3**

```bash
GET https://scumsm.com/api/v3/servers/ready?server_hash=...
```

**Resultado:**
```
HTTP 404 Not Found
{
  "detail": "Not Found"
}
```

### **Teste 2: Endpoint v1**

```bash
GET https://scumsm.com/api/v1/servers/ready?server_hash=...
```

**Resultado:**
```
HTTP 200 OK
{
  "ready": true,
  "retry_after": null
}
```

---

## ✅ Mudanças Implementadas

### **Arquivo: `core/communication/gestao_sync_service.py`**

**Linha 187 (check_ready):**
```python
# ANTES
f"{self.gestao_url}/api/v1/servers/ready",

# DEPOIS
f"{self.gestao_url}/api/v3/servers/ready",
```

**Linha 263 (_send_payload):**
```python
# ANTES
f"{self.gestao_url}/api/v1/servers/sync",

# DEPOIS
f"{self.gestao_url}/api/v3/servers/sync",
```

### **Arquivo: `test_handshake_diagnostico.py`**

**Atualizado para usar v3:**
```python
handshake_url = f"{gestao_url}/api/v3/servers/ready"
```

---

## ⚠️ Problema Detectado

Após atualizar para `/api/v3/`, o endpoint retorna **404 Not Found**, enquanto `/api/v1/` retorna **200 OK**.

### **Possíveis Causas:**

1. **v3 ainda não está implementado no Gestão**
   - O sistema de fila pode estar documentado mas ainda não deployado
   - Pode estar em ambiente de desenvolvimento/teste

2. **Documentação pode estar incorreta**
   - A documentação menciona v3, mas o endpoint real ainda é v1
   - Pode haver confusão entre versão do sistema (v3.0) e versão da API (v1)

3. **v3 pode estar em outra URL ou ambiente**
   - Pode estar em staging/teste
   - Pode precisar de autenticação diferente

---

## 📊 Recomendações

### **Opção 1: Reverter para v1 (Temporário)**

Se v3 ainda não está disponível, podemos reverter para v1 e manter funcionando:

```python
# Reverter para v1 até v3 estar disponível
f"{self.gestao_url}/api/v1/servers/ready"
f"{self.gestao_url}/api/v1/servers/sync"
```

### **Opção 2: Tornar Versão Configurável**

Permitir configurar a versão da API no `config.json`:

```json
{
  "licensing": {
    "gestao_url": "https://scumsm.com",
    "gestao_api_version": "v1"  // ou "v3" quando disponível
  }
}
```

E usar no código:
```python
api_version = licensing_config.get('gestao_api_version', 'v1')
f"{self.gestao_url}/api/{api_version}/servers/ready"
```

### **Opção 3: Confirmar com Desenvolvedor do Gestão**

- ✅ Verificar se v3 está realmente deployado
- ✅ Verificar se há diferença entre versão do sistema (v3.0) e versão da API (v1)
- ✅ Confirmar qual endpoint deve ser usado

---

## ✅ Status Atual

- ✅ **Código atualizado para v3**
- ⚠️ **Endpoint v3 retorna 404** (não encontrado)
- ✅ **Endpoint v1 funciona** (200 OK)

---

## 🔄 Próximos Passos

1. **Confirmar com desenvolvedor do Gestão:**
   - Endpoint correto é `/api/v1/` ou `/api/v3/`?
   - v3 está deployado em produção?

2. **Decidir ação:**
   - Se v3 não está disponível: Reverter para v1
   - Se v3 está disponível em outro ambiente: Configurar URL correta
   - Se v3 será deployado em breve: Manter código preparado

---

**Última Atualização:** 18/12/2025  
**Versão:** 1.0  
**Status:** ⚠️ Aguardando Confirmação

