# Solução: Acesso Externo ao Frontend

## Status Atual ✅
- **Servidor Vite**: Rodando na porta **5175** e escutando em **0.0.0.0** (correto)
- **Firewall**: Desativado para teste
- **Acesso Local**: Funcionando (`192.168.100.3:5175`)
- **Acesso Externo**: Não funcionando (`191.217.227.74:5175`)

## Diagnóstico

Como o firewall está desativado e o servidor está escutando corretamente, o problema está **fora do computador**:

### Possíveis Causas (em ordem de probabilidade):

1. **Port Forwarding não configurado ou incorreto no modem/roteador**
2. **CGNAT do ISP** (Carrier-Grade NAT) - impede port forwarding
3. **Firewall do modem/roteador** bloqueando conexões de entrada
4. **ISP bloqueando a porta** 5175

## Soluções

### 1. Verificar Port Forwarding no Modem/Roteador

**Passos:**
1. Acesse o painel do modem/roteador:
   - Geralmente: `http://192.168.1.1` ou `http://192.168.0.1`
   - Ou verifique o gateway padrão: `ipconfig` → "Gateway Padrão"

2. Procure por:
   - "Port Forwarding"
   - "Virtual Server"
   - "NAT"
   - "Redirecionamento de Porta"
   - "Aplicações e Jogos"

3. Configure a regra:
   ```
   Nome: SSM Frontend
   Porta Externa: 5175
   Porta Interna: 5175
   Protocolo: TCP (ou TCP/UDP)
   IP Interno: 192.168.100.3
   Status: Habilitado
   ```

4. **IMPORTANTE**: Salve e reinicie o modem/roteador

### 2. Verificar se o IP Público Está Correto

**Teste:**
1. Acesse: https://whatismyipaddress.com
2. Compare com o IP que você está tentando acessar (`191.217.227.74`)
3. Se for diferente, o IP mudou (IP dinâmico)

**Solução para IP dinâmico:**
- Use um serviço de DNS dinâmico (No-IP, DuckDNS)
- Ou verifique o IP sempre antes de acessar

### 3. Verificar CGNAT (Carrier-Grade NAT)

**Como identificar:**
- Seu IP público começa com `100.x.x.x`? → Provavelmente CGNAT
- Você não consegue fazer port forwarding mesmo configurando corretamente? → Provavelmente CGNAT

**Soluções:**
- Contatar o ISP e solicitar IP público real
- Usar serviço de túnel (ngrok, Cloudflare Tunnel)
- Usar VPN

### 4. Testar com Outra Porta

**Se a porta 5175 estiver bloqueada pelo ISP:**
1. Tente portas comuns que geralmente não são bloqueadas:
   - `8080`
   - `3000`
   - `9000`
   - `8888`

2. Altere no `src/config.json`:
   ```json
   {
     "frontend": {
       "port": 8080,
       "host": "0.0.0.0"
     }
   }
   ```

3. Configure o port forwarding para a nova porta
4. Reinicie o servidor Vite

### 5. Verificar Firewall do Modem/Roteador

**No painel do modem:**
1. Procure por "Firewall" ou "Segurança"
2. Verifique se há bloqueio de conexões de entrada
3. Desabilite temporariamente para testar
4. Ou adicione uma exceção para a porta 5175

### 6. Criar Regra de Firewall do Windows (quando reativar)

**Execute no PowerShell como Administrador:**
```powershell
netsh advfirewall firewall add rule name="SSM Frontend TCP 5175" dir=in action=allow protocol=TCP localport=5175
```

## Testes de Conectividade

### Teste 1: Acesso Local
```
http://192.168.100.3:5175
```
**Deve funcionar** se o servidor estiver rodando.

### Teste 2: Acesso Externo
```
http://191.217.227.74:5175
```
**Só funcionará** se o port forwarding estiver correto.

### Teste 3: Verificar se a Porta Está Aberta

**De outro dispositivo na internet:**
```bash
# Linux/Mac
telnet 191.217.227.74 5175

# Ou use um serviço online:
https://www.yougetsignal.com/tools/open-ports/
```

Se a porta estiver fechada, o problema está no roteador/ISP.

## Checklist Final

- [ ] Port forwarding configurado no modem/roteador
- [ ] IP interno correto (`192.168.100.3`)
- [ ] Porta externa = porta interna (`5175`)
- [ ] Protocolo TCP selecionado
- [ ] Regra habilitada/ativa
- [ ] Modem/roteador reiniciado após configurar
- [ ] IP público verificado (pode ter mudado)
- [ ] Firewall do modem desabilitado ou porta liberada
- [ ] Testado acesso local primeiro (`192.168.100.3:5175`)
- [ ] Servidor Vite rodando e escutando em `0.0.0.0:5175`

## Se Nada Funcionar

**Últimas opções:**
1. **Contatar o ISP** e verificar:
   - Se há CGNAT
   - Se a porta está bloqueada
   - Se é possível obter IP público real

2. **Usar serviço de túnel** (mesmo sem ngrok, há alternativas):
   - Cloudflare Tunnel (gratuito)
   - LocalTunnel (gratuito)
   - Serveo (gratuito)

3. **Usar VPN** para criar túnel

## Comandos Úteis

### Verificar se o servidor está escutando:
```bash
netstat -ano | findstr :5175
```
Deve mostrar: `TCP    0.0.0.0:5175           0.0.0.0:0              LISTENING`

### Verificar gateway padrão:
```bash
ipconfig | findstr /i "Gateway"
```

### Verificar IP local:
```bash
ipconfig | findstr /i "IPv4"
```

## Nota Importante

O problema **NÃO está no código ou configuração do Vite**. O servidor está configurado corretamente para aceitar conexões externas. O problema está na infraestrutura de rede (roteador/modem/ISP).

