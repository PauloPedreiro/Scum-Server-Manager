package main

import (
	"embed"
	"log"
	"net/http"
	"sync"
	"time"

	"github.com/getlantern/systray"
	"github.com/go-toast/toast"
)

//go:embed Ativado.ico
//go:embed Parado.ico
//go:embed Mine_01.ico
var iconData embed.FS

var (
	serverRunning bool
	serverMutex   sync.Mutex
	mStart        *systray.MenuItem
	mStop         *systray.MenuItem
	mOpenExternal *systray.MenuItem
	mQuit         *systray.MenuItem
	server        *http.Server
	port          string
	externalURL   string
)

// runTray inicia o System Tray (deve rodar na goroutine principal)
func runTray(srv *http.Server, p string, external string) {
	server = srv
	port = p
	externalURL = external
	serverRunning = false // Começa parado, usuário inicia via menu

	systray.Run(onReady, onExit)
}

func onReady() {
	setTrayIcon(false)

	systray.SetTitle("SSM Server")
	updateTooltip()

	// Menu: Start Server
	mStart = systray.AddMenuItem("▶️  Start Server", "Start HTTP server")
	mStart.Enable() // Enabled when server is stopped

	// Menu: Stop Server
	mStop = systray.AddMenuItem("⏹️  Stop Server", "Stop HTTP server")
	mStop.Disable() // Disabled when server is stopped

	// Separador
	systray.AddSeparator()

	// Menu: Open in Browser
	mOpenExternal = systray.AddMenuItem("🌐 Open (Externo)", "Open the app using external URL")
	mOpenExternal.Disable()

	// Separador
	systray.AddSeparator()

	// Menu: Exit
	mQuit = systray.AddMenuItem("🚪 Exit", "Quit the server")

	// Handlers de menu
	go handleMenuClicks()

	// Toast informing tray is running
	showToast("SSM Server", "Running in the System Tray.", false)
}

func setTrayIcon(running bool) {
	iconFile := "Parado.ico"
	if running {
		iconFile = "Ativado.ico"
	}
	iconBytes, err := iconData.ReadFile(iconFile)
	if err == nil && iconBytes != nil {
		systray.SetIcon(iconBytes)
		return
	}

	fallbackBytes, fallbackErr := iconData.ReadFile("Mine_01.ico")
	if fallbackErr == nil && fallbackBytes != nil {
		systray.SetIcon(fallbackBytes)
	}
}

func handleMenuClicks() {
	for {
		select {
		case <-mStart.ClickedCh:
			startServer()
		case <-mStop.ClickedCh:
			stopServer()
		case <-mOpenExternal.ClickedCh:
			openBrowser(externalURL)
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

	log.Printf("[SERVER] Start requested (port=%s, host=%s)", port, currentHost)

	// Verificar se porta está disponível
	if err := checkPortAvailable(port); err != nil {
		showToast("Error", "Port "+port+" is already in use", false)
		return
	}

	// Iniciar servidor em goroutine
	go func() {
		err := server.ListenAndServe()
		if err != nil && err != http.ErrServerClosed {
			log.Printf("[SERVER] ListenAndServe error: %v", err)
			showToast("Error", "Failed to start server: "+err.Error(), false)
			serverMutex.Lock()
			serverRunning = false
			updateMenuState()
			updateTooltip()
			setTrayIcon(false)
			serverMutex.Unlock()
			return
		}
		log.Printf("[SERVER] ListenAndServe stopped: %v", err)
	}()

	// Aguardar um pouco para garantir que servidor iniciou
	time.Sleep(500 * time.Millisecond)

	serverRunning = true
	updateMenuState()
	updateTooltip()
	setTrayIcon(true)
	log.Printf("[SERVER] Started (port=%s)", port)
	showToast("Server Started", "SSM Server running on port "+port, true)
}

func stopServer() {
	serverMutex.Lock()
	defer serverMutex.Unlock()

	if !serverRunning {
		return
	}

	log.Printf("[SERVER] Stop requested")

	// Parar servidor graciosamente
	if err := server.Close(); err != nil {
		showToast("Error", "Failed to stop server: "+err.Error(), false)
		return
	}

	serverRunning = false
	updateMenuState()
	updateTooltip()
	setTrayIcon(false)
	log.Printf("[SERVER] Stopped")
	showToast("Server Stopped", "SSM Server has been stopped.", false)
}

func updateMenuState() {
	if serverRunning {
		mStart.Disable()
		mStop.Enable()
		mOpenExternal.Enable()
	} else {
		mStart.Enable()
		mStop.Disable()
		mOpenExternal.Disable()
	}
}

func updateTooltip() {
	status := "Stopped"
	if serverRunning {
		status = "Running on port " + port + " (" + configSource + ")"
	}
	systray.SetTooltip("SSM 3.0 - Frontend Server\n" + status)
}

func showToast(title, message string, success bool) {
	// go-toast precisa de caminho de arquivo, não bytes
	notification := toast.Notification{
		AppID:   "SSM Server",
		Title:   title,
		Message: message,
	}

	// Adicionar ação se servidor está rodando
	if success {
		notification.Actions = []toast.Action{
			{
				Type:      "protocol",
				Label:     "Open",
				Arguments: externalURL,
			},
		}
	}

	// Exibir notificação
	if err := notification.Push(); err != nil {
		// Ignorar erros silenciosamente (Toast pode não estar disponível em alguns sistemas)
	}
}

func onExit() {
	// Limpeza de recursos
	serverMutex.Lock()
	defer serverMutex.Unlock()

	if serverRunning {
		server.Close()
	}
}
