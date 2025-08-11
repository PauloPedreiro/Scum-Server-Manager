# 🔨 Build do Scum Server Manager

## 📋 Pré-requisitos

1. **Node.js** (versão 18 ou superior)
2. **npm** ou **yarn**
3. **Pkg** (será instalado automaticamente)

## 🚀 Como Fazer o Build

### 1. **Instalar dependências**
```bash
npm install
```

### 2. **Fazer o build**
```bash
npm run build
```

### 3. **Resultado**
O executável será gerado na pasta `dist/` junto com os arquivos JSON e .env necessários.

## 📁 Estrutura do Build

```
dist/
├── scum-server-manager-backend.exe    # Executável principal
├── src/
│   ├── data/                          # Arquivos JSON (configurações)
│   ├── config/                        # Configurações
│   └── middleware/                    # Middlewares
├── routes/                            # Rotas da API
├── scripts/                           # Scripts utilitários
├── .env                               # Variáveis de ambiente
├── .env.example                       # Exemplo de variáveis
├── nodemon.json                       # Configuração do nodemon
├── BUILD_INFO.json                    # Informações do build
└── README.md                          # Documentação
```

## ⚙️ Configuração

### **Arquivos que podem ser editados após o build:**
- `src/data/server/config.json` - Configurações do servidor
- `src/data/webhooks.json` - Webhooks do Discord
- `src/data/funny_statistics.json` - Estatísticas divertidas
- `src/data/auth/users.json` - Usuários do sistema
- `src/data/players/players.json` - Dados dos jogadores
- `.env` - Variáveis de ambiente
- `nodemon.json` - Configuração do nodemon

### **Arquivos que NÃO devem ser editados:**
- O executável principal
- Arquivos JavaScript compilados

## 🔧 Comandos Disponíveis

```bash
# Build completo (recomendado)
npm run build

# Build apenas com pkg
npm run build-pkg

# Build para Windows
npm run build-win

# Build para Linux
npm run build-linux
```

## 📦 Distribuição

Para distribuir o projeto:

1. **Copie a pasta `dist/` completa**
2. **Configure os arquivos JSON e .env** conforme necessário
3. **Execute o .exe**

## 🔐 Configuração de Segurança

### **Arquivo .env:**
```env
# Configurações do Servidor 
PORT=3000 
HOST=0.0.0.0 
NODE_ENV=development 
JWT_SECRET=seu_jwt_secret_aqui
FRONTEND_URL=http://localhost:5173

# Configurações dos Logs do SCUM 
SCUM_LOG_PATH=C:\\Servers\\Scum\\SCUM\\Saved\\SaveFiles\\Logs
SCUM_LOG_CACHE_PATH=src/data/logs/cache
SCUM_LOG_MAX_RETRIES=2

# Configuração do Webhook
WEBHOOK_URL=sua_url_do_webhook
```

## 🐛 Solução de Problemas

### **Erro de dependências:**
```bash
npm install
npm run build
```

### **Erro de permissão:**
Execute o terminal como administrador

### **Arquivos JSON não encontrados:**
Verifique se a estrutura de pastas está correta

### **Erro de .env:**
Certifique-se de que o arquivo `.env` está na pasta `dist/`

## 📝 Notas Importantes

- ✅ Os arquivos JSON e .env ficam separados do executável
- ✅ Configurações podem ser alteradas sem recompilar
- ✅ O executável é standalone (não precisa do Node.js)
- ✅ Funciona em qualquer Windows 10/11
- ✅ Arquivo .env preserva variáveis de ambiente

## 🔄 Atualizações

Para atualizar o executável:

1. **Faça as alterações no código**
2. **Execute `npm run build`**
3. **Substitua o executável antigo**

Os arquivos JSON e .env podem ser mantidos e não precisam ser recopiados.

## 🚨 Segurança

- **Nunca commite o arquivo `.env`** no Git
- **Use `.env.example`** como template
- **Configure senhas e tokens** apenas no arquivo `.env`
- **Mantenha o `.env` seguro** em produção