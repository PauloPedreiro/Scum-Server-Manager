package main

import (
	"bytes"
	"fmt"
	"io"
	"log"
	"net"
	"net/http"
	"net/url"
	"os"
	"os/signal"
	"path/filepath"
	"syscall"
)

func main() {
	// Inicializar logger para arquivo (e console se disponível)
	logFile, err := initLogger()
	if err != nil {
		log.Printf("[AVISO] Não foi possível inicializar logger em arquivo: %v", err)
	} else {
		defer logFile.Close()
	}

	// Carregar configuração
	port, host, err := loadConfig()
	if err != nil {
		log.Fatalf("[ERRO] Erro ao carregar configuracao: %v", err)
	}

	// Configurar handlers
	http.HandleFunc("/api/", serveAPI) // Proxy reverso para o backend (deve vir antes de serveSPA)
	http.HandleFunc("/", serveSPA)
	http.HandleFunc("/config.json", serveConfig)

	addr := fmt.Sprintf("%s:%s", host, port)

	// Mostrar informações de inicialização (inclui local/externo)
	printStartupInfo(port, host)

	// Criar servidor HTTP (não inicia automaticamente)
	server := &http.Server{
		Addr:    addr,
		Handler: corsMiddleware(http.DefaultServeMux),
	}

	// Configurar graceful shutdown (Ctrl+C ainda funciona)
	setupGracefulShutdown(server)

	// Iniciar System Tray (bloqueia até sair)
	// O servidor será iniciado/parado via menu do System Tray
	runTray(server, port, getExternalURL())
}

// serveSPA serve a aplicação SPA (Single Page Application)
func serveSPA(w http.ResponseWriter, r *http.Request) {
	path := r.URL.Path

	// Se for /api, não deve chegar aqui (já foi tratado pelo serveAPI)
	// Mas vamos garantir que não processe
	if path == "/api" || len(path) > 4 && path[:4] == "/api" {
		http.NotFound(w, r)
		return
	}

	// Se for config.json, usar handler específico
	if path == "/config.json" {
		serveConfig(w, r)
		return
	}

	// Se tiver extensão de arquivo, tentar servir arquivo
	if hasFileExtension(path) {
		serveFile(w, r, path)
		return
	}

	// Caso contrário, servir index.html (SPA)
	serveFile(w, r, "/index.html")
}

// serveConfig serve o config.json com Content-Type correto
func serveConfig(w http.ResponseWriter, r *http.Request) {
	configData, err := getConfigJSON()
	if err != nil {
		http.Error(w, "Erro ao carregar config.json", http.StatusInternalServerError)
		return
	}

	// Headers para config.json
	w.Header().Set("Content-Type", "application/json; charset=utf-8")
	w.Header().Set("Cache-Control", "no-cache, no-store, must-revalidate")
	w.Header().Set("Pragma", "no-cache")
	w.Header().Set("Expires", "0")

	w.WriteHeader(http.StatusOK)
	w.Write(configData)
}

// serveAPI faz proxy reverso para o backend SSM
func serveAPI(w http.ResponseWriter, r *http.Request) {
	backendURL := getBackendURL()
	
	// Construir URL do backend
	targetURL, err := url.Parse(backendURL + r.URL.Path)
	if err != nil {
		log.Printf("[PROXY] Erro ao construir URL do backend: %v", err)
		http.Error(w, "Erro interno do servidor", http.StatusInternalServerError)
		return
	}

	// Adicionar query string se houver
	targetURL.RawQuery = r.URL.RawQuery

	// Ler body da requisição original
	var body io.Reader
	var bodyLength int64
	if r.Body != nil {
		bodyBytes, err := io.ReadAll(r.Body)
		if err != nil {
			log.Printf("[PROXY] Erro ao ler body: %v", err)
			http.Error(w, "Erro ao ler requisição", http.StatusBadRequest)
			return
		}
		bodyLength = int64(len(bodyBytes))
		body = bytes.NewReader(bodyBytes)
	}

	// Criar nova requisição para o backend
	req, err := http.NewRequest(r.Method, targetURL.String(), body)
	if err != nil {
		log.Printf("[PROXY] Erro ao criar requisição: %v", err)
		http.Error(w, "Erro ao criar requisição", http.StatusInternalServerError)
		return
	}

	// Copiar headers da requisição original (exceto alguns que são gerenciados pelo cliente HTTP)
	for key, values := range r.Header {
		// Pular headers que devem ser gerenciados pelo cliente HTTP ou ajustados manualmente
		if key == "Connection" || key == "Keep-Alive" || key == "Proxy-Authenticate" ||
			key == "Proxy-Authorization" || key == "Te" || key == "Trailers" ||
			key == "Transfer-Encoding" || key == "Upgrade" || key == "Host" {
			continue
		}
		for _, value := range values {
			req.Header.Add(key, value)
		}
	}
	
	// Definir Host corretamente para o backend (não usar o Host da requisição original)
	req.Host = targetURL.Host
	
	// Definir Content-Length se houver body (importante para requisições POST/PUT)
	if bodyLength > 0 {
		req.ContentLength = bodyLength
	}

	// Fazer requisição para o backend
	client := &http.Client{
		Timeout: 0, // Sem timeout (deixa o backend gerenciar)
	}
	
	resp, err := client.Do(req)
	if err != nil {
		log.Printf("[PROXY] Erro ao conectar ao backend (%s): %v", backendURL, err)
		http.Error(w, fmt.Sprintf("Erro ao conectar ao backend: %v", err), http.StatusBadGateway)
		return
	}
	defer resp.Body.Close()
	
	// Log de debug em caso de erro
	if resp.StatusCode >= 400 {
		// Ler corpo da resposta de erro para log (sem consumir completamente)
		bodyBytes, _ := io.ReadAll(resp.Body)
		resp.Body = io.NopCloser(bytes.NewReader(bodyBytes)) // Restaurar body para copiar depois
		
		log.Printf("[PROXY] Erro %d do backend - URL: %s, Response: %s", resp.StatusCode, targetURL.String(), string(bodyBytes))
	}

	// Copiar headers da resposta
	for key, values := range resp.Header {
		// Não copiar Content-Length, será recalculado pelo Go
		if key == "Content-Length" {
			continue
		}
		for _, value := range values {
			w.Header().Add(key, value)
		}
	}

	// Copiar status code
	w.WriteHeader(resp.StatusCode)

	// Copiar corpo da resposta
	_, err = io.Copy(w, resp.Body)
	if err != nil {
		log.Printf("[PROXY] Erro ao copiar resposta: %v", err)
	}
}

