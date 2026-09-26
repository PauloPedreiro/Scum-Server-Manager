# 📋 Planejamento: Adicionar Ícone ao System Tray

## 🎯 Objetivo

Adicionar o ícone da aplicação (Mine_01.ico) na **System Tray** (bandeja do sistema) do Windows, permitindo:
- ✅ Ícone visível na área de notificação
- ✅ Menu de contexto ao clicar com botão direito
- ✅ **Opções Start/Stop do servidor**
- ✅ **Notificações Toast do Windows**
- ✅ Minimizar para System Tray (opcional)
- ✅ Fechar janela de console (opcional)

---

## 📊 Análise de Opções

### ⭐ Opção 1: `github.com/getlantern/systray` (RECOMENDADA)

**Biblioteca:** `github.com/getlantern/systray`

**Vantagens:**
- ✅ Multiplataforma (Windows, Linux, Mac)
- ✅ API simples e fácil de usar
- ✅ Bem mantida e documentada
- ✅ Suporta menus de contexto
- ✅ Suporta tooltips
- ✅ Suporta ícones embutidos

**Desvantagens:**
- ⚠️ Adiciona dependência externa
- ⚠️ Aumenta um pouco o tamanho do executável (~1-2 MB)

**Complexidade:** Baixa

**Tamanho adicional:** ~1-2 MB

---

### Opção 2: Windows API Diretamente

**Tecnologia:** Windows API via `syscall` ou `golang.org/x/sys/windows`

**Vantagens:**
- ✅ Sem dependências externas
- ✅ Controle total
- ✅ Tamanho menor

**Desvantagens:**
- ⚠️ Código mais complexo
- ⚠️ Apenas Windows
- ⚠️ Mais difícil de manter

**Complexidade:** Alta

**Tamanho adicional:** ~0 MB (usa APIs do sistema)

---

### Opção 3: `github.com/lxn/walk` (Windows GUI)

**Biblioteca:** `github.com/lxn/walk`

**Vantagens:**
- ✅ Biblioteca completa para GUI Windows
- ✅ Suporta System Tray
- ✅ Suporta janelas, diálogos, etc.

**Desvantagens:**
- ⚠️ Muito pesada para apenas System Tray
- ⚠️ Aumenta significativamente o tamanho
- ⚠️ Apenas Windows

**Complexidade:** Média

**Tamanho adicional:** ~5-10 MB

---

## 🏆 Recomendação: **Opção 1 - systray**

### Por quê?

1. **Simplicidade:** API muito fácil de usar
2. **Multiplataforma:** Funciona em Windows, Linux e Mac
3. **Manutenibilidade:** Código limpo e bem documentado
4. **Funcionalidades:** Suporta tudo que precisamos
5. **Tamanho:** Apenas ~1-2 MB adicionais

---

## 📝 Plano de Implementação

### Fase 1: Preparação (15 minutos)

#### Tarefa 1.1: Adicionar Dependência
- Adicionar `github.com/getlantern/systray` ao `go.mod`
- Executar `go mod tidy`

#### Tarefa 1.2: Preparar Ícone
- Usar `Mine_01.ico` já existente
- Verificar se está acessível para embed

---

### Fase 2: Implementação (1-2 horas)

#### Tarefa 2.1: Criar `tray.go`
- Criar arquivo `tools/server/tray.go`
- Implementar inicialização do System Tray
- Implementar menu de contexto

#### Tarefa 2.2: Integrar com `main.go`
- Modificar `main.go` para usar System Tray
- Executar servidor HTTP em goroutine
- Executar System Tray na goroutine principal

#### Tarefa 2.3: Menu de Contexto
- "▶️ Iniciar Servidor" - Inicia o servidor HTTP
- "⏹️ Parar Servidor" - Para o servidor HTTP
- Separador
- "Abrir no Navegador" - Abre http://localhost:5173
- Separador
- "Sair" - Encerra aplicação

---

### Fase 3: Funcionalidades Avançadas (30 minutos)

#### Tarefa 3.1: Tooltip
- Mostrar status do servidor
- Ex: "SSM Server - Rodando na porta 5173"

#### Tarefa 3.2: Notificações Toast (OBRIGATÓRIO)
- Notificação Toast quando servidor inicia
- Notificação Toast quando servidor para
- Notificação Toast quando servidor é iniciado via menu
- Notificação Toast quando servidor é parado via menu
- Usar Windows Toast API (Windows 10/11)

#### Tarefa 3.3: Ocultar Console (Opcional)
- Opção para compilar sem janela de console
- Usar `-ldflags="-H windowsgui"` para Windows

---

### Fase 4: Build e Testes (30 minutos)

#### Tarefa 4.1: Atualizar Script de Build
- Verificar se dependências são baixadas
- Testar compilação

