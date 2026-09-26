# 🚀 Planejamento Detalhado: Implementação Go + embed

## 📋 Visão Geral

Criar um servidor HTTP standalone em Go que:
- Embuta todos os arquivos estáticos da aplicação React
- Serve como SPA (Single Page Application)
- Lê `config.json` para configuração
- Abre navegador automaticamente
- Gera executável `.exe` com ícone personalizado

---

## 🎯 Objetivos por Fase

### Fase 1: Preparação e Setup
- Instalar Go SDK
- Criar estrutura de projeto
- Converter logo para ICO

### Fase 2: Desenvolvimento do Servidor
- Implementar servidor HTTP básico
- Implementar embed de arquivos
- Implementar suporte a SPA
- Implementar leitura de config.json

### Fase 3: Funcionalidades Avançadas
- Abertura automática do navegador
- Tratamento de erros robusto
- Logs informativos
- Suporte a CORS

### Fase 4: Build e Distribuição
- Script de build automatizado
- Adicionar ícone ao executável
- Integração com processo de build do Vite
- Testes e validação

---

## 📁 Estrutura de Arquivos

```
Frontend/
├── tools/
│   ├── server/                    # Projeto Go
│   │   ├── main.go                # Servidor HTTP principal
│   │   ├── config.go              # Leitura de config.json
│   │   ├── embed.go               # Embed de arquivos estáticos
│   │   ├── browser.go             # Abertura do navegador
│   │   ├── go.mod                 # Dependências Go
│   │   ├── go.sum                 # Checksums
│   │   └── versioninfo.json       # Metadados do executável
│   ├── build-server.bat           # Script de build
│   ├── build-server.sh            # Script de build (Linux/Mac)
│   ├── Mine_01.png                # Imagem original (mina)
│   └── Mine_01.ico                 # Ícone do executável (convertido)
├── dist/                           # Build do frontend
│   ├── index.html
│   ├── config.json
│   ├── assets/
│   └── ...
└── vite.config.ts                 # Atualizar para build do servidor
```

---

## 🔧 Fase 1: Preparação e Setup

### Tarefa 1.1: Instalar Go SDK

**Requisitos:**
- Go 1.21 ou superior
- Windows 10/11

**Passos:**
1. Download: https://golang.org/dl/
2. Instalar Go (padrão: `C:\Program Files\Go`)
3. Verificar instalação:
   ```bash
   go version
   ```
4. Configurar GOPATH (opcional, Go 1.11+ usa módulos)

**Validação:**
```bash
go version
# Deve mostrar: go version go1.21.x windows/amd64
```

---

### Tarefa 1.2: Criar Estrutura de Projeto

**Ações:**
1. Criar pasta `tools/server/`
2. Inicializar módulo Go:
   ```bash
   cd tools/server
   go mod init ssm-server
   ```
3. Criar arquivos base:
   - `main.go`
   - `config.go`
   - `embed.go`
   - `browser.go`

**Estrutura inicial:**
```bash
mkdir -p tools/server
cd tools/server
go mod init ssm-server
```

---

### Tarefa 1.3: Converter Logo para ICO

**Opções:**

**Imagem escolhida:** `Mine_01.png` (já copiada para `tools/Mine_01.png`)

**Opção A: Online (Mais Fácil)**
1. Acessar: https://convertio.co/png-ico/
2. Upload: `tools/Mine_01.png`
3. Download: `Mine_01.ico`
4. Salvar em: `tools/Mine_01.ico`

**Opção B: ImageMagick (Se instalado)**
```bash
magick tools/Mine_01.png -define icon:auto-resize=256,128,64,48,32,16 tools/Mine_01.ico
```

**Opção C: GIMP/Photoshop**
- Abrir `tools/Mine_01.png`
- Exportar como ICO
- Múltiplos tamanhos: 16x16, 32x32, 48x48, 256x256

**Validação:**
- Arquivo `tools/Mine_01.ico` existe
- Tamanho: ~50-200 KB
- Múltiplos tamanhos embutidos

---

