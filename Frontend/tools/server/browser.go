package main

import (
	"os/exec"
	"runtime"
	"time"
)

// openBrowser abre o navegador padrão na URL especificada
func openBrowser(url string) {
	// Aguardar servidor iniciar (1-2 segundos)
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
		// Sistema operacional não suportado
		return
	}

	// Tentar abrir navegador (ignorar erros se não conseguir)
	if err := cmd.Run(); err != nil {
		// Ignorar erros silenciosamente (navegador pode não estar disponível)
		// Log pode ser adicionado aqui se necessário
	}
}

