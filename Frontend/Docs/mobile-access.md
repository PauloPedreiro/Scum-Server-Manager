# 📱 Acesso Móvel - Solução de Problemas

## 🔧 **Configuração Atual**

O projeto foi configurado para permitir acesso externo:

```typescript
// vite.config.ts
server: {
  port: 5173,
  host: '0.0.0.0', // Permite acesso externo
  open: false,
  cors: true, // Habilita CORS
  proxy: {
    '/api': {
      target: 'http://127.0.0.1:3000',
      changeOrigin: true,
      secure: false,
    }
  }
}
```

## 🚀 **Como Acessar pelo Celular**

### **Seu IP da Rede: `192.168.100.3`**

**Acesse no celular:**
```
http://192.168.100.3:5173
```

## 🔍 **Diagnóstico Atual**

✅ **Frontend (Vite):** Acessível em `http://192.168.100.3:5173`  
✅ **Backend (API):** Acessível em `http://192.168.100.3:3000`  
✅ **Servidores rodando:** Ambos na porta correta  

## 🛠️ **Possíveis Problemas e Soluções**

### **Problema 1: Firewall do Windows**
**Solução:**
1. Abrir "Firewall do Windows Defender"
2. Clicar em "Permitir um aplicativo ou recurso"
3. Adicionar `node.exe` e permitir nas redes privadas
4. Ou executar como administrador:
```cmd
netsh advfirewall firewall add rule name="Vite Dev Server" dir=in action=allow protocol=TCP localport=5173
netsh advfirewall firewall add rule name="Backend API" dir=in action=allow protocol=TCP localport=3000
```

### **Problema 2: Antivírus Bloqueando**
**Solução:**
- Verificar se o antivírus não está bloqueando Node.js
- Adicionar exceção para a pasta do projeto

### **Problema 3: Rede WiFi com Isolamento**
**Solução:**
- Verificar se o roteador não tem "AP Isolation" ativado
- Celular e PC devem estar na mesma rede WiFi

### **Problema 4: Backend não Aceita Conexões Externas**
**Solução:**
- O backend precisa estar configurado para aceitar `0.0.0.0:3000`
- Se for Node.js/Express:
```javascript
app.listen(3000, '0.0.0.0', () => {
  console.log('Servidor rodando em 0.0.0.0:3000');
});
```

## 🧪 **Testes para Diagnosticar**

### **1. Teste de Ping**
```cmd
# No celular, abrir terminal e executar:
ping 192.168.100.3
```

### **2. Teste de Porta**
```cmd
# No PC, testar se as portas estão abertas:
telnet 192.168.100.3 5173
telnet 192.168.100.3 3000
```

### **3. Teste de Navegador**
- No celular, abrir navegador
- Acessar: `http://192.168.100.3:5173`
- Se não carregar, tentar: `http://192.168.100.3:3000`

## 📋 **Checklist de Verificação**

- [ ] **Frontend rodando:** `npm run dev` mostra "Network: http://192.168.100.3:5173"
- [ ] **Backend rodando:** `http://localhost:3000` funciona no PC
- [ ] **Mesma rede WiFi:** Celular e PC conectados na mesma rede
- [ ] **Firewall:** Portas 5173 e 3000 liberadas
- [ ] **Antivírus:** Não bloqueando Node.js
- [ ] **Roteador:** Sem isolamento de rede ativado

## 🎯 **URLs para Testar**

### **Frontend (Vite)**
```
http://192.168.100.3:5173
```

### **Backend (API)**
```
http://192.168.100.3:3000/api/auth/login
```

## 🔧 **Soluções Alternativas**

### **Se o Problema Persistir:**

1. **Usar IP Fixo no Vite:**
```typescript
// vite.config.ts
server: {
  host: '192.168.100.3', // Seu IP específico
  port: 5173,
}
```

2. **Configurar Proxy Manual:**
```typescript
proxy: {
  '/api': {
    target: 'http://192.168.100.3:3000', // IP do backend
    changeOrigin: true,
    secure: false,
  }
}
```

3. **Usar ngrok (Alternativa):**
```bash
# Instalar ngrok
npm install -g ngrok

# Expor o frontend
ngrok http 5173

# Expor o backend
ngrok http 3000
```

## 📞 **Comandos Úteis**

### **Verificar Status dos Servidores:**
```cmd
netstat -an | findstr :5173
netstat -an | findstr :3000
```

### **Testar Conectividade:**
```cmd
node test-mobile-access.js
```

### **Reiniciar Servidores:**
```cmd
# Parar servidor atual (Ctrl+C)
# Reiniciar
npm run dev
```

## 🚨 **Problemas Comuns**

1. **"ERR_CONNECTION_REFUSED"**
   - Servidor não está rodando
   - Firewall bloqueando

2. **"ERR_NETWORK_CHANGED"**
   - Rede WiFi instável
   - Trocar de rede

3. **"ERR_NAME_NOT_RESOLVED"**
   - IP incorreto
   - Verificar com `ipconfig`

4. **Página carrega mas API não funciona**
   - Backend não aceita conexões externas
   - Configurar backend para `0.0.0.0:3000`

---

**💡 Dica:** Se nada funcionar, tente usar o ngrok para criar um túnel público temporário. 