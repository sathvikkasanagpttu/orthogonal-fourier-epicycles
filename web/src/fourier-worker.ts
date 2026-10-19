/**
 * High-performance epicycle chain computation with optional Lanczos smoothing.
 */

import { FourierChain } from "./types";

export interface EpicycleCircle {
  cx: number;
  cy: number;
  r: number;
  tx: number;
  ty: number;
}

export interface ChainResult {
  circles: EpicycleCircle[];
  tip: { x: number; y: number };
}

/**
 * Compute the visible epicycles and exact summed tip for a 1D real Fourier chain.
 *
 * @param t Current parameter angle in [0, 2π)
 * @param origin Base center position {x, y}
 * @param chain Fourier chain data
 * @param N_active Number of active harmonics to sum
 * @param maxVisible Number of circles to draw visibly
 * @param isX True for X chain (dx is horizontal), False for Y chain (dy is vertical)
 * @param useLanczos Apply Lanczos sigma factor smoothing
 */
export function computeChain(
  t: number,
  origin: { x: number; y: number },
  chain: FourierChain,
  N_active: number,
  maxVisible: number = 25,
  isX: boolean = true,
  useLanczos: boolean = false
): ChainResult {
  const totalHarmonics = chain.order.length;
  const total = Math.min(N_active, totalHarmonics);
  const order = chain.order;
  const R = chain.R;
  const phi = chain.phi;

  const visCount = Math.min(maxVisible, total);
  const circles: EpicycleCircle[] = [];

  let curX = origin.x;
  let curY = origin.y;

  // Pre-calculate Lanczos sigma multipliers if requested
  for (let i = 0; i < visCount; i++) {
    const idx = order[i];
    const k = idx + 1;
    let radius = R[idx];

    if (useLanczos && total > 1) {
      const sincArg = (Math.PI * k) / total;
      const sigma = Math.sin(sincArg) / sincArg;
      radius *= sigma;
    }

    const angle = k * t - phi[idx];

    let dx = 0;
    let dy = 0;

    if (isX) {
      dx = radius * Math.cos(angle);
      dy = radius * Math.sin(angle);
    } else {
      dx = radius * Math.sin(angle);
      // Canvas coordinate system: invert Y so positive cartesian y goes UP on screen
      dy = -radius * Math.cos(angle);
    }

    const nextX = curX + dx;
    const nextY = curY + dy;

    circles.push({ cx: curX, cy: curY, r: radius, tx: nextX, ty: nextY });
    curX = nextX;
    curY = nextY;
  }

  // Sum remaining tail harmonics invisibly to guarantee exact tip position
  for (let i = visCount; i < total; i++) {
    const idx = order[i];
    const k = idx + 1;
    let radius = R[idx];

    if (useLanczos && total > 1) {
      const sincArg = (Math.PI * k) / total;
      const sigma = Math.sin(sincArg) / sincArg;
      radius *= sigma;
    }

    const angle = k * t - phi[idx];

    if (isX) {
      curX += radius * Math.cos(angle);
      curY += radius * Math.sin(angle);
    } else {
      curX += radius * Math.sin(angle);
      curY -= radius * Math.cos(angle);
    }
  }

  return { circles, tip: { x: curX, y: curY } };
}
