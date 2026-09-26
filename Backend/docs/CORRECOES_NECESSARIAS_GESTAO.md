# 🔧 Correções Necessárias no Servidor Gestão

**Data:** 18/12/2025  
**Sistema:** SSM Backend v3.0  
**API:** Gestão v2.0  

---

## 📋 Resumo Executivo

O SSM Backend está implementado corretamente conforme a documentação da API v2.0, mas encontramos problemas no servidor do Gestão que impedem a sincronização adequada. Este documento detalha os problemas identificados e as correções necessárias.

---

## 🐛 Problema 1: Handshake Retornando `ready=false` com `retry_after=0`

### **Endpoint Afetado:**
```
GET /api/v1/servers/ready?server_hash={hash}
```

### **Comportamento Atual (Problemático):**
Quando o servidor não está pronto, o Gestão retorna:
```json
{
  "ready": false,
  "retry_after": 0
}
```

### **Comportamento Esperado:**
O Gestão deve retornar:
```json
{
  "ready": false,
  "retry_after": 30
}
```

Ou qualquer valor **maior que 0** (recomendado: 30-60 segundos).

### **Impacto:**
- O SSM Backend tenta sincronizar imediatamente (sem espera)
- Causa loop de tentativas rápidas
- Pode causar rate limiting desnecessário
- Sobrecarrega o servidor do Gestão

### **Evidências nos Logs:**
```
[13:41:46] [INFO] Aguardando 0 segundos antes de tentar novamente... (tentativa 1/2)
[13:41:47] [⚠] ❌ Sincronização falhou: Gestão não está pronto. Próxima tentativa em 0s
[13:41:48] [INFO] Aguardando 0 segundos antes de tentar novamente... (tentativa 2/2)
```

### **Correção Necessária:**
```python
# ❌ ERRADO (atual)
{
  "ready": false,
  "retry_after": 0  # NUNCA retornar 0!
}

# ✅ CORRETO (esperado)
{
  "ready": false,
  "retry_after": 30  # Sempre retornar valor > 0
}
```

### **Nota:**
O SSM Backend já implementa uma proteção que força um mínimo de 5 segundos mesmo quando recebe `retry_after=0`, mas é melhor corrigir no servidor para evitar tentativas desnecessárias.

---

## 🐛 Problema 2: Erro 502 Bad Gateway Frequente

### **Endpoint Afetado:**
```
POST /api/v1/servers/sync
```

### **Comportamento Atual (Problemático):**
O servidor retorna frequentemente:
```
502 Bad Gateway
```

Com resposta HTML (página de erro do Cloudflare/gateway):
```html
<!DOCTYPE html>
<title>scumsm.com | 502: Bad gateway</title>
```

### **Comportamento Esperado:**
O servidor deve:
1. Responder com código HTTP apropriado (200, 400, 401, 413, 429, 500)
2. Retornar JSON na resposta, nunca HTML
3. Incluir informações úteis no corpo da resposta

### **Impacto:**
- Sincronizações falham silenciosamente
- Não há como saber o motivo real da falha
- O SSM Backend não consegue processar a resposta corretamente

### **Evidências nos Logs:**
```
[13:31:51] [ERROR] Erro ao sincronizar: 502 - <!DOCTYPE html>...
```

### **Correção Necessária:**
Garantir que o gateway/load balancer esteja configurado corretamente e que o servidor de aplicação esteja respondendo adequadamente. Se o servidor estiver realmente indisponível, retornar:

```json
{
  "success": false,
  "error": "Servidor temporariamente indisponível",
  "retry_after": 300
}
```

Com código HTTP `503 Service Unavailable` (não 502).

---

## 🐛 Problema 3: Erro 500 Internal Server Error

### **Endpoint Afetado:**
```
POST /api/v1/servers/sync
```

### **Comportamento Atual (Problemático):**
O servidor retorna:
```
500 Internal Server Error
```

Sem detalhes úteis no corpo da resposta.

### **Comportamento Esperado:**
O servidor deve retornar JSON com informações sobre o erro:
```json
{
  "success": false,
  "error": "Erro ao processar dados",
  "detail": "Descrição técnica do erro (para logs)",
  "retry_after": 60
}
```

### **Impacto:**
- Impossível diagnosticar o problema
- SSM Backend não sabe se deve tentar novamente ou não

### **Evidências nos Logs:**
```
[13:41:46] [ERROR] Erro do servidor: Erro interno do servidor (500)
```

### **Correção Necessária:**
1. Adicionar tratamento de erros robusto no servidor
2. Retornar JSON estruturado em caso de erro
3. Incluir `retry_after` quando apropriado

---

## ✅ Comportamento Correto Implementado no SSM Backend

### **1. Validação de Server Hash:**
- ✅ Valida formato: 64 caracteres hexadecimais
- ✅ Rejeita valores inválidos antes de enviar