#### Tarefa 4.2: Testes
- Testar System Tray aparece
- Testar menu de contexto
- Testar ações do menu
- Testar encerramento

---

## 🛠️ Estrutura do Código

### `tools/server/tray.go`

```go
package main

import (
	"embed"
	"net/http"
	"sync"
	"github.com/getlantern/systray"
	"github.com/go-toast/toast"
)

//go:embed ../Mine_01.ico
var iconData embed.FS

var (
	serverRunning bool
	serverMutex   sync.Mutex
	mStart        *systray.MenuItem
	mStop         *systray.MenuItem
	mOpen         *systray.MenuItem
	mQuit         *systray.MenuItem
	server        *http.Server
	port          string
)

func runTray(srv *http.Server, p string) {
	server = srv
	port = p
	serverRunning = true
	systray.Run(onReady, onExit)
}

func onReady() {
	// Carregar ícone
	iconBytes, _ := iconData.ReadFile("Mine_01.ico")
	systray.SetIcon(iconBytes)
	systray.SetTitle("SSM Server")
	updateTooltip()

	// Menu: Iniciar Servidor
	mStart = systray.AddMenuItem("▶️  Iniciar Servidor", "Inicia o servidor HTTP")
	mStart.Disable() // Desabilitado quando já está rodando

	// Menu: Parar Servidor
	mStop = systray.AddMenuItem("⏹️  Parar Servidor", "Para o servidor HTTP")
	mStop.Enable() // Habilitado quando está rodando

	// Separador
	systray.AddSeparator()

	// Menu: Abrir no Navegador
	mOpen = systray.AddMenuItem("🎯 Abrir no Navegador", "Abre a aplicação no navegador")

	// Separador
	systray.AddSeparator()

	// Menu: Sair
	mQuit = systray.AddMenuItem("🚪 Sair", "Encerra o servidor")

	// Handlers
	go handleMenuClicks()
}

func handleMenuClicks() {
	for {
		select {
		case <-mStart.ClickedCh:
			startServer()
		case <-mStop.ClickedCh:
			stopServer()
		case <-mOpen.ClickedCh:
			openBrowser("http://localhost:" + port)
		case <-mQuit.ClickedCh:
			stopServer()
			systray.Quit()
			return
		}
	}
}

func startServer() {
	serverMutex.Lock()
	defer serverMutex.Unlock()

	if serverRunning {
		return
	}

	// Iniciar servidor em goroutine
	go func() {
		if err := server.ListenAndServe(); err != nil && err != http.ErrServerClosed {
			showToast("Erro", "Falha ao iniciar servidor: "+err.Error(), false)
		}
	}()

	serverRunning = true
	updateMenuState()
	updateTooltip()
	showToast("Servidor Iniciado", "SSM Server rodando na porta "+port, true)
}

func stopServer() {
	serverMutex.Lock()
	defer serverMutex.Unlock()

	if !serverRunning {
		return
	}

	// Parar servidor graciosamente
	if err := server.Close(); err != nil {
		showToast("Erro", "Falha ao parar servidor: "+err.Error(), false)
		return
	}

	serverRunning = false
	updateMenuState()
	updateTooltip()
	showToast("Servidor Parado", "SSM Server foi encerrado", false)
}

func updateMenuState() {
	if serverRunning {
		mStart.Disable()
		mStop.Enable()
	} else {
		mStart.Enable()
		mStop.Disable()
	}
}

func updateTooltip() {
	status := "Parado"
	if serverRunning {
		status = "Rodando na porta " + port
	}
	systray.SetTooltip("SSM 3.0 - Servidor Frontend\n" + status)
}

func showToast(title, message string, success bool) {
	iconPath := "Mine_01.ico"
	notification := toast.Notification{
		AppID:   "SSM Server",
		Title:   title,
		Message: message,
		Icon:    iconPath,
		Actions: []toast.Action{
			{"protocol", "Abrir", "http://localhost:" + port},
		},
	}
	notification.Push()
}

func onExit() {
	// Limpeza de recursos
	if serverRunning {
		server.Close()
	}
}
```

### Modificações em `main.go`

```go
func main() {
	// Carregar configuração
	port, host, err := loadConfig()
	// ... validações ...

	// Configurar handlers
	http.HandleFunc("/", serveSPA)
	http.HandleFunc("/config.json", serveConfig)

	addr := fmt.Sprintf("%s:%s", host, port)

	// Criar servidor HTTP
	server := &http.Server{
		Addr:    addr,
		Handler: corsMiddleware(http.DefaultServeMux),
	}

	// Iniciar System Tray (bloqueia até sair)
	// System Tray deve rodar na goroutine principal
	runTray(server, port)

	// Quando System Tray sair, encerrar aplicação
	os.Exit(0)
}
```

