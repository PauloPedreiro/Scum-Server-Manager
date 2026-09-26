/**
 * Calibração de direções (yaw) do jogo SCUM
 * Converte valores de yaw do jogo para ângulos de rotação da seta no mapa
 * 
 * Valores de calibração:
 * - North: 91.09554290771484 → 0° (cima)
 * - South: -90.20409393310547 → 180° (baixo)
 * - East: 179.8896942138672 → 90° (direita)
 * - West: -0.1585388034582138 → 270° (esquerda)
 * - NW: 44.407691955566406 → 315° (noroeste)
 * - NE: 135.10470581054688 → 45° (nordeste)
 * - SE: -135.2752227783203 → 135° (sudeste)
 * - SW: -44.81232833862305 → 225° (sudoeste)
 */

// Pontos de calibração: [yaw_do_jogo, ângulo_correto_da_seta]
const CALIBRATION_POINTS: Array<[number, number]> = [
  [91.09554290771484, 0],      // North → 0°
  [-90.20409393310547, 180],   // South → 180°
  [179.8896942138672, 90],     // East → 90°
  [-0.1585388034582138, 270],  // West → 270°
  [44.407691955566406, 315],   // NW → 315°
  [135.10470581054688, 45],    // NE → 45°
  [-135.2752227783203, 135],   // SE → 135°
  [-44.81232833862305, 225],   // SW → 225°
];

/**
 * Normaliza um ângulo para o intervalo 0-360 graus
 */
function normalizeAngle(angle: number): number {
  let normalized = angle % 360;
  if (normalized < 0) {
    normalized += 360;
  }
  return normalized;
}

/**
 * Calcula a diferença angular entre dois ângulos (em graus)
 * Retorna o menor caminho entre os dois ângulos (-180 a 180)
 */
function angleDifference(a: number, b: number): number {
  let diff = normalizeAngle(a) - normalizeAngle(b);
  if (diff > 180) {
    diff -= 360;
  } else if (diff < -180) {
    diff += 360;
  }
  return diff;
}

/**
 * Converte um valor de yaw do jogo para o ângulo de rotação correto da seta
 * Usa mapeamento direto baseado nos pontos de calibração mais próximos
 * 
 * @param gameYaw - Valor de yaw do jogo (pode ser negativo)
 * @returns Ângulo de rotação da seta em graus (0-360, onde 0° = Norte/cima)
 */
export function gameYawToArrowAngle(gameYaw: number): number {
  // Normaliza o yaw do jogo para 0-360
  const normalizedGameYaw = normalizeAngle(gameYaw);

  // Encontra o ponto de calibração mais próximo
  let closestPoint: [number, number] | null = null;
  let minDist = Infinity;

  for (const [calibYaw, calibAngle] of CALIBRATION_POINTS) {
    const normalizedCalibYaw = normalizeAngle(calibYaw);
    const dist = Math.abs(angleDifference(normalizedGameYaw, normalizedCalibYaw));

    if (dist < minDist) {
      minDist = dist;
      closestPoint = [normalizedCalibYaw, calibAngle];
    }
  }

  if (!closestPoint) {
    // Fallback: se não encontrar pontos, usa uma rotação fixa
    // Baseado na média dos offsets: North (91° → 0°) = -91°
    const offset = -91;
    return normalizeAngle(normalizedGameYaw + offset);
  }

  const [closestYaw, closestAngle] = closestPoint;
  
  // Calcula a diferença entre o yaw atual e o ponto de calibração mais próximo
  const yawDiff = angleDifference(normalizedGameYaw, closestYaw);
  
  // Aplica a mesma diferença ao ângulo de destino
  // Se o yaw do jogo está X graus à frente do ponto de calibração,
  // o ângulo da seta também deve estar X graus à frente
  return normalizeAngle(closestAngle + yawDiff);
}

