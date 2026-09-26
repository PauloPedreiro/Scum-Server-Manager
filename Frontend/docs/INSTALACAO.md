# 📦 Guia de Instalação - SSM 3.0 Frontend

Este guia detalha passo a passo como instalar e configurar o frontend do SSM 3.0.

## 📋 Pré-requisitos

Antes de começar, certifique-se de ter instalado:

- **Node.js** >= 18.0.0
  - Download: https://nodejs.org/
  - Verificar versão: `node --version`

- **npm** >= 9.0.0 (vem com Node.js)
  - Verificar versão: `npm --version`

- **Git** (opcional, para clonar o repositório)
  - Download: https://git-scm.com/

## 🚀 Instalação Passo a Passo

### 1. Obter o Código Fonte

#### Opção A: Clonar do GitHub
```bash
git clone https://github.com/PauloPedreiro/PauloPedreiro-Scum-Server-Manager-3.0-Frontend.git
cd PauloPedreiro-Scum-Server-Manager-3.0-Frontend
```

#### Opção B: Baixar ZIP
1. Acesse: https://github.com/PauloPedreiro/PauloPedreiro-Scum-Server-Manager-3.0-Frontend
2. Clique em "Code" → "Download ZIP"
3. Extraia o arquivo
4. Abra o terminal na pasta extraída

### 2. Instalar Dependências

```bash
npm install
```

Este comando irá:
- Instalar todas as dependências listadas no `package.json`
- Criar a pasta `node_modules/` com todas as bibliotecas
- Gerar `package-lock.json` com versões exatas

**Tempo estimado**: 2-5 minutos (dependendo da conexão)

### 3. Configurar o Backend

Edite o arquivo `src/config.json`:

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

**Importante**: Substitua `192.168.100.3` pelo IP real do seu backend.

### 4. Testar a Conexão com o Backend

Antes de iniciar o frontend, verifique se o backend está acessível:

```bash
# No Windows (PowerShell)
curl http://192.168.100.3:3000/api/server/status

# Ou abra no navegador:
# http://192.168.100.3:3000/api/server/status
```

Você deve receber uma resposta JSON. Se houver erro de conexão, verifique:
- Backend está rodando?
- Firewall permite conexões na porta 3000?
- IP está correto?

### 5. Iniciar o Servidor de Desenvolvimento

```bash
npm run dev
```

Você verá algo como:
```
  VITE v5.4.21  ready in 500 ms

  ➜  Local:   http://localhost:5173/
  ➜  Network: http://192.168.100.3:5173/
  ➜  press h to show help
```

### 6. Acessar a Aplicação

Abra o navegador em:
- **Local**: http://localhost:5173
- **Rede**: http://[SEU_IP]:5173

---

## 🏗️ Build para Produção

Para gerar uma build otimizada para produção:

```bash
npm run build
```

Isso irá:
- Compilar o TypeScript
- Minificar JavaScript e CSS
- Otimizar imagens e assets
- Gerar a pasta `dist/` com os arquivos prontos

### Servir a Build

Para testar a build de produção localmente:

```bash
npm run preview
```

Para servir em produção, você pode usar:
- **Nginx**: Configure para servir a pasta `dist/`
- **Apache**: Configure DocumentRoot apontando para `dist/`
- **Node.js**: Use `serve` ou `http-server`

#### Exemplo com `serve`:
```bash
npm install -g serve
serve -s dist -l 5173
```

---

## ✅ Verificação da Instalação

Após a instalação, verifique:

1. ✅ **Dependências instaladas**: Pasta `node_modules/` existe
2. ✅ **Backend configurado**: `src/config.json` está correto
3. ✅ **Servidor inicia**: `npm run dev` executa sem erros
4. ✅ **Página carrega**: Navegador mostra a interface
5. ✅ **API conecta**: Status do servidor aparece na Home

---

## 🔧 Configurações Adicionais

### Variáveis de Ambiente

Você pode criar um arquivo `.env` na raiz do projeto:

```env
# URL base da API (opcional)
VITE_API_BASE_URL=http://192.168.100.3:3000/api
```

### Porta Personalizada

Para mudar a porta do servidor de desenvolvimento, edite `src/config.json`:

```json
{
  "frontend": {
    "port": 8080,
    "host": "0.0.0.0"
  }
}
```

---

## 🐛 Problemas Comuns

### Erro: "Cannot find module"

**Solução**: Execute `npm install` novamente.

### Erro: "Port 5173 already in use"

**Solução**: 
- Feche outras instâncias do Vite
- Ou mude a porta em `src/config.json`

### Erro: "ERR_CONNECTION_REFUSED"

**Solução**: 
- Verifique se o backend está rodando
- Verifique o IP/porta em `src/config.json`
- Verifique o firewall

### Erro: "Permission denied" (Linux/Mac)

**Solução**: Use `sudo` ou configure permissões adequadas.

---

## 📝 Próximos Passos

Após a instalação bem-sucedida:

1. Leia a [Documentação Principal](./README.md)
2. Consulte o [Guia de Configuração](./CONFIGURACAO.md)
3. Veja exemplos na [Documentação de API](./API.md)

---

**Última atualização**: 2025-12-03

