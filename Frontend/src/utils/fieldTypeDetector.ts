/**
 * Detecta o tipo de campo baseado no nome e valor
 */
export type FieldType = 'boolean' | 'number' | 'time' | 'text';

/**
 * Padrões para detectar campos booleanos
 */
const BOOLEAN_PATTERNS = [
  /^Allow/i,
  /^Enable/i,
  /^Disable/i,
  /^Hide/i,
  /^Show/i,
  /^Use/i,
  /^Log/i,
  /Can/i,
  /Should/i,
  /Enabled$/i, // Campos que terminam com "Enabled" são booleanos (ex: MaxPingCheckEnabled)
  /Disabled$/i, // Campos que terminam com "Disabled" são booleanos
];

/**
 * Padrões para detectar campos numéricos
 */
const NUMERIC_PATTERNS = [
  /Multiplier$/i,
  /Amount$/i,
  /Count$/i,
  /Timer$/i,
  /Cooldown$/i,
  /Duration$/i,
  /Rate$/i,
  /Ping$/i,
  /Price$/i,
  /Cost$/i,
  /Distance$/i,
  /Radius$/i,
  /Speed$/i,
  /Weight$/i,
  /Health$/i,
  /Damage$/i,
  /Threshold$/i,
  /Percentage$/i,
  /Interval$/i,
  /Period$/i,
  /Budget$/i,
  /Bounds$/i,
  /Chance$/i,
  /Bonus$/i,
  /Penalty$/i,
  /Reward$/i,
  /Points$/i,
  /Level$/i,
  /^Max/i,
  /^Min/i,
  /^Version$/i,
  /^Players$/i,
  /^Port$/i,
];

/**
 * Verifica se um valor é booleano (0, 1, true, false)
 */
function isBooleanValue(value: string | boolean | number): boolean {
  if (typeof value === 'boolean') return true;
  if (typeof value === 'number') return value === 0 || value === 1;
  const trimmed = String(value).trim().toLowerCase();
  return trimmed === '0' || trimmed === '1' || trimmed === 'true' || trimmed === 'false';
}

/**
 * Verifica se um valor é numérico (incluindo negativos e decimais)
 * Retorna false se contiver caracteres não numéricos (exceto sinal negativo e ponto decimal)
 */
function isNumericValue(value: string): boolean {
  if (!value || value.trim() === '') return false;
  const trimmed = value.trim();
  // Se contém letras ou caracteres especiais (exceto - e .), não é numérico puro
  if (/[a-zA-Z]/.test(trimmed)) return false;
  // Permite números negativos, decimais e notação científica
  return /^-?\d+(\.\d+)?([eE][+-]?\d+)?$/.test(trimmed);
}

/**
 * Verifica se um valor está no formato de tempo HH:MM ou HH:MM:SS
 */
function isTimeFormat(value: string): boolean {
  if (!value || value.trim() === '') return false;
  const trimmed = value.trim();
  // Aceita HH:MM ou HH:MM:SS
  return /^\d{1,3}:\d{2}(:\d{2})?$/.test(trimmed);
}

/**
 * Detecta o tipo de campo baseado no nome e valor
 */
export function getFieldType(key: string, value: string | boolean | number): FieldType {
  const fieldName = key.replace(/^scum\./, '');
  const stringValue = String(value);

  // 1. Verificar se é formato de tempo (HH:MM ou HH:MM:SS)
  if (isTimeFormat(stringValue)) {
    return 'time';
  }

  // 2. Verificar se é booleano
  // PRIMEIRO verificar pelo nome se tem padrões booleanos (incluindo "Enabled" no final)
  // Isso tem prioridade sobre padrões numéricos para evitar conflitos
  const isBooleanName = BOOLEAN_PATTERNS.some(pattern => pattern.test(fieldName));
  
  // Se o nome sugere booleano E o valor é boolean (0, 1, true, false), é boolean
  if (isBooleanName && isBooleanValue(value)) {
    return 'boolean';
  }
  
  // Se o valor é boolean (0, 1, true, false) mas o nome não sugere explicitamente
  if (isBooleanValue(value)) {
    // Se for true/false explícito, sempre é boolean
    if (typeof value === 'boolean' || stringValue.toLowerCase() === 'true' || stringValue.toLowerCase() === 'false') {
      return 'boolean';
    }
    // Se for 0/1, verificar se o nome sugere booleano (caso não tenha sido detectado antes)
    if (isBooleanName) {
      return 'boolean';
    }
  }

  // 3. Verificar se é numérico
  // Só verificar como numérico se NÃO for um campo booleano pelo nome
  if (isNumericValue(stringValue) && !isBooleanName) {
    // Verificar se o nome também sugere numérico
    const isNumericName = NUMERIC_PATTERNS.some(pattern => pattern.test(fieldName));
    if (isNumericName) {
      return 'number';
    }
    // Se o valor é numérico mas o nome não sugere, ainda pode ser número
    // (ex: SettingsVersion, MaxPlayers)
    return 'number';
  }

  // 4. Verificar pelo nome se é booleano (mesmo que o valor não seja 0/1/true/false ainda)
  if (isBooleanName && (stringValue === '' || isBooleanValue(value))) {
    return 'boolean';
  }

  // 5. Verificar pelo nome se é numérico
  // Mas só se o valor não contém caracteres não numéricos (como "g", ":", etc.)
  const isNumericName = NUMERIC_PATTERNS.some(pattern => pattern.test(fieldName));
  if (isNumericName && isNumericValue(stringValue)) {
    return 'number';
  }

  // 6. Padrão: texto (inclui valores com sufixos como "1g", "3g", etc.)
  return 'text';
}

/**
 * Valida um valor baseado no tipo de campo
 */
export function validateFieldValue(type: FieldType, value: string): { valid: boolean; error?: string } {
  if (value.trim() === '') {
    return { valid: true }; // Campos vazios são permitidos
  }

  switch (type) {
    case 'boolean':
      if (!isBooleanValue(value)) {
        return { valid: false, error: 'Deve ser true, false, 0 ou 1' };
      }
      break;

    case 'number':
      if (!isNumericValue(value)) {
        return { valid: false, error: 'Deve ser um número válido' };
      }
      break;

    case 'time':
      if (!isTimeFormat(value)) {
        return { valid: false, error: 'Formato inválido. Use HH:MM ou HH:MM:SS (ex: 02:00 ou 02:00:00)' };
      }
      // Validar valores (horas: 0-24, minutos: 0-59, segundos: 0-59 se presente)
      // Nota: 24:00:00 é válido (representa 24 horas = 1 dia completo)
      const timeParts = value.split(':');
      const hours = Number(timeParts[0]);
      const minutes = Number(timeParts[1]);
      const seconds = timeParts[2] ? Number(timeParts[2]) : null;
      
      // Aceitar 24:00:00 como caso especial (24 horas = 1 dia)
      if (hours === 24 && minutes === 0 && (seconds === null || seconds === 0)) {
        return { valid: true };
      }
      
      // Validação padrão: horas 0-23, minutos 0-59
      if (hours < 0 || hours > 999 || minutes < 0 || minutes > 59) {
        return { valid: false, error: 'Valores inválidos. Horas: 0-999, Minutos: 0-59' };
      }
      if (seconds !== null && (seconds < 0 || seconds > 59)) {
        return { valid: false, error: 'Valores inválidos. Segundos: 0-59' };
      }
      break;

    case 'text':
      // Texto sempre válido
      break;
  }

  return { valid: true };
}

