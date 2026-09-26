package main

import (
	"embed"
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"
	"strings"
	"strconv"
)

//go:embed dist/config.json
var configJSON embed.FS

// PortString aceita tanto número quanto string no JSON e converte para string
type PortString string

// UnmarshalJSON permite que PortString aceite tanto int quanto string
func (p *PortString) UnmarshalJSON(data []byte) error {
	// Tentar como número primeiro
	var num int
	if err := json.Unmarshal(data, &num); err == nil {
		*p = PortString(strconv.Itoa(num))
		return nil
	}
	// Se não for número, tentar como string
	var str string
	if err := json.Unmarshal(data, &str); err != nil {
		return err
	}
	*p = PortString(str)
	return nil
}

// String retorna o valor como string
func (p PortString) String() string {
	return string(p)
}

// Config representa a estrutura do config.json
type Config struct {
	Backend struct {
		Port PortString `json:"port"`
		Host string     `json:"host"`
	} `json:"backend"`
	Frontend struct {
		Port PortString `json:"port"`
		Host string     `json:"host"`
		URLs struct {
			External string `json:"external"`
			Local    string `json:"local"`
		} `json:"urls"`
	} `json:"frontend"`
}

var (
	currentPort        = ""
	currentHost        = ""
	currentLocalURL    = ""
	currentExternalURL = ""
	configSource       = "embedded"
	backendPort        = "3000" // Porta padrão do backend
	backendHost        = "localhost"
)

// loadConfig carrega a configuração do config.json embutido
// Retorna porta, host e erro
func loadConfig() (string, string, error) {
	// Tentar ler config.json externo ao lado do executável (obrigatório)
	data, err := readConfigFromDisk()
	if err != nil || data == nil {
		return "", "", fmt.Errorf("config.json não encontrado ao lado do executável")
	}
	configSource = "external"

	var config Config
	if err := json.Unmarshal(data, &config); err != nil {
		return "", "", fmt.Errorf("erro ao parsear config.json: %w", err)
	}

	port := config.Frontend.Port.String()
	host := config.Frontend.Host

	// Ler configuração do backend (para proxy reverso)
	if config.Backend.Port.String() != "" {
		backendPort = config.Backend.Port.String()
	}
	if config.Backend.Host != "" {
		backendHost = config.Backend.Host
	}

	// Override via variáveis de ambiente (opcional)
	if envPort := os.Getenv("SSM_PORT"); envPort != "" {
		port = envPort
	}
	if envHost := os.Getenv("SSM_HOST"); envHost != "" {
		host = envHost
	}

	// Validar host/porta obrigatórios
	if port == "" || host == "" {
		return "", "", fmt.Errorf("config inválida: host/port obrigatórios ausentes")
	}

	// Guardar para uso em outras partes (tray)
	currentPort = port
	currentHost = host

	// Definir URLs de conveniência (local e externa)
	currentLocalURL, currentExternalURL = computeFrontendURLs(port, host, config.Frontend.URLs.Local, config.Frontend.URLs.External)

	// Log do que foi carregado
	fmt.Printf("[CONFIG] fonte=%s host=%s port=%s\n", configSource, host, port)

	return port, host, nil
}

// getConfigJSON retorna o conteúdo do config.json como string
func getConfigJSON() ([]byte, error) {
	// Retornar sempre o arquivo do disco (obrigatório)
	data, err := readConfigFromDisk()
	if err != nil {
		return nil, fmt.Errorf("erro ao ler config.json externo: %w", err)
	}
	return data, nil
}

// computeFrontendURLs resolve URLs local/externa a partir das configs
func computeFrontendURLs(port, host, localCfg, externalCfg string) (string, string) {
	localURL := localCfg
	externalURL := externalCfg

	if localURL == "" {
		localURL = "http://localhost:" + port
	}

	if externalURL == "" {
		externalURL = "http://" + host + ":" + port
	}

	return localURL, externalURL
}

// readConfigFromDisk tenta ler config.json do mesmo diretório do executável
func readConfigFromDisk() ([]byte, error) {
	exePath, err := os.Executable()
	if err != nil {
		return nil, err
	}
	exeDir := filepath.Dir(exePath)
	cfgPath := filepath.Join(exeDir, "config.json")

	data, err := os.ReadFile(cfgPath)
	if err != nil {
		// Se não existir ou não puder ler, retornar nil sem erro fatal
		return nil, err
	}
	return stripUTF8BOM(data), nil
}

// stripUTF8BOM remove BOM UTF-8 (EF BB BF) que pode quebrar o json.Unmarshal no Windows.
func stripUTF8BOM(data []byte) []byte {
	if len(data) >= 3 && data[0] == 0xEF && data[1] == 0xBB && data[2] == 0xBF {
		return data[3:]
	}
	return data
}

// getLocalURL retorna a URL local configurada (ou default)
func getLocalURL() string {
	if currentLocalURL != "" {
		return currentLocalURL
	}
	return "http://localhost:" + currentPort
}

// getExternalURL retorna a URL externa configurada (ou fallback host:port)
func getExternalURL() string {
	if currentExternalURL != "" {
		return currentExternalURL
	}
	return "http://" + currentHost + ":" + currentPort
}

// getConfigSource retorna se a config veio do disco (external) ou embutida
func getConfigSource() string {
	return configSource
}

// getBackendURL retorna a URL do backend para proxy reverso
func getBackendURL() string {
	host := backendHost
	// Evitar resolver localhost para IPv6 (::1) em máquinas onde o backend só escuta em IPv4.
	if strings.EqualFold(host, "localhost") {
		host = "127.0.0.1"
	}
	return fmt.Sprintf("http://%s:%s", host, backendPort)
}
