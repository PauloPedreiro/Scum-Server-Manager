# 📦 SSM 3.0 Frontend - Distribuição

Este arquivo será copiado para a pasta `dist/` durante o build.

## 📋 Arquivos Necessários

A pasta `dist/` contém todos os arquivos necessários para rodar a aplicação:

- ✅ `index.html` - Arquivo HTML principal
- ✅ `config.json` - Configuração do backend e frontend
- ✅ `assets/` - Todos os arquivos JavaScript, CSS e imagens otimizados

## 🚀 Como Iniciar em Produção

### Opção 1: Usando o script start.bat (Mais Fácil)

1. **Duplo clique em `start.bat`** na pasta `dist/`
2. O script irá:
   - Verificar se `serve` está instalado
   - Oferecer instalar automaticamente se necessário
   - Iniciar o servidor em `http://localhost:5173`

### Opção 2: Usando serve manualmente

```bash
# Instalar serve globalmente (apenas uma vez)
npm install -g serve

# Iniciar o servidor
serve -s . -l 5173
```

### Opção 2: Usando http-server

```bash
# Instalar http-server globalmente (apenas uma vez)
npm install -g http-server

# Iniciar o servidor
http-server . -p 5173 -a 0.0.0.0
```

### Opção 3: Usando Python (se tiver Python instalado)

```bash
# Python 3
python -m http.server 5173

# Ou Python 2
python -m SimpleHTTPServer 5173
```

## ⚙️ Configuração

Antes de iniciar, edite o arquivo `config.json` com as configurações do seu backend:

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
    "host": "0.0.0.0",
    "urls": {
      "external": "http://192.168.100.3:5173",
      "local": "http://localhost:5173"
    }
  }
}
```

**Importante:** 
- Substitua `192.168.100.3` pelo IP real do seu backend e frontend
- `external`: URL para acesso externo (rede)
- `local`: URL para acesso local (backend abre o painel)

## 🌐 Acessar a Aplicação

Após iniciar o servidor, acesse:

- **Local**: http://localhost:5173
- **Rede**: http://[SEU_IP]:5173

## 📝 Notas

- A pasta `dist/` contém apenas os arquivos necessários para produção
- Não é necessário Node.js para rodar a aplicação (apenas para servir os arquivos)
- Para produção real, recomenda-se usar Nginx ou Apache

## 🔧 Troubleshooting

### Erro: "Cannot GET /route"

Configure o servidor para redirecionar todas as rotas para `index.html` (SPA mode).

### Erro: "ERR_CONNECTION_REFUSED" no backend

Verifique:
- Se o backend está rodando
- Se o IP/porta em `config.json` está correto
- Se o firewall permite conexões

---

**Versão**: 1.4.1  
**Última atualização**: 2025-01-27