**Importante:** System Tray deve rodar na goroutine principal, não em goroutine separada!

---

## 📦 Dependências

### Dependências Necessárias
```go
require (
	github.com/getlantern/systray v1.2.2
	github.com/go-toast/toast v0.0.0-20190211030409-01e6764cf0a4  // Para Toast Notifications
)
```

### Alternativa para Toast (Windows 10/11)
- **Opção A:** `github.com/go-toast/toast` - Biblioteca simples para Toast
- **Opção B:** Windows Runtime API diretamente (mais complexo, sem dependência)
- **Opção C:** PowerShell via `exec.Command` (simples, mas menos elegante)

**Recomendação:** Opção A (`go-toast`) - Simples e funcional

### Tamanho Adicional
- systray: ~1-2 MB
- go-toast: ~0.5 MB
- **Total:** ~1.5-2.5 MB
- **Total do executável:** ~28-30 MB (antes: 26.48 MB)

---

## 🎨 Menu de Contexto Proposto

```
┌─────────────────────────┐
│ ▶️  Iniciar Servidor    │
│ ⏹️  Parar Servidor      │
├─────────────────────────┤
│ 🎯 Abrir no Navegador   │
├─────────────────────────┤
│ 🚪 Sair                 │
└─────────────────────────┘
```

**Comportamento:**
- **Iniciar Servidor:** Habilita quando servidor está parado
- **Parar Servidor:** Habilita quando servidor está rodando
- Menu dinâmico baseado no estado do servidor

**Opções Futuras (Opcional):**
- Mostrar/Ocultar Console
- Configurações
- Sobre
- Status do Servidor (mostrar porta, status, etc.)

---

## ⚙️ Opções de Compilação

### Opção A: Com Console (Atual)
```bash
go build -ldflags="-s -w" -o SSM-Server.exe
```
- Mostra janela de console
- Útil para debug
- Logs visíveis

### Opção B: Sem Console (Opcional)
```bash
go build -ldflags="-s -w -H windowsgui" -o SSM-Server.exe
```
- Sem janela de console
- Apenas System Tray
- Mais "limpo" para usuário final

**Recomendação:** Manter console por padrão, adicionar opção para compilar sem console.

---

## ✅ Checklist de Implementação

### Preparação
- [ ] Adicionar `systray` ao `go.mod`
- [ ] Executar `go mod tidy`
- [ ] Verificar se `Mine_01.ico` está acessível

### Implementação
- [ ] Criar `tray.go`
- [ ] Implementar `runTray()`
- [ ] Implementar `onReady()`
- [ ] Implementar `onExit()`
- [ ] Integrar com `main.go`
- [ ] Adicionar menu de contexto
- [ ] Adicionar tooltip

### Funcionalidades
- [ ] Menu "Iniciar Servidor"
- [ ] Menu "Parar Servidor"
- [ ] Menu "Abrir no Navegador"
- [ ] Menu "Sair"
- [ ] Menu dinâmico (habilitar/desabilitar baseado no estado)
- [ ] Tooltip com status
- [ ] Notificações Toast quando inicia
- [ ] Notificações Toast quando para
- [ ] Sincronização de estado (mutex)

### Build e Testes
- [ ] Atualizar script de build
- [ ] Testar compilação
- [ ] Testar System Tray aparece
- [ ] Testar menu funciona
- [ ] Testar encerramento

---

## 🔄 Modificações Necessárias

### Arquivos a Modificar
1. `tools/server/go.mod` - Adicionar dependência
2. `tools/server/main.go` - Integrar System Tray
3. `tools/server/tray.go` - **NOVO** - Implementação do System Tray

### Arquivos a Criar
- `tools/server/tray.go` - Implementação do System Tray

---

## 📊 Impacto

### Tamanho do Executável
- **Antes:** 26.48 MB
- **Depois:** ~28-30 MB
- **Aumento:** ~1.5-3.5 MB

### Funcionalidades
- ✅ System Tray funcional
- ✅ Menu de contexto dinâmico
- ✅ **Start/Stop do servidor via menu**
- ✅ **Notificações Toast (Windows 10/11)**
- ✅ Tooltip informativo com status
- ✅ Integração com servidor HTTP
- ✅ Sincronização de estado (mutex)

### Experiência do Usuário
- ✅ Aplicação mais "profissional"
- ✅ Fácil acesso via System Tray
- ✅ Não precisa abrir Gerenciador de Tarefas
- ✅ Menu rápido para ações comuns

---

## 🚀 Ordem de Execução

1. **Fase 1:** Preparação (15 min)
   - Adicionar dependência
   - Verificar ícone

2. **Fase 2:** Implementação (1-2 horas)
   - Criar `tray.go`
   - Integrar com `main.go`
   - Implementar menu

