/**
 * Sistema de logging seguro
 * Em produção, remove logs sensíveis e reduz verbosidade
 */

const isDevelopment = import.meta.env.DEV;
const isProduction = import.meta.env.PROD;

/**
 * Logger seguro que só mostra informações em desenvolvimento
 */
export const logger = {
  /**
   * Log de informações gerais (só em dev)
   */
  info: (...args: any[]) => {
    if (isDevelopment) {
      console.log(...args);
    }
  },

  /**
   * Log de sucesso (só em dev)
   */
  success: (...args: any[]) => {
    if (isDevelopment) {
      console.log('✅', ...args);
    }
  },

  /**
   * Log de avisos (sempre visível, mas sem dados sensíveis)
   */
  warn: (...args: any[]) => {
    // Em produção, remove dados sensíveis dos logs
    if (isProduction) {
      const sanitized = args.map(arg => {
        if (typeof arg === 'string' && (arg.includes('http://') || arg.includes('https://'))) {
          return '[URL oculta]';
        }
        if (typeof arg === 'object' && arg !== null) {
          return '[Objeto]';
        }
        return arg;
      });
      console.warn(...sanitized);
    } else {
      console.warn(...args);
    }
  },

  /**
   * Log de erros (sempre visível, mas sanitizado em produção)
   */
  error: (...args: any[]) => {
    // Em produção, remove dados sensíveis dos logs
    if (isProduction) {
      const sanitized = args.map(arg => {
        if (typeof arg === 'string') {
          // Remove URLs
          let sanitized = arg.replace(/https?:\/\/[^\s]+/g, '[URL oculta]');
          // Remove IPs
          sanitized = sanitized.replace(/\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b/g, '[IP oculto]');
          return sanitized;
        }
        if (typeof arg === 'object' && arg !== null) {
          // Não loga objetos completos em produção
          return '[Erro]';
        }
        return arg;
      });
      console.error(...sanitized);
    } else {
      console.error(...args);
    }
  },

  /**
   * Log de debug (só em dev)
   */
  debug: (...args: any[]) => {
    if (isDevelopment) {
      console.debug(...args);
    }
  },
};

/**
 * Função helper para sanitizar dados sensíveis antes de logar
 */
export function sanitizeForLog(data: any): any {
  if (typeof data === 'string') {
    // Remove URLs
    let sanitized = data.replace(/https?:\/\/[^\s]+/g, '[URL]');
    // Remove IPs
    sanitized = sanitized.replace(/\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b/g, '[IP]');
    return sanitized;
  }
  
  if (typeof data === 'object' && data !== null) {
    if (Array.isArray(data)) {
      return data.map(sanitizeForLog);
    }
    
    const sanitized: any = {};
    for (const [key, value] of Object.entries(data)) {
      // Não loga campos sensíveis
      if (['password', 'token', 'secret', 'key', 'apiKey', 'auth'].includes(key.toLowerCase())) {
        sanitized[key] = '[Oculto]';
      } else if (typeof value === 'string' && (value.includes('http://') || value.includes('https://'))) {
        sanitized[key] = '[URL]';
      } else {
        sanitized[key] = sanitizeForLog(value);
      }
    }
    return sanitized;
  }
  
  return data;
}

