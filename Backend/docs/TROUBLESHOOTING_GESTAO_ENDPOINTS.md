# 🔍 Troubleshooting: Endpoints do Gestão Retornando "Not Found"

## ❌ Problemas Identificados

### Problema 1: Endpoints Retornando "Not Found"
Ao tentar acessar os endpoints do Gestão via Postman, estava retornando:
- **GET** `/api/servers/ready?server_hash={{serverHash}}` → `{"detail": "Not Found"}`
- **POST** `/api/servers/sync` → `{"detail": "Not Found"}`

**✅ RESOLVIDO**: Os endpoints usam o prefixo `/api/v1/` em vez de `/api/`.

### Problema 2: Erro 500 no Endpoint de Sincronização
- **POST** `/api/v1/servers/sync` → `500 Internal Server Error`
- **Erro**: `"float() argument must be a string or a real number, not 'NoneType'"`

**⚠️ PENDENTE**: Bug no processamento do Gestão. Ver documentação: `docs/CORRECAO_BUG_SINCRONIZACAO_GESTAO.md`

## 🔎 Possíveis Causas

### 1. **Prefixo de Versão da API Faltando**

O Gestão pode estar usando um prefixo de versão que não está na documentação.

**Verificar:**
- O Gestão pode estar usando `/api/v1/servers/ready` em vez de `/api/servers/ready`
- Ou `/v1/api/servers/ready`
- Ou apenas `/servers/ready` (sem `/api`)

**Teste no Postman:**
```
GET {{gestaoUrl}}/api/v1/servers/ready?server_hash={{serverHash}}
GET {{gestaoUrl}}/v1/api/servers/ready?server_hash={{serverHash}}
GET {{gestaoUrl}}/servers/ready?server_hash={{serverHash}}
```

### 2. **URL Base Incorreta**

A URL base do Gestão pode estar incorreta ou incompleta.

**Verificar no config.json:**
```json
{
  "licensing": {
    "gestao_url": "https://gestao.seudominio.com"  // ← Verificar se está correto
  }
}
```

**Teste no Postman:**
- Verificar se a variável `{{gestaoUrl}}` está configurada corretamente
- Tentar acessar diretamente no navegador: `https://gestao.seudominio.com/api/servers/ready?server_hash=TESTE`

### 3. **Endpoints Não Implementados ou Registrados Incorretamente**

Os endpoints podem não estar registrados no roteador do Gestão.

**Verificar com o desenvolvedor do Gestão:**
- Os endpoints estão registrados no roteador principal?
- Estão dentro de um blueprint ou router específico?
- Há algum middleware bloqueando as requisições?

### 4. **Roteamento com Blueprint/Router**

O Gestão pode estar usando blueprints ou routers que adicionam prefixos.

**Exemplo (Flask):**
```python
# Se o Gestão estiver usando blueprints
bp = Blueprint('servers', __name__, url_prefix='/api')
app.register_blueprint(bp)

# Então os endpoints seriam:
# GET /api/servers/ready
# POST /api/servers/sync
```

**Exemplo (FastAPI):**
```python
# Se o Gestão estiver usando routers
router = APIRouter(prefix="/api")
app.include_router(router)

# Então os endpoints seriam:
# GET /api/servers/ready
# POST /api/servers/sync
```

### 5. **CORS ou Middleware Bloqueando**

Algum middleware pode estar bloqueando as requisições antes de chegar aos endpoints.

**Verificar:**
- Logs do servidor Gestão
- Configuração de CORS
- Middlewares de autenticação/autorização

## 🧪 Passos para Diagnosticar

### Passo 1: Verificar URL Base

1. Abra o Postman
2. Verifique a variável `{{gestaoUrl}}` na aba "Variables"
3. Teste acessar a URL base diretamente no navegador:
   ```
   https://gestao.seudominio.com
   ```
4. Se houver uma página de documentação (Swagger/OpenAPI), verifique os endpoints listados

### Passo 2: Testar Endpoints com Diferentes Prefixos

No Postman, teste estas variações:

**Para GET /api/servers/ready:**
```
GET {{gestaoUrl}}/api/servers/ready?server_hash=TESTE
GET {{gestaoUrl}}/api/v1/servers/ready?server_hash=TESTE
GET {{gestaoUrl}}/v1/api/servers/ready?server_hash=TESTE
GET {{gestaoUrl}}/servers/ready?server_hash=TESTE
```

