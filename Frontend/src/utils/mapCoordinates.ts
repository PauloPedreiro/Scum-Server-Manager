/**
 * Funções de conversão de coordenadas do jogo SCUM para pixels do mapa
 */

import {
  MAP_WIDTH,
  MAP_HEIGHT,
  CENTER_X,
  CENTER_Y,
  CENTER_PIXEL_X,
  CENTER_PIXEL_Y,
  SCALE_X,
  SCALE_Y,
  AFFINE_TRANSFORM
} from './mapCalibration';

export const MAP_COORDINATE_ERROR = {
  INVALID_FORMAT: 'MAP_COORDINATE_INVALID_FORMAT',
  INVALID_NUMBER: 'MAP_COORDINATE_INVALID_NUMBER'
} as const;

export type MapCoordinateErrorCode =
  (typeof MAP_COORDINATE_ERROR)[keyof typeof MAP_COORDINATE_ERROR];

export interface GameCoordinates {
  x: number;
  y: number;
}

export interface PixelCoordinates {
  x: number;
  y: number;
}

/**
 * Parse das coordenadas do jogo
 * Extrai os valores X e Y do formato do jogo:
 * {X=-142798.922 Y=-142780.359 Z=39619.605|P=0.000000 Y=0.000000 R=0.000000}
 */
export function parseCoordinates(input: string): GameCoordinates {
  const regex = /X=([-+]?\d+\.?\d*)\s+Y=([-+]?\d+\.?\d*)/;
  const match = input.match(regex);
  
  if (!match) {
    throw new Error(MAP_COORDINATE_ERROR.INVALID_FORMAT);
  }

  const x = parseFloat(match[1]);
  const y = parseFloat(match[2]);

  // Validação básica (apenas verifica se são números válidos)
  if (isNaN(x) || isNaN(y)) {
    throw new Error(MAP_COORDINATE_ERROR.INVALID_NUMBER);
  }

  return { x, y };
}

/**
 * Conversão de coordenadas do jogo para pixels
 * Calibração baseada em posições reais dos cruzamentos
 * O mapa tem inversão horizontal (X) aplicada automaticamente
 */
export function gameToPixel(gameX: number, gameY: number): PixelCoordinates {
  // Preferir transformação afim (regressão 2D) para melhor precisão em todo o mapa.
  // pixelX_calc = ax*X + bx*Y + cx (antes de inverter)
  // pixelY_calc = ay*X + by*Y + cy
  const hasAffine =
    Number.isFinite(AFFINE_TRANSFORM.ax) &&
    Number.isFinite(AFFINE_TRANSFORM.bx) &&
    Number.isFinite(AFFINE_TRANSFORM.cx) &&
    Number.isFinite(AFFINE_TRANSFORM.ay) &&
    Number.isFinite(AFFINE_TRANSFORM.by) &&
    Number.isFinite(AFFINE_TRANSFORM.cy);

  let calculatedX: number;
  let calculatedY: number;

  if (hasAffine) {
    calculatedX =
      AFFINE_TRANSFORM.ax * gameX + AFFINE_TRANSFORM.bx * gameY + AFFINE_TRANSFORM.cx;
    calculatedY =
      AFFINE_TRANSFORM.ay * gameX + AFFINE_TRANSFORM.by * gameY + AFFINE_TRANSFORM.cy;
  } else {
    // Fallback antigo (centro + escala)
    const deltaX = gameX - CENTER_X;
    const deltaY = gameY - CENTER_Y;
    calculatedX = CENTER_PIXEL_X + deltaX * SCALE_X;
    calculatedY = CENTER_PIXEL_Y + deltaY * SCALE_Y;
  }

  // APLICA INVERSÃO HORIZONTAL (X)
  const pixelX = MAP_WIDTH - calculatedX;
  const pixelY = calculatedY;

  // Clamp para garantir que fique dentro dos limites do mapa visual
  const clampedX = Math.max(0, Math.min(MAP_WIDTH, pixelX));
  const clampedY = Math.max(0, Math.min(MAP_HEIGHT, pixelY));

  return { x: clampedX, y: clampedY };
}

/**
 * Cálculo do quadrante
 * O mapa está dividido em 5x5 quadrantes:
 * Cada quadrante tem 216x216 px (1080 / 5)
 * Nomenclatura: Z0-Z4, A0-A4, B0-B4, C0-C4, D0-D4
 * Z0 = canto inferior esquerdo, D4 = canto superior direito
 */
export function calculateQuadrant(pixelX: number, pixelY: number): string {
  // Cada quadrante tem 216 pixels
  const quadrantSize = MAP_WIDTH / 5;
  
  // Calcula o índice da coluna (0-4, da esquerda para direita)
  const col = Math.floor(pixelX / quadrantSize);
  // Calcula o índice da linha (0-4, de cima para baixo)
  const row = Math.floor(pixelY / quadrantSize);
  
  // Limita aos valores válidos (0-4)
  const colIndex = Math.max(0, Math.min(4, col));
  const rowIndex = Math.max(0, Math.min(4, row));
  
  // Mapeia para as letras: Z (linha 4), A (linha 3), B (linha 2), C (linha 1), D (linha 0)
  const letters = ['D', 'C', 'B', 'A', 'Z'];
  const letter = letters[rowIndex];
  const number = colIndex;
  
  return `${letter}${number}`;
}

