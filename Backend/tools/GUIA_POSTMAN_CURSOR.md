# 🧪 Guia Completo: Testar Endpoints com Postman no Cursor

## 📋 Pré-requisitos

✅ Extensão do Postman instalada no Cursor  
✅ Backend rodando na porta 3000  
✅ Coleção do Postman disponível em `docs/endpoints/postman-collection.json`

## 🚀 Como Usar a Extensão do Postman no Cursor

### 1. Abrir o Postman no Cursor

1. No Cursor, procure pela extensão do Postman (geralmente aparece na barra lateral)
2. Clique para abrir o painel do Postman
3. Ou use o atalho: `Ctrl+Shift+P` → digite "Postman"

### 2. Importar a Coleção

**Opção A: Via Interface do Postman**
1. No painel do Postman, clique em **Import**
2. Selecione **File** ou **Link**
3. Navegue até: `docs/endpoints/postman-collection.json`
4. Clique em **Import**

**Opção B: Via Drag and Drop**
1. Abra o explorador de arquivos do Cursor
2. Arraste o arquivo `docs/endpoints/postman-collection.json` para o painel do Postman

### 3. Configurar Variáveis da Coleção

Após importar, configure as variáveis:

1. Na coleção "SCUM Backend API", clique em **Variables**
2. Configure:
   - `baseUrl`: `http://localhost:3000` (ou seu IP se estiver em outra máquina)
   - `token`: Deixe vazio (será preenchido após login)
   - `username`: `admin`
   - `password`: `admin123`

### 4. Fazer Login Primeiro

1. Expanda a coleção → **Authentication** → **Login**
2. Clique em **Send**
3. Na resposta, copie o valor do campo `token`
4. Volte para **Variables** da coleção
5. Cole o token na variável `token`
6. Salve as variáveis

**OU** use o script automático que faz isso:

```bash
.venv\Scripts\python.exe tools/test_all_endpoints.py
```

### 5. Testar Endpoints

Agora você pode:

- **Testar um endpoint específico**: Clique no endpoint e depois em **Send**
- **Testar todos os endpoints**: Use o script Python ou execute manualmente cada um
- **Ver respostas**: As respostas aparecem no painel do Postman

## 🔍 Endpoints para Testar

### Endpoints Públicos (não precisam de token)
- ✅ `GET /api/health`
- ✅ `GET /api/server/status`
- ✅ `POST /api/auth/login`

### Endpoints Protegidos (precisam de token)
Todos os outros endpoints precisam do token no header `Authorization: Bearer {{token}}`

A coleção já está configurada para usar `{{token}}` automaticamente!

## 🐛 Solução de Problemas

### Token Expirado (401 Unauthorized)

1. Faça login novamente (Authentication > Login)
2. Copie o novo token
3. Atualize a variável `token` na coleção

### Backend Não Responde

1. Verifique se o backend está rodando:
   ```bash
   netstat -an | findstr :3000
   ```
2. Verifique os logs do backend
3. Tente acessar `http://localhost:3000/api/health` no navegador

### Erro de CORS

Se aparecer erro de CORS, verifique se o backend está configurado para aceitar requisições do Postman. O backend já tem CORS habilitado por padrão.

### Endpoint Retorna 404

1. Verifique se a URL está correta
2. Verifique se o endpoint existe na coleção
3. Verifique se o backend tem esse endpoint implementado

### Endpoint Retorna 500 (Internal Server Error)

1. Verifique os logs do backend
2. Verifique se os dados enviados estão no formato correto
3. Verifique se o servidor SCUM está rodando (para endpoints que dependem dele)

## 📊 Teste Automático com Script

Para testar todos os endpoints automaticamente:

```bash
# Ativar ambiente virtual (se necessário)
.venv\Scripts\activate.bat

# Executar script de teste
python tools/test_all_endpoints.py
```

O script irá:
- ✅ Fazer login automaticamente
- ✅ Testar todos os endpoints da coleção
- ✅ Renovar token automaticamente se expirar
- ✅ Gerar relatório completo
- ✅ Salvar resultados em `endpoint_test_results.json`

## 📝 Estrutura da Coleção

A coleção está organizada em pastas:

- **Health Check** - Verificação de saúde
- **Authentication** - Login, logout, gerenciamento de usuários
- **Server** - Controle do servidor SCUM
- **Configurações do Servidor** - ServerSettings.ini
- **Configuração** - config.json
- **Webhooks** - webhooks.json
- **Sistema de Notificações** - Notificações Discord
- **Sistema de Agendamento** - Scheduler
- **Clima** - Weather scheduler
- **Players** - Dados dos jogadores
- **Rankings** - Rankings diversos
- **Squads** - Squads e membros
- **GPS** - Localização dos jogadores
- **Baús** - Chests
- **Flags** - Bandeiras do mapa
- **Logs** - Logs do sistema
- **Permissões** - Sistema de permissões
- **Elevated Users** - Usuários elevados
- **Survival Stats** - Estatísticas de sobrevivência
- E mais...

## ⚡ Dicas

1. **Use variáveis**: A coleção usa `{{baseUrl}}` e `{{token}}` - configure uma vez, use em todos os endpoints
2. **Salve exemplos**: Após testar, salve as respostas como exemplos na coleção
3. **Organize por ambiente**: Crie diferentes valores para `baseUrl` (localhost, produção, etc.)
4. **Use o script para testes rápidos**: O script Python testa tudo automaticamente
5. **Verifique logs**: Sempre verifique os logs do backend quando um endpoint falhar

## 🔗 Recursos

- Coleção do Postman: `docs/endpoints/postman-collection.json`
- Script de teste: `tools/test_all_endpoints.py`
- Lista de endpoints: `tools/endpoints_list.md`
- Documentação da API: `docs/`