**Para POST /api/servers/sync:**
```
POST {{gestaoUrl}}/api/servers/sync
POST {{gestaoUrl}}/api/v1/servers/sync
POST {{gestaoUrl}}/v1/api/servers/sync
POST {{gestaoUrl}}/servers/sync
```

### Passo 3: Verificar Documentação do Gestão

Se o Gestão tiver documentação Swagger/OpenAPI:

1. Acesse: `https://gestao.seudominio.com/docs` ou `/swagger` ou `/api-docs`
2. Procure pelos endpoints:
   - `GET /api/servers/ready`
   - `POST /api/servers/sync`
3. Verifique o caminho exato listado na documentação

### Passo 4: Verificar Logs do Gestão

Peça ao desenvolvedor do Gestão para verificar:
- Se as requisições estão chegando ao servidor
- Qual é o caminho exato que está sendo acessado
- Se há erros nos logs relacionados aos endpoints

### Passo 5: Testar com cURL

Teste diretamente via terminal:

```bash
# Teste GET
curl -X GET "https://gestao.seudominio.com/api/servers/ready?server_hash=TESTE" \
  -H "Content-Type: application/json"

# Teste POST
curl -X POST "https://gestao.seudominio.com/api/servers/sync" \
  -H "Content-Type: application/json" \
  -d '{
    "server_hash": "TESTE",
    "api_key": "TESTE"
  }'
```

## ✅ Soluções Possíveis

### Solução 1: Adicionar Prefixo de Versão

Se o Gestão usar `/api/v1/`, atualize o código do SSM Backend:

**Arquivo:** `core/communication/gestao_sync_service.py`

```python
# Linha 103 - Antes:
f"{self.gestao_url}/api/servers/ready",

# Depois (se usar v1):
f"{self.gestao_url}/api/v1/servers/ready",
```

```python
# Linha 190 - Antes:
f"{self.gestao_url}/api/servers/sync",

# Depois (se usar v1):
f"{self.gestao_url}/api/v1/servers/sync",
```

### Solução 2: Remover Prefixo `/api`

Se o Gestão não usar `/api`, remova:

```python
# Antes:
f"{self.gestao_url}/api/servers/ready",

# Depois:
f"{self.gestao_url}/servers/ready",
```

### Solução 3: Configurar Prefixo Dinamicamente

Adicionar configuração no `config.json`:

```json
{
  "licensing": {
    "gestao_url": "https://gestao.seudominio.com",
    "gestao_api_prefix": "/api/v1"  // ← Novo campo
  }
}
```

E usar no código:
```python
api_prefix = licensing_config.get('gestao_api_prefix', '/api')
f"{self.gestao_url}{api_prefix}/servers/ready"
```

## 📋 Checklist para o Desenvolvedor do Gestão

Peça ao desenvolvedor do Gestão para verificar:

- [ ] Os endpoints estão registrados no roteador principal?
- [ ] Qual é o caminho exato dos endpoints? (incluindo prefixos)
- [ ] Há algum middleware bloqueando as requisições?
- [ ] Os endpoints estão acessíveis sem autenticação? (ou qual autenticação é necessária?)
- [ ] Há documentação Swagger/OpenAPI disponível?
- [ ] Qual framework está sendo usado? (Flask, FastAPI, Django, etc.)
- [ ] Os endpoints estão funcionando quando testados diretamente no código?

## 🔗 Referências

- Documentação de implementação: `docs/GESTAO_IMPLEMENTACAO_ENDPOINTS.md`
- Planejamento: `docs/PLANEJAMENTO_ENDPOINT_SINCRONIZACAO_GESTAO.md`
- Código do serviço: `core/communication/gestao_sync_service.py`
- **Bug identificado**: `docs/CORRECAO_BUG_SINCRONIZACAO_GESTAO.md` (correção necessária no Gestão)
- **Resumo do bug**: `docs/RESUMO_BUG_SINCRONIZACAO_GESTAO.md` (versão resumida)

## 💡 Próximos Passos

1. **Testar as variações de URL** no Postman
2. **Verificar a documentação do Gestão** (Swagger/OpenAPI)
3. **Entrar em contato com o desenvolvedor do Gestão** para confirmar:
   - Caminho exato dos endpoints
   - Se há prefixos de versão
   - Se há autenticação necessária
4. **Atualizar o código do SSM Backend** conforme necessário
5. **Atualizar a documentação** com os caminhos corretos

