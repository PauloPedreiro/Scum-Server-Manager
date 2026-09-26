# 🧪 Guia de Teste de Endpoints com Postman no Cursor

## 📋 Como Testar Todos os Endpoints

### 1. Abrir a Extensão do Postman no Cursor

1. No Cursor, procure pela extensão do Postman na barra lateral
2. Clique para abrir o painel do Postman
3. Ou use o atalho: `Ctrl+Shift+P` → digite "Postman" → selecione "Postman: Open"

### 2. Importar a Coleção

**Opção A: Via Interface do Postman**
1. No painel do Postman, clique em **Import** (ou use `Ctrl+O`)
2. Selecione **File**
3. Navegue até: `docs/endpoints/postman-collection.json`
4. Clique em **Import**

**Opção B: Via Drag and Drop**
1. Abra o explorador de arquivos do Cursor (`Ctrl+Shift+E`)
2. Navegue até `docs/endpoints/`
3. Arraste o arquivo `postman-collection.json` para o painel do Postman

### 2. Configurar Variáveis

1. Na coleção importada, clique em **Variables**
2. Configure as seguintes variáveis:
   - `baseUrl`: `http://localhost:3000` (ou `http://192.168.100.3:3000` se estiver em outra máquina)
   - `token`: Deixe vazio (será preenchido automaticamente após login)
   - `username`: `admin`
   - `password`: `admin123`

### 3. Fazer Login Primeiro

1. Na coleção, vá para **Authentication > Login**
2. Clique em **Send**
3. Copie o `token` da resposta
4. Vá em **Variables** da coleção e cole o token na variável `token`

**OU** use o script de teste automático:

```bash
python tools/test_all_endpoints.py
```

### 4. Testar Endpoints

Agora você pode testar qualquer endpoint da coleção. O token será usado automaticamente nos headers.

## 🔍 Endpoints para Testar

### Endpoints Públicos (não precisam de token)
- ✅ `GET /api/health`
- ✅ `GET /api/server/status`
- ✅ `POST /api/auth/login`

### Endpoints Protegidos (precisam de token)
Todos os outros endpoints precisam do token no header `Authorization: Bearer <token>`

## ⚠️ Endpoints que Podem Ter Problemas

Baseado na estrutura do código, estes endpoints podem precisar de atenção:

1. **Endpoints que requerem dados específicos:**
   - `/api/players/<steam_id>/fame` - Precisa de um steam_id válido
   - `/api/squads/<squad_id>` - Precisa de um squad_id válido
   - `/api/rankings/player/<steam_id>` - Precisa de um steam_id válido

2. **Endpoints que podem falhar se o servidor SCUM não estiver rodando:**
   - `/api/server/start`
   - `/api/server/stop`
   - `/api/server/restart`

3. **Endpoints Admin apenas:**
   - `/api/auth/users` (POST, GET, PUT, DELETE)
   - `/api/config` (PUT)
   - `/api/webhooks` (PUT)
   - `/api/scheduler/force-restart`

## 🐛 Como Identificar Problemas

1. **Status 401 (Unauthorized):**
   - Token expirado ou inválido
   - Faça login novamente

2. **Status 403 (Forbidden):**
   - Endpoint requer role de admin
   - Verifique se você está logado como admin

3. **Status 500 (Internal Server Error):**
   - Erro no servidor
   - Verifique os logs do backend

4. **Status 404 (Not Found):**
   - Endpoint não existe ou URL incorreta
   - Verifique a URL na coleção

## 📝 Script de Teste Automático

Se preferir testar automaticamente, execute:

```bash
python tools/test_all_endpoints.py
```

Este script:
- Faz login automaticamente
- Testa todos os endpoints da coleção
- Gera relatório com sucessos e falhas
- Salva resultados em `endpoint_test_results.json`

## 🔧 Atualizar Senha na Coleção

Se a senha mudar, atualize no arquivo `docs/endpoints/postman-collection.json`:

1. Procure por `"password": "12345678910"`
2. Substitua por `"password": "admin123"` (ou sua senha atual)
3. Salve o arquivo
4. Reimporte a coleção no Postman
