package main

import (
	"embed"
	"io/fs"
	"net/http"
	"path/filepath"
	"strings"
)

//go:embed dist/** dist/config.json
var distFiles embed.FS

// hasFileExtension verifica se o path tem uma extensão de arquivo
func hasFileExtension(path string) bool {
	ext := filepath.Ext(path)
	return ext != "" && ext != "/" && !strings.HasSuffix(path, "/")
}

// getContentType retorna o Content-Type apropriado baseado na extensão do arquivo
func getContentType(path string) string {
	ext := strings.ToLower(filepath.Ext(path))
	switch ext {
	case ".html":
		return "text/html; charset=utf-8"
	case ".js":
		return "application/javascript; charset=utf-8"
	case ".css":
		return "text/css; charset=utf-8"
	case ".json":
		return "application/json; charset=utf-8"
	case ".png":
		return "image/png"
	case ".jpg", ".jpeg":
		return "image/jpeg"
	case ".gif":
		return "image/gif"
	case ".webp":
		return "image/webp"
	case ".svg":
		return "image/svg+xml"
	case ".ico":
		return "image/x-icon"
	case ".woff", ".woff2":
		return "font/woff2"
	case ".ttf":
		return "font/ttf"
	case ".otf":
		return "font/otf"
	default:
		return "application/octet-stream"
	}
}

// serveFile serve um arquivo do filesystem embutido
func serveFile(w http.ResponseWriter, r *http.Request, path string) {
	// Normalizar path
	path = strings.TrimPrefix(path, "/")
	if path == "" {
		path = "index.html"
	}

	// Tentar ler arquivo
	data, err := fs.ReadFile(distFiles, "dist/"+path)
	if err != nil {
		// Se não encontrou, servir index.html (SPA)
		path = "index.html"
		data, err = fs.ReadFile(distFiles, "dist/"+path)
		if err != nil {
			http.NotFound(w, r)
			return
		}
	}

	// Detectar Content-Type
	contentType := getContentType(path)
	w.Header().Set("Content-Type", contentType)

	// Headers para cache (opcional, pode ser ajustado)
	if strings.HasPrefix(path, "assets/") {
		// Assets podem ser cacheados
		w.Header().Set("Cache-Control", "public, max-age=31536000")
	} else {
		// HTML e outros arquivos não devem ser cacheados
		w.Header().Set("Cache-Control", "no-cache, no-store, must-revalidate")
		w.Header().Set("Pragma", "no-cache")
		w.Header().Set("Expires", "0")
	}

	// Servir conteúdo
	w.Write(data)
}
