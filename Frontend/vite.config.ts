import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react-swc';
import tsconfigPaths from 'vite-tsconfig-paths';
import fs from 'fs';
import os from 'os';
import path from 'path';

// Load runtime dev settings from src/config.json
// Falls back to sensible defaults if file isn't present or fields are missing
let devHost: string = '0.0.0.0';
let devPort: number = 5173;
let hmrHost: string | undefined;

// Função para obter o IP local da máquina
function getLocalIP(): string {
  const interfaces = os.networkInterfaces();
  for (const name of Object.keys(interfaces)) {
    const iface = interfaces[name];
    if (iface) {
      for (const addr of iface) {
        // Ignora endereços internos e não IPv4
        if (addr.family === 'IPv4' && !addr.internal) {
          return addr.address;
        }
      }
    }
  }
  return 'localhost';
}

try {
  const raw = fs.readFileSync('src/config.json', 'utf-8');
  const cfg = JSON.parse(raw);
  if (typeof cfg?.frontend?.host === 'string' && cfg.frontend.host.trim() !== '') {
    // Importante: em Windows/redes instáveis, bindar o Vite em um IP específico pode causar
    // ERR_CONNECTION_REFUSED quando a interface muda ou o IP troca.
    // Mantemos o bind em 0.0.0.0 e usamos o host configurado apenas para HMR.
    hmrHost = cfg.frontend.host;
  }
  if (cfg?.frontend?.port !== undefined && cfg.frontend.port !== null) {
    const parsed = Number(cfg.frontend.port);
    if (!Number.isNaN(parsed) && parsed > 0) {
      devPort = parsed;
    }
  }
  
  // Para acesso externo: usar IP local para HMR quando não tiver vindo do config
  if (!hmrHost) {
    hmrHost = getLocalIP();
  }
} catch (_) {
  // Ignore errors; defaults above will be used
  hmrHost = getLocalIP();
}

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [
    react(),
    tsconfigPaths(),
    {
      name: 'copy-files',
      writeBundle() {
        // Copiar config.json para dist após o build
        // Priorizar public/config.json se existir, senão usar src/config.json
        const publicConfigPath = path.resolve(__dirname, 'public/config.json');
        const srcConfigPath = path.resolve(__dirname, 'src/config.json');
        const distConfigPath = path.resolve(__dirname, 'dist/config.json');
        
        let configPath: string | null = null;
        if (fs.existsSync(publicConfigPath)) {
          configPath = publicConfigPath;
        } else if (fs.existsSync(srcConfigPath)) {
          configPath = srcConfigPath;
        }
        
        if (configPath) {
          try {
            fs.copyFileSync(configPath, distConfigPath);
            console.log('✓ config.json copiado para dist/');
          } catch (error) {
            console.error('Erro ao copiar config.json:', error);
          }
        }

        // Copiar README para dist (se existir)
        const readmePath = path.resolve(__dirname, 'dist-README.md');
        const distReadmePath = path.resolve(__dirname, 'dist/README.md');
        
        if (fs.existsSync(readmePath)) {
          try {
            fs.copyFileSync(readmePath, distReadmePath);
            console.log('✓ README.md copiado para dist/');
          } catch (error) {
            console.error('Erro ao copiar README.md:', error);
          }
        }

        // Copiar script de inicialização para dist
        const startScriptPath = path.resolve(__dirname, 'dist-start.bat');
        const distStartScriptPath = path.resolve(__dirname, 'dist/start.bat');
        
        if (fs.existsSync(startScriptPath)) {
          try {
            fs.copyFileSync(startScriptPath, distStartScriptPath);
            console.log('✓ start.bat copiado para dist/');
          } catch (error) {
            console.error('Erro ao copiar start.bat:', error);
          }
        }

        // Copiar serve.json para dist (configuração do serve)
        const serveConfigPath = path.resolve(__dirname, 'serve.json');
        const distServeConfigPath = path.resolve(__dirname, 'dist/serve.json');
        
        if (fs.existsSync(serveConfigPath)) {
          try {
            fs.copyFileSync(serveConfigPath, distServeConfigPath);
            console.log('✓ serve.json copiado para dist/');
          } catch (error) {
            console.error('Erro ao copiar serve.json:', error);
          }
        }

        // Copiar ícone PWA para a raiz do dist (usado pelo manifest.webmanifest)
        const pwaIconPath = path.resolve(__dirname, 'src/assets/logo/Ativado.webp');
        const distPwaIconPath = path.resolve(__dirname, 'dist/Ativado.webp');

        if (fs.existsSync(pwaIconPath)) {
          try {
            fs.copyFileSync(pwaIconPath, distPwaIconPath);
            console.log('✓ Ativado.webp copiado para dist/');
          } catch (error) {
            console.error('Erro ao copiar Ativado.webp:', error);
          }
        }
      },
    },
  ],
  server: {
    host: devHost,
    port: devPort,
    strictPort: true,
    open: true,
    cors: true,
    // HMR configurado para usar IP local, permitindo acesso externo
    hmr: {
      host: hmrHost || 'localhost',
      port: devPort,
      protocol: 'ws',
    },
    // Proxy reverso para o backend SSM (mesma máquina)
    proxy: {
      '/api': {
        target: 'http://localhost:3000',
        changeOrigin: true,
        secure: false,
        rewrite: (path) => path, // Manter o path original (já inclui /api)
        configure: (proxy, _options) => {
          proxy.on('proxyReq', (proxyReq, req, _res) => {
            // Log de requisições do proxy
            const targetURL = `${_options.target}${proxyReq.path}`;
            console.log(`[Vite Proxy] ${req.method} ${req.url} -> ${targetURL}`);
            
            // Log de headers importantes (apenas em dev, para debug)
            if (req.method === 'POST' || req.method === 'PUT' || req.method === 'PATCH') {
              const contentType = proxyReq.getHeader('content-type');
              console.log(`[Vite Proxy] Content-Type: ${contentType || 'not set'}`);
              
              // Garantir que Content-Type está presente
              if (!contentType) {
                proxyReq.setHeader('content-type', 'application/json');
                console.log('[Vite Proxy] Content-Type definido como application/json');
              }
            }
          });
          proxy.on('proxyRes', (proxyRes, req, _res) => {
            // Log de respostas do proxy (especialmente erros)
            const statusCode = proxyRes.statusCode;
            if (typeof statusCode === 'number' && statusCode >= 400) {
              console.log(`[Vite Proxy] ⚠️ Response ${statusCode} for ${req.method} ${req.url}`);
              // Tentar ler o body da resposta de erro (se disponível)
              const chunks: Buffer[] = [];
              proxyRes.on('data', (chunk) => chunks.push(chunk));
              proxyRes.on('end', () => {
                const body = Buffer.concat(chunks).toString();
                if (body) {
                  console.log(`[Vite Proxy] Error body: ${body.substring(0, 200)}`);
                }
              });
            }
          });
          proxy.on('error', (err, req, _res) => {
            console.error('[Vite Proxy Error]', err);
            console.error('[Vite Proxy Error] Request:', req.method, req.url);
          });
        },
      },
    },
  },
  build: {
    // Garantir que todos os assets sejam copiados
    assetsDir: 'assets',
    // Copiar arquivos públicos (se houver pasta public)
    copyPublicDir: true,
    // Desabilitar source maps em produção (proteção adicional)
    sourcemap: false,
    // Minificação mais agressiva
    minify: 'terser',
    terserOptions: {
      compress: {
        drop_console: true, // Remove console.log em produção
        drop_debugger: true,
        pure_funcs: ['console.log', 'console.info', 'console.debug'], // Remove funções específicas
      },
      format: {
        comments: false, // Remove todos os comentários
      },
      mangle: {
        // Ofuscação de nomes de variáveis e funções
        toplevel: true,
        properties: {
          regex: /^_/ // Ofusca propriedades que começam com _
        }
      },
    },
    // Rollup options para garantir que todos os arquivos sejam incluídos
    rollupOptions: {
      output: {
        // Manter estrutura de diretórios para assets
        assetFileNames: 'assets/[name]-[hash][extname]',
        chunkFileNames: 'assets/[name]-[hash].js',
        entryFileNames: 'assets/[name]-[hash].js',
      },
    },
    // Aumentar limite de aviso de chunk size
    chunkSizeWarningLimit: 1000,
  },
  // Configurar pasta public (se não existir, será criada automaticamente)
  publicDir: 'public',
});


