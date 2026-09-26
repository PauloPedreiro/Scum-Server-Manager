/**
 * Define constraints e propriedades de validação para cada campo de configuração
 */

import { getFieldType } from './fieldTypeDetector';

export interface FieldConstraints {
  max?: number;
  min?: number;
  maxLength?: number;
  step?: number;
  pattern?: string;
  options?: string[]; // Para campos com valores específicos (ex: PVP/PVE)
  decimalPlaces?: number; // Limite de casas decimais
}

/**
 * Mapeamento de campos para suas constraints específicas
 */
const FIELD_CONSTRAINTS: Record<string, FieldConstraints> = {
  // General Section
  'scum.MaxPlayers': {
    min: 1,
    max: 128,
    step: 1,
  },
  'scum.ServerPlaystyle': {
    options: ['PVP', 'PVE'],
  },
  'scum.MessageOfTheDayCooldown': {
    min: 0,
    max: 9999999999,
    step: 0.0000001,
    decimalPlaces: 10,
  },
  'scum.MinServerTickRate': {
    min: 1,
    max: 100,
    step: 1,
  },
  'scum.MaxServerTickRate': {
    min: 1,
    max: 100,
    step: 1,
  },
  // MaxPingCheckEnabled é booleano, não precisa de constraints numéricas
  // 'scum.MaxPingCheckEnabled': removido - campo booleano
  'scum.MaxPing': {
    min: 0,
    max: 10000,
    step: 0.000001,
  },
  'scum.LogoutTimer': {
    min: -1,
    step: 0.000001,
  },
  'scum.LogoutTimerWhileCaptured': {
    min: -1,
    step: 0.000001,
  },
  'scum.LogoutTimerInBunker': {
    min: -1,
    step: 0.000001,
  },
  'scum.VotingDuration': {
    min: 0,
    step: 0.000001,
  },
  'scum.PlayerMinimalVotingInterest': {
    min: 0,
    max: 100,
    step: 0.000001,
  },
  'scum.PlayerPositiveVotePercentage': {
    min: 0,
    max: 100,
    step: 0.000001,
  },
  'scum.MasterServerUpdateSendInterval': {
    min: 0,
    step: 0.000001,
  },
  'scum.FameGainMultiplier': {
    min: 0,
    step: 0.000001,
  },
  'scum.FamePointPenaltyOnDeath': {
    min: 0,
    step: 0.000001,
  },
  'scum.FamePointPenaltyOnKilled': {
    min: 0,
    step: 0.000001,
  },
  'scum.FamePointRewardOnKill': {
    min: 0,
    step: 0.000001,
  },
  'scum.DaysSinceLastLoginToBecomeInactive': {
    min: 0,
    max: 365,
    step: 1,
  },
  'scum.MaximumTimeForChestsInForbiddenZones': {
    pattern: '^\\d{1,3}:\\d{2}:\\d{2}$',
    maxLength: 10,
  },
  'scum.SettingsVersion': {
    min: 0,
    step: 1,
  },

  // World Section - Adicionar conforme necessário
  'scum.MaxAllowedBirds': {
    min: 0,
    max: 1000,
    step: 1,
  },

  // Respawn Section
  'scum.SectorRespawnPrice': {
    min: 0,
    step: 0.000001,
  },
  'scum.RandomRespawnPrice': {
    min: 0,
    step: 0.000001,
  },
  'scum.ShelterRespawnPrice': {
    min: 0,
    step: 0.000001,
  },
  'scum.ShelterRespawnPriceOutsideFlagArea': {
    min: 0,
    step: 0.000001,
  },
  'scum.SquadRespawnPrice': {
    min: 0,
    step: 0.000001,
  },
  'scum.RandomRespawnInitialTime': {
    min: 0,
    step: 0.000001,
  },
  'scum.SectorRespawnInitialTime': {
    min: 0,
    step: 0.000001,
  },
  'scum.ShelterRespawnInitialTime': {
    min: 0,
    step: 0.000001,
  },
  'scum.SquadRespawnInitialTime': {
    min: 0,
    step: 0.000001,
  },
  'scum.RandomRespawnCooldown': {
    min: 0,
    step: 0.000001,
  },
  'scum.SectorRespawnCooldown': {
    min: 0,
    step: 0.000001,
  },
  'scum.ShelterRespawnCooldown': {
    min: 0,
    step: 0.000001,
  },
  'scum.SquadRespawnCooldown': {
    min: 0,
    step: 0.000001,
  },

  // Vehicles Section
  'scum.BatteryChargeWithAlternatorMultiplier': {
    min: 0,
    max: 10,
    step: 0.000001,
  },

  // Damage Section - Multipliers geralmente entre 0 e 10
  'scum.HumanToHumanDamageMultiplier': {
    min: 0,
    max: 10,
    step: 0.000001,
  },
  'scum.HumanToHumanArmedMeleeDamageMultiplier': {
    min: 0,
    max: 10,
    step: 0.000001,
  },
  'scum.HumanToHumanUnarmedMeleeDamageMultiplier': {
    min: 0,
    max: 10,
    step: 0.000001,
  },
  'scum.HumanToHumanThrowingDamageMultiplier': {
    min: 0,
    max: 10,
    step: 0.000001,
  },
  'scum.SentryDamageMultiplier': {
    min: 0,
    max: 10,
    step: 0.000001,
  },
  'scum.SentryRailgunDamageMultiplier': {
    min: 0,
    max: 10,
    step: 0.000001,
  },
  'scum.SentryGrenadeDamageMultiplier': {
    min: 0,
    max: 10,
    step: 0.000001,
  },
  'scum.BaseBuildingAttackerSentryDamageMultiplier': {
    min: 0,
    max: 10,
    step: 0.000001,
  },
};

