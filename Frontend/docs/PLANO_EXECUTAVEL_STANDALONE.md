# 📋 Plano: Executável Standalone (.exe) - SSM 3.0 Frontend

## 🎯 Objetivo

Criar um executável `.exe` que:
- ✅ **NÃO requer Node.js, Python ou qualquer dependência externa**
- ✅ **Serve os arquivos estáticos da aplicação React**
- ✅ **Abre o navegador automaticamente**
- ✅ **Funciona em qualquer máquina Windows**
- ✅ **Inclui ícone personalizado do logo SSM**

## 📊 Análise de Opções

### ⭐ Opção 1: Go + embed (RECOMENDADA)

**Tecnologia:** Go (Golang) com `embed` para arquivos estáticos

**Vantagens:**
- ✅ Executável único e pequeno (~10-15 MB)
- ✅ Zero dependências (não precisa de runtime)
- ✅ Compilação cross-platform (Windows, Linux, Mac)
- ✅ Performance excelente
- ✅ Fácil de manter
- ✅ Suporta ícone personalizado
- ✅ Pode abrir navegador automaticamente

**Desvantagens:**
- ⚠️ Precisa instalar Go SDK (apenas para desenvolvimento)
- ⚠️ Requer criar código Go (~200 linhas)

**Tamanho do executável:** ~10-15 MB (inclui todos os arquivos estáticos embutidos)

**Complexidade:** Média (precisa escrever código Go)

---

### Opção 2: Rust + embed

**Tecnologia:** Rust com `include_dir!` macro

**Vantagens:**
- ✅ Executável muito pequeno (~5-8 MB)
- ✅ Zero dependências
- ✅ Performance excepcional
- ✅ Compilação cross-platform

**Desvantagens:**
- ⚠️ Curva de aprendizado mais íngreme
- ⚠️ Compilação mais lenta
- ⚠️ Requer Rust SDK

**Tamanho do executável:** ~5-8 MB

**Complexidade:** Alta (Rust é mais complexo)

---

### Opção 3: C# (.NET) com servidor HTTP embutido

**Tecnologia:** C# com ASP.NET Core ou servidor HTTP simples

