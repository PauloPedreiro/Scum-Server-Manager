# 🧪 Script de Teste de Endpoints

## 📋 Como Usar

### 1. Certifique-se de que o backend está rodando

O backend deve estar rodando na porta 3000. Você pode verificar com:

```bash
# Verificar se a porta 3000 está em uso
netstat -an | findstr :3000
```

### 2. Configure as credenciais

Edite o arquivo `tools/test_endpoints.py` e ajuste:

```python
BASE_URL = "http://localhost:3000"  # Ou o IP da sua máquina
USERNAME = "admin"
PASSWORD = "admin123"  # Sua senha atual
```

### 3. Execute o script

```bash
python tools/test_endpoints.py
```

## 📊 O que o script faz

1. **Faz login** e obtém o token JWT
2. **Testa todos os principais endpoints** da API
3. **Gera um relatório** com sucessos e falhas
4. **Salva os resultados** em `endpoint_test_results.json`

## 🔍 Endpoints Testados

O script testa os seguintes grupos de endpoints:

- ✅ Health Check
- ✅ Autenticação
- ✅ Servidor (status, configurações)
- ✅ Configuração (config.json)
- ✅ Webhooks
- ✅ Agendador
- ✅ Clima
- ✅ Players
- ✅ Rankings
- ✅ Squads
- ✅ GPS
- ✅ Baús
- ✅ Flags
- ✅ Logs
- ✅ Notificações
- ✅ Permissões
- ✅ Elevated Users
- ✅ Survival Stats

## 📝 Resultados

Os resultados são salvos em `endpoint_test_results.json` com:
- Status code de cada requisição
- Resposta completa
- Mensagens de erro (se houver)

## ⚠️ Notas

- Alguns endpoints podem falhar se o servidor SCUM não estiver rodando
- Endpoints que requerem dados específicos podem retornar vazios
- O script usa timeout de 10 segundos por requisição