// checkPortAvailable verifica se a porta está disponível
func checkPortAvailable(port string) error {
	addr := fmt.Sprintf(":%s", port)
	listener, err := net.Listen("tcp", addr)
	if err != nil {
		return fmt.Errorf("porta %s ja esta em uso. Feche o processo que esta usando esta porta ou altere a porta no config.json", port)
	}
	listener.Close()
	return nil
}

// printStartupInfo imprime informações de inicialização
func printStartupInfo(port, host string) {
	fmt.Println("╔════════════════════════════════════════╗")
	fmt.Println("║   SSM 3.0 - Servidor Frontend        ║")
	fmt.Println("╚════════════════════════════════════════╝")
	fmt.Printf("[INFO] Servidor iniciado em:\n")
	fmt.Printf("   Local:   http://localhost:%s\n", port)
	if host == "0.0.0.0" {
		fmt.Printf("   Rede:    http://[SEU_IP]:%s\n", port)
	}
	fmt.Printf("[INFO] Proxy reverso: /api/* -> %s\n", getBackendURL())
	fmt.Printf("[INFO] Arquivos embutidos no executavel\n")
	fmt.Printf("[INFO] Pressione Ctrl+C para parar\n")
	fmt.Println()
}

// corsMiddleware adiciona headers CORS
func corsMiddleware(next http.Handler) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		// Headers CORS
		w.Header().Set("Access-Control-Allow-Origin", "*")
		w.Header().Set("Access-Control-Allow-Methods", "GET, POST, PUT, DELETE, OPTIONS")
		w.Header().Set("Access-Control-Allow-Headers", "Content-Type, Authorization")

		// Responder a requisições OPTIONS
		if r.Method == "OPTIONS" {
			w.WriteHeader(http.StatusOK)
			return
		}

		// Continuar com o próximo handler
		next.ServeHTTP(w, r)
	})
}

// setupGracefulShutdown configura o graceful shutdown (Ctrl+C)
func setupGracefulShutdown(server *http.Server) {
	// Canal para receber sinais do sistema
	sigChan := make(chan os.Signal, 1)
	signal.Notify(sigChan, os.Interrupt, syscall.SIGTERM)

	// Goroutine para lidar com shutdown
	go func() {
		<-sigChan
		fmt.Println("\n[INFO] Encerrando servidor...")
		
		// Parar servidor se estiver rodando
		// Nota: serverMutex e serverRunning estão em tray.go
		// Por enquanto, apenas fechar servidor diretamente
		if err := server.Close(); err != nil && err != http.ErrServerClosed {
			log.Printf("[ERRO] Erro ao encerrar servidor: %v", err)
		}
		
		fmt.Println("[INFO] Servidor encerrado")
		os.Exit(0)
	}()
}

// initLogger configura o logger para gravar em arquivo (e stdout, se houver)
func initLogger() (*os.File, error) {
	exePath, err := os.Executable()
	if err != nil {
		return nil, err
	}
	exeDir := filepath.Dir(exePath)
	logPath := filepath.Join(exeDir, "ssm-server.log")

	f, err := os.OpenFile(logPath, os.O_CREATE|os.O_WRONLY|os.O_APPEND, 0644)
	if err != nil {
		return nil, err
	}

	// Tentar também manter saída no stdout para builds com console
	log.SetOutput(io.MultiWriter(f, os.Stdout))
	log.SetFlags(log.LstdFlags | log.Lshortfile)

	return f, nil
}

