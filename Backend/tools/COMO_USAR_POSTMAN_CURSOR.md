# 🚀 Como Usar o Postman no Cursor - Passo a Passo

## ⚠️ IMPORTANTE: Diferença entre Script e Postman

- **Script Python** (`test_all_endpoints.py`): Mostra resultados no **TERMINAL**
- **Postman Console**: Mostra resultados quando você faz requisições **DIRETAMENTE no Postman**

## 📋 Passo a Passo para Ver Resultados no Postman Console

### 1. Verificar se o Backend Está Rodando

Primeiro, certifique-se de que o backend está rodando:

```bash
# Verificar se a porta 3000 está em uso
netstat -an | findstr :3000
```

Ou teste no navegador:
```
http://localhost:3000/api/health
```

### 2. Abrir o Postman no Cursor

1. Procure pelo ícone do **Postman** na barra lateral esquerda do Cursor
2. Ou use `Ctrl+Shift+P` → digite "Postman" → selecione "Postman: Open"
3. O painel do Postman deve abrir

### 3. Importar a Coleção

1. No painel do Postman, clique em **Import** (ou `Ctrl+O`)
2. Selecione **File**
3. Navegue até: `docs/endpoints/postman-collection.json`
4. Clique em **Import**
5. A coleção "SCUM Backend API" deve aparecer na lista

### 4. Configurar Variáveis da Coleção

1. Clique com botão direito na coleção "SCUM Backend API"
2. Selecione **Edit**
3. Vá na aba **Variables**
4. Verifique se `baseUrl` está como `http://localhost:3000`
5. Deixe `token` vazio por enquanto

### 5. Fazer Login (Primeira Requisição)

1. Expanda a coleção → **Authentication** → **Login**
2. Clique no endpoint **Login**
3. Verifique o body (deve ter `username: admin` e `password: admin123`)
4. Clique no botão **Send** (ou `Ctrl+Enter`)
5. **AGORA** você deve ver:
   - A resposta no painel direito
   - Os logs no **Postman Console** (aba inferior)

### 6. Copiar o Token

1. Na resposta do login, copie o valor de `data.token`
2. Volte para **Variables** da coleção
3. Cole o token na variável `token`
4. Salve

### 7. Testar Outros Endpoints

Agora você pode testar qualquer endpoint:

1. Clique em qualquer endpoint (ex: **Health Check**)
2. Clique em **Send**
3. Veja os resultados no **Postman Console**

## 🔍 Onde Ver os Resultados

### No Postman Console (aba inferior):
- Status da requisição
- Headers enviados
- Body da requisição
- Resposta recebida
- Tempo de resposta
- Erros (se houver)

### No Painel Direito:
- Resposta formatada
- Status code
- Headers da resposta
- Body da resposta

## 🐛 Problemas Comuns

### Console Vazio (como você está vendo)

**Causa**: Nenhuma requisição foi enviada ainda pelo Postman

**Solução**:
1. Certifique-se de que a coleção foi importada
2. Clique em um endpoint
3. Clique em **Send**
4. O console deve mostrar os logs

### "No logs yet"

Isso é normal se você ainda não enviou nenhuma requisição. Faça uma requisição primeiro!

### Erro de Conexão

Se aparecer erro de conexão:
1. Verifique se o backend está rodando
2. Verifique se a URL está correta (`http://localhost:3000`)
3. Teste no navegador: `http://localhost:3000/api/health`

### Token Inválido (401)

1. Faça login novamente
2. Copie o novo token
3. Atualize a variável `token` na coleção

## 📊 Teste Rápido

Para verificar se está funcionando:

1. **Abra o Postman no Cursor**
2. **Importe a coleção** (se ainda não importou)
3. **Clique em "Health Check"** (primeiro endpoint)
4. **Clique em "Send"**
5. **Veja o Postman Console** - deve aparecer:
   ```
   GET http://localhost:3000/api/health
   Status: 200 OK
   Time: XXXms
   ```

## 🎯 Dica: Usar o Script Python

Se quiser testar todos os endpoints automaticamente, use o script:

```bash
.venv\Scripts\python.exe tools/test_all_endpoints.py
```

**Mas lembre-se**: O script mostra resultados no **TERMINAL**, não no Postman Console!

Para ver os resultados do script:
- Abra o terminal do Cursor (`Ctrl+`` `)
- Execute o script
- Veja a saída no terminal

## ✅ Checklist

- [ ] Backend está rodando na porta 3000
- [ ] Postman está aberto no Cursor
- [ ] Coleção foi importada
- [ ] Variável `baseUrl` está configurada
- [ ] Fiz login e copiei o token
- [ ] Token está na variável `token` da coleção
- [ ] Enviei uma requisição pelo Postman
- [ ] Vejo logs no Postman Console
