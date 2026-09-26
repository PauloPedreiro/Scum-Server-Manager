/**
 * Constantes e cálculos de calibração do mapa SCUM
 * Baseado na aplicação index.html com 16 pontos de cruzamento
 */

export const MAP_WIDTH = 1080; // Largura do mapa em pixels
export const MAP_HEIGHT = 1080; // Altura do mapa em pixels

// PONTO DE REFERÊNCIA: Centro do mapa
export const CENTER_X = -142798.922;  // Coordenada X do centro do jogo
export const CENTER_Y = -142780.359;  // Coordenada Y do centro do jogo
export const CENTER_PIXEL_X = 540;    // Centro do mapa em pixels (X)
export const CENTER_PIXEL_Y = 540;    // Centro do mapa em pixels (Y)

// TODOS OS 16 CRUZAMENTOS COM COORDENADAS DO JOGO E POSIÇÕES REAIS
export interface Intersection {
  id: string;
  label: string;
  gameX: number;
  gameY: number;
  pixelX: number;
  pixelY: number;
}

export const ALL_INTERSECTIONS: Intersection[] = [
  // Linha D-C (Y = 216px)
  { id: 'D-C-4-3', label: 'D4/D3/C4/C3', gameX: 314400.000, gameY: 314399.938, pixelX: 216, pixelY: 216 },
  { id: 'D-C-3-2', label: 'D3/D2/C3/C2', gameX: 9620.312, gameY: 314373.688, pixelX: 432, pixelY: 216 },
  { id: 'D-C-2-1', label: 'D2/D1/C2/C1', gameX: -295196.812, gameY: 314368.094, pixelX: 648, pixelY: 216 },
  { id: 'D-C-1-0', label: 'D1/D0/C1/C0', gameX: -599999.062, gameY: 314380.656, pixelX: 864, pixelY: 216 },
  
  // Linha C-B (Y = 432px)
  { id: 'C-B-4-3', label: 'C4/C3/B4/B3', gameX: 314400.000, gameY: 9599.969, pixelX: 216, pixelY: 432 },
  { id: 'C-B-3-2', label: 'C3/C2/B3/B2', gameX: 9599.000, gameY: 9587.815, pixelX: 432, pixelY: 432 },
  { id: 'C-B-2-1', label: 'C2/C1/B2/B1', gameX: -295200.000, gameY: 9599.965, pixelX: 648, pixelY: 432 },
  { id: 'C-B-1-0', label: 'C1/C0/B1/B0', gameX: -600005.250, gameY: 9593.698, pixelX: 864, pixelY: 432 },
  
  // Linha B-A (Y = 648px)
  { id: 'B-A-4-3', label: 'B4/B3/A4/A3', gameX: 314401.500, gameY: -295219.562, pixelX: 216, pixelY: 648 },
  { id: 'B-A-3-2', label: 'B3/B2/A3/A2', gameX: 9593.594, gameY: -295233.000, pixelX: 432, pixelY: 648 },
  { id: 'B-A-2-1', label: 'B2/B1/A2/A1', gameX: -295192.781, gameY: -295188.625, pixelX: 648, pixelY: 648 },
  { id: 'B-A-1-0', label: 'B1/B0/A1/A0', gameX: -600001.312, gameY: -295201.375, pixelX: 864, pixelY: 648 },
  
  // Linha A-Z (Y = 864px)
  { id: 'A-Z-4-3', label: 'A4/A3/Z4/Z3', gameX: 314400.000, gameY: -599981.438, pixelX: 216, pixelY: 864 },
  { id: 'A-Z-3-2', label: 'A3/A2/Z3/Z2', gameX: 9600.000, gameY: -600000.000, pixelX: 432, pixelY: 864 },
  { id: 'A-Z-2-1', label: 'A2/A1/Z2/Z1', gameX: -295205.219, gameY: -599993.750, pixelX: 648, pixelY: 864 },
  { id: 'A-Z-1-0', label: 'A1/A0/Z1/Z0', gameX: -600000.000, gameY: -600000.000, pixelX: 864, pixelY: 864 }
];

/**
 * Calcula as escalas usando regressão linear (mínimos quadrados)
 * Usa todos os 16 pontos para calcular SCALE_X e SCALE_Y
 */
