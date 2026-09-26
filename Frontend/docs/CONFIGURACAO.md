# ⚙️ Guia de Configuração - SSM 3.0 Frontend

Este guia explica todas as configurações disponíveis no frontend do SSM 3.0.

## 📄 Arquivo de Configuração Principal

O arquivo `src/config.json` é o principal arquivo de configuração:

```json
{
  "backend": {
    "host": "192.168.100.3",
    "port": 3000,
    "protocol": "http",
    "basePath": "/api",
    "timeout": 60000
  },
  "frontend": {
    "port": 5173,
    "host": "0.0.0.0"
  }
}
```

---

## 🔌 Configurações do Backend

### `host`
- **Tipo**: `string`
- **Padrão**: `"192.168.100.3"`
- **Descrição**: IP ou hostname do servidor backend
- **Exemplo**: `"localhost"`, `"192.168.1.100"`, `"backend.example.com"`

### `port`
- **Tipo**: `number`
- **Padrão**: `3000`
- **Descrição**: Porta do servidor backend
- **Exemplo**: `3000`, `8080`, `443`

### `protocol`
- **Tipo**: `string`
- **Padrão**: `"http"`
- **Valores**: `"http"` ou `"https"`
- **Descrição**: Protocolo usado para comunicação

### `basePath`
- **Tipo**: `string`
- **Padrão**: `"/api"`
- **Descrição**: Caminho base de todas as requisições API
- **Exemplo**: `"/api"`, `"/v1/api"`, `""`

**URL final**: `{protocol}://{host}:{port}{basePath}`

### `timeout`
- **Tipo**: `number`
- **Padrão**: `60000` (60 segundos)
- **Descrição**: Timeout em milissegundos para requisições HTTP
- **Recomendação**: 
  - Desenvolvimento: `30000` (30s)
  - Produção: `60000` (60s)
  - Operações longas: `120000` (120s)

---

## 🖥️ Configurações do Frontend

### `port`
- **Tipo**: `number`
- **Padrão**: `5173`
- **Descrição**: Porta do servidor de desenvolvimento Vite
- **Nota**: Mudanças requerem reiniciar o servidor

### `host`
- **Tipo**: `string`
- **Padrão**: `"0.0.0.0"`
- **Descrição**: Interface de rede para o servidor
- **Valores**:
  - `"0.0.0.0"`: Aceita conexões de qualquer IP (recomendado)
  - `"localhost"`: Apenas localhost
  - `"127.0.0.1"`: Apenas loopback
  - IP específico: `"192.168.1.100"`

### `urls` (Novo)
- **Tipo**: `object`
- **Descrição**: URLs de acesso ao frontend
- **Propriedades**:
  - `external`: URL para acesso externo (por IP da rede)
  - `local`: URL para acesso local (localhost - usado pelo backend para abrir o painel)

**Exemplo:**
```json
{
  "frontend": {
    "port": 5173,
    "host": "0.0.0.0",
    "urls": {
      "external": "http://192.168.100.3:5173",
      "local": "http://localhost:5173"
    }
  }
}
```

**Uso:**
- `external`: Usado para acessar o frontend de outros dispositivos na rede
- `local`: Usado pelo backend SSM para abrir o painel automaticamente

---

## 🌐 Variáveis de Ambiente

Você também pode usar variáveis de ambiente através do arquivo `.env` na raiz do projeto:

### Criar arquivo `.env`

```env
# URL completa da API (opcional - sobrescreve config.json)
VITE_API_BASE_URL=http://192.168.100.3:3000/api

# Outras variáveis (se necessário)
VITE_APP_TITLE=SSM 3.0
```

**Nota**: Variáveis devem começar com `VITE_` para serem expostas ao código.

---

## 📝 Exemplos de Configuração

### Configuração Local (Desenvolvimento)

```json
{
  "backend": {
    "host": "localhost",
    "port": 3000,
    "protocol": "http",
    "basePath": "/api",
    "timeout": 30000
  },
  "frontend": {
    "port": 5173,
    "host": "localhost"
  }
}
```

### Configuração de Rede Local

```json
{
  "backend": {
    "host": "192.168.100.3",
    "port": 3000,
    "protocol": "http",
    "basePath": "/api",
    "timeout": 60000
  },
  "frontend": {
    "port": 5173,
    "host": "0.0.0.0"
  }
}
```

### Configuração de Produção (HTTPS)

```json
{
  "backend": {
    "host": "api.scumserver.com",
    "port": 443,
    "protocol": "https",
    "basePath": "/api",
    "timeout": 60000
  },
  "frontend": {
    "port": 5173,
    "host": "0.0.0.0"
  }
}
```

### Configuração com Porta Customizada

```json
{
  "backend": {
    "host": "192.168.100.3",
    "port": 8080,
    "protocol": "http",
    "basePath": "/api/v1",
    "timeout": 45000
  },
  "frontend": {
    "port": 3000,
    "host": "0.0.0.0"
  }
}
```

---

## 🔄 Aplicar Mudanças

### Durante Desenvolvimento

1. Edite `src/config.json`
2. Salve o arquivo
3. O Vite recarrega automaticamente (HMR)

### Em Produção

1. Edite `src/config.json`
2. Execute `npm run build`
3. A nova build terá as configurações atualizadas

---

## 🔍 Validação da Configuração

### Verificar Configuração Carregada

Abra o console do navegador (F12) e procure por:
```
[API] Base URL: http://192.168.100.3:3000/api
```

### Testar Conexão

No navegador, acesse:
```
http://[BACKEND_HOST]:[BACKEND_PORT]/api/server/status
```

Deve retornar JSON com status do servidor.

---

## 🛡️ Segurança

### Desenvolvimento

- ✅ Usar HTTP está OK
- ✅ `host: "0.0.0.0"` permite acesso da rede local

### Produção

- ⚠️ **Sempre use HTTPS** se expor publicamente
- ⚠️ Configure CORS adequadamente no backend
- ⚠️ Não exponha credenciais no `config.json`
- ⚠️ Use variáveis de ambiente para dados sensíveis

---

## 🐛 Troubleshooting

### Erro: "Cannot connect to backend"

1. Verifique `host` e `port` em `config.json`
2. Teste a URL manualmente no navegador
3. Verifique firewall e rede

### Erro: "Timeout"

1. Aumente `timeout` em `config.json`
2. Verifique se o backend está respondendo lentamente
3. Verifique a rede

### Erro: "CORS Policy"

1. Configure CORS no backend para aceitar o frontend
2. Verifique `protocol`, `host` e `port` estão corretos

### Configuração não está sendo aplicada

1. Certifique-se de salvar `src/config.json`
2. Reinicie o servidor de desenvolvimento
3. Limpe o cache do navegador (Ctrl+Shift+R)

---

## 📚 Referências

- [Documentação Principal](./README.md)
- [Guia de Instalação](./INSTALACAO.md)
- [Documentação de API](./API.md)

---

**Última atualização**: 2025-12-03