3. **Fase 3:** Funcionalidades (30 min)
   - Tooltip
   - Notificações (opcional)

4. **Fase 4:** Build e Testes (30 min)
   - Atualizar build
   - Testar tudo

**Tempo total estimado:** 3-4 horas (com Start/Stop e Toast)

---

## ⚠️ Considerações Importantes

### 1. Goroutines e Sincronização
- **System Tray deve rodar na goroutine principal** (bloqueia)
- Servidor HTTP deve rodar em goroutine separada quando iniciado
- Usar `sync.Mutex` para proteger estado do servidor
- Sincronização adequada para Start/Stop
- Sincronização adequada para encerramento

### 1.1. Controle de Estado
- Variável `serverRunning` protegida por mutex
- Menu atualizado dinamicamente baseado no estado
- Tooltip atualizado quando estado muda

### 2. Encerramento
- Menu "Sair" deve encerrar servidor HTTP graciosamente
- Menu "Parar Servidor" também deve encerrar graciosamente
- Limpar recursos adequadamente
- Fechar System Tray corretamente
- Notificação Toast ao encerrar

### 2.1. Start/Stop
- Servidor inicia parado ou rodando? (Decidir comportamento inicial)
- Quando parar, servidor pode ser reiniciado via menu
- Verificar porta disponível antes de iniciar
- Tratar erros ao iniciar/parar

### 3. Ícone
- Usar `Mine_01.ico` já existente
- Embed do ícone no executável
- Verificar se carrega corretamente

### 4. Console
- Decidir se mantém console ou não
- Opção para compilar com/sem console
- Logs podem ir para arquivo se sem console
- Console pode ser opcional se System Tray estiver funcionando

### 5. Notificações Toast
- Requer Windows 10/11
- Usar biblioteca `go-toast` ou Windows API
- Notificações aparecem no canto inferior direito
- Pode incluir ações (ex: "Abrir no Navegador")
- Ícone da notificação pode usar Mine_01.ico

---

## 🔔 Notificações Toast - Detalhes

### Biblioteca Recomendada
- **`github.com/go-toast/toast`** - Biblioteca simples para Toast no Windows
- Alternativa: Windows Runtime API diretamente (mais complexo)

### Funcionalidades Toast

#### 1. Notificação ao Iniciar Servidor
```go
showToast("Servidor Iniciado", "SSM Server rodando na porta 5173", true)
```
- Título: "Servidor Iniciado"
- Mensagem: Porta e status
- Ação: Botão "Abrir" que abre navegador

#### 2. Notificação ao Parar Servidor
```go
showToast("Servidor Parado", "SSM Server foi encerrado", false)
```
- Título: "Servidor Parado"
- Mensagem: Confirmação de encerramento
- Sem ação (servidor não está mais disponível)

#### 3. Notificação de Erro
```go
showToast("Erro", "Falha ao iniciar servidor: [detalhes]", false)
```
- Título: "Erro"
- Mensagem: Detalhes do erro
- Tipo: Erro (ícone diferente)

### Exemplo de Implementação Toast

```go
import "github.com/go-toast/toast"

func showToast(title, message string, success bool) {
	iconPath := "Mine_01.ico" // Ou caminho absoluto
	
	notification := toast.Notification{
		AppID:   "SSM Server",
		Title:   title,
		Message: message,
		Icon:    iconPath,
	}
	
	// Adicionar ação se servidor está rodando
	if success {
		notification.Actions = []toast.Action{
			{"protocol", "Abrir", "http://localhost:" + port},
		}
	}
	
	// Exibir notificação
	if err := notification.Push(); err != nil {
		// Log erro silenciosamente ou tratar
	}
}
```

### Requisitos Toast
- **Windows 10/11** (Toast não funciona em Windows 7/8)
- Aplicação deve ter AppID único
- Ícone deve estar acessível (pode ser embutido)

---

## 📚 Recursos e Referências

### System Tray
- **systray GitHub:** https://github.com/getlantern/systray
- **Documentação:** https://pkg.go.dev/github.com/getlantern/systray
- **Exemplos:** https://github.com/getlantern/systray/tree/master/example

### Toast Notifications
- **go-toast GitHub:** https://github.com/go-toast/toast
- **Documentação:** https://pkg.go.dev/github.com/go-toast/toast
- **Windows Toast API:** https://docs.microsoft.com/en-us/windows/uwp/design/shell/tiles-and-notifications/

---

## 🎯 Próximos Passos

1. **Aprovar:** Este planejamento está adequado?
2. **Implementar:** Começar pela Fase 1
3. **Testar:** Validar funcionamento
4. **Distribuir:** Atualizar executável final

---

**Última atualização:** 16/12/2025