function calculateScales() {
  let sumDeltaX = 0, sumDeltaY = 0;
  let sumDeltaPixelX = 0, sumDeltaPixelY = 0;
  let sumDeltaXDeltaPixelX = 0, sumDeltaYDeltaPixelY = 0;
  let sumDeltaXSquared = 0, sumDeltaYSquared = 0;
  
  ALL_INTERSECTIONS.forEach(intersection => {
    const deltaX = intersection.gameX - CENTER_X;
    const deltaY = intersection.gameY - CENTER_Y;
    
    // IMPORTANTE: As posições pixelX do JSON já estão invertidas
    // Para calcular a escala, precisamos da posição ANTES da inversão
    // pixelX_real = 1080 - pixelX_calc, então pixelX_calc = 1080 - pixelX_real
    const pixelX_calc = MAP_WIDTH - intersection.pixelX;
    const pixelY_calc = intersection.pixelY; // Y não é invertido
    
    const deltaPixelX = pixelX_calc - CENTER_PIXEL_X;
    const deltaPixelY = pixelY_calc - CENTER_PIXEL_Y;
    
    // Acumula valores para regressão linear
    sumDeltaX += deltaX;
    sumDeltaY += deltaY;
    sumDeltaPixelX += deltaPixelX;
    sumDeltaPixelY += deltaPixelY;
    sumDeltaXDeltaPixelX += deltaX * deltaPixelX;
    sumDeltaYDeltaPixelY += deltaY * deltaPixelY;
    sumDeltaXSquared += deltaX * deltaX;
    sumDeltaYSquared += deltaY * deltaY;
  });
  
  // Calcula escala usando regressão linear (mínimos quadrados)
  // SCALE = Σ(deltaCoord * deltaPixel) / Σ(deltaCoord²)
  const SCALE_X = sumDeltaXDeltaPixelX / sumDeltaXSquared;
  const SCALE_Y = sumDeltaYDeltaPixelY / sumDeltaYSquared;
  
  return { SCALE_X, SCALE_Y };
}

// Calcula as escalas uma vez ao carregar o módulo
export const { SCALE_X, SCALE_Y } = calculateScales();

export interface AffineTransform {
  ax: number;
  bx: number;
  cx: number;
  ay: number;
  by: number;
  cy: number;
}

function solve3x3(A: number[][], b: number[]): [number, number, number] {
  const M = [
    [A[0][0], A[0][1], A[0][2], b[0]],
    [A[1][0], A[1][1], A[1][2], b[1]],
    [A[2][0], A[2][1], A[2][2], b[2]],
  ];

  for (let i = 0; i < 3; i++) {
    let maxRow = i;
    for (let r = i + 1; r < 3; r++) {
      if (Math.abs(M[r][i]) > Math.abs(M[maxRow][i])) {
        maxRow = r;
      }
    }
    if (maxRow !== i) {
      const tmp = M[i];
      M[i] = M[maxRow];
      M[maxRow] = tmp;
    }

    const pivot = M[i][i];
    if (Math.abs(pivot) < 1e-12) {
      return [0, 0, 0];
    }

    for (let c = i; c < 4; c++) {
      M[i][c] /= pivot;
    }

    for (let r = 0; r < 3; r++) {
      if (r === i) continue;
      const factor = M[r][i];
      for (let c = i; c < 4; c++) {
        M[r][c] -= factor * M[i][c];
      }
    }
  }

  return [M[0][3], M[1][3], M[2][3]];
}

function calculateAffineTransform(): AffineTransform {
  // Ajuste afim (mínimos quadrados):
  // pixelX_calc = ax*gameX + bx*gameY + cx
  // pixelY_calc = ay*gameX + by*gameY + cy
  // Onde pixelX_calc é ANTES da inversão horizontal.

  let sXX = 0, sXY = 0, sX1 = 0;
  let sYY = 0, sY1 = 0;
  let s11 = 0;

  let sX_px = 0, sY_px = 0, s1_px = 0;
  let sX_py = 0, sY_py = 0, s1_py = 0;

  ALL_INTERSECTIONS.forEach((p) => {
    const x = p.gameX;
    const y = p.gameY;
    const one = 1;

    const pixelX_calc = MAP_WIDTH - p.pixelX;
    const pixelY_calc = p.pixelY;

    sXX += x * x;
    sXY += x * y;
    sX1 += x * one;
    sYY += y * y;
    sY1 += y * one;
    s11 += one * one;

    sX_px += x * pixelX_calc;
    sY_px += y * pixelX_calc;
    s1_px += one * pixelX_calc;

    sX_py += x * pixelY_calc;
    sY_py += y * pixelY_calc;
    s1_py += one * pixelY_calc;
  });

  const A = [
    [sXX, sXY, sX1],
    [sXY, sYY, sY1],
    [sX1, sY1, s11],
  ];

  const [ax, bx, cx] = solve3x3(A, [sX_px, sY_px, s1_px]);
  const [ay, by, cy] = solve3x3(A, [sX_py, sY_py, s1_py]);

  return { ax, bx, cx, ay, by, cy };
}

export const AFFINE_TRANSFORM: AffineTransform = calculateAffineTransform();

// Limites estimados
export const MIN_X = -500000;
export const MAX_X = 500000;
export const MIN_Y = -500000;
export const MAX_Y = 500000;