## 💻 Fase 2: Desenvolvimento do Servidor

### Tarefa 2.1: Implementar Servidor HTTP Básico

**Arquivo:** `tools/server/main.go`

**Funcionalidades:**
- Servidor HTTP na porta 5173 (padrão)
- Handler para servir arquivos estáticos
- Handler para SPA (redirecionar rotas para index.html)
- Handler especial para config.json (Content-Type correto)

**Código base:**
```go
package main

import (
    "embed"
    "fmt"
    "log"
    "net/http"
    "os"
    "path/filepath"
    "strings"
)

//go:embed dist/*
var distFiles embed.FS

func main() {
    // Ler configuração
    port := "5173"
    host := "0.0.0.0"
    
    // Configurar handlers
    http.HandleFunc("/", serveSPA)
    http.HandleFunc("/config.json", serveConfig)
    
    addr := fmt.Sprintf("%s:%s", host, port)
    log.Printf("🚀 Servidor SSM iniciado em http://localhost:%s", port)
    
    // Abrir navegador
    go openBrowser(fmt.Sprintf("http://localhost:%s", port))
    
    // Iniciar servidor
    if err := http.ListenAndServe(addr, nil); err != nil {
        log.Fatalf("❌ Erro ao iniciar servidor: %v", err)
    }
}

func serveSPA(w http.ResponseWriter, r *http.Request) {
    // Lógica para servir arquivos ou redirecionar para index.html
}

func serveConfig(w http.ResponseWriter, r *http.Request) {
    // Servir config.json com Content-Type correto
}
```

---

### Tarefa 2.2: Implementar Embed de Arquivos

**Arquivo:** `tools/server/embed.go`

**Funcionalidades:**
- Embed de todos os arquivos de `dist/`
- Função helper para ler arquivos embutidos
- Suporte a subdiretórios (assets/)

**Código:**
```go
package main

import (
    "embed"
    "io/fs"
    "net/http"
    "path/filepath"
    "strings"
)

//go:embed dist/*
var distFiles embed.FS

// getFileSystem retorna o filesystem embutido sem o prefixo "dist/"
func getFileSystem() http.FileSystem {
    fsys, err := fs.Sub(distFiles, "dist")
    if err != nil {
        panic(err)
    }
    return http.FS(fsys)
}

// serveFile serve um arquivo do filesystem embutido
func serveFile(w http.ResponseWriter, r *http.Request, path string) {
    // Normalizar path
    path = strings.TrimPrefix(path, "/")
    if path == "" {
        path = "index.html"
    }
    
    // Tentar servir arquivo
    file, err := distFiles.Open("dist/" + path)
    if err != nil {
        // Se não encontrou, servir index.html (SPA)
        path = "index.html"
        file, err = distFiles.Open("dist/" + path)
        if err != nil {
            http.NotFound(w, r)
            return
        }
    }
    defer file.Close()
    
    // Detectar Content-Type
    contentType := getContentType(path)
    w.Header().Set("Content-Type", contentType)
    
    // Servir arquivo
    http.ServeContent(w, r, filepath.Base(path), modTime, file)
}
```

---

### Tarefa 2.3: Implementar Suporte a SPA

**Funcionalidades:**
- Todas as rotas que não são arquivos → redirecionar para `index.html`
- Exceções: `/config.json`, `/assets/*`, arquivos com extensão

**Lógica:**
```go
func serveSPA(w http.ResponseWriter, r *http.Request) {
    path := r.URL.Path
    
    // Se for config.json, usar handler específico
    if path == "/config.json" {
        serveConfig(w, r)
        return
    }
    
    // Se tiver extensão de arquivo, tentar servir
    if hasFileExtension(path) {
        serveFile(w, r, path)
        return
    }
    
    // Caso contrário, servir index.html (SPA)
    serveFile(w, r, "/index.html")
}

func hasFileExtension(path string) bool {
    ext := filepath.Ext(path)
    return ext != "" && ext != "/"
}
```

---

### Tarefa 2.4: Implementar Leitura de config.json