### **2. Validação de API Key:**
- ✅ Valida formato: `ssm_` + 64 caracteres hex
- ✅ Rejeita valores inválidos antes de enviar

### **3. Formato de Rankings (v2.0):**
- ✅ Campos `longest_shot` e `lockpicking` planos (não aninhados)
- ✅ Todos os campos da tabela `rankings` incluídos
- ✅ Sem limite fixo de 1000 jogadores
- ✅ Todos os jogadores são enviados

### **4. Tamanho de Payload:**
- ✅ Calcula tamanho do payload automaticamente
- ✅ Divide em lotes quando excede 5 MB
- ✅ Envia múltiplos lotes respeitando rate limit

### **5. Rate Limiting:**
- ✅ Aguarda 5 minutos entre lotes
- ✅ Respeita `retry_after` da resposta do servidor
- ✅ Implementa backoff exponencial

### **6. Tratamento de Erros:**
- ✅ 400: Erro de validação (não tenta novamente)
- ✅ 401: Erro de autenticação (não tenta novamente)
- ✅ 413: Payload muito grande (divide em lotes)
- ✅ 429: Rate limit (aguarda `retry_after`)
- ✅ 500: Erro do servidor (tenta novamente após aguardar)
- ✅ 502: Bad Gateway (tenta novamente após aguardar)
- ✅ 503: Servidor ocupado (aguarda `retry_after`)

---

## 📊 Estatísticas de Sincronização

### **Dados Enviados (Último Teste):**
- **Total de Players:** 532 jogadores
- **Tamanho do Payload:** ~0.66 MB
- **Status:** Dentro do limite de 5 MB

### **Formato do Payload:**
```json
{
  "server_hash": "37dc698057791e6b428e...cfd53be571",
  "api_key": "ssm_7d0e076e088cb3a8...",
  "server_info": {
    "name": "Meu Servidor SCUM",
    "version": "3.0.0",
    "region": "unknown",
    "is_online": false,
    ...
  },
  "players": [...],
  "rankings": {
    "data": {
      "players": [...]
    }
  },
  "timestamp": "2025-01-17T00:00:00Z"
}
```

---

## 🔍 Testes Realizados

### **Teste 1: Envio Real de Dados**
- ✅ Configuração carregada corretamente
- ✅ API key descriptografada e validada
- ✅ Server hash obtido e validado
- ✅ Dados coletados (532 jogadores)
- ✅ Payload preparado (0.66 MB)
- ❌ **Resultado:** 502 Bad Gateway (problema no Gestão)

### **Teste 2: Handshake**
- ✅ Requisição enviada corretamente
- ❌ **Resultado:** `ready=false` com `retry_after=0` (problema no Gestão)

---

## 📝 Recomendações

### **Prioridade Alta:**
1. ✅ **Corrigir `retry_after=0`** no endpoint `/api/v1/servers/ready`
   - Sempre retornar valor ≥ 30 segundos quando `ready=false`

2. ✅ **Resolver problemas de 502 Bad Gateway**
   - Verificar configuração do gateway/load balancer
   - Garantir que servidor de aplicação esteja respondendo

3. ✅ **Melhorar tratamento de erro 500**
   - Retornar JSON estruturado
   - Incluir `retry_after` quando apropriado

### **Prioridade Média:**
4. ✅ **Adicionar logs no servidor**
   - Para facilitar diagnóstico de problemas
   - Registrar requisições rejeitadas e motivos

5. ✅ **Documentar códigos de erro**
   - Especificar quando cada código é retornado
   - Documentar formato de respostas de erro

### **Prioridade Baixa:**
6. ✅ **Melhorar mensagens de erro**
   - Mensagens mais descritivas
   - Sugestões de ação quando possível

---

## 🔗 Referências

### **Documentação da API:**
- API v2.0 - Endpoint de Sincronização de Rankings
- Especificação de Payload e Validações

### **Código do SSM Backend:**
- `core/communication/gestao_sync_service.py`
- `test_gestao_sync_real.py` (script de teste)

---

## 📞 Contato

Para dúvidas ou esclarecimentos sobre esta documentação, entre em contato com a equipe do SSM Backend.

---

## ✅ Checklist de Correções

Após as correções, por favor confirmar:

- [ ] Endpoint `/api/v1/servers/ready` nunca retorna `retry_after=0`
- [ ] Endpoint `/api/v1/servers/sync` não retorna mais 502 Bad Gateway
- [ ] Erros 500 retornam JSON estruturado com `retry_after`
- [ ] Todos os endpoints retornam JSON (não HTML) em caso de erro
- [ ] Rate limiting está funcionando corretamente
- [ ] Logs no servidor estão capturando problemas

---

**Última Atualização:** 18/12/2025  
**Versão do Documento:** 1.0

