# 🔧 Correção Necessária: Sincronização entre Sistemas de Licenciamento e Gestão

**Data:** 2025-12-18  
**Prioridade:** Alta  
**Status:** Aguardando correção

---

## 📋 Resumo do Problema

O SSM Backend está iniciando com sucesso (validação de licença passou), mas a sincronização com o sistema de Gestão falha com erro **404 Not Found**, indicando que o hash do servidor não está cadastrado no Gestão.

**Conclusão:** Os sistemas de **Licenciamento** e **Gestão** estão desconectados, causando uma inconsistência lógica onde um servidor válido (que passou na validação) não consegue sincronizar dados.

---

## 🔍 Análise Técnica

### Fluxo Atual

1. **Validação de Licença (SSM → Servidor de Licenciamento)**
   - SSM gera `equipment_hash` usando `HardwareFingerprint.generate()`
   - Envia `POST /api/v1/validate` com `equipment_hash`
   - Se hash está cadastrado → Backend inicia ✅
   - Se hash não está cadastrado → Backend bloqueia ❌

2. **Sincronização com Gestão (SSM → Gestão)**
   - SSM gera `server_hash` usando `HardwareFingerprint.generate()` (mesmo método)
   - Envia `GET /api/v1/servers/ready?server_hash=...` (handshake)
   - Envia `POST /api/v1/servers/sync` com `server_hash` no payload
   - Se hash está cadastrado → Sincronização funciona ✅
   - Se hash não está cadastrado → Erro 404 ❌

### Problema Identificado

**O mesmo hash que passa na validação de licença não é reconhecido no sistema de Gestão.**

### Evidências dos Logs

```
🔑 Hash do servidor (equipment_hash) que será usado: 6207cf790a5cb2b8...13316031
🔑 API key que será usada: ssm_2817a6...0aab9
📊 Rankings coletados do banco: 532 players
📊 Dados coletados: 532 players de ranking, 532 players totais

❌ Erro 404: Servidor não encontrado. Hash: '6207cf790a5cb2b869f6...' não cadastrado

⚠️ DIAGNÓSTICO:
   • Validação de licença: PASSOU ✅ (backend iniciou com sucesso)
   • Sincronização com Gestão: FALHOU ❌ (hash não encontrado)
```

### Código do SSM Backend

**Geração do Hash (mesma função para ambos):**
```python
# Validação de Licença
current_hash, components = self.hardware_fingerprint.generate()

# Sincronização com Gestão
server_hash, _ = self.hardware_fingerprint.generate()
```

**Payload enviado ao Gestão:**
```json
{
  "server_hash": "6207cf790a5cb2b869f6...13316031",
  "api_key": "ssm_2817a6...0aab9",
  "server_info": { ... },
  "players": [ ... ],
  "rankings": { ... },
  "timestamp": "2025-12-18T22:18:27.618274Z"
}
```

---

## 🎯 Lógica Esperada

Se um servidor passou na validação de licença (o que significa que o `equipment_hash` está cadastrado e válido), ele **deveria automaticamente** estar disponível no sistema de Gestão para sincronização.

**Razão:** O hash usado é o mesmo (`equipment_hash` = `server_hash`), então ambos os sistemas deveriam reconhecer o mesmo identificador único do servidor.

---

## 💡 Solução Proposta

### Opção 1: Sincronização Automática (Recomendada)

Quando o sistema de Licenciamento valida um `equipment_hash` com sucesso:

1. **Registrar automaticamente no Gestão:**
   - Ao validar licença, criar/atualizar registro no Gestão
   - Usar o mesmo `equipment_hash` como `server_hash`
   - Garantir que os dois sistemas compartilhem a mesma base de dados de servidores

2. **API do Gestão:**
   - Criar endpoint `/api/v1/servers/register` ou
   - Modificar endpoint de validação para também registrar no Gestão

### Opção 2: Endpoint de Verificação Unificada

Criar um endpoint que verifica em ambos os sistemas:

```
GET /api/v1/servers/{server_hash}/status
```

Retorna:
```json
{
  "license_valid": true,
  "gestao_registered": true,
  "can_sync": true
}
```

### Opção 3: Auto-registro no Primeiro Sync

Quando o Gestão recebe um `server_hash` desconhecido (404):

1. Verificar se o hash está cadastrado no sistema de Licenciamento
2. Se estiver → Auto-registrar no Gestão e processar sincronização
3. Se não estiver → Retornar erro 401 (não autorizado)

---

## 🔧 Implementação Sugerida (Opção 3)

**Modificar endpoint `/api/v1/servers/sync`:**

