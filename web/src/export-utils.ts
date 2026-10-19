/**
 * Export utilities for Orthogonal Fourier Epicycles.
 * Supports:
 * - Canvas PNG screenshot
 * - WebM canvas video recording (1 complete period or manual stop)
 * - JSON Fourier coefficients export
 * - CSV Fourier coefficients export
 */

import { MapData } from "./types";

export function exportCanvasPNG(canvas: HTMLCanvasElement, filename: string = "fourier_epicycles.png"): void {
  const link = document.createElement("a");
  link.download = filename;
  link.href = canvas.toDataURL("image/png");
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
}

export interface VideoRecorderController {
  stop: () => void;
  isRecording: () => boolean;
}

export function recordCanvasWebM(
  canvas: HTMLCanvasElement,
  durationMs: number,
  filename: string = "fourier_animation.webm",
  onProgress?: (progress: number) => void,
  onComplete?: () => void
): VideoRecorderController {
  const stream = canvas.captureStream(60);
  let mimeType = "video/webm;codecs=vp9";
  if (!MediaRecorder.isTypeSupported(mimeType)) {
    mimeType = "video/webm";
  }

  const mediaRecorder = new MediaRecorder(stream, {
    mimeType,
    videoBitsPerSecond: 8000000,
  });

  const chunks: Blob[] = [];
  let isRecording = true;

  mediaRecorder.ondataavailable = (e) => {
    if (e.data && e.data.size > 0) {
      chunks.push(e.data);
    }
  };

  mediaRecorder.onstop = () => {
    isRecording = false;
    const blob = new Blob(chunks, { type: "video/webm" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = filename;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
    if (onComplete) onComplete();
  };

  mediaRecorder.start(100);

  const startTime = performance.now();
  const timer = setInterval(() => {
    const elapsed = performance.now() - startTime;
    const progress = Math.min(1, elapsed / durationMs);
    if (onProgress) onProgress(progress);
    if (elapsed >= durationMs) {
      clearInterval(timer);
      if (mediaRecorder.state !== "inactive") {
        mediaRecorder.stop();
      }
    }
  }, 100);

  return {
    stop: () => {
      clearInterval(timer);
      if (mediaRecorder.state !== "inactive") {
        mediaRecorder.stop();
      }
      isRecording = false;
    },
    isRecording: () => isRecording,
  };
}

export function exportCoefficientsJSON(mapData: MapData, activeN: number): void {
  const exportPayload = {
    id: mapData.id,
    name: mapData.name,
    continent: mapData.continent,
    activeN,
    rings: mapData.rings.map((ring) => {
      const N = Math.min(activeN, ring.x_chain.R.length);
      return {
        ring_id: ring.ring_id,
        area_ratio: ring.area_ratio,
        a0: ring.x_chain.a0,
        c0: ring.y_chain.c0,
        x_harmonics: ring.x_chain.order.slice(0, N).map((k, i) => ({
          frequency_k: k,
          amplitude_R: ring.x_chain.R[i],
          phase_phi: ring.x_chain.phi[i],
          a_k: ring.x_chain.a ? ring.x_chain.a[i] : undefined,
          b_k: ring.x_chain.b ? ring.x_chain.b[i] : undefined,
        })),
        y_harmonics: ring.y_chain.order.slice(0, N).map((k, i) => ({
          frequency_k: k,
          amplitude_R: ring.y_chain.R[i],
          phase_phi: ring.y_chain.phi[i],
          c_k: ring.y_chain.c ? ring.y_chain.c[i] : undefined,
          d_k: ring.y_chain.d ? ring.y_chain.d[i] : undefined,
        })),
      };
    }),
  };

  const blob = new Blob([JSON.stringify(exportPayload, null, 2)], {
    type: "application/json",
  });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = `${mapData.id}_N${activeN}_fourier_coefficients.json`;
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  URL.revokeObjectURL(url);
}

export function exportCoefficientsCSV(mapData: MapData, activeN: number): void {
  // Export main ring (ring 0)
  const ring = mapData.rings[0];
  if (!ring) return;

  const N = Math.min(activeN, ring.x_chain.R.length);
  const rows: string[] = [
    `# Map: ${mapData.name} (${mapData.id})`,
    `# a0 = ${ring.x_chain.a0 ?? 0}, c0 = ${ring.y_chain.c0 ?? 0}`,
    "rank,frequency_k_x,amplitude_R_x,phase_phi_x,frequency_k_y,amplitude_R_y,phase_phi_y",
  ];

  for (let i = 0; i < N; i++) {
    const kx = ring.x_chain.order[i];
    const Rx = ring.x_chain.R[i].toFixed(7);
    const phix = ring.x_chain.phi[i].toFixed(7);

    const ky = ring.y_chain.order[i];
    const Ry = ring.y_chain.R[i].toFixed(7);
    const phiy = ring.y_chain.phi[i].toFixed(7);

    rows.push(`${i + 1},${kx},${Rx},${phix},${ky},${Ry},${phiy}`);
  }

  const blob = new Blob([rows.join("\n")], { type: "text/csv;charset=utf-8;" });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = `${mapData.id}_N${activeN}_harmonics.csv`;
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  URL.revokeObjectURL(url);
}