**Arquivo:** `tools/server/config.go`

**Funcionalidades:**
- Ler `config.json` embutido
- Extrair porta e host
- Permitir override via variáveis de ambiente
- Validação de configuração

**Código:**
```go
package main

import (
    "embed"
    "encoding/json"
    "fmt"
    "os"
)

//go:embed dist/config.json
var configJSON embed.FS

type Config struct {
    Frontend struct {
        Port string `json:"port"`
        Host string `json:"host"`
    } `json:"frontend"`
}

func loadConfig() (string, string, error) {
    // Tentar ler config.json embutido
    data, err := configJSON.ReadFile("dist/config.json")
    if err != nil {
        return "5173", "0.0.0.0", nil // Valores padrão
    }
    
    var config Config
    if err := json.Unmarshal(data, &config); err != nil {
        return "5173", "0.0.0.0", nil
    }
    
    port := config.Frontend.Port
    host := config.Frontend.Host
    
    // Override via variáveis de ambiente
    if envPort := os.Getenv("SSM_PORT"); envPort != "" {
        port = envPort
    }
    if envHost := os.Getenv("SSM_HOST"); envHost != "" {
        host = envHost
    }
    
    return port, host, nil
}
```

---

## 🎨 Fase 3: Funcionalidades Avançadas

### Tarefa 3.1: Abertura Automática do Navegador

**Arquivo:** `tools/server/browser.go`

**Funcionalidades:**
- Abrir navegador padrão
- Aguardar servidor iniciar (1-2 segundos)
- Suportar Windows, Linux, Mac

**Código:**
```go
package main

import (
    "os/exec"
    "runtime"
    "time"
)

func openBrowser(url string) {
    // Aguardar servidor iniciar
    time.Sleep(1 * time.Second)
    
    var cmd *exec.Cmd
    switch runtime.GOOS {
    case "windows":
        cmd = exec.Command("cmd", "/c", "start", url)
    case "darwin":
        cmd = exec.Command("open", url)
    case "linux":
        cmd = exec.Command("xdg-open", url)
    default:
        return
    }
    
    if err := cmd.Run(); err != nil {
        // Ignorar erros (navegador pode não estar disponível)
    }
}
```

---

### Tarefa 3.2: Tratamento de Erros Robusto

**Funcionalidades:**
- Verificar se porta está em uso
- Mensagens de erro claras
- Logs informativos
- Graceful shutdown

**Código:**
```go
func checkPortAvailable(port string) error {
    addr := fmt.Sprintf(":%s", port)
    listener, err := net.Listen("tcp", addr)
    if err != nil {
        return fmt.Errorf("porta %s já está em uso", port)
    }
    listener.Close()
    return nil
}

func main() {
    port, host, err := loadConfig()
    if err != nil {
        log.Fatalf("❌ Erro ao carregar configuração: %v", err)
    }
    
    if err := checkPortAvailable(port); err != nil {
        log.Fatalf("❌ %v", err)
    }
    
    // ... resto do código
}
```

---

### Tarefa 3.3: Logs Informativos

**Funcionalidades:**
- Logs coloridos (se suportado)
- Informações de inicialização
- URLs de acesso
- Status do servidor

**Código:**
```go
func printStartupInfo(port, host string) {
    fmt.Println("╔════════════════════════════════════════╗")
    fmt.Println("║   SSM 3.0 - Servidor Frontend          ║")
    fmt.Println("╚════════════════════════════════════════╝")
    fmt.Printf("🌐 Servidor iniciado em:\n")
    fmt.Printf("   Local:   http://localhost:%s\n", port)
    if host == "0.0.0.0" {
        fmt.Printf("   Rede:    http://[SEU_IP]:%s\n", port)
    }
    fmt.Printf("📦 Arquivos embutidos: %d arquivos\n", countFiles())
    fmt.Println("🛑 Pressione Ctrl+C para parar")
    fmt.Println()
}
```

---

### Tarefa 3.4: Suporte a CORS

