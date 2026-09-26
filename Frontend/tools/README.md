# 🛠️ Ferramentas de Build - SSM 3.0

Esta pasta contém ferramentas para criar o executável standalone do servidor.

## 📁 Estrutura

```
tools/
├── server/              # Código fonte do servidor Go
│   ├── main.go         # Servidor HTTP principal
│   ├── config.go       # Leitura de config.json
│   ├── embed.go        # Embed de arquivos estáticos
│   ├── browser.go      # Abertura do navegador
│   └── go.mod          # Módulo Go
├── build-server.bat    # Script de build do servidor
├── convert_to_ico.py   # Script para converter PNG → ICO
├── Mine_01.png         # Imagem original (mina)
└── Mine_01.ico         # Ícone do executável
```

## 🚀 Processo de Build Completo

### Passo 1: Build do Frontend
```bash
npm run build
```
Isso gera a pasta `dist/` com todos os arquivos estáticos.

### Passo 2: Instalar Go SDK
1. Download: https://golang.org/dl/
2. Instalar Go (padrão: `C:\Program Files\Go`)
3. Verificar: `go version`

### Passo 3: Instalar rsrc (Opcional - para ícone)
```bash
go install github.com/akavel/rsrc@latest
```

### Passo 4: Compilar Servidor
```bash
cd tools
build-server.bat
```

O executável será gerado em: `dist/SSM-Server.exe`

## ✅ Resultado

Após a compilação, você terá:
- `dist/SSM-Server.exe` - Executável standalone (~10-15 MB)
- Zero dependências (não precisa Node.js, Python, etc.)
- Ícone da mina no Windows Explorer

## 🎯 Como Usar o Executável

1. Copie `SSM-Server.exe` para qualquer máquina Windows
2. Execute o arquivo
3. O navegador abrirá automaticamente em `http://localhost:5173`
4. A aplicação estará disponível!

## ⚠️ Importante

- O servidor Go precisa compilar **APÓS** o build do frontend
- Os arquivos de `dist/` são embutidos no executável durante a compilação
- Se modificar arquivos em `dist/`, precisa recompilar o servidor

## 🔧 Troubleshooting

### "Go não está instalado"
- Instale Go: https://golang.org/dl/
- Adicione ao PATH se necessário

### "dist/ não encontrada"
- Execute `npm run build` primeiro

### "Ícone não aparece"
- Instale rsrc: `go install github.com/akavel/rsrc@latest`
- Verifique se `Mine_01.ico` existe em `tools/`

