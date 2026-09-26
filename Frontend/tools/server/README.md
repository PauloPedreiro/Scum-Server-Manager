# SSM Server - Servidor HTTP Standalone

Servidor HTTP standalone em Go que serve a aplicação React SSM 3.0 sem precisar de Node.js ou outras dependências.

## 📋 Requisitos

- Go 1.21 ou superior
- Build do frontend em `../../dist/` (execute `npm run build` primeiro)

## 🚀 Como Compilar

### Opção 1: Usar Script de Build (Recomendado)

```bash
cd tools
build-server.bat
```

### Opção 2: Compilar Manualmente

```bash
cd tools/server

# Adicionar ícone (opcional, requer rsrc)
go install github.com/akavel/rsrc@latest
rsrc -ico ../Mine_01.ico -o rsrc.syso

# Compilar
go build -ldflags="-s -w" -o ../../dist/SSM-Server.exe
```

## 📦 Estrutura

- `main.go` - Servidor HTTP principal
- `config.go` - Leitura de config.json
- `embed.go` - Embed de arquivos estáticos
- `browser.go` - Abertura automática do navegador

## ⚙️ Configuração

O servidor lê a configuração de `dist/config.json`:
- Porta padrão: 5173
- Host padrão: 0.0.0.0 (aceita conexões de qualquer IP)

Você pode sobrescrever via variáveis de ambiente:
- `SSM_PORT` - Porta do servidor
- `SSM_HOST` - Host do servidor

## 🎯 Como Usar

1. Execute `npm run build` para gerar a pasta `dist/`
2. Compile o servidor: `tools/build-server.bat`
3. Execute `dist/SSM-Server.exe`
4. O navegador abrirá automaticamente em `http://localhost:5173`

## 🔧 Funcionalidades

- ✅ Serve arquivos estáticos embutidos
- ✅ Suporte a SPA (Single Page Application)
- ✅ Serve config.json corretamente
- ✅ Abre navegador automaticamente
- ✅ CORS habilitado
- ✅ Graceful shutdown (Ctrl+C)
- ✅ Zero dependências (executável standalone)

## 📝 Notas

- Os arquivos de `dist/` são embutidos no executável durante a compilação
- Se você modificar arquivos em `dist/`, precisa recompilar o servidor
- O `config.json` é lido do arquivo embutido, mas pode ser editado externamente se necessário