**Funcionalidades:**
- Headers CORS apropriados
- Suporte a requisições do backend
- Configurável

**Código:**
```go
func corsMiddleware(next http.HandlerFunc) http.HandlerFunc {
    return func(w http.ResponseWriter, r *http.Request) {
        w.Header().Set("Access-Control-Allow-Origin", "*")
        w.Header().Set("Access-Control-Allow-Methods", "GET, POST, PUT, DELETE, OPTIONS")
        w.Header().Set("Access-Control-Allow-Headers", "Content-Type, Authorization")
        
        if r.Method == "OPTIONS" {
            w.WriteHeader(http.StatusOK)
            return
        }
        
        next(w, r)
    }
}
```

---

## 🔨 Fase 4: Build e Distribuição

### Tarefa 4.1: Script de Build Automatizado

**Arquivo:** `tools/build-server.bat`

**Funcionalidades:**
- Verificar se Go está instalado
- Compilar servidor
- Adicionar ícone
- Copiar para dist/

**Código:**
```batch
@echo off
chcp 65001 >nul
echo.
echo ========================================
echo   Build do Servidor Go - SSM 3.0
echo ========================================
echo.

REM Verificar se Go está instalado
where go >nul 2>&1
if errorlevel 1 (
    echo [ERRO] Go não está instalado!
    echo.
    echo Instale Go: https://golang.org/dl/
    pause
    exit /b 1
)

echo [OK] Go encontrado!
go version
echo.

REM Verificar se dist/ existe
if not exist "..\dist\index.html" (
    echo [ERRO] Pasta dist/ não encontrada!
    echo.
    echo Execute 'npm run build' primeiro.
    pause
    exit /b 1
)

echo [OK] Pasta dist/ encontrada!
echo.

REM Entrar na pasta do servidor
cd server
if errorlevel 1 (
    echo [ERRO] Pasta tools/server/ não encontrada!
    pause
    exit /b 1
)

echo Compilando servidor...
echo.

REM Compilar com ícone (se rsrc estiver instalado)
where rsrc >nul 2>&1
if not errorlevel 1 (
    echo Adicionando ícone (Mine_01.ico)...
    rsrc -ico ..\Mine_01.ico -o rsrc.syso
    if errorlevel 1 (
        echo [AVISO] Erro ao adicionar ícone, continuando sem ícone...
    )
)

REM Compilar
go build -ldflags="-s -w" -o ..\..\dist\SSM-Server.exe
if errorlevel 1 (
    echo [ERRO] Falha na compilação!
    pause
    exit /b 1
)

echo.
echo [OK] Servidor compilado com sucesso!
echo.
echo Executável: ..\..\dist\SSM-Server.exe
echo.
pause
```

---

### Tarefa 4.2: Adicionar Ícone ao Executável

**Opção A: Usar `rsrc` (Recomendado para Windows)**

1. Instalar rsrc:
   ```bash
   go install github.com/akavel/rsrc@latest
   ```

2. Gerar arquivo de recursos:
   ```bash
   rsrc -ico Mine_01.ico -o rsrc.syso
   ```

3. Compilar:
   ```bash
   go build -o SSM-Server.exe
   ```

**Opção B: Usar `goversioninfo`**

1. Instalar:
   ```bash
   go install github.com/josephspurrier/goversioninfo/cmd/goversioninfo@latest
   ```

2. Criar `versioninfo.json`:
   ```json
   {
     "FixedFileInfo": {
       "FileVersion": {
         "Major": 1,
         "Minor": 0,
         "Patch": 0,
         "Build": 0
       }
     },
     "StringFileInfo": {
       "CompanyName": "SSM",
       "FileDescription": "SSM 3.0 Frontend Server",
       "FileVersion": "1.0.0",
       "ProductName": "SSM Server"
     },
     "IconPath": "Mine_01.ico"
   }
   ```

3. Gerar e compilar:
   ```bash
   goversioninfo -icon=Mine_01.ico
   go build -o SSM-Server.exe
   ```

---

### Tarefa 4.3: Integração com Build do Vite