/**
 * Obtém as constraints para um campo específico
 */
export function getFieldConstraints(key: string): FieldConstraints | null {
  return FIELD_CONSTRAINTS[key] || null;
}

/**
 * Valida um valor contra as constraints do campo
 */
export function validateFieldConstraints(
  key: string,
  value: string
): { valid: boolean; error?: string } {
  const constraints = getFieldConstraints(key);
  if (!constraints) {
    return { valid: true }; // Sem constraints = válido
  }

  // Campos vazios são permitidos (a menos que seja obrigatório)
  if (value.trim() === '') {
    return { valid: true };
  }

  // Validar opções específicas (ex: PVP/PVE)
  if (constraints.options) {
    if (!constraints.options.includes(value.trim())) {
      return {
        valid: false,
        error: `Deve ser um dos valores: ${constraints.options.join(', ')}`,
      };
    }
    return { valid: true };
  }

  // Verificar o tipo do campo antes de aplicar validações
  // Se for booleano, não aplicar validações numéricas
  const fieldType = getFieldType(key, value);
  
  // Se o campo é booleano, não validar como número (mesmo que tenha constraints numéricas)
  if (fieldType === 'boolean') {
    return { valid: true }; // Campos booleanos são validados apenas pelo tipo
  }

  // Validar números apenas para campos numéricos
  if (fieldType === 'number') {
    const numValue = parseFloat(value);
    if (isNaN(numValue)) {
      return { valid: false, error: 'Deve ser um número válido' };
    }

    // Validar min
    if (constraints.min !== undefined && numValue < constraints.min) {
      return {
        valid: false,
        error: `Valor mínimo: ${constraints.min}`,
      };
    }

    // Validar max
    if (constraints.max !== undefined && numValue > constraints.max) {
      return {
        valid: false,
        error: `Valor máximo: ${constraints.max}`,
      };
    }

    // Validar casas decimais
    if (constraints.decimalPlaces !== undefined) {
      const decimalPart = value.split('.')[1];
      if (decimalPart && decimalPart.length > constraints.decimalPlaces) {
        return {
          valid: false,
          error: `Máximo de ${constraints.decimalPlaces} casas decimais`,
        };
      }
    }
  }

  // Validar pattern (regex)
  if (constraints.pattern) {
    const regex = new RegExp(constraints.pattern);
    if (!regex.test(value)) {
      return { valid: false, error: 'Formato inválido' };
    }
  }

  return { valid: true };
}

/**
 * Formata um valor numérico para respeitar as casas decimais máximas
 */
export function formatNumericValue(value: string, decimalPlaces?: number): string {
  if (!decimalPlaces) return value;
  
  const numValue = parseFloat(value);
  if (isNaN(numValue)) return value;
  
  return numValue.toFixed(decimalPlaces);
}

