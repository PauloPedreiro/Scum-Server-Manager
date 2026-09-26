# 🔍 Diagnóstico: Acesso Externo ao Frontend - Porta 5175

## ✅ Status Atual

- **Servidor Vite:** ✅ Escutando em `0.0.0.0:5175` (correto)
- **Firewall Windows:** ⚠️ Desativado para teste (não é o problema)
- **Acesso Local:** ✅ Funcionando (`192.168.100.3:5175`)
- **Acesso Externo:** ❌ Não funciona (`191.217.227.74:5175`)

## 🔴 Problema Identificado

O erro `ERR_CONNECTION_REFUSED` ao acessar pelo IP externo indica que:
- A conexão não está chegando ao servidor
- O problema está **ANTES** do servidor (roteador/modem ou ISP)

## 📋 Checklist de Verificação

### 1. Port Forwarding no Modem/Roteador ⚠️ CRÍTICO

**Você precisa configurar o port forwarding para a porta 5175:**

1. Acesse o painel do modem/roteador:
   - Geralmente: `http://192.168.100.1` ou `http://192.168.1.1`
   - Ou verifique o "Gateway Padrão" com: `ipconfig`

2. Procure por:
   - "Port Forwarding"
   - "Virtual Server"
   - "NAT"
   - "Port Mapping"
   - "Redirecionamento de Porta"

3. Configure a regra:
   ```
   Nome: SSM Frontend
   Porta Externa: 5175
   Porta Interna: 5175
   Protocolo: TCP (ou TCP/UDP)
   IP Interno: 192.168.100.3
   Status: Habilitado
   ```

4. **IMPORTANTE:** Salve e reinicie o modem/roteador

### 2. Verificar IP Público

O IP que você está tentando acessar (`191.217.227.74`) pode ter mudado:

1. Acesse: https://whatismyipaddress.com
2. Compare com o IP que você está usando
3. Se for diferente, use o IP atual

### 3. Testar Conectividade

**De dentro da rede local:**
```bash
# Deve funcionar
http://192.168.100.3:5175
```

**De fora da rede:**
```bash
# Deve funcionar se port forwarding estiver correto
http://191.217.227.74:5175
```

### 4. Verificar Firewall do Modem

Alguns modems têm firewall próprio que bloqueia conexões de entrada:

1. No painel do modem, procure por "Firewall" ou "Segurança"
2. Verifique se há bloqueio de portas
3. Adicione exceção para a porta 5175
4. Ou desabilite temporariamente para testar

### 5. Verificar CGNAT (Carrier-Grade NAT)

**Sintomas:**
- Port forwarding configurado corretamente
- Firewall desativado
- Ainda não funciona

**Solução:**
- Entre em contato com seu ISP
- Solicite IP público real (pode ter custo adicional)
- Ou use serviço de túnel (ngrok, Cloudflare Tunnel)

## 🧪 Testes de Diagnóstico

### Teste 1: Verificar se o servidor está escutando
```bash
netstat -ano | findstr :5175
```
**Deve mostrar:** `TCP    0.0.0.0:5175           0.0.0.0:0              LISTENING`

### Teste 2: Testar acesso local
```bash
# De outro dispositivo na mesma rede
curl http://192.168.100.3:5175
```
**Deve retornar:** HTML da aplicação

### Teste 3: Verificar port forwarding
```bash
# Use um serviço online para verificar se a porta está aberta
# Exemplo: https://www.yougetsignal.com/tools/open-ports/
# Ou: https://canyouseeme.org/
```
**Digite:** Porta `5175` e seu IP público

### Teste 4: Testar com outra porta
Se a porta 5175 estiver bloqueada pelo ISP, tente:
- `8080`
- `9000`
- `3000`

## 🚨 Problemas Comuns

### Problema 1: ISP Bloqueando Porta
**Solução:** Tente outra porta (8080, 9000, etc.)

### Problema 2: CGNAT
**Solução:** Contatar ISP ou usar túnel

### Problema 3: Port Forwarding Incorreto
**Solução:** Verificar configuração no modem

### Problema 4: Firewall do Modem
**Solução:** Desabilitar ou adicionar exceção

## 📝 Próximos Passos

1. ✅ **Verificar port forwarding** no modem para porta 5175
2. ✅ **Reiniciar modem** após configurar
3. ✅ **Testar acesso externo** novamente
4. ✅ Se não funcionar, **testar outra porta** (8080)
5. ✅ Se ainda não funcionar, **verificar CGNAT** com ISP

## 🔧 Configuração Atual

**Frontend:**
- Porta: `5175`
- Host: `0.0.0.0` (aceita conexões externas)
- IP Local: `192.168.100.3`
- IP Público: `191.217.227.74` (verificar se ainda é válido)

**Backend:**
- Não está bloqueando (CORS habilitado)
- Porta: `3000`
- Host: `0.0.0.0`

## ⚠️ Nota Importante

O problema **NÃO está no código** ou no servidor Vite. O servidor está configurado corretamente. O problema está na infraestrutura de rede (modem/roteador ou ISP).