**Arquivo:** `vite.config.ts`

**Modificações:**
```typescript
{
  name: 'build-go-server',
  closeBundle() {
    // Executar build do servidor Go após build do frontend
    const { execSync } = require('child_process');
    try {
      console.log('🔨 Compilando servidor Go...');
      execSync('cd tools && build-server.bat', { 
        stdio: 'inherit',
        cwd: __dirname 
      });
      console.log('✓ Servidor Go compilado!');
    } catch (error) {
      console.warn('⚠️ Erro ao compilar servidor Go (pode ser ignorado se Go não estiver instalado)');
    }
  }
}
```

---

### Tarefa 4.4: Testes e Validação

**Checklist de Testes:**

1. **Teste Local:**
   - [ ] Executar `SSM-Server.exe`
   - [ ] Verificar se servidor inicia na porta 5173
   - [ ] Verificar se navegador abre automaticamente
   - [ ] Verificar se aplicação carrega corretamente
   - [ ] Verificar se `config.json` é servido corretamente
   - [ ] Testar rotas da SPA (ex: `/players`, `/settings`)

2. **Teste em Máquina Limpa:**
   - [ ] Copiar `SSM-Server.exe` para máquina sem Node.js
   - [ ] Executar e verificar funcionamento
   - [ ] Verificar se não há dependências faltando

3. **Teste de Rede:**
   - [ ] Acessar de outra máquina na rede
   - [ ] Verificar se `config.json` funciona
   - [ ] Verificar se API do backend funciona

4. **Teste de Ícone:**
   - [ ] Verificar se ícone aparece no Windows Explorer
   - [ ] Verificar se ícone aparece na barra de tarefas

---

## 📝 Checklist Completo de Implementação

### Preparação
- [ ] Instalar Go SDK (1.21+)
- [ ] Verificar instalação: `go version`
- [ ] Converter logo PNG → ICO
- [ ] Criar estrutura `tools/server/`
- [ ] Inicializar módulo Go: `go mod init ssm-server`

### Desenvolvimento
- [ ] Criar `main.go` (servidor HTTP básico)
- [ ] Criar `embed.go` (embed de arquivos)
- [ ] Criar `config.go` (leitura de config.json)
- [ ] Criar `browser.go` (abertura do navegador)
- [ ] Implementar handler SPA
- [ ] Implementar handler config.json
- [ ] Implementar tratamento de erros
- [ ] Implementar logs informativos
- [ ] Implementar CORS

### Build
- [ ] Criar `build-server.bat`
- [ ] Instalar `rsrc` ou `goversioninfo`
- [ ] Testar compilação
- [ ] Adicionar ícone ao executável
- [ ] Integrar com build do Vite (opcional)

### Testes
- [ ] Teste local completo
- [ ] Teste em máquina limpa
- [ ] Teste de rede
- [ ] Verificar tamanho do executável (~10-15 MB)

### Documentação
- [ ] Atualizar README.md
- [ ] Criar guia de uso do executável
- [ ] Documentar processo de build
- [ ] Adicionar troubleshooting

---

## 🚀 Ordem de Execução Recomendada

1. **Fase 1:** Preparação (30 min)
   - Instalar Go
   - Converter logo
   - Criar estrutura

2. **Fase 2:** Desenvolvimento (2-3 horas)
   - Implementar servidor básico
   - Implementar embed
   - Implementar SPA

3. **Fase 3:** Funcionalidades (1 hora)
   - Abertura do navegador
   - Tratamento de erros
   - Logs

4. **Fase 4:** Build (1 hora)
   - Script de build
   - Adicionar ícone
   - Testes

**Tempo total estimado:** 4-5 horas

---

## 📚 Recursos e Referências

- **Go Embed:** https://pkg.go.dev/embed
- **Go HTTP Server:** https://pkg.go.dev/net/http
- **rsrc (Ícone):** https://github.com/akavel/rsrc
- **goversioninfo:** https://github.com/josephspurrier/goversioninfo

---

**Última atualização:** 2025-01-27