**Vantagens:**
- ✅ Nativo Windows
- ✅ Bom suporte a ícones
- ✅ Fácil de desenvolver (se conhecer C#)

**Desvantagens:**
- ⚠️ Pode precisar de .NET Runtime (ou usar self-contained)
- ⚠️ Executável maior (~50-100 MB self-contained)
- ⚠️ Requer .NET SDK

**Tamanho do executável:** ~50-100 MB (self-contained)

**Complexidade:** Média

---

### Opção 4: Electron (NÃO RECOMENDADO)

**Tecnologia:** Electron (Chromium + Node.js)

**Vantagens:**
- ✅ Interface desktop completa
- ✅ Fácil de desenvolver

**Desvantagens:**
- ❌ Executável MUITO grande (~150-200 MB)
- ❌ Não é o que o usuário precisa (quer servidor web, não app desktop)

**Tamanho do executável:** ~150-200 MB

**Complexidade:** Baixa, mas não adequado

---

### Opção 5: pkg/nexe (Node.js empacotado)

**Tecnologia:** pkg ou nexe (empacota Node.js)

**Vantagens:**
- ✅ Pode usar código Node.js existente
- ✅ Automatizável

**Desvantagens:**
- ⚠️ Executável grande (~40-60 MB)
- ⚠️ Pode ter problemas com binários nativos
- ⚠️ Requer Node.js para build

**Tamanho do executável:** ~40-60 MB

**Complexidade:** Média

---

## 🏆 Recomendação: **Opção 1 - Go + embed**

### Por quê?

1. **Tamanho ideal:** ~10-15 MB (muito menor que outras opções)
2. **Zero dependências:** Funciona em qualquer Windows
3. **Performance:** Excelente para servir arquivos estáticos
4. **Manutenibilidade:** Código Go é simples e fácil de manter
5. **Cross-platform:** Pode compilar para Linux/Mac também
6. **Maturidade:** Go é amplamente usado para este tipo de aplicação

---

## 📝 Plano de Implementação Detalhado

### Fase 1: Preparação do Ambiente

1. **Instalar Go SDK** (apenas para desenvolvimento)
   - Download: https://golang.org/dl/
   - Versão mínima: Go 1.21+
   - Verificar: `go version`

2. **Converter logo para ICO**
   - Converter `SSMlogo.png` → `SSMlogo.ico`
   - Usar ferramenta online ou ImageMagick

3. **Criar estrutura de projeto Go**
   ```
   tools/
   ├── server/
   │   ├── main.go          # Servidor HTTP
   │   ├── embed.go         # Arquivos embutidos
   │   ├── go.mod           # Dependências Go
   │   └── go.sum           # Checksums
   ├── build.bat            # Script de build
   └── SSMlogo.ico          # Ícone do executável
   ```

### Fase 2: Desenvolvimento do Servidor

**Funcionalidades necessárias:**

1. **Servidor HTTP simples**
   - Servir arquivos estáticos da pasta `dist/`
   - Suporte a SPA (redirecionar todas as rotas para `index.html`)
   - Servir `config.json` corretamente (Content-Type: application/json)
   - CORS habilitado

2. **Embed de arquivos**
   - Usar `embed` do Go para embutir todos os arquivos de `dist/`
   - Incluir: `index.html`, `config.json`, `assets/`, etc.

3. **Abertura automática do navegador**
   - Abrir `http://localhost:5173` automaticamente
   - Aguardar servidor iniciar antes de abrir

4. **Configuração via config.json**
   - Ler `config.json` para obter porta e host
   - Permitir override via argumentos de linha de comando

5. **Tratamento de erros**
   - Verificar se porta está em uso
   - Mensagens de erro claras
   - Logs informativos

### Fase 3: Build e Integração

1. **Script de build (`tools/build-server.bat`)**
   ```batch
   @echo off
   cd tools\server
   go build -ldflags="-s -w -H windowsgui" -o ../../dist/SSM-Server.exe
   rsrc -ico SSMlogo.ico -o rsrc.syso
   go build -ldflags="-s -w" -o ../../dist/SSM-Server.exe
   ```

2. **Integração no build do Vite**
   - Adicionar passo no `vite.config.ts` para compilar o servidor Go
   - Ou manter como passo manual/separado

3. **Testes**
   - Testar em máquina com Windows limpo (sem Node.js)
   - Verificar se abre navegador
   - Verificar se serve arquivos corretamente
   - Verificar se `config.json` funciona

### Fase 4: Distribuição

1. **Estrutura final:**
   ```
   dist/
   ├── SSM-Server.exe      # Executável standalone
   ├── config.json          # Configuração (pode ser editada)
   └── README.md            # Instruções
   ```

2. **Documentação:**
   - Atualizar README com instruções
   - Criar guia de uso do executável
   - Documentar como editar `config.json`

---

## 🛠️ Estrutura do Código Go

### `tools/server/main.go`

```go
package main

import (
    "embed"
    "fmt"
    "log"
    "net/http"
    "os"
    "os/exec"
    "runtime"
    "time"
)

//go:embed dist/*
var distFiles embed.FS

func main() {
    // Ler config.json para obter porta
    port := "5173"
    host := "0.0.0.0"
    
    // Servir arquivos estáticos
    http.HandleFunc("/", serveSPA)
    
    addr := fmt.Sprintf("%s:%s", host, port)
    fmt.Printf("Servidor iniciado em http://localhost:%s\n", port)
    
    // Abrir navegador após 1 segundo
    go openBrowser(fmt.Sprintf("http://localhost:%s", port))
    
    log.Fatal(http.ListenAndServe(addr, nil))
}

func serveSPA(w http.ResponseWriter, r *http.Request) {
    // Lógica para servir arquivos e SPA
}
```

---

## 📦 Dependências Go Necessárias

- **Nenhuma!** Go padrão tem tudo que precisamos:
  - `net/http` - Servidor HTTP
  - `embed` - Embed de arquivos
  - `os/exec` - Abrir navegador

---

## ⚙️ Configurações do Executável

- **Nome:** `SSM-Server.exe`
- **Ícone:** `SSMlogo.ico`
- **Tamanho:** ~10-15 MB (com todos os arquivos embutidos)
- **Porta padrão:** 5173 (configurável via `config.json`)
- **Host padrão:** 0.0.0.0 (aceita conexões de qualquer IP)

---

## 🔄 Processo de Build Completo

1. **Build do Frontend:**
   ```bash
   npm run build
   ```
   → Gera `dist/` com arquivos estáticos

2. **Build do Servidor Go:**
   ```bash
   cd tools/server
   go build -o ../../dist/SSM-Server.exe
   ```
   → Gera `dist/SSM-Server.exe` com arquivos embutidos

3. **Distribuição:**
   - Copiar `dist/SSM-Server.exe` para usuário
   - Copiar `dist/config.json` (opcional, pode ser embutido também)
   - Usuário executa `SSM-Server.exe` → Servidor inicia + Navegador abre

---

## ✅ Checklist de Implementação

### Preparação
- [ ] Instalar Go SDK
- [ ] Converter logo PNG → ICO
- [ ] Criar estrutura de pastas `tools/server/`

### Desenvolvimento
- [ ] Criar `main.go` com servidor HTTP
- [ ] Implementar embed de arquivos estáticos
- [ ] Implementar suporte a SPA (redirecionamento)
- [ ] Implementar leitura de `config.json`
- [ ] Implementar abertura automática do navegador
- [ ] Adicionar tratamento de erros
- [ ] Adicionar logs informativos

### Build e Testes
- [ ] Criar script de build (`build-server.bat`)
- [ ] Testar compilação
- [ ] Testar em máquina limpa (sem Node.js)
- [ ] Verificar se serve arquivos corretamente
- [ ] Verificar se `config.json` funciona
- [ ] Verificar se abre navegador
- [ ] Testar acesso externo (rede)

### Distribuição
- [ ] Adicionar ícone ao executável
- [ ] Criar documentação
- [ ] Atualizar README
- [ ] Criar guia de uso

---

## 🎨 Adicionar Ícone ao Executável

### Opção 1: Usar `rsrc` (Windows)
```bash
go install github.com/akavel/rsrc@latest
rsrc -ico SSMlogo.ico -o rsrc.syso
go build -o SSM-Server.exe
```

### Opção 2: Usar `goversioninfo`
```bash
go install github.com/josephspurrier/goversioninfo/cmd/goversioninfo@latest
goversioninfo -icon=SSMlogo.ico
go build -o SSM-Server.exe
```

---

## ⚠️ Considerações Importantes

1. **Antivírus:**
   - Executáveis Go podem ser marcados como suspeitos
   - Solução: Assinar digitalmente (custo) ou confiar no desenvolvedor

2. **Firewall:**
   - Windows pode pedir permissão de firewall
   - Usuário precisa permitir na primeira execução

3. **Porta em uso:**
   - Verificar se porta 5173 está disponível
   - Oferecer porta alternativa se necessário

4. **Config.json:**
   - Pode ser embutido (não editável) ou externo (editável)
   - Recomendação: Externo para permitir configuração

---

## 🚀 Próximos Passos

1. **Decidir:** Aprovar este plano?
2. **Preparar:** Instalar Go SDK e converter logo
3. **Desenvolver:** Criar servidor Go
4. **Testar:** Validar em máquina limpa
5. **Distribuir:** Incluir na build final

---

**Última atualização:** 2025-01-27

