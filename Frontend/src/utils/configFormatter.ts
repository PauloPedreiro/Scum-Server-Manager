/**
 * Utilitários para formatar e trabalhar com configurações do config.json
 */

/**
 * Flatten um objeto aninhado em chaves planas
 * Exemplo: { paths: { application: { data_directory: "data" } } }
 * Resultado: { "paths.application.data_directory": "data" }
 */
export function flattenConfig(obj: Record<string, any>, prefix = ''): Record<string, any> {
  const flattened: Record<string, any> = {};
  
  for (const key in obj) {
    if (obj.hasOwnProperty(key)) {
      const newKey = prefix ? `${prefix}.${key}` : key;
      const value = obj[key];
      
      if (value !== null && typeof value === 'object' && !Array.isArray(value)) {
        // É um objeto aninhado, fazer flatten recursivo
        Object.assign(flattened, flattenConfig(value, newKey));
      } else {
        // É um valor primitivo ou array
        flattened[newKey] = value;
      }
    }
  }
  
  return flattened;
}

/**
 * Unflatten um objeto plano em estrutura aninhada
 * Exemplo: { "paths.application.data_directory": "data" }
 * Resultado: { paths: { application: { data_directory: "data" } } }
 */
export function unflattenConfig(flat: Record<string, any>): Record<string, any> {
  const result: Record<string, any> = {};
  
  for (const key in flat) {
    if (flat.hasOwnProperty(key)) {
      const keys = key.split('.');
      let current = result;
      
      for (let i = 0; i < keys.length - 1; i++) {
        const k = keys[i];
        if (!current[k]) {
          current[k] = {};
        }
        current = current[k];
      }
      
      current[keys[keys.length - 1]] = flat[key];
    }
  }
  
  return result;
}

/**
 * Formata o nome de exibição de uma chave aninhada
 * Exemplo: "paths.application.data_directory" -> "Application > Data Directory"
 */
export function formatConfigKey(key: string): string {
  const parts = key.split('.');
  
  // Se tiver apenas uma parte, retorna capitalizada
  if (parts.length === 1) {
    return capitalizeFirst(parts[0]);
  }
  
  // Pega a última parte (o campo real) e as anteriores (caminho)
  const fieldName = parts[parts.length - 1];
  const pathParts = parts.slice(0, -1);
  
  // Formata o caminho (última parte do caminho > campo)
  const lastPathPart = pathParts[pathParts.length - 1];
  return `${capitalizeFirst(lastPathPart)} > ${capitalizeFirst(fieldName)}`;
}

/**
 * Capitaliza a primeira letra e adiciona espaços antes de maiúsculas
 */
function capitalizeFirst(str: string): string {
  // Remove underscores e substitui por espaços
  let formatted = str.replace(/_/g, ' ');
  
  // Adiciona espaços antes de maiúsculas (camelCase)
  formatted = formatted.replace(/([a-z])([A-Z])/g, '$1 $2');
  
  // Capitaliza primeira letra de cada palavra
  return formatted
    .split(' ')
    .map(word => word.charAt(0).toUpperCase() + word.slice(1).toLowerCase())
    .join(' ');
}

/**
 * Obtém o caminho (seção pai) de uma chave aninhada
 * Exemplo: "paths.application.data_directory" -> "paths.application"
 */
export function getConfigKeyPath(key: string): string {
  const parts = key.split('.');
  return parts.slice(0, -1).join('.');
}

/**
 * Obtém o nome do campo (última parte) de uma chave aninhada
 * Exemplo: "paths.application.data_directory" -> "data_directory"
 */
export function getConfigFieldName(key: string): string {
  const parts = key.split('.');
  return parts[parts.length - 1];
}

