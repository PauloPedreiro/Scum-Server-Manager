# Troubleshooting: Acesso Externo ao Frontend

## Problema
Não consegue acessar o frontend pelo IP externo `191.217.227.74:5170`, mesmo com port forwarding configurado no modem e firewall liberado.

## Verificações Realizadas ✅

### 1. Servidor Vite
- ✅ Escutando em `0.0.0.0:5170` (correto)
- ✅ Configuração atualizada para suportar acesso externo

### 2. Firewall do Windows
- ✅ Regra "SSM Teste TCP 5170" habilitada
- ✅ Aceita conexões de qualquer IP remoto
- ✅ Porta 5170 liberada para TCP

### 3. Configuração do Vite
- ✅ `host: "0.0.0.0"` no config.json
- ✅ HMR configurado para usar IP local

## Possíveis Causas e Soluções

### 1. Port Forwarding no Roteador/Modem

**Verificar:**
- A porta externa está configurada como `5170`?
- O IP interno está correto (`192.168.100.3`)?
- A regra está **habilitada/ativa**?
- O protocolo está como `TCP` (não apenas UDP)?

**Teste:**
1. Acesse o painel do modem/roteador
2. Verifique se a regra de port forwarding está ativa
3. Tente desabilitar e reabilitar a regra
4. Reinicie o modem/roteador após configurar

### 2. ISP (Provedor de Internet)

**Possível problema:**
- Alguns ISPs bloqueiam portas comuns (80, 443, 8080, etc.)
- Alguns ISPs usam CGNAT (Carrier-Grade NAT), que impede port forwarding

**Solução:**
- Tente usar uma porta diferente (ex: 8080, 3000, 9000)
- Entre em contato com o ISP para verificar se há bloqueio
- Verifique se seu IP é público ou está atrás de CGNAT

### 3. Firewall do Roteador/Modem

**Verificar:**
- O firewall do modem pode estar bloqueando conexões de entrada
- Procure por "Firewall", "Segurança" ou "Bloqueio de Porta" no painel
- Desabilite temporariamente para testar

### 4. Teste de Conectividade

**Teste local primeiro:**
```bash
# De outro dispositivo na mesma rede local
http://192.168.100.3:5170
```

**Teste externo:**
```bash
# De um dispositivo fora da rede
http://191.217.227.74:5170
```

### 5. Verificar se o IP Público Está Correto

**Verificar IP público atual:**
- Acesse: https://whatismyipaddress.com
- Compare com o IP que você está tentando acessar (`191.217.227.74`)
- Se for diferente, o IP mudou (IP dinâmico)

### 6. Reiniciar Servidor Vite

**Após as mudanças no vite.config.ts:**
1. Pare o servidor atual (Ctrl+C)
2. Reinicie: `npm run dev`
3. Verifique se está escutando em `0.0.0.0:5170`

### 7. Teste com Outra Porta

**Se a porta 5170 estiver bloqueada:**
1. Altere a porta no `src/config.json` para `8080` (ou outra)
2. Configure o port forwarding para a nova porta
3. Reinicie o servidor

## Comandos Úteis

### Verificar se a porta está escutando:
```bash
netstat -ano | findstr :5170
```
Deve mostrar: `TCP    0.0.0.0:5170           0.0.0.0:0              LISTENING`

### Verificar regras de firewall:
```bash
netsh advfirewall firewall show rule name="SSM Teste TCP 5170" verbose
```

### Testar conectividade local:
```bash
curl http://192.168.100.3:5170
```

## Próximos Passos

1. **Reinicie o servidor Vite** com as novas configurações
2. **Verifique o port forwarding** no modem/roteador
3. **Teste de dentro da rede local** primeiro (`192.168.100.3:5170`)
4. **Teste de fora da rede** (`191.217.227.74:5170`)
5. Se não funcionar, **tente outra porta** (ex: 8080)

## Nota Importante

Se o problema persistir mesmo após todas as verificações, é muito provável que seja:
- **CGNAT do ISP** (impede port forwarding)
- **Bloqueio de porta pelo ISP**
- **Configuração incorreta do port forwarding no modem**

Nesses casos, considere:
- Contatar o ISP
- Usar um serviço de túnel (ngrok, Cloudflare Tunnel)
- Usar uma VPN

