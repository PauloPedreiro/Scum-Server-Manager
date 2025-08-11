import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import fs from 'fs'
import path from 'path'

// Função para ler a configuração
function getConfig() {
  try {
    const configPath = path.resolve(__dirname, 'public/config.json')
    const configContent = fs.readFileSync(configPath, 'utf-8')
    return JSON.parse(configContent)
  } catch (error) {
    console.warn('Erro ao ler config.json, usando configuração padrão:', error)
    return {
      backend: {
        host: '127.0.0.1',
        port: 3000,
        protocol: 'http'
      },
      frontend: {
        port: 5173,
        host: '0.0.0.0'
      }
    }
  }
}

const config = getConfig()
const backendUrl = `${config.backend.protocol}://${config.backend.host}:${config.backend.port}`

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    port: config.frontend.port,
    host: config.frontend.host, // Permite acesso externo
    open: false, // Não abre o navegador automaticamente
    cors: true, // Habilita CORS
    proxy: {
      '/api': {
        target: backendUrl,
        changeOrigin: true,
        secure: false,
        rewrite: (path) => path.replace(/^\/api/, '/api'),
      }
    }
  }
}) 