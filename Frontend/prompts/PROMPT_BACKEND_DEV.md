# 🔌 Solicitação de Acesso/Configuração do Backend - SSM Frontend

## 📋 Contexto

Olá! Estou desenvolvendo o **Frontend do sistema SSM** e preciso acessar a **API do Backend** para implementar as funcionalidades de controle do servidor SCUM.

---

## 🎯 Situação Atual

O frontend está tentando se conectar ao backend, mas está recebendo o erro:

```
ERR_CONNECTION_REFUSED
```

**URL de conexão atual configurada:**
```
http://192.168.100.3:3000/api
```

**Configuração no frontend:**
- Protocolo: `http`
- Host: `192.168.100.3`
- Porta: `3000`
- Base Path: `/api`

---

## ❓ Solicitações

Preciso de sua ajuda com uma das seguintes opções:

### Opção 1: Confirmar se o backend está rodando
- [ ] O backend está atualmente rodando na porta **3000**?
- [ ] O IP/host `192.168.100.3` está correto?
- [ ] Há alguma configuração especial necessária para iniciar o backend?

### Opção 2: Informar a URL correta
Se a configuração estiver diferente, por favor, informe:
- [ ] **Protocolo:** `http` ou `https`?
- [ ] **Host/IP:** Qual o endereço correto? (ex: `localhost`, `192.168.x.x`, etc.)
- [ ] **Porta:** Qual porta o backend está usando?
- [ ] **Base Path:** Qual o caminho base da API? (ex: `/api`, `/v1/api`, etc.)

### Opção 3: Solicitar permissão/acesso
Se houver restrições de acesso:
- [ ] Preciso de alguma permissão especial?
- [ ] Há firewall que precisa ser configurado?
- [ ] O backend precisa ser configurado para aceitar conexões do frontend?
- [ ] Há CORS que precisa ser configurado?

---

## 📡 Endpoints Necessários

Para implementar a funcionalidade completa, preciso acessar os seguintes endpoints:

### 1. **POST** `/api/server/start`
- Inicia o servidor SCUM
- Body opcional: `{ force: boolean, wait_timeout: number }`

### 2. **POST** `/api/server/stop`
- Para o servidor SCUM
- Body opcional: `{ force: boolean, wait_timeout: number }`

### 3. **POST** `/api/server/restart`
- Reinicia o servidor SCUM
- Body opcional: `{ force: boolean, wait_timeout: number }`

### 4. **GET** `/api/server/status` (opcional, para status futuro)
- Retorna status atual do servidor

---

## 🔍 Informações Técnicas do Frontend

**Ambiente:**
- Framework: React 18 + TypeScript
- Build: Vite
- URL Frontend: `http://localhost:5173` (dev) ou `http://192.168.100.3:5173`
- Cliente HTTP: Axios

**Arquivo de configuração:**
- Localização: `src/config.json`
- Conteúdo atual:
```json
{
  "backend": {
    "host": "192.168.100.3",
    "port": 3000,
    "protocol": "http"
  }
}
```

---

## ✅ Como Testar a Conexão

Para verificar se a conexão está funcionando, posso testar acessando:

1. **Teste simples no navegador:**
   ```
   http://192.168.100.3:3000/api/server/status
   ```
   (ou a URL correta que você informar)

2. **Via Postman/Insomnia:**
   - POST `http://192.168.100.3:3000/api/server/start`
   - Body: `{}` (vazio ou com parâmetros opcionais)

---

## 📝 Exemplo de Resposta Esperada

Se possível, envie algo como:

```
Backend está rodando em:
- URL: http://192.168.100.3:3000
- Base Path: /api
- Status: ✅ Funcionando

Para testar, acesse: http://192.168.100.3:3000/api/server/status
```

**OU**

```
A configuração correta é:
- Protocolo: https
- Host: 192.168.100.5
- Porta: 8080
- Base Path: /v1/api
- Autenticação: Token Bearer necessário (token: xyz...)
```

---

## 🚀 Próximos Passos

Assim que receber as informações:
1. ✅ Atualizarei a configuração no frontend
2. ✅ Testarei a conexão
3. ✅ Implementarei as funcionalidades de controle do servidor
4. ✅ Avisarei quando estiver pronto para testes integrados

---

## 📞 Contato

Qualquer dúvida ou necessidade de ajustes, estou à disposição!

**Obrigado pela colaboração!** 🙏

---

*Este documento foi gerado automaticamente pelo Frontend SSM - Sistema de Gerenciamento do Servidor SCUM*

