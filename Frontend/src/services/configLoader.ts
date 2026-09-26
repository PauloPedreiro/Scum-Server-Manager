/**
 * Carrega config.json em runtime (não em build time)
 * Isso permite editar o config.json na pasta dist/ sem precisar fazer rebuild
 */

interface ConfigData {
  backend?: {
    host?: string;
    port?: number;
    protocol?: string;
    basePath?: string;
    timeout?: number;
  };
  frontend?: {
    port?: number;
    host?: string;
    urls?: {
      external?: string;
      local?: string;
    };
  };
}

let cachedConfig: ConfigData | null = null;
let configLoadPromise: Promise<ConfigData> | null = null;
let configLoaded = false;

// Carregar config imediatamente quando o módulo é importado
const defaultConfig: ConfigData = {
  backend: {
    host: 'localhost',
    port: 3000,
    protocol: 'http',
    basePath: '/api',
    timeout: 60000,
  },
};

/**
 * Carrega config.json da pasta dist/ em runtime
 */
async function loadConfig(): Promise<ConfigData> {
  // Se já está carregando, retorna a mesma promise
  if (configLoadPromise && !configLoaded) {
    return configLoadPromise;
  }

  // Se já está em cache, retorna imediatamente
  if (cachedConfig) {
    return cachedConfig;
  }

  // Carrega o config.json
  configLoadPromise = (async () => {
    try {
      const response = await fetch('/config.json?t=' + Date.now(), {
        method: 'GET',
        headers: {
          'Accept': 'application/json',
        },
        cache: 'no-store',
      });
      
      if (!response.ok) {
        throw new Error(`Failed to load config.json: ${response.status} ${response.statusText}`);
      }
      
      // Verificar se a resposta é realmente JSON (não HTML)
      const contentType = response.headers.get('content-type');
      if (!contentType || !contentType.includes('application/json')) {
        const text = await response.text();
        // Se começar com <, é HTML (provavelmente página de erro)
        if (text.trim().startsWith('<')) {
          throw new Error(`config.json retornou HTML ao invés de JSON. Verifique se o arquivo existe e está sendo servido corretamente.`);
        }
        throw new Error(`Content-Type inválido: ${contentType}. Esperado application/json.`);
      }
      
      const config = await response.json();
      
      // Validar estrutura básica do config
      if (!config || typeof config !== 'object') {
        throw new Error('config.json não contém um objeto JSON válido');
      }
      
      cachedConfig = config;
      configLoaded = true;
      // Log apenas em desenvolvimento, sem expor informações sensíveis
      if (import.meta.env.DEV) {
        console.log('[Config] ✅ Carregado em runtime');
      }
      return config;
    } catch (error) {
      // Log de erro sanitizado
      if (import.meta.env.DEV) {
        console.error('[Config] ❌ Erro ao carregar config.json, usando padrões:', error);
      } else {
        console.error('[Config] ❌ Erro ao carregar configuração');
      }
      // Retorna configuração padrão se não conseguir carregar
      cachedConfig = defaultConfig;
      configLoaded = true;
      return defaultConfig;
    }
  })();

  return configLoadPromise;
}

// Iniciar carregamento imediatamente
loadConfig();

/**
 * Obtém a URL base da API
 * Quando o config usa "localhost", usa URL relativa para permitir proxy reverso
 * Isso permite que o servidor frontend faça proxy para o backend na mesma máquina
 */
export async function getApiBaseURL(): Promise<string> {
  const envURL = import.meta.env.VITE_API_BASE_URL;
  if (envURL) return envURL;

  const config = await loadConfig();

  if (config?.backend) {
    const { basePath = '/api' } = config.backend;

    // Por padrão, o frontend deve usar URL relativa para evitar expor host/IP do backend no browser.
    // Para cenários onde você realmente precisa de URL absoluta, use VITE_API_BASE_URL.
    return basePath;
  }

  return '/api';
}

/**
 * Obtém timeout do backend
 */
export async function getBackendTimeout(): Promise<number> {
  const config = await loadConfig();
  return config?.backend?.timeout ?? 60000;
}

/**
 * Obtém configuração completa
 */
export async function getConfig(): Promise<ConfigData> {
  return await loadConfig();
}

/**
 * Limpa o cache (útil para recarregar após editar config.json)
 */
export function clearConfigCache(): void {
  cachedConfig = null;
  configLoadPromise = null;
}

