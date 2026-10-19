/**
 * Type definitions for Orthogonal Fourier Epicycles: World Atlas Edition.
 */

export interface AtlasIndexEntry {
  id: string;
  name: string;
  continent: string;
  aspect: number;
  ring_count: number;
  centroid: [number, number];
  file: string;
  best_error?: number;
}

export interface FourierChain {
  a0?: number;
  c0?: number;
  a?: number[];
  b?: number[];
  c?: number[];
  d?: number[];
  R: number[];
  phi: number[];
  order: number[];
}

export interface RingData {
  ring_id: number;
  area_ratio: number;
  M: number;
  N: number;
  ground_truth: {
    x: number[];
    y: number[];
  };
  error_table: Record<string, number>;
  x_chain: FourierChain;
  y_chain: FourierChain;
}

export interface MapData {
  id: string;
  name: string;
  continent: string;
  centroid: [number, number];
  aspect: number;
  ring_count: number;
  rings: RingData[];
}

export type DetailLevel = "main" | "large" | "all";
export type AppTheme = "dark" | "light";

export interface AppState {
  selectedMapId: string;
  mapData: MapData | null;
  activeN: number;
  speed: number;
  isPlaying: boolean;
  showCircles: boolean;
  showProjectionLines: boolean;
  showSilhouette: boolean;
  showGroundTruth: boolean;
  useLanczos: boolean;
  detailLevel: DetailLevel;
  theme: AppTheme;
  currentT: number;
  activeRingIndex: number;
  isCompareMode: boolean;
  compareMapId: string | null;
  compareMapData: MapData | null;
  isAutoSweep: boolean;
}