```python
# Pseudocódigo
def sync_server(payload):
    server_hash = payload.get("server_hash")
    
    # 1. Verificar se está cadastrado no Gestão
    server = get_server_from_gestao(server_hash)
    if server:
        # Servidor já cadastrado - processar normalmente
        return process_sync(payload)
    
    # 2. Servidor não encontrado - verificar no sistema de Licenciamento
    license_valid = check_license_server(server_hash)
    if license_valid:
        # Hash válido - auto-registrar no Gestão
        server = auto_register_server(server_hash, payload)
        return process_sync(payload)
    else:
        # Hash inválido - retornar erro
        return error_response(401, "Hash não autorizado")
```

---

## 📊 Requisitos Técnicos

### Hash Format
- **Formato:** 64 caracteres hexadecimal (SHA-256)
- **Exemplo:** `6207cf790a5cb2b869f6d5e8c4b3a2f1e9d8c7b6a5f4e3d2c1b0a9f8e7d6c5b4a3f2e1d0c9b8a713316031`
- **Origem:** Hardware fingerprint (MAC addresses, CPU ID, Disk serials, etc.)

### Endpoint Handshake
```
GET /api/v1/servers/ready?server_hash={hash}
```

**Resposta esperada:**
```json
{
  "ready": true,
  "retry_after": null
}
```

**Resposta atual (quando hash não cadastrado):**
```json
{
  "detail": "Servidor não encontrado. Hash: '...' não cadastrado"
}
```

**Status HTTP:** 404 Not Found

### Endpoint Sync
```
POST /api/v1/servers/sync
```

**Headers:**
```
Content-Type: application/json
```

**Payload:**
```json
{
  "server_hash": "6207cf790a5cb2b869f6...13316031",
  "api_key": "ssm_2817a6...0aab9",
  "server_info": {
    "name": "Server Name",
    "region": "BR",
    "is_online": true
  },
  "players": [ ... ],
  "rankings": {
    "data": {
      "players": [ ... ]
    }
  },
  "timestamp": "2025-12-18T22:18:27.618274Z"
}
```

---

## ✅ Critérios de Aceitação

1. ✅ Servidor que passou na validação de licença consegue sincronizar com Gestão
2. ✅ Não é necessário cadastro manual adicional no Gestão
3. ✅ Hash válido no sistema de Licenciamento é reconhecido no Gestão
4. ✅ Erro 404 não ocorre para servidores válidos

---

## 🔗 Integração com Sistema de Licenciamento

### Verificação de Hash Válido

O Gestão precisa ter acesso ao sistema de Licenciamento para verificar se um `server_hash` está cadastrado e válido.

**Opções:**

1. **Compartilhar base de dados** (mesma tabela de servidores)
2. **API de verificação** (`GET /api/v1/validate/check/{hash}`)
3. **Cache sincronizado** (atualizar quando licença é validada)

---

## 📝 Logs e Debugging

O SSM Backend já está registrando logs detalhados:

```
🔑 Hash do servidor (equipment_hash) que será usado: {hash}
🔑 API key que será usada: {api_key}
📊 Dados coletados: {n} players de ranking, {m} players totais
```

**Logs de erro atuais:**
```
❌ Erro 404: Servidor não encontrado. Hash: '{hash}' não cadastrado
⚠️ Hash usado na sincronização: {hash}
⚠️ Este é o mesmo hash (equipment_hash) usado na validação de licença.
⚠️ DIAGNÓSTICO:
   • Validação de licença: PASSOU ✅ (backend iniciou com sucesso)
   • Sincronização com Gestão: FALHOU ❌ (hash não encontrado)
```

---

## 🚀 Próximos Passos

1. **Desenvolvedor do Gestão:**
   - Implementar verificação no sistema de Licenciamento
   - Implementar auto-registro ou sincronização automática
   - Testar com hash válido que passou na validação

2. **Teste:**
   - Validar licença de um servidor
   - Tentar sincronizar com Gestão
   - Verificar que não retorna 404

3. **Validação:**
   - Confirmar que servidores válidos sincronizam automaticamente
   - Confirmar que servidores inválidos ainda são rejeitados

---

## 📞 Contato

**Dúvidas sobre o problema ou implementação?** Entre em contato com a equipe do SSM Backend.

**Hash de exemplo para teste:**
```
6207cf790a5cb2b869f6d5e8c4b3a2f1e9d8c7b6a5f4e3d2c1b0a9f8e7d6c5b4a3f2e1d0c9b8a713316031
```

---

**Documento criado em:** 2025-12-18  
**Versão:** 1.0

