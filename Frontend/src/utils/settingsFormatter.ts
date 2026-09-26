/**
 * Utilitários para formatação e tradução de nomes de campos do ServerSettings.ini
 */

/**
 * Formata automaticamente nomes de campos desconhecidos
 * Exemplo: "scum.AllowAdminChat" → "Allow Admin Chat"
 */
export function formatFieldNameAuto(key: string): string {
  // 1. Remove prefixos conhecidos (scum., mod., custom.)
  let formatted = key
    .replace(/^(scum|mod|custom)\./i, '')
    .replace(/^mod\.[^.]*\./i, ''); // Remove mod.ModName.
  
  // 2. Adiciona espaços antes de maiúsculas
  formatted = formatted.replace(/([a-z])([A-Z])/g, '$1 $2');
  
  // 3. Capitaliza primeira letra
  formatted = formatted.charAt(0).toUpperCase() + formatted.slice(1);
  
  return formatted;
}

/**
 * Obtém o nome formatado/traduzido do campo
 * @param key - Nome original do campo (ex: "scum.AllowAdminChat")
 * @param section - Seção atual (ex: "General")
 * @param t - Função de tradução do i18next
 * @returns Nome formatado/traduzido
 */
export function getFieldDisplayName(
  key: string,
  section: string,
  t: (key: string) => string
): string {
  // 1. Tentar buscar tradução específica
  const translationKey = `settings.fields.${section}.${key}`;
  const translation = t(translationKey);
  
  // Se encontrou tradução (não retornou a chave), usar ela
  if (translation && translation !== translationKey) {
    return translation;
  }
  
  // 2. Fallback: formatação automática
  return formatFieldNameAuto(key);
}

