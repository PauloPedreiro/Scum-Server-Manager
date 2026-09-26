# ⚡ Teste Rápido - Ver Logs no Postman Console

## 🎯 Objetivo: Ver logs no Postman Console

O Postman Console **só mostra logs quando você envia requisições pela interface do Postman**.

## ✅ Passo a Passo Rápido

### 1. Verificar se o Backend Está Rodando

Abra o terminal e execute:
```bash
curl http://localhost:3000/api/health
```

Ou teste no navegador:
```
http://localhost:3000/api/health
```

**Se não funcionar**: O backend não está rodando. Inicie o backend primeiro!

### 2. Abrir o Postman no Cursor

1. Procure o ícone do **Postman** na barra lateral esquerda
2. Clique para abrir
3. Você deve ver o painel do Postman

### 3. Importar a Coleção (se ainda não importou)

1. No painel do Postman, clique em **Import** (ou `Ctrl+O`)
2. Selecione **File**
3. Navegue até: `docs/endpoints/postman-collection.json`
4. Clique em **Import**
5. A coleção "SCUM Backend API" deve aparecer

### 4. Fazer Sua Primeira Requisição

1. Expanda a coleção "SCUM Backend API"
2. Clique em **Health Check** (primeiro endpoint)
3. No painel direito, você verá:
   - URL: `{{baseUrl}}/api/health`
   - Método: `GET`
4. Clique no botão **Send** (ou pressione `Ctrl+Enter`)
5. **AGORA** você deve ver:
   - ✅ Resposta no painel direito
   - ✅ Logs no **Postman Console** (aba inferior)

### 5. Verificar o Postman Console

No **Postman Console** (aba inferior), você deve ver:
```
GET http://localhost:3000/api/health
Status: 200 OK
Time: XXXms
Request Headers:
  ...
Response Headers:
  ...
Response Body:
  {
    "status": "healthy",
    ...
  }
```

## 🔍 Onde Está o Postman Console?

O Postman Console geralmente fica na **parte inferior** do painel do Postman. Se não estiver visível:

1. Procure por uma aba chamada **"Console"** ou **"Logs"**
2. Ou use o atalho: `Ctrl+Shift+C` (pode variar dependendo da extensão)

## 🐛 Se Ainda Não Aparecer Nada

### Problema 1: Backend não está rodando
**Solução**: Inicie o backend primeiro!

### Problema 2: Coleção não foi importada
**Solução**: Importe a coleção novamente (passo 3)

### Problema 3: Não clicou em "Send"
**Solução**: Você precisa clicar em **Send** para enviar a requisição!

### Problema 4: Console não está visível
**Solução**: 
- Procure por uma aba "Console" ou "Logs"
- Ou tente abrir o console do Postman manualmente

## 📝 Teste Simples

Execute este teste rápido:

1. ✅ Backend rodando? → Teste `http://localhost:3000/api/health` no navegador
2. ✅ Postman aberto? → Veja o painel do Postman
3. ✅ Coleção importada? → Veja "SCUM Backend API" na lista
4. ✅ Clique em "Health Check"
5. ✅ Clique em **Send**
6. ✅ Veja o Postman Console → Deve aparecer os logs!

## 💡 Dica

Se você executou o **script Python** (`test_all_endpoints.py`), os resultados aparecem no **TERMINAL**, não no Postman Console!

Para ver os resultados do script:
- Abra o terminal do Cursor (`Ctrl+`` `)
- Execute: `.venv\Scripts\python.exe tools/test_all_endpoints.py`
- Veja a saída no terminal
